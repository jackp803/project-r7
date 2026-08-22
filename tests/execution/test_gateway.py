import copy
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.execution.gateway import (
    AuthorityBoundaryError,
    ContractMismatchError,
    ExecutionGateway,
)
from src.execution.models import Side


def _approved_plan(now: datetime, *, direction: str = "LONG") -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "trade_plan_id": "plan-001",
        "risk_decision_id": "risk-001",
        "intent_id": "intent-001",
        "strategy_id": "strategy-001",
        "strategy_version": "v1",
        "symbol": "BTC_USDT_PERP",
        "direction": direction,
        "quantity": "0.010",
        "quantity_profile_version": "base-asset-v0.1",
        "quantity_unit": "BASE_ASSET",
        "quantity_asset": "BTC",
        "leverage": "2",
        "margin_mode": "ISOLATED",
        "entry_instruction": {
            "profile_version": "entry-v0.1",
            "order_type": "MARKET",
            "reference_price": "100000",
        },
        "protection_instruction": {"stop_level": "90000", "max_hold_seconds": 3600},
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
        "risk_policy_version": "risk-v1",
    }


class ExecutionGatewayTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 21, 0, 0, tzinfo=timezone.utc)
        self.gateway = ExecutionGateway()

    def test_valid_profiled_market_plan_translates_mechanically(self):
        request = self.gateway.prepare_entry_order(_approved_plan(self.now), now=self.now)
        self.assertEqual(request.side, Side.BUY)
        self.assertEqual(request.order_type, "MARKET")
        self.assertEqual(request.quantity, Decimal("0.010"))
        self.assertEqual(request.quantity_profile_version, "base-asset-v0.1")
        self.assertEqual(request.quantity_unit, "BASE_ASSET")
        self.assertEqual(request.quantity_asset, "BTC")

    def test_long_short_side_mapping(self):
        long_request = self.gateway.prepare_entry_order(_approved_plan(self.now, direction="LONG"), now=self.now)
        short_plan = _approved_plan(self.now, direction="SHORT")
        short_plan["trade_plan_id"] = "plan-002"
        short_request = self.gateway.prepare_entry_order(short_plan, now=self.now)
        self.assertEqual(long_request.side, Side.BUY)
        self.assertEqual(short_request.side, Side.SELL)

    def test_reference_price_is_advisory_only(self):
        request = self.gateway.prepare_entry_order(_approved_plan(self.now), now=self.now)
        self.assertIsNone(request.limit_price)
        self.assertIsNone(request.stop_price)
        self.assertIsNone(request.time_in_force)

    def test_strategy_trade_intent_cannot_cross_authority_boundary(self):
        raw_trade_intent = {
            "schema_version": "contracts-v0.1",
            "intent_id": "intent-001",
            "strategy_id": "strategy-001",
            "strategy_version": "v1",
            "symbol": "BTC_USDT_PERP",
            "direction": "LONG",
        }
        with self.assertRaises(AuthorityBoundaryError):
            self.gateway.prepare_entry_order(raw_trade_intent, now=self.now)

    def test_stable_client_order_id_for_same_logical_order(self):
        plan = _approved_plan(self.now)
        first = self.gateway.prepare_entry_order(plan, now=self.now)
        second = self.gateway.prepare_entry_order(plan, now=self.now + timedelta(seconds=1))
        self.assertEqual(first.client_order_id, second.client_order_id)
        self.assertEqual(first.order_request_id, second.order_request_id)

    def test_missing_or_unknown_quantity_profile_fails_closed(self):
        missing = _approved_plan(self.now)
        del missing["quantity_profile_version"]
        with self.assertRaises(AuthorityBoundaryError):
            self.gateway.prepare_entry_order(missing, now=self.now)

        unknown = _approved_plan(self.now)
        unknown["quantity_profile_version"] = "other-v9"
        with self.assertRaises(AuthorityBoundaryError):
            self.gateway.prepare_entry_order(unknown, now=self.now)

    def test_missing_or_unknown_entry_profile_fails_closed(self):
        missing = _approved_plan(self.now)
        del missing["entry_instruction"]["profile_version"]
        with self.assertRaises(ContractMismatchError):
            self.gateway.prepare_entry_order(missing, now=self.now)

        unknown = _approved_plan(self.now)
        unknown["entry_instruction"]["profile_version"] = "entry-v9"
        with self.assertRaises(ContractMismatchError):
            self.gateway.prepare_entry_order(unknown, now=self.now)

    def test_unsupported_entry_order_type_fails_closed(self):
        plan = _approved_plan(self.now)
        plan["entry_instruction"]["order_type"] = "LIMIT"
        with self.assertRaises(ContractMismatchError):
            self.gateway.prepare_entry_order(plan, now=self.now)

    def test_forbidden_executable_price_or_tif_fails_closed(self):
        for field, value in (("limit_price", "99000"), ("stop_price", "98000"), ("trigger_price", "97000"), ("time_in_force", "IOC")):
            with self.subTest(field=field):
                plan = _approved_plan(self.now)
                plan["entry_instruction"][field] = value
                with self.assertRaises(ContractMismatchError):
                    self.gateway.prepare_entry_order(plan, now=self.now)

    def test_malformed_quantity_and_expired_plan_fail_closed(self):
        malformed = _approved_plan(self.now)
        malformed["quantity"] = "not-a-number"
        with self.assertRaises(AuthorityBoundaryError):
            self.gateway.prepare_entry_order(malformed, now=self.now)

        expired = _approved_plan(self.now)
        with self.assertRaisesRegex(AuthorityBoundaryError, "expired"):
            self.gateway.prepare_entry_order(expired, now=self.now + timedelta(minutes=6))


if __name__ == "__main__":
    unittest.main()
