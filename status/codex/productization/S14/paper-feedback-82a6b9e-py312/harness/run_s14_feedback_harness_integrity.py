from pathlib import Path
import hashlib,json,os,re,sys
base=Path(__file__).resolve().parent;repo=base.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.qualification import _sanitize,parse_result
from application.platform.processes import ResourceLimits,spawn_owned
label=sys.argv[1];assert re.fullmatch('[A-Za-z0-9_-]+',label)
log=base/(label+'.log');assert not log.exists()
with log.open('xb') as stream:
 owned=spawn_owned([sys.executable,str(base/'test_s14_feedback_harness_integrity.py')],cwd=base,limits=ResourceLimits(30),
  stdout=stream,stderr=-2,env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'));code=owned.wait()
text=_sanitize(log.read_text(encoding='utf-8',errors='replace'),repo).replace('\r\n','\n');log.write_text(text,encoding='utf-8',newline='\n')
result=parse_result(text,returncode=code)
facts=dict(tests_run=result.tests_run,failures=result.failures,errors=result.errors,passed=result.passed and owned.termination_report.reaped,
 tree_reaped=owned.termination_report.reaped,scope='QUALIFICATION_EXIT_AND_DEPENDENCY_HASH_GUARD_FRAGMENTS;CONTROLLED_CLEANUP_AND_REPLACEMENT;NO_PRODUCT_EXECUTION',
 log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest(),wrapper_sha256='sha256:'+hashlib.sha256((base/'s14_feedback_bound_installer.py').read_bytes()).hexdigest())
log.with_suffix('.json').write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(facts));raise SystemExit(0 if facts['passed'] else (code or 1))
