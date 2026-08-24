import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from position import (
    PositionEvent,
    PositionLifecycleState,
    ProtectionResultEvidence,
    build_position_lifecycle_genesis_with_execution_binding,
    build_position_lifecycle_transition_with_execution_binding,
    build_protect_position_action,
    interpret_protection_result,
)
from src.brokers.paper import PaperBroker
from src.execution.protection import prepare_protection_order
from storage.runtime import open_paper_runtime_journal


def _utc(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _decimal(value):
    return None if value is None else format(value, "f")


def _request_payload(request):
    return {
        "schema_version": request.schema_version,
        "order_request_id": request.order_request_id,
        "trade_plan_id": request.trade_plan_id,
        "client_order_id": request.client_order_id,
        "symbol": request.symbol,
        "side": request.side.value,
        "order_type": request.order_type,
        "quantity": _decimal(request.quantity),
        "quantity_profile_version": request.quantity_profile_version,
        "quantity_unit": request.quantity_unit,
        "quantity_asset": request.quantity_asset,
        "created_at": _utc(request.created_at),
        "authorization_type": request.authorization_type,
        "position_action_id": request.position_action_id,
        "position_id": request.position_id,
        "risk_decision_id": request.risk_decision_id,
        "order_role": request.order_role,
        "limit_price": _decimal(request.limit_price),
        "stop_price": _decimal(request.stop_price),
        "reduce_only": request.reduce_only,
        "time_in_force": request.time_in_force,
    }


def _result_payload(result):
    return {
        "schema_version": result.schema_version,
        "order_request_id": result.order_request_id,
        "client_order_id": result.client_order_id,
        "broker_order_id": result.broker_order_id,
        "order_status": result.order_status.value,
        "observed_at": _utc(result.observed_at),
        "execution_health_status": result.execution_health_status.value,
        "requested_quantity": _decimal(result.requested_quantity),
        "filled_quantity": _decimal(result.filled_quantity),
        "average_fill_price": _decimal(result.average_fill_price),
        "reject_reason": result.reject_reason,
    }


def _fill_payload(fill):
    return {
        "schema_version": fill.schema_version,
        "fill_id": fill.fill_id,
        "broker_order_id": fill.broker_order_id,
        "client_order_id": fill.client_order_id,
        "trade_plan_id": fill.trade_plan_id,
        "symbol": fill.symbol,
        "side": fill.side.value,
        "quantity": _decimal(fill.quantity),
        "price": _decimal(fill.price),
        "filled_at": _utc(fill.filled_at),
        "fee": _decimal(fill.fee),
        "fee_currency": fill.fee_currency,
        "liquidity_role": fill.liquidity_role,
        "position_action_id": fill.position_action_id,
        "position_id": fill.position_id,
        "order_role": fill.order_role,
    }


class GateBDurableLifecycleFreshnessDefinitions(unittest.TestCase):
    """Cross-module fail-closed restart freshness definitions.

    E7-20260824-057 updates the old E7-052 blocker definitions to consume the
    accepted E5 execution-binding producer and E6 binding consumer. These are
    NOT_RUN definitions; no result is asserted from execution in this task.
    """

    def setUp(self):
        self.t0 = datetime(2026, 8, 24, 7, 0, 20, tzinfo=timezone.utc)
        self.plan = {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-e7-durable-freshness-001",
            "risk_decision_id": "risk-e7-durable-freshness-001",
            "intent_id": "intent-e7-durable-freshness-001",
            "strategy_id": "strategy-e7-durable-freshness",
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
            "protection_instruction": {
                "stop_level": "59400",
                "target_level": "61200",
                "max_hold_seconds": 1800,
            },
            "created_at": "2026-08-24T06:59:00Z",
            "expires_at": "2026-08-24T07:00:05Z",
            "risk_policy_version": "e5-e7-durable-freshness-v0.1",
        }
        self.risk = {
            "schema_version": "contracts-v0.1",
            "risk_decision_id": self.plan["risk_decision_id"],
            "intent_id": self.plan["intent_id"],
            "strategy_id": self.plan["strategy_id"],
            "strategy_version": self.plan["strategy_version"],
            "decision": "APPROVE",
            "reason_codes": [],
            "risk_policy_version": self.plan["risk_policy_version"],
            "decided_at": "2026-08-24T06:59:00Z",
            "market_health_status": "HEALTHY",
            "account_state_status": "KNOWN",
            "position_state_status": "FLAT",
            "approved_quantity": "0.003",
            "approved_leverage": "20",
            "margin_mode": "ISOLATED",
            "required_stop_level": "59400",
            "max_hold_seconds": 1800,
        }
        self.position = {
            "schema_version": "contracts-v0.1",
            "position_id": "position-e7-durable-freshness-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": "0.0012",
            "average_entry_price": "60000",
            "opened_at": "2026-08-24T07:00:10Z",
            "broker_state_observed_at": _utc(self.t0),
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": "OPEN_UNPROTECTED",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }

    def _persist_composed(self, journal, composed):
        journal.persist_position_projection(composed.lifecycle_projection)
        journal.persist_lifecycle_execution_binding(composed.execution_binding)

    def _materialize_verified_graph(self, journal):
        journal.persist_risk_decision(self.risk)
        journal.persist_approved_trade_plan(self.plan)
        genesis = build_position_lifecycle_genesis_with_execution_binding(
            self.position,
            lifecycle_state=PositionLifecycleState.OPEN_UNPROTECTED,
            lifecycle_interpreted_at=self.t0,
            order_requests=(),
            order_results=(),
            fills=(),
        )
        self._persist_composed(journal, genesis)

        action = build_protect_position_action(
            self.position,
            self.plan,
            created_at=self.t0,
            expires_at=self.t0 + timedelta(seconds=60),
        )
        request = prepare_protection_order(action, self.plan, self.position, now=self.t0)
        broker = PaperBroker()
        submit = broker.submit_order(request)
        queried = broker.query_order(request.client_order_id)
        self.assertIsNotNone(queried)
        verified = interpret_protection_result(
            request,
            ProtectionResultEvidence(query_performed=True, queried_order=queried, submit_result=submit),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )
        self.assertEqual(PositionEvent.PROTECTION_VERIFIED, verified.event)

        journal.persist_position_action(action)
        journal.persist_order_request(_request_payload(request))
        journal.persist_order_result(_result_payload(queried))
        protected = build_position_lifecycle_transition_with_execution_binding(
            self.position,
            genesis.lifecycle_projection,
            lifecycle_event=verified.event,
            lifecycle_interpreted_at=self.t0 + timedelta(seconds=1),
            order_requests=(request,),
            order_results=(queried,),
            fills=(),
        )
        self._persist_composed(journal, protected)
        return broker, request, protected

    def test_matching_e5_binding_is_restart_authoritative_before_new_execution_truth(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "durable-current.sqlite3"
            journal = open_paper_runtime_journal(path)
            _, _, protected = self._materialize_verified_graph(journal)
            journal.close()
            journal = open_paper_runtime_journal(path)
            try:
                recovery = journal.recover(position_id=self.position["position_id"])
                self.assertEqual("READY", recovery.status)
                self.assertTrue(recovery.restart_authoritative)
                self.assertEqual(protected.lifecycle_projection, recovery.current_position_projection.payload)
                self.assertEqual(protected.execution_binding, recovery.current_lifecycle_execution_binding.payload)
            finally:
                journal.close()

    def test_newer_partial_protection_fill_invalidates_old_e5_binding(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "durable-partial.sqlite3"
            journal = open_paper_runtime_journal(path)
            broker, request, protected = self._materialize_verified_graph(journal)
            fill = broker.record_fill(
                request.client_order_id,
                quantity=Decimal("0.0004"),
                price=Decimal("59390"),
                filled_at=self.t0 + timedelta(seconds=2),
                fee=Decimal("0.01"),
                fee_currency="USDT",
                liquidity_role="TAKER",
            )
            latest = broker.query_order(request.client_order_id)
            e5 = interpret_protection_result(
                request,
                ProtectionResultEvidence(query_performed=True, queried_order=latest),
                PositionLifecycleState.OPEN_PROTECTED,
            )
            self.assertEqual(PositionEvent.STATE_UNKNOWN, e5.event)
            journal.persist_order_result(_result_payload(latest))
            journal.persist_fill(_fill_payload(fill))
            journal.close()

            journal = open_paper_runtime_journal(path)
            try:
                recovery = journal.recover(position_id=self.position["position_id"])
                self.assertEqual(protected.lifecycle_projection, recovery.current_position_projection.payload)
                self.assertFalse(recovery.restart_authoritative)
                self.assertEqual("REINTERPRETATION_REQUIRED", recovery.status)
                self.assertIn("E5_EXECUTION_REINTERPRETATION_REQUIRED", recovery.reason_codes)
            finally:
                journal.close()

    def test_newer_canceled_protection_invalidates_old_e5_binding(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "durable-cancel.sqlite3"
            journal = open_paper_runtime_journal(path)
            broker, request, protected = self._materialize_verified_graph(journal)
            canceled = broker.cancel_order(request.client_order_id, observed_at=self.t0 + timedelta(seconds=2))
            e5 = interpret_protection_result(
                request,
                ProtectionResultEvidence(query_performed=True, queried_order=canceled),
                PositionLifecycleState.OPEN_PROTECTED,
            )
            self.assertEqual(PositionEvent.PROTECTION_LOST, e5.event)
            journal.persist_order_result(_result_payload(canceled))
            journal.close()

            journal = open_paper_runtime_journal(path)
            try:
                recovery = journal.recover(position_id=self.position["position_id"])
                self.assertEqual(protected.lifecycle_projection, recovery.current_position_projection.payload)
                self.assertFalse(recovery.restart_authoritative)
                self.assertEqual("REINTERPRETATION_REQUIRED", recovery.status)
                self.assertIn("E5_EXECUTION_REINTERPRETATION_REQUIRED", recovery.reason_codes)
            finally:
                journal.close()

    def test_newer_raw_position_truth_remains_independent_reattestation_axis(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "durable-position-freshness.sqlite3"
            journal = open_paper_runtime_journal(path)
            self._materialize_verified_graph(journal)
            newer = dict(self.position)
            newer["lifecycle_state"] = "OPEN_PROTECTED"
            newer["actual_quantity"] = "0.0011"
            newer["broker_state_observed_at"] = _utc(self.t0 + timedelta(seconds=5))
            journal.persist_raw_position_observation(newer)
            recovery = journal.recover(position_id=self.position["position_id"])
            try:
                self.assertFalse(recovery.restart_authoritative)
                self.assertEqual("REATTESTATION_REQUIRED", recovery.status)
                self.assertIn("E5_REATTESTATION_REQUIRED", recovery.reason_codes)
            finally:
                journal.close()

    def test_missing_companion_binding_cannot_recover_ready(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "durable-missing-binding.sqlite3"
            journal = open_paper_runtime_journal(path)
            journal.persist_risk_decision(self.risk)
            journal.persist_approved_trade_plan(self.plan)
            composed = build_position_lifecycle_genesis_with_execution_binding(
                self.position,
                lifecycle_state=PositionLifecycleState.OPEN_UNPROTECTED,
                lifecycle_interpreted_at=self.t0,
                order_requests=(),
                order_results=(),
                fills=(),
            )
            journal.persist_position_projection(composed.lifecycle_projection)
            recovery = journal.recover(position_id=self.position["position_id"])
            try:
                self.assertFalse(recovery.restart_authoritative)
                self.assertIn("LIFECYCLE_EXECUTION_BINDING_MISSING", recovery.reason_codes)
            finally:
                journal.close()


if __name__ == "__main__":
    unittest.main()
