"""Retain only sanitized public UI evidence; keep native and full-source scope distinct."""
from pathlib import Path
import json,os,subprocess,sys
from s09_normal_fixture_source_qualify import BASE,REPO,inputs
from s09_owner_worker_native_regression import OwnedProof,sha,stamp,PROJECT
from s09_ui_dependency_inputs import protected_bytes,installed_dependencies,cache_inventory
from application.qualification import revision_fact

REV='9a48e09f877b46d5e6f0971cf6a47df8c0485859'
OLD='d3d849642f278ccd39723355367bf1030d8f0619'
REL='status/codex/productization/S09'
DEST=REPO/REL/'forward-ui-9a48e09-py312'
MANIFEST=REPO/REL/'forward-ui-artifact-hashes-9a48e09.json'
FRESH=BASE/'S09-forward-ui-bound-9a48e09-fresh-cache'
FAILED_SERIAL=BASE/'S09-forward-ui-serial-9a48e09'
SERIAL=BASE/'S09-forward-ui-serial-9a48e09-literal-bound'
revision_fact(REPO,REV,True)
proof_raw=protected_bytes(SERIAL/'ui-qualification.json',8*1024**2)
proof=json.loads(proof_raw)
assert proof['passed'] and inputs()==proof['source_input_hashes']
assert len(proof['frontend_commands'])==4 and all(c['passed'] and c['tree_reaped'] for c in proof['frontend_commands'])
assert [(c['label'],c['log']) for c in proof['frontend_commands']]==[(label,label+'.log') for label in ['contract','typecheck','unit','build']]
profiles=['empty','research','paper','protected','temporal','approval','deployment']
assert len(proof['commands'])==7 and all(c['tree_reaped'] and c['exit_code']==0 for c in proof['commands'])
assert [c['profile'] for c in proof['commands']]==profiles
assert [c['log'] for c in proof['commands']]==[profile+'.log' for profile in profiles]
assert sum(c['tests'] for c in proof['commands'])==proof['browser_tests']==11
assert proof['unit_tests']==18 and proof['awake_request']['restored']
assert proof['unit_failures']==proof['unit_skipped']==proof['browser_failures']==proof['browser_skipped']==proof['browser_flaky']==0
assert installed_dependencies()==proof['installed_dependency_hashes']
assert cache_inventory()==proof['commands'][-1]['derived_cache_inventory_after']
prefix_raw=protected_bytes(FRESH/'ui-qualification.json',8*1024**2)
prefix=json.loads(prefix_raw)
assert sha(prefix_raw)==proof['frontend_prefix_report_sha256']
assert prefix['source_input_hashes']==proof['source_input_hashes'] and not prefix['passed']
unit_raw=protected_bytes(FRESH/'unit-results.json',8*1024**2)
unit=json.loads(unit_raw)
assert sha(unit_raw)==proof['frontend_prefix_unit_results_sha256']
assert unit['success'] and unit['numTotalTests']==unit['numPassedTests']==18
assert unit['numFailedTests']==unit['numPendingTests']==0
for command in proof['frontend_commands']:
    assert sha(protected_bytes(FRESH/command['log'],8*1024**2))==command['log_sha256']
for command in proof['commands']:
    assert sha(protected_bytes(SERIAL/command['log'],8*1024**2))==command['log_sha256']
    assert sha(protected_bytes(SERIAL/(command['profile']+'.config.mjs'),8*1024**2))==command['config_sha256']
    if command['exit_code']==0:
        raw=protected_bytes(SERIAL/command['profile']/'results.json',8*1024**2)
        assert sha(raw)==command['results_sha256']
        stats=json.loads(raw)['stats']
        assert stats['expected']==command['tests'] and stats['unexpected']==stats['skipped']==stats['flaky']==0
assert b'RESEARCH_MEMORY_PRESSURE' in protected_bytes(FRESH/'browser.log',8*1024**2)
assert b'RESEARCH_MEMORY_PRESSURE' in protected_bytes(FAILED_SERIAL/'paper.log',8*1024**2)
expected_helpers=[BASE/'s09_forward_ui_serial_browser.py',BASE/'s09_ui_dependency_inputs.py',
 BASE/'s09_forward_ui_bound_qualification.py',BASE/'s09_normal_fixture_source_qualify.py',
 BASE/'s09_owner_worker_native_regression.py',BASE/'local_windows_qualification_awake.py',
 Path('C:/Program Files/nodejs/node.exe'),Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'),Path(sys.executable)]
assert set(proof['helper_hashes'])=={str(path) for path in expected_helpers}
for path,digest in proof['helper_hashes'].items():
    actual=Path(path)
    assert sha(protected_bytes(actual))==digest
browser_raw=protected_bytes(SERIAL/'browser-results.json',8*1024**2)
assert sha(browser_raw)==proof['browser_results_sha256']
failed= json.loads(protected_bytes(FAILED_SERIAL/'ui-qualification.json',8*1024**2))
assert not failed['passed'] and len(failed['commands'])==3
assert sha(protected_bytes(BASE/'s09_forward_ui_serial_browser-before-review.py'))==failed['helper_hashes'][str(BASE/'s09_forward_ui_serial_browser.py')]
previous=json.loads(protected_bytes(BASE/'r7-productization-S09-normal-fixture-qualified-d3d8496/qualification-context.json',8*1024**2))
delta=sorted(name for name,value in inputs().items() if previous['source_input_hashes'].get(name)!=value)
assert delta==['ui/qa/control-center.spec.ts','ui/src/App.tsx','ui/src/model.test.ts','ui/src/model.ts']
assert len(inputs())==636 and prefix['implementation_hash']==previous['implementation_hash']
assert not os.path.lexists(DEST) and not os.path.lexists(MANIFEST)
DEST.mkdir();files=[]
def publish(path,target):
    raw=protected_bytes(path,8*1024**2)
    out=raw
    if path.suffix!='.png':
        text=raw.decode('utf-8')
        for actual,label in [(REPO,'<SOURCE_ROOT>'),(PROJECT,'<PROJECT_ROOT>')]:
            for value in [str(actual),str(actual).replace('\\','/'),json.dumps(str(actual),ensure_ascii=False)[1:-1],json.dumps(str(actual),ensure_ascii=True)[1:-1]]:
                text=text.replace(value,label)
        out=text.replace('\r\n','\n').encode()
    target.parent.mkdir(parents=True,exist_ok=True)
    with OwnedProof(target) as owner:
        owner.stream.write(out);owner.stream.flush();owner.require_owned()
    assert protected_bytes(target,8*1024**2)==out
    files.append(dict(source=path.relative_to(BASE).as_posix(),destination=target.relative_to(REPO).as_posix(),
       original_sha256=sha(raw),published_sha256=sha(out),bytes=len(out),sanitized=out!=raw))
for label in ['RED','GREEN','GREEN_BOUND']:
    folder=BASE/('S09-forward-ui-'+label)
    for name in ['probe.json','unit-results.json','unit.log','contract.log','typecheck.log','build.log']:
        if (folder/name).exists():publish(folder/name,DEST/'diagnostic'/label/name)
for name in ['ui-qualification.json','unit-results.json','contract.log','typecheck.log','unit.log','build.log','browser.log']:
    publish(BASE/'S09-forward-ui-bound-9a48e09'/name,DEST/'observation-before-cache-repair'/name)
for name in ['ui-qualification.json','unit-results.json','contract.log','typecheck.log','unit.log','build.log','browser.log']:
    publish(FRESH/name,DEST/'failed-parallel-memory'/name)
if (FRESH/'browser/results.json').exists():publish(FRESH/'browser/results.json',DEST/'failed-parallel-memory/browser-results.json')
publish(FAILED_SERIAL/'ui-qualification.json',DEST/'incomplete-serial/ui-qualification.json')
for profile in ['empty','research','paper']:
    for name in [profile+'.log',profile+'.config.mjs']:publish(FAILED_SERIAL/name,DEST/'incomplete-serial'/name)
    if (FAILED_SERIAL/profile/'results.json').exists():publish(FAILED_SERIAL/profile/'results.json',DEST/'incomplete-serial'/profile/'results.json')
publish(SERIAL/'ui-qualification.json',DEST/'passed/ui-qualification.json')
publish(SERIAL/'browser-results.json',DEST/'passed/browser-results.json')
for command in proof['commands']:
    profile=command['profile']
    for name in [profile+'.log',profile+'.config.mjs']:publish(SERIAL/name,DEST/'passed'/name)
    publish(SERIAL/profile/'results.json',DEST/'passed'/profile/'results.json')
for name in ['overview.png','protected-paper.png','approval-preview.png','deployment-pause.png','health.png','supervised-health.png']:
    publish(SERIAL/name,DEST/'passed'/name)
for name in ['s09_forward_ui_probe-before-review.py','s09_forward_ui_probe.py',
    's09_forward_ui_bound_qualification-before-cache-review.py','s09_forward_ui_bound_qualification.py',
    's09_ui_dependency_inputs.py','s09_forward_ui_serial_browser-before-review.py',
    's09_forward_ui_serial_browser.py','test_s09_forward_ui_prefix_guards.py',
    'S09-forward-ui-prefix-RED.log','S09-forward-ui-prefix-GREEN.log','s09_owner_worker_native_regression.py',
    's09_normal_fixture_source_qualify.py','local_windows_qualification_awake.py',Path(__file__).name]:
    publish(BASE/name,DEST/'execution-inputs'/name)
review=BASE/'S09-forward-ui-final-reviews.json'
assert review.exists()
publish(review,DEST/'execution-inputs'/review.name)
disposition=dict(executable_revision=REV,accepted_full_source_native_revision=OLD,
    state='IN_PROGRESS',scope='SCOPED_CURRENT_SOURCE_UI_PASS;NORMAL_NATIVE_D3_SEPARATE;NO_FULL_MASTER_ACCEPTANCE',
    source_unit_tests=18,source_unit_failures=0,source_unit_skipped=0,
    frontend_commands_passed=4,serial_browser_commands=7,serial_browser_commands_passed=7,
    browser_cases_passed=11,browser_cases_total=11,browser_failures=0,browser_skipped=0,browser_flaky=0,
    current_browser_qualification='PASS_SOURCE_UI_ONLY;NO_NATIVE_OR_FULL_PRODUCT_ACCEPTANCE',
    prior_parallel_browser_command_failures=1,prior_serial_browser_command_failures=1,
    source_inputs=636,source_input_delta=delta,python_implementation_unchanged=True,
    actual_forward_display='RAW_OWNER_REAL_ELAPSED_NS0_AND_RENDERED_SECONDS0;EXACT_SAFE_INTEGER_CONVERSION;NO_SIMULATED_TIME_SUBSTITUTION',
    runtime_generations_or_financial_authority='UNCHANGED',
    earlier_development_and_browser_observations='RETAINED_DIAGNOSTIC_ONLY;NO_FINAL_CLOSURE_ACCEPTANCE_CREDIT',
    cache_freshness='PREEXISTING_ORDINARY_CACHES_PRESERVED_PRIVATE;FRESH_GENERATED_CACHE_INVENTORY_BOUND_EACH_COMMAND',
    raw_result_hashes=dict(unit=proof['frontend_prefix_unit_results_sha256'],browser=proof['browser_results_sha256'],serial_report=sha(proof_raw)),
    installed_dependency_files=len(proof['installed_dependency_hashes']),
    visual_review='SELF_REVIEW_ACTUAL_PROTECTED_PAPER_SCREENSHOT_ONLY;NOT_INDEPENDENT_VISUAL_ACCEPTANCE',
    cleanup='ALL7_SERIAL_JOB_TREES_AND4_PREFIX_TREES_REAPED;FINAL_AWAKE_RESTORED',
    prior_failed_cleanup='THREE_OLD_SERIAL_JOB_TREES_REAPED;OLD_FAILED_REPORT_NO_FINAL_AWAKE_RECEIPT_OR_FINAL_CLOSURE_CREDIT',
    serial_driver_review='EXECUTED_PRE_REVIEW_BYTES_PRESERVED;TWO_IMPORTANT_GAPS_REPAIRED_WITH5_FAIL_FIRST_GUARDS;READ_ONLY_RE_REVIEW0C_I;REPAIRED_WORKLOAD_PASS_SOURCE_UI_ONLY',
    native_ui='NOT_RUN_FOR_THIS_NEW_REVISION',full_source='NOT_RUN_FOR_THIS_NEW_REVISION',
    ubuntu24='NOT_RUN',ubuntu26='NOT_RUN',ordinary_paper='NOT_RUN',
    production_profile='PROPOSED_NOT_ACTIVE',real_cloud='NOT_RUN',real_forward='NOT_RUN',
    real_provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',
    excluded='PRIVATE_API_FIXTURES_AUTH_CONFIG_DATABASES_TEMPORARY_AND_QUARANTINED_CACHES_NODE_BINARY_INSTALLED_DEPENDENCY_BYTES',
    created_at_utc=stamp(),retained_files=len(files)+1)
with OwnedProof(DEST/'disposition.json') as owner:owner.persist(disposition)
raw=protected_bytes(DEST/'disposition.json',8*1024**2)
files.append(dict(source='GENERATED_PUBLIC_DISPOSITION',destination=(DEST/'disposition.json').relative_to(REPO).as_posix(),
  original_sha256=sha(raw),published_sha256=sha(raw),bytes=len(raw),sanitized=False))
with OwnedProof(MANIFEST) as owner:owner.persist(dict(executable_revision=REV,files=files,count=len(files),
    raw_and_published_hashes_explicit=True,private_exclusions=disposition['excluded']))
assert inputs()==proof['source_input_hashes']
print(json.dumps(dict(retained=len(files),source_ui_pass=True,unit_tests=18,browser_passed=11,browser_total=11,python_implementation_unchanged=True)))
