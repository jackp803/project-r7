import unittest
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.execution.close import (
    CloseAuthorityError,
    EMERGENCY_EXIT_ROLE,
    POSITION_EXIT_ROLE,
    prepare_close_order,
)
from src.execution.models import Side


class CloseV01ConsumerTests(unittest.TestCase):
    def setUp(self):
        self.position_observed_at = datetime(2026, 8, 24, 5, 10, 20, tzinfo=timezone.utc)
        self.now = datetime(2026, 8, 24, 5, 10, 30, tzinfo=timezone.utc)
        self.expires_at = self.now + timedelta(seconds=60)

    def _plan(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-close-e4-001",
            "risk_decision_id": "risk-close-e4-001",
            "intent_id": "intent-close-e4-001",
            "strategy_id": "strategy-close-e4",
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
                "stop_level": "59400",
                "target_level": "61200",
                "max_hold_seconds": 1800,
            },
            # Entry authority is intentionally expired before the close action.
            "created_at": "2026-08-24T05:00:00Z",
            "expires_at": "2026-08-24T05:00:30Z",
            "risk_policy_version": "e5-close-policy-v0.1",
        }
        values.update(changes)
        return values

    def _position(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "position_id": "position-close-e4-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": "0.0012",
            "average_entry_price": "60000",
            "opened_at": "2026-08-24T05:05:00Z",
            "broker_state_observed_at": "2026-08-24T05:10:20Z",
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": "OPEN_PROTECTED",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }
        values.update(changes)
        return values

    def _action(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "close_profile_version": "close-v0.1",
            "position_action_id": "posact-close-e4-001",
            "position_id": "position-close-e4-001",
            "action": "EXIT",
            "reason_codes": ["E5_EXIT_REQUESTED"],
            "risk_policy_version": "e5-close-policy-v0.1",
            "trade_plan_id": "plan-close-e4-001",
            "risk_decision_id": "risk-close-e4-001",
            "strategy_id": "strategy-close-e4",
            "strategy_version": "1.0.0",
            "symbol": "BTC_USDT_PERP",
            "position_side": "LONG",
            "source_lifecycle_state": "OPEN_PROTECTED",
            "position_observed_at": "2026-08-24T05:10:20Z",
            "position_reconciliation_status": "CONSISTENT",
            "quantity": "0.0012",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
            "close_order_type": "MARKET",
            "created_at": "2026-08-24T05:10:30Z",
            "expires_at": "2026-08-24T05:11:30Z",
        }
        values.update(changes)
        return values

    def _prepare(self, *, action=None, plan=None, position=None, now=None):
        return prepare_close_order(
            self._action() if action is None else action,
            self._plan() if plan is None else plan,
            self._position() if position is None else position,
            now=self.now if now is None else now,
        )

    def test_long_exit_maps_to_sell_market_reduce_only_position_exit(self):
        request = self._prepare()
        self.assertEqual(Side.SELL, request.side)
        self.assertEqual("MARKET", request.order_type)
        self.assertTrue(request.reduce_only)
        self.assertEqual("POSITION_ACTION", request.authorization_type)
        self.assertEqual(POSITION_EXIT_ROLE, request.order_role)
        self.assertEqual(Decimal("0.0012"), request.quantity)
        self.assertEqual("plan-close-e4-001", request.trade_plan_id)
        self.assertEqual("posact-close-e4-001", request.position_action_id)
        self.assertEqual("position-close-e4-001", request.position_id)
        self.assertEqual("risk-close-e4-001", request.risk_decision_id)
        self.assertIsNone(request.limit_price)
        self.assertIsNone(request.stop_price)
        self.assertIsNone(request.time_in_force)

    def test_short_exit_maps_to_buy_with_exact_lineage(self):
        plan = self._plan(direction="SHORT")
        position = self._position(side="SHORT")
        action = self._action(position_side="SHORT")
        request = self._prepare(action=action, plan=plan, position=position)
        self.assertEqual(Side.BUY, request.side)
        self.assertEqual(POSITION_EXIT_ROLE, request.order_role)
        self.assertEqual(Decimal(position["actual_quantity"]), request.quantity)
        self.assertEqual(action["position_action_id"], request.position_action_id)
        self.assertEqual(position["position_id"], request.position_id)

    def test_emergency_exit_uses_distinct_role_and_identity(self):
        position = self._position(lifecycle_state="EMERGENCY")
        action = self._action(
            action="EMERGENCY_EXIT",
            position_action_id="posact-close-e4-emergency-001",
            reason_codes=["E5_EMERGENCY_EXIT_REQUIRED"],
            source_lifecycle_state="EMERGENCY",
        )
        emergency = self._prepare(action=action, position=position)
        ordinary = self._prepare()
        self.assertEqual(EMERGENCY_EXIT_ROLE, emergency.order_role)
        self.assertEqual(Side.SELL, emergency.side)
        self.assertNotEqual(ordinary.client_order_id, emergency.client_order_id)
        self.assertNotEqual(ordinary.order_request_id, emergency.order_request_id)

    def test_same_action_is_deterministic_and_changed_authority_changes_identity(self):
        first = self._prepare()
        second = self._prepare()
        self.assertEqual(first.client_order_id, second.client_order_id)
        self.assertEqual(first.order_request_id, second.order_request_id)
        self.assertEqual(first.safety_fingerprint(), second.safety_fingerprint())

        changed = self._prepare(
            action=self._action(position_action_id="posact-close-e4-002")
        )
        self.assertNotEqual(first.client_order_id, changed.client_order_id)
        self.assertNotEqual(first.order_request_id, changed.order_request_id)

    def test_parent_entry_ttl_does_not_invalidate_valid_close_action(self):
        request = self._prepare(
            plan=self._plan(
                created_at="2026-08-24T05:00:00Z",
                expires_at="2026-08-24T05:00:30Z",
            )
        )
        self.assertEqual("MARKET", request.order_type)
        self.assertEqual(Decimal("0.0012"), request.quantity)

    def test_expired_or_unsupported_close_authority_fails_closed(self):
        cases = (
            (self._action(close_profile_version="close-v9"), self._plan(), self._position()),
            (self._action(action="HOLD"), self._plan(), self._position()),
            (self._action(close_order_type="LIMIT"), self._plan(), self._position()),
            (
                self._action(expires_at="2026-08-24T05:10:30Z"),
                self._plan(),
                self._position(),
            ),
        )
        for action, plan, position in cases:
            with self.subTest(action=action):
                with self.assertRaises(CloseAuthorityError):
                    self._prepare(action=action, plan=plan, position=position)

    def test_plan_risk_strategy_lineage_mismatch_fails_closed(self):
        fields = (
            ("trade_plan_id", "plan-other"),
            ("risk_decision_id", "risk-other"),
            ("strategy_id", "strategy-other"),
            ("strategy_version", "2.0.0"),
            ("risk_policy_version", "policy-other"),
        )
        for field, value in fields:
            with self.subTest(field=field):
                plan = self._plan(**{field: value})
                with self.assertRaises(CloseAuthorityError) as caught:
                    self._prepare(plan=plan)
                self.assertEqual("POSITION_ACTION_LINEAGE_MISMATCH", caught.exception.code)

    def test_position_identity_state_observation_and_reconciliation_mismatch_fail_closed(self):
        cases = (
            ({"position_id": "position-other"}, "POSITION_ACTION_POSITION_MISMATCH"),
            ({"symbol": "ETH_USDT_PERP"}, "POSITION_SYMBOL_MISMATCH"),
            ({"side": "SHORT"}, "POSITION_SIDE_MISMATCH"),
            ({"lifecycle_state": "EXIT_REQUESTED"}, "POSITION_ACTION_POSITION_MISMATCH"),
            (
                {"broker_state_observed_at": "2026-08-24T05:10:21Z"},
                "POSITION_ACTION_POSITION_MISMATCH",
            ),
            (
                {"reconciliation_status": "RECONCILIATION_REQUIRED"},
                "POSITION_RECONCILIATION_NOT_CONSISTENT",
            ),
        )
        for changes, code in cases:
            with self.subTest(changes=changes):
                with self.assertRaises(CloseAuthorityError) as caught:
                    self._prepare(position=self._position(**changes))
                self.assertEqual(code, caught.exception.code)

    def test_quantity_profile_unit_asset_and_exact_quantity_mismatch_fail_closed(self):
        cases = (
            ({"actual_quantity": "0.0011"}, {}, "CLOSE_QUANTITY_NOT_ACTUAL_EXPOSURE"),
            (
                {"quantity_profile_version": "legacy"},
                {},
                "POSITION_QUANTITY_PROFILE_MISMATCH",
            ),
            ({"quantity_unit": "CONTRACT"}, {}, "POSITION_QUANTITY_UNIT_MISMATCH"),
            ({"quantity_asset": "USDT"}, {}, "POSITION_QUANTITY_ASSET_MISMATCH"),
            (
                {"actual_quantity": "0.004"},
                {"quantity": "0.004"},
                "ACTUAL_QUANTITY_EXCEEDS_APPROVED_MAXIMUM",
            ),
        )
        for position_changes, action_changes, code in cases:
            with self.subTest(position_changes=position_changes):
                with self.assertRaises(CloseAuthorityError) as caught:
                    self._prepare(
                        position=self._position(**position_changes),
                        action=self._action(**action_changes),
                    )
                self.assertEqual(code, caught.exception.code)

    def test_emergency_action_requires_emergency_source_lifecycle(self):
        action = self._action(
            action="EMERGENCY_EXIT",
            position_action_id="posact-close-e4-emergency-invalid",
            reason_codes=["E5_EMERGENCY_EXIT_REQUIRED"],
            source_lifecycle_state="OPEN_PROTECTED",
        )
        with self.assertRaises(CloseAuthorityError) as caught:
            self._prepare(action=action)
        self.assertEqual("EMERGENCY_EXIT_SOURCE_LIFECYCLE_NOT_ALLOWED", caught.exception.code)

    def test_close_request_contains_no_provider_native_or_credential_fields(self):
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
            "api_key",
            "secret_key",
            "passphrase",
            "credentials",
        ):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
