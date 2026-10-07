"""Actual frozen Windows public access facts; no SSH connection or credentials."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,socket,sys,time
from urllib.error import URLError
from urllib.request import Request
project=Path(__file__).resolve().parent.parent
repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.platform.distribution import verify_distribution
from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned
from application.qualification import revision_fact,_sanitize
from s13_native_access_integrity import build_loopback_opener,require_owned_generation
package,output=map(Path,sys.argv[1:]);assert os.name=='nt' and output.is_absolute() and not output.exists()
assert output.resolve().is_relative_to(project/'artifacts')
identity=verify_distribution(package);revision=identity['executable_revision'];revision_fact(repo,revision,True)
output.mkdir(mode=0o700);cwd=output/'空白 中文 工作目錄';cwd.mkdir()
config=output/'公開端點 中文 設定.json';data=output/'私人 本機 資料'
with socket.socket() as probe:
    probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
executable=package/'R7.exe'
env={key:os.environ[key] for key in ('SystemRoot','WINDIR','SystemDrive','TEMP','TMP') if key in os.environ}
env.update(PATH='',PYTHONUTF8='1')
commands=[];scenarios=[]
report=dict(identity=identity,passed=False,commands=commands,scenarios=scenarios,product_path='EMPTY',pythonpath='UNSET',
    actual_provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',ssh_connection='NOT_STARTED',
    real_tunnel='NOT_RUN',ubuntu='NOT_RUN',runtime='NOT_STARTED',paper='NOT_STARTED',financial_authority='NONE',
    scope='ACTUAL_WINDOWS_NATIVE_PUBLIC_LOOPBACK_STATUS_AND_SSH_ARGV_ONLY')
stamp=lambda:datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
digest=lambda path:'sha256:'+hashlib.sha256(path.read_bytes()).hexdigest()
def persist():
    report.update(command_count=len(commands),scenario_count=len(scenarios))
    (output/'native-ssh-access.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
def command(name,argv,*,expected=0,environment=None):
    revision_fact(repo,revision,True);log=output/(name+'.log');started=stamp()
    with log.open('xb') as stream:
        owned=spawn_owned([str(executable),*argv],cwd=cwd,limits=ResourceLimits(30),stdout=stream,stderr=-2,env=environment or env)
        code=owned.wait()
    text=_sanitize(log.read_text(encoding='utf-8'),repo).replace('\r\n','\n');log.write_text(text,encoding='utf-8',newline='\n')
    passed=code==expected and owned.termination_report.reaped
    record=dict(name=name,started_at_utc=started,finished_at_utc=stamp(),exit_code=code,expected_exit_code=expected,
        tree_reaped=owned.termination_report.reaped,passed=passed,log=log.name,log_sha256=digest(log))
    commands.append(record);persist()
    if not passed:raise ValueError('Actual native access command failed')
    return text,record
def result(name,argv,*,expected=0,environment=None):
    text,record=command(name,argv,expected=expected,environment=environment)
    value=json.loads(text);record['result']=value;persist();return value
def scenario(name):
    scenarios.append(dict(name=name,result='PASS'));persist()
try:
    plan=result('plan-hostname',['plan-ssh-tunnel','--host','r7.example.test','--username','operator','--port',str(port)])
    assert plan['argv']==['ssh','-N','-T','-a','-F','none','-o','ExitOnForwardFailure=yes','-o','GatewayPorts=no',
        '-o','StrictHostKeyChecking=yes','-p','22','-l','operator','-L',f'127.0.0.1:{port}:127.0.0.1:{port}','r7.example.test']
    assert plan['status']=='PLANNED_ONLY' and plan['ssh_connection']=='NOT_STARTED' and plan['credentials']=='NOT_READ'
    scenario('NATIVE_LITERAL_LOOPBACK_SSH_PLAN_WITHOUT_CONNECTION')
    ipv6=result('plan-ipv6',['plan-ssh-tunnel','--host','2001:db8::7','--username','operator','--port',str(port)])
    assert ipv6['argv'][-1]=='2001:db8::7' and ipv6['ssh_connection']=='NOT_STARTED'
    scenario('NATIVE_CANONICAL_IPV6_DESTINATION_PLAN')
    for name,args in [('invalid-host',['--host','host;injection','--username','operator']),('invalid-root',['--host','r7.example.test','--username','root'])]:
        text,_=command(name,['plan-ssh-tunnel',*args],expected=2)
        assert text.strip()=='R7: local configuration or startup validation failed' and not any(cwd.iterdir())
        scenario('NATIVE_'+name.upper().replace('-','_')+'_DENIED')
    created=result('init-profile',['init-profile','--config',str(config),'--data-root',str(data),'--instance-id','native-public-access-fixture','--port',str(port)])
    assert created['status']=='PROFILE_CREATED' and not data.exists()
    raw=json.loads(config.read_bytes());assert raw['diagnostic_only'] and not raw['paper_runtime_enabled']
    scenario('NATIVE_PUBLIC_PROFILE_HAS_NO_TRADING_OR_AUTH_ENROLLMENT')
    unavailable=result('unavailable-before-start',['probe-control-access','--port',str(port)],expected=2)
    assert unavailable['status']=='UNAVAILABLE' and unavailable['reason_code']=='PUBLIC_STATUS_UNAVAILABLE' and unavailable['tree_reaped']
    scenario('NATIVE_MISSING_PUBLIC_ENDPOINT_DENIED_AND_CHILD_REAPED')
    log=output/'control-owner.log';started=stamp();success=False
    with log.open('xb') as stream:
        owner=spawn_owned([str(executable),'serve','--config',str(config)],cwd=cwd,limits=ResourceLimits(90),stdout=stream,stderr=-2,env=env)
        try:
            opener=build_loopback_opener();deadline=time.monotonic()+30
            while True:
                if owner.process.poll() is not None:raise ValueError('Actual native control exited before readiness')
                try:
                    with opener.open(Request(f'http://127.0.0.1:{port}/api/v1/auth/status'),timeout=1) as response:
                        assert json.loads(response.read(2049))==dict(configured=False,namespace='LOCAL_RESEARCH',enrollment='LOCAL_CLI_ONLY')
                    break
                except URLError:
                    if time.monotonic()>=deadline:raise ValueError('Actual native endpoint startup deadline') from None
                    time.sleep(.1)
            generation=require_owned_generation(owner,config,identity)
            report['control_generation_before']=generation;persist()
            observed=result('public-probe',['probe-control-access','--port',str(port),'--expected-namespace','LOCAL_RESEARCH'])
            require_owned_generation(owner,config,identity,generation)
            assert observed['status']=='PUBLIC_AUTH_STATUS_AVAILABLE' and observed['tree_reaped'] and observed['child_exit_code']==0
            assert observed['public_auth_status']==dict(configured=False,namespace='LOCAL_RESEARCH',enrollment='LOCAL_CLI_ONLY')
            assert observed['tunnel_provenance']=='UNVERIFIED_LOCAL_ENDPOINT_ONLY' and observed['credentials']=='NONE' and observed['actual_provider_requests']==0
            scenario('ACTUAL_NATIVE_PARENT_AND_FROZEN_CHILD_READ_ACTUAL_PUBLIC_ENDPOINT')
            wrong=result('wrong-namespace',['probe-control-access','--port',str(port),'--expected-namespace','FIXTURE'],expected=2)
            require_owned_generation(owner,config,identity,generation)
            assert wrong['reason_code']=='PUBLIC_STATUS_INVALID' and wrong['tree_reaped'] and 'public_auth_status' not in wrong
            scenario('NATIVE_PUBLIC_NAMESPACE_MISMATCH_DENIED')
            proxy=dict(env,http_proxy='http://192.0.2.99:9',HTTP_PROXY='http://192.0.2.99:9',NO_PROXY='')
            ignored=result('proxy-ignored',['probe-control-access','--port',str(port)],environment=proxy)
            report['control_generation_after']=require_owned_generation(owner,config,identity,generation);persist()
            assert ignored['status']=='PUBLIC_AUTH_STATUS_AVAILABLE' and ignored['tree_reaped']
            scenario('NATIVE_PUBLIC_PROBE_IGNORES_ENVIRONMENT_PROXY')
            success=owner.process.poll() is None
        finally:
            termination=terminate_owned(owner,deadline_seconds=5);stream.flush()
            text=_sanitize(log.read_text(encoding='utf-8'),repo).replace('\r\n','\n');log.write_text(text,encoding='utf-8',newline='\n')
            commands.append(dict(name='control-owner',started_at_utc=started,finished_at_utc=stamp(),tree_reaped=termination.reaped,
                exit_code=owner.process.returncode,termination_reason=termination.reason,passed=success and termination.reaped,
                log=log.name,log_sha256=digest(log)));persist()
    assert termination.reaped and success
    scenario('ACTUAL_NATIVE_CONTROL_OWNER_TREE_REAPED_WITHOUT_SSH_CONNECTION')
    assert config.is_file() and verify_distribution(package)==identity
    assert len(commands)==len(scenarios)==10 and all(c['passed'] for c in commands)
    revision_fact(repo,revision,True);report['passed']=True;persist()
    print(json.dumps(dict(passed=True,commands=len(commands),scenarios=len(scenarios))))
except Exception:
    report.update(passed=False,failure='NATIVE_PUBLIC_ACCESS_QUALIFICATION_FAILED');persist();raise
