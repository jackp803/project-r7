"""Canonical timeframe semantics and the bounded OKX adapter mapping."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .errors import UnsupportedTimeframeError

_TIMEFRAME_DURATION = {
    "1m": timedelta(minutes=1),
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
}

# OKX API V5 historical-candles bar labels. Provider labels remain inside E1.
_OKX_BAR = {
    "1m": "1m",
    "15m": "15m",
    "1h": "1H",
    "4h": "4H",
}

SUPPORTED_TIMEFRAMES = frozenset(_TIMEFRAME_DURATION)


def timeframe_duration(timeframe: str) -> timedelta:
    try:
        return _TIMEFRAME_DURATION[timeframe]
    except KeyError as exc:
        raise UnsupportedTimeframeError(f"unsupported canonical timeframe: {timeframe!r}") from exc


def okx_bar(timeframe: str) -> str:
    try:
        return _OKX_BAR[timeframe]
    except KeyError as exc:
        raise UnsupportedTimeframeError(f"unsupported canonical timeframe: {timeframe!r}") from exc


def is_timeframe_aligned(value: datetime, timeframe: str) -> bool:
    if value.tzinfo is None or value.utcoffset() is None:
        return False
    utc_value = value.astimezone(timezone.utc)
    duration_ms = int(timeframe_duration(timeframe).total_seconds() * 1000)
    epoch_ms = int(utc_value.timestamp() * 1000)
    return epoch_ms % duration_ms == 0
