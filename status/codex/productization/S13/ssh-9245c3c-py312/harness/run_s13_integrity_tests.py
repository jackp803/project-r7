from pathlib import Path
import hashlib,json,os,re,sys
project=Path(__file__).resolve().parent.parent;base=project/'artifacts';repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.platform.processes import ResourceLimits,spawn_owned
from application.qualification import _sanitize
label=sys.argv[1];assert re.fullmatch('[A-Za-z0-9_-]+',label)
log=base/(label+'.log');assert not log.exists()
raw=log.with_suffix('.raw');env=os.environ.copy();env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
with raw.open('xb') as stream:
    owned=spawn_owned([sys.executable,'-m','unittest','discover','-s',str(base),'-p','s13_acceptance_integrity_tests.py','-v'],cwd=repo,
        limits=ResourceLimits(90),stdout=stream,stderr=-2,env=env)
    code=owned.wait()
text=_sanitize(raw.read_text(encoding='utf-8',errors='replace'),repo).replace('\r\n','\n');log.write_text(text,encoding='utf-8',newline='\n')
counts=re.search(r'Ran (\d+) tests?',text);assert counts
facts=dict(tests_run=int(counts[1]),exit_code=code,passed=code==0 and owned.termination_report.reaped,tree_reaped=owned.termination_report.reaped,
    log=log.name,log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest())
log.with_suffix('.json').write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(facts));raise SystemExit(code)
