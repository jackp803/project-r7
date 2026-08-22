import copy
import unittest

from strategy import (
    ENTRY_ORDER_TYPE_MARKET,
    ENTRY_PROFILE_VERSION,
    RUNTIME_FAMILY,
    RUNTIME_VERSION,
    StrategyRuntime,
    TradeIntentError,
    build_trade_intent,
    compute_content_hash,
    parse_strategy_definition,
)


def _sma_expr(parameter):
    return {
        "primitive": "SMA",
        "field": "close",
        "window": {"parameter": parameter},
    }


def make_definition():
    definition = {
        "schema_version": "contracts-v0.1",
        "strategy_id": "baseline-sma-cross",
        "strategy_version": "1.0.0",
        "name": "Baseline SMA Cross",
        "symbol": "BTC_USDT_PERP",
        "required_timeframes": ["1h"],
        "parameters": {"fast_window": 2, "slow_window": 3},
        "rules": {
            "dsl_version": "0.1",
            "long": {
                "operator": "GT",
                "left": _sma_expr("fast_window"),
                "right": _sma_expr("slow_window"),
            },
            "short": {
                "operator": "LT",
                "left": _sma_expr("fast_window"),
                "right": _sma_expr("slow_window"),
            },
        },
        "runtime_compatibility": {
            "runtime_family": RUNTIME_FAMILY,
            "runtime_version": RUNTIME_VERSION,
        },
        "content_hash": "",
        "created_at": "2026-08-21T02:00:00Z",
    }
    definition["content_hash"] = compute_content_hash(definition)
    return definition


def candle(hour, close):
    close_value = str(close)
    numeric = int(close)
    return {
        "schema_version": "contracts-v0.1",
        "symbol": "BTC_USDT_PERP",
        "timeframe": "1h",
        "open_time": f"2026-08-21T{hour:02d}:00:00Z",
        "close_time": f"2026-08-21T{hour + 1:02d}:00:00Z",
        "open": close_value,
        "high": str(numeric + 1),
        "low": str(numeric - 1),
        "close": close_value,
        "volume": "100",
        "is_closed": True,
        "source": "e2-trade-intent-test",
    }


def make_signal():
    runtime = StrategyRuntime()
    strategy = parse_strategy_definition(make_definition())
    candles = [candle(0, 10), candle(1, 11), candle(2, 12), candle(3, 13)]
    return runtime.evaluate(strategy, candles, "2026-08-21T04:00:00Z")


class TradeIntentEntryProfileTests(unittest.TestCase):
    def setUp(self):
        self.signal = make_signal()

    def test_canonical_entry_v01_market_serialization_is_deterministic(self):
        first = build_trade_intent(
            self.signal,
            entry_profile_version=ENTRY_PROFILE_VERSION,
            entry_order_type=ENTRY_ORDER_TYPE_MARKET,
        )
        second = build_trade_intent(
            copy.deepcopy(self.signal),
            entry_profile_version=ENTRY_PROFILE_VERSION,
            entry_order_type=ENTRY_ORDER_TYPE_MARKET,
        )

        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], "contracts-v0.1")
        self.assertEqual(first["entry_profile_version"], "entry-v0.1")
        self.assertEqual(first["entry_order_type"], "MARKET")
        self.assertEqual(first["direction"], "LONG")
        self.assertNotIn("quantity", first)
        self.assertNotIn("leverage", first)
        self.assertNotIn("margin_mode", first)

    def test_unsupported_entry_order_type_is_rejected(self):
        with self.assertRaises(TradeIntentError) as raised:
            build_trade_intent(
                self.signal,
                entry_profile_version=ENTRY_PROFILE_VERSION,
                entry_order_type="LIMIT",
            )
        self.assertEqual(raised.exception.code, "UNSUPPORTED_ENTRY_ORDER_TYPE")
        self.assertEqual(raised.exception.details["supported"], "MARKET")
        self.assertEqual(raised.exception.details["actual"], "LIMIT")

    def test_unknown_entry_profile_is_rejected(self):
        with self.assertRaises(TradeIntentError) as raised:
            build_trade_intent(
                self.signal,
                entry_profile_version="entry-v9.9",
                entry_order_type="MARKET",
            )
        self.assertEqual(raised.exception.code, "UNSUPPORTED_ENTRY_PROFILE_VERSION")

    def test_entry_v01_missing_order_type_is_rejected(self):
        with self.assertRaises(TradeIntentError) as raised:
            build_trade_intent(
                self.signal,
                entry_profile_version=ENTRY_PROFILE_VERSION,
            )
        self.assertEqual(raised.exception.code, "MISSING_ENTRY_ORDER_TYPE")

    def test_legacy_entry_style_does_not_become_executable(self):
        intent = build_trade_intent(
            self.signal,
            entry_style="MARKET",
        )
        self.assertEqual(intent["entry_style"], "MARKET")
        self.assertNotIn("entry_profile_version", intent)
        self.assertNotIn("entry_order_type", intent)

    def test_advisory_reference_price_remains_advisory(self):
        intent = build_trade_intent(
            self.signal,
            entry_profile_version=ENTRY_PROFILE_VERSION,
            entry_order_type=ENTRY_ORDER_TYPE_MARKET,
            entry_reference_price="42000.50",
            entry_style="context-only",
        )
        self.assertEqual(intent["entry_reference_price"], "42000.50")
        self.assertEqual(intent["entry_style"], "context-only")
        self.assertEqual(intent["entry_order_type"], "MARKET")
        self.assertNotIn("limit_price", intent)
        self.assertNotIn("stop_price", intent)
        self.assertNotIn("trigger_price", intent)

    def test_provider_specific_entry_semantics_are_rejected(self):
        with self.assertRaises(TradeIntentError) as raised:
            build_trade_intent(
                self.signal,
                entry_profile_version=ENTRY_PROFILE_VERSION,
                entry_order_type=ENTRY_ORDER_TYPE_MARKET,
                okx_order_type="market",
            )
        self.assertEqual(raised.exception.code, "PROVIDER_SPECIFIC_ENTRY_SEMANTICS")

    def test_risk_or_sizing_authority_is_rejected(self):
        with self.assertRaises(TradeIntentError) as raised:
            build_trade_intent(
                self.signal,
                entry_profile_version=ENTRY_PROFILE_VERSION,
                entry_order_type=ENTRY_ORDER_TYPE_MARKET,
                quantity="0.1",
            )
        self.assertEqual(raised.exception.code, "FORBIDDEN_TRADE_INTENT_AUTHORITY")

    def test_existing_strategy_runtime_determinism_is_unchanged(self):
        runtime = StrategyRuntime()
        strategy = parse_strategy_definition(make_definition())
        candles = [candle(0, 10), candle(1, 11), candle(2, 12), candle(3, 13)]

        first = runtime.evaluate(strategy, candles, "2026-08-21T04:00:00Z")
        second = runtime.evaluate(
            strategy,
            copy.deepcopy(candles),
            "2026-08-21T04:00:00Z",
        )

        self.assertEqual(first, second)
        self.assertEqual(first["direction"], "LONG")
        self.assertEqual(first["schema_version"], "contracts-v0.1")


if __name__ == "__main__":
    unittest.main()
