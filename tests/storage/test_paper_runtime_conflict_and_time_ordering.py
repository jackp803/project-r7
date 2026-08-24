from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from storage._sqlite_registry import _apply_migrations, _connect
from storage.runtime import RuntimeConflictError, open_paper_runtime_journal


def _json(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _risk() -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "risk_decision_id": "risk-e6-time-001",
        "intent_id": "intent-e6-time-001",
        "strategy_id": "strategy-e6-time",
        "strategy_version": "1.0.0",
        "decision": "APPROVE",
        "reason_codes": [],
        "risk_policy_version": "risk-policy-e6-time-v0.1",
        "decided_at": "2026-08-24T07:00:00Z",
        "market_health_status": "HEALTHY",
        "account_state_status": "KNOWN",
        "position_state_status": "FLAT",
    }


def _plan() -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "trade_plan_id": "plan-e6-time-001",
        "risk_decision_id": "risk-e6-time-001",
        "intent_id": "intent-e6-time-001",
        "strategy_id": "strategy-e6-time",
        "strategy_version": "1.0.0",
        "symbol": "BTC_USDT_PERP",
        "direction": "LONG",
        "quantity": "0.003",
        "quantity_profile_version": "base-asset-v0.1",
        "quantity_unit": "BASE_ASSET",
        "quantity_asset": "BTC",
        "leverage": "20",
        "margin_mode": "ISOLATED",
        "entry_instruction": {"profile_version": "entry-v0.1", "order_type": "MARKET"},
        "protection_instruction": {"stop_level": "59400", "max_hold_seconds": 1800},
        "created_at": "2026-08-24T07:00:01Z",
        "expires_at": "2026-08-24T07:00:31Z",
        "risk_policy_version": "risk-policy-e6-time-v0.1",
    }


def _position(observed_at: str, *, quantity: str = "0.0012", lifecycle: str = "OPEN_UNPROTECTED") -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "position_id": "position-e6-time-001",
        "symbol": "BTC_USDT_PERP",
        "side": "LONG",
        "actual_quantity": quantity,
        "average_entry_price": "60000",
        "opened_at": "2026-08-24T07:00:10Z",
        "broker_state_observed_at": observed_at,
        "reconciliation_status": "CONSISTENT",
        "lifecycle_state": lifecycle,
        "quantity_profile_version": "base-asset-v0.1",
        "quantity_unit": "BASE_ASSET",
        "quantity_asset": "BTC",
    }


def _projection(
    source: dict,
    *,
    revision: int,
    previous_id: str | None,
    kind: str,
    event: str | None,
    lifecycle_state: str,
    interpreted_at: str,
) -> dict:
    payload = dict(source)
    payload["lifecycle_state"] = lifecycle_state
    payload["position_lifecycle_projection_profile_version"] = "position-lifecycle-projection-v0.1"
    payload["lifecycle_revision"] = revision
    payload["previous_lifecycle_projection_id"] = previous_id
    payload["lifecycle_projection_kind"] = kind
    payload["lifecycle_event"] = event
    payload["lifecycle_interpreted_at"] = interpreted_at
    payload["lifecycle_source_broker_state_observed_at"] = source["broker_state_observed_at"]
    payload["lifecycle_projection_id"] = "posproj_" + hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()
    return payload


def _action() -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "protection_profile_version": "protection-v0.1",
        "position_action_id": "posact-e6-time-001",
        "position_id": "position-e6-time-001",
        "action": "PROTECT",
        "reason_codes": ["E5_PROTECTION_REQUIRED"],
        "risk_policy_version": "risk-policy-e6-time-v0.1",
        "trade_plan_id": "plan-e6-time-001",
        "risk_decision_id": "risk-e6-time-001",
        "symbol": "BTC_USDT_PERP",
        "position_side": "LONG",
        "position_observed_at": "2026-08-24T07:00:20Z",
        "position_reconciliation_status": "CONSISTENT",
        "quantity": "0.0012",
        "quantity_profile_version": "base-asset-v0.1",
        "quantity_unit": "BASE_ASSET",
        "quantity_asset": "BTC",
        "protection_instruction": {"stop_level": "59400", "max_hold_seconds": 1800},
        "created_at": "2026-08-24T07:00:20Z",
        "expires_at": "2026-08-24T07:01:20Z",
    }


def _request() -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "order_request_id": "ordreq-e6-time-001",
        "trade_plan_id": "plan-e6-time-001",
        "client_order_id": "client-e6-time-001",
        "symbol": "BTC_USDT_PERP",
        "side": "SELL",
        "order_type": "STOP_MARKET",
        "quantity": "0.0012",
        "quantity_profile_version": "base-asset-v0.1",
        "quantity_unit": "BASE_ASSET",
        "quantity_asset": "BTC",
        "created_at": "2026-08-24T07:00:20Z",
        "authorization_type": "POSITION_ACTION",
        "position_action_id": "posact-e6-time-001",
        "position_id": "position-e6-time-001",
        "risk_decision_id": "risk-e6-time-001",
        "order_role": "PROTECTION_STOP",
        "limit_price": None,
        "stop_price": "59400",
        "reduce_only": True,
        "time_in_force": None,
    }


def _order_result(observed_at: str, status: str, filled: str) -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "order_request_id": "ordreq-e6-time-001",
        "client_order_id": "client-e6-time-001",
        "broker_order_id": "paper-e6-time-001",
        "order_status": status,
        "observed_at": observed_at,
        "execution_health_status": "HEALTHY",
        "requested_quantity": "0.0012",
        "filled_quantity": filled,
        "average_fill_price": None,
        "reject_reason": None,
    }


def _funding() -> dict:
    payload = {
        "schema_version": "contracts-v0.1",
        "funding_evidence_profile_version": "funding-allocation-v0.1",
        "source_kind": "PAPER_MODEL",
        "source": "R7_PAPER_FUNDING_MODEL",
        "source_version": "paper-zero-funding-v0.1",
        "source_material_hash": "sha256:e6-time-source",
        "source_record_count": 0,
        "source_complete_through": "2026-08-24T07:01:00Z",
        "trade_plan_id": "plan-e6-time-001",
        "position_id": "position-e6-time-001",
        "symbol": "BTC_USDT_PERP",
        "interval_start": "2026-08-24T07:00:10Z",
        "interval_end": "2026-08-24T07:01:00Z",
        "interval_semantics": "START_INCLUSIVE_END_EXCLUSIVE",
        "status": "ZERO_CONFIRMED",
        "funding_cost": "0",
        "cost_currency": "USDT",
        "calculated_at": "2026-08-24T07:01:00Z",
    }
    identity_fields = (
        "schema_version",
        "funding_evidence_profile_version",
        "source_kind",
        "source",
        "source_version",
        "source_material_hash",
        "source_record_count",
        "source_complete_through",
        "trade_plan_id",
        "position_id",
        "symbol",
        "interval_start",
        "interval_end",
        "interval_semantics",
        "status",
        "funding_cost",
        "cost_currency",
    )
    material = {field: payload[field] for field in identity_fields}
    payload["funding_evidence_id"] = "fundev_" + hashlib.sha256(_json(material).encode("utf-8")).hexdigest()
    return payload


class PaperRuntimeConflictAndOrderingDefinitions(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "runtime.sqlite3"
        self.journal = open_paper_runtime_journal(self.db_path)

    def tearDown(self) -> None:
        try:
            self.journal.close()
        except sqlite3.Error:
            pass
        self.temp.cleanup()

    def _parents(self) -> None:
        self.journal.persist_risk_decision(_risk())
        self.journal.persist_approved_trade_plan(_plan())

    def _order_parent_graph(self) -> None:
        self._parents()
        self.journal.persist_position_action(_action())
        self.journal.persist_order_request(_request())

    def test_true_additive_migration_from_registry_only_database(self) -> None:
        self.journal.close()
        fresh_path = Path(self.temp.name) / "registry-first.sqlite3"
        connection = _connect(fresh_path)
        try:
            migrations_dir = Path("src/storage/migrations")
            one_migration_dir = Path(self.temp.name) / "only-0001"
            one_migration_dir.mkdir()
            (one_migration_dir / "0001_strategy_registry.sql").write_text(
                (migrations_dir / "0001_strategy_registry.sql").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            _apply_migrations(connection, one_migration_dir)
            connection.execute(
                """
                INSERT INTO strategy_versions (
                    strategy_id, strategy_version, strategy_schema_version, content_hash,
                    name, symbol, declared_runtime_family, declared_runtime_version,
                    definition_json, upstream_created_at, registered_at,
                    current_lifecycle_state, registry_revision
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DRAFT', 0)
                """,
                (
                    "strategy-pre-runtime-migration",
                    "1.0.0",
                    "contracts-v0.1",
                    "sha256:pre-runtime-migration",
                    "Pre Runtime Migration",
                    "BTC_USDT_PERP",
                    "project-r7-e2-strategy-runtime",
                    "0.1.0",
                    '{"fixture":true}',
                    "2026-08-24T06:00:00Z",
                    "2026-08-24T06:01:00Z",
                ),
            )
            connection.commit()
        finally:
            connection.close()

        journal = open_paper_runtime_journal(fresh_path)
        journal.close()
        verify = sqlite3.connect(fresh_path)
        try:
            strategy = verify.execute(
                "SELECT current_lifecycle_state, registry_revision FROM strategy_versions WHERE strategy_id = ?",
                ("strategy-pre-runtime-migration",),
            ).fetchone()
            self.assertEqual(("DRAFT", 0), strategy)
            migrations = {row[0] for row in verify.execute("SELECT migration_name FROM schema_migrations")}
            self.assertEqual({"0001_strategy_registry.sql", "0002_paper_runtime_durability.sql"}, migrations)
        finally:
            verify.close()
        self.journal = open_paper_runtime_journal(self.db_path)

    def test_same_declared_projection_id_with_changed_payload_is_durable_conflict(self) -> None:
        source = _position("2026-08-24T07:00:20Z")
        projection = _projection(
            source,
            revision=0,
            previous_id=None,
            kind="GENESIS",
            event=None,
            lifecycle_state="OPEN_UNPROTECTED",
            interpreted_at="2026-08-24T07:00:20Z",
        )
        self.journal.persist_position_projection(projection)
        corrupt = dict(projection)
        corrupt["actual_quantity"] = "0.0011"
        with self.assertRaises(RuntimeConflictError) as ctx:
            self.journal.persist_position_projection(corrupt)
        self.assertEqual("LIFECYCLE_PROJECTION_ID_CORRUPTION", ctx.exception.code)
        self._parents()
        recovery = self.journal.recover(position_id="position-e6-time-001")
        self.assertEqual("CONFLICT", recovery.status)
        self.assertIn("UNRESOLVED_DURABLE_CONFLICT", recovery.reason_codes)

    def test_same_funding_id_with_changed_identity_material_is_durable_conflict(self) -> None:
        first = _funding()
        self.journal.persist_funding_evidence(first)
        corrupt = dict(first)
        corrupt["source_material_hash"] = "sha256:changed-but-id-not-recomputed"
        with self.assertRaises(RuntimeConflictError) as ctx:
            self.journal.persist_funding_evidence(corrupt)
        self.assertEqual("FUNDING_IDENTITY_CORRUPTION", ctx.exception.code)
        recovery = self.journal.recover(position_id="position-e6-time-001")
        self.assertEqual("CONFLICT", recovery.status)

    def test_fractional_order_result_timestamp_advances_current_without_lexical_bug(self) -> None:
        self._order_parent_graph()
        first = _order_result("2026-08-24T07:00:20Z", "OPEN", "0")
        later = _order_result("2026-08-24T07:00:20.500000Z", "PARTIALLY_FILLED", "0.0004")
        self.journal.persist_order_result(first)
        self.journal.persist_order_result(later)
        genesis = _projection(
            _position("2026-08-24T07:00:20Z"),
            revision=0,
            previous_id=None,
            kind="GENESIS",
            event=None,
            lifecycle_state="OPEN_UNPROTECTED",
            interpreted_at="2026-08-24T07:00:20Z",
        )
        self.journal.persist_position_projection(genesis)
        recovery = self.journal.recover(position_id="position-e6-time-001")
        self.assertEqual("2026-08-24T07:00:20.500000Z", recovery.current_order_results[0].payload["observed_at"])
        self.assertEqual("PARTIALLY_FILLED", recovery.current_order_results[0].payload["order_status"])

    def test_fractional_newer_raw_position_requires_reattestation(self) -> None:
        self._parents()
        genesis = _projection(
            _position("2026-08-24T07:00:20Z"),
            revision=0,
            previous_id=None,
            kind="GENESIS",
            event=None,
            lifecycle_state="OPEN_UNPROTECTED",
            interpreted_at="2026-08-24T07:00:20Z",
        )
        self.journal.persist_position_projection(genesis)
        newer = _position("2026-08-24T07:00:20.500000Z", quantity="0.0010")
        self.journal.persist_raw_position_observation(newer)
        recovery = self.journal.recover(position_id="position-e6-time-001")
        self.assertEqual("REATTESTATION_REQUIRED", recovery.status)
        self.assertEqual(newer, recovery.raw_position_observations[-1].payload)
        self.assertEqual(genesis, recovery.current_position_projection.payload)


if __name__ == "__main__":
    unittest.main()
