"""Curated sanitized public evidence retention; never copies private fixture trees."""
from pathlib import Path
import json,os,re
from s09_owner_worker_native_regression import BASE,PROJECT,REPO,OwnedProof,sha,stamp
from s09_local_paper_control_native_regression import read_input
from s09_normal_fixture_source_qualify import inputs
from application.qualification import revision_fact
from application.platform.supervision import _local_path
from application.cloud.safe_files import _windows_read,_posix_read

REV='d3d849642f278ccd39723355367bf1030d8f0619'
SHORT=REV[:7]
REL=Path('status/codex/productization/S09')
DEST=REPO/REL/f'normal-fixture-qualified-{SHORT}-py312'
MANIFEST=REPO/REL/f'normal-fixture-qualified-artifact-hashes-{SHORT}.json'

def sanitize(raw,path):
    if path.suffix=='.png':return raw
    text=raw.decode('utf-8')
    for actual,label in [(REPO,'<SOURCE_ROOT>'),(PROJECT,'<PROJECT_ROOT>')]:
        for value in [str(actual),str(actual).replace('\\','/'),json.dumps(str(actual),ensure_ascii=False)[1:-1],json.dumps(str(actual),ensure_ascii=True)[1:-1]]:
            text=text.replace(value,label)
    if re.search(r'r7-native-fixture-only-[0-9A-Za-z!_-]{8,}',text):raise ValueError('Synthetic login value must not be published')
    return text.encode('utf-8')

def main():
    revision_fact(REPO,REV,True)
    context=json.loads(read_input(BASE/f'r7-productization-S09-normal-fixture-qualified-{SHORT}/qualification-context.json',8*1024**2))
    source=json.loads(read_input(BASE/f'r7-productization-S09-normal-fixture-qualified-{SHORT}/qualification.json',8*1024**2))
    native=json.loads(read_input(BASE/f'S09-normal-fixture-{SHORT}-native-regression.json',8*1024**2))
    flow_folder=BASE/f'r7-native-S09-normal-fixture-user-flow-{SHORT}-edge-pinned'
    flow=json.loads(read_input(flow_folder/'native-normal-fixture-outcome.json',8*1024**2))
    assert source['passed'] and source['tests_run']==2101 and len(source['commands'])==33
    assert context['inputs_unchanged'] and inputs()==context['source_input_hashes'] and len(inputs())==636
    assert native['passed'] and flow['passed'] and len(flow['browser'])==5 and len(flow['commands'])==22
    assert native['native_build_identity']==flow['native_build_identity']
    assert not os.path.lexists(DEST) and not os.path.lexists(MANIFEST)
    DEST.mkdir();files=[]
    def copy(path,target):
        if path.name=='_loopback_probe.py' and path.is_relative_to(BASE/'normal-fixture-native-execution-inputs'):
            _local_path(path)
            raw=(_windows_read if os.name=='nt' else _posix_read)(path,64*1024**2,require_single_link=True)
        else:raw=read_input(path,64*1024**2)
        published=sanitize(raw,path)
        target.parent.mkdir(parents=True,exist_ok=True)
        with OwnedProof(target) as owner:
            owner.stream.write(published);owner.stream.flush();owner.require_owned()
        assert read_input(target,64*1024**2)==published
        files.append(dict(source=path.relative_to(BASE).as_posix(),destination=target.relative_to(REPO).as_posix(),
          original_sha256=sha(raw),published_sha256=sha(published),bytes=len(published),sanitized=published!=raw))
    def public_root(folder,target):
        for path in sorted(folder.iterdir()):
            if not path.is_file():continue
            if path.suffix=='.json' and not path.name.startswith(('native-','observed-','qualification','hardware-')):continue
            if path.suffix in ('.json','.log','.png'):copy(path,target/path.name)
    attempts=[]
    for path in sorted(BASE.glob('S09-normal-fixture-*.json')):
        if path.name.endswith('-native-regression.json') or path.name.endswith('-independent-reviews.json'):continue
        value=json.loads(read_input(path,8*1024**2));copy(path,DEST/'bounded-history'/path.name)
        log=path.with_suffix('.log')
        if log.exists():
            raw=read_input(log,8*1024**2);assert sha(raw)==value['log_sha256']
            copy(log,DEST/'bounded-history'/log.name)
        attempts.append(dict(label=value.get('label'),revision=value.get('source_revision'),tests=value.get('tests_run'),
          failures=value.get('failures'),errors=value.get('errors'),skipped=value.get('skipped'),exit_code=value.get('exit_code'),
          scope=value.get('scope'),qualified_product_acceptance='NONE;HISTORICAL_BOUNDED_OR_DIAGNOSTIC_ONLY',
          retained_execution_closure=value.get('execution_inputs_retained_at'),
          closure_limit='COMPLETE_RETAINED_NAMED_EXTERNAL_CODE' if value.get('execution_inputs_retained_at') else 'EARLY_EXTERNAL_DRIVER_VERSIONS_NOT_RETAINED;NOT_FULLY_REPLAYABLE'))
    for folder_name in [f'r7-productization-S09-normal-fixture-qualified-666fdde',f'r7-productization-S09-normal-fixture-qualified-{SHORT}']:
        public_root(BASE/folder_name,DEST/'source'/('failed' if '666fdde' in folder_name else 'passed'))
    for path in sorted(BASE.glob(f'S09-normal-fixture-{SHORT}-native-*')):
        if path.is_file() and path.suffix in ('.json','.log'):copy(path,DEST/'native-baseline'/path.name)
    for index,folder_name in enumerate([f'r7-native-S09-normal-fixture-reader-fixed-smoke-{SHORT}',f'r7-native-S09-normal-fixture-reader-fixed-historical-{SHORT}',
      f'r7-native-S12-storage-reader-fixed-reader-{SHORT}',f'r7-native-S09-public-setup-probe-{SHORT}',f'r7-native-S09-long-backup-probe-{SHORT}']):
        public_root(BASE/folder_name,DEST/'native-baseline'/str(index))
    for index,folder in enumerate([BASE/f'r7-native-S09-normal-fixture-user-flow-{SHORT}',flow_folder]):
        public_root(folder,DEST/'native-flow'/str(index))
        for path in sorted((folder/'execution-inputs').iterdir()):
            if path.is_file():copy(path,DEST/'native-flow'/str(index)/'inputs'/path.name)
    for folder_name in ['normal-fixture-execution-inputs','normal-fixture-native-execution-inputs']:
        for path in sorted((BASE/folder_name).rglob('*')):
            if path.is_file() and path.suffix in ('.py','.mjs','.cs','.json'):
                relative=path.relative_to(BASE/folder_name)
                prefix='bounded' if folder_name=='normal-fixture-execution-inputs' else 'native'
                copy(path,DEST/'closures'/prefix/relative.parts[0][:8]/path.name.lstrip('_'))
    for name in ['s09_normal_fixture_source_qualify.py','s09_normal_fixture_native_regression.py','s09_native_normal_fixture_flow.py',
      's09_native_normal_fixture_browser.mjs','record_s09_observed_native_tty.py','local_windows_qualification_awake.py',
      'S09-normal-fixture-independent-reviews.json',Path(__file__).name]:
        copy(BASE/name,DEST/'current-execution-inputs'/name)
    assert sha(read_input(BASE/'s09_normal_fixture_source_qualify.py',1024**2))==context['launcher_sha256']
    assert sha(read_input(BASE/'local_windows_qualification_awake.py',1024**2))==context['awake_helper_sha256_after']
    assert inputs()==context['source_input_hashes']
    with OwnedProof(DEST/'bounded-history-index.json') as owner:owner.persist(dict(attempts=attempts,
      filename_does_not_imply_pass=True,counts_are_actual_results=True,failed_attempts_not_erased=True,
      precommit_normal_paper_rejection='WORKER_LEGACY_RESTORE_GREEN_FAILED_DIRTY_SOURCE_GUARD;FULL_CLEAN_D3D8496_LATER_PASSED',
      diagnostic_and_test_authoring_errors='PRESERVED_NO_ACCEPTANCE_CREDIT',
      earlier_external_execution_closure_gap='EXPLICITLY_RETAINED_AS_A_LIMIT;CURRENT_COMPLETE_SOURCE_AND_NATIVE_CLOSURES_SEPARATE'))
    archive=BASE/f'r7-native-windows-S09-normal-fixture-{SHORT}/r7-product-0.2.0-windows-{SHORT}.zip'
    archive_sha=sha(read_input(archive,64*1024**2))
    disposition=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',spec_baseline='r7-product-v0.2',
      state='IN_PROGRESS',executable_revision=REV,implementation_hash=context['implementation_hash'],native_build_identity=native['native_build_identity'],
      source=dict(passed=True,commands=33,tests=2101,phase_1=247,phase_2=1854,failures=0,errors=0,skipped=0,input_files=636),
      native_baseline=dict(passed=True,scenarios=25,commands=28,stages=6),
      normal_native_fixture=dict(passed=True,recorded_owned_commands=22,browser_stages=5,public_native_cli_commands=17,
        separately_observed_native_tty_enrollments=1,owned_native_control_starts=3,canonical_fills=2,canonical_closed_trades=1,
        paper_runtime_generations=[0,1,2],paper_reports=2,local_staging=True,cloud_acknowledged=0,real_elapsed_ns=0,
        control_stop='FORCED_OWNED_CLEANUP;NO_GRACEFUL_CONTROL_STOP_CREDIT',worker_stop='PUBLIC_BOUNDED_MANAGED_STOP',
        visual_review='SELF_REVIEW_OF_ACTUAL_PACKAGED_PROTECTED_PAUSED_AND_CLOSED_UI;NO_WHOLE_UI_ACCEPTANCE',
        ui_follow_up='FORWARD_SECONDS_SUMMARY_AND_ENTRY_ORDER_ROLE_SHOW_UNAVAILABLE_DESPITE_RAW_OWNER_FACTS;COSMETIC_MAPPING_NOT_YET_FIXED'),
      native_archive=dict(location=archive.relative_to(PROJECT).as_posix(),sha256=archive_sha,retention='PRIVATE_LOCAL_BINARY_NOT_COMMITTED'),
      independent_review='BOUNDED_SOURCE_AND_TOOLING0_CRITICAL0_IMPORTANT;REVIEWER_EXECUTION_NONE;NOT_WHOLE_PRODUCT_ACCEPTANCE',
      failed_prior_source=dict(revision='666fdde223d394f79552bc04078862f4122cddc8',tests=1849,commands=31,errors=1,reason='LEGACY_E6_MINIMAL_RUNTIME_NO_FORWARD;REPRODUCED_FIXED'),
      failed_prior_native_flow='BROWSER_HARNESS_EDGE_CHANNEL_ENV_LOOKUP;FAILED_BEFORE_BROWSER_RESEARCH_OR_PAPER;FRESH_CORPUS_RETRY_PASSED',
      source_authentication='SYNTHETIC_TTY_SEAM;NATIVE_TTY_AND_BROWSER_SEPARATE_ACTUAL_PROOF',
      ordinary_paper='NOT_RUN',production_profile='PROPOSED_NOT_ACTIVE',real_cloud='NOT_RUN',real_dataset='NOT_RUN',real_forward='NOT_RUN',
      ubuntu24='NOT_RUN',ubuntu26='NOT_RUN',full_requirement_pass_claims=0,real_provider_requests=0,credentials='NONE',
      capital='NONE',runtime_llm_calls=0,github_compute='NOT_USED',main_merge='NOT_PERFORMED',
      excluded='PRIVATE_CONFIG_DATASET_STORES_AUTH_SESSIONS_BACKUPS_NATIVE_BINARY_ARCHIVES_NODE_BINARY_AND_OTHER_PRIVATE_FIXTURE_CONTENT',
      retained_files=len(files)+2,created_at_utc=stamp())
    with OwnedProof(DEST/'disposition.json') as owner:owner.persist(disposition)
    for path in [DEST/'bounded-history-index.json',DEST/'disposition.json']:
        raw=read_input(path,8*1024**2);files.append(dict(source='GENERATED_PUBLIC_DISPOSITION',destination=path.relative_to(REPO).as_posix(),original_sha256=sha(raw),published_sha256=sha(raw),bytes=len(raw),sanitized=False))
    with OwnedProof(MANIFEST) as owner:owner.persist(dict(executable_revision=REV,files=files,count=len(files),
      source_inputs_unchanged=True,raw_vs_published_hashes_explicit=True,private_exclusions=disposition['excluded']))
    print(json.dumps(dict(retained=len(files),archive_sha256=archive_sha,disposition=str(DEST/'disposition.json'))),flush=True)
if __name__=='__main__':main()
