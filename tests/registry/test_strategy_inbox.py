from __future__ import annotations

import unittest

from registry import (
    CompatibilityEvidence,
    EvidenceGateError,
    IdentityConflict,
    IntakeRejected,
    StrategyIdentity,
    StrategyPlatformService,
)
from storage import SQLiteRegistryStore, apply_migrations, connect


def strategy_payload(*, content_hash: str = "sha256:fixture", schema: str = "contracts-v0.1") -> dict:
    return {
        "schema_version": schema,
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
        "content_hash": content_hash,
        "created_at": "2026-08-20T00:00:00Z",
    }


class FakeE2CompatibilityBoundary:
    """Synthetic gate fixture only; this is not evidence that E2 passed locally."""

    def __init__(self, *, status: str, verification_kind: str) -> None:
        self.status = status
        self.verification_kind = verification_kind

    def check(self, definition: dict) -> CompatibilityEvidence:
        local_pass = self.status == "PASS" and self.verification_kind == "LOCAL_EXECUTION"
        return CompatibilityEvidence(
            compatibility_id=f"compat-{self.status}-{self.verification_kind}",
            identity=StrategyIdentity(definition["strategy_id"], definition["strategy_version"]),
            status=self.status,
            verification_kind=self.verification_kind,
            checker="E2_TEST_FIXTURE",
            checked_at="2026-08-20T00:01:00Z",
            reason_codes=("SYNTHETIC_TEST_EVIDENCE",),
            details={"fixture": True},
            source_revision="e2-test-revision" if local_pass else None,
            environment="local-test-fixture" if local_pass else None,
            command="synthetic-e2-compat-check" if local_pass else None,
            result_ref="synthetic-pass" if local_pass else None,
        )


class StrategyInboxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = connect(":memory:")
        apply_migrations(self.connection)
        self.store = SQLiteRegistryStore(self.connection)

    def tearDown(self) -> None:
        self.connection.close()

    def test_default_boundary_registers_draft_but_never_implies_e2_pass(self) -> None:
        service = StrategyPlatformService(self.store)
        outcome = service.intake(strategy_payload(), source_actor="unit-test")

        self.assertEqual("DRAFT", outcome.strategy.current_lifecycle_state)
        self.assertEqual("NOT_RUN", outcome.compatibility.status)
        self.assertEqual("COMPATIBILITY_NOT_RUN", outcome.receipt.result_status)
        with self.assertRaises(EvidenceGateError):
            service.begin_backtesting(outcome.strategy.identity, actor="unit-test")

    def test_draft_to_backtesting_requires_explicit_local_e2_pass_metadata(self) -> None:
        boundary = FakeE2CompatibilityBoundary(status="PASS", verification_kind="LOCAL_EXECUTION")
        service = StrategyPlatformService(self.store, boundary)
        outcome = service.intake(strategy_payload(), source_actor="unit-test")

        updated = service.begin_backtesting(outcome.strategy.identity, actor="unit-test")
        self.assertEqual("BACKTESTING", updated.current_lifecycle_state)
        self.assertEqual(1, updated.registry_revision)

    def test_static_or_declared_pass_is_not_enough_for_backtesting(self) -> None:
        boundary = FakeE2CompatibilityBoundary(status="PASS", verification_kind="STATIC_REVIEW")
        service = StrategyPlatformService(self.store, boundary)
        outcome = service.intake(strategy_payload(), source_actor="unit-test")

        with self.assertRaises(EvidenceGateError):
            service.begin_backtesting(outcome.strategy.identity, actor="unit-test")

    def test_same_identity_same_content_is_registry_idempotent(self) -> None:
        service = StrategyPlatformService(self.store)
        first = service.intake(strategy_payload(), source_actor="unit-test")
        second = service.intake(strategy_payload(), source_actor="unit-test")

        self.assertEqual(first.strategy.identity, second.strategy.identity)
        self.assertEqual("COMPATIBILITY_NOT_RUN", second.receipt.result_status)
        self.assertEqual(1, len(self.store.list_versions("baseline-sma-cross")))

    def test_same_identity_different_content_hash_fails_closed(self) -> None:
        service = StrategyPlatformService(self.store)
        service.intake(strategy_payload(), source_actor="unit-test")

        with self.assertRaises(IdentityConflict):
            service.intake(
                strategy_payload(content_hash="sha256:different"),
                source_actor="unit-test",
            )

    def test_unsupported_shared_schema_is_rejected_before_registry_write(self) -> None:
        service = StrategyPlatformService(self.store)
        with self.assertRaises(IntakeRejected):
            service.intake(strategy_payload(schema="0.1"), source_actor="unit-test")

        count = self.connection.execute("SELECT COUNT(*) FROM strategy_versions").fetchone()[0]
        self.assertEqual(0, count)

    def test_secret_like_prefixed_fields_are_rejected_and_not_persisted(self) -> None:
        payload = strategy_payload()
        payload["parameters"]["pionex_api_secret"] = "must-never-be-stored"
        service = StrategyPlatformService(self.store)

        with self.assertRaises(IntakeRejected):
            service.intake(payload, source_actor="unit-test")

        count = self.connection.execute("SELECT COUNT(*) FROM strategy_versions").fetchone()[0]
        self.assertEqual(0, count)


if __name__ == "__main__":
    unittest.main()
