"""Owned local execution of three scoped joined-owner acceptance probes."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,re,stat,subprocess,sys
base=Path(__file__).resolve().parent;project=base.parent;repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.datasets.catalog import read_local
from application.platform.processes import ResourceLimits,spawn_owned
from application.qualification import _sanitize,parse_result,revision_fact
from strategy.v02.capabilities import _revision
label,mode=sys.argv[1:];assert re.fullmatch('[A-Za-z0-9_-]+',label) and mode in ('NORMAL','MUTATION_CONTROL')
names=subprocess.check_output([r'C:\Program Files\Git\cmd\git.exe','ls-files','--','tests/**/*.py'],cwd=repo).decode().splitlines()
paths=[repo/name for name in names]+[Path(__file__),base/'s15_joined_owner_fixture_child.py',base/'s15_joined_owner_acceptance_cases.py']
def bind():
    return {path.relative_to(project).as_posix():'sha256:'+hashlib.sha256(read_local(path.parent,path.name,1024*1024)).hexdigest() for path in paths}
before=bind();source_before=revision_fact(repo,None,False);implementation_before=_revision()
assert source_before['worktree']=='CLEAN' and implementation_before=='sha256:ba01027908e0e8ddf694eb8619d28b5d7a1bd9f94de0df804dc1471afe189576'
raw=base/(label+'.owned.raw');log=base/(label+'.log');report=base/(label+'.json');assert not any(os.path.lexists(p) for p in (raw,log,report))
for parent in (base,*base.parents):
    info=parent.lstat()
    if not stat.S_ISDIR(info.st_mode) or parent.is_symlink() or getattr(info,'st_file_attributes',0)&0x400:
        raise ValueError('Fixture scratch parent must be an ordinary project directory')
scratch=base/(label+'-fixture-temp');scratch.mkdir(exist_ok=False)
assert scratch.resolve()==scratch and scratch.is_relative_to(project)
started=datetime.now(timezone.utc).isoformat()
with raw.open('xb') as stream:
    owned=spawn_owned([sys.executable,str(base/'s15_joined_owner_fixture_child.py'),mode],cwd=repo,
        env=dict(os.environ,PYTHONPATH=os.pathsep.join((str(repo/'src'),str(repo))),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(scratch),TMP=str(scratch)),
        limits=ResourceLimits(180),stdout=stream,stderr=stream)
    code=owned.wait(timeout=190)
finished=datetime.now(timezone.utc).isoformat()
value=_sanitize(raw.read_text(encoding='utf-8',errors='replace'),repo);raw.unlink();log.write_text(value,encoding='utf-8',newline='\n')
result=parse_result(value,returncode=code);after=bind();source_after=revision_fact(repo,None,False);implementation_after=_revision()
scratch_info=scratch.lstat()
if scratch.is_symlink() or getattr(scratch_info,'st_file_attributes',0)&0x400:raise ValueError('Owned fixture scratch identity changed')
scratch_empty=not any(scratch.iterdir())
if scratch_empty:scratch.rmdir()
facts=dict(**result.__dict__,exit_code=code,mode=mode,tree_reaped=owned.termination_report.reaped,
    started_at_utc=started,finished_at_utc=finished,harness_binding='BEFORE_AND_AFTER_EXECUTION',
    input_sha256_before=before,input_sha256_after=after,source_before=source_before,source_after=source_after,
    implementation_hash_before=implementation_before,implementation_hash_after=implementation_after,
    log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest(),
    fixture_origin='SOURCE_CREATED_ACTUAL_CLOUD_FAKE_TRANSPORT_E2_E3_E5_E6_API_PAPER_FEEDBACK_JOINED_FIXTURE;NOT_NATIVE_RUNTIME_COMPOSITION',
    real_provider_requests=0,credentials='NONE',capital='NONE',real_forward='NOT_RUN',github_compute='NOT_USED',
    fixture_scratch_empty=scratch_empty,fixture_scratch_cleanup='REMOVED_VERIFIED_EMPTY_ROOT' if scratch_empty else 'RETAINED_NONEMPTY_ROOT;FAIL_CLOSED',
    scope='THREE_JOINED_OWNER_CASES_ONLY;NOT_FULL_REQUIREMENT_NATIVE_BROWSER_OR_MASTER_ACCEPTANCE')
closure=owned.termination_report.reaped and before==after and source_before==source_after and implementation_before==implementation_after and scratch_empty
facts['passed']=mode=='NORMAL' and result.passed and result.tests_run==3 and closure
positive='test_joined_cloud_intake_research_paper_ready_api_and_exact_feedback_ack'
negatives=('test_joined_genuine_oos_loss_rejects_without_paper_run','test_joined_changed_sealed_input_denies_queue_and_research_evidence')
failed_ids=re.findall(r'^FAIL: (test_\w+) \(',value,re.M)
negative_passes=all(re.search(r'^'+name+r' \(s15_joined_owner_acceptance_cases\.JoinedOwnerAcceptanceTests\.'+name+r'\) \.\.\. ok$',value,re.M) for name in negatives)
ack_failure_point=bool(re.search(r'^AssertionError: 0 != 1 : JOINED_CLOUD_OUTAGE_MUST_REMAIN_UNACKNOWLEDGED$',value,re.M))
facts['mutation_failed_test_names']=failed_ids
facts['mutation_ack_failure_point_observed']=ack_failure_point
facts['mutation_control_detected']=(mode=='MUTATION_CONTROL' and result.tests_run==3 and result.failures==1 and result.errors==0 and result.skipped==0
    and result.expected_failures==0 and result.unexpected_successes==0 and code==1 and failed_ids==[positive] and negative_passes and ack_failure_point and closure)
report.write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({key:value for key,value in facts.items() if not key.startswith('input_')}))
raise SystemExit(0 if facts['passed'] or facts['mutation_control_detected'] else 1)
