import unittest
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

from src.brokers.paper import (
    ExposureLimitError,
    IdempotencyConflictError,
    PaperBroker,
    ReconciliationRequiredError,
)
from src.execution.models import (
    SCHEMA_VERSION,
    OrderRequest,
    OrderStatus,
    Side,
    stable_client_order_id,
    stable_order_request_id,
)


def _request(quantity: str = "1.0") -> OrderRequest:
    client_order_id = stable_client_order_id("plan-001", "entry")
    return OrderRequest(
        schema_version=SCHEMA_VERSION,
        order_request_id=stable_order_request_id(client_order_id),
        trade_plan_id="plan-001",
        client_order_id=client_order_id,
        symbol="BTCUSDT",
        side=Side.BUY,
        order_type="TEST_ORDER",
        quantity=Decimal(quantity),
        created_at=datetime(2026, 8, 21, 0, 0, tzinfo=timezone.utc),
    )


class PaperBrokerTests(unittest.TestCase):
    def test_partial_fill_keeps_requested_and_filled_quantity_distinct(self):
        request = _request("1.0")
        broker = PaperBroker()
        broker.submit_order(request)
        broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.4"),
            price=Decimal("100000"),
            filled_at=datetime(2026, 8, 21, 0, 1, tzinfo=timezone.utc),
        )
        result = broker.query_order(request.client_order_id)
        self.assertIsNotNone(result)
        self.assertEqual(result.order_status, OrderStatus.PARTIALLY_FILLED)
        self.assertEqual(result.requested_quantity, Decimal("1.0"))
        self.assertEqual(result.filled_quantity, Decimal("0.4"))

    def test_fill_cannot_increase_exposure_beyond_approved_request(self):
        request = _request("1.0")
        broker = PaperBroker()
        broker.submit_order(request)
        with self.assertRaises(ExposureLimitError):
            broker.record_fill(
                request.client_order_id,
                quantity=Decimal("1.1"),
                price=Decimal("100000"),
                filled_at=datetime(2026, 8, 21, 0, 1, tzinfo=timezone.utc),
            )

    def test_same_client_id_with_different_payload_is_idempotency_conflict(self):
        request = _request("1.0")
        broker = PaperBroker()
        broker.submit_order(request)
        changed = replace(request, quantity=Decimal("2.0"))
        with self.assertRaises(IdempotencyConflictError):
            broker.submit_order(changed)

    def test_ambiguous_ack_does_not_blind_duplicate_submit_when_order_exists(self):
        request = _request("1.0")
        broker = PaperBroker(ambiguous_outcomes={request.client_order_id: True})
        first = broker.submit_order(request)
        second = broker.submit_order(request)
        self.assertEqual(first.order_status, OrderStatus.RECONCILIATION_REQUIRED)
        self.assertEqual(second, first)

        order_snapshot = broker.query_order(request.client_order_id)
        position_snapshot = broker.query_position(request.symbol)
        reconciliation = broker.reconcile(
            request,
            order_snapshot=order_snapshot,
            position_snapshot=position_snapshot,
        )
        self.assertFalse(reconciliation.retry_allowed)
        self.assertEqual(reconciliation.reason, "BROKER_ORDER_FOUND_NO_RETRY")

    def test_retry_requires_query_and_reconcile_evidence(self):
        request = _request("1.0")
        broker = PaperBroker(ambiguous_outcomes={request.client_order_id: False})
        ambiguous = broker.submit_order(request)
        self.assertEqual(ambiguous.order_status, OrderStatus.RECONCILIATION_REQUIRED)

        with self.assertRaises(ReconciliationRequiredError):
            broker.retry_order(
                request,
                reconciliation=type("Fake", (), {
                    "retry_allowed": True,
                    "client_order_id": request.client_order_id,
                    "retry_token": "fake",
                })(),
            )

        order_snapshot = broker.query_order(request.client_order_id)
        position_snapshot = broker.query_position(request.symbol)
        reconciliation = broker.reconcile(
            request,
            order_snapshot=order_snapshot,
            position_snapshot=position_snapshot,
        )
        self.assertTrue(reconciliation.retry_allowed)
        retried = broker.retry_order(request, reconciliation=reconciliation)
        self.assertEqual(retried.order_status, OrderStatus.OPEN)

    def test_reconciliation_rejects_fabricated_query_evidence(self):
        request = _request("1.0")
        broker = PaperBroker(ambiguous_outcomes={request.client_order_id: True})
        broker.submit_order(request)
        actual_position = broker.query_position(request.symbol)
        with self.assertRaises(ReconciliationRequiredError):
            broker.reconcile(
                request,
                order_snapshot=None,
                position_snapshot=actual_position,
            )


if __name__ == "__main__":
    unittest.main()
