from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from storage._lifecycle_execution_binding import recompute_position_linked_execution_snapshot
from storage.runtime import RuntimeConflictError, RuntimeValidationError, open_paper_runtime_journal
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


def _binding_id(payload: dict) -> str:
    material = dict(payload)
    material.pop("lifecycle_execution_binding_id", None)
    return "posexecbind_" + hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def entry_order_request() -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "order_request_id": "ordreq-entry-e6-001",
        "trade_plan_id": "plan-e6-paper-001",
        "client_order_id": "client-entry-e6-001",
        "symbol": "BTC_USDT_PERP",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": "0.0012",
        "quantity_profile_version": "base-asset-v0.1",
        "quantity_unit": "BASE_ASSET",
        "quantity_asset": "BTC",
        "created_at": "2026-08-24T07:00:05Z",
        "authorization_type": None,
        "position_action_id": None,
        "position_id": None,
        "risk_decision_id": None,
        "order_role": None,
        "limit_price": None,
        "stop_price": None,
        "reduce_only": False,
        "time_in_force": None,
    }


def entry_fill() -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "fill_id": "fill-entry-e6-001",
        "broker_order_id": "paper-entry-e6-001",
        "client_order_id": "client-entry-e6-001",
        "trade_plan_id": "plan-e6-paper-001",
        "symbol": "BTC_USDT_PERP",
        "side": "BUY",
        "quantity": "0.0012",
        "price": "60000",
        "filled_at": "2026-08-24T07:00:10Z",
        "fee": "0.01",
        "fee_currency": "USDT",
        "liquidity_role": "TAKER",
        "position_action_id": None,
        "position_id": None,
        "order_role": None,
    }


def reduction_action(*, action_id: str, action: str, observed_at: str = "2026-08-24T07:00:20Z") -> dict:
    result = dict(protect_action())
    result["position_action_id"] = action_id
    result["action"] = action
    result["position_observed_at"] = observed_at
    if action in {"EXIT", "EMERGENCY_EXIT"}:
        result.pop("protection_profile_version", None)
        result.pop("protection_instruction", None)
        result["close_profile_version"] = "close-v0.1"
        result["strategy_id"] = "strategy-e6-paper"
        result["strategy_version"] = "1.0.0"
        result["source_lifecycle_state"] = "OPEN_PROTECTED" if action == "EXIT" else "EMERGENCY"
        result["close_order_type"] = "MARKET"
        result["reason_codes"] = ["E5_EXIT_REQUIRED"]
    return result


def reduction_request(*, request_id: str, client_id: str, action_id: str, role: str) -> dict:
    result = order_request(request_id=request_id, client_id=client_id, role=role)
    result["position_action_id"] = action_id
    result["stop_price"] = "59400" if role == "PROTECTION_STOP" else None
    result["order_type"] = "STOP_MARKET" if role == "PROTECTION_STOP" else "MARKET"
    return result


def request_result(request: dict, *, observed_at: str, status: str, filled: str = "0", broker_id: str | None = None) -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "order_request_id": request["order_request_id"],
        "client_order_id": request["client_order_id"],
        "broker_order_id": broker_id,
        "order_status": status,
        "observed_at": observed_at,
        "execution_health_status": "HEALTHY",
        "requested_quantity": request["quantity"],
        "filled_quantity": filled,
        "average_fill_price": None,
        "reject_reason": None,
    }


def request_fill(request: dict, *, fill_id: str, filled_at: str, quantity: str = "0.0012") -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "fill_id": fill_id,
        "broker_order_id": "paper-" + request["order_request_id"],
        "client_order_id": request["client_order_id"],
        "trade_plan_id": request["trade_plan_id"],
        "symbol": request["symbol"],
        "side": request["side"],
        "quantity": quantity,
        "price": "59400",
        "filled_at": filled_at,
        "fee": "0.01",
        "fee_currency": "USDT",
        "liquidity_role": "TAKER",
        "position_action_id": request["position_action_id"],
        "position_id": request["position_id"],
        "order_role": request["order_role"],
    }


class BindingAndTradeResultCompletenessDefinitions(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "paper-runtime.sqlite3"
        self.journal = open_paper_runtime_journal(self.db_path)
        self.journal.persist_risk_decision(risk_decision())
        self.journal.persist_approved_trade_plan(approved_plan())

    def tearDown(self) -> None:
        try:
            self.journal.close()
        except sqlite3.Error:
            pass
        self.temp.cleanup()

    def _project_open_protected(self) -> tuple[dict, dict]:
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
        return genesis, protected

    def _binding_for(self, projection: dict) -> dict:
        snapshot = recompute_position_linked_execution_snapshot(
            self.journal._store,
            projection["position_id"],
        )
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

    def _persist_protection_execution(self, *, result_status: str = "OPEN", filled: str = "0") -> tuple[dict, dict, dict]:
        action = protect_action()
        request = order_request()
        self.journal.persist_position_action(action)
        self.journal.persist_order_request(request)
        result = order_result(
            observed_at="2026-08-24T07:00:22Z",
            status=result_status,
            filled=filled,
            broker_id="paper-e6-order-001",
        )
        self.journal.persist_order_result(result)
        return action, request, result

    def _persist_exact_current_binding(self) -> tuple[dict, dict]:
        _, protected = self._project_open_protected()
        self._persist_protection_execution()
        binding = self._binding_for(protected)
        self.journal.persist_lifecycle_execution_binding(binding)
        return protected, binding

    def _persist_closed_complete_graph(self) -> tuple[dict, dict, dict]:
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

        entry_request = entry_order_request()
        self.journal.persist_order_request(entry_request)
        self.journal.persist_fill(entry_fill())

        action = protect_action()
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

        binding = self._binding_for(closed)
        self.journal.persist_lifecycle_execution_binding(binding)
        funding = funding_evidence()
        self.journal.persist_funding_evidence(funding)
        result = trade_result(funding)
        self.journal.persist_trade_result(result)
        return closed, binding, result

    def test_exact_matching_binding_keeps_execution_freshness_axis_current(self) -> None:
        projection, binding = self._persist_exact_current_binding()
        recovery = self.journal.recover(position_id=projection["position_id"])
        self.assertEqual("READY", recovery.status)
        self.assertEqual(binding, recovery.current_lifecycle_execution_binding.payload)
        self.assertNotIn("E5_EXECUTION_REINTERPRETATION_REQUIRED", recovery.reason_codes)

    def test_binding_absent_is_not_ready(self) -> None:
        _, protected = self._project_open_protected()
        self._persist_protection_execution()
        recovery = self.journal.recover(position_id=protected["position_id"])
        self.assertNotEqual("READY", recovery.status)
        self.assertIn("LIFECYCLE_EXECUTION_BINDING_MISSING", recovery.reason_codes)

    def test_binding_projection_revision_time_profile_scope_and_hash_mismatch_fail_closed(self) -> None:
        _, protected = self._project_open_protected()
        self._persist_protection_execution()
        base = self._binding_for(protected)
        cases = (
            ("lifecycle_projection_id", "posproj_" + "0" * 64),
            ("lifecycle_revision", 99),
            ("execution_interpreted_at", "2026-08-24T07:00:22Z"),
            ("lifecycle_execution_binding_profile_version", "unsupported-binding-v9"),
            ("execution_scope", "UNSUPPORTED_SCOPE"),
            ("execution_snapshot_hash", "sha256:" + "0" * 64),
        )
        for field, value in cases:
            with self.subTest(field=field):
                payload = dict(base)
                payload[field] = value
                payload["lifecycle_execution_binding_id"] = _binding_id(payload)
                with self.assertRaises(RuntimeValidationError):
                    self.journal.persist_lifecycle_execution_binding(payload)
        recovery = self.journal.recover(position_id=protected["position_id"])
        self.assertNotEqual("READY", recovery.status)

    def test_later_partial_or_filled_protection_truth_requires_fresh_e5_interpretation(self) -> None:
        projection, _ = self._persist_exact_current_binding()
        for index, status in enumerate(("PARTIALLY_FILLED", "FILLED"), start=1):
            with self.subTest(status=status):
                if index > 1:
                    # Use a fresh database because terminal FILLED cannot be meaningfully
                    # compared to the earlier subcase without adding unrelated semantics.
                    self.journal.close()
                    self.temp.cleanup()
                    self.temp = tempfile.TemporaryDirectory()
                    self.db_path = Path(self.temp.name) / "paper-runtime.sqlite3"
                    self.journal = open_paper_runtime_journal(self.db_path)
                    self.journal.persist_risk_decision(risk_decision())
                    self.journal.persist_approved_trade_plan(approved_plan())
                    projection, _ = self._persist_exact_current_binding()
                self.journal.persist_order_result(
                    order_result(
                        observed_at=f"2026-08-24T07:00:2{index + 2}Z",
                        status=status,
                        filled="0.0004" if status == "PARTIALLY_FILLED" else "0.0012",
                        broker_id="paper-e6-order-001",
                    )
                )
                if status == "FILLED":
                    self.journal.persist_fill(fill())
                recovery = self.journal.recover(position_id=projection["position_id"])
                self.assertNotEqual("READY", recovery.status)
                self.assertIn("E5_EXECUTION_REINTERPRETATION_REQUIRED", recovery.reason_codes)

    def test_later_canceled_expired_or_rejected_protection_truth_requires_reinterpretation(self) -> None:
        for index, status in enumerate(("CANCELED", "EXPIRED", "REJECTED"), start=1):
            with self.subTest(status=status):
                if index > 1:
                    self.journal.close()
                    self.temp.cleanup()
                    self.temp = tempfile.TemporaryDirectory()
                    self.db_path = Path(self.temp.name) / "paper-runtime.sqlite3"
                    self.journal = open_paper_runtime_journal(self.db_path)
                    self.journal.persist_risk_decision(risk_decision())
                    self.journal.persist_approved_trade_plan(approved_plan())
                projection, _ = self._persist_exact_current_binding()
                self.journal.persist_order_result(
                    order_result(
                        observed_at=f"2026-08-24T07:00:3{index}Z",
                        status=status,
                        filled="0",
                        broker_id="paper-e6-order-001",
                    )
                )
                recovery = self.journal.recover(position_id=projection["position_id"])
                self.assertIn("E5_EXECUTION_REINTERPRETATION_REQUIRED", recovery.reason_codes)
                self.assertNotEqual("READY", recovery.status)

    def test_new_exit_or_emergency_execution_evidence_invalidates_old_binding(self) -> None:
        for index, (action_name, role) in enumerate(
            (("EXIT", "POSITION_EXIT"), ("EMERGENCY_EXIT", "EMERGENCY_EXIT")),
            start=1,
        ):
            with self.subTest(role=role):
                if index > 1:
                    self.journal.close()
                    self.temp.cleanup()
                    self.temp = tempfile.TemporaryDirectory()
                    self.db_path = Path(self.temp.name) / "paper-runtime.sqlite3"
                    self.journal = open_paper_runtime_journal(self.db_path)
                    self.journal.persist_risk_decision(risk_decision())
                    self.journal.persist_approved_trade_plan(approved_plan())
                projection, _ = self._persist_exact_current_binding()
                action = reduction_action(action_id=f"posact-e6-{index}", action=action_name)
                request = reduction_request(
                    request_id=f"ordreq-e6-{index}",
                    client_id=f"client-e6-{index}",
                    action_id=action["position_action_id"],
                    role=role,
                )
                self.journal.persist_position_action(action)
                self.journal.persist_order_request(request)
                self.journal.persist_order_result(
                    request_result(
                        request,
                        observed_at=f"2026-08-24T07:00:4{index}Z",
                        status="OPEN",
                        broker_id=f"paper-exit-{index}",
                    )
                )
                recovery = self.journal.recover(position_id=projection["position_id"])
                self.assertIn("E5_EXECUTION_REINTERPRETATION_REQUIRED", recovery.reason_codes)

    def test_binding_duplicate_replay_is_idempotent(self) -> None:
        _, binding = self._persist_exact_current_binding()
        first = self.journal.persist_lifecycle_execution_binding(binding)
        second = self.journal.persist_lifecycle_execution_binding(binding)
        self.assertEqual(first.payload_hash, second.payload_hash)
        self.assertEqual(binding, second.payload)

    def test_execution_identity_conflicts_remain_fail_closed(self) -> None:
        projection, _ = self._persist_exact_current_binding()
        changed_result = order_result(status="FILLED", filled="0.0012", broker_id="paper-e6-order-001")
        with self.assertRaises(RuntimeConflictError):
            self.journal.persist_order_result(changed_result)

        original_fill = fill()
        self.journal.persist_fill(original_fill)
        changed_fill = dict(original_fill)
        changed_fill["price"] = "59000"
        with self.assertRaises(RuntimeConflictError):
            self.journal.persist_fill(changed_fill)

        changed_request = order_request()
        changed_request["quantity"] = "0.0011"
        with self.assertRaises(RuntimeConflictError):
            self.journal.persist_order_request(changed_request)

        recovery = self.journal.recover(position_id=projection["position_id"])
        self.assertEqual("CONFLICT", recovery.status)

    def test_equal_anchor_reattestation_with_new_matching_binding_restores_execution_freshness(self) -> None:
        _, protected = self._project_open_protected()
        self._persist_protection_execution()
        self.journal.persist_lifecycle_execution_binding(self._binding_for(protected))
        self.journal.persist_order_result(
            order_result(
                observed_at="2026-08-24T07:00:30Z",
                status="PARTIALLY_FILLED",
                filled="0.0004",
                broker_id="paper-e6-order-001",
            )
        )
        stale = self.journal.recover(position_id=protected["position_id"])
        self.assertIn("E5_EXECUTION_REINTERPRETATION_REQUIRED", stale.reason_codes)

        source = base_position(lifecycle="OPEN_PROTECTED")
        reattested = lifecycle_projection(
            source,
            revision=2,
            previous_id=protected["lifecycle_projection_id"],
            kind="REATTESTATION",
            event=None,
            lifecycle_state="OPEN_PROTECTED",
            interpreted_at="2026-08-24T07:00:31Z",
        )
        self.journal.persist_position_projection(reattested)
        new_binding = self._binding_for(reattested)
        self.journal.persist_lifecycle_execution_binding(new_binding)
        recovery = self.journal.recover(position_id=reattested["position_id"])
        self.assertEqual("READY", recovery.status)
        self.assertNotIn("E5_EXECUTION_REINTERPRETATION_REQUIRED", recovery.reason_codes)

    def test_newer_raw_position_remains_independently_reattestation_required(self) -> None:
        projection, _ = self._persist_exact_current_binding()
        newer = base_position(
            observed_at="2026-08-24T07:00:40Z",
            quantity="0.0011",
            lifecycle="OPEN_PROTECTED",
        )
        self.journal.persist_raw_position_observation(newer)
        recovery = self.journal.recover(position_id=projection["position_id"])
        self.assertEqual("REATTESTATION_REQUIRED", recovery.status)
        self.assertIn("E5_REATTESTATION_REQUIRED", recovery.reason_codes)

    def test_entry_execution_is_outside_binding_scope_and_not_joined_by_trade_plan(self) -> None:
        _, protected = self._project_open_protected()
        entry_request = entry_order_request()
        self.journal.persist_order_request(entry_request)
        self.journal.persist_fill(entry_fill())
        binding = self._binding_for(protected)
        self.assertEqual([], binding["order_evidence"])
        self.journal.persist_lifecycle_execution_binding(binding)
        recovery = self.journal.recover(position_id=protected["position_id"])
        self.assertEqual("READY", recovery.status)

    def test_complete_trade_result_reference_graph_can_recover_normally(self) -> None:
        closed, binding, result = self._persist_closed_complete_graph()
        self.journal.close()
        self.journal = open_paper_runtime_journal(self.db_path)
        recovery = self.journal.recover(position_id=closed["position_id"])
        self.assertEqual("READY", recovery.status)
        self.assertEqual(binding, recovery.current_lifecycle_execution_binding.payload)
        self.assertEqual(result, recovery.trade_result.payload)

    def test_missing_trade_result_referenced_objects_are_rejected_and_not_ready(self) -> None:
        cases = (
            ("entry_order_request_ids", ["missing-entry-request"]),
            ("exit_order_request_ids", ["missing-exit-request"]),
            ("entry_fill_ids", ["missing-entry-fill"]),
            ("exit_fill_ids", ["missing-exit-fill"]),
            (
                "exit_authority_refs",
                [{
                    "position_action_id": "missing-action",
                    "position_id": "position-e6-paper-001",
                    "action": "PROTECT",
                    "order_role": "PROTECTION_STOP",
                }],
            ),
        )
        for index, (field, value) in enumerate(cases):
            with self.subTest(field=field):
                if index:
                    self.journal.close()
                    self.temp.cleanup()
                    self.temp = tempfile.TemporaryDirectory()
                    self.db_path = Path(self.temp.name) / "paper-runtime.sqlite3"
                    self.journal = open_paper_runtime_journal(self.db_path)
                    self.journal.persist_risk_decision(risk_decision())
                    self.journal.persist_approved_trade_plan(approved_plan())
                source = base_position(lifecycle="OPEN_PROTECTED")
                closed_source = base_position(
                    observed_at="2026-08-24T07:00:50Z",
                    quantity="0",
                    lifecycle="CLOSED",
                    closed_at="2026-08-24T07:00:50Z",
                )
                genesis = lifecycle_projection(source, revision=0, previous_id=None, kind="GENESIS", event=None, lifecycle_state="OPEN_PROTECTED", interpreted_at="2026-08-24T07:00:20Z")
                closed = lifecycle_projection(closed_source, revision=1, previous_id=genesis["lifecycle_projection_id"], kind="TRANSITION", event="POSITION_CLOSED", lifecycle_state="CLOSED", interpreted_at="2026-08-24T07:00:51Z")
                self.journal.persist_position_projection(genesis)
                self.journal.persist_position_projection(closed)
                self.journal.persist_order_request(entry_order_request())
                self.journal.persist_fill(entry_fill())
                self.journal.persist_position_action(protect_action())
                self.journal.persist_order_request(order_request())
                self.journal.persist_order_result(order_result(observed_at="2026-08-24T07:00:40Z", status="FILLED", filled="0.0012", broker_id="paper-e6-order-001"))
                self.journal.persist_fill(fill())
                self.journal.persist_lifecycle_execution_binding(self._binding_for(closed))
                funding = funding_evidence()
                self.journal.persist_funding_evidence(funding)
                result = trade_result(funding)
                result[field] = value
                with self.assertRaises(RuntimeValidationError):
                    self.journal.persist_trade_result(result)
                recovery = self.journal.recover(position_id=closed["position_id"])
                self.assertNotEqual("READY", recovery.status)
                self.assertIsNone(recovery.trade_result)

    def test_trade_result_reference_lineage_mismatch_fails_closed(self) -> None:
        source = base_position(lifecycle="OPEN_PROTECTED")
        closed_source = base_position(observed_at="2026-08-24T07:00:50Z", quantity="0", lifecycle="CLOSED", closed_at="2026-08-24T07:00:50Z")
        genesis = lifecycle_projection(source, revision=0, previous_id=None, kind="GENESIS", event=None, lifecycle_state="OPEN_PROTECTED", interpreted_at="2026-08-24T07:00:20Z")
        closed = lifecycle_projection(closed_source, revision=1, previous_id=genesis["lifecycle_projection_id"], kind="TRANSITION", event="POSITION_CLOSED", lifecycle_state="CLOSED", interpreted_at="2026-08-24T07:00:51Z")
        self.journal.persist_position_projection(genesis)
        self.journal.persist_position_projection(closed)
        self.journal.persist_order_request(entry_order_request())
        self.journal.persist_fill(entry_fill())
        self.journal.persist_position_action(protect_action())
        self.journal.persist_order_request(order_request())
        self.journal.persist_fill(fill())
        self.journal.persist_lifecycle_execution_binding(self._binding_for(closed))
        funding = funding_evidence()
        self.journal.persist_funding_evidence(funding)
        result = trade_result(funding)
        result["exit_authority_refs"] = [{
            "position_action_id": "posact-e6-protect-001",
            "position_id": "position-e6-paper-001",
            "action": "EXIT",
            "order_role": "PROTECTION_STOP",
        }]
        with self.assertRaises(RuntimeValidationError):
            self.journal.persist_trade_result(result)


if __name__ == "__main__":
    unittest.main()
