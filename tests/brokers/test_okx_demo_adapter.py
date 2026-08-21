import base64
import hashlib
import hmac
import re
import unittest
from datetime import datetime, timezone
from decimal import Decimal

from src.brokers.okx_demo import (
    OKXAccountConfigSnapshot,
    OKXCredentials,
    OKXDemoAdapter,
    OKXDemoAdapterConfig,
    OKXDemoConfigurationError,
    OKXPendingOrderFact,
    OKXPositionFact,
    OKXPrerequisiteError,
    OKXPrerequisiteSnapshot,
    OKXProtocolError,
    OKXReconciliationError,
    materialize_demo_market_order,
    parse_fills_response,
    parse_order_lookup_response,
    prepare_demo_private_request,
    stable_okx_cl_ord_id,
    validate_demo_prerequisites,
)
from src.brokers.okx_sizing import OKXInstrumentMetadata, size_okx_market_entry
from src.execution.models import (
    SCHEMA_VERSION,
    OrderRequest,
    OrderStatus,
    Side,
    stable_client_order_id,
    stable_order_request_id,
)


NOW = datetime(2026, 8, 21, 5, 0, tzinfo=timezone.utc)
TIMESTAMP = "2026-08-21T05:00:00.000Z"
FAKE_API_KEY = "fakeApiKeyForLocalTestOnly"
FAKE_SECRET = "fakeSecretForLocalTestOnly"
FAKE_PASSPHRASE = "fakePassphraseForLocalTestOnly"


class _FakeTransport:
    def __init__(self, effects=()):
        self.effects = list(effects)
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        if not self.effects:
            raise AssertionError("fake transport has no configured effect")
        effect = self.effects.pop(0)
        if isinstance(effect, BaseException):
            raise effect
        return effect


def _request(*, side=Side.BUY, quantity="0.010"):
    client_id = stable_client_order_id("plan-okx-demo-001", "entry")
    return OrderRequest(
        schema_version=SCHEMA_VERSION,
        order_request_id=stable_order_request_id(client_id),
        trade_plan_id="plan-okx-demo-001",
        client_order_id=client_id,
        symbol="BTC_USDT_PERP",
        side=side,
        order_type="MARKET",
        quantity=Decimal(quantity),
        quantity_profile_version="base-asset-v0.1",
        quantity_unit="BASE_ASSET",
        quantity_asset="BTC",
        created_at=NOW,
    )


def _metadata(now=NOW):
    return OKXInstrumentMetadata(
        provider="OKX",
        canonical_symbol="BTC_USDT_PERP",
        instrument_id="BTC-USDT-SWAP",
        inst_type="SWAP",
        ct_val=Decimal("0.001"),
        ct_mult=Decimal("1"),
        ct_val_ccy="BTC",
        ct_type="linear",
        lot_sz=Decimal("1"),
        min_sz=Decimal("1"),
        tick_sz=Decimal("0.1"),
        state="live",
        observed_at=now,
        metadata_ref="fake-public:btc-usdt-swap:001",
    )


def _prerequisites(*, account_level="2", position_mode="net_mode", positions=(), pending=()):
    return OKXPrerequisiteSnapshot(
        account=OKXAccountConfigSnapshot(
            account_level=account_level,
            position_mode=position_mode,
            uid="fake-sub-uid",
            main_uid="fake-main-uid",
        ),
        positions=tuple(positions),
        pending_orders=tuple(pending),
    )


def _config(*, position_mode="net_mode", order_not_found_codes=frozenset()):
    return OKXDemoAdapterConfig(
        expected_account_level="2",
        expected_position_mode=position_mode,
        order_not_found_codes=order_not_found_codes,
    )


def _materialization(*, side=Side.BUY, quantity="0.010", position_mode="net_mode"):
    request = _request(side=side, quantity=quantity)
    metadata = _metadata()
    sizing = size_okx_market_entry(request, metadata, now=NOW)
    prerequisites = _prerequisites(position_mode=position_mode)
    materialized = materialize_demo_market_order(
        request,
        sizing,
        metadata,
        prerequisites,
        config=_config(position_mode=position_mode),
        now=NOW,
    )
    return request, metadata, sizing, prerequisites, materialized


def _adapter(effects, *, position_mode="net_mode", order_not_found_codes=frozenset()):
    transport = _FakeTransport(effects)
    adapter = OKXDemoAdapter(
        credentials=OKXCredentials(
            api_key=FAKE_API_KEY,
            secret_key=FAKE_SECRET,
            passphrase=FAKE_PASSPHRASE,
        ),
        config=_config(
            position_mode=position_mode,
            order_not_found_codes=order_not_found_codes,
        ),
        transport=transport,
        timestamp_provider=lambda: TIMESTAMP,
    )
    return adapter, transport


class OKXDemoAdapterTests(unittest.TestCase):
    def test_signature_and_demo_headers_use_fake_runtime_credentials(self):
        body = {
            "instId": "BTC-USDT-SWAP",
            "tdMode": "isolated",
            "side": "buy",
            "posSide": "net",
            "ordType": "market",
            "sz": "10",
            "clOrdId": "R7ABC123",
        }
        prepared = prepare_demo_private_request(
            OKXCredentials(FAKE_API_KEY, FAKE_SECRET, FAKE_PASSPHRASE),
            method="POST",
            path="/api/v5/trade/order",
            timestamp=TIMESTAMP,
            body=body,
        )
        prehash = TIMESTAMP + "POST" + "/api/v5/trade/order" + prepared.body_text
        expected = base64.b64encode(
            hmac.new(FAKE_SECRET.encode(), prehash.encode(), hashlib.sha256).digest()
        ).decode("ascii")
        self.assertEqual(prepared.headers["OK-ACCESS-SIGN"], expected)
        self.assertEqual(prepared.headers["OK-ACCESS-KEY"], FAKE_API_KEY)
        self.assertEqual(prepared.headers["OK-ACCESS-PASSPHRASE"], FAKE_PASSPHRASE)
        self.assertEqual(prepared.headers["x-simulated-trading"], "1")
        self.assertNotIn(FAKE_SECRET, repr(prepared))

    def test_demo_adapter_structurally_rejects_production_mode_or_other_base_url(self):
        with self.assertRaises(OKXDemoConfigurationError):
            OKXDemoAdapterConfig(
                expected_account_level="2",
                expected_position_mode="net_mode",
                environment="production",
            )
        with self.assertRaises(OKXDemoConfigurationError):
            OKXDemoAdapterConfig(
                expected_account_level="2",
                expected_position_mode="net_mode",
                rest_base_url="https://example.invalid",
            )

    def test_stable_provider_clordid_is_legal_and_traceable(self):
        internal = _request().client_order_id
        first = stable_okx_cl_ord_id(internal)
        second = stable_okx_cl_ord_id(internal)
        self.assertEqual(first, second)
        self.assertEqual(first.internal_client_order_id, internal)
        self.assertRegex(first.provider_cl_ord_id, re.compile(r"^[A-Za-z0-9]{1,32}$"))
        self.assertLessEqual(len(first.provider_cl_ord_id), 32)

    def test_market_isolated_payload_uses_sizing_audit_contracts_not_canonical_btc(self):
        request, _, sizing, _, materialized = _materialization()
        self.assertEqual(request.quantity, Decimal("0.010"))
        self.assertEqual(sizing.provider_requested_contract_quantity, Decimal("10"))
        self.assertEqual(materialized.body["instId"], "BTC-USDT-SWAP")
        self.assertEqual(materialized.body["tdMode"], "isolated")
        self.assertEqual(materialized.body["side"], "buy")
        self.assertEqual(materialized.body["posSide"], "net")
        self.assertEqual(materialized.body["ordType"], "market")
        self.assertEqual(materialized.body["sz"], "10")
        self.assertNotEqual(materialized.body["sz"], format(request.quantity, "f"))
        self.assertLessEqual(materialized.effective_canonical_quantity, request.quantity)

    def test_long_short_mode_maps_new_long_and_short_position_side_mechanically(self):
        _, _, _, _, long_order = _materialization(
            side=Side.BUY, position_mode="long_short_mode"
        )
        _, _, _, _, short_order = _materialization(
            side=Side.SELL, position_mode="long_short_mode"
        )
        self.assertEqual(long_order.body["side"], "buy")
        self.assertEqual(long_order.body["posSide"], "long")
        self.assertEqual(short_order.body["side"], "sell")
        self.assertEqual(short_order.body["posSide"], "short")

    def test_account_or_position_mode_mismatch_fails_closed(self):
        config = _config(position_mode="net_mode")
        with self.assertRaises(OKXPrerequisiteError):
            validate_demo_prerequisites(
                _prerequisites(account_level="3", position_mode="net_mode"),
                config=config,
            )
        with self.assertRaises(OKXPrerequisiteError):
            validate_demo_prerequisites(
                _prerequisites(account_level="2", position_mode="long_short_mode"),
                config=config,
            )

    def test_existing_position_or_pending_order_blocks_new_exposure(self):
        position = OKXPositionFact(
            instrument_id="BTC-USDT-SWAP",
            margin_mode="isolated",
            position_side="net",
            provider_contract_quantity=Decimal("1"),
        )
        with self.assertRaises(OKXPrerequisiteError):
            validate_demo_prerequisites(
                _prerequisites(positions=(position,)), config=_config()
            )
        pending = OKXPendingOrderFact(
            instrument_id="BTC-USDT-SWAP",
            order_id="fake-order",
            client_order_id="fake-client-order",
            state="live",
        )
        with self.assertRaises(OKXPrerequisiteError):
            validate_demo_prerequisites(
                _prerequisites(pending=(pending,)), config=_config()
            )

    def test_success_ack_is_pending_not_fill_truth(self):
        _, _, _, _, materialized = _materialization()
        response = {
            "code": "0",
            "msg": "",
            "data": [
                {
                    "clOrdId": materialized.provider_cl_ord_id,
                    "ordId": "fake-okx-order-1",
                    "sCode": "0",
                    "sMsg": "",
                }
            ],
        }
        adapter, transport = _adapter((response,))
        result = adapter.submit_entry(materialized, observed_at=NOW)
        self.assertEqual(result.order_status, OrderStatus.PENDING)
        self.assertEqual(result.filled_quantity, Decimal("0"))
        self.assertEqual(result.requested_quantity, materialized.effective_canonical_quantity)
        self.assertEqual(transport.requests[0].headers["x-simulated-trading"], "1")

    def test_timeout_is_reconciliation_required_and_repeated_submit_is_not_sent_twice(self):
        _, _, _, _, materialized = _materialization()
        adapter, transport = _adapter((TimeoutError("fake timeout"),))
        first = adapter.submit_entry(materialized, observed_at=NOW)
        second = adapter.submit_entry(materialized, observed_at=NOW)
        self.assertEqual(first.order_status, OrderStatus.RECONCILIATION_REQUIRED)
        self.assertEqual(second, first)
        self.assertEqual(len(transport.requests), 1)

    def test_order_status_mapping_preserves_partial_fill_and_unknown_fails_closed(self):
        _, _, _, _, materialized = _materialization()
        partial = {
            "code": "0",
            "data": [
                {
                    "instId": "BTC-USDT-SWAP",
                    "clOrdId": materialized.provider_cl_ord_id,
                    "ordId": "fake-okx-order-2",
                    "state": "partially_filled",
                    "sz": "10",
                    "accFillSz": "4",
                    "avgPx": "100000",
                }
            ],
        }
        lookup = parse_order_lookup_response(
            partial, materialized, observed_at=NOW, config=_config()
        )
        self.assertTrue(lookup.found)
        self.assertEqual(lookup.result.order_status, OrderStatus.PARTIALLY_FILLED)
        self.assertEqual(lookup.result.filled_quantity, Decimal("0.004"))

        unknown = {
            "code": "0",
            "data": [
                {
                    "instId": "BTC-USDT-SWAP",
                    "clOrdId": materialized.provider_cl_ord_id,
                    "ordId": "fake-okx-order-3",
                    "state": "future_unknown_state",
                    "sz": "10",
                    "accFillSz": "0",
                    "avgPx": "",
                }
            ],
        }
        unknown_lookup = parse_order_lookup_response(
            unknown, materialized, observed_at=NOW, config=_config()
        )
        self.assertEqual(
            unknown_lookup.result.order_status, OrderStatus.RECONCILIATION_REQUIRED
        )

    def test_contradictory_provider_order_size_fails_closed(self):
        _, _, _, _, materialized = _materialization()
        contradictory = {
            "code": "0",
            "data": [
                {
                    "instId": "BTC-USDT-SWAP",
                    "clOrdId": materialized.provider_cl_ord_id,
                    "ordId": "fake-okx-order-4",
                    "state": "live",
                    "sz": "11",
                    "accFillSz": "0",
                    "avgPx": "",
                }
            ],
        }
        with self.assertRaises(OKXReconciliationError):
            parse_order_lookup_response(
                contradictory, materialized, observed_at=NOW, config=_config()
            )

    def test_fill_contracts_normalize_to_canonical_btc_without_conflation(self):
        _, _, _, _, materialized = _materialization()
        response = {
            "code": "0",
            "data": [
                {
                    "instId": "BTC-USDT-SWAP",
                    "clOrdId": materialized.provider_cl_ord_id,
                    "ordId": "fake-okx-order-5",
                    "tradeId": "fake-trade-1",
                    "fillSz": "4",
                    "fillPx": "100000",
                    "fillTime": "1787288400000",
                    "fee": "-0.01",
                    "feeCcy": "USDT",
                }
            ],
        }
        fills = parse_fills_response(response, materialized)
        self.assertEqual(len(fills), 1)
        self.assertEqual(fills[0].quantity, Decimal("0.004"))
        self.assertNotEqual(fills[0].quantity, Decimal("4"))

    def test_reconciliation_queries_order_position_fill_and_pending_before_retry(self):
        _, _, _, _, materialized = _materialization()
        effects = (
            TimeoutError("fake submit timeout"),
            {"code": "51603", "msg": "fake explicit order absence", "data": []},
            {"code": "0", "msg": "", "data": []},
            {"code": "0", "msg": "", "data": []},
            {"code": "0", "msg": "", "data": []},
            {
                "code": "0",
                "msg": "",
                "data": [
                    {
                        "clOrdId": materialized.provider_cl_ord_id,
                        "ordId": "fake-okx-order-retry",
                        "sCode": "0",
                        "sMsg": "",
                    }
                ],
            },
        )
        adapter, transport = _adapter(
            effects, order_not_found_codes=frozenset({"51603"})
        )
        ambiguous = adapter.submit_entry(materialized, observed_at=NOW)
        self.assertEqual(ambiguous.order_status, OrderStatus.RECONCILIATION_REQUIRED)

        evidence = adapter.reconcile_ambiguous(materialized, observed_at=NOW)
        self.assertTrue(evidence.retry_allowed)
        self.assertEqual(
            evidence.reason, "EXPLICIT_ORDER_ABSENCE_AND_NO_PROVIDER_EXPOSURE"
        )
        paths = [request.request_path.split("?", 1)[0] for request in transport.requests]
        self.assertEqual(
            paths[:5],
            [
                "/api/v5/trade/order",
                "/api/v5/trade/order",
                "/api/v5/account/positions",
                "/api/v5/trade/fills",
                "/api/v5/trade/orders-pending",
            ],
        )
        retried = adapter.retry_entry(materialized, evidence, observed_at=NOW)
        self.assertEqual(retried.order_status, OrderStatus.PENDING)
        self.assertEqual(len(transport.requests), 6)

    def test_no_explicit_order_absence_semantics_means_no_retry(self):
        _, _, _, _, materialized = _materialization()
        adapter, _ = _adapter((TimeoutError("fake timeout"),))
        adapter.submit_entry(materialized, observed_at=NOW)
        with self.assertRaises(OKXReconciliationError):
            # Non-zero provider code is not assumed to mean absence unless the
            # exact code is explicitly configured from current provider authority.
            parse_order_lookup_response(
                {"code": "51603", "data": []},
                materialized,
                observed_at=NOW,
                config=_config(order_not_found_codes=frozenset()),
            )

    def test_adapter_surface_has_no_asset_movement_or_account_mutation_methods(self):
        adapter, _ = _adapter(())
        forbidden = (
            "withdraw",
            "deposit",
            "transfer",
            "funding_transfer",
            "adjust_balance",
            "set_position_mode",
            "set_leverage",
            "set_account_mode",
        )
        for name in forbidden:
            with self.subTest(name=name):
                self.assertFalse(hasattr(adapter, name))

    def test_provider_quantity_cannot_exceed_e5_approved_canonical_bound(self):
        request, metadata, sizing, prerequisites, _ = _materialization(quantity="0.0105")
        materialized = materialize_demo_market_order(
            request,
            sizing,
            metadata,
            prerequisites,
            config=_config(),
            now=NOW,
        )
        self.assertEqual(materialized.provider_contract_quantity, Decimal("10"))
        self.assertEqual(materialized.effective_canonical_quantity, Decimal("0.010"))
        self.assertLessEqual(
            materialized.effective_canonical_quantity,
            materialized.canonical_approved_quantity,
        )


if __name__ == "__main__":
    unittest.main()
