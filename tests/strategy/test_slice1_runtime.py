import copy
import unittest

from strategy import (
    RUNTIME_FAMILY,
    RUNTIME_VERSION,
    StrategyError,
    StrategyRuntime,
    compute_content_hash,
    parse_strategy_definition,
    validate_strategy_definition,
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
        "created_at": "2026-08-20T03:00:00Z",
    }
    definition["content_hash"] = compute_content_hash(definition)
    return definition


def candle(hour, close, *, is_closed=True):
    close_value = str(close)
    numeric = int(close)
    return {
        "schema_version": "contracts-v0.1",
        "symbol": "BTC_USDT_PERP",
        "timeframe": "1h",
        "open_time": f"2026-08-20T{hour:02d}:00:00Z",
        "close_time": f"2026-08-20T{hour + 1:02d}:00:00Z",
        "open": close_value,
        "high": str(numeric + 1),
        "low": str(numeric - 1),
        "close": close_value,
        "volume": "100",
        "is_closed": is_closed,
        "source": "e1-test-fixture",
    }


class StrategyParserTests(unittest.TestCase):
    def test_valid_definition_is_accepted(self):
        result = validate_strategy_definition(make_definition())
        self.assertTrue(result["valid"])
        self.assertEqual(result["runtime_version"], RUNTIME_VERSION)

    def test_unsupported_strategy_schema_is_structured(self):
        definition = make_definition()
        definition["schema_version"] = "contracts-v9.9"
        definition["content_hash"] = compute_content_hash(definition)
        result = validate_strategy_definition(definition)
        self.assertFalse(result["valid"])
        self.assertEqual(result["error"]["code"], "UNSUPPORTED_SCHEMA_VERSION")
        self.assertEqual(result["error"]["details"]["object_type"], "StrategyDefinition")
        self.assertEqual(result["error"]["details"]["supported"], "contracts-v0.1")
        self.assertEqual(result["error"]["details"]["actual"], "contracts-v9.9")

    def test_content_hash_mismatch_is_rejected(self):
        definition = make_definition()
        definition["name"] = "mutated without version/hash update"
        result = validate_strategy_definition(definition)
        self.assertFalse(result["valid"])
        self.assertEqual(result["error"]["code"], "CONTENT_HASH_MISMATCH")

    def test_unsupported_primitive_is_structured(self):
        definition = make_definition()
        definition["rules"]["long"]["left"]["primitive"] = "RSI"
        definition["content_hash"] = compute_content_hash(definition)
        result = validate_strategy_definition(definition)
        self.assertFalse(result["valid"])
        self.assertEqual(result["error"]["code"], "UNSUPPORTED_PRIMITIVE")
        self.assertEqual(result["error"]["details"]["primitive"], "RSI")

    def test_runtime_version_mismatch_is_rejected(self):
        definition = make_definition()
        definition["runtime_compatibility"]["runtime_version"] = "9.9.9"
        definition["content_hash"] = compute_content_hash(definition)
        result = validate_strategy_definition(definition)
        self.assertFalse(result["valid"])
        self.assertEqual(result["error"]["code"], "RUNTIME_INCOMPATIBLE")


class StrategyRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.strategy = parse_strategy_definition(make_definition())
        self.runtime = StrategyRuntime()

    def test_same_definition_boundary_and_runtime_produce_identical_signal(self):
        candles = [candle(0, 10), candle(1, 11), candle(2, 12), candle(3, 13)]
        first = self.runtime.evaluate(self.strategy, candles, "2026-08-20T04:00:00Z")
        second = self.runtime.evaluate(self.strategy, copy.deepcopy(candles), "2026-08-20T04:00:00Z")
        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], "contracts-v0.1")
        self.assertEqual(first["direction"], "LONG")
        self.assertEqual(first["reason_codes"], ["LONG_RULE_MATCHED"])

    def test_unsupported_consumed_candle_schema_is_structured(self):
        candles = [candle(0, 10), candle(1, 11), candle(2, 12)]
        candles[0]["schema_version"] = "contracts-v9.9"
        with self.assertRaises(StrategyError) as raised:
            self.runtime.evaluate(self.strategy, candles, "2026-08-20T03:00:00Z")
        self.assertEqual(raised.exception.code, "UNSUPPORTED_CANDLE_SCHEMA_VERSION")
        self.assertEqual(raised.exception.details["supported"], "contracts-v0.1")
        self.assertEqual(raised.exception.details["actual"], "contracts-v9.9")

    def test_short_path(self):
        candles = [candle(0, 13), candle(1, 12), candle(2, 11), candle(3, 10)]
        signal = self.runtime.evaluate(self.strategy, candles, "2026-08-20T04:00:00Z")
        self.assertEqual(signal["direction"], "SHORT")
        self.assertEqual(signal["reason_codes"], ["SHORT_RULE_MATCHED"])

    def test_no_trade_path(self):
        candles = [candle(0, 10), candle(1, 10), candle(2, 10), candle(3, 10)]
        signal = self.runtime.evaluate(self.strategy, candles, "2026-08-20T04:00:00Z")
        self.assertEqual(signal["direction"], "NO_TRADE")
        self.assertEqual(signal["reason_codes"], ["NO_RULE_MATCHED"])

    def test_insufficient_history_is_no_trade(self):
        candles = [candle(0, 10), candle(1, 11)]
        signal = self.runtime.evaluate(self.strategy, candles, "2026-08-20T02:00:00Z")
        self.assertEqual(signal["direction"], "NO_TRADE")
        self.assertEqual(signal["reason_codes"], ["INSUFFICIENT_HISTORY"])

    def test_future_candle_cannot_change_signal(self):
        base = [candle(0, 10), candle(1, 11), candle(2, 12), candle(3, 13)]
        baseline = self.runtime.evaluate(self.strategy, base, "2026-08-20T04:00:00Z")
        future = candle(4, 1)
        with_future = self.runtime.evaluate(
            self.strategy, base + [future], "2026-08-20T04:00:00Z"
        )
        self.assertEqual(baseline, with_future)

    def test_unclosed_candle_cannot_change_signal(self):
        base = [candle(0, 10), candle(1, 11), candle(2, 12)]
        baseline = self.runtime.evaluate(self.strategy, base, "2026-08-20T04:00:00Z")
        provisional = candle(3, 1, is_closed=False)
        with_provisional = self.runtime.evaluate(
            self.strategy, base + [provisional], "2026-08-20T04:00:00Z"
        )
        self.assertEqual(baseline, with_provisional)


if __name__ == "__main__":
    unittest.main()
