from pathlib import Path
import hashlib,json,os,re,sys
project=Path(__file__).resolve().parent.parent;repo=project/'workspaces/project-r7-productization-master-20261002'
base=project/'artifacts';dev=base/'S13-service-install-development'
sys.path.insert(0,str(repo/'src'))
import application.platform
application.platform.__path__.insert(0,str(dev/'src/application/platform'))
from application.platform.processes import ResourceLimits,spawn_owned
from application.qualification import _sanitize
if sys.argv[1]=='_execute_tests':
    import unittest
    suite=unittest.defaultTestLoader.discover(str(dev/'tests'),pattern='test_service_admin*.py')
    result=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(0 if result.wasSuccessful() else 1)
label=sys.argv[1];assert re.fullmatch('[A-Za-z0-9_-]+',label)
log=base/(label+'.log');assert not log.exists();raw=log.with_suffix('.raw')
env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
with raw.open('xb') as stream:
    owned=spawn_owned([sys.executable,str(Path(__file__)),'_execute_tests'],cwd=repo,limits=ResourceLimits(90),stdout=stream,stderr=-2,env=env)
    code=owned.wait()
text=_sanitize(raw.read_text(encoding='utf-8',errors='replace'),repo).replace('\r\n','\n');log.write_text(text,encoding='utf-8',newline='\n')
counts=re.search(r'Ran (\d+) tests?',text);assert counts
facts=dict(tests_run=int(counts[1]),exit_code=code,passed=code==0 and owned.termination_report.reaped,tree_reaped=owned.termination_report.reaped,
    log=log.name,log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest(),
    scope='OUTSIDE_GIT_FUTURE_INSTALLER_SIMULATED_BACKEND_ONLY;NOT_LINUX_SYSTEMD_ACCEPTANCE',native_ubuntu='NOT_RUN',actual_systemctl='NOT_RUN')
log.with_suffix('.json').write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(facts));raise SystemExit(code)
