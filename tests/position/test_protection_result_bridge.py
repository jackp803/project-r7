import inspect
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
    transition,
)
from src.execution.models import (
    ExecutionHealthStatus,
    OrderResult,
    OrderStatus,
    ReconciliationResult,
)
from src.execution.protection import prepare_protection_order


class ProtectionResultBridgeTests(unittest.TestCase):
    def setUp(self):
        self.action_created_at = datetime(2026, 8, 24, 3, 5, 30, tzinfo=timezone.utc)
        self.action_expires_at = datetime(2026, 8, 24, 3, 6, 30, tzinfo=timezone.utc)
        self.consume_at = datetime(2026, 8, 24, 3, 6, 0, tzinfo=timezone.utc)
        self.observed_at = datetime(2026, 8, 24, 3, 6, 5, tzinfo=timezone.utc)

    def _plan(self):
        return {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-result-bridge-001",
            "risk_decision_id": "risk-result-bridge-001",
            "intent_id": "intent-result-bridge-001",
            "strategy_id": "strategy-result-bridge",
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
            "risk_policy_version": "e5-result-bridge-policy-v0.1",
        }

    def _position(self):
        return {
            "schema_version": "contracts-v0.1",
            "position_id": "position-result-bridge-001",
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
        position = self._position()
        plan = self._plan()
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

    def _result(
        self,
        request,
        *,
        status=OrderStatus.OPEN,
        health=ExecutionHealthStatus.HEALTHY,
        broker_order_id="paper-protection-001",
        order_request_id=None,
        client_order_id=None,
        requested_quantity=None,
        filled_quantity=Decimal("0"),
    ):
        return OrderResult(
            schema_version="contracts-v0.1",
            order_request_id=request.order_request_id if order_request_id is None else order_request_id,
            client_order_id=request.client_order_id if client_order_id is None else client_order_id,
            broker_order_id=broker_order_id,
            order_status=status,
            observed_at=self.observed_at,
            execution_health_status=health,
            requested_quantity=request.quantity if requested_quantity is None else requested_quantity,
            filled_quantity=filled_quantity,
        )

    def _reconciliation(self, request, *, status=OrderStatus.OPEN, retry_allowed=False):
        return ReconciliationResult(
            client_order_id=request.client_order_id,
            resolved_status=status,
            retry_allowed=retry_allowed,
            reason="E5_TEST_NORMALIZED_RECONCILIATION",
        )

    def test_submit_open_without_authoritative_query_never_verifies(self):
        request = self._request()
        submit = self._result(request)
        outcome = interpret_protection_result(
            request,
            ProtectionResultEvidence(query_performed=False, submit_result=submit),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )

        self.assertEqual(PositionEvent.STATE_UNKNOWN, outcome.event)
        self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, outcome.next_state)
        self.assertEqual("AUTHORITATIVE_QUERY_NOT_PERFORMED", outcome.reason_code)
        self.assertFalse(outcome.protection_verified)

    def test_exact_authoritative_open_healthy_query_verifies_initial_protection(self):
        request = self._request()
        queried = self._result(request)
        outcome = interpret_protection_result(
            request,
            ProtectionResultEvidence(query_performed=True, queried_order=queried),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )

        self.assertEqual(PositionEvent.PROTECTION_VERIFIED, outcome.event)
        self.assertEqual(PositionLifecycleState.OPEN_PROTECTED, outcome.next_state)
        self.assertEqual("PROTECTION_ACTIVE_VERIFIED", outcome.reason_code)
        self.assertTrue(outcome.protection_verified)

    def test_missing_broker_order_identity_cannot_verify(self):
        request = self._request()
        queried = self._result(request, broker_order_id=None)
        outcome = interpret_protection_result(
            request,
            ProtectionResultEvidence(query_performed=True, queried_order=queried),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )

        self.assertEqual(PositionEvent.STATE_UNKNOWN, outcome.event)
        self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, outcome.next_state)
        self.assertFalse(outcome.protection_verified)

    def test_request_or_client_identity_mismatch_never_verifies(self):
        request = self._request()
        cases = (
            self._result(request, order_request_id="different-order-request"),
            self._result(request, client_order_id="different-client-order"),
        )
        for queried in cases:
            with self.subTest(queried=queried):
                outcome = interpret_protection_result(
                    request,
                    ProtectionResultEvidence(query_performed=True, queried_order=queried),
                    PositionLifecycleState.OPEN_UNPROTECTED,
                )
                self.assertEqual(PositionEvent.STATE_UNKNOWN, outcome.event)
                self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, outcome.next_state)
                self.assertFalse(outcome.protection_verified)

    def test_unknown_and_reconciliation_required_order_status_fail_closed(self):
        request = self._request()
        for status in (OrderStatus.UNKNOWN, OrderStatus.RECONCILIATION_REQUIRED):
            with self.subTest(status=status):
                queried = self._result(request, status=status, broker_order_id=None)
                outcome = interpret_protection_result(
                    request,
                    ProtectionResultEvidence(query_performed=True, queried_order=queried),
                    PositionLifecycleState.OPEN_UNPROTECTED,
                )
                self.assertEqual(PositionEvent.STATE_UNKNOWN, outcome.event)
                self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, outcome.next_state)
                self.assertFalse(outcome.protection_verified)

    def test_degraded_and_unknown_execution_health_fail_closed(self):
        request = self._request()
        for health in (ExecutionHealthStatus.DEGRADED, ExecutionHealthStatus.UNKNOWN):
            with self.subTest(health=health):
                queried = self._result(request, health=health)
                outcome = interpret_protection_result(
                    request,
                    ProtectionResultEvidence(query_performed=True, queried_order=queried),
                    PositionLifecycleState.OPEN_UNPROTECTED,
                )
                self.assertEqual(PositionEvent.STATE_UNKNOWN, outcome.event)
                self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, outcome.next_state)
                self.assertFalse(outcome.protection_verified)

    def test_definitive_initial_rejected_canceled_expired_truth_enters_emergency(self):
        request = self._request()
        for status in (OrderStatus.REJECTED, OrderStatus.CANCELED, OrderStatus.EXPIRED):
            with self.subTest(status=status):
                queried = self._result(request, status=status, broker_order_id=None)
                outcome = interpret_protection_result(
                    request,
                    ProtectionResultEvidence(query_performed=True, queried_order=queried),
                    PositionLifecycleState.OPEN_UNPROTECTED,
                )
                self.assertEqual(PositionEvent.PROTECTION_FAILED, outcome.event)
                self.assertEqual(PositionLifecycleState.EMERGENCY, outcome.next_state)
                self.assertFalse(outcome.protection_verified)

    def test_definitive_loss_from_protected_states_enters_emergency(self):
        request = self._request()
        queried = self._result(request, status=OrderStatus.CANCELED)
        for current_state in (
            PositionLifecycleState.OPEN_PROTECTED,
            PositionLifecycleState.PROFIT_PROTECTED,
        ):
            with self.subTest(current_state=current_state):
                outcome = interpret_protection_result(
                    request,
                    ProtectionResultEvidence(query_performed=True, queried_order=queried),
                    current_state,
                )
                self.assertEqual(PositionEvent.PROTECTION_LOST, outcome.event)
                self.assertEqual(PositionLifecycleState.EMERGENCY, outcome.next_state)
                self.assertFalse(outcome.protection_verified)

    def test_query_not_performed_and_query_not_found_are_distinct(self):
        request = self._request()
        not_performed = interpret_protection_result(
            request,
            ProtectionResultEvidence(query_performed=False),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )
        not_found = interpret_protection_result(
            request,
            ProtectionResultEvidence(query_performed=True, queried_order=None),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )

        self.assertEqual("AUTHORITATIVE_QUERY_NOT_PERFORMED", not_performed.reason_code)
        self.assertEqual("AUTHORITATIVE_QUERY_NOT_FOUND_UNRESOLVED", not_found.reason_code)
        self.assertNotEqual(not_performed.reason_code, not_found.reason_code)
        self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, not_performed.next_state)
        self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, not_found.next_state)

    def test_query_not_found_can_be_definitive_only_with_sufficient_reconciliation(self):
        request = self._request()
        reconciliation = self._reconciliation(request, status=OrderStatus.CANCELED)
        outcome = interpret_protection_result(
            request,
            ProtectionResultEvidence(
                query_performed=True,
                queried_order=None,
                reconciliation_result=reconciliation,
            ),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )

        self.assertEqual(PositionEvent.PROTECTION_FAILED, outcome.event)
        self.assertEqual(PositionLifecycleState.EMERGENCY, outcome.next_state)
        self.assertEqual("PROTECTION_CANCELED", outcome.reason_code)

    def test_ambiguous_submit_requires_consistent_reconciliation_before_open_can_verify(self):
        request = self._request()
        ambiguous_submit = self._result(
            request,
            status=OrderStatus.RECONCILIATION_REQUIRED,
            health=ExecutionHealthStatus.DEGRADED,
            broker_order_id=None,
        )
        queried = self._result(request, status=OrderStatus.OPEN)

        before_reconciliation = interpret_protection_result(
            request,
            ProtectionResultEvidence(
                query_performed=True,
                queried_order=queried,
                submit_result=ambiguous_submit,
            ),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )
        self.assertEqual(PositionEvent.STATE_UNKNOWN, before_reconciliation.event)
        self.assertFalse(before_reconciliation.protection_verified)

        after_reconciliation = interpret_protection_result(
            request,
            ProtectionResultEvidence(
                query_performed=True,
                queried_order=queried,
                submit_result=ambiguous_submit,
                reconciliation_result=self._reconciliation(request, status=OrderStatus.OPEN),
            ),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )
        self.assertEqual(PositionEvent.PROTECTION_VERIFIED, after_reconciliation.event)
        self.assertEqual(PositionLifecycleState.OPEN_PROTECTED, after_reconciliation.next_state)
        self.assertTrue(after_reconciliation.protection_verified)

    def test_contradictory_reconciliation_and_query_never_verify(self):
        request = self._request()
        queried = self._result(request, status=OrderStatus.OPEN)
        contradictory = self._reconciliation(request, status=OrderStatus.UNKNOWN)
        outcome = interpret_protection_result(
            request,
            ProtectionResultEvidence(
                query_performed=True,
                queried_order=queried,
                reconciliation_result=contradictory,
            ),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )

        self.assertEqual(PositionEvent.STATE_UNKNOWN, outcome.event)
        self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, outcome.next_state)
        self.assertFalse(outcome.protection_verified)

    def test_partially_filled_and_filled_protective_exit_are_not_mislabeled_as_loss(self):
        request = self._request()
        cases = (
            (OrderStatus.PARTIALLY_FILLED, request.quantity / Decimal("2")),
            (OrderStatus.FILLED, request.quantity),
        )
        for status, filled_quantity in cases:
            with self.subTest(status=status):
                queried = self._result(
                    request,
                    status=status,
                    filled_quantity=filled_quantity,
                )
                outcome = interpret_protection_result(
                    request,
                    ProtectionResultEvidence(query_performed=True, queried_order=queried),
                    PositionLifecycleState.OPEN_PROTECTED,
                )
                self.assertEqual(PositionEvent.STATE_UNKNOWN, outcome.event)
                self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, outcome.next_state)
                self.assertNotEqual(PositionEvent.PROTECTION_LOST, outcome.event)
                self.assertNotEqual(PositionEvent.PROTECTION_FAILED, outcome.event)
                self.assertFalse(outcome.protection_verified)

    def test_repeated_identical_authoritative_evidence_is_deterministic(self):
        request = self._request()
        queried = self._result(request)
        evidence = ProtectionResultEvidence(query_performed=True, queried_order=queried)

        first = interpret_protection_result(
            request,
            evidence,
            PositionLifecycleState.OPEN_UNPROTECTED,
        )
        second = interpret_protection_result(
            request,
            evidence,
            PositionLifecycleState.OPEN_UNPROTECTED,
        )
        self.assertEqual(first, second)

    def test_malformed_non_protection_request_fails_closed(self):
        request = replace(self._request(), authorization_type=None)
        queried = self._result(request)
        outcome = interpret_protection_result(
            request,
            ProtectionResultEvidence(query_performed=True, queried_order=queried),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )
        self.assertEqual(PositionEvent.STATE_UNKNOWN, outcome.event)
        self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, outcome.next_state)
        self.assertFalse(outcome.protection_verified)

    def test_unreconciled_current_position_truth_never_verifies(self):
        request = self._request()
        queried = self._result(request)
        outcome = interpret_protection_result(
            request,
            ProtectionResultEvidence(
                query_performed=True,
                queried_order=queried,
                position_reconciliation_status="MISMATCH",
            ),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )
        self.assertEqual(PositionEvent.STATE_UNKNOWN, outcome.event)
        self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, outcome.next_state)
        self.assertFalse(outcome.protection_verified)

    def test_repeated_unknown_evidence_keeps_existing_reconciliation_state(self):
        request = self._request()
        outcome = interpret_protection_result(
            request,
            ProtectionResultEvidence(query_performed=False),
            PositionLifecycleState.RECONCILIATION_REQUIRED,
        )
        self.assertIsNone(outcome.event)
        self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, outcome.next_state)
        self.assertFalse(outcome.protection_verified)

    def test_bridge_has_no_broker_submit_query_or_retry_dependency(self):
        parameters = tuple(inspect.signature(interpret_protection_result).parameters)
        self.assertEqual(("request", "evidence", "current_state"), parameters)
        for forbidden in ("broker", "submit", "query", "retry", "provider", "sz"):
            self.assertNotIn(forbidden, parameters)

    def test_existing_state_machine_transition_remains_unchanged(self):
        state = transition(
            PositionLifecycleState.PENDING_ENTRY,
            PositionEvent.ENTRY_FILL_OBSERVED,
        )
        self.assertEqual(PositionLifecycleState.OPEN_UNPROTECTED, state)


if __name__ == "__main__":
    unittest.main()
