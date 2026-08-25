from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from market_data import (  # noqa: E402
    CONTRACT_SCHEMA_VERSION,
    CurrentMarketState,
    FutureMarketDataError,
    MalformedCandleError,
    MissingCandleError,
    NonMonotonicMarketDataError,
    OkxPublicCurrentMarketSource,
    ProviderResponseError,
    StaleMarketDataError,
    normalize_okx_current_candles,
    normalize_okx_ticker,
)

UTC = timezone.utc
BASE = datetime(2026, 8, 25, 4, 0, 0, tzinfo=UTC)


def ms(value: datetime) -> str:
    return str(int(value.timestamp() * 1000))


def ticker_payload(
    observed_at: datetime,
    *,
    last: str = "64000.10",
    bid: str = "64000.00",
    ask: str = "64000.20",
    code: str = "0",
    include_ts: bool = True,
) -> dict[str, object]:
    row: dict[str, object] = {
        "instId": "BTC-USDT-SWAP",
        "last": last,
        "bidPx": bid,
        "askPx": ask,
    }
    if include_ts:
        row["ts"] = ms(observed_at)
    return {"code": code, "msg": "", "data": [row]}


def candle_row(
    open_time: datetime,
    *,
    confirm: str = "1",
    open_price: str = "100.0",
    high: str = "101.0",
    low: str = "99.0",
    close: str = "100.5",
    volume: str = "10.0",
) -> list[str]:
    return [
        ms(open_time),
        open_price,
        high,
        low,
        close,
        volume,
        "10.0",
        "1000.0",
        confirm,
    ]


def candle_payload(rows: list[list[str]], *, code: str = "0") -> dict[str, object]:
    return {"code": code, "msg": "", "data": rows}


class GateCCurrentTickerTests(unittest.TestCase):
    def test_current_ticker_normalizes_to_canonical_market_snapshot(self) -> None:
        snapshot = normalize_okx_ticker(
            ticker_payload(BASE),
            symbol="BTC_USDT_PERP",
            received_at=BASE + timedelta(milliseconds=250),
        )
        self.assertEqual(snapshot.schema_version, CONTRACT_SCHEMA_VERSION)
        self.assertEqual(snapshot.symbol, "BTC_USDT_PERP")
        self.assertEqual(snapshot.health_status, "HEALTHY")
        self.assertEqual(snapshot.source, "OKX_PUBLIC_TICKER")
        self.assertEqual(snapshot.observed_at, BASE)
        self.assertEqual(snapshot.received_at, BASE + timedelta(milliseconds=250))
        self.assertEqual(snapshot.last_price, Decimal("64000.10"))
        self.assertEqual(snapshot.best_bid, Decimal("64000.00"))
        self.assertEqual(snapshot.best_ask, Decimal("64000.20"))
        self.assertEqual(snapshot.freshness_ms, 250)
        serialized = snapshot.to_interchange_dict()
        self.assertEqual(serialized["schema_version"], "contracts-v0.1")
        self.assertEqual(serialized["last_price"], "64000.10")
        self.assertEqual(serialized["observed_at"], "2026-08-25T04:00:00.000Z")

    def test_healthy_boundary_is_5000_ms(self) -> None:
        snapshot = normalize_okx_ticker(
            ticker_payload(BASE),
            symbol="BTC_USDT_PERP",
            received_at=BASE + timedelta(milliseconds=5000),
        )
        self.assertEqual(snapshot.health_status, "HEALTHY")
        self.assertEqual(snapshot.freshness_ms, 5000)

    def test_stale_over_5000_ms_fails_closed(self) -> None:
        with self.assertRaises(StaleMarketDataError):
            normalize_okx_ticker(
                ticker_payload(BASE),
                symbol="BTC_USDT_PERP",
                received_at=BASE + timedelta(milliseconds=5001),
            )

    def test_missing_timestamp_fails_closed(self) -> None:
        with self.assertRaises(ProviderResponseError):
            normalize_okx_ticker(
                ticker_payload(BASE, include_ts=False),
                symbol="BTC_USDT_PERP",
                received_at=BASE,
            )

    def test_materially_future_timestamp_fails_closed(self) -> None:
        with self.assertRaises(FutureMarketDataError):
            normalize_okx_ticker(
                ticker_payload(BASE + timedelta(milliseconds=5001)),
                symbol="BTC_USDT_PERP",
                received_at=BASE,
            )

    def test_future_timestamp_within_clock_tolerance_is_eligible(self) -> None:
        snapshot = normalize_okx_ticker(
            ticker_payload(BASE + timedelta(milliseconds=5000)),
            symbol="BTC_USDT_PERP",
            received_at=BASE,
        )
        self.assertEqual(snapshot.health_status, "HEALTHY")
        self.assertEqual(snapshot.freshness_ms, 0)

    def test_older_second_response_cannot_replace_newer_truth(self) -> None:
        state = CurrentMarketState()
        newer = state.ingest_ticker(
            ticker_payload(BASE + timedelta(seconds=2)),
            symbol="BTC_USDT_PERP",
            received_at=BASE + timedelta(seconds=2, milliseconds=100),
        )
        with self.assertRaises(NonMonotonicMarketDataError):
            state.ingest_ticker(
                ticker_payload(BASE + timedelta(seconds=1)),
                symbol="BTC_USDT_PERP",
                received_at=BASE + timedelta(seconds=2, milliseconds=200),
            )
        self.assertIs(state.current_snapshot("BTC_USDT_PERP"), newer)

    def test_provider_error_or_zero_price_does_not_produce_valid_observation(self) -> None:
        with self.assertRaises(ProviderResponseError):
            normalize_okx_ticker(
                ticker_payload(BASE, code="51000"),
                symbol="BTC_USDT_PERP",
                received_at=BASE,
            )
        with self.assertRaises(MalformedCandleError):
            normalize_okx_ticker(
                ticker_payload(BASE, last="0"),
                symbol="BTC_USDT_PERP",
                received_at=BASE,
            )


class GateCCurrentCandleTests(unittest.TestCase):
    def test_finalized_closed_candle_is_exposed(self) -> None:
        candles = normalize_okx_current_candles(
            candle_payload([candle_row(BASE, confirm="1")]),
            symbol="BTC_USDT_PERP",
            timeframe="1m",
            received_at=BASE + timedelta(minutes=1),
        )
        self.assertEqual(len(candles), 1)
        self.assertTrue(candles[0].is_closed)
        self.assertEqual(candles[0].source, "OKX_PUBLIC_CURRENT_CANDLES")
        self.assertEqual(candles[0].open_time, BASE)
        self.assertEqual(candles[0].close_time, BASE + timedelta(minutes=1))

    def test_unconfirmed_or_not_yet_closed_candle_is_withheld(self) -> None:
        unconfirmed = normalize_okx_current_candles(
            candle_payload([candle_row(BASE, confirm="0")]),
            symbol="BTC_USDT_PERP",
            timeframe="1m",
            received_at=BASE + timedelta(minutes=2),
        )
        self.assertEqual(unconfirmed, ())

        not_yet_closed = normalize_okx_current_candles(
            candle_payload([candle_row(BASE, confirm="1")]),
            symbol="BTC_USDT_PERP",
            timeframe="1m",
            received_at=BASE + timedelta(seconds=59),
        )
        self.assertEqual(not_yet_closed, ())

    def test_gap_between_finalized_candles_is_visible(self) -> None:
        rows = [candle_row(BASE + timedelta(minutes=2)), candle_row(BASE)]
        with self.assertRaises(MissingCandleError):
            normalize_okx_current_candles(
                candle_payload(rows),
                symbol="BTC_USDT_PERP",
                timeframe="1m",
                received_at=BASE + timedelta(minutes=4),
            )

    def test_malformed_ohlc_and_provider_error_fail_closed(self) -> None:
        with self.assertRaises(MalformedCandleError):
            normalize_okx_current_candles(
                candle_payload([candle_row(BASE, open_price="105", high="101")]),
                symbol="BTC_USDT_PERP",
                timeframe="1m",
                received_at=BASE + timedelta(minutes=2),
            )
        with self.assertRaises(ProviderResponseError):
            normalize_okx_current_candles(
                candle_payload([], code="51000"),
                symbol="BTC_USDT_PERP",
                timeframe="1m",
                received_at=BASE,
            )

    def test_current_endpoint_mapping_is_exact_for_supported_timeframes(self) -> None:
        source = OkxPublicCurrentMarketSource(base_url="https://example.invalid")
        expected = {"1m": "1m", "15m": "15m", "1h": "1H", "4h": "4H"}
        for timeframe, provider_bar in expected.items():
            with self.subTest(timeframe=timeframe):
                parsed = urlparse(source.build_candles_url(
                    symbol="BTC_USDT_PERP", timeframe=timeframe
                ))
                self.assertEqual(parsed.path, "/api/v5/market/candles")
                query = parse_qs(parsed.query)
                self.assertEqual(query, {
                    "instId": ["BTC-USDT-SWAP"],
                    "bar": [provider_bar],
                })

    def test_ticker_endpoint_is_public_allowlist_shape(self) -> None:
        source = OkxPublicCurrentMarketSource(base_url="https://example.invalid")
        parsed = urlparse(source.build_ticker_url(symbol="BTC_USDT_PERP"))
        self.assertEqual(parsed.path, "/api/v5/market/ticker")
        self.assertEqual(parse_qs(parsed.query), {"instId": ["BTC-USDT-SWAP"]})


if __name__ == "__main__":
    unittest.main()
