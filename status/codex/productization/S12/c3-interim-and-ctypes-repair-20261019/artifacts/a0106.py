"""Bounded synthetic own-process ABI lifetime measurement, never qualification."""
from datetime import datetime, timezone
import ctypes, gc, hashlib, json, os, subprocess, sys, threading
from pathlib import Path
from tempfile import TemporaryDirectory
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1];ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tools')]
from application.cloud.safe_files import read_bounded,stage_author_input
from application.platform.resources import inspect_hardware
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from verify_paper_isolation import WindowsOwnedProcessSampler,MeasurementProcessExited

def counts():
    gc.collect()
    return {module:sum(getattr(kind,'__module__',None)==module for kind in ctypes._pointer_type_cache)
        for module in ('application.cloud.safe_files','application.platform.resources')}

if len(sys.argv)==2 and sys.argv[1]=='--child':
    with TemporaryDirectory(prefix='r7-abi-probe-',dir=BASE) as directory:
        root=Path(directory);(root/'value.json').write_bytes(b'synthetic-owned-memory-probe')
        read_bounded(root,'value.json',64);inspect_hardware(root)
        before=counts()
        for number in range(5000):
            assert read_bounded(root,'value.json',64)==b'synthetic-owned-memory-probe'
            if number%100==0:stage_author_input(root,'inbox/strategies/probe/strategy.json',str(number).encode())
            if number%50==0:inspect_hardware(root)
        after=counts()
        print(json.dumps(dict(before=before,after=after,growth={key:after[key]-before[key] for key in before},
            actual_reads=5000,actual_atomic_stages=50,actual_hardware_samples=100)),flush=True)
    raise SystemExit(0)

label=sys.argv[1]
if label not in ('before','after'):raise ValueError('Explicit diagnostic label required')
output=BASE/('ctypes-memory-'+label);output.mkdir()
sampler=WindowsOwnedProcessSampler();samples=[];done=threading.Event();owned=None
started=datetime.now(timezone.utc).isoformat()
def monitor():
    while not done.is_set():
        try:
            rows=sampler.sample_owned(owned)
            samples.append(dict(at=datetime.now(timezone.utc).isoformat(),rss_bytes=sum(row['rss_bytes'] for row in rows),
                private_bytes=sum(row['private_bytes'] for row in rows)))
        except MeasurementProcessExited:break
        done.wait(.1)
environment=os.environ.copy();environment.update(PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1')
with (output/'child.json').open('xb') as stream:
    owned=spawn_owned([sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--child'],cwd=ROOT,
        env=environment,limits=ResourceLimits(120),stdout=stream,stderr=subprocess.STDOUT)
    worker=threading.Thread(target=monitor,daemon=True);worker.start()
    try:code=owned.wait()
    finally:done.set();worker.join(timeout=2);reaped=terminate_owned(owned,deadline_seconds=5).reaped
result=dict(kind='SYNTHETIC_OWN_PROCESS_MEMORY_DIAGNOSTIC_ONLY',label=label,started_at=started,
    finished_at=datetime.now(timezone.utc).isoformat(),exit_code=code,tree_reaped=reaped,
    qualification_credit='NONE',provider_requests=0,credentials='NONE',private_requests=0,
    source_files={ref:'sha256:'+hashlib.sha256((ROOT/ref).read_bytes()).hexdigest() for ref in (
        'src/application/cloud/safe_files.py','src/application/platform/resources.py')},samples=samples,
    peak_owned_rss_bytes=max((row['rss_bytes'] for row in samples),default=0),
    peak_owned_private_bytes=max((row['private_bytes'] for row in samples),default=0))
if code==0:result['observed']=json.loads((output/'child.json').read_text())
(output/'checkpoint.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({key:value for key,value in result.items() if key not in ('samples','source_files')}),flush=True)
raise SystemExit(code)
