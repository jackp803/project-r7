import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from position import (
    PositionEvent,
    PositionLifecycleState,
    ProtectionResultEvidence,
    build_protect_position_action,
    interpret_protection_result,
)
from src.brokers.paper import PaperBroker
from src.execution.models import ExecutionHealthStatus, OrderStatus
from src.execution.protection import prepare_protection_order


class GateBProtectionFailureLifecycleIntegrationTests(unittest.TestCase):
    """Real PaperBroker terminal truth -> E5 failure/loss lifecycle definitions.

    These definitions use accepted production APIs end to end. They never
    construct synthetic terminal OrderResult values as a substitute for the
    PaperBroker callable terminal-state surface.
    """

    def setUp(self):
        self.action_created_at = datetime(2026, 8, 24, 4, 30, 0, tzinfo=timezone.utc)
        self.action_expires_at = datetime(2026, 8, 24, 4, 31, 0, tzinfo=timezone.utc)
        self.consume_at = datetime(2026, 8, 24, 4, 30, 30, tzinfo=timezone.utc)

    def _plan(self):
        return {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-gate-b-failure-001",
            "risk_decision_id": "risk-gate-b-failure-001",
            "intent_id": "intent-gate-b-failure-001",
            "strategy_id": "strategy-gate-b-failure",
            "strategy_version": "1.0.0",
            "symbol": "BTC_USDT_PERP",
            "direction": "LONG",
            "quantity": "0.003",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
            "leverage": "20",
            "margin_mode": "ISOLATED",
            "entry_instruction": {
                "profile_version": "entry-v0.1",
                "order_type": "MARKET",
            },
            "protection_instruction": {
                "stop_level": "59400.00",
                "target_level": "61200.00",
                "max_hold_seconds": 1800,
            },
            "created_at": "2026-08-24T04:00:00Z",
            "expires_at": "2026-08-24T04:00:30Z",
            "risk_policy_version": "e5-gate-b-failure-policy-v0.1",
        }

    def _position(self):
        return {
            "schema_version": "contracts-v0.1",
            "position_id": "position-gate-b-failure-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": "0.0012",
            "average_entry_price": "60000",
            "opened_at": "2026-08-24T04:29:00Z",
            "broker_state_observed_at": "2026-08-24T04:29:30Z",
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": "OPEN_UNPROTECTED",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }

    def _request(self):
        plan = self._plan()
        position = self._position()
        action = build_protect_position_action(
            position,
            plan,
            created_at=self.action_created_at,
            expires_at=self.action_expires_at,
        )
        return prepare_protection_order(
            action,
            plan,
            position,
            now=self.consume_at,
        )

    def _reconcile_current(self, broker, request):
        queried = broker.query_order(request.client_order_id)
        reconciliation = broker.reconcile(
            request,
            order_snapshot=queried,
            position_snapshot=broker.query_position(request.symbol),
        )
        self.assertFalse(reconciliation.retry_allowed)
        self.assertIsNone(reconciliation.retry_token)
        return queried, reconciliation

    def _verify_open(self, broker, request):
        submitted = broker.submit_order(request)
        self.assertEqual(OrderStatus.OPEN, submitted.order_status)
        self.assertEqual(ExecutionHealthStatus.HEALTHY, submitted.execution_health_status)
        queried = broker.query_order(request.client_order_id)
        self.assertIsNotNone(queried)
        self.assertEqual(OrderStatus.OPEN, queried.order_status)

        outcome = interpret_protection_result(
            request,
            ProtectionResultEvidence(
                query_performed=True,
                queried_order=queried,
                submit_result=submitted,
            ),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )
        self.assertEqual(PositionEvent.PROTECTION_VERIFIED, outcome.event)
        self.assertEqual(PositionLifecycleState.OPEN_PROTECTED, outcome.next_state)
        self.assertTrue(outcome.protection_verified)
        return queried, outcome

    def test_real_rejected_protection_becomes_protection_failed_and_emergency(self):
        request = self._request()
        broker = PaperBroker(
            rejected_outcomes={request.client_order_id: "PAPER_SIMULATED_REJECTION"}
        )

        submitted = broker.submit_order(request)
        self.assertEqual(OrderStatus.REJECTED, submitted.order_status)
        self.assertEqual(ExecutionHealthStatus.HEALTHY, submitted.execution_health_status)
        queried, reconciliation = self._reconcile_current(broker, request)
        self.assertIsNotNone(queried)
        self.assertEqual(OrderStatus.REJECTED, queried.order_status)
        self.assertEqual(OrderStatus.REJECTED, reconciliation.resolved_status)

        self.assertEqual(request.order_request_id, queried.order_request_id)
        self.assertEqual(request.client_order_id, queried.client_order_id)
        self.assertEqual(request.quantity, queried.requested_quantity)
        self.assertEqual(Decimal("0"), queried.filled_quantity)
        self.assertIsNone(queried.broker_order_id)

        outcome = interpret_protection_result(
            request,
            ProtectionResultEvidence(
                query_performed=True,
                queried_order=queried,
                submit_result=submitted,
                reconciliation_result=reconciliation,
            ),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )
        self.assertEqual(PositionEvent.PROTECTION_FAILED, outcome.event)
        self.assertEqual(PositionLifecycleState.EMERGENCY, outcome.next_state)
        self.assertEqual("PROTECTION_REJECTED", outcome.reason_code)
        self.assertFalse(outcome.protection_verified)
        self.assertFalse(hasattr(outcome, "retry_allowed"))

    def test_verified_open_then_real_cancel_becomes_protection_lost_and_emergency(self):
        request = self._request()
        broker = PaperBroker()
        opened, verified = self._verify_open(broker, request)
        self.assertEqual(PositionLifecycleState.OPEN_PROTECTED, verified.next_state)

        terminal_at = self.consume_at + timedelta(seconds=10)
        canceled = broker.cancel_order(request.client_order_id, observed_at=terminal_at)
        queried, reconciliation = self._reconcile_current(broker, request)

        self.assertEqual(OrderStatus.CANCELED, canceled.order_status)
        self.assertEqual(canceled, queried)
        self.assertEqual(OrderStatus.CANCELED, reconciliation.resolved_status)
        self.assertEqual(opened.order_request_id, canceled.order_request_id)
        self.assertEqual(opened.client_order_id, canceled.client_order_id)
        self.assertEqual(opened.broker_order_id, canceled.broker_order_id)
        self.assertEqual(opened.requested_quantity, canceled.requested_quantity)
        self.assertEqual(opened.filled_quantity, canceled.filled_quantity)
        self.assertEqual(ExecutionHealthStatus.HEALTHY, canceled.execution_health_status)

        lost = interpret_protection_result(
            request,
            ProtectionResultEvidence(
                query_performed=True,
                queried_order=queried,
                reconciliation_result=reconciliation,
            ),
            PositionLifecycleState.OPEN_PROTECTED,
        )
        self.assertEqual(PositionEvent.PROTECTION_LOST, lost.event)
        self.assertEqual(PositionLifecycleState.EMERGENCY, lost.next_state)
        self.assertEqual("PROTECTION_CANCELED", lost.reason_code)
        self.assertFalse(lost.protection_verified)

    def test_verified_open_then_explicit_real_expiry_becomes_protection_lost_and_emergency(self):
        request = self._request()
        broker = PaperBroker()
        opened, verified = self._verify_open(broker, request)
        self.assertEqual(PositionLifecycleState.OPEN_PROTECTED, verified.next_state)

        terminal_at = self.consume_at + timedelta(seconds=20)
        expired = broker.expire_order(request.client_order_id, observed_at=terminal_at)
        queried, reconciliation = self._reconcile_current(broker, request)

        self.assertEqual(OrderStatus.EXPIRED, expired.order_status)
        self.assertEqual(expired, queried)
        self.assertEqual(OrderStatus.EXPIRED, reconciliation.resolved_status)
        self.assertEqual(opened.order_request_id, expired.order_request_id)
        self.assertEqual(opened.client_order_id, expired.client_order_id)
        self.assertEqual(opened.broker_order_id, expired.broker_order_id)
        self.assertEqual(opened.requested_quantity, expired.requested_quantity)
        self.assertEqual(opened.filled_quantity, expired.filled_quantity)
        self.assertEqual(ExecutionHealthStatus.HEALTHY, expired.execution_health_status)
        self.assertEqual(terminal_at, expired.observed_at)

        lost = interpret_protection_result(
            request,
            ProtectionResultEvidence(
                query_performed=True,
                queried_order=queried,
                reconciliation_result=reconciliation,
            ),
            PositionLifecycleState.OPEN_PROTECTED,
        )
        self.assertEqual(PositionEvent.PROTECTION_LOST, lost.event)
        self.assertEqual(PositionLifecycleState.EMERGENCY, lost.next_state)
        self.assertEqual("PROTECTION_EXPIRED", lost.reason_code)
        self.assertFalse(lost.protection_verified)

    def test_all_real_terminal_truth_reconciles_definitively_without_retry_authority(self):
        scenarios = ("rejected", "canceled", "expired")
        for index, scenario in enumerate(scenarios, start=1):
            with self.subTest(scenario=scenario):
                request = self._request()
                if scenario == "rejected":
                    broker = PaperBroker(
                        rejected_outcomes={request.client_order_id: f"PAPER_REJECT_{index}"}
                    )
                    broker.submit_order(request)
                    expected = OrderStatus.REJECTED
                else:
                    broker = PaperBroker()
                    broker.submit_order(request)
                    terminal_at = self.consume_at + timedelta(seconds=30 + index)
                    if scenario == "canceled":
                        broker.cancel_order(request.client_order_id, observed_at=terminal_at)
                        expected = OrderStatus.CANCELED
                    else:
                        broker.expire_order(request.client_order_id, observed_at=terminal_at)
                        expected = OrderStatus.EXPIRED

                queried, reconciliation = self._reconcile_current(broker, request)
                self.assertIsNotNone(queried)
                self.assertEqual(expected, queried.order_status)
                self.assertEqual(expected, reconciliation.resolved_status)
                self.assertFalse(reconciliation.retry_allowed)
                self.assertIsNone(reconciliation.retry_token)


if __name__ == "__main__":
    unittest.main()
