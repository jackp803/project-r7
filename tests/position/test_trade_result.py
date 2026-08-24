import hashlib
import inspect
import json
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import position.trade_result as trade_result_module
from position import (
    FundingEvidence,
    PositionEvent,
    PositionLifecycleState,
    TradeResultBuildError,
    build_close_position_action,
    build_protect_position_action,
    build_trade_result,
    transition,
)
from src.execution.close import prepare_close_order
from src.execution.gateway import ExecutionGateway
from src.execution.models import Fill, Side
from src.execution.protection import prepare_protection_order


FUNDING_IDENTITY_FIELDS = (
    "schema_version",
    "funding_evidence_profile_version",
    "source_kind",
    "source",
    "source_version",
    "source_material_hash",
    "source_record_count",
    "source_complete_through",
    "trade_plan_id",
    "position_id",
    "symbol",
    "interval_start",
    "interval_end",
    "interval_semantics",
    "status",
    "funding_cost",
    "cost_currency",
)


def stable_funding_id(evidence):
    material = {field: evidence[field] for field in FUNDING_IDENTITY_FIELDS}
    payload = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return "fundev_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TradeResultFundingConsumerTests(unittest.TestCase):
    def setUp(self):
        self.entry_request_at = datetime(2026, 8, 24, 5, 5, 0, tzinfo=timezone.utc)
        self.entry_fill_1_at = datetime(2026, 8, 24, 5, 5, 10, tzinfo=timezone.utc)
        self.entry_fill_2_at = datetime(2026, 8, 24, 5, 5, 20, tzinfo=timezone.utc)
        self.close_observed_at = datetime(2026, 8, 24, 5, 20, 0, tzinfo=timezone.utc)
        self.close_action_at = datetime(2026, 8, 24, 5, 20, 10, tzinfo=timezone.utc)
        self.close_request_at = datetime(2026, 8, 24, 5, 20, 20, tzinfo=timezone.utc)
        self.exit_fill_at = datetime(2026, 8, 24, 5, 20, 30, tzinfo=timezone.utc)
        self.flat_observed_at = datetime(2026, 8, 24, 5, 20, 40, tzinfo=timezone.utc)
        self.calculated_at = datetime(2026, 8, 24, 5, 20, 50, tzinfo=timezone.utc)

    def _plan(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-result-001",
            "risk_decision_id": "risk-result-001",
            "intent_id": "intent-result-001",
            "strategy_id": "strategy-result",
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
            "created_at": "2026-08-24T05:00:00Z",
            "expires_at": "2026-08-24T05:10:00Z",
            "risk_policy_version": "e5-result-policy-v0.1",
        }
        values.update(changes)
        return values

    def _source_position(self, *, plan=None, **changes):
        parent = self._plan() if plan is None else plan
        values = {
            "schema_version": "contracts-v0.1",
            "position_id": "position-result-001",
            "symbol": parent["symbol"],
            "side": parent["direction"],
            "actual_quantity": "0.002",
            "average_entry_price": "60050",
            "opened_at": "2026-08-24T05:05:10Z",
            "broker_state_observed_at": "2026-08-24T05:20:00Z",
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": "OPEN_PROTECTED",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }
        values.update(changes)
        return values

    def _entry_request(self, plan=None):
        parent = self._plan() if plan is None else plan
        return ExecutionGateway().prepare_entry_order(parent, now=self.entry_request_at)

    def _entry_fills(self, request, *, fee_currency="USDT", missing_fee=False):
        fee1 = None if missing_fee else Decimal("0.01")
        return (
            Fill(
                schema_version="contracts-v0.1",
                fill_id="fill-entry-001",
                broker_order_id="broker-entry-001",
                client_order_id=request.client_order_id,
                trade_plan_id=request.trade_plan_id,
                symbol=request.symbol,
                side=request.side,
                quantity=Decimal("0.001"),
                price=Decimal("60000"),
                filled_at=self.entry_fill_1_at,
                fee=fee1,
                fee_currency=fee_currency,
            ),
            Fill(
                schema_version="contracts-v0.1",
                fill_id="fill-entry-002",
                broker_order_id="broker-entry-001",
                client_order_id=request.client_order_id,
                trade_plan_id=request.trade_plan_id,
                symbol=request.symbol,
                side=request.side,
                quantity=Decimal("0.001"),
                price=Decimal("60100"),
                filled_at=self.entry_fill_2_at,
                fee=Decimal("0.01"),
                fee_currency=fee_currency,
            ),
        )

    def _close_action_and_request(self, *, plan=None, emergency=False, reason_codes=None):
        parent = self._plan() if plan is None else plan
        source = self._source_position(
            plan=parent,
            lifecycle_state="EMERGENCY" if emergency else "OPEN_PROTECTED",
        )
        action = build_close_position_action(
            source,
            parent,
            action="EMERGENCY_EXIT" if emergency else "EXIT",
            created_at=self.close_action_at,
            expires_at=self.close_action_at + timedelta(seconds=60),
            reason_codes=reason_codes,
        )
        request = prepare_close_order(action, parent, source, now=self.close_request_at)
        return action, request

    def _protection_action_and_request(self, *, plan=None):
        parent = self._plan() if plan is None else plan
        source = self._source_position(
            plan=parent,
            lifecycle_state="OPEN_UNPROTECTED",
            broker_state_observed_at="2026-08-24T05:06:00Z",
        )
        action = build_protect_position_action(
            source,
            parent,
            created_at=datetime(2026, 8, 24, 5, 6, 10, tzinfo=timezone.utc),
            expires_at=datetime(2026, 8, 24, 5, 30, 0, tzinfo=timezone.utc),
        )
        request = prepare_protection_order(
            action,
            parent,
            source,
            now=datetime(2026, 8, 24, 5, 6, 20, tzinfo=timezone.utc),
        )
        return action, request

    def _exit_fill(
        self,
        request,
        *,
        fill_id="fill-exit-001",
        quantity="0.002",
        price="61000",
        fee="0.02",
        fee_currency="USDT",
        **changes,
    ):
        values = {
            "schema_version": "contracts-v0.1",
            "fill_id": fill_id,
            "broker_order_id": "broker-exit-001",
            "client_order_id": request.client_order_id,
            "trade_plan_id": request.trade_plan_id,
            "symbol": request.symbol,
            "side": request.side,
            "quantity": Decimal(quantity),
            "price": Decimal(price),
            "filled_at": self.exit_fill_at,
            "fee": None if fee is None else Decimal(fee),
            "fee_currency": fee_currency,
            "position_action_id": request.position_action_id,
            "position_id": request.position_id,
            "order_role": request.order_role,
        }
        values.update(changes)
        return Fill(**values)

    def _final_position(self, *, plan=None, **changes):
        parent = self._plan() if plan is None else plan
        values = {
            "schema_version": "contracts-v0.1",
            "position_id": "position-result-001",
            "symbol": parent["symbol"],
            "side": parent["direction"],
            "actual_quantity": "0",
            "average_entry_price": "60050",
            "opened_at": "2026-08-24T05:05:10Z",
            "broker_state_observed_at": "2026-08-24T05:20:40Z",
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": "OPEN_PROTECTED",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }
        values.update(changes)
        return values

    def _funding(
        self,
        *,
        plan=None,
        position_id="position-result-001",
        symbol=None,
        status="ZERO_CONFIRMED",
        funding_cost="0",
        source_record_count=None,
        source_kind="PAPER_MODEL",
        source="R7_PAPER_FUNDING_MODEL",
        source_version="paper-zero-funding-v0.1",
        source_material_hash=None,
        source_complete_through=None,
        interval_start=None,
        interval_end=None,
        interval_semantics="START_INCLUSIVE_END_EXCLUSIVE",
        cost_currency="USDT",
        calculated_at=None,
        **changes,
    ):
        parent = self._plan() if plan is None else plan
        interval_start = "2026-08-24T05:05:10Z" if interval_start is None else interval_start
        interval_end = "2026-08-24T05:20:40Z" if interval_end is None else interval_end
        if source_record_count is None:
            source_record_count = 0 if status == "ZERO_CONFIRMED" else 1
        if source_material_hash is None:
            seed = f"{source_kind}|{source}|{source_version}|{parent['trade_plan_id']}|{position_id}|{interval_start}|{interval_end}|{status}|{funding_cost}"
            source_material_hash = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        if source_complete_through is None:
            source_complete_through = interval_end
        if calculated_at is None:
            calculated_at = "2026-08-24T05:20:50Z"
        evidence = {
            "schema_version": "contracts-v0.1",
            "funding_evidence_profile_version": "funding-allocation-v0.1",
            "source_kind": source_kind,
            "source": source,
            "source_version": source_version,
            "source_material_hash": source_material_hash,
            "source_record_count": source_record_count,
            "source_complete_through": source_complete_through,
            "trade_plan_id": parent["trade_plan_id"],
            "position_id": position_id,
            "symbol": parent["symbol"] if symbol is None else symbol,
            "interval_start": interval_start,
            "interval_end": interval_end,
            "interval_semantics": interval_semantics,
            "status": status,
            "funding_cost": funding_cost,
            "cost_currency": cost_currency,
            "calculated_at": calculated_at,
        }
        evidence.update(changes)
        evidence["funding_evidence_id"] = stable_funding_id(evidence)
        return evidence

    def _ordinary_evidence(
        self,
        *,
        plan=None,
        reason_codes=None,
        entry_fills=None,
        exit_fill_changes=None,
        final_changes=None,
        funding=None,
    ):
        parent = self._plan() if plan is None else plan
        entry_request = self._entry_request(parent)
        if entry_fills is None:
            entry_fills = self._entry_fills(entry_request)
        action, exit_request = self._close_action_and_request(
            plan=parent,
            reason_codes=reason_codes,
        )
        exit_fill_changes = {} if exit_fill_changes is None else dict(exit_fill_changes)
        exit_fill = self._exit_fill(exit_request, **exit_fill_changes)
        final_changes = {} if final_changes is None else dict(final_changes)
        final_position = self._final_position(plan=parent, **final_changes)
        if funding is None:
            funding = self._funding(plan=parent)
        return {
            "parent_plan": parent,
            "current_lifecycle_state": "EXIT_REQUESTED",
            "exit_authority": action,
            "entry_order_requests": (entry_request,),
            "entry_fills": entry_fills,
            "exit_order_request": exit_request,
            "exit_fills": (exit_fill,),
            "final_position": final_position,
            "funding_evidence": funding,
        }

    def test_canonical_zero_confirmed_ordinary_exit_finalizes_and_emits_audit_refs(self):
        evidence = self._ordinary_evidence()
        outcome = build_trade_result(**evidence)
        result = outcome.trade_result

        self.assertEqual(PositionEvent.POSITION_CLOSED, outcome.event)
        self.assertEqual(PositionLifecycleState.CLOSED, outcome.next_state)
        self.assertEqual("funding-allocation-v0.1", result["funding_evidence_profile_version"])
        self.assertEqual(evidence["funding_evidence"]["funding_evidence_id"], result["funding_evidence_id"])
        self.assertEqual("ZERO_CONFIRMED", result["funding_evidence_status"])
        self.assertNotIn("funding_cost", result)
        self.assertEqual("1.900", result["gross_pnl"])
        self.assertEqual("0.04", result["total_fees"])
        self.assertEqual("1.860", result["net_pnl"])
        self.assertNotIn("slippage_cost", result)

    def test_canonical_zero_confirmed_emergency_exit_finalizes(self):
        plan = self._plan()
        entry_request = self._entry_request(plan)
        action, exit_request = self._close_action_and_request(plan=plan, emergency=True)
        funding = self._funding(plan=plan)
        outcome = build_trade_result(
            plan,
            current_lifecycle_state="EXIT_REQUESTED",
            exit_authority=action,
            entry_order_requests=(entry_request,),
            entry_fills=self._entry_fills(entry_request),
            exit_order_request=exit_request,
            exit_fills=(self._exit_fill(exit_request),),
            final_position=self._final_position(plan=plan),
            funding_evidence=funding,
        )
        self.assertEqual(["E5_EMERGENCY_EXIT_REQUIRED"], outcome.trade_result["exit_reason_codes"])
        self.assertEqual("EMERGENCY_EXIT", outcome.trade_result["exit_authority_refs"][0]["action"])
        self.assertEqual(funding["funding_evidence_id"], outcome.trade_result["funding_evidence_id"])

    def test_structural_full_protection_stop_preserves_existing_closure_semantics(self):
        plan = self._plan()
        entry_request = self._entry_request(plan)
        action, stop_request = self._protection_action_and_request(plan=plan)
        outcome = build_trade_result(
            plan,
            current_lifecycle_state="OPEN_PROTECTED",
            exit_authority=action,
            entry_order_requests=(entry_request,),
            entry_fills=self._entry_fills(entry_request),
            exit_order_request=stop_request,
            exit_fills=(self._exit_fill(stop_request, price="59400"),),
            final_position=self._final_position(plan=plan),
            funding_evidence=self._funding(plan=plan),
        )
        self.assertEqual(["PROTECTION_STOP_FILLED"], outcome.trade_result["exit_reason_codes"])
        self.assertEqual("PROTECTION_STOP", outcome.trade_result["exit_authority_refs"][0]["order_role"])

    def test_exact_pr52_serialized_shape_is_consumable_without_e4_funding_import(self):
        evidence = self._funding()
        self.assertEqual(
            {
                "schema_version",
                "funding_evidence_profile_version",
                "funding_evidence_id",
                "source_kind",
                "source",
                "source_version",
                "source_material_hash",
                "source_record_count",
                "source_complete_through",
                "trade_plan_id",
                "position_id",
                "symbol",
                "interval_start",
                "interval_end",
                "interval_semantics",
                "status",
                "funding_cost",
                "cost_currency",
                "calculated_at",
            },
            set(evidence),
        )
        self.assertNotIn("src.execution.funding", inspect.getsource(trade_result_module))
        self.assertEqual(evidence["funding_evidence_id"], build_trade_result(**self._ordinary_evidence(funding=evidence)).trade_result["funding_evidence_id"])

    def test_funding_evidence_id_is_recomputed_and_corruption_fails_closed(self):
        evidence = self._funding()
        evidence["funding_evidence_id"] = "fundev_" + ("0" * 64)
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**self._ordinary_evidence(funding=evidence))
        self.assertEqual("FUNDING_EVIDENCE_ID_MISMATCH", caught.exception.code)

    def test_exact_plan_position_symbol_and_interval_mismatch_fail_closed(self):
        cases = (
            (self._funding(trade_plan_id="plan-other"), "FUNDING_TRADE_PLAN_MISMATCH"),
            (self._funding(position_id="position-other"), "FUNDING_POSITION_MISMATCH"),
            (self._funding(symbol="ETH_USDT_PERP"), "FUNDING_SYMBOL_MISMATCH"),
            (self._funding(interval_start="2026-08-24T05:05:11Z"), "FUNDING_INTERVAL_MISMATCH"),
            (self._funding(interval_end="2026-08-24T05:20:41Z"), "FUNDING_INTERVAL_MISMATCH"),
        )
        for funding, code in cases:
            funding["funding_evidence_id"] = stable_funding_id(funding)
            with self.subTest(code=code):
                with self.assertRaises(TradeResultBuildError) as caught:
                    build_trade_result(**self._ordinary_evidence(funding=funding))
                self.assertEqual(code, caught.exception.code)

    def test_unsupported_schema_profile_source_kind_and_blank_source_fail_closed(self):
        cases = (
            ({"schema_version": "contracts-v9"}, "FUNDING_SCHEMA_UNSUPPORTED"),
            ({"funding_evidence_profile_version": "funding-v9"}, "FUNDING_PROFILE_UNSUPPORTED"),
            ({"source_kind": "UNKNOWN_SOURCE"}, "FUNDING_SOURCE_KIND_UNSUPPORTED"),
            ({"source": ""}, "INVALID_TEXT_FIELD"),
            ({"source_version": ""}, "INVALID_TEXT_FIELD"),
        )
        for changes, code in cases:
            funding = self._funding()
            funding.update(changes)
            if all(field in funding for field in FUNDING_IDENTITY_FIELDS):
                funding["funding_evidence_id"] = stable_funding_id(funding)
            with self.subTest(changes=changes):
                with self.assertRaises(TradeResultBuildError) as caught:
                    build_trade_result(**self._ordinary_evidence(funding=funding))
                self.assertEqual(code, caught.exception.code)

    def test_incomplete_watermark_and_premature_calculated_at_fail_closed(self):
        for funding, code in (
            (
                self._funding(source_complete_through="2026-08-24T05:20:39Z"),
                "FUNDING_SOURCE_INCOMPLETE",
            ),
            (
                self._funding(calculated_at="2026-08-24T05:20:39Z"),
                "FUNDING_CALCULATED_PREMATURELY",
            ),
        ):
            funding["funding_evidence_id"] = stable_funding_id(funding)
            with self.subTest(code=code):
                with self.assertRaises(TradeResultBuildError) as caught:
                    build_trade_result(**self._ordinary_evidence(funding=funding))
                self.assertEqual(code, caught.exception.code)

    def test_malformed_source_hash_fails_closed(self):
        funding = self._funding(source_material_hash="not-a-sha256")
        funding["funding_evidence_id"] = "fundev_" + ("0" * 64)
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**self._ordinary_evidence(funding=funding))
        self.assertEqual("FUNDING_SOURCE_HASH_INVALID", caught.exception.code)

    def test_zero_confirmed_count_and_cost_contradictions_fail_closed(self):
        for funding in (
            self._funding(source_record_count=1),
            self._funding(funding_cost="0.1"),
        ):
            funding["funding_evidence_id"] = stable_funding_id(funding)
            with self.assertRaises(TradeResultBuildError) as caught:
                build_trade_result(**self._ordinary_evidence(funding=funding))
            self.assertEqual("ZERO_FUNDING_CONTRADICTION", caught.exception.code)

    def test_included_signed_cost_is_decimal_and_net_pnl_formula_is_unchanged(self):
        cost = self._funding(
            status="INCLUDED",
            funding_cost="0.25",
            source_record_count=2,
            source="R7_TEST_INCLUDED_FUNDING_MODEL",
            source_version="paper-included-test-v0.1",
        )
        result = build_trade_result(**self._ordinary_evidence(funding=cost)).trade_result
        self.assertEqual("0.25", result["funding_cost"])
        self.assertEqual("1.610", result["net_pnl"])

        credit = self._funding(
            status="INCLUDED",
            funding_cost="-0.10",
            source_record_count=1,
            source="R7_TEST_INCLUDED_FUNDING_MODEL",
            source_version="paper-included-test-v0.1",
        )
        credit_result = build_trade_result(**self._ordinary_evidence(funding=credit)).trade_result
        self.assertEqual("-0.10", credit_result["funding_cost"])
        self.assertEqual("1.960", credit_result["net_pnl"])

    def test_unsupported_funding_currency_fails_closed(self):
        funding = self._funding(cost_currency="BTC")
        funding["funding_evidence_id"] = stable_funding_id(funding)
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**self._ordinary_evidence(funding=funding))
        self.assertEqual("FUNDING_CURRENCY_UNSUPPORTED", caught.exception.code)

    def test_missing_canonical_funding_evidence_and_legacy_helper_cannot_bypass(self):
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**self._ordinary_evidence(funding=None))
        self.assertEqual("CANONICAL_FUNDING_EVIDENCE_REQUIRED", caught.exception.code)

        legacy = FundingEvidence(
            status="ZERO_CONFIRMED",
            source_version="legacy-private-v0.1",
            position_id="position-result-001",
            interval_start=self.entry_fill_1_at,
            interval_end=self.flat_observed_at,
            funding_cost=None,
        )
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**self._ordinary_evidence(funding=legacy))
        self.assertEqual("CANONICAL_FUNDING_EVIDENCE_REQUIRED", caught.exception.code)

    def test_calculated_at_only_change_keeps_funding_and_trade_result_identity_stable(self):
        first = self._funding(calculated_at="2026-08-24T05:20:50Z")
        second = dict(first)
        second["calculated_at"] = "2026-08-24T05:21:50Z"
        self.assertEqual(first["funding_evidence_id"], second["funding_evidence_id"])

        first_result = build_trade_result(**self._ordinary_evidence(funding=first)).trade_result
        second_result = build_trade_result(**self._ordinary_evidence(funding=second)).trade_result
        self.assertEqual(first_result["trade_result_id"], second_result["trade_result_id"])

    def test_changed_funding_identity_material_changes_trade_result_identity(self):
        first = self._funding()
        changed = self._funding(
            source_material_hash=hashlib.sha256(b"changed-authoritative-source-material").hexdigest()
        )
        self.assertNotEqual(first["funding_evidence_id"], changed["funding_evidence_id"])
        first_result = build_trade_result(**self._ordinary_evidence(funding=first)).trade_result
        changed_result = build_trade_result(**self._ordinary_evidence(funding=changed)).trade_result
        self.assertNotEqual(first_result["trade_result_id"], changed_result["trade_result_id"])

    def test_authoritative_flatness_remains_mandatory(self):
        for changes, code in (
            ({"actual_quantity": "0.001"}, "FINAL_POSITION_NOT_FLAT"),
            ({"reconciliation_status": "UNKNOWN"}, "FINAL_POSITION_NOT_CONSISTENT"),
            ({"reconciliation_status": "RECONCILIATION_REQUIRED"}, "FINAL_POSITION_NOT_CONSISTENT"),
            ({"broker_state_observed_at": "2026-08-24T05:20:29Z"}, "FINAL_POSITION_STALE"),
        ):
            evidence = self._ordinary_evidence(final_changes=changes)
            if "broker_state_observed_at" in changes:
                evidence["funding_evidence"] = self._funding(
                    interval_end=changes["broker_state_observed_at"],
                    source_complete_through=changes["broker_state_observed_at"],
                    calculated_at="2026-08-24T05:20:50Z",
                )
            with self.subTest(changes=changes):
                with self.assertRaises(TradeResultBuildError) as caught:
                    build_trade_result(**evidence)
                self.assertEqual(code, caught.exception.code)

    def test_partial_close_quantity_conservation_and_cross_set_duplicates_fail_closed(self):
        partial = self._ordinary_evidence(
            exit_fill_changes={"quantity": "0.001"},
            final_changes={"actual_quantity": "0.001"},
        )
        with self.assertRaises(TradeResultBuildError):
            build_trade_result(**partial)

        duplicate = self._ordinary_evidence()
        duplicate_exit = replace(
            duplicate["exit_fills"][0],
            fill_id=duplicate["entry_fills"][0].fill_id,
        )
        duplicate["exit_fills"] = (duplicate_exit,)
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**duplicate)
        self.assertEqual("CROSS_SET_DUPLICATE_FILL", caught.exception.code)

    def test_wrong_exit_role_and_exact_entry_request_binding_fail_closed(self):
        wrong_role = self._ordinary_evidence()
        wrong_role["exit_fills"] = (
            replace(wrong_role["exit_fills"][0], order_role="PROTECTION_STOP"),
        )
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**wrong_role)
        self.assertEqual("EXIT_FILL_ROLE_MISMATCH", caught.exception.code)

        exact_binding = self._ordinary_evidence()
        exact_binding["entry_fills"] = (
            replace(exact_binding["entry_fills"][0], client_order_id="different-entry-order"),
            exact_binding["entry_fills"][1],
        )
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**exact_binding)
        self.assertEqual("ENTRY_FILL_REQUEST_BINDING_MISSING", caught.exception.code)

    def test_missing_fee_and_unsupported_fee_currency_still_fail_closed(self):
        evidence = self._ordinary_evidence()
        evidence["entry_fills"] = self._entry_fills(
            evidence["entry_order_requests"][0],
            missing_fee=True,
        )
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**evidence)
        self.assertEqual("FILL_FEE_MISSING", caught.exception.code)

        evidence = self._ordinary_evidence()
        evidence["entry_fills"] = self._entry_fills(
            evidence["entry_order_requests"][0],
            fee_currency="BTC",
        )
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**evidence)
        self.assertEqual("UNSUPPORTED_FEE_CURRENCY", caught.exception.code)

    def test_short_pnl_uses_actual_fill_prices_and_no_slippage_double_charge(self):
        plan = self._plan(direction="SHORT")
        entry_request = self._entry_request(plan)
        entry_fills = (
            replace(self._entry_fills(entry_request)[0], side=Side.SELL),
            replace(self._entry_fills(entry_request)[1], side=Side.SELL),
        )
        action, exit_request = self._close_action_and_request(plan=plan)
        exit_fill = self._exit_fill(exit_request, price="59000")
        result = build_trade_result(
            plan,
            current_lifecycle_state="EXIT_REQUESTED",
            exit_authority=action,
            entry_order_requests=(entry_request,),
            entry_fills=entry_fills,
            exit_order_request=exit_request,
            exit_fills=(exit_fill,),
            final_position=self._final_position(plan=plan),
            funding_evidence=self._funding(plan=plan),
        ).trade_result
        self.assertEqual("2.100", result["gross_pnl"])
        self.assertEqual("2.060", result["net_pnl"])
        self.assertNotIn("slippage_cost", result)

    def test_opened_closed_time_and_existing_state_machine_semantics_remain_compatible(self):
        result = build_trade_result(**self._ordinary_evidence()).trade_result
        self.assertEqual("2026-08-24T05:05:10Z", result["opened_at"])
        self.assertEqual("2026-08-24T05:20:40Z", result["closed_at"])
        self.assertEqual(result["closed_at"], result["flat_position_observed_at"])
        self.assertEqual(
            PositionLifecycleState.CLOSED,
            transition(PositionLifecycleState.EXIT_REQUESTED, PositionEvent.POSITION_CLOSED),
        )

    def test_no_provider_native_credential_persistence_or_release_fields_are_emitted(self):
        result = build_trade_result(**self._ordinary_evidence()).trade_result
        for forbidden in (
            "api_key",
            "secret_key",
            "passphrase",
            "credentials",
            "account_id",
            "provider_instrument_id",
            "contract_count",
            "database_id",
            "storage_key",
            "release_gate",
            "paper_ready",
            "live_authorized",
        ):
            self.assertNotIn(forbidden, result)


if __name__ == "__main__":
    unittest.main()
