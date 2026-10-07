"""Fixed integrated regression with actual changed source subprocesses."""
from pathlib import Path
import hashlib,json,os,re,sys
base=Path(__file__).resolve().parent
repo=base.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.platform.processes import ResourceLimits,spawn_owned
from application.qualification import _sanitize,parse_result,revision_fact
from strategy.v02.capabilities import _revision
label=sys.argv[1];assert re.fullmatch('[A-Za-z0-9_-]+',label)
names=('tests.application.test_runtime_process_supervision','tests.application.test_process_supervision',
    'tests.application.test_control_process_supervision','tests.application.test_database_backup','tests.application.test_product_data_backup')
code=('import sys,unittest;sys.path.insert(0,'+repr(str(repo))+');sys.path.insert(0,'+repr(str(repo/'src'))+');'
    'suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in '+repr(names)+');'
    'result=unittest.TextTestRunner(verbosity=2).run(suite);sys.exit(0 if result.wasSuccessful() else 1)')
paths=(Path(__file__),repo/'src/application/platform/supervision.py',repo/'src/application/migrations/0008_runtime_process_supervision.sql',
    repo/'src/application/migrations/0006_process_supervision.sql',repo/'tests/application/test_runtime_process_supervision.py',
    repo/'docs/product/v0_2/RUNTIME_PROCESS_SUPERVISION_IMPLEMENTATION.md')
capture=lambda:{path.relative_to(base.parent).as_posix():'sha256:'+hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
before=revision_fact(repo);before_implementation=_revision();before_inputs=capture()
log=base/(label+'.log');raw=log.with_suffix('.raw');assert not log.exists() and not raw.exists()
with raw.open('xb') as stream:
    owned=spawn_owned([sys.executable,'-c',code],cwd=repo,limits=ResourceLimits(300),stdout=stream,stderr=-2,
        env=dict(os.environ,PYTHONPATH=str(repo/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
    returncode=owned.wait()
text=_sanitize(raw.read_text(encoding='utf-8',errors='replace'),repo).replace('\r\n','\n')
log.write_text(text,encoding='utf-8',newline='\n');result=parse_result(text,returncode=returncode)
after=revision_fact(repo);after_implementation=_revision();after_inputs=capture()
facts=dict(selection=list(names),source_before=before,source_after=after,
    implementation_hash_before=before_implementation,implementation_hash_after=after_implementation,
    execution_input_sha256_before=before_inputs,execution_input_sha256_after=after_inputs,harness_binding='BEFORE_AND_AFTER_EXECUTION',
    tests_run=result.tests_run,failures=result.failures,errors=result.errors,skipped=result.skipped,
    passed=result.passed and result.tests_run==52 and owned.termination_report.reaped and before==after
        and before_implementation==after_implementation and before_inputs==after_inputs,
    tree_reaped=owned.termination_report.reaped,exit_code=returncode,
    scope='INTEGRATED_SOURCE_OWNERS_AND_ACTUAL_CHANGED_CONTROL_SUBPROCESSES;LOCAL_FIXTURES;NOT_EXACT_CLEAN_QUALIFICATION',
    log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest(),
    real_provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
log.with_suffix('.json').write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({key:facts[key] for key in ('tests_run','failures','errors','skipped','passed','tree_reaped','log_sha256')}))
raise SystemExit(returncode if returncode else (0 if facts['passed'] else 1))
