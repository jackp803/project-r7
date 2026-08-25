import inspect
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from brokers.okx_shadow import OKXShadowObservation, OKXShadowReadResult, ShadowFillCheckpoint
from market_data.current import MarketSnapshot
from risk import (
    RiskContextDerivationError,
    RiskPolicy,
    RiskProposal,
    derive_gate_c_risk_context,
    evaluate_trade_intent,
)


class GateCRiskContextDerivationTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 25, 5, 0, 10, tzinfo=timezone.utc)
        self.runtime_balance = Decimal("123.456789")

    def _market(self, *, decision_age_ms=1_000, health_status="HEALTHY", symbol="BTC_USDT_PERP", source="OKX_PUBLIC_TICKER"):
        observed_at = self.now - timedelta(milliseconds=decision_age_ms)
        received_at = observed_at + timedelta(milliseconds=100)
        return MarketSnapshot(
            schema_version="contracts-v0.1",
            symbol=symbol,
            observed_at=observed_at,
            received_at=received_at,
            health_status=health_status,
            source=source,
            last_price=Decimal("60000"),
            best_bid=Decimal("59999"),
            best_ask=Decimal("60001"),
            freshness_ms=100,
        )

    def _observation(self, **changes):
        values = {
            "provider": "OKX",
            "api_version": "V5",
            "environment": "production_read_only_shadow",
            "rest_hostname": "www.okx.com",
            "canonical_symbol": "BTC_USDT_PERP",
            "provider_instrument_id": "BTC-USDT-SWAP",
            "observed_at": self.now - timedelta(milliseconds=200),
            "provider_time": self.now - timedelta(milliseconds=250),
            "clock_skew_ms": 50,
            "clock_status": "HEALTHY",
            "permission_category": "read_only",
            "account_config_known": True,
            "account_level": "2",
            "position_mode": "net_mode",
            "subaccount_status": "SUBACCOUNT",
            "usdt_balance_known": True,
            "position_known": True,
            "unexpected_exposure": False,
            "isolated_leverage_known": True,
            "isolated_leverage_ok": True,
            "pending_order_count": 0,
            "recent_fill_window_count": 0,
            "fill_checkpoint": ShadowFillCheckpoint(None, 0),
            "new_unreconciled_fill_count": 0,
            "private_get_count": 6,
            "health_status": "HEALTHY",
            "reason_codes": (),
        }
        values.update(changes)
        return OKXShadowObservation(**values)

    def _shadow(self, *, observation=None, balance=None):
        if observation is None:
            observation = self._observation()
        if balance is None:
            balance = self.runtime_balance
        return OKXShadowReadResult(observation, balance)

    def _derive(self, *, market=None, shadow=None, kill_switch_active=False, trades_today=0, consecutive_losses=0, drawdown=Decimal("0.02")):
        return derive_gate_c_risk_context(
            self._market() if market is None else market,
            self._shadow() if shadow is None else shadow,
            risk_evaluation_time=self.now,
            kill_switch_active=kill_switch_active,
            trades_today=trades_today,
            consecutive_losses=consecutive_losses,
            drawdown=drawdown,
        )

    @staticmethod
    def _policy():
        return RiskPolicy(
            version="e5-gate-c-test-v0.1",
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

    def _intent(self):
        generated = (self.now - timedelta(seconds=10)).isoformat().replace("+00:00", "Z")
        return {
            "schema_version": "contracts-v0.1",
            "intent_id": "intent-gate-c-001",
            "signal_id": "signal-gate-c-001",
            "strategy_id": "strategy-gate-c-001",
            "strategy_version": "1.0.0",
            "symbol": "BTC_USDT_PERP",
            "direction": "LONG",
            "generated_at": generated,
            "market_boundary_ref": "sha256:gate-c-boundary",
            "entry_profile_version": "entry-v0.1",
            "entry_order_type": "MARKET",
            "entry_reference_price": "60000",
            "strategy_stop_level": "59400",
            "strategy_target_level": "61200",
            "max_hold_seconds": 1800,
        }

    @staticmethod
    def _proposal():
        return RiskProposal(
            quantity=Decimal("0.003"),
            notional=Decimal("180"),
            margin=Decimal("9"),
            leverage=Decimal("20"),
            estimated_max_loss=Decimal("4"),
            estimated_cost=Decimal("0.5"),
            reward_amount=Decimal("10"),
            required_stop_level=Decimal("59400"),
            required_target_level=Decimal("61200"),
        )

    def test_healthy_normalized_inputs_derive_existing_safe_risk_context(self):
        result = self._derive()
        context = result.context
        self.assertTrue(result.safe_for_new_exposure)
        self.assertEqual((), result.reason_codes)
        self.assertEqual("HEALTHY", context.market_health_status)
        self.assertTrue(context.market_data_fresh)
        self.assertEqual("KNOWN", context.account_state_status)
        self.assertTrue(context.account_state_known)
        self.assertEqual("FLAT", context.position_state_status)
        self.assertTrue(context.position_state_known)
        self.assertEqual(0, context.open_position_count)
        self.assertFalse(context.same_symbol_position_open)
        self.assertEqual("KNOWN", context.order_state_status)
        self.assertTrue(context.order_state_known)
        self.assertTrue(context.new_exposure_allowed)
        self.assertEqual(self.runtime_balance, context.available_balance)

    def test_runtime_balance_is_exact_but_derivation_repr_is_redacted(self):
        result = self._derive()
        self.assertEqual(self.runtime_balance, result.context.available_balance)
        rendered = repr(result)
        self.assertNotIn(format(self.runtime_balance, "f"), rendered)
        self.assertIn("context=<runtime-sensitive>", rendered)

    def test_market_decision_boundary_accepts_5000_ms_and_rejects_over_limit(self):
        at_limit = self._derive(market=self._market(decision_age_ms=5_000))
        self.assertTrue(at_limit.context.market_data_fresh)
        over_limit = self._derive(market=self._market(decision_age_ms=5_001))
        self.assertFalse(over_limit.context.market_data_fresh)
        self.assertEqual("STALE", over_limit.context.market_health_status)
        self.assertFalse(over_limit.context.new_exposure_allowed)
        self.assertIn("GATE_C_MARKET_STALE_AT_DECISION", over_limit.reason_codes)

    def test_market_stale_future_malformed_and_identity_mismatch_fail_closed(self):
        cases = []
        cases.append(self._market(decision_age_ms=6_000))
        future_observed = self.now + timedelta(milliseconds=5_001)
        cases.append(
            SimpleNamespace(
                schema_version="contracts-v0.1",
                symbol="BTC_USDT_PERP",
                observed_at=future_observed,
                received_at=self.now,
                health_status="HEALTHY",
                source="OKX_PUBLIC_TICKER",
                freshness_ms=0,
            )
        )
        cases.append(
            SimpleNamespace(
                schema_version="contracts-v0.1",
                symbol="BTC_USDT_PERP",
                observed_at="malformed",
                received_at=self.now,
                health_status="HEALTHY",
                source="OKX_PUBLIC_TICKER",
                freshness_ms=0,
            )
        )
        cases.append(self._market(symbol="ETH_USDT_PERP"))
        cases.append(self._market(source="CALLER_ASSERTED_HEALTH"))
        for market in cases:
            with self.subTest(market=market):
                result = self._derive(market=market)
                self.assertFalse(result.context.market_data_fresh)
                self.assertFalse(result.context.new_exposure_allowed)
                self.assertTrue(result.reason_codes)

    def test_e1_health_and_freshness_metadata_contradictions_fail_closed(self):
        degraded = self._derive(market=self._market(health_status="DEGRADED"))
        self.assertFalse(degraded.context.market_data_fresh)
        contradictory = SimpleNamespace(
            schema_version="contracts-v0.1",
            symbol="BTC_USDT_PERP",
            observed_at=self.now - timedelta(seconds=1),
            received_at=self.now - timedelta(milliseconds=900),
            health_status="HEALTHY",
            source="OKX_PUBLIC_TICKER",
            freshness_ms=999,
        )
        result = self._derive(market=contradictory)
        self.assertFalse(result.context.market_data_fresh)
        self.assertIn("GATE_C_MARKET_FRESHNESS_CONTRADICTION", result.reason_codes)

    def test_degraded_shadow_batch_fails_closed_even_with_same_batch_balance(self):
        observation = self._observation(health_status="DEGRADED", reason_codes=("PROVIDER_DEGRADED",))
        result = self._derive(shadow=self._shadow(observation=observation))
        self.assertFalse(result.context.account_state_known)
        self.assertFalse(result.context.position_state_known)
        self.assertFalse(result.context.order_state_known)
        self.assertIsNone(result.context.available_balance)
        self.assertFalse(result.context.new_exposure_allowed)

    def test_missing_or_invalid_runtime_balance_cannot_make_account_known(self):
        observation = self._observation()
        for balance in (None, Decimal("NaN"), Decimal("-1")):
            fake_batch = SimpleNamespace(
                sanitized_observation=observation,
                runtime_available_balance=balance,
            )
            with self.subTest(balance=balance):
                result = self._derive(shadow=fake_batch)
                self.assertFalse(result.context.account_state_known)
                self.assertIsNone(result.context.available_balance)
                self.assertFalse(result.context.new_exposure_allowed)

    def test_unexpected_or_unknown_position_never_becomes_flat(self):
        cases = (
            self._observation(unexpected_exposure=True),
            self._observation(position_known=False, unexpected_exposure=None),
        )
        for observation in cases:
            with self.subTest(observation=observation):
                result = self._derive(shadow=self._shadow(observation=observation))
                self.assertEqual("UNKNOWN", result.context.position_state_status)
                self.assertFalse(result.context.position_state_known)
                self.assertEqual(1, result.context.open_position_count)
                self.assertTrue(result.context.same_symbol_position_open)
                self.assertFalse(result.context.new_exposure_allowed)

    def test_pending_order_new_fill_and_unknown_checkpoint_activity_are_unsafe(self):
        cases = (
            self._observation(pending_order_count=1),
            self._observation(new_unreconciled_fill_count=1),
            self._observation(pending_order_count=None),
            self._observation(new_unreconciled_fill_count=None),
            self._observation(fill_checkpoint=None),
        )
        for observation in cases:
            with self.subTest(observation=observation):
                result = self._derive(shadow=self._shadow(observation=observation))
                self.assertEqual("UNKNOWN", result.context.order_state_status)
                self.assertFalse(result.context.order_state_known)
                self.assertFalse(result.context.new_exposure_allowed)

    def test_shadow_identity_permission_clock_account_and_health_contradictions_fail_closed(self):
        observations = (
            self._observation(provider="NOT_OKX"),
            self._observation(environment="demo"),
            self._observation(provider_instrument_id="ETH-USDT-SWAP"),
            self._observation(rest_hostname="evil.example"),
            self._observation(permission_category="trade"),
            self._observation(clock_status="HEALTHY", clock_skew_ms=5_001),
            self._observation(account_config_known=False),
            self._observation(subaccount_status="UNKNOWN"),
            self._observation(health_status="HEALTHY", reason_codes=("CONTRADICTION",)),
        )
        for observation in observations:
            with self.subTest(observation=observation):
                result = self._derive(shadow=self._shadow(observation=observation))
                self.assertFalse(result.context.new_exposure_allowed)
                self.assertTrue(result.reason_codes)

    def test_kill_switch_and_existing_policy_counters_remain_e5_authority(self):
        killed = self._derive(kill_switch_active=True)
        self.assertFalse(killed.context.new_exposure_allowed)
        killed_decision = evaluate_trade_intent(
            self._intent(), killed.context, self._proposal(), self._policy(), decided_at=self.now
        )
        self.assertEqual("REJECT", killed_decision["decision"])
        self.assertIn("KILL_SWITCH_ACTIVE", killed_decision["reason_codes"])

        at_daily_limit = self._derive(trades_today=self._policy().max_trades_per_day)
        self.assertTrue(at_daily_limit.context.new_exposure_allowed)
        decision = evaluate_trade_intent(
            self._intent(), at_daily_limit.context, self._proposal(), self._policy(), decided_at=self.now
        )
        self.assertEqual("REJECT", decision["decision"])
        self.assertIn("DAILY_TRADE_LIMIT_REACHED", decision["reason_codes"])

    def test_invalid_e5_runtime_state_is_rejected_before_context_construction(self):
        bad_cases = (
            {"kill_switch_active": 1},
            {"trades_today": -1},
            {"consecutive_losses": "0"},
            {"drawdown": Decimal("NaN")},
        )
        for changes in bad_cases:
            with self.subTest(changes=changes):
                with self.assertRaises(RiskContextDerivationError):
                    self._derive(**changes)

    def test_no_caller_supplied_safety_booleans_exist_in_derivation_surface(self):
        parameters = inspect.signature(derive_gate_c_risk_context).parameters
        for forbidden in (
            "market_data_fresh",
            "account_state_known",
            "position_state_known",
            "order_state_known",
            "new_exposure_allowed",
            "available_balance",
            "open_position_count",
            "same_symbol_position_open",
        ):
            self.assertNotIn(forbidden, parameters)

    def test_existing_risk_evaluation_consumes_healthy_context_and_rejects_unsafe_context(self):
        healthy = self._derive()
        approved = evaluate_trade_intent(
            self._intent(), healthy.context, self._proposal(), self._policy(), decided_at=self.now
        )
        self.assertEqual("APPROVE", approved["decision"])
        self.assertEqual([], approved["reason_codes"])

        unsafe = self._derive(market=self._market(decision_age_ms=5_001))
        rejected = evaluate_trade_intent(
            self._intent(), unsafe.context, self._proposal(), self._policy(), decided_at=self.now
        )
        self.assertEqual("REJECT", rejected["decision"])
        self.assertIn("MARKET_DATA_STALE_OR_UNKNOWN", rejected["reason_codes"])
        self.assertIn("NEW_EXPOSURE_DISABLED", rejected["reason_codes"])


if __name__ == "__main__":
    unittest.main()
