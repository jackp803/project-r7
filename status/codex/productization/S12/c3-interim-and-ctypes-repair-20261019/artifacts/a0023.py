"""Actual owned source recheck; resource diagnostic, no qualification credit."""
from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,threading
from pathlib import Path
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1];ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT/'tools'),str(BASE.parent)]
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.platform.private_files import create_private_directory,write_private_new
from application.platform.resources import inspect_hardware
from application.qualification import revision_fact,parse_result,_sanitize
from verify_paper_isolation import WindowsOwnedProcessSampler,MeasurementProcessExited
from local_windows_qualification_awake import awake_request
REVISION='c3f4f2a71d4203d3ceb12796570ebc9958a63323'
revision_fact(ROOT,REVISION,True)
output=BASE/'source151-resource-recheck-c3f4f2a-first';create_private_directory(output)
report=dict(revision=REVISION,kind='SOURCE_RECHECK_AND_OWNED_MEMORY_DIAGNOSTIC_ONLY',passed=False,
    started_at=datetime.now(timezone.utc).isoformat(),additional_public_requests=0,cumulative_public_requests=8,
    credentials='NONE',private_requests=0,capital='NONE',github_compute='NOT_USED',master='IN_PROGRESS')
environment=os.environ.copy();environment.update(PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
owned=None;done=threading.Event();samples=[];sampler=WindowsOwnedProcessSampler()
def monitor():
    while not done.is_set():
        try:
            hardware=inspect_hardware(BASE);rows=sampler.sample_owned(owned)
            samples.append(dict(observed_at=datetime.now(timezone.utc).isoformat(),available_memory_bytes=hardware.available_memory_bytes,
                processes=rows,total_owned_rss_bytes=sum(r['rss_bytes'] for r in rows),total_owned_private_bytes=sum(r['private_bytes'] for r in rows)))
        except MeasurementProcessExited:break
        except BaseException as error:samples.append(dict(error_type=type(error).__name__))
        done.wait(1)
with awake_request() as awake:
    try:
        with (output/'source.raw').open('xb') as stream:
            owned=spawn_owned([sys.executable,'-X','utf8','-m','unittest','discover','-s','tests/product','-p','test_trading_position_v02.py','-v'],
                cwd=ROOT,limits=ResourceLimits(900),stdout=stream,stderr=subprocess.STDOUT,env=environment)
            worker=threading.Thread(target=monitor,daemon=True);worker.start()
            code=owned.wait();done.set();worker.join(timeout=3)
        text=_sanitize((output/'source.raw').read_text(encoding='utf-8',errors='replace'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n')
        raw=text.encode();write_private_new(output/'source.log',raw)
        result=parse_result(text,returncode=code)
        report.update(passed=result.passed,tests=result.tests_run,failures=result.failures,errors=result.errors,
            skipped=result.skipped,exit_code=code,source_log_hash='sha256:'+hashlib.sha256(raw).hexdigest())
    finally:
        done.set()
        if owned is not None:report['tree_reaped']=terminate_owned(owned,deadline_seconds=5).reaped
        report['samples']=samples;report['finished_at']=datetime.now(timezone.utc).isoformat();report['awake']=awake
        revision_fact(ROOT,REVISION,True);report['source_unchanged']=True
        valid=[r for r in samples if 'processes' in r]
        report['peak_owned_rss_bytes']=max((r['total_owned_rss_bytes'] for r in valid),default=None)
        report['peak_owned_private_bytes']=max((r['total_owned_private_bytes'] for r in valid),default=None)
        report['minimum_host_available_bytes']=min((r['available_memory_bytes'] for r in valid),default=None)
write_private_new(output/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
print(json.dumps({k:v for k,v in report.items() if k not in ('samples','awake')}),flush=True)
raise SystemExit(0 if report['passed'] and report['tree_reaped'] else 2)
