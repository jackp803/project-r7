import unittest
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
from src.execution.models import OrderStatus
from src.execution.protection import prepare_protection_order


class GateBProtectionLifecycleIntegrationTests(unittest.TestCase):
    """Cross-module definitions for the real PaperBroker -> E5 lifecycle boundary.

    These tests use the accepted E5 producer/result bridge, E4 protection
    translator, and PaperBroker directly. They do not synthesize terminal
    REJECTED/CANCELED/EXPIRED system truth that PaperBroker cannot currently
    produce through its public callable surface.
    """

    def setUp(self):
        self.action_created_at = datetime(2026, 8, 24, 3, 5, 30, tzinfo=timezone.utc)
        self.action_expires_at = datetime(2026, 8, 24, 3, 6, 30, tzinfo=timezone.utc)
        self.consume_at = datetime(2026, 8, 24, 3, 6, 0, tzinfo=timezone.utc)
        self.fill_at = datetime(2026, 8, 24, 3, 6, 10, tzinfo=timezone.utc)

    def _plan(self):
        return {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-gate-b-lifecycle-001",
            "risk_decision_id": "risk-gate-b-lifecycle-001",
            "intent_id": "intent-gate-b-lifecycle-001",
            "strategy_id": "strategy-gate-b-lifecycle",
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
            "risk_policy_version": "e5-gate-b-lifecycle-policy-v0.1",
        }

    def _position(self):
        return {
            "schema_version": "contracts-v0.1",
            "position_id": "position-gate-b-lifecycle-001",
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

    def test_submit_open_alone_never_verifies_but_authoritative_query_does(self):
        request = self._request()
        broker = PaperBroker()
        submit_result = broker.submit_order(request)
        self.assertEqual(OrderStatus.OPEN, submit_result.order_status)

        submit_only = interpret_protection_result(
            request,
            ProtectionResultEvidence(
                query_performed=False,
                submit_result=submit_result,
            ),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )
        self.assertEqual(PositionEvent.STATE_UNKNOWN, submit_only.event)
        self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, submit_only.next_state)
        self.assertFalse(submit_only.protection_verified)

        queried = broker.query_order(request.client_order_id)
        self.assertIsNotNone(queried)
        verified = interpret_protection_result(
            request,
            ProtectionResultEvidence(
                query_performed=True,
                queried_order=queried,
                submit_result=submit_result,
            ),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )
        self.assertEqual(PositionEvent.PROTECTION_VERIFIED, verified.event)
        self.assertEqual(PositionLifecycleState.OPEN_PROTECTED, verified.next_state)
        self.assertTrue(verified.protection_verified)

    def test_ambiguous_submit_accepted_requires_query_and_reconciliation_before_verification(self):
        request = self._request()
        broker = PaperBroker(ambiguous_outcomes={request.client_order_id: True})
        submit_result = broker.submit_order(request)
        self.assertEqual(OrderStatus.RECONCILIATION_REQUIRED, submit_result.order_status)

        queried = broker.query_order(request.client_order_id)
        self.assertIsNotNone(queried)
        self.assertEqual(OrderStatus.OPEN, queried.order_status)

        before_reconciliation = interpret_protection_result(
            request,
            ProtectionResultEvidence(
                query_performed=True,
                queried_order=queried,
                submit_result=submit_result,
            ),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )
        self.assertEqual(PositionEvent.STATE_UNKNOWN, before_reconciliation.event)
        self.assertFalse(before_reconciliation.protection_verified)

        reconciliation = broker.reconcile(
            request,
            order_snapshot=queried,
            position_snapshot=broker.query_position(request.symbol),
        )
        self.assertEqual(OrderStatus.OPEN, reconciliation.resolved_status)
        self.assertFalse(reconciliation.retry_allowed)

        after_reconciliation = interpret_protection_result(
            request,
            ProtectionResultEvidence(
                query_performed=True,
                queried_order=queried,
                submit_result=submit_result,
                reconciliation_result=reconciliation,
            ),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )
        self.assertEqual(PositionEvent.PROTECTION_VERIFIED, after_reconciliation.event)
        self.assertEqual(PositionLifecycleState.OPEN_PROTECTED, after_reconciliation.next_state)
        self.assertTrue(after_reconciliation.protection_verified)

    def test_ambiguous_submit_not_accepted_stays_fail_closed_even_when_e4_allows_retry(self):
        request = self._request()
        broker = PaperBroker(ambiguous_outcomes={request.client_order_id: False})
        submit_result = broker.submit_order(request)
        self.assertEqual(OrderStatus.RECONCILIATION_REQUIRED, submit_result.order_status)

        queried = broker.query_order(request.client_order_id)
        self.assertIsNone(queried)
        reconciliation = broker.reconcile(
            request,
            order_snapshot=queried,
            position_snapshot=broker.query_position(request.symbol),
        )
        self.assertEqual(OrderStatus.UNKNOWN, reconciliation.resolved_status)
        self.assertTrue(reconciliation.retry_allowed)

        outcome = interpret_protection_result(
            request,
            ProtectionResultEvidence(
                query_performed=True,
                queried_order=queried,
                submit_result=submit_result,
                reconciliation_result=reconciliation,
            ),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )
        self.assertEqual(PositionEvent.STATE_UNKNOWN, outcome.event)
        self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, outcome.next_state)
        self.assertFalse(outcome.protection_verified)
        self.assertFalse(hasattr(outcome, "retry_allowed"))

    def test_real_partial_or_full_protective_fill_is_not_mislabeled_as_failure_or_loss(self):
        for fill_quantity, expected_status in (
            (Decimal("0.0006"), OrderStatus.PARTIALLY_FILLED),
            (Decimal("0.0012"), OrderStatus.FILLED),
        ):
            with self.subTest(expected_status=expected_status):
                request = self._request()
                broker = PaperBroker()
                broker.submit_order(request)
                queried_open = broker.query_order(request.client_order_id)
                self.assertIsNotNone(queried_open)
                verified = interpret_protection_result(
                    request,
                    ProtectionResultEvidence(
                        query_performed=True,
                        queried_order=queried_open,
                    ),
                    PositionLifecycleState.OPEN_UNPROTECTED,
                )
                self.assertEqual(PositionLifecycleState.OPEN_PROTECTED, verified.next_state)

                broker.record_fill(
                    request.client_order_id,
                    quantity=fill_quantity,
                    price=Decimal("59390"),
                    filled_at=self.fill_at,
                )
                queried_after_trigger = broker.query_order(request.client_order_id)
                self.assertIsNotNone(queried_after_trigger)
                self.assertEqual(expected_status, queried_after_trigger.order_status)

                triggered = interpret_protection_result(
                    request,
                    ProtectionResultEvidence(
                        query_performed=True,
                        queried_order=queried_after_trigger,
                    ),
                    PositionLifecycleState.OPEN_PROTECTED,
                )
                self.assertEqual(PositionEvent.STATE_UNKNOWN, triggered.event)
                self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, triggered.next_state)
                self.assertNotEqual(PositionEvent.PROTECTION_FAILED, triggered.event)
                self.assertNotEqual(PositionEvent.PROTECTION_LOST, triggered.event)
                self.assertFalse(triggered.protection_verified)


if __name__ == "__main__":
    unittest.main()
