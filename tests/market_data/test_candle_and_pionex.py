from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from market_data import (  # noqa: E402
    Candle,
    DuplicateCandleError,
    MalformedCandleError,
    OutOfOrderCandleError,
    PionexPublicKlineSource,
    normalize_pionex_kline_page,
)
from market_data.candle import CONTRACT_SCHEMA_VERSION  # noqa: E402
from market_data.timeframes import pionex_interval  # noqa: E402

UTC = timezone.utc
BASE = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def raw_kline(open_time: datetime, **overrides: str) -> dict[str, object]:
    row: dict[str, object] = {
        "time": ms(open_time),
        "open": "100.10",
        "high": "101.20",
        "low": "99.90",
        "close": "100.80",
        "volume": "12.345",
    }
    row.update(overrides)
    return row


def payload(rows: list[dict[str, object]], response_time: datetime) -> dict[str, object]:
    return {
        "result": True,
        "timestamp": ms(response_time),
        "data": {"klines": rows},
    }


class CandleContractTests(unittest.TestCase):
    def test_decimal_and_rfc3339_interchange(self) -> None:
        candle = Candle(
            schema_version=CONTRACT_SCHEMA_VERSION,
            symbol="BTC_USDT_PERP",
            timeframe="1m",
            open_time=BASE,
            close_time=BASE + timedelta(minutes=1),
            open=Decimal("100.10"),
            high=Decimal("101.20"),
            low=Decimal("99.90"),
            close=Decimal("100.80"),
            volume=Decimal("12.345"),
            is_closed=True,
            source="TEST",
        )

        serialized = candle.to_interchange_dict()
        self.assertEqual(serialized["schema_version"], "contracts-v0.1")
        self.assertEqual(serialized["open"], "100.10")
        self.assertEqual(serialized["volume"], "12.345")
        self.assertEqual(serialized["open_time"], "2026-01-01T00:00:00.000Z")
        self.assertEqual(serialized["close_time"], "2026-01-01T00:01:00.000Z")

    def test_binary_float_is_rejected(self) -> None:
        with self.assertRaises(MalformedCandleError):
            Candle(
                schema_version=CONTRACT_SCHEMA_VERSION,
                symbol="BTC_USDT_PERP",
                timeframe="1m",
                open_time=BASE,
                close_time=BASE + timedelta(minutes=1),
                open=100.1,  # type: ignore[arg-type]
                high=Decimal("101.2"),
                low=Decimal("99.9"),
                close=Decimal("100.8"),
                volume=Decimal("1"),
                is_closed=True,
                source="TEST",
            )


class PionexNormalizationTests(unittest.TestCase):
    def test_supported_timeframe_mapping_is_explicit(self) -> None:
        self.assertEqual(pionex_interval("1m"), "1M")
        self.assertEqual(pionex_interval("15m"), "15M")
        self.assertEqual(pionex_interval("1h"), "60M")
        self.assertEqual(pionex_interval("4h"), "4H")

    def test_url_uses_futures_symbol_and_provider_interval(self) -> None:
        source = PionexPublicKlineSource()
        url = source.build_klines_url(
            symbol="BTC_USDT_PERP",
            timeframe="1h",
            end_time_ms=123456789,
            limit=500,
        )
        self.assertIn("symbol=BTC_USDT_PERP", url)
        self.assertIn("interval=60M", url)
        self.assertIn("endTime=123456789", url)
        self.assertIn("limit=500", url)

    def test_descending_provider_page_becomes_ascending_canonical_sequence(self) -> None:
        rows = [raw_kline(BASE + timedelta(minutes=1)), raw_kline(BASE)]
        candles = normalize_pionex_kline_page(
            payload(rows, BASE + timedelta(minutes=3)),
            symbol="BTC_USDT_PERP",
            timeframe="1m",
        )
        self.assertEqual([c.open_time for c in candles], [BASE, BASE + timedelta(minutes=1)])
        self.assertTrue(all(c.is_closed for c in candles))
        self.assertTrue(all(isinstance(c.open, Decimal) for c in candles))

    def test_current_provisional_candle_is_not_marked_closed(self) -> None:
        candles = normalize_pionex_kline_page(
            payload([raw_kline(BASE)], BASE + timedelta(seconds=30)),
            symbol="BTC_USDT_PERP",
            timeframe="1m",
        )
        self.assertFalse(candles[0].is_closed)

    def test_duplicate_provider_identity_is_rejected(self) -> None:
        with self.assertRaises(DuplicateCandleError):
            normalize_pionex_kline_page(
                payload([raw_kline(BASE), raw_kline(BASE)], BASE + timedelta(minutes=2)),
                symbol="BTC_USDT_PERP",
                timeframe="1m",
            )

    def test_mixed_provider_order_is_rejected(self) -> None:
        rows = [
            raw_kline(BASE),
            raw_kline(BASE + timedelta(minutes=2)),
            raw_kline(BASE + timedelta(minutes=1)),
        ]
        with self.assertRaises(OutOfOrderCandleError):
            normalize_pionex_kline_page(
                payload(rows, BASE + timedelta(minutes=4)),
                symbol="BTC_USDT_PERP",
                timeframe="1m",
            )

    def test_malformed_ohlc_is_rejected(self) -> None:
        with self.assertRaises(MalformedCandleError):
            normalize_pionex_kline_page(
                payload(
                    [raw_kline(BASE, open="105", high="101", low="99", close="100")],
                    BASE + timedelta(minutes=2),
                ),
                symbol="BTC_USDT_PERP",
                timeframe="1m",
            )


if __name__ == "__main__":
    unittest.main()
