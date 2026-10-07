"""Owned local development tests; never qualified release or runtime activation."""
from pathlib import Path
import hashlib,json,os,re,sys

base=Path(__file__).resolve().parent
repo=base.parent/'workspaces/project-r7-productization-master-20261002'
development=base/'S12-runtime-supervision-development'
sys.path.insert(0,str(repo/'src'))
from application.platform.processes import ResourceLimits,spawn_owned
from application.qualification import _sanitize,parse_result,revision_fact
from s12_runtime_supervision_harness_integrity import capture_inputs,require_unchanged_inputs
label=sys.argv[1]
assert re.fullmatch('[A-Za-z0-9_-]+',label)
selection=sys.argv[2] if len(sys.argv)>2 else 'new'
groups={'new':('test_runtime_process_supervision.RuntimeProcessSupervisionTests',),
    'harness':('test_s12_runtime_supervision_harness_integrity.RuntimeSupervisionHarnessIntegrityTests',),
    'regression':('tests.application.test_process_supervision','tests.application.test_control_process_supervision',
        'tests.application.test_database_backup','tests.application.test_product_data_backup')}
names=groups[selection]
code=('import sys,unittest;sys.path.insert(0,'+repr(str(base))+');sys.path.insert(0,'+repr(str(development))+');sys.path.insert(0,'+repr(str(repo))+');sys.path.insert(0,'+repr(str(repo/'src'))+');'
    'import application.platform;application.platform.__path__.insert(0,'+repr(str(development/'platform'))+');'
    'suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in '+repr(names)+');'
    'result=unittest.TextTestRunner(verbosity=2).run(suite);sys.exit(0 if result.wasSuccessful() else 1)')
before=revision_fact(repo)
harnesses=(Path(__file__),base/'s12_runtime_supervision_harness_integrity.py',
    base/'test_s12_runtime_supervision_harness_integrity.py')
before_inputs=capture_inputs(development,harnesses)
log=base/(label+'.log');raw=log.with_suffix('.raw')
assert not log.exists() and not raw.exists()
with raw.open('xb') as stream:
    owned=spawn_owned([sys.executable,'-c',code],cwd=repo,limits=ResourceLimits(300),stdout=stream,stderr=-2,
        env=dict(os.environ,PYTHONPATH=str(repo/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
    returncode=owned.wait()
text=_sanitize(raw.read_text(encoding='utf-8',errors='replace'),repo).replace('\r\n','\n')
log.write_text(text,encoding='utf-8',newline='\n')
result=parse_result(text,returncode=returncode)
after_source=revision_fact(repo)
after_inputs={};input_binding=False;input_binding_error=None
try:
    after_inputs=capture_inputs(development,harnesses)
    require_unchanged_inputs(before_inputs,after_inputs)
    input_binding=True
except (OSError,ValueError) as error:
    input_binding_error=type(error).__name__
facts=dict(selection=list(names),source_before=before,source_after=after_source,
    tests_run=result.tests_run,failures=result.failures,errors=result.errors,skipped=result.skipped,
    passed=result.passed and owned.termination_report.reaped and input_binding and before==after_source,exit_code=returncode,
    tree_reaped=owned.termination_report.reaped,scope='DEVELOPMENT_OVERLAY;ACTUAL_SUPERVISOR_SQLITE_AND_HOST_LOCK_FIXTURES;NOT_EXACT_CLEAN_RELEASE;NO_PAPER_RUNTIME_START',
    subprocess_scope='COMMITTED_SOURCE_CHILDREN;SAME_PROCESS_OWNERS_USE_DEVELOPMENT_OVERLAY;INTEGRATED_CHILD_VERIFICATION_PENDING',
    log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest(),
    harness_binding='BEFORE_AND_AFTER_EXECUTION',inputs_unchanged=input_binding,input_binding_error=input_binding_error,
    execution_input_sha256_before=before_inputs,execution_input_sha256_after=after_inputs,
    wrapper_sha256=before_inputs['harness/'+Path(__file__).name],
    real_provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
log.with_suffix('.json').write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({key:facts[key] for key in ('tests_run','failures','errors','skipped','passed','tree_reaped','log_sha256')}))
raise SystemExit(returncode if returncode else (0 if facts['passed'] else 1))
