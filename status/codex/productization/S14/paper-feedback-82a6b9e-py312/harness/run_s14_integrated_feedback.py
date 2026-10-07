"""Bounded affected source tests, with retained sanitized logs."""
from pathlib import Path
import hashlib,json,os,re,sys
base=Path(__file__).resolve().parent;repo=base.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.platform.processes import ResourceLimits,spawn_owned
from application.qualification import _sanitize,parse_result,revision_fact
label=sys.argv[1];assert re.fullmatch('[A-Za-z0-9_-]+',label)
selection=sys.argv[2]
groups={
 'new':('tests.product.test_paper_feedback_projection.PaperFeedbackProjectionTests',
 'tests.product.test_paper_feedback_outbox.PaperFeedbackOutboxTests',
 'tests.product.test_paper_feedback_schema.PaperFeedbackSchemaTests',
 'tests.product.test_public_feedback_dispatch.PublicFeedbackDispatchTests',
 'tests.product.test_paper_feedback_bridge.PaperFeedbackBridgeTests'),
 'cloud':('tests.application.test_cloud_bridge','tests.application.test_cloud_long_paths',
 'tests.application.test_feedback_redaction','tests.application.test_authoring_roundtrip')}
names=groups[selection]
code=('import sys,unittest;sys.path.insert(0,'+repr(str(repo))+');sys.path.insert(0,'+repr(str(repo/'src'))+');'
 'suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in '+repr(names)+');'
 'result=unittest.TextTestRunner(verbosity=2).run(suite);sys.exit(0 if result.wasSuccessful() else 1)')
before=revision_fact(repo)
log=base/(label+'.log');raw=log.with_suffix('.raw');assert not log.exists()
with raw.open('xb') as stream:
 owned=spawn_owned([sys.executable,'-c',code],cwd=repo,limits=ResourceLimits(420),stdout=stream,stderr=-2,
   env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'));returncode=owned.wait()
text=_sanitize(raw.read_text(encoding='utf-8',errors='replace'),repo).replace('\r\n','\n')
log.write_text(text,encoding='utf-8',newline='\n');result=parse_result(text,returncode=returncode)
facts=dict(selection=list(names),source_before=before,source_after=revision_fact(repo),tests_run=result.tests_run,
 failures=result.failures,errors=result.errors,skipped=result.skipped,passed=result.passed and owned.termination_report.reaped,
 tree_reaped=owned.termination_report.reaped,scope='AFFECTED_SOURCE_TESTS;LOCAL_FIXTURES_ONLY;NOT_NATIVE_QUALIFICATION',
 log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest(),real_provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
log.with_suffix('.json').write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(facts));raise SystemExit(returncode)
