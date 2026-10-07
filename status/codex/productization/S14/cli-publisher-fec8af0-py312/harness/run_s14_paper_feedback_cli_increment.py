"""Owned bounded current-source tests with input and implementation closure."""
from pathlib import Path
import hashlib,json,os,re,sys
base=Path(__file__).resolve().parent
repo=base.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.platform.processes import ResourceLimits,spawn_owned
from application.qualification import _sanitize,parse_result,revision_fact
from strategy.v02.capabilities import _revision
label,selection=sys.argv[1:]
assert re.fullmatch('[A-Za-z0-9_-]+',label)
groups={
    'new':('tests.product.test_paper_feedback_cli.PaperFeedbackCliTests',
        'tests.storage.test_paper_process_existing.PaperProcessExistingTests'),
    'affected':('tests.product.test_paper_feedback_cli.PaperFeedbackCliTests',
        'tests.storage.test_paper_process_existing.PaperProcessExistingTests',
        'tests.storage.test_paper_process_journal',
        'tests.product.test_paper_feedback_projection.PaperFeedbackProjectionTests',
        'tests.product.test_paper_feedback_outbox.PaperFeedbackOutboxTests',
        'tests.product.test_paper_feedback_schema.PaperFeedbackSchemaTests',
        'tests.product.test_public_feedback_dispatch.PublicFeedbackDispatchTests',
        'tests.product.test_paper_feedback_bridge.PaperFeedbackBridgeTests',
        'tests.application.test_cloud_bridge','tests.application.test_cloud_long_paths',
        'tests.application.test_feedback_redaction','tests.application.test_authoring_roundtrip')}
names=groups[selection]
paths=[Path(__file__),repo/'src/application/cli.py',repo/'tests/product/test_paper_feedback_cli.py',
       repo/'tests/storage/test_paper_process_existing.py',base/'S14-paper-feedback-cli-increment-plan.md']
bind=lambda:{p.relative_to(base.parent).as_posix():'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
inputs_before=bind();source_before=revision_fact(repo);implementation_before=_revision()
code=('import sys,unittest;sys.path.insert(0,'+repr(str(repo))+');sys.path.insert(0,'+repr(str(repo/'src'))+');'
      'suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in '+repr(names)+');'
      'result=unittest.TextTestRunner(verbosity=2).run(suite);sys.exit(0 if result.wasSuccessful() else 1)')
raw=base/(label+'.owned.raw');log=base/(label+'.log');report=base/(label+'.json')
assert not any(path.exists() for path in (raw,log,report))
with raw.open('xb') as stream:
    owned=spawn_owned([sys.executable,'-c',code],cwd=repo,limits=ResourceLimits(420),stdout=stream,stderr=stream,
        env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
    returncode=owned.wait()
text=_sanitize(raw.read_text(encoding='utf-8',errors='replace'),repo).replace('\r\n','\n')
raw.unlink();log.write_text(text,encoding='utf-8',newline='\n')
result=parse_result(text,returncode=returncode)
inputs_after=bind();source_after=revision_fact(repo);implementation_after=_revision()
facts=dict(**result.__dict__,exit_code=returncode,tree_reaped=owned.termination_report.reaped,
    harness_binding='BEFORE_AND_AFTER_EXECUTION',input_sha256_before=inputs_before,input_sha256_after=inputs_after,
    source_before=source_before,source_after=source_after,
    implementation_hash_before=implementation_before,implementation_hash_after=implementation_after,
    selection=list(names),scope='SOURCE_COMPOSITION;ACTUAL_HISTORICAL_PAPER_OWNER;LOCAL_FAKE_ONLY;NOT_NATIVE_OR_NORMAL_RUNTIME',
    log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest(),
    real_provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
facts['passed']=result.passed and owned.termination_report.reaped and inputs_before==inputs_after and source_before==source_after and implementation_before==implementation_after
report.write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({key:value for key,value in facts.items() if not key.startswith('input_') and key!='selection'}))
raise SystemExit(0 if facts['passed'] else 1)
