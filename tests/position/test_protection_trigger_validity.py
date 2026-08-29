import inspect
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import position.protection_trigger_validity as trigger_module
from position import (
    ACTIONABLE,
    FAIL_CLOSED,
    FRESH,
    STALE,
    UNKNOWN,
    ProtectionActionError,
    build_position_lifecycle_genesis,
    build_position_lifecycle_reattestation,
    build_protect_position_action,
    build_protection_trigger_validity_evidence,
    protection_trigger_validity_evidence_is_current,
    protection_trigger_validity_is_actionable,
    stable_protection_trigger_validity_id,
    validate_protection_action,
    validate_protection_trigger_validity_evidence,
)
from src.market_data.current import MarketSnapshot


class ProtectionTriggerValidityV01Tests(unittest.TestCase):
    def setUp(self):
        self.position_time = datetime(2026, 8, 29, 4, 0, 0, tzinfo=timezone.utc)
        self.action_time = self.position_time + timedelta(seconds=1)
        self.market_observed = self.position_time + timedelta(seconds=2)
        self.market_received = self.position_time + timedelta(seconds=3)
        self.evaluated_at = self.position_time + timedelta(seconds=4)

    def _plan(self, *, side="LONG", stop=None, **changes):
        if stop is None:
            stop = "59400.00" if side == "LONG" else "60600.00"
        values = {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-fp03-001",
            "risk_decision_id": "risk-fp03-001",
            "intent_id": "intent-fp03-001",
            "strategy_id": "strategy-fp03",
            "strategy_version": "1.0.0",
            "symbol": "BTC_USDT_PERP",
            "direction": side,
            "quantity": "0.003",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
            "leverage": "20",
            "margin_mode": "ISOLATED",
            "entry_instruction": {"profile_version": "entry-v0.1", "order_type": "MARKET"},
            "protection_instruction": {
                "stop_level": stop,
                "target_level": "61200.00" if side == "LONG" else "58800.00",
                "max_hold_seconds": 1800,
            },
            "created_at": "2026-08-29T03:59:00Z",
            "expires_at": "2026-08-29T03:59:30Z",
            "risk_policy_version": "e5-fp03-policy-v0.1",
        }
        values.update(changes)
        return values

    def _position(self, *, side="LONG", observed_at=None, **changes):
        observed = self.position_time if observed_at is None else observed_at
        values = {
            "schema_version": "contracts-v0.1",
            "position_id": "position-fp03-001",
            "symbol": "BTC_USDT_PERP",
            "side": side,
            "actual_quantity": "0.0012",
            "average_entry_price": "60000",
            "opened_at": "2026-08-29T03:59:50Z",
            "broker_state_observed_at": observed.isoformat().replace("+00:00", "Z"),
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": "OPEN_UNPROTECTED",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }
        values.update(changes)
        return values

    def _action(self, *, side="LONG", position=None, plan=None, created_at=None):
        source = self._position(side=side) if position is None else position
        parent = self._plan(side=side) if plan is None else plan
        created = self.action_time if created_at is None else created_at
        return build_protect_position_action(
            source,
            parent,
            created_at=created,
            expires_at=created + timedelta(seconds=60),
        )

    def _market(
        self,
        price="60000",
        *,
        health="HEALTHY",
        observed_at=None,
        received_at=None,
        symbol="BTC_USDT_PERP",
        freshness_ms=100,
    ):
        return MarketSnapshot(
            schema_version="contracts-v0.1",
            symbol=symbol,
            observed_at=self.market_observed if observed_at is None else observed_at,
            received_at=self.market_received if received_at is None else received_at,
            health_status=health,
            source="OKX_PUBLIC_TICKER",
            last_price=Decimal(price),
            best_bid=Decimal(price) - Decimal("1"),
            best_ask=Decimal(price) + Decimal("1"),
            freshness_ms=freshness_ms,
        )

    def _evidence(
        self,
        *,
        side="LONG",
        price="60000",
        position=None,
        plan=None,
        action=None,
        market=None,
        classification=FRESH,
        evaluated_at=None,
        semantic="LAST_PRICE",
    ):
        source = self._position(side=side) if position is None else position
        parent = self._plan(side=side) if plan is None else plan
        authority = self._action(side=side, position=source, plan=parent) if action is None else action
        snapshot = self._market(price) if market is None else market
        return build_protection_trigger_validity_evidence(
            source,
            authority,
            parent,
            snapshot,
            market_freshness_classification=classification,
            evaluated_at=self.evaluated_at if evaluated_at is None else evaluated_at,
            trigger_reference_semantic=semantic,
        )

    def test_long_valid(self):
        evidence = self._evidence(side="LONG", price="60000")
        self.assertEqual(ACTIONABLE, evidence["validity_status"])
        self.assertEqual(["PROTECTION_TRIGGER_ACTIONABLE"], evidence["reason_codes"])
        self.assertEqual("NONE", evidence["handoff_category"])
        self.assertEqual("LAST_PRICE", evidence["trigger_reference_semantic"])
        self.assertEqual("60000", evidence["trigger_reference_price"])
        self.assertTrue(protection_trigger_validity_is_actionable(evidence))

    def test_short_valid(self):
        evidence = self._evidence(side="SHORT", price="60000")
        self.assertEqual(ACTIONABLE, evidence["validity_status"])
        self.assertEqual("SHORT", evidence["position_side"])
        self.assertEqual("60600.00", evidence["stop_level"])
        self.assertTrue(protection_trigger_validity_is_actionable(evidence))

    def test_long_equality_breached(self):
        evidence = self._evidence(side="LONG", price="59400.00")
        self.assertEqual(FAIL_CLOSED, evidence["validity_status"])
        self.assertEqual(["TRIGGER_ALREADY_BREACHED"], evidence["reason_codes"])
        self.assertEqual("E5_PROTECTION_POLICY_REEVALUATION_REQUIRED", evidence["handoff_category"])
        self.assertFalse(protection_trigger_validity_is_actionable(evidence))

    def test_short_equality_breached(self):
        evidence = self._evidence(side="SHORT", price="60600.00")
        self.assertEqual(FAIL_CLOSED, evidence["validity_status"])
        self.assertEqual(["TRIGGER_ALREADY_BREACHED"], evidence["reason_codes"])

    def test_long_crossed(self):
        evidence = self._evidence(side="LONG", price="59000")
        self.assertEqual(FAIL_CLOSED, evidence["validity_status"])
        self.assertEqual(["TRIGGER_ALREADY_BREACHED"], evidence["reason_codes"])

    def test_short_crossed(self):
        evidence = self._evidence(side="SHORT", price="61000")
        self.assertEqual(FAIL_CLOSED, evidence["validity_status"])
        self.assertEqual(["TRIGGER_ALREADY_BREACHED"], evidence["reason_codes"])

    def test_stale_market_uses_e1_attested_classification_without_second_threshold(self):
        evidence = self._evidence(classification=STALE)
        self.assertEqual(FAIL_CLOSED, evidence["validity_status"])
        self.assertEqual(["MARKET_EVIDENCE_STALE"], evidence["reason_codes"])
        self.assertEqual("REFRESH_MARKET_EVIDENCE_REQUIRED", evidence["handoff_category"])
        self.assertEqual(STALE, evidence["market_freshness_classification"])

    def test_unknown_market_fails_closed(self):
        market = self._market(health="UNKNOWN")
        evidence = self._evidence(market=market, classification=UNKNOWN)
        self.assertEqual(FAIL_CLOSED, evidence["validity_status"])
        self.assertIn("MARKET_EVIDENCE_UNKNOWN", evidence["reason_codes"])
        self.assertFalse(protection_trigger_validity_is_actionable(evidence))

    def test_stale_position_evidence_fails_closed(self):
        old_position = self._position()
        plan = self._plan()
        action = self._action(position=old_position, plan=plan)
        newer_position = self._position(observed_at=self.position_time + timedelta(seconds=5))
        evidence = self._evidence(position=newer_position, plan=plan, action=action)
        self.assertEqual(FAIL_CLOSED, evidence["validity_status"])
        self.assertIn("POSITION_AUTHORITY_STALE", evidence["reason_codes"])
        self.assertEqual("POSITION_RECONCILIATION_REQUIRED", evidence["handoff_category"])

    def test_mismatched_side_fails_closed_before_breach_interpretation(self):
        long_position = self._position(side="LONG")
        plan = self._plan(side="LONG")
        action = self._action(side="LONG", position=long_position, plan=plan)
        contradictory_position = self._position(side="SHORT")
        evidence = self._evidence(
            side="SHORT",
            position=contradictory_position,
            plan=plan,
            action=action,
        )
        self.assertEqual(FAIL_CLOSED, evidence["validity_status"])
        self.assertIn("POSITION_AUTHORITY_MISMATCH", evidence["reason_codes"])
        self.assertIn("TRIGGER_SIDE_OR_GEOMETRY_INVALID", evidence["reason_codes"])
        self.assertNotIn("PROTECTION_TRIGGER_ACTIONABLE", evidence["reason_codes"])

    def test_unsupported_trigger_reference_fails_closed(self):
        evidence = self._evidence(semantic="MARK_PRICE")
        self.assertEqual(FAIL_CLOSED, evidence["validity_status"])
        self.assertEqual(["TRIGGER_REFERENCE_SEMANTIC_UNSUPPORTED"], evidence["reason_codes"])
        self.assertEqual("E5_PROTECTION_POLICY_REEVALUATION_REQUIRED", evidence["handoff_category"])

    def test_temporal_precompute_fails_closed(self):
        evidence = self._evidence(evaluated_at=self.market_received - timedelta(milliseconds=1))
        self.assertEqual(FAIL_CLOSED, evidence["validity_status"])
        self.assertEqual(["TEMPORAL_ORDER_INVALID"], evidence["reason_codes"])
        self.assertEqual("REFRESH_MARKET_EVIDENCE_REQUIRED", evidence["handoff_category"])

    def test_unchanged_breached_evidence_does_not_become_retryable_when_only_time_advances(self):
        position = self._position()
        plan = self._plan()
        action = self._action(position=position, plan=plan)
        market = self._market("59000")
        first = self._evidence(position=position, plan=plan, action=action, market=market)
        later = self._evidence(
            position=position,
            plan=plan,
            action=action,
            market=market,
            evaluated_at=self.evaluated_at + timedelta(seconds=1),
        )
        self.assertEqual(["TRIGGER_ALREADY_BREACHED"], first["reason_codes"])
        self.assertEqual(["TRIGGER_ALREADY_BREACHED"], later["reason_codes"])
        self.assertFalse(protection_trigger_validity_is_actionable(first))
        self.assertFalse(protection_trigger_validity_is_actionable(later))
        self.assertTrue(
            protection_trigger_validity_evidence_is_current(
                first,
                position,
                action,
                market,
                market_freshness_classification=FRESH,
            )
        )
        self.assertNotEqual(first["protection_trigger_validity_id"], later["protection_trigger_validity_id"])

    def test_new_market_reevaluation_invalidates_old_evidence_and_can_change_geometry_result(self):
        position = self._position()
        plan = self._plan()
        action = self._action(position=position, plan=plan)
        old_market = self._market("59000")
        old = self._evidence(position=position, plan=plan, action=action, market=old_market)

        new_observed = self.market_observed + timedelta(seconds=2)
        new_received = self.market_received + timedelta(seconds=2)
        new_market = self._market(
            "60000",
            observed_at=new_observed,
            received_at=new_received,
        )
        self.assertFalse(
            protection_trigger_validity_evidence_is_current(
                old,
                position,
                action,
                new_market,
                market_freshness_classification=FRESH,
            )
        )
        new = self._evidence(
            position=position,
            plan=plan,
            action=action,
            market=new_market,
            evaluated_at=new_received + timedelta(seconds=1),
        )
        self.assertEqual(ACTIONABLE, new["validity_status"])
        self.assertNotEqual(old["market_snapshot_ref"], new["market_snapshot_ref"])
        self.assertNotEqual(old["protection_trigger_validity_id"], new["protection_trigger_validity_id"])

    def test_new_position_requires_new_protection_authority(self):
        old_position = self._position()
        plan = self._plan()
        old_action = self._action(position=old_position, plan=plan)
        market = self._market("60000")
        old_evidence = self._evidence(position=old_position, plan=plan, action=old_action, market=market)

        newer_position = self._position(observed_at=self.position_time + timedelta(seconds=5))
        self.assertFalse(
            protection_trigger_validity_evidence_is_current(
                old_evidence,
                newer_position,
                old_action,
                market,
                market_freshness_classification=FRESH,
            )
        )
        stale = self._evidence(
            position=newer_position,
            plan=plan,
            action=old_action,
            market=market,
            evaluated_at=self.position_time + timedelta(seconds=7),
        )
        self.assertEqual(FAIL_CLOSED, stale["validity_status"])
        self.assertIn("POSITION_AUTHORITY_STALE", stale["reason_codes"])

        new_action = self._action(
            position=newer_position,
            plan=plan,
            created_at=self.position_time + timedelta(seconds=6),
        )
        self.assertNotEqual(old_action["position_action_id"], new_action["position_action_id"])
        refreshed = self._evidence(
            position=newer_position,
            plan=plan,
            action=new_action,
            market=market,
            evaluated_at=self.position_time + timedelta(seconds=7),
        )
        self.assertEqual(ACTIONABLE, refreshed["validity_status"])

    def test_new_lifecycle_projection_invalidates_old_evidence_even_on_same_broker_anchor(self):
        raw = self._position()
        plan = self._plan()
        action = self._action(position=raw, plan=plan)
        genesis = build_position_lifecycle_genesis(
            raw,
            lifecycle_state="OPEN_UNPROTECTED",
            lifecycle_interpreted_at=self.position_time + timedelta(milliseconds=500),
        )
        first = self._evidence(position=genesis, plan=plan, action=action)
        reattested = build_position_lifecycle_reattestation(
            raw,
            genesis,
            lifecycle_interpreted_at=self.position_time + timedelta(milliseconds=750),
        )
        self.assertEqual(genesis["broker_state_observed_at"], reattested["broker_state_observed_at"])
        self.assertFalse(
            protection_trigger_validity_evidence_is_current(
                first,
                reattested,
                action,
                self._market(),
                market_freshness_classification=FRESH,
            )
        )
        second = self._evidence(position=reattested, plan=plan, action=action)
        self.assertEqual(ACTIONABLE, second["validity_status"])
        self.assertNotEqual(first["position_authority_ref"], second["position_authority_ref"])

    def test_deterministic_evidence_identity_and_material_change(self):
        position = self._position()
        plan = self._plan()
        action = self._action(position=position, plan=plan)
        market = self._market()
        first = self._evidence(position=position, plan=plan, action=action, market=market)
        replay = self._evidence(position=position, plan=plan, action=action, market=market)
        self.assertEqual(first, replay)
        self.assertEqual(
            first["protection_trigger_validity_id"],
            stable_protection_trigger_validity_id(first),
        )
        validate_protection_trigger_validity_evidence(first)

        changed_time = self._evidence(
            position=position,
            plan=plan,
            action=action,
            market=market,
            evaluated_at=self.evaluated_at + timedelta(milliseconds=1),
        )
        self.assertNotEqual(
            first["protection_trigger_validity_id"],
            changed_time["protection_trigger_validity_id"],
        )

    def test_material_stop_policy_change_requires_new_action_identity(self):
        position = self._position()
        old_plan = self._plan(stop="59400.00")
        old_action = self._action(position=position, plan=old_plan)
        old_evidence = self._evidence(position=position, plan=old_plan, action=old_action)

        changed_plan = self._plan(stop="59500.00")
        changed_action = self._action(position=position, plan=changed_plan)
        self.assertNotEqual(old_action["position_action_id"], changed_action["position_action_id"])
        self.assertFalse(
            protection_trigger_validity_evidence_is_current(
                old_evidence,
                position,
                changed_action,
                self._market(),
                market_freshness_classification=FRESH,
            )
        )

    def test_no_stop_widening_cannot_be_bypassed_by_trigger_validity(self):
        position = self._position()
        plan = self._plan()
        action = self._action(position=position, plan=plan)
        forged = dict(action)
        forged["protection_instruction"] = dict(action["protection_instruction"])
        forged["protection_instruction"]["stop_level"] = "59000.00"

        with self.assertRaises(ProtectionActionError) as caught:
            validate_protection_action(forged, position, plan, now=self.action_time)
        self.assertEqual("PROTECTION_BOUND_MISMATCH", caught.exception.code)

        evidence = self._evidence(position=position, plan=plan, action=forged)
        self.assertEqual(FAIL_CLOSED, evidence["validity_status"])
        self.assertIn("POSITION_AUTHORITY_MISMATCH", evidence["reason_codes"])
        self.assertFalse(protection_trigger_validity_is_actionable(evidence))

    def test_fail_closed_validity_never_claims_successful_protection_or_lifecycle_transition(self):
        evidence = self._evidence(side="LONG", price="59000")
        self.assertEqual(FAIL_CLOSED, evidence["validity_status"])
        self.assertFalse(protection_trigger_validity_is_actionable(evidence))
        for forbidden in (
            "protection_verified",
            "lifecycle_event",
            "lifecycle_state",
            "order_request_id",
            "broker_order_id",
        ):
            self.assertNotIn(forbidden, evidence)

    def test_no_provider_mapping_or_mutation_surface_is_encoded(self):
        source = inspect.getsource(trigger_module)
        for forbidden_text in (
            "triggerPxType",
            "submit_order",
            "cancel_order",
            "amend_order",
            "credentials",
            "provider_order_id",
        ):
            self.assertNotIn(forbidden_text, source)
        evidence = self._evidence()
        for forbidden_field in (
            "triggerPxType",
            "provider_trigger_type",
            "provider_order_id",
            "credentials",
            "sz",
            "contract_count",
        ):
            self.assertNotIn(forbidden_field, evidence)


if __name__ == "__main__":
    unittest.main()
