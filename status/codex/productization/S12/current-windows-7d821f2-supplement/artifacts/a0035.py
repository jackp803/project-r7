"""Unapplied public-contract source regression drafts; no owning execution."""
import ast,json
from prepare_strategy_test_drafts import draft,ART,REPO

def recovery_draft():
    relative='tests/application/test_research_e6_recovery.py'
    path=REPO/relative
    source=path.read_text(encoding='utf-8')
    old="""                original=service.journal.finish
                def crash(claim,*args,**kwargs):
                    if claim.stage=='e6_backtest_persistence': raise RuntimeError('fixture crash after E6 save')
                    return original(claim,*args,**kwargs)
"""
    new="""                import sqlite3
                from contextlib import closing
                before=[]
                def actual_evidence_rows():
                    uri=(Path(root)/'registry.sqlite').resolve().as_uri()+'?mode=ro'
                    with closing(sqlite3.connect(uri,uri=True)) as db:
                        db.execute('PRAGMA query_only=ON')
                        definition=strategy()
                        return db.execute('SELECT * FROM validation_evidence WHERE evidence_type=? AND strategy_id=? AND strategy_version=? ORDER BY evidence_id',
                            ('BACKTEST_RESULT',definition['strategy_id'],definition['strategy_version'])).fetchall()
                original=service.journal.finish
                def crash(claim,*args,**kwargs):
                    if claim.stage=='e6_backtest_persistence':
                        before.extend(actual_evidence_rows())
                        self.assertEqual(len(before),1)
                        raise RuntimeError('fixture crash after E6 save')
                    return original(claim,*args,**kwargs)
"""
    anchor="                self.assertTrue(report['backtest_e6_evidence_id'])\n"
    replacement="""                self.assertEqual(report['backtest_e6_evidence_id'],before[0][0])
                self.assertEqual(actual_evidence_rows(),before)
"""
    assert source.count(old)==source.count(anchor)==1
    ast.parse(source.replace(old,new).replace(anchor,replacement))
    patch='*** Begin Patch\n*** Update File: '+str(path)+'\n@@\n'
    patch+=''.join('-'+line+'\n' for line in old.splitlines())
    patch+=''.join('+'+line+'\n' for line in new.splitlines())+'@@\n-'+anchor
    patch+=''.join('+'+line+'\n' for line in replacement.splitlines())+'*** End Patch\n'
    target=ART/'postcheckpoint_test_research_e6_recovery_tests.patch'
    target.write_text(patch,encoding='utf-8',newline='\n')
    return dict(ref=target.name,existing_methods_augmented=1,status='DRAFT_ONLY_NOT_EXECUTED')

dataset='''    def test_purge_uses_larger_holding_or_label_horizon_without_changing_embargo(self):
        import json
        from application.datasets.split_plan import resolve_split
        hashes=[]
        clocks=[]
        for hold,label in ((7200,3600),(3600,7200)):
            with self.subTest(hold=hold,label=label),TemporaryDirectory() as root:
                dataset(root)
                policy=split_policy()
                policy.update(max_holding_seconds=hold,label_horizon_seconds=label)
                split=resolve_split(self.resolve(self.api(),root),policy)
                self.assertEqual(json.loads(split.canonical_policy_json),policy)
                hashes.append(split.policy_hash)
                actual=[]
                for name,start,end,warmup,entry_start,entry_end in (
                    ('training',0,4,0,0,2),('development',4,8,2,5,6),('sealed_oos',8,12,6,9,10)):
                    part=getattr(split,name)
                    observed=(part.start,part.end,part.warmup_start,part.entry_start,part.entry_end)
                    self.assertEqual(observed,tuple(START+timedelta(hours=n) for n in (start,end,warmup,entry_start,entry_end)))
                    actual.append(observed)
                clocks.append(actual)
        self.assertEqual(clocks[0],clocks[1])
        self.assertNotEqual(hashes[0],hashes[1])

'''

walk_forward='''    def test_walk_forward_entry_bounds_use_maximum_horizon_and_exact_embargo(self):
        import json
        from application.datasets.split_plan import resolve_split
        for hold,label in ((7200,3600),(3600,7200)):
            with self.subTest(hold=hold,label=label),TemporaryDirectory() as root:
                api=self.api()
                data,original,cost=inputs(root)
                split_policy=json.loads(original.canonical_policy_json)
                split_policy.update(max_holding_seconds=hold,label_horizon_seconds=label)
                split=resolve_split(data,split_policy)
                binding=api.DevelopmentBinding.from_dataset(data,split,cost)
                policy=robustness_policy(split,cost)
                for raw,clocks in zip(policy['walk_forward_windows'],((8,12,6,9,10),(12,16,10,13,14))):
                    window=binding.window(raw['evaluation'],embargo=True)
                    self.assertEqual((window.start,window.end,window.warmup_start,window.entry_start,window.entry_end),
                        tuple(START+timedelta(hours=n) for n in clocks))
                result=api.evaluate_robustness(subject(),binding,policy,
                    research_policy=research_policy(split,cost),seed=42).as_dict()['walk_forward']
                self.assertEqual(len(result['windows']),2)
                for window,(start,end) in zip(result['windows'],((9,10),(13,14))):
                    self.assertEqual(window['purge_seconds'],7200)
                    self.assertEqual(window['embargo_seconds'],3600)
                    self.assertEqual(window['evaluation_entry_start'],z(START+timedelta(hours=start)))
                    self.assertEqual(window['evaluation_entry_end'],z(START+timedelta(hours=end)))
                    for trade in window['evaluation']['trades']:
                        self.assertGreaterEqual(trade['opened_at'],window['evaluation_entry_start'])
                        self.assertLess(trade['opened_at'],window['evaluation_entry_end'])
                        self.assertLessEqual(trade['closed_at'],window['evaluation_end'])

'''

assessment='''    def test_canonical_candidate_validator_rejects_nonindependent_or_unverified_actual_product_evidence(self):
        from dataclasses import replace
        from unittest.mock import patch
        from registry.product_assessment import canonical,digest,require_product_candidate
        with TemporaryDirectory() as root:
            selected(root)
            (Path(root)/'risk.json').write_bytes(encoded(risk_fixture()))
            with self.service(root) as service:
                result=self.execute(service)
            with open_sqlite_platform(Path(root)/'registry.sqlite',research_namespace='FIXTURE') as e6:
                record=e6.product_assessment(result.run_id)
                strategy=e6.get_strategy(record.identity)
                self.assertEqual(require_product_candidate(e6._store,strategy,record.validation_evidence_id),record)
                for field in ('independent_oos','sealed_dataset_verification'):
                    payload=json.loads(record.payload_json)
                    if field=='independent_oos': payload[field]=False
                    else: payload[field]['scope']='DEVELOPMENT_VERIFIED_SEALED_LOGICAL_PENDING'
                    raw=canonical(payload)
                    hostile=replace(record,payload_json=raw,payload_hash=digest(raw))
                    with self.subTest(field=field),patch.object(e6._store,'product_assessment_for_decision',return_value=hostile):
                        with self.assertRaises(EvidenceGateError) as caught:
                            require_product_candidate(e6._store,strategy,record.validation_evidence_id)
                        self.assertEqual(str(caught.exception),'Complete independent final OOS required')
                    self.assertEqual(e6.product_assessment(result.run_id),record)
                    self.assertEqual(e6.get_strategy(record.identity),strategy)
                    self.assertEqual(require_product_candidate(e6._store,strategy,record.validation_evidence_id),record)

'''

robustness='''    def test_quantitatively_failing_neighbors_remain_in_actual_report_and_trial_ledger(self):
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

'''

robustness+='''    def test_actual_trial_failure_is_recorded_by_owner_before_stage_exception_and_survives_reopen(self):
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

'''

if __name__=='__main__':
    rows=[draft('tests/application/test_dataset_binding.py',
            '    def test_public_versioned_schemas_accept_bindings_and_reject_wrong_units_or_external_pass(self):\n',dataset),
          draft('tests/validation/test_walk_forward.py','    def api(self):\n',walk_forward),
          draft('tests/application/test_product_assessment_binding.py',
            '    def test_actual_positive_pipeline_enters_candidate_with_exact_selected_e5_policy(self):\n',assessment),
          draft('tests/application/test_research_robustness.py','    def service(self,root):\n',robustness),
          recovery_draft()]
    print(json.dumps(dict(status='UNAPPLIED_AST_CHECK_ONLY',drafts=rows,tracked_writes=0),indent=2))
