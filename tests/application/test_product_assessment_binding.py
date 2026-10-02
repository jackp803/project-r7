"""Actual E1/E2/E3/E6 mechanics; FIXTURE namespace grants no real authority."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from application.research.service import ResearchService
from storage.platform import open_sqlite_platform
from registry import EvidenceGateError,StrategyIdentity
from tests.application.test_research_robustness import selected
from tests.application.dataset_fixtures import encoded
from tests.validation.robustness_fixtures import subject


def risk_fixture():
    return dict(schema_version='r7-selected-risk-policy-v0.2',namespace='FIXTURE',generation=1,
        units=dict(margin='USDT_AMOUNT',notional='USDT_AMOUNT',estimated_cost='USDT_AMOUNT',
                   drawdown='USDT_AMOUNT',leverage='RATIO',reward_risk='RATIO',time='SECONDS'),
        policy=dict(version='FIXTURE_RISK_V1',max_margin='100',max_notional='100',max_leverage='1',
            min_reward_risk='1',max_estimated_cost='1',max_trades_per_day=10,max_open_positions=1,
            max_drawdown='10',max_consecutive_losses=3,max_intent_age_seconds=60,max_hold_seconds=3600,
            plan_ttl_seconds=30,margin_mode='ISOLATED'))


class ProductAssessmentBindingTests(unittest.TestCase):
    def execute(self, service, *, risk=True):
        kwargs=dict(submission_id='fixture-product',definition=subject(),dataset_ref='dataset.json',
            split_policy_ref='split.json',cost_policy_ref='cost.json',research_policy_ref='research.json',
            robustness_policy_ref='robustness.json',family_id='fixture-family',seed=42)
        if risk: kwargs['risk_policy_ref']='risk.json'
        return service.run(**kwargs)

    def service(self, root):
        return ResearchService(local_root=root,database_path=Path(root)/'research.sqlite',
            registry_path=Path(root)/'registry.sqlite',namespace='FIXTURE',owner_id='fixture-owner')

    def test_actual_positive_pipeline_enters_candidate_with_exact_selected_e5_policy(self):
        with TemporaryDirectory() as root:
            selected(root); (Path(root)/'risk.json').write_bytes(encoded(risk_fixture()))
            with self.service(root) as service:
                self.assertIn('risk_policy_ref',__import__('inspect').signature(service.run).parameters,
                              'Missing pre-run frozen E5 risk selection')
                result=self.execute(service); report=service.report(result.run_id)
                self.assertEqual('CANDIDATE',result.strategy_lifecycle)
                self.assertEqual('PASS',report['candidate_gate']['status'])
                self.assertEqual(risk_fixture(),report['inputs']['risk_policy'])
                self.assertEqual(result,self.execute(service))
                self.assertEqual(0,report['provenance']['provider_requests'])
            with open_sqlite_platform(Path(root)/'registry.sqlite',research_namespace='FIXTURE') as e6:
                record=e6.product_assessment(result.run_id)
                self.assertEqual('PASS',record.status)
                self.assertEqual('sha256:',record.risk_policy_hash[:7])
                self.assertEqual('CANDIDATE',e6.get_strategy(record.identity).current_lifecycle_state)
                self.assertEqual(record,e6.product_assessment(result.run_id))

    def test_quantitative_failure_rejects_but_sample_blocked_retains_backtesting(self):
        for outcome in ('FAIL','BLOCKED'):
            with self.subTest(outcome=outcome),TemporaryDirectory() as root:
                def adverse(rows):
                    for index,row in enumerate(rows[32:]):
                        row.update(open=str(1000000+index),high=str(1000002+index),
                                   low=str(999999+index),close=str(1000001+index))
                selected(root,adverse if outcome=='FAIL' else None)
                path=Path(root)/'research.json'; value=json.loads(path.read_text())
                if outcome=='BLOCKED': value['minimum_closed_trades']['sealed_oos']=100
                path.write_bytes(encoded(value))
                with self.service(root) as service:
                    result=self.execute(service,risk=False)
                    self.assertEqual(outcome,result.status)
                    self.assertEqual('REJECTED' if outcome=='FAIL' else 'BACKTESTING',result.strategy_lifecycle)
                    self.assertEqual(result,self.execute(service,risk=False))

    def test_missing_risk_preserves_diagnostic_pass_without_candidate_authority(self):
        with TemporaryDirectory() as root:
            selected(root)
            with self.service(root) as service:
                result=self.execute(service,risk=False); report=service.report(result.run_id)
                self.assertEqual('PASS',result.status); self.assertEqual('BACKTESTING',result.strategy_lifecycle)
                self.assertIn('MISSING_SELECTED_RISK_POLICY',report['candidate_gate']['reason_codes'])

    def test_e6_product_record_requires_configured_actual_producer_not_caller_pass(self):
        with TemporaryDirectory() as root:
            with open_sqlite_platform(Path(root)/'registry.sqlite',research_namespace='FIXTURE') as e6:
                self.assertTrue(hasattr(e6,'record_product_assessment'),'Missing owner product assessment interface')
                with self.assertRaises(EvidenceGateError):
                    e6.record_product_assessment(StrategyIdentity('forged','1'),run_id='caller-pass',actor='caller')

    def test_immutable_risk_adapter_reuses_e5_and_rejects_wrong_namespace_or_units(self):
        import importlib
        try: module=importlib.import_module('risk.product_policy')
        except ModuleNotFoundError: self.fail('Missing strict selected E5 RiskPolicy adapter')
        from risk.policy import RiskPolicy
        parsed=module.parse_product_risk_policy(risk_fixture(),namespace='FIXTURE')
        self.assertIsInstance(parsed.risk_policy,RiskPolicy)
        self.assertEqual('100',str(parsed.risk_policy.max_notional))
        for kind in ('namespace','units','unknown','boolean'):
            value=risk_fixture()
            if kind=='namespace': value['namespace']='LOCAL_RESEARCH'
            elif kind=='units': value['units']['drawdown']='PERCENT'
            elif kind=='unknown': value['policy']['allow_live']=True
            else: value['policy']['max_open_positions']=True
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                module.parse_product_risk_policy(value,namespace='FIXTURE')

    def test_wrong_subject_stale_source_and_direct_writer_do_not_create_product_authority(self):
        from unittest.mock import patch
        from application.research.product_assessment import ExecutedProductAssessmentBoundary
        with TemporaryDirectory() as root:
            selected(root); (Path(root)/'risk.json').write_bytes(encoded(risk_fixture()))
            with self.service(root) as service:
                result=self.execute(service)
                boundary=ExecutedProductAssessmentBoundary(service.journal,service.ledger,'FIXTURE')
                with open_sqlite_platform(Path(root)/'registry.sqlite',research_namespace='FIXTURE',
                                          product_assessment_boundary=boundary) as e6:
                    record=e6.product_assessment(result.run_id)
                    with self.assertRaises(EvidenceGateError):
                        e6.record_product_assessment(StrategyIdentity(record.identity.strategy_id,'wrong-version'),
                            run_id=result.run_id,actor='caller')
                    with patch('application.research.product_assessment._revision',return_value='sha256:'+'0'*64):
                        with self.assertRaises(EvidenceGateError):
                            e6.record_product_assessment(record.identity,run_id=result.run_id,actor='caller')
                    with self.assertRaises(EvidenceGateError):
                        e6._store._save_product_assessment(record,capability=object())
                    self.assertEqual(record,e6.product_assessment(result.run_id))
            import sqlite3
            from contextlib import closing
            with closing(sqlite3.connect(Path(root)/'registry.sqlite')) as db:
                with self.assertRaises(sqlite3.IntegrityError):
                    db.execute("UPDATE product_assessments SET status='FAIL'")
                with self.assertRaises(sqlite3.IntegrityError): db.execute('DELETE FROM product_assessments')
