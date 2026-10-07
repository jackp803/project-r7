"""Actual frozen Windows denial checks, not native Ubuntu service acceptance."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,sys
project=Path(__file__).resolve().parent.parent
repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.platform.distribution import verify_distribution
from application.platform.processes import ResourceLimits,spawn_owned
from application.qualification import revision_fact,_sanitize
package,output=map(Path,sys.argv[1:])
assert os.name=='nt' and output.is_absolute() and not output.exists()
assert output.resolve().is_relative_to(project/'artifacts')
identity=verify_distribution(package)
revision=identity['executable_revision']
revision_fact(repo,revision,True)
output.mkdir(mode=0o700)
cwd=output/'空白 工作目錄';cwd.mkdir()
config=output/'未讀取 中文 設定.json'
sentinel=b'Unsupported platform must reject without composing owners'
config.write_bytes(sentinel)
env={key:os.environ[key] for key in ('SystemRoot','WINDIR','SystemDrive','TEMP','TMP') if key in os.environ}
env.update(PATH='',PYTHONUTF8='1')
common=['--config',str(config),'--expected-revision',revision,'--expected-build-hash',identity['build_hash'],
    '--expected-config-hash','sha256:'+'a'*64,'--expected-memory-bytes','33736265728','--service-user','r7-worker']
commands=[];scenarios=[]
report=dict(identity=identity,passed=False,commands=commands,scenarios=scenarios,
    scope='Actual Windows frozen installer platform/commitment denial only; actual Ubuntu root/files/systemd NOT_RUN',
    native_ubuntu='NOT_RUN',systemd='NOT_RUN',credentials='NONE',capital='NONE',
    actual_provider_requests=0,runtime='NOT_STARTED',github_compute='NOT_USED',
    product_path='EMPTY',pythonpath='UNSET',node='UNAVAILABLE_ON_PATH')
stamp=lambda:datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
for name,arguments in [('install-dry',['install-services',*common]),
                       ('uninstall-dry',['uninstall-services',*common]),
                       ('install-apply',['install-services',*common,'--apply','--operation-hash','sha256:'+'d'*64]),
                       ('uninstall-apply',['uninstall-services',*common,'--apply','--operation-hash','sha256:'+'d'*64]),
                       ('invalid-commitment',['install-services',*common,'--apply','--operation-hash','INVALID'])]:
    log=output/(name+'.log');started=stamp()
    with log.open('xb') as stream:
        owned=spawn_owned([str(package/'R7.exe'),*arguments],cwd=cwd,
            limits=ResourceLimits(45),stdout=stream,stderr=-2,env=env)
        code=owned.wait()
    text=_sanitize(log.read_text(encoding='utf-8'),repo).replace('\r\n','\n')
    log.write_text(text,encoding='utf-8',newline='\n')
    passed=(code==2 and owned.termination_report.reaped and text.strip()=='R7: local configuration or startup validation failed'
        and config.read_bytes()==sentinel and not any(cwd.iterdir()) and not (output/'must-not-exist').exists())
    commands.append(dict(name=name,started_at_utc=started,finished_at_utc=stamp(),exit_code=code,expected_exit_code=2,
        tree_reaped=owned.termination_report.reaped,passed=passed,log=log.name,log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest()))
    scenarios.append(dict(name='unsupported-Windows-'+name+'-denied',passed=passed))
    (output/'native-installer-denial.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    if not passed:raise SystemExit(1)
assert {p.name for p in output.iterdir()}=={cwd.name,config.name,'install-dry.log','uninstall-dry.log','install-apply.log','uninstall-apply.log','invalid-commitment.log','native-installer-denial.json'}
revision_fact(repo,revision,True)
report['passed']=True
(output/'native-installer-denial.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(passed=True,scenarios=len(scenarios),commands=len(commands))))
