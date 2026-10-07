"""Actual existing PAPER owners; accelerated mechanics only, no real forward."""
import copy,importlib,json,unittest
from tests.product import test_paper_runtime_v02 as fixtures

class PaperFeedbackProjectionTests(unittest.TestCase):
    def setUp(self):
        self.module=importlib.import_module('application.cloud.paper_feedback')
        self.case=fixtures.PaperRuntimeV02Tests();self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.runtime=self.case.start()
    def closed(self):
        self.runtime.on_market_event(self.case.event(0,bars=True))
        self.runtime.on_market_event(self.case.event(1))
        self.runtime.on_market_event(self.case.event(2,'60020'))
        self.runtime.on_market_event(self.case.event(3,'60020'))
    def feedback(self,**options):return self.module.build_paper_feedback(self.runtime,**options)
    def test_actual_closed_financial_graph_defaults_to_opt_out_without_runtime_mutation(self):
        self.closed();before=self.case.process.recover(self.runtime.run_id)
        value=self.feedback();after=self.case.process.recover(self.runtime.run_id)
        self.assertEqual(value['schema_version'],'r7-paper-feedback-v0.2')
        self.assertEqual(value['performance_policy'],'OPT_OUT');self.assertIsNone(value['performance'])
        self.assertEqual(value['observation']['closed_trades'],1)
        self.assertEqual((before.process_generation,before.revision,before.state_json),(after.process_generation,after.revision,after.state_json))
        self.assertEqual(value['financial_authority'],'NONE');self.assertEqual(value['live'],{'status':'NOT_RUN','performance':None})
        raw=json.dumps(value)
        for forbidden in ('provider_order_id','broker_order_id','account_balance','api_secret',str(self.case.root)):
            self.assertNotIn(forbidden,raw)
    def test_opt_in_projects_exact_current_published_metrics(self):
        self.closed();value=self.feedback(performance_opt_in=True)
        from application.paper.assessment import assess_forward
        actual=assess_forward(self.runtime,self.case.service.promotion).as_dict()
        self.assertEqual(value['performance']['net_pnl_usdt'],actual['net_pnl_usdt'])
        self.assertEqual(value['performance']['expectancy_usdt_per_trade'],actual['expectancy_usdt_per_trade'])
        self.assertTrue(all(number is None or isinstance(number,str) for number in value['performance'].values()))
    def test_financial_conventions_are_explicit_without_publishing_account_values(self):
        self.closed();value=self.feedback()
        self.assertEqual(value['cost_conventions'],dict(slippage='IN_FILL_PRICE_NO_ADDITIONAL_DEDUCTION',
            funding_model='EXPLICIT_REGISTERED_PAPER_ZERO',account_scope='ISOLATED_PER_STRATEGY_RUN'))
    def test_unperformed_financial_summary_is_null_even_when_opted_in(self):
        value=self.feedback(performance_opt_in=True)
        self.assertEqual(value['observation']['closed_trades'],0);self.assertIsNone(value['performance'])
        self.assertEqual(value['assessment']['status'],'BLOCKED')
    def test_fixture_duration_never_qualifies_real_observation(self):
        self.closed();value=self.feedback()
        self.assertEqual(value['observation']['mode'],'ACCELERATED_FIXTURE')
        self.assertEqual(value['observation']['execution'],'SIMULATED_MECHANICS')
        self.assertEqual(value['observation']['actual_elapsed_seconds'],0)
        self.assertEqual(value['observation']['actual_healthy_seconds'],0)
        self.assertGreater(value['observation']['simulated_elapsed_seconds'],0)
    def test_stale_runtime_generation_cannot_export_as_current_owner(self):
        self.case.process.begin_process(self.runtime.run_id,'replacement-worker',expected_generation=self.runtime.coordinator.generation,now=self.case.clock[0])
        with self.assertRaises(ValueError):self.feedback()
    def test_mismatched_selected_policy_is_not_current_evidence(self):
        from unittest.mock import patch
        from dataclasses import replace
        with patch.object(self.case.service,'promotion',replace(self.case.service.promotion,policy_hash='sha256:'+'e'*64)):
            with self.assertRaises(ValueError):self.feedback()
    def test_strict_public_schema_refuses_private_fields_unbound_time_and_monetary_opt_out(self):
        self.closed();value=self.feedback()
        cases=[]
        private=copy.deepcopy(value);private['provider_account_id']='SYNTHETIC_FORBIDDEN';cases.append(private)
        false_time=copy.deepcopy(value);false_time['observation']['actual_elapsed_seconds']=99;cases.append(false_time)
        monetary=copy.deepcopy(value);monetary['performance']={'net_pnl_usdt':'999'};cases.append(monetary)
        for tampered in cases:
            with self.subTest(keys=list(tampered)),self.assertRaises(ValueError):self.module.validate_paper_feedback(tampered)
    def test_content_addressed_self_contained_bundle_is_deterministic_and_refuses_changed_html(self):
        self.closed();value=self.feedback();bundle=self.module.paper_feedback_bundle(value)
        self.assertTrue(bundle.logical_path.startswith('reports/feedback/paper/'))
        self.assertEqual(self.module.paper_feedback_bundle(value),bundle)
        self.module.validate_paper_feedback_publication(bundle.logical_path,dict(bundle.payloads))
        changed=dict(bundle.payloads);changed['report.html']+=b'<script>forbidden()</script>'
        with self.assertRaises(ValueError):self.module.validate_paper_feedback_publication(bundle.logical_path,changed)
        html=bundle.payloads['report.html'].decode('utf-8')
        self.assertIn('SIMULATED_MECHANICS',html);self.assertIn('default-src',html)
        self.assertNotIn('<script',html);self.assertIn('NOT_RUN',html)

if __name__=='__main__':unittest.main()
