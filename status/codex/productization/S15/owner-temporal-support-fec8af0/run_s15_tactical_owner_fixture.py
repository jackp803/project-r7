"""Owned bounded execution, no native/runtime/real-forward acceptance claim."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,re,subprocess,sys
base=Path(__file__).resolve().parent;project=base.parent;repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.datasets.catalog import read_local
from application.platform.processes import ResourceLimits,spawn_owned
from application.qualification import _sanitize,parse_result,revision_fact
from strategy.v02.capabilities import _revision
label,mode=sys.argv[1:];assert re.fullmatch('[A-Za-z0-9_-]+',label) and mode in ('NORMAL','MUTATION_CONTROL')
names=subprocess.check_output([r'C:\Program Files\Git\cmd\git.exe','ls-files','--','tests/**/*.py'],cwd=repo).decode('utf-8').splitlines()
paths=[repo/name for name in names]+[Path(__file__),base/'s15_tactical_owner_fixture_child.py',base/'s15_tactical_owner_acceptance_cases.py']
def bind():
    result={}
    for path in paths:
        value=read_local(path.parent,path.name,1024*1024)
        result[path.relative_to(project).as_posix()]='sha256:'+hashlib.sha256(value).hexdigest()
    return result
before=bind();source_before=revision_fact(repo,None,False);implementation_before=_revision()
assert source_before['worktree']=='CLEAN' and implementation_before=='sha256:ba01027908e0e8ddf694eb8619d28b5d7a1bd9f94de0df804dc1471afe189576'
raw=base/(label+'.owned.raw');log=base/(label+'.log');report=base/(label+'.json');assert not any(p.exists() for p in (raw,log,report))
started=datetime.now(timezone.utc).isoformat()
with raw.open('xb') as stream:
    owned=spawn_owned([sys.executable,str(base/'s15_tactical_owner_fixture_child.py'),mode],cwd=repo,
        env=dict(os.environ,PYTHONPATH=os.pathsep.join((str(repo/'src'),str(repo))),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'),
        limits=ResourceLimits(120),stdout=stream,stderr=stream)
    code=owned.wait(timeout=130)
finished=datetime.now(timezone.utc).isoformat()
text=_sanitize(raw.read_text(encoding='utf-8',errors='replace'),repo);raw.unlink();log.write_text(text,encoding='utf-8',newline='\n')
result=parse_result(text,returncode=code);after=bind();source_after=revision_fact(repo,None,False);implementation_after=_revision()
facts=dict(**result.__dict__,exit_code=code,mode=mode,tree_reaped=owned.termination_report.reaped,
    started_at_utc=started,finished_at_utc=finished,harness_binding='BEFORE_AND_AFTER_EXECUTION',
    input_sha256_before=before,input_sha256_after=after,source_before=source_before,source_after=source_after,
    implementation_hash_before=implementation_before,implementation_hash_after=implementation_after,
    log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest(),
    fixture_origin='SOURCE_CREATED_ACTUAL_E2_E3_E5_E6_ACCELERATED_FIXTURE;NOT_NATIVE_RUNTIME_COMPOSITION',
    real_provider_requests=0,credentials='NONE',capital='NONE',real_forward='NOT_RUN',github_compute='NOT_USED',
    scope='FIVE_TACTICAL_OWNER_MECHANICS_CASES_ONLY;NOT_FULL_REQUIREMENT_OR_MASTER_ACCEPTANCE')
closure=owned.termination_report.reaped and before==after and source_before==source_after and implementation_before==implementation_after
facts['passed']=mode=='NORMAL' and result.passed and result.tests_run==5 and closure
facts['mutation_control_detected']=mode=='MUTATION_CONTROL' and result.tests_run==5 and result.failures==3 and result.errors==0 and result.skipped==0 and closure
report.write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({key:value for key,value in facts.items() if not key.startswith('input_')}))
raise SystemExit(0 if facts['passed'] or facts['mutation_control_detected'] else 1)
