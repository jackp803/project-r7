import unittest
from datetime import datetime, timezone
from decimal import Decimal

from src.brokers.okx_demo import (
    OKXAccountConfigSnapshot,
    OKXDemoAdapterConfig,
    OKXPrerequisiteSnapshot,
    OKXReconciliationError,
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


NOW = datetime(2026, 8, 21, 7, 30, tzinfo=timezone.utc)


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
        max_mkt_sz=Decimal("1000"),
    )
    sizing = size_okx_market_entry(request, metadata, now=NOW)
    config = OKXDemoAdapterConfig("2", "net_mode")
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


def _response(materialized, *, state, filled, size="10", avg_px=None):
    if avg_px is None:
        avg_px = "100000" if Decimal(filled) > 0 else ""
    return {
        "code": "0",
        "data": [
            {
                "instId": "BTC-USDT-SWAP",
                "clOrdId": materialized.provider_cl_ord_id,
                "ordId": "fake-provider-order",
                "state": state,
                "sz": size,
                "accFillSz": filled,
                "avgPx": avg_px,
            }
        ],
    }


class OKXDemoStatusMappingTests(unittest.TestCase):
    def test_consistent_live_partial_filled_and_canceled_states(self):
        materialized, config = _materialized()
        cases = (
            ("live", "0", OrderStatus.OPEN, Decimal("0")),
            ("partially_filled", "4", OrderStatus.PARTIALLY_FILLED, Decimal("0.004")),
            ("filled", "10", OrderStatus.FILLED, Decimal("0.010")),
            ("canceled", "0", OrderStatus.CANCELED, Decimal("0")),
            ("canceled", "4", OrderStatus.CANCELED, Decimal("0.004")),
            ("mmp_canceled", "4", OrderStatus.CANCELED, Decimal("0.004")),
        )
        for state, filled, expected_status, expected_fill in cases:
            with self.subTest(state=state, filled=filled):
                lookup = parse_order_lookup_response(
                    _response(materialized, state=state, filled=filled),
                    materialized,
                    observed_at=NOW,
                    config=config,
                )
                self.assertEqual(lookup.lookup_status, "FOUND_CONSISTENT")
                self.assertEqual(lookup.result.order_status, expected_status)
                self.assertEqual(lookup.result.filled_quantity, expected_fill)

    def test_contradictory_known_state_fill_combinations_require_reconciliation(self):
        materialized, config = _materialized()
        contradictions = (
            ("filled", "9"),
            ("partially_filled", "0"),
            ("partially_filled", "10"),
            ("live", "1"),
        )
        for state, filled in contradictions:
            with self.subTest(state=state, filled=filled):
                lookup = parse_order_lookup_response(
                    _response(materialized, state=state, filled=filled),
                    materialized,
                    observed_at=NOW,
                    config=config,
                )
                self.assertEqual(lookup.lookup_status, "FOUND_CONTRADICTORY_STATE")
                self.assertEqual(
                    lookup.result.order_status,
                    OrderStatus.RECONCILIATION_REQUIRED,
                )

    def test_overfill_is_hard_failure(self):
        materialized, config = _materialized()
        with self.assertRaises(OKXReconciliationError):
            parse_order_lookup_response(
                _response(materialized, state="filled", filled="11"),
                materialized,
                observed_at=NOW,
                config=config,
            )

    def test_positive_fill_without_average_price_is_hard_failure(self):
        materialized, config = _materialized()
        with self.assertRaises(OKXReconciliationError):
            parse_order_lookup_response(
                _response(
                    materialized,
                    state="partially_filled",
                    filled="4",
                    avg_px="",
                ),
                materialized,
                observed_at=NOW,
                config=config,
            )

    def test_unknown_state_is_never_optimistic_success(self):
        materialized, config = _materialized()
        lookup = parse_order_lookup_response(
            _response(materialized, state="future_unknown_state", filled="0"),
            materialized,
            observed_at=NOW,
            config=config,
        )
        self.assertEqual(lookup.lookup_status, "FOUND_UNKNOWN_STATE")
        self.assertEqual(lookup.result.order_status, OrderStatus.RECONCILIATION_REQUIRED)


if __name__ == "__main__":
    unittest.main()
