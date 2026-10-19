"""Sanitized source/driver recovery and historical native failure, no PASS transfer."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1];ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(ROOT/'src'))
from application.paper.qualification import artifact_bytes
from application.qualification import _sanitize
def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
names=['paper-start-timeout-ledger-readonly.json','paper-start-response-timeout-review.json','native-paper-retry-test-seam.json',
    'paper-original-retry-review.json','paper-original-retry-owner-regressions.log','paper-original-retry-inventory-green.log',
    'paper-original-retry-source-red01/checkpoint.json','paper-original-retry-source-red01/browser.log',
    'paper-original-retry-source-green01/checkpoint.json','paper-original-retry-source-green01/browser.log',
    'retainer-host-depth-red.log','retainer-host-depth-green.log','retainer-host-depth-review.json','retainer-host-depth-final-review.json',
    'native07-history-scope-probe.json','probe_native07_history_scope.py','retain_current_checkpoint.py',
    'test_retain_current_checkpoint.py','retain_native07_depth_history.py','run_source_ui_retry.py','retain_paper_retry_repair.py',
    'build-1e99e09-first/checkpoint.json','build-1e99e09-first/native-build.log','build-1e99e09-first/native-build-execution.json',
    'build-1e99e09/build-result.json']
red=json.loads(artifact_bytes(BASE,'paper-original-retry-source-red01/checkpoint.json'))
green=json.loads(artifact_bytes(BASE,'paper-original-retry-source-green01/checkpoint.json'))
assert red['exit_code']==1 and red['tree_reaped'] and green['exit_code']==0 and green['tree_reaped']
target=ROOT/'status/codex/productization/S12/paper-original-command-retry-20261020'
prepared=[];bindings=[]
for number,name in enumerate(names,1):
    raw=artifact_bytes(BASE,name);safe=_sanitize(raw.decode('utf-8-sig'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').replace('\r','').encode()
    ref=f'artifacts/a{number:04d}'+Path(name).suffix;prepared.append((ref,safe))
    bindings.append(dict(original_ref='artifacts/current-windows-20261019/'+name,original_hash=sha(raw),retained_ref=ref,retained_hash=sha(safe)))
target.mkdir();(target/'artifacts').mkdir()
for ref,safe in prepared:(target/ref).write_bytes(safe)
disposition=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',branch='codex/r7-productization-master-20261002',
    observed_at=datetime.now(timezone.utc).isoformat(),historical_executable_revision='1e99e09f08d2b5bd3b773c0f19610f2ef458fb8e',
    historical_build='PASS',historical_native07='FAIL_PAPER_START_RESPONSE_TIMEOUT_BEFORE_HELPER_BUILD',
    actual_start_ledger='COMPLETE;PREPARED15:42:18.896609Z;COMPLETED15:42:47.986737Z;2026-10-19',
    measured_start_duration_seconds=29.090128,ui_request_deadline_seconds=15,
    static_expensive_release_chain='REPEATED_DISTRIBUTION_CHECKS;INDIVIDUAL_PHASE_LATENCY_NOT_MEASURED',
    repair='NATIVE_VERIFIER_USES_EXISTING_UI_PENDING_ORIGINAL_COMMAND_RETRY;NO_PRODUCT_AUTHORITY_CHANGE',
    actual_source_browser=dict(red_failed_cases=1,green_passed_cases=1,skips=0,
        scope='REAL_SOURCE_OWNER;FIRST_BROWSER_RESPONSE_LOSS_INJECTION_SOURCE_ONLY',
        assertions=['VISIBLE_RESPONSE_UNKNOWN_AND_PENDING','BYTE_IDENTICAL_TWO_POSTS','ORIGINAL_COMPLETE_RECEIPT',
            'SOLE_RUN_AND_SAME_EFFECT_REF','ORIGINAL_ZERO_GENERATION','PAUSE_RETENTION']),
    source_owner_api_driver_regressions=dict(passed=36,failures=0,errors=0,skips=0),
    frozen_inventory_checks=dict(passed=2,failures=0,errors=0,skips=0),
    frozen_inventory=dict(groups=7,commands=160,source_commands=154,source_case_executions=2429,source_files=297),
    ancillary_retainer_host_depth=dict(red_errors=1,green_checks=6,green_errors=0,
        unsafe_ref_sentinel_before_capture_calls=4,unsafe_ref_sentinel_after_capture_calls=0,
        scope='SOURCE_ONLY;NO_PRIVATE_FILE_READ;CLOUD_PATH_DEPTH_UNCHANGED'),
    independent_reviews='0_CRITICAL_0_IMPORTANT_FINAL;EXECUTION_NONE',
    next_exact_candidate_software_qualification='PENDING',additional_public_requests=0,cumulative_public_requests=8,
    cumulative_public_responses=8,private_requests=0,credentials='NONE',provider_mutation=0,
    capital='NONE',github_compute='NOT_USED',os_power_settings='UNCHANGED',master='IN_PROGRESS',artifacts=bindings)
(target/'disposition.json').write_text(json.dumps(disposition,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(retained_files=len(bindings),next_software_qualification='PENDING')))
