import unittest
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from position import build_protect_position_action, state_allows_safe_open_claim
from src.brokers.paper import PaperBroker
from src.execution.models import OrderStatus
from src.execution.protection import prepare_protection_order


class GateBProtectionBoundaryIntegrationTests(unittest.TestCase):
    """Cross-role definitions for the accepted E5 -> E4 protection-v0.1 boundary.

    These tests intentionally call the real E5 producer, real E4 translator, and
    (where relevant) the real PaperBroker. They do not reproduce producer or
    consumer semantics in E7 helpers.
    """

    def setUp(self):
        self.action_created_at = datetime(2026, 8, 24, 3, 5, 30, tzinfo=timezone.utc)
        self.action_expires_at = datetime(2026, 8, 24, 3, 6, 30, tzinfo=timezone.utc)
        self.consume_at = datetime(2026, 8, 24, 3, 6, 0, tzinfo=timezone.utc)

    def _plan(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-gate-b-protection-001",
            "risk_decision_id": "risk-gate-b-protection-001",
            "intent_id": "intent-gate-b-protection-001",
            "strategy_id": "strategy-gate-b-protection",
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
            # Entry authority has expired before the post-fill protection action.
            # protection-v0.1 intentionally uses the action's own expiry.
            "created_at": "2026-08-24T03:00:00Z",
            "expires_at": "2026-08-24T03:00:30Z",
            "risk_policy_version": "e5-gate-b-policy-v0.1",
        }
        values.update(changes)
        return values

    def _position(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "position_id": "position-gate-b-001",
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

    def _produce_action(self, *, position=None, plan=None, created_at=None, expires_at=None):
        return build_protect_position_action(
            self._position() if position is None else position,
            self._plan() if plan is None else plan,
            created_at=self.action_created_at if created_at is None else created_at,
            expires_at=self.action_expires_at if expires_at is None else expires_at,
        )

    def _produce_and_prepare(self, *, position=None, plan=None, created_at=None, expires_at=None, now=None):
        source_position = self._position() if position is None else position
        parent_plan = self._plan() if plan is None else plan
        action = self._produce_action(
            position=source_position,
            plan=parent_plan,
            created_at=created_at,
            expires_at=expires_at,
        )
        request = prepare_protection_order(
            action,
            parent_plan,
            source_position,
            now=self.consume_at if now is None else now,
        )
        return action, request, source_position, parent_plan

    def test_partial_fill_exact_actual_exposure_propagates_e5_to_e4(self):
        action, request, position, plan = self._produce_and_prepare()

        self.assertEqual("0.0012", position["actual_quantity"])
        self.assertEqual(position["actual_quantity"], action["quantity"])
        self.assertEqual(Decimal(position["actual_quantity"]), request.quantity)
        self.assertNotEqual(plan["quantity"], action["quantity"])
        self.assertNotEqual(Decimal(plan["quantity"]), request.quantity)
        self.assertEqual("base-asset-v0.1", request.quantity_profile_version)
        self.assertEqual("BASE_ASSET", request.quantity_unit)
        self.assertEqual("BTC", request.quantity_asset)

    def test_full_fill_preserves_exact_canonical_quantity_without_provider_units(self):
        plan = self._plan(quantity="0.003")
        position = self._position(actual_quantity="0.003")
        action, request, _, _ = self._produce_and_prepare(position=position, plan=plan)

        self.assertEqual("0.003", action["quantity"])
        self.assertEqual(Decimal("0.003"), request.quantity)
        self.assertEqual("base-asset-v0.1", action["quantity_profile_version"])
        self.assertEqual("BASE_ASSET", action["quantity_unit"])
        self.assertEqual("BTC", action["quantity_asset"])

        serialized_request = asdict(request)
        for provider_field in (
            "sz",
            "contract_count",
            "ctVal",
            "ctMult",
            "ctValCcy",
            "lotSz",
            "minSz",
            "tickSz",
            "provider_instrument_id",
            "triggerPx",
        ):
            self.assertNotIn(provider_field, serialized_request)

    def test_exact_parent_protection_bounds_reach_stop_request_without_extra_execution_semantics(self):
        action, request, _, plan = self._produce_and_prepare()

        self.assertEqual(plan["protection_instruction"], action["protection_instruction"])
        self.assertEqual(Decimal(plan["protection_instruction"]["stop_level"]), request.stop_price)
        self.assertEqual("STOP_MARKET", request.order_type)
        self.assertTrue(request.reduce_only)
        self.assertIsNone(request.limit_price)
        self.assertIsNone(request.time_in_force)

        serialized_request = asdict(request)
        for non_v01_behavior in ("target_level", "take_profit", "oco", "max_hold_seconds", "exit_timer"):
            self.assertNotIn(non_v01_behavior, serialized_request)

    def test_authority_lineage_and_request_identity_are_deterministic_and_immediate_action_scoped(self):
        first_action, first_request, first_position, first_plan = self._produce_and_prepare()
        second_action, second_request, _, _ = self._produce_and_prepare(
            position=first_position,
            plan=first_plan,
        )

        self.assertEqual(first_action["position_action_id"], second_action["position_action_id"])
        self.assertEqual(first_request.client_order_id, second_request.client_order_id)
        self.assertEqual(first_request.order_request_id, second_request.order_request_id)
        self.assertEqual(first_request.safety_fingerprint(), second_request.safety_fingerprint())

        self.assertEqual(first_action["trade_plan_id"], first_request.trade_plan_id)
        self.assertEqual(first_action["risk_decision_id"], first_request.risk_decision_id)
        self.assertEqual(first_action["position_id"], first_request.position_id)
        self.assertEqual(first_action["position_action_id"], first_request.position_action_id)
        self.assertEqual("POSITION_ACTION", first_request.authorization_type)
        self.assertEqual("PROTECTION_STOP", first_request.order_role)

        later_position = self._position(
            actual_quantity="0.0010",
            broker_state_observed_at="2026-08-24T03:05:40Z",
        )
        later_created = datetime(2026, 8, 24, 3, 5, 45, tzinfo=timezone.utc)
        later_expires = later_created + timedelta(seconds=60)
        later_action, later_request, _, _ = self._produce_and_prepare(
            position=later_position,
            created_at=later_created,
            expires_at=later_expires,
        )

        self.assertNotEqual(first_action["position_action_id"], later_action["position_action_id"])
        self.assertNotEqual(first_request.client_order_id, later_request.client_order_id)
        self.assertNotEqual(first_request.order_request_id, later_request.order_request_id)
        self.assertNotEqual(first_request.safety_fingerprint(), later_request.safety_fingerprint())

    def test_expired_parent_entry_ttl_does_not_invalidate_fresh_post_fill_action(self):
        plan = self._plan()
        parent_expires_at = datetime.fromisoformat(plan["expires_at"].replace("Z", "+00:00"))
        self.assertLess(parent_expires_at, self.consume_at)

        action, request, _, _ = self._produce_and_prepare(plan=plan)
        self.assertGreater(
            datetime.fromisoformat(action["expires_at"].replace("Z", "+00:00")),
            self.consume_at,
        )
        self.assertEqual("PROTECTION_STOP", request.order_role)
        self.assertEqual(Decimal("0.0012"), request.quantity)

    def test_prepare_and_paper_submit_do_not_claim_protection_verification(self):
        action, request, position, _ = self._produce_and_prepare()
        broker = PaperBroker()
        result = broker.submit_order(request)

        self.assertEqual("PROTECT", action["action"])
        self.assertEqual(OrderStatus.OPEN, result.order_status)
        self.assertEqual("OPEN_UNPROTECTED", position["lifecycle_state"])
        self.assertFalse(state_allows_safe_open_claim(position["lifecycle_state"]))
        self.assertFalse(hasattr(result, "protection_verified"))
        self.assertNotIn("lifecycle_state", asdict(request))


if __name__ == "__main__":
    unittest.main()
