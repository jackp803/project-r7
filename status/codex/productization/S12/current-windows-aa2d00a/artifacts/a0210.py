"""One outer established owned scope for a readonly one-off committed-tree scan."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.platform.resources import _memory,GIB
from application.qualification import revision_fact,_sanitize
REV='aa2d00a4de1147fbc5ff5c4ed14db2f5032b65dd'
mode=sys.argv[1]
if mode not in ('refusal-retry01','first'):raise ValueError('Fixed fresh scan attempt required')
revision_fact(ROOT,REV,True)
helper=BASE/'audit_l01_l05_committed_tree_aa2d00a.py'
rules=BASE/'l01-l05-local-audit-rules-aa2d00a.json'
assert hashlib.sha256(helper.read_bytes()).hexdigest()=='71cf4640edacc9d608e9dfe72b106e9f6c4b1ca93432f13b15dc60962b4a4903'
assert hashlib.sha256(rules.read_bytes()).hexdigest()=='66da69b0834dabef460981916d655613a7ade826d406879a963a8a70fe23eacd'
compile(helper.read_bytes(),str(helper),'exec')
_,available=_memory()
if available<6*GIB:raise ValueError('Conservative scan launch floor; no product threshold changed')
out=BASE/('committed-tree-owned-aa2d00a-'+mode)
out.mkdir(exist_ok=False)
report=BASE/('l01-l05-audit-aa2d00a-'+mode+'.json')
if report.exists():raise ValueError('Preserve prior reports')
expected='aa2d00a'+'0'*33 if mode.startswith('refusal') else REV
owned=None;cleanup=None;code=None;start=time.monotonic()
try:
    with (out/'stdout.raw').open('xb') as stream:
        owned=spawn_owned([sys.executable,'-X','utf8',str(helper),'--expected-head',expected,
            '--git','C:/Program Files/Git/mingw64/bin/git.exe','--output',str(report)],
            cwd=ROOT,limits=ResourceLimits(300),stdout=stream,stderr=subprocess.STDOUT)
        code=owned.wait()
finally:
    if owned is not None:cleanup=terminate_owned(owned,deadline_seconds=5)
raw=(out/'stdout.raw').read_text(encoding='utf-8')
(out/'stdout.log').write_text(_sanitize(raw,ROOT),encoding='utf-8',newline='\n')
(out/'stdout.raw').unlink()
actual=json.loads(report.read_bytes()) if report.exists() else None
if mode.startswith('refusal'):
    assert code==2 and actual['status']=='STOP_AUDIT_FAILED' and actual['error_code']=='HEAD_SUBJECT_MISMATCH'
    assert 'findings' not in actual
else:
    assert actual is not None and actual['subject']['head']==REV
    assert actual['final_subject_unchanged'] and actual['all_direct_git_children_reaped']
revision_fact(ROOT,REV,True)
result=dict(mode=mode,scanner_exit_code=code,scanner_status=actual['status'],
    outer_tree_reaped=bool(cleanup and cleanup.reaped),memory_enforcement='SOFT_LIMIT_ONLY',
    outer_timeout_seconds=300,available_at_launch=available,elapsed_seconds=time.monotonic()-start,
    scanner_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),report_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),
    source_revision=REV,source_unchanged=True,public_requests=0,private_requests=0,github_compute='NOT_USED',
    acceptance='SCOPED_STATIC_SCAN_ONLY;ROOT_TRIAGE_REQUIRED;NO_WHOLE_HISTORY_OR_REQUIREMENT_PASS')
assert result['outer_tree_reaped']
(out/'checkpoint.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(result))
