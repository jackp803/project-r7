from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from market_data import (  # noqa: E402
    MissingCandleError,
    UnclosedCandleError,
    load_pionex_historical_candles,
    normalize_pionex_kline_page,
    validate_historical_sequence,
)

UTC = timezone.utc
BASE = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def raw_kline(open_time: datetime) -> dict[str, object]:
    return {
        "time": ms(open_time),
        "open": "100.0",
        "high": "101.0",
        "low": "99.0",
        "close": "100.5",
        "volume": "10.0",
    }


def payload(rows: list[dict[str, object]], response_time: datetime) -> dict[str, object]:
    return {"result": True, "timestamp": ms(response_time), "data": {"klines": rows}}


class FakePagedPionexSource:
    def __init__(self, opens: list[datetime], response_time: datetime) -> None:
        self.opens = opens
        self.response_time = response_time
        self.calls: list[dict[str, Any]] = []

    def fetch_page(
        self,
        *,
        symbol: str,
        timeframe: str,
        end_time_ms: int | None,
        limit: int = 500,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "end_time_ms": end_time_ms,
                "limit": limit,
            }
        )
        eligible = [value for value in self.opens if end_time_ms is None or ms(value) <= end_time_ms]
        selected = sorted(eligible, reverse=True)[:limit]
        return payload([raw_kline(value) for value in selected], self.response_time)


class HistoricalSequenceTests(unittest.TestCase):
    def test_backward_pagination_yields_exact_ascending_sequence(self) -> None:
        opens = [BASE + timedelta(minutes=i) for i in range(4)]
        source = FakePagedPionexSource(opens, BASE + timedelta(hours=1))

        candles = load_pionex_historical_candles(
            source,
            symbol="BTC_USDT_PERP",
            timeframe="1m",
            start=BASE,
            end=BASE + timedelta(minutes=4),
            page_limit=2,
        )

        self.assertEqual([c.open_time for c in candles], opens)
        self.assertEqual(len(source.calls), 2)
        self.assertEqual(source.calls[0]["end_time_ms"], ms(BASE + timedelta(minutes=4)) - 1)
        self.assertEqual(source.calls[1]["end_time_ms"], ms(BASE + timedelta(minutes=2)) - 1)

    def test_gap_is_rejected_instead_of_filled(self) -> None:
        candles = normalize_pionex_kline_page(
            payload(
                [raw_kline(BASE), raw_kline(BASE + timedelta(minutes=2))],
                BASE + timedelta(hours=1),
            ),
            symbol="BTC_USDT_PERP",
            timeframe="1m",
        )
        with self.assertRaises(MissingCandleError):
            validate_historical_sequence(
                candles,
                symbol="BTC_USDT_PERP",
                timeframe="1m",
                start=BASE,
                end=BASE + timedelta(minutes=3),
            )

    def test_unclosed_candle_cannot_enter_closed_historical_sequence(self) -> None:
        candles = normalize_pionex_kline_page(
            payload([raw_kline(BASE)], BASE + timedelta(seconds=30)),
            symbol="BTC_USDT_PERP",
            timeframe="1m",
        )
        with self.assertRaises(UnclosedCandleError):
            validate_historical_sequence(
                candles,
                symbol="BTC_USDT_PERP",
                timeframe="1m",
                start=BASE,
                end=BASE + timedelta(minutes=1),
            )

    def test_loader_reports_missing_when_provider_range_is_incomplete(self) -> None:
        source = FakePagedPionexSource(
            [BASE, BASE + timedelta(minutes=2)],
            BASE + timedelta(hours=1),
        )
        with self.assertRaises(MissingCandleError):
            load_pionex_historical_candles(
                source,
                symbol="BTC_USDT_PERP",
                timeframe="1m",
                start=BASE,
                end=BASE + timedelta(minutes=3),
                page_limit=2,
            )


if __name__ == "__main__":
    unittest.main()
