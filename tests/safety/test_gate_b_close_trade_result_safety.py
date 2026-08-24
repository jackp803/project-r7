import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from position import TradeResultBuildError, authorize_close_position_action, build_trade_result
from src.brokers.paper import PaperBroker
from src.execution.close import prepare_close_order
from src.execution.gateway import ExecutionGateway


class GateBCloseTradeResultSafetyDefinitions(unittest.TestCase):
    """Cross-module fail-closed definitions using real accepted E4/E5 APIs."""

    def setUp(self):
        self.entry_request_at = datetime(2026, 8, 24, 5, 5, 0, tzinfo=timezone.utc)
        self.entry_fill_at = datetime(2026, 8, 24, 5, 5, 10, tzinfo=timezone.utc)
        self.position_observed_at = datetime(2026, 8, 24, 5, 10, 20, tzinfo=timezone.utc)
        self.action_at = datetime(2026, 8, 24, 5, 10, 30, tzinfo=timezone.utc)
        self.request_at = datetime(2026, 8, 24, 5, 10, 40, tzinfo=timezone.utc)
        self.exit_fill_at = datetime(2026, 8, 24, 5, 10, 50, tzinfo=timezone.utc)
        self.final_observed_at = datetime(2026, 8, 24, 5, 11, 0, tzinfo=timezone.utc)

    def _plan(self):
        return {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-e7-close-safety-001",
            "risk_decision_id": "risk-e7-close-safety-001",
            "intent_id": "intent-e7-close-safety-001",
            "strategy_id": "strategy-e7-close-safety",
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
            "risk_policy_version": "e5-e7-close-safety-policy-v0.1",
        }

    def _position(self):
        return {
            "schema_version": "contracts-v0.1",
            "position_id": "position-e7-close-safety-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": "0.0012",
            "average_entry_price": "60000",
            "opened_at": "2026-08-24T05:05:10Z",
            "broker_state_observed_at": "2026-08-24T05:10:20Z",
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": "OPEN_PROTECTED",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }

    def _real_chain(self, *, exit_quantity="0.0012", exit_fee=Decimal("0.01"), fee_currency="USDT"):
        plan = self._plan()
        source_position = self._position()
        broker = PaperBroker()

        entry_request = ExecutionGateway().prepare_entry_order(plan, now=self.entry_request_at)
        broker.submit_order(entry_request)
        entry_fill = broker.record_fill(
            entry_request.client_order_id,
            quantity=Decimal("0.0012"),
            price=Decimal("60000"),
            filled_at=self.entry_fill_at,
            fee=Decimal("0.01"),
            fee_currency="USDT",
            liquidity_role="TAKER",
        )

        close_outcome = authorize_close_position_action(
            source_position,
            plan,
            action="EXIT",
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
            quantity=Decimal(exit_quantity),
            price=Decimal("61000"),
            filled_at=self.exit_fill_at,
            fee=exit_fee,
            fee_currency=fee_currency,
            liquidity_role="TAKER",
        )
        observed = broker.observe_position_after_close(
            close_request,
            source_position,
            observed_at=self.final_observed_at,
        )
        return {
            "plan": plan,
            "source_position": source_position,
            "entry_request": entry_request,
            "entry_fill": entry_fill,
            "close_outcome": close_outcome,
            "close_request": close_request,
            "exit_fill": exit_fill,
            "observed": observed,
        }

    def _build_without_funding(self, evidence, *, final_position=None, exit_fills=None):
        return build_trade_result(
            evidence["plan"],
            current_lifecycle_state=evidence["close_outcome"].next_state,
            exit_authority=evidence["close_outcome"].position_action,
            entry_order_requests=(evidence["entry_request"],),
            entry_fills=(evidence["entry_fill"],),
            exit_order_request=evidence["close_request"],
            exit_fills=(evidence["exit_fill"],) if exit_fills is None else exit_fills,
            final_position=evidence["observed"] if final_position is None else final_position,
            funding_evidence=None,
        )

    def test_real_partial_close_residual_cannot_finalize_trade_result(self):
        evidence = self._real_chain(exit_quantity="0.0004")
        self.assertEqual("0.0008", evidence["observed"]["actual_quantity"])
        with self.assertRaises(TradeResultBuildError) as caught:
            self._build_without_funding(evidence)
        self.assertEqual("QUANTITY_CONSERVATION_FAILED", caught.exception.code)

    def test_real_filled_order_without_authoritative_flat_position_cannot_finalize(self):
        evidence = self._real_chain()
        self.assertEqual("0.0000", format(Decimal(evidence["observed"]["actual_quantity"]), ".4f"))
        nonflat = dict(evidence["source_position"])
        nonflat["broker_state_observed_at"] = "2026-08-24T05:11:00Z"
        with self.assertRaises(TradeResultBuildError) as caught:
            self._build_without_funding(evidence, final_position=nonflat)
        self.assertEqual("FINAL_POSITION_NOT_FLAT", caught.exception.code)

    def test_real_fill_missing_fee_cannot_become_zero_silently(self):
        evidence = self._real_chain(exit_fee=None, fee_currency=None)
        with self.assertRaises(TradeResultBuildError) as caught:
            self._build_without_funding(evidence)
        self.assertEqual("FILL_FEE_MISSING", caught.exception.code)

    def test_real_fill_unsupported_fee_currency_fails_closed(self):
        evidence = self._real_chain(exit_fee=Decimal("0.01"), fee_currency="BTC")
        with self.assertRaises(TradeResultBuildError) as caught:
            self._build_without_funding(evidence)
        self.assertEqual("UNSUPPORTED_FEE_CURRENCY", caught.exception.code)

    def test_duplicate_real_fill_evidence_cannot_finalize(self):
        evidence = self._real_chain()
        with self.assertRaises(TradeResultBuildError) as caught:
            self._build_without_funding(
                evidence,
                exit_fills=(evidence["exit_fill"], evidence["exit_fill"]),
            )
        self.assertEqual("DUPLICATE_FILL_ID", caught.exception.code)


if __name__ == "__main__":
    unittest.main()
