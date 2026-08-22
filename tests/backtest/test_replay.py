from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from src.backtest.costs import FeeModel, FixedFundingModel, SlippageModel
from src.backtest.replay import (
    DatasetDescriptor,
    E2RuntimeBinding,
    HistoricalReplayEngine,
    ReplayConfig,
    ReplayValidationError,
    RuntimeContractError,
)

UTC = timezone.utc
BASE = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def z(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def candle(index: int, *, open_: str, high: str, low: str, close: str, closed: bool = True):
    open_time = BASE + timedelta(minutes=15 * index)
    close_time = open_time + timedelta(minutes=15)
    return {
        "schema_version": "contracts-v0.1",
        "symbol": "BTC_USDT_PERP",
        "timeframe": "15m",
        "open_time": z(open_time),
        "close_time": z(close_time),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": "10",
        "is_closed": closed,
        "source": "fixture",
    }


def strategy_definition():
    return {
        "schema_version": "contracts-v0.1",
        "strategy_id": "baseline-test",
        "strategy_version": "1.0.0",
        "name": "Baseline Test",
        "symbol": "BTC_USDT_PERP",
        "required_timeframes": ["15m"],
        "parameters": {},
        "rules": {},
        "runtime_compatibility": "e2-test",
        "content_hash": "sha256:baseline-test",
        "created_at": "2026-01-01T00:00:00Z",
    }


def dataset_for(candles):
    return DatasetDescriptor(
        dataset_id="fixture-btc-15m-v1",
        dataset_hash="sha256:fixture-btc-15m-v1",
        dataset_start=candles[0]["open_time"],
        dataset_end=candles[-1]["close_time"],
    )


def zero_config(**overrides):
    values = {
        "fixed_quantity": Decimal("1"),
        "cost_model_version": "cost-zero-v1",
        "fee_model": FeeModel(
            version="fee-zero-v1",
            maker_bps=Decimal("0"),
            taker_bps=Decimal("0"),
        ),
        "slippage_model": SlippageModel(
            version="slippage-zero-v1",
            entry_bps=Decimal("0"),
            exit_bps=Decimal("0"),
        ),
        "funding_model": FixedFundingModel(
            version="funding-zero-v1",
            rate_per_event=Decimal("0"),
            interval_seconds=8 * 60 * 60,
            first_event_at=datetime(1970, 1, 1, tzinfo=UTC),
        ),
        "run_created_at": datetime(2026, 1, 2, tzinfo=UTC),
    }
    values.update(overrides)
    return ReplayConfig(**values)


class RecordingRuntime:
    def __init__(
        self,
        directions,
        levels=None,
        timestamp_offset_seconds=0,
        signal_schema_version="contracts-v0.1",
    ):
        self.directions = list(directions)
        self.levels = levels or {}
        self.timestamp_offset_seconds = timestamp_offset_seconds
        self.signal_schema_version = signal_schema_version
        self.history_lengths = []
        self.boundaries = []

    def evaluate(self, definition, history, evaluated_at):
        self.history_lengths.append(len(history))
        self.boundaries.append(evaluated_at)
        for item in history:
            candle_close = datetime.fromisoformat(item["close_time"].replace("Z", "+00:00"))
            if candle_close > evaluated_at:
                raise AssertionError("future candle leaked into E2 runtime history")
        index = len(self.history_lengths) - 1
        direction = self.directions[index]
        level = self.levels.get(index, {})
        signal_time = evaluated_at + timedelta(seconds=self.timestamp_offset_seconds)
        return {
            "schema_version": self.signal_schema_version,
            "signal_id": f"signal-{index}",
            "strategy_id": definition["strategy_id"],
            "strategy_version": definition["strategy_version"],
            "strategy_content_hash": definition["content_hash"],
            "symbol": definition["symbol"],
            "evaluated_at": z(signal_time),
            "direction": direction,
            "reason_codes": ["TEST_DOUBLE_ONLY"],
            "market_boundary_ref": f"fixture:{z(evaluated_at)}",
            **level,
        }


def runtime_binding(runtime):
    return E2RuntimeBinding(
        runtime=runtime,
        runtime_version="e2-runtime-test-double-v1",
        invoke=lambda e2, definition, history, evaluated_at: e2.evaluate(
            definition, history, evaluated_at
        ),
    )


class ReplayTests(unittest.TestCase):
    def test_replay_calls_runtime_with_closed_prefix_and_uses_next_open_fills(self) -> None:
        candles = [
            candle(0, open_="100", high="101", low="99", close="100"),
            candle(1, open_="101", high="103", low="100", close="102"),
            candle(2, open_="104", high="105", low="103", close="104"),
            candle(3, open_="103", high="104", low="102", close="103"),
        ]
        runtime = RecordingRuntime(["LONG", "NO_TRADE", "SHORT", "NO_TRADE"])
        result = HistoricalReplayEngine(runtime_binding(runtime), zero_config()).run(
            strategy_definition(), candles, dataset_for(candles)
        )

        self.assertEqual(runtime.history_lengths, [1, 2, 3, 4])
        self.assertEqual(result.metrics.total_trades, 1)
        trade = result.trades[0]
        self.assertEqual(trade.opened_at, BASE + timedelta(minutes=15))
        self.assertEqual(trade.closed_at, BASE + timedelta(minutes=45))
        self.assertEqual(trade.entry_fill_price, Decimal("101"))
        self.assertEqual(trade.exit_fill_price, Decimal("103"))
        self.assertEqual(trade.net_pnl, Decimal("2"))
        self.assertEqual(trade.exit_reason, "OPPOSITE_SIGNAL")

        contract = result.to_contract()
        self.assertEqual(contract["schema_version"], "contracts-v0.1")
        self.assertEqual(contract["strategy_id"], "baseline-test")
        self.assertEqual(contract["runtime_version"], "e2-runtime-test-double-v1")
        self.assertEqual(contract["dataset_hash"], "sha256:fixture-btc-15m-v1")
        self.assertEqual(contract["validation_stages"]["monte_carlo"], "NOT_RUN")

    def test_last_bar_signal_does_not_enter_without_a_future_fill_bar(self) -> None:
        candles = [
            candle(0, open_="100", high="101", low="99", close="100"),
            candle(1, open_="101", high="102", low="100", close="101"),
        ]
        runtime = RecordingRuntime(["NO_TRADE", "LONG"])
        result = HistoricalReplayEngine(runtime_binding(runtime), zero_config()).run(
            strategy_definition(), candles, dataset_for(candles)
        )
        self.assertEqual(result.metrics.total_trades, 0)

    def test_unclosed_candle_is_rejected_before_runtime_evaluation(self) -> None:
        candles = [
            candle(0, open_="100", high="101", low="99", close="100"),
            candle(1, open_="101", high="102", low="100", close="101", closed=False),
        ]
        runtime = RecordingRuntime(["NO_TRADE", "NO_TRADE"])
        with self.assertRaises(ReplayValidationError):
            HistoricalReplayEngine(runtime_binding(runtime), zero_config()).run(
                strategy_definition(), candles, dataset_for(candles)
            )
        self.assertEqual(runtime.history_lengths, [])

    def test_incompatible_strategy_schema_is_rejected_before_runtime(self) -> None:
        candles = [candle(0, open_="100", high="101", low="99", close="100")]
        definition = strategy_definition()
        definition["schema_version"] = "contracts-v9"
        runtime = RecordingRuntime(["NO_TRADE"])
        with self.assertRaises(ReplayValidationError):
            HistoricalReplayEngine(runtime_binding(runtime), zero_config()).run(
                definition, candles, dataset_for(candles)
            )
        self.assertEqual(runtime.history_lengths, [])

    def test_incompatible_candle_schema_is_rejected_before_runtime(self) -> None:
        candles = [candle(0, open_="100", high="101", low="99", close="100")]
        candles[0]["schema_version"] = "contracts-v9"
        runtime = RecordingRuntime(["NO_TRADE"])
        with self.assertRaises(ReplayValidationError):
            HistoricalReplayEngine(runtime_binding(runtime), zero_config()).run(
                strategy_definition(), candles, dataset_for(candles)
            )
        self.assertEqual(runtime.history_lengths, [])

    def test_signal_evaluated_at_must_equal_replay_boundary(self) -> None:
        candles = [candle(0, open_="100", high="101", low="99", close="100")]
        runtime = RecordingRuntime(["NO_TRADE"], timestamp_offset_seconds=1)
        with self.assertRaises(RuntimeContractError):
            HistoricalReplayEngine(runtime_binding(runtime), zero_config()).run(
                strategy_definition(), candles, dataset_for(candles)
            )

    def test_incompatible_signal_schema_is_runtime_contract_error(self) -> None:
        candles = [candle(0, open_="100", high="101", low="99", close="100")]
        runtime = RecordingRuntime(["NO_TRADE"], signal_schema_version="contracts-v9")
        with self.assertRaises(RuntimeContractError):
            HistoricalReplayEngine(runtime_binding(runtime), zero_config()).run(
                strategy_definition(), candles, dataset_for(candles)
            )

    def test_same_candle_stop_target_ambiguity_resolves_to_stop(self) -> None:
        candles = [
            candle(0, open_="100", high="101", low="99", close="100"),
            candle(1, open_="100", high="106", low="94", close="100"),
        ]
        runtime = RecordingRuntime(
            ["LONG", "NO_TRADE"],
            levels={
                0: {
                    "strategy_stop_level": "95",
                    "strategy_target_level": "105",
                }
            },
        )
        result = HistoricalReplayEngine(runtime_binding(runtime), zero_config()).run(
            strategy_definition(), candles, dataset_for(candles)
        )
        self.assertEqual(result.metrics.total_trades, 1)
        self.assertEqual(result.trades[0].exit_reason, "STOP_LOSS")
        self.assertEqual(result.trades[0].exit_reference_price, Decimal("95"))
        self.assertEqual(result.trades[0].net_pnl, Decimal("-5"))

    def test_fee_slippage_and_funding_are_reflected_in_net_result(self) -> None:
        candles = [
            candle(0, open_="100", high="101", low="99", close="100"),
            candle(1, open_="100", high="102", low="99", close="101"),
            candle(2, open_="101", high="103", low="100", close="102"),
        ]
        runtime = RecordingRuntime(["LONG", "NO_TRADE", "NO_TRADE"])
        config = zero_config(
            cost_model_version="cost-stress-v1",
            fee_model=FeeModel(
                version="fee-10bps-v1",
                maker_bps=Decimal("10"),
                taker_bps=Decimal("10"),
            ),
            slippage_model=SlippageModel(
                version="slippage-10bps-v1",
                entry_bps=Decimal("10"),
                exit_bps=Decimal("10"),
            ),
            funding_model=FixedFundingModel(
                version="funding-fixed-v1",
                rate_per_event=Decimal("0.0001"),
                interval_seconds=8 * 60 * 60,
                first_event_at=BASE + timedelta(minutes=30),
            ),
        )
        result = HistoricalReplayEngine(runtime_binding(runtime), config).run(
            strategy_definition(), candles, dataset_for(candles)
        )
        self.assertEqual(result.metrics.total_trades, 1)
        self.assertGreater(result.metrics.total_fees, Decimal("0"))
        self.assertGreater(result.metrics.total_slippage_cost, Decimal("0"))
        self.assertGreater(result.metrics.total_funding_cost, Decimal("0"))
        self.assertLess(result.metrics.net_pnl, result.metrics.gross_pnl)

    def test_dataset_descriptor_must_match_consumed_boundaries(self) -> None:
        candles = [candle(0, open_="100", high="101", low="99", close="100")]
        bad_dataset = DatasetDescriptor(
            dataset_id="fixture",
            dataset_hash="sha256:fixture",
            dataset_start=z(BASE - timedelta(minutes=15)),
            dataset_end=candles[-1]["close_time"],
        )
        runtime = RecordingRuntime(["NO_TRADE"])
        with self.assertRaises(ReplayValidationError):
            HistoricalReplayEngine(runtime_binding(runtime), zero_config()).run(
                strategy_definition(), candles, bad_dataset
            )


if __name__ == "__main__":
    unittest.main()
