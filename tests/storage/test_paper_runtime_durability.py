from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from storage._sqlite_registry import _apply_migrations, _connect
from storage.runtime import (
    RuntimeConflictError,
    RuntimePersistenceError,
    RuntimeValidationError,
    open_paper_runtime_journal,
)


def _canonical_json(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def risk_decision() -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "risk_decision_id": "risk-e6-paper-001",
        "intent_id": "intent-e6-paper-001",
        "strategy_id": "strategy-e6-paper",
        "strategy_version": "1.0.0",
        "decision": "APPROVE",
        "reason_codes": [],
        "risk_policy_version": "risk-policy-e6-v0.1",
        "decided_at": "2026-08-24T07:00:00Z",
        "market_health_status": "HEALTHY",
        "account_state_status": "KNOWN",
        "position_state_status": "FLAT",
        "approved_quantity": "0.003",
        "approved_leverage": "20",
        "margin_mode": "ISOLATED",
        "required_stop_level": "59400",
        "max_hold_seconds": 1800,
    }


def approved_plan() -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "trade_plan_id": "plan-e6-paper-001",
        "risk_decision_id": "risk-e6-paper-001",
        "intent_id": "intent-e6-paper-001",
        "strategy_id": "strategy-e6-paper",
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
        "protection_instruction": {"stop_level": "59400", "target_level": "61200", "max_hold_seconds": 1800},
        "created_at": "2026-08-24T07:00:01Z",
        "expires_at": "2026-08-24T07:00:31Z",
        "risk_policy_version": "risk-policy-e6-v0.1",
    }


def base_position(*, observed_at: str = "2026-08-24T07:00:20Z", quantity: str = "0.0012", lifecycle: str = "OPEN_UNPROTECTED", closed_at: str | None = None) -> dict:
    result = {
        "schema_version": "contracts-v0.1",
        "position_id": "position-e6-paper-001",
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
    if closed_at is not None:
        result["closed_at"] = closed_at
    return result


def lifecycle_projection(
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
    material = dict(payload)
    digest = hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    payload["lifecycle_projection_id"] = "posproj_" + digest
    return payload


def protect_action() -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "protection_profile_version": "protection-v0.1",
        "position_action_id": "posact-e6-protect-001",
        "position_id": "position-e6-paper-001",
        "action": "PROTECT",
        "reason_codes": ["E5_PROTECTION_REQUIRED"],
        "risk_policy_version": "risk-policy-e6-v0.1",
        "trade_plan_id": "plan-e6-paper-001",
        "risk_decision_id": "risk-e6-paper-001",
        "symbol": "BTC_USDT_PERP",
        "position_side": "LONG",
        "position_observed_at": "2026-08-24T07:00:20Z",
        "position_reconciliation_status": "CONSISTENT",
        "quantity": "0.0012",
        "quantity_profile_version": "base-asset-v0.1",
        "quantity_unit": "BASE_ASSET",
        "quantity_asset": "BTC",
        "protection_instruction": {"stop_level": "59400", "target_level": "61200", "max_hold_seconds": 1800},
        "created_at": "2026-08-24T07:00:20Z",
        "expires_at": "2026-08-24T07:01:20Z",
    }


def order_request(*, request_id: str = "ordreq-e6-protect-001", client_id: str = "client-e6-protect-001", role: str = "PROTECTION_STOP") -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "order_request_id": request_id,
        "trade_plan_id": "plan-e6-paper-001",
        "client_order_id": client_id,
        "symbol": "BTC_USDT_PERP",
        "side": "SELL",
        "order_type": "STOP_MARKET" if role == "PROTECTION_STOP" else "MARKET",
        "quantity": "0.0012",
        "quantity_profile_version": "base-asset-v0.1",
        "quantity_unit": "BASE_ASSET",
        "quantity_asset": "BTC",
        "created_at": "2026-08-24T07:00:20Z",
        "authorization_type": "POSITION_ACTION",
        "position_action_id": "posact-e6-protect-001",
        "position_id": "position-e6-paper-001",
        "risk_decision_id": "risk-e6-paper-001",
        "order_role": role,
        "limit_price": None,
        "stop_price": "59400" if role == "PROTECTION_STOP" else None,
        "reduce_only": True,
        "time_in_force": None,
    }


def order_result(*, observed_at: str = "2026-08-24T07:00:20Z", status: str = "OPEN", health: str = "HEALTHY", filled: str = "0", broker_id: str | None = "paper-e6-order-001") -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "order_request_id": "ordreq-e6-protect-001",
        "client_order_id": "client-e6-protect-001",
        "broker_order_id": broker_id,
        "order_status": status,
        "observed_at": observed_at,
        "execution_health_status": health,
        "requested_quantity": "0.0012",
        "filled_quantity": filled,
        "average_fill_price": None,
        "reject_reason": None,
    }


def fill(*, fill_id: str = "fill-e6-protect-001", price: str = "59400", filled_at: str = "2026-08-24T07:00:40Z") -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "fill_id": fill_id,
        "broker_order_id": "paper-e6-order-001",
        "client_order_id": "client-e6-protect-001",
        "trade_plan_id": "plan-e6-paper-001",
        "symbol": "BTC_USDT_PERP",
        "side": "SELL",
        "quantity": "0.0012",
        "price": price,
        "filled_at": filled_at,
        "fee": "0.01",
        "fee_currency": "USDT",
        "liquidity_role": "TAKER",
        "position_action_id": "posact-e6-protect-001",
        "position_id": "position-e6-paper-001",
        "order_role": "PROTECTION_STOP",
    }


def funding_evidence(*, source_material_hash: str = "sha256:funding-source-a", calculated_at: str = "2026-08-24T07:00:50Z") -> dict:
    payload = {
        "schema_version": "contracts-v0.1",
        "funding_evidence_profile_version": "funding-allocation-v0.1",
        "source_kind": "PAPER_MODEL",
        "source": "R7_PAPER_FUNDING_MODEL",
        "source_version": "paper-zero-funding-v0.1",
        "source_material_hash": source_material_hash,
        "source_record_count": 0,
        "source_complete_through": "2026-08-24T07:00:50Z",
        "trade_plan_id": "plan-e6-paper-001",
        "position_id": "position-e6-paper-001",
        "symbol": "BTC_USDT_PERP",
        "interval_start": "2026-08-24T07:00:10Z",
        "interval_end": "2026-08-24T07:00:50Z",
        "interval_semantics": "START_INCLUSIVE_END_EXCLUSIVE",
        "status": "ZERO_CONFIRMED",
        "funding_cost": "0",
        "cost_currency": "USDT",
        "calculated_at": calculated_at,
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
    payload["funding_evidence_id"] = "fundev_" + hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    return payload


def trade_result(funding: dict) -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "trade_result_id": "trade-result-e6-paper-001",
        "strategy_id": "strategy-e6-paper",
        "strategy_version": "1.0.0",
        "trade_plan_id": "plan-e6-paper-001",
        "position_id": "position-e6-paper-001",
        "opened_at": "2026-08-24T07:00:10Z",
        "closed_at": "2026-08-24T07:00:50Z",
        "entry_quantity": "0.0012",
        "average_entry_price": "60000",
        "average_exit_price": "59400",
        "gross_pnl": "-0.72",
        "net_pnl": "-0.74",
        "total_fees": "0.02",
        "exit_reason_codes": ["PROTECTION_STOP_FILLED"],
        "trade_result_profile_version": "trade-result-v0.1",
        "pnl_profile_version": "linear-base-asset-pnl-v0.1",
        "risk_decision_id": "risk-e6-paper-001",
        "risk_policy_version": "risk-policy-e6-v0.1",
        "symbol": "BTC_USDT_PERP",
        "direction": "LONG",
        "quantity_profile_version": "base-asset-v0.1",
        "quantity_unit": "BASE_ASSET",
        "quantity_asset": "BTC",
        "pnl_currency": "USDT",
        "entry_fill_ids": ["fill-entry-e6-001"],
        "exit_fill_ids": ["fill-e6-protect-001"],
        "entry_order_request_ids": ["ordreq-entry-e6-001"],
        "exit_order_request_ids": ["ordreq-e6-protect-001"],
        "exit_authority_refs": [{"position_action_id": "posact-e6-protect-001", "position_id": "position-e6-paper-001", "action": "PROTECT", "order_role": "PROTECTION_STOP"}],
        "flat_position_observed_at": "2026-08-24T07:00:50Z",
        "funding_evidence_status": "ZERO_CONFIRMED",
        "funding_evidence_profile_version": "funding-allocation-v0.1",
        "funding_evidence_id": funding["funding_evidence_id"],
    }


class PaperRuntimeDurabilityDefinitions(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "paper-runtime.sqlite3"
        self.journal = open_paper_runtime_journal(self.db_path)

    def tearDown(self) -> None:
        try:
            self.journal.close()
        except sqlite3.Error:
            pass
        self.temp.cleanup()

    def _persist_core(self) -> tuple[dict, dict]:
        risk = risk_decision()
        plan = approved_plan()
        self.journal.persist_risk_decision(risk)
        self.journal.persist_approved_trade_plan(plan)
        return risk, plan

    def _persist_open_protection_graph(self, *, ambiguous: bool = False) -> dict:
        self._persist_core()
        source = base_position()
        genesis = lifecycle_projection(
            source,
            revision=0,
            previous_id=None,
            kind="GENESIS",
            event=None,
            lifecycle_state="OPEN_UNPROTECTED",
            interpreted_at="2026-08-24T07:00:20Z",
        )
        protected = lifecycle_projection(
            source,
            revision=1,
            previous_id=genesis["lifecycle_projection_id"],
            kind="TRANSITION",
            event="PROTECTION_VERIFIED",
            lifecycle_state="OPEN_PROTECTED",
            interpreted_at="2026-08-24T07:00:21Z",
        )
        self.journal.persist_position_projection(genesis)
        self.journal.persist_position_projection(protected)
        action = protect_action()
        request = order_request()
        self.journal.persist_position_action(action)
        self.journal.persist_order_request(request)
        result = order_result(
            observed_at="2026-08-24T07:00:22Z",
            status="RECONCILIATION_REQUIRED" if ambiguous else "PARTIALLY_FILLED",
            health="DEGRADED" if ambiguous else "HEALTHY",
            filled="0" if ambiguous else "0.0004",
            broker_id=None if ambiguous else "paper-e6-order-001",
        )
        self.journal.persist_order_result(result)
        if not ambiguous:
            partial_fill = fill(fill_id="fill-e6-partial-001", price="59450", filled_at="2026-08-24T07:00:22Z")
            partial_fill["quantity"] = "0.0004"
            self.journal.persist_fill(partial_fill)
        return {"genesis": genesis, "protected": protected, "action": action, "request": request, "result": result}

    def test_additive_migration_preserves_existing_registry_schema_and_data(self) -> None:
        self.journal.close()
        connection = _connect(self.db_path)
        try:
            _apply_migrations(connection)
            connection.execute(
                """
                INSERT INTO strategy_versions (
                    strategy_id, strategy_version, strategy_schema_version,
                    content_hash, name, symbol, declared_runtime_family,
                    declared_runtime_version, definition_json, upstream_created_at,
                    registered_at, current_lifecycle_state, registry_revision
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DRAFT', 0)
                """,
                (
                    "strategy-registry-preserved",
                    "1.0.0",
                    "contracts-v0.1",
                    "sha256:registry-preserved",
                    "Registry Preserved",
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
        self.journal = open_paper_runtime_journal(self.db_path)
        self.journal.close()
        verify = sqlite3.connect(self.db_path)
        try:
            row = verify.execute(
                "SELECT current_lifecycle_state, registry_revision FROM strategy_versions WHERE strategy_id = ?",
                ("strategy-registry-preserved",),
            ).fetchone()
            self.assertEqual(("DRAFT", 0), row)
            tables = {r[0] for r in verify.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertIn("paper_position_lifecycle_projections", tables)
            self.assertIn("paper_trade_results", tables)
        finally:
            verify.close()
        self.journal = open_paper_runtime_journal(self.db_path)

    def test_immutable_objects_round_trip_and_idempotent_replay(self) -> None:
        risk, plan = self._persist_core()
        action = protect_action()
        request = order_request()
        self.journal.persist_position_action(action)
        self.journal.persist_order_request(request)
        fill_payload = fill()
        self.journal.persist_fill(fill_payload)
        for method, payload in (
            (self.journal.persist_risk_decision, risk),
            (self.journal.persist_approved_trade_plan, plan),
            (self.journal.persist_position_action, action),
            (self.journal.persist_order_request, request),
            (self.journal.persist_fill, fill_payload),
        ):
            stored = method(payload)
            self.assertEqual(payload, stored.payload)
            self.assertEqual(stored.payload_json, _canonical_json(payload))

    def test_same_immutable_id_changed_payload_fails_closed(self) -> None:
        risk, plan = self._persist_core()
        action = protect_action()
        request = order_request()
        fill_payload = fill()
        self.journal.persist_position_action(action)
        self.journal.persist_order_request(request)
        self.journal.persist_fill(fill_payload)
        cases = (
            (self.journal.persist_risk_decision, risk, "market_health_status", "STALE"),
            (self.journal.persist_approved_trade_plan, plan, "quantity", "0.004"),
            (self.journal.persist_position_action, action, "quantity", "0.0011"),
            (self.journal.persist_order_request, request, "quantity", "0.0011"),
            (self.journal.persist_fill, fill_payload, "price", "59399"),
        )
        for method, original, field, changed in cases:
            with self.subTest(field=field):
                conflict = dict(original)
                conflict[field] = changed
                with self.assertRaises(RuntimeConflictError):
                    method(conflict)

    def test_position_genesis_transition_reattestation_round_trip_and_current_revision(self) -> None:
        source = base_position()
        genesis = lifecycle_projection(source, revision=0, previous_id=None, kind="GENESIS", event=None, lifecycle_state="OPEN_UNPROTECTED", interpreted_at="2026-08-24T07:00:20Z")
        protected = lifecycle_projection(source, revision=1, previous_id=genesis["lifecycle_projection_id"], kind="TRANSITION", event="PROTECTION_VERIFIED", lifecycle_state="OPEN_PROTECTED", interpreted_at="2026-08-24T07:00:21Z")
        newer = base_position(observed_at="2026-08-24T07:00:30Z", lifecycle="OPEN_PROTECTED")
        reattested = lifecycle_projection(newer, revision=2, previous_id=protected["lifecycle_projection_id"], kind="REATTESTATION", event=None, lifecycle_state="OPEN_PROTECTED", interpreted_at="2026-08-24T07:00:31Z")
        for payload in (genesis, protected, reattested):
            self.assertEqual(payload, self.journal.persist_position_projection(payload).payload)
        self.journal.persist_position_projection(genesis)
        self._persist_core()
        action = protect_action()
        self.journal.persist_position_action(action)
        recovery = self.journal.recover(position_id="position-e6-paper-001")
        self.assertEqual(2, recovery.current_position_projection.payload["lifecycle_revision"])
        self.assertEqual(reattested, recovery.current_position_projection.payload)
        self.assertEqual([0, 1, 2], [item.payload["lifecycle_revision"] for item in recovery.lifecycle_history])

    def test_lifecycle_same_revision_changed_projection_conflicts(self) -> None:
        source = base_position()
        genesis = lifecycle_projection(source, revision=0, previous_id=None, kind="GENESIS", event=None, lifecycle_state="OPEN_UNPROTECTED", interpreted_at="2026-08-24T07:00:20Z")
        self.journal.persist_position_projection(genesis)
        alternative = lifecycle_projection(source, revision=0, previous_id=None, kind="GENESIS", event=None, lifecycle_state="OPEN_PROTECTED", interpreted_at="2026-08-24T07:00:21Z")
        with self.assertRaises(RuntimeConflictError):
            self.journal.persist_position_projection(alternative)

    def test_lifecycle_gap_predecessor_mismatch_and_broker_anchor_regression_fail_closed(self) -> None:
        source = base_position()
        genesis = lifecycle_projection(source, revision=0, previous_id=None, kind="GENESIS", event=None, lifecycle_state="OPEN_UNPROTECTED", interpreted_at="2026-08-24T07:00:20Z")
        self.journal.persist_position_projection(genesis)
        gap = lifecycle_projection(source, revision=2, previous_id=genesis["lifecycle_projection_id"], kind="TRANSITION", event="EXIT_REQUESTED", lifecycle_state="EXIT_REQUESTED", interpreted_at="2026-08-24T07:00:22Z")
        with self.assertRaises(RuntimeConflictError):
            self.journal.persist_position_projection(gap)

        protected = lifecycle_projection(source, revision=1, previous_id=genesis["lifecycle_projection_id"], kind="TRANSITION", event="PROTECTION_VERIFIED", lifecycle_state="OPEN_PROTECTED", interpreted_at="2026-08-24T07:00:21Z")
        self.journal.persist_position_projection(protected)
        wrong_previous = lifecycle_projection(source, revision=2, previous_id=genesis["lifecycle_projection_id"], kind="TRANSITION", event="EXIT_REQUESTED", lifecycle_state="EXIT_REQUESTED", interpreted_at="2026-08-24T07:00:22Z")
        with self.assertRaises(RuntimeConflictError):
            self.journal.persist_position_projection(wrong_previous)

        older = base_position(observed_at="2026-08-24T07:00:19Z", lifecycle="OPEN_PROTECTED")
        regression = lifecycle_projection(older, revision=2, previous_id=protected["lifecycle_projection_id"], kind="REATTESTATION", event=None, lifecycle_state="OPEN_PROTECTED", interpreted_at="2026-08-24T07:00:23Z")
        with self.assertRaises(RuntimeConflictError):
            self.journal.persist_position_projection(regression)

    def test_stale_exact_lifecycle_replay_never_replaces_current(self) -> None:
        graph = self._persist_open_protection_graph()
        replay = self.journal.persist_position_projection(graph["genesis"])
        self.assertEqual(graph["genesis"], replay.payload)
        recovery = self.journal.recover(position_id="position-e6-paper-001")
        self.assertEqual(1, recovery.current_position_projection.payload["lifecycle_revision"])

    def test_newer_raw_broker_observation_requires_e5_reattestation_without_synthetic_position(self) -> None:
        self._persist_open_protection_graph()
        newer_raw = base_position(observed_at="2026-08-24T07:00:40Z", quantity="0.0010", lifecycle="OPEN_PROTECTED")
        self.journal.persist_raw_position_observation(newer_raw)
        recovery = self.journal.recover(position_id="position-e6-paper-001")
        self.assertEqual("REATTESTATION_REQUIRED", recovery.status)
        self.assertIn("E5_REATTESTATION_REQUIRED", recovery.reason_codes)
        self.assertEqual("2026-08-24T07:00:20Z", recovery.current_position_projection.payload["broker_state_observed_at"])
        self.assertEqual(newer_raw, recovery.raw_position_observations[-1].payload)

    def test_legacy_unprofiled_position_never_becomes_restart_authoritative_by_row_order(self) -> None:
        self._persist_core()
        self.journal.persist_raw_position_observation(base_position())
        recovery = self.journal.recover(trade_plan_id="plan-e6-paper-001")
        self.assertEqual("INCOMPLETE", recovery.status)
        self.assertIsNone(recovery.current_position_projection)

    def test_order_result_history_advances_by_authoritative_time_and_stale_does_not_regress(self) -> None:
        self._persist_core()
        self.journal.persist_position_action(protect_action())
        self.journal.persist_order_request(order_request())
        first = order_result(observed_at="2026-08-24T07:00:20Z", status="OPEN")
        later = order_result(observed_at="2026-08-24T07:00:30Z", status="PARTIALLY_FILLED", filled="0.0004")
        stale = order_result(observed_at="2026-08-24T07:00:25Z", status="OPEN")
        for payload in (first, later, stale):
            self.journal.persist_order_result(payload)
        self.journal.persist_position_projection(lifecycle_projection(base_position(), revision=0, previous_id=None, kind="GENESIS", event=None, lifecycle_state="OPEN_UNPROTECTED", interpreted_at="2026-08-24T07:00:20Z"))
        recovery = self.journal.recover(position_id="position-e6-paper-001")
        self.assertEqual("2026-08-24T07:00:30Z", recovery.current_order_results[0].payload["observed_at"])
        self.assertEqual("PARTIALLY_FILLED", recovery.current_order_results[0].payload["order_status"])
        self.assertEqual(3, len(recovery.order_result_observations))

    def test_equal_time_conflicting_order_result_fails_closed(self) -> None:
        self._persist_core()
        self.journal.persist_position_action(protect_action())
        self.journal.persist_order_request(order_request())
        first = order_result()
        self.journal.persist_order_result(first)
        conflict = order_result(status="FILLED", filled="0.0012")
        with self.assertRaises(RuntimeConflictError):
            self.journal.persist_order_result(conflict)

    def test_funding_replay_calculated_at_and_same_lineage_conflict_rules(self) -> None:
        self._persist_core()
        first = funding_evidence()
        stored = self.journal.persist_funding_evidence(first)
        self.assertEqual(first, stored.payload)
        self.assertEqual(first, self.journal.persist_funding_evidence(first).payload)
        later_observation = funding_evidence(calculated_at="2026-08-24T07:01:20Z")
        self.assertEqual(first["funding_evidence_id"], later_observation["funding_evidence_id"])
        replay = self.journal.persist_funding_evidence(later_observation)
        self.assertEqual(first, replay.payload)

        conflict = funding_evidence(source_material_hash="sha256:changed-source")
        self.assertNotEqual(first["funding_evidence_id"], conflict["funding_evidence_id"])
        with self.assertRaises(RuntimeConflictError):
            self.journal.persist_funding_evidence(conflict)

    def test_trade_result_is_immutable_and_retains_exact_funding_binding(self) -> None:
        self._persist_core()
        funding = funding_evidence()
        self.journal.persist_funding_evidence(funding)
        result = trade_result(funding)
        stored = self.journal.persist_trade_result(result)
        self.assertEqual(result, stored.payload)
        self.assertEqual(result, self.journal.persist_trade_result(result).payload)
        changed = dict(result)
        changed["net_pnl"] = "999"
        with self.assertRaises(RuntimeConflictError):
            self.journal.persist_trade_result(changed)
        self.assertEqual(funding["funding_evidence_id"], stored.payload["funding_evidence_id"])

    def test_close_reopen_recovers_exact_open_partial_fill_graph(self) -> None:
        graph = self._persist_open_protection_graph()
        self.journal.close()
        self.journal = open_paper_runtime_journal(self.db_path)
        recovery = self.journal.recover(position_id="position-e6-paper-001")
        self.assertEqual("READY", recovery.status)
        self.assertEqual(graph["protected"], recovery.current_position_projection.payload)
        self.assertEqual(graph["action"], recovery.position_actions[0].payload)
        self.assertEqual(graph["request"], recovery.order_requests[0].payload)
        self.assertEqual("PARTIALLY_FILLED", recovery.current_order_results[0].payload["order_status"])
        self.assertEqual("0.0004", recovery.fills[0].payload["quantity"])

    def test_close_reopen_preserves_reconciliation_required_truth(self) -> None:
        self._persist_open_protection_graph(ambiguous=True)
        self.journal.close()
        self.journal = open_paper_runtime_journal(self.db_path)
        recovery = self.journal.recover(position_id="position-e6-paper-001")
        self.assertEqual("RECONCILIATION_REQUIRED", recovery.status)
        self.assertEqual("RECONCILIATION_REQUIRED", recovery.current_order_results[0].payload["order_status"])
        self.assertEqual("DEGRADED", recovery.current_order_results[0].payload["execution_health_status"])

    def test_close_reopen_recovers_exact_closed_projection_funding_and_trade_result(self) -> None:
        self._persist_core()
        source = base_position(lifecycle="OPEN_PROTECTED")
        genesis = lifecycle_projection(source, revision=0, previous_id=None, kind="GENESIS", event=None, lifecycle_state="OPEN_PROTECTED", interpreted_at="2026-08-24T07:00:20Z")
        exit_requested = lifecycle_projection(source, revision=1, previous_id=genesis["lifecycle_projection_id"], kind="TRANSITION", event="EXIT_REQUESTED", lifecycle_state="EXIT_REQUESTED", interpreted_at="2026-08-24T07:00:21Z")
        flat = base_position(observed_at="2026-08-24T07:00:50Z", quantity="0", lifecycle="CLOSED", closed_at="2026-08-24T07:00:50Z")
        closed = lifecycle_projection(flat, revision=2, previous_id=exit_requested["lifecycle_projection_id"], kind="TRANSITION", event="POSITION_CLOSED", lifecycle_state="CLOSED", interpreted_at="2026-08-24T07:00:51Z")
        for projection in (genesis, exit_requested, closed):
            self.journal.persist_position_projection(projection)
        action = protect_action()
        self.journal.persist_position_action(action)
        request = order_request()
        self.journal.persist_order_request(request)
        self.journal.persist_order_result(order_result(observed_at="2026-08-24T07:00:40Z", status="FILLED", filled="0.0012"))
        self.journal.persist_fill(fill())
        funding = funding_evidence()
        self.journal.persist_funding_evidence(funding)
        result = trade_result(funding)
        self.journal.persist_trade_result(result)
        self.journal.close()
        self.journal = open_paper_runtime_journal(self.db_path)
        recovery = self.journal.recover(position_id="position-e6-paper-001")
        self.assertEqual("READY", recovery.status)
        self.assertEqual(closed, recovery.current_position_projection.payload)
        self.assertEqual(funding, recovery.funding_evidence[0].payload)
        self.assertEqual(result, recovery.trade_result.payload)
        self.assertEqual(funding["funding_evidence_id"], recovery.trade_result.payload["funding_evidence_id"])

    def test_conflicting_runtime_graph_recovers_fail_closed(self) -> None:
        self._persist_open_protection_graph()
        conflicting_action = protect_action()
        self.journal.persist_position_action(conflicting_action)
        conflicting_action["quantity"] = "0.0009"
        with self.assertRaises(RuntimeConflictError):
            self.journal.persist_position_action(conflicting_action)
        recovery = self.journal.recover(position_id="position-e6-paper-001")
        self.assertEqual("CONFLICT", recovery.status)
        self.assertIn("UNRESOLVED_DURABLE_CONFLICT", recovery.reason_codes)

    def test_atomic_projection_write_rolls_back_when_current_index_update_fails(self) -> None:
        source = base_position()
        genesis = lifecycle_projection(source, revision=0, previous_id=None, kind="GENESIS", event=None, lifecycle_state="OPEN_UNPROTECTED", interpreted_at="2026-08-24T07:00:20Z")
        self.journal.persist_position_projection(genesis)
        blocker = sqlite3.connect(self.db_path)
        try:
            blocker.executescript(
                """
                CREATE TRIGGER fail_test_current_projection_update
                BEFORE UPDATE ON paper_position_current_projection
                BEGIN
                    SELECT RAISE(ABORT, 'synthetic local-test rollback trigger');
                END;
                """
            )
            blocker.commit()
        finally:
            blocker.close()
        transition = lifecycle_projection(source, revision=1, previous_id=genesis["lifecycle_projection_id"], kind="TRANSITION", event="PROTECTION_VERIFIED", lifecycle_state="OPEN_PROTECTED", interpreted_at="2026-08-24T07:00:21Z")
        with self.assertRaises(sqlite3.DatabaseError):
            self.journal.persist_position_projection(transition)
        inspect = sqlite3.connect(self.db_path)
        try:
            rows = inspect.execute(
                "SELECT lifecycle_revision FROM paper_position_lifecycle_projections WHERE position_id = ? ORDER BY lifecycle_revision",
                ("position-e6-paper-001",),
            ).fetchall()
            current = inspect.execute(
                "SELECT lifecycle_revision FROM paper_position_current_projection WHERE position_id = ?",
                ("position-e6-paper-001",),
            ).fetchone()
            self.assertEqual([(0,)], rows)
            self.assertEqual((0,), current)
        finally:
            inspect.close()

    def test_secret_like_fields_and_release_authority_are_not_persisted(self) -> None:
        bad = risk_decision()
        bad["api_key"] = "fake-but-forbidden"
        with self.assertRaises(RuntimeValidationError):
            self.journal.persist_risk_decision(bad)
        public_methods = set(dir(self.journal))
        for forbidden in ("enable_paper", "approve", "go_live", "enable_live", "submit_provider_order"):
            self.assertNotIn(forbidden, public_methods)


if __name__ == "__main__":
    unittest.main()
