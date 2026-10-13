"""Execute the actual owning fixed issuer; never import a caller PASS/result."""
from contextlib import nullcontext
from datetime import datetime,timezone
import hashlib,json,os
from pathlib import Path
import subprocess,sys,threading
REPO=Path(r'<SOURCE_ROOT>')
BASE=Path(__file__).resolve().parent;REVISION=sys.argv[1]
sys.path[:0]=[str(REPO),str(REPO/'src'),str(BASE.parent)]
from application.config import load_config
from application.paper.producer import qualify,_guard
from application.paper.inventory import fixed_profile,current_target
from application.platform.distribution import verify_distribution
from application.platform.private_files import create_private_directory,write_private_new
from application.platform.processes import ResourceLimits,spawn_owned
from application.platform.resources import inspect_hardware
from application.qualification import revision_fact,_sanitize
from storage.qualification import open_qualification_receipts
from local_windows_qualification_awake import awake_request
def inputs():
    raw=subprocess.check_output(['git','ls-files','--','src','tests','tools','ui','packaging',
        'contracts','docs/product/v0_2','status/PM_PAPER_RELEASE_MAPPING_DECISION_20261013.md'],cwd=REPO)
    return {ref:'sha256:'+hashlib.sha256((REPO/ref).read_bytes()).hexdigest() for ref in raw.decode('utf-8').splitlines()}
revision_fact(REPO,REVISION,True);before=inputs()
output=BASE/('owning-pqr-'+REVISION[:7]);create_private_directory(output)
package=BASE/('build-'+REVISION[:7])/'dist/R7';facts=verify_distribution(package)
if facts['executable_revision']!=REVISION:raise ValueError('Actual exact native revision required')
profile=fixed_profile(current_target());_guard(REPO,REVISION,package,facts,profile)
config=output/'product.json';data=output/'data'
env={k:os.environ[k] for k in ('SystemRoot','WINDIR','SystemDrive','TEMP','TMP') if k in os.environ}
env.update(PATH='',PYTHONUTF8='1')
with (output/'native-init.raw').open('xb') as stream:
    init=spawn_owned([str(package/'R7.exe'),'init-profile','--config',str(config),'--data-root',str(data),
        '--instance-id','owning-pqr-'+REVISION[:7]],cwd=output,limits=ResourceLimits(45),stdout=stream,stderr=subprocess.STDOUT,env=env)
    code=init.wait()
raw=_sanitize((output/'native-init.raw').read_text(encoding='utf-8'),REPO).replace(str(output),'<PRIVATE_QUALIFICATION_ROOT>').encode('utf-8')
write_private_new(output/'native-init.log',raw);(output/'native-init.raw').unlink()
if code or not init.termination_report.reaped:raise ValueError('Actual public native init failed')
checkpoint=dict(revision=REVISION,source_worktree='CLEAN',input_files=len(before),input_hashes=before,
    started_at=datetime.now(timezone.utc).isoformat(),execution_completed=False,
    tool_hash='sha256:'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',financial_authority='NONE')
done=threading.Event();samples=[];errors=[]
def observe():
    while not done.is_set():
        try:
            host=inspect_hardware(BASE)
            samples.append(dict(at=datetime.now(timezone.utc).isoformat(),available_memory_bytes=host.available_memory_bytes,
                physical_memory_bytes=host.physical_memory_bytes))
        except Exception as error:errors.append(type(error).__name__)
        done.wait(2)
monitor=threading.Thread(target=observe,daemon=True);monitor.start()
scope=awake_request() if os.name=='nt' else nullcontext(dict(requested=False,restored=True))
with scope as awake:
    try:
        result=qualify(config,REPO,package);checkpoint['result']=result
        with open_qualification_receipts(load_config(config).database_path,namespace='LOCAL_RESEARCH') as store:
            receipt=store.get(result['receipt_ref'])
        expected=profile['groups'][0]['members'];checks=receipt.checks[:len(expected)]
        checkpoint['source_passed']=len(checks)==len(expected) and all(c.passed for c in checks)
        checkpoint['source_tests']=sum(c.tests_run for c in checks)
        checkpoint['phases']={phase:dict(tests=sum(c.tests_run for c in rows),failures=sum(c.failures for c in rows),
            errors=sum(c.errors for c in rows),skipped=sum(c.skipped for c in rows))
            for phase,rows in (('phase_1',checks[:16]),('phase_2',checks[16:]))}
        checkpoint['native_checks']=[dict(check_id=c.check_id,passed=c.passed,returncode=c.returncode,tree_reaped=c.tree_reaped)
            for c in receipt.checks[len(expected):]]
        checkpoint['execution_completed']=True
        _guard(REPO,REVISION,package,facts,profile)
    except Exception as error:checkpoint['error_type']=type(error).__name__
    finally:
        done.set();monitor.join(timeout=3)
        checkpoint.update(host_samples=samples,host_sample_errors=errors,capacity_claim='NONE;ACTUAL_HOST_ONLY')
        revision_fact(REPO,REVISION,True)
        if inputs()!=before:raise ValueError('Actual qualification inputs changed')
        checkpoint.update(inputs_unchanged=True,finished_at=datetime.now(timezone.utc).isoformat(),awake=awake)
write_private_new(output/'checkpoint.json',(json.dumps(checkpoint,indent=2)+'\n').encode('utf-8'))
print(json.dumps({k:v for k,v in checkpoint.items() if k not in ('input_hashes','host_samples','awake')}),flush=True)
raise SystemExit(0 if checkpoint['execution_completed'] else 2)
