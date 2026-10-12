"""Publish explicit public native artifacts; retain private synthetic profiles locally."""
from pathlib import Path
import json,os
from s09_normal_fixture_source_qualify import BASE,REPO,inputs
from s09_owner_worker_native_regression import PROJECT,OwnedProof,sha,stamp
from s09_ui_dependency_inputs import protected_bytes
from application.qualification import revision_fact
from application.platform.distribution import verify_distribution

REV='dd533694df21bd3608e58408d14b5b05255b4d21'
REL='status/codex/productization/S09'
DEST=REPO/REL/'native-forward-ui-dd53369'
MANIFEST=REPO/REL/'native-forward-ui-artifact-hashes-dd53369.json'
PACKAGE=BASE/'r7-native-windows-S09-forward-ui-dd53369'
identity=verify_distribution(PACKAGE/'dist/R7')
revision_fact(REPO,REV,True)
build_path=BASE/'S09-forward-ui-dd53369-native-build.json'
build=json.loads(protected_bytes(build_path,8*1024**2))
assert build['passed'] and build['native_build_identity']==identity
captured=inputs();assert captured==build['source_input_hashes'] and len(captured)==636
assert not os.path.lexists(DEST) and not os.path.lexists(MANIFEST)
DEST.mkdir();files=[];runs={}
def publish(path,target):
    raw=protected_bytes(path,8*1024**2);out=raw
    if path.suffix!='.png':
        text=raw.decode('utf-8')
        for actual,label in [(REPO,'<SOURCE_ROOT>'),(PROJECT,'<PROJECT_ROOT>')]:
            for value in [str(actual),str(actual).replace('\\','/'),json.dumps(str(actual),ensure_ascii=False)[1:-1],json.dumps(str(actual),ensure_ascii=True)[1:-1]]:
                text=text.replace(value,label)
        out=text.replace('\r\n','\n').encode()
    target.parent.mkdir(parents=True,exist_ok=True)
    with OwnedProof(target) as owner:owner.stream.write(out);owner.stream.flush();owner.require_owned()
    assert protected_bytes(target,8*1024**2)==out
    files.append(dict(source=path.relative_to(BASE).as_posix(),destination=target.relative_to(REPO).as_posix(),
      original_sha256=sha(raw),published_sha256=sha(out),bytes=len(out),sanitized=out!=raw))
for name in ['S09-forward-ui-dd53369-native-build.json','S09-forward-ui-dd53369-native-build.log']:
    publish(BASE/name,DEST/'build'/name)
for name in ['build-result.json','pyinstaller.log','dist/R7/distribution.json','dist/R7/FIRST_RUN.md',
 'dist/R7/requirements-build-py312.lock','dist/R7/licenses/inventory.json']:
    publish(PACKAGE/name,DEST/'build'/Path(name).name)
for scenario,expected,commands,browsers,controls in [('positive','CANDIDATE',22,5,3),('oos-loss','REJECTED',8,3,2),('insufficient-oos','BACKTESTING',8,3,2)]:
    folder=BASE/('r7-native-S09-forward-ui-user-flow-dd53369-'+scenario)
    outcome=json.loads(protected_bytes(folder/'native-normal-fixture-outcome.json',8*1024**2))
    assert outcome['passed'] and outcome['phase']=='COMPLETE' and outcome['scenario']==scenario
    assert outcome['native_build_identity']==identity and outcome['source_input_hashes']==captured
    assert outcome['awake_request']['restored'] and outcome['execution_inputs_unchanged'] and outcome['package_identity_unchanged']
    assert len(outcome['commands'])==commands and len(outcome['browser'])==browsers and len(outcome['control_sessions'])==controls
    assert all(row['passed'] and row['tree_reaped'] for row in outcome['commands'])
    assert all(row['tree_reaped'] for row in outcome['control_sessions'])
    assert all(row['passed'] and row['remote_requests']==0 for row in outcome['browser'])
    results=[row for row in outcome['browser'] if row['stage']=='research-result'];assert len(results)==1
    assert results[0]['lifecycle']==expected
    tty=json.loads(protected_bytes(folder/'observed-native-tty-enrollment.json',8192))
    assert tty['actual_tool_tty'] and not tty['password_echoed'] and tty['exit_code']==0
    assert tty['native_build_identity']==identity
    for name in ['native-normal-fixture-flow.json','native-normal-fixture-outcome.json','observed-native-tty-enrollment.json','observed-native-tty-enrollment.log']:
        publish(folder/name,DEST/scenario/name)
    expected_logs={row['label']+'.log' for row in outcome['commands']}
    assert {row['log'] for row in outcome['commands']}==expected_logs
    expected_controls={'control-research.log','control-paper-start.log','control-paper-resume.log'} if scenario=='positive' else {'control-research.log','control-paper-denied.log'}
    assert {row['log'] for row in outcome['control_sessions']}==expected_controls
    for row in outcome['commands']+outcome['control_sessions']:
        path=folder/row['log'];assert sha(protected_bytes(path,8*1024**2))==row['log_sha256']
        publish(path,DEST/scenario/path.name)
    for row in outcome['browser']:
        assert row['screenshot']==row['stage']+'.png'
        path=folder/row['screenshot'];assert sha(protected_bytes(path,8*1024**2))==row['screenshot_sha256']
        publish(path,DEST/scenario/path.name)
    for name in ['s09_native_forward_ui_flow.py','s09_native_forward_ui_browser.mjs','s09_owner_worker_native_regression.py',
      's09_normal_fixture_source_qualify.py','s09_local_paper_control_native_regression.py','s13_native_access_integrity.py',
      'local_windows_qualification_awake.py','S09-forward-ui-dd53369-native-build.json']:
        path=folder/'execution-inputs'/name
        assert sha(protected_bytes(path,8*1024**2))==outcome['execution_input_hashes'][str(BASE/name)]
        publish(path,DEST/scenario/'execution-inputs'/name)
    if scenario=='positive':
        assert outcome['canonical_fills']==2 and outcome['canonical_closed_trades']==1 and outcome['real_elapsed_ns']==0
        assert len(outcome['paper_publications'])==2 and all(row['assessment']=='BLOCKED' for row in outcome['paper_publications'])
    else:
        assert outcome['native_paper_start']=='DENIED_BEFORE_RUN_CREATION' and outcome['native_paper_worker']=='NOT_STARTED'
        denial=[row for row in outcome['browser'] if row['stage']=='paper-denied'][0]
        assert denial['denial']=='CURRENT_OWNER_EVIDENCE_REQUIRED' and denial['registry_subject_unchanged']
    runs[scenario]=dict(lifecycle=expected,passed=True,commands=commands,browser_stages=browsers,control_starts=controls,
      tty_enrollment='ACTUAL_HIDDEN_TOOL_TTY',outcome_sha256=sha(protected_bytes(folder/'native-normal-fixture-outcome.json',8*1024**2)))
for name in ['s09_forward_ui_native_build.py','s09_native_forward_ui_flow.py','s09_native_forward_ui_browser.mjs',
 'record_s09_forward_ui_native_tty.py',Path(__file__).name]:
    publish(BASE/name,DEST/'execution-inputs'/name)
disposition=dict(executable_revision=REV,native_build_identity=identity,scope='ACTUAL_PACKAGED_WINDOWS_NORMAL_PUBLIC_FIXTURE_POSITIVE_AND_TWO_NEGATIVE_FLOWS',
 state='IN_PROGRESS',normal_native_fixture='PASS_3_OF3_SCENARIOS',scenarios=runs,
 owned_commands=38,native_cli_commands=27,native_browser_commands=11,observed_native_tty_enrollments=3,owned_control_starts=7,
 native_forward_seconds='RAW_REAL_ELAPSED_NS0_AND_RENDERED_SECONDS0;ACTUAL_PACKAGED_UI',
 native_package=str(PACKAGE/'dist/R7'),archive=str(PACKAGE/build['archive_name']),archive_sha256=build['archive_sha256'],
 inherited_full_python_revision='d3d849642f278ccd39723355367bf1030d8f0619',inherited_python_execution_instances=2101,
 current_ui_source_revision='9a48e09f877b46d5e6f0971cf6a47df8c0485859',current_ui_units=18,current_source_ui_browser_tests=11,
 new_full_python_run='NOT_RUN;PYTHON_BYTES_UNCHANGED',new_native_legacy25_baseline='NOT_RUN;HISTORICAL_D3_SCOPE_RETAINED',
 native_control_cleanup='FORCED_REAPED;NO_GRACEFUL_CONTROL_STOP_CREDIT',native_paper_worker_stop='PUBLIC_BOUNDED_MANAGED_STOP',
 native_backup_restore='ACTUAL_PROTECTED_STATE_PRESERVED;RESTORED_START_DENIED;SOURCE_UNCHANGED',
 paper_feedback='2_ACTUAL_BLOCKED_REPORTS;PERFORMANCE_OPT_OUT;LOCAL_STAGED;REMOTE_ACK0;REAL_ELAPSED_NS0',
 review='NATIVE_EXECUTION_DRIVER_SELF_REVIEW;PRIOR_UI_SOURCE_READ_ONLY0C_I_SEPARATE;NO_WHOLE_MASTER_REVIEW',
 visual_review='SELF_ACTUAL_POSITIVE_PACKAGED_PAPER_CLOSED_SCREENSHOT;NOT_INDEPENDENT_VISUAL_ACCEPTANCE',
 ordinary_paper='NOT_RUN',production_profile='PROPOSED_NOT_ACTIVE',ubuntu24='NOT_RUN',ubuntu26='NOT_RUN',
 real_cloud='NOT_RUN',real_dataset='NOT_RUN',real_forward='NOT_RUN',provider_requests=0,credentials='NONE',capital='NONE',
 runtime_llm_calls=0,github_compute='NOT_USED',main_merge='NOT_PERFORMED',
 excluded='PRIVATE_FIXTURE_PROFILES_AUTH_CONFIG_DATABASES_DATASETS_BACKUPS_TEMPORARY_AND_NODE_OR_NATIVE_BINARIES',
 created_at_utc=stamp(),retained_files=len(files)+1)
with OwnedProof(DEST/'disposition.json') as owner:owner.persist(disposition)
raw=protected_bytes(DEST/'disposition.json',8*1024**2)
files.append(dict(source='GENERATED_PUBLIC_DISPOSITION',destination=(DEST/'disposition.json').relative_to(REPO).as_posix(),
 original_sha256=sha(raw),published_sha256=sha(raw),bytes=len(raw),sanitized=False))
with OwnedProof(MANIFEST) as owner:owner.persist(dict(executable_revision=REV,count=len(files),files=files,
 raw_and_published_hashes_explicit=True,private_exclusions=disposition['excluded']))
assert inputs()==captured and verify_distribution(PACKAGE/'dist/R7')==identity
print(json.dumps(dict(retained=len(files),scenarios_passed=3,native_owned_commands=38,native_browser_stages=11)))
