import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.brokers.okx_sizing import (
    OKXInstrumentMetadata,
    OKXMetadataValidationError,
    OKXSizingError,
    OKXUnsupportedConversionError,
    size_okx_market_entry,
)
from src.execution.models import (
    SCHEMA_VERSION,
    OrderRequest,
    Side,
    stable_client_order_id,
    stable_order_request_id,
)


def _request(quantity: str = "0.010", *, side: Side = Side.BUY) -> OrderRequest:
    client_order_id = stable_client_order_id("plan-okx-001", "entry")
    return OrderRequest(
        schema_version=SCHEMA_VERSION,
        order_request_id=stable_order_request_id(client_order_id),
        trade_plan_id="plan-okx-001",
        client_order_id=client_order_id,
        symbol="BTC_USDT_PERP",
        side=side,
        order_type="MARKET",
        quantity=Decimal(quantity),
        quantity_profile_version="base-asset-v0.1",
        quantity_unit="BASE_ASSET",
        quantity_asset="BTC",
        created_at=datetime(2026, 8, 21, 4, 0, tzinfo=timezone.utc),
    )


def _metadata(now: datetime) -> OKXInstrumentMetadata:
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
        metadata_ref="local-fixture:btc-usdt-swap:001",
    )


class OKXSizingTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 21, 4, 0, tzinfo=timezone.utc)

    def test_exact_representable_quantity(self):
        audit = size_okx_market_entry(_request("0.010"), _metadata(self.now), now=self.now)
        self.assertEqual(audit.provider_requested_contract_quantity, Decimal("10"))
        self.assertEqual(audit.effective_canonical_requested_quantity, Decimal("0.010"))
        self.assertEqual(audit.canonical_approved_quantity, Decimal("0.010"))

    def test_round_down_quantity_never_rounds_up(self):
        audit = size_okx_market_entry(_request("0.0105"), _metadata(self.now), now=self.now)
        self.assertEqual(audit.provider_requested_contract_quantity, Decimal("10"))
        self.assertEqual(audit.effective_canonical_requested_quantity, Decimal("0.010"))
        self.assertLessEqual(audit.effective_canonical_requested_quantity, audit.canonical_approved_quantity)

    def test_below_minimum_or_nonrepresentable_quantity_rejects(self):
        with self.assertRaises(OKXSizingError):
            size_okx_market_entry(_request("0.0005"), _metadata(self.now), now=self.now)

    def test_lot_and_min_size_relationship_is_validated(self):
        bad = replace(_metadata(self.now), lot_sz=Decimal("2"), min_sz=Decimal("3"))
        with self.assertRaises(OKXMetadataValidationError):
            size_okx_market_entry(_request("0.010"), bad, now=self.now)

    def test_missing_stale_and_malformed_metadata_reject(self):
        with self.assertRaises(OKXMetadataValidationError):
            size_okx_market_entry(_request(), None, now=self.now)

        stale = replace(_metadata(self.now), observed_at=self.now - timedelta(seconds=301))
        with self.assertRaises(OKXMetadataValidationError):
            size_okx_market_entry(_request(), stale, now=self.now)

        malformed = replace(_metadata(self.now), ct_val="bad")  # type: ignore[arg-type]
        with self.assertRaises(OKXMetadataValidationError):
            size_okx_market_entry(_request(), malformed, now=self.now)

    def test_nontradable_states_reject_market_entry(self):
        for state in ("suspend", "rebase", "post_only"):
            with self.subTest(state=state):
                with self.assertRaises(OKXMetadataValidationError):
                    size_okx_market_entry(
                        _request(), replace(_metadata(self.now), state=state), now=self.now
                    )

    def test_provider_or_instrument_mismatch_rejects(self):
        mismatches = (
            {"provider": "OTHER"},
            {"canonical_symbol": "ETH_USDT_PERP"},
            {"instrument_id": "ETH-USDT-SWAP"},
            {"inst_type": "FUTURES"},
        )
        for changes in mismatches:
            with self.subTest(changes=changes):
                with self.assertRaises(OKXMetadataValidationError):
                    size_okx_market_entry(
                        _request(), replace(_metadata(self.now), **changes), now=self.now
                    )

    def test_unsupported_price_dependent_or_nonbase_conversion_rejects(self):
        with self.assertRaises(OKXUnsupportedConversionError):
            size_okx_market_entry(
                _request(), replace(_metadata(self.now), ct_val_ccy="USDT"), now=self.now
            )
        with self.assertRaises(OKXUnsupportedConversionError):
            size_okx_market_entry(
                _request(), replace(_metadata(self.now), ct_type="inverse"), now=self.now
            )

    def test_provider_sizing_never_exceeds_canonical_approved_btc(self):
        metadata = replace(
            _metadata(self.now),
            ct_val=Decimal("0.003"),
            lot_sz=Decimal("1"),
            min_sz=Decimal("1"),
        )
        audit = size_okx_market_entry(_request("0.010"), metadata, now=self.now)
        self.assertEqual(audit.provider_requested_contract_quantity, Decimal("3"))
        self.assertEqual(audit.effective_canonical_requested_quantity, Decimal("0.009"))
        self.assertLessEqual(audit.effective_canonical_requested_quantity, Decimal("0.010"))

    def test_canonical_btc_quantity_and_provider_contract_quantity_are_distinct(self):
        audit = size_okx_market_entry(_request("0.010"), _metadata(self.now), now=self.now)
        self.assertEqual(audit.quantity_unit, "BASE_ASSET")
        self.assertEqual(audit.quantity_asset, "BTC")
        self.assertEqual(audit.canonical_approved_quantity, Decimal("0.010"))
        self.assertEqual(audit.provider_requested_contract_quantity, Decimal("10"))
        self.assertNotEqual(
            audit.canonical_approved_quantity,
            audit.provider_requested_contract_quantity,
        )
        self.assertEqual(audit.provider_instrument_id, "BTC-USDT-SWAP")
        self.assertEqual(audit.instrument_metadata_ref, "local-fixture:btc-usdt-swap:001")


if __name__ == "__main__":
    unittest.main()
