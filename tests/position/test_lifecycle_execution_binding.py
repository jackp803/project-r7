import inspect
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import position.lifecycle_execution_binding as binding_module
from position import (
    LifecycleExecutionBindingError,
    PositionEvent,
    build_position_lifecycle_execution_evidence_binding,
    build_position_lifecycle_genesis,
    build_position_lifecycle_genesis_with_execution_binding,
    build_position_lifecycle_reattestation_with_execution_binding,
    build_position_lifecycle_transition_with_execution_binding,
    stable_lifecycle_projection_id,
    validate_position_lifecycle_execution_evidence_binding,
)
from src.execution.models import ExecutionHealthStatus, Fill, OrderRequest, OrderResult, OrderStatus, Side


class PositionLifecycleExecutionBindingV01Tests(unittest.TestCase):
    def setUp(self):
        self.observed_at = datetime(2026, 8, 24, 14, 0, 20, tzinfo=timezone.utc)
        self.interpreted_at = self.observed_at + timedelta(seconds=1)

    def _source(self, *, lifecycle="OPEN_PROTECTED"):
        return {
            "schema_version": "contracts-v0.1",
            "position_id": "position-binding-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": "0.0012",
            "average_entry_price": "60000",
            "opened_at": "2026-08-24T14:00:10Z",
            "broker_state_observed_at": "2026-08-24T14:00:20Z",
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": lifecycle,
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }

    def _projection(self, *, lifecycle="OPEN_PROTECTED"):
        return build_position_lifecycle_genesis(
            self._source(lifecycle=lifecycle),
            lifecycle_state=lifecycle,
            lifecycle_interpreted_at=self.interpreted_at,
        )

    def _request(
        self,
        *,
        request_id="ordreq-protection-001",
        client_id="client-protection-001",
        role="PROTECTION_STOP",
        action_id="posact-protection-001",
        created_at=None,
    ):
        created_at = created_at or self.observed_at
        return OrderRequest(
            schema_version="contracts-v0.1",
            order_request_id=request_id,
            trade_plan_id="plan-binding-001",
            client_order_id=client_id,
            symbol="BTC_USDT_PERP",
            side=Side.SELL,
            order_type="STOP_MARKET" if role == "PROTECTION_STOP" else "MARKET",
            quantity=Decimal("0.0012"),
            quantity_profile_version="base-asset-v0.1",
            quantity_unit="BASE_ASSET",
            quantity_asset="BTC",
            created_at=created_at,
            authorization_type="POSITION_ACTION",
            position_action_id=action_id,
            position_id="position-binding-001",
            risk_decision_id="risk-binding-001",
            order_role=role,
            limit_price=None,
            stop_price=Decimal("59400") if role == "PROTECTION_STOP" else None,
            reduce_only=True,
            time_in_force=None,
        )

    def _entry_request(self):
        return OrderRequest(
            schema_version="contracts-v0.1",
            order_request_id="ordreq-entry-001",
            trade_plan_id="plan-binding-001",
            client_order_id="client-entry-001",
            symbol="BTC_USDT_PERP",
            side=Side.BUY,
            order_type="MARKET",
            quantity=Decimal("0.0012"),
            quantity_profile_version="base-asset-v0.1",
            quantity_unit="BASE_ASSET",
            quantity_asset="BTC",
            created_at=self.observed_at - timedelta(seconds=10),
        )

    def _result(
        self,
        request,
        *,
        status=OrderStatus.OPEN,
        observed_at=None,
        filled="0",
    ):
        observed_at = observed_at or (self.observed_at + timedelta(seconds=1))
        average = None if Decimal(filled) == 0 else Decimal("59400")
        return OrderResult(
            schema_version="contracts-v0.1",
            order_request_id=request.order_request_id,
            client_order_id=request.client_order_id,
            broker_order_id="broker-" + request.order_request_id,
            order_status=status,
            observed_at=observed_at,
            execution_health_status=ExecutionHealthStatus.HEALTHY,
            requested_quantity=request.quantity,
            filled_quantity=Decimal(filled),
            average_fill_price=average,
        )

    def _entry_result(self, request):
        return OrderResult(
            schema_version="contracts-v0.1",
            order_request_id=request.order_request_id,
            client_order_id=request.client_order_id,
            broker_order_id="broker-entry-001",
            order_status=OrderStatus.FILLED,
            observed_at=self.observed_at - timedelta(seconds=5),
            execution_health_status=ExecutionHealthStatus.HEALTHY,
            requested_quantity=request.quantity,
            filled_quantity=request.quantity,
            average_fill_price=Decimal("60000"),
        )

    def _fill(self, request, *, fill_id="fill-protection-001", filled_at=None, quantity="0.0004", price="59400"):
        filled_at = filled_at or (self.observed_at + timedelta(seconds=2))
        return Fill(
            schema_version="contracts-v0.1",
            fill_id=fill_id,
            broker_order_id="broker-" + request.order_request_id,
            client_order_id=request.client_order_id,
            trade_plan_id=request.trade_plan_id,
            symbol=request.symbol,
            side=request.side,
            quantity=Decimal(quantity),
            price=Decimal(price),
            filled_at=filled_at,
            fee=Decimal("0.01"),
            fee_currency="USDT",
            liquidity_role="TAKER",
            position_action_id=request.position_action_id,
            position_id=request.position_id,
            order_role=request.order_role,
        )

    def _entry_fill(self, request):
        return Fill(
            schema_version="contracts-v0.1",
            fill_id="fill-entry-001",
            broker_order_id="broker-entry-001",
            client_order_id=request.client_order_id,
            trade_plan_id=request.trade_plan_id,
            symbol=request.symbol,
            side=request.side,
            quantity=Decimal("0.0012"),
            price=Decimal("60000"),
            filled_at=self.observed_at - timedelta(seconds=6),
            fee=Decimal("0.01"),
            fee_currency="USDT",
            liquidity_role="TAKER",
        )

    def test_empty_in_scope_snapshot_is_deterministic_for_valid_projection(self):
        projection = self._projection()
        first = build_position_lifecycle_execution_evidence_binding(
            projection,
            order_requests=(),
            order_results=(),
            fills=(),
        )
        replay = build_position_lifecycle_execution_evidence_binding(
            projection,
            order_requests=(),
            order_results=(),
            fills=(),
        )
        self.assertEqual(first, replay)
        self.assertEqual("position-lifecycle-execution-binding-v0.1", first["lifecycle_execution_binding_profile_version"])
        self.assertEqual("POSITION_LINKED_REDUCTION_ORDERS_V0_1", first["execution_scope"])
        self.assertEqual(projection["lifecycle_projection_id"], first["lifecycle_projection_id"])
        self.assertEqual(projection["lifecycle_revision"], first["lifecycle_revision"])
        self.assertEqual(projection["lifecycle_interpreted_at"], first["execution_interpreted_at"])
        self.assertEqual([], first["order_evidence"])
        self.assertTrue(first["execution_snapshot_hash"].startswith("sha256:"))
        self.assertTrue(first["lifecycle_execution_binding_id"].startswith("posexecbind_"))
        validate_position_lifecycle_execution_evidence_binding(first, projection)

    def test_open_protected_protection_stop_open_observation_binds_exactly(self):
        projection = self._projection()
        request = self._request()
        opened = self._result(request)
        first = build_position_lifecycle_execution_evidence_binding(
            projection,
            order_requests=(request,),
            order_results=(opened,),
            fills=(),
        )
        replay = build_position_lifecycle_execution_evidence_binding(
            projection,
            order_requests=(request,),
            order_results=(opened,),
            fills=(),
        )
        self.assertEqual(first, replay)
        self.assertEqual(1, len(first["order_evidence"]))
        evidence = first["order_evidence"][0]
        self.assertEqual(request.order_request_id, evidence["order_request_id"])
        self.assertEqual("PROTECTION_STOP", evidence["order_role"])
        self.assertEqual(1, evidence["order_result_observation_count"])
        self.assertEqual("2026-08-24T14:00:21Z", evidence["latest_order_result_observed_at"])
        self.assertEqual(0, evidence["fill_count"])
        self.assertIsNone(evidence["latest_fill_at"])

    def test_partial_or_full_new_protection_execution_changes_binding_after_transition(self):
        for status, filled in ((OrderStatus.PARTIALLY_FILLED, "0.0004"), (OrderStatus.FILLED, "0.0012")):
            with self.subTest(status=status):
                source = self._source(lifecycle="OPEN_PROTECTED")
                projection = self._projection(lifecycle="OPEN_PROTECTED")
                request = self._request()
                opened = self._result(request)
                old_binding = build_position_lifecycle_execution_evidence_binding(
                    projection,
                    order_requests=(request,),
                    order_results=(opened,),
                    fills=(),
                )
                later = self._result(
                    request,
                    status=status,
                    observed_at=self.observed_at + timedelta(seconds=3),
                    filled=filled,
                )
                fill = self._fill(request, quantity=filled)
                composed = build_position_lifecycle_transition_with_execution_binding(
                    source,
                    projection,
                    lifecycle_event=PositionEvent.STATE_UNKNOWN,
                    lifecycle_interpreted_at=self.interpreted_at + timedelta(seconds=5),
                    order_requests=(request,),
                    order_results=(opened, later),
                    fills=(fill,),
                )
                self.assertEqual("RECONCILIATION_REQUIRED", composed.lifecycle_projection["lifecycle_state"])
                self.assertNotEqual(old_binding["execution_snapshot_hash"], composed.execution_binding["execution_snapshot_hash"])
                self.assertNotEqual(old_binding["lifecycle_execution_binding_id"], composed.execution_binding["lifecycle_execution_binding_id"])

    def test_inactive_protection_truth_changes_snapshot_and_binding(self):
        for status in (OrderStatus.CANCELED, OrderStatus.EXPIRED, OrderStatus.REJECTED):
            with self.subTest(status=status):
                source = self._source(lifecycle="OPEN_PROTECTED")
                projection = self._projection(lifecycle="OPEN_PROTECTED")
                request = self._request()
                opened = self._result(request)
                old_binding = build_position_lifecycle_execution_evidence_binding(
                    projection,
                    order_requests=(request,),
                    order_results=(opened,),
                    fills=(),
                )
                terminal = self._result(request, status=status, observed_at=self.observed_at + timedelta(seconds=3))
                composed = build_position_lifecycle_transition_with_execution_binding(
                    source,
                    projection,
                    lifecycle_event=PositionEvent.PROTECTION_LOST,
                    lifecycle_interpreted_at=self.interpreted_at + timedelta(seconds=4),
                    order_requests=(request,),
                    order_results=(opened, terminal),
                    fills=(),
                )
                self.assertEqual("EMERGENCY", composed.lifecycle_projection["lifecycle_state"])
                self.assertNotEqual(old_binding["execution_snapshot_hash"], composed.execution_binding["execution_snapshot_hash"])

    def test_position_exit_and_emergency_exit_share_the_same_scope(self):
        for role in ("POSITION_EXIT", "EMERGENCY_EXIT"):
            with self.subTest(role=role):
                projection = self._projection(lifecycle="EXIT_REQUESTED")
                request = self._request(
                    request_id="ordreq-" + role.lower(),
                    client_id="client-" + role.lower(),
                    role=role,
                    action_id="posact-" + role.lower(),
                )
                opened = self._result(request)
                binding = build_position_lifecycle_execution_evidence_binding(
                    projection,
                    order_requests=(request,),
                    order_results=(opened,),
                    fills=(),
                )
                self.assertEqual(role, binding["order_evidence"][0]["order_role"])

    def test_equal_broker_anchor_reattestation_binds_newer_execution_without_lifecycle_change(self):
        source = self._source(lifecycle="OPEN_PROTECTED")
        projection = self._projection(lifecycle="OPEN_PROTECTED")
        request = self._request()
        opened = self._result(request)
        old_binding = build_position_lifecycle_execution_evidence_binding(
            projection,
            order_requests=(request,),
            order_results=(opened,),
            fills=(),
        )
        later_open = self._result(request, observed_at=self.observed_at + timedelta(seconds=4))
        composed = build_position_lifecycle_reattestation_with_execution_binding(
            source,
            projection,
            lifecycle_interpreted_at=self.interpreted_at + timedelta(seconds=5),
            order_requests=(request,),
            order_results=(later_open, opened),
            fills=(),
        )
        self.assertEqual(projection["lifecycle_revision"] + 1, composed.lifecycle_projection["lifecycle_revision"])
        self.assertEqual("REATTESTATION", composed.lifecycle_projection["lifecycle_projection_kind"])
        self.assertEqual("OPEN_PROTECTED", composed.lifecycle_projection["lifecycle_state"])
        self.assertEqual(projection["broker_state_observed_at"], composed.lifecycle_projection["broker_state_observed_at"])
        self.assertNotEqual(old_binding["execution_snapshot_hash"], composed.execution_binding["execution_snapshot_hash"])
        self.assertEqual(
            composed.lifecycle_projection["lifecycle_interpreted_at"],
            composed.execution_binding["execution_interpreted_at"],
        )

    def test_order_evidence_ordering_is_independent_of_caller_order(self):
        projection = self._projection(lifecycle="EXIT_REQUESTED")
        protection = self._request(request_id="ordreq-b", client_id="client-b")
        exit_request = self._request(
            request_id="ordreq-a",
            client_id="client-a",
            role="POSITION_EXIT",
            action_id="posact-exit-a",
        )
        protection_result = self._result(protection, observed_at=self.observed_at + timedelta(seconds=2))
        exit_result = self._result(exit_request, observed_at=self.observed_at + timedelta(seconds=3))
        first = build_position_lifecycle_execution_evidence_binding(
            projection,
            order_requests=(protection, exit_request),
            order_results=(protection_result, exit_result),
            fills=(),
        )
        second = build_position_lifecycle_execution_evidence_binding(
            projection,
            order_requests=(exit_request, protection),
            order_results=(exit_result, protection_result),
            fills=(),
        )
        self.assertEqual(first, second)
        self.assertEqual(["ordreq-a", "ordreq-b"], [item["order_request_id"] for item in first["order_evidence"]])

    def test_order_result_set_is_deterministic_and_exact_duplicate_is_idempotent(self):
        projection = self._projection()
        request = self._request()
        first_result = self._result(request, observed_at=self.observed_at + timedelta(seconds=1))
        second_result = self._result(request, observed_at=self.observed_at + timedelta(seconds=3))
        first = build_position_lifecycle_execution_evidence_binding(
            projection,
            order_requests=(request,),
            order_results=(second_result, first_result, first_result),
            fills=(),
        )
        second = build_position_lifecycle_execution_evidence_binding(
            projection,
            order_requests=(request,),
            order_results=(first_result, second_result),
            fills=(),
        )
        self.assertEqual(first, second)
        self.assertEqual(2, first["order_evidence"][0]["order_result_observation_count"])

    def test_fill_set_is_deterministic_and_exact_duplicate_is_idempotent(self):
        projection = self._projection()
        request = self._request()
        first_fill = self._fill(request, fill_id="fill-b", filled_at=self.observed_at + timedelta(seconds=4))
        second_fill = self._fill(request, fill_id="fill-a", filled_at=self.observed_at + timedelta(seconds=3))
        first = build_position_lifecycle_execution_evidence_binding(
            projection,
            order_requests=(request,),
            order_results=(),
            fills=(first_fill, second_fill, second_fill),
        )
        second = build_position_lifecycle_execution_evidence_binding(
            projection,
            order_requests=(request,),
            order_results=(),
            fills=(second_fill, first_fill),
        )
        self.assertEqual(first, second)
        self.assertEqual(2, first["order_evidence"][0]["fill_count"])
        self.assertEqual("2026-08-24T14:00:24Z", first["order_evidence"][0]["latest_fill_at"])

    def test_conflicting_equal_time_order_result_fails_closed(self):
        projection = self._projection()
        request = self._request()
        observed_at = self.observed_at + timedelta(seconds=2)
        opened = self._result(request, status=OrderStatus.OPEN, observed_at=observed_at)
        canceled = self._result(request, status=OrderStatus.CANCELED, observed_at=observed_at)
        with self.assertRaises(LifecycleExecutionBindingError) as caught:
            build_position_lifecycle_execution_evidence_binding(
                projection,
                order_requests=(request,),
                order_results=(opened, canceled),
                fills=(),
            )
        self.assertEqual("ORDER_RESULT_EQUAL_TIME_CONFLICT", caught.exception.code)

    def test_conflicting_fill_identity_fails_closed(self):
        projection = self._projection()
        request = self._request()
        first = self._fill(request, fill_id="fill-conflict", quantity="0.0004")
        changed = replace(first, quantity=Decimal("0.0005"))
        with self.assertRaises(LifecycleExecutionBindingError) as caught:
            build_position_lifecycle_execution_evidence_binding(
                projection,
                order_requests=(request,),
                order_results=(),
                fills=(first, changed),
            )
        self.assertEqual("FILL_IDENTITY_CONFLICT", caught.exception.code)

    def test_request_result_and_fill_lineage_mismatches_fail_closed(self):
        projection = self._projection()
        request = self._request()
        wrong_result = replace(self._result(request), client_order_id="wrong-client")
        with self.assertRaises(LifecycleExecutionBindingError) as result_error:
            build_position_lifecycle_execution_evidence_binding(
                projection,
                order_requests=(request,),
                order_results=(wrong_result,),
                fills=(),
            )
        self.assertEqual("ORDER_RESULT_CLIENT_ID_MISMATCH", result_error.exception.code)

        wrong_fill = replace(self._fill(request), position_action_id="wrong-action")
        with self.assertRaises(LifecycleExecutionBindingError) as fill_error:
            build_position_lifecycle_execution_evidence_binding(
                projection,
                order_requests=(request,),
                order_results=(),
                fills=(wrong_fill,),
            )
        self.assertEqual("FILL_LINEAGE_MISMATCH", fill_error.exception.code)

        wrong_position_request = replace(request, position_id="other-position")
        with self.assertRaises(LifecycleExecutionBindingError) as request_error:
            build_position_lifecycle_execution_evidence_binding(
                projection,
                order_requests=(wrong_position_request,),
                order_results=(),
                fills=(),
            )
        self.assertEqual("ORDER_REQUEST_POSITION_MISMATCH", request_error.exception.code)

    def test_entry_v01_evidence_is_not_joined_by_trade_plan_heuristic(self):
        projection = self._projection()
        entry_request = self._entry_request()
        entry_result = self._entry_result(entry_request)
        entry_fill = self._entry_fill(entry_request)
        with_entry = build_position_lifecycle_execution_evidence_binding(
            projection,
            order_requests=(entry_request,),
            order_results=(entry_result,),
            fills=(entry_fill,),
        )
        empty = build_position_lifecycle_execution_evidence_binding(
            projection,
            order_requests=(),
            order_results=(),
            fills=(),
        )
        self.assertEqual(empty, with_entry)
        self.assertEqual([], with_entry["order_evidence"])

    def test_binding_projection_profile_scope_and_reference_mismatches_fail_closed(self):
        projection = self._projection()
        binding = build_position_lifecycle_execution_evidence_binding(
            projection,
            order_requests=(),
            order_results=(),
            fills=(),
        )
        mutations = (
            ("schema_version", "contracts-v9", "UNSUPPORTED_SCHEMA_VERSION"),
            ("lifecycle_execution_binding_profile_version", "position-lifecycle-execution-binding-v9", "UNSUPPORTED_BINDING_PROFILE"),
            ("execution_scope", "OTHER_SCOPE", "UNSUPPORTED_EXECUTION_SCOPE"),
            ("position_id", "other-position", "BINDING_POSITION_MISMATCH"),
            ("lifecycle_projection_id", "posproj_" + "0" * 64, "BINDING_PROJECTION_ID_MISMATCH"),
            ("lifecycle_revision", 99, "BINDING_REVISION_MISMATCH"),
            ("execution_interpreted_at", "2026-08-24T14:00:22Z", "BINDING_INTERPRETATION_TIME_MISMATCH"),
        )
        for field, value, code in mutations:
            with self.subTest(field=field):
                changed = dict(binding)
                changed[field] = value
                with self.assertRaises(LifecycleExecutionBindingError) as caught:
                    validate_position_lifecycle_execution_evidence_binding(changed, projection)
                self.assertEqual(code, caught.exception.code)

    def test_duplicate_request_identity_change_and_binary_float_fail_closed(self):
        projection = self._projection()
        request = self._request()
        changed = replace(request, quantity=Decimal("0.0011"))
        with self.assertRaises(LifecycleExecutionBindingError) as conflict:
            build_position_lifecycle_execution_evidence_binding(
                projection,
                order_requests=(request, changed),
                order_results=(),
                fills=(),
            )
        self.assertEqual("ORDER_REQUEST_IDENTITY_CONFLICT", conflict.exception.code)

        bad_mapping = {
            key: value
            for key, value in request.__dict__.items()
        }
        bad_mapping["quantity"] = 0.0012
        with self.assertRaises(LifecycleExecutionBindingError) as binary_float:
            build_position_lifecycle_execution_evidence_binding(
                projection,
                order_requests=(bad_mapping,),
                order_results=(),
                fills=(),
            )
        self.assertEqual("BINARY_FLOAT_FORBIDDEN", binary_float.exception.code)

    def test_binding_does_not_mutate_projection_identity_or_import_storage_provider_network(self):
        source = self._source(lifecycle="OPEN_PROTECTED")
        composed = build_position_lifecycle_genesis_with_execution_binding(
            source,
            lifecycle_state="OPEN_PROTECTED",
            lifecycle_interpreted_at=self.interpreted_at,
            order_requests=(),
            order_results=(),
            fills=(),
        )
        projection = composed.lifecycle_projection
        self.assertEqual(stable_lifecycle_projection_id(projection), projection["lifecycle_projection_id"])
        self.assertNotIn("execution_snapshot_hash", projection)
        self.assertNotIn("lifecycle_execution_binding_id", projection)

        source_text = inspect.getsource(binding_module).lower()
        for forbidden in (
            "src.storage",
            "sqlite",
            "requests.",
            "http://",
            "https://",
            "api_key",
            "secret_key",
            "password",
            "live_authorized",
        ):
            self.assertNotIn(forbidden, source_text)


if __name__ == "__main__":
    unittest.main()
