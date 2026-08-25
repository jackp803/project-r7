from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from brokers.okx_shadow import OKXShadowCredentials, OKXShadowProviderReader, OKXShadowReaderConfig
from integration import ShadowComposition
from market_data import normalize_okx_current_candles, normalize_okx_ticker
from risk import RiskPolicy, RiskProposal
from storage import open_operational_mode_store
from strategy import RUNTIME_FAMILY, RUNTIME_VERSION, compute_content_hash, parse_strategy_definition

UTC = timezone.utc
BASE_URL = "https://openapi.okx.com"
FIRST = datetime(2026, 8, 25, 4, 15, 0, tzinfo=UTC)
SECOND = datetime(2026, 8, 25, 4, 16, 0, tzinfo=UTC)

PUBLIC_TIME = "/api/v5/public/time"
ACCOUNT_CONFIG = "/api/v5/account/config"
BALANCE = "/api/v5/account/balance?ccy=USDT"
POSITIONS = "/api/v5/account/positions?instId=BTC-USDT-SWAP"
LEVERAGE = "/api/v5/account/leverage-info?instId=BTC-USDT-SWAP&mgnMode=isolated"
PENDING = "/api/v5/trade/orders-pending?instId=BTC-USDT-SWAP&instType=SWAP"
FILLS = "/api/v5/trade/fills?instId=BTC-USDT-SWAP&instType=SWAP"
EXPECTED = (PUBLIC_TIME, ACCOUNT_CONFIG, BALANCE, POSITIONS, LEVERAGE, PENDING, FILLS)


def _ms(value: datetime) -> str:
    return str(int(value.timestamp() * 1000))


def _responses(now: datetime) -> dict:
    return {
        PUBLIC_TIME: {"code": "0", "data": [{"ts": _ms(now)}]},
        ACCOUNT_CONFIG: {
            "code": "0",
            "data": [
                {
                    "acctLv": "2",
                    "posMode": "net_mode",
                    "uid": "synthetic-subaccount-uid",
                    "mainUid": "synthetic-main-uid",
                    "perm": "read_only",
                }
            ],
        },
        BALANCE: {"code": "0", "data": [{"details": [{"ccy": "USDT", "availBal": "1000"}]}]},
        POSITIONS: {"code": "0", "data": []},
        LEVERAGE: {
            "code": "0",
            "data": [{"instId": "BTC-USDT-SWAP", "mgnMode": "isolated", "lever": "3"}],
        },
        PENDING: {"code": "0", "data": []},
        FILLS: {"code": "0", "data": []},
    }


class _AuditTransport:
    def __init__(self, responses: dict) -> None:
        self.responses = responses
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        return self.responses[request.request_path]

    @property
    def mutation_requests(self):
        return tuple(request for request in self.requests if request.method != "GET")


def _reader(now: datetime, transport: _AuditTransport):
    return OKXShadowProviderReader(
        credentials=OKXShadowCredentials("synthetic-key", "synthetic-secret", "synthetic-passphrase"),
        config=OKXShadowReaderConfig(
            rest_base_url=BASE_URL,
            operator_confirmed_rest_base_url=BASE_URL,
            expected_account_level="2",
            expected_position_mode="net_mode",
        ),
        transport=transport,
        utc_now_provider=lambda: now,
    )


def _market(now: datetime):
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
        open_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        rows.append(
            [
                _ms(open_time),
                str(close),
                str(close + 1),
                str(close - 1),
                str(close),
                "100",
                "100",
                "1000",
                "1",
            ]
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
        "strategy_id": "gate-c-e2e",
        "strategy_version": "1.0.0",
        "name": "Gate C E2E",
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
        version="gate-c-e2e-policy",
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


def _enter_shadow(store) -> None:
    store.initialize(
        "RESEARCH",
        changed_at="2026-08-25T04:00:00Z",
        changed_by="product-owner",
        reason_codes=["GATE_C_E2E_BASELINE"],
        evidence_ref="gate-c-e2e-baseline",
    )
    store.transition(
        "SHADOW",
        expected_revision=0,
        changed_at="2026-08-25T04:00:01Z",
        changed_by="product-owner",
        reason_codes=["SHADOW_ONLY_E2E"],
        evidence_ref="shadow-only-e2e",
    )


def _run(composition: ShadowComposition, now: datetime):
    snapshot, candles = _market(now)
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


class GateCShadowNoSubmitE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "shadow-e2e.sqlite3"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_restart_requires_new_provider_reconciliation_before_shadow_planning_is_safe_again(self):
        first_store = open_operational_mode_store(self.path)
        _enter_shadow(first_store)
        first_transport = _AuditTransport(_responses(FIRST))
        first = ShadowComposition(
            mode_store=first_store,
            provider_reader=_reader(FIRST, first_transport),
        )
        first_result = _run(first, FIRST)
        self.assertTrue(first_result.ready_for_hypothetical_new_exposure)
        self.assertTrue(first_store.recover().shadow_planning_safe)
        first_store.close()

        restored = open_operational_mode_store(self.path)
        recovery = restored.recover()
        self.assertEqual("RECONCILIATION_REQUIRED", recovery.status)
        self.assertTrue(recovery.fresh_reconciliation_required)
        self.assertFalse(recovery.shadow_planning_safe)

        second_transport = _AuditTransport(_responses(SECOND))
        second = ShadowComposition(
            mode_store=restored,
            provider_reader=_reader(SECOND, second_transport),
        )
        second_result = _run(second, SECOND)
        self.assertTrue(second_result.ready_for_hypothetical_new_exposure)
        self.assertTrue(restored.recover().shadow_planning_safe)
        self.assertNotEqual(first_result.provider_observation_ref, second_result.provider_observation_ref)
        restored.close()

        for transport in (first_transport, second_transport):
            self.assertEqual(EXPECTED, tuple(request.request_path for request in transport.requests))
            self.assertEqual((), transport.mutation_requests)
            self.assertTrue(all(request.method == "GET" for request in transport.requests))

    def test_healthy_shadow_batch_has_exact_public_time_plus_private_get_allowlist_and_zero_mutations(self):
        store = open_operational_mode_store(self.path)
        _enter_shadow(store)
        transport = _AuditTransport(_responses(FIRST))
        composition = ShadowComposition(mode_store=store, provider_reader=_reader(FIRST, transport))
        result = _run(composition, FIRST)

        self.assertTrue(result.ready_for_hypothetical_new_exposure)
        self.assertEqual(EXPECTED, tuple(request.request_path for request in transport.requests))
        self.assertEqual(1, sum(request.request_path == PUBLIC_TIME for request in transport.requests))
        self.assertEqual(6, sum(request.authenticated for request in transport.requests))
        self.assertEqual((), transport.mutation_requests)
        self.assertFalse(any("order" in name.lower() and "pending" not in name.lower() for name in composition.capability_manifest()))
        store.close()


if __name__ == "__main__":
    unittest.main()
