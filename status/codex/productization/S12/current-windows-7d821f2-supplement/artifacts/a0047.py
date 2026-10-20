"""UNAPPLIED SOURCE DRAFT — NOT_EXECUTED, no acceptance credit.

Proposed seam tests, not existing callable API. Requires the genuine owner
flat-context fixture described in api-plan.json; never replace it with DB rows,
PaperBroker/PaperZeroFundingModel, fabricated Position or final TradeResult.
"""
import unittest
from copy import deepcopy
from datetime import timedelta

from application.trading.admission import RuntimeAdmissionError
from application.trading.provider import FakeProductProvider
from storage.runtime_models import StoredCanonicalObject

# PROPOSED test-only setup dependency. Must drive existing genuine FIXTURE
# entry/protect/exit/readback owners. Missing close seam is explicitly unresolved.
from tests.product.fixture_allocated_ledger import actual_flat_fixture_owner


class FixtureAllocatedLedgerOwnerDraftTests(unittest.TestCase):
    def setUp(self):
        self.ctx = actual_flat_fixture_owner(self)
        self.service = self.ctx.service
        self.before = self.ctx.recover()
        self.assertTrue(self.before.restart_authoritative)
        self.assertEqual('0', self.before.current_position_projection.payload['actual_quantity'])
        self.assertNotEqual('CLOSED', self.before.current_position_projection.payload['lifecycle_state'])
        self.assertIsNone(self.before.trade_result)
        self.assertEqual((), self.before.funding_evidence)

    def response(self):
        # These are scripted provider INPUT rows, never canonical evidence.
        # ctx supplies actual owner lineage and interval after real readback.
        return self.ctx.ledger_response(records=[
            self.ctx.allocated_row('fixture-debit', self.ctx.interval_start, '0.125'),
            self.ctx.allocated_row('fixture-credit', self.ctx.interval_end-timedelta(microseconds=1), '-0.025'),
        ], complete_from=self.ctx.interval_start, complete_through=self.ctx.interval_end)

    def read(self, response):
        self.service.provider = FakeProductProvider([response])
        metadata, proof = self.ctx.current_metadata()
        value = self.service.read_fixture_funding_ledger(
            trade_plan_id=self.ctx.plan_id, position_id=self.ctx.position_id,
            metadata=metadata, proof=proof, expected_revision=self.ctx.revision)
        self.assertEqual(1, len(self.service.provider.calls))
        self.assertEqual('GET', self.service.provider.calls[0]['method'])
        self.assertEqual('/r7-fixture/allocated-funding-ledger', self.service.provider.calls[0]['path'])
        self.assertIsNone(self.ctx.recover().trade_result)
        self.assertEqual((), self.ctx.recover().funding_evidence, 'Observation is not publication')
        return value

    def publish(self, observed):
        metadata, proof = self.ctx.current_metadata()
        return self.service.publish_fixture_funding_ledger(
            observed, metadata=metadata, proof=proof, expected_revision=self.ctx.revision)

    def assert_no_effect(self):
        after = self.ctx.recover()
        self.assertEqual(self.before.current_position_projection, after.current_position_projection)
        self.assertEqual(self.before.lifecycle_history, after.lifecycle_history)
        self.assertEqual((), after.funding_evidence)
        self.assertIsNone(after.trade_result)

    def test_signed_allocated_costs_bind_exact_real_interval_and_publish_through_owner(self):
        observed = self.read(self.response())
        stored = self.publish(observed)
        self.assertIsInstance(stored, StoredCanonicalObject)
        evidence = stored.payload
        self.assertEqual('BROKER_LEDGER', evidence['source_kind'])
        self.assertEqual('R7_FIXTURE_FAKE_PRODUCT_PROVIDER_LEDGER', evidence['source'])
        self.assertEqual('INCLUDED', evidence['status'])
        self.assertEqual('0.1', evidence['funding_cost'])
        self.assertEqual(2, evidence['source_record_count'])
        self.assertEqual('USDT', evidence['cost_currency'])
        self.assertEqual(self.ctx.plan_id, evidence['trade_plan_id'])
        self.assertEqual(self.ctx.position_id, evidence['position_id'])
        self.assertEqual(self.ctx.symbol, evidence['symbol'])
        self.assertEqual(self.ctx.utc(self.ctx.interval_start), evidence['interval_start'])
        self.assertEqual(self.ctx.utc(self.ctx.interval_end), evidence['interval_end'])
        self.assertEqual('START_INCLUSIVE_END_EXCLUSIVE', evidence['interval_semantics'])
        self.assertEqual(self.ctx.utc(self.ctx.interval_end), evidence['source_complete_through'])
        self.assertRegex(evidence['source_material_hash'], r'^[0-9a-f]{64}$')
        self.assertEqual((stored,), self.ctx.recover().funding_evidence)
        self.assertIsNone(self.ctx.recover().trade_result, 'Funding does not finalize E5')

    def test_same_observed_allocation_replay_is_idempotent(self):
        observed = self.read(self.response())
        first = self.publish(observed)
        second = self.publish(observed)
        self.assertEqual(first, second)
        self.assertEqual(1, len(self.ctx.recover().funding_evidence))
        self.assertEqual(1, len(self.service.provider.calls), 'No resubmission/read on publication replay')

    def test_unissued_caller_dictionary_is_not_source_authority(self):
        with self.assertRaises(RuntimeAdmissionError):
            self.publish(self.response())
        self.assert_no_effect()

    def test_incomplete_missing_foreign_duplicate_and_boundary_records_fail_without_effect(self):
        base = self.response()
        # All mutations affect only the next scripted fake-provider response.
        mutations = {
            'missing_watermark': lambda x: x.pop('complete_through'),
            'incomplete_end': lambda x: x.update(complete_through=self.ctx.utc(self.ctx.interval_end-timedelta(microseconds=1))),
            'late_coverage_start': lambda x: x.update(complete_from=self.ctx.utc(self.ctx.interval_start+timedelta(microseconds=1))),
            'foreign_plan': lambda x: x.update(trade_plan_id='another-plan'),
            'foreign_position': lambda x: x.update(position_id='another-position'),
            'foreign_symbol': lambda x: x.update(symbol='ETH_USDT_PERP'),
            'duplicate_row': lambda x: x['records'].append(deepcopy(x['records'][0])),
            'end_is_exclusive': lambda x: x['records'][0].update(event_at=self.ctx.utc(self.ctx.interval_end)),
            'before_start': lambda x: x['records'][0].update(event_at=self.ctx.utc(self.ctx.interval_start-timedelta(microseconds=1))),
            'nonfinite_cost': lambda x: x['records'][0].update(funding_cost='NaN'),
            'unsupported_currency': lambda x: x['records'][0].update(cost_currency='BTC'),
            'missing_is_not_zero': lambda x: x.update(records=[], completeness='UNAVAILABLE'),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                response = deepcopy(base); mutate(response)
                with self.assertRaises(RuntimeAdmissionError):
                    self.read(response)
                self.assert_no_effect()

    def test_observation_expires_or_changes_issuer_generation_before_publication(self):
        observed = self.read(self.response())
        self.ctx.advance(timedelta(seconds=5))  # Proposed exact existing read TTL.
        with self.assertRaises(RuntimeAdmissionError): self.publish(observed)
        self.assert_no_effect()

    def test_provider_replacement_invalidates_previously_issued_read(self):
        observed = self.read(self.response())
        self.service.provider = FakeProductProvider([])
        with self.assertRaises(RuntimeAdmissionError): self.publish(observed)
        self.assert_no_effect()

    def test_successor_process_generation_invalidates_previously_issued_read(self):
        observed = self.read(self.response())
        self.ctx.restart_owner_generation()  # Actual dispatch begin_process, no DB mutation.
        with self.assertRaises(RuntimeAdmissionError): self.publish(observed)
        self.assert_no_effect()

    def test_another_service_cannot_publish_an_issuer_bound_observation(self):
        observed = self.read(self.response())
        other = self.ctx.second_service_same_fixture_process()
        metadata, proof = self.ctx.current_metadata()
        with self.assertRaises(RuntimeAdmissionError):
            other.publish_fixture_funding_ledger(observed, metadata=metadata, proof=proof,
                                                 expected_revision=self.ctx.revision)
        self.assert_no_effect()

    def reread_after_publication(self, response):
        # A fresh real fake-provider read; the response source timestamp remains
        # fixed while actual receipt/calculation owner time may advance.
        self.service.provider = FakeProductProvider([response])
        metadata, proof = self.ctx.current_metadata()
        return self.service.read_fixture_funding_ledger(
            trade_plan_id=self.ctx.plan_id, position_id=self.ctx.position_id,
            metadata=metadata, proof=proof, expected_revision=self.ctx.revision)

    def test_fresh_read_same_source_later_calculation_retains_identity(self):
        response = self.response()
        first = self.publish(self.read(response))
        self.ctx.advance(timedelta(seconds=1))
        second = self.publish(self.reread_after_publication(deepcopy(response)))
        self.assertEqual(first.canonical_id, second.canonical_id)
        self.assertEqual(first.payload['source_material_hash'], second.payload['source_material_hash'])
        self.assertEqual((first,), self.ctx.recover().funding_evidence)
        self.assertIsNone(self.ctx.recover().trade_result)

    def test_changed_observed_allocation_same_lineage_conflicts_without_replacement(self):
        from storage.runtime_models import RuntimeConflictError
        response = self.response()
        first = self.publish(self.read(response))
        changed = deepcopy(response)
        changed['records'][0]['funding_cost'] = '0.126'
        observed = self.reread_after_publication(changed)
        with self.assertRaises(RuntimeConflictError): self.publish(observed)
        self.assertEqual((first,), self.ctx.recover().funding_evidence)
        self.assertIsNone(self.ctx.recover().trade_result)
        # Legitimate canonical conflict audit may change recovery status; never
        # assert no audit write or inject reset state to make this case pass.
