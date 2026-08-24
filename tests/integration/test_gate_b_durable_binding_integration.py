import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from position import (
    PositionLifecycleState,
    authorize_close_position_action,
    build_position_lifecycle_genesis_with_execution_binding,
    build_position_lifecycle_reattestation_with_execution_binding,
    build_position_lifecycle_transition_with_execution_binding,
)
from src.brokers.paper import PaperBroker
from src.execution.close import prepare_close_order
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


class GateBDurableBindingIntegrationDefinitions(unittest.TestCase):
    """Real E5 producer -> E4 close truth -> E6 freshness comparison definitions.

    This specifically proves the accepted equal-broker-anchor REATTESTATION use:
    E5 may enter EXIT_REQUESTED before later E4 close-order evidence exists; the
    later execution evidence first invalidates the old binding, then a new E5
    REATTESTATION with an exact companion restores mechanical freshness without
    changing lifecycle state. Definitions are NOT_RUN in E7-057.
    """

    def setUp(self):
        self.t0 = datetime(2026, 8, 24, 7, 0, 20, tzinfo=timezone.utc)
        self.plan = {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-e7-binding-int-001",
            "risk_decision_id": "risk-e7-binding-int-001",
            "intent_id": "intent-e7-binding-int-001",
            "strategy_id": "strategy-e7-binding-int",
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
            "created_at": "2026-08-24T06:59:00Z",
            "expires_at": "2026-08-24T07:00:05Z",
            "risk_policy_version": "e5-e7-binding-int-v0.1",
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
            "position_id": "position-e7-binding-int-001",
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

    def _persist(self, journal, composed):
        journal.persist_position_projection(composed.lifecycle_projection)
        journal.persist_lifecycle_execution_binding(composed.execution_binding)

    def test_later_open_close_order_requires_then_allows_equal_anchor_reattestation(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "binding-integration.sqlite3"
            journal = open_paper_runtime_journal(path)
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
            self._persist(journal, genesis)

            close = authorize_close_position_action(
                self.position,
                self.plan,
                action="EXIT",
                created_at=self.t0 + timedelta(seconds=1),
                expires_at=self.t0 + timedelta(seconds=61),
            )
            exit_requested = build_position_lifecycle_transition_with_execution_binding(
                self.position,
                genesis.lifecycle_projection,
                lifecycle_event=close.event,
                lifecycle_interpreted_at=self.t0 + timedelta(seconds=2),
                order_requests=(),
                order_results=(),
                fills=(),
            )
            journal.persist_position_action(close.position_action)
            self._persist(journal, exit_requested)
            current = journal.recover(position_id=self.position["position_id"])
            self.assertEqual("READY", current.status)
            self.assertEqual("EXIT_REQUESTED", current.current_position_projection.payload["lifecycle_state"])

            request = prepare_close_order(
                close.position_action,
                self.plan,
                self.position,
                now=self.t0 + timedelta(seconds=3),
            )
            broker = PaperBroker()
            opened = broker.submit_order(request)
            journal.persist_order_request(_request_payload(request))
            journal.persist_order_result(_result_payload(opened))

            stale = journal.recover(position_id=self.position["position_id"])
            self.assertEqual("REINTERPRETATION_REQUIRED", stale.status)
            self.assertIn("E5_EXECUTION_REINTERPRETATION_REQUIRED", stale.reason_codes)
            self.assertEqual(exit_requested.lifecycle_projection, stale.current_position_projection.payload)

            reattested = build_position_lifecycle_reattestation_with_execution_binding(
                self.position,
                exit_requested.lifecycle_projection,
                lifecycle_interpreted_at=self.t0 + timedelta(seconds=4),
                order_requests=(request,),
                order_results=(opened,),
                fills=(),
            )
            self._persist(journal, reattested)
            journal.close()

            journal = open_paper_runtime_journal(path)
            try:
                recovered = journal.recover(position_id=self.position["position_id"])
                self.assertEqual("READY", recovered.status)
                self.assertTrue(recovered.restart_authoritative)
                self.assertEqual("EXIT_REQUESTED", recovered.current_position_projection.payload["lifecycle_state"])
                self.assertEqual("REATTESTATION", recovered.current_position_projection.payload["lifecycle_projection_kind"])
                self.assertEqual(reattested.execution_binding, recovered.current_lifecycle_execution_binding.payload)
                self.assertEqual(self.position["broker_state_observed_at"], recovered.current_position_projection.payload["broker_state_observed_at"])
            finally:
                journal.close()


if __name__ == "__main__":
    unittest.main()
