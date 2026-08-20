from __future__ import annotations

import unittest

from registry import CompatibilityEvidence, EvidenceGateError, StrategyIdentity, StrategyPlatformService
from registry.contract_validation import (
    BACKTEST_CORE_METRIC_FIELDS,
    BACKTEST_IDENTITY_REPRODUCIBILITY_FIELDS,
    VALIDATION_DECISION_FIELDS,
)
from storage import SQLiteRegistryStore, apply_migrations, connect


def strategy_payload() -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "strategy_id": "baseline-sma-cross",
        "strategy_version": "1.0.0",
        "name": "Baseline SMA Cross",
        "symbol": "BTC_USDT_PERP",
        "required_timeframes": ["1h"],
        "parameters": {"fast": 2, "slow": 3},
        "rules": {"dsl_version": "0.1", "long": {}, "short": {}},
        "runtime_compatibility": {
            "runtime_family": "project-r7-e2-strategy-runtime",
            "runtime_version": "0.1.0",
        },
        "content_hash": "sha256:fixture",
        "created_at": "2026-08-20T00:00:00Z",
    }


def backtest_payload(result_id: str = "bt-contract") -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "backtest_result_id": result_id,
        "strategy_id": "baseline-sma-cross",
        "strategy_version": "1.0.0",
        "strategy_content_hash": "sha256:fixture",
        "runtime_version": "0.1.0",
        "dataset_id": "synthetic-dataset",
        "dataset_hash": "sha256:dataset",
        "dataset_start": "2026-08-20T00:00:00Z",
        "dataset_end": "2026-08-20T06:00:00Z",
        "cost_model_version": "test-cost-v1",
        "created_at": "2026-08-20T07:00:00Z",
        "total_trades": 1,
        "wins": 1,
        "losses": 0,
        "breakeven": 0,
        "gross_pnl": "1",
        "net_pnl": "1",
        "total_fees": "0",
        "profit_factor": None,
        "expectancy": "1",
        "max_drawdown": "0",
        "max_consecutive_losses": 0,
    }


def validation_decision_payload(backtest_id: str, decision_id: str = "vd-contract") -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "validation_decision_id": decision_id,
        "strategy_id": "baseline-sma-cross",
        "strategy_version": "1.0.0",
        "backtest_result_id": backtest_id,
        "validation_policy_version": "test-policy-v1",
        "decision": "PASS",
        "reason_codes": ["SYNTHETIC_TEST_PASS"],
        "decided_at": "2026-08-20T07:01:00Z",
    }


class LocalPassE2Boundary:
    def check(self, definition: dict) -> CompatibilityEvidence:
        return CompatibilityEvidence(
            compatibility_id="compat-contract-local-pass",
            identity=StrategyIdentity(definition["strategy_id"], definition["strategy_version"]),
            status="PASS",
            verification_kind="LOCAL_EXECUTION",
            checker="E2_TEST_FIXTURE",
            checked_at="2026-08-20T00:01:00Z",
            reason_codes=("SYNTHETIC_TEST_EVIDENCE",),
            details={"fixture": True},
            source_revision="e2-synthetic-revision",
            environment="local-test-fixture",
            command="synthetic-e2-compat-check",
            result_ref="synthetic-pass",
        )


LOCAL_PASS_METADATA = {
    "verification_status": "PASS",
    "verification_kind": "LOCAL_EXECUTION",
    "source_revision": "e3-synthetic-revision",
    "environment": "local-test-fixture",
    "command": "synthetic-e3-local-test",
    "result_ref": "synthetic-pass",
}


class EvidenceContractValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = connect(":memory:")
        apply_migrations(self.connection)
        self.store = SQLiteRegistryStore(self.connection)
        self.service = StrategyPlatformService(self.store, LocalPassE2Boundary())
        outcome = self.service.intake(strategy_payload(), source_actor="unit-test")
        self.identity = outcome.strategy.identity
        self.service.begin_backtesting(self.identity, actor="unit-test")

    def tearDown(self) -> None:
        self.connection.close()

    def evidence_count(self) -> int:
        return self.connection.execute("SELECT COUNT(*) FROM validation_evidence").fetchone()[0]

    def test_every_required_backtest_field_is_fail_closed_even_with_fake_local_pass(self) -> None:
        required = BACKTEST_IDENTITY_REPRODUCIBILITY_FIELDS + BACKTEST_CORE_METRIC_FIELDS
        for field in required:
            with self.subTest(field=field):
                payload = backtest_payload(f"bt-missing-{field}")
                del payload[field]
                before = self.evidence_count()
                with self.assertRaises(EvidenceGateError):
                    self.service.record_backtest_result(payload, **LOCAL_PASS_METADATA)
                self.assertEqual(before, self.evidence_count())

    def test_backtest_financial_metrics_require_decimal_interchange_shape(self) -> None:
        payload = backtest_payload("bt-float-pnl")
        payload["net_pnl"] = 1.0
        with self.assertRaises(EvidenceGateError):
            self.service.record_backtest_result(payload, **LOCAL_PASS_METADATA)
        self.assertEqual(0, self.evidence_count())

    def test_backtest_timestamps_must_be_rfc3339_utc(self) -> None:
        payload = backtest_payload("bt-nonutc")
        payload["created_at"] = "2026-08-20T15:00:00+08:00"
        with self.assertRaises(EvidenceGateError):
            self.service.record_backtest_result(payload, **LOCAL_PASS_METADATA)
        self.assertEqual(0, self.evidence_count())

    def test_every_required_validation_decision_field_is_fail_closed(self) -> None:
        backtest = self.service.record_backtest_result(
            backtest_payload("bt-parent"),
            **LOCAL_PASS_METADATA,
        )
        self.assertEqual(1, self.evidence_count())

        for index, field in enumerate(VALIDATION_DECISION_FIELDS):
            with self.subTest(field=field):
                payload = validation_decision_payload("bt-parent", f"vd-missing-{index}")
                del payload[field]
                with self.assertRaises(EvidenceGateError):
                    self.service.record_validation_decision(
                        payload,
                        backtest_evidence_id=backtest.evidence_id,
                        **LOCAL_PASS_METADATA,
                    )
                self.assertEqual(1, self.evidence_count())

    def test_validation_decision_rejects_noncanonical_enum_and_reason_codes_shape(self) -> None:
        backtest = self.service.record_backtest_result(
            backtest_payload("bt-enum-parent"),
            **LOCAL_PASS_METADATA,
        )

        invalid_decision = validation_decision_payload("bt-enum-parent", "vd-invalid-enum")
        invalid_decision["decision"] = "APPROVED"
        with self.assertRaises(EvidenceGateError):
            self.service.record_validation_decision(
                invalid_decision,
                backtest_evidence_id=backtest.evidence_id,
                **LOCAL_PASS_METADATA,
            )

        invalid_reasons = validation_decision_payload("bt-enum-parent", "vd-invalid-reasons")
        invalid_reasons["reason_codes"] = "NOT_A_SEQUENCE_OF_REASON_CODES"
        with self.assertRaises(EvidenceGateError):
            self.service.record_validation_decision(
                invalid_reasons,
                backtest_evidence_id=backtest.evidence_id,
                **LOCAL_PASS_METADATA,
            )
        self.assertEqual(1, self.evidence_count())

    def test_valid_backtest_shape_alone_cannot_promote_without_validation_decision(self) -> None:
        backtest = self.service.record_backtest_result(
            backtest_payload("bt-shape-only"),
            **LOCAL_PASS_METADATA,
        )
        with self.assertRaises(EvidenceGateError):
            self.service.mark_candidate(
                self.identity,
                actor="unit-test",
                validation_evidence_id=backtest.evidence_id,
            )
        self.assertEqual(
            "BACKTESTING",
            self.store.get_strategy(self.identity).current_lifecycle_state,
        )

    def test_lifecycle_public_surface_remains_capped_at_candidate(self) -> None:
        self.assertFalse(hasattr(self.service, "approve"))
        self.assertFalse(hasattr(self.service, "go_live"))
        self.assertFalse(hasattr(self.service, "promote_to_live"))
        self.assertFalse(hasattr(self.service, "transition"))


if __name__ == "__main__":
    unittest.main()
