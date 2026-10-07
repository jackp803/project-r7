from pathlib import Path
import hashlib,json,os,re,sys
base=Path(__file__).resolve().parent;repo=base.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.platform.processes import ResourceLimits,spawn_owned
from application.qualification import _sanitize,parse_result
label=sys.argv[1];assert re.fullmatch('[A-Za-z0-9_-]+',label)
suite=sys.argv[2] if len(sys.argv)>2 else 'test_paper_feedback_projection.PaperFeedbackProjectionTests'
assert suite in ('test_paper_feedback_projection.PaperFeedbackProjectionTests','test_paper_feedback_outbox.PaperFeedbackOutboxTests',
    'test_paper_feedback_schema.PaperFeedbackSchemaTests','test_public_feedback_dispatch.PublicFeedbackDispatchTests',
    'test_paper_feedback_bridge.PaperFeedbackBridgeTests')
development=base/'S14-paper-feedback-development'
code=('import sys,unittest;sys.path.insert(0,'+repr(str(repo))+');sys.path.insert(0,'+repr(str(repo/'src'))+');'
    'import application.cloud,storage;application.cloud.__path__.insert(0,'+repr(str(development/'cloud'))+');'
    'storage.__path__.insert(0,'+repr(str(development/'storage'))+');'
    'suite=unittest.defaultTestLoader.loadTestsFromName('+repr(suite)+');'
    'result=unittest.TextTestRunner(verbosity=2).run(suite);sys.exit(0 if result.wasSuccessful() else 1)')
log=base/(label+'.log');assert not log.exists();raw=log.with_suffix('.raw')
with raw.open('xb') as stream:
    owned=spawn_owned([sys.executable,'-c',code],cwd=development,limits=ResourceLimits(240),stdout=stream,stderr=-2,
        env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'));code=owned.wait()
text=_sanitize(raw.read_text(encoding='utf-8',errors='replace'),repo).replace('\r\n','\n');log.write_text(text,encoding='utf-8',newline='\n')
result=parse_result(text,returncode=code)
facts=dict(tests_run=result.tests_run,failures=result.failures,errors=result.errors,passed=result.passed and owned.termination_report.reaped,
    tree_reaped=owned.termination_report.reaped,scope='DEVELOPMENT_OVERLAY;ACTUAL_EXISTING_PAPER_OWNERS;ACCELERATED_FIXTURE_ONLY;NOT_EXACT_CLEAN_RELEASE',
    log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest(),real_provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
log.with_suffix('.json').write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(facts));raise SystemExit(code)
