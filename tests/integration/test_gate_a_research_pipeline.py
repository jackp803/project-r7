"""Gate A cross-role research pipeline definition.

This E7-owned test is for Product Owner-approved local execution only. It uses the
real supported E1/E2/E3/E6 interfaces, but all market data and any LOCAL_EXECUTION
compatibility metadata in this file are synthetic test fixtures. Nothing in this
module is project PASS evidence and this test must never be run by GitHub CI.
"""

from __future__ import annotations

import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Mapping

from backtest import (
    DatasetDescriptor,
    FeeModel,
    FixedFundingModel,
    HistoricalReplayEngine,
    ReplayConfig,
    SlippageModel,
    project_e2_runtime_binding,
)
from market_data import CONTRACT_SCHEMA_VERSION, Candle
from registry import CompatibilityEvidence, EvidenceGateError, StrategyIdentity
from registry.contract_validation import (
    validate_backtest_result_contract,
    validate_validation_decision_contract,
)
from storage import open_sqlite_platform
from strategy import (
    RUNTIME_FAMILY,
    RUNTIME_VERSION,
    compute_content_hash,
    parse_strategy_definition,
)
from validation import (
    EXECUTION_EXECUTED,
    OOSValidationContext,
    ValidationPolicy,
    ValidationSubject,
    evaluate_oos_validation,
)

UTC = timezone.utc
BASE = datetime(2026, 8, 20, 0, 0, tzinfo=UTC)


class TestOnlyLocalE2CompatibilityBoundary:
    """Synthetic fixture that still delegates compatibility semantics to real E2.

    The PASS/LOCAL_EXECUTION metadata below exists only so E6's test database can
    represent DRAFT -> BACKTESTING. It is deliberately labelled TEST_ONLY and must
    never be copied into Gate A evidence or a real Registry.
    """

    def check(self, strategy_definition: Mapping[str, Any]) -> CompatibilityEvidence:
        parsed = parse_strategy_definition(strategy_definition)
        return CompatibilityEvidence(
            compatibility_id="test-only-gate-a-e2-compatibility",
            identity=StrategyIdentity(parsed.strategy_id, parsed.strategy_version),
            status="PASS",
            verification_kind="LOCAL_EXECUTION",
            checker="E2_GATE_A_TEST_ONLY_BOUNDARY",
            checked_at="2026-08-20T00:00:00Z",
            reason_codes=("TEST_ONLY_SYNTHETIC_LOCAL_PASS",),
            details={
                "fixture": "TEST_ONLY_NOT_PROJECT_EVIDENCE",
                "runtime_version": parsed.runtime_version,
            },
            source_revision="TEST_ONLY_NOT_PROJECT_EVIDENCE",
            environment="TEST_ONLY_LOCAL_FIXTURE",
            command="TEST_ONLY_FIXTURE_NOT_AN_EXECUTED_GATE_A_COMMAND",
            result_ref="TEST_ONLY_RESULT_REF",
        )


def _sma(parameter: str) -> dict[str, Any]:
    return {
        "primitive": "SMA",
        "field": "close",
        "window": {"parameter": parameter},
    }


def strategy_definition() -> dict[str, Any]:
    definition: dict[str, Any] = {
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "strategy_id": "gate-a-synthetic-sma-cross",
        "strategy_version": "1.0.0",
        "name": "Gate A Synthetic SMA Cross",
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


def candle(hour: int, open_: str, high: str, low: str, close: str) -> Candle:
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
        source="gate-a-test-only-e1-candle",
    )


def candles() -> list[Candle]:
    return [
        candle(0, "10", "11", "9", "10"),
        candle(1, "10", "12", "9", "11"),
        candle(2, "11", "13", "10", "12"),
        candle(3, "12", "13", "10", "11"),
        candle(4, "11", "12", "9", "10"),
        candle(5, "10", "11", "8", "9"),
    ]


def dataset(items: list[Candle]) -> DatasetDescriptor:
    canonical = json.dumps(
        [item.to_interchange_dict() for item in items],
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return DatasetDescriptor(
        dataset_id="gate-a-test-only-oos-dataset",
        dataset_hash=f"sha256:{digest}",
        dataset_start=items[0].open_time,
        dataset_end=items[-1].close_time,
    )


def replay_config() -> ReplayConfig:
    return ReplayConfig(
        fixed_quantity=Decimal("1"),
        cost_model_version="gate-a-test-only-zero-cost-v1",
        fee_model=FeeModel(
            version="gate-a-test-only-fee-v1",
            maker_bps=Decimal("0"),
            taker_bps=Decimal("0"),
        ),
        slippage_model=SlippageModel(
            version="gate-a-test-only-slippage-v1",
            entry_bps=Decimal("0"),
            exit_bps=Decimal("0"),
        ),
        funding_model=FixedFundingModel(
            version="gate-a-test-only-funding-v1",
            rate_per_event=Decimal("0"),
            interval_seconds=8 * 60 * 60,
            first_event_at=datetime(1970, 1, 1, tzinfo=UTC),
        ),
        run_created_at=datetime(2026, 8, 20, 12, 0, tzinfo=UTC),
    )


class GateAResearchPipelineTests(unittest.TestCase):
    def test_real_cross_role_pipeline_is_canonical_but_synthetic_pass_has_no_authority(self) -> None:
        definition = strategy_definition()
        items = candles()
        data = dataset(items)

        # E1 canonical Candle -> real E2 parser/runtime through the E3 replay binding.
        backtest = HistoricalReplayEngine(
            project_e2_runtime_binding(), replay_config()
        ).run(definition, items, data)
        backtest_contract = backtest.to_contract()
        backtest_view = validate_backtest_result_contract(backtest_contract)
        self.assertEqual(backtest_view.strategy_id, definition["strategy_id"])
        self.assertEqual(backtest_view.strategy_version, definition["strategy_version"])
        self.assertEqual(backtest_view.strategy_content_hash, definition["content_hash"])
        self.assertEqual(backtest.runtime_version, RUNTIME_VERSION)

        # E3 explicit OOS stage consumes the canonical BacktestResult. The permissive
        # policy creates a synthetic PASS fixture only; it is not durable execution evidence.
        policy = ValidationPolicy(
            version="gate-a-test-only-oos-policy-v1",
            min_total_trades=1,
            min_net_pnl=Decimal("-100"),
            max_drawdown=Decimal("100"),
            max_consecutive_losses=10,
            min_profit_factor=None,
        )
        context = OOSValidationContext(
            split_id="gate-a-test-only-split",
            oos_dataset_id=data.dataset_id,
            oos_dataset_hash=data.dataset_hash,
            oos_dataset_start=data.dataset_start,
            oos_dataset_end=data.dataset_end,
            training_dataset_id="gate-a-test-only-training-dataset",
            training_dataset_hash="sha256:gate-a-test-only-training-dataset",
            validation_policy_version=policy.version,
        )
        decision = evaluate_oos_validation(
            subject=ValidationSubject(
                strategy_id=definition["strategy_id"],
                strategy_version=definition["strategy_version"],
                backtest_result_id=backtest.backtest_result_id,
            ),
            backtest_result=backtest_contract,
            context=context,
            policy=policy,
            execution_state=EXECUTION_EXECUTED,
            decided_at="2026-08-20T12:30:00Z",
        )
        self.assertEqual(decision.decision, "PASS")
        decision_contract = decision.to_contract()
        decision_view = validate_validation_decision_contract(decision_contract)
        self.assertEqual(decision_view.backtest_result_id, backtest.backtest_result_id)

        # E6 supported factory/service ingests the exact strategy and canonical E3
        # objects. Durable E3 evidence is deliberately recorded as NOT_RUN here. The
        # E3 payload's PASS/EXECUTED fields must not become lifecycle authority.
        platform = open_sqlite_platform(
            ":memory:",
            compatibility_boundary=TestOnlyLocalE2CompatibilityBoundary(),
        )
        intake = platform.intake(definition, source_actor="gate-a-test-only")
        backtesting = platform.begin_backtesting(
            intake.strategy.identity,
            actor="gate-a-test-only",
        )
        self.assertEqual(backtesting.current_lifecycle_state, "BACKTESTING")

        backtest_evidence = platform.record_backtest_result(backtest_contract)
        decision_evidence = platform.record_validation_decision(
            decision_contract,
            backtest_evidence_id=backtest_evidence.evidence_id,
        )
        self.assertEqual(backtest_evidence.verification_status, "NOT_RUN")
        self.assertEqual(backtest_evidence.verification_kind, "NOT_RUN")
        self.assertEqual(decision_evidence.verification_status, "NOT_RUN")
        self.assertEqual(decision_evidence.verification_kind, "NOT_RUN")

        with self.assertRaises(EvidenceGateError):
            platform.mark_candidate(
                intake.strategy.identity,
                actor="gate-a-test-only",
                validation_evidence_id=decision_evidence.evidence_id,
            )


if __name__ == "__main__":
    unittest.main()
