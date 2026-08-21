import unittest
from datetime import datetime, timezone
from decimal import Decimal

from src.brokers.okx_demo import (
    OKXDemoAdapterConfig,
    materialize_demo_market_order,
    parse_order_lookup_response,
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
from src.brokers.okx_demo import OKXAccountConfigSnapshot, OKXPrerequisiteSnapshot


NOW = datetime(2026, 8, 21, 5, 0, tzinfo=timezone.utc)


def _materialized():
    client_id = stable_client_order_id("plan-status-001", "entry")
    request = OrderRequest(
        schema_version=SCHEMA_VERSION,
        order_request_id=stable_order_request_id(client_id),
        trade_plan_id="plan-status-001",
        client_order_id=client_id,
        symbol="BTC_USDT_PERP",
        side=Side.BUY,
        order_type="MARKET",
        quantity=Decimal("0.010"),
        quantity_profile_version="base-asset-v0.1",
        quantity_unit="BASE_ASSET",
        quantity_asset="BTC",
        created_at=NOW,
    )
    metadata = OKXInstrumentMetadata(
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
        metadata_ref="fake-public:status:001",
    )
    sizing = size_okx_market_entry(request, metadata, now=NOW)
    config = OKXDemoAdapterConfig(
        expected_account_level="2", expected_position_mode="net_mode"
    )
    prerequisites = OKXPrerequisiteSnapshot(
        account=OKXAccountConfigSnapshot(
            account_level="2",
            position_mode="net_mode",
            uid="fake-sub",
            main_uid="fake-main",
        ),
        positions=(),
        pending_orders=(),
    )
    return materialize_demo_market_order(
        request,
        sizing,
        metadata,
        prerequisites,
        config=config,
        now=NOW,
    ), config


def _response(materialized, *, state, filled):
    return {
        "code": "0",
        "data": [
            {
                "instId": "BTC-USDT-SWAP",
                "clOrdId": materialized.provider_cl_ord_id,
                "ordId": "fake-provider-order",
                "state": state,
                "sz": "10",
                "accFillSz": filled,
                "avgPx": "100000" if Decimal(filled) > 0 else "",
            }
        ],
    }


class OKXDemoStatusMappingTests(unittest.TestCase):
    def test_filled_maps_to_canonical_filled_quantity(self):
        materialized, config = _materialized()
        lookup = parse_order_lookup_response(
            _response(materialized, state="filled", filled="10"),
            materialized,
            observed_at=NOW,
            config=config,
        )
        self.assertEqual(lookup.result.order_status, OrderStatus.FILLED)
        self.assertEqual(lookup.result.filled_quantity, Decimal("0.010"))

    def test_canceled_with_partial_fill_preserves_actual_fill(self):
        materialized, config = _materialized()
        lookup = parse_order_lookup_response(
            _response(materialized, state="canceled", filled="4"),
            materialized,
            observed_at=NOW,
            config=config,
        )
        self.assertEqual(lookup.result.order_status, OrderStatus.CANCELED)
        self.assertEqual(lookup.result.filled_quantity, Decimal("0.004"))


if __name__ == "__main__":
    unittest.main()
