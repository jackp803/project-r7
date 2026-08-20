import unittest
from datetime import datetime, timezone
from decimal import Decimal

from risk import RiskContext, RiskPolicy, RiskProposal, evaluate_trade_intent


class FailClosedBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.policy = RiskPolicy(
            version="e5-safety-fixture-v0.1",
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
        self.intent = {
            "schema_version": "contracts-v0.1",
            "intent_id": "intent-safety",
            "signal_id": "signal-safety",
            "strategy_id": "strategy-safety",
            "strategy_version": "1.0.0",
            "symbol": "BTC_USDT_PERP",
            "direction": "SHORT",
            "generated_at": "2026-08-20T04:00:00Z",
            "market_boundary_ref": "sha256:safety",
            "entry_style": "MARKET",
        }
        self.proposal = RiskProposal(
            quantity=Decimal("0.003"),
            notional=Decimal("180"),
            margin=Decimal("9"),
            leverage=Decimal("20"),
            estimated_max_loss=Decimal("4"),
            estimated_cost=Decimal("0.5"),
            reward_amount=Decimal("10"),
            required_stop_level=Decimal("60600"),
            required_target_level=Decimal("58800"),
        )
        self.now = datetime(2026, 8, 20, 4, 0, 10, tzinfo=timezone.utc)

    def _context(self, **changes):
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
            "drawdown": Decimal("0.01"),
            "available_balance": Decimal("100"),
        }
        values.update(changes)
        return RiskContext(**values)

    def test_kill_switch_always_rejects_new_exposure(self):
        decision = evaluate_trade_intent(
            self.intent,
            self._context(kill_switch_active=True),
            self.proposal,
            self.policy,
            decided_at=self.now,
        )
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("KILL_SWITCH_ACTIVE", decision["reason_codes"])

    def test_unknown_order_state_rejects_new_exposure(self):
        decision = evaluate_trade_intent(
            self.intent,
            self._context(order_state_known=False, order_state_status="UNKNOWN"),
            self.proposal,
            self.policy,
            decided_at=self.now,
        )
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("ORDER_STATE_UNKNOWN", decision["reason_codes"])

    def test_existing_same_symbol_position_blocks_position_add(self):
        decision = evaluate_trade_intent(
            self.intent,
            self._context(same_symbol_position_open=True),
            self.proposal,
            self.policy,
            decided_at=self.now,
        )
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("AVERAGING_DOWN_OR_POSITION_ADD_BLOCKED", decision["reason_codes"])

    def test_loss_lock_does_not_auto_reset_on_new_signal(self):
        decision = evaluate_trade_intent(
            self.intent,
            self._context(consecutive_losses=5),
            self.proposal,
            self.policy,
            decided_at=self.now,
        )
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("CONSECUTIVE_LOSS_LOCK_ACTIVE", decision["reason_codes"])


if __name__ == "__main__":
    unittest.main()
