from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from brokers.okx_demo import OKXCredentials, OKXDemoAdapter, OKXDemoAdapterConfig
from brokers.okx_shadow import (
    OKXShadowConfigurationError,
    OKXShadowCredentials,
    OKXShadowProviderReader,
    OKXShadowReaderConfig,
)
from integration import ShadowComposition, ShadowCompositionError
from market_data import normalize_okx_current_candles, normalize_okx_ticker
from risk import RiskPolicy, RiskProposal
from storage import OperationalModeAuthorityError, OperationalModeValidationError, open_operational_mode_store
from strategy import RUNTIME_FAMILY, RUNTIME_VERSION, compute_content_hash, parse_strategy_definition

UTC = timezone.utc
NOW = datetime(2026, 8, 25, 4, 15, 0, tzinfo=UTC)
BASE_URL = "https://openapi.okx.com"

FAKE_KEY = "synthetic-shadow-key-never-log"
FAKE_SECRET = "synthetic-shadow-secret-never-log"
FAKE_PASSPHRASE = "synthetic-shadow-passphrase-never-log"
RAW_UID = "raw-subaccount-uid-never-log"
RAW_MAIN_UID = "raw-main-uid-never-log"
RAW_LABEL = "raw-api-label-never-log"
RAW_IP = "203.0.113.77"
RAW_BALANCE = "98765.4321"
RAW_ORDER_ID = "raw-provider-order-id-never-log"
RAW_FILL_ID = "raw-provider-fill-id-never-log"
RAW_PROVIDER_MESSAGE = "raw-provider-message-never-log"

PUBLIC_TIME = "/api/v5/public/time"
ACCOUNT_CONFIG = "/api/v5/account/config"
BALANCE = "/api/v5/account/balance?ccy=USDT"
POSITIONS = "/api/v5/account/positions?instId=BTC-USDT-SWAP"
LEVERAGE = "/api/v5/account/leverage-info?instId=BTC-USDT-SWAP&mgnMode=isolated"
PENDING = "/api/v5/trade/orders-pending?instId=BTC-USDT-SWAP&instType=SWAP"
FILLS = "/api/v5/trade/fills?instId=BTC-USDT-SWAP&instType=SWAP"


def _ms(value: datetime) -> str:
    return str(int(value.timestamp() * 1000))


def _healthy_responses(now: datetime = NOW) -> dict:
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
                    "perm": "read_only",
                    "label": RAW_LABEL,
                    "ip": RAW_IP,
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


class _AuditTransport:
    def __init__(self, responses=None) -> None:
        self.responses = dict(_healthy_responses() if responses is None else responses)
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        effect = self.responses.get(request.request_path)
        if isinstance(effect, BaseException):
            raise effect
        if effect is None:
            raise AssertionError("unexpected fake request")
        return effect


def _shadow_reader(transport: _AuditTransport, *, credentials=None, now: datetime = NOW):
    return OKXShadowProviderReader(
        credentials=credentials or OKXShadowCredentials(FAKE_KEY, FAKE_SECRET, FAKE_PASSPHRASE),
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
        reason_codes=["GATE_C_SAFETY_BASELINE"],
        evidence_ref="gate-c-safety-baseline",
    )
    store.transition(
        "SHADOW",
        expected_revision=0,
        changed_at="2026-08-25T04:00:01Z",
        changed_by="product-owner",
        reason_codes=["SHADOW_ONLY_SAFETY"],
        evidence_ref="shadow-only-safety",
    )


def _market(now: datetime = NOW):
    snapshot = normalize_okx_ticker(
        {
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
        },
        symbol="BTC_USDT_PERP",
        received_at=now,
    )
    rows = []
    for hour, close in ((3, 13), (2, 12), (1, 11), (0, 10)):
        opened = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        rows.append(
            [_ms(opened), str(close), str(close + 1), str(close - 1), str(close), "100", "100", "1000", "1"]
        )
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
        "strategy_id": "gate-c-safety",
        "strategy_version": "1.0.0",
        "name": "Gate C Safety",
        "symbol": "BTC_USDT_PERP",
        "required_timeframes": ["1h"],
        "parameters": {"fast": 2, "slow": 3},
        "rules": {
            "dsl_version": "0.1",
            "long": {"operator": "GT", "left": _sma("fast"), "right": _sma("slow")},
            "short": {"operator": "LT", "left": _sma("fast"), "right": _sma("slow")},
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
        version="gate-c-safety-policy",
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
    )


class GateCShadowCompositionSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "gate-c-safety.sqlite3"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_submit_capable_okx_demo_adapter_is_rejected_before_transport(self):
        store = open_operational_mode_store(self.db_path)
        _enter_shadow(store)
        transport = _AuditTransport({})
        demo = OKXDemoAdapter(
            credentials=OKXCredentials("fake-demo-key", "fake-demo-secret", "fake-demo-passphrase"),
            config=OKXDemoAdapterConfig(expected_account_level="2", expected_position_mode="net_mode"),
            transport=transport,
            timestamp_provider=lambda: "2026-08-25T04:15:00.000Z",
        )
        with self.assertRaises(ShadowCompositionError) as caught:
            ShadowComposition(mode_store=store, provider_reader=demo)  # type: ignore[arg-type]
        self.assertEqual("SHADOW_PROVIDER_READER_TYPE_REQUIRED", caught.exception.code)
        self.assertEqual([], transport.requests)
        store.close()

    def test_synthetic_credentials_do_not_change_reachable_composition_or_reader_capabilities(self):
        store = open_operational_mode_store(self.db_path)
        _enter_shadow(store)
        first_reader = _shadow_reader(_AuditTransport())
        second_reader = _shadow_reader(
            _AuditTransport(),
            credentials=OKXShadowCredentials("different-key", "different-secret", "different-passphrase"),
        )
        first = ShadowComposition(mode_store=store, provider_reader=first_reader)
        second = ShadowComposition(mode_store=store, provider_reader=second_reader)
        first_surface = {name for name in dir(first) if not name.startswith("_")}
        second_surface = {name for name in dir(second) if not name.startswith("_")}
        reader_one = {name for name in dir(first_reader) if not name.startswith("_")}
        reader_two = {name for name in dir(second_reader) if not name.startswith("_")}
        self.assertEqual(first_surface, second_surface)
        self.assertEqual(reader_one, reader_two)
        self.assertEqual({"observe", "provider", "environment"}, reader_one)
        forbidden_fragments = (
            "submit", "place", "cancel", "amend", "close", "leverage", "mode", "transfer",
            "deposit", "withdraw", "request", "send",
        )
        self.assertFalse(
            any(any(fragment in name.lower() for fragment in forbidden_fragments) for name in first_surface)
        )
        store.close()

    def test_invalid_provider_domain_is_rejected_before_composition_or_transport(self):
        transport = _AuditTransport({})
        with self.assertRaises(OKXShadowConfigurationError):
            OKXShadowProviderReader(
                credentials=OKXShadowCredentials(FAKE_KEY, FAKE_SECRET, FAKE_PASSPHRASE),
                config=OKXShadowReaderConfig(
                    rest_base_url="https://example.com",
                    operator_confirmed_rest_base_url="https://example.com",
                    expected_account_level="2",
                    expected_position_mode="net_mode",
                ),
                transport=transport,
                utc_now_provider=lambda: NOW,
            )
        self.assertEqual([], transport.requests)

    def test_e4_degradation_axes_flow_to_e5_reject_with_zero_mutations(self):
        cases = []

        clock = _healthy_responses(NOW - timedelta(seconds=6))
        cases.append(("clock", clock))

        auth = _healthy_responses()
        auth[ACCOUNT_CONFIG] = {"code": "50113", "msg": RAW_PROVIDER_MESSAGE, "data": []}
        cases.append(("auth", auth))

        account = _healthy_responses()
        account[ACCOUNT_CONFIG]["data"][0]["acctLv"] = "3"
        cases.append(("account", account))

        position = _healthy_responses()
        position[POSITIONS] = {
            "code": "0",
            "data": [{"instId": "BTC-USDT-SWAP", "mgnMode": "isolated", "posSide": "net", "pos": "1"}],
        }
        cases.append(("position", position))

        pending = _healthy_responses()
        pending[PENDING] = {"code": "0", "data": [{"instId": "BTC-USDT-SWAP", "ordId": RAW_ORDER_ID}]}
        cases.append(("pending", pending))

        fills = _healthy_responses()
        fills[FILLS] = {
            "code": "0",
            "data": [{"instId": "BTC-USDT-SWAP", "ordId": RAW_ORDER_ID, "tradeId": RAW_FILL_ID, "fillTime": _ms(NOW)}],
        }
        cases.append(("fills", fills))

        provider_error = _healthy_responses()
        provider_error[BALANCE] = {"code": "50000", "msg": RAW_PROVIDER_MESSAGE, "data": []}
        cases.append(("provider_error", provider_error))

        for name, responses in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "case.sqlite3"
                store = open_operational_mode_store(path)
                _enter_shadow(store)
                transport = _AuditTransport(responses)
                composition = ShadowComposition(mode_store=store, provider_reader=_shadow_reader(transport))
                snapshot, candles = _market()
                result = _run(composition, snapshot, candles)
                self.assertFalse(result.provider_read_healthy)
                self.assertIsNotNone(result.risk_decision)
                self.assertEqual("REJECT", result.risk_decision["decision"])
                self.assertFalse(result.ready_for_hypothetical_new_exposure)
                self.assertIsNone(result.hypothetical_trade_plan)
                self.assertIsNone(result.shadow_checkpoint_id)
                self.assertTrue(all(request.method == "GET" for request in transport.requests))
                self.assertEqual(0, sum(request.method != "GET" for request in transport.requests))
                loggable = repr(result)
                for secret in (
                    FAKE_KEY, FAKE_SECRET, FAKE_PASSPHRASE, RAW_UID, RAW_MAIN_UID, RAW_LABEL,
                    RAW_IP, RAW_BALANCE, RAW_ORDER_ID, RAW_FILL_ID, RAW_PROVIDER_MESSAGE,
                ):
                    self.assertNotIn(secret, loggable)
                store.close()

    def test_unclosed_or_future_candle_is_rejected_before_provider_transport(self):
        store = open_operational_mode_store(self.db_path)
        _enter_shadow(store)
        transport = _AuditTransport()
        composition = ShadowComposition(mode_store=store, provider_reader=_shadow_reader(transport))
        snapshot, candles = _market()

        unclosed = list(candles)
        object.__setattr__(unclosed[-1], "is_closed", False)
        with self.assertRaises(ShadowCompositionError) as caught:
            _run(composition, snapshot, unclosed)
        self.assertEqual("E1_UNFINALIZED_CANDLE_REJECTED", caught.exception.code)
        self.assertEqual([], transport.requests)

        snapshot, fresh_candles = _market()
        future = list(fresh_candles)
        object.__setattr__(future[-1], "close_time", NOW + timedelta(seconds=1))
        with self.assertRaises(ShadowCompositionError) as caught:
            _run(composition, snapshot, future)
        self.assertEqual("E1_FUTURE_CANDLE_REJECTED", caught.exception.code)
        self.assertEqual([], transport.requests)
        store.close()

    def test_paper_shaped_checkpoint_cannot_satisfy_shadow_truth_and_live_cannot_be_inferred(self):
        store = open_operational_mode_store(self.db_path)
        _enter_shadow(store)
        paper_shaped = {
            "schema_version": "contracts-v0.1",
            "provider": "OKX",
            "environment_classification": "PAPER",
            "regional_hostname_ref": "paper",
            "canonical_instrument": "BTC_USDT_PERP",
            "provider_instrument": "BTC-USDT-SWAP",
            "observed_at": "2026-08-25T04:15:00Z",
            "permission_category": "read_only",
            "market_healthy": True,
            "account_config_known": True,
            "balance_known": True,
            "position_truth_known": True,
            "isolated_leverage_known": True,
            "unexpected_exposure": False,
            "pending_order_count": 0,
            "unreconciled_fill_count": 0,
            "provider_observation_ref": "r7obs_paper_not_shadow",
            "provider_observation_hash": "sha256:" + "1" * 64,
            "reason_codes": [],
        }
        with self.assertRaises(OperationalModeValidationError):
            store.record_shadow_checkpoint(paper_shaped)
        self.assertFalse(store.recover().shadow_planning_safe)
        with self.assertRaises(OperationalModeAuthorityError):
            store.transition(
                "LIVE",
                expected_revision=1,
                changed_at="2026-08-25T04:15:01Z",
                changed_by="synthetic-test",
                reason_codes=["MUST_NOT_PROMOTE"],
                evidence_ref="must-not-promote",
            )
        self.assertEqual("SHADOW", store.recover().current_mode.mode)
        store.close()

    def test_missing_or_corrupt_e6_state_fails_closed_before_provider_transport(self):
        missing_store = open_operational_mode_store(self.db_path)
        missing_transport = _AuditTransport()
        missing = ShadowComposition(
            mode_store=missing_store,
            provider_reader=_shadow_reader(missing_transport),
        )
        with self.assertRaises(ShadowCompositionError) as caught:
            missing.recover_shadow_state()
        self.assertEqual("AUTHORITATIVE_OPERATIONAL_MODE_MISSING", caught.exception.code)
        self.assertEqual([], missing_transport.requests)
        missing_store.close()

        corrupt_path = Path(self.temp.name) / "corrupt.sqlite3"
        store = open_operational_mode_store(corrupt_path)
        _enter_shadow(store)
        store.close()

        corrupt_payload = {
            "schema_version": "contracts-v0.1",
            "provider": "OKX",
            "environment_classification": "PRODUCTION_READ_ONLY_SHADOW",
            "regional_hostname_ref": "openapi.okx.com",
            "canonical_instrument": "BTC_USDT_PERP",
            "provider_instrument": "BTC-USDT-SWAP",
            "observed_at": "2026-08-25T04:15:00Z",
            "permission_category": "read_only",
            "market_healthy": True,
            "account_config_known": True,
            "balance_known": True,
            "position_truth_known": True,
            "isolated_leverage_known": True,
            "unexpected_exposure": False,
            "pending_order_count": 0,
            "unreconciled_fill_count": 0,
            "provider_observation_ref": "r7obs_corrupt_synthetic",
            "provider_observation_hash": "sha256:" + "2" * 64,
            "reason_codes": [],
        }
        payload_json = json.dumps(
            corrupt_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        connection = sqlite3.connect(corrupt_path)
        connection.execute(
            """
            INSERT INTO shadow_provider_checkpoints (
                checkpoint_id, checkpoint_revision, mode_revision,
                observed_at, provider_observation_ref, payload_json, payload_hash
            ) VALUES (?, 0, 1, ?, ?, ?, ?)
            """,
            (
                "shadowcp_" + "0" * 64,
                corrupt_payload["observed_at"],
                corrupt_payload["provider_observation_ref"],
                payload_json,
                "sha256:" + "0" * 64,
            ),
        )
        connection.commit()
        connection.close()

        corrupt_store = open_operational_mode_store(corrupt_path)
        corrupt_transport = _AuditTransport()
        corrupt = ShadowComposition(
            mode_store=corrupt_store,
            provider_reader=_shadow_reader(corrupt_transport),
        )
        with self.assertRaises(ShadowCompositionError) as caught:
            corrupt.recover_shadow_state()
        self.assertEqual("AUTHORITATIVE_OPERATIONAL_MODE_UNSAFE", caught.exception.code)
        self.assertEqual([], corrupt_transport.requests)
        corrupt_store.close()

    def test_loggable_healthy_result_and_durable_checkpoint_redact_runtime_sensitive_material(self):
        store = open_operational_mode_store(self.db_path)
        _enter_shadow(store)
        transport = _AuditTransport(_healthy_responses())
        composition = ShadowComposition(mode_store=store, provider_reader=_shadow_reader(transport))
        snapshot, candles = _market()
        result = _run(composition, snapshot, candles)
        checkpoint_text = repr(store.recover().last_shadow_checkpoint.payload)
        combined = repr(result) + checkpoint_text
        for forbidden in (
            FAKE_KEY, FAKE_SECRET, FAKE_PASSPHRASE, RAW_UID, RAW_MAIN_UID, RAW_LABEL,
            RAW_IP, RAW_BALANCE, RAW_ORDER_ID, RAW_FILL_ID,
        ):
            self.assertNotIn(forbidden, combined)
        self.assertNotIn("runtime_available_balance", checkpoint_text)
        self.assertNotIn("exact_account_balance", checkpoint_text)
        store.close()


if __name__ == "__main__":
    unittest.main()
