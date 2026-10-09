"""Retain only fixed sanitized public evidence for the normal research setup increment."""
from pathlib import Path
import hashlib,json,os,subprocess,sys

BASE=Path(__file__).resolve().parent
PROJECT=BASE.parent
REPO=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(REPO/'src'))
sys.path.insert(0,str(BASE))
from s09_native_evidence_guards import original_binding,continuation_binding
from application.datasets.catalog import read_local
from application.cloud.safe_files import _windows_read,_posix_read
from application.platform.supervision import _local_path
from application.platform.distribution import verify_distribution
from application.qualification import revision_fact,parse_result,_sanitize

REVISION='af01b45f980882e64f3c83784d0a4da0731728ba'
SHORT=REVISION[:7]
EXPECTED=dict(revision=REVISION,worktree='CLEAN')
REF=f'status/codex/productization/S09/public-research-setup-qualified-{SHORT}-py312'
SOURCE_LOGS='''001-phase_1-brokers.log 002-phase_1-position.log 003-phase_1-execution.log
004-phase_1-execution.log 005-phase_1-position.log 006-phase_1-brokers.log 007-phase_1-execution.log
008-phase_1-position.log 009-phase_1-storage.log 010-phase_1-storage.log 011-phase_1-storage.log
012-phase_1-integration.log 013-phase_1-integration.log 014-phase_1-integration.log 015-phase_1-safety.log
016-phase_1-e2e.log 017-phase_2-market_data.log 018-phase_2-indicators.log 019-phase_2-strategy.log
020-phase_2-backtest.log 021-phase_2-validation.log 022-phase_2-execution.log 023-phase_2-brokers.log
024-phase_2-risk.log 025-phase_2-position.log 026-phase_2-storage.log 027-phase_2-platform.log
028-phase_2-integration.log 029-phase_2-e2e.log 030-phase_2-safety.log 031-phase_2-application.log
032-phase_2-product.log 033-phase_2-registry.log'''.split()
SMOKE_LOGS='''01-doctor.log 02-init-profile.log 03-preserve-profile.log
04-first-control-start-second-process-denied.log 04-first-control-start.log 05-control-restart.log
06-control-config-change.log 07-unconfigured-research-worker.log 08-tampered-resource-denied.log'''.split()
# Every retained runtime helper is bound by the actual native or source proof.



def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def read_public(path,limit):
    if path==REPO/'src/application/platform/_loopback_probe.py':
        _local_path(path)
        return (_windows_read if os.name=='nt' else _posix_read)(path,limit)
    return read_local(path.parent,path.name,limit)

def collect():
    assert revision_fact(REPO,REVISION,True)==EXPECTED
    snapshots={};retained={}
    def capture(path,target=None,limit=64*1024**2):
        if path not in snapshots:snapshots[path]=read_public(path,limit)
        raw=snapshots[path]
        if target is not None:
            assert target not in retained
            retained[target]=_sanitize(raw.decode('utf-8'),REPO).replace('\r\n','\n').encode('utf-8')
        return raw
    def report(path,target):return json.loads(capture(path,target))
    source=BASE/f'r7-productization-S09-public-research-setup-qualified-{SHORT}-long-path-fixed'
    q=report(source/'qualification.json','source/qualification.json')
    context=report(source/'qualification-context.json','source/qualification-context.json')
    hardware=report(source/'hardware-observations.json','source/hardware-observations.json')
    native=report(BASE/f'S09-public-research-setup-{SHORT}-native-regression.json','native/native-regression.json')
    original_binding(native,REVISION)
    native_paths=[BASE/'s09_public_research_setup_native_regression.py',BASE/'s09_local_paper_control_native_regression.py',BASE/'s09_owner_worker_native_regression.py',
        BASE/'s12_storage_native_paper_reader.py',BASE/'s13_native_access_integrity.py',
        REPO/'src/application/platform/_loopback_probe.py',REPO/'tools/build_product.py',REPO/'tools/verify_native_product.py',
        BASE/'s14_feedback_cli_native_paper.py',BASE/'S14LocalFakeRclone.exe',BASE/'S14LocalFakeRclone.cs',
        source/'qualification.json',source/'qualification-context.json',BASE/'s09_owner_worker_source_qualify.py',
        BASE/'s09_public_research_setup_source_qualify.py',BASE/'local_windows_qualification_awake.py',
        BASE/'s09_native_public_research_setup_probe.py',BASE/'s09_native_long_backup_probe.py']
    assert set(native['input_hashes_before'])=={p.relative_to(PROJECT).as_posix() for p in native_paths},'UNEXPECTED_NATIVE_INPUT_SET'
    assert native['passed'] is False
    assert all(c['passed'] is True for c in native['commands'][:5])
    assert native['commands'][-1]['label']=='long-backup' and native['commands'][-1]['exit_code']==1
    for path in (source/'qualification.json',source/'qualification-context.json'):
        assert sha(snapshots[path])==native['input_hashes_before'][path.relative_to(PROJECT).as_posix()]
    assert q['passed'] is True and q['tests_run']==2052 and len(q['commands'])==33
    assert q['source_before']==q['source_after']==context['source_before']==context['source_after']==EXPECTED
    assert context['inputs_unchanged'] is True and context['memory_monitor_joined'] is True
    assert context['configuration']==dict(suites=['all'],include_focused=True,require_clean=True,
        timeout_seconds=900,expected_revision=REVISION)
    assert [c['log'] for c in q['commands']]==SOURCE_LOGS
    phase=dict(phase_1=0,phase_2=0)
    for command in q['commands']:
        assert command['passed'] is True and command['tree_reaped'] is True and command['source_after']==EXPECTED
        assert command['returncode']==command['failures']==command['errors']==command['skipped']==command['expected_failures']==command['unexpected_successes']==0
        raw=capture(source/command['log'],'source/'+command['log'])
        assert sha(raw)=='sha256:'+command['log_sha256']
        result=parse_result(raw.decode('utf-8').replace('\r\n','\n'),returncode=0)
        assert result.passed and result.tests_run==command['tests_run']
        phase[command['phase']]+=result.tests_run
    assert phase==dict(phase_1=247,phase_2=1805)
    failed_expected=dict(revision='048713ada12e8773b2af5e5b42151505f34d10dd',worktree='CLEAN')
    failed_source=BASE/'r7-productization-S09-public-research-setup-qualified-048713a'
    failed=report(failed_source/'qualification.json','failed-memory-attempt/qualification.json')
    failed_context=report(failed_source/'qualification-context.json','failed-memory-attempt/qualification-context.json')
    report(failed_source/'hardware-observations.json','failed-memory-attempt/hardware-observations.json')
    assert failed['passed'] is False and failed['tests_run']==2001 and len(failed['commands'])==32
    assert failed['source_before']==failed['source_after']==failed_expected
    assert failed_context['inputs_unchanged'] is True and failed_context['awake_request']['restored'] is True
    assert len(failed_context['source_input_hashes'])==624
    assert failed['commands'][-1]['suite']=='product' and failed['commands'][-1]['errors']==3
    assert [command['log'] for command in failed['commands']]==SOURCE_LOGS[:32]
    for command in failed['commands']:
        assert command['tree_reaped'] is True
        assert sha(capture(failed_source/command['log'],'failed-memory-attempt/'+command['log']))=='sha256:'+command['log_sha256']
    original_launcher=BASE/'s09_public_research_setup_source_qualify.original-attempt.py'
    assert sha(capture(original_launcher,'tools/'+original_launcher.name))==failed_context['launcher_sha256']
    failed_retry_source=BASE/'r7-productization-S09-public-research-setup-qualified-048713a-memory-retry'
    failed_retry=report(failed_retry_source/'qualification.json','failed-backup-attempt/qualification.json')
    failed_retry_context=report(failed_retry_source/'qualification-context.json','failed-backup-attempt/qualification-context.json')
    report(failed_retry_source/'hardware-observations.json','failed-backup-attempt/hardware-observations.json')
    assert failed_retry['passed'] is False and failed_retry['tests_run']==1796 and len(failed_retry['commands'])==31
    assert failed_retry['source_before']==failed_retry['source_after']==failed_expected
    assert failed_retry_context['inputs_unchanged'] is True and failed_retry_context['awake_request']['restored'] is True
    assert failed_retry_context['source_input_hashes']==failed_context['source_input_hashes']
    assert failed_retry['commands'][-1]['suite']=='application' and failed_retry['commands'][-1]['failures']==1
    assert [command['log'] for command in failed_retry['commands']]==SOURCE_LOGS[:31]
    for command in failed_retry['commands']:
        assert command['tree_reaped'] is True
        assert sha(capture(failed_retry_source/command['log'],'failed-backup-attempt/'+command['log']))=='sha256:'+command['log_sha256']
    retry_launcher=BASE/'s09_public_research_setup_source_qualify.original-memory-retry.py'
    assert sha(capture(retry_launcher,'tools/'+retry_launcher.name))==failed_retry_context['launcher_sha256']
    tracked=set(subprocess.check_output(['git','ls-files','--','src','tests','tools','packaging','ui','docs','contracts'],
        cwd=REPO,text=True,encoding='utf-8',timeout=15).splitlines())
    assert len(tracked)==625 and set(context['source_input_hashes'])==tracked,'UNEXPECTED_SOURCE_INPUT_SET'
    for name,expected in context['source_input_hashes'].items():
        path=REPO/name;_local_path(path)
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert sha((_windows_read if os.name=='nt' else _posix_read)(path,64*1024**2))==expected
    assert context['launcher_sha256']==native['input_hashes_before'][(BASE/'s09_public_research_setup_source_qualify.py').relative_to(PROJECT).as_posix()]
    assert context['awake_request']['restored'] is True
    assert context['awake_helper_sha256_before']==context['awake_helper_sha256_after']==native['input_hashes_before'][(BASE/'local_windows_qualification_awake.py').relative_to(PROJECT).as_posix()]
    capture(Path(__file__),'tools/'+Path(__file__).name)
    capture(BASE/'record_s09_public_research_setup_checkpoint.py','tools/record_s09_public_research_setup_checkpoint.py')
    assert native['executable_revision']==REVISION
    assert native['native_worker_invoked'] is False and native['ordinary_native_paper']=='NOT_RUN'
    assert [c['label'] for c in native['commands']]==['build','smoke','historical-paper','paper-reader','public-setup','long-backup']
    original_probe=BASE/'s09_native_long_backup_probe.original-import-failure.py'
    for path in native_paths:
        actual=original_probe if path==BASE/'s09_native_long_backup_probe.py' else path
        assert sha(capture(actual))==native['input_hashes_before'][path.relative_to(PROJECT).as_posix()]
    for path in native_paths:
        if path.parent==BASE and path.suffix in ('.py','.cs'):
            actual=original_probe if path==BASE/'s09_native_long_backup_probe.py' else path
            capture(actual,'tools/'+actual.name)
    for command in native['commands']:
        assert command['tree_reaped'] is True
        assert (command['passed'] is True and command['exit_code']==0) if command['label']!='long-backup' else (command['passed'] is False and command['exit_code']==1)
        assert command['log']==f'S09-public-research-setup-{SHORT}-native-{command["label"]}.log'
        assert sha(capture(BASE/command['log'],'native/'+command['log']))==command['log_sha256']
    build_root=BASE/f'r7-native-windows-S09-public-research-setup-{SHORT}';package=build_root/'dist/R7'
    identity=verify_distribution(package)
    assert identity==native['native_build_identity'] and identity['executable_revision']==REVISION
    assert identity['implementation_hash']==context['implementation_hash']
    build=report(build_root/'build-result.json','native-build/build-result.json')
    assert build['identity']==identity and build['target']=='windows'
    assert build['source']==EXPECTED|{'implementation_hash':context['implementation_hash']}
    assert build['archive']==f'r7-product-0.2.0-windows-{SHORT}.zip'
    assert sha(capture(build_root/build['archive'],limit=128*1024**2))=='sha256:'+build['archive_sha256']
    for path,target in [(build_root/'pyinstaller.log','pyinstaller.log'),(package/'distribution.json','distribution.json'),
        (package/'licenses/inventory.json','licenses-inventory.json')]:capture(path,'native-build/'+target)
    probes=[('smoke','native-smoke.json',8,SMOKE_LOGS),
        ('historical','native-paper-feedback.json',3,['01-historical-paper-publish.log','02-historical-paper-idempotent.log']),
        ('reader','native-paper-reader.json',2,['01-native-profile.log','02-native-control.log'])]
    for label,name,count,logs in probes:
        prefix='r7-native-S09-public-research-setup-reader-fixed' if label in ('smoke','historical') else 'r7-native-S12-storage-reader-fixed'
        folder=BASE/f'{prefix}-{label}-{SHORT}';target='native-'+label
        value=report(folder/name,target+'/'+name)
        assert value['passed'] is True and value['identity']==identity and value['scenario_count']==count
        assert len(value['scenarios'])==count and [c['log'] for c in value['commands']]==logs
        for case in value['scenarios']:assert case.get('passed',case.get('result')=='PASS') is True
        for command in value['commands']:
            assert command['passed'] is True and command['tree_reaped'] is True
            raw=capture(folder/command['log'],target+'/'+command['log']);expected=command['log_sha256']
            assert sha(raw)==(expected if expected.startswith('sha256:') else 'sha256:'+expected)
        if label in ('historical','reader'):
            assert value['source_before']==value['source_after']==EXPECTED
        if label=='historical':
            assert value['normal_runtime']=='NOT_RUN' and value['fixture_cleanup_complete'] is True
            assert value['input_sha256_before']==value['input_sha256_after']
        if label=='reader':
            paths=[BASE/'s12_storage_native_paper_reader.py',BASE/'s09_owner_worker_native_regression.py',
                REPO/'src/application/local_owners.py',REPO/'src/application/control_api/paper_ports.py',
                REPO/'src/application/entrypoints.py',REPO/'src/application/control_api/auth.py',
                REPO/'src/application/control_api/app.py',BASE/'s13_native_access_integrity.py',
                REPO/'src/application/platform/_loopback_probe.py']
            assert set(value['input_hashes_before'])=={p.relative_to(PROJECT).as_posix() for p in paths}
            assert value['input_hashes_before']==value['input_hashes_after']
            for path in paths:assert sha(capture(path))==value['input_hashes_before'][path.relative_to(PROJECT).as_posix()]
            assert value['native_worker_invoked'] is False and value['ordinary_native_paper']=='NOT_RUN'
            assert value['auth_origin']=='SOURCE_CREATED_NEW_SYNTHETIC_LOCAL_AUTH_FIXTURE;NOT_NATIVE_CLI_ENROLLMENT'
            assert value['native_path']=='EMPTY' and value['native_pythonpath']=='UNSET'
            assert value['real_credentials']=='NONE' and value['provider_requests']==0 and value['capital']=='NONE'
    folder=BASE/f'r7-native-S09-public-setup-probe-{SHORT}'
    setup=report(folder/'native-public-setup.json','native-public-setup/native-public-setup.json')
    assert setup['passed'] is True and setup['native_build_identity']==identity and setup['executable_revision']==REVISION
    assert setup['private_fixture_removed'] is True and setup['paper']=='NOT_STARTED' and setup['research']=='NOT_STARTED'
    assert setup['native_authentication']=='NOT_INVOKED' and setup['product_path']=='EMPTY' and setup['pythonpath']=='UNSET'
    assert len(setup['scenarios'])==10 and all(case['passed'] is True for case in setup['scenarios'])
    assert [c['log'] for c in setup['commands']]==['01-init.log','02-configure.log','03-identical-retry.log',
        '04-different-selection.log','05-cloud-origin.log','06-cloud-hardlink.log','07-unknown-authority.log',
        '08-missing-local-input.log','09-cloud-config.log','10-equal-cloud-config.log','11-overlapping-roots.log']
    probe_hash=native['input_hashes_before'][(BASE/'s09_native_public_research_setup_probe.py').relative_to(PROJECT).as_posix()]
    assert setup['launcher_sha256_before']==setup['launcher_sha256_after']==probe_hash
    for command in setup['commands']:
        assert command['passed'] is True and command['tree_reaped'] is True
        assert (command['exit_code']!=0)==command['expected_rejection']
        assert sha(capture(folder/command['log'],'native-public-setup/'+command['log']))==command['log_sha256']
    continuation_path=BASE/f'S09-public-research-setup-{SHORT}-native-long-backup-bounded-continuation.json'
    continuation=report(continuation_path,'native-long-backup/continuation.json')
    continuation_binding(continuation,REVISION,guarded=True,label='bounded-fixed')
    assert continuation['passed'] is True and continuation['exit_code']==0 and continuation['tree_reaped'] is True
    assert continuation['executable_revision']==REVISION and continuation['native_build_identity']==identity
    assert continuation['source_inputs_unchanged'] is True and continuation['awake_request']['restored'] is True
    assert continuation['input_hashes_before']==continuation['input_hashes_after']
    assert continuation['original_native_proof_sha256']==sha(snapshots[BASE/f'S09-public-research-setup-{SHORT}-native-regression.json'])
    for name,expected in continuation['input_hashes_before'].items():
        path=PROJECT/name
        assert sha(capture(path))==expected
        target='tools/'+path.name
        if path.parent==BASE and path.suffix=='.py' and target not in retained:capture(path,target)
    assert sha(capture(BASE/continuation['log'],'native-long-backup/'+continuation['log']))==continuation['log_sha256']
    failed_acl_path=BASE/f'S09-public-research-setup-{SHORT}-native-long-backup-continuation.json'
    failed_acl=report(failed_acl_path,'native-failed-acl/continuation.json')
    continuation_binding(failed_acl,REVISION,guarded=False,label='fixed')
    assert failed_acl['passed'] is False and failed_acl['exit_code']==1 and failed_acl['tree_reaped'] is True
    assert failed_acl['input_hashes_before']==failed_acl['input_hashes_after'] and failed_acl['source_inputs_unchanged'] is True
    for name,expected in failed_acl['input_hashes_before'].items():
        path=PROJECT/name
        if path.name=='s09_native_long_backup_probe.py':path=BASE/'s09_native_long_backup_probe.original-acl-failure.py'
        elif path.name=='s09_native_long_backup_continuation.py':path=BASE/'s09_native_long_backup_continuation.original-acl-failure.py'
        assert sha(capture(path))==expected
        if path.parent==BASE and path.suffix=='.py' and 'tools/'+path.name not in retained:capture(path,'tools/'+path.name)
    assert sha(capture(BASE/failed_acl['log'],'native-failed-acl/'+failed_acl['log']))==failed_acl['log_sha256']
    folder=BASE/f'r7-native-S09-long-backup-bounded-fixed-probe-{SHORT}'
    long_backup=report(folder/'native-long-backup.json','native-long-backup/native-long-backup.json')
    assert long_backup['passed'] is True and long_backup['native_build_identity']==identity and long_backup['executable_revision']==REVISION
    assert long_backup['private_fixture_removed'] is True and long_backup['paper']=='NOT_STARTED' and long_backup['research']=='NOT_STARTED'
    assert long_backup['product_path']=='EMPTY' and long_backup['pythonpath']=='UNSET'
    assert len(long_backup['scenarios'])==2 and all(case['passed'] is True and case['path_length']>280 for case in long_backup['scenarios'])
    assert [case['id'] for case in long_backup['scenarios']]==['FROZEN_LONG_PRODUCT_BACKUP_AND_VERIFY','FROZEN_LONG_DATABASES_BACKUP_AND_VERIFY']
    assert [c['log'] for c in long_backup['commands']]==['01-product-create.log','02-product-verify.log','03-databases-create.log','04-databases-verify.log']
    assert long_backup['launcher_sha256_before']==long_backup['launcher_sha256_after']==continuation['input_hashes_before'][(BASE/'s09_native_long_backup_probe.py').relative_to(PROJECT).as_posix()]
    for command in long_backup['commands']:
        assert command['passed'] is True and command['tree_reaped'] is True and command['exit_code']==0
        assert sha(capture(folder/command['log'],'native-long-backup/'+command['log']))==command['log_sha256']
    review=report(BASE/'S09-public-research-setup-long-backup-review.json','review/long-backup-review.json')
    assert review['reviewer_execution']=='NONE' and review['remaining_critical']==review['remaining_important']==0
    assert set(review['raw_reviewed_sha256'])=={'src/application/platform/private_files.py',
        'src/application/platform/product_backup.py','src/application/platform/supervision.py',
        'src/application/platform/backup.py','tests/application/test_private_long_paths.py'}
    for name,expected in review['raw_reviewed_sha256'].items():
        assert context['source_input_hashes'][name]=='sha256:'+expected
    for label in ('RED','GREEN'):
        stem='S09-native-reference-guards-bound-'+label
        guard=report(BASE/(stem+'.json'),'external-guards/'+stem+'.json')
        assert guard['tests_run']==3 and guard['scope']=='EXTERNAL_REFERENCE_BINDING_GUARDS_ONLY;NO_PRODUCT_TEST_CREDIT'
        guard_raw=capture(BASE/(stem+'.log'),'external-guards/'+stem+'.log')
        assert sha(guard_raw)==guard['log_sha256']
        parsed_guard=parse_result(guard_raw.decode('utf-8').replace('\r\n','\n'),returncode=1 if label=='RED' else 0)
        assert parsed_guard.tests_run==3 and parsed_guard.skipped==0 and parsed_guard.failures==0
        assert parsed_guard.errors==(3 if label=='RED' else 0) and parsed_guard.passed==(label=='GREEN')
        assert guard['test_sha256']==sha(capture(BASE/'test_s09_native_reference_guards.py'))
        assert guard['tested_caller']==('s09_native_long_backup_continuation.original-before-guard-remediation.py' if label=='RED' else 's09_native_long_backup_continuation.py')
        assert sha(capture(BASE/guard['tested_caller']))==guard['tested_caller_sha256']
        if label=='RED':assert guard['errors']==3 and guard['failures']==0 and guard['passed'] is False
        else:assert guard['errors']==guard['failures']==0 and guard['passed'] is True
    capture(BASE/'test_s09_native_reference_guards.py','tools/test_s09_native_reference_guards.py')
    capture(BASE/'s09_native_long_backup_continuation.original-before-guard-remediation.py','tools/s09_native_long_backup_continuation.original-before-guard-remediation.py')
    histories=['RED','PRECOMMIT','PRECOMMIT_REVIEW_RED','CANONICAL_RED','PRECOMMIT_REVIEW_GREEN',
        'PROOF_RED','PROOF_BOUND_GREEN','CLEAN_FLOW','CLEAN_FLOW_FINAL','CLEAN_FIXED_FLOW','PROOF_FIXED_GREEN',
        'BACKUP_DIAGNOSTIC','LONG_PATH_RED','LONG_REPARSE_RED','LONG_INVENTORY_RED','LONG_INVENTORY_GREEN',
        'DIAGNOSTIC_LONG_BACKUP','DIAGNOSTIC_SQLITE','LONG_DATABASE_RED','LONG_DATABASE_GREEN',
        'LONG_PATH_REGRESSION_FINAL','BACKUP_FIXED']
    for label in histories:
        stem='S09-public-research-setup-'+label
        value=report(BASE/(stem+'.json'),'development/'+stem+'.json')
        raw=capture(BASE/(stem+'.log'),'development/'+stem+'.log')
        assert sha(raw)==value['log_sha256']
        if label in ('CLEAN_FIXED_FLOW','PROOF_FIXED_GREEN'):
            assert value['exit_code']==value['failures']==value['errors']==value['skipped']==0
            assert value['tree_reaped'] is True and value['awake_request']['restored'] is True and value['inputs_unchanged'] is True
            assert value['tests_run']==(11 if label=='CLEAN_FIXED_FLOW' else 2)
            if label=='CLEAN_FIXED_FLOW':
                assert value['source_revision']==REVISION and value['worktree']=='CLEAN'
                assert value['source_input_hashes']==context['source_input_hashes']
            assert len(value['execution_input_hashes'])==5
            for name,expected in value['execution_input_hashes'].items():
                path=BASE/name.removeprefix('external/')
                assert path.parent==BASE and path.name in ['run_s09_public_research_setup_tests.py',
                    's09_owner_worker_native_regression.py','s09_owner_worker_source_qualify.py',
                    'local_windows_qualification_awake.py','test_s09_public_setup_runner_bindings.py']
                assert sha(capture(path,'tools/'+path.name) if 'tools/'+path.name not in retained else capture(path))==expected
        if label in ('LONG_DATABASE_GREEN','LONG_PATH_REGRESSION_FINAL','BACKUP_FIXED'):
            assert value['exit_code']==value['failures']==value['errors']==value['skipped']==0
            assert value['tests_run']=={'LONG_DATABASE_GREEN':6,'LONG_PATH_REGRESSION_FINAL':32,'BACKUP_FIXED':3}[label]
            assert value['tree_reaped'] is True and value['awake_request']['restored'] is True and value['inputs_unchanged'] is True
            expected_runner='run_s09_restored_backup_diagnostic.py' if label=='BACKUP_FIXED' else 'run_s09_recovery_long_path_tests.py'
            assert set(value['execution_input_hashes'])=={'external/'+name for name in [expected_runner,
                's09_owner_worker_native_regression.py','s09_owner_worker_source_qualify.py',
                'local_windows_qualification_awake.py','s09_restored_backup_diagnostic.py']}
            for name,expected in value['execution_input_hashes'].items():
                path=BASE/name.removeprefix('external/')
                assert path.parent==BASE
                assert sha(capture(path,'tools/'+path.name) if 'tools/'+path.name not in retained else capture(path))==expected
    samples=hardware['samples'];assert samples
    memory=dict(samples=len(samples),minimum_available_bytes=min(x['available_memory_bytes'] for x in samples),
        below_unchanged_admission_threshold=sum(x['available_memory_bytes']<x['existing_admission_minimum_bytes'] for x in samples),
        scope=hardware['scope'])
    facts=dict(task_id=context['task_id'],spec_baseline=context['spec_baseline'],spec_revision=context['spec_revision'],
        revision=REVISION,implementation_hash=context['implementation_hash'],
        source=dict(passed=True,tests=2052,commands=33,phase=phase),source_input_files=625,
        native_build=identity,native_scoped=dict(passed=True,scenarios=25,commands=28,wrapper_stages=6,
            existing_scoped_scenarios=13,existing_scoped_commands=13,public_setup_scenarios=10,public_setup_commands=11,
            long_backup_scenarios=2,long_backup_commands=4),memory=memory,
        source_awake_request=context['awake_request'],native_awake_request=continuation['awake_request'],
        native_evidence_binding='FIRST_FIVE_COMPLETED_STAGES_KEEP_ORIGINAL_CLOSURE;LONG_BACKUP_USES_FIXED_CONTINUATION_CLOSURE;NO_EXECUTION_CREDIT_FOR_TWO_FAILED_PROBES',
        original_failed_native_aggregate_binding='UNRECORDED;COMPLETED_STAGE_GUARDS_IN_HASHED_LAUNCHER_AND_EXACT_CURRENT_REVALIDATION_ONLY',
        failed_native_probes=['OUTER_TEST_IMPORT_MISSING;NO_PRODUCT_COMMAND_RUN','SYNTHETIC_PROFILE_PARENT_ACL_NOT_PRIVATE;NO_PRODUCT_COMMAND_RUN'],
        accepted_prior_revision='ac0b889829777db884666f82bd2d18f2c38ba4cb',new_component_cases=11,
        failed_prior_source_attempt=dict(tests=2001,commands=32,errors=3,failed_group='product',reason='ACTUAL_RESEARCH_MEMORY_PRESSURE',registry='NOT_RUN',acceptance='NONE'),
        failed_backup_source_attempt=dict(revision=failed_expected['revision'],tests=1796,commands=31,failures=1,
            failed_group='application',reason='DETERMINISTIC_WINDOWS_LONG_PRIVATE_DIRECTORY_PATH',product='NOT_RUN',registry='NOT_RUN',acceptance='NONE'),
        long_path_recovery=dict(new_tests=6,affected_tests=32,original_failed_restored_backup_repetitions_passed=3,
            native_scenarios=2,native_commands=4,review=review),
        development_setup_and_regression_tests=51,external_execution_binding_guard_tests=2,external_binding_mutation_subcases=5,
        external_native_reference_guard_tests=3,
        bounded_review=dict(initial_critical=0,initial_important=3,reviewer_execution='NONE',
            disposition='THREE_FINDINGS_REPRODUCED_AND_FIXED_BY_REGRESSION;NO_INDEPENDENT_RE_REVIEW_CLAIM'),
        native_owner_composition_factory='NOT_INVOKED',native_worker_invoked=False,ordinary_native_paper='NOT_RUN',
        browser='NOT_RUN_FOR_THIS_CANDIDATE',production_profile='PROPOSED_NOT_ACTIVE',owning_producer='NOT_IMPLEMENTED',
        ubuntu24='NOT_RUN',ubuntu26='NOT_RUN',real_cloud='NOT_RUN',real_dataset='NOT_RUN',real_forward='NOT_RUN',
        provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',master='IN_PROGRESS',
        scope='NORMAL_PUBLIC_SOURCE_SETUP_LOGIN_INTAKE_ACTUAL_RESEARCH_CHILD;FROZEN_SETUP_PLUS_EXISTING_SCOPED_NATIVE_REGRESSIONS;NO_NORMAL_PAPER_WORKFLOW_COMPLETION',
        limitations=['2052 source execution instances include focused repeats; not distinct definitions.',
          'Native25 are8 first-run,3 historical publication,2 source-created synthetic auth empty reads/start denial,10 actual frozen setup and2 long backup scenarios.',
          'New native setup checks selection shape/local references/namespace only; no actual native research or auth enrollment in this increment.',
          'The three new source research flows use newly generated synthetic LOCAL_RESEARCH inputs and a local-folder cloud simulation.',
          'Historical development failures are preserved observations, not final exact-clean qualification credit.',
          'No native CLI auth enrollment,managed reader stop,native composition factory/worker,current browser or whole-product acceptance.',
          'No24GB target or pressure-capacity claim; no historical qualification transferred.',
          'Two final runner guard tests include five actual dependency-copy mutations, separate from product qualification.',
          'Ordinary LOCAL_RESEARCH Paper remains without accepted production release mapping; authorized normal FIXTURE wiring is pending implementation.'])
    retained['disposition.json']=encoded(facts)
    for path,raw in snapshots.items():assert read_public(path,max(64*1024**2,len(raw)))==raw
    assert revision_fact(REPO,REVISION,True)==EXPECTED and verify_distribution(package)==identity
    return retained,snapshots,facts

def main():
    retained,snapshots,facts=collect();target=REPO/REF
    _local_path(target);assert not os.path.lexists(target);target.mkdir()
    manifest={}
    for name,raw in sorted(retained.items()):
        path=target/name;_local_path(path);path.parent.mkdir(exist_ok=True)
        with path.open('xb') as stream:stream.write(raw)
        assert read_local(path.parent,path.name,64*1024**2)==raw
        manifest[path.relative_to(REPO).as_posix()]=sha(raw)
    path=target.parent/f'public-research-setup-qualified-artifact-hashes-{SHORT}.json';_local_path(path)
    with path.open('xb') as stream:stream.write(encoded(dict(files=manifest,
        captured_raw_sha256={p.relative_to(PROJECT).as_posix():sha(raw) for p,raw in snapshots.items()},
        capture_tool_sha256=sha(read_public(Path(__file__),1024**2)),scope='FIXED_PUBLIC_CORPUS;PRIVATE_DB_CONFIG_ARCHIVE_NOT_RETAINED')))
    print(json.dumps(dict(retained_files=len(manifest),source_tests=2052,native_scoped=facts['native_scoped'],state='MASTER_IN_PROGRESS')))

if __name__=='__main__':main()
