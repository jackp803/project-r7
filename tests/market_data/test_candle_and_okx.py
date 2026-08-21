from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from market_data import (  # noqa: E402
    Candle,
    DuplicateCandleError,
    MalformedCandleError,
    OkxPublicHistoricalCandleSource,
    OutOfOrderCandleError,
    ProviderRateLimitError,
    ProviderResponseError,
    normalize_okx_history_page,
    okx_bar,
    okx_instrument,
)
from market_data.candle import CONTRACT_SCHEMA_VERSION  # noqa: E402

UTC = timezone.utc
BASE = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)


def ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def raw_row(
    open_time: datetime,
    *,
    open_price: str = "100.10",
    high: str = "101.20",
    low: str = "99.90",
    close: str = "100.80",
    volume: str = "12.345",
    confirm: str = "1",
) -> list[str]:
    return [
        str(ms(open_time)),
        open_price,
        high,
        low,
        close,
        volume,
        "123.45",
        "1234.56",
        confirm,
    ]


def payload(rows: list[list[str]], *, code: str = "0", msg: str = "") -> dict[str, object]:
    return {"code": code, "msg": msg, "data": rows}


class CandleContractTests(unittest.TestCase):
    def test_decimal_and_rfc3339_interchange_keeps_contract_version(self) -> None:
        candle = Candle(
            schema_version=CONTRACT_SCHEMA_VERSION,
            symbol="BTC_USDT_PERP",
            timeframe="1m",
            open_time=BASE,
            close_time=BASE + timedelta(minutes=1),
            open=Decimal("100.10"),
            high=Decimal("101.20"),
            low=Decimal("99.90"),
            close=Decimal("100.80"),
            volume=Decimal("12.345"),
            is_closed=True,
            source="TEST",
        )
        serialized = candle.to_interchange_dict()
        self.assertEqual(serialized["schema_version"], "contracts-v0.1")
        self.assertEqual(serialized["open"], "100.10")
        self.assertEqual(serialized["volume"], "12.345")
        self.assertEqual(serialized["open_time"], "2026-01-01T00:00:00.000Z")
        self.assertEqual(serialized["close_time"], "2026-01-01T00:01:00.000Z")

    def test_binary_float_is_rejected(self) -> None:
        with self.assertRaises(MalformedCandleError):
            Candle(
                schema_version=CONTRACT_SCHEMA_VERSION,
                symbol="BTC_USDT_PERP",
                timeframe="1m",
                open_time=BASE,
                close_time=BASE + timedelta(minutes=1),
                open=100.1,  # type: ignore[arg-type]
                high=Decimal("101.2"),
                low=Decimal("99.9"),
                close=Decimal("100.8"),
                volume=Decimal("1"),
                is_closed=True,
                source="TEST",
            )


class OkxNormalizationTests(unittest.TestCase):
    def test_symbol_mapping_is_adapter_local(self) -> None:
        self.assertEqual(okx_instrument("BTC_USDT_PERP"), "BTC-USDT-SWAP")

    def test_supported_timeframe_mapping_is_exact(self) -> None:
        self.assertEqual(okx_bar("1m"), "1m")
        self.assertEqual(okx_bar("15m"), "15m")
        self.assertEqual(okx_bar("1h"), "1H")
        self.assertEqual(okx_bar("4h"), "4H")

    def test_url_uses_swap_instrument_bar_after_and_limit(self) -> None:
        source = OkxPublicHistoricalCandleSource()
        url = source.build_history_url(
            symbol="BTC_USDT_PERP",
            timeframe="1h",
            end_time_ms=123456789,
            limit=100,
        )
        self.assertIn("instId=BTC-USDT-SWAP", url)
        self.assertIn("bar=1H", url)
        self.assertIn("after=123456789", url)
        self.assertIn("limit=100", url)

    def test_descending_provider_page_becomes_ascending_canonical_sequence(self) -> None:
        rows = [raw_row(BASE + timedelta(minutes=1)), raw_row(BASE)]
        candles = normalize_okx_history_page(
            payload(rows), symbol="BTC_USDT_PERP", timeframe="1m"
        )
        self.assertEqual([c.open_time for c in candles], [BASE, BASE + timedelta(minutes=1)])
        self.assertTrue(all(c.is_closed for c in candles))
        self.assertTrue(all(isinstance(c.open, Decimal) for c in candles))
        self.assertTrue(all(c.schema_version == "contracts-v0.1" for c in candles))

    def test_provider_confirm_controls_finality(self) -> None:
        provisional = normalize_okx_history_page(
            payload([raw_row(BASE, confirm="0")]),
            symbol="BTC_USDT_PERP",
            timeframe="1m",
        )
        closed = normalize_okx_history_page(
            payload([raw_row(BASE, confirm="1")]),
            symbol="BTC_USDT_PERP",
            timeframe="1m",
        )
        self.assertFalse(provisional[0].is_closed)
        self.assertTrue(closed[0].is_closed)

    def test_duplicate_provider_identity_is_rejected(self) -> None:
        with self.assertRaises(DuplicateCandleError):
            normalize_okx_history_page(
                payload([raw_row(BASE), raw_row(BASE)]),
                symbol="BTC_USDT_PERP",
                timeframe="1m",
            )

    def test_mixed_provider_order_is_rejected(self) -> None:
        rows = [
            raw_row(BASE),
            raw_row(BASE + timedelta(minutes=2)),
            raw_row(BASE + timedelta(minutes=1)),
        ]
        with self.assertRaises(OutOfOrderCandleError):
            normalize_okx_history_page(
                payload(rows), symbol="BTC_USDT_PERP", timeframe="1m"
            )

    def test_malformed_ohlc_is_rejected(self) -> None:
        with self.assertRaises(MalformedCandleError):
            normalize_okx_history_page(
                payload([raw_row(BASE, open_price="105", high="101", low="99", close="100")]),
                symbol="BTC_USDT_PERP",
                timeframe="1m",
            )

    def test_negative_volume_is_rejected(self) -> None:
        with self.assertRaises(MalformedCandleError):
            normalize_okx_history_page(
                payload([raw_row(BASE, volume="-1")]),
                symbol="BTC_USDT_PERP",
                timeframe="1m",
            )

    def test_invalid_confirm_is_rejected(self) -> None:
        with self.assertRaises(ProviderResponseError):
            normalize_okx_history_page(
                payload([raw_row(BASE, confirm="unknown")]),
                symbol="BTC_USDT_PERP",
                timeframe="1m",
            )

    def test_okx_rate_limit_code_is_typed(self) -> None:
        with self.assertRaises(ProviderRateLimitError):
            normalize_okx_history_page(
                payload([], code="50011", msg="Rate limit reached"),
                symbol="BTC_USDT_PERP",
                timeframe="1m",
            )


if __name__ == "__main__":
    unittest.main()
