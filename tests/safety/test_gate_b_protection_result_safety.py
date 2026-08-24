import unittest
from dataclasses import replace
from datetime import datetime, timezone
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


class GateBProtectionResultSafetyTests(unittest.TestCase):
    """Fail-closed definitions across PaperBroker normalized truth and E5 interpretation."""

    def setUp(self):
        self.action_created_at = datetime(2026, 8, 24, 3, 5, 30, tzinfo=timezone.utc)
        self.action_expires_at = datetime(2026, 8, 24, 3, 6, 30, tzinfo=timezone.utc)
        self.consume_at = datetime(2026, 8, 24, 3, 6, 0, tzinfo=timezone.utc)

    def _plan(self):
        return {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-gate-b-result-safety-001",
            "risk_decision_id": "risk-gate-b-result-safety-001",
            "intent_id": "intent-gate-b-result-safety-001",
            "strategy_id": "strategy-gate-b-result-safety",
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
            "created_at": "2026-08-24T03:00:00Z",
            "expires_at": "2026-08-24T03:00:30Z",
            "risk_policy_version": "e5-gate-b-result-safety-policy-v0.1",
        }

    def _position(self):
        return {
            "schema_version": "contracts-v0.1",
            "position_id": "position-gate-b-result-safety-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": "0.0012",
            "average_entry_price": "60000",
            "opened_at": "2026-08-24T03:05:00Z",
            "broker_state_observed_at": "2026-08-24T03:05:20Z",
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": "OPEN_UNPROTECTED",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }

    def _request_and_query(self):
        plan = self._plan()
        position = self._position()
        action = build_protect_position_action(
            position,
            plan,
            created_at=self.action_created_at,
            expires_at=self.action_expires_at,
        )
        request = prepare_protection_order(
            action,
            plan,
            position,
            now=self.consume_at,
        )
        broker = PaperBroker()
        broker.submit_order(request)
        queried = broker.query_order(request.client_order_id)
        self.assertIsNotNone(queried)
        return request, queried

    def _assert_fail_closed(self, request, queried, *, position_status="CONSISTENT"):
        outcome = interpret_protection_result(
            request,
            ProtectionResultEvidence(
                query_performed=True,
                queried_order=queried,
                position_reconciliation_status=position_status,
            ),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )
        self.assertEqual(PositionEvent.STATE_UNKNOWN, outcome.event)
        self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, outcome.next_state)
        self.assertFalse(outcome.protection_verified)

    def test_mismatched_order_or_client_identity_never_verifies(self):
        request, queried = self._request_and_query()
        cases = (
            replace(queried, order_request_id="different-order-request"),
            replace(queried, client_order_id="different-client-order"),
        )
        for mismatched in cases:
            with self.subTest(mismatched=mismatched):
                self._assert_fail_closed(request, mismatched)

    def test_requested_or_filled_quantity_inconsistency_never_verifies(self):
        request, queried = self._request_and_query()
        cases = (
            replace(queried, requested_quantity=request.quantity + Decimal("0.0001")),
            replace(
                queried,
                filled_quantity=request.quantity + Decimal("0.0001"),
            ),
        )
        for inconsistent in cases:
            with self.subTest(inconsistent=inconsistent):
                self._assert_fail_closed(request, inconsistent)

    def test_degraded_unknown_health_or_ambiguous_order_status_never_verifies(self):
        request, queried = self._request_and_query()
        health_cases = (
            replace(queried, execution_health_status=ExecutionHealthStatus.DEGRADED),
            replace(queried, execution_health_status=ExecutionHealthStatus.UNKNOWN),
        )
        for degraded in health_cases:
            with self.subTest(health=degraded.execution_health_status):
                self._assert_fail_closed(request, degraded)

        status_cases = (
            replace(queried, order_status=OrderStatus.UNKNOWN, broker_order_id=None),
            replace(
                queried,
                order_status=OrderStatus.RECONCILIATION_REQUIRED,
                execution_health_status=ExecutionHealthStatus.DEGRADED,
                broker_order_id=None,
            ),
        )
        for ambiguous in status_cases:
            with self.subTest(status=ambiguous.order_status):
                self._assert_fail_closed(request, ambiguous)

    def test_incompatible_position_reconciliation_truth_never_verifies(self):
        request, queried = self._request_and_query()
        for status in ("UNKNOWN", "MISMATCH", "RECONCILIATION_REQUIRED"):
            with self.subTest(position_reconciliation_status=status):
                self._assert_fail_closed(
                    request,
                    queried,
                    position_status=status,
                )


if __name__ == "__main__":
    unittest.main()
