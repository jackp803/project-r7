"""Pionex public historical kline adapter for E1 Slice 1.

Provider documentation baseline inspected 2026-08-20:
- REST base URL: https://api.pionex.com
- GET /api/v1/market/klines
- BTC_USDT_PERP futures symbol
- intervals use uppercase M for minutes (1M/15M/60M) and 4H for four hours
- response OHLCV values are strings; kline `time` is milliseconds

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
    ProviderResponseError,
    ProviderUnavailableError,
    UnsupportedSymbolError,
)
from .timeframes import pionex_interval, timeframe_duration

PIONEX_BASE_URL = "https://api.pionex.com"
PIONEX_KLINES_PATH = "/api/v1/market/klines"
PIONEX_SOURCE = "PIONEX_PUBLIC_KLINES"
SUPPORTED_SYMBOLS = frozenset({"BTC_USDT_PERP"})
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _millis_to_utc(value: Any, field_name: str) -> datetime:
    if isinstance(value, bool):
        raise ProviderResponseError(f"{field_name} must be integer milliseconds")
    try:
        milliseconds = int(value)
    except (TypeError, ValueError) as exc:
        raise ProviderResponseError(f"{field_name} must be integer milliseconds") from exc
    return _EPOCH + timedelta(milliseconds=milliseconds)


def _decimal_from_provider(value: Any, field_name: str) -> Decimal:
    # Pionex documents OHLCV fields as decimal strings. Reject binary floats so
    # provider/schema drift cannot silently contaminate canonical precision.
    if not isinstance(value, str):
        raise MalformedCandleError(f"Pionex {field_name} must be a decimal string")
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise MalformedCandleError(f"invalid Pionex decimal in {field_name}: {value!r}") from exc
    if not parsed.is_finite():
        raise MalformedCandleError(f"non-finite Pionex decimal in {field_name}")
    return parsed


def _extract_klines(payload: dict[str, Any]) -> tuple[datetime, list[dict[str, Any]]]:
    if payload.get("result") is not True:
        code = payload.get("code", "UNKNOWN")
        message = payload.get("message", "provider returned result=false")
        raise ProviderResponseError(f"Pionex error {code}: {message}")

    response_time = _millis_to_utc(payload.get("timestamp"), "timestamp")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise ProviderResponseError("Pionex response data must be an object")
    klines = data.get("klines")
    if not isinstance(klines, list):
        raise ProviderResponseError("Pionex response data.klines must be a list")
    if not all(isinstance(item, dict) for item in klines):
        raise ProviderResponseError("each Pionex kline must be an object")
    return response_time, klines


def normalize_pionex_kline_page(
    payload: dict[str, Any], *, symbol: str, timeframe: str
) -> tuple[Candle, ...]:
    """Normalize one Pionex page into ascending canonical Candles.

    The provider page may be strictly ascending or strictly descending. Any
    mixed order is surfaced as an out-of-order defect rather than silently
    repaired. Duplicate identities are rejected. Returned canonical Candles
    are always ordered by open_time ascending.
    """

    if symbol not in SUPPORTED_SYMBOLS:
        raise UnsupportedSymbolError(f"Slice 1 supports only: {sorted(SUPPORTED_SYMBOLS)!r}")

    response_time, raw_klines = _extract_klines(payload)
    duration = timeframe_duration(timeframe)
    seen_open_times: set[datetime] = set()
    observed_order: list[datetime] = []
    candles: list[Candle] = []

    for raw in raw_klines:
        open_time = _millis_to_utc(raw.get("time"), "kline.time")
        if open_time in seen_open_times:
            raise DuplicateCandleError(
                f"duplicate Pionex Candle identity: {symbol} {timeframe} {open_time.isoformat()}"
            )
        seen_open_times.add(open_time)
        observed_order.append(open_time)
        close_time = open_time + duration

        candle = Candle(
            schema_version=CONTRACT_SCHEMA_VERSION,
            symbol=symbol,
            timeframe=timeframe,
            open_time=open_time,
            close_time=close_time,
            open=_decimal_from_provider(raw.get("open"), "open"),
            high=_decimal_from_provider(raw.get("high"), "high"),
            low=_decimal_from_provider(raw.get("low"), "low"),
            close=_decimal_from_provider(raw.get("close"), "close"),
            volume=_decimal_from_provider(raw.get("volume"), "volume"),
            # Pionex kline payload does not expose a finalization flag. E1's
            # safe normalizer marks a candle closed only after the provider
            # response timestamp reaches/passes its exclusive close boundary.
            is_closed=response_time >= close_time,
            source=PIONEX_SOURCE,
        )
        candles.append(candle)

    if len(observed_order) > 1:
        ascending = all(a < b for a, b in zip(observed_order, observed_order[1:]))
        descending = all(a > b for a, b in zip(observed_order, observed_order[1:]))
        if not (ascending or descending):
            raise OutOfOrderCandleError("Pionex kline page is neither strictly ascending nor descending")

    return tuple(sorted(candles, key=lambda candle: candle.open_time))


class PionexPublicKlineSource:
    """Minimal unauthenticated HTTP source for Pionex historical klines."""

    def __init__(
        self,
        *,
        base_url: str = PIONEX_BASE_URL,
        timeout_seconds: float = 10.0,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._opener = opener or urlopen

    def build_klines_url(
        self,
        *,
        symbol: str,
        timeframe: str,
        end_time_ms: int | None,
        limit: int,
    ) -> str:
        if symbol not in SUPPORTED_SYMBOLS:
            raise UnsupportedSymbolError(f"Slice 1 supports only: {sorted(SUPPORTED_SYMBOLS)!r}")
        if not 1 <= limit <= 500:
            raise ValueError("Pionex kline limit must be between 1 and 500")

        params: dict[str, str | int] = {
            "symbol": symbol,
            "interval": pionex_interval(timeframe),
            "limit": limit,
        }
        if end_time_ms is not None:
            params["endTime"] = end_time_ms
        return f"{self.base_url}{PIONEX_KLINES_PATH}?{urlencode(params)}"

    def fetch_page(
        self,
        *,
        symbol: str,
        timeframe: str,
        end_time_ms: int | None,
        limit: int = 500,
    ) -> dict[str, Any]:
        url = self.build_klines_url(
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
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise ProviderUnavailableError(f"Pionex public kline request failed: {exc}") from exc

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderResponseError("Pionex returned non-JSON kline response") from exc
        if not isinstance(payload, dict):
            raise ProviderResponseError("Pionex kline response root must be an object")

        # Validate envelope now; normalization validates each kline later.
        _extract_klines(payload)
        return payload
