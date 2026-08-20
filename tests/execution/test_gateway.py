import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.execution.gateway import (
    AuthorityBoundaryError,
    ContractMismatchError,
    CurrentE5ProvisionalEntryTranslator,
    ExecutionGateway,
    TranslatedEntryInstruction,
)


class _TestOnlyTranslator:
    """Test seam only; it does not define shared E5/E4 instruction semantics."""

    def translate(self, plan):
        return TranslatedEntryInstruction(order_type="TEST_ORDER")


def _approved_plan(now: datetime) -> dict:
    return {
        "schema_version": "contracts-v0.1",
        "trade_plan_id": "plan-001",
        "risk_decision_id": "risk-001",
        "intent_id": "intent-001",
        "strategy_id": "strategy-001",
        "strategy_version": "v1",
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "quantity": "0.010",
        "leverage": "2",
        "margin_mode": "ISOLATED",
        "entry_instruction": {"style": "PROVISIONAL_STYLE"},
        "protection_instruction": {"stop_level": "90000", "max_hold_seconds": 3600},
        "created_at": now.isoformat().replace("+00:00", "Z"),
        "expires_at": (now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
        "risk_policy_version": "risk-v1",
    }


class ExecutionGatewayTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 21, 0, 0, tzinfo=timezone.utc)
        self.gateway = ExecutionGateway()

    def test_strategy_trade_intent_cannot_cross_authority_boundary(self):
        raw_trade_intent = {
            "schema_version": "contracts-v0.1",
            "intent_id": "intent-001",
            "strategy_id": "strategy-001",
            "strategy_version": "v1",
            "symbol": "BTCUSDT",
            "direction": "LONG",
        }
        with self.assertRaises(AuthorityBoundaryError):
            self.gateway.prepare_entry_order(
                raw_trade_intent,
                translator=_TestOnlyTranslator(),
                now=self.now,
            )

    def test_stable_client_order_id_for_same_logical_order(self):
        plan = _approved_plan(self.now)
        first = self.gateway.prepare_entry_order(
            plan,
            translator=_TestOnlyTranslator(),
            now=self.now,
        )
        second = self.gateway.prepare_entry_order(
            plan,
            translator=_TestOnlyTranslator(),
            now=self.now + timedelta(seconds=1),
        )
        self.assertEqual(first.client_order_id, second.client_order_id)
        self.assertEqual(first.order_request_id, second.order_request_id)
        self.assertEqual(first.quantity, Decimal("0.010"))
        self.assertEqual(second.quantity, Decimal("0.010"))

    def test_current_e5_nested_entry_shape_fails_closed_as_contract_mismatch(self):
        plan = _approved_plan(self.now)
        with self.assertRaisesRegex(ContractMismatchError, "CONTRACT MISMATCH"):
            self.gateway.prepare_entry_order(
                plan,
                translator=CurrentE5ProvisionalEntryTranslator(),
                now=self.now,
            )

    def test_expired_approved_plan_is_rejected(self):
        plan = _approved_plan(self.now)
        with self.assertRaisesRegex(AuthorityBoundaryError, "expired"):
            self.gateway.prepare_entry_order(
                plan,
                translator=_TestOnlyTranslator(),
                now=self.now + timedelta(minutes=6),
            )


if __name__ == "__main__":
    unittest.main()
