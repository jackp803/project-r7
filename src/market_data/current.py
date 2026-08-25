"""Gate C current OKX public market-state normalization for E1.

This module is intentionally REST/public only. It normalizes current OKX ticker
facts into the existing contracts-v0.1 MarketSnapshot shape and exposes only
provider-confirmed candles whose canonical interval is already closed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .candle import CONTRACT_SCHEMA_VERSION, Candle
from .errors import (
    DuplicateCandleError,
    FutureMarketDataError,
    MalformedCandleError,
    MissingCandleError,
    NonMonotonicMarketDataError,
    OutOfOrderCandleError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
    StaleMarketDataError,
)
from .okx import OKX_BASE_URL, okx_instrument
from .timeframes import okx_bar, timeframe_duration

OKX_TICKER_PATH = "/api/v5/market/ticker"
OKX_CURRENT_CANDLES_PATH = "/api/v5/market/candles"
OKX_TICKER_SOURCE = "OKX_PUBLIC_TICKER"
OKX_CURRENT_CANDLES_SOURCE = "OKX_PUBLIC_CURRENT_CANDLES"
GATE_C_MAX_FRESHNESS_MS = 5_000
GATE_C_CLOCK_TOLERANCE_MS = 5_000
HEALTHY = "HEALTHY"
_HEALTH_STATUSES = frozenset({"HEALTHY", "DEGRADED", "UNHEALTHY", "UNKNOWN"})
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ProviderResponseError(f"{field_name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _rfc3339_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _millis_to_utc(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise ProviderResponseError(f"OKX {field_name} must be a millisecond timestamp string")
    try:
        milliseconds = int(value)
    except ValueError as exc:
        raise ProviderResponseError(f"OKX {field_name} must be integer milliseconds") from exc
    return _EPOCH + timedelta(milliseconds=milliseconds)


def _provider_decimal(value: Any, field_name: str) -> Decimal:
    if not isinstance(value, str) or not value:
        raise MalformedCandleError(f"OKX {field_name} must be a non-empty decimal string")
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise MalformedCandleError(f"invalid OKX decimal in {field_name}: {value!r}") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise MalformedCandleError(f"OKX {field_name} must be positive and finite")
    return parsed


def _provider_volume(value: Any) -> Decimal:
    if not isinstance(value, str) or not value:
        raise MalformedCandleError("OKX volume must be a non-empty decimal string")
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise MalformedCandleError(f"invalid OKX decimal in volume: {value!r}") from exc
    if not parsed.is_finite() or parsed < 0:
        raise MalformedCandleError("OKX volume must be non-negative and finite")
    return parsed


def _extract_data(payload: dict[str, Any], endpoint: str) -> list[Any]:
    code = payload.get("code")
    if code == "50011":
        raise ProviderRateLimitError(f"OKX rate limit 50011 at {endpoint}: {payload.get('msg', '')}")
    if code != "0":
        raise ProviderResponseError(f"OKX error {code!r} at {endpoint}: {payload.get('msg', '')}")
    data = payload.get("data")
    if not isinstance(data, list):
        raise ProviderResponseError(f"OKX {endpoint} data must be a list")
    return data


@dataclass(frozen=True, slots=True)
class MarketSnapshot:
    """Executable E1 representation of canonical contracts-v0.1 MarketSnapshot."""

    schema_version: str
    symbol: str
    observed_at: datetime
    received_at: datetime
    health_status: str
    source: str
    last_price: Decimal | None = None
    best_bid: Decimal | None = None
    best_ask: Decimal | None = None
    freshness_ms: int | None = None

    def __post_init__(self) -> None:
        if self.schema_version != CONTRACT_SCHEMA_VERSION:
            raise ProviderResponseError(
                f"unsupported MarketSnapshot schema_version: {self.schema_version!r}"
            )
        if not self.symbol or not self.source:
            raise ProviderResponseError("MarketSnapshot symbol/source must be non-empty")
        if self.health_status not in _HEALTH_STATUSES:
            raise ProviderResponseError(f"unsupported health_status: {self.health_status!r}")
        object.__setattr__(self, "observed_at", _utc(self.observed_at, "observed_at"))
        object.__setattr__(self, "received_at", _utc(self.received_at, "received_at"))
        if self.freshness_ms is not None and (
            not isinstance(self.freshness_ms, int) or self.freshness_ms < 0
        ):
            raise ProviderResponseError("freshness_ms must be a non-negative integer")
        for name in ("last_price", "best_bid", "best_ask"):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, Decimal) or not value.is_finite() or value <= 0
            ):
                raise MalformedCandleError(f"MarketSnapshot {name} must be positive Decimal")
        if self.best_bid is not None and self.best_ask is not None and self.best_bid > self.best_ask:
            raise MalformedCandleError("MarketSnapshot best_bid must be <= best_ask")

    def to_interchange_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "symbol": self.symbol,
            "observed_at": _rfc3339_z(self.observed_at),
            "received_at": _rfc3339_z(self.received_at),
            "health_status": self.health_status,
            "source": self.source,
        }
        for name in ("last_price", "best_bid", "best_ask"):
            value = getattr(self, name)
            if value is not None:
                payload[name] = format(value, "f")
        if self.freshness_ms is not None:
            payload["freshness_ms"] = self.freshness_ms
        return payload


def normalize_okx_ticker(
    payload: dict[str, Any],
    *,
    symbol: str,
    received_at: datetime,
    max_freshness_ms: int = GATE_C_MAX_FRESHNESS_MS,
    clock_tolerance_ms: int = GATE_C_CLOCK_TOLERANCE_MS,
) -> MarketSnapshot:
    """Normalize one healthy current OKX ticker or fail closed with a typed error."""

    provider_symbol = okx_instrument(symbol)
    received_at = _utc(received_at, "received_at")
    rows = _extract_data(payload, "market/ticker")
    if len(rows) != 1 or not isinstance(rows[0], dict):
        raise ProviderResponseError("OKX market/ticker must return exactly one object")
    row = rows[0]
    if row.get("instId") != provider_symbol:
        raise ProviderResponseError(
            f"OKX ticker instrument mismatch: expected {provider_symbol!r}, got {row.get('instId')!r}"
        )

    observed_at = _millis_to_utc(row.get("ts"), "ticker.ts")
    age_ms = int((received_at - observed_at).total_seconds() * 1000)
    if age_ms < -clock_tolerance_ms:
        raise FutureMarketDataError(
            f"OKX ticker timestamp is {-age_ms} ms in the future; tolerance={clock_tolerance_ms} ms"
        )
    if age_ms > max_freshness_ms:
        raise StaleMarketDataError(
            f"OKX ticker age {age_ms} ms exceeds Gate C limit {max_freshness_ms} ms"
        )

    last_price = _provider_decimal(row.get("last"), "ticker.last")
    best_bid = _provider_decimal(row.get("bidPx"), "ticker.bidPx")
    best_ask = _provider_decimal(row.get("askPx"), "ticker.askPx")
    if best_bid > best_ask:
        raise MalformedCandleError("OKX ticker bidPx must be <= askPx")

    return MarketSnapshot(
        schema_version=CONTRACT_SCHEMA_VERSION,
        symbol=symbol,
        observed_at=observed_at,
        received_at=received_at,
        health_status=HEALTHY,
        source=OKX_TICKER_SOURCE,
        last_price=last_price,
        best_bid=best_bid,
        best_ask=best_ask,
        freshness_ms=max(0, age_ms),
    )


class CurrentMarketState:
    """Monotonic accepted current-market truth for polling consumers."""

    def __init__(self) -> None:
        self._snapshots: dict[str, MarketSnapshot] = {}

    def accept_snapshot(self, snapshot: MarketSnapshot) -> MarketSnapshot:
        previous = self._snapshots.get(snapshot.symbol)
        if previous is not None and snapshot.observed_at < previous.observed_at:
            raise NonMonotonicMarketDataError(
                f"older {snapshot.symbol} observation {snapshot.observed_at.isoformat()} cannot replace "
                f"newer accepted {previous.observed_at.isoformat()}"
            )
        self._snapshots[snapshot.symbol] = snapshot
        return snapshot

    def ingest_ticker(
        self, payload: dict[str, Any], *, symbol: str, received_at: datetime
    ) -> MarketSnapshot:
        return self.accept_snapshot(
            normalize_okx_ticker(payload, symbol=symbol, received_at=received_at)
        )

    def current_snapshot(self, symbol: str) -> MarketSnapshot | None:
        return self._snapshots.get(symbol)


def normalize_okx_current_candles(
    payload: dict[str, Any],
    *,
    symbol: str,
    timeframe: str,
    received_at: datetime,
) -> tuple[Candle, ...]:
    """Return only confirmed candles whose canonical close boundary has passed.

    Provisional (`confirm=0`) rows and not-yet-closed intervals are validated but
    withheld. Duplicate, mixed-order, malformed, and gaps between exposed final
    candles remain explicit failures.
    """

    okx_instrument(symbol)
    okx_bar(timeframe)
    received_at = _utc(received_at, "received_at")
    rows = _extract_data(payload, "market/candles")
    if not all(isinstance(item, list) for item in rows):
        raise ProviderResponseError("each OKX market/candles row must be an array")

    duration = timeframe_duration(timeframe)
    seen: set[datetime] = set()
    observed_order: list[datetime] = []
    finalized: list[Candle] = []

    for raw in rows:
        if len(raw) not in (8, 9):
            raise ProviderResponseError(
                f"OKX market/candles row must contain 8 or 9 fields; got {len(raw)}"
            )
        open_time = _millis_to_utc(raw[0], "candles.ts")
        if open_time in seen:
            raise DuplicateCandleError(
                f"duplicate OKX current Candle identity: {symbol} {timeframe} {open_time.isoformat()}"
            )
        seen.add(open_time)
        observed_order.append(open_time)
        confirm = raw[-1]
        if confirm not in ("0", "1"):
            raise ProviderResponseError(f"OKX candle confirm must be '0' or '1'; got {confirm!r}")
        close_time = open_time + duration
        candle = Candle(
            schema_version=CONTRACT_SCHEMA_VERSION,
            symbol=symbol,
            timeframe=timeframe,
            open_time=open_time,
            close_time=close_time,
            open=_provider_decimal(raw[1], "candle.open"),
            high=_provider_decimal(raw[2], "candle.high"),
            low=_provider_decimal(raw[3], "candle.low"),
            close=_provider_decimal(raw[4], "candle.close"),
            volume=_provider_volume(raw[5]),
            is_closed=confirm == "1" and close_time <= received_at,
            source=OKX_CURRENT_CANDLES_SOURCE,
            received_at=received_at,
        )
        if candle.is_closed:
            finalized.append(candle)

    if len(observed_order) > 1:
        ascending = all(a < b for a, b in zip(observed_order, observed_order[1:]))
        descending = all(a > b for a, b in zip(observed_order, observed_order[1:]))
        if not (ascending or descending):
            raise OutOfOrderCandleError(
                "OKX market/candles page is neither strictly ascending nor descending"
            )

    finalized.sort(key=lambda candle: candle.open_time)
    for previous, current in zip(finalized, finalized[1:]):
        if current.open_time != previous.close_time:
            raise MissingCandleError(
                f"missing {symbol} {timeframe} current Candle after {previous.open_time.isoformat()}"
            )
    return tuple(finalized)


class OkxPublicCurrentMarketSource:
    """Credential-free OKX Gate C REST source restricted to ticker/current candles."""

    def __init__(
        self,
        *,
        base_url: str = OKX_BASE_URL,
        timeout_seconds: float = 10.0,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._opener = opener or urlopen

    def build_ticker_url(self, *, symbol: str) -> str:
        params = {"instId": okx_instrument(symbol)}
        return f"{self.base_url}{OKX_TICKER_PATH}?{urlencode(params)}"

    def build_candles_url(self, *, symbol: str, timeframe: str) -> str:
        params = {"instId": okx_instrument(symbol), "bar": okx_bar(timeframe)}
        return f"{self.base_url}{OKX_CURRENT_CANDLES_PATH}?{urlencode(params)}"

    def _fetch(self, url: str) -> dict[str, Any]:
        request = Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "project-r7-e1/0.1"},
            method="GET",
        )
        try:
            with self._opener(request, timeout=self.timeout_seconds) as response:
                raw_body = response.read()
        except HTTPError as exc:
            if exc.code == 429:
                raise ProviderRateLimitError("OKX public current-market request rate-limited") from exc
            raise ProviderUnavailableError(
                f"OKX public current-market request failed: HTTP {exc.code}"
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ProviderUnavailableError(f"OKX public current-market request failed: {exc}") from exc
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderResponseError("OKX returned non-JSON current-market response") from exc
        if not isinstance(payload, dict):
            raise ProviderResponseError("OKX current-market response root must be an object")
        return payload

    def fetch_ticker(self, *, symbol: str) -> dict[str, Any]:
        return self._fetch(self.build_ticker_url(symbol=symbol))

    def fetch_candles(self, *, symbol: str, timeframe: str) -> dict[str, Any]:
        return self._fetch(self.build_candles_url(symbol=symbol, timeframe=timeframe))
