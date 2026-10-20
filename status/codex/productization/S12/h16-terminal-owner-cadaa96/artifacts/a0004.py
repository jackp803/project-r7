"""Bounded current-session resource wait, then one genuine owner RED attempt."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys,time
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.platform.resources import _memory,GIB
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.qualification import _sanitize
from strategy.v02.capabilities import _revision
out=BASE/'h16-terminal-stop-owner-red-retry01';out.mkdir(exist_ok=False)
source=_revision();case=ROOT/'tests/product/test_trading_terminal_stop_v02.py'
test_hash=hashlib.sha256(case.read_bytes()).hexdigest();start=datetime.now(timezone.utc).isoformat()
samples=[];deadline=time.monotonic()+180;owned=None;cleanup=None;exit_code=None
while True:
    total,available=_memory();samples.append(dict(at=datetime.now(timezone.utc).isoformat(),available_bytes=available))
    if available>=6*GIB:break
    if time.monotonic()>=deadline:break
    time.sleep(10)
if available>=6*GIB:
    if _revision()!=source or hashlib.sha256(case.read_bytes()).hexdigest()!=test_hash:raise ValueError('Subject changed')
    try:
        with (out/'source.raw').open('xb') as stream:
            owned=spawn_owned([sys.executable,'-X','utf8','-m','unittest','-v','tests.product.test_trading_terminal_stop_v02'],
                cwd=ROOT,limits=ResourceLimits(900),stdout=stream,stderr=subprocess.STDOUT)
            exit_code=owned.wait()
    finally:
        if owned is not None:cleanup=terminate_owned(owned,deadline_seconds=10)
    raw=(out/'source.raw').read_text(encoding='utf-8')
    safe=_sanitize(raw,ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n')
    (out/'source.log').write_text(safe,encoding='utf-8',newline='\n');(out/'source.raw').unlink()
    status='EXECUTED_RED_ATTEMPT'
else:status='NOT_RUN_RESOURCE_PREFLIGHT_BELOW_6GIB_NO_TEST_FAILURE_OR_PASS'
if _revision()!=source or hashlib.sha256(case.read_bytes()).hexdigest()!=test_hash:raise ValueError('Subject changed')
report=dict(status=status,implementation_hash=source,test_hash=test_hash,started_at=start,
    finished_at=datetime.now(timezone.utc).isoformat(),resource_samples=samples,exit_code=exit_code,
    tree_reaped=bool(cleanup and cleanup.reaped),source_unchanged=True,
    acceptance_credit='NONE',private_requests=0,public_requests=0)
(out/'checkpoint.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:v for k,v in report.items() if k!='resource_samples'}))
