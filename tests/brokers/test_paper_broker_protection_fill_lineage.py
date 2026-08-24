import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.brokers.paper import (
    ExposureLimitError,
    InvalidOrderTransitionError,
    PaperBroker,
)
from src.execution.models import (
    SCHEMA_VERSION,
    OrderRequest,
    OrderStatus,
    Side,
    stable_client_order_id,
    stable_order_request_id,
    stable_position_action_client_order_id,
)


class PaperBrokerProtectionFillLineageTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 24, 4, 35, 0, tzinfo=timezone.utc)

    def _protection_request(
        self,
        *,
        position_action_id: str = "posact-fill-lineage-001",
        position_id: str = "position-fill-lineage-001",
        trade_plan_id: str = "plan-fill-lineage-001",
        side: Side = Side.SELL,
        quantity: str = "0.0012",
    ) -> OrderRequest:
        client_order_id = stable_position_action_client_order_id(
            position_action_id,
            "PROTECTION_STOP",
        )
        return OrderRequest(
            schema_version=SCHEMA_VERSION,
            order_request_id=stable_order_request_id(client_order_id),
            trade_plan_id=trade_plan_id,
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
            position_id=position_id,
            risk_decision_id="risk-fill-lineage-001",
            order_role="PROTECTION_STOP",
            stop_price=Decimal("59400"),
            reduce_only=True,
        )

    def _entry_request(self) -> OrderRequest:
        client_order_id = stable_client_order_id("plan-entry-fill-lineage", "entry")
        return OrderRequest(
            schema_version=SCHEMA_VERSION,
            order_request_id=stable_order_request_id(client_order_id),
            trade_plan_id="plan-entry-fill-lineage",
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

    def test_partial_protection_fill_copies_exact_request_lineage_and_actual_facts(self):
        request = self._protection_request()
        broker = PaperBroker()
        broker.submit_order(request)

        fill = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0004"),
            price=Decimal("59390"),
            filled_at=self.now + timedelta(seconds=1),
            fee=Decimal("0.000001"),
            fee_currency="BTC",
            liquidity_role="TAKER",
        )

        self.assertEqual(request.trade_plan_id, fill.trade_plan_id)
        self.assertEqual(request.position_action_id, fill.position_action_id)
        self.assertEqual(request.position_id, fill.position_id)
        self.assertEqual("PROTECTION_STOP", fill.order_role)
        self.assertEqual(request.side, fill.side)
        self.assertEqual(Decimal("0.0004"), fill.quantity)
        self.assertEqual(Decimal("59390"), fill.price)
        self.assertEqual(self.now + timedelta(seconds=1), fill.filled_at)
        self.assertEqual(Decimal("0.000001"), fill.fee)
        self.assertEqual("BTC", fill.fee_currency)
        self.assertEqual("TAKER", fill.liquidity_role)

        result = broker.query_order(request.client_order_id)
        self.assertEqual(OrderStatus.PARTIALLY_FILLED, result.order_status)
        self.assertEqual(Decimal("0.0004"), result.filled_quantity)
        self.assertEqual(request.quantity, result.requested_quantity)

    def test_subsequent_full_fill_retains_same_lineage_and_exact_per_fill_quantities(self):
        request = self._protection_request(quantity="0.0012")
        broker = PaperBroker()
        broker.submit_order(request)

        first = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0004"),
            price=Decimal("59390"),
            filled_at=self.now + timedelta(seconds=1),
        )
        second = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0008"),
            price=Decimal("59380"),
            filled_at=self.now + timedelta(seconds=2),
        )

        for fill in (first, second):
            self.assertEqual(request.trade_plan_id, fill.trade_plan_id)
            self.assertEqual(request.position_action_id, fill.position_action_id)
            self.assertEqual(request.position_id, fill.position_id)
            self.assertEqual(request.order_role, fill.order_role)

        self.assertEqual(Decimal("0.0004"), first.quantity)
        self.assertEqual(Decimal("0.0008"), second.quantity)
        self.assertEqual(request.quantity, first.quantity + second.quantity)
        self.assertEqual(OrderStatus.FILLED, broker.query_order(request.client_order_id).order_status)
        self.assertEqual(request.quantity, broker.query_order(request.client_order_id).filled_quantity)

    def test_query_fills_preserves_lineage_order_and_objects(self):
        request = self._protection_request(position_action_id="posact-query-lineage")
        broker = PaperBroker()
        broker.submit_order(request)
        first = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0003"),
            price=Decimal("59390"),
            filled_at=self.now + timedelta(seconds=1),
        )
        second = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0009"),
            price=Decimal("59380"),
            filled_at=self.now + timedelta(seconds=2),
        )

        queried_once = broker.query_fills(request.client_order_id)
        queried_twice = broker.query_fills(request.client_order_id)

        self.assertEqual((first, second), queried_once)
        self.assertEqual(queried_once, queried_twice)
        self.assertEqual([first.fill_id, second.fill_id], [fill.fill_id for fill in queried_once])
        for fill in queried_once:
            self.assertEqual(request.position_action_id, fill.position_action_id)
            self.assertEqual(request.position_id, fill.position_id)
            self.assertEqual("PROTECTION_STOP", fill.order_role)

    def test_long_sell_and_short_buy_protection_requests_preserve_lineage_identically(self):
        cases = (
            (Side.SELL, "posact-long-sell", "position-long"),
            (Side.BUY, "posact-short-buy", "position-short"),
        )
        for index, (side, action_id, position_id) in enumerate(cases, start=1):
            with self.subTest(side=side):
                request = self._protection_request(
                    position_action_id=action_id,
                    position_id=position_id,
                    trade_plan_id=f"plan-side-{index}",
                    side=side,
                )
                broker = PaperBroker()
                broker.submit_order(request)
                fill = broker.record_fill(
                    request.client_order_id,
                    quantity=Decimal("0.0002"),
                    price=Decimal("59390"),
                    filled_at=self.now + timedelta(seconds=index),
                )
                self.assertEqual(side, fill.side)
                self.assertEqual(request.trade_plan_id, fill.trade_plan_id)
                self.assertEqual(action_id, fill.position_action_id)
                self.assertEqual(position_id, fill.position_id)
                self.assertEqual("PROTECTION_STOP", fill.order_role)

    def test_entry_fill_keeps_trade_plan_lineage_without_inventing_protection_lineage(self):
        request = self._entry_request()
        broker = PaperBroker()
        broker.submit_order(request)
        fill = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.001"),
            price=Decimal("60000"),
            filled_at=self.now + timedelta(seconds=1),
        )

        self.assertEqual(request.trade_plan_id, fill.trade_plan_id)
        self.assertIsNone(fill.position_action_id)
        self.assertIsNone(fill.position_id)
        self.assertIsNone(fill.order_role)

    def test_total_fills_cannot_exceed_request_quantity(self):
        request = self._protection_request(quantity="0.0012")
        broker = PaperBroker()
        broker.submit_order(request)
        broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0008"),
            price=Decimal("59390"),
            filled_at=self.now + timedelta(seconds=1),
        )
        with self.assertRaises(ExposureLimitError):
            broker.record_fill(
                request.client_order_id,
                quantity=Decimal("0.0005"),
                price=Decimal("59380"),
                filled_at=self.now + timedelta(seconds=2),
            )

        queried = broker.query_fills(request.client_order_id)
        self.assertEqual(1, len(queried))
        self.assertEqual(Decimal("0.0008"), queried[0].quantity)
        self.assertEqual(Decimal("0.0008"), broker.query_order(request.client_order_id).filled_quantity)

    def test_rejected_canceled_and_expired_orders_still_cannot_receive_fills(self):
        scenarios = ("rejected", "canceled", "expired")
        for index, scenario in enumerate(scenarios, start=1):
            with self.subTest(scenario=scenario):
                request = self._protection_request(
                    position_action_id=f"posact-terminal-fill-lineage-{index}"
                )
                if scenario == "rejected":
                    broker = PaperBroker(
                        rejected_outcomes={request.client_order_id: "PAPER_REJECT"}
                    )
                    broker.submit_order(request)
                else:
                    broker = PaperBroker()
                    broker.submit_order(request)
                    observed_at = self.now + timedelta(seconds=1)
                    if scenario == "canceled":
                        broker.cancel_order(request.client_order_id, observed_at=observed_at)
                    else:
                        broker.expire_order(request.client_order_id, observed_at=observed_at)

                with self.assertRaises(InvalidOrderTransitionError):
                    broker.record_fill(
                        request.client_order_id,
                        quantity=Decimal("0.0001"),
                        price=Decimal("59390"),
                        filled_at=self.now + timedelta(seconds=2),
                    )
                self.assertEqual((), broker.query_fills(request.client_order_id))

    def test_ambiguous_accepted_reconciliation_behavior_remains_compatible(self):
        request = self._protection_request(position_action_id="posact-ambiguous-lineage")
        broker = PaperBroker(ambiguous_outcomes={request.client_order_id: True})
        submit = broker.submit_order(request)
        self.assertEqual(OrderStatus.RECONCILIATION_REQUIRED, submit.order_status)

        order_snapshot = broker.query_order(request.client_order_id)
        position_snapshot = broker.query_position(request.symbol)
        reconciliation = broker.reconcile(
            request,
            order_snapshot=order_snapshot,
            position_snapshot=position_snapshot,
        )
        self.assertEqual(OrderStatus.OPEN, reconciliation.resolved_status)
        self.assertFalse(reconciliation.retry_allowed)
        self.assertIsNone(reconciliation.retry_token)

    def test_fill_lineage_surface_is_provider_neutral_and_contains_no_credentials(self):
        request = self._protection_request(position_action_id="posact-provider-neutral-lineage")
        broker = PaperBroker()
        broker.submit_order(request)
        fill = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0002"),
            price=Decimal("59390"),
            filled_at=self.now + timedelta(seconds=1),
        )

        forbidden = {
            "sz",
            "instId",
            "clOrdId",
            "ctVal",
            "ctMult",
            "lotSz",
            "api_key",
            "secret_key",
            "passphrase",
            "credentials",
        }
        self.assertTrue(forbidden.isdisjoint(vars(fill)))


if __name__ == "__main__":
    unittest.main()
