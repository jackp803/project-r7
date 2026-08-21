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
    load_okx_historical_candles,
    normalize_okx_history_page,
    validate_historical_sequence,
)

UTC = timezone.utc
BASE = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def raw_row(open_time: datetime, *, confirm: str = "1") -> list[str]:
    return [
        str(ms(open_time)),
        "100.0",
        "101.0",
        "99.0",
        "100.5",
        "10.0",
        "1000.0",
        "1000.0",
        confirm,
    ]


def payload(rows: list[list[str]]) -> dict[str, object]:
    return {"code": "0", "msg": "", "data": rows}


class FakePagedOkxSource:
    def __init__(
        self,
        opens: list[datetime],
        *,
        confirm_by_open: dict[datetime, str] | None = None,
    ) -> None:
        self.opens = opens
        self.confirm_by_open = confirm_by_open or {}
        self.calls: list[dict[str, Any]] = []

    def fetch_page(
        self,
        *,
        symbol: str,
        timeframe: str,
        end_time_ms: int | None,
        limit: int = 100,
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
        rows = [
            raw_row(value, confirm=self.confirm_by_open.get(value, "1"))
            for value in selected
        ]
        return payload(rows)


class HistoricalSequenceTests(unittest.TestCase):
    def test_backward_pagination_yields_exact_ascending_sequence(self) -> None:
        opens = [BASE + timedelta(minutes=i) for i in range(4)]
        source = FakePagedOkxSource(opens)

        candles = load_okx_historical_candles(
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
        candles = normalize_okx_history_page(
            payload([raw_row(BASE), raw_row(BASE + timedelta(minutes=2))]),
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

    def test_unconfirmed_provider_candle_cannot_enter_closed_range(self) -> None:
        source = FakePagedOkxSource([BASE], confirm_by_open={BASE: "0"})
        with self.assertRaises(UnclosedCandleError):
            load_okx_historical_candles(
                source,
                symbol="BTC_USDT_PERP",
                timeframe="1m",
                start=BASE,
                end=BASE + timedelta(minutes=1),
                page_limit=1,
            )

    def test_loader_reports_missing_when_provider_range_is_incomplete(self) -> None:
        source = FakePagedOkxSource([BASE, BASE + timedelta(minutes=2)])
        with self.assertRaises(MissingCandleError):
            load_okx_historical_candles(
                source,
                symbol="BTC_USDT_PERP",
                timeframe="1m",
                start=BASE,
                end=BASE + timedelta(minutes=3),
                page_limit=2,
            )


if __name__ == "__main__":
    unittest.main()
