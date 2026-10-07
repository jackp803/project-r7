from pathlib import Path
import hashlib,json,os,sys
base=Path(__file__).resolve().parent;repo=base.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.platform.processes import ResourceLimits,spawn_owned
from application.qualification import _sanitize,parse_result
label=sys.argv[1];assert __import__('re').fullmatch('[A-Za-z0-9_-]+',label)
log=base/(label+'.log');assert not log.exists();raw=log.with_suffix('.raw')
with raw.open('xb') as stream:
    owned=spawn_owned([sys.executable,'-m','unittest','-v','s13_installer_package_binding_tests'],cwd=base,limits=ResourceLimits(90),
        stdout=stream,stderr=-2,env=dict(os.environ,PYTHONPATH=str(repo/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'));code=owned.wait()
text=_sanitize(raw.read_text(encoding='utf-8',errors='replace'),repo).replace('\r\n','\n');log.write_text(text,encoding='utf-8',newline='\n');result=parse_result(text,returncode=code)
facts=dict(tests_run=result.tests_run,failures=result.failures,errors=result.errors,passed=result.passed and owned.termination_report.reaped,
    tree_reaped=owned.termination_report.reaped,scope='ACTUAL_SEALED_SYNTHETIC_PACKAGE_REPLACEMENT_AND_NATIVE_HARNESS_SOURCE_ORDER',
    log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest())
log.with_suffix('.json').write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(facts));raise SystemExit(code)
