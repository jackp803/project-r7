"""Actual formal native timeout/reap only, never full PQR05 isolation credit."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys,subprocess,threading
BASE=Path(__file__).resolve().parent
REPO=BASE.parents[1]/'workspaces/project-r7-productization-master-20261002'
REVISION=sys.argv[1]
sys.path[:0]=[str(REPO),str(REPO/'src'),str(REPO/'tools'),str(BASE.parent)]
from application.qualification import revision_fact,_sanitize
from application.paper.producer import _guard
from application.paper.inventory import fixed_profile,current_target
from application.platform.distribution import verify_distribution
from application.platform.resources import inspect_hardware
from application.platform.private_files import create_private_directory,write_private_new
from application.datasets.catalog import read_local
from local_windows_qualification_awake import awake_request
from verify_paper_product import NativeExpiryFlow

def inputs():
    refs=subprocess.check_output(['git','ls-files','--','src','tests','tools','ui','packaging','contracts','docs/product/v0_2','status/PM_PAPER_RELEASE_MAPPING_DECISION_20261013.md'],cwd=REPO).decode('utf-8').splitlines()
    return {ref:'sha256:'+hashlib.sha256((REPO/ref).read_bytes()).hexdigest() for ref in refs}

def main():
    revision_fact(REPO,REVISION,True);before=inputs()
    package=BASE/('build-'+REVISION[:7])/'dist/R7'
    identity=verify_distribution(package);profile=fixed_profile(current_target())
    _guard(REPO,REVISION,package,identity,profile)
    output=BASE/('native-public-timeout-'+REVISION[:7]);create_private_directory(output)
    flow=NativeExpiryFlow(package,output/'timeout','checkpoint-cancel',expected_identity=identity)
    record=dict(scope='ACTUAL_PUBLIC_TIMEOUT_REAP_ONLY',passed=False,revision=REVISION,identity=identity,
        started_at=datetime.now(timezone.utc).isoformat(),input_files=len(before),input_hashes=before,
        native_protection_isolation='NOT_RUN',full_pqr='NOT_QUALIFIED',ordinary_paper='NOT_QUALIFIED',
        provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',
        tool_hash='sha256:'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    stop=threading.Event();samples=[]
    def observe():
        while not stop.is_set():
            host=inspect_hardware(BASE)
            samples.append(dict(at=datetime.now(timezone.utc).isoformat(),available_memory_bytes=host.available_memory_bytes,physical_memory_bytes=host.physical_memory_bytes))
            stop.wait(2)
    thread=threading.Thread(target=observe,daemon=True);thread.start()
    with awake_request() as awake:
        try:
            flow.setup();flow.scan();receipt=flow.submission()['receipt'];_,_,run=flow.enqueue()
            result=flow.command('research-worker-timeout',['research-worker','--config',flow.config,'--once','--job-timeout-seconds','30'],timeout=80,expected=2,json_result=True)
            if (result['status']!='JOB_TERMINATED' or result['job_state']!='FAILED'
                or result['reason_codes']!=['OWNED_WORKER_TIMEOUT'] or result['parent_pid']==result['child_pid'] or not result['tree_reaped']):
                raise ValueError('Actual formal timeout result mismatch')
            job=flow.view('research/runs/'+run)['payload']
            if job['state']!='FAILED' or job['reason_codes']!=['OWNED_WORKER_TIMEOUT'] or flow.submission()['receipt']!=receipt:
                raise ValueError('Actual timeout durable state mismatch')
            rows=flow.retained_checkpoint_observations()
            if len(rows)!=1 or 'actual_finished_at' in rows[0]:raise ValueError('Actual sealed wait missing or falsely completed')
            stages={row['stage'] for row in job['evidence']['attempts'] if row['status']=='COMPLETE'}
            if not {'development_replay','e6_backtest_persistence'}.issubset(stages) or stages.intersection({'robustness','sealed_oos','e6_product_assessment'}):
                raise ValueError('Actual timeout development or final evidence mismatch')
            raw=read_local(flow.data,result['log_ref'],4*1024*1024)
            sanitized=_sanitize(raw.decode('utf-8',errors='replace'),REPO).replace(str(flow.output),'<PRIVATE_FIXTURE_ROOT>').replace(flow.password,'<SYNTHETIC_TEST_INPUT>')
            write_private_new(output/'research-child.log',sanitized.encode('utf-8'))
            record.update(passed=True,result=result,research_state=job['state'],reason_codes=job['reason_codes'],
                original_receipt_preserved=True,retained_complete_stages=sorted(stages),checkpoint_observations=rows)
            flow.observation.update(passed=True,timeout_result=result)
        except Exception as error:
            record.update(passed=False,error_type=type(error).__name__)
        finally:
            try:flow.stop_control();flow.persist();flow.guard()
            except Exception as error:record.update(passed=False,cleanup_error_type=type(error).__name__)
            stop.set();thread.join(timeout=3)
            revision_fact(REPO,REVISION,True)
            if before!=inputs():raise ValueError('Checkpoint inputs changed')
            _guard(REPO,REVISION,package,identity,profile)
            record.update(inputs_unchanged=True,host_samples=samples,finished_at=datetime.now(timezone.utc).isoformat(),awake=awake)
    write_private_new(output/'checkpoint.json',(json.dumps(record,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({k:v for k,v in record.items() if k not in ('input_hashes','host_samples','checkpoint_observations','awake')},ensure_ascii=False))
    return 0 if record['passed'] else 2

if __name__=='__main__':raise SystemExit(main())
