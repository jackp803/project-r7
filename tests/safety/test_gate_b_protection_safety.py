import unittest
from datetime import datetime, timezone

from position import ProtectionActionError, build_protect_position_action
from src.execution.protection import ProtectionAuthorityError, prepare_protection_order


class GateBProtectionSafetyTests(unittest.TestCase):
    """Fail-closed cross-module definitions for protection-v0.1.

    These tests exercise the accepted E5 producer and E4 consumer directly.
    They intentionally stop before inventing the still-missing protection-result
    -> E5 lifecycle verification/failure bridge.
    """

    def setUp(self):
        self.created_at = datetime(2026, 8, 24, 3, 5, 30, tzinfo=timezone.utc)
        self.expires_at = datetime(2026, 8, 24, 3, 6, 30, tzinfo=timezone.utc)
        self.now = datetime(2026, 8, 24, 3, 6, 0, tzinfo=timezone.utc)

    def _plan(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-gate-b-safety-001",
            "risk_decision_id": "risk-gate-b-safety-001",
            "intent_id": "intent-gate-b-safety-001",
            "strategy_id": "strategy-gate-b-safety",
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
            "created_at": "2026-08-24T03:00:00Z",
            "expires_at": "2026-08-24T03:00:30Z",
            "risk_policy_version": "e5-gate-b-policy-v0.1",
        }
        values.update(changes)
        return values

    def _position(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "position_id": "position-gate-b-safety-001",
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

    def _action(self, *, position=None, plan=None):
        source_position = self._position() if position is None else position
        parent_plan = self._plan() if plan is None else plan
        return build_protect_position_action(
            source_position,
            parent_plan,
            created_at=self.created_at,
            expires_at=self.expires_at,
        )

    def test_ambiguous_or_unreconciled_position_truth_cannot_produce_or_consume_protection(self):
        for status in ("UNKNOWN", "MISMATCH", "RECONCILIATION_REQUIRED"):
            with self.subTest(producer_status=status):
                with self.assertRaises(ProtectionActionError):
                    self._action(position=self._position(reconciliation_status=status))

        valid_position = self._position()
        plan = self._plan()
        action = self._action(position=valid_position, plan=plan)
        for status in ("UNKNOWN", "MISMATCH", "RECONCILIATION_REQUIRED"):
            with self.subTest(consumer_status=status):
                current_position = self._position(reconciliation_status=status)
                with self.assertRaises(ProtectionAuthorityError):
                    prepare_protection_order(
                        action,
                        plan,
                        current_position,
                        now=self.now,
                    )

    def test_over_approved_actual_exposure_cannot_expand_e5_or_e4_ordinary_authority(self):
        over_position = self._position(actual_quantity="0.004")
        plan = self._plan(quantity="0.003")
        with self.assertRaises(ProtectionActionError):
            self._action(position=over_position, plan=plan)

        valid_action = self._action(position=self._position(), plan=plan)
        forged_action = dict(valid_action)
        forged_action["quantity"] = "0.004"
        forged_action["position_observed_at"] = over_position["broker_state_observed_at"]
        forged_action["position_id"] = over_position["position_id"]
        with self.assertRaises(ProtectionAuthorityError) as caught:
            prepare_protection_order(
                forged_action,
                plan,
                over_position,
                now=self.now,
            )
        self.assertEqual("ACTUAL_QUANTITY_EXCEEDS_APPROVED_MAXIMUM", caught.exception.code)

    def test_tampered_protection_bounds_are_rejected_at_e4_boundary(self):
        position = self._position()
        plan = self._plan()
        action = self._action(position=position, plan=plan)

        tampered_cases = (
            {"stop_level": "59000.00", "target_level": "61200.00", "max_hold_seconds": 1800},
            {"stop_level": "59400.00", "target_level": "62000.00", "max_hold_seconds": 1800},
            {"stop_level": "59400.00", "target_level": "61200.00", "max_hold_seconds": 3600},
        )
        for protection_instruction in tampered_cases:
            with self.subTest(protection_instruction=protection_instruction):
                tampered = dict(action)
                tampered["protection_instruction"] = protection_instruction
                with self.assertRaises(ProtectionAuthorityError) as caught:
                    prepare_protection_order(tampered, plan, position, now=self.now)
                self.assertEqual("PROTECTION_BOUND_MISMATCH", caught.exception.code)

    def test_legacy_unsupported_and_modify_protection_actions_are_non_executable(self):
        position = self._position()
        plan = self._plan()
        action = self._action(position=position, plan=plan)

        missing_profile = dict(action)
        missing_profile.pop("protection_profile_version")
        with self.assertRaises(ProtectionAuthorityError):
            prepare_protection_order(missing_profile, plan, position, now=self.now)

        unsupported_profile = dict(action)
        unsupported_profile["protection_profile_version"] = "protection-v9.9"
        with self.assertRaises(ProtectionAuthorityError) as caught:
            prepare_protection_order(unsupported_profile, plan, position, now=self.now)
        self.assertEqual("UNSUPPORTED_PROTECTION_PROFILE", caught.exception.code)

        modify = dict(action)
        modify["action"] = "MODIFY_PROTECTION"
        with self.assertRaises(ProtectionAuthorityError) as caught:
            prepare_protection_order(modify, plan, position, now=self.now)
        self.assertEqual("UNSUPPORTED_PROTECTION_ACTION", caught.exception.code)

    def test_expired_position_action_fails_closed_even_when_parent_lineage_is_structurally_valid(self):
        position = self._position()
        plan = self._plan()
        action = self._action(position=position, plan=plan)

        with self.assertRaises(ProtectionAuthorityError) as caught:
            prepare_protection_order(
                action,
                plan,
                position,
                now=self.expires_at,
            )
        self.assertEqual("POSITION_ACTION_EXPIRED", caught.exception.code)

    def test_current_position_must_remain_open_unprotected_for_initial_protect(self):
        position = self._position()
        plan = self._plan()
        action = self._action(position=position, plan=plan)

        already_protected = self._position(lifecycle_state="OPEN_PROTECTED")
        with self.assertRaises(ProtectionAuthorityError) as caught:
            prepare_protection_order(action, plan, already_protected, now=self.now)
        self.assertEqual("POSITION_NOT_OPEN_UNPROTECTED", caught.exception.code)


if __name__ == "__main__":
    unittest.main()
