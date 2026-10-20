"""Retain a historical strict probe only after the active owning chain ends."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,re,subprocess,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tools')]
from application.qualification import _sanitize
from application.cloud.manifest import safe_relative
from application.paper.qualification import artifact_bytes
from application.platform.private_files import create_private_directory,write_private_new
from retain_current_checkpoint import CapturedEvidence

def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()

def require_ended_chain(captured,revision,attempt):
    q=captured.document(BASE/('qualify-'+revision[:7]+'-'+attempt)/'checkpoint.json')
    m=captured.document(BASE/('owning-memory-'+revision[:7]+'-'+attempt)/'checkpoint.json')
    if (q.get('stage')!='qualify' or m.get('kind')!='ACTUAL_OWNING_EXECUTION_RESOURCE_OBSERVATION'
            or q.get('attempt')!=attempt or m.get('attempt')!=attempt
            or q.get('source_unchanged') is not True or q.get('source_worktree')!='CLEAN'
            or q.get('revision')!=revision or m.get('revision')!=revision or m.get('tree_reaped') is not True
            or m.get('monitor_stopped') is not True or m.get('source_unchanged') is not True
            or m.get('wrapper_unchanged') is not True):
        raise ValueError('Actual owning scope must have ended and reaped')
    if q.get('passed') is True:
        if m.get('owning_passed') is not True or m.get('exit_code')!=0:
            raise ValueError('Actual successful observer and qualification differ')
        d=captured.document(ROOT/'status/codex/productization/S12'/('current-windows-'+revision[:7])/'disposition.json')
        paper=d['ordinary_windows_paper_software']
        if d.get('executable_revision')!=revision or paper.get('status')!='PASS' or paper.get('groups_completed')!=7:
            raise ValueError('Successful chain must finish all postchecks and primary retention first')
    elif q.get('passed') is not False or m.get('owning_passed') is not False or m.get('exit_code')!=2:
        raise ValueError('Failed historical owning scope must be explicitly completed')

def require_bound_observation(child,observation,outer_log,research_log):
    if json.loads(outer_log)!=child:
        raise ValueError('Actual wrapper output differs from child report')
    fields=('research_result','actual_research_target_pids','sample_count',
        'actual_target_concurrent_protected_samples','progress')
    if any(child.get(key)!=observation.get(key) for key in fields):
        raise ValueError('Historical child and observation summaries differ')
    samples=observation['process_samples'];targets=observation['actual_research_target_pids']
    concurrent=[sample for sample in samples
        if any(row['pid'] in targets for row in sample['processes']['research'])]
    if (not samples or not targets or type(observation['sample_count']) is not int
            or observation['sample_count']!=len(samples)
            or type(observation['actual_target_concurrent_protected_samples']) is not int
            or observation['actual_target_concurrent_protected_samples']!=len(concurrent)):
        raise ValueError('Historical process sample counts differ')
    commands=[row for row in observation['commands'] if row.get('command')=='concurrent-research']
    if (len(commands)!=1 or commands[0].get('log')!='concurrent-research.log'
            or commands[0].get('tree_reaped') is not True or commands[0].get('exit_code')!=2
            or commands[0].get('log_hash')!=sha(research_log)):
        raise ValueError('Actual concurrent research command commitment differs')
    lines=[line for line in research_log.splitlines() if line.startswith(b'{')]
    if len(lines)!=1 or json.loads(lines[0])!=observation['research_result']:
        raise ValueError('Actual concurrent research output differs')
    return commands[0]

def publish_archive(target,prepared,disposition):
    create_private_directory(target);create_private_directory(target/'artifacts')
    for ref,payload in prepared:
        safe_relative(ref)
        write_private_new(target/ref,payload)
    for ref,payload in prepared:
        if artifact_bytes(target,ref)!=payload:raise ValueError('Retained historical bytes differ')
    serialized=(json.dumps(disposition,indent=2)+'\n').encode()
    write_private_new(target/'disposition.json',serialized)
    if artifact_bytes(target,'disposition.json')!=serialized:raise ValueError('Historical disposition readback differs')

def run(revision,probe='probe01',owning_attempt='first'):
    if (not re.fullmatch('[0-9a-f]{40}',revision) or not re.fullmatch('probe[0-9]{2}',probe)
            or not re.fullmatch('first|retry[0-9]{2}',owning_attempt)):
        raise ValueError('Explicit historical subjects required')
    captured=CapturedEvidence(PROJECT)
    require_ended_chain(captured,revision,owning_attempt)
    stage=BASE/('isolation-'+revision[:7]+'-'+probe)
    row=captured.document(stage/'checkpoint.json');facts=row['facts']
    if (row.get('passed') is not True or row.get('revision')!=revision or facts.get('executable_revision')!=revision
            or row.get('source_unchanged') is not True or row.get('package_unchanged') is not True
            or row.get('scope')!='ACTUAL_STRICT_NATIVE_ISOLATION_AT_OWNING_DEPTH_ONLY'
            or row.get('full_qualification_credit')!='NONE'):
        raise ValueError('Exact passed historical probe required')
    ref=row['artifact_root_ref'];safe_relative(ref)
    expected='artifacts/q-'+revision[:7]+'-i00'+probe[-2:]+'/worker-logs/pqr-[0-9a-f]{32}/PQR-05-native-artifacts/research-isolation'
    if re.fullmatch(expected,ref) is None:raise ValueError('Fixed historical artifact scope required')
    source=PROJECT/ref
    child=captured.document(source/'probe-result.json');observation=captured.document(source/'observations.json')
    if (child!=row['observed'] or child.get('facts')!=facts or child.get('revision')!=revision
            or child.get('helper_hash')!=row['helper_hash'] or child.get('passed') is not True
            or child.get('cleanup_confirmed') is not True or child.get('source_unchanged') is not True
            or child.get('package_unchanged') is not True or observation.get('identity')!=facts
            or any(observation.get(k) is not True for k in ('passed','research_fault_protection_isolation','host_bounded_capacity_measured'))):
        raise ValueError('Actual strict native child and observation binding differ')
    original_driver=subprocess.check_output(['git','show',revision+':tools/verify_paper_isolation.py'],cwd=ROOT)
    captured.capture(ROOT/'tools/verify_paper_isolation.py',sha(original_driver))
    execution=captured.document(stage/'actual-isolation-execution.json')
    if execution.get('exit_code')!=0 or execution.get('tree_reaped') is not True or execution.get('log_ref')!='actual-isolation.log':
        raise ValueError('Actual owning command cleanup missing')
    outer_log=captured.capture(stage/'actual-isolation.log',execution['log_hash'])
    research_log=captured.capture(source/'concurrent-research.log')
    concurrent_command=require_bound_observation(child,observation,outer_log,research_log)
    from verify_paper_isolation import require_timeout,require_research_target,progress_report
    result=observation['research_result'];samples=observation['process_samples']
    require_timeout(result,run_id=result['run_id'],process_exit_code=concurrent_command['exit_code'])
    if require_research_target(samples,result)!=observation['actual_research_target_pids']:
        raise ValueError('Actual sampled target binding differs')
    if progress_report(observation['protected_observations'],selected_deadline_seconds=observation['selected_protection_poll_seconds'])!=observation['progress']:
        raise ValueError('Actual protection progress binding differs')
    # Match the existing native producer's public artifact types, excluding
    # fixture inputs, configuration, authentication and database files.
    for path in sorted(source.rglob('*')):
        if path.suffix in ('.log','.png') or path.name in ('observations.json','doctor-execution.json'):
            captured.capture(path)
    captured.capture(BASE/'verify_isolation_owning_depth.py',row['helper_hash'])
    for name in ('test_isolation_owning_depth_helper.py','isolation-probe-binding-red.log',
            'isolation-probe-binding-green.log','isolation-owning-depth-helper-final-review.json',
            'retain_isolation_depth_history.py','test_isolation_depth_history_helper.py',
            'isolation-history-retention-red.log','isolation-history-retention-green.log',
            'isolation-depth-history-helper-review.json','isolation-depth-history-helper-final-review.json'):
        captured.capture(BASE/name)
    target=ROOT/'status/codex/productization/S12'/('current-windows-'+revision[:7]+'-isolation-depth')
    if target.exists():raise ValueError('Fresh historical retention required')
    prepared=[];bindings=[]
    for number,(path,raw) in enumerate(sorted(captured.bytes.items(),key=lambda pair:pair[0].relative_to(PROJECT).as_posix()),1):
        retained='artifacts/a'+str(number).zfill(4)+path.suffix
        if path.suffix=='.png' and raw.startswith(b'\x89PNG\r\n\x1a\n'):safe=raw
        else:
            safe=_sanitize(raw.decode('utf-8-sig'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').replace('\r','').encode()
            if path.suffix=='.log':safe=b'\n'.join(line.rstrip() for line in safe.split(b'\n'))
        prepared.append((retained,safe))
        bindings.append(dict(original_ref=path.relative_to(PROJECT).as_posix(),original_hash=sha(raw),
            retained_ref=retained,retained_hash=sha(safe),normalization='PROJECT_SANITIZATION_LF;LOG_TRAILING_SPACE_REMOVAL_IF_LOG'))
    disposition=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',executable_revision=revision,identity=facts,
        retained_at=datetime.now(timezone.utc).isoformat(),scope='HISTORICAL_STRICT_NATIVE_ISOLATION_ONLY',
        full_qualification_credit='NONE',passed=True,sample_count=observation['sample_count'],
        actual_target_concurrent_protected_samples=observation['actual_target_concurrent_protected_samples'],
        observed_progress=observation['progress'],additional_public_requests=0,cumulative_public_requests=8,
        private_requests=0,credentials='NONE',provider_mutation=0,capital='NONE',github_compute='NOT_USED',artifacts=bindings)
    publish_archive(target,prepared,disposition)
    print(json.dumps(dict(retained_files=len(bindings),revision=revision,scope=disposition['scope'])))

if __name__=='__main__':run(*sys.argv[1:])
