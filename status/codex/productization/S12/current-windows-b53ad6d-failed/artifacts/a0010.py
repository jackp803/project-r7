"""Retain the failed exact b53 owning closure; never transfer qualification."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1];ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from application.config import load_config
from application.qualification import _sanitize
from application.paper.qualification import artifact_bytes
from storage.qualification import open_qualification_receipts
def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
captured={}
def capture(root,ref,expected=None):
    raw=artifact_bytes(root,ref)
    if expected is not None and sha(raw)!=expected:raise ValueError('Original declared artifact changed')
    captured[root/ref]=raw
    return raw
stage=BASE/'qualify-b53ad6d-first';checkpoint=json.loads(capture(stage,'checkpoint.json'))
config=load_config(stage/'product.json')
with open_qualification_receipts(config.database_path,namespace='LOCAL_RESEARCH') as reader:
    receipt=reader.get(checkpoint['result']['receipt_ref'])
assert not receipt.passed and not checkpoint['passed'] and len(receipt.checks)==160
assert checkpoint['result']['groups_completed']==6
assert receipt.subject.executable_revision=='b53ad6dcfd04966da82322e94fbe06d60fcea568'
source=config.local_data_root/'qualification'/receipt.execution_id
for member in receipt.execution_evidence['members']:
    for row in member['artifacts']:capture(source,row['ref'],row['hash'])
for ref in ('preflight.json','result.json'):capture(source,ref)
for name in ('init-owning.log','init-owning-execution.json'):capture(stage,name)
memory=BASE/'owning-memory-b53ad6d-first';observed=json.loads(capture(memory,'checkpoint.json'))
capture(memory,'wrapper.log')
assert observed['tree_reaped'] and observed['source_unchanged'] and observed['wrapper_unchanged']
assert observed['errors']==[] and observed['monitor_stopped'] and not observed['owning_passed']
assert observed['exit_code']==2
for name in ('publication-depth-red-corrected.log','publication-depth-green.log',
    'publication-depth-repair-review.json','run_owning_with_memory.py',
    'owning-memory-observer-final2-review.json','retain_b53_failed_publication.py'):
    capture(BASE,name)
target=ROOT/'status/codex/productization/S12/current-windows-b53ad6d-failed'
if (target/'disposition.json').exists():raise ValueError('Completed retention already exists')
prepared=[];bindings=[]
for number,(path,raw) in enumerate(sorted(captured.items(),key=lambda item:item[0].relative_to(PROJECT).as_posix()),1):
    ref=f'artifacts/a{number:04d}'+path.suffix
    if path.suffix=='.png' and raw.startswith(b'\x89PNG\r\n\x1a\n'):safe=raw
    else:safe=_sanitize(raw.decode('utf-8-sig'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').replace('\r','').encode()
    prepared.append((ref,safe))
    bindings.append(dict(original_ref=path.relative_to(PROJECT).as_posix(),original_hash=sha(raw),retained_ref=ref,retained_hash=sha(safe)))
target.mkdir(exist_ok=True);(target/'artifacts').mkdir(exist_ok=True)
if set(p.relative_to(target).as_posix() for p in (target/'artifacts').iterdir())-{ref for ref,_ in prepared}:
    raise ValueError('Unexpected partial retention member')
for ref,safe in prepared:
    path=target/ref
    if path.exists():
        if path.read_bytes()!=safe:raise ValueError('Partial retained member changed')
    else:path.write_bytes(safe)
value=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',branch='codex/r7-productization-master-20261002',
    observed_at=datetime.now(timezone.utc).isoformat(),executable_revision=receipt.subject.executable_revision,
    receipt_ref=receipt.receipt_id,execution_id=receipt.execution_id,software_qualification='NOT_QUALIFIED',
    source_commands=154,source_case_executions=sum(c.tests_run for c in receipt.checks),
    failures=sum(c.failures for c in receipt.checks),errors=sum(c.errors for c in receipt.checks),
    all_owned_trees_reaped=all(c.tree_reaped for c in receipt.checks),
    completed_groups=6,required_groups=7,native02_06='PASS',native07='FAIL_HELPER_COLLECT_WINDOWS_MAX_PATH',
    actual_failure_path_chars=267,new_private_workspace='OUTPUT_ROOT/h',
    ordinary_deterministic_defect='DEVELOPMENT_HELPER_OUTPUT_LAYOUT',
    tdd=dict(corrected_red_tests=1,corrected_red_errors=1,green_tests=16,green_failures=0,green_errors=0),
    independent_source_review='0_CRITICAL_0_IMPORTANT;EXECUTION_NONE',
    observed_resources={k:observed[k] for k in ('valid_samples','peak_owned_rss_bytes','peak_owned_private_bytes','minimum_host_available_bytes')},
    resource_scope='OBSERVED_OWNED_TREE_NOT_MAXIMUM_CAPACITY_OR_24GB_TARGET',
    new_exact_candidate_qualification='PENDING',os_power_settings='UNCHANGED',
    additional_public_requests=0,cumulative_public_requests=8,cumulative_public_responses=8,
    private_requests=0,credentials='NONE',provider_mutation=0,capital='NONE',github_compute='NOT_USED',
    master='IN_PROGRESS',artifacts=bindings)
assert value['source_case_executions']==2428 and value['failures']==0 and value['errors']==0
(target/'disposition.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:v for k,v in value.items() if k!='artifacts'}));print('Retained files:',len(bindings))
