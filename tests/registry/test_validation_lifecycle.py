from __future__ import annotations

import unittest

from registry import CompatibilityEvidence, EvidenceGateError, StrategyIdentity, StrategyPlatformService
from storage._sqlite_registry import (
    _apply_migrations as apply_migrations,
    _connect as connect,
    _internal_store_for_tests as SQLiteRegistryStore,
)


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


def backtest_payload(result_id: str = "bt-1") -> dict:
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
        "validation_stages": {
            "oos": "NOT_RUN",
            "walk_forward": "NOT_RUN",
            "monte_carlo": "NOT_RUN",
        },
    }


def validation_decision_payload(backtest_id: str, decision_id: str = "vd-1") -> dict:
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
            compatibility_id="compat-local-pass",
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


class ValidationLifecycleTests(unittest.TestCase):
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

    def test_legal_looking_backtest_result_with_not_run_evidence_cannot_promote(self) -> None:
        backtest = self.service.record_backtest_result(backtest_payload())
        decision = self.service.record_validation_decision(
            validation_decision_payload("bt-1"),
            backtest_evidence_id=backtest.evidence_id,
        )

        self.assertEqual("PASS", decision.decision)
        self.assertEqual("NOT_RUN", decision.verification_status)
        with self.assertRaises(EvidenceGateError):
            self.service.mark_candidate(
                self.identity,
                actor="unit-test",
                validation_evidence_id=decision.evidence_id,
            )
        self.assertEqual(
            "BACKTESTING",
            self.store.get_strategy(self.identity).current_lifecycle_state,
        )

    def test_candidate_requires_local_pass_for_backtest_and_validation_decision(self) -> None:
        evidence_kwargs = {
            "verification_status": "PASS",
            "verification_kind": "LOCAL_EXECUTION",
            "source_revision": "e3-synthetic-revision",
            "environment": "local-test-fixture",
            "command": "synthetic-e3-local-test",
            "result_ref": "synthetic-pass",
        }
        backtest = self.service.record_backtest_result(
            backtest_payload("bt-local-pass"),
            **evidence_kwargs,
        )
        decision = self.service.record_validation_decision(
            validation_decision_payload("bt-local-pass", "vd-local-pass"),
            backtest_evidence_id=backtest.evidence_id,
            **evidence_kwargs,
        )

        candidate = self.service.mark_candidate(
            self.identity,
            actor="unit-test",
            validation_evidence_id=decision.evidence_id,
        )
        self.assertEqual("CANDIDATE", candidate.current_lifecycle_state)
        self.assertEqual(2, candidate.registry_revision)

    def test_candidate_service_exposes_no_approval_or_live_path(self) -> None:
        self.assertFalse(hasattr(self.service, "approve"))
        self.assertFalse(hasattr(self.service, "go_live"))
        self.assertFalse(hasattr(self.service, "promote_to_live"))
        self.assertFalse(hasattr(self.service, "transition"))

    def test_rejected_strategy_is_retained_with_audit_state(self) -> None:
        rejected = self.service.reject_from_backtesting(
            self.identity,
            actor="unit-test",
            reason_codes=("VALIDATION_FAILED",),
        )
        self.assertEqual("REJECTED", rejected.current_lifecycle_state)

        persisted = self.store.get_strategy(self.identity)
        self.assertIsNotNone(persisted)
        self.assertEqual("REJECTED", persisted.current_lifecycle_state)

    def test_backtest_result_for_wrong_content_hash_is_rejected(self) -> None:
        payload = backtest_payload("bt-wrong-hash")
        payload["strategy_content_hash"] = "sha256:not-this-version"

        with self.assertRaises(EvidenceGateError):
            self.service.record_backtest_result(payload)


if __name__ == "__main__":
    unittest.main()
