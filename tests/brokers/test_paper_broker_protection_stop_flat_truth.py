import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.brokers.paper import (
    ExposureLimitError,
    PaperBroker,
    ReconciliationRequiredError,
)
from src.execution.close import prepare_close_order
from src.execution.funding import produce_paper_zero_funding_evidence
from src.execution.models import (
    SCHEMA_VERSION,
    ExecutionHealthStatus,
    OrderRequest,
    OrderStatus,
    Side,
    stable_client_order_id,
    stable_order_request_id,
)
from src.execution.protection import prepare_protection_order


class PaperBrokerProtectionStopFlatTruthTests(unittest.TestCase):
    def setUp(self):
        self.protection_now = datetime(2026, 8, 24, 3, 6, 0, tzinfo=timezone.utc)
        self.protected_observed_at = self.protection_now + timedelta(seconds=10)
        self.fill_at = self.protection_now + timedelta(seconds=20)
        self.flat_observed_at = self.protection_now + timedelta(seconds=30)

    def _plan(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-protection-flat-001",
            "risk_decision_id": "risk-protection-flat-001",
            "intent_id": "intent-protection-flat-001",
            "strategy_id": "strategy-protection-flat",
            "strategy_version": "1.0.0",
            "symbol": "BTC_USDT_PERP",
            "direction": "LONG",
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
            "created_at": "2026-08-24T03:00:00Z",
            "expires_at": "2026-08-24T03:00:30Z",
            "risk_policy_version": "e5-protection-flat-policy-v0.1",
        }
        values.update(changes)
        return values

    def _initial_unprotected_position(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "position_id": "position-protection-flat-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": "0.0012",
            "average_entry_price": "60000",
            "opened_at": "2026-08-24T03:05:00Z",
            "broker_state_observed_at": "2026-08-24T03:05:50Z",
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": "OPEN_UNPROTECTED",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }
        values.update(changes)
        return values

    def _protect_action(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "protection_profile_version": "protection-v0.1",
            "position_action_id": "posact-protection-flat-001",
            "trade_plan_id": "plan-protection-flat-001",
            "risk_decision_id": "risk-protection-flat-001",
            "position_id": "position-protection-flat-001",
            "action": "PROTECT",
            "reason_codes": [],
            "risk_policy_version": "e5-protection-flat-policy-v0.1",
            "symbol": "BTC_USDT_PERP",
            "position_side": "LONG",
            "position_observed_at": "2026-08-24T03:05:50Z",
            "position_reconciliation_status": "CONSISTENT",
            "quantity": "0.0012",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
            "protection_instruction": {
                "stop_level": "59400",
                "target_level": "61200",
                "max_hold_seconds": 1800,
            },
            "created_at": "2026-08-24T03:05:55Z",
            "expires_at": "2026-08-24T03:07:00Z",
        }
        values.update(changes)
        return values

    def _protected_source_position(self, **changes):
        values = self._initial_unprotected_position(
            lifecycle_state="OPEN_PROTECTED",
            broker_state_observed_at=self.protected_observed_at.isoformat().replace(
                "+00:00", "Z"
            ),
        )
        values.update(changes)
        return values

    def _protection_request(self, *, plan=None, initial_position=None, action=None):
        return prepare_protection_order(
            self._protect_action() if action is None else action,
            self._plan() if plan is None else plan,
            self._initial_unprotected_position()
            if initial_position is None
            else initial_position,
            now=self.protection_now,
        )

    def _full_protection_stop(self, *, request=None, source_position=None):
        request = self._protection_request() if request is None else request
        source_position = (
            self._protected_source_position()
            if source_position is None
            else source_position
        )
        broker = PaperBroker()
        broker.submit_order(request)
        fill = broker.record_fill(
            request.client_order_id,
            quantity=request.quantity,
            price=Decimal("59390"),
            filled_at=self.fill_at,
            fee=Decimal("0.01"),
            fee_currency="USDT",
            liquidity_role="TAKER",
        )
        flat = broker.observe_position_after_close(
            request,
            source_position,
            observed_at=self.flat_observed_at,
        )
        return broker, request, source_position, fill, flat

    def test_long_full_protection_stop_sell_fill_produces_exact_same_position_flat_truth(self):
        broker, request, source_position, fill, flat = self._full_protection_stop()

        self.assertEqual(Side.SELL, request.side)
        self.assertEqual("PROTECTION_STOP", request.order_role)
        self.assertEqual("STOP_MARKET", request.order_type)
        self.assertTrue(request.reduce_only)
        self.assertEqual(Decimal("59400"), request.stop_price)
        self.assertEqual(OrderStatus.FILLED, broker.query_order(request.client_order_id).order_status)
        self.assertEqual(request.quantity, fill.quantity)
        self.assertEqual(source_position["position_id"], flat["position_id"])
        self.assertEqual(source_position["symbol"], flat["symbol"])
        self.assertEqual("0", flat["actual_quantity"])
        self.assertEqual("CONSISTENT", flat["reconciliation_status"])
        self.assertEqual(
            self.flat_observed_at.isoformat().replace("+00:00", "Z"),
            flat["broker_state_observed_at"],
        )
        self.assertEqual("OPEN_PROTECTED", flat["lifecycle_state"])
        self.assertNotIn("closed_at", flat)

    def test_short_full_protection_stop_buy_fill_produces_flat_truth(self):
        plan = self._plan(direction="SHORT")
        initial = self._initial_unprotected_position(side="SHORT")
        action = self._protect_action(position_side="SHORT")
        request = self._protection_request(
            plan=plan,
            initial_position=initial,
            action=action,
        )
        source = self._protected_source_position(side="SHORT")
        _, request, _, fill, flat = self._full_protection_stop(
            request=request,
            source_position=source,
        )

        self.assertEqual(Side.BUY, request.side)
        self.assertEqual(Side.BUY, fill.side)
        self.assertEqual("0", flat["actual_quantity"])
        self.assertEqual("CONSISTENT", flat["reconciliation_status"])
        self.assertEqual("SHORT", flat["side"])
        self.assertEqual("OPEN_PROTECTED", flat["lifecycle_state"])

    def test_profit_protected_full_stop_closure_is_supported_without_lifecycle_rewrite(self):
        source = self._protected_source_position(lifecycle_state="PROFIT_PROTECTED")
        _, _, _, _, flat = self._full_protection_stop(source_position=source)
        self.assertEqual("0", flat["actual_quantity"])
        self.assertEqual("CONSISTENT", flat["reconciliation_status"])
        self.assertEqual("PROFIT_PROTECTED", flat["lifecycle_state"])
        self.assertNotIn("closed_at", flat)

    def test_request_fill_and_position_lineage_are_exact_and_preserved(self):
        _, request, source, fill, flat = self._full_protection_stop()
        self.assertEqual(request.trade_plan_id, fill.trade_plan_id)
        self.assertEqual(request.position_action_id, fill.position_action_id)
        self.assertEqual(request.position_id, fill.position_id)
        self.assertEqual("PROTECTION_STOP", fill.order_role)
        self.assertEqual(request.symbol, fill.symbol)
        self.assertEqual(request.side, fill.side)
        self.assertEqual(request.position_id, source["position_id"])
        self.assertEqual(request.position_id, flat["position_id"])
        self.assertEqual(request.symbol, source["symbol"])
        self.assertEqual(request.symbol, flat["symbol"])

    def test_full_fill_requires_exact_filled_orderresult_and_quantity_equality(self):
        request = self._protection_request()
        source = self._protected_source_position()
        broker = PaperBroker()
        broker.submit_order(request)
        broker.record_fill(
            request.client_order_id,
            quantity=request.quantity,
            price=Decimal("59390"),
            filled_at=self.fill_at,
        )

        stored = broker._orders[request.client_order_id]
        stored.result = replace(stored.result, order_status=OrderStatus.PARTIALLY_FILLED)
        with self.assertRaises(ReconciliationRequiredError):
            broker.observe_position_after_close(
                request,
                source,
                observed_at=self.flat_observed_at,
            )

        stored.result = replace(
            stored.result,
            order_status=OrderStatus.FILLED,
            filled_quantity=Decimal("0.0011"),
        )
        with self.assertRaises(ReconciliationRequiredError):
            broker.observe_position_after_close(
                request,
                source,
                observed_at=self.flat_observed_at,
            )

    def test_stale_observation_before_latest_protection_fill_fails_closed(self):
        request = self._protection_request()
        source = self._protected_source_position()
        broker = PaperBroker()
        broker.submit_order(request)
        broker.record_fill(
            request.client_order_id,
            quantity=request.quantity,
            price=Decimal("59390"),
            filled_at=self.fill_at,
        )
        with self.assertRaises(ReconciliationRequiredError):
            broker.observe_position_after_close(
                request,
                source,
                observed_at=self.fill_at - timedelta(microseconds=1),
            )

    def test_open_unprotected_source_cannot_prove_protection_triggered_flatness(self):
        request = self._protection_request()
        source = self._protected_source_position(lifecycle_state="OPEN_UNPROTECTED")
        broker = PaperBroker()
        broker.submit_order(request)
        broker.record_fill(
            request.client_order_id,
            quantity=request.quantity,
            price=Decimal("59390"),
            filled_at=self.fill_at,
        )
        with self.assertRaises(ReconciliationRequiredError):
            broker.observe_position_after_close(
                request,
                source,
                observed_at=self.flat_observed_at,
            )

    def test_partial_protection_fill_is_reconciliation_required_not_consistent_residual(self):
        request = self._protection_request()
        source = self._protected_source_position()
        broker = PaperBroker()
        broker.submit_order(request)
        broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0004"),
            price=Decimal("59390"),
            filled_at=self.fill_at,
        )
        self.assertEqual(
            OrderStatus.PARTIALLY_FILLED,
            broker.query_order(request.client_order_id).order_status,
        )
        with self.assertRaises(ReconciliationRequiredError) as caught:
            broker.observe_position_after_close(
                request,
                source,
                observed_at=self.flat_observed_at,
            )
        self.assertIn("residual-protection", str(caught.exception))
        self.assertEqual("0.0012", source["actual_quantity"])
        self.assertEqual("CONSISTENT", source["reconciliation_status"])

    def test_zero_or_open_no_fill_protection_order_cannot_report_flat(self):
        request = self._protection_request()
        source = self._protected_source_position()
        broker = PaperBroker()
        opened = broker.submit_order(request)
        self.assertEqual(OrderStatus.OPEN, opened.order_status)
        self.assertEqual((), broker.query_fills(request.client_order_id))
        with self.assertRaises(ReconciliationRequiredError):
            broker.observe_position_after_close(
                request,
                source,
                observed_at=self.flat_observed_at,
            )

    def test_rejected_canceled_expired_ambiguous_and_degraded_protection_truth_cannot_report_flat(self):
        source = self._protected_source_position()

        rejected_request = self._protection_request()
        rejected = PaperBroker(
            rejected_outcomes={rejected_request.client_order_id: "PAPER_REJECT"}
        )
        rejected.submit_order(rejected_request)
        with self.assertRaises(ReconciliationRequiredError):
            rejected.observe_position_after_close(
                rejected_request,
                source,
                observed_at=self.flat_observed_at,
            )

        for terminal in ("cancel", "expire"):
            with self.subTest(terminal=terminal):
                request = self._protection_request(
                    action=self._protect_action(
                        position_action_id=f"posact-protection-{terminal}"
                    )
                )
                broker = PaperBroker()
                broker.submit_order(request)
                terminal_at = self.protected_observed_at + timedelta(seconds=1)
                if terminal == "cancel":
                    broker.cancel_order(request.client_order_id, observed_at=terminal_at)
                else:
                    broker.expire_order(request.client_order_id, observed_at=terminal_at)
                with self.assertRaises(ReconciliationRequiredError):
                    broker.observe_position_after_close(
                        request,
                        source,
                        observed_at=self.flat_observed_at,
                    )

        ambiguous_request = self._protection_request(
            action=self._protect_action(position_action_id="posact-protection-ambiguous")
        )
        ambiguous = PaperBroker(
            ambiguous_outcomes={ambiguous_request.client_order_id: True}
        )
        submit = ambiguous.submit_order(ambiguous_request)
        self.assertEqual(OrderStatus.RECONCILIATION_REQUIRED, submit.order_status)
        ambiguous.record_fill(
            ambiguous_request.client_order_id,
            quantity=ambiguous_request.quantity,
            price=Decimal("59390"),
            filled_at=self.fill_at,
        )
        with self.assertRaises(ReconciliationRequiredError):
            ambiguous.observe_position_after_close(
                ambiguous_request,
                source,
                observed_at=self.flat_observed_at,
            )

        degraded_request = self._protection_request(
            action=self._protect_action(position_action_id="posact-protection-degraded")
        )
        degraded = PaperBroker()
        degraded.submit_order(degraded_request)
        degraded.record_fill(
            degraded_request.client_order_id,
            quantity=degraded_request.quantity,
            price=Decimal("59390"),
            filled_at=self.fill_at,
        )
        stored = degraded._orders[degraded_request.client_order_id]
        stored.result = replace(
            stored.result,
            execution_health_status=ExecutionHealthStatus.DEGRADED,
        )
        with self.assertRaises(ReconciliationRequiredError):
            degraded.observe_position_after_close(
                degraded_request,
                source,
                observed_at=self.flat_observed_at,
            )

    def test_wrong_protection_order_role_type_reduce_only_or_stop_semantics_fail_closed(self):
        canonical = self._protection_request()
        source = self._protected_source_position()
        cases = (
            replace(canonical, order_role="UNSUPPORTED_ROLE"),
            replace(canonical, order_type="MARKET"),
            replace(canonical, reduce_only=False),
            replace(canonical, stop_price=Decimal("0")),
            replace(canonical, limit_price=Decimal("59300")),
            replace(canonical, time_in_force="GTC"),
        )
        for request in cases:
            with self.subTest(request=request):
                broker = PaperBroker()
                broker.submit_order(request)
                with self.assertRaises(ReconciliationRequiredError):
                    broker.observe_position_after_close(
                        request,
                        source,
                        observed_at=self.flat_observed_at,
                    )

    def test_wrong_side_position_symbol_or_quantity_fails_closed(self):
        canonical = self._protection_request()
        source = self._protected_source_position()
        cases = (
            replace(canonical, side=Side.BUY),
            replace(canonical, position_id="position-other"),
            replace(canonical, symbol="ETH_USDT_PERP"),
            replace(canonical, quantity=Decimal("0.0011")),
        )
        for request in cases:
            with self.subTest(request=request):
                broker = PaperBroker()
                broker.submit_order(request)
                with self.assertRaises(ReconciliationRequiredError):
                    broker.observe_position_after_close(
                        request,
                        source,
                        observed_at=self.flat_observed_at,
                    )

    def test_tampered_fill_action_plan_symbol_or_side_lineage_fails_closed(self):
        mutations = {
            "action": {"position_action_id": "posact-other"},
            "plan": {"trade_plan_id": "plan-other"},
            "symbol": {"symbol": "ETH_USDT_PERP"},
            "side": {"side": Side.BUY},
        }
        for name, changes in mutations.items():
            with self.subTest(name=name):
                request = self._protection_request()
                source = self._protected_source_position()
                broker = PaperBroker()
                broker.submit_order(request)
                fill = broker.record_fill(
                    request.client_order_id,
                    quantity=request.quantity,
                    price=Decimal("59390"),
                    filled_at=self.fill_at,
                )
                broker._orders[request.client_order_id].fills[0] = replace(
                    fill,
                    **changes,
                )
                with self.assertRaises(ReconciliationRequiredError):
                    broker.observe_position_after_close(
                        request,
                        source,
                        observed_at=self.flat_observed_at,
                    )

    def test_overfill_cannot_produce_flat_truth(self):
        request = self._protection_request()
        broker = PaperBroker()
        broker.submit_order(request)
        with self.assertRaises(ExposureLimitError):
            broker.record_fill(
                request.client_order_id,
                quantity=request.quantity + Decimal("0.0001"),
                price=Decimal("59390"),
                filled_at=self.fill_at,
            )
        self.assertEqual((), broker.query_fills(request.client_order_id))

    def test_interfering_same_symbol_fill_after_source_observation_fails_closed(self):
        request = self._protection_request()
        source = self._protected_source_position()
        broker = PaperBroker()
        broker.submit_order(request)

        other_client = stable_client_order_id("plan-interfering-entry", "entry")
        other = OrderRequest(
            schema_version=SCHEMA_VERSION,
            order_request_id=stable_order_request_id(other_client),
            trade_plan_id="plan-interfering-entry",
            client_order_id=other_client,
            symbol=request.symbol,
            side=Side.BUY,
            order_type="MARKET",
            quantity=Decimal("0.0001"),
            quantity_profile_version="base-asset-v0.1",
            quantity_unit="BASE_ASSET",
            quantity_asset="BTC",
            created_at=self.protected_observed_at + timedelta(seconds=1),
        )
        broker.submit_order(other)
        broker.record_fill(
            other.client_order_id,
            quantity=other.quantity,
            price=Decimal("60010"),
            filled_at=self.protected_observed_at + timedelta(seconds=2),
        )
        broker.record_fill(
            request.client_order_id,
            quantity=request.quantity,
            price=Decimal("59390"),
            filled_at=self.fill_at,
        )
        with self.assertRaises(ReconciliationRequiredError):
            broker.observe_position_after_close(
                request,
                source,
                observed_at=self.flat_observed_at,
            )

    def _close_action(self, *, emergency=False):
        return {
            "schema_version": "contracts-v0.1",
            "close_profile_version": "close-v0.1",
            "position_action_id": (
                "posact-close-emergency-compat"
                if emergency
                else "posact-close-ordinary-compat"
            ),
            "position_id": "position-protection-flat-001",
            "action": "EMERGENCY_EXIT" if emergency else "EXIT",
            "reason_codes": [
                "E5_EMERGENCY_EXIT_REQUIRED" if emergency else "E5_EXIT_REQUESTED"
            ],
            "risk_policy_version": "e5-protection-flat-policy-v0.1",
            "trade_plan_id": "plan-protection-flat-001",
            "risk_decision_id": "risk-protection-flat-001",
            "strategy_id": "strategy-protection-flat",
            "strategy_version": "1.0.0",
            "symbol": "BTC_USDT_PERP",
            "position_side": "LONG",
            "source_lifecycle_state": "EMERGENCY" if emergency else "OPEN_PROTECTED",
            "position_observed_at": "2026-08-24T03:06:40Z",
            "position_reconciliation_status": "CONSISTENT",
            "quantity": "0.0012",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
            "close_order_type": "MARKET",
            "created_at": "2026-08-24T03:06:50Z",
            "expires_at": "2026-08-24T03:07:50Z",
        }

    def _close_source(self, *, emergency=False):
        return self._protected_source_position(
            lifecycle_state="EMERGENCY" if emergency else "OPEN_PROTECTED",
            broker_state_observed_at="2026-08-24T03:06:40Z",
        )

    def test_existing_position_exit_partial_and_emergency_full_observation_semantics_remain_unchanged(self):
        ordinary_source = self._close_source()
        ordinary_request = prepare_close_order(
            self._close_action(),
            self._plan(),
            ordinary_source,
            now=datetime(2026, 8, 24, 3, 6, 50, tzinfo=timezone.utc),
        )
        ordinary = PaperBroker()
        ordinary.submit_order(ordinary_request)
        ordinary.record_fill(
            ordinary_request.client_order_id,
            quantity=Decimal("0.0004"),
            price=Decimal("60100"),
            filled_at=datetime(2026, 8, 24, 3, 7, 0, tzinfo=timezone.utc),
        )
        residual = ordinary.observe_position_after_close(
            ordinary_request,
            ordinary_source,
            observed_at=datetime(2026, 8, 24, 3, 7, 5, tzinfo=timezone.utc),
        )
        self.assertEqual("0.0008", residual["actual_quantity"])
        self.assertEqual("CONSISTENT", residual["reconciliation_status"])

        emergency_source = self._close_source(emergency=True)
        emergency_request = prepare_close_order(
            self._close_action(emergency=True),
            self._plan(),
            emergency_source,
            now=datetime(2026, 8, 24, 3, 6, 50, tzinfo=timezone.utc),
        )
        emergency = PaperBroker()
        emergency.submit_order(emergency_request)
        emergency.record_fill(
            emergency_request.client_order_id,
            quantity=emergency_request.quantity,
            price=Decimal("59900"),
            filled_at=datetime(2026, 8, 24, 3, 7, 0, tzinfo=timezone.utc),
        )
        flat = emergency.observe_position_after_close(
            emergency_request,
            emergency_source,
            observed_at=datetime(2026, 8, 24, 3, 7, 5, tzinfo=timezone.utc),
        )
        self.assertIsInstance(flat["actual_quantity"], str)
        self.assertEqual(Decimal("0"), Decimal(flat["actual_quantity"]))
        self.assertEqual("EMERGENCY", flat["lifecycle_state"])

    def test_funding_producer_and_entry_path_remain_compatible(self):
        _, _, _, _, flat = self._full_protection_stop()
        evidence = produce_paper_zero_funding_evidence(
            self._plan(),
            flat,
            calculated_at=self.flat_observed_at,
        )
        self.assertEqual("ZERO_CONFIRMED", evidence["status"])
        self.assertEqual("0", evidence["funding_cost"])
        self.assertEqual(flat["position_id"], evidence["position_id"])

        entry_client = stable_client_order_id("plan-entry-compat-flat", "entry")
        entry = OrderRequest(
            schema_version=SCHEMA_VERSION,
            order_request_id=stable_order_request_id(entry_client),
            trade_plan_id="plan-entry-compat-flat",
            client_order_id=entry_client,
            symbol="BTC_USDT_PERP",
            side=Side.BUY,
            order_type="MARKET",
            quantity=Decimal("0.001"),
            quantity_profile_version="base-asset-v0.1",
            quantity_unit="BASE_ASSET",
            quantity_asset="BTC",
            created_at=self.protection_now,
        )
        broker = PaperBroker()
        opened = broker.submit_order(entry)
        fill = broker.record_fill(
            entry.client_order_id,
            quantity=Decimal("0.0004"),
            price=Decimal("60000"),
            filled_at=self.protection_now + timedelta(seconds=1),
        )
        self.assertEqual(OrderStatus.OPEN, opened.order_status)
        self.assertEqual(
            OrderStatus.PARTIALLY_FILLED,
            broker.query_order(entry.client_order_id).order_status,
        )
        self.assertIsNone(fill.position_action_id)
        self.assertIsNone(fill.position_id)
        self.assertIsNone(fill.order_role)


if __name__ == "__main__":
    unittest.main()
