import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from position import (
    TradeResultBuildError,
    authorize_close_position_action,
    build_protect_position_action,
    build_trade_result,
)
from src.brokers.paper import PaperBroker, ReconciliationRequiredError
from src.execution.close import prepare_close_order
from src.execution.gateway import ExecutionGateway
from src.execution.protection import prepare_protection_order


class GateBCloseTradeResultIntegrationDefinitions(unittest.TestCase):
    """Static E7 definitions over accepted E4/E5 production APIs.

    The explicit EXIT/EMERGENCY_EXIT cases deliberately stop at the current
    real funding-evidence boundary. They must not manufacture an E5-internal
    FundingEvidence instance merely to make the system chain appear complete.
    """

    def setUp(self):
        self.entry_request_at = datetime(2026, 8, 24, 5, 5, 0, tzinfo=timezone.utc)
        self.entry_fill_at = datetime(2026, 8, 24, 5, 5, 10, tzinfo=timezone.utc)
        self.position_observed_at = datetime(2026, 8, 24, 5, 10, 20, tzinfo=timezone.utc)
        self.action_at = datetime(2026, 8, 24, 5, 10, 30, tzinfo=timezone.utc)
        self.request_at = datetime(2026, 8, 24, 5, 10, 40, tzinfo=timezone.utc)
        self.exit_fill_at = datetime(2026, 8, 24, 5, 10, 50, tzinfo=timezone.utc)
        self.flat_observed_at = datetime(2026, 8, 24, 5, 11, 0, tzinfo=timezone.utc)

    def _plan(self, *, direction="LONG"):
        return {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-e7-close-chain-001",
            "risk_decision_id": "risk-e7-close-chain-001",
            "intent_id": "intent-e7-close-chain-001",
            "strategy_id": "strategy-e7-close-chain",
            "strategy_version": "1.0.0",
            "symbol": "BTC_USDT_PERP",
            "direction": direction,
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
            "created_at": "2026-08-24T05:00:00Z",
            "expires_at": "2026-08-24T05:10:00Z",
            "risk_policy_version": "e5-e7-close-chain-policy-v0.1",
        }

    def _source_position(self, *, lifecycle="OPEN_PROTECTED", direction="LONG"):
        return {
            "schema_version": "contracts-v0.1",
            "position_id": "position-e7-close-chain-001",
            "symbol": "BTC_USDT_PERP",
            "side": direction,
            "actual_quantity": "0.0012",
            "average_entry_price": "60000",
            "opened_at": "2026-08-24T05:05:10Z",
            "broker_state_observed_at": "2026-08-24T05:10:20Z",
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": lifecycle,
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }

    def _real_entry_truth(self, broker, plan):
        request = ExecutionGateway().prepare_entry_order(
            plan,
            now=self.entry_request_at,
        )
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

    def _real_explicit_close_to_flat(self, *, emergency=False):
        plan = self._plan()
        broker = PaperBroker()
        entry_request, entry_fill = self._real_entry_truth(broker, plan)
        lifecycle = "EMERGENCY" if emergency else "OPEN_PROTECTED"
        source_position = self._source_position(lifecycle=lifecycle)

        close_outcome = authorize_close_position_action(
            source_position,
            plan,
            action="EMERGENCY_EXIT" if emergency else "EXIT",
            created_at=self.action_at,
            expires_at=self.action_at + timedelta(seconds=60),
        )
        close_request = prepare_close_order(
            close_outcome.position_action,
            plan,
            source_position,
            now=self.request_at,
        )
        broker.submit_order(close_request)
        exit_fill = broker.record_fill(
            close_request.client_order_id,
            quantity=Decimal("0.0012"),
            price=Decimal("61000"),
            filled_at=self.exit_fill_at,
            fee=Decimal("0.01"),
            fee_currency="USDT",
            liquidity_role="TAKER",
        )
        flat_position = broker.observe_position_after_close(
            close_request,
            source_position,
            observed_at=self.flat_observed_at,
        )
        return {
            "plan": plan,
            "entry_request": entry_request,
            "entry_fill": entry_fill,
            "source_position": source_position,
            "close_outcome": close_outcome,
            "close_request": close_request,
            "exit_fill": exit_fill,
            "flat_position": flat_position,
        }

    def _assert_real_explicit_close_reaches_flat_but_not_final_result(self, *, emergency=False):
        evidence = self._real_explicit_close_to_flat(emergency=emergency)
        expected_role = "EMERGENCY_EXIT" if emergency else "POSITION_EXIT"

        self.assertEqual(expected_role, evidence["close_request"].order_role)
        self.assertTrue(evidence["close_request"].reduce_only)
        self.assertEqual(Decimal("0.0012"), evidence["exit_fill"].quantity)
        self.assertEqual(
            evidence["close_request"].position_action_id,
            evidence["exit_fill"].position_action_id,
        )
        self.assertEqual(
            evidence["source_position"]["position_id"],
            evidence["flat_position"]["position_id"],
        )
        self.assertEqual("0.0000", format(Decimal(evidence["flat_position"]["actual_quantity"]), ".4f"))
        self.assertEqual("CONSISTENT", evidence["flat_position"]["reconciliation_status"])

        # The current system has no real provider-neutral Paper/runtime producer
        # for the exact-interval FundingEvidence consumed by E5. Missing evidence
        # must therefore block final TradeResult rather than being treated as zero.
        with self.assertRaises(TradeResultBuildError) as caught:
            build_trade_result(
                evidence["plan"],
                current_lifecycle_state=evidence["close_outcome"].next_state,
                exit_authority=evidence["close_outcome"].position_action,
                entry_order_requests=(evidence["entry_request"],),
                entry_fills=(evidence["entry_fill"],),
                exit_order_request=evidence["close_request"],
                exit_fills=(evidence["exit_fill"],),
                final_position=evidence["flat_position"],
                funding_evidence=None,
            )
        self.assertIn("funding_evidence", caught.exception.message)

    def test_real_ordinary_exit_reaches_authoritative_flat_but_requires_real_funding_source(self):
        self._assert_real_explicit_close_reaches_flat_but_not_final_result(emergency=False)

    def test_real_emergency_exit_reaches_authoritative_flat_but_requires_real_funding_source(self):
        self._assert_real_explicit_close_reaches_flat_but_not_final_result(emergency=True)

    def test_real_protection_stop_fill_has_no_same_position_flat_observer_yet(self):
        plan = self._plan()
        source_position = self._source_position(lifecycle="OPEN_UNPROTECTED")
        action = build_protect_position_action(
            source_position,
            plan,
            created_at=self.action_at,
            expires_at=self.action_at + timedelta(seconds=60),
        )
        request = prepare_protection_order(
            action,
            plan,
            source_position,
            now=self.request_at,
        )
        broker = PaperBroker()
        broker.submit_order(request)
        fill = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0012"),
            price=Decimal("59390"),
            filled_at=self.exit_fill_at,
            fee=Decimal("0.01"),
            fee_currency="USDT",
            liquidity_role="TAKER",
        )
        self.assertEqual("PROTECTION_STOP", fill.order_role)
        self.assertEqual(source_position["position_id"], fill.position_id)

        # E4's current same-position residual/flat observer is intentionally
        # bounded to POSITION_EXIT | EMERGENCY_EXIT and rejects PROTECTION_STOP.
        protected_position = dict(source_position)
        protected_position["lifecycle_state"] = "OPEN_PROTECTED"
        with self.assertRaises(ReconciliationRequiredError) as caught:
            broker.observe_position_after_close(
                request,
                protected_position,
                observed_at=self.flat_observed_at,
            )
        self.assertIn("accepted close-v0.1 order role", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
