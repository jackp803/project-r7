from pathlib import Path
import hashlib,json,os,re,sys
base=Path(__file__).resolve().parent;repo=base.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.qualification import _sanitize,parse_result
from application.platform.processes import ResourceLimits,spawn_owned
label=sys.argv[1];assert re.fullmatch('[A-Za-z0-9_-]+',label)
names=(Path(__file__).name,'s12_runtime_supervision_review_integrity.py','test_s12_runtime_supervision_review_integrity.py',
    's13_installer_acceptance_integrity.py','s14_feedback_acceptance_core.py',
    's13_acceptance_integrity.py','s13_ssh_acceptance_integrity.py')
capture=lambda:{name:'sha256:'+hashlib.sha256((base/name).read_bytes()).hexdigest() for name in names}
before=capture();log=base/(label+'.log');assert not log.exists()
with log.open('xb') as stream:
    owned=spawn_owned([sys.executable,'-m','unittest','test_s12_runtime_supervision_review_integrity','-v'],cwd=base,
        limits=ResourceLimits(30),stdout=stream,stderr=-2,
        env=dict(os.environ,PYTHONPATH=str(repo/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
    code=owned.wait()
text=_sanitize(log.read_text(encoding='utf-8',errors='replace'),repo).replace('\r\n','\n')
log.write_text(text,encoding='utf-8',newline='\n');result=parse_result(text,returncode=code);after=capture()
facts=dict(tests_run=result.tests_run,failures=result.failures,errors=result.errors,skipped=result.skipped,
    passed=result.passed and result.tests_run==8 and owned.termination_report.reaped and before==after,
    exit_code=code,tree_reaped=owned.termination_report.reaped,harness_binding='BEFORE_AND_AFTER_EXECUTION',
    input_sha256_before=before,input_sha256_after=after,
    scope='CONTROLLED_REVIEW_INVENTORY_AND_PRIMARY_EXECUTION_LOG_RETENTION_GUARDS;NO_PRODUCT_EXECUTION',
    log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest())
log.with_suffix('.json').write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({key:facts[key] for key in ('tests_run','failures','errors','skipped','passed','tree_reaped','log_sha256')}))
raise SystemExit(0 if facts['passed'] else (code or 1))
