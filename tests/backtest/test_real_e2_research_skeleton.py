"""Cross-role Slice 1 test definition using real E1 Candle and real E2 Runtime.

This test must run only in a local integration checkout where E1 + E2 + E3
revisions are present together. It must never be executed by GitHub Actions/CI.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
import unittest

from market_data import CONTRACT_SCHEMA_VERSION, Candle
from strategy import (
    RUNTIME_FAMILY,
    RUNTIME_VERSION,
    StrategyRuntime,
    compute_content_hash,
)
from src.backtest import (
    DatasetDescriptor,
    FeeModel,
    FixedFundingModel,
    HistoricalReplayEngine,
    ReplayConfig,
    SlippageModel,
    project_e2_runtime_binding,
)

UTC = timezone.utc
BASE = datetime(2026, 8, 20, 0, 0, tzinfo=UTC)


def _sma(parameter: str) -> dict:
    return {
        "primitive": "SMA",
        "field": "close",
        "window": {"parameter": parameter},
    }


def _strategy_definition() -> dict:
    definition = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
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
                "left": _sma("fast_window"),
                "right": _sma("slow_window"),
            },
            "short": {
                "operator": "LT",
                "left": _sma("fast_window"),
                "right": _sma("slow_window"),
            },
        },
        "runtime_compatibility": {
            "runtime_family": RUNTIME_FAMILY,
            "runtime_version": RUNTIME_VERSION,
        },
        "content_hash": "",
        "created_at": "2026-08-20T00:00:00Z",
    }
    definition["content_hash"] = compute_content_hash(definition)
    return definition


def _candle(hour: int, open_: str, high: str, low: str, close: str) -> Candle:
    opened = BASE + timedelta(hours=hour)
    return Candle(
        schema_version=CONTRACT_SCHEMA_VERSION,
        symbol="BTC_USDT_PERP",
        timeframe="1h",
        open_time=opened,
        close_time=opened + timedelta(hours=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("100"),
        is_closed=True,
        source="e1-e3-integration-fixture",
    )


def _candles() -> list[Candle]:
    return [
        _candle(0, "10", "11", "9", "10"),
        _candle(1, "10", "12", "9", "11"),
        _candle(2, "11", "13", "10", "12"),
        _candle(3, "12", "13", "10", "11"),
        _candle(4, "11", "12", "9", "10"),
        _candle(5, "10", "11", "8", "9"),
    ]


def _dataset(candles: list[Candle]) -> DatasetDescriptor:
    canonical = json.dumps(
        [item.to_interchange_dict() for item in candles],
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return DatasetDescriptor(
        dataset_id="e1-e2-e3-synthetic-btc-1h-v1",
        dataset_hash=f"sha256:{digest}",
        dataset_start=candles[0].open_time,
        dataset_end=candles[-1].close_time,
    )


def _config() -> ReplayConfig:
    return ReplayConfig(
        fixed_quantity=Decimal("1"),
        cost_model_version="integration-zero-cost-v1",
        fee_model=FeeModel(
            version="integration-fee-zero-v1",
            maker_bps=Decimal("0"),
            taker_bps=Decimal("0"),
        ),
        slippage_model=SlippageModel(
            version="integration-slippage-zero-v1",
            entry_bps=Decimal("0"),
            exit_bps=Decimal("0"),
        ),
        funding_model=FixedFundingModel(
            version="integration-funding-zero-v1",
            rate_per_event=Decimal("0"),
            interval_seconds=8 * 60 * 60,
            first_event_at=datetime(1970, 1, 1, tzinfo=UTC),
        ),
        run_created_at=datetime(2026, 8, 20, 12, 0, tzinfo=UTC),
    )


class RealE2ResearchSkeletonTests(unittest.TestCase):
    def test_e3_binding_invokes_actual_e2_runtime(self) -> None:
        definition = _strategy_definition()
        candles = _candles()
        binding = project_e2_runtime_binding()

        self.assertIsInstance(binding.runtime, StrategyRuntime)
        self.assertEqual(binding.runtime_version, RUNTIME_VERSION)

        signal = binding.evaluate(
            definition,
            tuple(candles[:3]),
            candles[2].close_time,
        )
        self.assertEqual(signal["schema_version"], CONTRACT_SCHEMA_VERSION)
        self.assertEqual(signal["direction"], "LONG")
        self.assertEqual(signal["strategy_content_hash"], definition["content_hash"])

    def test_e1_candle_to_e2_runtime_to_e3_replay_is_deterministic(self) -> None:
        definition = _strategy_definition()
        candles = _candles()
        dataset = _dataset(candles)
        config = _config()

        first = HistoricalReplayEngine(project_e2_runtime_binding(), config).run(
            definition, candles, dataset
        )
        second = HistoricalReplayEngine(project_e2_runtime_binding(), config).run(
            definition, candles, dataset
        )

        self.assertEqual(first.runtime_version, RUNTIME_VERSION)
        self.assertEqual(first.strategy_content_hash, definition["content_hash"])
        self.assertEqual(first.dataset_hash, dataset.dataset_hash)
        self.assertEqual(first.runtime_invocations, len(candles))
        self.assertEqual(first.backtest_result_id, second.backtest_result_id)
        self.assertEqual(first.metrics, second.metrics)
        self.assertEqual(first.metrics.total_trades, 1)
        self.assertEqual(first.trades[0].entry_fill_price, Decimal("12"))
        self.assertEqual(first.trades[0].exit_fill_price, Decimal("10"))
        self.assertEqual(first.trades[0].net_pnl, Decimal("-2"))


if __name__ == "__main__":
    unittest.main()
