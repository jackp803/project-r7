import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from position import (
    PositionEvent,
    PositionLifecycleState,
    ProtectionResultEvidence,
    authorize_close_position_action,
    build_protect_position_action,
    build_trade_result,
    interpret_protection_result,
)
from src.brokers.paper import PaperBroker
from src.execution.close import prepare_close_order
from src.execution.funding import produce_paper_zero_funding_evidence
from src.execution.gateway import ExecutionGateway
from src.execution.models import OrderStatus
from src.execution.protection import prepare_protection_order


class GateBPaperTradeResultIntegrationDefinitions(unittest.TestCase):
    """E7 cross-module definitions over the accepted real in-memory Paper APIs.

    These definitions intentionally stop before persistence/restart. They use E4
    broker/funding truth and E5 lifecycle/TradeResult authority directly; no
    synthetic OrderResult, Fill, flat Position, or funding evidence replaces a
    production boundary in a positive path.
    """

    def setUp(self):
        self.entry_request_at = datetime(2026, 8, 24, 7, 0, 0, tzinfo=timezone.utc)
        self.entry_fill_at = datetime(2026, 8, 24, 7, 0, 10, tzinfo=timezone.utc)
        self.position_observed_at = datetime(2026, 8, 24, 7, 0, 20, tzinfo=timezone.utc)
        self.close_action_at = datetime(2026, 8, 24, 7, 1, 0, tzinfo=timezone.utc)
        self.close_request_at = datetime(2026, 8, 24, 7, 1, 10, tzinfo=timezone.utc)
        self.close_fill_at = datetime(2026, 8, 24, 7, 1, 20, tzinfo=timezone.utc)
        self.flat_observed_at = datetime(2026, 8, 24, 7, 1, 30, tzinfo=timezone.utc)
        # Protection request must be no later than the exact broker observation
        # later carrying E5's OPEN_PROTECTED lifecycle projection.
        self.protection_action_at = self.position_observed_at
        self.protection_request_at = self.position_observed_at
        self.protection_fill_at = datetime(2026, 8, 24, 7, 0, 40, tzinfo=timezone.utc)
        self.protection_flat_at = datetime(2026, 8, 24, 7, 0, 50, tzinfo=timezone.utc)

    def _plan(self):
        return {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-e7-paper-result-001",
            "risk_decision_id": "risk-e7-paper-result-001",
            "intent_id": "intent-e7-paper-result-001",
            "strategy_id": "strategy-e7-paper-result",
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
            "created_at": "2026-08-24T06:59:00Z",
            "expires_at": "2026-08-24T07:00:05Z",
            "risk_policy_version": "e5-e7-paper-result-policy-v0.1",
        }

    def _position(self, *, lifecycle="OPEN_PROTECTED"):
        return {
            "schema_version": "contracts-v0.1",
            "position_id": "position-e7-paper-result-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": "0.0012",
            "average_entry_price": "60000",
            "opened_at": "2026-08-24T07:00:10Z",
            "broker_state_observed_at": "2026-08-24T07:00:20Z",
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": lifecycle,
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }

    def _entry_truth(self, broker, plan):
        request = ExecutionGateway().prepare_entry_order(plan, now=self.entry_request_at)
        broker.submit_order(request)
        fill = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0012"),
            price=Decimal("60000"),
            filled_at=self.entry_fill_at,
            fee=Decimal("0.01"),
            fee_currency="USDT",
            liquidity_role="TAKER",
        )
        return request, fill

    def _explicit_chain(self, *, emergency=False):
        plan = self._plan()
        broker = PaperBroker()
        entry_request, entry_fill = self._entry_truth(broker, plan)
        source_position = self._position(lifecycle="EMERGENCY" if emergency else "OPEN_PROTECTED")
        close_outcome = authorize_close_position_action(
            source_position,
            plan,
            action="EMERGENCY_EXIT" if emergency else "EXIT",
            created_at=self.close_action_at,
            expires_at=self.close_action_at + timedelta(seconds=60),
        )
        request = prepare_close_order(
            close_outcome.position_action,
            plan,
            source_position,
            now=self.close_request_at,
        )
        submit = broker.submit_order(request)
        self.assertEqual(OrderStatus.OPEN, submit.order_status)
        exit_fill = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0012"),
            price=Decimal("61000"),
            filled_at=self.close_fill_at,
            fee=Decimal("0.01"),
            fee_currency="USDT",
            liquidity_role="TAKER",
        )
        flat_position = broker.observe_position_after_close(
            request,
            source_position,
            observed_at=self.flat_observed_at,
        )
        funding = produce_paper_zero_funding_evidence(
            plan,
            flat_position,
            calculated_at=self.flat_observed_at,
        )
        outcome = build_trade_result(
            plan,
            current_lifecycle_state=close_outcome.next_state,
            exit_authority=close_outcome.position_action,
            entry_order_requests=(entry_request,),
            entry_fills=(entry_fill,),
            exit_order_request=request,
            exit_fills=(exit_fill,),
            final_position=flat_position,
            funding_evidence=funding,
        )
        return {
            "plan": plan,
            "broker": broker,
            "entry_request": entry_request,
            "entry_fill": entry_fill,
            "source_position": source_position,
            "authority": close_outcome.position_action,
            "request": request,
            "exit_fill": exit_fill,
            "flat_position": flat_position,
            "funding": funding,
            "outcome": outcome,
        }

    def _assert_explicit_result(self, evidence, *, emergency=False):
        request = evidence["request"]
        result = evidence["outcome"].trade_result
        expected_role = "EMERGENCY_EXIT" if emergency else "POSITION_EXIT"
        self.assertEqual(expected_role, request.order_role)
        self.assertEqual("MARKET", request.order_type)
        self.assertTrue(request.reduce_only)
        self.assertEqual(Decimal("0.0012"), request.quantity)
        self.assertEqual(Decimal("0.0012"), evidence["exit_fill"].quantity)
        self.assertEqual(request.position_action_id, evidence["exit_fill"].position_action_id)
        self.assertEqual(request.position_id, evidence["exit_fill"].position_id)
        self.assertEqual(expected_role, evidence["exit_fill"].order_role)
        self.assertEqual("0", evidence["flat_position"]["actual_quantity"])
        self.assertEqual("CONSISTENT", evidence["flat_position"]["reconciliation_status"])
        self.assertEqual(PositionEvent.POSITION_CLOSED, evidence["outcome"].event)
        self.assertEqual(PositionLifecycleState.CLOSED, evidence["outcome"].next_state)
        self.assertEqual("funding-allocation-v0.1", result["funding_evidence_profile_version"])
        self.assertEqual(evidence["funding"]["funding_evidence_id"], result["funding_evidence_id"])
        self.assertEqual("ZERO_CONFIRMED", result["funding_evidence_status"])
        self.assertEqual("0.0012", result["entry_quantity"])
        self.assertEqual("0.02", result["total_fees"])
        self.assertEqual(evidence["authority"]["reason_codes"], result["exit_reason_codes"])

    def test_real_ordinary_exit_full_chain_to_canonical_trade_result(self):
        evidence = self._explicit_chain(emergency=False)
        self._assert_explicit_result(evidence, emergency=False)

    def test_real_emergency_exit_full_chain_to_canonical_trade_result(self):
        evidence = self._explicit_chain(emergency=True)
        self._assert_explicit_result(evidence, emergency=True)
        self.assertEqual("EMERGENCY_EXIT", evidence["authority"]["action"])
        self.assertEqual("EMERGENCY_EXIT", evidence["request"].order_role)

    def test_funding_calculated_at_replay_does_not_change_financial_identity(self):
        evidence = self._explicit_chain(emergency=False)
        later_funding = produce_paper_zero_funding_evidence(
            evidence["plan"],
            evidence["flat_position"],
            calculated_at=self.flat_observed_at + timedelta(seconds=30),
        )
        self.assertNotEqual(evidence["funding"]["calculated_at"], later_funding["calculated_at"])
        self.assertEqual(evidence["funding"]["funding_evidence_id"], later_funding["funding_evidence_id"])
        replay = build_trade_result(
            evidence["plan"],
            current_lifecycle_state=PositionLifecycleState.EXIT_REQUESTED,
            exit_authority=evidence["authority"],
            entry_order_requests=(evidence["entry_request"],),
            entry_fills=(evidence["entry_fill"],),
            exit_order_request=evidence["request"],
            exit_fills=(evidence["exit_fill"],),
            final_position=evidence["flat_position"],
            funding_evidence=later_funding,
        )
        self.assertEqual(
            evidence["outcome"].trade_result["trade_result_id"],
            replay.trade_result["trade_result_id"],
        )

    def test_real_verified_protection_stop_full_trigger_to_trade_result(self):
        plan = self._plan()
        broker = PaperBroker()
        entry_request, entry_fill = self._entry_truth(broker, plan)
        source_position = self._position(lifecycle="OPEN_UNPROTECTED")
        action = build_protect_position_action(
            source_position,
            plan,
            created_at=self.protection_action_at,
            expires_at=self.protection_action_at + timedelta(seconds=60),
        )
        request = prepare_protection_order(
            action,
            plan,
            source_position,
            now=self.protection_request_at,
        )
        submit = broker.submit_order(request)
        queried = broker.query_order(request.client_order_id)
        self.assertIsNotNone(queried)
        verified = interpret_protection_result(
            request,
            ProtectionResultEvidence(
                query_performed=True,
                queried_order=queried,
                submit_result=submit,
            ),
            PositionLifecycleState.OPEN_UNPROTECTED,
        )
        self.assertEqual(PositionEvent.PROTECTION_VERIFIED, verified.event)
        self.assertEqual(PositionLifecycleState.OPEN_PROTECTED, verified.next_state)
        self.assertTrue(verified.protection_verified)

        # Project only the E5-owned lifecycle result. Every E4-owned broker fact
        # remains byte-for-byte the source observation consumed by PROTECT.
        protected_position = dict(source_position)
        protected_position["lifecycle_state"] = verified.next_state.value
        for field in (
            "position_id",
            "actual_quantity",
            "broker_state_observed_at",
            "reconciliation_status",
        ):
            self.assertEqual(source_position[field], protected_position[field])

        exit_fill = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0012"),
            price=Decimal("59390"),
            filled_at=self.protection_fill_at,
            fee=Decimal("0.01"),
            fee_currency="USDT",
            liquidity_role="TAKER",
        )
        flat_position = broker.observe_position_after_close(
            request,
            protected_position,
            observed_at=self.protection_flat_at,
        )
        funding = produce_paper_zero_funding_evidence(
            plan,
            flat_position,
            calculated_at=self.protection_flat_at,
        )
        outcome = build_trade_result(
            plan,
            current_lifecycle_state=verified.next_state,
            exit_authority=action,
            entry_order_requests=(entry_request,),
            entry_fills=(entry_fill,),
            exit_order_request=request,
            exit_fills=(exit_fill,),
            final_position=flat_position,
            funding_evidence=funding,
        )
        result = outcome.trade_result
        self.assertEqual("PROTECTION_STOP", request.order_role)
        self.assertEqual("STOP_MARKET", request.order_type)
        self.assertTrue(request.reduce_only)
        self.assertEqual("0", flat_position["actual_quantity"])
        self.assertEqual(PositionEvent.POSITION_CLOSED, outcome.event)
        self.assertEqual(PositionLifecycleState.CLOSED, outcome.next_state)
        self.assertEqual(["PROTECTION_STOP_FILLED"], result["exit_reason_codes"])
        self.assertEqual(funding["funding_evidence_id"], result["funding_evidence_id"])
        self.assertEqual("ZERO_CONFIRMED", result["funding_evidence_status"])

    def test_positive_outputs_expose_no_provider_private_or_release_authority(self):
        evidence = self._explicit_chain(emergency=False)
        forbidden = {
            "api_key",
            "secret_key",
            "passphrase",
            "credentials",
            "provider_private_endpoint",
            "paper_authorized",
            "shadow_authorized",
            "live_authorized",
        }
        self.assertTrue(forbidden.isdisjoint(evidence["funding"].keys()))
        self.assertTrue(forbidden.isdisjoint(evidence["outcome"].trade_result.keys()))


if __name__ == "__main__":
    unittest.main()
