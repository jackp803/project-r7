"""Bound the actual serial pipeline harnesses while testing their guard fragments."""
from pathlib import Path
import ast,hashlib,json,os,re,sys
base=Path(__file__).resolve().parent;repo=base.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.qualification import _sanitize,parse_result
from application.platform.processes import ResourceLimits,spawn_owned
label=sys.argv[1];assert re.fullmatch('[A-Za-z0-9_-]+',label)
tree=ast.parse((base/'s14_feedback_cli_candidate_pipeline.py').read_bytes())
pipeline_names=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign)
    and any(isinstance(target,ast.Name) and target.id=='names' for target in node.targets))
names=(*pipeline_names,Path(__file__).name,'test_s14_feedback_cli_qualification_integrity.py')
hashes=lambda:{name:'sha256:'+hashlib.sha256((base/name).read_bytes()).hexdigest() for name in names}
before=hashes();log=base/(label+'.log');assert not log.exists()
with log.open('xb') as stream:
    owned=spawn_owned([sys.executable,str(base/'test_s14_feedback_cli_qualification_integrity.py')],cwd=base,
        limits=ResourceLimits(30),stdout=stream,stderr=-2,
        env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
    code=owned.wait()
text=_sanitize(log.read_text(encoding='utf-8',errors='replace'),repo).replace('\r\n','\n')
log.write_text(text,encoding='utf-8',newline='\n');result=parse_result(text,returncode=code)
after=hashes()
facts=dict(tests_run=result.tests_run,failures=result.failures,errors=result.errors,skipped=result.skipped,
    passed=result.passed and result.tests_run==10 and owned.termination_report.reaped and before==after,
    tree_reaped=owned.termination_report.reaped,exit_code=code,harness_binding='BEFORE_AND_AFTER_EXECUTION',
    input_sha256_before=before,input_sha256_after=after,
    scope='QUALIFICATION_EXIT_AND_DEPENDENCY_HASH_GUARD_FRAGMENTS;CONTROLLED_CLEANUP_AND_REPLACEMENT;NO_PRODUCT_EXECUTION',
    log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest(),
    wrapper_sha256=before['s14_feedback_cli_bound_installer.py'])
log.with_suffix('.json').write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({key:facts[key] for key in ('tests_run','failures','errors','skipped','passed','tree_reaped','log_sha256')}))
raise SystemExit(0 if facts['passed'] else (code or 1))
