import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from position import (
    FundingEvidence,
    PositionEvent,
    PositionLifecycleState,
    ProtectionResultEvidence,
    TradeResultBuildError,
    build_close_position_action,
    build_protect_position_action,
    build_trade_result,
    interpret_protection_result,
    transition,
)
from src.execution.close import prepare_close_order
from src.execution.gateway import ExecutionGateway
from src.execution.models import (
    ExecutionHealthStatus,
    Fill,
    OrderResult,
    OrderStatus,
    Side,
)
from src.execution.protection import prepare_protection_order


class TradeResultV01Tests(unittest.TestCase):
    def setUp(self):
        self.entry_request_at = datetime(2026, 8, 24, 5, 5, 0, tzinfo=timezone.utc)
        self.entry_fill_1_at = datetime(2026, 8, 24, 5, 5, 10, tzinfo=timezone.utc)
        self.entry_fill_2_at = datetime(2026, 8, 24, 5, 5, 20, tzinfo=timezone.utc)
        self.close_observed_at = datetime(2026, 8, 24, 5, 20, 0, tzinfo=timezone.utc)
        self.close_action_at = datetime(2026, 8, 24, 5, 20, 10, tzinfo=timezone.utc)
        self.close_request_at = datetime(2026, 8, 24, 5, 20, 20, tzinfo=timezone.utc)
        self.exit_fill_at = datetime(2026, 8, 24, 5, 20, 30, tzinfo=timezone.utc)
        self.flat_observed_at = datetime(2026, 8, 24, 5, 20, 40, tzinfo=timezone.utc)

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

    def _entry_fills(self, request, *, fee_currency="USDT"):
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
                fee=Decimal("0.01"),
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

    def _close_action_and_request(self, *, plan=None, emergency=False, reason_codes=None, source_changes=None):
        parent = self._plan() if plan is None else plan
        source_changes = {} if source_changes is None else dict(source_changes)
        source_changes.setdefault("lifecycle_state", "EMERGENCY" if emergency else "OPEN_PROTECTED")
        source = self._source_position(plan=parent, **source_changes)
        action = build_close_position_action(
            source,
            parent,
            action="EMERGENCY_EXIT" if emergency else "EXIT",
            created_at=self.close_action_at,
            expires_at=self.close_action_at + timedelta(seconds=60),
            reason_codes=reason_codes,
        )
        request = prepare_close_order(action, parent, source, now=self.close_request_at)
        return action, request, source

    def _protection_action_and_request(self, *, plan=None):
        parent = self._plan() if plan is None else plan
        source = self._source_position(
            plan=parent,
            lifecycle_state="OPEN_UNPROTECTED",
            broker_state_observed_at="2026-08-24T05:06:00Z",
        )
        action_created = datetime(2026, 8, 24, 5, 6, 10, tzinfo=timezone.utc)
        action = build_protect_position_action(
            source,
            parent,
            created_at=action_created,
            expires_at=datetime(2026, 8, 24, 5, 30, 0, tzinfo=timezone.utc),
        )
        request = prepare_protection_order(
            action,
            parent,
            source,
            now=datetime(2026, 8, 24, 5, 6, 20, tzinfo=timezone.utc),
        )
        return action, request, source

    def _exit_fill(self, request, *, fill_id="fill-exit-001", quantity="0.002", price="61000", fee="0.02", fee_currency="USDT", **changes):
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

    def _final_position(self, *, plan=None, position_id="position-result-001", **changes):
        parent = self._plan() if plan is None else plan
        values = {
            "schema_version": "contracts-v0.1",
            "position_id": position_id,
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

    def _funding(self, *, position_id="position-result-001", status="ZERO_CONFIRMED", funding_cost=None, source_version="paper-funding-v0.1", interval_end=None):
        return FundingEvidence(
            status=status,
            source_version=source_version,
            position_id=position_id,
            interval_start=self.entry_fill_1_at,
            interval_end=self.flat_observed_at if interval_end is None else interval_end,
            funding_cost=funding_cost,
        )

    def _ordinary_evidence(self, *, plan=None, reason_codes=None, exit_fill_changes=None, final_changes=None, funding=None):
        parent = self._plan() if plan is None else plan
        entry_request = self._entry_request(parent)
        entry_fills = self._entry_fills(entry_request)
        action, exit_request, _ = self._close_action_and_request(
            plan=parent,
            reason_codes=reason_codes,
        )
        exit_fill_changes = {} if exit_fill_changes is None else dict(exit_fill_changes)
        exit_fill = self._exit_fill(exit_request, **exit_fill_changes)
        final_changes = {} if final_changes is None else dict(final_changes)
        final_position = self._final_position(plan=parent, **final_changes)
        funding = self._funding() if funding is None else funding
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

    def test_valid_ordinary_exit_requires_flat_proof_and_builds_canonical_result(self):
        outcome = build_trade_result(**self._ordinary_evidence())
        result = outcome.trade_result

        self.assertEqual(PositionEvent.POSITION_CLOSED, outcome.event)
        self.assertEqual(PositionLifecycleState.CLOSED, outcome.next_state)
        self.assertEqual("contracts-v0.1", result["schema_version"])
        self.assertEqual("trade-result-v0.1", result["trade_result_profile_version"])
        self.assertEqual("linear-base-asset-pnl-v0.1", result["pnl_profile_version"])
        self.assertEqual("0.002", result["entry_quantity"])
        self.assertEqual("60050", result["average_entry_price"])
        self.assertEqual("61000", result["average_exit_price"])
        self.assertEqual("1.900", result["gross_pnl"])
        self.assertEqual("0.04", result["total_fees"])
        self.assertEqual("1.860", result["net_pnl"])
        self.assertEqual(["E5_EXIT_REQUESTED"], result["exit_reason_codes"])
        self.assertEqual("2026-08-24T05:05:10Z", result["opened_at"])
        self.assertEqual("2026-08-24T05:20:40Z", result["closed_at"])
        self.assertEqual(result["closed_at"], result["flat_position_observed_at"])
        self.assertEqual("ZERO_CONFIRMED", result["funding_evidence_status"])
        self.assertNotIn("funding_cost", result)
        self.assertNotIn("slippage_cost", result)
        self.assertEqual("EXIT", result["exit_authority_refs"][0]["action"])
        self.assertEqual("POSITION_EXIT", result["exit_authority_refs"][0]["order_role"])

    def test_valid_emergency_exit_preserves_emergency_authority_and_reason(self):
        plan = self._plan()
        entry_request = self._entry_request(plan)
        action, exit_request, _ = self._close_action_and_request(plan=plan, emergency=True)
        outcome = build_trade_result(
            plan,
            current_lifecycle_state="EXIT_REQUESTED",
            exit_authority=action,
            entry_order_requests=(entry_request,),
            entry_fills=self._entry_fills(entry_request),
            exit_order_request=exit_request,
            exit_fills=(self._exit_fill(exit_request),),
            final_position=self._final_position(plan=plan),
            funding_evidence=self._funding(),
        )
        result = outcome.trade_result
        self.assertEqual(["E5_EMERGENCY_EXIT_REQUIRED"], result["exit_reason_codes"])
        self.assertEqual("EMERGENCY_EXIT", result["exit_authority_refs"][0]["action"])
        self.assertEqual("EMERGENCY_EXIT", result["exit_authority_refs"][0]["order_role"])
        self.assertEqual(PositionLifecycleState.CLOSED, outcome.next_state)

    def test_full_protection_stop_can_finalize_only_with_flat_truth(self):
        plan = self._plan()
        entry_request = self._entry_request(plan)
        action, stop_request, _ = self._protection_action_and_request(plan=plan)
        outcome = build_trade_result(
            plan,
            current_lifecycle_state="OPEN_PROTECTED",
            exit_authority=action,
            entry_order_requests=(entry_request,),
            entry_fills=self._entry_fills(entry_request),
            exit_order_request=stop_request,
            exit_fills=(self._exit_fill(stop_request, price="59400"),),
            final_position=self._final_position(plan=plan),
            funding_evidence=self._funding(),
        )
        result = outcome.trade_result
        self.assertEqual(["PROTECTION_STOP_FILLED"], result["exit_reason_codes"])
        self.assertEqual("PROTECT", result["exit_authority_refs"][0]["action"])
        self.assertEqual("PROTECTION_STOP", result["exit_authority_refs"][0]["order_role"])
        self.assertEqual(PositionLifecycleState.CLOSED, outcome.next_state)

    def test_full_fill_or_filled_status_never_substitutes_for_flat_position_truth(self):
        evidence = self._ordinary_evidence(final_changes={"actual_quantity": "0.0001"})
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**evidence)
        self.assertEqual("FINAL_POSITION_NOT_FLAT", caught.exception.code)

    def test_unknown_reconciliation_required_or_stale_final_position_cannot_finalize(self):
        for status in ("UNKNOWN", "MISMATCH", "RECONCILIATION_REQUIRED"):
            with self.subTest(status=status):
                evidence = self._ordinary_evidence(final_changes={"reconciliation_status": status})
                with self.assertRaises(TradeResultBuildError) as caught:
                    build_trade_result(**evidence)
                self.assertEqual("FINAL_POSITION_NOT_CONSISTENT", caught.exception.code)

        evidence = self._ordinary_evidence(
            final_changes={"broker_state_observed_at": "2026-08-24T05:20:29Z"},
            funding=self._funding(interval_end=datetime(2026, 8, 24, 5, 20, 29, tzinfo=timezone.utc)),
        )
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**evidence)
        self.assertEqual("FINAL_POSITION_STALE", caught.exception.code)

    def test_partial_explicit_and_partial_protection_close_cannot_finalize(self):
        explicit = self._ordinary_evidence(
            exit_fill_changes={"quantity": "0.001"},
            final_changes={"actual_quantity": "0.001"},
        )
        with self.assertRaises(TradeResultBuildError):
            build_trade_result(**explicit)

        plan = self._plan()
        entry_request = self._entry_request(plan)
        action, stop_request, _ = self._protection_action_and_request(plan=plan)
        with self.assertRaises(TradeResultBuildError):
            build_trade_result(
                plan,
                current_lifecycle_state="OPEN_PROTECTED",
                exit_authority=action,
                entry_order_requests=(entry_request,),
                entry_fills=self._entry_fills(entry_request),
                exit_order_request=stop_request,
                exit_fills=(self._exit_fill(stop_request, quantity="0.001", price="59400"),),
                final_position=self._final_position(plan=plan, actual_quantity="0.001"),
                funding_evidence=self._funding(),
            )

    def test_duplicate_fill_ids_and_cross_set_duplicate_fill_fail_closed(self):
        evidence = self._ordinary_evidence()
        duplicated_exit = evidence["exit_fills"][0]
        evidence["exit_fills"] = (duplicated_exit, duplicated_exit)
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**evidence)
        self.assertEqual("DUPLICATE_FILL_ID", caught.exception.code)

        evidence = self._ordinary_evidence()
        exit_fill = replace(evidence["exit_fills"][0], fill_id=evidence["entry_fills"][0].fill_id)
        evidence["exit_fills"] = (exit_fill,)
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**evidence)
        self.assertEqual("CROSS_SET_DUPLICATE_FILL", caught.exception.code)

    def test_cross_plan_position_symbol_side_role_and_action_lineage_fail_closed(self):
        base = self._ordinary_evidence()
        cases = (
            replace(base["exit_fills"][0], trade_plan_id="plan-other"),
            replace(base["exit_fills"][0], position_id="position-other"),
            replace(base["exit_fills"][0], symbol="ETH_USDT_PERP"),
            replace(base["exit_fills"][0], side=Side.BUY),
            replace(base["exit_fills"][0], order_role="PROTECTION_STOP"),
            replace(base["exit_fills"][0], position_action_id="posact-other"),
        )
        for bad_fill in cases:
            with self.subTest(bad_fill=bad_fill):
                evidence = self._ordinary_evidence()
                evidence["exit_fills"] = (bad_fill,)
                with self.assertRaises(TradeResultBuildError):
                    build_trade_result(**evidence)

        evidence = self._ordinary_evidence()
        forged = dict(evidence["exit_authority"])
        forged["action"] = "PROTECT"
        evidence["exit_authority"] = forged
        with self.assertRaises(TradeResultBuildError):
            build_trade_result(**evidence)

    def test_entry_fill_must_bind_to_declared_entry_request_not_trade_plan_alone(self):
        evidence = self._ordinary_evidence()
        bad = replace(evidence["entry_fills"][0], client_order_id="different-entry-client")
        evidence["entry_fills"] = (bad, evidence["entry_fills"][1])
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**evidence)
        self.assertEqual("ENTRY_FILL_REQUEST_BINDING_MISSING", caught.exception.code)

    def test_quantity_conservation_exact_pass_and_fail(self):
        result = build_trade_result(**self._ordinary_evidence()).trade_result
        self.assertEqual("0.002", result["entry_quantity"])

        evidence = self._ordinary_evidence(exit_fill_changes={"quantity": "0.0019"})
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**evidence)
        self.assertEqual("QUANTITY_CONSERVATION_FAILED", caught.exception.code)

    def test_missing_fee_or_unsupported_fee_currency_blocks_finalization(self):
        evidence = self._ordinary_evidence(exit_fill_changes={"fee": None, "fee_currency": None})
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**evidence)
        self.assertEqual("FILL_FEE_MISSING", caught.exception.code)

        evidence = self._ordinary_evidence(exit_fill_changes={"fee": "0.02", "fee_currency": "BTC"})
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**evidence)
        self.assertEqual("UNSUPPORTED_FEE_CURRENCY", caught.exception.code)

    def test_zero_confirmed_and_included_funding_use_signed_cost_semantics(self):
        zero = build_trade_result(**self._ordinary_evidence()).trade_result
        self.assertEqual("1.860", zero["net_pnl"])
        self.assertNotIn("funding_cost", zero)

        included = build_trade_result(
            **self._ordinary_evidence(
                funding=self._funding(status="INCLUDED", funding_cost="0.25")
            )
        ).trade_result
        self.assertEqual("INCLUDED", included["funding_evidence_status"])
        self.assertEqual("0.25", included["funding_cost"])
        self.assertEqual("1.610", included["net_pnl"])

        credit = build_trade_result(
            **self._ordinary_evidence(
                funding=self._funding(status="INCLUDED", funding_cost="-0.10")
            )
        ).trade_result
        self.assertEqual("1.960", credit["net_pnl"])

    def test_missing_or_contradictory_funding_evidence_blocks_finalization(self):
        evidence = self._ordinary_evidence()
        evidence["funding_evidence"] = None
        with self.assertRaises(TradeResultBuildError):
            build_trade_result(**evidence)

        evidence = self._ordinary_evidence(
            funding=self._funding(status="ZERO_CONFIRMED", funding_cost="0.01")
        )
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**evidence)
        self.assertEqual("ZERO_FUNDING_CONTRADICTION", caught.exception.code)

    def test_long_and_short_pnl_use_actual_fill_prices_and_do_not_double_subtract_slippage(self):
        long_result = build_trade_result(**self._ordinary_evidence()).trade_result
        self.assertEqual("1.900", long_result["gross_pnl"])
        self.assertEqual("1.860", long_result["net_pnl"])
        self.assertNotIn("slippage_cost", long_result)

        plan = self._plan(direction="SHORT")
        entry_request = self._entry_request(plan)
        source = self._source_position(plan=plan, side="SHORT", lifecycle_state="OPEN_PROTECTED")
        action = build_close_position_action(
            source,
            plan,
            action="EXIT",
            created_at=self.close_action_at,
            expires_at=self.close_action_at + timedelta(seconds=60),
        )
        exit_request = prepare_close_order(action, plan, source, now=self.close_request_at)
        short_result = build_trade_result(
            plan,
            current_lifecycle_state="EXIT_REQUESTED",
            exit_authority=action,
            entry_order_requests=(entry_request,),
            entry_fills=self._entry_fills(entry_request),
            exit_order_request=exit_request,
            exit_fills=(self._exit_fill(exit_request, price="59000"),),
            final_position=self._final_position(plan=plan, side="SHORT"),
            funding_evidence=self._funding(),
        ).trade_result
        self.assertEqual("2.100", short_result["gross_pnl"])
        self.assertEqual("2.060", short_result["net_pnl"])

    def test_opened_and_closed_time_semantics_fail_closed_on_conflict(self):
        valid = build_trade_result(**self._ordinary_evidence()).trade_result
        self.assertEqual("2026-08-24T05:05:10Z", valid["opened_at"])
        self.assertEqual("2026-08-24T05:20:40Z", valid["closed_at"])

        evidence = self._ordinary_evidence(final_changes={"opened_at": "2026-08-24T05:05:00Z"})
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**evidence)
        self.assertEqual("FINAL_POSITION_OPENED_AT_CONFLICT", caught.exception.code)

    def test_trade_result_identity_is_deterministic_and_changes_with_material_evidence(self):
        baseline = build_trade_result(**self._ordinary_evidence()).trade_result
        repeat = build_trade_result(**self._ordinary_evidence()).trade_result
        self.assertEqual(baseline, repeat)
        self.assertEqual(baseline["trade_result_id"], repeat["trade_result_id"])

        changed_fill = build_trade_result(
            **self._ordinary_evidence(exit_fill_changes={"price": "61100"})
        ).trade_result
        self.assertNotEqual(baseline["trade_result_id"], changed_fill["trade_result_id"])

        changed_reason = build_trade_result(
            **self._ordinary_evidence(reason_codes=("E5_EXIT_REQUESTED", "E5_TIME_STOP"))
        ).trade_result
        self.assertNotEqual(baseline["trade_result_id"], changed_reason["trade_result_id"])

        changed_funding = build_trade_result(
            **self._ordinary_evidence(
                funding=self._funding(source_version="paper-funding-v0.2")
            )
        ).trade_result
        self.assertNotEqual(baseline["trade_result_id"], changed_funding["trade_result_id"])

        later_flat = datetime(2026, 8, 24, 5, 20, 50, tzinfo=timezone.utc)
        changed_flat = build_trade_result(
            **self._ordinary_evidence(
                final_changes={"broker_state_observed_at": "2026-08-24T05:20:50Z"},
                funding=self._funding(interval_end=later_flat),
            )
        ).trade_result
        self.assertNotEqual(baseline["trade_result_id"], changed_flat["trade_result_id"])

    def test_explicit_close_requires_exit_requested_and_protection_close_requires_protected_state(self):
        evidence = self._ordinary_evidence()
        evidence["current_lifecycle_state"] = "OPEN_PROTECTED"
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(**evidence)
        self.assertEqual("EXPLICIT_EXIT_LIFECYCLE_NOT_REQUESTED", caught.exception.code)

        plan = self._plan()
        entry_request = self._entry_request(plan)
        action, stop_request, _ = self._protection_action_and_request(plan=plan)
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(
                plan,
                current_lifecycle_state="OPEN_UNPROTECTED",
                exit_authority=action,
                entry_order_requests=(entry_request,),
                entry_fills=self._entry_fills(entry_request),
                exit_order_request=stop_request,
                exit_fills=(self._exit_fill(stop_request, price="59400"),),
                final_position=self._final_position(plan=plan),
                funding_evidence=self._funding(),
            )
        self.assertEqual("PROTECTION_CLOSE_LIFECYCLE_INVALID", caught.exception.code)

    def test_existing_protection_bridge_close_producer_and_state_machine_remain_compatible(self):
        plan = self._plan()
        protection_action, protection_request, _ = self._protection_action_and_request(plan=plan)
        queried_open = OrderResult(
            schema_version="contracts-v0.1",
            order_request_id=protection_request.order_request_id,
            client_order_id=protection_request.client_order_id,
            broker_order_id="paper-protection-001",
            order_status=OrderStatus.OPEN,
            observed_at=datetime(2026, 8, 24, 5, 6, 21, tzinfo=timezone.utc),
            execution_health_status=ExecutionHealthStatus.HEALTHY,
            requested_quantity=protection_request.quantity,
            filled_quantity=Decimal("0"),
        )
        bridge = interpret_protection_result(
            protection_request,
            ProtectionResultEvidence(query_performed=True, queried_order=queried_open),
            "OPEN_UNPROTECTED",
        )
        self.assertEqual(PositionEvent.PROTECTION_VERIFIED, bridge.event)
        self.assertEqual(PositionLifecycleState.OPEN_PROTECTED, bridge.next_state)
        self.assertEqual(
            PositionLifecycleState.EXIT_REQUESTED,
            transition(PositionLifecycleState.OPEN_PROTECTED, PositionEvent.EXIT_REQUESTED),
        )
        self.assertEqual(
            PositionLifecycleState.CLOSED,
            transition(PositionLifecycleState.EXIT_REQUESTED, PositionEvent.POSITION_CLOSED),
        )

        close_action, _, _ = self._close_action_and_request(plan=plan)
        self.assertEqual("EXIT", close_action["action"])
        self.assertEqual("PROTECT", protection_action["action"])

    def test_trade_result_contains_no_provider_native_credentials_persistence_or_release_fields(self):
        result = build_trade_result(**self._ordinary_evidence()).trade_result
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
            "secret_key",
            "passphrase",
            "credentials",
            "database_id",
            "registry_state",
            "paper_ready",
            "shadow_ready",
            "live_ready",
        ):
            self.assertNotIn(forbidden, result)


if __name__ == "__main__":
    unittest.main()
