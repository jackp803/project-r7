import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.brokers.paper import (
    ExposureLimitError,
    InvalidOrderTransitionError,
    PaperBroker,
    ReconciliationRequiredError,
)
from src.execution.close import prepare_close_order
from src.execution.models import (
    SCHEMA_VERSION,
    OrderRequest,
    OrderStatus,
    Side,
    stable_client_order_id,
    stable_order_request_id,
    stable_position_action_client_order_id,
)


class PaperBrokerCloseTruthTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 24, 5, 10, 30, tzinfo=timezone.utc)

    def _plan(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-paper-close-001",
            "risk_decision_id": "risk-paper-close-001",
            "intent_id": "intent-paper-close-001",
            "strategy_id": "strategy-paper-close",
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
            "expires_at": "2026-08-24T05:00:30Z",
            "risk_policy_version": "e5-close-policy-v0.1",
        }
        values.update(changes)
        return values

    def _position(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "position_id": "position-paper-close-001",
            "symbol": "BTC_USDT_PERP",
            "side": "LONG",
            "actual_quantity": "0.0012",
            "average_entry_price": "60000",
            "opened_at": "2026-08-24T05:05:00Z",
            "broker_state_observed_at": "2026-08-24T05:10:20Z",
            "reconciliation_status": "CONSISTENT",
            "lifecycle_state": "OPEN_PROTECTED",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
        }
        values.update(changes)
        return values

    def _action(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "close_profile_version": "close-v0.1",
            "position_action_id": "posact-paper-close-001",
            "position_id": "position-paper-close-001",
            "action": "EXIT",
            "reason_codes": ["E5_EXIT_REQUESTED"],
            "risk_policy_version": "e5-close-policy-v0.1",
            "trade_plan_id": "plan-paper-close-001",
            "risk_decision_id": "risk-paper-close-001",
            "strategy_id": "strategy-paper-close",
            "strategy_version": "1.0.0",
            "symbol": "BTC_USDT_PERP",
            "position_side": "LONG",
            "source_lifecycle_state": "OPEN_PROTECTED",
            "position_observed_at": "2026-08-24T05:10:20Z",
            "position_reconciliation_status": "CONSISTENT",
            "quantity": "0.0012",
            "quantity_profile_version": "base-asset-v0.1",
            "quantity_unit": "BASE_ASSET",
            "quantity_asset": "BTC",
            "close_order_type": "MARKET",
            "created_at": "2026-08-24T05:10:30Z",
            "expires_at": "2026-08-24T05:11:30Z",
        }
        values.update(changes)
        return values

    def _request(self, *, action=None, plan=None, position=None):
        return prepare_close_order(
            self._action() if action is None else action,
            self._plan() if plan is None else plan,
            self._position() if position is None else position,
            now=self.now,
        )

    def test_partial_close_fill_preserves_lineage_and_truthful_residual(self):
        position = self._position()
        request = self._request(position=position)
        broker = PaperBroker()
        broker.submit_order(request)

        fill = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0004"),
            price=Decimal("60100"),
            filled_at=self.now + timedelta(seconds=10),
            fee=Decimal("0.01"),
            fee_currency="USDT",
            liquidity_role="TAKER",
        )
        result = broker.query_order(request.client_order_id)
        observed = broker.observe_position_after_close(
            request,
            position,
            observed_at=self.now + timedelta(seconds=15),
        )

        self.assertEqual(OrderStatus.PARTIALLY_FILLED, result.order_status)
        self.assertEqual(Decimal("0.0004"), fill.quantity)
        self.assertEqual(request.trade_plan_id, fill.trade_plan_id)
        self.assertEqual(request.position_action_id, fill.position_action_id)
        self.assertEqual(request.position_id, fill.position_id)
        self.assertEqual("POSITION_EXIT", fill.order_role)
        self.assertEqual("0.0008", observed["actual_quantity"])
        self.assertEqual(position["position_id"], observed["position_id"])
        self.assertEqual(position["symbol"], observed["symbol"])
        self.assertEqual("CONSISTENT", observed["reconciliation_status"])
        self.assertEqual("2026-08-24T05:10:45Z", observed["broker_state_observed_at"])
        self.assertEqual(position["lifecycle_state"], observed["lifecycle_state"])
        self.assertNotIn("closed_at", observed)

    def test_full_close_requires_actual_fill_set_and_yields_broker_derived_zero(self):
        position = self._position()
        request = self._request(position=position)
        broker = PaperBroker()
        broker.submit_order(request)
        first = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0004"),
            price=Decimal("60100"),
            filled_at=self.now + timedelta(seconds=10),
        )
        second = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0008"),
            price=Decimal("60120"),
            filled_at=self.now + timedelta(seconds=20),
        )

        result = broker.query_order(request.client_order_id)
        observed = broker.observe_position_after_close(
            request,
            position,
            observed_at=self.now + timedelta(seconds=25),
        )
        fills = broker.query_fills(request.client_order_id)

        self.assertEqual(OrderStatus.FILLED, result.order_status)
        self.assertEqual("0.0004", format(first.quantity, "f"))
        self.assertEqual("0.0008", format(second.quantity, "f"))
        self.assertEqual((first.fill_id, second.fill_id), tuple(fill.fill_id for fill in fills))
        self.assertEqual("0.0000", format(sum((fill.quantity for fill in fills), Decimal("0")), "f")) if False else None
        self.assertEqual(Decimal("0.0012"), sum((fill.quantity for fill in fills), Decimal("0")))
        self.assertEqual("0.0000", format(Decimal(observed["actual_quantity"]), ".4f"))
        self.assertEqual(position["position_id"], observed["position_id"])
        self.assertEqual("CONSISTENT", observed["reconciliation_status"])
        self.assertEqual(position["lifecycle_state"], observed["lifecycle_state"])
        self.assertNotIn("closed_at", observed)
        for fill in fills:
            self.assertEqual(request.position_action_id, fill.position_action_id)
            self.assertEqual(request.position_id, fill.position_id)
            self.assertEqual(request.order_role, fill.order_role)

    def test_filled_order_does_not_override_conflicting_same_position_quantity_truth(self):
        position = self._position()
        request = self._request(position=position)
        broker = PaperBroker()
        broker.submit_order(request)
        broker.record_fill(
            request.client_order_id,
            quantity=request.quantity,
            price=Decimal("60120"),
            filled_at=self.now + timedelta(seconds=10),
        )
        self.assertEqual(OrderStatus.FILLED, broker.query_order(request.client_order_id).order_status)

        conflicting_position = dict(position)
        conflicting_position["actual_quantity"] = "0.0013"
        with self.assertRaises(ReconciliationRequiredError):
            broker.observe_position_after_close(
                request,
                conflicting_position,
                observed_at=self.now + timedelta(seconds=15),
            )

    def test_overfill_and_overclose_remain_rejected(self):
        position = self._position()
        request = self._request(position=position)
        broker = PaperBroker()
        broker.submit_order(request)
        with self.assertRaises(ExposureLimitError):
            broker.record_fill(
                request.client_order_id,
                quantity=Decimal("0.0013"),
                price=Decimal("60100"),
                filled_at=self.now + timedelta(seconds=10),
            )

    def test_short_buy_and_emergency_close_fill_lineage_are_identical_in_semantics(self):
        cases = (
            (
                self._plan(direction="SHORT"),
                self._position(side="SHORT"),
                self._action(position_side="SHORT", position_action_id="posact-paper-close-short"),
                Side.BUY,
                "POSITION_EXIT",
            ),
            (
                self._plan(),
                self._position(lifecycle_state="EMERGENCY"),
                self._action(
                    action="EMERGENCY_EXIT",
                    reason_codes=["E5_EMERGENCY_EXIT_REQUIRED"],
                    source_lifecycle_state="EMERGENCY",
                    position_action_id="posact-paper-close-emergency",
                ),
                Side.SELL,
                "EMERGENCY_EXIT",
            ),
        )
        for plan, position, action, expected_side, expected_role in cases:
            with self.subTest(expected_role=expected_role):
                request = self._request(action=action, plan=plan, position=position)
                broker = PaperBroker()
                broker.submit_order(request)
                fill = broker.record_fill(
                    request.client_order_id,
                    quantity=Decimal("0.0002"),
                    price=Decimal("60050"),
                    filled_at=self.now + timedelta(seconds=10),
                )
                self.assertEqual(expected_side, request.side)
                self.assertEqual(expected_role, request.order_role)
                self.assertEqual(request.trade_plan_id, fill.trade_plan_id)
                self.assertEqual(request.position_action_id, fill.position_action_id)
                self.assertEqual(request.position_id, fill.position_id)
                self.assertEqual(expected_role, fill.order_role)

    def test_query_fills_preserves_order_and_lineage(self):
        request = self._request()
        broker = PaperBroker()
        broker.submit_order(request)
        first = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0003"),
            price=Decimal("60090"),
            filled_at=self.now + timedelta(seconds=5),
        )
        second = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0002"),
            price=Decimal("60100"),
            filled_at=self.now + timedelta(seconds=8),
        )
        queried = broker.query_fills(request.client_order_id)
        self.assertEqual((first, second), queried)
        for fill in queried:
            self.assertEqual(request.position_action_id, fill.position_action_id)
            self.assertEqual(request.position_id, fill.position_id)
            self.assertEqual(request.order_role, fill.order_role)

    def test_ambiguous_close_submit_cannot_be_presented_as_definitively_flat(self):
        position = self._position()
        request = self._request(position=position)
        broker = PaperBroker(ambiguous_outcomes={request.client_order_id: True})
        submit = broker.submit_order(request)
        self.assertEqual(OrderStatus.RECONCILIATION_REQUIRED, submit.order_status)
        broker.record_fill(
            request.client_order_id,
            quantity=request.quantity,
            price=Decimal("60120"),
            filled_at=self.now + timedelta(seconds=10),
        )
        with self.assertRaises(ReconciliationRequiredError):
            broker.observe_position_after_close(
                request,
                position,
                observed_at=self.now + timedelta(seconds=15),
            )

    def test_other_same_symbol_fill_after_source_observation_blocks_definitive_truth(self):
        position = self._position()
        close_request = self._request(position=position)
        broker = PaperBroker()
        broker.submit_order(close_request)

        other_client_id = stable_client_order_id("plan-other", "entry-after-close-source")
        other = OrderRequest(
            schema_version=SCHEMA_VERSION,
            order_request_id=stable_order_request_id(other_client_id),
            trade_plan_id="plan-other",
            client_order_id=other_client_id,
            symbol="BTC_USDT_PERP",
            side=Side.BUY,
            order_type="MARKET",
            quantity=Decimal("0.0001"),
            quantity_profile_version="base-asset-v0.1",
            quantity_unit="BASE_ASSET",
            quantity_asset="BTC",
            created_at=self.now + timedelta(seconds=1),
        )
        broker.submit_order(other)
        broker.record_fill(
            other.client_order_id,
            quantity=Decimal("0.0001"),
            price=Decimal("60010"),
            filled_at=self.now + timedelta(seconds=2),
        )
        broker.record_fill(
            close_request.client_order_id,
            quantity=Decimal("0.0004"),
            price=Decimal("60100"),
            filled_at=self.now + timedelta(seconds=10),
        )

        with self.assertRaises(ReconciliationRequiredError):
            broker.observe_position_after_close(
                close_request,
                position,
                observed_at=self.now + timedelta(seconds=15),
            )

    def test_terminal_and_reconciliation_safety_remain_compatible(self):
        request = self._request()
        broker = PaperBroker()
        broker.submit_order(request)
        canceled = broker.cancel_order(
            request.client_order_id,
            observed_at=self.now + timedelta(seconds=3),
        )
        self.assertEqual(OrderStatus.CANCELED, canceled.order_status)
        with self.assertRaises(InvalidOrderTransitionError):
            broker.record_fill(
                request.client_order_id,
                quantity=Decimal("0.0001"),
                price=Decimal("60050"),
                filled_at=self.now + timedelta(seconds=4),
            )
        reconciliation = broker.reconcile(
            request,
            order_snapshot=broker.query_order(request.client_order_id),
            position_snapshot=broker.query_position(request.symbol),
        )
        self.assertEqual(OrderStatus.CANCELED, reconciliation.resolved_status)
        self.assertFalse(reconciliation.retry_allowed)
        self.assertIsNone(reconciliation.retry_token)

    def test_legacy_entry_and_protection_fill_lineage_remain_compatible(self):
        entry_client = stable_client_order_id("plan-entry-legacy", "entry")
        entry = OrderRequest(
            schema_version=SCHEMA_VERSION,
            order_request_id=stable_order_request_id(entry_client),
            trade_plan_id="plan-entry-legacy",
            client_order_id=entry_client,
            symbol="BTC_USDT_PERP",
            side=Side.BUY,
            order_type="MARKET",
            quantity=Decimal("0.001"),
            quantity_profile_version="base-asset-v0.1",
            quantity_unit="BASE_ASSET",
            quantity_asset="BTC",
            created_at=self.now,
        )
        broker = PaperBroker()
        broker.submit_order(entry)
        entry_fill = broker.record_fill(
            entry.client_order_id,
            quantity=Decimal("0.0002"),
            price=Decimal("60000"),
            filled_at=self.now + timedelta(seconds=1),
        )
        self.assertIsNone(entry_fill.position_action_id)
        self.assertIsNone(entry_fill.position_id)
        self.assertIsNone(entry_fill.order_role)

        protection_client = stable_position_action_client_order_id(
            "posact-protection-compat",
            "PROTECTION_STOP",
        )
        protection = OrderRequest(
            schema_version=SCHEMA_VERSION,
            order_request_id=stable_order_request_id(protection_client),
            trade_plan_id="plan-protection-compat",
            client_order_id=protection_client,
            symbol="BTC_USDT_PERP",
            side=Side.SELL,
            order_type="STOP_MARKET",
            quantity=Decimal("0.001"),
            quantity_profile_version="base-asset-v0.1",
            quantity_unit="BASE_ASSET",
            quantity_asset="BTC",
            created_at=self.now,
            authorization_type="POSITION_ACTION",
            position_action_id="posact-protection-compat",
            position_id="position-protection-compat",
            risk_decision_id="risk-protection-compat",
            order_role="PROTECTION_STOP",
            stop_price=Decimal("59400"),
            reduce_only=True,
        )
        broker2 = PaperBroker()
        broker2.submit_order(protection)
        protection_fill = broker2.record_fill(
            protection.client_order_id,
            quantity=Decimal("0.0002"),
            price=Decimal("59390"),
            filled_at=self.now + timedelta(seconds=1),
        )
        self.assertEqual("posact-protection-compat", protection_fill.position_action_id)
        self.assertEqual("position-protection-compat", protection_fill.position_id)
        self.assertEqual("PROTECTION_STOP", protection_fill.order_role)

    def test_close_fill_and_position_truth_introduce_no_provider_native_or_credential_fields(self):
        position = self._position()
        request = self._request(position=position)
        broker = PaperBroker()
        broker.submit_order(request)
        fill = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0004"),
            price=Decimal("60100"),
            filled_at=self.now + timedelta(seconds=10),
        )
        observed = broker.observe_position_after_close(
            request,
            position,
            observed_at=self.now + timedelta(seconds=15),
        )
        forbidden = {
            "sz",
            "instId",
            "clOrdId",
            "ctVal",
            "lotSz",
            "api_key",
            "secret_key",
            "passphrase",
            "credentials",
        }
        self.assertTrue(forbidden.isdisjoint(vars(request)))
        self.assertTrue(forbidden.isdisjoint(vars(fill)))
        self.assertTrue(forbidden.isdisjoint(observed))


if __name__ == "__main__":
    unittest.main()
