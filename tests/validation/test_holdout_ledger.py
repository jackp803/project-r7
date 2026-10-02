import importlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from datetime import timedelta
from application.research.evidence import ResearchJournal,capture_provenance,now_utc
from application.research.orchestrator import ResearchOrchestrator
from application.datasets.catalog import DatasetCatalog
from application.datasets.resolver import DatasetResolver
from tests.application.dataset_fixtures import START,z,encoded
from tests.validation.robustness_fixtures import inputs,subject,research_policy,robustness_policy

def completed_run(journal,root,run_id='fixture-run',family_id='fixture-family'):
    from validation.robustness.evaluator import DevelopmentBinding,evaluate_robustness
    data,split,cost=inputs(root); rp=research_policy(split,cost); robust=robustness_policy(split,cost)
    policies={'research':rp,'robustness':robust,'split':json.loads(split.canonical_policy_json),'cost':cost}
    value=dict(namespace='FIXTURE',family_id=family_id,strategy=subject(),dataset=data.manifest_json,
               dataset_manifest_hash=data.manifest_hash,split_policy=policies['split'],cost_policy=cost,
               research_policy=rp,robustness_policy=robust,random_seed=42,provenance=capture_provenance())
    journal.register_run(run_id,value,now_utc())
    ResearchOrchestrator(journal,'actual-test-worker').execute(run_id,'robustness',value,
        lambda _:evaluate_robustness(subject(),DevelopmentBinding.from_dataset(data,split,cost),robust,research_policy=rp,seed=42).as_dict())
    return data,split,policies,value

class HoldoutLedgerTests(unittest.TestCase):
    def api(self):
        try: return importlib.import_module('application.research.holdout')
        except ModuleNotFoundError: self.fail('Missing durable sealed-OOS authority and trial ledger')
    def test_freeze_requires_actual_completed_robustness_and_exact_immutable_inputs(self):
        api=self.api()
        with TemporaryDirectory() as root,ResearchJournal(Path(root)/'research.sqlite') as journal:
            with api.ResearchTrialLedger(Path(root)/'research.sqlite') as ledger:
                ledger.register_family('fixture-family','FIXTURE','BTC_USDT_PERP','TRAIN_NET_PNL_THEN_VARIANT_HASH_V1')
                with self.assertRaises(ValueError): ledger.freeze_finalist('missing-run',subject()['content_hash'],{})
                data,split,policies,run=completed_run(journal,root)
                frozen=ledger.freeze_finalist('fixture-run',subject()['content_hash'],policies)
                self.assertTrue(frozen.finalist_id); self.assertEqual(subject()['content_hash'],frozen.as_dict()['strategy_content_hash'])
                self.assertEqual(data.manifest_hash,frozen.as_dict()['dataset_manifest_hash'])
                self.assertEqual(frozen,ledger.freeze_finalist('fixture-run',subject()['content_hash'],policies))
                changed=json.loads(json.dumps(policies)); changed['research']['min_net_pnl_usdt']='-99'
                with self.assertRaises(ValueError): ledger.freeze_finalist('fixture-run',subject()['content_hash'],changed)
                with self.assertRaises(ValueError): ledger.freeze_finalist('fixture-run','sha256:'+'a'*64,policies)
    def test_actual_finalist_is_frozen_before_oos_read_and_replay_is_once(self):
        api=self.api()
        with TemporaryDirectory() as root,ResearchJournal(Path(root)/'research.sqlite') as journal:
            with api.ResearchTrialLedger(Path(root)/'research.sqlite') as ledger:
                ledger.register_family('fixture-family','FIXTURE','BTC_USDT_PERP','TRAIN_NET_PNL_THEN_VARIANT_HASH_V1')
                data,split,policies,_=completed_run(journal,root)
                frozen=ledger.freeze_finalist('fixture-run',subject()['content_hash'],policies)
                binding=api.SealedOOSBinding(ledger,DatasetResolver(DatasetCatalog(root)),'dataset.json')
                result=api.evaluate_sealed_oos(frozen,binding).as_dict()
                self.assertEqual('PASS',result['status']); self.assertTrue(result['independent_oos'])
                self.assertEqual('PASS',result['canonical_oos_decision']['decision'])
                self.assertGreater(result['sealed_backtest']['reproducibility']['runtime_invocations'],0)
                self.assertEqual(frozen.finalist_id,result['finalist_id'])
                self.assertTrue(result['raw_result_hashes']); self.assertTrue(result['trial_count'])
                self.assertEqual(result,api.evaluate_sealed_oos(frozen,binding).as_dict())
                self.assertEqual(1,len(ledger.holdout_observations()))
                self.assertEqual('EVALUATION_BEGIN',ledger.holdout_observations()[0]['kind'])
    def test_chat_observation_is_global_for_symbol_period_even_after_family_or_hash_change(self):
        api=self.api()
        with TemporaryDirectory() as root,ResearchJournal(Path(root)/'research.sqlite') as journal:
            with api.ResearchTrialLedger(Path(root)/'research.sqlite') as ledger:
                ledger.register_family('old-family','FIXTURE','BTC_USDT_PERP','TRAIN_NET_PNL_THEN_VARIANT_HASH_V1')
                ledger.observe_holdout('old-family',z(START+timedelta(hours=32)),z(START+timedelta(hours=48)),
                                       kind='CHAT_OBSERVATION',reference_hash='sha256:'+'1'*64)
                ledger.record_event('old-family','MANUAL_CHAT_REVISION',{'prior_strategy_hash':'sha256:'+'2'*64,'next_strategy_hash':subject()['content_hash']})
                ledger.register_family('renamed-family','FIXTURE','BTC_USDT_PERP','TRAIN_NET_PNL_THEN_VARIANT_HASH_V1')
                data,split,policies,_=completed_run(journal,root,run_id='changed-run',family_id='renamed-family')
                frozen=ledger.freeze_finalist('changed-run',subject()['content_hash'],policies)
                # Burned OOS must be rejected before a missing or corrupt payload is opened.
                (Path(root)/'candles.parquet').write_bytes(b'not parquet')
                result=api.evaluate_sealed_oos(frozen,api.SealedOOSBinding(ledger,DatasetResolver(DatasetCatalog(root)),'dataset.json')).as_dict()
                self.assertEqual('BLOCKED',result['status']); self.assertFalse(result['independent_oos'])
                self.assertIn('HOLDOUT_ALREADY_OBSERVED',result['reason_codes']); self.assertIsNone(result['sealed_backtest'])
                self.assertEqual(1,len(ledger.holdout_observations()))
                self.assertIn('MANUAL_CHAT_REVISION',[event['kind'] for event in ledger.events('old-family')])
    def test_append_only_trials_keep_invalid_failed_and_aborted_after_restart(self):
        api=self.api()
        with TemporaryDirectory() as root:
            path=Path(root)/'ledger.sqlite'
            with api.ResearchTrialLedger(path) as ledger:
                ledger.register_family('family','FIXTURE','BTC_USDT_PERP','TRAIN_NET_PNL_THEN_VARIANT_HASH_V1')
                for status in ('INVALID','FAILED','ABORTED'):
                    ledger.record_event('family','TRIAL',{'trial_id':status,'status':status,'reason_codes':['EXPLICIT_TEST_CASE']})
            with api.ResearchTrialLedger(path) as ledger:
                events=ledger.events('family'); self.assertEqual(3,len(events)); self.assertEqual(['INVALID','FAILED','ABORTED'],[v['payload']['status'] for v in events])
            import sqlite3
            from contextlib import closing
            with closing(sqlite3.connect(path)) as db:
                for sql in ('DELETE FROM research_family_events','UPDATE research_family_events SET kind="PASS"'):
                    with self.assertRaises(sqlite3.DatabaseError): db.execute(sql)
                    db.rollback()
    def test_consumed_incomplete_oos_cannot_be_replayed_after_crash_or_new_version(self):
        api=self.api()
        with TemporaryDirectory() as root,ResearchJournal(Path(root)/'research.sqlite') as journal:
            with api.ResearchTrialLedger(Path(root)/'research.sqlite') as ledger:
                ledger.register_family('fixture-family','FIXTURE','BTC_USDT_PERP','TRAIN_NET_PNL_THEN_VARIANT_HASH_V1')
                data,split,policies,_=completed_run(journal,root)
                frozen=ledger.freeze_finalist('fixture-run',subject()['content_hash'],policies)
                self.assertTrue(ledger.claim_holdout(frozen)['allowed'])
            with api.ResearchTrialLedger(Path(root)/'research.sqlite') as ledger:
                result=api.evaluate_sealed_oos(frozen,api.SealedOOSBinding(ledger,DatasetResolver(DatasetCatalog(root)),'dataset.json')).as_dict()
                self.assertEqual('BLOCKED',result['status']); self.assertIn('HOLDOUT_EXPOSED_INCOMPLETE',result['reason_codes'])
                self.assertIsNone(result['sealed_backtest']); self.assertEqual(1,len(ledger.holdout_observations()))
    def test_changed_source_or_policy_after_freeze_never_becomes_oos_pass(self):
        api=self.api()
        with TemporaryDirectory() as root,ResearchJournal(Path(root)/'research.sqlite') as journal:
            with api.ResearchTrialLedger(Path(root)/'research.sqlite') as ledger:
                ledger.register_family('fixture-family','FIXTURE','BTC_USDT_PERP','TRAIN_NET_PNL_THEN_VARIANT_HASH_V1')
                data,split,policies,_=completed_run(journal,root); frozen=ledger.freeze_finalist('fixture-run',subject()['content_hash'],policies)
                manifest=json.loads((Path(root)/'dataset.json').read_text()); manifest['dataset_version']='2'; (Path(root)/'dataset.json').write_bytes(encoded(manifest))
                with self.assertRaises(ValueError): api.evaluate_sealed_oos(frozen,api.SealedOOSBinding(ledger,DatasetResolver(DatasetCatalog(root)),'dataset.json'))
                self.assertEqual(1,len(ledger.holdout_observations()))
    def test_concurrent_reader_cannot_publish_blocked_over_the_owned_replay(self):
        api=self.api()
        from unittest.mock import patch
        with TemporaryDirectory() as root,ResearchJournal(Path(root)/'research.sqlite') as journal:
            with api.ResearchTrialLedger(Path(root)/'research.sqlite') as ledger:
                ledger.register_family('fixture-family','FIXTURE','BTC_USDT_PERP','TRAIN_NET_PNL_THEN_VARIANT_HASH_V1')
                _,_,policies,_=completed_run(journal,root); frozen=ledger.freeze_finalist('fixture-run',subject()['content_hash'],policies)
                binding=api.SealedOOSBinding(ledger,DatasetResolver(DatasetCatalog(root)),'dataset.json')
                original=binding._replay_final; other=[]
                def interleaved(value):
                    other.append(api.evaluate_sealed_oos(frozen,binding).as_dict())
                    return original(value)
                with patch.object(binding,'_replay_final',interleaved):
                    result=api.evaluate_sealed_oos(frozen,binding).as_dict()
                self.assertEqual('PASS',result['status']); self.assertEqual('BLOCKED',other[0]['status'])
                self.assertEqual(result,ledger.result(frozen).as_dict())
    def test_upstream_result_with_a_different_input_commitment_cannot_freeze_finalist(self):
        api=self.api()
        with TemporaryDirectory() as root,ResearchJournal(Path(root)/'research.sqlite') as journal:
            with api.ResearchTrialLedger(Path(root)/'research.sqlite') as ledger:
                ledger.register_family('fixture-family','FIXTURE','BTC_USDT_PERP','TRAIN_NET_PNL_THEN_VARIANT_HASH_V1')
                _,_,policies,value=completed_run(journal,root)
                journal.register_run('misbound-run',value,now_utc())
                claim=journal.claim('misbound-run','robustness','sha256:'+'a'*64,'owner',now_utc())
                journal.finish(claim,journal.result('fixture-run','robustness'),now_utc())
                with self.assertRaises(ValueError): ledger.freeze_finalist('misbound-run',subject()['content_hash'],policies)
