"""Retain captured public native workflow subjects only; no private corpus copy."""
import json,os,sys
from pathlib import Path
from s09_normal_fixture_source_qualify import BASE,REPO,inputs
from s09_owner_worker_native_regression import PROJECT,OwnedProof,sha,stamp,capture_qualification
from s09_local_paper_control_native_regression import read_input
from application.qualification import revision_fact
from application.platform.distribution import verify_distribution

SOURCE=sys.argv[1];REV='13d7375d6297c8df94124e95856821df6dee7f09'
REL='status/codex/productization/S09'
DEST=REPO/REL/'native-current-user-flow-13d7375'
MANIFEST=REPO/REL/'native-current-user-flow-artifact-hashes-13d7375.json'
PACKAGE=BASE/'r7-native-windows-S15-negative-intake-13d7375'
identity=verify_distribution(PACKAGE/'dist/R7')
revision_fact(REPO,SOURCE,True)
captures={};targets={};runs={}
def capture(path,target=None,limit=8*1024**2):
    raw=read_input(path,limit)
    if path in captures:assert captures[path]==raw
    captures[path]=raw
    if target is not None:
        assert target not in targets
        targets[target]=(path,raw)
    return raw
buildpath=BASE/'S15-negative-intake-13d7375-native-build.json'
build=json.loads(capture(buildpath))
assert build['passed'] and build['native_build_identity']==identity
assert build['source_before']==build['source_after']==dict(revision=REV,worktree='CLEAN')
captured=inputs();assert len(captured)==637 and captured==build['source_input_hashes']
q,context,qhash=capture_qualification(BASE/'r7-productization-S09-normal-fixture-qualified-13d7375',REV)
assert q['tests_run']==build['full_source_execution_instances']==2108
assert {str(p):h for p,h in qhash.items()}==build['source_qualification_hashes']
for path,digest in qhash.items():assert sha(capture(path))==digest
helpers=['s09_current_native_user_flow.py','record_s09_current_tty.py','s09_native_forward_ui_flow.py',
 's09_native_forward_ui_browser.mjs','s09_owner_worker_native_regression.py','s09_normal_fixture_source_qualify.py',
 's09_local_paper_control_native_regression.py','s13_native_access_integrity.py','local_windows_qualification_awake.py',
 'S15-negative-intake-13d7375-native-build.json']
for scenario,expected,counts in [('positive','CANDIDATE',(22,5,3)),('oos-loss','REJECTED',(8,3,2)),('insufficient-oos','BACKTESTING',(8,3,2))]:
    folder=BASE/f'r7-native-S09-current-user-flow-13d7375-{scenario}'
    outcome=json.loads(capture(folder/'native-normal-fixture-outcome.json',Path(scenario)/'native-normal-fixture-outcome.json'))
    assert outcome['passed'] is True and outcome['phase']=='COMPLETE' and outcome['scenario']==scenario
    assert outcome['source_revision']==SOURCE and outcome['executable_revision']==REV
    assert outcome['source_before']==outcome['source_after']==dict(revision=SOURCE,worktree='CLEAN')
    assert outcome['source_input_hashes']==captured and outcome['native_build_identity']==identity
    assert outcome['awake_request']['restored'] and all(outcome[k] for k in ['execution_inputs_unchanged','package_identity_unchanged','source_inputs_unchanged'])
    assert outcome['native_build_proof_sha256']==sha(captures[buildpath])
    assert (len(outcome['commands']),len(outcome['browser']),len(outcome['control_sessions']))==counts
    assert all(r['passed'] and r['tree_reaped'] for r in outcome['commands'])
    assert all(r['tree_reaped'] for r in outcome['control_sessions'])
    assert all(r['passed'] and r['remote_requests']==0 for r in outcome['browser'])
    results=[r for r in outcome['browser'] if r['stage']=='research-result'];assert len(results)==1 and results[0]['lifecycle']==expected
    for name,digest in outcome['execution_input_hashes'].items():
        assert sha(capture(Path(name),limit=128*1024**2))==digest
    for path,digest in qhash.items():assert outcome['execution_input_hashes'][str(path)]==digest
    initial=json.loads(capture(folder/'native-normal-fixture-flow.json',Path(scenario)/'native-normal-fixture-flow.json'))
    assert not initial['passed'] and initial['phase']=='AWAITING_OBSERVED_NATIVE_TTY'
    assert initial['execution_input_hashes']==outcome['execution_input_hashes'] and initial['native_build_identity']==identity
    tty=json.loads(capture(folder/'observed-native-tty-enrollment.json',Path(scenario)/'observed-native-tty-enrollment.json'))
    assert tty['actual_tool_tty'] and not tty['password_echoed'] and tty['exit_code']==0 and tty['status']=='OWNER_CONFIGURED'
    assert tty['native_build_identity']==identity and tty['config_sha256']==initial['initial_profile_sha256']
    assert tty['observer_sha256']==outcome['execution_input_hashes'][str(BASE/'record_s09_current_tty.py')]
    assert outcome['tty_evidence_sha256']==sha(captures[folder/'observed-native-tty-enrollment.json'])
    assert sha(capture(folder/'observed-native-tty-enrollment.log',Path(scenario)/'observed-native-tty-enrollment.log'))==tty['observed_transcript_sha256']
    for row in outcome['commands']+outcome['control_sessions']:
        name=row['log'];assert Path(name).name==name and name.endswith('.log')
        assert sha(capture(folder/name,Path(scenario)/name))==row['log_sha256']
    for row in outcome['browser']:
        assert row['screenshot']==row['stage']+'.png'
        assert sha(capture(folder/row['screenshot'],Path(scenario)/row['screenshot']))==row['screenshot_sha256']
    for name in helpers:
        path=folder/'execution-inputs'/name
        assert sha(capture(path,Path(scenario)/'execution-inputs'/name))==outcome['execution_input_hashes'][str(BASE/name)]
    if scenario=='positive':
        assert outcome['canonical_fills']==2 and outcome['canonical_closed_trades']==1 and outcome['real_elapsed_ns']==0
        assert len(outcome['paper_publications'])==2 and all(r['assessment']=='BLOCKED' and r['state']=='LOCAL_STAGED' for r in outcome['paper_publications'])
    else:
        assert outcome['native_paper_start']=='DENIED_BEFORE_RUN_CREATION' and outcome['native_paper_worker']=='NOT_STARTED'
        denied=[r for r in outcome['browser'] if r['stage']=='paper-denied'][0]
        assert denied['denial']=='CURRENT_OWNER_EVIDENCE_REQUIRED' and denied['registry_subject_unchanged'] and denied['paper_runs_after']==denied['paper_runs_before']==0
    runs[scenario]=dict(passed=True,lifecycle=expected,commands=counts[0],browser_stages=counts[1],control_starts=counts[2],outcome_sha256=sha(captures[folder/'native-normal-fixture-outcome.json']))
capture(Path(__file__),Path('execution-inputs')/Path(__file__).name)
review=BASE/'S09-current-native-readiness-review.json'
capture(review,Path('execution-inputs')/review.name)
reviewvalue=json.loads(captures[review]);assert reviewvalue['critical']==reviewvalue['important']==0 and reviewvalue['reviewer_execution']=='NONE'
assert reviewvalue['driver_sha256']==sha(captures[BASE/'s09_current_native_user_flow.py'])
def guard():
    assert inputs()==captured and verify_distribution(PACKAGE/'dist/R7')==identity
    for path,raw in captures.items():assert read_input(path,max(8*1024**2,len(raw)))==raw
guard()
assert not os.path.lexists(DEST) and not os.path.lexists(MANIFEST)
DEST.mkdir();files=[]
for target,(path,raw) in targets.items():
    published=raw
    if path.suffix!='.png':
        text=raw.decode('utf-8')
        for actual,label in [(REPO,'<SOURCE_ROOT>'),(PROJECT,'<PROJECT_ROOT>')]:
            for value in [str(actual),str(actual).replace('\\','/'),json.dumps(str(actual),ensure_ascii=False)[1:-1],json.dumps(str(actual),ensure_ascii=True)[1:-1]]:text=text.replace(value,label)
        published=text.replace('\r\n','\n').encode()
    destination=DEST/target;destination.parent.mkdir(parents=True,exist_ok=True)
    with OwnedProof(destination) as owner:owner.stream.write(published);owner.stream.flush();owner.require_owned()
    assert read_input(destination,8*1024**2)==published
    files.append(dict(source=path.relative_to(BASE).as_posix(),destination=destination.relative_to(REPO).as_posix(),original_sha256=sha(raw),published_sha256=sha(published),bytes=len(published),sanitized=raw!=published))
guard()
disposition=dict(passed=True,scope='CURRENT_ACTUAL_WINDOWS_NORMAL_PUBLIC_FIXTURE_THREE_OUTCOMES_ONLY',state='IN_PROGRESS',
 executable_revision=REV,execution_source_metadata_revision=SOURCE,native_build_identity=identity,scenarios=runs,
 owned_commands=38,native_cli_commands=27,native_browser_commands=11,observed_native_tty_enrollments=3,owned_control_starts=7,
 source_full_execution_instances=2108,source_full_commands=33,source_inputs=637,source_full_revision=REV,
 source_proof_ref='status/codex/productization/S15/source-13d7375/qualification.json',
 native_build_proof_ref='status/codex/productization/S15/native-build-13d7375.json',
 native_package=str(PACKAGE/'dist/R7'),archive=str(PACKAGE/build['archive_name']),archive_sha256=build['archive_sha256'],
 native_worker_stop='ACTUAL_PUBLIC_BOUNDED_MANAGED_STOP',native_control_stop='FORCED_REAPED;NO_GRACEFUL_CONTROL_STOP_CREDIT',
 paper_feedback='2_ACTUAL_BLOCKED_REPORTS;PERFORMANCE_OPT_OUT;LOCAL_STAGED;REMOTE_ACK0;REAL_ELAPSED_NS0',
 review='BOUNDED_TWO_TOOL_READINESS0C_I;NOT_WHOLE_MASTER_REVIEW',visual_review='SELF_ACTUAL_PAPER_CLOSED_SCREENSHOT;NOT_INDEPENDENT_ACCEPTANCE',
 ordinary_paper='NOT_RUN',production_profile='PROPOSED_NOT_ACTIVE',ubuntu24='NOT_RUN',ubuntu26='NOT_RUN',real_cloud='NOT_RUN',real_dataset='NOT_RUN',real_forward='NOT_RUN',
 provider_requests=0,credentials='NONE',capital='NONE',runtime_llm_calls=0,github_compute='NOT_USED',main_merge='NOT_PERFORMED',
 excluded='PRIVATE_PROFILES_AUTH_CONFIG_DATABASES_DATASETS_BACKUPS_TEMPORARY_BINARY_INPUTS',created_at_utc=stamp())
with OwnedProof(DEST/'disposition.json') as owner:owner.persist(disposition)
raw=read_input(DEST/'disposition.json',8*1024**2)
files.append(dict(source='GENERATED_PUBLIC_DISPOSITION',destination=(DEST/'disposition.json').relative_to(REPO).as_posix(),original_sha256=sha(raw),published_sha256=sha(raw),bytes=len(raw),sanitized=False))
with OwnedProof(MANIFEST) as owner:owner.persist(dict(executable_revision=REV,count=len(files),files=files,raw_and_published_hashes_explicit=True,private_exclusions=disposition['excluded']))
guard()
print(json.dumps(dict(retained=len(files),scenarios_passed=3,commands=38,browser_stages=11)))
