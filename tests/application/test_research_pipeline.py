import importlib
import json
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tests.application.dataset_fixtures import dataset,encoded,split_policy,START
from tests.backtest.test_v02_owner_binding import strategy

def configured(root):
    root=Path(root); dataset(root)
    (root/'split.json').write_bytes(encoded(split_policy()))
    cost=dict(schema_version='r7-replay-cost-policy-v0.2',policy_id='FIXTURE_COST',generation=1,namespace='FIXTURE',
              cost_model_version='FIXTURE_COST_V1',fixed_quantity='1',quantity_unit='BASE',fee_unit='BPS_OF_NOTIONAL',
              maker_bps='2',taker_bps='4',slippage_unit='BPS_OF_REFERENCE_PRICE',entry_bps='1',exit_bps='1',max_evaluations=100)
    (root/'cost.json').write_bytes(encoded(cost))
    return root

class ResearchPipelineTests(unittest.TestCase):
    def test_division_by_zero_runtime_result_cannot_pass_compatibility(self):
        api=self.api()
        from strategy import compute_content_hash
        from tests.strategy.v02_fixtures import operator
        value=strategy()
        value['rules']['long']=operator('GT',operator('DIV',{'kind':'decimal','value':'1'},{'kind':'decimal','value':'0'}),{'kind':'decimal','value':'0'})
        value['content_hash']=compute_content_hash(value)
        with TemporaryDirectory() as root:
            configured(root)
            with self.service(api,root) as service:
                result=self.execute(service,value)
                self.assertEqual('BLOCKED',result.compatibility_status)
                self.assertEqual('DRAFT',result.strategy_lifecycle)
                self.assertIn('DIVISION_BY_ZERO',result.reason_codes)
                self.assertIsNone(service.report(result.run_id)['backtest'])

    def test_failed_dataset_resolution_is_a_retained_stage_attempt(self):
        api=self.api()
        with TemporaryDirectory() as root:
            configured(root); path=Path(root)/'candles.parquet'; path.write_bytes(path.read_bytes()+b'changed')
            with self.service(api,root) as service:
                with self.assertRaises(ValueError): self.execute(service)
                self.assertTrue(hasattr(service.journal,'runs'),'Missing retained run inventory')
                runs=service.journal.runs()
                self.assertEqual(1,len(runs))
                attempt=service.journal.attempts(runs[0]['run_id'])[-1]
                self.assertEqual('dataset_resolution',attempt['stage'])
                self.assertEqual('FAILED',attempt['status'])
                self.assertIn('CONTAINER_HASH_MISMATCH',attempt['reason_codes_json'])

    def test_cost_file_change_after_freeze_cannot_change_actual_replay_assumptions(self):
        api=self.api()
        from unittest.mock import patch
        with TemporaryDirectory() as root:
            configured(root); original=api.read_local
            def changing_read(base,relative,limit):
                raw=original(base,relative,limit)
                if relative=='cost.json':
                    changed=json.loads(raw); changed['taker_bps']='9'
                    (Path(root)/'cost.json').write_bytes(encoded(changed))
                return raw
            with self.service(api,root) as service,patch.object(api,'read_local',changing_read):
                result=self.execute(service); report=service.report(result.run_id)
                self.assertEqual('4',report['inputs']['cost_policy']['taker_bps'])
                self.assertEqual('4',report['backtest']['reproducibility']['cost_assumptions']['fee']['taker_bps'])

    def test_memory_pressure_prevents_parquet_decode_and_is_recorded(self):
        api=self.api()
        from unittest.mock import patch
        from application.platform.resources import inspect_hardware
        from dataclasses import replace
        with TemporaryDirectory() as root:
            configured(root)
            low=replace(inspect_hardware(Path(root)),available_memory_bytes=1024)
            self.assertTrue(hasattr(api,'inspect_hardware'),'Missing actual research admission')
            with self.service(api,root) as service,patch.object(api,'inspect_hardware',return_value=low):
                with self.assertRaises(api.ResearchError) as caught: self.execute(service)
                self.assertEqual('RESEARCH_MEMORY_PRESSURE',caught.exception.code)
                attempts=service.journal.attempts(service.journal.runs()[0]['run_id'])
                self.assertEqual('resource_admission',attempts[-1]['stage'])
                self.assertEqual('FAILED',attempts[-1]['status'])

    def test_invalid_split_and_exhausted_budget_preserve_failed_attempts(self):
        api=self.api()
        for kind in ('split','budget'):
            with self.subTest(kind=kind),TemporaryDirectory() as root:
                configured(root); p=Path(root)/('split.json' if kind=='split' else 'cost.json'); m=json.loads(p.read_text())
                if kind=='split': m['max_holding_seconds']=None
                else: m['max_evaluations']=1
                p.write_bytes(encoded(m))
                with self.service(api,root) as service:
                    with self.assertRaises(ValueError): self.execute(service)
                    attempts=service.journal.attempts(service.journal.runs()[0]['run_id'])
                    self.assertEqual('FAILED',attempts[-1]['status'])
                    self.assertTrue(attempts[-1]['output_hash'])

    def api(self):
        try: return importlib.import_module('application.research.service')
        except ModuleNotFoundError: self.fail('Missing actual local E1/E2/E3/E6 research service')

    def service(self,api,root):
        return api.ResearchService(local_root=root,database_path=Path(root)/'research.sqlite',
                                   registry_path=Path(root)/'fixture-registry.sqlite',namespace='FIXTURE',owner_id='worker-1')

    def execute(self,service,definition=None,**kwargs):
        return service.run(submission_id='fixture-submission',definition=definition or strategy(),dataset_ref='dataset.json',
                           split_policy_ref='split.json',cost_policy_ref='cost.json',**kwargs)

    def test_actual_owner_pipeline_persists_execution_and_keeps_diagnostic_out_of_candidate(self):
        api=self.api()
        with TemporaryDirectory() as root:
            configured(root)
            with self.service(api,root) as service:
                result=self.execute(service)
                self.assertEqual('BLOCKED',result.status)
                self.assertIn('MISSING_PROMOTION_POLICY',result.reason_codes)
                self.assertIn('ROBUSTNESS_NOT_RUN',result.reason_codes)
                self.assertEqual('PASS',result.compatibility_status)
                self.assertEqual('BACKTESTING',result.strategy_lifecycle)
                evidence=service.report(result.run_id)
                self.assertEqual('0.2.0',evidence['backtest']['runtime_version'])
                self.assertGreater(evidence['backtest']['reproducibility']['runtime_invocations'],0)
                self.assertEqual('NOT_RUN',evidence['sealed_oos'])
                self.assertEqual('FIXTURE',evidence['namespace'])
                self.assertEqual(0,evidence['provenance']['provider_requests'])
                self.assertTrue(evidence['provenance']['implementation_hash'].startswith('sha256:'))
                self.assertTrue(evidence['backtest_e6_evidence_id'])
                self.assertTrue(evidence['compatibility']['signal']['market_boundary_ref'])
                self.assertTrue(all(item['input_hash'] and item['output_hash'] and item['started_at'] and item['ended_at'] for item in evidence['attempts']))

    def test_resume_returns_same_durable_outputs_and_does_not_repeat_replay(self):
        api=self.api()
        with TemporaryDirectory() as root:
            configured(root)
            with self.service(api,root) as service:
                first=self.execute(service); original=service.report(first.run_id)
            with self.service(api,root) as service:
                second=self.execute(service); resumed=service.report(second.run_id)
                self.assertEqual(first,second)
                self.assertEqual(original['attempts'],resumed['attempts'])
                self.assertEqual(original['backtest_e6_evidence_id'],resumed['backtest_e6_evidence_id'])

    def test_author_supplied_pass_is_rejected_and_wrong_namespace_never_enters_registry(self):
        api=self.api()
        from strategy import compute_content_hash
        with TemporaryDirectory() as root:
            configured(root)
            with self.service(api,root) as service:
                forged=strategy(); forged['rules']['decision']='PASS'; forged['content_hash']=compute_content_hash(forged)
                with self.assertRaises(ValueError): self.execute(service,forged)
                m=json.loads((Path(root)/'dataset.json').read_text()); m['namespace']='LOCAL_RESEARCH'
                (Path(root)/'dataset.json').write_bytes(encoded(m))
                with self.assertRaises(api.ResearchError) as caught: self.execute(service)
                self.assertEqual('NAMESPACE_MISMATCH',caught.exception.code)

    def test_missing_funding_blocks_replay_without_inventing_zero_cost(self):
        api=self.api()
        with TemporaryDirectory() as root:
            configured(root); p=Path(root)/'dataset.json'; m=json.loads(p.read_text()); m['funding']={'mode':'MISSING'}; p.write_bytes(encoded(m))
            with self.service(api,root) as service:
                result=self.execute(service); report=service.report(result.run_id)
                self.assertIn('MISSING_FUNDING',result.reason_codes)
                self.assertIsNone(report['backtest'])
                self.assertEqual('NOT_RUN',report['sealed_oos'])

    def test_wrong_fee_units_and_nonfinite_costs_block_before_replay(self):
        api=self.api()
        for key,value in (('fee_unit','FRACTION'),('taker_bps','NaN')):
            with self.subTest(key=key),TemporaryDirectory() as root:
                configured(root); p=Path(root)/'cost.json'; m=json.loads(p.read_text()); m[key]=value; p.write_bytes(encoded(m))
                with self.service(api,root) as service:
                    with self.assertRaises(ValueError): self.execute(service)

    def test_expired_worker_cannot_finish_new_generation_and_attempt_is_retained(self):
        api=self.api()
        from application.research.evidence import ResearchJournal,ResearchLeaseConflict
        with TemporaryDirectory() as root:
            with ResearchJournal(Path(root)/'jobs.sqlite') as journal:
                a=journal.claim('run-1','replay','sha256:'+'1'*64,'a',START,lease_seconds=1)
                with self.assertRaises(ResearchLeaseConflict): journal.claim('run-1','replay','sha256:'+'1'*64,'b',START,lease_seconds=1)
                b=journal.claim('run-1','replay','sha256:'+'1'*64,'b',START+timedelta(seconds=2),lease_seconds=10)
                with self.assertRaises(ResearchLeaseConflict): journal.finish(a,{'real_result':'old'},START+timedelta(seconds=3))
                journal.finish(b,{'real_result':'new'},START+timedelta(seconds=3))
                attempts=journal.attempts('run-1')
                self.assertEqual(['ABORTED','COMPLETE'],[item['status'] for item in attempts])
                self.assertEqual(2,attempts[-1]['lease_generation'])

