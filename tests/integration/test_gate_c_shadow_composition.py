from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from brokers.okx_shadow import (
    OKXShadowCredentials,
    OKXShadowProviderReader,
    OKXShadowReaderConfig,
)
from integration import ShadowComposition, ShadowCompositionError
from market_data import MarketSnapshot, normalize_okx_current_candles, normalize_okx_ticker
from risk import RiskPolicy, RiskProposal
from storage import open_operational_mode_store
from strategy import RUNTIME_FAMILY, RUNTIME_VERSION, compute_content_hash, parse_strategy_definition

UTC = timezone.utc
NOW = datetime(2026, 8, 25, 4, 15, 0, tzinfo=UTC)
BASE_URL = "https://openapi.okx.com"
RAW_BALANCE = "12345.6789"
RAW_UID = "raw-subaccount-uid-never-durable"
RAW_MAIN_UID = "raw-main-uid-never-durable"

PUBLIC_TIME = "/api/v5/public/time"
ACCOUNT_CONFIG = "/api/v5/account/config"
BALANCE = "/api/v5/account/balance?ccy=USDT"
POSITIONS = "/api/v5/account/positions?instId=BTC-USDT-SWAP"
LEVERAGE = "/api/v5/account/leverage-info?instId=BTC-USDT-SWAP&mgnMode=isolated"
PENDING = "/api/v5/trade/orders-pending?instId=BTC-USDT-SWAP&instType=SWAP"
FILLS = "/api/v5/trade/fills?instId=BTC-USDT-SWAP&instType=SWAP"
EXPECTED_PATHS = (PUBLIC_TIME, ACCOUNT_CONFIG, BALANCE, POSITIONS, LEVERAGE, PENDING, FILLS)


def _ms(value: datetime) -> str:
    return str(int(value.timestamp() * 1000))


def _ticker(now: datetime) -> dict:
    return {
        "code": "0",
        "msg": "",
        "data": [
            {
                "instId": "BTC-USDT-SWAP",
                "last": "64000",
                "bidPx": "63999",
                "askPx": "64001",
                "ts": _ms(now),
            }
        ],
    }


def _candle_row(open_time: datetime, close: int, *, confirm: str = "1") -> list[str]:
    return [
        _ms(open_time),
        str(close),
        str(close + 1),
        str(close - 1),
        str(close),
        "100",
        "100",
        "1000",
        confirm,
    ]


def _market_inputs(now: datetime = NOW):
    snapshot = normalize_okx_ticker(
        _ticker(now),
        symbol="BTC_USDT_PERP",
        received_at=now,
    )
    rows = [
        _candle_row(now.replace(hour=3, minute=0, second=0), 13),
        _candle_row(now.replace(hour=2, minute=0, second=0), 12),
        _candle_row(now.replace(hour=1, minute=0, second=0), 11),
        _candle_row(now.replace(hour=0, minute=0, second=0), 10),
    ]
    candles = normalize_okx_current_candles(
        {"code": "0", "msg": "", "data": rows},
        symbol="BTC_USDT_PERP",
        timeframe="1h",
        received_at=now,
    )
    return snapshot, candles


def _sma(parameter: str) -> dict:
    return {"primitive": "SMA", "field": "close", "window": {"parameter": parameter}}


def _strategy():
    definition = {
        "schema_version": "contracts-v0.1",
        "strategy_id": "gate-c-shadow-sma",
        "strategy_version": "1.0.0",
        "name": "Gate C Shadow SMA",
        "symbol": "BTC_USDT_PERP",
        "required_timeframes": ["1h"],
        "parameters": {"fast_window": 2, "slow_window": 3},
        "rules": {
            "dsl_version": "0.1",
            "long": {"operator": "GT", "left": _sma("fast_window"), "right": _sma("slow_window")},
            "short": {"operator": "LT", "left": _sma("fast_window"), "right": _sma("slow_window")},
        },
        "runtime_compatibility": {
            "runtime_family": RUNTIME_FAMILY,
            "runtime_version": RUNTIME_VERSION,
        },
        "content_hash": "",
        "created_at": "2026-08-25T00:00:00Z",
    }
    definition["content_hash"] = compute_content_hash(definition)
    return parse_strategy_definition(definition)


def _policy() -> RiskPolicy:
    return RiskPolicy(
        version="gate-c-shadow-policy-test-v0.1",
        max_margin=Decimal("100"),
        max_notional=Decimal("10000"),
        max_leverage=Decimal("20"),
        min_reward_risk=Decimal("2"),
        max_estimated_cost=Decimal("5"),
        max_trades_per_day=10,
        max_open_positions=1,
        max_drawdown=Decimal("0.20"),
        max_consecutive_losses=5,
        max_intent_age_seconds=60,
        max_hold_seconds=3600,
        plan_ttl_seconds=30,
        margin_mode="ISOLATED",
    )


def _proposal() -> RiskProposal:
    return RiskProposal(
        quantity=Decimal("0.001"),
        notional=Decimal("64"),
        margin=Decimal("3.2"),
        leverage=Decimal("20"),
        estimated_max_loss=Decimal("1"),
        estimated_cost=Decimal("0.1"),
        reward_amount=Decimal("3"),
        required_stop_level=Decimal("63000"),
        required_target_level=Decimal("65000"),
    )


def _responses(now: datetime = NOW, *, permission: str = "read_only") -> dict:
    return {
        PUBLIC_TIME: {"code": "0", "data": [{"ts": _ms(now)}]},
        ACCOUNT_CONFIG: {
            "code": "0",
            "data": [
                {
                    "acctLv": "2",
                    "posMode": "net_mode",
                    "uid": RAW_UID,
                    "mainUid": RAW_MAIN_UID,
                    "perm": permission,
                    "label": "raw-label-never-durable",
                    "ip": "203.0.113.10",
                }
            ],
        },
        BALANCE: {"code": "0", "data": [{"details": [{"ccy": "USDT", "availBal": RAW_BALANCE}]}]},
        POSITIONS: {"code": "0", "data": []},
        LEVERAGE: {
            "code": "0",
            "data": [{"instId": "BTC-USDT-SWAP", "mgnMode": "isolated", "lever": "3"}],
        },
        PENDING: {"code": "0", "data": []},
        FILLS: {"code": "0", "data": []},
    }


class _Transport:
    def __init__(self, responses: dict) -> None:
        self.responses = responses
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        if request.request_path not in self.responses:
            raise AssertionError("unexpected fake request")
        return self.responses[request.request_path]


def _reader(transport: _Transport, *, now: datetime = NOW):
    return OKXShadowProviderReader(
        credentials=OKXShadowCredentials("fake-key", "fake-secret", "fake-passphrase"),
        config=OKXShadowReaderConfig(
            rest_base_url=BASE_URL,
            operator_confirmed_rest_base_url=BASE_URL,
            expected_account_level="2",
            expected_position_mode="net_mode",
        ),
        transport=transport,
        utc_now_provider=lambda: now,
    )


def _enter_shadow(store) -> None:
    store.initialize(
        "RESEARCH",
        changed_at="2026-08-25T04:00:00Z",
        changed_by="product-owner",
        reason_codes=["GATE_C_TEST_BASELINE"],
        evidence_ref="gate-c-test-baseline",
    )
    store.transition(
        "SHADOW",
        expected_revision=0,
        changed_at="2026-08-25T04:00:01Z",
        changed_by="product-owner",
        reason_codes=["SHADOW_ONLY_TEST_AUTHORITY"],
        evidence_ref="shadow-only-test-authority",
    )


def _run(composition: ShadowComposition, snapshot, candles, *, now: datetime = NOW):
    return composition.run_cycle(
        strategy=_strategy(),
        candles=candles,
        market_snapshot=snapshot,
        risk_policy=_policy(),
        risk_proposal=_proposal(),
        risk_evaluation_time=now,
        kill_switch_active=False,
        trades_today=0,
        consecutive_losses=0,
        drawdown=Decimal("0.01"),
        strategy_stop_level="63000",
        strategy_target_level="65000",
        max_hold_seconds=900,
    )


class GateCShadowCompositionIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "gate-c-shadow.sqlite3"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_healthy_owner_surfaces_produce_hypothetical_plan_and_sanitized_checkpoint_only(self):
        store = open_operational_mode_store(self.db_path)
        _enter_shadow(store)
        transport = _Transport(_responses())
        composition = ShadowComposition(mode_store=store, provider_reader=_reader(transport))
        snapshot, candles = _market_inputs()

        result = _run(composition, snapshot, candles)

        self.assertTrue(result.provider_read_healthy)
        self.assertEqual("LONG", result.signal["direction"])
        self.assertEqual("APPROVE", result.risk_decision["decision"])
        self.assertTrue(result.ready_for_hypothetical_new_exposure)
        self.assertIsNotNone(result.hypothetical_trade_plan)
        self.assertEqual("BTC_USDT_PERP", result.hypothetical_trade_plan["symbol"])
        self.assertIsNotNone(result.shadow_checkpoint_id)
        recovery = store.recover()
        self.assertEqual("SHADOW", recovery.current_mode.mode)
        self.assertTrue(recovery.shadow_planning_safe)
        durable = recovery.last_shadow_checkpoint.payload
        durable_text = repr(durable)
        for forbidden in (RAW_BALANCE, RAW_UID, RAW_MAIN_UID, "fake-key", "fake-secret", "fake-passphrase"):
            self.assertNotIn(forbidden, durable_text)
        self.assertNotIn("exact_account_balance", durable)
        self.assertNotIn("runtime_available_balance", durable)
        self.assertEqual(0, durable["pending_order_count"])
        self.assertEqual(0, durable["unreconciled_fill_count"])
        self.assertEqual(EXPECTED_PATHS, tuple(request.request_path for request in transport.requests))
        self.assertTrue(all(request.method == "GET" for request in transport.requests))
        store.close()

    def test_authoritative_mode_must_be_shadow_before_any_provider_observation(self):
        store = open_operational_mode_store(self.db_path)
        store.initialize(
            "RESEARCH",
            changed_at="2026-08-25T04:00:00Z",
            changed_by="product-owner",
            reason_codes=["RESEARCH_ONLY"],
            evidence_ref="research-only",
        )
        transport = _Transport(_responses())
        composition = ShadowComposition(mode_store=store, provider_reader=_reader(transport))
        snapshot, candles = _market_inputs()
        with self.assertRaises(ShadowCompositionError) as caught:
            _run(composition, snapshot, candles)
        self.assertEqual("AUTHORITATIVE_SHADOW_MODE_REQUIRED", caught.exception.code)
        self.assertEqual([], transport.requests)
        store.close()

    def test_e4_permission_degradation_flows_through_e5_as_reject_and_never_checkpoints(self):
        store = open_operational_mode_store(self.db_path)
        _enter_shadow(store)
        transport = _Transport(_responses(permission="trade"))
        composition = ShadowComposition(mode_store=store, provider_reader=_reader(transport))
        snapshot, candles = _market_inputs()

        result = _run(composition, snapshot, candles)

        self.assertFalse(result.provider_read_healthy)
        self.assertEqual("REJECT", result.risk_decision["decision"])
        self.assertFalse(result.ready_for_hypothetical_new_exposure)
        self.assertIsNone(result.hypothetical_trade_plan)
        self.assertIsNone(result.shadow_checkpoint_id)
        self.assertIn("GATE_C_SHADOW_PERMISSION_NOT_READ_ONLY", result.reason_codes)
        recovery = store.recover()
        self.assertEqual("RECONCILIATION_REQUIRED", recovery.status)
        self.assertFalse(recovery.shadow_planning_safe)
        self.assertTrue(all(request.method == "GET" for request in transport.requests))
        store.close()

    def test_future_market_snapshot_is_not_converted_into_new_exposure_permission(self):
        store = open_operational_mode_store(self.db_path)
        _enter_shadow(store)
        transport = _Transport(_responses())
        composition = ShadowComposition(mode_store=store, provider_reader=_reader(transport))
        healthy_snapshot, candles = _market_inputs()
        future = MarketSnapshot(
            schema_version=healthy_snapshot.schema_version,
            symbol=healthy_snapshot.symbol,
            observed_at=NOW + timedelta(seconds=6),
            received_at=NOW,
            health_status="HEALTHY",
            source=healthy_snapshot.source,
            last_price=healthy_snapshot.last_price,
            best_bid=healthy_snapshot.best_bid,
            best_ask=healthy_snapshot.best_ask,
            freshness_ms=0,
        )

        result = _run(composition, future, candles)

        self.assertEqual("REJECT", result.risk_decision["decision"])
        self.assertFalse(result.ready_for_hypothetical_new_exposure)
        self.assertIn("GATE_C_MARKET_FUTURE_AT_DECISION", result.reason_codes)
        self.assertIsNone(result.shadow_checkpoint_id)
        store.close()


if __name__ == "__main__":
    unittest.main()
