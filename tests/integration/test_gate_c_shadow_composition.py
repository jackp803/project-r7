from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from brokers.okx_shadow import OKXShadowCredentials, OKXShadowProviderReader, OKXShadowReaderConfig
from integration import SHADOW_PLANNING_PROFILE, ShadowComposition, ShadowCompositionError
from market_data import MarketSnapshot, normalize_okx_current_candles, normalize_okx_ticker
from risk import RiskPolicy, RiskProposal, derive_gate_c_risk_context
from storage import open_operational_mode_store
from strategy import RUNTIME_FAMILY, RUNTIME_VERSION, compute_content_hash, parse_strategy_definition

UTC = timezone.utc
NOW = datetime(2026, 8, 25, 4, 15, 0, tzinfo=UTC)
BASE_URL = "https://openapi.okx.com"
RAW_BALANCE = "12345.6789"
RAW_UID = "raw-subaccount-uid-must-not-persist"
RAW_MAIN_UID = "raw-main-uid-must-not-persist"

PUBLIC_TIME = "/api/v5/public/time"
ACCOUNT_CONFIG = "/api/v5/account/config"
BALANCE = "/api/v5/account/balance?ccy=USDT"
POSITIONS = "/api/v5/account/positions?instId=BTC-USDT-SWAP"
LEVERAGE = "/api/v5/account/leverage-info?instId=BTC-USDT-SWAP&mgnMode=isolated"
PENDING = "/api/v5/trade/orders-pending?instId=BTC-USDT-SWAP&instType=SWAP"
FILLS = "/api/v5/trade/fills?instId=BTC-USDT-SWAP&instType=SWAP"
EXPECTED_BATCH_PATHS = (PUBLIC_TIME, ACCOUNT_CONFIG, BALANCE, POSITIONS, LEVERAGE, PENDING, FILLS)


def _ms(value: datetime) -> str:
    return str(int(value.timestamp() * 1000))


def _responses(*, now: datetime = NOW, permission: str = "read_only") -> dict:
    return {
        PUBLIC_TIME: {"code": "0", "data": [{"ts": _ms(now)}]},
        ACCOUNT_CONFIG: {
            "code": "0",
            "data": [{"acctLv": "2", "posMode": "net_mode", "uid": RAW_UID, "mainUid": RAW_MAIN_UID, "perm": permission}],
        },
        BALANCE: {"code": "0", "data": [{"details": [{"ccy": "USDT", "availBal": RAW_BALANCE}]}]},
        POSITIONS: {"code": "0", "data": []},
        LEVERAGE: {"code": "0", "data": [{"instId": "BTC-USDT-SWAP", "mgnMode": "isolated", "lever": "3"}]},
        PENDING: {"code": "0", "data": []},
        FILLS: {"code": "0", "data": []},
    }


class _Transport:
    def __init__(self, responses: dict) -> None:
        self.responses = responses
        self.requests = []

    def send(self, request):
        self.requests.append(request)
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


def _market_inputs(*, now: datetime = NOW):
    snapshot = normalize_okx_ticker(
        {"code": "0", "msg": "", "data": [{"instId": "BTC-USDT-SWAP", "last": "64000", "bidPx": "63999", "askPx": "64001", "ts": _ms(now)}]},
        symbol="BTC_USDT_PERP",
        received_at=now,
    )
    rows = []
    for hour, close in ((3, 13), (2, 12), (1, 11), (0, 10)):
        opened = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        rows.append([_ms(opened), str(close), str(close + 1), str(close - 1), str(close), "100", "100", "1000", "1"])
    candles = normalize_okx_current_candles(
        {"code": "0", "msg": "", "data": rows},
        symbol="BTC_USDT_PERP",
        timeframe="1h",
        received_at=now,
    )
    return snapshot, candles


def _sma(name: str) -> dict:
    return {"primitive": "SMA", "field": "close", "window": {"parameter": name}}


def _strategy():
    definition = {
        "schema_version": "contracts-v0.1",
        "strategy_id": "gate-c-shadow-sma",
        "strategy_version": "1.0.0",
        "name": "Gate C Shadow SMA",
        "symbol": "BTC_USDT_PERP",
        "required_timeframes": ["1h"],
        "parameters": {"fast": 2, "slow": 3},
        "rules": {
            "dsl_version": "0.1",
            "long": {"operator": "GT", "left": _sma("fast"), "right": _sma("slow")},
            "short": {"operator": "LT", "left": _sma("fast"), "right": _sma("slow")},
        },
        "runtime_compatibility": {"runtime_family": RUNTIME_FAMILY, "runtime_version": RUNTIME_VERSION},
        "content_hash": "",
        "created_at": "2026-08-25T00:00:00Z",
    }
    definition["content_hash"] = compute_content_hash(definition)
    return parse_strategy_definition(definition)


def _policy() -> RiskPolicy:
    return RiskPolicy(
        version="gate-c-shadow-policy-test-v0.1",
        max_margin=Decimal("100"), max_notional=Decimal("10000"), max_leverage=Decimal("20"),
        min_reward_risk=Decimal("2"), max_estimated_cost=Decimal("5"), max_trades_per_day=10,
        max_open_positions=1, max_drawdown=Decimal("0.20"), max_consecutive_losses=5,
        max_intent_age_seconds=60, max_hold_seconds=3600, plan_ttl_seconds=30, margin_mode="ISOLATED",
    )


def _proposal() -> RiskProposal:
    return RiskProposal(
        quantity=Decimal("0.001"), notional=Decimal("64"), margin=Decimal("3.2"), leverage=Decimal("20"),
        estimated_max_loss=Decimal("1"), estimated_cost=Decimal("0.1"), reward_amount=Decimal("3"),
        required_stop_level=Decimal("63000"), required_target_level=Decimal("65000"),
    )


def _enter_shadow(store) -> None:
    store.initialize("RESEARCH", changed_at="2026-08-25T04:00:00Z", changed_by="product-owner", reason_codes=["GATE_C_TEST_BASELINE"], evidence_ref="gate-c-test-baseline")
    store.transition("SHADOW", expected_revision=0, changed_at="2026-08-25T04:00:01Z", changed_by="product-owner", reason_codes=["SHADOW_ONLY_TEST_AUTHORITY"], evidence_ref="shadow-only-test-authority")


def _run(
    composition: ShadowComposition,
    snapshot,
    candles,
    *,
    strategy_time: datetime = NOW,
    risk_time: datetime | None = None,
    risk_clock=None,
):
    if risk_clock is None:
        decided_at = strategy_time if risk_time is None else risk_time
        risk_clock = lambda: decided_at
    return composition.run_cycle(
        strategy=_strategy(), candles=candles, market_snapshot=snapshot,
        risk_policy=_policy(), risk_proposal=_proposal(), strategy_evaluation_time=strategy_time,
        risk_time_provider=risk_clock,
        kill_switch_active=False, trades_today=0, consecutive_losses=0, drawdown=Decimal("0.01"),
        strategy_stop_level="63000", strategy_target_level="65000", max_hold_seconds=900,
    )


class GateCShadowCompositionIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "gate-c-shadow.sqlite3"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_healthy_owner_surfaces_produce_non_authoritative_shadow_decision_and_sanitized_checkpoint(self):
        store = open_operational_mode_store(self.db_path)
        _enter_shadow(store)
        transport = _Transport(_responses())
        composition = ShadowComposition(mode_store=store, provider_reader=_reader(transport))
        snapshot, candles = _market_inputs()
        result = _run(composition, snapshot, candles)

        self.assertTrue(result.provider_read_healthy)
        self.assertEqual("LONG", result.signal["direction"])
        self.assertTrue(result.ready_for_hypothetical_new_exposure)
        self.assertEqual(SHADOW_PLANNING_PROFILE, result.planning_evidence.profile_version)
        self.assertEqual("APPROVE", result.planning_evidence.risk_decision)
        self.assertEqual("SHADOW", result.planning_evidence.operational_mode)
        self.assertTrue(result.planning_evidence.hypothetical_new_exposure_allowed)
        self.assertFalse(result.planning_evidence.provider_submit_reachable)
        self.assertFalse(result.planning_evidence.provider_mutation_reachable)
        self.assertFalse(hasattr(result, "trade_intent"))
        self.assertFalse(hasattr(result, "risk_decision"))
        self.assertFalse(hasattr(result, "hypothetical_trade_plan"))
        self.assertFalse(hasattr(result.planning_evidence, "trade_plan_id"))
        self.assertIsNotNone(result.shadow_checkpoint_id)
        self.assertEqual((), result.reason_codes)

        recovery = store.recover()
        self.assertEqual("SHADOW", recovery.current_mode.mode)
        self.assertTrue(recovery.shadow_planning_safe)
        durable = recovery.last_shadow_checkpoint.payload
        durable_text = repr(durable)
        for forbidden in (RAW_BALANCE, RAW_UID, RAW_MAIN_UID, "fake-key", "fake-secret", "fake-passphrase"):
            self.assertNotIn(forbidden, durable_text)
        self.assertNotIn("runtime_available_balance", durable)
        self.assertEqual(EXPECTED_BATCH_PATHS, tuple(request.request_path for request in transport.requests))
        self.assertTrue(all(request.method == "GET" for request in transport.requests))
        store.close()

    def test_advancing_clock_reproduces_old_pre_provider_boundary_and_new_clock_runs_after_observation(self):
        provider_now = NOW + timedelta(seconds=1)
        risk_now = NOW + timedelta(seconds=2)
        snapshot, candles = _market_inputs()

        legacy_transport = _Transport(_responses(now=provider_now))
        legacy_read = _reader(legacy_transport, now=provider_now).observe()
        legacy_derivation = derive_gate_c_risk_context(
            snapshot,
            legacy_read,
            risk_evaluation_time=NOW,
            kill_switch_active=False,
            trades_today=0,
            consecutive_losses=0,
            drawdown=Decimal("0.01"),
        )
        self.assertIn("GATE_C_SHADOW_OBSERVATION_TIME_INVALID", legacy_derivation.reason_codes)
        self.assertFalse(legacy_derivation.safe_for_new_exposure)

        store = open_operational_mode_store(self.db_path)
        _enter_shadow(store)
        transport = _Transport(_responses(now=provider_now))
        composition = ShadowComposition(
            mode_store=store,
            provider_reader=_reader(transport, now=provider_now),
        )

        def post_provider_clock():
            self.assertEqual(EXPECTED_BATCH_PATHS, tuple(request.request_path for request in transport.requests))
            return risk_now

        result = _run(
            composition,
            snapshot,
            candles,
            strategy_time=NOW,
            risk_clock=post_provider_clock,
        )
        self.assertTrue(result.provider_read_healthy)
        self.assertTrue(result.ready_for_hypothetical_new_exposure)
        self.assertNotIn("GATE_C_SHADOW_OBSERVATION_TIME_INVALID", result.reason_codes)
        store.close()

    def test_provider_observation_genuinely_after_risk_clock_remains_fail_closed(self):
        provider_now = NOW + timedelta(seconds=3)
        risk_now = NOW + timedelta(seconds=2)
        store = open_operational_mode_store(self.db_path)
        _enter_shadow(store)
        transport = _Transport(_responses(now=provider_now))
        composition = ShadowComposition(
            mode_store=store,
            provider_reader=_reader(transport, now=provider_now),
        )
        snapshot, candles = _market_inputs()
        result = _run(
            composition,
            snapshot,
            candles,
            strategy_time=NOW,
            risk_time=risk_now,
        )
        self.assertTrue(result.provider_read_healthy)
        self.assertEqual("REJECT", result.planning_evidence.risk_decision)
        self.assertFalse(result.ready_for_hypothetical_new_exposure)
        self.assertIsNone(result.shadow_checkpoint_id)
        self.assertIn("GATE_C_SHADOW_OBSERVATION_TIME_INVALID", result.reason_codes)
        self.assertIn("E7_RISK_CONTEXT_UNSAFE", result.reason_codes)
        self.assertIn("E7_SHADOW_CHECKPOINT_NOT_RECORDED", result.reason_codes)
        self.assertNotIn("E7_PROVIDER_READ_DEGRADED", result.reason_codes)
        store.close()

    def test_authoritative_mode_must_be_shadow_before_any_provider_observation(self):
        store = open_operational_mode_store(self.db_path)
        store.initialize("RESEARCH", changed_at="2026-08-25T04:00:00Z", changed_by="product-owner", reason_codes=["RESEARCH_ONLY"], evidence_ref="research-only")
        transport = _Transport(_responses())
        composition = ShadowComposition(mode_store=store, provider_reader=_reader(transport))
        snapshot, candles = _market_inputs()
        with self.assertRaises(ShadowCompositionError) as caught:
            _run(composition, snapshot, candles)
        self.assertEqual("AUTHORITATIVE_SHADOW_MODE_REQUIRED", caught.exception.code)
        self.assertEqual([], transport.requests)
        store.close()

    def test_permission_degradation_flows_through_e5_as_reject_and_has_sanitized_stage_codes(self):
        store = open_operational_mode_store(self.db_path)
        _enter_shadow(store)
        transport = _Transport(_responses(permission="trade"))
        composition = ShadowComposition(mode_store=store, provider_reader=_reader(transport))
        snapshot, candles = _market_inputs()
        result = _run(composition, snapshot, candles)
        self.assertFalse(result.provider_read_healthy)
        self.assertEqual("REJECT", result.planning_evidence.risk_decision)
        self.assertFalse(result.ready_for_hypothetical_new_exposure)
        self.assertFalse(result.planning_evidence.hypothetical_new_exposure_allowed)
        self.assertIsNone(result.shadow_checkpoint_id)
        self.assertIn("E7_PROVIDER_READ_DEGRADED", result.reason_codes)
        self.assertIn("E7_RISK_CONTEXT_UNSAFE", result.reason_codes)
        self.assertIn("E7_SHADOW_CHECKPOINT_NOT_RECORDED", result.reason_codes)
        self.assertFalse(store.recover().shadow_planning_safe)
        self.assertTrue(all(request.method == "GET" for request in transport.requests))
        store.close()

    def test_future_market_snapshot_is_not_converted_into_new_exposure_permission(self):
        store = open_operational_mode_store(self.db_path)
        _enter_shadow(store)
        transport = _Transport(_responses())
        composition = ShadowComposition(mode_store=store, provider_reader=_reader(transport))
        healthy, candles = _market_inputs()
        future = MarketSnapshot(
            schema_version=healthy.schema_version, symbol=healthy.symbol,
            observed_at=NOW + timedelta(seconds=6), received_at=NOW,
            health_status="HEALTHY", source=healthy.source,
            last_price=healthy.last_price, best_bid=healthy.best_bid, best_ask=healthy.best_ask, freshness_ms=0,
        )
        result = _run(composition, future, candles)
        self.assertEqual("REJECT", result.planning_evidence.risk_decision)
        self.assertFalse(result.ready_for_hypothetical_new_exposure)
        self.assertIn("GATE_C_MARKET_FUTURE_AT_DECISION", result.reason_codes)
        self.assertIsNone(result.shadow_checkpoint_id)
        store.close()

    def test_stale_or_nonhealthy_market_snapshot_fails_closed_through_e5(self):
        for label, health_status, observed_at, received_at, freshness_ms in (
            ("stale", "HEALTHY", NOW - timedelta(seconds=6), NOW, 6000),
            ("nonhealthy", "DEGRADED", NOW, NOW, 0),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                store = open_operational_mode_store(Path(directory) / "market.sqlite3")
                _enter_shadow(store)
                transport = _Transport(_responses())
                composition = ShadowComposition(mode_store=store, provider_reader=_reader(transport))
                healthy, candles = _market_inputs()
                unsafe = MarketSnapshot(
                    schema_version=healthy.schema_version, symbol=healthy.symbol,
                    observed_at=observed_at, received_at=received_at,
                    health_status=health_status, source=healthy.source,
                    last_price=healthy.last_price, best_bid=healthy.best_bid, best_ask=healthy.best_ask,
                    freshness_ms=freshness_ms,
                )
                result = _run(composition, unsafe, candles)
                self.assertEqual("REJECT", result.planning_evidence.risk_decision)
                self.assertFalse(result.ready_for_hypothetical_new_exposure)
                self.assertIsNone(result.shadow_checkpoint_id)
                self.assertFalse(store.recover().shadow_planning_safe)
                self.assertTrue(all(request.method == "GET" for request in transport.requests))
                store.close()


if __name__ == "__main__":
    unittest.main()
