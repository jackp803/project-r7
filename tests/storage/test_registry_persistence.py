from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from registry import CompatibilityEvidence, StrategyIdentity, StrategyPlatformService
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
