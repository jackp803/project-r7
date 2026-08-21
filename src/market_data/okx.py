"""OKX public historical-candle adapter for the bounded E1 migration.

Official OKX API V5 baseline inspected 2026-08-21:
- REST base URL: https://www.okx.com
- GET /api/v5/market/history-candles
- canonical BTC_USDT_PERP maps to BTC-USDT-SWAP
- bar labels used here: 1m / 15m / 1H / 4H
- `ts` is candle opening time in Unix milliseconds
- `confirm`: "0" uncompleted, "1" completed
- `after` paginates toward older records; maximum page limit is 100

No private credential is used or accepted by this adapter.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .candle import CONTRACT_SCHEMA_VERSION, Candle
from .errors import (
    DuplicateCandleError,
    MalformedCandleError,
    OutOfOrderCandleError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderUnavailableError,
    UnsupportedSymbolError,
)
from .timeframes import okx_bar, timeframe_duration

OKX_BASE_URL = "https://www.okx.com"
OKX_HISTORY_CANDLES_PATH = "/api/v5/market/history-candles"
OKX_SOURCE = "OKX_PUBLIC_HISTORY_CANDLES"
_CANONICAL_TO_OKX_INSTRUMENT = {"BTC_USDT_PERP": "BTC-USDT-SWAP"}
SUPPORTED_SYMBOLS = frozenset(_CANONICAL_TO_OKX_INSTRUMENT)
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def okx_instrument(symbol: str) -> str:
    try:
        return _CANONICAL_TO_OKX_INSTRUMENT[symbol]
    except KeyError as exc:
        raise UnsupportedSymbolError(f"OKX migration supports only: {sorted(SUPPORTED_SYMBOLS)!r}") from exc


def _millis_to_utc(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise ProviderResponseError(f"OKX {field_name} must be a millisecond timestamp string")
    try:
        milliseconds = int(value)
    except ValueError as exc:
        raise ProviderResponseError(f"OKX {field_name} must be integer milliseconds") from exc
    return _EPOCH + timedelta(milliseconds=milliseconds)


def _decimal_from_provider(value: Any, field_name: str) -> Decimal:
    if not isinstance(value, str):
        raise MalformedCandleError(f"OKX {field_name} must be a decimal string")
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise MalformedCandleError(f"invalid OKX decimal in {field_name}: {value!r}") from exc
    if not parsed.is_finite():
        raise MalformedCandleError(f"non-finite OKX decimal in {field_name}")
    return parsed


def _extract_history_rows(payload: dict[str, Any]) -> list[list[Any]]:
    code = payload.get("code")
    if code == "50011":
        raise ProviderRateLimitError(f"OKX rate limit 50011: {payload.get('msg', '')}")
    if code != "0":
        raise ProviderResponseError(f"OKX error {code!r}: {payload.get('msg', '')}")

    data = payload.get("data")
    if not isinstance(data, list):
        raise ProviderResponseError("OKX history-candles data must be a list")
    if not all(isinstance(item, list) for item in data):
        raise ProviderResponseError("each OKX history-candles row must be an array")
    return data


def _parse_history_row(
    raw: list[Any], *, symbol: str, timeframe: str
) -> tuple[datetime, Candle]:
    # Current OKX docs/examples have shown both 8- and 9-field history rows.
    # In both forms, OHLCV occupy indexes 1..5 and `confirm` is the final field.
    if len(raw) not in (8, 9):
        raise ProviderResponseError(
            f"OKX history-candles row must contain 8 or 9 fields; got {len(raw)}"
        )

    open_time = _millis_to_utc(raw[0], "history-candles.ts")
    confirm = raw[-1]
    if confirm not in ("0", "1"):
        raise ProviderResponseError(f"OKX candle confirm must be '0' or '1'; got {confirm!r}")

    close_time = open_time + timeframe_duration(timeframe)
    candle = Candle(
        schema_version=CONTRACT_SCHEMA_VERSION,
        symbol=symbol,
        timeframe=timeframe,
        open_time=open_time,
        close_time=close_time,
        open=_decimal_from_provider(raw[1], "open"),
        high=_decimal_from_provider(raw[2], "high"),
        low=_decimal_from_provider(raw[3], "low"),
        close=_decimal_from_provider(raw[4], "close"),
        # `vol` is preserved exactly as the provider's SWAP volume fact. E1 does
        # not reinterpret it as canonical position/order quantity.
        volume=_decimal_from_provider(raw[5], "volume"),
        is_closed=confirm == "1",
        source=OKX_SOURCE,
    )
    return open_time, candle


def normalize_okx_history_page(
    payload: dict[str, Any], *, symbol: str, timeframe: str
) -> tuple[Candle, ...]:
    """Normalize one OKX history page into ascending canonical Candles.

    Provider pages may be strictly descending (the normal OKX history shape)
    or strictly ascending. Mixed order is surfaced rather than silently fixed.
    Duplicate identities are rejected. Provider `confirm`, not wall-clock time,
    is the only source of canonical finality.
    """

    okx_instrument(symbol)
    okx_bar(timeframe)
    raw_rows = _extract_history_rows(payload)

    seen_open_times: set[datetime] = set()
    observed_order: list[datetime] = []
    candles: list[Candle] = []

    for raw in raw_rows:
        open_time, candle = _parse_history_row(raw, symbol=symbol, timeframe=timeframe)
        if open_time in seen_open_times:
            raise DuplicateCandleError(
                f"duplicate OKX Candle identity: {symbol} {timeframe} {open_time.isoformat()}"
            )
        seen_open_times.add(open_time)
        observed_order.append(open_time)
        candles.append(candle)

    if len(observed_order) > 1:
        ascending = all(a < b for a, b in zip(observed_order, observed_order[1:]))
        descending = all(a > b for a, b in zip(observed_order, observed_order[1:]))
        if not (ascending or descending):
            raise OutOfOrderCandleError(
                "OKX history-candles page is neither strictly ascending nor descending"
            )

    return tuple(sorted(candles, key=lambda candle: candle.open_time))


class OkxPublicHistoricalCandleSource:
    """Minimal unauthenticated HTTP source for OKX historical SWAP candles."""

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

    def build_history_url(
        self,
        *,
        symbol: str,
        timeframe: str,
        end_time_ms: int | None,
        limit: int,
    ) -> str:
        if not 1 <= limit <= 100:
            raise ValueError("OKX history-candles limit must be between 1 and 100")

        params: dict[str, str | int] = {
            "instId": okx_instrument(symbol),
            "bar": okx_bar(timeframe),
            "limit": limit,
        }
        if end_time_ms is not None:
            # OKX `after` returns records at/before the supplied timestamp.
            # The exact-range loader passes end-exclusive minus 1 ms.
            params["after"] = end_time_ms
        return f"{self.base_url}{OKX_HISTORY_CANDLES_PATH}?{urlencode(params)}"

    def fetch_page(
        self,
        *,
        symbol: str,
        timeframe: str,
        end_time_ms: int | None,
        limit: int = 100,
    ) -> dict[str, Any]:
        url = self.build_history_url(
            symbol=symbol,
            timeframe=timeframe,
            end_time_ms=end_time_ms,
            limit=limit,
        )
        request = Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "project-r7-e1/0.1"},
            method="GET",
        )
        try:
            with self._opener(request, timeout=self.timeout_seconds) as response:
                raw_body = response.read()
        except HTTPError as exc:
            raw_body = exc.read()
            try:
                error_payload = json.loads(raw_body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                error_payload = None
            if exc.code == 429 or (
                isinstance(error_payload, dict) and error_payload.get("code") == "50011"
            ):
                raise ProviderRateLimitError(f"OKX public history request rate-limited: HTTP {exc.code}") from exc
            raise ProviderUnavailableError(
                f"OKX public history request failed: HTTP {exc.code}"
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ProviderUnavailableError(f"OKX public history request failed: {exc}") from exc

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderResponseError("OKX returned non-JSON history-candles response") from exc
        if not isinstance(payload, dict):
            raise ProviderResponseError("OKX history-candles response root must be an object")

        _extract_history_rows(payload)
        return payload
