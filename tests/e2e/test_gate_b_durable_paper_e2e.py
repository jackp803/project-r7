import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from position import (
    PositionEvent,
    PositionLifecycleState,
    ProtectionResultEvidence,
    authorize_close_position_action,
    build_position_lifecycle_closed_transition,
    build_position_lifecycle_execution_evidence_binding,
    build_position_lifecycle_genesis_with_execution_binding,
    build_position_lifecycle_transition_with_execution_binding,
    build_protect_position_action,
    build_trade_result,
    interpret_protection_result,
)
from src.brokers.paper import PaperBroker
from src.execution.close import prepare_close_order
from src.execution.funding import produce_paper_zero_funding_evidence
from src.execution.gateway import ExecutionGateway
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


class GateBDurablePaperE2EDefinitions(unittest.TestCase):
    """E7 durable Paper E2E definitions over accepted E4/E5/E6 APIs.

    These are definitions only for E7-20260824-057. They are intentionally
    NOT_RUN. Upstream Signal/TradeIntent lineage is represented canonically;
    risk/execution/lifecycle/funding/TradeResult/storage behavior uses the
    accepted production surfaces rather than a parallel implementation.
    """

    def setUp(self):
        self.t_entry_request = datetime(2026, 8, 24, 7, 0, 0, tzinfo=timezone.utc)
        self.t_entry_fill = datetime(2026, 8, 24, 7, 0, 10, tzinfo=timezone.utc)
        self.t_position = datetime(2026, 8, 24, 7, 0, 20, tzinfo=timezone.utc)
        self.t_action = datetime(2026, 8, 24, 7, 1, 0, tzinfo=timezone.utc)
        self.t_request = datetime(2026, 8, 24, 7, 1, 10, tzinfo=timezone.utc)
        self.t_fill = datetime(2026, 8, 24, 7, 1, 20, tzinfo=timezone.utc)
        self.t_flat = datetime(2026, 8, 24, 7, 1, 30, tzinfo=timezone.utc)

    def _signal(self):
        return {
            "schema_version": "contracts-v0.1",
            "signal_id": "signal-e7-durable-001",
            "strategy_id": "strategy-e7-durable",
            "strategy_version": "1.0.0",
            "strategy_content_hash": "sha256:strategy-e7-durable-fixture",
            "symbol": "BTC_USDT_PERP",
            "evaluated_at": "2026-08-24T06:59:00Z",
            "direction": "LONG",
            "reason_codes": ["E7_DURABLE_FIXTURE"],
            "market_boundary_ref": "boundary-e7-durable-001",
        }

    def _intent(self):
        signal = self._signal()
        return {
            "schema_version": "contracts-v0.1",
            "intent_id": "intent-e7-durable-001",
            "signal_id": signal["signal_id"],
            "strategy_id": signal["strategy_id"],
            "strategy_version": signal["strategy_version"],
            "symbol": signal["symbol"],
            "direction": signal["direction"],
            "generated_at": "2026-08-24T06:59:01Z",
            "market_boundary_ref": signal["market_boundary_ref"],
            "entry_profile_version": "entry-v0.1",
            "entry_order_type": "MARKET",
            "strategy_stop_level": "59400",
            "strategy_target_level": "61200",
            "max_hold_seconds": 1800,
        }

    def _risk(self):
        intent = self._intent()
        return {
            "schema_version": "contracts-v0.1",
            "risk_decision_id": "risk-e7-durable-001",
            "intent_id": intent["intent_id"],
            "strategy_id": intent["strategy_id"],
            "strategy_version": intent["strategy_version"],
            "decision": "APPROVE",
            "reason_codes": [],
            "risk_policy_version": "e5-e7-durable-policy-v0.1",
            "decided_at": "2026-08-24T06:59:02Z",
            "market_health_status": "HEALTHY",
            "account_state_status": "KNOWN",
            "position_state_status": "FLAT",
            "approved_quantity": "0.003",
            "approved_leverage": "20",
            "margin_mode": "ISOLATED",
            "required_stop_level": "59400",
            "max_hold_seconds": 1800,
        }

    def _plan(self):
        intent = self._intent()
        risk = self._risk()
        return {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-e7-durable-001",
            "risk_decision_id": risk["risk_decision_id"],
            "intent_id": intent["intent_id"],
            "strategy_id": intent["strategy_id"],
            "strategy_version": intent["strategy_version"],
            "symbol": intent["symbol"],
            "direction": intent["direction"],
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
            "created_at": "2026-08-24T06:59:02Z",
            "expires_at": "2026-08-24T07:00:05Z",
            "risk_policy_version": risk["risk_policy_version"],
        }

    def _position(self, lifecycle):
        return {
            "schema_version": "contracts-v0.1",
            "position_id": "position-e7-durable-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": "0.0012",
            "average_entry_price": "60000",
            "opened_at": _utc(self.t_entry_fill),
            "broker_state_observed_at": _utc(self.t_position),
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": lifecycle,
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }

    def _persist_upstream(self, journal):
        signal = self._signal()
        intent = self._intent()
        risk = self._risk()
        plan = self._plan()
        self.assertEqual(signal["signal_id"], intent["signal_id"])
        self.assertEqual(intent["intent_id"], risk["intent_id"])
        self.assertEqual(intent["intent_id"], plan["intent_id"])
        self.assertEqual(risk["risk_decision_id"], plan["risk_decision_id"])
        journal.persist_risk_decision(risk)
        journal.persist_approved_trade_plan(plan)
        return plan

    def _entry_truth(self, broker, journal, plan):
        request = ExecutionGateway().prepare_entry_order(plan, now=self.t_entry_request)
        submit = broker.submit_order(request)
        journal.persist_order_request(_request_payload(request))
        journal.persist_order_result(_result_payload(submit))
        fill = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0012"),
            price=Decimal("60000"),
            filled_at=self.t_entry_fill,
            fee=Decimal("0.01"),
            fee_currency="USDT",
            liquidity_role="TAKER",
        )
        journal.persist_order_result(_result_payload(broker.query_order(request.client_order_id)))
        journal.persist_fill(_fill_payload(fill))
        return request, fill

    def _persist_projection_and_binding(self, journal, composed):
        journal.persist_position_projection(composed.lifecycle_projection)
        journal.persist_lifecycle_execution_binding(composed.execution_binding)

    def _explicit_close_graph(self, journal, *, emergency):
        plan = self._persist_upstream(journal)
        broker = PaperBroker()
        entry_request, entry_fill = self._entry_truth(broker, journal, plan)
        lifecycle = "EMERGENCY" if emergency else "OPEN_UNPROTECTED"
        source = self._position(lifecycle)
        genesis = build_position_lifecycle_genesis_with_execution_binding(
            source,
            lifecycle_state=lifecycle,
            lifecycle_interpreted_at=self.t_position,
            order_requests=(entry_request,),
            order_results=(),
            fills=(entry_fill,),
        )
        self._persist_projection_and_binding(journal, genesis)

        close = authorize_close_position_action(
            source,
            plan,
            action="EMERGENCY_EXIT" if emergency else "EXIT",
            created_at=self.t_action,
            expires_at=self.t_action + timedelta(seconds=60),
        )
        request = prepare_close_order(
            close.position_action,
            plan,
            source,
            now=self.t_request,
        )
        submit = broker.submit_order(request)
        journal.persist_position_action(close.position_action)
        journal.persist_order_request(_request_payload(request))
        journal.persist_order_result(_result_payload(submit))

        exit_requested = build_position_lifecycle_transition_with_execution_binding(
            source,
            genesis.lifecycle_projection,
            lifecycle_event=close.event,
            lifecycle_interpreted_at=self.t_request + timedelta(seconds=1),
            order_requests=(entry_request, request),
            order_results=(submit,),
            fills=(entry_fill,),
        )
        self._persist_projection_and_binding(journal, exit_requested)

        exit_fill = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0012"),
            price=Decimal("61000"),
            filled_at=self.t_fill,
            fee=Decimal("0.01"),
            fee_currency="USDT",
            liquidity_role="TAKER",
        )
        latest = broker.query_order(request.client_order_id)
        journal.persist_order_result(_result_payload(latest))
        journal.persist_fill(_fill_payload(exit_fill))
        flat = broker.observe_position_after_close(request, source, observed_at=self.t_flat)
        funding = produce_paper_zero_funding_evidence(plan, flat, calculated_at=self.t_flat)
        result = build_trade_result(
            plan,
            current_lifecycle_state=close.next_state,
            exit_authority=close.position_action,
            entry_order_requests=(entry_request,),
            entry_fills=(entry_fill,),
            exit_order_request=request,
            exit_fills=(exit_fill,),
            final_position=flat,
            funding_evidence=funding,
        )
        closed_projection = build_position_lifecycle_closed_transition(
            flat,
            exit_requested.lifecycle_projection,
            trade_result_outcome=result,
            lifecycle_interpreted_at=self.t_flat + timedelta(seconds=1),
        )
        closed_binding = build_position_lifecycle_execution_evidence_binding(
            closed_projection,
            order_requests=(entry_request, request),
            order_results=(submit, latest),
            fills=(entry_fill, exit_fill),
        )
        journal.persist_position_projection(closed_projection)
        journal.persist_lifecycle_execution_binding(closed_binding)
        journal.persist_funding_evidence(funding)
        journal.persist_trade_result(result.trade_result)
        return closed_projection, closed_binding, result.trade_result

    def _assert_close_reopen(self, *, emergency):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "gate-b-durable.sqlite3"
            journal = open_paper_runtime_journal(path)
            closed, binding, result = self._explicit_close_graph(journal, emergency=emergency)
            journal.close()
            journal = open_paper_runtime_journal(path)
            try:
                recovery = journal.recover(position_id=closed["position_id"])
                self.assertEqual("READY", recovery.status)
                self.assertTrue(recovery.restart_authoritative)
                self.assertEqual(closed, recovery.current_position_projection.payload)
                self.assertEqual(binding, recovery.current_lifecycle_execution_binding.payload)
                self.assertEqual(result, recovery.trade_result.payload)
                self.assertEqual(result["funding_evidence_id"], recovery.funding_evidence[0].canonical_id)
            finally:
                journal.close()

    def test_ordinary_exit_closes_reopens_with_exact_durable_audit_graph(self):
        self._assert_close_reopen(emergency=False)

    def test_emergency_exit_closes_reopens_with_exact_durable_audit_graph(self):
        self._assert_close_reopen(emergency=True)

    def test_verified_protection_stop_full_trigger_closes_reopens_with_exact_audit_graph(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "gate-b-protection-durable.sqlite3"
            journal = open_paper_runtime_journal(path)
            plan = self._persist_upstream(journal)
            broker = PaperBroker()
            entry_request, entry_fill = self._entry_truth(broker, journal, plan)
            source = self._position("OPEN_UNPROTECTED")
            genesis = build_position_lifecycle_genesis_with_execution_binding(
                source,
                lifecycle_state=PositionLifecycleState.OPEN_UNPROTECTED,
                lifecycle_interpreted_at=self.t_position,
                order_requests=(entry_request,),
                order_results=(),
                fills=(entry_fill,),
            )
            self._persist_projection_and_binding(journal, genesis)

            action = build_protect_position_action(
                source,
                plan,
                created_at=self.t_position,
                expires_at=self.t_position + timedelta(seconds=60),
            )
            request = prepare_protection_order(action, plan, source, now=self.t_position)
            submit = broker.submit_order(request)
            queried = broker.query_order(request.client_order_id)
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
                source,
                genesis.lifecycle_projection,
                lifecycle_event=verified.event,
                lifecycle_interpreted_at=self.t_position + timedelta(seconds=1),
                order_requests=(entry_request, request),
                order_results=(queried,),
                fills=(entry_fill,),
            )
            self._persist_projection_and_binding(journal, protected)

            protected_source = dict(source)
            protected_source["lifecycle_state"] = PositionLifecycleState.OPEN_PROTECTED.value
            exit_fill = broker.record_fill(
                request.client_order_id,
                quantity=Decimal("0.0012"),
                price=Decimal("59390"),
                filled_at=self.t_fill,
                fee=Decimal("0.01"),
                fee_currency="USDT",
                liquidity_role="TAKER",
            )
            latest = broker.query_order(request.client_order_id)
            journal.persist_order_result(_result_payload(latest))
            journal.persist_fill(_fill_payload(exit_fill))
            flat = broker.observe_position_after_close(request, protected_source, observed_at=self.t_flat)
            funding = produce_paper_zero_funding_evidence(plan, flat, calculated_at=self.t_flat)
            result = build_trade_result(
                plan,
                current_lifecycle_state=PositionLifecycleState.OPEN_PROTECTED,
                exit_authority=action,
                entry_order_requests=(entry_request,),
                entry_fills=(entry_fill,),
                exit_order_request=request,
                exit_fills=(exit_fill,),
                final_position=flat,
                funding_evidence=funding,
            )
            closed = build_position_lifecycle_closed_transition(
                flat,
                protected.lifecycle_projection,
                trade_result_outcome=result,
                lifecycle_interpreted_at=self.t_flat + timedelta(seconds=1),
            )
            binding = build_position_lifecycle_execution_evidence_binding(
                closed,
                order_requests=(entry_request, request),
                order_results=(queried, latest),
                fills=(entry_fill, exit_fill),
            )
            journal.persist_position_projection(closed)
            journal.persist_lifecycle_execution_binding(binding)
            journal.persist_funding_evidence(funding)
            journal.persist_trade_result(result.trade_result)
            journal.close()

            journal = open_paper_runtime_journal(path)
            try:
                recovery = journal.recover(position_id=closed["position_id"])
                self.assertEqual("READY", recovery.status)
                self.assertEqual(closed, recovery.current_position_projection.payload)
                self.assertEqual(binding, recovery.current_lifecycle_execution_binding.payload)
                self.assertEqual(result.trade_result, recovery.trade_result.payload)
                self.assertEqual(["PROTECTION_STOP_FILLED"], recovery.trade_result.payload["exit_reason_codes"])
            finally:
                journal.close()


if __name__ == "__main__":
    unittest.main()
