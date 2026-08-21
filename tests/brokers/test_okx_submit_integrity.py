import json
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

from src.brokers.okx_demo import (
    OKXAccountConfigSnapshot,
    OKXCredentials,
    OKXDemoAdapter,
    OKXDemoAdapterConfig,
    OKXPrerequisiteSnapshot,
    OKXProtocolError,
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


NOW = datetime(2026, 8, 21, 8, 30, tzinfo=timezone.utc)
TIMESTAMP = "2026-08-21T08:30:00.000Z"


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
    client_id = stable_client_order_id("plan-submit-integrity-001", "entry")
    return OrderRequest(
        schema_version=SCHEMA_VERSION,
        order_request_id=stable_order_request_id(client_id),
        trade_plan_id="plan-submit-integrity-001",
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


def _metadata(*, ref="fake-public:submit-integrity:001"):
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
        observed_at=NOW,
        metadata_ref=ref,
    )


def _prerequisites(*, position_mode="net_mode"):
    return OKXPrerequisiteSnapshot(
        account=OKXAccountConfigSnapshot(
            account_level="2",
            position_mode=position_mode,
            uid="fake-sub-uid",
            main_uid="fake-main-uid",
        ),
        positions=(),
        pending_orders=(),
    )


def _config(*, position_mode="net_mode"):
    return OKXDemoAdapterConfig(
        expected_account_level="2",
        expected_position_mode=position_mode,
    )


def _success_ack(cl_ord_id):
    return {
        "code": "0",
        "msg": "",
        "data": [
            {
                "clOrdId": cl_ord_id,
                "ordId": "fake-provider-order-submit-integrity",
                "sCode": "0",
                "sMsg": "",
            }
        ],
    }


def _adapter(effects=(), *, position_mode="net_mode"):
    transport = _FakeTransport(effects)
    adapter = OKXDemoAdapter(
        credentials=OKXCredentials(
            api_key="fakeApiKeyForLocalTestOnly",
            secret_key="fakeSecretForLocalTestOnly",
            passphrase="fakePassphraseForLocalTestOnly",
        ),
        config=_config(position_mode=position_mode),
        transport=transport,
        timestamp_provider=lambda: TIMESTAMP,
    )
    return adapter, transport


def _prepare(adapter, *, side=Side.BUY, quantity="0.010", position_mode="net_mode"):
    request = _request(side=side, quantity=quantity)
    metadata = _metadata()
    sizing = size_okx_market_entry(request, metadata, now=NOW)
    prerequisites = _prerequisites(position_mode=position_mode)
    materialization = adapter.prepare_entry(
        request,
        sizing,
        metadata,
        prerequisites,
        now=NOW,
    )
    return request, metadata, sizing, prerequisites, materialization


class OKXSubmitIntegrityTests(unittest.TestCase):
    def _assert_body_mutation_rejected(self, key, value):
        adapter, transport = _adapter()
        _, _, _, _, materialization = _prepare(adapter)
        materialization.body[key] = value
        with self.assertRaises(OKXProtocolError):
            adapter.submit_entry(materialization, observed_at=NOW)
        self.assertEqual(transport.requests, [])

    def test_mutated_sz_rejected_before_transport(self):
        self._assert_body_mutation_rejected("sz", "999999")

    def test_mutated_inst_id_rejected_before_transport(self):
        self._assert_body_mutation_rejected("instId", "ETH-USDT-SWAP")

    def test_mutated_side_rejected_before_transport(self):
        self._assert_body_mutation_rejected("side", "sell")

    def test_mutated_position_side_rejected_before_transport(self):
        self._assert_body_mutation_rejected("posSide", "short")

    def test_mutated_order_type_rejected_before_transport(self):
        self._assert_body_mutation_rejected("ordType", "limit")

    def test_mutated_cl_ord_id_rejected_before_transport(self):
        self._assert_body_mutation_rejected("clOrdId", "R7FORGEDCLORDID")

    def test_direct_caller_constructed_clone_rejected_before_transport(self):
        adapter, transport = _adapter()
        _, _, _, _, issued = _prepare(adapter)
        caller_clone = replace(issued, body=dict(issued.body))
        with self.assertRaises(OKXProtocolError):
            adapter.submit_entry(caller_clone, observed_at=NOW)
        self.assertEqual(transport.requests, [])

    def test_cross_adapter_materialization_rejected_before_transport(self):
        issuer, _ = _adapter()
        _, _, _, _, issued = _prepare(issuer)
        other_adapter, other_transport = _adapter()
        with self.assertRaises(OKXProtocolError):
            other_adapter.submit_entry(issued, observed_at=NOW)
        self.assertEqual(other_transport.requests, [])

    def test_materially_changed_clone_under_same_client_identity_rejected(self):
        adapter, transport = _adapter()
        _, _, _, _, issued = _prepare(adapter)
        changed = replace(
            issued,
            provider_contract_quantity=Decimal("11"),
            effective_canonical_quantity=Decimal("0.010"),
            body={**issued.body, "sz": "11"},
        )
        with self.assertRaises(OKXProtocolError):
            adapter.submit_entry(changed, observed_at=NOW)
        self.assertEqual(transport.requests, [])

    def test_same_cl_ord_id_cannot_be_reprepared_with_materially_different_facts(self):
        adapter, transport = _adapter()
        _prepare(adapter, side=Side.BUY)
        request = _request(side=Side.SELL)
        metadata = _metadata()
        sizing = size_okx_market_entry(request, metadata, now=NOW)
        with self.assertRaises(OKXProtocolError):
            adapter.prepare_entry(
                request,
                sizing,
                metadata,
                _prerequisites(),
                now=NOW,
            )
        self.assertEqual(transport.requests, [])

    def test_valid_adapter_issued_preparation_sends_exact_demo_market_isolated_body(self):
        adapter, transport = _adapter()
        _, _, _, _, issued = _prepare(adapter)
        transport.effects.append(_success_ack(issued.provider_cl_ord_id))

        result = adapter.submit_entry(issued, observed_at=NOW)

        self.assertEqual(result.order_status, OrderStatus.PENDING)
        self.assertEqual(len(transport.requests), 1)
        request = transport.requests[0]
        self.assertEqual(request.headers["x-simulated-trading"], "1")
        self.assertEqual(
            json.loads(request.body_text),
            {
                "instId": "BTC-USDT-SWAP",
                "tdMode": "isolated",
                "clOrdId": issued.provider_cl_ord_id,
                "side": "buy",
                "posSide": "net",
                "ordType": "market",
                "sz": "10",
            },
        )

    def test_repeated_submit_of_same_issued_object_is_idempotent_without_second_transport(self):
        adapter, transport = _adapter()
        _, _, _, _, issued = _prepare(adapter)
        transport.effects.append(_success_ack(issued.provider_cl_ord_id))
        first = adapter.submit_entry(issued, observed_at=NOW)
        second = adapter.submit_entry(issued, observed_at=NOW)
        self.assertEqual(first, second)
        self.assertEqual(len(transport.requests), 1)

    def test_provider_effective_quantity_never_exceeds_e5_canonical_bound(self):
        adapter, transport = _adapter()
        request, _, _, _, issued = _prepare(adapter, quantity="0.0105")
        self.assertEqual(request.quantity, Decimal("0.0105"))
        self.assertEqual(issued.provider_contract_quantity, Decimal("10"))
        self.assertEqual(issued.effective_canonical_quantity, Decimal("0.010"))
        self.assertLessEqual(
            issued.effective_canonical_quantity,
            issued.canonical_approved_quantity,
        )
        transport.effects.append(_success_ack(issued.provider_cl_ord_id))
        adapter.submit_entry(issued, observed_at=NOW)
        self.assertEqual(json.loads(transport.requests[0].body_text)["sz"], "10")


if __name__ == "__main__":
    unittest.main()
