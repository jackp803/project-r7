import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.brokers.paper import (
    IdempotencyConflictError,
    InvalidOrderTransitionError,
    PaperBroker,
    UnknownOrderError,
)
from src.execution.models import (
    SCHEMA_VERSION,
    ExecutionHealthStatus,
    OrderRequest,
    OrderStatus,
    Side,
    stable_client_order_id,
    stable_order_request_id,
    stable_position_action_client_order_id,
)


class PaperBrokerProtectionTerminalTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 24, 4, 15, 0, tzinfo=timezone.utc)

    def _protection_request(
        self,
        *,
        position_action_id: str = "posact-paper-terminal-001",
        quantity: str = "0.0012",
        side: Side = Side.SELL,
    ) -> OrderRequest:
        client_order_id = stable_position_action_client_order_id(
            position_action_id,
            "PROTECTION_STOP",
        )
        return OrderRequest(
            schema_version=SCHEMA_VERSION,
            order_request_id=stable_order_request_id(client_order_id),
            trade_plan_id="plan-paper-terminal-001",
            client_order_id=client_order_id,
            symbol="BTC_USDT_PERP",
            side=side,
            order_type="STOP_MARKET",
            quantity=Decimal(quantity),
            quantity_profile_version="base-asset-v0.1",
            quantity_unit="BASE_ASSET",
            quantity_asset="BTC",
            created_at=self.now,
            authorization_type="POSITION_ACTION",
            position_action_id=position_action_id,
            position_id="position-paper-terminal-001",
            risk_decision_id="risk-paper-terminal-001",
            order_role="PROTECTION_STOP",
            limit_price=None,
            stop_price=Decimal("59400"),
            reduce_only=True,
            time_in_force=None,
        )

    def _entry_request(self) -> OrderRequest:
        client_order_id = stable_client_order_id("plan-entry-compat", "entry")
        return OrderRequest(
            schema_version=SCHEMA_VERSION,
            order_request_id=stable_order_request_id(client_order_id),
            trade_plan_id="plan-entry-compat",
            client_order_id=client_order_id,
            symbol="BTC_USDT_PERP",
            side=Side.BUY,
            order_type="MARKET",
            quantity=Decimal("0.002"),
            quantity_profile_version="base-asset-v0.1",
            quantity_unit="BASE_ASSET",
            quantity_asset="BTC",
            created_at=self.now,
        )

    def test_configured_exact_protection_rejection_is_queryable_healthy_and_zero_exposure(self):
        request = self._protection_request()
        broker = PaperBroker(
            rejected_outcomes={request.client_order_id: "PAPER_SIMULATED_REJECTION"}
        )

        result = broker.submit_order(request)
        queried = broker.query_order(request.client_order_id)

        self.assertEqual(OrderStatus.REJECTED, result.order_status)
        self.assertEqual(ExecutionHealthStatus.HEALTHY, result.execution_health_status)
        self.assertEqual(request.order_request_id, result.order_request_id)
        self.assertEqual(request.client_order_id, result.client_order_id)
        self.assertEqual(request.quantity, result.requested_quantity)
        self.assertEqual(Decimal("0"), result.filled_quantity)
        self.assertIsNone(result.broker_order_id)
        self.assertEqual(result, queried)
        self.assertEqual(Decimal("0"), broker.query_position(request.symbol).net_quantity)
        self.assertEqual((), broker.query_fills(request.client_order_id))

    def test_repeated_identical_rejected_submit_is_idempotent_and_changed_request_conflicts(self):
        request = self._protection_request()
        broker = PaperBroker(
            rejected_outcomes={request.client_order_id: "PAPER_SIMULATED_REJECTION"}
        )
        first = broker.submit_order(request)
        second = broker.submit_order(request)
        self.assertEqual(first, second)
        self.assertEqual(OrderStatus.REJECTED, second.order_status)

        changed = replace(request, quantity=Decimal("0.0011"))
        with self.assertRaises(IdempotencyConflictError):
            broker.submit_order(changed)
        self.assertEqual(OrderStatus.REJECTED, broker.query_order(request.client_order_id).order_status)
        self.assertEqual(Decimal("0"), broker.query_position(request.symbol).net_quantity)

    def test_open_to_canceled_preserves_identity_quantity_health_and_observation(self):
        request = self._protection_request()
        broker = PaperBroker()
        opened = broker.submit_order(request)
        observed_at = self.now + timedelta(seconds=5)

        canceled = broker.cancel_order(request.client_order_id, observed_at=observed_at)

        self.assertEqual(OrderStatus.OPEN, opened.order_status)
        self.assertEqual(OrderStatus.CANCELED, canceled.order_status)
        self.assertEqual(opened.order_request_id, canceled.order_request_id)
        self.assertEqual(opened.client_order_id, canceled.client_order_id)
        self.assertEqual(opened.broker_order_id, canceled.broker_order_id)
        self.assertTrue(canceled.broker_order_id)
        self.assertEqual(opened.requested_quantity, canceled.requested_quantity)
        self.assertEqual(opened.filled_quantity, canceled.filled_quantity)
        self.assertEqual(ExecutionHealthStatus.HEALTHY, canceled.execution_health_status)
        self.assertEqual(observed_at, canceled.observed_at)
        self.assertEqual(canceled, broker.query_order(request.client_order_id))

        repeated = broker.cancel_order(
            request.client_order_id,
            observed_at=observed_at + timedelta(seconds=1),
        )
        self.assertEqual(canceled, repeated)
        self.assertEqual(canceled, broker.submit_order(request))

    def test_open_to_expired_preserves_identity_quantity_health_and_observation(self):
        request = self._protection_request(position_action_id="posact-paper-terminal-expire")
        broker = PaperBroker()
        opened = broker.submit_order(request)
        observed_at = self.now + timedelta(seconds=7)

        expired = broker.expire_order(request.client_order_id, observed_at=observed_at)

        self.assertEqual(OrderStatus.EXPIRED, expired.order_status)
        self.assertEqual(opened.order_request_id, expired.order_request_id)
        self.assertEqual(opened.client_order_id, expired.client_order_id)
        self.assertEqual(opened.broker_order_id, expired.broker_order_id)
        self.assertTrue(expired.broker_order_id)
        self.assertEqual(opened.requested_quantity, expired.requested_quantity)
        self.assertEqual(opened.filled_quantity, expired.filled_quantity)
        self.assertEqual(ExecutionHealthStatus.HEALTHY, expired.execution_health_status)
        self.assertEqual(observed_at, expired.observed_at)
        self.assertEqual(expired, broker.query_order(request.client_order_id))

        repeated = broker.expire_order(
            request.client_order_id,
            observed_at=observed_at + timedelta(seconds=1),
        )
        self.assertEqual(expired, repeated)
        self.assertEqual(expired, broker.submit_order(request))

    def test_definitive_terminal_truth_reconciles_without_retry_token(self):
        cases = (OrderStatus.REJECTED, OrderStatus.CANCELED, OrderStatus.EXPIRED)
        for index, expected in enumerate(cases, start=1):
            with self.subTest(expected=expected):
                request = self._protection_request(
                    position_action_id=f"posact-terminal-reconcile-{index}"
                )
                if expected == OrderStatus.REJECTED:
                    broker = PaperBroker(
                        rejected_outcomes={request.client_order_id: "PAPER_REJECT"}
                    )
                    broker.submit_order(request)
                else:
                    broker = PaperBroker()
                    broker.submit_order(request)
                    observed_at = self.now + timedelta(seconds=10 + index)
                    if expected == OrderStatus.CANCELED:
                        broker.cancel_order(request.client_order_id, observed_at=observed_at)
                    else:
                        broker.expire_order(request.client_order_id, observed_at=observed_at)

                order_snapshot = broker.query_order(request.client_order_id)
                position_snapshot = broker.query_position(request.symbol)
                reconciliation = broker.reconcile(
                    request,
                    order_snapshot=order_snapshot,
                    position_snapshot=position_snapshot,
                )
                self.assertEqual(expected, reconciliation.resolved_status)
                self.assertFalse(reconciliation.retry_allowed)
                self.assertIsNone(reconciliation.retry_token)

    def test_unknown_order_terminal_operations_fail_explicitly(self):
        broker = PaperBroker()
        with self.assertRaises(UnknownOrderError):
            broker.cancel_order("missing-client", observed_at=self.now)
        with self.assertRaises(UnknownOrderError):
            broker.expire_order("missing-client", observed_at=self.now)

    def test_filled_protection_order_cannot_be_canceled_or_expired_or_reopened(self):
        request = self._protection_request(position_action_id="posact-filled-terminal")
        broker = PaperBroker()
        broker.submit_order(request)
        broker.record_fill(
            request.client_order_id,
            quantity=request.quantity,
            price=Decimal("59390"),
            filled_at=self.now + timedelta(seconds=2),
        )
        self.assertEqual(OrderStatus.FILLED, broker.query_order(request.client_order_id).order_status)

        with self.assertRaises(InvalidOrderTransitionError):
            broker.cancel_order(
                request.client_order_id,
                observed_at=self.now + timedelta(seconds=3),
            )
        with self.assertRaises(InvalidOrderTransitionError):
            broker.expire_order(
                request.client_order_id,
                observed_at=self.now + timedelta(seconds=3),
            )
        self.assertEqual(OrderStatus.FILLED, broker.submit_order(request).order_status)

    def test_partially_filled_protection_is_not_reclassified_as_failure_or_loss(self):
        request = self._protection_request(position_action_id="posact-partial-terminal")
        broker = PaperBroker()
        broker.submit_order(request)
        broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0004"),
            price=Decimal("59390"),
            filled_at=self.now + timedelta(seconds=2),
        )
        partial = broker.query_order(request.client_order_id)
        self.assertEqual(OrderStatus.PARTIALLY_FILLED, partial.order_status)

        with self.assertRaises(InvalidOrderTransitionError):
            broker.cancel_order(
                request.client_order_id,
                observed_at=self.now + timedelta(seconds=3),
            )
        with self.assertRaises(InvalidOrderTransitionError):
            broker.expire_order(
                request.client_order_id,
                observed_at=self.now + timedelta(seconds=3),
            )
        self.assertEqual(
            OrderStatus.PARTIALLY_FILLED,
            broker.query_order(request.client_order_id).order_status,
        )

    def test_terminal_orders_cannot_receive_later_fills_or_create_exposure(self):
        scenarios = ("rejected", "canceled", "expired")
        for index, scenario in enumerate(scenarios, start=1):
            with self.subTest(scenario=scenario):
                request = self._protection_request(
                    position_action_id=f"posact-no-terminal-fill-{index}"
                )
                if scenario == "rejected":
                    broker = PaperBroker(
                        rejected_outcomes={request.client_order_id: "PAPER_REJECT"}
                    )
                    broker.submit_order(request)
                else:
                    broker = PaperBroker()
                    broker.submit_order(request)
                    terminal_at = self.now + timedelta(seconds=3)
                    if scenario == "canceled":
                        broker.cancel_order(request.client_order_id, observed_at=terminal_at)
                    else:
                        broker.expire_order(request.client_order_id, observed_at=terminal_at)

                with self.assertRaises(InvalidOrderTransitionError):
                    broker.record_fill(
                        request.client_order_id,
                        quantity=Decimal("0.0001"),
                        price=Decimal("59390"),
                        filled_at=self.now + timedelta(seconds=4),
                    )
                self.assertEqual(Decimal("0"), broker.query_position(request.symbol).net_quantity)

    def test_existing_ambiguous_accepted_reconciliation_path_remains_compatible(self):
        request = self._protection_request(position_action_id="posact-ambiguous-compat")
        broker = PaperBroker(ambiguous_outcomes={request.client_order_id: True})
        submit = broker.submit_order(request)
        self.assertEqual(OrderStatus.RECONCILIATION_REQUIRED, submit.order_status)

        order_snapshot = broker.query_order(request.client_order_id)
        position_snapshot = broker.query_position(request.symbol)
        self.assertIsNotNone(order_snapshot)
        self.assertEqual(OrderStatus.OPEN, order_snapshot.order_status)
        reconciliation = broker.reconcile(
            request,
            order_snapshot=order_snapshot,
            position_snapshot=position_snapshot,
        )
        self.assertEqual(OrderStatus.OPEN, reconciliation.resolved_status)
        self.assertFalse(reconciliation.retry_allowed)
        self.assertIsNone(reconciliation.retry_token)

    def test_existing_entry_and_fill_behavior_remains_compatible(self):
        request = self._entry_request()
        broker = PaperBroker()
        opened = broker.submit_order(request)
        self.assertEqual(OrderStatus.OPEN, opened.order_status)
        broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.001"),
            price=Decimal("60000"),
            filled_at=self.now + timedelta(seconds=1),
        )
        partial = broker.query_order(request.client_order_id)
        self.assertEqual(OrderStatus.PARTIALLY_FILLED, partial.order_status)
        self.assertEqual(Decimal("0.001"), partial.filled_quantity)
        self.assertEqual(request.quantity, partial.requested_quantity)

    def test_paper_terminal_surface_introduces_no_provider_native_or_credential_fields(self):
        request = self._protection_request(position_action_id="posact-provider-neutral")
        forbidden = {
            "sz",
            "instId",
            "clOrdId",
            "ctVal",
            "lotSz",
            "api_key",
            "secret_key",
            "passphrase",
            "credentials",
        }
        self.assertTrue(forbidden.isdisjoint(vars(request)))

        broker = PaperBroker()
        broker.submit_order(request)
        canceled = broker.cancel_order(
            request.client_order_id,
            observed_at=self.now + timedelta(seconds=1),
        )
        self.assertTrue(forbidden.isdisjoint(vars(canceled)))


if __name__ == "__main__":
    unittest.main()
