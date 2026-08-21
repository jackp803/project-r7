"""Executable Candle producer semantics for contracts-v0.1."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from .errors import MalformedCandleError
from .timeframes import timeframe_duration

CONTRACT_SCHEMA_VERSION = "contracts-v0.1"


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise MalformedCandleError(f"{field_name} must be timezone-aware UTC")
    return value.astimezone(timezone.utc)


def _decimal_string(value: Decimal) -> str:
    return format(value, "f")


def _rfc3339_z(value: datetime) -> str:
    value = value.astimezone(timezone.utc)
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class Candle:
    """Canonical E1 Candle consumed by E2/E3.

    Internal financial fields are Decimal. Interchange serialization emits
    decimal strings and RFC 3339 UTC timestamps, matching contracts-v0.1.
    """

    schema_version: str
    symbol: str
    timeframe: str
    open_time: datetime
    close_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    is_closed: bool
    source: str
    received_at: datetime | None = None
    source_record_id: str | None = None

    def __post_init__(self) -> None:
        if self.schema_version != CONTRACT_SCHEMA_VERSION:
            raise MalformedCandleError(
                f"unsupported Candle schema_version: {self.schema_version!r}; "
                f"expected {CONTRACT_SCHEMA_VERSION!r}"
            )
        if not self.symbol:
            raise MalformedCandleError("symbol must be non-empty")
        if not self.source:
            raise MalformedCandleError("source must be non-empty")
        if not isinstance(self.is_closed, bool):
            raise MalformedCandleError("is_closed must be bool")

        open_time = _utc(self.open_time, "open_time")
        close_time = _utc(self.close_time, "close_time")
        received_at = None if self.received_at is None else _utc(self.received_at, "received_at")
        object.__setattr__(self, "open_time", open_time)
        object.__setattr__(self, "close_time", close_time)
        object.__setattr__(self, "received_at", received_at)

        expected_duration = timeframe_duration(self.timeframe)
        if close_time <= open_time:
            raise MalformedCandleError("open_time must be before close_time")
        if close_time - open_time != expected_duration:
            raise MalformedCandleError(
                f"{self.timeframe} Candle duration must be {expected_duration}; "
                f"got {close_time - open_time}"
            )

        financial_fields = {
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }
        for name, value in financial_fields.items():
            if not isinstance(value, Decimal):
                raise MalformedCandleError(f"{name} must use Decimal semantics")
            if not value.is_finite():
                raise MalformedCandleError(f"{name} must be finite")

        if self.volume < Decimal("0"):
            raise MalformedCandleError("volume must be non-negative")
        if self.low > self.high:
            raise MalformedCandleError("low must be <= high")
        if not (self.low <= self.open <= self.high):
            raise MalformedCandleError("open must satisfy low <= open <= high")
        if not (self.low <= self.close <= self.high):
            raise MalformedCandleError("close must satisfy low <= close <= high")

    @property
    def identity(self) -> tuple[str, str, datetime]:
        return (self.symbol, self.timeframe, self.open_time)

    def to_interchange_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "open_time": _rfc3339_z(self.open_time),
            "close_time": _rfc3339_z(self.close_time),
            "open": _decimal_string(self.open),
            "high": _decimal_string(self.high),
            "low": _decimal_string(self.low),
            "close": _decimal_string(self.close),
            "volume": _decimal_string(self.volume),
            "is_closed": self.is_closed,
            "source": self.source,
        }
        if self.received_at is not None:
            payload["received_at"] = _rfc3339_z(self.received_at)
        if self.source_record_id is not None:
            payload["source_record_id"] = self.source_record_id
        return payload
