from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from storage._lifecycle_execution_binding import recompute_position_linked_execution_snapshot
from storage.runtime import RuntimeValidationError, open_paper_runtime_journal
from test_paper_runtime_binding_and_traderesult_completeness import (
    entry_fill,
    entry_order_request,
    reduction_action,
    reduction_request,
    request_fill,
)
from test_paper_runtime_durability import (
    approved_plan,
    base_position,
    fill,
    funding_evidence,
    lifecycle_projection,
    order_request,
    order_result,
    protect_action,
    risk_decision,
    trade_result,
)


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha256_json(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _binding_id(payload: dict) -> str:
    material = dict(payload)
    material.pop("lifecycle_execution_binding_id", None)
    return "posexecbind_" + hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def _binding_for(journal, projection: dict) -> dict:
    snapshot = recompute_position_linked_execution_snapshot(journal._store, projection["position_id"])
    payload = {
        "schema_version": "contracts-v0.1",
        "lifecycle_execution_binding_profile_version": "position-lifecycle-execution-binding-v0.1",
        "position_id": projection["position_id"],
        "lifecycle_projection_id": projection["lifecycle_projection_id"],
        "lifecycle_revision": projection["lifecycle_revision"],
        "execution_interpreted_at": projection["lifecycle_interpreted_at"],
        "execution_scope": "POSITION_LINKED_REDUCTION_ORDERS_V0_1",
        "order_evidence": snapshot["order_evidence"],
        "execution_snapshot_hash": snapshot["execution_snapshot_hash"],
    }
    payload["lifecycle_execution_binding_id"] = _binding_id(payload)
    return payload


class TradeResultReferenceRemediationDefinitions(unittest.TestCase):
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

    def _persist_core(self) -> None:
        self.journal.persist_risk_decision(risk_decision())
        self.journal.persist_approved_trade_plan(approved_plan())

    def _persist_closed_projection(self) -> dict:
        source = base_position(lifecycle="OPEN_PROTECTED")
        genesis = lifecycle_projection(
            source,
            revision=0,
            previous_id=None,
            kind="GENESIS",
            event=None,
            lifecycle_state="OPEN_PROTECTED",
            interpreted_at="2026-08-24T07:00:20Z",
        )
        flat = base_position(
            observed_at="2026-08-24T07:00:50Z",
            quantity="0",
            lifecycle="CLOSED",
            closed_at="2026-08-24T07:00:50Z",
        )
        closed = lifecycle_projection(
            flat,
            revision=1,
            previous_id=genesis["lifecycle_projection_id"],
            kind="TRANSITION",
            event="POSITION_CLOSED",
            lifecycle_state="CLOSED",
            interpreted_at="2026-08-24T07:00:51Z",
        )
        self.journal.persist_position_projection(genesis)
        self.journal.persist_position_projection(closed)
        return closed

    def _persist_entry(self) -> None:
        self.journal.persist_order_request(entry_order_request())
        self.journal.persist_fill(entry_fill())

    def _persist_protection_exit(self, action: dict | None = None) -> tuple[dict, dict]:
        action = protect_action() if action is None else action
        request = order_request()
        self.journal.persist_position_action(action)
        self.journal.persist_order_request(request)
        self.journal.persist_order_result(
            order_result(
                observed_at="2026-08-24T07:00:40Z",
                status="FILLED",
                filled="0.0012",
                broker_id="paper-e6-order-001",
            )
        )
        self.journal.persist_fill(fill())
        return action, request

    def _persist_complete_closed_prerequisites(self, action: dict | None = None) -> dict:
        self._persist_core()
        closed = self._persist_closed_projection()
        self._persist_entry()
        self._persist_protection_exit(action)
        binding = _binding_for(self.journal, closed)
        self.journal.persist_lifecycle_execution_binding(binding)
        funding = funding_evidence()
        self.journal.persist_funding_evidence(funding)
        return trade_result(funding)

    def _persist_complete_closed_graph(self) -> dict:
        result = self._persist_complete_closed_prerequisites()
        self.journal.persist_trade_result(result)
        return result

    def _direct_insert_legacy_trade_result(self, payload: dict) -> None:
        """Represent pre-remediation durable material without mutating canonical rows.

        The production immutability triggers remain installed and untouched.  A
        legacy invalid TradeResult is introduced only as an INSERT fixture so
        recovery can prove that already-durable historical material fails closed.
        """

        payload_json = _canonical_json(payload)
        payload_hash = _sha256_json(payload)
        self.journal._store._connection.execute(
            """
            INSERT INTO paper_trade_results (
                trade_result_id, trade_plan_id, position_id,
                strategy_id, strategy_version, funding_evidence_id,
                payload_json, payload_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["trade_result_id"],
                payload["trade_plan_id"],
                payload["position_id"],
                payload["strategy_id"],
                payload["strategy_version"],
                payload["funding_evidence_id"],
                payload_json,
                payload_hash,
            ),
        )
        self.journal._store._connection.commit()

    def test_valid_complete_closed_graph_remains_definition_compatible(self) -> None:
        result = self._persist_complete_closed_graph()
        recovery = self.journal.recover(position_id="position-e6-paper-001")
        self.assertEqual("READY", recovery.status)
        self.assertEqual(result, recovery.trade_result.payload)
        self.assertNotIn("TRADE_RESULT_REFERENCED_GRAPH_INVALID", recovery.reason_codes)

    def test_legacy_generic_invalid_trade_result_graph_cannot_recover_ready(self) -> None:
        result = self._persist_complete_closed_prerequisites()
        legacy = dict(result)
        legacy["entry_fill_ids"] = ["fill-entry-e6-001", "fill-entry-e6-001"]
        self._direct_insert_legacy_trade_result(legacy)

        recovery = self.journal.recover(position_id="position-e6-paper-001")
        self.assertNotEqual("READY", recovery.status)
        self.assertEqual("INCOMPLETE", recovery.status)
        self.assertIn("TRADE_RESULT_REFERENCED_GRAPH_INVALID", recovery.reason_codes)

    def test_referenced_protect_action_missing_required_policy_lineage_is_rejected(self) -> None:
        self._persist_core()
        self._persist_entry()
        action = protect_action()
        action.pop("risk_policy_version")
        self._persist_protection_exit(action)
        funding = funding_evidence()
        self.journal.persist_funding_evidence(funding)

        with self.assertRaises(RuntimeValidationError) as ctx:
            self.journal.persist_trade_result(trade_result(funding))
        self.assertEqual("TRADE_RESULT_POSITION_ACTION_LINEAGE_MISSING", ctx.exception.code)

    def test_referenced_close_action_missing_or_mismatched_required_lineage_is_rejected(self) -> None:
        cases = (
            ("EXIT", "POSITION_EXIT", "strategy_id", None),
            ("EMERGENCY_EXIT", "EMERGENCY_EXIT", "risk_policy_version", "wrong-policy"),
        )
        for index, (action_type, role, field, replacement) in enumerate(cases, start=1):
            with self.subTest(action=action_type, field=field):
                if index > 1:
                    self.journal.close()
                    self.temp.cleanup()
                    self.temp = tempfile.TemporaryDirectory()
                    self.db_path = Path(self.temp.name) / "paper-runtime.sqlite3"
                    self.journal = open_paper_runtime_journal(self.db_path)
                self._persist_core()
                self._persist_entry()
                action_id = f"posact-e6-{action_type.lower()}-018"
                action = reduction_action(action_id=action_id, action=action_type)
                if replacement is None:
                    action.pop(field)
                else:
                    action[field] = replacement
                self.journal.persist_position_action(action)
                request = reduction_request(
                    request_id=f"ordreq-e6-{action_type.lower()}-018",
                    client_id=f"client-e6-{action_type.lower()}-018",
                    action_id=action_id,
                    role=role,
                )
                self.journal.persist_order_request(request)
                exit_fill = request_fill(
                    request,
                    fill_id=f"fill-e6-{action_type.lower()}-018",
                    filled_at="2026-08-24T07:00:40Z",
                )
                self.journal.persist_fill(exit_fill)
                funding = funding_evidence()
                self.journal.persist_funding_evidence(funding)
                result = trade_result(funding)
                result["exit_fill_ids"] = [exit_fill["fill_id"]]
                result["exit_order_request_ids"] = [request["order_request_id"]]
                result["exit_authority_refs"] = [
                    {
                        "position_action_id": action_id,
                        "position_id": "position-e6-paper-001",
                        "action": action_type,
                        "order_role": role,
                    }
                ]

                with self.assertRaises(RuntimeValidationError) as ctx:
                    self.journal.persist_trade_result(result)
                expected = (
                    "TRADE_RESULT_POSITION_ACTION_LINEAGE_MISSING"
                    if replacement is None
                    else "TRADE_RESULT_POSITION_ACTION_LINEAGE_MISMATCH"
                )
                self.assertEqual(expected, ctx.exception.code)

    def test_recovered_position_action_lineage_mismatch_is_conflict(self) -> None:
        action = protect_action()
        action["risk_policy_version"] = "wrong-policy"
        result = self._persist_complete_closed_prerequisites(action)
        self._direct_insert_legacy_trade_result(result)

        recovery = self.journal.recover(position_id="position-e6-paper-001")
        self.assertEqual("CONFLICT", recovery.status)
        self.assertIn("TRADE_RESULT_POSITION_ACTION_LINEAGE_MISMATCH", recovery.reason_codes)

    def test_recovered_position_action_missing_lineage_is_non_ready_incomplete(self) -> None:
        action = protect_action()
        action.pop("risk_policy_version")
        result = self._persist_complete_closed_prerequisites(action)
        self._direct_insert_legacy_trade_result(result)

        recovery = self.journal.recover(position_id="position-e6-paper-001")
        self.assertNotEqual("READY", recovery.status)
        self.assertEqual("INCOMPLETE", recovery.status)
        self.assertIn("TRADE_RESULT_POSITION_ACTION_LINEAGE_MISSING", recovery.reason_codes)

    def test_production_canonical_rows_remain_immutable_during_legacy_fixture_recovery(self) -> None:
        result = self._persist_complete_closed_graph()
        with self.assertRaises(sqlite3.IntegrityError):
            self.journal._store._connection.execute(
                "UPDATE paper_trade_results SET payload_hash = 'sha256:forbidden' WHERE trade_result_id = ?",
                (result["trade_result_id"],),
            )
        self.journal._store._connection.rollback()
        with self.assertRaises(sqlite3.IntegrityError):
            self.journal._store._connection.execute(
                "UPDATE paper_runtime_objects SET payload_hash = 'sha256:forbidden' WHERE object_kind = 'POSITION_ACTION' AND canonical_id = ?",
                (protect_action()["position_action_id"],),
            )
        self.journal._store._connection.rollback()


if __name__ == "__main__":
    unittest.main()
