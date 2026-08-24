import copy
import unittest
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.execution.gateway import ExecutionGateway
from src.execution.models import Fill, Side
from src.execution.protection import (
    AUTHORIZATION_TYPE,
    ORDER_ROLE,
    ORDER_TYPE,
    ProtectionAuthorityError,
    prepare_protection_order,
)


class ProtectionConsumerTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 24, 3, 6, 0, tzinfo=timezone.utc)

    def _plan(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-protection-001",
            "risk_decision_id": "risk-protection-001",
            "intent_id": "intent-protection-001",
            "strategy_id": "strategy-protection",
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
            # This entry authority has already expired by the time the post-fill
            # protection action is consumed. That must not invalidate protection.
            "created_at": "2026-08-24T03:00:00Z",
            "expires_at": "2026-08-24T03:00:30Z",
            "risk_policy_version": "e5-test-policy-v0.1",
        }
        values.update(changes)
        return values

    def _position(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "position_id": "position-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": "0.0012",
            "average_entry_price": "60000",
            "opened_at": "2026-08-24T03:05:00Z",
            "broker_state_observed_at": "2026-08-24T03:05:20Z",
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": "OPEN_UNPROTECTED",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }
        values.update(changes)
        return values

    def _action(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "protection_profile_version": "protection-v0.1",
            "position_action_id": "posact-protection-001",
            "trade_plan_id": "plan-protection-001",
            "risk_decision_id": "risk-protection-001",
            "position_id": "position-001",
            "action": "PROTECT",
            "reason_codes": [],
            "risk_policy_version": "e5-test-policy-v0.1",
            "symbol": "BTC_USDT_PERP",
            "position_side": "LONG",
            "position_observed_at": "2026-08-24T03:05:20Z",
            "position_reconciliation_status": "CONSISTENT",
            "quantity": "0.0012",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
            "protection_instruction": {
                "stop_level": "59400.00",
                "target_level": "61200.00",
                "max_hold_seconds": 1800,
            },
            "created_at": "2026-08-24T03:05:30Z",
            "expires_at": "2026-08-24T03:06:30Z",
        }
        values.update(changes)
        return values

    def _prepare(self, *, action=None, plan=None, position=None, now=None):
        return prepare_protection_order(
            self._action() if action is None else action,
            self._plan() if plan is None else plan,
            self._position() if position is None else position,
            now=self.now if now is None else now,
        )

    def test_partial_fill_action_maps_exact_actual_quantity_and_lineage(self):
        request = self._prepare()
        self.assertEqual(Decimal("0.0012"), request.quantity)
        self.assertNotEqual(Decimal(self._plan()["quantity"]), request.quantity)
        self.assertEqual(AUTHORIZATION_TYPE, request.authorization_type)
        self.assertEqual("posact-protection-001", request.position_action_id)
        self.assertEqual("position-001", request.position_id)
        self.assertEqual("risk-protection-001", request.risk_decision_id)
        self.assertEqual(ORDER_ROLE, request.order_role)
        self.assertEqual("plan-protection-001", request.trade_plan_id)

    def test_full_fill_action_maps_exact_action_quantity(self):
        position = self._position(actual_quantity="0.003")
        action = self._action(quantity="0.003", position_action_id="posact-full-001")
        request = self._prepare(action=action, position=position)
        self.assertEqual(Decimal("0.003"), request.quantity)

    def test_long_maps_sell_and_short_maps_buy(self):
        long_request = self._prepare()
        short_plan = self._plan(direction="SHORT", trade_plan_id="plan-short", risk_decision_id="risk-short")
        short_position = self._position(
            position_id="position-short",
            side="SHORT",
        )
        short_action = self._action(
            position_action_id="posact-short",
            trade_plan_id="plan-short",
            risk_decision_id="risk-short",
            position_id="position-short",
            position_side="SHORT",
        )
        short_request = self._prepare(
            action=short_action,
            plan=short_plan,
            position=short_position,
        )
        self.assertEqual(Side.SELL, long_request.side)
        self.assertEqual(Side.BUY, short_request.side)

    def test_protect_maps_exact_stop_market_reduce_only_without_limit_or_tif(self):
        request = self._prepare()
        self.assertEqual(ORDER_TYPE, request.order_type)
        self.assertEqual(Decimal("59400.00"), request.stop_price)
        self.assertTrue(request.reduce_only)
        self.assertIsNone(request.limit_price)
        self.assertIsNone(request.time_in_force)

    def test_different_immediate_position_actions_do_not_collide(self):
        first = self._prepare()
        later_position = self._position(
            position_id="position-002",
            actual_quantity="0.0010",
            broker_state_observed_at="2026-08-24T03:05:40Z",
        )
        later_action = self._action(
            position_action_id="posact-protection-002",
            position_id="position-002",
            position_observed_at="2026-08-24T03:05:40Z",
            quantity="0.0010",
            created_at="2026-08-24T03:05:45Z",
            expires_at="2026-08-24T03:06:45Z",
        )
        second = self._prepare(action=later_action, position=later_position)
        self.assertNotEqual(first.client_order_id, second.client_order_id)
        self.assertNotEqual(first.order_request_id, second.order_request_id)

    def test_identical_action_translation_is_deterministic(self):
        first = self._prepare()
        second = self._prepare()
        self.assertEqual(first.client_order_id, second.client_order_id)
        self.assertEqual(first.order_request_id, second.order_request_id)
        self.assertEqual(first.safety_fingerprint(), second.safety_fingerprint())

    def test_safety_fingerprint_changes_with_authority_bearing_protection_material(self):
        first = self._prepare()
        changed_position = self._position(position_id="position-002")
        changed_action = self._action(
            position_action_id="posact-protection-002",
            position_id="position-002",
        )
        second = self._prepare(action=changed_action, position=changed_position)
        self.assertNotEqual(first.safety_fingerprint(), second.safety_fingerprint())

    def test_mismatched_authority_position_and_protection_material_fail_closed(self):
        cases = []

        action = self._action(quantity="0.0011")
        cases.append((action, self._plan(), self._position(), "quantity"))

        action = self._action(position_observed_at="2026-08-24T03:05:19Z")
        cases.append((action, self._plan(), self._position(), "observation"))

        action = self._action(position_side="SHORT")
        cases.append((action, self._plan(), self._position(), "side"))

        action = self._action(symbol="ETH_USDT_PERP")
        cases.append((action, self._plan(), self._position(), "symbol"))

        action = self._action(quantity_profile_version="legacy")
        cases.append((action, self._plan(), self._position(), "profile"))

        action = self._action(quantity_unit="CONTRACT")
        cases.append((action, self._plan(), self._position(), "unit"))

        action = self._action(quantity_asset="USDT")
        cases.append((action, self._plan(), self._position(), "asset"))

        action = self._action(risk_decision_id="risk-other")
        cases.append((action, self._plan(), self._position(), "risk_lineage"))

        action = self._action(trade_plan_id="plan-other")
        cases.append((action, self._plan(), self._position(), "plan_lineage"))

        action = self._action(
            protection_instruction={
                "stop_level": "59000.00",
                "target_level": "61200.00",
                "max_hold_seconds": 1800,
            }
        )
        cases.append((action, self._plan(), self._position(), "stop_bound"))

        action = self._action(
            protection_instruction={
                "stop_level": "59400.00",
                "target_level": "62000.00",
                "max_hold_seconds": 1800,
            }
        )
        cases.append((action, self._plan(), self._position(), "target_bound"))

        action = self._action(
            protection_instruction={
                "stop_level": "59400.00",
                "target_level": "61200.00",
                "max_hold_seconds": 3600,
            }
        )
        cases.append((action, self._plan(), self._position(), "max_hold_bound"))

        for action, plan, position, name in cases:
            with self.subTest(name=name):
                with self.assertRaises(ProtectionAuthorityError):
                    self._prepare(action=action, plan=plan, position=position)

    def test_unknown_mismatch_or_reconciliation_required_current_position_fails_closed(self):
        for status in ("UNKNOWN", "MISMATCH", "RECONCILIATION_REQUIRED"):
            with self.subTest(status=status):
                position = self._position(reconciliation_status=status)
                with self.assertRaises(ProtectionAuthorityError):
                    self._prepare(position=position)

    def test_expired_action_fails_closed(self):
        with self.assertRaises(ProtectionAuthorityError) as caught:
            self._prepare(now=datetime(2026, 8, 24, 3, 6, 30, tzinfo=timezone.utc))
        self.assertEqual("POSITION_ACTION_EXPIRED", caught.exception.code)

    def test_legacy_missing_unsupported_profile_and_modify_protection_fail_closed(self):
        missing = self._action()
        missing.pop("protection_profile_version")
        with self.assertRaises(ProtectionAuthorityError):
            self._prepare(action=missing)

        unsupported = self._action(protection_profile_version="protection-v9.9")
        with self.assertRaises(ProtectionAuthorityError) as caught:
            self._prepare(action=unsupported)
        self.assertEqual("UNSUPPORTED_PROTECTION_PROFILE", caught.exception.code)

        modified = self._action(action="MODIFY_PROTECTION")
        with self.assertRaises(ProtectionAuthorityError) as caught:
            self._prepare(action=modified)
        self.assertEqual("UNSUPPORTED_PROTECTION_ACTION", caught.exception.code)

    def test_parent_entry_expiry_alone_does_not_invalidate_live_protection_action(self):
        self.assertLess(
            datetime.fromisoformat(self._plan()["expires_at"].replace("Z", "+00:00")),
            self.now,
        )
        request = self._prepare()
        self.assertEqual(ORDER_ROLE, request.order_role)
        self.assertEqual(Decimal("0.0012"), request.quantity)

    def test_entry_v01_prepare_entry_order_behavior_remains_unchanged(self):
        entry_now = self.now
        fresh_plan = self._plan(
            created_at=entry_now.isoformat().replace("+00:00", "Z"),
            expires_at=(entry_now + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
        )
        request = ExecutionGateway().prepare_entry_order(fresh_plan, now=entry_now)
        self.assertEqual(Side.BUY, request.side)
        self.assertEqual("MARKET", request.order_type)
        self.assertEqual(Decimal("0.003"), request.quantity)
        self.assertIsNone(request.authorization_type)
        self.assertIsNone(request.position_action_id)
        self.assertIsNone(request.position_id)
        self.assertIsNone(request.risk_decision_id)
        self.assertIsNone(request.order_role)
        self.assertIsNone(request.stop_price)
        self.assertIsNone(request.reduce_only)

    def test_protection_request_contains_no_provider_native_fields(self):
        serialized = asdict(self._prepare())
        for forbidden in (
            "sz",
            "contract_count",
            "ctVal",
            "ctMult",
            "ctValCcy",
            "lotSz",
            "minSz",
            "tickSz",
            "provider_instrument_id",
            "credentials",
            "triggerPx",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_additive_protection_fill_lineage_preserves_legacy_entry_fill_meaning(self):
        request = self._prepare()
        legacy_fill = Fill(
            schema_version="contracts-v0.1",
            fill_id="fill-entry-001",
            broker_order_id="paper-entry-001",
            client_order_id="entry-client-001",
            trade_plan_id="plan-entry-001",
            symbol="BTC_USDT_PERP",
            side=Side.BUY,
            quantity=Decimal("0.001"),
            price=Decimal("60000"),
            filled_at=self.now,
        )
        self.assertIsNone(legacy_fill.position_action_id)
        self.assertIsNone(legacy_fill.position_id)
        self.assertIsNone(legacy_fill.order_role)

        protection_fill = Fill(
            schema_version="contracts-v0.1",
            fill_id="fill-protection-001",
            broker_order_id="paper-protection-001",
            client_order_id=request.client_order_id,
            trade_plan_id=request.trade_plan_id,
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            price=Decimal("59390"),
            filled_at=self.now,
            position_action_id=request.position_action_id,
            position_id=request.position_id,
            order_role=request.order_role,
        )
        self.assertEqual("posact-protection-001", protection_fill.position_action_id)
        self.assertEqual("position-001", protection_fill.position_id)
        self.assertEqual("PROTECTION_STOP", protection_fill.order_role)

    def test_request_creation_does_not_claim_protection_verified_or_protected_lifecycle(self):
        request = self._prepare()
        serialized = asdict(request)
        self.assertNotIn("protection_verified", serialized)
        self.assertNotIn("lifecycle_state", serialized)
        self.assertEqual("OPEN_UNPROTECTED", self._position()["lifecycle_state"])


if __name__ == "__main__":
    unittest.main()
