"""Retain bounded public qualification snapshots; never private product data."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, os, re, subprocess, sys

BASE=Path(__file__).resolve().parent
PROJECT=BASE.parent
REPO=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(REPO/'src'))
from application.datasets.catalog import read_local
from application.cloud.safe_files import _windows_read, _posix_read
from application.platform.distribution import verify_distribution
from application.platform.supervision import _local_path
from application.qualification import revision_fact, parse_result, _sanitize

REVISION='9bf85349a81486297dbfb3e452f84f67421230d5'
SHORT=REVISION[:7]
EXPECTED=dict(revision=REVISION,worktree='CLEAN')
REF=f'status/codex/productization/S09/owner-worker-qualified-{SHORT}-py312'
REVIEWED={
    's09_owner_worker_native_regression.py':'20c41ca946c78f8c98d418707ea9d90a0443096b9d32d71b34fd66576354a2af',
    'test_s09_native_wrapper_guards.py':'b908e5b4f971581f8e591007e5c70525f4cac85f9a6c04381e2ff5fdbb977416',
    's09_owner_worker_source_qualify.py':'77b2ba6ffd9419d40904dc94a1dd4a2c70aa4cc0041d962d779b877860d4c679',
}

def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
def encoded(value):return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def safe_name(name):
    if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}',name) or name in ('.','..'):
        raise ValueError('Owned plain artifact name required')
    return name

def collect():
    assert revision_fact(REPO,REVISION,True)==EXPECTED
    snapshots={};retained={}
    def capture(path,target=None,limit=64*1024**2):
        path=Path(path)
        if path not in snapshots:snapshots[path]=read_local(path.parent,path.name,limit)
        raw=snapshots[path]
        if target is not None:
            if target in retained:raise ValueError('Duplicate retained target')
            retained[target]=_sanitize(raw.decode('utf-8'),REPO).replace('\r\n','\n').encode('utf-8')
        return raw
    def report(path,target):return json.loads(capture(path,target))
    source=BASE/f'r7-productization-S09-owner-worker-qualified-{SHORT}'
    qualification=report(source/'qualification.json','source/qualification.json')
    context=report(source/'qualification-context.json','source/qualification-context.json')
    hardware=report(source/'hardware-observations.json','source/hardware-observations.json')
    native=report(BASE/f'S09-owner-worker-{SHORT}-native-regression.json','native/native-regression.json')
    expected_native={path.relative_to(PROJECT).as_posix() for path in (
        BASE/'s09_owner_worker_native_regression.py',REPO/'tools/build_product.py',REPO/'tools/verify_native_product.py',
        BASE/'s14_feedback_cli_native_paper.py',BASE/'S14LocalFakeRclone.exe',BASE/'S14LocalFakeRclone.cs',
        source/'qualification.json',source/'qualification-context.json',BASE/'s09_owner_worker_source_qualify.py',
        BASE/'test_s09_native_wrapper_guards.py')}
    assert set(native['input_hashes_before'])==expected_native
    assert native['input_hashes_before']==native['input_hashes_after']
    for path in (source/'qualification.json',source/'qualification-context.json'):
        assert sha(snapshots[path])==native['input_hashes_before'][path.relative_to(PROJECT).as_posix()]
    assert qualification['passed'] is True and qualification['tests_run']==1970 and len(qualification['commands'])==33
    assert qualification['source_before']==qualification['source_after']==context['source_before']==context['source_after']==EXPECTED
    assert context['inputs_unchanged'] is True and context['memory_monitor_joined'] is True
    assert context['configuration']==dict(suites=['all'],include_focused=True,require_clean=True,timeout_seconds=900,expected_revision=REVISION)
    phase=dict(phase_1=0,phase_2=0)
    for command in qualification['commands']:
        assert command['passed'] is True and command['tree_reaped'] is True and command['source_after']==EXPECTED
        assert command['returncode']==command['failures']==command['errors']==command['skipped']==command['expected_failures']==command['unexpected_successes']==0
        name=safe_name(command['log']);raw=capture(source/name,'source/'+name)
        assert sha(raw)=='sha256:'+command['log_sha256']
        outcome=parse_result(raw.decode('utf-8').replace('\r\n','\n'),returncode=0)
        assert outcome.passed and outcome.tests_run==command['tests_run']
        phase[command['phase']]+=command['tests_run']
    assert phase==dict(phase_1=247,phase_2=1723)
    tracked=set(subprocess.check_output(['git','ls-files','--','src','tests','tools','packaging','ui','docs','contracts'],
        cwd=REPO,text=True,encoding='utf-8',timeout=15).splitlines())
    assert len(tracked)==609 and set(context['source_input_hashes'])==tracked
    for name,expected in context['source_input_hashes'].items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        path=REPO/name;_local_path(path)
        # Tracked dotfiles use native repository names, not cloud path grammar.
        raw=(_windows_read if os.name=='nt' else _posix_read)(path,64*1024**2)
        assert sha(raw)==expected
    for name,expected in REVIEWED.items():
        assert sha(capture(BASE/name,'tools/'+name))=='sha256:'+expected
    assert context['launcher_sha256']=='sha256:'+REVIEWED['s09_owner_worker_source_qualify.py']
    for label,counts in [('RED',(4,4,0,1)),('GREEN',(4,0,1,1)),('AFTER_SHARING_REPAIR',(4,0,0,0))]:
        name=f'S09-native-wrapper-guards-{label}.log'
        raw=capture(BASE/name,'tool-history/'+name)
        parsed=parse_result(raw.decode('utf-8').replace('\r\n','\n'),returncode=counts[3])
        assert (parsed.tests_run,parsed.failures,parsed.errors,parsed.returncode)==counts
    for label,counts in [('RED',(2,0,2,1)),('GREEN',(2,0,0,0))]:
        name=f'S09-retention-private-scope-{label}.log'
        raw=capture(BASE/name,'tool-history/'+name)
        parsed=parse_result(raw.decode('utf-8').replace('\r\n','\n'),returncode=counts[3])
        assert (parsed.tests_run,parsed.failures,parsed.errors,parsed.returncode)==counts
    capture(Path(__file__),'tools/'+Path(__file__).name)
    capture(BASE/'test_s09_qualification_retention_scope.py','tools/test_s09_qualification_retention_scope.py')
    assert native['passed'] is True and native['executable_revision']==REVISION
    assert native['native_worker_invoked'] is False and native['ordinary_native_paper']=='NOT_RUN'
    assert native['input_hashes_before']==native['input_hashes_after']
    for name,expected in native['input_hashes_before'].items():
        assert not Path(name).is_absolute() and '..' not in Path(name).parts
        assert sha(capture(PROJECT/name))==expected
    assert [item['label'] for item in native['commands']]==['build','smoke','historical-paper']
    for command in native['commands']:
        assert command['passed'] is True and command['tree_reaped'] is True and command['exit_code']==0
        name=safe_name(command['log']);raw=capture(BASE/name,'native/'+name)
        assert sha(raw)==command['log_sha256']
    build_root=BASE/f'r7-native-windows-S09-owner-worker-{SHORT}'
    package=build_root/'dist/R7';identity=verify_distribution(package)
    assert identity==native['native_build_identity'] and identity['executable_revision']==REVISION
    assert identity['implementation_hash']==context['implementation_hash']
    build=report(build_root/'build-result.json','native-build/build-result.json')
    assert build['identity']==identity and build['target']=='windows' and build['source']==EXPECTED|{'implementation_hash':context['implementation_hash']}
    archive=build_root/safe_name(build['archive'])
    assert sha(capture(archive,limit=128*1024**2))=='sha256:'+build['archive_sha256']
    capture(build_root/'pyinstaller.log','native-build/pyinstaller.log')
    capture(package/'distribution.json','native-build/distribution.json')
    capture(package/'licenses/inventory.json','native-build/licenses-inventory.json')
    for folder,name,target,scenarios,commands in [
        (BASE/f'r7-native-S09-owner-worker-smoke-{SHORT}','native-smoke.json','native-smoke',8,9),
        (BASE/f'r7-native-S09-owner-worker-historical-{SHORT}','native-paper-feedback.json','native-historical-paper',3,2)]:
        value=report(folder/name,target+'/'+name)
        assert value['passed'] is True and value['identity']==identity
        assert value['scenario_count']==scenarios and len(value['commands'])==commands
        assert len(value['scenarios'])==scenarios
        for item in value['scenarios']:
            assert item.get('passed',item.get('result')=='PASS') is True
        for command in value['commands']:
            assert command['passed'] is True and command['tree_reaped'] is True
            log=safe_name(command['log']);raw=capture(folder/log,target+'/'+log)
            assert sha(raw)==command['log_sha256'] if command['log_sha256'].startswith('sha256:') else sha(raw)=='sha256:'+command['log_sha256']
        if target=='native-historical-paper':
            assert value['normal_runtime']=='NOT_RUN' and value['fixture_cleanup_complete'] is True
            assert value['source_before']==value['source_after']==EXPECTED
            assert value['input_sha256_before']==value['input_sha256_after']
    samples=hardware['samples'];assert samples
    memory=dict(samples=len(samples),minimum_available_bytes=min(item['available_memory_bytes'] for item in samples),
        below_unchanged_admission_threshold=sum(item['available_memory_bytes']<item['existing_admission_minimum_bytes'] for item in samples),
        scope=hardware['scope'])
    disposition=dict(task_id=context['task_id'],spec_baseline=context['spec_baseline'],spec_revision=context['spec_revision'],
        revision=REVISION,source=dict(passed=True,tests=1970,commands=33,phase=phase),implementation_hash=context['implementation_hash'],
        native_build=identity,native_scoped=dict(passed=True,scenarios=11,commands=11,wrapper_stages=3),memory=memory,
        ordinary_native_paper='NOT_RUN',native_worker_invoked=False,browser='NOT_RUN_FOR_THIS_CANDIDATE',
        production_qualified_release_profile='PROPOSED_NOT_ACTIVE',ubuntu24='NOT_RUN',ubuntu26='NOT_RUN',
        real_cloud='NOT_RUN',real_dataset='NOT_RUN',real_forward='NOT_RUN',provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',
        accepted_prior_revision='fec8af0f70d787deea720b1e7f952c4fca9487b5',
        guard_history=dict(initial_red='4FAIL',intermediate_file_named_GREEN='3PASS_1ERROR_WINDOWS_SHARING',final='4PASS',
            retention_scope_red='2ERROR_MOCKED_PRIVATE_READ_TRAPS;NO_REAL_PRIVATE_READ',retention_scope_final='2PASS',
            scope='EXTERNAL_TOOL_ONLY;NO_NATIVE_OR_SOURCE_QUALIFICATION_CREDIT'),
        limitations=['Source execution instances include focused repeats; phase2 has1723 execution instances.',
            'Native11 scoped scenarios are8 first-run plus3 historical publication scenarios; new worker was bundled but not invoked.',
            'Source-created accelerated historical FIXTURE uses compiled local fake transport; no real cloud or forward observation.',
            'No current browser execution or full native acceptance; prior revisions remain historical and are not transferred.',
            'Hardware samples qualify this measured host only; no24GB target/resource-pressure qualification.',
            'Bounded source/launcher/wrapper review is not independent whole-product acceptance.'])
    retained['disposition.json']=encoded(disposition)
    retained['bounded-review.json']=encoded(dict(reviewer='/root/qualification_review',reviewer_execution='NONE',critical=0,important=0,
        reviewed_external_raw_sha256=REVIEWED,scope='SCOPED_SOURCE_QUALIFICATION_LAUNCHER_AND_NATIVE_WRAPPER;NO_WHOLE_PRODUCT_OR_VISUAL_REVIEW'))
    for path,raw in snapshots.items():assert read_local(path.parent,path.name,max(64*1024**2,len(raw)))==raw
    assert revision_fact(REPO,REVISION,True)==EXPECTED and verify_distribution(package)==identity
    return retained,snapshots,disposition

def main():
    retained,snapshots,facts=collect();target=REPO/REF
    _local_path(target);assert not os.path.lexists(target)
    target.mkdir()
    manifest={}
    for name,raw in sorted(retained.items()):
        path=target/name;_local_path(path);path.parent.mkdir(exist_ok=True)
        with path.open('xb') as stream:stream.write(raw)
        assert read_local(path.parent,path.name,64*1024**2)==raw
        manifest[path.relative_to(REPO).as_posix()]=sha(raw)
    manifest_path=target.parent/f'owner-worker-qualified-artifact-hashes-{SHORT}.json'
    _local_path(manifest_path)
    with manifest_path.open('xb') as stream:stream.write(encoded(dict(files=manifest,
        captured_raw_sha256={path.relative_to(PROJECT).as_posix():sha(raw) for path,raw in snapshots.items()},
        capture_tool_sha256=sha(read_local(BASE,Path(__file__).name,1024**2)),scope='PUBLIC_SCOPED_QUALIFICATION;PRIVATE_DB_CONFIG_ARCHIVE_NOT_RETAINED')))
    print(json.dumps(dict(retained_files=len(manifest),source_tests=facts['source']['tests'],native_scoped=facts['native_scoped'],state='MASTER_IN_PROGRESS')))

if __name__=='__main__':main()
