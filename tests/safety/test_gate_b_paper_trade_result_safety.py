import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from position import (
    PositionEvent,
    PositionLifecycleState,
    ProtectionResultEvidence,
    TradeResultBuildError,
    authorize_close_position_action,
    build_protect_position_action,
    build_trade_result,
    interpret_protection_result,
)
from src.brokers.paper import PaperBroker, ReconciliationRequiredError
from src.execution.close import prepare_close_order
from src.execution.funding import produce_paper_zero_funding_evidence
from src.execution.gateway import ExecutionGateway
from src.execution.models import OrderStatus
from src.execution.protection import prepare_protection_order


class GateBPaperTradeResultSafetyDefinitions(unittest.TestCase):
    """Fail-closed cross-module definitions for the in-memory Gate B chain."""

    def setUp(self):
        self.entry_request_at = datetime(2026, 8, 24, 8, 0, 0, tzinfo=timezone.utc)
        self.entry_fill_at = datetime(2026, 8, 24, 8, 0, 10, tzinfo=timezone.utc)
        self.position_observed_at = datetime(2026, 8, 24, 8, 0, 20, tzinfo=timezone.utc)
        self.close_action_at = datetime(2026, 8, 24, 8, 1, 0, tzinfo=timezone.utc)
        self.close_request_at = datetime(2026, 8, 24, 8, 1, 10, tzinfo=timezone.utc)
        self.close_fill_at = datetime(2026, 8, 24, 8, 1, 20, tzinfo=timezone.utc)
        self.flat_at = datetime(2026, 8, 24, 8, 1, 30, tzinfo=timezone.utc)
        self.protection_at = self.position_observed_at
        self.protection_fill_at = datetime(2026, 8, 24, 8, 0, 40, tzinfo=timezone.utc)
        self.protection_flat_at = datetime(2026, 8, 24, 8, 0, 50, tzinfo=timezone.utc)

    def _plan(self):
        return {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-e7-paper-safety-001",
            "risk_decision_id": "risk-e7-paper-safety-001",
            "intent_id": "intent-e7-paper-safety-001",
            "strategy_id": "strategy-e7-paper-safety",
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
            "risk_policy_version": "e5-e7-paper-safety-policy-v0.1",
        }

    def _position(self, *, lifecycle="OPEN_PROTECTED"):
        return {
            "schema_version": "contracts-v0.1",
            "position_id": "position-e7-paper-safety-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": "0.0012",
            "average_entry_price": "60000",
            "opened_at": "2026-08-24T08:00:10Z",
            "broker_state_observed_at": "2026-08-24T08:00:20Z",
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": lifecycle,
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }

    def _entry_truth(self, broker, plan, *, fee=Decimal("0.01"), fee_currency="USDT"):
        request = ExecutionGateway().prepare_entry_order(plan, now=self.entry_request_at)
        broker.submit_order(request)
        fill = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0012"),
            price=Decimal("60000"),
            filled_at=self.entry_fill_at,
            fee=fee,
            fee_currency=fee_currency,
            liquidity_role="TAKER",
        )
        return request, fill

    def _completed_explicit_chain(self, *, exit_fee=Decimal("0.01"), exit_fee_currency="USDT"):
        plan = self._plan()
        broker = PaperBroker()
        entry_request, entry_fill = self._entry_truth(broker, plan)
        source_position = self._position()
        close = authorize_close_position_action(
            source_position,
            plan,
            action="EXIT",
            created_at=self.close_action_at,
            expires_at=self.close_action_at + timedelta(seconds=60),
        )
        request = prepare_close_order(
            close.position_action,
            plan,
            source_position,
            now=self.close_request_at,
        )
        broker.submit_order(request)
        exit_fill = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0012"),
            price=Decimal("61000"),
            filled_at=self.close_fill_at,
            fee=exit_fee,
            fee_currency=exit_fee_currency,
            liquidity_role="TAKER",
        )
        flat = broker.observe_position_after_close(
            request,
            source_position,
            observed_at=self.flat_at,
        )
        funding = produce_paper_zero_funding_evidence(plan, flat, calculated_at=self.flat_at)
        return {
            "plan": plan,
            "broker": broker,
            "entry_request": entry_request,
            "entry_fill": entry_fill,
            "source_position": source_position,
            "close": close,
            "request": request,
            "exit_fill": exit_fill,
            "flat": flat,
            "funding": funding,
        }

    def _build(self, evidence, *, final_position=None, funding=None, exit_fills=None):
        return build_trade_result(
            evidence["plan"],
            current_lifecycle_state=evidence["close"].next_state,
            exit_authority=evidence["close"].position_action,
            entry_order_requests=(evidence["entry_request"],),
            entry_fills=(evidence["entry_fill"],),
            exit_order_request=evidence["request"],
            exit_fills=(evidence["exit_fill"],) if exit_fills is None else exit_fills,
            final_position=evidence["flat"] if final_position is None else final_position,
            funding_evidence=evidence["funding"] if funding is None else funding,
        )

    def _protection_request(self):
        plan = self._plan()
        source_position = self._position(lifecycle="OPEN_UNPROTECTED")
        action = build_protect_position_action(
            source_position,
            plan,
            created_at=self.protection_at,
            expires_at=self.protection_at + timedelta(seconds=60),
        )
        request = prepare_protection_order(
            action,
            plan,
            source_position,
            now=self.protection_at,
        )
        return plan, source_position, action, request

    def _verified_protection(self, broker, request, source_position):
        submit = broker.submit_order(request)
        queried = broker.query_order(request.client_order_id)
        self.assertIsNotNone(queried)
        outcome = interpret_protection_result(
            request,
            ProtectionResultEvidence(
                query_performed=True,
                queried_order=queried,
                submit_result=submit,
            ),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )
        self.assertEqual(PositionEvent.PROTECTION_VERIFIED, outcome.event)
        self.assertEqual(PositionLifecycleState.OPEN_PROTECTED, outcome.next_state)
        protected = dict(source_position)
        protected["lifecycle_state"] = outcome.next_state.value
        return outcome, protected

    def test_filled_order_without_later_same_position_flat_observation_cannot_finalize(self):
        evidence = self._completed_explicit_chain()
        queried = evidence["broker"].query_order(evidence["request"].client_order_id)
        self.assertIsNotNone(queried)
        self.assertEqual(OrderStatus.FILLED, queried.order_status)
        nonflat = dict(evidence["source_position"])
        nonflat["broker_state_observed_at"] = "2026-08-24T08:01:30Z"
        with self.assertRaises(TradeResultBuildError) as caught:
            self._build(evidence, final_position=nonflat)
        self.assertEqual("FINAL_POSITION_NOT_FLAT", caught.exception.code)

    def test_partial_protection_stop_cannot_emit_consistent_closure_truth(self):
        _, source_position, _, request = self._protection_request()
        broker = PaperBroker()
        _, protected = self._verified_protection(broker, request, source_position)
        broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0006"),
            price=Decimal("59390"),
            filled_at=self.protection_fill_at,
            fee=Decimal("0.01"),
            fee_currency="USDT",
        )
        with self.assertRaises(ReconciliationRequiredError) as caught:
            broker.observe_position_after_close(
                request,
                protected,
                observed_at=self.protection_flat_at,
            )
        self.assertIn("partial PROTECTION_STOP", str(caught.exception))

    def test_untriggered_protection_stop_cannot_emit_flat_truth(self):
        _, source_position, _, request = self._protection_request()
        broker = PaperBroker()
        _, protected = self._verified_protection(broker, request, source_position)
        with self.assertRaises(ReconciliationRequiredError) as caught:
            broker.observe_position_after_close(
                request,
                protected,
                observed_at=self.protection_flat_at,
            )
        self.assertIn("no trigger Fill truth", str(caught.exception))

    def test_terminal_failed_protection_enters_emergency_not_closed(self):
        _, source_position, _, request = self._protection_request()
        broker = PaperBroker(rejected_outcomes={request.client_order_id: "SANITIZED_PAPER_REJECT"})
        submit = broker.submit_order(request)
        queried = broker.query_order(request.client_order_id)
        self.assertIsNotNone(queried)
        self.assertEqual(OrderStatus.REJECTED, queried.order_status)
        outcome = interpret_protection_result(
            request,
            ProtectionResultEvidence(
                query_performed=True,
                queried_order=queried,
                submit_result=submit,
            ),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )
        self.assertEqual(PositionEvent.PROTECTION_FAILED, outcome.event)
        self.assertEqual(PositionLifecycleState.EMERGENCY, outcome.next_state)
        self.assertFalse(outcome.protection_verified)
        with self.assertRaises(ReconciliationRequiredError):
            broker.observe_position_after_close(
                request,
                source_position,
                observed_at=self.protection_flat_at,
            )

    def test_ambiguous_degraded_protection_without_reconciliation_cannot_verify_or_close(self):
        _, source_position, _, request = self._protection_request()
        broker = PaperBroker(ambiguous_outcomes={request.client_order_id: True})
        submit = broker.submit_order(request)
        self.assertEqual(OrderStatus.RECONCILIATION_REQUIRED, submit.order_status)
        queried = broker.query_order(request.client_order_id)
        self.assertIsNotNone(queried)
        outcome = interpret_protection_result(
            request,
            ProtectionResultEvidence(
                query_performed=True,
                queried_order=queried,
                submit_result=submit,
            ),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )
        self.assertEqual(PositionEvent.STATE_UNKNOWN, outcome.event)
        self.assertEqual(PositionLifecycleState.RECONCILIATION_REQUIRED, outcome.next_state)
        self.assertFalse(outcome.protection_verified)
        protected = dict(source_position)
        protected["lifecycle_state"] = "OPEN_PROTECTED"
        with self.assertRaises(ReconciliationRequiredError) as caught:
            broker.observe_position_after_close(
                request,
                protected,
                observed_at=self.protection_flat_at,
            )
        self.assertIn("ambiguous", str(caught.exception))

    def test_missing_or_corrupt_funding_evidence_never_becomes_zero(self):
        evidence = self._completed_explicit_chain()
        with self.assertRaises(TradeResultBuildError) as missing:
            build_trade_result(
                evidence["plan"],
                current_lifecycle_state=evidence["close"].next_state,
                exit_authority=evidence["close"].position_action,
                entry_order_requests=(evidence["entry_request"],),
                entry_fills=(evidence["entry_fill"],),
                exit_order_request=evidence["request"],
                exit_fills=(evidence["exit_fill"],),
                final_position=evidence["flat"],
                funding_evidence=None,
            )
        self.assertEqual("CANONICAL_FUNDING_EVIDENCE_REQUIRED", missing.exception.code)

        corrupt = dict(evidence["funding"])
        corrupt["funding_evidence_id"] = "fundev_" + "0" * 64
        with self.assertRaises(TradeResultBuildError) as invalid:
            self._build(evidence, funding=corrupt)
        self.assertEqual("FUNDING_EVIDENCE_ID_MISMATCH", invalid.exception.code)

    def test_cross_plan_position_fill_and_funding_lineage_fail_closed(self):
        evidence = self._completed_explicit_chain()
        wrong_funding = dict(evidence["funding"])
        wrong_funding["trade_plan_id"] = "plan-other"
        with self.assertRaises(TradeResultBuildError) as funding_mismatch:
            self._build(evidence, funding=wrong_funding)
        self.assertEqual("FUNDING_TRADE_PLAN_MISMATCH", funding_mismatch.exception.code)

        wrong_fill = replace(evidence["exit_fill"], position_id="position-other")
        with self.assertRaises(TradeResultBuildError) as fill_mismatch:
            self._build(evidence, exit_fills=(wrong_fill,))
        self.assertEqual("EXIT_FILL_AUTHORITY_MISMATCH", fill_mismatch.exception.code)

    def test_quantity_conservation_and_fee_evidence_remain_required(self):
        evidence = self._completed_explicit_chain()
        partial_fill = replace(evidence["exit_fill"], quantity=Decimal("0.0006"))
        with self.assertRaises(TradeResultBuildError) as quantity_error:
            self._build(evidence, exit_fills=(partial_fill,))
        self.assertEqual("QUANTITY_CONSERVATION_FAILED", quantity_error.exception.code)

        missing_fee = replace(evidence["exit_fill"], fee=None, fee_currency=None)
        with self.assertRaises(TradeResultBuildError) as fee_error:
            self._build(evidence, exit_fills=(missing_fee,))
        self.assertEqual("FILL_FEE_MISSING", fee_error.exception.code)

    def test_trade_result_contains_no_persistence_or_release_authority_claim(self):
        evidence = self._completed_explicit_chain()
        result = self._build(evidence).trade_result
        for forbidden in (
            "persisted_at",
            "restart_recovered",
            "audit_committed",
            "paper_ready",
            "shadow_ready",
            "live_ready",
            "live_authorized",
        ):
            self.assertNotIn(forbidden, result)


if __name__ == "__main__":
    unittest.main()
