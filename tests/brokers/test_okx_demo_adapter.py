import base64
import hashlib
import hmac
import re
import unittest
from dataclasses import replace
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


NOW = datetime(2026, 8, 21, 7, 30, tzinfo=timezone.utc)
TIMESTAMP = "2026-08-21T07:30:00.000Z"
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


def _request(*, side=Side.BUY, quantity="0.010", plan_id="plan-okx-demo-001"):
    client_id = stable_client_order_id(plan_id, "entry")
    return OrderRequest(
        schema_version=SCHEMA_VERSION,
        order_request_id=stable_order_request_id(client_id),
        trade_plan_id=plan_id,
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
        max_mkt_sz=Decimal("1000"),
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


def _config(*, position_mode="net_mode"):
    return OKXDemoAdapterConfig(
        expected_account_level="2",
        expected_position_mode=position_mode,
    )


def _materialization(*, side=Side.BUY, quantity="0.010", position_mode="net_mode", plan_id="plan-okx-demo-001"):
    request = _request(side=side, quantity=quantity, plan_id=plan_id)
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


def _adapter(effects, *, position_mode="net_mode"):
    transport = _FakeTransport(effects)
    adapter = OKXDemoAdapter(
        credentials=OKXCredentials(
            api_key=FAKE_API_KEY,
            secret_key=FAKE_SECRET,
            passphrase=FAKE_PASSPHRASE,
        ),
        config=_config(position_mode=position_mode),
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
        self.assertEqual(prepared.headers["x-simulated-trading"], "1")
        self.assertNotIn(FAKE_SECRET, repr(prepared))

    def test_demo_adapter_rejects_production_and_nonapproved_account_levels(self):
        with self.assertRaises(OKXDemoConfigurationError):
            OKXDemoAdapterConfig("2", "net_mode", environment="production")
        for acct_lv in ("1", "3", "4"):
            with self.subTest(acct_lv=acct_lv):
                with self.assertRaises(OKXDemoConfigurationError):
                    OKXDemoAdapterConfig(acct_lv, "net_mode")

    def test_v1_account_matrix_accepts_only_futures_mode_net_or_long_short(self):
        self.assertEqual(_config(position_mode="net_mode").expected_account_level, "2")
        self.assertEqual(_config(position_mode="long_short_mode").expected_account_level, "2")
        with self.assertRaises(OKXDemoConfigurationError):
            OKXDemoAdapterConfig("2", "unsupported_mode")

    def test_prerequisite_matrix_rejects_spot_multi_currency_and_portfolio(self):
        for acct_lv, pos_mode in (
            ("1", "net_mode"),
            ("3", "net_mode"),
            ("3", "long_short_mode"),
            ("4", "net_mode"),
            ("4", "long_short_mode"),
        ):
            with self.subTest(acct_lv=acct_lv, pos_mode=pos_mode):
                with self.assertRaises(OKXPrerequisiteError):
                    validate_demo_prerequisites(
                        _prerequisites(account_level=acct_lv, position_mode=pos_mode),
                        config=_config(),
                    )

    def test_stable_provider_clordid_is_legal_and_traceable(self):
        internal = _request().client_order_id
        first = stable_okx_cl_ord_id(internal)
        second = stable_okx_cl_ord_id(internal)
        self.assertEqual(first, second)
        self.assertEqual(first.internal_client_order_id, internal)
        self.assertRegex(first.provider_cl_ord_id, re.compile(r"^[A-Za-z0-9]{1,32}$"))
        self.assertLessEqual(len(first.provider_cl_ord_id), 32)

    def test_valid_materialization_uses_recomputed_provider_size_not_canonical_btc(self):
        request, _, sizing, _, materialized = _materialization()
        self.assertEqual(request.quantity, Decimal("0.010"))
        self.assertEqual(sizing.provider_requested_contract_quantity, Decimal("10"))
        self.assertEqual(materialized.body["sz"], "10")
        self.assertNotEqual(materialized.body["sz"], format(request.quantity, "f"))
        self.assertLessEqual(materialized.effective_canonical_quantity, request.quantity)

    def test_forged_oversized_sizing_audit_fails_closed(self):
        request = _request()
        metadata = _metadata()
        sizing = size_okx_market_entry(request, metadata, now=NOW)
        forged = replace(
            sizing,
            provider_requested_contract_quantity=Decimal("999"),
            effective_canonical_requested_quantity=Decimal("0.001"),
        )
        with self.assertRaises(OKXProtocolError):
            materialize_demo_market_order(
                request, forged, metadata, _prerequisites(), config=_config(), now=NOW
            )

    def test_changed_request_quantity_invalidates_prior_sizing_evidence(self):
        request = _request(quantity="0.010")
        metadata = _metadata()
        sizing = size_okx_market_entry(request, metadata, now=NOW)
        changed = replace(request, quantity=Decimal("0.020"))
        with self.assertRaises(OKXProtocolError):
            materialize_demo_market_order(
                changed, sizing, metadata, _prerequisites(), config=_config(), now=NOW
            )

    def test_altered_metadata_invalidates_prior_sizing_evidence(self):
        request = _request()
        metadata = _metadata()
        sizing = size_okx_market_entry(request, metadata, now=NOW)
        altered = replace(metadata, ct_val=Decimal("0.002"))
        with self.assertRaises(OKXProtocolError):
            materialize_demo_market_order(
                request, sizing, altered, _prerequisites(), config=_config(), now=NOW
            )

    def test_metadata_reference_mismatch_invalidates_prior_sizing_evidence(self):
        request = _request()
        metadata = _metadata()
        sizing = size_okx_market_entry(request, metadata, now=NOW)
        changed_ref = replace(metadata, metadata_ref="fake-public:tampered")
        with self.assertRaises(OKXProtocolError):
            materialize_demo_market_order(
                request, sizing, changed_ref, _prerequisites(), config=_config(), now=NOW
            )

    def test_long_short_mode_maps_position_side_mechanically(self):
        _, _, _, _, long_order = _materialization(
            side=Side.BUY, position_mode="long_short_mode"
        )
        _, _, _, _, short_order = _materialization(
            side=Side.SELL, position_mode="long_short_mode", plan_id="plan-short"
        )
        self.assertEqual(long_order.body["posSide"], "long")
        self.assertEqual(short_order.body["posSide"], "short")

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
            "data": [{
                "clOrdId": materialized.provider_cl_ord_id,
                "ordId": "fake-okx-order-1",
                "sCode": "0",
                "sMsg": "",
            }],
        }
        adapter, transport = _adapter((response,))
        result = adapter.submit_entry(materialized, observed_at=NOW)
        self.assertEqual(result.order_status, OrderStatus.PENDING)
        self.assertEqual(result.filled_quantity, Decimal("0"))
        self.assertEqual(len(transport.requests), 1)

    def test_timeout_is_reconciliation_required_and_ordinary_resubmit_is_not_sent(self):
        _, _, _, _, materialized = _materialization()
        adapter, transport = _adapter((TimeoutError("fake timeout"),))
        first = adapter.submit_entry(materialized, observed_at=NOW)
        second = adapter.submit_entry(materialized, observed_at=NOW)
        self.assertEqual(first.order_status, OrderStatus.RECONCILIATION_REQUIRED)
        self.assertEqual(second, first)
        self.assertEqual(len(transport.requests), 1)

    def test_non_success_order_lookup_never_proves_absence(self):
        _, _, _, _, materialized = _materialization()
        lookup = parse_order_lookup_response(
            {"code": "51603", "msg": "fixture only", "data": []},
            materialized,
            observed_at=NOW,
            config=_config(),
        )
        self.assertFalse(lookup.found)
        self.assertEqual(lookup.lookup_status, "PROVIDER_ERROR_NOT_ABSENCE_PROOF")
        self.assertEqual(lookup.provider_error_code, "51603")

    def test_arbitrary_absence_code_configuration_surface_is_removed(self):
        with self.assertRaises(TypeError):
            OKXDemoAdapterConfig(
                expected_account_level="2",
                expected_position_mode="net_mode",
                order_not_found_codes=frozenset({"51603"}),
            )

    def test_reconciliation_queries_truth_but_never_authorizes_retry(self):
        _, _, _, _, materialized = _materialization()
        effects = (
            TimeoutError("fake submit timeout"),
            {"code": "51603", "msg": "fixture provider error", "data": []},
            {"code": "0", "msg": "", "data": []},
            {"code": "0", "msg": "", "data": []},
            {"code": "0", "msg": "", "data": []},
        )
        adapter, transport = _adapter(effects)
        ambiguous = adapter.submit_entry(materialized, observed_at=NOW)
        self.assertEqual(ambiguous.order_status, OrderStatus.RECONCILIATION_REQUIRED)
        evidence = adapter.reconcile_ambiguous(materialized, observed_at=NOW)
        self.assertFalse(evidence.retry_allowed)
        self.assertEqual(
            evidence.reason,
            "ORDER_ABSENCE_NOT_AUTHORITATIVELY_PROVEN_RETRY_DISABLED",
        )
        self.assertEqual(len(transport.requests), 5)
        with self.assertRaises(OKXReconciliationError):
            adapter.retry_entry(materialized, evidence, observed_at=NOW)
        self.assertEqual(len(transport.requests), 5)

    def test_forged_mutated_replayed_or_cross_materialization_evidence_cannot_submit(self):
        _, _, _, _, materialized = _materialization()
        effects = (
            TimeoutError("fake submit timeout"),
            {"code": "51603", "data": []},
            {"code": "0", "data": []},
            {"code": "0", "data": []},
            {"code": "0", "data": []},
        )
        adapter, transport = _adapter(effects)
        adapter.submit_entry(materialized, observed_at=NOW)
        evidence = adapter.reconcile_ambiguous(materialized, observed_at=NOW)
        forged = replace(evidence, retry_allowed=True, reason="FORGED")
        for candidate in (forged, evidence, forged):
            with self.assertRaises(OKXReconciliationError):
                adapter.retry_entry(materialized, candidate, observed_at=NOW)
        _, _, _, _, other = _materialization(plan_id="other-plan")
        with self.assertRaises(OKXReconciliationError):
            adapter.retry_entry(other, forged, observed_at=NOW)
        self.assertEqual(len(transport.requests), 5)

    def test_adapter_surface_has_no_asset_movement_or_account_mutation_methods(self):
        adapter, _ = _adapter(())
        for name in (
            "withdraw",
            "deposit",
            "transfer",
            "funding_transfer",
            "adjust_balance",
            "set_position_mode",
            "set_leverage",
            "set_account_mode",
        ):
            with self.subTest(name=name):
                self.assertFalse(hasattr(adapter, name))


if __name__ == "__main__":
    unittest.main()
