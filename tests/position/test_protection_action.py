import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from position import (
    PositionLifecycleState,
    ProtectionActionError,
    build_protect_position_action,
    state_allows_safe_open_claim,
    validate_protection_action,
)


class ProtectionActionProducerTests(unittest.TestCase):
    def setUp(self):
        self.created_at = datetime(2026, 8, 24, 3, 5, 30, tzinfo=timezone.utc)
        self.expires_at = self.created_at + timedelta(seconds=30)

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

    def _build(self, position=None, plan=None, created_at=None, expires_at=None):
        return build_protect_position_action(
            self._position() if position is None else position,
            self._plan() if plan is None else plan,
            created_at=self.created_at if created_at is None else created_at,
            expires_at=self.expires_at if expires_at is None else expires_at,
        )

    def test_partial_actual_fill_is_exact_protection_quantity(self):
        position = self._position(actual_quantity="0.0012")
        action = self._build(position=position)

        self.assertEqual("PROTECT", action["action"])
        self.assertEqual("protection-v0.1", action["protection_profile_version"])
        self.assertEqual("0.0012", action["quantity"])
        self.assertEqual(position["actual_quantity"], action["quantity"])
        self.assertNotEqual(self._plan()["quantity"], action["quantity"])
        self.assertEqual("base-asset-v0.1", action["quantity_profile_version"])
        self.assertEqual("BASE_ASSET", action["quantity_unit"])
        self.assertEqual("BTC", action["quantity_asset"])

    def test_full_actual_fill_is_exact_protection_quantity(self):
        position = self._position(actual_quantity=self._plan()["quantity"])
        action = self._build(position=position)

        self.assertEqual("0.003", action["quantity"])
        self.assertEqual(position["actual_quantity"], action["quantity"])

    def test_action_quantity_cannot_exceed_actual_open_exposure(self):
        position = self._position(actual_quantity="0.0012")
        plan = self._plan()
        action = self._build(position=position, plan=plan)
        forged = dict(action)
        forged["quantity"] = "0.002"

        with self.assertRaises(ProtectionActionError) as caught:
            validate_protection_action(
                forged,
                position,
                plan,
                now=self.created_at,
            )
        self.assertEqual("PROTECTION_QUANTITY_NOT_ACTUAL_EXPOSURE", caught.exception.code)

    def test_actual_exposure_over_parent_maximum_fails_closed(self):
        position = self._position(actual_quantity="0.004")

        with self.assertRaises(ProtectionActionError) as caught:
            self._build(position=position)
        self.assertEqual("ACTUAL_QUANTITY_EXCEEDS_APPROVED_MAXIMUM", caught.exception.code)

    def test_unreconciled_position_truth_cannot_produce_protect(self):
        for status in ("UNKNOWN", "MISMATCH", "RECONCILIATION_REQUIRED"):
            with self.subTest(status=status):
                with self.assertRaises(ProtectionActionError) as caught:
                    self._build(position=self._position(reconciliation_status=status))
                self.assertEqual("POSITION_RECONCILIATION_NOT_CONSISTENT", caught.exception.code)

    def test_zero_negative_and_nonfinite_actual_quantity_fail_closed(self):
        for quantity in ("0", "-0.001", "NaN", "Infinity"):
            with self.subTest(quantity=quantity):
                with self.assertRaises(ProtectionActionError):
                    self._build(position=self._position(actual_quantity=quantity))

    def test_position_symbol_side_identity_and_quantity_profile_mismatch_fail_closed(self):
        cases = (
            ({"symbol": "ETH_USDT_PERP"}, "POSITION_SYMBOL_MISMATCH"),
            ({"side": "SHORT"}, "POSITION_SIDE_MISMATCH"),
            ({"quantity_profile_version": "legacy"}, "POSITION_QUANTITY_PROFILE_MISMATCH"),
            ({"quantity_unit": "CONTRACT"}, "POSITION_QUANTITY_UNIT_MISMATCH"),
            ({"quantity_asset": "USDT"}, "POSITION_QUANTITY_ASSET_MISMATCH"),
        )
        for changes, expected_code in cases:
            with self.subTest(changes=changes):
                with self.assertRaises(ProtectionActionError) as caught:
                    self._build(position=self._position(**changes))
                self.assertEqual(expected_code, caught.exception.code)

        with self.assertRaises(ProtectionActionError):
            self._build(position=self._position(position_id=""))

        position = self._position()
        plan = self._plan()
        action = self._build(position=position, plan=plan)
        different_position = self._position(position_id="position-002")
        with self.assertRaises(ProtectionActionError) as caught:
            validate_protection_action(action, different_position, plan, now=self.created_at)
        self.assertEqual("POSITION_ACTION_POSITION_MISMATCH", caught.exception.code)

    def test_parent_stop_target_and_max_hold_are_copied_exactly(self):
        plan = self._plan(
            protection_instruction={
                "stop_level": "59400.00",
                "target_level": "61200.00",
                "max_hold_seconds": 1800,
            }
        )
        action = self._build(plan=plan)

        self.assertEqual(plan["trade_plan_id"], action["trade_plan_id"])
        self.assertEqual(plan["risk_decision_id"], action["risk_decision_id"])
        self.assertEqual(plan["risk_policy_version"], action["risk_policy_version"])
        self.assertEqual(plan["protection_instruction"], action["protection_instruction"])
        self.assertEqual("59400.00", action["protection_instruction"]["stop_level"])
        self.assertEqual("61200.00", action["protection_instruction"]["target_level"])
        self.assertEqual(1800, action["protection_instruction"]["max_hold_seconds"])

    def test_position_action_id_is_stable_and_changes_with_authority_material(self):
        position = self._position()
        plan = self._plan()
        first = self._build(position=position, plan=plan)
        second = self._build(position=position, plan=plan)
        self.assertEqual(first["position_action_id"], second["position_action_id"])

        changed_position = self._position(
            actual_quantity="0.0010",
            broker_state_observed_at="2026-08-24T03:05:25Z",
        )
        changed = self._build(position=changed_position, plan=plan)
        self.assertNotEqual(first["position_action_id"], changed["position_action_id"])

    def test_invalid_and_expired_action_timing_fail_closed(self):
        with self.assertRaises(ProtectionActionError) as caught:
            self._build(expires_at=self.created_at)
        self.assertEqual("INVALID_ACTION_EXPIRY", caught.exception.code)

        future_observation = self._position(
            broker_state_observed_at="2026-08-24T03:05:40Z"
        )
        with self.assertRaises(ProtectionActionError) as caught:
            self._build(position=future_observation)
        self.assertEqual("POSITION_OBSERVATION_AFTER_ACTION_CREATION", caught.exception.code)

        position = self._position()
        plan = self._plan()
        action = self._build(position=position, plan=plan)
        with self.assertRaises(ProtectionActionError) as caught:
            validate_protection_action(action, position, plan, now=self.expires_at)
        self.assertEqual("POSITION_ACTION_EXPIRED", caught.exception.code)

    def test_legacy_or_unsupported_protection_profile_fails_closed(self):
        position = self._position()
        plan = self._plan()
        action = self._build(position=position, plan=plan)

        legacy = dict(action)
        legacy.pop("protection_profile_version")
        with self.assertRaises(ProtectionActionError) as caught:
            validate_protection_action(legacy, position, plan, now=self.created_at)
        self.assertEqual("POSITION_ACTION_INCOMPLETE", caught.exception.code)

        unsupported = dict(action)
        unsupported["protection_profile_version"] = "protection-v9.9"
        with self.assertRaises(ProtectionActionError) as caught:
            validate_protection_action(unsupported, position, plan, now=self.created_at)
        self.assertEqual("UNSUPPORTED_PROTECTION_PROFILE", caught.exception.code)

    def test_modify_protection_is_not_executable_under_v01(self):
        position = self._position()
        plan = self._plan()
        action = self._build(position=position, plan=plan)
        modified = dict(action)
        modified["action"] = "MODIFY_PROTECTION"

        with self.assertRaises(ProtectionActionError) as caught:
            validate_protection_action(modified, position, plan, now=self.created_at)
        self.assertEqual("UNSUPPORTED_PROTECTION_ACTION", caught.exception.code)

    def test_producing_protect_does_not_mark_position_protected(self):
        position = self._position(lifecycle_state="OPEN_UNPROTECTED")
        action = self._build(position=position)

        self.assertEqual("PROTECT", action["action"])
        self.assertEqual("OPEN_UNPROTECTED", position["lifecycle_state"])
        self.assertFalse(state_allows_safe_open_claim(position["lifecycle_state"]))
        self.assertEqual(PositionLifecycleState.OPEN_UNPROTECTED.value, position["lifecycle_state"])

    def test_provider_native_fields_are_absent_from_position_action(self):
        action = self._build()
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
        ):
            self.assertNotIn(forbidden, action)


if __name__ == "__main__":
    unittest.main()
