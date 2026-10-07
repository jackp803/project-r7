"""Capture one bounded existing suite pattern without shell redirection."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,time
project=Path(__file__).resolve().parent.parent
repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.platform.processes import ResourceLimits,spawn_owned
from application.qualification import _sanitize
suite,pattern,label=sys.argv[1:]
assert suite in ('application','product')
assert re.fullmatch(r'test_[a-z0-9_*]+\.py',pattern)
assert re.fullmatch(r'[A-Za-z0-9_-]+',label)
log=project/'artifacts'/f'{label}.log'; assert not log.exists()
raw_path=log.with_suffix('.raw')
env=os.environ.copy();env.update(PYTHONPATH=str(repo/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
start=time.monotonic()
with raw_path.open('xb') as stream:
    owned=spawn_owned([sys.executable,'-m','unittest','discover','-s',f'tests/{suite}','-p',pattern,'-v'],
        cwd=repo,limits=ResourceLimits(900),stdout=stream,stderr=subprocess.STDOUT,env=env)
    code=owned.wait()
sanitized=_sanitize(raw_path.read_text(encoding='utf-8',errors='replace'),repo).replace('\r\n','\n')
log.write_text(sanitized,encoding='utf-8',newline='\n')
counts=re.search(r'Ran (\d+) tests?',sanitized); assert counts
record=dict(suite=suite,pattern=pattern,tests_run=int(counts[1]),exit_code=code,tree_reaped=owned.termination_report.reaped,
    passed=code==0 and owned.termination_report.reaped,duration_seconds=time.monotonic()-start,
    log=log.name,log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest(),local=True)
for name in ('failures','errors','skipped'):
    found=re.search(r'\b'+name+r'=(\d+)',sanitized);record[name]=int(found[1]) if found else 0
log.with_suffix('.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(record))
raise SystemExit(code)
