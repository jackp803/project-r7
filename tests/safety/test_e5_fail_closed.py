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
            "entry_profile_version": "entry-v0.1",
            "entry_order_type": "MARKET",
            "entry_reference_price": "60000",
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

    def _decision(self, intent=None, **context_changes):
        return evaluate_trade_intent(
            self.intent if intent is None else intent,
            self._context(**context_changes),
            self.proposal,
            self.policy,
            decided_at=self.now,
        )

    def _plan(self, intent=None, decision=None):
        payload = self.intent if intent is None else intent
        risk_decision = self._decision(intent=payload) if decision is None else decision
        return build_approved_trade_plan(
            payload,
            risk_decision,
            self.policy,
            created_at=self.now,
        )

    # Accepted E5-RISK-UNKNOWN-001 behavior remains covered.
    def test_kill_switch_always_rejects_new_exposure(self):
        decision = self._decision(kill_switch_active=True)
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("KILL_SWITCH_ACTIVE", decision["reason_codes"])

    def test_unknown_order_state_rejects_new_exposure(self):
        decision = self._decision(order_state_known=False, order_state_status="UNKNOWN")
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("ORDER_STATE_UNKNOWN", decision["reason_codes"])

    def test_existing_same_symbol_position_blocks_position_add(self):
        decision = self._decision(same_symbol_position_open=True)
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("AVERAGING_DOWN_OR_POSITION_ADD_BLOCKED", decision["reason_codes"])

    def test_loss_lock_does_not_auto_reset_on_new_signal(self):
        decision = self._decision(consecutive_losses=5)
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("CONSECUTIVE_LOSS_LOCK_ACTIVE", decision["reason_codes"])

    def test_unknown_account_status_cannot_be_overridden_by_known_flag(self):
        decision = self._decision(account_state_status="UNKNOWN", account_state_known=True)
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("ACCOUNT_STATE_STATUS_NOT_SAFE", decision["reason_codes"])
        self.assertIn("ACCOUNT_STATE_STATUS_FLAG_CONTRADICTION", decision["reason_codes"])

    def test_unknown_order_status_cannot_be_overridden_by_known_flag(self):
        decision = self._decision(order_state_status="UNKNOWN", order_state_known=True)
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("ORDER_STATE_STATUS_NOT_SAFE", decision["reason_codes"])
        self.assertIn("ORDER_STATE_STATUS_FLAG_CONTRADICTION", decision["reason_codes"])

    def test_unknown_position_status_cannot_be_overridden_by_known_flag(self):
        decision = self._decision(position_state_status="UNKNOWN", position_state_known=True)
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("POSITION_STATE_STATUS_NOT_SAFE", decision["reason_codes"])
        self.assertIn("POSITION_STATE_STATUS_FLAG_CONTRADICTION", decision["reason_codes"])

    def test_unsafe_market_status_cannot_be_overridden_by_fresh_flag(self):
        for market_status in (
            "UNKNOWN",
            "STALE",
            "DEGRADED",
            "UNSAFE",
            "RECONCILIATION_REQUIRED",
        ):
            with self.subTest(market_status=market_status):
                decision = self._decision(
                    market_health_status=market_status,
                    market_data_fresh=True,
                )
                self.assertEqual("REJECT", decision["decision"])
                self.assertIn("MARKET_HEALTH_STATUS_NOT_SAFE", decision["reason_codes"])
                self.assertIn("MARKET_STATUS_FLAG_CONTRADICTION", decision["reason_codes"])

    def test_reconciliation_required_and_mismatch_states_fail_closed(self):
        cases = (
            {
                "order_state_status": "RECONCILIATION_REQUIRED",
                "order_state_known": True,
                "reason": "ORDER_STATE_STATUS_NOT_SAFE",
            },
            {
                "position_state_status": "RECONCILIATION_REQUIRED",
                "position_state_known": True,
                "reason": "POSITION_STATE_STATUS_NOT_SAFE",
            },
            {
                "position_state_status": "MISMATCH",
                "position_state_known": True,
                "reason": "POSITION_STATE_STATUS_NOT_SAFE",
            },
        )
        for case in cases:
            reason = case["reason"]
            changes = {key: value for key, value in case.items() if key != "reason"}
            with self.subTest(changes=changes):
                decision = self._decision(**changes)
                self.assertEqual("REJECT", decision["decision"])
                self.assertIn(reason, decision["reason_codes"])

    # E5-20260821-004 executable profile coverage.
    def test_valid_profiled_market_intent_produces_profiled_plan(self):
        decision = self._decision()
        self.assertEqual("APPROVE", decision["decision"])
        plan = self._plan(decision=decision)
        self.assertEqual(
            {"profile_version", "order_type", "reference_price"},
            set(plan["entry_instruction"].keys()),
        )
        self.assertEqual("entry-v0.1", plan["entry_instruction"]["profile_version"])
        self.assertEqual("MARKET", plan["entry_instruction"]["order_type"])

    def test_missing_and_unknown_entry_profile_fail_closed(self):
        missing = dict(self.intent)
        missing.pop("entry_profile_version")
        decision = self._decision(intent=missing)
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("ENTRY_PROFILE_VERSION_REQUIRED", decision["reason_codes"])

        unknown = dict(self.intent)
        unknown["entry_profile_version"] = "entry-v9.9"
        decision = self._decision(intent=unknown)
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("UNSUPPORTED_ENTRY_PROFILE_VERSION", decision["reason_codes"])

    def test_unsupported_executable_order_type_fails_closed(self):
        payload = dict(self.intent)
        payload["entry_order_type"] = "LIMIT"
        decision = self._decision(intent=payload)
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("UNSUPPORTED_ENTRY_ORDER_TYPE", decision["reason_codes"])

    def test_legacy_style_only_intent_is_not_execution_eligible(self):
        payload = dict(self.intent)
        payload.pop("entry_profile_version")
        payload.pop("entry_order_type")
        payload["entry_style"] = "MARKET"
        decision = self._decision(intent=payload)
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("ENTRY_PROFILE_VERSION_REQUIRED", decision["reason_codes"])
        self.assertIn("ENTRY_ORDER_TYPE_REQUIRED", decision["reason_codes"])

    def test_reference_price_remains_advisory_non_executable(self):
        plan = self._plan()
        entry = plan["entry_instruction"]
        self.assertEqual("60000", entry["reference_price"])
        self.assertEqual("MARKET", entry["order_type"])
        for forbidden in ("limit_price", "stop_price", "trigger_price", "time_in_force"):
            self.assertNotIn(forbidden, entry)

    def test_quantity_profile_is_exact_btc_base_asset_upper_bound_metadata(self):
        plan = self._plan()
        self.assertEqual("0.003", plan["quantity"])
        self.assertEqual("base-asset-v0.1", plan["quantity_profile_version"])
        self.assertEqual("BASE_ASSET", plan["quantity_unit"])
        self.assertEqual("BTC", plan["quantity_asset"])
        for provider_field in (
            "sz",
            "ctVal",
            "ctMult",
            "ctValCcy",
            "lotSz",
            "minSz",
            "tickSz",
        ):
            self.assertNotIn(provider_field, plan)

    def test_unknown_state_cannot_produce_approved_plan(self):
        decision = self._decision(account_state_status="UNKNOWN", account_state_known=True)
        self.assertEqual("REJECT", decision["decision"])
        with self.assertRaises(RiskInputError):
            self._plan(decision=decision)

    def test_forged_approve_with_unsafe_state_cannot_produce_plan(self):
        valid_decision = self._decision()
        self.assertEqual("APPROVE", valid_decision["decision"])
        forged = dict(valid_decision)
        forged["market_health_status"] = "UNKNOWN"
        with self.assertRaises(RiskInputError):
            self._plan(decision=forged)


if __name__ == "__main__":
    unittest.main()
