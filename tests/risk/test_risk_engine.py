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
        "entry_profile_version": "entry-v0.1",
        "entry_order_type": "MARKET",
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

    def _decision(self, *, risk_policy=None, trade_intent=None, **context_changes):
        return evaluate_trade_intent(
            intent() if trade_intent is None else trade_intent,
            context(**context_changes),
            proposal(),
            policy() if risk_policy is None else risk_policy,
            decided_at=self.now,
        )

    def test_valid_profiled_intent_can_be_approved_and_planned(self):
        decision = evaluate_trade_intent(intent(), context(), proposal(), policy(), decided_at=self.now)
        self.assertEqual("APPROVE", decision["decision"])
        self.assertEqual([], decision["reason_codes"])

        plan = build_approved_trade_plan(intent(), decision, policy(), created_at=self.now)
        self.assertEqual(decision["risk_decision_id"], plan["risk_decision_id"])
        self.assertEqual("0.003", plan["quantity"])
        self.assertEqual("base-asset-v0.1", plan["quantity_profile_version"])
        self.assertEqual("BASE_ASSET", plan["quantity_unit"])
        self.assertEqual("BTC", plan["quantity_asset"])
        self.assertEqual("20", plan["leverage"])
        self.assertEqual("entry-v0.1", plan["entry_instruction"]["profile_version"])
        self.assertEqual("MARKET", plan["entry_instruction"]["order_type"])
        self.assertEqual("60000", plan["entry_instruction"]["reference_price"])
        self.assertNotIn("style", plan["entry_instruction"])
        self.assertNotIn("limit_price", plan["entry_instruction"])
        self.assertNotIn("stop_price", plan["entry_instruction"])
        self.assertEqual("59400", plan["protection_instruction"]["stop_level"])

    def test_unknown_account_fails_closed(self):
        decision = evaluate_trade_intent(
            intent(),
            context(account_state_known=False, account_state_status="UNKNOWN"),
            proposal(),
            policy(),
            decided_at=self.now,
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
            intent(),
            context(),
            proposal(
                estimated_max_loss=Decimal("4.5"),
                estimated_cost=Decimal("0.5"),
                reward_amount=Decimal("9"),
            ),
            policy(),
            decided_at=self.now,
        )
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("REWARD_RISK_BELOW_MINIMUM", decision["reason_codes"])

    def test_gate_b_daily_trade_cap_uses_configured_policy_boundary(self):
        risk_policy = policy()
        below_limit = risk_policy.max_trades_per_day - 1

        below_decision = self._decision(
            risk_policy=risk_policy,
            trades_today=below_limit,
        )
        self.assertEqual("APPROVE", below_decision["decision"])
        self.assertNotIn("DAILY_TRADE_LIMIT_REACHED", below_decision["reason_codes"])

        for trades_today in (
            risk_policy.max_trades_per_day,
            risk_policy.max_trades_per_day + 1,
        ):
            with self.subTest(trades_today=trades_today):
                decision = self._decision(
                    risk_policy=risk_policy,
                    trades_today=trades_today,
                )
                self.assertEqual("REJECT", decision["decision"])
                self.assertIn("DAILY_TRADE_LIMIT_REACHED", decision["reason_codes"])

    def test_gate_b_open_position_cap_uses_configured_policy_boundary(self):
        risk_policy = policy()
        below_limit = risk_policy.max_open_positions - 1

        below_decision = self._decision(
            risk_policy=risk_policy,
            open_position_count=below_limit,
            same_symbol_position_open=False,
        )
        self.assertEqual("APPROVE", below_decision["decision"])
        self.assertNotIn("SIMULTANEOUS_POSITION_LIMIT_REACHED", below_decision["reason_codes"])

        for open_position_count in (
            risk_policy.max_open_positions,
            risk_policy.max_open_positions + 1,
        ):
            with self.subTest(open_position_count=open_position_count):
                decision = self._decision(
                    risk_policy=risk_policy,
                    open_position_count=open_position_count,
                    same_symbol_position_open=False,
                )
                self.assertEqual("REJECT", decision["decision"])
                self.assertIn("SIMULTANEOUS_POSITION_LIMIT_REACHED", decision["reason_codes"])
                self.assertNotIn("AVERAGING_DOWN_OR_POSITION_ADD_BLOCKED", decision["reason_codes"])

    def test_gate_b_drawdown_lock_uses_configured_policy_threshold(self):
        risk_policy = policy()
        self.assertGreater(risk_policy.max_drawdown, Decimal("0"))
        below_threshold = risk_policy.max_drawdown / Decimal("2")

        below_decision = self._decision(
            risk_policy=risk_policy,
            drawdown=below_threshold,
        )
        self.assertEqual("APPROVE", below_decision["decision"])
        self.assertNotIn("DRAWDOWN_LOCK_ACTIVE", below_decision["reason_codes"])

        for drawdown in (
            risk_policy.max_drawdown,
            risk_policy.max_drawdown * Decimal("2"),
        ):
            with self.subTest(drawdown=drawdown):
                decision = self._decision(
                    risk_policy=risk_policy,
                    drawdown=drawdown,
                )
                self.assertEqual("REJECT", decision["decision"])
                self.assertIn("DRAWDOWN_LOCK_ACTIVE", decision["reason_codes"])

    def test_gate_b_new_intent_identity_does_not_bypass_active_limit_locks(self):
        risk_policy = policy()
        new_intent = intent()
        new_intent["intent_id"] = "intent-002"
        new_intent["signal_id"] = "signal-002"

        cases = (
            ({"trades_today": risk_policy.max_trades_per_day}, "DAILY_TRADE_LIMIT_REACHED"),
            ({"open_position_count": risk_policy.max_open_positions}, "SIMULTANEOUS_POSITION_LIMIT_REACHED"),
            ({"drawdown": risk_policy.max_drawdown}, "DRAWDOWN_LOCK_ACTIVE"),
        )
        for context_changes, expected_reason in cases:
            with self.subTest(expected_reason=expected_reason):
                decision = self._decision(
                    risk_policy=risk_policy,
                    trade_intent=new_intent,
                    **context_changes,
                )
                self.assertEqual("REJECT", decision["decision"])
                self.assertIn(expected_reason, decision["reason_codes"])


if __name__ == "__main__":
    unittest.main()
