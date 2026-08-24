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
_DEFAULT = object()


def stable_funding_id(evidence):
    material = {field: evidence[field] for field in FUNDING_IDENTITY_FIELDS}
    payload = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return "fundev_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TradeResultFundingConsumerTests(unittest.TestCase):
    def setUp(self):
        self.entry_request_at = datetime(2026, 8, 24, 5, 5, 0, tzinfo=timezone.utc)
        self.entry_fill_1_at = datetime(2026, 8, 24, 5, 5, 10, tzinfo=timezone.utc)
        self.entry_fill_2_at = datetime(2026, 8, 24, 5, 5, 20, tzinfo=timezone.utc)
        self.close_action_at = datetime(2026, 8, 24, 5, 20, 10, tzinfo=timezone.utc)
        self.close_request_at = datetime(2026, 8, 24, 5, 20, 20, tzinfo=timezone.utc)
        self.exit_fill_at = datetime(2026, 8, 24, 5, 20, 30, tzinfo=timezone.utc)

    def plan(self, **changes):
        value = {
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
        value.update(changes)
        return value

    def source_position(self, plan=None, **changes):
        parent = self.plan() if plan is None else plan
        value = {
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
        value.update(changes)
        return value

    def entry_request(self, plan=None):
        parent = self.plan() if plan is None else plan
        return ExecutionGateway().prepare_entry_order(parent, now=self.entry_request_at)

    def entry_fills(self, request, *, fee_currency="USDT", first_fee="0.01"):
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
                fee=None if first_fee is None else Decimal(first_fee),
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

    def close_action_request(self, plan=None, *, emergency=False, reason_codes=None):
        parent = self.plan() if plan is None else plan
        source = self.source_position(
            parent,
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
        return action, prepare_close_order(action, parent, source, now=self.close_request_at)

    def protection_action_request(self, plan=None):
        parent = self.plan() if plan is None else plan
        source = self.source_position(
            parent,
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

    def exit_fill(self, request, **changes):
        value = {
            "schema_version": "contracts-v0.1",
            "fill_id": "fill-exit-001",
            "broker_order_id": "broker-exit-001",
            "client_order_id": request.client_order_id,
            "trade_plan_id": request.trade_plan_id,
            "symbol": request.symbol,
            "side": request.side,
            "quantity": Decimal("0.002"),
            "price": Decimal("61000"),
            "filled_at": self.exit_fill_at,
            "fee": Decimal("0.02"),
            "fee_currency": "USDT",
            "position_action_id": request.position_action_id,
            "position_id": request.position_id,
            "order_role": request.order_role,
        }
        value.update(changes)
        return Fill(**value)

    def final_position(self, plan=None, **changes):
        parent = self.plan() if plan is None else plan
        value = {
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
        value.update(changes)
        return value

    def funding(self, plan=None, **changes):
        parent = self.plan() if plan is None else plan
        status = changes.pop("status", "ZERO_CONFIRMED")
        cost = changes.pop("funding_cost", "0")
        count = changes.pop("source_record_count", 0 if status == "ZERO_CONFIRMED" else 1)
        start = changes.pop("interval_start", "2026-08-24T05:05:10Z")
        end = changes.pop("interval_end", "2026-08-24T05:20:40Z")
        source_kind = changes.pop("source_kind", "PAPER_MODEL")
        source = changes.pop("source", "R7_PAPER_FUNDING_MODEL")
        source_version = changes.pop("source_version", "paper-zero-funding-v0.1")
        position_id = changes.pop("position_id", "position-result-001")
        seed = f"{source_kind}|{source}|{source_version}|{parent['trade_plan_id']}|{position_id}|{start}|{end}|{status}|{cost}"
        value = {
            "schema_version": "contracts-v0.1",
            "funding_evidence_profile_version": "funding-allocation-v0.1",
            "source_kind": source_kind,
            "source": source,
            "source_version": source_version,
            "source_material_hash": hashlib.sha256(seed.encode("utf-8")).hexdigest(),
            "source_record_count": count,
            "source_complete_through": end,
            "trade_plan_id": parent["trade_plan_id"],
            "position_id": position_id,
            "symbol": parent["symbol"],
            "interval_start": start,
            "interval_end": end,
            "interval_semantics": "START_INCLUSIVE_END_EXCLUSIVE",
            "status": status,
            "funding_cost": cost,
            "cost_currency": "USDT",
            "calculated_at": "2026-08-24T05:20:50Z",
        }
        value.update(changes)
        value["funding_evidence_id"] = stable_funding_id(value)
        return value

    def ordinary(self, *, plan=None, funding=_DEFAULT, final_changes=None, exit_fill_changes=None):
        parent = self.plan() if plan is None else plan
        entry_request = self.entry_request(parent)
        action, exit_request = self.close_action_request(parent)
        final_changes = {} if final_changes is None else dict(final_changes)
        exit_fill_changes = {} if exit_fill_changes is None else dict(exit_fill_changes)
        if funding is _DEFAULT:
            funding = self.funding(parent)
        return {
            "parent_plan": parent,
            "current_lifecycle_state": "EXIT_REQUESTED",
            "exit_authority": action,
            "entry_order_requests": (entry_request,),
            "entry_fills": self.entry_fills(entry_request),
            "exit_order_request": exit_request,
            "exit_fills": (self.exit_fill(exit_request, **exit_fill_changes),),
            "final_position": self.final_position(parent, **final_changes),
            "funding_evidence": funding,
        }

    def test_zero_confirmed_ordinary_exit_emits_canonical_audit_binding(self):
        evidence = self.ordinary()
        outcome = build_trade_result(**evidence)
        result = outcome.trade_result
        self.assertEqual(PositionEvent.POSITION_CLOSED, outcome.event)
        self.assertEqual(PositionLifecycleState.CLOSED, outcome.next_state)
        self.assertEqual("funding-allocation-v0.1", result["funding_evidence_profile_version"])
        self.assertEqual(evidence["funding_evidence"]["funding_evidence_id"], result["funding_evidence_id"])
        self.assertEqual("ZERO_CONFIRMED", result["funding_evidence_status"])
        self.assertNotIn("funding_cost", result)
        self.assertEqual("1.900", result["gross_pnl"])
        self.assertEqual("1.860", result["net_pnl"])
        self.assertNotIn("slippage_cost", result)

    def test_zero_confirmed_emergency_exit_preserves_emergency_authority(self):
        plan = self.plan()
        entry_request = self.entry_request(plan)
        action, exit_request = self.close_action_request(plan, emergency=True)
        result = build_trade_result(
            plan,
            current_lifecycle_state="EXIT_REQUESTED",
            exit_authority=action,
            entry_order_requests=(entry_request,),
            entry_fills=self.entry_fills(entry_request),
            exit_order_request=exit_request,
            exit_fills=(self.exit_fill(exit_request),),
            final_position=self.final_position(plan),
            funding_evidence=self.funding(plan),
        ).trade_result
        self.assertEqual(["E5_EMERGENCY_EXIT_REQUIRED"], result["exit_reason_codes"])
        self.assertEqual("EMERGENCY_EXIT", result["exit_authority_refs"][0]["action"])

    def test_structural_protection_close_remains_compatible_with_canonical_funding(self):
        plan = self.plan()
        entry_request = self.entry_request(plan)
        action, request = self.protection_action_request(plan)
        result = build_trade_result(
            plan,
            current_lifecycle_state="OPEN_PROTECTED",
            exit_authority=action,
            entry_order_requests=(entry_request,),
            entry_fills=self.entry_fills(entry_request),
            exit_order_request=request,
            exit_fills=(self.exit_fill(request, price=Decimal("59400")),),
            final_position=self.final_position(plan),
            funding_evidence=self.funding(plan),
        ).trade_result
        self.assertEqual(["PROTECTION_STOP_FILLED"], result["exit_reason_codes"])
        self.assertEqual("PROTECTION_STOP", result["exit_authority_refs"][0]["order_role"])

    def test_exact_pr52_shape_is_consumable_without_e4_funding_import(self):
        funding = self.funding()
        self.assertEqual(19, len(funding))
        self.assertEqual(set(FUNDING_IDENTITY_FIELDS) | {"funding_evidence_id", "calculated_at"}, set(funding))
        self.assertNotIn("src.execution.funding", inspect.getsource(trade_result_module))
        self.assertEqual(funding["funding_evidence_id"], build_trade_result(**self.ordinary(funding=funding)).trade_result["funding_evidence_id"])

    def test_id_recomputation_and_hash_shape_fail_closed(self):
        corrupt = self.funding()
        corrupt["funding_evidence_id"] = "fundev_" + "0" * 64
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**self.ordinary(funding=corrupt))
        self.assertEqual("FUNDING_EVIDENCE_ID_MISMATCH", caught.exception.code)

        bad_hash = self.funding(source_material_hash="not-a-sha256")
        bad_hash["funding_evidence_id"] = "fundev_" + "0" * 64
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**self.ordinary(funding=bad_hash))
        self.assertEqual("FUNDING_SOURCE_HASH_INVALID", caught.exception.code)

    def test_lineage_and_interval_mismatch_fail_closed(self):
        cases = (
            ({"trade_plan_id": "plan-other"}, "FUNDING_TRADE_PLAN_MISMATCH"),
            ({"position_id": "position-other"}, "FUNDING_POSITION_MISMATCH"),
            ({"symbol": "ETH_USDT_PERP"}, "FUNDING_SYMBOL_MISMATCH"),
            ({"interval_start": "2026-08-24T05:05:11Z"}, "FUNDING_INTERVAL_MISMATCH"),
            ({"interval_end": "2026-08-24T05:20:41Z"}, "FUNDING_INTERVAL_MISMATCH"),
        )
        for changes, code in cases:
            funding = self.funding(**changes)
            funding["funding_evidence_id"] = stable_funding_id(funding)
            with self.subTest(code=code):
                with self.assertRaises(TradeResultBuildError) as caught:
                    build_trade_result(**self.ordinary(funding=funding))
                self.assertEqual(code, caught.exception.code)

    def test_profile_source_completeness_and_timestamp_validation(self):
        cases = (
            ({"schema_version": "contracts-v9"}, "FUNDING_SCHEMA_UNSUPPORTED"),
            ({"funding_evidence_profile_version": "funding-v9"}, "FUNDING_PROFILE_UNSUPPORTED"),
            ({"source_kind": "UNKNOWN"}, "FUNDING_SOURCE_KIND_UNSUPPORTED"),
            ({"source": ""}, "INVALID_TEXT_FIELD"),
            ({"source_version": ""}, "INVALID_TEXT_FIELD"),
            ({"source_complete_through": "2026-08-24T05:20:39Z"}, "FUNDING_SOURCE_INCOMPLETE"),
            ({"calculated_at": "2026-08-24T05:20:39Z"}, "FUNDING_CALCULATED_PREMATURELY"),
        )
        for changes, code in cases:
            funding = self.funding(**changes)
            if all(field in funding for field in FUNDING_IDENTITY_FIELDS):
                funding["funding_evidence_id"] = stable_funding_id(funding)
            with self.subTest(changes=changes):
                with self.assertRaises(TradeResultBuildError) as caught:
                    build_trade_result(**self.ordinary(funding=funding))
                self.assertEqual(code, caught.exception.code)

    def test_zero_and_included_status_cost_currency_semantics(self):
        for funding in (
            self.funding(source_record_count=1),
            self.funding(funding_cost="0.1"),
        ):
            funding["funding_evidence_id"] = stable_funding_id(funding)
            with self.assertRaises(TradeResultBuildError) as caught:
                build_trade_result(**self.ordinary(funding=funding))
            self.assertEqual("ZERO_FUNDING_CONTRADICTION", caught.exception.code)

        included = self.funding(
            status="INCLUDED",
            source_record_count=2,
            funding_cost="0.25",
            source="R7_TEST_INCLUDED_MODEL",
            source_version="paper-included-test-v0.1",
        )
        result = build_trade_result(**self.ordinary(funding=included)).trade_result
        self.assertEqual("0.25", result["funding_cost"])
        self.assertEqual("1.610", result["net_pnl"])

        credit = self.funding(
            status="INCLUDED",
            source_record_count=1,
            funding_cost="-0.10",
            source="R7_TEST_INCLUDED_MODEL",
            source_version="paper-included-test-v0.1",
        )
        result = build_trade_result(**self.ordinary(funding=credit)).trade_result
        self.assertEqual("-0.10", result["funding_cost"])
        self.assertEqual("1.960", result["net_pnl"])

        unsupported_currency = self.funding(cost_currency="BTC")
        unsupported_currency["funding_evidence_id"] = stable_funding_id(unsupported_currency)
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**self.ordinary(funding=unsupported_currency))
        self.assertEqual("FUNDING_CURRENCY_UNSUPPORTED", caught.exception.code)

    def test_missing_and_legacy_private_funding_cannot_bypass(self):
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**self.ordinary(funding=None))
        self.assertEqual("CANONICAL_FUNDING_EVIDENCE_REQUIRED", caught.exception.code)

        legacy = FundingEvidence(
            status="ZERO_CONFIRMED",
            source_version="legacy-private-v0.1",
            position_id="position-result-001",
            interval_start=self.entry_fill_1_at,
            interval_end=datetime(2026, 8, 24, 5, 20, 40, tzinfo=timezone.utc),
        )
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**self.ordinary(funding=legacy))
        self.assertEqual("CANONICAL_FUNDING_EVIDENCE_REQUIRED", caught.exception.code)

    def test_calculated_at_is_nonidentity_but_changed_allocation_changes_result_id(self):
        first = self.funding(calculated_at="2026-08-24T05:20:50Z")
        later = dict(first)
        later["calculated_at"] = "2026-08-24T05:21:50Z"
        self.assertEqual(first["funding_evidence_id"], later["funding_evidence_id"])
        first_result = build_trade_result(**self.ordinary(funding=first)).trade_result
        later_result = build_trade_result(**self.ordinary(funding=later)).trade_result
        self.assertEqual(first_result["trade_result_id"], later_result["trade_result_id"])

        changed = self.funding(
            source_material_hash=hashlib.sha256(b"changed-source-material").hexdigest()
        )
        changed_result = build_trade_result(**self.ordinary(funding=changed)).trade_result
        self.assertNotEqual(first["funding_evidence_id"], changed["funding_evidence_id"])
        self.assertNotEqual(first_result["trade_result_id"], changed_result["trade_result_id"])

    def test_existing_flat_fill_quantity_fee_and_lineage_guards_remain(self):
        cases = (
            (self.ordinary(final_changes={"actual_quantity": "0.001"}), "FINAL_POSITION_NOT_FLAT"),
            (self.ordinary(final_changes={"reconciliation_status": "UNKNOWN"}), "FINAL_POSITION_NOT_CONSISTENT"),
            (self.ordinary(exit_fill_changes={"quantity": Decimal("0.001")}), "QUANTITY_CONSERVATION_FAILED"),
        )
        for evidence, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(TradeResultBuildError) as caught:
                    build_trade_result(**evidence)
                self.assertEqual(code, caught.exception.code)

        duplicate = self.ordinary()
        duplicate["exit_fills"] = (
            replace(duplicate["exit_fills"][0], fill_id=duplicate["entry_fills"][0].fill_id),
        )
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**duplicate)
        self.assertEqual("CROSS_SET_DUPLICATE_FILL", caught.exception.code)

        wrong_role = self.ordinary()
        wrong_role["exit_fills"] = (replace(wrong_role["exit_fills"][0], order_role="PROTECTION_STOP"),)
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**wrong_role)
        self.assertEqual("EXIT_FILL_ROLE_MISMATCH", caught.exception.code)

        wrong_entry = self.ordinary()
        wrong_entry["entry_fills"] = (
            replace(wrong_entry["entry_fills"][0], client_order_id="other-entry"),
            wrong_entry["entry_fills"][1],
        )
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**wrong_entry)
        self.assertEqual("ENTRY_FILL_REQUEST_BINDING_MISSING", caught.exception.code)

    def test_missing_fee_and_unsupported_fee_currency_remain_fail_closed(self):
        evidence = self.ordinary()
        evidence["entry_fills"] = self.entry_fills(evidence["entry_order_requests"][0], first_fee=None)
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**evidence)
        self.assertEqual("FILL_FEE_MISSING", caught.exception.code)

        evidence = self.ordinary()
        evidence["entry_fills"] = self.entry_fills(evidence["entry_order_requests"][0], fee_currency="BTC")
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**evidence)
        self.assertEqual("UNSUPPORTED_FEE_CURRENCY", caught.exception.code)

    def test_short_pnl_and_time_semantics_are_preserved(self):
        plan = self.plan(direction="SHORT")
        entry_request = self.entry_request(plan)
        action, exit_request = self.close_action_request(plan)
        result = build_trade_result(
            plan,
            current_lifecycle_state="EXIT_REQUESTED",
            exit_authority=action,
            entry_order_requests=(entry_request,),
            entry_fills=self.entry_fills(entry_request),
            exit_order_request=exit_request,
            exit_fills=(self.exit_fill(exit_request, price=Decimal("59000")),),
            final_position=self.final_position(plan),
            funding_evidence=self.funding(plan),
        ).trade_result
        self.assertEqual("2.100", result["gross_pnl"])
        self.assertEqual("2.060", result["net_pnl"])
        self.assertEqual("2026-08-24T05:05:10Z", result["opened_at"])
        self.assertEqual("2026-08-24T05:20:40Z", result["closed_at"])
        self.assertNotIn("slippage_cost", result)
        self.assertEqual(
            PositionLifecycleState.CLOSED,
            transition(PositionLifecycleState.EXIT_REQUESTED, PositionEvent.POSITION_CLOSED),
        )

    def test_trade_result_emits_no_provider_credential_persistence_or_release_fields(self):
        result = build_trade_result(**self.ordinary()).trade_result
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
