from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import market_data  # noqa: E402
import market_data.candle as candle_module  # noqa: E402
import market_data.errors as errors_module  # noqa: E402
import market_data.timeframes as timeframes_module  # noqa: E402


class MarketDataImportIntegrityTests(unittest.TestCase):
    def test_public_surface_resolves_from_intended_modules(self) -> None:
        self.assertIs(market_data.Candle, candle_module.Candle)
        self.assertEqual(
            market_data.CONTRACT_SCHEMA_VERSION,
            candle_module.CONTRACT_SCHEMA_VERSION,
        )
        self.assertIs(market_data.SUPPORTED_TIMEFRAMES, timeframes_module.SUPPORTED_TIMEFRAMES)
        self.assertIs(market_data.okx_bar, timeframes_module.okx_bar)
        self.assertEqual(candle_module.Candle.__module__, "market_data.candle")
        self.assertEqual(timeframes_module.okx_bar.__module__, "market_data.timeframes")

    def test_expected_errors_resolve_from_errors_module(self) -> None:
        names = (
            "MarketDataError",
            "UnsupportedTimeframeError",
            "UnsupportedSymbolError",
            "MalformedCandleError",
            "DuplicateCandleError",
            "OutOfOrderCandleError",
            "MissingCandleError",
            "UnclosedCandleError",
            "RangeAlignmentError",
            "IncompleteHistoricalRangeError",
            "ProviderResponseError",
            "ProviderUnavailableError",
            "ProviderRateLimitError",
        )
        for name in names:
            with self.subTest(name=name):
                exported = getattr(market_data, name)
                defined = getattr(errors_module, name)
                self.assertIs(exported, defined)
                self.assertEqual(defined.__module__, "market_data.errors")

    def test_module_roles_are_not_permuted(self) -> None:
        self.assertTrue(hasattr(candle_module, "Candle"))
        self.assertTrue(hasattr(candle_module, "CONTRACT_SCHEMA_VERSION"))
        self.assertFalse(hasattr(candle_module, "MarketDataError"))

        self.assertTrue(hasattr(errors_module, "MarketDataError"))
        self.assertFalse(hasattr(errors_module, "timeframe_duration"))

        self.assertTrue(hasattr(timeframes_module, "timeframe_duration"))
        self.assertTrue(hasattr(timeframes_module, "SUPPORTED_TIMEFRAMES"))
        self.assertFalse(hasattr(timeframes_module, "Candle"))

    def test_existing_candle_and_timeframe_semantics_remain_represented(self) -> None:
        self.assertEqual(
            market_data.SUPPORTED_TIMEFRAMES,
            frozenset({"1m", "15m", "1h", "4h"}),
        )
        self.assertEqual(timeframes_module.okx_bar("1m"), "1m")
        self.assertEqual(timeframes_module.okx_bar("15m"), "15m")
        self.assertEqual(timeframes_module.okx_bar("1h"), "1H")
        self.assertEqual(timeframes_module.okx_bar("4h"), "4H")
        self.assertEqual(timeframes_module.timeframe_duration("1m"), timedelta(minutes=1))

        open_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
        candle = market_data.Candle(
            schema_version=market_data.CONTRACT_SCHEMA_VERSION,
            symbol="BTC_USDT_PERP",
            timeframe="1m",
            open_time=open_time,
            close_time=open_time + timedelta(minutes=1),
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


if __name__ == "__main__":
    unittest.main()
