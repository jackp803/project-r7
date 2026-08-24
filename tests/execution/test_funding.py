import hashlib
import inspect
import json
import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import src.execution.funding as funding_module
from src.brokers.paper import PaperBroker
from src.execution.funding import (
    DEFAULT_PAPER_ZERO_FUNDING_MODEL,
    FundingEvidenceError,
    PaperZeroFundingModel,
    funding_evidence_identity_material,
    paper_zero_source_material,
    produce_paper_zero_funding_evidence,
    stable_funding_evidence_id,
)
from src.execution.models import (
    SCHEMA_VERSION,
    OrderRequest,
    OrderStatus,
    Side,
    stable_client_order_id,
    stable_order_request_id,
)


class PaperFundingEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.opened_at = "2026-08-24T05:05:00Z"
        self.closed_at = "2026-08-24T05:15:00Z"
        self.calculated_at = datetime(2026, 8, 24, 5, 15, 1, tzinfo=timezone.utc)

    def _plan(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "trade_plan_id": "plan-funding-001",
            "symbol": "BTC_USDT_PERP",
        }
        values.update(changes)
        return values

    def _position(self, **changes):
        values = {
            "schema_version": "contracts-v0.1",
            "position_id": "position-funding-001",
            "symbol": "BTC_USDT_PERP",
            "actual_quantity": "0",
            "reconciliation_status": "CONSISTENT",
            "opened_at": self.opened_at,
            "broker_state_observed_at": self.closed_at,
        }
        values.update(changes)
        return values

    def _produce(self, *, plan=None, position=None, calculated_at=None, model=None):
        kwargs = {}
        if model is not None:
            kwargs["model"] = model
        return produce_paper_zero_funding_evidence(
            self._plan() if plan is None else plan,
            self._position() if position is None else position,
            calculated_at=self.calculated_at if calculated_at is None else calculated_at,
            **kwargs,
        )

    def test_valid_exact_interval_zero_model_emits_exact_canonical_shape(self):
        evidence = self._produce()
        expected_fields = {
            "schema_version",
            "funding_evidence_profile_version",
            "funding_evidence_id",
            "source_kind",
            "source",
            "source_version",
            "source_material_hash",
            "source_record_count",
            "source_complete_through",
            "trade_plan_id",
            "position_id",
            "symbol",
            "interval_start",
            "interval_end",
            "interval_semantics",
            "status",
            "funding_cost",
            "cost_currency",
            "calculated_at",
        }
        self.assertEqual(expected_fields, set(evidence))
        self.assertEqual("contracts-v0.1", evidence["schema_version"])
        self.assertEqual("funding-allocation-v0.1", evidence["funding_evidence_profile_version"])
        self.assertEqual("PAPER_MODEL", evidence["source_kind"])
        self.assertEqual("R7_PAPER_FUNDING_MODEL", evidence["source"])
        self.assertEqual("paper-zero-funding-v0.1", evidence["source_version"])
        self.assertEqual(0, evidence["source_record_count"])
        self.assertEqual(self.closed_at, evidence["source_complete_through"])
        self.assertEqual("plan-funding-001", evidence["trade_plan_id"])
        self.assertEqual("position-funding-001", evidence["position_id"])
        self.assertEqual("BTC_USDT_PERP", evidence["symbol"])
        self.assertEqual(self.opened_at, evidence["interval_start"])
        self.assertEqual(self.closed_at, evidence["interval_end"])
        self.assertEqual("START_INCLUSIVE_END_EXCLUSIVE", evidence["interval_semantics"])
        self.assertEqual("ZERO_CONFIRMED", evidence["status"])
        self.assertEqual("0", evidence["funding_cost"])
        self.assertEqual("USDT", evidence["cost_currency"])
        self.assertEqual("2026-08-24T05:15:01Z", evidence["calculated_at"])
        self.assertRegex(evidence["source_material_hash"], r"^[0-9a-f]{64}$")
        self.assertRegex(evidence["funding_evidence_id"], r"^fundev_[0-9a-f]{64}$")

    def test_zero_confirmation_is_positive_model_assertion_not_empty_result_inference(self):
        material = paper_zero_source_material(self._plan(), self._position())
        self.assertEqual(
            "FUNDING_EQUALS_ZERO_FOR_EVERY_INSTANT_IN_EXACT_INTERVAL",
            material["assertion"],
        )
        self.assertEqual(
            "MODEL_COMPLETE_THROUGH_EXACT_INTERVAL_END",
            material["completeness_assertion"],
        )
        self.assertEqual(self.opened_at, material["interval_start"])
        self.assertEqual(self.closed_at, material["interval_end"])
        self.assertEqual(self.closed_at, material["source_complete_through"])
        self.assertEqual(0, material["source_record_count"])
        self.assertEqual("ZERO_CONFIRMED", material["status"])
        self.assertEqual("0", material["funding_cost"])

    def test_source_material_hash_is_exact_sorted_compact_utf8_sha256(self):
        material = paper_zero_source_material(self._plan(), self._position())
        payload = json.dumps(
            material,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        expected_hash = hashlib.sha256(payload).hexdigest()
        evidence = self._produce()
        self.assertEqual(expected_hash, evidence["source_material_hash"])

        changed_plan = self._produce(plan=self._plan(trade_plan_id="plan-funding-002"))
        self.assertNotEqual(evidence["source_material_hash"], changed_plan["source_material_hash"])

    def test_funding_evidence_identity_uses_exact_contract_fields_and_excludes_calculated_at(self):
        evidence = self._produce()
        material = funding_evidence_identity_material(evidence)
        self.assertEqual(17, len(material))
        self.assertNotIn("funding_evidence_id", material)
        self.assertNotIn("calculated_at", material)
        expected_id = "fundev_" + hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(expected_id, evidence["funding_evidence_id"])
        self.assertEqual(expected_id, stable_funding_evidence_id(evidence))

    def test_exact_same_material_is_idempotent_and_later_calculated_at_keeps_same_id(self):
        first = self._produce()
        second = self._produce()
        later = self._produce(calculated_at=self.calculated_at + timedelta(hours=1))
        self.assertEqual(first, second)
        self.assertEqual(first["funding_evidence_id"], later["funding_evidence_id"])
        self.assertEqual(first["source_material_hash"], later["source_material_hash"])
        self.assertNotEqual(first["calculated_at"], later["calculated_at"])

    def test_changed_plan_position_symbol_or_interval_changes_identity(self):
        baseline = self._produce()
        changed_plan = self._produce(plan=self._plan(trade_plan_id="plan-funding-002"))
        changed_position = self._produce(position=self._position(position_id="position-funding-002"))
        changed_symbol = self._produce(
            plan=self._plan(symbol="ETH_USDT_PERP"),
            position=self._position(symbol="ETH_USDT_PERP"),
        )
        changed_start = self._produce(
            position=self._position(opened_at="2026-08-24T05:06:00Z")
        )
        changed_end = self._produce(
            position=self._position(broker_state_observed_at="2026-08-24T05:16:00Z"),
            calculated_at=datetime(2026, 8, 24, 5, 16, 1, tzinfo=timezone.utc),
        )
        for changed in (
            changed_plan,
            changed_position,
            changed_symbol,
            changed_start,
            changed_end,
        ):
            self.assertNotEqual(baseline["funding_evidence_id"], changed["funding_evidence_id"])

    def test_unsupported_source_or_model_version_never_falls_back_to_zero(self):
        cases = (
            replace(DEFAULT_PAPER_ZERO_FUNDING_MODEL, source_kind="BROKER_LEDGER"),
            replace(DEFAULT_PAPER_ZERO_FUNDING_MODEL, source="UNKNOWN_SOURCE"),
            replace(DEFAULT_PAPER_ZERO_FUNDING_MODEL, source_version="paper-zero-funding-v9"),
            replace(DEFAULT_PAPER_ZERO_FUNDING_MODEL, zero_assertion="NO_ROWS_RETURNED"),
            replace(DEFAULT_PAPER_ZERO_FUNDING_MODEL, completeness_assertion="UNKNOWN"),
            replace(DEFAULT_PAPER_ZERO_FUNDING_MODEL, status="INCLUDED"),
            replace(DEFAULT_PAPER_ZERO_FUNDING_MODEL, funding_cost="1"),
            replace(DEFAULT_PAPER_ZERO_FUNDING_MODEL, cost_currency="BTC"),
            replace(DEFAULT_PAPER_ZERO_FUNDING_MODEL, source_record_count=1),
        )
        for model in cases:
            with self.subTest(model=model):
                with self.assertRaises(FundingEvidenceError) as caught:
                    self._produce(model=model)
                self.assertEqual("UNSUPPORTED_FUNDING_MODEL_VERSION", caught.exception.code)

        with self.assertRaises(FundingEvidenceError) as caught:
            produce_paper_zero_funding_evidence(
                self._plan(),
                self._position(),
                calculated_at=self.calculated_at,
                model=object(),
            )
        self.assertEqual("UNSUPPORTED_FUNDING_SOURCE", caught.exception.code)

    def test_nonflat_unknown_mismatch_and_reconciliation_required_positions_fail_closed(self):
        for quantity in ("0.0001", "-0.0001", "NaN", "Infinity"):
            with self.subTest(quantity=quantity):
                with self.assertRaises(FundingEvidenceError):
                    self._produce(position=self._position(actual_quantity=quantity))

        for status in ("UNKNOWN", "MISMATCH", "RECONCILIATION_REQUIRED", ""):
            with self.subTest(status=status):
                with self.assertRaises(FundingEvidenceError) as caught:
                    self._produce(position=self._position(reconciliation_status=status))
                self.assertEqual("FINAL_POSITION_NOT_CONSISTENT", caught.exception.code)

    def test_plan_position_symbol_mismatch_and_blank_identifiers_fail_closed(self):
        with self.assertRaises(FundingEvidenceError) as caught:
            self._produce(position=self._position(symbol="ETH_USDT_PERP"))
        self.assertEqual("PLAN_POSITION_SYMBOL_MISMATCH", caught.exception.code)

        for plan in (
            self._plan(trade_plan_id=""),
            self._plan(symbol=""),
        ):
            with self.subTest(plan=plan):
                with self.assertRaises(FundingEvidenceError):
                    self._produce(plan=plan)

        with self.assertRaises(FundingEvidenceError):
            self._produce(position=self._position(position_id=""))

    def test_schema_missing_fields_and_malformed_intervals_fail_closed(self):
        with self.assertRaises(FundingEvidenceError):
            self._produce(plan=self._plan(schema_version="contracts-v9"))
        with self.assertRaises(FundingEvidenceError):
            self._produce(position=self._position(schema_version="contracts-v9"))

        plan_missing = self._plan()
        del plan_missing["trade_plan_id"]
        with self.assertRaises(FundingEvidenceError):
            self._produce(plan=plan_missing)

        position_missing = self._position()
        del position_missing["opened_at"]
        with self.assertRaises(FundingEvidenceError):
            self._produce(position=position_missing)

        malformed_cases = (
            self._position(opened_at="2026-08-24T05:05:00+00:00"),
            self._position(broker_state_observed_at="not-a-time"),
            self._position(opened_at=self.closed_at),
            self._position(opened_at="2026-08-24T05:16:00Z"),
        )
        for position in malformed_cases:
            with self.subTest(position=position):
                with self.assertRaises(FundingEvidenceError):
                    self._produce(position=position)

    def test_optional_closed_at_must_match_authoritative_flat_observation(self):
        valid = self._produce(position=self._position(closed_at=self.closed_at))
        self.assertEqual(self.closed_at, valid["interval_end"])
        with self.assertRaises(FundingEvidenceError) as caught:
            self._produce(
                position=self._position(closed_at="2026-08-24T05:14:59Z")
            )
        self.assertEqual("FINAL_POSITION_CLOSED_AT_CONFLICT", caught.exception.code)

    def test_calculated_at_must_be_utc_and_at_or_after_interval_end(self):
        boundary = self._produce(calculated_at=self.closed_at)
        self.assertEqual(self.closed_at, boundary["calculated_at"])

        with self.assertRaises(FundingEvidenceError) as caught:
            self._produce(calculated_at="2026-08-24T05:14:59Z")
        self.assertEqual("CALCULATED_BEFORE_INTERVAL_END", caught.exception.code)

        with self.assertRaises(FundingEvidenceError):
            self._produce(calculated_at="2026-08-24T05:15:01+00:00")
        with self.assertRaises(FundingEvidenceError):
            self._produce(calculated_at=datetime(2026, 8, 24, 5, 15, 1))

    def test_no_random_uuid_e5_private_dependency_network_or_credentials(self):
        source = inspect.getsource(funding_module)
        self.assertNotIn("uuid", source.lower())
        self.assertNotIn("src.position", source)
        self.assertNotIn("FundingEvidence", source.replace("FundingEvidenceError", ""))
        for forbidden_import in ("requests", "httpx", "urllib", "socket", "aiohttp"):
            self.assertNotIn(f"import {forbidden_import}", source)

        evidence = self._produce()
        forbidden_fields = {
            "api_key",
            "secret_key",
            "passphrase",
            "credentials",
            "account_id",
            "broker_order_id",
            "client_order_id",
            "risk_decision_id",
            "risk_policy_version",
            "strategy_id",
            "strategy_version",
            "provider_instrument_id",
            "provider_contract_count",
            "persistence_id",
            "paper_ready",
            "live_enabled",
        }
        self.assertTrue(forbidden_fields.isdisjoint(evidence))

    def test_producer_does_not_mutate_plan_or_final_position(self):
        plan = self._plan()
        position = self._position()
        plan_before = deepcopy(plan)
        position_before = deepcopy(position)
        self._produce(plan=plan, position=position)
        self.assertEqual(plan_before, plan)
        self.assertEqual(position_before, position)

    def test_existing_paperbroker_order_and_fill_surface_remains_compatible(self):
        client_order_id = stable_client_order_id("plan-entry-regression", "entry")
        request = OrderRequest(
            schema_version=SCHEMA_VERSION,
            order_request_id=stable_order_request_id(client_order_id),
            trade_plan_id="plan-entry-regression",
            client_order_id=client_order_id,
            symbol="BTC_USDT_PERP",
            side=Side.BUY,
            order_type="MARKET",
            quantity=Decimal("0.001"),
            quantity_profile_version="base-asset-v0.1",
            quantity_unit="BASE_ASSET",
            quantity_asset="BTC",
            created_at=datetime(2026, 8, 24, 5, 0, tzinfo=timezone.utc),
        )
        broker = PaperBroker()
        opened = broker.submit_order(request)
        fill = broker.record_fill(
            request.client_order_id,
            quantity=Decimal("0.0004"),
            price=Decimal("60000"),
            filled_at=datetime(2026, 8, 24, 5, 1, tzinfo=timezone.utc),
        )
        queried = broker.query_order(request.client_order_id)
        self.assertEqual(OrderStatus.OPEN, opened.order_status)
        self.assertEqual(OrderStatus.PARTIALLY_FILLED, queried.order_status)
        self.assertEqual(Decimal("0.0004"), fill.quantity)
        self.assertIsNone(fill.position_action_id)
        self.assertIsNone(fill.position_id)
        self.assertIsNone(fill.order_role)


if __name__ == "__main__":
    unittest.main()
