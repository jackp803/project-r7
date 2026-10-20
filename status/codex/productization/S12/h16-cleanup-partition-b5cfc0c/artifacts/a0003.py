"""One-off exact-input test relocation; refuses while frozen run is unfinished."""
from pathlib import Path
import ast,hashlib,json,re,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.qualification import revision_fact
from strategy.v02.capabilities import _revision

def main():
    if not __debug__:raise RuntimeError('Optimized Python is not admitted for this one-off mutation utility')
    head=sys.argv[1];apply='--apply' in sys.argv[2:]
    checkpoint=(BASE/'h16-stop-cleanup-source-7de014e/checkpoint.json').read_bytes()
    if hashlib.sha256(checkpoint).hexdigest()!='342763ac9b99bb94124bb72bb40eac7a1e49ed5c3189ad278ae43a23a2a09b1c':
        raise ValueError('Exact retained failed attempt checkpoint required')
    run=json.loads(checkpoint)
    assert run['executable_revision']=='7de014eeedf2791c8e186a9608c589454c792f4c'
    assert run['tests_run']==158 and run['source_unchanged'] and run['tree_reaped']
    # A failed resource admission is retained as failure, never converted to PASS.
    log=(BASE/'h16-stop-cleanup-source-7de014e/source.log').read_bytes()
    if hashlib.sha256(log).hexdigest()!='c6be7807600527ca1a2db41fbc67422c18532d3211783c8c85b69cc3d0145737':
        raise ValueError('Exact retained failed attempt log required')
    assert 'sha256:'+hashlib.sha256(log).hexdigest()==run['log_hash']
    text=log.decode('utf-8')
    if not run['passed']:
        assert run['exit_code']==1 and run['failure_type'] is None
        assert re.search(r'^FAILED \(errors=92\)$',text,re.M)
        blocks=[part for part in re.split(r'\n={70}\n',text)[1:] if part.startswith('ERROR:')]
        assert len(blocks)==92
        for part in blocks:
            errors=[line for line in part.splitlines() if 'Error:' in line]
            assert errors and errors[-1].startswith('application.research.service.ResearchResourceError: RESEARCH_MEMORY_PRESSURE {')
        cleanup=re.findall(r'^test_.*\(tests.product.test_trading_stop_cleanup_v02\..*\) \.\.\. ok$',text,re.M)
        assert len(cleanup)==11
    else:
        assert run['exit_code']==0
    revision_fact(ROOT,head,True)
    assert _revision()==run['implementation_hash'],'Production inputs changed before relocation'
    review_bytes=(BASE/'h16-stop-cleanup-owner-review-final-retry01.json').read_bytes()
    if hashlib.sha256(review_bytes).hexdigest()!='c00e4267598d2d9a9a0284d39116d5af7379c0a0d255cc973799b3bc2fcb9ba7':
        raise ValueError('Exact retained nine-file review bytes required before interpreting paths')
    review=json.loads(review_bytes)
    for name,wanted in review['subject_hashes'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==wanted,name
    old_path=ROOT/'tests/product/test_trading_stop_cleanup_v02.py'
    old=old_path.read_text(encoding='utf-8');lines=old.splitlines(keepends=True)
    tree=ast.parse(old)
    owner=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='TradingStopCleanupV02Tests')
    methods={node.name:''.join(lines[node.lineno-1:node.end_lineno]).rstrip()+'\n'
             for node in owner.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))}
    groups=[('test_trading_stop_cleanup_v02','TradingStopCleanupV02Tests',[
        'test_one_exact_target_cancel_ack_leaves_original_stop_unsettled_and_duplicate_never_resends',
        'test_before_original_flat_cleanup_refuses_without_cancel']),
      ('test_trading_cleanup_expiry_v02','TradingCleanupExpiryV02Tests',[
        'test_copied_expired_native_nonzero_or_unowned_inventory_cannot_cancel',
        'test_reads_expiring_during_actual_post_guard_preserve_claim_without_cancel']),
      ('test_trading_cleanup_inventory_v02','TradingCleanupInventoryV02Tests',[
        'test_empty_inventory_or_competing_active_object_is_not_cleanup_authority',
        'test_provider_or_execution_replacement_denies_before_any_cancel']),
      ('test_trading_cleanup_races_v02','TradingCleanupRacesV02Tests',[
        'test_actual_second_connection_append_at_claim_writer_blocks_claim_and_cancel',
        'test_actual_second_connection_append_after_claim_blocks_final_provider_guard']),
      ('test_trading_cleanup_recovery_v02','TradingCleanupRecoveryV02Tests',[
        'test_lost_cancel_ack_keeps_claim_then_native_terminal_is_reconciled_without_another_cancel',
        'test_successor_process_generation_two_reads_original_stop_without_resending_cancel']),
      ('test_trading_cleanup_immutability_v02','TradingCleanupImmutabilityV02Tests',[
        'test_cleanup_claim_is_immutable_even_when_recursive_delete_triggers_are_disabled'])]
    names=[name for _,_,items in groups for name in items]
    assert len(names)==len(set(names))==11
    assert set(names)=={name for name in methods if name.startswith('test_')}
    immut=names[-1]
    before="replacement=dict(original);replacement['stop_operation_id']='replacement'"
    after="replacement=dict(original);replacement['stop_operation_id']=self.flow.entry_operation\n"+\
        "        entry=self.service.dispatch.operation(self.service.run_id,self.flow.entry_operation)\n"+\
        "        self.assertIsNotNone(entry)\n"+\
        "        self.assertEqual(entry.recovery_disposition,'READBACK_REQUIRED')\n"+\
        "        self.assertIsNone(self.service.dispatch.stop_cleanup_claim(self.service.run_id,self.flow.entry_operation))"
    assert methods[immut].count(before)==1
    methods[immut]=methods[immut].replace(before,after)
    imports=''.join(lines[1:owner.lineno-1]).strip()+'\n'
    helper_methods=[body for name,body in methods.items() if not name.startswith('test_')]
    outputs={ROOT/'tests/product/trading_stop_cleanup_fixtures.py':
        '"""Shared genuine cleanup source fixture; no discoverable TestCase/tests."""\n'+imports+
        '\n\nclass StopCleanupFixture:\n'+('\n'.join(helper_methods)).rstrip()+'\n'}
    mapping=[]
    for module,klass,items in groups:
        outputs[ROOT/'tests/product'/f'{module}.py']=f'"""Bounded genuine cleanup regressions: {klass}."""\n'+imports+\
            '\nfrom tests.product.trading_stop_cleanup_fixtures import StopCleanupFixture\n'+\
            f'\n\nclass {klass}(StopCleanupFixture,unittest.TestCase):\n'+\
            ('\n'.join(methods[name] for name in items)).rstrip()+'\n'
        for name in items:
            mapping.append(dict(original='tests.product.test_trading_stop_cleanup_v02.TradingStopCleanupV02Tests.'+name,
                relocated='tests.product.'+module+'.'+klass+'.'+name,
                change='VALID_EXISTING_ENTRY_FK_ORACLE' if name==immut else 'METHOD_BODY_UNCHANGED'))
    for path,content in outputs.items():
        assert path==old_path or not path.exists(),str(path)
        compile(content,str(path),'exec')
    report=dict(status='APPLIED_NOT_EXECUTED' if apply else 'DRY_RUN_NOT_APPLIED',original_revision=run['executable_revision'],original_run_passed=run['passed'],
        original_run_status='PASS' if run['passed'] else 'FAILED_92_MEMORY_ADMISSION_ERRORS_66_PASS_CLEANUP11_PASS',
        original_source_hash=hashlib.sha256(old.encode()).hexdigest(),production_implementation_hash=run['implementation_hash'],
        cases_before=11,cases_after=11,shared_helper='NON_TESTCASE_MIXIN_NO_TEST_METHODS',
        fixed_pqr_member_timeout_seconds=900,partitions_need_actual_timing=True,
        outputs={path.relative_to(ROOT).as_posix():hashlib.sha256(content.encode()).hexdigest() for path,content in outputs.items()},
        case_mapping=mapping)
    if apply:
        target=BASE/'h16-cleanup-case-partition.json'
        assert not target.exists()
        (BASE/'h16-stop-cleanup-unpartitioned.py.unapplied').write_text(old,encoding='utf-8',newline='\n')
        for path,content in outputs.items():path.write_text(content,encoding='utf-8',newline='\n')
        assert _revision()==run['implementation_hash'],'Relocation must not alter production source'
        target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(status=report['status'],cases=11,partitions=len(groups),
        source_files=list(report['outputs']),production_implementation_hash=run['implementation_hash'])))

if __name__=='__main__':main()
