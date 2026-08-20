"""Canonical timeframe semantics for E1 Slice 1."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .errors import UnsupportedTimeframeError

_TIMEFRAME_DURATION = {
    "1m": timedelta(minutes=1),
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
}

# Pionex Futures API uses uppercase M for minutes. Lowercase m is month.
_PIONEX_INTERVAL = {
    "1m": "1M",
    "15m": "15M",
    "1h": "60M",
    "4h": "4H",
}

SUPPORTED_TIMEFRAMES = frozenset(_TIMEFRAME_DURATION)


def timeframe_duration(timeframe: str) -> timedelta:
    try:
        return _TIMEFRAME_DURATION[timeframe]
    except KeyError as exc:
        raise UnsupportedTimeframeError(f"unsupported canonical timeframe: {timeframe!r}") from exc


def pionex_interval(timeframe: str) -> str:
    try:
        return _PIONEX_INTERVAL[timeframe]
    except KeyError as exc:
        raise UnsupportedTimeframeError(f"unsupported canonical timeframe: {timeframe!r}") from exc


def is_timeframe_aligned(value: datetime, timeframe: str) -> bool:
    if value.tzinfo is None or value.utcoffset() is None:
        return False
    utc_value = value.astimezone(timezone.utc)
    duration_ms = int(timeframe_duration(timeframe).total_seconds() * 1000)
    epoch_ms = int(utc_value.timestamp() * 1000)
    return epoch_ms % duration_ms == 0
