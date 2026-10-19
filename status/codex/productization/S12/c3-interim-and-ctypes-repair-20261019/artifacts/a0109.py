"""Retain exact failed owning receipts and completed scoped c3 evidence; no PASS transfer."""
from pathlib import Path
import hashlib,json,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1];ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from application.config import load_config
from application.qualification import _sanitize
from application.paper.qualification import artifact_bytes
from storage.qualification import open_qualification_receipts
def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
captured={};summaries=[]
def capture(root,ref,expected=None):
    raw=artifact_bytes(root,ref)
    if expected is not None and sha(raw)!=expected:raise ValueError('Declared original artifact changed')
    captured[root/ref]=raw
    return raw
for attempt,expected_count in [('first',106),('retry01',151)]:
    stage=BASE/('qualify-c3f4f2a-'+attempt)
    checkpoint=json.loads(capture(stage,'checkpoint.json'));config=load_config(stage/'product.json')
    with open_qualification_receipts(config.database_path,namespace='LOCAL_RESEARCH') as reader:
        receipt=reader.get(checkpoint['result']['receipt_ref'])
    assert not receipt.passed and not checkpoint['passed'] and len(receipt.checks)==expected_count
    source=config.local_data_root/'qualification'/receipt.execution_id
    for member in receipt.execution_evidence['members']:
        for row in member['artifacts']:capture(source,row['ref'],row['hash'])
    for ref in ('preflight.json','result.json'):capture(source,ref)
    summaries.append(dict(attempt=attempt,receipt_ref=receipt.receipt_id,execution_id=receipt.execution_id,
        revision=receipt.subject.executable_revision,tests=sum(c.tests_run for c in receipt.checks),
        failures=sum(c.failures for c in receipt.checks),errors=sum(c.errors for c in receipt.checks),
        commands=len(receipt.checks),passed_commands=sum(c.returncode==0 for c in receipt.checks),
        groups_completed=checkpoint['result']['groups_completed'],tree_reaped=all(c.tree_reaped for c in receipt.checks),
        cause='PHYSICAL_LID_STANDBY_HIBERNATION' if attempt=='first' else 'ACTUAL_HOST_RESEARCH_MEMORY_PRESSURE'))
stage=BASE/'native04-c3f4f2a-first';assert json.loads(capture(stage,'checkpoint.json'))['passed']
native=stage/'execution';report=json.loads(capture(native,'pqr-result.json'))
for row in report['artifacts']:capture(native,row['ref'],row['hash'])
stage=BASE/'headless-c3f4f2a-first';assert json.loads(capture(stage,'checkpoint.json'))['passed']
for name in ('observations.json','coordinator-crash.log','coordinator-first.log','coordinator-recovered.log',
    'init-headless.log','second-coordinator-denied.log','select-headless-diagnostic.log',
    'stop-first-coordinator-repeat.log','stop-first-coordinator.log',
    'stop-recovered-coordinator-repeat.log','stop-recovered-coordinator.log'):
    capture(stage/'execution',name)
stage=BASE/'portable-c3f4f2a-first';assert json.loads(capture(stage,'checkpoint.json'))['passed']
smoke=json.loads(capture(stage/'first-run-smoke','native-smoke.json'))
for row in smoke['commands']:
    capture(stage/'first-run-smoke',row['log'],'sha256:'+row['log_sha256'])
for name in ('author-engineering-example-execution.json','author-engineering-example.log',
    'export-capabilities-execution.json','export-capabilities.log'):capture(stage,name)
for name in ('c3f4f2a-sleep-events.json','c3f4f2a-post-sleep-research-setup.log',
    'source151-resource-recheck-c3f4f2a-first/checkpoint.json','source151-resource-recheck-c3f4f2a-first/source.log',
    'guard-memory-static-review.json','fixture-memory-static-review.json','windows-abi-type-cache-repair-review.json','ctypes-lifetime-red.log',
    'ctypes-lifetime-red-corrected.log','ctypes-lifetime-green.log','ctypes-affected-regressions.log',
    'ctypes-memory-before/checkpoint.json','ctypes-memory-after/checkpoint.json','probe_windows_ctypes_memory.py',
    'measure_position_source_recheck.py','retain_c3_interim_and_memory.py'):
    capture(BASE,name)
target=ROOT/'status/codex/productization/S12/c3-interim-and-ctypes-repair-20261019'
target.mkdir();(target/'artifacts').mkdir();bindings=[]
for number,(path,raw) in enumerate(sorted(captured.items(),key=lambda item:item[0].relative_to(PROJECT).as_posix()),1):
    ref=f'artifacts/a{number:04d}'+path.suffix
    safe=_sanitize(raw.decode('utf-8-sig'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').replace('\r','').encode()
    (target/ref).write_bytes(safe)
    bindings.append(dict(original_ref=path.relative_to(PROJECT).as_posix(),original_hash=sha(raw),retained_ref=ref,retained_hash=sha(safe)))
value=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',branch='codex/r7-productization-master-20261002',
    historical_executable_revision='c3f4f2a71d4203d3ceb12796570ebc9958a63323',owning_attempts=summaries,
    historical_scoped_native04='PASS7_OF7',historical_portable='PASS1107_FILES8_SCENARIOS9_COMMANDS',
    historical_headless='PASS_START_DUPLICATE_STOP_CHILD_AND_COORDINATOR_CRASH_RECOVERY',
    software_qualification='NOT_QUALIFIED',new_source='WINDOWS_ABI_TYPE_LIFETIME_REPAIR_PENDING_EXACT_CANDIDATE',
    tdd=dict(red_tests=3,red_failures=3,green_and_affected_tests=66,green_failures=0,green_errors=0),
    actual_probe=dict(reads=5000,stages=50,hardware_samples=100,before_new_types=5200,after_new_types=0,
        before_peak_owned_rss=93442048,after_peak_owned_rss=53473280,qualification_credit='NONE'),
    causality='CUMULATIVE_POINTER_CACHE_DEFECT_REPRODUCED;FULL_INCIDENT_BYTES_NOT_MEASURED;HOST_PRESSURE_MAY_COEXIST',
    os_power_settings='UNCHANGED',additional_public_requests=0,cumulative_actual_public_requests=8,
    cumulative_actual_public_responses=8,private_requests=0,credentials='NONE',provider_mutation=0,
    capital='NONE',github_compute='NOT_USED',master='IN_PROGRESS',artifacts=bindings)
(target/'disposition.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(retained_files=len(bindings),owning_attempts=summaries)))
