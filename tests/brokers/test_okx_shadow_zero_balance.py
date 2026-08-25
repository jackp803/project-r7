import unittest
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal

from src.brokers.okx_shadow import (
    OKXShadowCredentials,
    OKXShadowProviderReader,
    OKXShadowReaderConfig,
)


NOW = datetime(2026, 8, 25, 14, 55, 0, tzinfo=timezone.utc)
BASE_URL = "https://openapi.okx.com"
RAW_BALANCE = "12345.6789"

PUBLIC_TIME = "/api/v5/public/time"
ACCOUNT_CONFIG = "/api/v5/account/config"
BALANCE = "/api/v5/account/balance?ccy=USDT"
POSITIONS = "/api/v5/account/positions?instId=BTC-USDT-SWAP"
LEVERAGE = "/api/v5/account/leverage-info?instId=BTC-USDT-SWAP&mgnMode=isolated"
PENDING = "/api/v5/trade/orders-pending?instId=BTC-USDT-SWAP&instType=SWAP"
FILLS = "/api/v5/trade/fills?instId=BTC-USDT-SWAP&instType=SWAP"
EXPECTED_PATHS = (PUBLIC_TIME, ACCOUNT_CONFIG, BALANCE, POSITIONS, LEVERAGE, PENDING, FILLS)


def _epoch_ms(value=NOW):
    return str(int(value.timestamp() * 1000))


def _healthy_responses():
    return {
        PUBLIC_TIME: {"code": "0", "data": [{"ts": _epoch_ms()}]},
        ACCOUNT_CONFIG: {
            "code": "0",
            "data": [
                {
                    "acctLv": "2",
                    "posMode": "net_mode",
                    "uid": "fake-subaccount-uid",
                    "mainUid": "fake-main-account-uid",
                    "perm": "read_only",
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
                {"instId": "BTC-USDT-SWAP", "mgnMode": "isolated", "lever": "3"}
            ],
        },
        PENDING: {"code": "0", "data": []},
        FILLS: {"code": "0", "data": []},
    }


class _FakeTransport:
    def __init__(self, responses):
        self.responses = responses
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        return self.responses[request.request_path]


def _reader(responses):
    transport = _FakeTransport(responses)
    reader = OKXShadowProviderReader(
        credentials=OKXShadowCredentials(
            "fake-read-key",
            "fake-read-secret",
            "fake-read-passphrase",
        ),
        config=OKXShadowReaderConfig(
            rest_base_url=BASE_URL,
            operator_confirmed_rest_base_url=BASE_URL,
            expected_account_level="2",
            expected_position_mode="net_mode",
        ),
        transport=transport,
        utc_now_provider=lambda: NOW,
    )
    return reader, transport


class OKXShadowZeroBalanceNormalizationTests(unittest.TestCase):
    def test_exact_usdt_request_with_empty_details_normalizes_known_runtime_zero(self):
        responses = _healthy_responses()
        responses[BALANCE] = {"code": "0", "data": [{"details": []}]}
        reader, transport = _reader(responses)

        result = reader.observe()

        self.assertTrue(result.healthy)
        self.assertTrue(result.usdt_balance_known)
        self.assertEqual(Decimal("0"), result.runtime_available_balance)
        self.assertEqual(EXPECTED_PATHS, tuple(request.request_path for request in transport.requests))

    def test_explicit_zero_and_positive_usdt_detail_behaviors_remain_unchanged(self):
        for value in ("0", RAW_BALANCE):
            with self.subTest(value=value):
                responses = _healthy_responses()
                responses[BALANCE]["data"][0]["details"][0]["availBal"] = value
                reader, _ = _reader(responses)
                result = reader.observe()
                self.assertTrue(result.healthy)
                self.assertTrue(result.usdt_balance_known)
                self.assertEqual(Decimal(value), result.runtime_available_balance)

    def test_wrong_currency_and_duplicate_usdt_details_fail_closed_not_zero(self):
        cases = (
            [{"ccy": "BTC", "availBal": "0"}],
            [
                {"ccy": "USDT", "availBal": "0"},
                {"ccy": "USDT", "availBal": "0"},
            ],
        )
        for details in cases:
            with self.subTest(details=details):
                responses = _healthy_responses()
                responses[BALANCE] = {"code": "0", "data": [{"details": details}]}
                reader, transport = _reader(responses)
                result = reader.observe()
                self.assertFalse(result.healthy)
                self.assertEqual(("BALANCE_USDT_UNKNOWN",), result.reason_codes)
                self.assertFalse(result.usdt_balance_known)
                self.assertIsNone(result.runtime_available_balance)
                self.assertEqual(
                    (PUBLIC_TIME, ACCOUNT_CONFIG, BALANCE),
                    tuple(request.request_path for request in transport.requests),
                )

    def test_missing_or_non_sequence_details_fail_closed(self):
        cases = (
            {},
            {"details": None},
            {"details": "not-a-sequence-of-detail-objects"},
            {"details": {"ccy": "USDT", "availBal": "0"}},
        )
        for account_object in cases:
            with self.subTest(account_object=account_object):
                responses = _healthy_responses()
                responses[BALANCE] = {"code": "0", "data": [account_object]}
                reader, _ = _reader(responses)
                result = reader.observe()
                self.assertFalse(result.healthy)
                self.assertEqual(("BALANCE_MALFORMED",), result.reason_codes)
                self.assertFalse(result.usdt_balance_known)
                self.assertIsNone(result.runtime_available_balance)

    def test_invalid_avail_bal_values_fail_closed(self):
        for value in (None, "", "-0.01", "NaN", "Infinity", "not-a-decimal"):
            with self.subTest(value=value):
                responses = _healthy_responses()
                responses[BALANCE] = {
                    "code": "0",
                    "data": [{"details": [{"ccy": "USDT", "availBal": value}]}],
                }
                reader, _ = _reader(responses)
                result = reader.observe()
                self.assertFalse(result.healthy)
                self.assertEqual(("BALANCE_USDT_MALFORMED",), result.reason_codes)
                self.assertFalse(result.usdt_balance_known)
                self.assertIsNone(result.runtime_available_balance)

    def test_provider_error_and_malformed_account_envelope_fail_closed(self):
        cases = (
            ({"code": "50000", "data": []}, "BALANCE_PROVIDER_ERROR"),
            ({"code": "0"}, "BALANCE_MALFORMED"),
            ({"code": "0", "data": []}, "BALANCE_MALFORMED"),
            ({"code": "0", "data": [{"details": []}, {"details": []}]}, "BALANCE_MALFORMED"),
            ({"code": "0", "data": ["not-an-account-object"]}, "BALANCE_MALFORMED"),
        )
        for payload, reason in cases:
            with self.subTest(reason=reason):
                responses = _healthy_responses()
                responses[BALANCE] = payload
                reader, _ = _reader(responses)
                result = reader.observe()
                self.assertFalse(result.healthy)
                self.assertEqual((reason,), result.reason_codes)
                self.assertFalse(result.usdt_balance_known)
                self.assertIsNone(result.runtime_available_balance)

    def test_runtime_balance_is_redacted_from_repr_and_public_projection(self):
        responses = _healthy_responses()
        reader, _ = _reader(responses)
        result = reader.observe()

        self.assertEqual(Decimal(RAW_BALANCE), result.runtime_available_balance)
        self.assertNotIn(RAW_BALANCE, repr(result))
        public_projection = asdict(result.sanitized_observation)
        self.assertNotIn("runtime_available_balance", public_projection)
        self.assertNotIn(RAW_BALANCE, repr(public_projection))
        self.assertTrue(public_projection["usdt_balance_known"])

    def test_allowlist_get_only_no_demo_and_no_mutation_capability_are_unchanged(self):
        responses = _healthy_responses()
        reader, transport = _reader(responses)
        result = reader.observe()
        self.assertTrue(result.healthy)
        self.assertEqual(EXPECTED_PATHS, tuple(request.request_path for request in transport.requests))
        for request in transport.requests:
            self.assertEqual("GET", request.method)
            self.assertNotIn("x-simulated-trading", {key.lower() for key in request.headers})

        public_callables = {
            name
            for name in dir(reader)
            if not name.startswith("_") and callable(getattr(reader, name))
        }
        self.assertEqual({"observe"}, public_callables)
        forbidden_fragments = (
            "submit",
            "place",
            "cancel",
            "amend",
            "close",
            "leverage",
            "transfer",
            "withdraw",
            "deposit",
            "request",
            "send",
        )
        self.assertFalse(
            any(fragment in name.lower() for name in public_callables for fragment in forbidden_fragments)
        )


if __name__ == "__main__":
    unittest.main()
