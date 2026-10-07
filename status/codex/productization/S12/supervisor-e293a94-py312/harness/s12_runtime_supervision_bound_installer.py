"""Exact native Windows denials with before/after harness and package binding."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,sys
base=Path(__file__).resolve().parent;repo=base.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.qualification import revision_fact,_sanitize
from application.platform.processes import ResourceLimits,spawn_owned
from application.platform.distribution import verify_distribution
revision=sys.argv[1];assert re.fullmatch('[0-9a-f]{40}',revision)
short=revision[:7];package=base/f'r7-native-windows-S12-runtime-supervision-{short}/dist/R7'
output=base/f'r7-native-S12-runtime-supervision-installer-{short}'
revision_fact(repo,revision,True);identity=verify_distribution(package);assert identity['executable_revision']==revision
report_path=base/f'S12-runtime-supervision-bound-installer-{short}.json';log=report_path.with_suffix('.log')
assert not log.exists() and not report_path.exists()
stamp=lambda:datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
names=('s13_native_installer_denial_v2.py','s13_installer_package_binding.py',Path(__file__).name)
hashes=lambda:{name:'sha256:'+hashlib.sha256((base/name).read_bytes()).hexdigest() for name in names}
before=hashes();started=stamp()
with log.open('xb') as stream:
 owned=spawn_owned([sys.executable,str(base/'s13_native_installer_denial_v2.py'),str(package),str(output)],cwd=repo,
  limits=ResourceLimits(300),stdout=stream,stderr=-2);code=owned.wait()
text=_sanitize(log.read_text(encoding='utf-8',errors='replace'),repo).replace('\r\n','\n');log.write_text(text,encoding='utf-8',newline='\n')
assert verify_distribution(package)==identity;revision_fact(repo,revision,True);assert before==hashes()
facts=dict(revision=revision,worktree='CLEAN',identity=identity,passed=code==0 and owned.termination_report.reaped,
 scope='ACTUAL_WINDOWS_DENIAL_ONLY;UBUNTU_INSTALLER_NOT_RUN',harness_binding='BEFORE_AND_AFTER_EXECUTION',harness_hashes=before,
 command=dict(started_at_utc=started,finished_at_utc=stamp(),exit_code=code,tree_reaped=owned.termination_report.reaped,
 log=log.name,log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest()))
report_path.write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(dict(passed=facts['passed'])));raise SystemExit(0 if facts['passed'] else (code or 1))
