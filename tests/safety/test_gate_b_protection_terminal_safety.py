import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from position import build_protect_position_action
from src.brokers.paper import (
    InvalidOrderTransitionError,
    PaperBroker,
    UnknownOrderError,
)
from src.execution.models import OrderStatus
from src.execution.protection import prepare_protection_order


class GateBProtectionTerminalSafetyTests(unittest.TestCase):
    """Real PaperBroker terminal-state safety for canonical protection requests."""

    def setUp(self):
        self.created_at = datetime(2026, 8, 24, 4, 40, 0, tzinfo=timezone.utc)
        self.expires_at = datetime(2026, 8, 24, 4, 41, 0, tzinfo=timezone.utc)
        self.now = datetime(2026, 8, 24, 4, 40, 30, tzinfo=timezone.utc)

    def _request(self):
        plan = {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-gate-b-terminal-safety-001",
            "risk_decision_id": "risk-gate-b-terminal-safety-001",
            "intent_id": "intent-gate-b-terminal-safety-001",
            "strategy_id": "strategy-gate-b-terminal-safety",
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
            "risk_policy_version": "e5-gate-b-terminal-safety-policy-v0.1",
        }
        position = {
            "schema_version": "contracts-v0.1",
            "position_id": "position-gate-b-terminal-safety-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": "0.0012",
            "average_entry_price": "60000",
            "opened_at": "2026-08-24T04:39:00Z",
            "broker_state_observed_at": "2026-08-24T04:39:30Z",
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": "OPEN_UNPROTECTED",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }
        action = build_protect_position_action(
            position,
            plan,
            created_at=self.created_at,
            expires_at=self.expires_at,
        )
        return prepare_protection_order(action, plan, position, now=self.now)

    def test_unknown_order_cannot_be_canceled_or_expired(self):
        broker = PaperBroker()
        for terminalize in (broker.cancel_order, broker.expire_order):
            with self.subTest(operation=terminalize.__name__):
                with self.assertRaises(UnknownOrderError):
                    terminalize(
                        "missing-protection-order",
                        observed_at=self.now,
                    )

    def test_filled_protection_cannot_be_canceled_expired_or_reopened(self):
        request = self._request()
        broker = PaperBroker()
        broker.submit_order(request)
        broker.record_fill(
            request.client_order_id,
            quantity=request.quantity,
            price=Decimal("59390"),
            filled_at=self.now + timedelta(seconds=1),
        )
        self.assertEqual(
            OrderStatus.FILLED,
            broker.query_order(request.client_order_id).order_status,
        )

        for terminalize in (broker.cancel_order, broker.expire_order):
            with self.subTest(operation=terminalize.__name__):
                with self.assertRaises(InvalidOrderTransitionError):
                    terminalize(
                        request.client_order_id,
                        observed_at=self.now + timedelta(seconds=2),
                    )

        repeated_submit = broker.submit_order(request)
        self.assertEqual(OrderStatus.FILLED, repeated_submit.order_status)
        self.assertEqual(
            OrderStatus.FILLED,
            broker.query_order(request.client_order_id).order_status,
        )

    def test_partially_filled_protection_is_not_reclassified_as_terminal_failure(self):
        request = self._request()
        broker = PaperBroker()
        broker.submit_order(request)
        broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0004"),
            price=Decimal("59390"),
            filled_at=self.now + timedelta(seconds=1),
        )
        self.assertEqual(
            OrderStatus.PARTIALLY_FILLED,
            broker.query_order(request.client_order_id).order_status,
        )

        for terminalize in (broker.cancel_order, broker.expire_order):
            with self.subTest(operation=terminalize.__name__):
                with self.assertRaises(InvalidOrderTransitionError):
                    terminalize(
                        request.client_order_id,
                        observed_at=self.now + timedelta(seconds=2),
                    )

        self.assertEqual(
            OrderStatus.PARTIALLY_FILLED,
            broker.query_order(request.client_order_id).order_status,
        )

    def test_terminal_orders_do_not_reopen_and_cannot_receive_later_fill(self):
        scenarios = ("rejected", "canceled", "expired")
        for index, scenario in enumerate(scenarios, start=1):
            with self.subTest(scenario=scenario):
                request = self._request()
                if scenario == "rejected":
                    broker = PaperBroker(
                        rejected_outcomes={request.client_order_id: f"PAPER_REJECT_{index}"}
                    )
                    terminal = broker.submit_order(request)
                    expected = OrderStatus.REJECTED
                else:
                    broker = PaperBroker()
                    broker.submit_order(request)
                    terminal_at = self.now + timedelta(seconds=10 + index)
                    if scenario == "canceled":
                        terminal = broker.cancel_order(
                            request.client_order_id,
                            observed_at=terminal_at,
                        )
                        expected = OrderStatus.CANCELED
                    else:
                        terminal = broker.expire_order(
                            request.client_order_id,
                            observed_at=terminal_at,
                        )
                        expected = OrderStatus.EXPIRED

                self.assertEqual(expected, terminal.order_status)
                repeated_submit = broker.submit_order(request)
                self.assertEqual(expected, repeated_submit.order_status)
                self.assertEqual(
                    expected,
                    broker.query_order(request.client_order_id).order_status,
                )

                with self.assertRaises(InvalidOrderTransitionError):
                    broker.record_fill(
                        request.client_order_id,
                        quantity=Decimal("0.0001"),
                        price=Decimal("59390"),
                        filled_at=self.now + timedelta(seconds=20 + index),
                    )
                self.assertEqual(Decimal("0"), broker.query_position(request.symbol).net_quantity)


if __name__ == "__main__":
    unittest.main()
