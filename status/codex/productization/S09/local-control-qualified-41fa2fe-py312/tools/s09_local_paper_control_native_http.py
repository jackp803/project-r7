"""Actual packaged authenticated PAPER inventory; synthetic fresh local auth only."""
from pathlib import Path
import http.cookiejar,json,os,socket,subprocess,sys,time
from urllib.error import HTTPError,URLError
from urllib.request import Request,build_opener,HTTPCookieProcessor,ProxyHandler
from s09_owner_worker_native_regression import OwnedProof,sha,stamp,REPO,BASE,PROJECT
from application.config import load_config
from application.control_api.auth import LocalAuth
from application.platform.distribution import verify_distribution
from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned
from application.platform.supervision import _local_path
from application.qualification import revision_fact,_sanitize
from application.datasets.catalog import read_local
from application.cloud.safe_files import _windows_read,_posix_read
from application.platform._loopback_probe import NoRedirect
from s13_native_access_integrity import require_owned_generation

REVISION='41fa2fe0d74435fed5831ed728af8b87c28883f0'

def read_input(path,limit):
    if path==REPO/'src/application/platform/_loopback_probe.py':
        _local_path(path)
        return (_windows_read if os.name=='nt' else _posix_read)(path,limit)
    return read_local(path.parent,path.name,limit)

def main():
    package=Path(sys.argv[1]);output=Path(sys.argv[2])
    assert output==BASE/f'r7-native-S09-local-control-reader-{REVISION[:7]}'
    _local_path(output);assert not os.path.lexists(output);output.mkdir()
    identity=verify_distribution(package);assert identity['executable_revision']==REVISION
    before=revision_fact(REPO,REVISION,True)
    inputs=[Path(__file__),BASE/'s09_owner_worker_native_regression.py',REPO/'src/application/local_owners.py',
        REPO/'src/application/control_api/paper_ports.py',REPO/'src/application/entrypoints.py',
        REPO/'src/application/control_api/auth.py',REPO/'src/application/control_api/app.py']
    inputs.extend([BASE/'s13_native_access_integrity.py',REPO/'src/application/platform/_loopback_probe.py'])
    def capture():return {path.relative_to(PROJECT).as_posix():sha(read_input(path,8*1024**2)) for path in inputs}
    captured=capture();config=output/'設定 空格.json';data=output/'本機 資料';cwd=output/'空白 工作';cwd.mkdir()
    with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    exe=package/'R7.exe'
    env={key:os.environ[key] for key in ('SystemRoot','WINDIR','SystemDrive','TEMP','TMP') if key in os.environ}
    env.update(PATH='',PYTHONUTF8='1')
    value=dict(passed=False,identity=identity,source_before=before,input_hashes_before=captured,commands=[],scenarios=[],
        auth_origin='SOURCE_CREATED_NEW_SYNTHETIC_LOCAL_AUTH_FIXTURE;NOT_NATIVE_CLI_ENROLLMENT',
        namespace='LOCAL_RESEARCH',native_path='EMPTY',native_pythonpath='UNSET',
        provider_requests=0,real_credentials='NONE',capital='NONE',github_compute='NOT_USED',
        native_worker_invoked=False,ordinary_native_paper='NOT_RUN',production_profile='PROPOSED_NOT_ACTIVE',ubuntu='NOT_RUN')
    with OwnedProof(output/'native-paper-reader.json') as proof:
        owned=None
        try:
            with OwnedProof(output/'01-native-profile.log') as log:
                started=stamp();owned=spawn_owned([str(exe),'init-profile','--config',str(config),'--data-root',str(data),
                    '--instance-id','native-reader-fixture','--port',str(port)],cwd=cwd,limits=ResourceLimits(60),
                    stdout=log.stream,stderr=subprocess.STDOUT,env=env)
                code=owned.wait();cleanup=terminate_owned(owned,deadline_seconds=5)
                log.require_owned();log.stream.seek(0);raw=log.stream.read(1024**2+1)
                assert len(raw)<=1024**2 and code==0 and cleanup.reaped
                result=json.loads(raw);assert result['status']=='PROFILE_CREATED' and result['runtime']=='NOT_STARTED'
                sanitized=_sanitize(raw.decode('utf-8'),REPO).replace('\r\n','\n').encode()
                log.stream.seek(0);log.stream.write(sanitized);log.stream.truncate();log.stream.flush();log.require_owned()
                value['commands'].append(dict(name='native-profile',started_at_utc=started,finished_at_utc=stamp(),
                    exit_code=code,tree_reaped=cleanup.reaped,passed=True,log='01-native-profile.log',log_sha256=sha(sanitized)))
            assert capture()==captured and verify_distribution(package)==identity
            settings=load_config(config)
            assert settings.diagnostic_only and not settings.paper_runtime_enabled
            # Construct only a new isolated qualification fixture identity. Never
            # inspect a user's existing auth store or persist cookies/grant bytes.
            password='SYNTHETIC-native-reader-password-only'
            LocalAuth(data/'local-auth.sqlite',namespace='LOCAL_RESEARCH').create_owner('fixture-native-reader',password)
            opener=build_opener(ProxyHandler({}),NoRedirect(),HTTPCookieProcessor(http.cookiejar.CookieJar()));url=f'http://127.0.0.1:{port}'
            generation=None
            def request(path,payload=None,csrf=None,expected=200):
                if generation is None:
                    assert path=='/api/v1/auth/status' and payload is None
                else:
                    require_owned_generation(owned,config,identity,generation)
                headers={} if payload is None else {'Content-Type':'application/json','Origin':url}
                if csrf is not None:headers['X-R7-CSRF']=csrf
                data_bytes=None if payload is None else json.dumps(payload).encode()
                req=Request(url+path,data=data_bytes,headers=headers)
                try:
                    response=opener.open(req,timeout=3)
                except HTTPError as error:response=error
                with response:
                    assert response.status==expected
                    raw=response.read(1024**2+1);assert len(raw)<=1024**2
                    result=json.loads(raw)
                if generation is not None:require_owned_generation(owned,config,identity,generation)
                return result
            succeeded=False
            with OwnedProof(output/'02-native-control.log') as log:
                started=stamp();owned=spawn_owned([str(exe),'serve','--config',str(config)],cwd=cwd,
                    limits=ResourceLimits(120),stdout=log.stream,stderr=subprocess.STDOUT,env=env)
                try:
                    deadline=time.monotonic()+20
                    while True:
                        try:
                            status=request('/api/v1/auth/status');break
                        except (URLError,TimeoutError):
                            if time.monotonic()>=deadline:raise
                            time.sleep(.05)
                    assert status['configured'] is True and status['namespace']=='LOCAL_RESEARCH'
                    generation=require_owned_generation(owned,config,identity)
                    value['native_control_generation']=generation
                    login=request('/api/v1/auth/login',dict(username='fixture-native-reader',password=password,
                        command_id='native-reader-login',expected_revision=0))
                    csrf=login['csrf_token']
                    inventory=request('/api/v1/paper/runs')
                    assert inventory['metadata']['namespace']=='LOCAL_RESEARCH'
                    assert inventory['data']['status']=='AVAILABLE' and inventory['data']['items']==[]
                    value['scenarios'].append(dict(name='native-authenticated-real-empty-paper-inventory',passed=True))
                    denial=request('/api/v1/paper/runs',dict(command_id='native-reader-no-start',expected_revision=0,
                        strategy_id='missing',strategy_version='1',policy_id='unselected'),csrf,503)
                    assert denial['error']['reason_codes']==['OWNER_NOT_CONFIGURED']
                    health=request('/api/v1/health')['data']
                    assert health['runtime']=='NOT_CONFIGURED' and health['live_authorized'] is False
                    value['scenarios'].append(dict(name='native-unselected-paper-start-denied-without-runtime-authority',passed=True))
                    require_owned_generation(owned,config,identity,generation)
                    succeeded=True
                finally:
                    cleanup=terminate_owned(owned,deadline_seconds=5);log.require_owned()
                    log.stream.seek(0);raw=log.stream.read(4*1024**2+1);assert len(raw)<=4*1024**2
                    sanitized=_sanitize(raw.decode('utf-8',errors='replace'),REPO).replace('\r\n','\n').encode()
                    log.stream.seek(0);log.stream.write(sanitized);log.stream.truncate();log.stream.flush();log.require_owned()
                    value['commands'].append(dict(name='native-control',started_at_utc=started,finished_at_utc=stamp(),
                        exit_code=owned.process.returncode,termination_reason=cleanup.reason,tree_reaped=cleanup.reaped,
                        passed=succeeded and cleanup.reaped,log='02-native-control.log',log_sha256=sha(sanitized),
                        termination_scope='OWNED_KERNEL_STOP_OF_ISOLATED_NONTRADING_CONTROL;NO_MANAGED_STOP_CLAIM'))
            assert succeeded and cleanup.reaped and capture()==captured and verify_distribution(package)==identity
            value.update(passed=True,source_after=revision_fact(REPO,REVISION,True),input_hashes_after=capture(),
                scenario_count=2,command_count=2)
            assert value['source_after']==before
        except BaseException as error:
            value.update(passed=False,failure_class=type(error).__name__)
            raise
        finally:
            if owned is not None:assert terminate_owned(owned,deadline_seconds=5).reaped
            proof.persist(value)
    print(json.dumps(dict(passed=True,scenarios=2,commands=2,ordinary_native_paper='NOT_RUN')),flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
