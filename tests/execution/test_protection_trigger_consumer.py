import copy
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.execution.protection import ProtectionAuthorityError
from src.execution.protection_trigger import (
    ProtectionTriggerConsumerError,
    prepare_trigger_validated_protection_order,
    require_provider_trigger_basis_compatibility,
    validate_protection_trigger_create_evidence,
)
from src.position.protection import build_protect_position_action
from src.position.protection_trigger_validity import (
    build_protection_trigger_validity_evidence,
    stable_protection_trigger_validity_id,
)


class ProtectionTriggerConsumerTests(unittest.TestCase):
    def setUp(self):
        self.position_observed_at = "2026-08-29T14:00:00Z"
        self.market_observed_at = "2026-08-29T14:00:10Z"
        self.market_received_at = "2026-08-29T14:00:11Z"
        self.action_created_at = datetime(2026, 8, 29, 14, 0, 5, tzinfo=timezone.utc)
        self.action_expires_at = datetime(2026, 8, 29, 14, 5, 0, tzinfo=timezone.utc)
        self.evaluated_at = datetime(2026, 8, 29, 14, 0, 12, tzinfo=timezone.utc)
        self.now = datetime(2026, 8, 29, 14, 0, 15, tzinfo=timezone.utc)

    def _plan(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-fp03-001",
            "risk_decision_id": "risk-fp03-001",
            "intent_id": "intent-fp03-001",
            "strategy_id": "strategy-fp03",
            "strategy_version": "1.0.0",
            "symbol": "BTC_USDT_PERP",
            "direction": "LONG",
            "quantity": "0.003",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
            "leverage": "3",
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
            "created_at": "2026-08-29T13:59:00Z",
            "expires_at": "2026-08-29T14:10:00Z",
            "risk_policy_version": "e5-fp03-policy-v0.1",
        }
        values.update(changes)
        return values

    def _position(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "position_id": "position-fp03-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": "0.0012",
            "average_entry_price": "60000",
            "opened_at": "2026-08-29T13:59:50Z",
            "broker_state_observed_at": self.position_observed_at,
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": "OPEN_UNPROTECTED",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }
        values.update(changes)
        return values

    def _action(self, *, position=None, plan=None, **changes):
        position = self._position() if position is None else position
        plan = self._plan() if plan is None else plan
        values = build_protect_position_action(
            position,
            plan,
            created_at=self.action_created_at,
            expires_at=self.action_expires_at,
        )
        values.update(changes)
        return values

    def _market(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "symbol": "BTC_USDT_PERP",
            "source": "OKX_PUBLIC_TICKER",
            "observed_at": self.market_observed_at,
            "received_at": self.market_received_at,
            "health_status": "HEALTHY",
            "last_price": "60000.00",
            "freshness_ms": 100,
        }
        values.update(changes)
        return values

    def _evidence(self, *, position=None, action=None, plan=None, market=None, **kwargs):
        position = self._position() if position is None else position
        plan = self._plan() if plan is None else plan
        action = self._action(position=position, plan=plan) if action is None else action
        market = self._market() if market is None else market
        return build_protection_trigger_validity_evidence(
            position,
            action,
            plan,
            market,
            market_freshness_classification=kwargs.pop("market_freshness_classification", "FRESH"),
            evaluated_at=kwargs.pop("evaluated_at", self.evaluated_at),
            **kwargs,
        )

    def _validate(self, *, action=None, plan=None, position=None, evidence=None, market=None, now=None):
        position = self._position() if position is None else position
        plan = self._plan() if plan is None else plan
        action = self._action(position=position, plan=plan) if action is None else action
        market = self._market() if market is None else market
        if evidence is None:
            evidence = self._evidence(position=position, action=action, plan=plan, market=market)
        return validate_protection_trigger_create_evidence(
            action,
            plan,
            position,
            evidence,
            market,
            market_freshness_classification="FRESH",
            now=self.now if now is None else now,
        )

    def _prepare(self, *, action=None, plan=None, position=None, evidence=None, market=None, now=None):
        position = self._position() if position is None else position
        plan = self._plan() if plan is None else plan
        action = self._action(position=position, plan=plan) if action is None else action
        market = self._market() if market is None else market
        if evidence is None:
            evidence = self._evidence(position=position, action=action, plan=plan, market=market)
        return prepare_trigger_validated_protection_order(
            action,
            plan,
            position,
            evidence,
            market,
            market_freshness_classification="FRESH",
            now=self.now if now is None else now,
        )

    def test_actionable_matching_create_evidence_is_accepted_by_pre_mutation_consumer(self):
        evidence = self._evidence()
        facts = self._validate(evidence=evidence)
        self.assertEqual(evidence["protection_trigger_validity_id"], facts["protection_trigger_validity_id"])
        self.assertEqual(Decimal("0.0012"), facts["quantity"])
        self.assertEqual(Decimal("59400.00"), facts["stop_level"])
        self.assertEqual("LAST_PRICE", facts["trigger_reference_semantic"])

    def test_missing_and_unsupported_evidence_fail_closed(self):
        action = self._action()
        with self.assertRaises(ProtectionTriggerConsumerError) as missing:
            validate_protection_trigger_create_evidence(
                action,
                self._plan(),
                self._position(),
                None,
                self._market(),
                market_freshness_classification="FRESH",
                now=self.now,
            )
        self.assertEqual("E4_TRIGGER_VALIDITY_EVIDENCE_REQUIRED", missing.exception.code)

        unsupported = self._evidence()
        unsupported["protection_trigger_validity_profile_version"] = "protection-trigger-validity-v9.9"
        with self.assertRaises(ProtectionTriggerConsumerError) as caught:
            self._validate(evidence=unsupported)
        self.assertEqual("UNSUPPORTED_TRIGGER_VALIDITY_PROFILE", caught.exception.code)

    def test_fail_closed_breached_evidence_never_authorizes_create_or_time_only_retry(self):
        breached_market = self._market(last_price="59000.00")
        action = self._action()
        evidence = self._evidence(action=action, market=breached_market)
        self.assertEqual("FAIL_CLOSED", evidence["validity_status"])
        self.assertIn("TRIGGER_ALREADY_BREACHED", evidence["reason_codes"])
        for now in (self.now, self.now + timedelta(seconds=30)):
            with self.subTest(now=now):
                with self.assertRaises(ProtectionTriggerConsumerError) as caught:
                    validate_protection_trigger_create_evidence(
                        action,
                        self._plan(),
                        self._position(),
                        evidence,
                        breached_market,
                        market_freshness_classification="FRESH",
                        now=now,
                    )
                self.assertEqual("E4_TRIGGER_VALIDITY_FAIL_CLOSED", caught.exception.code)

    def test_e4_binding_mismatch_rejects_different_action_position_side_symbol_stop_role_operation(self):
        base = self._evidence()
        cases = {}

        changed = copy.deepcopy(base)
        changed["position_action_id"] = "posact-other"
        cases["action_id"] = changed

        changed = copy.deepcopy(base)
        changed["position_id"] = "position-other"
        cases["position_id"] = changed

        changed = copy.deepcopy(base)
        changed["position_side"] = "SHORT"
        cases["side"] = changed

        changed = copy.deepcopy(base)
        changed["market_symbol"] = "ETH_USDT_PERP"
        cases["symbol"] = changed

        changed = copy.deepcopy(base)
        changed["stop_level"] = "59300.00"
        cases["stop"] = changed

        changed = copy.deepcopy(base)
        changed["order_role"] = "POSITION_EXIT"
        cases["role"] = changed

        changed = copy.deepcopy(base)
        changed["protection_operation"] = "REPLACE"
        cases["operation"] = changed

        for name, evidence in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(ProtectionTriggerConsumerError) as caught:
                    self._validate(evidence=evidence)
                self.assertEqual("E4_BINDING_MISMATCH", caught.exception.code)

    def test_e4_binding_mismatch_rejects_changed_position_authority_reference(self):
        evidence = copy.deepcopy(self._evidence())
        evidence["position_authority_ref"] = "sha256:" + "0" * 64
        evidence["protection_trigger_validity_id"] = stable_protection_trigger_validity_id(evidence)
        with self.assertRaises(ProtectionTriggerConsumerError) as caught:
            self._validate(evidence=evidence)
        self.assertEqual("E4_BINDING_MISMATCH", caught.exception.code)

    def test_newer_market_or_position_truth_invalidates_prior_evidence(self):
        evidence = self._evidence()
        newer_market = self._market(
            observed_at="2026-08-29T14:00:20Z",
            received_at="2026-08-29T14:00:21Z",
            last_price="60010.00",
        )
        with self.assertRaises(ProtectionTriggerConsumerError) as market_caught:
            self._validate(evidence=evidence, market=newer_market)
        self.assertEqual("E4_TRIGGER_VALIDITY_NOT_CURRENT", market_caught.exception.code)

        newer_position = self._position(broker_state_observed_at="2026-08-29T14:00:20Z")
        with self.assertRaises(ProtectionTriggerConsumerError) as position_caught:
            self._validate(evidence=evidence, position=newer_position, action=self._action())
        self.assertEqual("E4_TRIGGER_VALIDITY_NOT_CURRENT", position_caught.exception.code)

    def test_replace_remains_non_executable_under_current_baseline(self):
        evidence = copy.deepcopy(self._evidence())
        evidence["protection_operation"] = "REPLACE"
        evidence["protection_trigger_validity_id"] = stable_protection_trigger_validity_id(evidence)
        with self.assertRaises(ProtectionTriggerConsumerError) as caught:
            self._validate(evidence=evidence)
        self.assertEqual("E4_BINDING_MISMATCH", caught.exception.code)

    def test_existing_protection_quantity_expiry_and_idempotency_checks_remain_enforced(self):
        first = self._prepare()
        second = self._prepare()
        self.assertEqual(Decimal("0.0012"), first.quantity)
        self.assertEqual(first.client_order_id, second.client_order_id)
        self.assertEqual(first.order_request_id, second.order_request_id)

        bad_action = self._action(quantity="0.0011")
        evidence = self._evidence()
        with self.assertRaises(ProtectionAuthorityError):
            self._prepare(action=bad_action, evidence=evidence)

        with self.assertRaises(ProtectionAuthorityError) as expired:
            self._prepare(now=self.action_expires_at)
        self.assertEqual("POSITION_ACTION_EXPIRED", expired.exception.code)

    def test_provider_neutral_request_contains_no_provider_native_trigger_basis(self):
        request = self._prepare()
        self.assertEqual("PROTECTION_STOP", request.order_role)
        self.assertEqual("STOP_MARKET", request.order_type)
        self.assertEqual(Decimal("59400.00"), request.stop_price)
        self.assertTrue(request.reduce_only)
        self.assertFalse(hasattr(request, "triggerPxType"))
        self.assertFalse(hasattr(request, "provider_trigger_type"))

    def test_shared_last_price_evidence_alone_does_not_authorize_provider_trigger_basis(self):
        evidence = self._evidence()
        self._validate(evidence=evidence)
        for caller_asserted_value in (None, True, {"compatible": True}, "LAST_PRICE"):
            with self.subTest(caller_asserted_value=caller_asserted_value):
                with self.assertRaises(ProtectionTriggerConsumerError) as caught:
                    require_provider_trigger_basis_compatibility(
                        evidence,
                        provider_capability_evidence=caller_asserted_value,
                    )
                self.assertEqual("PROVIDER_TRIGGER_BASIS_NOT_PROVEN", caught.exception.code)

    def test_provider_native_mapping_incompatibility_is_fail_closed(self):
        unsupported = self._evidence(trigger_reference_semantic="MARK_PRICE")
        self.assertEqual("FAIL_CLOSED", unsupported["validity_status"])
        with self.assertRaises(ProtectionTriggerConsumerError) as caught:
            require_provider_trigger_basis_compatibility(
                unsupported,
                provider_capability_evidence={"claimed_provider_basis": "mark"},
            )
        self.assertEqual("PROVIDER_TRIGGER_BASIS_INCOMPATIBLE", caught.exception.code)

    def test_no_provider_client_request_credentials_or_mutation_are_required_or_invoked(self):
        evidence = self._evidence()
        self._validate(evidence=evidence)
        request = self._prepare(evidence=evidence)
        self.assertEqual("PROTECTION_STOP", request.order_role)
        consumer_names = set(validate_protection_trigger_create_evidence.__code__.co_varnames)
        for forbidden in ("credentials", "transport", "client", "submit", "cancel", "amend"):
            self.assertNotIn(forbidden, consumer_names)


if __name__ == "__main__":
    unittest.main()
