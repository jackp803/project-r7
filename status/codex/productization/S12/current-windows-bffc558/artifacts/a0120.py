"""Monitor the actual complete owning process tree; no imported/stitched receipts."""
from datetime import datetime,timezone
import hashlib,json,os,re,subprocess,sys,threading
from pathlib import Path
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1];ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tools')]
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.platform.private_files import create_private_directory,write_private_new
from application.platform.resources import inspect_hardware
from application.qualification import revision_fact,_sanitize
from verify_paper_isolation import WindowsOwnedProcessSampler,MeasurementProcessExited

revision,attempt=sys.argv[1:]
if not re.fullmatch('[0-9a-f]{40}',revision) or not re.fullmatch('first|retry[0-9]{2}',attempt):
    raise ValueError('Explicit fixed owning attempt required')
revision_fact(ROOT,revision,True)
output=BASE/('owning-memory-'+revision[:7]+'-'+attempt);create_private_directory(output)
wrapper=BASE/'run_current_checkpoint.py';wrapper_raw=wrapper.read_bytes()
sampler=WindowsOwnedProcessSampler();samples=[];done=threading.Event();owned=None
started=datetime.now(timezone.utc).isoformat()
def monitor():
    while not done.is_set():
        try:
            rows=sampler.sample_owned(owned);hardware=inspect_hardware(BASE)
            samples.append(dict(at=datetime.now(timezone.utc).isoformat(),
                host_available_bytes=hardware.available_memory_bytes,owned_process_count=len(rows),
                owned_rss_bytes=sum(row['rss_bytes'] for row in rows),
                owned_private_bytes=sum(row['private_bytes'] for row in rows),
                largest_owned_rss_bytes=max((row['rss_bytes'] for row in rows),default=0)))
            if len(samples)%15==0:
                write_private_new(output/('sample-'+str(len(samples)).zfill(5)+'.json'),
                    (json.dumps(samples[-15:],indent=2)+'\n').encode())
        except MeasurementProcessExited:
            samples.append(dict(at=datetime.now(timezone.utc).isoformat(),sample_status='OWNED_DESCENDANT_EXIT_RACE'))
            if owned.process.poll() is not None:break
        except BaseException as error:samples.append(dict(at=datetime.now(timezone.utc).isoformat(),error_type=type(error).__name__))
        done.wait(2)
environment=os.environ.copy();environment.update(PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
code=None;reaped=False;worker=None;errors=[];unchanged=False;wrapper_unchanged=False;stage=None
try:
    with (output/'wrapper.raw').open('xb') as stream:
        owned=spawn_owned([sys.executable,'-X','utf8',str(wrapper),'qualify',revision,attempt],cwd=ROOT,
            env=environment,limits=ResourceLimits(10800),stdout=stream,stderr=subprocess.STDOUT)
        worker=threading.Thread(target=monitor,daemon=True);worker.start()
        code=owned.wait()
except BaseException as error:errors.append(dict(phase='OWNED_EXECUTION',error_type=type(error).__name__))
finally:
    done.set()
    try:
        if worker is not None and worker.ident is not None:worker.join(timeout=3)
        if worker is not None and worker.is_alive():errors.append(dict(phase='MONITOR_CLEANUP',error_type='MonitorStillRunning'))
    except BaseException as error:errors.append(dict(phase='MONITOR_CLEANUP',error_type=type(error).__name__))
    if owned is not None:
        try:reaped=terminate_owned(owned,deadline_seconds=5).reaped
        except BaseException as error:errors.append(dict(phase='OWNED_CLEANUP',error_type=type(error).__name__))
for phase in ('LOG_RETENTION','SOURCE_GUARD','WRAPPER_GUARD','OWNING_CHECKPOINT'):
    try:
        if phase=='LOG_RETENTION':
            raw=(output/'wrapper.raw').read_bytes()
            safe=_sanitize(raw.decode('utf-8',errors='replace'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').encode()
            write_private_new(output/'wrapper.log',safe)
        elif phase=='SOURCE_GUARD':revision_fact(ROOT,revision,True);unchanged=True
        elif phase=='WRAPPER_GUARD':
            wrapper_unchanged=wrapper.read_bytes()==wrapper_raw
            if not wrapper_unchanged:raise ValueError('Owning wrapper changed')
        else:
            from application.paper.qualification import artifact_bytes
            stage=json.loads(artifact_bytes(BASE/('qualify-'+revision[:7]+'-'+attempt),'checkpoint.json'))
    except BaseException as error:errors.append(dict(phase=phase,error_type=type(error).__name__))
sample_snapshot=list(samples)
valid=[row for row in sample_snapshot if 'host_available_bytes' in row]
owning_passed=stage.get('passed') if isinstance(stage,dict) else None
result=dict(kind='ACTUAL_OWNING_EXECUTION_RESOURCE_OBSERVATION',revision=revision,attempt=attempt,
    started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),exit_code=code,tree_reaped=reaped,
    owning_passed=owning_passed,qualification_credit='ONLY_ACTUAL_OWNING_RECEIPT',source_unchanged=unchanged,
    wrapper_unchanged=wrapper_unchanged,errors=errors,valid_samples=len(valid),
    monitor_stopped=worker is None or not worker.is_alive(),
    wrapper_hash='sha256:'+hashlib.sha256(wrapper_raw).hexdigest(),observer_hash='sha256:'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    samples=sample_snapshot,peak_owned_rss_bytes=max((row['owned_rss_bytes'] for row in valid),default=None),
    peak_owned_private_bytes=max((row['owned_private_bytes'] for row in valid),default=None),
    minimum_host_available_bytes=min((row['host_available_bytes'] for row in valid),default=None),
    provider_requests_additional=0,provider_requests_cumulative=8,private_requests=0,credentials='NONE',capital='NONE')
write_private_new(output/'checkpoint.json',(json.dumps(result,indent=2)+'\n').encode())
print(json.dumps({key:value for key,value in result.items() if key!='samples'}),flush=True)
raise SystemExit(0 if code==0 and reaped and owning_passed is True and unchanged and wrapper_unchanged and valid and result['monitor_stopped'] and not errors else 2)
