import unittest
from datetime import datetime, timezone
from decimal import Decimal

from risk import (
    RiskContext,
    RiskInputError,
    RiskPolicy,
    RiskProposal,
    build_approved_trade_plan,
    evaluate_trade_intent,
)


def policy():
    return RiskPolicy(
        version="e5-test-policy-v0.1",
        max_margin=Decimal("10"),
        max_notional=Decimal("200"),
        max_leverage=Decimal("20"),
        min_reward_risk=Decimal("2"),
        max_estimated_cost=Decimal("1"),
        max_trades_per_day=1,
        max_open_positions=1,
        max_drawdown=Decimal("0.10"),
        max_consecutive_losses=5,
        max_intent_age_seconds=60,
        max_hold_seconds=3600,
        plan_ttl_seconds=30,
        margin_mode="ISOLATED",
    )


def intent():
    return {
        "schema_version": "contracts-v0.1",
        "intent_id": "intent-001",
        "signal_id": "signal-001",
        "strategy_id": "strategy-001",
        "strategy_version": "1.0.0",
        "symbol": "BTC_USDT_PERP",
        "direction": "LONG",
        "generated_at": "2026-08-20T04:00:00Z",
        "market_boundary_ref": "sha256:boundary",
        "entry_style": "MARKET",
        "entry_reference_price": "60000",
        "strategy_stop_level": "59400",
        "strategy_target_level": "61200",
        "max_hold_seconds": 1800,
    }


def context(**changes):
    values = {
        "market_health_status": "HEALTHY",
        "market_data_fresh": True,
        "account_state_status": "KNOWN",
        "account_state_known": True,
        "position_state_status": "FLAT",
        "position_state_known": True,
        "order_state_status": "KNOWN",
        "order_state_known": True,
        "kill_switch_active": False,
        "new_exposure_allowed": True,
        "trades_today": 0,
        "open_position_count": 0,
        "same_symbol_position_open": False,
        "consecutive_losses": 0,
        "drawdown": Decimal("0.02"),
        "available_balance": Decimal("100"),
    }
    values.update(changes)
    return RiskContext(**values)


def proposal(**changes):
    values = {
        "quantity": Decimal("0.003"),
        "notional": Decimal("180"),
        "margin": Decimal("9"),
        "leverage": Decimal("20"),
        "estimated_max_loss": Decimal("4"),
        "estimated_cost": Decimal("0.5"),
        "reward_amount": Decimal("10"),
        "required_stop_level": Decimal("59400"),
        "required_target_level": Decimal("61200"),
    }
    values.update(changes)
    return RiskProposal(**values)


class RiskEngineTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 20, 4, 0, 10, tzinfo=timezone.utc)

    def test_valid_intent_can_be_approved_and_planned(self):
        decision = evaluate_trade_intent(intent(), context(), proposal(), policy(), decided_at=self.now)
        self.assertEqual("APPROVE", decision["decision"])
        self.assertEqual([], decision["reason_codes"])
        plan = build_approved_trade_plan(intent(), decision, policy(), created_at=self.now)
        self.assertEqual(decision["risk_decision_id"], plan["risk_decision_id"])
        self.assertEqual("0.003", plan["quantity"])
        self.assertEqual("20", plan["leverage"])
        self.assertEqual("59400", plan["protection_instruction"]["stop_level"])

    def test_unknown_account_fails_closed(self):
        decision = evaluate_trade_intent(
            intent(), context(account_state_known=False, account_state_status="UNKNOWN"), proposal(), policy(), decided_at=self.now
        )
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("ACCOUNT_STATE_UNKNOWN", decision["reason_codes"])

    def test_trade_intent_cannot_smuggle_approved_authority(self):
        payload = intent()
        payload["approved_quantity"] = "10"
        decision = evaluate_trade_intent(payload, context(), proposal(), policy(), decided_at=self.now)
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("TRADE_INTENT_UNDECLARED_FIELD", decision["reason_codes"])

    def test_missing_stop_fails_closed(self):
        decision = evaluate_trade_intent(
            intent(), context(), proposal(required_stop_level=None), policy(), decided_at=self.now
        )
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("PROTECTIVE_STOP_REQUIRED", decision["reason_codes"])

    def test_rejected_decision_cannot_create_plan(self):
        decision = evaluate_trade_intent(
            intent(), context(kill_switch_active=True), proposal(), policy(), decided_at=self.now
        )
        with self.assertRaises(RiskInputError):
            build_approved_trade_plan(intent(), decision, policy(), created_at=self.now)

    def test_cost_adjusted_reward_risk_is_enforced(self):
        decision = evaluate_trade_intent(
            intent(), context(), proposal(estimated_max_loss=Decimal("4.5"), estimated_cost=Decimal("0.5"), reward_amount=Decimal("9")), policy(), decided_at=self.now
        )
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("REWARD_RISK_BELOW_MINIMUM", decision["reason_codes"])


if __name__ == "__main__":
    unittest.main()
