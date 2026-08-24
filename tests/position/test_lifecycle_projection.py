import inspect
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import position.lifecycle_projection as lifecycle_projection_module
from position import (
    LifecycleProjectionError,
    PositionEvent,
    PositionLifecycleState,
    ProtectionResultEvidence,
    authorize_close_position_action,
    build_position_lifecycle_genesis,
    build_position_lifecycle_reattestation,
    build_position_lifecycle_transition,
    build_trade_result,
    interpret_protection_result,
    stable_lifecycle_projection_id,
    validate_position_lifecycle_projection,
)
from src.brokers.paper import PaperBroker
from src.execution.close import prepare_close_order
from src.execution.funding import produce_paper_zero_funding_evidence
from src.execution.gateway import ExecutionGateway


class PositionLifecycleProjectionV01Tests(unittest.TestCase):
    def setUp(self):
        self.observed_at = datetime(2026, 8, 24, 8, 0, 20, tzinfo=timezone.utc)
        self.interpreted_at = self.observed_at + timedelta(seconds=1)

    def _source(self, *, lifecycle="OPEN_UNPROTECTED", observed_at=None, **changes):
        observed = self.observed_at if observed_at is None else observed_at
        values = {
            "schema_version": "contracts-v0.1",
            "position_id": "position-projection-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": "0.0012",
            "average_entry_price": "60000",
            "opened_at": "2026-08-24T08:00:10Z",
            "broker_state_observed_at": observed.isoformat().replace("+00:00", "Z"),
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": lifecycle,
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }
        values.update(changes)
        return values

    def _plan(self):
        return {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-projection-001",
            "risk_decision_id": "risk-projection-001",
            "intent_id": "intent-projection-001",
            "strategy_id": "strategy-projection",
            "strategy_version": "1.0.0",
            "symbol": "BTC_USDT_PERP",
            "direction": "LONG",
            "quantity": "0.003",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
            "leverage": "20",
            "margin_mode": "ISOLATED",
            "entry_instruction": {"profile_version": "entry-v0.1", "order_type": "MARKET"},
            "protection_instruction": {
                "stop_level": "59400",
                "target_level": "61200",
                "max_hold_seconds": 1800,
            },
            "created_at": "2026-08-24T07:59:00Z",
            "expires_at": "2026-08-24T08:00:05Z",
            "risk_policy_version": "e5-projection-policy-v0.1",
        }

    def _protection_request(self):
        return {
            "schema_version": "contracts-v0.1",
            "order_request_id": "ordreq-projection-protect-001",
            "client_order_id": "client-projection-protect-001",
            "trade_plan_id": "plan-projection-001",
            "position_action_id": "posact-projection-protect-001",
            "position_id": "position-projection-001",
            "risk_decision_id": "risk-projection-001",
            "symbol": "BTC_USDT_PERP",
            "side": "SELL",
            "order_type": "STOP_MARKET",
            "quantity": "0.0012",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
            "authorization_type": "POSITION_ACTION",
            "order_role": "PROTECTION_STOP",
            "reduce_only": True,
            "stop_price": "59400",
            "limit_price": None,
            "time_in_force": None,
        }

    def _queried_protection(self, status):
        return {
            "schema_version": "contracts-v0.1",
            "order_request_id": "ordreq-projection-protect-001",
            "client_order_id": "client-projection-protect-001",
            "broker_order_id": "broker-projection-protect-001",
            "order_status": status,
            "execution_health_status": "HEALTHY",
            "requested_quantity": "0.0012",
            "filled_quantity": "0",
        }

    def _protection_outcome(self, current_state, status="OPEN", *, query_performed=True):
        return interpret_protection_result(
            self._protection_request(),
            ProtectionResultEvidence(
                query_performed=query_performed,
                queried_order=self._queried_protection(status) if query_performed else None,
            ),
            current_state,
        )

    def _assert_source_broker_facts_preserved(self, source, projection):
        e5_fields = {
            "lifecycle_state",
            "position_lifecycle_projection_profile_version",
            "lifecycle_projection_id",
            "lifecycle_revision",
            "previous_lifecycle_projection_id",
            "lifecycle_projection_kind",
            "lifecycle_event",
            "lifecycle_interpreted_at",
            "lifecycle_source_broker_state_observed_at",
        }
        for key, value in source.items():
            if key not in e5_fields:
                self.assertEqual(value, projection[key], key)

    def test_genesis_revision_zero_profile_identity_and_exact_replay(self):
        source = self._source()
        first = build_position_lifecycle_genesis(
            source,
            lifecycle_state=PositionLifecycleState.OPEN_UNPROTECTED,
            lifecycle_interpreted_at=self.interpreted_at,
        )
        replay = build_position_lifecycle_genesis(
            source,
            lifecycle_state="OPEN_UNPROTECTED",
            lifecycle_interpreted_at=self.interpreted_at,
        )

        self.assertEqual("contracts-v0.1", first["schema_version"])
        self.assertEqual(
            "position-lifecycle-projection-v0.1",
            first["position_lifecycle_projection_profile_version"],
        )
        self.assertEqual(0, first["lifecycle_revision"])
        self.assertIsNone(first["previous_lifecycle_projection_id"])
        self.assertEqual("GENESIS", first["lifecycle_projection_kind"])
        self.assertIsNone(first["lifecycle_event"])
        self.assertEqual(source["broker_state_observed_at"], first["lifecycle_source_broker_state_observed_at"])
        self.assertTrue(first["lifecycle_projection_id"].startswith("posproj_"))
        self.assertEqual(stable_lifecycle_projection_id(first), first["lifecycle_projection_id"])
        self.assertEqual(first, replay)
        self._assert_source_broker_facts_preserved(source, first)
        validate_position_lifecycle_projection(first)

    def test_protection_verified_transition_same_broker_observation_from_real_bridge(self):
        source = self._source(lifecycle="OPEN_UNPROTECTED")
        genesis = build_position_lifecycle_genesis(
            source,
            lifecycle_state="OPEN_UNPROTECTED",
            lifecycle_interpreted_at=self.interpreted_at,
        )
        outcome = self._protection_outcome(PositionLifecycleState.OPEN_UNPROTECTED, "OPEN")
        self.assertEqual(PositionEvent.PROTECTION_VERIFIED, outcome.event)
        self.assertEqual(PositionLifecycleState.OPEN_PROTECTED, outcome.next_state)

        protected = build_position_lifecycle_transition(
            source,
            genesis,
            lifecycle_event=outcome.event,
            lifecycle_interpreted_at=self.interpreted_at + timedelta(seconds=1),
        )
        self.assertEqual(1, protected["lifecycle_revision"])
        self.assertEqual(genesis["lifecycle_projection_id"], protected["previous_lifecycle_projection_id"])
        self.assertEqual("TRANSITION", protected["lifecycle_projection_kind"])
        self.assertEqual("PROTECTION_VERIFIED", protected["lifecycle_event"])
        self.assertEqual("OPEN_PROTECTED", protected["lifecycle_state"])
        self.assertEqual(source["broker_state_observed_at"], protected["broker_state_observed_at"])
        self._assert_source_broker_facts_preserved(source, protected)

    def test_protection_failed_and_lost_transitions_from_real_bridge(self):
        cases = (
            ("OPEN_UNPROTECTED", PositionEvent.PROTECTION_FAILED),
            ("OPEN_PROTECTED", PositionEvent.PROTECTION_LOST),
        )
        for lifecycle, expected_event in cases:
            with self.subTest(lifecycle=lifecycle):
                source = self._source(lifecycle=lifecycle)
                previous = build_position_lifecycle_genesis(
                    source,
                    lifecycle_state=lifecycle,
                    lifecycle_interpreted_at=self.interpreted_at,
                )
                outcome = self._protection_outcome(PositionLifecycleState(lifecycle), "REJECTED")
                self.assertEqual(expected_event, outcome.event)
                projected = build_position_lifecycle_transition(
                    source,
                    previous,
                    lifecycle_event=outcome.event,
                    lifecycle_interpreted_at=self.interpreted_at + timedelta(seconds=1),
                )
                self.assertEqual("EMERGENCY", projected["lifecycle_state"])

    def test_profit_protection_transition_compatibility(self):
        source = self._source(lifecycle="OPEN_PROTECTED")
        previous = build_position_lifecycle_genesis(
            source,
            lifecycle_state="OPEN_PROTECTED",
            lifecycle_interpreted_at=self.interpreted_at,
        )
        projected = build_position_lifecycle_transition(
            source,
            previous,
            lifecycle_event=PositionEvent.PROFIT_PROTECTION_VERIFIED,
            lifecycle_interpreted_at=self.interpreted_at + timedelta(seconds=1),
        )
        self.assertEqual("PROFIT_PROTECTED", projected["lifecycle_state"])
        self.assertEqual("PROFIT_PROTECTION_VERIFIED", projected["lifecycle_event"])

    def test_ordinary_and_emergency_exit_requested_use_real_close_outcomes(self):
        plan = self._plan()
        cases = (("OPEN_PROTECTED", "EXIT"), ("EMERGENCY", "EMERGENCY_EXIT"))
        for lifecycle, action in cases:
            with self.subTest(action=action):
                source = self._source(lifecycle=lifecycle)
                previous = build_position_lifecycle_genesis(
                    source,
                    lifecycle_state=lifecycle,
                    lifecycle_interpreted_at=self.interpreted_at,
                )
                close_outcome = authorize_close_position_action(
                    source,
                    plan,
                    action=action,
                    created_at=self.observed_at + timedelta(seconds=20),
                    expires_at=self.observed_at + timedelta(seconds=80),
                )
                self.assertEqual(PositionEvent.EXIT_REQUESTED, close_outcome.event)
                projected = build_position_lifecycle_transition(
                    source,
                    previous,
                    lifecycle_event=close_outcome.event,
                    lifecycle_interpreted_at=self.observed_at + timedelta(seconds=21),
                )
                self.assertEqual("EXIT_REQUESTED", projected["lifecycle_state"])

    def test_state_unknown_and_supported_reconciliation_transition(self):
        source = self._source(lifecycle="OPEN_UNPROTECTED")
        genesis = build_position_lifecycle_genesis(
            source,
            lifecycle_state="OPEN_UNPROTECTED",
            lifecycle_interpreted_at=self.interpreted_at,
        )
        unknown = self._protection_outcome(
            PositionLifecycleState.OPEN_UNPROTECTED,
            query_performed=False,
        )
        self.assertEqual(PositionEvent.STATE_UNKNOWN, unknown.event)
        recon = build_position_lifecycle_transition(
            source,
            genesis,
            lifecycle_event=unknown.event,
            lifecycle_interpreted_at=self.interpreted_at + timedelta(seconds=1),
        )
        self.assertEqual("RECONCILIATION_REQUIRED", recon["lifecycle_state"])

        reconciled = build_position_lifecycle_transition(
            source,
            recon,
            lifecycle_event=PositionEvent.RECONCILED_OPEN_UNPROTECTED,
            lifecycle_interpreted_at=self.interpreted_at + timedelta(seconds=2),
        )
        self.assertEqual("OPEN_UNPROTECTED", reconciled["lifecycle_state"])

    def test_position_closed_uses_real_trade_result_outcome_and_exact_flat_position(self):
        plan = self._plan()
        broker = PaperBroker()
        entry_request_at = datetime(2026, 8, 24, 8, 0, 0, tzinfo=timezone.utc)
        entry_fill_at = datetime(2026, 8, 24, 8, 0, 10, tzinfo=timezone.utc)
        close_action_at = datetime(2026, 8, 24, 8, 1, 0, tzinfo=timezone.utc)
        close_request_at = datetime(2026, 8, 24, 8, 1, 10, tzinfo=timezone.utc)
        close_fill_at = datetime(2026, 8, 24, 8, 1, 20, tzinfo=timezone.utc)
        flat_at = datetime(2026, 8, 24, 8, 1, 30, tzinfo=timezone.utc)

        entry_request = ExecutionGateway().prepare_entry_order(plan, now=entry_request_at)
        broker.submit_order(entry_request)
        entry_fill = broker.record_fill(
            entry_request.client_order_id,
            quantity=Decimal("0.0012"),
            price=Decimal("60000"),
            filled_at=entry_fill_at,
            fee=Decimal("0.01"),
            fee_currency="USDT",
            liquidity_role="TAKER",
        )

        source = self._source(lifecycle="OPEN_PROTECTED")
        genesis = build_position_lifecycle_genesis(
            source,
            lifecycle_state="OPEN_PROTECTED",
            lifecycle_interpreted_at=self.observed_at + timedelta(seconds=1),
        )
        close_outcome = authorize_close_position_action(
            source,
            plan,
            action="EXIT",
            created_at=close_action_at,
            expires_at=close_action_at + timedelta(seconds=60),
        )
        exiting = build_position_lifecycle_transition(
            source,
            genesis,
            lifecycle_event=close_outcome.event,
            lifecycle_interpreted_at=close_action_at,
        )
        exit_request = prepare_close_order(
            close_outcome.position_action,
            plan,
            source,
            now=close_request_at,
        )
        broker.submit_order(exit_request)
        exit_fill = broker.record_fill(
            exit_request.client_order_id,
            quantity=Decimal("0.0012"),
            price=Decimal("61000"),
            filled_at=close_fill_at,
            fee=Decimal("0.01"),
            fee_currency="USDT",
            liquidity_role="TAKER",
        )
        flat_position = broker.observe_position_after_close(
            exit_request,
            source,
            observed_at=flat_at,
        )
        funding = produce_paper_zero_funding_evidence(
            plan,
            flat_position,
            calculated_at=flat_at,
        )
        trade_outcome = build_trade_result(
            plan,
            current_lifecycle_state=close_outcome.next_state,
            exit_authority=close_outcome.position_action,
            entry_order_requests=(entry_request,),
            entry_fills=(entry_fill,),
            exit_order_request=exit_request,
            exit_fills=(exit_fill,),
            final_position=flat_position,
            funding_evidence=funding,
        )
        self.assertEqual(PositionEvent.POSITION_CLOSED, trade_outcome.event)
        self.assertEqual(PositionLifecycleState.CLOSED, trade_outcome.next_state)

        closed = build_position_lifecycle_transition(
            flat_position,
            exiting,
            lifecycle_event=trade_outcome.event,
            lifecycle_interpreted_at=flat_at + timedelta(seconds=1),
        )
        self.assertEqual("CLOSED", closed["lifecycle_state"])
        self.assertEqual("POSITION_CLOSED", closed["lifecycle_event"])
        self.assertEqual(flat_position["actual_quantity"], closed["actual_quantity"])
        self.assertEqual(flat_position["broker_state_observed_at"], closed["broker_state_observed_at"])
        self._assert_source_broker_facts_preserved(flat_position, closed)

    def test_reattestation_newer_broker_observation_preserves_lifecycle(self):
        source = self._source(lifecycle="EXIT_REQUESTED")
        previous = build_position_lifecycle_genesis(
            source,
            lifecycle_state="EXIT_REQUESTED",
            lifecycle_interpreted_at=self.interpreted_at,
        )
        newer_at = self.observed_at + timedelta(seconds=10)
        newer = self._source(
            lifecycle="OPEN_UNPROTECTED",
            observed_at=newer_at,
            actual_quantity="0.0008",
            unrealized_pnl="0.40",
        )
        reattested = build_position_lifecycle_reattestation(
            newer,
            previous,
            lifecycle_interpreted_at=newer_at + timedelta(seconds=1),
        )
        self.assertEqual(1, reattested["lifecycle_revision"])
        self.assertEqual("REATTESTATION", reattested["lifecycle_projection_kind"])
        self.assertIsNone(reattested["lifecycle_event"])
        self.assertEqual("EXIT_REQUESTED", reattested["lifecycle_state"])
        self.assertEqual("0.0008", reattested["actual_quantity"])
        self.assertEqual("0.40", reattested["unrealized_pnl"])
        self._assert_source_broker_facts_preserved(newer, reattested)

    def test_equal_broker_observation_allows_multiple_lifecycle_revisions(self):
        source = self._source(lifecycle="OPEN_UNPROTECTED")
        revision0 = build_position_lifecycle_genesis(
            source,
            lifecycle_state="OPEN_UNPROTECTED",
            lifecycle_interpreted_at=self.interpreted_at,
        )
        revision1 = build_position_lifecycle_transition(
            source,
            revision0,
            lifecycle_event=PositionEvent.PROTECTION_VERIFIED,
            lifecycle_interpreted_at=self.interpreted_at + timedelta(seconds=1),
        )
        revision2 = build_position_lifecycle_transition(
            source,
            revision1,
            lifecycle_event=PositionEvent.EXIT_REQUESTED,
            lifecycle_interpreted_at=self.interpreted_at + timedelta(seconds=2),
        )
        self.assertEqual([0, 1, 2], [revision0["lifecycle_revision"], revision1["lifecycle_revision"], revision2["lifecycle_revision"]])
        self.assertEqual(
            {source["broker_state_observed_at"]},
            {revision0["broker_state_observed_at"], revision1["broker_state_observed_at"], revision2["broker_state_observed_at"]},
        )
        self.assertEqual("EXIT_REQUESTED", revision2["lifecycle_state"])

    def test_broker_timestamp_regression_and_equal_time_fact_conflict_fail_closed(self):
        source = self._source(lifecycle="OPEN_PROTECTED")
        previous = build_position_lifecycle_genesis(
            source,
            lifecycle_state="OPEN_PROTECTED",
            lifecycle_interpreted_at=self.interpreted_at,
        )

        regressed = self._source(
            lifecycle="OPEN_PROTECTED",
            observed_at=self.observed_at - timedelta(seconds=1),
        )
        with self.assertRaises(LifecycleProjectionError) as caught:
            build_position_lifecycle_reattestation(
                regressed,
                previous,
                lifecycle_interpreted_at=self.interpreted_at + timedelta(seconds=2),
            )
        self.assertEqual("BROKER_OBSERVATION_REGRESSION", caught.exception.code)

        conflicting = self._source(lifecycle="OPEN_PROTECTED", actual_quantity="0.0011")
        with self.assertRaises(LifecycleProjectionError) as caught:
            build_position_lifecycle_reattestation(
                conflicting,
                previous,
                lifecycle_interpreted_at=self.interpreted_at + timedelta(seconds=2),
            )
        self.assertEqual("EQUAL_TIME_BROKER_FACT_CONFLICT", caught.exception.code)

    def test_invalid_previous_profile_id_revision_and_predecessor_fail_closed(self):
        source = self._source(lifecycle="OPEN_UNPROTECTED")
        genesis = build_position_lifecycle_genesis(
            source,
            lifecycle_state="OPEN_UNPROTECTED",
            lifecycle_interpreted_at=self.interpreted_at,
        )
        transition_projection = build_position_lifecycle_transition(
            source,
            genesis,
            lifecycle_event=PositionEvent.PROTECTION_VERIFIED,
            lifecycle_interpreted_at=self.interpreted_at + timedelta(seconds=1),
        )

        cases = []
        wrong_profile = dict(genesis)
        wrong_profile["position_lifecycle_projection_profile_version"] = "position-lifecycle-projection-v9"
        cases.append(wrong_profile)
        wrong_id = dict(genesis)
        wrong_id["lifecycle_projection_id"] = "posproj_" + "0" * 64
        cases.append(wrong_id)
        wrong_revision = dict(genesis)
        wrong_revision["lifecycle_revision"] = -1
        cases.append(wrong_revision)
        missing_predecessor = dict(transition_projection)
        missing_predecessor["previous_lifecycle_projection_id"] = None
        cases.append(missing_predecessor)

        for previous in cases:
            with self.subTest(previous=previous.get("lifecycle_projection_kind")):
                with self.assertRaises(LifecycleProjectionError):
                    build_position_lifecycle_reattestation(
                        source,
                        previous,
                        lifecycle_interpreted_at=self.interpreted_at + timedelta(seconds=3),
                    )

    def test_invalid_state_or_event_edge_fails_closed(self):
        source = self._source(lifecycle="OPEN_UNPROTECTED")
        previous = build_position_lifecycle_genesis(
            source,
            lifecycle_state="OPEN_UNPROTECTED",
            lifecycle_interpreted_at=self.interpreted_at,
        )
        with self.assertRaises(LifecycleProjectionError) as caught:
            build_position_lifecycle_transition(
                source,
                previous,
                lifecycle_event=PositionEvent.PROFIT_PROTECTION_VERIFIED,
                lifecycle_interpreted_at=self.interpreted_at + timedelta(seconds=1),
            )
        self.assertEqual("INVALID_LIFECYCLE_TRANSITION", caught.exception.code)

        with self.assertRaises(LifecycleProjectionError):
            build_position_lifecycle_transition(
                source,
                previous,
                lifecycle_event="NOT_A_REAL_EVENT",
                lifecycle_interpreted_at=self.interpreted_at + timedelta(seconds=1),
            )
        with self.assertRaises(LifecycleProjectionError):
            build_position_lifecycle_genesis(
                source,
                lifecycle_state="NOT_A_REAL_STATE",
                lifecycle_interpreted_at=self.interpreted_at,
            )

    def test_identity_changes_when_identity_bearing_projection_material_changes(self):
        source = self._source()
        baseline = build_position_lifecycle_genesis(
            source,
            lifecycle_state="OPEN_UNPROTECTED",
            lifecycle_interpreted_at=self.interpreted_at,
        )
        later_interpretation = build_position_lifecycle_genesis(
            source,
            lifecycle_state="OPEN_UNPROTECTED",
            lifecycle_interpreted_at=self.interpreted_at + timedelta(seconds=1),
        )
        different_lifecycle = build_position_lifecycle_genesis(
            source,
            lifecycle_state="OPEN_PROTECTED",
            lifecycle_interpreted_at=self.interpreted_at,
        )
        self.assertNotEqual(baseline["lifecycle_projection_id"], later_interpretation["lifecycle_projection_id"])
        self.assertNotEqual(baseline["lifecycle_projection_id"], different_lifecycle["lifecycle_projection_id"])

    def test_malformed_non_utc_and_interpreted_before_source_timestamps_fail_closed(self):
        malformed = self._source(broker_state_observed_at="2026-08-24 08:00:20")
        with self.assertRaises(LifecycleProjectionError):
            build_position_lifecycle_genesis(
                malformed,
                lifecycle_state="OPEN_UNPROTECTED",
                lifecycle_interpreted_at=self.interpreted_at,
            )

        with self.assertRaises(LifecycleProjectionError):
            build_position_lifecycle_genesis(
                self._source(),
                lifecycle_state="OPEN_UNPROTECTED",
                lifecycle_interpreted_at=datetime(2026, 8, 24, 8, 0, 21),
            )

        with self.assertRaises(LifecycleProjectionError) as caught:
            build_position_lifecycle_genesis(
                self._source(),
                lifecycle_state="OPEN_UNPROTECTED",
                lifecycle_interpreted_at=self.observed_at - timedelta(seconds=1),
            )
        self.assertEqual("INTERPRETATION_PREDATES_BROKER_OBSERVATION", caught.exception.code)

    def test_profiled_source_unknown_fields_and_storage_or_provider_authority_fail_closed(self):
        source = self._source()
        genesis = build_position_lifecycle_genesis(
            source,
            lifecycle_state="OPEN_UNPROTECTED",
            lifecycle_interpreted_at=self.interpreted_at,
        )
        with self.assertRaises(LifecycleProjectionError):
            build_position_lifecycle_genesis(
                genesis,
                lifecycle_state="OPEN_UNPROTECTED",
                lifecycle_interpreted_at=self.interpreted_at + timedelta(seconds=1),
            )
        with self.assertRaises(LifecycleProjectionError):
            build_position_lifecycle_genesis(
                self._source(api_key="fake-but-forbidden-shape"),
                lifecycle_state="OPEN_UNPROTECTED",
                lifecycle_interpreted_at=self.interpreted_at,
            )

        module_source = inspect.getsource(lifecycle_projection_module)
        self.assertNotIn("src.storage", module_source)
        self.assertNotIn("src.platform", module_source)
        self.assertNotIn("requests.", module_source)
        self.assertNotIn("api_key", module_source)

        forbidden_output_fields = {
            "persisted_at",
            "database_row_id",
            "storage_revision",
            "provider_order_id",
            "api_key",
            "secret_key",
            "credentials",
            "paper_authorized",
            "shadow_authorized",
            "live_authorized",
        }
        self.assertTrue(forbidden_output_fields.isdisjoint(genesis.keys()))

        genesis_signature = inspect.signature(build_position_lifecycle_genesis)
        transition_signature = inspect.signature(build_position_lifecycle_transition)
        self.assertNotIn("lifecycle_revision", genesis_signature.parameters)
        self.assertNotIn("lifecycle_projection_id", genesis_signature.parameters)
        self.assertNotIn("lifecycle_revision", transition_signature.parameters)
        self.assertNotIn("lifecycle_projection_id", transition_signature.parameters)


if __name__ == "__main__":
    unittest.main()
