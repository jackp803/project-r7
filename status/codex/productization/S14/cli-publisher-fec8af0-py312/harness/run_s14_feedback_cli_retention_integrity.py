"""Owned current retention guard with complete helper and source closure."""
from pathlib import Path
import hashlib,json,os,re,sys
base=Path(__file__).resolve().parent;repo=base.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.platform.processes import ResourceLimits,spawn_owned
from application.qualification import _sanitize,parse_result,revision_fact
from strategy.v02.capabilities import _revision
label=sys.argv[1];assert re.fullmatch('[A-Za-z0-9_-]+',label)
names=('s14_feedback_cli_accept.py','s14_feedback_cli_acceptance_core.py','s14_feedback_cli_native_evidence.py',
    'test_s14_feedback_cli_native_evidence.py','run_s14_feedback_cli_retention_integrity.py',
    's12_runtime_supervision_review_integrity.py','s14_feedback_acceptance_core.py',
    's13_installer_acceptance_integrity.py','s13_ssh_acceptance_integrity.py','s13_acceptance_integrity.py')
capture=lambda:{name:'sha256:'+hashlib.sha256((base/name).read_bytes()).hexdigest() for name in names}
before=capture();source_before=revision_fact(repo);implementation_before=_revision()
raw=base/(label+'.owned.raw');log=base/(label+'.log');target=base/(label+'.json')
assert not any(path.exists() for path in (raw,log,target))
with raw.open('xb') as stream:
    owned=spawn_owned([sys.executable,str(base/'test_s14_feedback_cli_native_evidence.py')],cwd=base,
        limits=ResourceLimits(30),stdout=stream,stderr=stream,
        env=dict(os.environ,PYTHONPATH=str(repo/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
    code=owned.wait()
text=_sanitize(raw.read_text(encoding='utf-8',errors='replace'),repo).replace('\r\n','\n')
raw.unlink();log.write_text(text,encoding='utf-8',newline='\n')
parsed=parse_result(text,returncode=code);after=capture();source_after=revision_fact(repo);implementation_after=_revision()
facts=dict(**parsed.__dict__,exit_code=code,tree_reaped=owned.termination_report.reaped,
    harness_binding='BEFORE_AND_AFTER_EXECUTION',input_sha256_before=before,input_sha256_after=after,
    source_before=source_before,source_after=source_after,implementation_hash_before=implementation_before,implementation_hash_after=implementation_after,
    log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest(),
    scope='CONTROLLED_RETENTION_NATIVE_SUBJECT_AND_CLEANUP_GUARD_ONLY;NO_PRODUCT_EXECUTION')
facts['passed']=parsed.passed and parsed.tests_run==11 and owned.termination_report.reaped and before==after and source_before==source_after and implementation_before==implementation_after
target.write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({key:facts[key] for key in ('passed','tests_run','failures','errors','skipped','tree_reaped','log_sha256')}))
raise SystemExit(0 if facts['passed'] else 1)
