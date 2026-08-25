from __future__ import annotations

import sqlite3
import unittest
from dataclasses import replace

import storage
from registry import (
    CompatibilityEvidence,
    InvalidTransition,
    StrategyIdentity,
    StrategyPlatformService,
    StrategyVersionRecord,
    ValidationEvidenceRecord,
)
from storage import OperationalModeRecovery, OperationalModeStore, ShadowCheckpoint, open_sqlite_platform
from storage._sqlite_registry import (
    _SQLiteRegistryStore,
    _apply_migrations,
    _connect,
    _internal_store_for_tests,
)


def strategy_payload(strategy_id: str = "public-boundary-strategy") -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "strategy_id": strategy_id,
        "strategy_version": "1.0.0",
        "name": "Public Boundary Strategy",
        "symbol": "BTC_USDT_PERP",
        "required_timeframes": ["1h"],
        "parameters": {"fast": 2, "slow": 3},
        "rules": {"dsl_version": "0.1", "long": {}, "short": {}},
        "runtime_compatibility": {
            "runtime_family": "project-r7-e2-strategy-runtime",
            "runtime_version": "0.1.0",
        },
        "content_hash": f"sha256:{strategy_id}",
        "created_at": "2026-08-20T00:00:00Z",
    }


def strategy_record(strategy_id: str = "internal-registration") -> StrategyVersionRecord:
    return StrategyVersionRecord(
        identity=StrategyIdentity(strategy_id, "1.0.0"),
        strategy_schema_version="contracts-v0.1",
        content_hash=f"sha256:{strategy_id}",
        name="Internal Registration Strategy",
        symbol="BTC_USDT_PERP",
        declared_runtime_family="project-r7-e2-strategy-runtime",
        declared_runtime_version="0.1.0",
        definition_json='{"fixture":true}',
        upstream_created_at="2026-08-20T00:00:00Z",
        registered_at="2026-08-20T00:01:00Z",
    )


def backtest_payload(strategy_id: str, result_id: str) -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "backtest_result_id": result_id,
        "strategy_id": strategy_id,
        "strategy_version": "1.0.0",
        "strategy_content_hash": f"sha256:{strategy_id}",
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


def decision_payload(strategy_id: str, backtest_id: str, decision_id: str) -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "validation_decision_id": decision_id,
        "strategy_id": strategy_id,
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
            compatibility_id=f"compat-{definition['strategy_id']}",
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


LOCAL_E3_PASS = {
    "verification_status": "PASS",
    "verification_kind": "LOCAL_EXECUTION",
    "source_revision": "e3-synthetic-revision",
    "environment": "local-test-fixture",
    "command": "synthetic-e3-local-test",
    "result_ref": "synthetic-pass",
}


class PublicPersistenceBoundaryTests(unittest.TestCase):
    def test_supported_storage_surface_exports_only_safe_factory(self) -> None:
        self.assertEqual(["open_sqlite_platform"], storage.__all__)
        self.assertIs(storage.open_sqlite_platform, open_sqlite_platform)
        for raw_name in (
            "SQLiteRegistryStore",
            "connect",
            "apply_migrations",
            "sqlite_registry",
        ):
            with self.subTest(raw_name=raw_name):
                self.assertFalse(hasattr(storage, raw_name))

    def test_gate_c_explicit_import_compatibility_does_not_expand_supported_exports(self) -> None:
        self.assertIs(storage.OperationalModeRecovery, OperationalModeRecovery)
        self.assertIs(storage.OperationalModeStore, OperationalModeStore)
        self.assertIs(storage.ShadowCheckpoint, ShadowCheckpoint)
        for compatibility_name in (
            "OperationalModeRecovery",
            "OperationalModeStore",
            "ShadowCheckpoint",
        ):
            with self.subTest(compatibility_name=compatibility_name):
                self.assertNotIn(compatibility_name, storage.__all__)

    def test_factory_returns_service_without_public_raw_writer_or_connection(self) -> None:
        service = open_sqlite_platform(":memory:")
        self.assertIsInstance(service, StrategyPlatformService)
        for raw_name in (
            "connection",
            "store",
            "register_strategy",
            "save_compatibility",
            "save_validation_evidence",
            "append_transition",
        ):
            with self.subTest(raw_name=raw_name):
                self.assertFalse(hasattr(service, raw_name))

    def test_internal_store_construction_requires_writer_capability(self) -> None:
        connection = _connect(":memory:")
        try:
            _apply_migrations(connection)
            with self.assertRaises(PermissionError):
                _SQLiteRegistryStore(connection)
        finally:
            connection.close()

    def test_authority_looking_dtos_are_not_public_write_capabilities(self) -> None:
        service = open_sqlite_platform(":memory:")
        identity = StrategyIdentity("dto-only", "1.0.0")
        compatibility = CompatibilityEvidence(
            compatibility_id="compat-dto-only",
            identity=identity,
            status="PASS",
            verification_kind="LOCAL_EXECUTION",
            checker="E2_CALLER_CONSTRUCTED",
            checked_at="2026-08-20T00:01:00Z",
            reason_codes=("SYNTHETIC_TEST_ONLY",),
            details={},
            source_revision="synthetic",
            environment="synthetic",
            command="synthetic",
            result_ref="synthetic",
        )
        evidence = ValidationEvidenceRecord(
            evidence_id="evidence-dto-only",
            evidence_type="VALIDATION_DECISION",
            upstream_object_id="vd-dto-only",
            identity=identity,
            strategy_content_hash="sha256:dto-only",
            upstream_schema_version="contracts-v0.1",
            producer="E3",
            payload_json="{}",
            recorded_at="2026-08-20T00:02:00Z",
            verification_status="PASS",
            verification_kind="LOCAL_EXECUTION",
            decision="PASS",
            source_revision="synthetic",
            environment="synthetic",
            command="synthetic",
            result_ref="synthetic",
        )
        self.assertIsNotNone(compatibility)
        self.assertIsNotNone(evidence)
        self.assertFalse(hasattr(service, "save_compatibility"))
        self.assertFalse(hasattr(service, "save_validation_evidence"))

    def test_internal_registration_rejects_non_initial_projection_without_mutation(self) -> None:
        variants = (
            replace(strategy_record("candidate-register"), current_lifecycle_state="CANDIDATE"),
            replace(strategy_record("backtesting-register"), current_lifecycle_state="BACKTESTING"),
            replace(strategy_record("rejected-register"), current_lifecycle_state="REJECTED"),
            replace(strategy_record("revision-register"), registry_revision=1),
        )
        for record in variants:
            with self.subTest(strategy=record.identity.strategy_id):
                connection = _connect(":memory:")
                try:
                    _apply_migrations(connection)
                    store = _internal_store_for_tests(connection)
                    with self.assertRaises(InvalidTransition):
                        store.register_strategy(record)
                    count = connection.execute("SELECT COUNT(*) FROM strategy_versions").fetchone()[0]
                    self.assertEqual(0, count)
                finally:
                    connection.close()

    def test_database_rejects_incoherent_initial_projection(self) -> None:
        connection = _connect(":memory:")
        try:
            _apply_migrations(connection)
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO strategy_versions (
                        strategy_id, strategy_version, strategy_schema_version, content_hash,
                        name, symbol, declared_runtime_family, declared_runtime_version,
                        definition_json, upstream_created_at, registered_at,
                        current_lifecycle_state, registry_revision
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "raw-candidate",
                        "1.0.0",
                        "contracts-v0.1",
                        "sha256:raw-candidate",
                        "Raw Candidate",
                        "BTC_USDT_PERP",
                        "project-r7-e2-strategy-runtime",
                        "0.1.0",
                        '{"fixture":true}',
                        "2026-08-20T00:00:00Z",
                        "2026-08-20T00:01:00Z",
                        "CANDIDATE",
                        2,
                    ),
                )
            connection.rollback()
            self.assertEqual(
                0,
                connection.execute("SELECT COUNT(*) FROM strategy_versions").fetchone()[0],
            )
        finally:
            connection.close()

    def test_database_rejects_naked_projection_update(self) -> None:
        connection = _connect(":memory:")
        try:
            _apply_migrations(connection)
            store = _internal_store_for_tests(connection)
            record = strategy_record("naked-projection")
            store.register_strategy(record)
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    UPDATE strategy_versions
                    SET current_lifecycle_state = 'BACKTESTING', registry_revision = 1
                    WHERE strategy_id = ? AND strategy_version = ?
                    """,
                    (record.identity.strategy_id, record.identity.strategy_version),
                )
            connection.rollback()
            persisted = store.get_strategy(record.identity)
            self.assertIsNotNone(persisted)
            self.assertEqual("DRAFT", persisted.current_lifecycle_state)
            self.assertEqual(0, persisted.registry_revision)
        finally:
            connection.close()

    def test_public_service_intake_creates_draft_revision_zero(self) -> None:
        service = open_sqlite_platform(":memory:")
        outcome = service.intake(strategy_payload("public-intake"), source_actor="unit-test")
        self.assertEqual("DRAFT", outcome.strategy.current_lifecycle_state)
        self.assertEqual(0, outcome.strategy.registry_revision)

    def test_public_factory_preserves_service_authorized_backtesting_and_candidate(self) -> None:
        strategy_id = "public-valid-flow"
        service = open_sqlite_platform(
            ":memory:",
            compatibility_boundary=LocalPassE2Boundary(),
        )
        outcome = service.intake(strategy_payload(strategy_id), source_actor="unit-test")
        backtesting = service.begin_backtesting(outcome.strategy.identity, actor="unit-test")
        self.assertEqual("BACKTESTING", backtesting.current_lifecycle_state)
        self.assertEqual(1, backtesting.registry_revision)

        backtest_id = "bt-public-valid-flow"
        backtest = service.record_backtest_result(
            backtest_payload(strategy_id, backtest_id),
            **LOCAL_E3_PASS,
        )
        decision = service.record_validation_decision(
            decision_payload(strategy_id, backtest_id, "vd-public-valid-flow"),
            backtest_evidence_id=backtest.evidence_id,
            **LOCAL_E3_PASS,
        )
        candidate = service.mark_candidate(
            outcome.strategy.identity,
            actor="unit-test",
            validation_evidence_id=decision.evidence_id,
        )
        self.assertEqual("CANDIDATE", candidate.current_lifecycle_state)
        self.assertEqual(2, candidate.registry_revision)


if __name__ == "__main__":
    unittest.main()
