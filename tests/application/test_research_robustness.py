import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from application.research.service import ResearchService
from tests.application.dataset_fixtures import encoded,dataset
from tests.validation.robustness_fixtures import inputs,subject,research_policy,robustness_policy

def selected(root,mutate=None):
    data,split,cost=inputs(root,mutate)
    for name,value in (('split',json.loads(split.canonical_policy_json)),('research',research_policy(split,cost)),
                       ('robustness',robustness_policy(split,cost))):
        (Path(root)/(name+'.json')).write_bytes(encoded(value))

class ResearchRobustnessTests(unittest.TestCase):
    def service(self,root):
        return ResearchService(local_root=root,database_path=Path(root)/'research.sqlite',registry_path=Path(root)/'registry.sqlite',namespace='FIXTURE',owner_id='owner-1')
    def execute(self,service):
        return service.run(submission_id='fixture-submission',definition=subject(),dataset_ref='dataset.json',split_policy_ref='split.json',
            cost_policy_ref='cost.json',research_policy_ref='research.json',robustness_policy_ref='robustness.json',family_id='fixture-family',seed=42)
    def test_real_complete_pipeline_freezes_before_final_replay_and_is_idempotent(self):
        with TemporaryDirectory() as root:
            selected(root)
            with self.service(root) as service:
                result=self.execute(service); report=service.report(result.run_id)
                self.assertEqual('PASS',result.status); self.assertEqual('BACKTESTING',result.strategy_lifecycle)
                self.assertEqual('PASS',report['robustness']['status']); self.assertEqual('PASS',report['product_assessment']['status'])
                self.assertEqual('PASS',report['sealed_oos']); self.assertEqual(0,report['provenance']['provider_requests'])
                self.assertEqual('FULL_LOGICAL_VERIFIED',report['product_assessment']['sealed_dataset_verification']['scope'])
                self.assertEqual('DEVELOPMENT_VERIFIED_SEALED_LOGICAL_PENDING',report['dataset_resolution']['verification_scope'])
                stages=[v['stage'] for v in report['attempts']]
                self.assertLess(stages.index('robustness'),stages.index('finalist_freeze'))
                self.assertLess(stages.index('finalist_freeze'),stages.index('sealed_oos'))
                self.assertGreater(report['product_assessment']['trial_count'],0)
                self.assertEqual('BLOCKED',report['candidate_gate']['status'])
                self.assertEqual('BACKTESTING',service.report(result.run_id)['strategy_lifecycle'])
                self.assertEqual(result,self.execute(service))
                self.assertEqual(report['attempts'],service.report(result.run_id)['attempts'])
    def test_actual_oos_losses_are_retained_as_fail_without_requery_or_threshold_change(self):
        def mutate(rows):
            for index,row in enumerate(rows[32:]):
                row.update(open=str(1000000+index),high=str(1000002+index),low=str(999999+index),close=str(1000001+index))
        with TemporaryDirectory() as root:
            selected(root,mutate)
            with self.service(root) as service:
                result=self.execute(service); report=service.report(result.run_id)
                self.assertEqual('PASS',report['robustness']['status']); self.assertEqual('FAIL',result.status)
                self.assertEqual('FAIL',report['sealed_oos']); self.assertLess(float(report['product_assessment']['sealed_backtest']['net_pnl']),0)
                self.assertIn('MIN_NET_PNL_NOT_MET',result.reason_codes)
                self.assertEqual(1,len(service.ledger.holdout_observations()))
                self.assertEqual(result,self.execute(service))
    def test_amended_policy_generation_cannot_reset_observed_holdout(self):
        with TemporaryDirectory() as root:
            selected(root)
            with self.service(root) as service:
                first=self.execute(service); self.assertEqual('PASS',first.status)
                path=Path(root)/'research.json'; policy=json.loads(path.read_text()); policy['generation']=2; path.write_bytes(encoded(policy))
                second=self.execute(service); self.assertNotEqual(first.run_id,second.run_id)
                self.assertEqual('BLOCKED',second.status); self.assertIn('HOLDOUT_ALREADY_OBSERVED',second.reason_codes)
                self.assertIsNone(service.report(second.run_id)['product_assessment']['sealed_backtest'])
                self.assertEqual(1,len(service.ledger.holdout_observations()))
                self.assertEqual(2,len([v for v in service.ledger.events('fixture-family') if v['kind']=='POLICY_SELECTION']))
    def test_selected_execution_requires_both_frozen_profiles_explicit_family_and_seed(self):
        with TemporaryDirectory() as root:
            selected(root)
            with self.service(root) as service:
                with self.assertRaises(ValueError): service.run(submission_id='s',definition=subject(),dataset_ref='dataset.json',split_policy_ref='split.json',
                                     cost_policy_ref='cost.json',research_policy_ref='research.json')
    def test_full_normalization_occurs_only_after_durable_finalist_freeze(self):
        from unittest.mock import patch
        with TemporaryDirectory() as root:
            selected(root)
            with self.service(root) as service:
                original=service.resolver.resolve; reads=[]
                def observed(reference):
                    frozen=bool(service.ledger._db.execute('SELECT finalist_id FROM research_finalists').fetchone())
                    reads.append(frozen); return original(reference)
                with patch.object(service.resolver,'resolve',observed): self.execute(service)
                self.assertTrue(reads); self.assertTrue(all(reads),'Full OOS payload was normalized before finalist freeze')
    def test_unselected_diagnostic_never_normalizes_invalid_sealed_values(self):
        def mutate(rows):
            for row in rows[32:]: row['high']='0'
        with TemporaryDirectory() as root:
            selected(root); dataset(root,count=48,mutate=mutate)
            with self.service(root) as service:
                try:
                    result=service.run(submission_id='diagnostic',definition=subject(),dataset_ref='dataset.json',split_policy_ref='split.json',cost_policy_ref='cost.json')
                except ValueError:
                    self.fail('Diagnostic decoded/validated sealed financial values before any finalist freeze')
                self.assertEqual('PASS',result.compatibility_status)
                self.assertGreater(service.report(result.run_id)['backtest']['total_trades'],0)
                self.assertEqual('NOT_RUN',service.report(result.run_id)['sealed_oos'])
    def test_interrupted_adaptive_trial_is_retained_before_stage_result_exists(self):
        from unittest.mock import patch
        with TemporaryDirectory() as root:
            selected(root)
            with self.service(root) as service:
                original=service.ledger.record_event; started=[]
                def interrupt(family,kind,payload):
                    result=original(family,kind,payload)
                    if kind=='TRIAL' and payload['status']=='STARTED':
                        started.append(payload['trial_id'])
                        if len(started)==2: raise RuntimeError('fixture interruption')
                    return result
                with patch.object(service.ledger,'record_event',interrupt):
                    with self.assertRaises(RuntimeError): self.execute(service)
                self.assertIsNone(service.journal.result(service.journal.runs()[0]['run_id'],'robustness'))
            with self.service(root) as resumed:
                events=resumed.ledger.events('fixture-family')
                self.assertEqual(2,len([v for v in events if v['kind']=='TRIAL' and v['payload']['status']=='STARTED']))
                self.assertTrue(any(v['kind']=='RUN_FAILED' for v in events))
    def test_insufficient_final_oos_is_product_blocked_and_preserves_legacy_numeric_decision(self):
        with TemporaryDirectory() as root:
            selected(root); path=Path(root)/'research.json'; p=json.loads(path.read_text()); p['minimum_closed_trades']['sealed_oos']=100
            path.write_bytes(encoded(p))
            with self.service(root) as service:
                result=self.execute(service); report=service.report(result.run_id)
                self.assertEqual('PASS',report['robustness']['status']); self.assertEqual('BLOCKED',result.status)
                self.assertIn('INSUFFICIENT_EVIDENCE',result.reason_codes)
                self.assertEqual('FAIL',report['product_assessment']['canonical_oos_decision']['decision'])
                self.assertGreater(report['product_assessment']['sealed_backtest']['total_trades'],0)
                self.assertEqual(1,len(service.ledger.holdout_observations()))
