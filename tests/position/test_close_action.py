import unittest
from datetime import datetime, timedelta, timezone

from position import (
    CloseActionError,
    PositionEvent,
    PositionLifecycleState,
    authorize_close_position_action,
    build_close_position_action,
    build_protect_position_action,
    default_close_reason_codes,
    transition,
    validate_close_position_action,
)


class CloseActionProducerTests(unittest.TestCase):
    def setUp(self):
        self.created_at = datetime(2026, 8, 24, 5, 10, 30, tzinfo=timezone.utc)
        self.expires_at = self.created_at + timedelta(seconds=60)

    def _plan(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-close-001",
            "risk_decision_id": "risk-close-001",
            "intent_id": "intent-close-001",
            "strategy_id": "strategy-close",
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
            # Parent entry authority is intentionally expired before close authority.
            "created_at": "2026-08-24T05:00:00Z",
            "expires_at": "2026-08-24T05:00:30Z",
            "risk_policy_version": "e5-close-policy-v0.1",
        }
        values.update(changes)
        return values

    def _position(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "position_id": "position-close-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": "0.0012",
            "average_entry_price": "60000",
            "opened_at": "2026-08-24T05:05:00Z",
            "broker_state_observed_at": "2026-08-24T05:10:20Z",
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": "OPEN_UNPROTECTED",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }
        values.update(changes)
        return values

    def _build(
        self,
        *,
        position=None,
        plan=None,
        action="EXIT",
        created_at=None,
        expires_at=None,
        reason_codes=None,
    ):
        return build_close_position_action(
            self._position() if position is None else position,
            self._plan() if plan is None else plan,
            action=action,
            created_at=self.created_at if created_at is None else created_at,
            expires_at=self.expires_at if expires_at is None else expires_at,
            reason_codes=reason_codes,
        )

    def _authorize(
        self,
        *,
        position=None,
        plan=None,
        action="EXIT",
        reason_codes=None,
    ):
        return authorize_close_position_action(
            self._position() if position is None else position,
            self._plan() if plan is None else plan,
            action=action,
            created_at=self.created_at,
            expires_at=self.expires_at,
            reason_codes=reason_codes,
        )

    def test_open_unprotected_exit_uses_exact_actual_quantity_and_parent_lineage(self):
        position = self._position(actual_quantity="0.0012")
        plan = self._plan(quantity="0.003")
        action = self._build(position=position, plan=plan)

        self.assertEqual("contracts-v0.1", action["schema_version"])
        self.assertEqual("close-v0.1", action["close_profile_version"])
        self.assertEqual("EXIT", action["action"])
        self.assertEqual(["E5_EXIT_REQUESTED"], action["reason_codes"])
        self.assertEqual(position["actual_quantity"], action["quantity"])
        self.assertNotEqual(plan["quantity"], action["quantity"])
        self.assertEqual(plan["trade_plan_id"], action["trade_plan_id"])
        self.assertEqual(plan["risk_decision_id"], action["risk_decision_id"])
        self.assertEqual(plan["strategy_id"], action["strategy_id"])
        self.assertEqual(plan["strategy_version"], action["strategy_version"])
        self.assertEqual(plan["risk_policy_version"], action["risk_policy_version"])
        self.assertEqual(position["position_id"], action["position_id"])
        self.assertEqual("OPEN_UNPROTECTED", action["source_lifecycle_state"])
        self.assertEqual("MARKET", action["close_order_type"])
        self.assertEqual("base-asset-v0.1", action["quantity_profile_version"])
        self.assertEqual("BASE_ASSET", action["quantity_unit"])
        self.assertEqual("BTC", action["quantity_asset"])

    def test_open_protected_and_profit_protected_support_ordinary_exit(self):
        for lifecycle in ("OPEN_PROTECTED", "PROFIT_PROTECTED"):
            with self.subTest(lifecycle=lifecycle):
                position = self._position(lifecycle_state=lifecycle)
                outcome = self._authorize(position=position, action="EXIT")
                self.assertEqual("EXIT", outcome.position_action["action"])
                self.assertEqual(lifecycle, outcome.position_action["source_lifecycle_state"])
                self.assertEqual(PositionEvent.EXIT_REQUESTED, outcome.event)
                self.assertEqual(PositionLifecycleState.EXIT_REQUESTED, outcome.next_state)

    def test_emergency_state_supports_distinct_emergency_exit(self):
        position = self._position(lifecycle_state="EMERGENCY")
        outcome = self._authorize(position=position, action="EMERGENCY_EXIT")

        self.assertEqual("EMERGENCY_EXIT", outcome.position_action["action"])
        self.assertEqual(["E5_EMERGENCY_EXIT_REQUIRED"], outcome.position_action["reason_codes"])
        self.assertEqual("EMERGENCY", outcome.position_action["source_lifecycle_state"])
        self.assertEqual(PositionEvent.EXIT_REQUESTED, outcome.event)
        self.assertEqual(PositionLifecycleState.EXIT_REQUESTED, outcome.next_state)

    def test_wrong_action_lifecycle_combinations_fail_closed(self):
        forbidden_exit_states = (
            "PENDING_ENTRY",
            "EXIT_REQUESTED",
            "CLOSED",
            "RECONCILIATION_REQUIRED",
            "EMERGENCY",
            "SOMETHING_NEW",
        )
        for lifecycle in forbidden_exit_states:
            with self.subTest(action="EXIT", lifecycle=lifecycle):
                with self.assertRaises(CloseActionError):
                    self._build(position=self._position(lifecycle_state=lifecycle), action="EXIT")

        for lifecycle in (
            "OPEN_UNPROTECTED",
            "OPEN_PROTECTED",
            "PROFIT_PROTECTED",
            "PENDING_ENTRY",
            "EXIT_REQUESTED",
            "CLOSED",
            "RECONCILIATION_REQUIRED",
        ):
            with self.subTest(action="EMERGENCY_EXIT", lifecycle=lifecycle):
                with self.assertRaises(CloseActionError):
                    self._build(
                        position=self._position(lifecycle_state=lifecycle),
                        action="EMERGENCY_EXIT",
                    )

        with self.assertRaises(CloseActionError):
            self._build(action="HOLD")

    def test_zero_negative_and_nonfinite_actual_quantity_fail_closed(self):
        for quantity in ("0", "-0.001", "NaN", "Infinity"):
            with self.subTest(quantity=quantity):
                with self.assertRaises(CloseActionError):
                    self._build(position=self._position(actual_quantity=quantity))

    def test_unknown_mismatch_and_reconciliation_required_position_truth_fail_closed(self):
        for status in ("UNKNOWN", "MISMATCH", "RECONCILIATION_REQUIRED"):
            with self.subTest(status=status):
                with self.assertRaises(CloseActionError) as caught:
                    self._build(position=self._position(reconciliation_status=status))
                self.assertEqual("POSITION_RECONCILIATION_NOT_CONSISTENT", caught.exception.code)

    def test_actual_quantity_above_parent_approved_maximum_fails_closed(self):
        with self.assertRaises(CloseActionError) as caught:
            self._build(
                position=self._position(actual_quantity="0.004"),
                plan=self._plan(quantity="0.003"),
            )
        self.assertEqual("ACTUAL_QUANTITY_EXCEEDS_APPROVED_MAXIMUM", caught.exception.code)

    def test_position_and_parent_quantity_semantic_mismatch_fail_closed(self):
        cases = (
            ({"symbol": "ETH_USDT_PERP"}, "POSITION_SYMBOL_MISMATCH"),
            ({"side": "SHORT"}, "POSITION_SIDE_MISMATCH"),
            ({"quantity_profile_version": "legacy"}, "POSITION_QUANTITY_PROFILE_MISMATCH"),
            ({"quantity_unit": "CONTRACT"}, "POSITION_QUANTITY_UNIT_MISMATCH"),
            ({"quantity_asset": "USDT"}, "POSITION_QUANTITY_ASSET_MISMATCH"),
        )
        for changes, expected_code in cases:
            with self.subTest(changes=changes):
                with self.assertRaises(CloseActionError) as caught:
                    self._build(position=self._position(**changes))
                self.assertEqual(expected_code, caught.exception.code)

    def test_plan_risk_strategy_lineage_tampering_fails_closed(self):
        position = self._position()
        plan = self._plan()
        action = self._build(position=position, plan=plan)

        cases = (
            ("trade_plan_id", "plan-other"),
            ("risk_decision_id", "risk-other"),
            ("strategy_id", "strategy-other"),
            ("strategy_version", "2.0.0"),
            ("risk_policy_version", "policy-other"),
        )
        for field, value in cases:
            with self.subTest(field=field):
                tampered_plan = dict(plan)
                tampered_plan[field] = value
                with self.assertRaises(CloseActionError) as caught:
                    validate_close_position_action(
                        action,
                        position,
                        tampered_plan,
                        now=self.created_at,
                    )
                self.assertEqual("POSITION_ACTION_LINEAGE_MISMATCH", caught.exception.code)

    def test_close_action_expiry_is_independent_of_expired_parent_entry_ttl(self):
        plan = self._plan(
            created_at="2026-08-24T05:00:00Z",
            expires_at="2026-08-24T05:00:30Z",
        )
        action = self._build(plan=plan)

        self.assertEqual("2026-08-24T05:10:30Z", action["created_at"])
        self.assertEqual("2026-08-24T05:11:30Z", action["expires_at"])
        validate_close_position_action(action, self._position(), plan, now=self.created_at)

        with self.assertRaises(CloseActionError) as caught:
            validate_close_position_action(action, self._position(), plan, now=self.expires_at)
        self.assertEqual("POSITION_ACTION_EXPIRED", caught.exception.code)

    def test_reason_sequence_and_action_identity_are_deterministic(self):
        first = self._build()
        second = self._build()
        self.assertEqual(first["reason_codes"], second["reason_codes"])
        self.assertEqual(first["position_action_id"], second["position_action_id"])
        self.assertEqual(("E5_EXIT_REQUESTED",), default_close_reason_codes("EXIT"))

        custom_reasons = ("E5_EXIT_REQUESTED", "E5_TIME_STOP")
        custom_first = self._build(reason_codes=custom_reasons)
        custom_second = self._build(reason_codes=custom_reasons)
        self.assertEqual(list(custom_reasons), custom_first["reason_codes"])
        self.assertEqual(custom_first["position_action_id"], custom_second["position_action_id"])
        self.assertNotEqual(first["position_action_id"], custom_first["position_action_id"])

        with self.assertRaises(CloseActionError):
            self._build(reason_codes=())

    def test_authority_changes_change_position_action_identity(self):
        baseline = self._build()

        newer_observation = self._build(
            position=self._position(broker_state_observed_at="2026-08-24T05:10:25Z")
        )
        residual_quantity = self._build(position=self._position(actual_quantity="0.0010"))
        changed_risk = self._build(plan=self._plan(risk_decision_id="risk-close-002"))
        changed_reason = self._build(reason_codes=("E5_EXIT_REQUESTED", "E5_MANUAL_EXIT"))

        for changed in (
            newer_observation,
            residual_quantity,
            changed_risk,
            changed_reason,
        ):
            self.assertNotEqual(baseline["position_action_id"], changed["position_action_id"])

        emergency = self._build(
            position=self._position(lifecycle_state="EMERGENCY"),
            action="EMERGENCY_EXIT",
        )
        self.assertNotEqual(baseline["position_action_id"], emergency["position_action_id"])

        emergency_changed_reason = self._build(
            position=self._position(lifecycle_state="EMERGENCY"),
            action="EMERGENCY_EXIT",
            reason_codes=("E5_EMERGENCY_EXIT_REQUIRED", "E5_PROTECTION_FAILURE"),
        )
        self.assertNotEqual(
            emergency["position_action_id"],
            emergency_changed_reason["position_action_id"],
        )

    def test_action_creation_reaches_exit_requested_only_and_never_closed(self):
        for lifecycle, action_type in (
            ("OPEN_UNPROTECTED", "EXIT"),
            ("OPEN_PROTECTED", "EXIT"),
            ("PROFIT_PROTECTED", "EXIT"),
            ("EMERGENCY", "EMERGENCY_EXIT"),
        ):
            with self.subTest(lifecycle=lifecycle, action=action_type):
                outcome = self._authorize(
                    position=self._position(lifecycle_state=lifecycle),
                    action=action_type,
                )
                self.assertEqual(PositionEvent.EXIT_REQUESTED, outcome.event)
                self.assertEqual(PositionLifecycleState.EXIT_REQUESTED, outcome.next_state)
                self.assertNotEqual(PositionLifecycleState.CLOSED, outcome.next_state)
                self.assertNotIn("closed_at", outcome.position_action)
                self.assertNotIn("position_closed", outcome.position_action)

    def test_position_closed_requires_later_existing_state_machine_event_not_close_creation(self):
        self.assertEqual(
            PositionLifecycleState.EXIT_REQUESTED,
            transition(PositionLifecycleState.OPEN_PROTECTED, PositionEvent.EXIT_REQUESTED),
        )
        self.assertEqual(
            PositionLifecycleState.CLOSED,
            transition(PositionLifecycleState.EXIT_REQUESTED, PositionEvent.POSITION_CLOSED),
        )
        self.assertEqual(
            PositionLifecycleState.EMERGENCY,
            transition(PositionLifecycleState.EXIT_REQUESTED, PositionEvent.EXIT_FAILED),
        )

        outcome = self._authorize(position=self._position(lifecycle_state="OPEN_PROTECTED"))
        self.assertEqual(PositionLifecycleState.EXIT_REQUESTED, outcome.next_state)
        self.assertNotEqual(PositionEvent.POSITION_CLOSED, outcome.event)

    def test_existing_protection_producer_remains_compatible(self):
        plan = self._plan()
        position = self._position(lifecycle_state="OPEN_UNPROTECTED")
        protect_action = build_protect_position_action(
            position,
            plan,
            created_at=self.created_at,
            expires_at=self.expires_at,
        )
        close_action = self._build(position=position, plan=plan)

        self.assertEqual("PROTECT", protect_action["action"])
        self.assertEqual("protection-v0.1", protect_action["protection_profile_version"])
        self.assertEqual("EXIT", close_action["action"])
        self.assertEqual("close-v0.1", close_action["close_profile_version"])
        self.assertEqual(position["actual_quantity"], protect_action["quantity"])
        self.assertEqual(position["actual_quantity"], close_action["quantity"])

    def test_provider_native_and_credential_fields_are_absent(self):
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
            "broker_order_id",
            "api_key",
            "api_secret",
            "credentials",
            "signature",
        ):
            self.assertNotIn(forbidden, action)


if __name__ == "__main__":
    unittest.main()
