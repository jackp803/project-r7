from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from registry import (
    CompatibilityEvidence,
    InvalidTransition,
    LifecycleTransitionRecord,
    StrategyIdentity,
    StrategyPlatformService,
    StrategyVersionRecord,
)
from storage import SQLiteRegistryStore, apply_migrations, connect


def strategy_payload() -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "strategy_id": "persisted-strategy",
        "strategy_version": "1.0.0",
        "name": "Persisted Strategy",
        "symbol": "BTC_USDT_PERP",
        "required_timeframes": ["1h"],
        "parameters": {"fast": 2, "slow": 3},
        "rules": {"dsl_version": "0.1", "long": {}, "short": {}},
        "runtime_compatibility": {
            "runtime_family": "project-r7-e2-strategy-runtime",
            "runtime_version": "0.1.0",
        },
        "content_hash": "sha256:persisted-fixture",
        "created_at": "2026-08-20T00:00:00Z",
    }


def direct_strategy_record(strategy_id: str = "direct-persistence-strategy") -> StrategyVersionRecord:
    identity = StrategyIdentity(strategy_id, "1.0.0")
    return StrategyVersionRecord(
        identity=identity,
        strategy_schema_version="contracts-v0.1",
        content_hash=f"sha256:{strategy_id}",
        name="Direct Persistence Strategy",
        symbol="BTC_USDT_PERP",
        declared_runtime_family="project-r7-e2-strategy-runtime",
        declared_runtime_version="0.1.0",
        definition_json='{"fixture":true}',
        upstream_created_at="2026-08-20T00:00:00Z",
        registered_at="2026-08-20T00:01:00Z",
    )


def transition_record(
    identity: StrategyIdentity,
    previous_state: str,
    new_state: str,
    expected_revision: int,
    *,
    suffix: str,
) -> LifecycleTransitionRecord:
    return LifecycleTransitionRecord(
        transition_id=f"transition-{suffix}",
        identity=identity,
        previous_state=previous_state,
        new_state=new_state,
        changed_at="2026-08-20T00:02:00Z",
        changed_by="unit-test",
        reason_codes=("SYNTHETIC_PERSISTENCE_AUTHORITY_TEST",),
        primary_evidence_id=None,
        expected_registry_revision=expected_revision,
        resulting_registry_revision=expected_revision + 1,
    )


class LocalPassE2Boundary:
    def check(self, definition: dict) -> CompatibilityEvidence:
        return CompatibilityEvidence(
            compatibility_id="compat-persisted-pass",
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


class RegistryPersistenceTests(unittest.TestCase):
    def _direct_store_at_state(
        self, state: str, *, strategy_id: str
    ) -> tuple[sqlite3.Connection, SQLiteRegistryStore, StrategyIdentity]:
        connection = connect(":memory:")
        apply_migrations(connection)
        store = SQLiteRegistryStore(connection)
        record = direct_strategy_record(strategy_id)
        store.register_strategy(record)
        identity = record.identity

        if state in {"BACKTESTING", "REJECTED", "CANDIDATE"}:
            store.append_transition(
                transition_record(
                    identity,
                    "DRAFT",
                    "BACKTESTING",
                    0,
                    suffix=f"{strategy_id}-draft-backtesting",
                )
            )
        if state == "REJECTED":
            store.append_transition(
                transition_record(
                    identity,
                    "BACKTESTING",
                    "REJECTED",
                    1,
                    suffix=f"{strategy_id}-backtesting-rejected",
                )
            )
        elif state == "CANDIDATE":
            store.append_transition(
                transition_record(
                    identity,
                    "BACKTESTING",
                    "CANDIDATE",
                    1,
                    suffix=f"{strategy_id}-backtesting-candidate",
                )
            )
        return connection, store, identity

    def test_migration_is_idempotent(self) -> None:
        connection = connect(":memory:")
        try:
            apply_migrations(connection)
            apply_migrations(connection)
            migrations = connection.execute(
                "SELECT migration_name FROM schema_migrations ORDER BY migration_name"
            ).fetchall()
            self.assertEqual(["0001_strategy_registry.sql"], [row[0] for row in migrations])
        finally:
            connection.close()

    def test_immutable_strategy_content_cannot_be_overwritten_directly(self) -> None:
        connection = connect(":memory:")
        try:
            apply_migrations(connection)
            store = SQLiteRegistryStore(connection)
            service = StrategyPlatformService(store)
            service.intake(strategy_payload(), source_actor="unit-test")

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    UPDATE strategy_versions
                    SET content_hash = 'sha256:overwritten'
                    WHERE strategy_id = 'persisted-strategy' AND strategy_version = '1.0.0'
                    """
                )
        finally:
            connection.close()

    def test_lifecycle_history_is_append_only(self) -> None:
        connection = connect(":memory:")
        try:
            apply_migrations(connection)
            store = SQLiteRegistryStore(connection)
            service = StrategyPlatformService(store, LocalPassE2Boundary())
            outcome = service.intake(strategy_payload(), source_actor="unit-test")
            service.begin_backtesting(outcome.strategy.identity, actor="unit-test")
            transition_id = connection.execute(
                "SELECT transition_id FROM lifecycle_transitions"
            ).fetchone()[0]

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "UPDATE lifecycle_transitions SET new_state = 'CANDIDATE' WHERE transition_id = ?",
                    (transition_id,),
                )
            connection.rollback()
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    "DELETE FROM lifecycle_transitions WHERE transition_id = ?",
                    (transition_id,),
                )
        finally:
            connection.close()

    def test_direct_store_allows_exactly_the_three_early_slice2_edges(self) -> None:
        cases = (
            ("DRAFT", "BACKTESTING", 0),
            ("BACKTESTING", "REJECTED", 1),
            ("BACKTESTING", "CANDIDATE", 1),
        )
        for index, (previous_state, new_state, expected_revision) in enumerate(cases):
            with self.subTest(previous_state=previous_state, new_state=new_state):
                connection, store, identity = self._direct_store_at_state(
                    previous_state,
                    strategy_id=f"legal-edge-{index}",
                )
                try:
                    before_count = connection.execute(
                        "SELECT COUNT(*) FROM lifecycle_transitions"
                    ).fetchone()[0]
                    result = store.append_transition(
                        transition_record(
                            identity,
                            previous_state,
                            new_state,
                            expected_revision,
                            suffix=f"legal-{index}",
                        )
                    )
                    self.assertEqual(new_state, result.current_lifecycle_state)
                    self.assertEqual(expected_revision + 1, result.registry_revision)
                    after_count = connection.execute(
                        "SELECT COUNT(*) FROM lifecycle_transitions"
                    ).fetchone()[0]
                    self.assertEqual(before_count + 1, after_count)
                finally:
                    connection.close()

    def test_direct_store_forbidden_edges_fail_closed_without_state_mutation(self) -> None:
        forbidden_cases = (
            ("DRAFT", "CANDIDATE"),
            ("DRAFT", "REJECTED"),
            ("CANDIDATE", "DRAFT"),
            ("CANDIDATE", "BACKTESTING"),
            ("REJECTED", "CANDIDATE"),
            ("REJECTED", "BACKTESTING"),
            ("DRAFT", "DRAFT"),
            ("BACKTESTING", "BACKTESTING"),
            ("REJECTED", "REJECTED"),
            ("CANDIDATE", "CANDIDATE"),
        )
        for index, (previous_state, new_state) in enumerate(forbidden_cases):
            with self.subTest(previous_state=previous_state, new_state=new_state):
                connection, store, identity = self._direct_store_at_state(
                    previous_state,
                    strategy_id=f"forbidden-edge-{index}",
                )
                try:
                    before = store.get_strategy(identity)
                    self.assertIsNotNone(before)
                    before_count = connection.execute(
                        "SELECT COUNT(*) FROM lifecycle_transitions"
                    ).fetchone()[0]

                    with self.assertRaises(InvalidTransition):
                        store.append_transition(
                            transition_record(
                                identity,
                                previous_state,
                                new_state,
                                before.registry_revision,
                                suffix=f"forbidden-{index}",
                            )
                        )

                    after = store.get_strategy(identity)
                    self.assertIsNotNone(after)
                    self.assertEqual(before.current_lifecycle_state, after.current_lifecycle_state)
                    self.assertEqual(before.registry_revision, after.registry_revision)
                    after_count = connection.execute(
                        "SELECT COUNT(*) FROM lifecycle_transitions"
                    ).fetchone()[0]
                    self.assertEqual(before_count, after_count)
                finally:
                    connection.close()

    def test_database_trigger_rejects_forbidden_direct_sql_edge_without_projection_change(self) -> None:
        connection = connect(":memory:")
        try:
            apply_migrations(connection)
            store = SQLiteRegistryStore(connection)
            record = direct_strategy_record("direct-sql-forbidden")
            store.register_strategy(record)

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO lifecycle_transitions (
                        transition_id, strategy_id, strategy_version,
                        previous_state, new_state, changed_at, changed_by,
                        reason_codes_json, primary_evidence_id,
                        expected_registry_revision, resulting_registry_revision
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "transition-direct-sql-forbidden",
                        record.identity.strategy_id,
                        record.identity.strategy_version,
                        "DRAFT",
                        "CANDIDATE",
                        "2026-08-20T00:02:00Z",
                        "unit-test",
                        '["SYNTHETIC_DIRECT_SQL_TEST"]',
                        None,
                        0,
                        1,
                    ),
                )
            connection.rollback()

            persisted = store.get_strategy(record.identity)
            self.assertIsNotNone(persisted)
            self.assertEqual("DRAFT", persisted.current_lifecycle_state)
            self.assertEqual(0, persisted.registry_revision)
            count = connection.execute("SELECT COUNT(*) FROM lifecycle_transitions").fetchone()[0]
            self.assertEqual(0, count)
        finally:
            connection.close()

    def test_registry_state_survives_restart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "registry.sqlite3"
            first = connect(database_path)
            apply_migrations(first)
            first_store = SQLiteRegistryStore(first)
            service = StrategyPlatformService(first_store, LocalPassE2Boundary())
            outcome = service.intake(strategy_payload(), source_actor="unit-test")
            service.begin_backtesting(outcome.strategy.identity, actor="unit-test")
            first.close()

            second = connect(database_path)
            try:
                apply_migrations(second)
                restored = SQLiteRegistryStore(second).get_strategy(outcome.strategy.identity)
                self.assertIsNotNone(restored)
                self.assertEqual("BACKTESTING", restored.current_lifecycle_state)
                self.assertEqual(1, restored.registry_revision)
                count = second.execute("SELECT COUNT(*) FROM lifecycle_transitions").fetchone()[0]
                self.assertEqual(1, count)
            finally:
                second.close()


if __name__ == "__main__":
    unittest.main()
