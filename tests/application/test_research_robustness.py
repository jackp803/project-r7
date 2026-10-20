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
    def test_quantitatively_failing_neighbors_remain_in_actual_report_and_trial_ledger(self):
        from decimal import Decimal
        from application.datasets.catalog import canonical,digest
        with TemporaryDirectory() as root:
            selected(root)
            cost_path=Path(root)/'cost.json'
            cost=json.loads(cost_path.read_text())
            cost['taker_bps']='1000'
            cost_path.write_bytes(encoded(cost))
            for name in ('research','robustness'):
                path=Path(root)/(name+'.json')
                policy=json.loads(path.read_text())
                policy['cost_policy_hash']=digest(canonical(cost).encode())
                path.write_bytes(encoded(policy))
            with self.service(root) as service:
                result=self.execute(service)
                report=service.report(result.run_id)
                neighborhood=report['robustness']['neighborhood']
                variants=neighborhood['variants']
                self.assertEqual([row['status'] for row in variants],['BLOCKED','FAIL','FAIL','INVALID'])
                self.assertEqual(len({row['variant_hash'] for row in variants}),4)
                self.assertEqual(neighborhood['pass_fraction'],'0')
                self.assertEqual(neighborhood['denominator'],'ALL_DECLARED_VARIANTS_INCLUDING_INVALID')
                failures=[row for row in variants if row['status']=='FAIL']
                events=service.ledger.events('fixture-family')
                for variant in failures:
                    self.assertLess(Decimal(variant['backtest']['net_pnl']),0)
                    self.assertGreater(Decimal(variant['backtest']['total_fees']),0)
                    self.assertEqual(variant['assessment']['status'],'FAIL')
                    self.assertIn('MIN_NET_PNL_NOT_MET',variant['reason_codes'])
                    terminal=[row for row in events if row['kind']=='TRIAL' and row['payload']['stage']=='neighborhood'
                        and row['payload']['variant_hash']==variant['variant_hash'] and row['payload']['status']=='FAIL']
                    self.assertEqual(len(terminal),1)
                    self.assertEqual(terminal[0]['payload']['run_id'],result.run_id)
                    self.assertEqual(terminal[0]['payload']['result_hash'],digest(canonical(variant).encode()))
                self.assertEqual(report['sealed_oos'],'NOT_RUN')
            with self.service(root) as reopened:
                self.assertEqual(reopened.ledger.events('fixture-family'),events)
                self.assertEqual(reopened.report(result.run_id)['robustness']['neighborhood'],neighborhood)

    def test_actual_trial_failure_is_recorded_by_owner_before_stage_exception_and_survives_reopen(self):
        from unittest.mock import patch
        from validation.robustness import evaluator
        with TemporaryDirectory() as root:
            selected(root)
            original=evaluator._replay
            actual_calls=[]
            def fail_after_actual_neighbor_replay(*args,**kwargs):
                result=original(*args,**kwargs)
                actual_calls.append(result)
                if len(actual_calls)==2: raise RuntimeError('SOURCE_ONLY_PRIVATE_TEXT_NOT_DISCLOSED')
                return result
            with self.service(root) as service:
                with patch.object(evaluator,'_replay',side_effect=fail_after_actual_neighbor_replay):
                    with self.assertRaises(RuntimeError): self.execute(service)
                self.assertEqual(len(actual_calls),2)
                run_id=service.journal.runs()[0]['run_id']
                events=service.ledger.events('fixture-family')
                trials=[row['payload'] for row in events if row['kind']=='TRIAL']
                self.assertEqual([row['status'] for row in trials],['STARTED','FAILED'])
                self.assertEqual(trials[0]['trial_id'],trials[1]['trial_id'])
                self.assertEqual(trials[0]['variant_hash'],trials[1]['variant_hash'])
                for trial in trials:
                    self.assertEqual(trial['run_id'],run_id)
                    self.assertEqual(trial['stage'],'neighborhood')
                    self.assertRegex(trial['result_hash'],r'^sha256:[0-9a-f]{64}$')
                self.assertEqual(trials[1]['reason_codes'],['RuntimeError'])
                attempts=service.journal.attempts(run_id)
                failed=[row for row in attempts if row['stage']=='robustness']
                self.assertEqual(len(failed),1)
                self.assertEqual(failed[0]['status'],'FAILED')
                self.assertRegex(failed[0]['output_hash'],r'^sha256:[0-9a-f]{64}$')
                self.assertIsNone(service.journal.result(run_id,'robustness'))
                self.assertFalse(any(row['stage'] in ('finalist_freeze','sealed_oos') for row in attempts))
                self.assertEqual(service.ledger.holdout_observations(),[])
                self.assertTrue(any(row['kind']=='RUN_FAILED' and row['payload']['run_id']==run_id for row in events))
                self.assertNotIn('SOURCE_ONLY_PRIVATE_TEXT_NOT_DISCLOSED',json.dumps(events))
            with self.service(root) as reopened:
                self.assertEqual(reopened.ledger.events('fixture-family'),events)
                self.assertEqual(reopened.journal.attempts(run_id),attempts)

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
