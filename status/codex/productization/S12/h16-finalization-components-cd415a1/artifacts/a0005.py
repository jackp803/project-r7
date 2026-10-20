"""Bounded development probe; source/test freeze, no qualification credit."""
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
out=BASE/sys.argv[1];modules=sys.argv[2:]
if not modules:raise ValueError('Exact modules required')
paths=sorted(set(list((ROOT/'tests/product').glob('*finalization*.py'))+[ROOT/'tests/storage/test_trade_finalization_constraints.py']))
def pin():return {str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
source=_revision();pins=pin();start=datetime.now(timezone.utc).isoformat()
out.mkdir(exist_ok=False);samples=[];deadline=time.monotonic()+180;owned=None;cleanup=None;code=None
while True:
    total,available=_memory();samples.append(dict(at=datetime.now(timezone.utc).isoformat(),available_bytes=available))
    if available>=6*GIB or time.monotonic()>=deadline:break
    time.sleep(10)
if available>=6*GIB:
    if _revision()!=source or pin()!=pins:raise ValueError('Subject changed before execution')
    try:
        with (out/'source.raw').open('xb') as stream:
            owned=spawn_owned([sys.executable,'-X','utf8','-m','unittest','-v',*modules],cwd=ROOT,
                limits=ResourceLimits(900),stdout=stream,stderr=subprocess.STDOUT)
            code=owned.wait()
    finally:
        if owned is not None:cleanup=terminate_owned(owned,deadline_seconds=10)
    raw=(out/'source.raw').read_text(encoding='utf-8')
    safe=_sanitize(raw,ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n')
    (out/'source.log').write_text(safe,encoding='utf-8',newline='\n');(out/'source.raw').unlink()
    status='EXECUTED_DEVELOPMENT_PROBE'
else:status='NOT_RUN_RESOURCE_PREFLIGHT_BELOW_6GIB'
unchanged=_revision()==source and pin()==pins
report=dict(status=status,implementation_hash=source,test_file_hashes=pins,modules=modules,
    helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),started_at=start,
    finished_at=datetime.now(timezone.utc).isoformat(),resource_samples=samples,exit_code=code,
    tree_reaped=bool(cleanup and cleanup.reaped),source_and_tests_unchanged=unchanged,
    acceptance_credit='NONE',private_requests=0,public_requests=0)
(out/'checkpoint.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('resource_samples','test_file_hashes')}))
if not unchanged:raise ValueError('Subject changed during execution')
