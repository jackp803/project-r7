from pathlib import Path
from dataclasses import asdict
import hashlib,json,os,subprocess,sys
BASE=Path(__file__).resolve().parent;REPO=BASE.parents[1]/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(REPO/'src'))
from application.platform.processes import spawn_owned,ResourceLimits
from application.qualification import parse_result,_sanitize
mode=sys.argv[1]
if mode=='application':
    modules=('test_native_paper_release_observation','test_native_paper_release_adapter','test_ordinary_paper_setup',
        'test_ordinary_paper_composition','test_paper_owner_worker','test_paper_owner_composition',
        'test_paper_selection_recovery','test_paper_release_selection','test_private_long_paths',
        'test_process_tree','test_managed_stop','test_native_entrypoints','test_product_assessment_binding')
    args=['-m','unittest','-v',*['tests.application.'+name for name in modules]]
elif mode=='registry':args=['-m','unittest','discover','-s','tests/registry','-p','test_*.py','-v']
else:raise ValueError('Fixed bounded regression only')
out=BASE/('native-observation-regression-'+mode);out.mkdir(exist_ok=False)
env=os.environ.copy();env.update(PYTHONPATH=str(REPO/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
with (out/'owned.raw').open('xb') as stream:
    owned=spawn_owned([sys.executable,'-X','utf8',*args],cwd=REPO,limits=ResourceLimits(300),stdout=stream,stderr=subprocess.STDOUT,env=env)
    code=owned.wait()
raw=(out/'owned.raw').read_text(encoding='utf-8',errors='replace')
log=_sanitize(raw,REPO).replace(str(REPO.parents[1]),'<PROJECT_ROOT>')
(out/'owned.log').write_text(log,encoding='utf-8',newline='\n');(out/'owned.raw').unlink()
record=dict(**asdict(parse_result(raw,returncode=code)),tree_reaped=owned.termination_report.reaped,
    scope='DIRTY_AFFECTED_SOURCE_NOT_NATIVE_QUALIFICATION',mode=mode,
    tool_hash='sha256:'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    log_hash='sha256:'+hashlib.sha256(log.encode()).hexdigest())
(out/'result.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(record));raise SystemExit(0 if record['passed'] and record['tree_reaped'] else 2)
