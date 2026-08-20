"""Deterministic closed historical Candle sequence for E1 Slice 1."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from .candle import Candle
from .errors import (
    DuplicateCandleError,
    IncompleteHistoricalRangeError,
    MissingCandleError,
    OutOfOrderCandleError,
    ProviderResponseError,
    RangeAlignmentError,
    UnclosedCandleError,
)
from .pionex import normalize_pionex_kline_page
from .timeframes import is_timeframe_aligned, timeframe_duration


class KlinePageSource(Protocol):
    def fetch_page(
        self,
        *,
        symbol: str,
        timeframe: str,
        end_time_ms: int | None,
        limit: int = 500,
    ) -> dict[str, Any]: ...


def _utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise RangeAlignmentError(f"{field_name} must be timezone-aware UTC")
    return value.astimezone(timezone.utc)


def _epoch_ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def validate_historical_sequence(
    candles: tuple[Candle, ...] | list[Candle],
    *,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
) -> tuple[Candle, ...]:
    """Validate an exact, gap-free, ascending, closed Candle range.

    This validator never sorts or repairs input. It surfaces duplicate,
    out-of-order, missing, wrong-boundary, and unclosed data explicitly.
    """

    start = _utc(start, "start")
    end = _utc(end, "end")
    if end <= start:
        raise RangeAlignmentError("historical end must be after start")
    if not is_timeframe_aligned(start, timeframe) or not is_timeframe_aligned(end, timeframe):
        raise RangeAlignmentError(
            f"historical range boundaries must align to canonical {timeframe} intervals"
        )

    duration = timeframe_duration(timeframe)
    sequence = tuple(candles)
    seen: set[tuple[str, str, datetime]] = set()
    expected_open = start
    previous_open: datetime | None = None

    for candle in sequence:
        if candle.symbol != symbol or candle.timeframe != timeframe:
            raise IncompleteHistoricalRangeError(
                "historical sequence contains a Candle from a different symbol/timeframe"
            )
        if candle.identity in seen:
            raise DuplicateCandleError(f"duplicate canonical Candle identity: {candle.identity!r}")
        seen.add(candle.identity)

        if previous_open is not None and candle.open_time <= previous_open:
            raise OutOfOrderCandleError(
                f"canonical Candle sequence is not strictly ascending at {candle.open_time.isoformat()}"
            )
        previous_open = candle.open_time

        if candle.open_time != expected_open:
            if candle.open_time > expected_open:
                raise MissingCandleError(
                    f"missing {symbol} {timeframe} Candle at {expected_open.isoformat()}"
                )
            raise OutOfOrderCandleError(
                f"unexpected overlapping/earlier Candle at {candle.open_time.isoformat()}"
            )
        if candle.close_time != candle.open_time + duration:
            raise IncompleteHistoricalRangeError("Candle duration does not match canonical timeframe")
        if not candle.is_closed:
            raise UnclosedCandleError(
                f"historical closed sequence contains provisional Candle {candle.open_time.isoformat()}"
            )
        expected_open = candle.close_time

    if expected_open != end:
        if expected_open < end:
            raise MissingCandleError(
                f"historical range ends early; next expected Candle is {expected_open.isoformat()}"
            )
        raise IncompleteHistoricalRangeError("historical sequence extends beyond requested end")

    return sequence


def load_pionex_historical_candles(
    source: KlinePageSource,
    *,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
    page_limit: int = 500,
) -> tuple[Candle, ...]:
    """Fetch an exact `[start, end)` closed historical range from Pionex.

    Pionex exposes `endTime` pagination but no startTime for this endpoint.
    E1 therefore paginates backwards, moves the cursor to one millisecond
    before the earliest returned open_time, then emits one ascending canonical
    sequence only after exact-range validation succeeds.
    """

    start = _utc(start, "start")
    end = _utc(end, "end")
    if end <= start:
        raise RangeAlignmentError("historical end must be after start")
    if not is_timeframe_aligned(start, timeframe) or not is_timeframe_aligned(end, timeframe):
        raise RangeAlignmentError(
            f"historical range boundaries must align to canonical {timeframe} intervals"
        )
    if not 1 <= page_limit <= 500:
        raise ValueError("page_limit must be between 1 and 500")

    # Requested range is half-open, while Pionex endTime is inclusive.
    cursor_end_ms = _epoch_ms(end) - 1
    collected: dict[tuple[str, str, datetime], Candle] = {}

    while True:
        payload = source.fetch_page(
            symbol=symbol,
            timeframe=timeframe,
            end_time_ms=cursor_end_ms,
            limit=page_limit,
        )
        page = normalize_pionex_kline_page(payload, symbol=symbol, timeframe=timeframe)
        if not page:
            break

        earliest_open = page[0].open_time
        for candle in page:
            # Exact historical path exports only fully-contained closed bars.
            if candle.open_time >= end or candle.close_time <= start:
                continue
            if candle.open_time < start or candle.close_time > end:
                continue
            if not candle.is_closed:
                continue
            if candle.identity in collected:
                raise DuplicateCandleError(
                    f"duplicate Candle across Pionex pages: {candle.identity!r}"
                )
            collected[candle.identity] = candle

        if earliest_open <= start:
            break

        next_cursor = _epoch_ms(earliest_open) - 1
        if next_cursor >= cursor_end_ms:
            raise ProviderResponseError("Pionex pagination cursor did not move backwards")
        cursor_end_ms = next_cursor

    ordered = tuple(sorted(collected.values(), key=lambda candle: candle.open_time))
    return validate_historical_sequence(
        ordered,
        symbol=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
    )
