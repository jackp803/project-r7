import base64
import hashlib
import hmac
import unittest
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.brokers.okx_shadow import (
    CLOCK_SKEW_LIMIT_MS,
    OKXShadowConfigurationError,
    OKXShadowCredentials,
    OKXShadowProviderReader,
    OKXShadowReaderConfig,
    ShadowFillCheckpoint,
    _prepare_shadow_private_request,
)


NOW = datetime(2026, 8, 25, 4, 15, 0, tzinfo=timezone.utc)
TIMESTAMP = "2026-08-25T04:15:00.000Z"
BASE_URL = "https://openapi.okx.com"
FAKE_API_KEY = "fakeShadowReadKeyLocalTestOnly"
FAKE_SECRET = "fakeShadowReadSecretLocalTestOnly"
FAKE_PASSPHRASE = "fakeShadowReadPassphraseLocalTestOnly"
RAW_UID = "raw-subaccount-uid-must-not-persist"
RAW_MAIN_UID = "raw-main-uid-must-not-persist"
RAW_LABEL = "raw-api-label-must-not-persist"
RAW_BOUND_IP = "203.0.113.44"
RAW_BALANCE = "12345.6789"
RAW_ORDER_ID = "provider-order-id-must-not-persist"
RAW_FILL_ID = "provider-fill-id-must-not-persist"

PUBLIC_TIME = "/api/v5/public/time"
ACCOUNT_CONFIG = "/api/v5/account/config"
BALANCE = "/api/v5/account/balance?ccy=USDT"
POSITIONS = "/api/v5/account/positions?instId=BTC-USDT-SWAP"
LEVERAGE = "/api/v5/account/leverage-info?instId=BTC-USDT-SWAP&mgnMode=isolated"
PENDING = "/api/v5/trade/orders-pending?instId=BTC-USDT-SWAP&instType=SWAP"
FILLS = "/api/v5/trade/fills?instId=BTC-USDT-SWAP&instType=SWAP"
EXPECTED_BATCH_PATHS = (
    PUBLIC_TIME,
    ACCOUNT_CONFIG,
    BALANCE,
    POSITIONS,
    LEVERAGE,
    PENDING,
    FILLS,
)


def _epoch_ms(value=NOW):
    return str(int(value.timestamp() * 1000))


def _credentials(api_key=FAKE_API_KEY, secret=FAKE_SECRET, passphrase=FAKE_PASSPHRASE):
    return OKXShadowCredentials(api_key, secret, passphrase)


def _config(*, rest_base_url=BASE_URL, confirmed=BASE_URL, position_mode="net_mode"):
    return OKXShadowReaderConfig(
        rest_base_url=rest_base_url,
        operator_confirmed_rest_base_url=confirmed,
        expected_account_level="2",
        expected_position_mode=position_mode,
    )


def _healthy_responses(*, provider_time=NOW):
    return {
        PUBLIC_TIME: {"code": "0", "data": [{"ts": _epoch_ms(provider_time)}]},
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
                    "ip": RAW_BOUND_IP,
                }
            ],
        },
        BALANCE: {
            "code": "0",
            "data": [{"details": [{"ccy": "USDT", "availBal": RAW_BALANCE}]}],
        },
        POSITIONS: {"code": "0", "data": []},
        LEVERAGE: {
            "code": "0",
            "data": [
                {
                    "instId": "BTC-USDT-SWAP",
                    "mgnMode": "isolated",
                    "lever": "3",
                }
            ],
        },
        PENDING: {"code": "0", "data": []},
        FILLS: {"code": "0", "data": []},
    }


class _FakeTransport:
    def __init__(self, responses=None):
        self.responses = dict(responses or {})
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        if request.request_path not in self.responses:
            raise AssertionError("unexpected fake transport path")
        effect = self.responses[request.request_path]
        if isinstance(effect, BaseException):
            raise effect
        return effect


def _reader(*, responses=None, credentials=None, config=None, now=NOW):
    transport = _FakeTransport(_healthy_responses() if responses is None else responses)
    reader = OKXShadowProviderReader(
        credentials=_credentials() if credentials is None else credentials,
        config=_config() if config is None else config,
        transport=transport,
        utc_now_provider=lambda: now,
    )
    return reader, transport


class OKXShadowReaderTests(unittest.TestCase):
    def test_private_get_signing_includes_query_path_and_has_empty_body_without_demo_header(self):
        request = _prepare_shadow_private_request(
            _credentials(),
            _config(),
            method="GET",
            path="/api/v5/account/leverage-info",
            query={"mgnMode": "isolated", "instId": "BTC-USDT-SWAP"},
            timestamp=TIMESTAMP,
        )
        self.assertEqual("GET", request.method)
        self.assertEqual(LEVERAGE, request.request_path)
        self.assertEqual("", request.body_text)
        prehash = TIMESTAMP + "GET" + LEVERAGE
        expected = base64.b64encode(
            hmac.new(FAKE_SECRET.encode(), prehash.encode(), hashlib.sha256).digest()
        ).decode("ascii")
        self.assertEqual(expected, request.headers["OK-ACCESS-SIGN"])
        self.assertNotIn("x-simulated-trading", {key.lower() for key in request.headers})
        safe = repr(request)
        for forbidden in (FAKE_API_KEY, FAKE_SECRET, FAKE_PASSPHRASE, expected):
            self.assertNotIn(forbidden, safe)

    def test_clock_skew_at_policy_limit_is_accepted(self):
        responses = _healthy_responses(
            provider_time=NOW - timedelta(milliseconds=CLOCK_SKEW_LIMIT_MS)
        )
        reader, _ = _reader(responses=responses)
        observation = reader.observe()
        self.assertTrue(observation.healthy)
        self.assertEqual(CLOCK_SKEW_LIMIT_MS, observation.clock_skew_ms)
        self.assertEqual("HEALTHY", observation.clock_status)
        self.assertEqual(6, observation.private_get_count)

    def test_clock_skew_over_policy_limit_fails_before_any_private_read(self):
        responses = _healthy_responses(
            provider_time=NOW - timedelta(milliseconds=CLOCK_SKEW_LIMIT_MS + 1)
        )
        reader, transport = _reader(responses=responses)
        observation = reader.observe()
        self.assertFalse(observation.healthy)
        self.assertEqual(("CLOCK_SKEW_EXCEEDED",), observation.reason_codes)
        self.assertIsNone(observation.runtime_available_balance)
        self.assertEqual(0, observation.private_get_count)
        self.assertEqual([PUBLIC_TIME], [request.request_path for request in transport.requests])

    def test_permission_must_be_exactly_read_only_and_aborts_before_other_private_reads(self):
        for permission in ("trade", "withdraw", "read_only,trade", "", None):
            with self.subTest(permission=permission):
                responses = _healthy_responses()
                responses[ACCOUNT_CONFIG]["data"][0]["perm"] = permission
                reader, transport = _reader(responses=responses)
                observation = reader.observe()
                self.assertFalse(observation.healthy)
                self.assertEqual(("PERMISSION_NOT_READ_ONLY",), observation.reason_codes)
                self.assertIsNone(observation.runtime_available_balance)
                self.assertEqual(1, observation.private_get_count)
                self.assertEqual(
                    [PUBLIC_TIME, ACCOUNT_CONFIG],
                    [request.request_path for request in transport.requests],
                )

    def test_healthy_batch_uses_every_and_only_gate_c_allowlisted_private_get(self):
        reader, transport = _reader()
        observation = reader.observe()
        self.assertTrue(observation.healthy)
        self.assertEqual(EXPECTED_BATCH_PATHS, tuple(request.request_path for request in transport.requests))
        self.assertEqual(6, observation.private_get_count)
        self.assertEqual("read_only", observation.permission_category)
        self.assertTrue(observation.account_config_known)
        self.assertEqual("2", observation.account_level)
        self.assertEqual("net_mode", observation.position_mode)
        self.assertEqual("SUBACCOUNT", observation.subaccount_status)
        self.assertTrue(observation.usdt_balance_known)
        self.assertEqual(Decimal(RAW_BALANCE), observation.runtime_available_balance)
        self.assertEqual(observation.observed_at, observation.sanitized_observation.observed_at)
        self.assertTrue(observation.position_known)
        self.assertFalse(observation.unexpected_exposure)
        self.assertTrue(observation.isolated_leverage_known)
        self.assertTrue(observation.isolated_leverage_ok)
        self.assertEqual(0, observation.pending_order_count)
        self.assertEqual(0, observation.recent_fill_window_count)
        self.assertEqual(0, observation.new_unreconciled_fill_count)

    def test_runtime_balance_is_same_batch_sensitive_data_and_sanitized_projection_excludes_it(self):
        reader, _ = _reader()
        result = reader.observe()
        self.assertTrue(result.healthy)
        self.assertEqual(Decimal(RAW_BALANCE), result.runtime_available_balance)
        self.assertTrue(result.sanitized_observation.usdt_balance_known)
        self.assertEqual(result.observed_at, result.sanitized_observation.observed_at)

        loggable = repr(result)
        self.assertNotIn(RAW_BALANCE, loggable)
        self.assertIn("runtime_available_balance=<redacted>", loggable)

        durable = asdict(result.sanitized_observation)
        self.assertNotIn("runtime_available_balance", durable)
        self.assertNotIn("available_balance", durable)
        self.assertNotIn(RAW_BALANCE, repr(durable))

    def test_zero_runtime_balance_is_known_and_valid(self):
        responses = _healthy_responses()
        responses[BALANCE]["data"][0]["details"][0]["availBal"] = "0"
        reader, _ = _reader(responses=responses)
        result = reader.observe()
        self.assertTrue(result.healthy)
        self.assertTrue(result.usdt_balance_known)
        self.assertEqual(Decimal("0"), result.runtime_available_balance)
        self.assertNotIn("runtime_available_balance", asdict(result.sanitized_observation))

    def test_invalid_runtime_balance_fails_closed_and_never_exposes_usable_value(self):
        cases = ("-0.01", "NaN", "Infinity", "not-a-decimal", "")
        for value in cases:
            with self.subTest(value=value):
                responses = _healthy_responses()
                responses[BALANCE]["data"][0]["details"][0]["availBal"] = value
                reader, transport = _reader(responses=responses)
                result = reader.observe()
                self.assertFalse(result.healthy)
                self.assertEqual(("BALANCE_USDT_MALFORMED",), result.reason_codes)
                self.assertFalse(result.usdt_balance_known)
                self.assertIsNone(result.runtime_available_balance)
                self.assertEqual(
                    [PUBLIC_TIME, ACCOUNT_CONFIG, BALANCE],
                    [request.request_path for request in transport.requests],
                )
                if value:
                    self.assertNotIn(value, repr(result))

    def test_non_get_and_non_allowlisted_private_request_are_denied_before_transport(self):
        transport = _FakeTransport()
        with self.assertRaises(OKXShadowConfigurationError) as caught:
            _prepare_shadow_private_request(
                _credentials(),
                _config(),
                method="POST",
                path="/api/v5/account/config",
                query=None,
                timestamp=TIMESTAMP,
            )
        self.assertEqual("PRIVATE_METHOD_DENIED", caught.exception.code)
        with self.assertRaises(OKXShadowConfigurationError) as caught:
            _prepare_shadow_private_request(
                _credentials(),
                _config(),
                method="GET",
                path="/api/v5/trade/order",
                query={"ordId": "forbidden"},
                timestamp=TIMESTAMP,
            )
        self.assertEqual("PRIVATE_ENDPOINT_DENIED", caught.exception.code)
        self.assertEqual([], transport.requests)

    def test_shadow_reader_public_capability_graph_contains_no_submit_or_mutation_methods(self):
        reader, _ = _reader()
        public_callables = {
            name
            for name in dir(reader)
            if not name.startswith("_") and callable(getattr(reader, name))
        }
        forbidden = {
            "submit",
            "submit_entry",
            "place_order",
            "cancel_order",
            "amend_order",
            "close_position",
            "set_leverage",
            "set_position_mode",
            "set_account_mode",
            "transfer",
            "withdraw",
            "deposit",
            "request",
            "send",
        }
        self.assertTrue(forbidden.isdisjoint(public_callables))
        self.assertEqual({"observe"}, public_callables)

    def test_different_valid_credentials_do_not_change_reachable_public_capabilities(self):
        first, _ = _reader(credentials=_credentials())
        second, _ = _reader(
            credentials=_credentials(
                api_key="differentFakeKey",
                secret="differentFakeSecret",
                passphrase="differentFakePassphrase",
            )
        )
        first_surface = {name for name in dir(first) if not name.startswith("_")}
        second_surface = {name for name in dir(second) if not name.startswith("_")}
        self.assertEqual(first_surface, second_surface)
        self.assertFalse(any("submit" in name.lower() for name in first_surface))
        self.assertFalse(any("cancel" in name.lower() for name in first_surface))
        self.assertFalse(any("amend" in name.lower() for name in first_surface))

    def test_production_shadow_private_requests_never_add_demo_header(self):
        reader, transport = _reader()
        self.assertTrue(reader.observe().healthy)
        private_requests = [request for request in transport.requests if request.authenticated]
        self.assertEqual(6, len(private_requests))
        for request in private_requests:
            lowered = {key.lower() for key in request.headers}
            self.assertNotIn("x-simulated-trading", lowered)
            self.assertEqual("GET", request.method)
            self.assertEqual("", request.body_text)

    def test_domain_must_be_explicit_okx_https_and_match_operator_confirmation(self):
        invalid = (
            ("https://example.com", "https://example.com"),
            ("http://openapi.okx.com", "http://openapi.okx.com"),
            ("https://openapi.okx.com/api/v5", "https://openapi.okx.com/api/v5"),
            ("https://openapi.okx.com", "https://regional.okx.com"),
        )
        for configured, confirmed in invalid:
            with self.subTest(configured=configured, confirmed=confirmed):
                with self.assertRaises(OKXShadowConfigurationError):
                    _config(rest_base_url=configured, confirmed=confirmed)

    def test_public_observation_and_errors_redact_credentials_sensitive_account_values_and_provider_ids(self):
        reader, _ = _reader()
        healthy = reader.observe()
        self.assertEqual(Decimal(RAW_BALANCE), healthy.runtime_available_balance)
        combined = repr(healthy) + repr(healthy.sanitized_observation) + repr(reader) + repr(_credentials())
        for forbidden in (
            FAKE_API_KEY,
            FAKE_SECRET,
            FAKE_PASSPHRASE,
            RAW_UID,
            RAW_MAIN_UID,
            RAW_LABEL,
            RAW_BOUND_IP,
            RAW_BALANCE,
        ):
            self.assertNotIn(forbidden, combined)

        responses = _healthy_responses()
        responses[PENDING] = {
            "code": "0",
            "data": [
                {
                    "instId": "BTC-USDT-SWAP",
                    "ordId": RAW_ORDER_ID,
                    "clOrdId": "also-sensitive-client-order-id",
                }
            ],
        }
        reader, _ = _reader(responses=responses)
        pending = reader.observe()
        self.assertEqual(("UNEXPECTED_PENDING_ORDER",), pending.reason_codes)
        self.assertNotIn(RAW_ORDER_ID, repr(pending))
        self.assertNotIn("also-sensitive-client-order-id", repr(pending))
        self.assertNotIn(RAW_BALANCE, repr(pending))

        responses = _healthy_responses()
        responses[FILLS] = {
            "code": "0",
            "data": [
                {
                    "instId": "BTC-USDT-SWAP",
                    "tradeId": RAW_FILL_ID,
                    "ordId": RAW_ORDER_ID,
                    "fillTime": _epoch_ms(),
                }
            ],
        }
        reader, _ = _reader(responses=responses)
        fills = reader.observe()
        self.assertEqual(("NEW_UNRECONCILED_FILL_ACTIVITY",), fills.reason_codes)
        self.assertNotIn(RAW_FILL_ID, repr(fills))
        self.assertNotIn(RAW_ORDER_ID, repr(fills))
        self.assertNotIn(RAW_BALANCE, repr(fills))

    def test_transport_exception_material_is_suppressed_from_loggable_observation(self):
        responses = _healthy_responses()
        responses[ACCOUNT_CONFIG] = RuntimeError(
            f"do not leak {FAKE_API_KEY} {FAKE_SECRET} {FAKE_PASSPHRASE}"
        )
        reader, _ = _reader(responses=responses)
        observation = reader.observe()
        self.assertEqual(("ACCOUNT_CONFIG_TRANSPORT_FAILURE",), observation.reason_codes)
        loggable = repr(observation)
        self.assertNotIn(FAKE_API_KEY, loggable)
        self.assertNotIn(FAKE_SECRET, loggable)
        self.assertNotIn(FAKE_PASSPHRASE, loggable)
        self.assertIsNone(observation.runtime_available_balance)

    def test_unexpected_position_pending_order_and_new_fill_fail_closed(self):
        cases = []

        position = _healthy_responses()
        position[POSITIONS] = {
            "code": "0",
            "data": [
                {
                    "instId": "BTC-USDT-SWAP",
                    "mgnMode": "isolated",
                    "posSide": "net",
                    "pos": "0.001",
                }
            ],
        }
        cases.append((position, "UNEXPECTED_POSITION_EXPOSURE"))

        pending = _healthy_responses()
        pending[PENDING] = {
            "code": "0",
            "data": [{"instId": "BTC-USDT-SWAP", "ordId": RAW_ORDER_ID}],
        }
        cases.append((pending, "UNEXPECTED_PENDING_ORDER"))

        fills = _healthy_responses()
        fills[FILLS] = {
            "code": "0",
            "data": [{"instId": "BTC-USDT-SWAP", "tradeId": RAW_FILL_ID, "fillTime": _epoch_ms()}],
        }
        cases.append((fills, "NEW_UNRECONCILED_FILL_ACTIVITY"))

        for responses, expected in cases:
            with self.subTest(expected=expected):
                reader, _ = _reader(responses=responses)
                observation = reader.observe()
                self.assertFalse(observation.healthy)
                self.assertEqual((expected,), observation.reason_codes)
                self.assertNotIn(RAW_BALANCE, repr(observation))

    def test_malformed_balance_wrong_margin_and_fill_checkpoint_regression_fail_closed(self):
        malformed = _healthy_responses()
        malformed[BALANCE] = {"code": "0", "data": [{"details": []}]}
        reader, _ = _reader(responses=malformed)
        malformed_result = reader.observe()
        self.assertEqual(("BALANCE_USDT_UNKNOWN",), malformed_result.reason_codes)
        self.assertFalse(malformed_result.usdt_balance_known)
        self.assertIsNone(malformed_result.runtime_available_balance)

        wrong_margin = _healthy_responses()
        wrong_margin[LEVERAGE] = {
            "code": "0",
            "data": [{"instId": "BTC-USDT-SWAP", "mgnMode": "cross", "lever": "3"}],
        }
        reader, _ = _reader(responses=wrong_margin)
        self.assertEqual(
            ("LEVERAGE_MARGIN_PREREQUISITE_MISMATCH",),
            reader.observe().reason_codes,
        )

        regression = _healthy_responses()
        regression[FILLS] = {
            "code": "0",
            "data": [
                {
                    "instId": "BTC-USDT-SWAP",
                    "fillTime": str(int(NOW.timestamp() * 1000) - 10_000),
                }
            ],
        }
        prior = ShadowFillCheckpoint(int(NOW.timestamp() * 1000), 1)
        reader, _ = _reader(responses=regression)
        self.assertEqual(
            ("FILL_CHECKPOINT_REGRESSED",),
            reader.observe(previous_fill_checkpoint=prior).reason_codes,
        )

    def test_known_fill_checkpoint_allows_already_reconciled_recent_window_without_provider_ids(self):
        timestamp = int(NOW.timestamp() * 1000)
        responses = _healthy_responses()
        responses[FILLS] = {
            "code": "0",
            "data": [
                {"instId": "BTC-USDT-SWAP", "tradeId": RAW_FILL_ID, "fillTime": str(timestamp)}
            ],
        }
        prior = ShadowFillCheckpoint(timestamp, 1)
        reader, _ = _reader(responses=responses)
        observation = reader.observe(previous_fill_checkpoint=prior)
        self.assertTrue(observation.healthy)
        self.assertEqual(1, observation.recent_fill_window_count)
        self.assertEqual(0, observation.new_unreconciled_fill_count)
        self.assertEqual(prior, observation.fill_checkpoint)
        self.assertEqual(Decimal(RAW_BALANCE), observation.runtime_available_balance)
        self.assertNotIn(RAW_FILL_ID, repr(observation))
        self.assertNotIn(RAW_BALANCE, repr(observation))

    def test_account_identity_and_position_mode_mismatch_fail_closed_without_raw_identity_persistence(self):
        main_account = _healthy_responses()
        main_account[ACCOUNT_CONFIG]["data"][0]["mainUid"] = RAW_UID
        reader, _ = _reader(responses=main_account)
        observation = reader.observe()
        self.assertEqual(("DEDICATED_SUBACCOUNT_NOT_CONFIRMED",), observation.reason_codes)
        self.assertNotIn(RAW_UID, repr(observation))
        self.assertIsNone(observation.runtime_available_balance)

        wrong_mode = _healthy_responses()
        wrong_mode[ACCOUNT_CONFIG]["data"][0]["posMode"] = "long_short_mode"
        reader, _ = _reader(responses=wrong_mode)
        self.assertEqual(("POSITION_MODE_MISMATCH",), reader.observe().reason_codes)

    def test_shadow_reader_has_no_demo_adapter_submit_dependency_or_websocket_surface(self):
        reader, _ = _reader()
        public_surface = {name.lower() for name in dir(reader) if not name.startswith("_")}
        for forbidden in (
            "websocket",
            "ws",
            "submit_entry",
            "retry_entry",
            "prepare_entry",
            "cancel_order",
            "amend_order",
        ):
            self.assertNotIn(forbidden, public_surface)
        self.assertEqual("OKX", reader.provider)
        self.assertEqual("production_read_only_shadow", reader.environment)


if __name__ == "__main__":
    unittest.main()
