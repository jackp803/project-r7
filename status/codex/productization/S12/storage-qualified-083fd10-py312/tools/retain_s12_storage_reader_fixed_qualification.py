"""Retain only a fixed public corpus for the exact local-control candidate."""
from pathlib import Path
import hashlib,json,os,subprocess,sys

BASE=Path(__file__).resolve().parent
PROJECT=BASE.parent
REPO=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(REPO/'src'))
from application.datasets.catalog import read_local
from application.cloud.safe_files import _windows_read,_posix_read
from application.platform.supervision import _local_path
from application.platform.distribution import verify_distribution
from application.qualification import revision_fact,parse_result,_sanitize

REVISION='083fd10e419e3eec903c3597093ea56e465f57cd'
SHORT=REVISION[:7]
EXPECTED=dict(revision=REVISION,worktree='CLEAN')
REF=f'status/codex/productization/S12/storage-qualified-{SHORT}-py312'
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
REVIEWED={
    's12_qualification_storage_memory_retry_native.py':'6a3dfe23926aa92c6fd7d50795a920036da741ca21bbc6580dfa7e71493ed8d4',
    's09_local_paper_control_native_http.py':'4cf8ae8a9837a6280a6c6a07640d65a5ad3c7449516dd0d545c810540f9ec718',
    'test_s12_native_reader_subject.py':'cf253ac5571c30d1d59e62b97ac9e1d3c1aa4c8f8aaefdf1bc43f6900500c4f8',
    's12_storage_awake_source_qualify.py':'affb0fab3da1f260f43ceed31932192eaf47c60ef2b512a666e3b19ac3370e92',
    's09_local_paper_control_native_regression.py':'ae79794233ae72bc288c9a7afefd81a4dc1199e1450783b68fe7fcdbe5ae1a2f',
    's12_storage_native_paper_reader.py':'64827044fd5960610cb9302f4dd7351062820a1fd25127eb373e8674eacd8b98',
    's12_storage_reader_fixed_native_regression.py':'c9130672d157300a737daf9038b801ff21033c6698989f44ca20894bb2e428a1',
    'test_s12_reader_fixed_native_final_guards.py':'1a44629ac5768d96d6c5e26af3b4da450caf66286102160413eb1860f582a930',
    's09_owner_worker_native_regression.py':'20c41ca946c78f8c98d418707ea9d90a0443096b9d32d71b34fd66576354a2af',
    's09_owner_worker_source_qualify.py':'77b2ba6ffd9419d40904dc94a1dd4a2c70aa4cc0041d962d779b877860d4c679',
    's13_native_access_integrity.py':'0f98ebae810800be38138c23099dfedaec6dd0daa6416bd60ba083716dc0d186',
    's12_storage_memory_retry_source_qualify.py':'d25b855607ca1b88c846f22f0a0244030ae9f436fa0a07245dfb9a10be4e06e8',
    'local_windows_qualification_awake.py':'626783f420996584618930fd50f2f1285d7d5536ae0bd672fe9191003be91f34',
    'test_local_windows_qualification_awake.py':'87c340e4f3550f7acc17112e1bf180c0123c2de0cd993075457cb7c96343dd4c',
}

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
    source=BASE/f'r7-productization-S12-storage-memory-retry-qualified-{SHORT}'
    q=report(source/'qualification.json','source/qualification.json')
    context=report(source/'qualification-context.json','source/qualification-context.json')
    hardware=report(source/'hardware-observations.json','source/hardware-observations.json')
    native=report(BASE/f'S12-storage-reader-fixed-{SHORT}-native-regression.json','native/native-regression.json')
    native_paths=[BASE/'s12_storage_reader_fixed_native_regression.py',BASE/'s09_local_paper_control_native_regression.py',BASE/'s09_owner_worker_native_regression.py',
        BASE/'s12_storage_native_paper_reader.py',BASE/'s13_native_access_integrity.py',
        REPO/'src/application/platform/_loopback_probe.py',REPO/'tools/build_product.py',REPO/'tools/verify_native_product.py',
        BASE/'s14_feedback_cli_native_paper.py',BASE/'S14LocalFakeRclone.exe',BASE/'S14LocalFakeRclone.cs',
        source/'qualification.json',source/'qualification-context.json',BASE/'s09_owner_worker_source_qualify.py',
        BASE/'s12_storage_memory_retry_source_qualify.py',BASE/'local_windows_qualification_awake.py']
    assert set(native['input_hashes_before'])=={p.relative_to(PROJECT).as_posix() for p in native_paths},'UNEXPECTED_NATIVE_INPUT_SET'
    assert native['input_hashes_before']==native['input_hashes_after']
    for path in (source/'qualification.json',source/'qualification-context.json'):
        assert sha(snapshots[path])==native['input_hashes_before'][path.relative_to(PROJECT).as_posix()]
    assert q['passed'] is True and q['tests_run']==1991 and len(q['commands'])==33
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
    assert phase==dict(phase_1=247,phase_2=1744)
    tracked=set(subprocess.check_output(['git','ls-files','--','src','tests','tools','packaging','ui','docs','contracts'],
        cwd=REPO,text=True,encoding='utf-8',timeout=15).splitlines())
    assert len(tracked)==614 and set(context['source_input_hashes'])==tracked,'UNEXPECTED_SOURCE_INPUT_SET'
    for name,expected in context['source_input_hashes'].items():
        path=REPO/name;_local_path(path)
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert sha((_windows_read if os.name=='nt' else _posix_read)(path,64*1024**2))==expected
    for name,expected in REVIEWED.items():assert sha(capture(BASE/name,'tools/'+name))=='sha256:'+expected
    assert context['launcher_sha256']=='sha256:'+REVIEWED['s12_storage_memory_retry_source_qualify.py']
    assert context['awake_request']['restored'] is True
    assert context['awake_helper_sha256_before']==context['awake_helper_sha256_after']=='sha256:'+REVIEWED['local_windows_qualification_awake.py']
    assert native['awake_request']['restored'] is True
    for label,failures,code in [('RED',4,1),('GREEN',0,0)]:
        name=f'S12-local-windows-awake-{label}.log';raw=capture(BASE/name,'tool-history/'+name)
        result=parse_result(raw.decode('utf-8').replace('\r\n','\n'),returncode=code)
        assert (result.tests_run,result.failures,result.errors,result.returncode)==(4,failures,0,code)
    awake_api=report(BASE/'S12-local-windows-awake-actual-api.json','tool-history/awake-actual-api.json')
    assert awake_api['requested'] is True and awake_api['restored'] is True
    for label,failures,code in [('RED',3,1),('GREEN',0,0)]:
        name=f'S12-native-final-proof-guards-{label}.log' if label=='RED' else 'S12-reader-fixed-native-final-guards-GREEN.log';raw=capture(BASE/name,'tool-history/'+name)
        result=parse_result(raw.decode('utf-8').replace('\r\n','\n'),returncode=code)
        assert (result.tests_run,result.failures,result.errors,result.returncode)==(3,failures,0,code)
    for name in ('retain_s12_storage_reader_fixed_qualification.py','test_s12_storage_reader_fixed_retention_scope.py'):
        capture(BASE/name,'tools/'+name)
    for label in ('GREEN',):
        name=f'S12-storage-reader-fixed-retention-scope-{label}.log';raw=capture(BASE/name,'tool-history/'+name)
        result=parse_result(raw.decode('utf-8').replace('\r\n','\n'),returncode=0)
        assert result.passed and result.tests_run==2
    review=report(BASE/'S12-storage-reader-fixed-bounded-review.json','bounded-review.json')
    assert review['critical']==review['important']==0 and review['reviewer_execution']=='NONE'
    expected_review=set(REVIEWED)|{'retain_s12_storage_reader_fixed_qualification.py','test_s12_storage_reader_fixed_retention_scope.py'}
    assert set(review['reviewed_external_raw_sha256'])==expected_review
    for name,expected in review['reviewed_external_raw_sha256'].items():assert sha(capture(BASE/name))=='sha256:'+expected
    assert native['passed'] is True and native['executable_revision']==REVISION
    assert native['native_worker_invoked'] is False and native['ordinary_native_paper']=='NOT_RUN'
    assert [c['label'] for c in native['commands']]==['build','smoke','historical-paper','paper-reader']
    for path in native_paths:assert sha(capture(path))==native['input_hashes_before'][path.relative_to(PROJECT).as_posix()]
    for command in native['commands']:
        assert command['passed'] is True and command['tree_reaped'] is True and command['exit_code']==0
        assert command['log']==f'S12-storage-reader-fixed-{SHORT}-native-{command["label"]}.log'
        assert sha(capture(BASE/command['log'],'native/'+command['log']))==command['log_sha256']
    build_root=BASE/f'r7-native-windows-S12-storage-reader-fixed-{SHORT}';package=build_root/'dist/R7'
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
        prefix='r7-native-S12-storage-reader-fixed-reader-fixed' if label in ('smoke','historical') else 'r7-native-S12-storage-reader-fixed'
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
    failed_root=BASE/f'r7-productization-S09-owner-worker-qualified-{SHORT}'
    failed=report(failed_root/'qualification.json','failed-source/qualification.json')
    failed_context=report(failed_root/'qualification-context.json','failed-source/qualification-context.json')
    capture(failed_root/'hardware-observations.json','failed-source/hardware-observations.json')
    assert failed['passed'] is False and failed['tests_run']==1946 and len(failed['commands'])==32
    assert failed['source_before']==failed['source_after']==failed_context['source_before']==failed_context['source_after']==EXPECTED
    assert failed_context['inputs_unchanged'] is True and failed_context['source_input_hashes']==context['source_input_hashes']
    assert failed_context['launcher_sha256']=='sha256:'+REVIEWED['s09_owner_worker_source_qualify.py']
    assert [c['log'] for c in failed['commands']]==SOURCE_LOGS[:32]
    assert sum(c['errors'] for c in failed['commands'])==1 and sum(c['failures'] for c in failed['commands'])==0
    for c in failed['commands']:
        assert c['tree_reaped'] is True and c['skipped']==c['expected_failures']==c['unexpected_successes']==0
        raw=capture(failed_root/c['log'],'failed-source/'+c['log'])
        assert sha(raw)=='sha256:'+c['log_sha256']
        parsed=parse_result(raw.decode('utf-8').replace('\r\n','\n'),returncode=c['returncode'])
        assert (parsed.tests_run,parsed.failures,parsed.errors)==(c['tests_run'],c['failures'],c['errors'])
    for name in ['S12-083fd10-host-power-transitions.json','S12-083fd10-source-failure-disposition.json',
                 'S12-host-resume-failing-case-GREEN.json','S12-host-resume-failing-case-GREEN.log']:
        capture(BASE/name,'failed-source/'+name)
    resumed=json.loads(snapshots[BASE/'S12-host-resume-failing-case-GREEN.json'])
    assert resumed['tests_run']==1 and resumed['returncode']==0 and resumed['tree_reaped'] is True and resumed['awake_request']['restored'] is True
    assert sha(snapshots[BASE/'S12-host-resume-failing-case-GREEN.log'])==resumed['log_sha256']
    memory_failed_root=BASE/f'r7-productization-S12-storage-awake-qualified-{SHORT}'
    memory_failed=report(memory_failed_root/'qualification.json','failed-memory-source/qualification.json')
    memory_context=report(memory_failed_root/'qualification-context.json','failed-memory-source/qualification-context.json')
    capture(memory_failed_root/'hardware-observations.json','failed-memory-source/hardware-observations.json')
    assert memory_failed['passed'] is False and memory_failed['tests_run']==1991 and len(memory_failed['commands'])==33
    assert memory_failed['source_before']==memory_failed['source_after']==memory_context['source_before']==memory_context['source_after']==EXPECTED
    assert memory_context['inputs_unchanged'] is True and memory_context['source_input_hashes']==context['source_input_hashes']
    assert memory_context['awake_request']['restored'] is True
    assert memory_context['launcher_sha256']=='sha256:'+REVIEWED['s12_storage_awake_source_qualify.py']
    assert [c['log'] for c in memory_failed['commands']]==SOURCE_LOGS
    assert sum(c['errors'] for c in memory_failed['commands'])==2 and sum(c['failures'] for c in memory_failed['commands'])==0
    for c in memory_failed['commands']:
        assert c['tree_reaped'] is True and c['skipped']==c['expected_failures']==c['unexpected_successes']==0
        raw=capture(memory_failed_root/c['log'],'failed-memory-source/'+c['log'])
        assert sha(raw)=='sha256:'+c['log_sha256']
        parsed=parse_result(raw.decode('utf-8').replace('\r\n','\n'),returncode=c['returncode'])
        assert (parsed.tests_run,parsed.failures,parsed.errors)==(c['tests_run'],c['failures'],c['errors'])
    for name in ['S12-083fd10-memory-pressure-source-disposition.json','S12-memory-pressure-failing-cases-GREEN.json','S12-memory-pressure-failing-cases-GREEN.log']:
        capture(BASE/name,'failed-memory-source/'+name)
    memory_disposition=json.loads(snapshots[BASE/'S12-083fd10-memory-pressure-source-disposition.json'])
    assert memory_disposition['qualification_credit']=='NONE' and memory_disposition['errors']==2 and memory_disposition['source_changes']=='NONE'
    memory_resumed=json.loads(snapshots[BASE/'S12-memory-pressure-failing-cases-GREEN.json'])
    assert memory_resumed['passed'] is True and memory_resumed['tests_run']==2 and memory_resumed['returncode']==0 and memory_resumed['tree_reaped'] is True
    assert memory_resumed['source_before']==memory_resumed['source_after']==EXPECTED and memory_resumed['source_inputs_unchanged'] is True
    assert memory_resumed['awake_request']['restored'] is True
    assert sha(snapshots[BASE/'S12-memory-pressure-failing-cases-GREEN.log'])==memory_resumed['log_sha256']
    for label,failures,code in [('RED',1,1),('GREEN',0,0)]:
        name=f'S12-native-reader-subject-{label}.log';raw=capture(BASE/name,'tool-history/'+name)
        parsed=parse_result(raw.decode('utf-8').replace('\r\n','\n'),returncode=code)
        assert (parsed.tests_run,parsed.failures,parsed.errors,parsed.returncode)==(3,failures,0,code)
    failed_native=report(BASE/f'S12-storage-{SHORT}-native-regression.json','failed-native/native-regression.json')
    assert failed_native['passed'] is False and [c['label'] for c in failed_native['commands']]==['build','smoke','historical-paper','paper-reader']
    assert all(c['passed'] and c['tree_reaped'] and c['exit_code']==0 for c in failed_native['commands'][:3])
    assert not failed_native['commands'][-1]['passed'] and failed_native['commands'][-1]['tree_reaped'] and failed_native['commands'][-1]['exit_code']==1
    old_native_paths=[BASE/'s12_qualification_storage_memory_retry_native.py',BASE/'s09_local_paper_control_native_regression.py',BASE/'s09_owner_worker_native_regression.py',
        BASE/'s09_local_paper_control_native_http.py',BASE/'s13_native_access_integrity.py',REPO/'src/application/platform/_loopback_probe.py',
        REPO/'tools/build_product.py',REPO/'tools/verify_native_product.py',BASE/'s14_feedback_cli_native_paper.py',BASE/'S14LocalFakeRclone.exe',BASE/'S14LocalFakeRclone.cs',
        source/'qualification.json',source/'qualification-context.json',BASE/'s09_owner_worker_source_qualify.py',BASE/'s12_storage_memory_retry_source_qualify.py',BASE/'local_windows_qualification_awake.py']
    assert set(failed_native['input_hashes_before'])=={p.relative_to(PROJECT).as_posix() for p in old_native_paths},'UNEXPECTED_FAILED_NATIVE_INPUT_SET'
    for path in old_native_paths:assert sha(capture(path))==failed_native['input_hashes_before'][path.relative_to(PROJECT).as_posix()]
    for c in failed_native['commands']:
        assert c['log']==f'S12-storage-{SHORT}-native-{c["label"]}.log'
        assert sha(capture(BASE/c['log'],'failed-native/'+c['log']))==c['log_sha256']
    failed_build_root=BASE/f'r7-native-windows-S12-storage-{SHORT}';failed_package=failed_build_root/'dist/R7'
    failed_identity=verify_distribution(failed_package);assert failed_identity==failed_native['native_build_identity']
    failed_build=report(failed_build_root/'build-result.json','failed-native-build/build-result.json')
    assert failed_build['identity']==failed_identity and failed_build['source']==EXPECTED|{'implementation_hash':context['implementation_hash']}
    assert failed_build['archive']==f'r7-product-0.2.0-windows-{SHORT}.zip'
    assert sha(capture(failed_build_root/failed_build['archive'],limit=128*1024**2))=='sha256:'+failed_build['archive_sha256']
    for path,target in [(failed_build_root/'pyinstaller.log','pyinstaller.log'),(failed_package/'distribution.json','distribution.json'),(failed_package/'licenses/inventory.json','licenses-inventory.json')]:
        capture(path,'failed-native-build/'+target)
    for label,name,count,logs in [('smoke','native-smoke.json',8,SMOKE_LOGS),('historical','native-paper-feedback.json',3,['01-historical-paper-publish.log','02-historical-paper-idempotent.log'])]:
        folder=BASE/f'r7-native-S12-storage-{label}-{SHORT}';target='failed-native-'+label
        probe=report(folder/name,target+'/'+name)
        assert probe['passed'] is True and probe['identity']==failed_identity and probe['scenario_count']==count
        assert [c['log'] for c in probe['commands']]==logs
        for c in probe['commands']:
            assert c['passed'] is True and c['tree_reaped'] is True
            expected=c['log_sha256'];raw=capture(folder/c['log'],target+'/'+c['log'])
            assert sha(raw)==(expected if expected.startswith('sha256:') else 'sha256:'+expected)
    failed_native_disposition=report(BASE/'S12-083fd10-native-reader-failure-disposition.json','failed-native/disposition.json')
    assert failed_native_disposition['qualification_credit']=='NONE' and failed_native_disposition['reader_fixture_created'] is False
    assert failed_native_disposition['native_input_hashes_verified_after']==failed_native['input_hashes_before']
    samples=hardware['samples'];assert samples
    memory=dict(samples=len(samples),minimum_available_bytes=min(x['available_memory_bytes'] for x in samples),
        below_unchanged_admission_threshold=sum(x['available_memory_bytes']<x['existing_admission_minimum_bytes'] for x in samples),
        scope=hardware['scope'])
    facts=dict(task_id=context['task_id'],spec_baseline=context['spec_baseline'],spec_revision=context['spec_revision'],
        revision=REVISION,implementation_hash=context['implementation_hash'],source=dict(passed=True,tests=1991,commands=33,phase=phase),
        native_build=identity,native_scoped=dict(passed=True,scenarios=13,commands=13,wrapper_stages=4),memory=memory,
        ordinary_native_paper='NOT_RUN',native_worker_invoked=False,browser='NOT_RUN_FOR_THIS_CANDIDATE',
        production_qualified_release_profile='PROPOSED_NOT_ACTIVE',ubuntu24='NOT_RUN',ubuntu26='NOT_RUN',
        real_cloud='NOT_RUN',real_dataset='NOT_RUN',real_forward='NOT_RUN',provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',
        accepted_prior_revision='41fa2fe0d74435fed5831ed728af8b87c28883f0',
        external_guard_tests=3,external_retention_guard_tests=2,external_awake_guard_tests=4,
        source_awake_request=context['awake_request'],native_awake_request=native['awake_request'],
        preserved_failed_attempt=dict(commands=32,tests=1946,errors=1,reason='ACTUAL_HOST_STANDBY_SLEEP;LEASE_EXPIRED;NO_QUALIFICATION_CREDIT'),
        preserved_memory_pressure_attempt=dict(commands=33,tests=1991,errors=2,reason='ACTUAL_MEMORY_PRESSURE;UNCHANGED_ADMISSION_THRESHOLD;NO_QUALIFICATION_CREDIT'),external_memory_recovery_cases=2,
        preserved_native_reader_attempt=dict(wrapper_stages=4,successful_stages=3,reader_scenarios=0,reason='STALE_HISTORICAL_READER_SUBJECT;NO_QUALIFICATION_CREDIT'),external_native_reader_subject_guards=3,
        scope='INTERNAL_SOFTWARE_QUALIFICATION_STORAGE_INCREMENT;SOURCE_FULL_AND_EXISTING_SCOPED_NATIVE_REGRESSIONS;NO_RECEIPT_PRODUCER_ADMISSION_OR_ORDINARY_PAPER',
        owning_producer='NOT_IMPLEMENTED',storage_new_cases=17,
        limitations=['1991 source execution instances include focused repeats; not1991 distinct test definitions.',
            'Native13 scenarios are8 first-run,3 historical publication,2 authenticated empty inventory/start-denial; bundled worker not invoked.',
            'Fresh synthetic local auth fixture is source-created; no native CLI enrollment or existing user auth read.',
            'Native reader control teardown is owned kernel termination; no managed-stop proof.',
            'Current browser/full native PAPER/whole-product acceptance NOT_RUN; historical revisions not transferred.',
            'Host memory observations do not qualify24GB target or pressure capacity.',
            'Bounded independent tooling/source review is not whole-product acceptance.'])
    retained['disposition.json']=encoded(facts)
    for path,raw in snapshots.items():assert read_public(path,max(64*1024**2,len(raw)))==raw
    assert revision_fact(REPO,REVISION,True)==EXPECTED and verify_distribution(package)==identity
    return retained,snapshots,facts

def main():
    retained,snapshots,facts=collect();assert len(retained)==188;target=REPO/REF
    _local_path(target);assert not os.path.lexists(target);target.mkdir()
    manifest={}
    for name,raw in sorted(retained.items()):
        path=target/name;_local_path(path);path.parent.mkdir(exist_ok=True)
        with path.open('xb') as stream:stream.write(raw)
        assert read_local(path.parent,path.name,64*1024**2)==raw
        manifest[path.relative_to(REPO).as_posix()]=sha(raw)
    path=target.parent/f'storage-qualified-artifact-hashes-{SHORT}.json';_local_path(path)
    with path.open('xb') as stream:stream.write(encoded(dict(files=manifest,
        captured_raw_sha256={p.relative_to(PROJECT).as_posix():sha(raw) for p,raw in snapshots.items()},
        capture_tool_sha256=sha(read_public(Path(__file__),1024**2)),scope='FIXED_PUBLIC_CORPUS;PRIVATE_DB_CONFIG_ARCHIVE_NOT_RETAINED')))
    print(json.dumps(dict(retained_files=len(manifest),source_tests=1991,native_scoped=facts['native_scoped'],state='MASTER_IN_PROGRESS')))

if __name__=='__main__':main()
