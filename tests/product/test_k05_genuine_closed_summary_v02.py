"""Genuine closed fake-provider history and read-only publication.

One genuine H16 ProductDispatch/CLOSED -> protected read-only K05 positive.
FIXTURE fake-provider ledger provenance is never relabeled PaperModel or LIVE.
"""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

import tests.product.trading_finalization_fixtures as finalization_fixtures
import tests.product.test_trading_dispatch_v02 as dispatch_fixtures
from application.cloud import trading_feedback as summaries
from application.cloud.manifest import canonical_bytes, byte_hash
from application.cloud.public_feedback import validate_public_feedback_publication
from brokers.okx_close_sizing import canonical_okx_close_sizing_hash
from storage.trading_feedback import open_trading_feedback_reader


class K05GenuineClosedSummaryTests(finalization_fixtures.FinalizationFixture, unittest.TestCase):
    def setUp(self):
        # Current genuine financial helper uses canonical.sqlite separate from
        # original admission.sqlite. The read-only port rightly requires the
        # canonical store to retain original E6 namespace+immutable definition.
        # Populate those through normal E6 owner INTAKE before real canonical
        # open, risk/plan writes, mechanical preparation or any provider claim.
        original_setup = dispatch_fixtures.TradingDispatchV02Tests.setUp
        original_open = dispatch_fixtures.open_paper_runtime_journal
        registered = []
        test = self

        def setup_with_original_e6_definition(helper):
            def open_actual_bound_canonical(path, *args, **kwargs):
                expected = helper.fixture.root/'canonical.sqlite'
                test.assertEqual(expected, path)
                owner = helper.fixture
                original = owner.e6.get_strategy(owner.identity)
                with owner.helper.platform(owner.root, owner.research, owner.helper.run_id,
                                           owner.boundary, 'canonical') as registrar:
                    registrar.intake(json.loads(original.definition_json),
                        source_actor='fixture-k05-original-immutable-definition')
                    retained = registrar.get_strategy(owner.identity)
                    test.assertEqual('FIXTURE', registrar.research_namespace)
                    test.assertEqual(original.identity, retained.identity)
                    test.assertEqual(original.content_hash, retained.content_hash)
                    test.assertEqual(original.definition_json, retained.definition_json)
                    registered.append((retained.identity, retained.content_hash))
                return original_open(path, *args, **kwargs)
            # Setup factory instrumentation only: delegates every real owner;
            # no risk/admission/financial outcome or source-result replacement.
            with patch.object(dispatch_fixtures, 'open_paper_runtime_journal',
                              side_effect=open_actual_bound_canonical):
                original_setup(helper)

        with patch.object(dispatch_fixtures.TradingDispatchV02Tests, 'setUp',
                          new=setup_with_original_e6_definition):
            finalization_fixtures.FinalizationFixture.setUp(self)
        self.assertEqual(1, len(registered))
        self.original_identity, self.original_content_hash = registered[0]
        self.assertEqual(self.fixture.identity, self.original_identity)
        self.assertEqual(canonical_okx_close_sizing_hash(self.flow.helper.plan),
                         self.flow.helper.prepared.source_plan_hash)

    def test_actual_closed_graph_private_snapshot_and_public_opt_policies_keep_exact_fake_ledger_provenance(self):
        self.settled()
        reads = self.final_reads()
        receipt = self.finalize(reads)
        graph = self.flow.assert_binding()
        self.assertEqual('READY', graph.status)
        self.assertEqual('CLOSED', graph.current_position_projection.payload['lifecycle_state'])
        result = graph.trade_result.payload
        self.assertEqual(self.funding_object.canonical_id, result['funding_evidence_id'])
        funding = next(row for row in graph.funding_evidence
                       if row.canonical_id == result['funding_evidence_id'])
        self.assertEqual('BROKER_LEDGER', funding.payload['source_kind'])
        self.assertNotEqual('paper-zero-funding-v0.1', funding.payload['source_version'])
        expected_amounts = {key:result[key] for key in ('gross_pnl','net_pnl','total_fees')}
        expected_amounts['funding_cost'] = funding.payload['funding_cost']
        self.assertTrue(all(type(value) is str for value in expected_amounts.values()))
        before_calls = deepcopy(self.provider.calls)
        before_dispatch = self.service.dispatch.recover(self.service.run_id)
        before_batch = self.service.dispatch.finalization_batch(self.service.run_id, self.close_id)
        before_receipt = self.service.dispatch.finalization_receipt(before_batch)
        self.assertEqual(receipt, before_receipt)
        canonical_path = self.fixture.root/'canonical.sqlite'
        dispatch_path = self.fixture.root/'dispatch.sqlite'
        with open_trading_feedback_reader(canonical_path, dispatch_path, namespace='FIXTURE') as reader:
            # Existing protected private snapshot API, not hand-made formatter
            # snapshot and not a new private-summary product API.
            private = reader.snapshot(self.service.run_id, graph.trade_plan_id)
            self.assertTrue(private.available)
            self.assertEqual('FIXTURE', private.namespace)
            self.assertEqual('SIMULATED_MECHANICS', private.execution)
            self.assertEqual(graph, private.canonical)
            self.assertEqual(self.service.lease.generation, private.observed_process_generation)
            binding = json.loads(private.original_binding_json)
            self.assertEqual(self.original_content_hash, binding['strategy_content_hash'])
            self.assertEqual(dict(strategy_id=self.original_identity.strategy_id,
                                  strategy_version=self.original_identity.strategy_version), binding['identity'])
            self.assertEqual('FIXTURE', binding['namespace'])
            self.assertEqual('SIMULATED_MECHANICS', binding['execution'])
            self.assertEqual(expected_amounts,
                {key:private.canonical.trade_result.payload[key] for key in ('gross_pnl','net_pnl','total_fees')}
                | {'funding_cost':funding.payload['funding_cost']})
            default = summaries.build_trading_feedback(reader, self.service.run_id, graph.trade_plan_id)
            opted = summaries.build_trading_feedback(reader, self.service.run_id, graph.trade_plan_id,
                                                     performance_opt_in=True)
            self.assertEqual('OPT_OUT', default['performance_policy'])
            self.assertIsNone(default['performance'])
            self.assertEqual('OPT_IN', opted['performance_policy'])
            self.assertEqual(expected_amounts, opted['performance'])
            for value in (default, opted):
                self.assertEqual(value, summaries.validate_trading_feedback(value))
                self.assertEqual('AVAILABLE', value['availability'])
                self.assertEqual(1, value['sample_count'])
                self.assertEqual('FIXTURE', value['namespace'])
                self.assertEqual({'kind':'FAKE_PROVIDER_VERIFICATION','execution':'SIMULATED_MECHANICS'},
                                 value['provenance'])
                self.assertEqual({'status':'NOT_RUN','performance':None}, value['actual_live'])
                self.assertEqual('NONE', value['financial_authority'])
                self.assertEqual({'source_kind':'BROKER_LEDGER',
                                  'source_version':funding.payload['source_version'],
                                  'evidence_hash':funding.payload_hash}, value['funding'])
                self.assertEqual(result['closed_at'], value['closed_at'])
                self.assertEqual(byte_hash(private.original_binding_json.encode('utf-8')),
                                 value['references']['original_binding_hash'])
                bundle = summaries.trading_feedback_bundle(value)
                self.assertEqual(bundle, summaries.trading_feedback_bundle(value))
                validate_public_feedback_publication(bundle.logical_path, dict(bundle.payloads))
                self.assertEqual({'feedback.json','report.html'}, set(bundle.payloads))
                decoded = json.loads(bundle.payloads['feedback.json'])
                self.assertEqual(value, decoded)
                html = bundle.payloads['report.html'].decode('utf-8')
                self.assertIn('FAKE_PROVIDER_VERIFICATION', html)
                self.assertIn('NOT_RUN', html)
                self.assertNotIn('<script', html)
                raw = canonical_bytes(value).decode('utf-8')
                self.assertNotIn(str(self.fixture.root), raw)
                self.assertNotIn(self.service.run_id, raw)
                for key in ('account_ref','account_balance','api_key','credentials','raw_provider_payload',
                            'provider_position_id','broker_order_id','human_identity'):
                    self.assertNotIn('"'+key+'"', raw)
            for key in expected_amounts:
                self.assertNotIn('"'+key+'"', canonical_bytes(default).decode('utf-8'))
            for invalid in (0, 1, 'OPT_IN', None):
                with self.subTest(opt_in=invalid), self.assertRaises(ValueError):
                    summaries.build_trading_feedback(reader, self.service.run_id, graph.trade_plan_id,
                                                     performance_opt_in=invalid)
        self.assertEqual(graph, self.flow.recover())
        self.assertEqual(before_dispatch, self.service.dispatch.recover(self.service.run_id))
        self.assertEqual(before_batch, self.service.dispatch.finalization_batch(self.service.run_id, self.close_id))
        self.assertEqual(before_receipt, self.service.dispatch.finalization_receipt(before_batch))
        self.assertEqual(before_calls, self.provider.calls)
