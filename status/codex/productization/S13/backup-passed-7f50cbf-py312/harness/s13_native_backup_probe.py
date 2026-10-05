"""Actual fresh native/private snapshot verification; synthetic empty stores only."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib, json, os, socket, sqlite3, subprocess, sys, time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
project = Path(__file__).resolve().parent.parent
repo = project / 'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0, str(repo / 'src'))
from application.platform.distribution import verify_distribution
from application.platform.processes import ResourceLimits, spawn_owned, terminate_owned
from application.platform.supervision import config_hash
from application.config import load_config
package, output = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).absolute()
if output.exists() or not output.is_relative_to(project / 'artifacts') or output.is_relative_to(package):
    raise ValueError('Fresh bounded project artifact root required')
identity = verify_distribution(package)
executable = package / json.loads((package / 'distribution.json').read_bytes())['entrypoint']
output.mkdir()
cwd = output / '空白 工作 目錄'; cwd.mkdir()
profile, data, backup = output / '設定 空格.json', output / '本機 資料', output / '私密 備份'
with socket.socket() as probe:
    probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
env = {key: os.environ[key] for key in ('SystemRoot', 'WINDIR', 'SystemDrive', 'TEMP', 'TMP') if key in os.environ}
env.update(PATH='', PYTHONUTF8='1')
commands, scenarios = [], []
report = dict(profile='r7-native-private-database-backup-probe-v0.2', identity=identity,
    passed=False, commands=commands, scenarios=scenarios, input_class='FRESH_EMPTY_SYNTHETIC_LOCAL_RESEARCH',
    product_path='EMPTY', pythonpath='UNSET', actual_provider_requests=0, credentials='NONE', capital='NONE',
    runtime='NOT_STARTED', paper='NOT_STARTED', live='NOT_STARTED', cloud='NOT_CONNECTED', github_compute='NOT_USED',
    restore='NOT_PERFORMED', native_external_console_signal='NOT_RUN', ubuntu='NOT_RUN')
def stamp(): return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
def digest(raw): return 'sha256:' + hashlib.sha256(raw).hexdigest()
def persist():
    (output / 'native-database-backup.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n',encoding='utf-8',newline='\n')
def command(label, argv, expected=0):
    log=output/(label+'.log'); started=stamp()
    with log.open('wb') as stream:
        owned=spawn_owned([str(executable),*argv],cwd=cwd,limits=ResourceLimits(45),stdout=stream,stderr=subprocess.STDOUT,env=env)
        code=owned.wait()
    row=dict(name=label,arguments=argv,started_at_utc=started,finished_at_utc=stamp(),exit_code=code,
        expected_exit_code=expected,tree_reaped=owned.termination_report.reaped,log=log.name,
        log_sha256=digest(log.read_bytes()),passed=code==expected and owned.termination_report.reaped)
    commands.append(row);persist();assert row['passed'],label
    return json.loads(log.read_bytes()) if expected==0 else None
def files(): return {path.name:digest(path.read_bytes()) for path in backup.iterdir()}
try:
    initialized=command('01-init-profile',['init-profile','--config',str(profile),'--data-root',str(data),
        '--instance-id','native-database-backup-fixture','--port',str(port)])
    assert initialized['runtime']=='NOT_STARTED'
    report['config_hash']=config_hash(load_config(profile))
    log=output/'02-active-control.log'; started=stamp(); succeeded=False
    with log.open('wb') as stream:
        owned=spawn_owned([str(executable),'serve','--config',str(profile)],cwd=cwd,limits=ResourceLimits(90),
            stdout=stream,stderr=subprocess.STDOUT,env=env)
        try:
            deadline=time.monotonic()+35
            while True:
                assert owned.process.poll() is None,'Native server exited before readiness'
                try:
                    with urlopen(f'http://127.0.0.1:{port}/api/v1/auth/status',timeout=2) as response:
                        auth=json.loads(response.read(65536));break
                except URLError:
                    if time.monotonic()>=deadline:raise ValueError('Native server readiness deadline')
                    time.sleep(0.1)
            assert auth==dict(configured=False,namespace='LOCAL_RESEARCH',enrollment='LOCAL_CLI_ONLY')
            report['auth_status']=auth
            command('03-active-owner-backup-denied',['backup-databases','--config',str(profile),'--destination',str(backup)],expected=2)
            assert not backup.exists()
            scenarios.append(dict(name='ACTUAL_RUNNING_NATIVE_CONTROL_EXCLUDES_BACKUP',passed=True))
            succeeded=True
        finally:
            termination=terminate_owned(owned,deadline_seconds=5)
            stream.flush()
            commands.append(dict(name='02-active-control',started_at_utc=started,finished_at_utc=stamp(),
                exit_code=owned.process.returncode,tree_reaped=termination.reaped,termination_reason=termination.reason,
                log=log.name,log_sha256=digest(log.read_bytes()),passed=succeeded and termination.reaped,
                stop='OWNED_TREE_TERMINATION_NOT_COOPERATIVE_SIGNAL_QUALIFICATION'))
            persist()
        assert succeeded and termination.reaped
    result=command('04-stopped-private-backup',['backup-databases','--config',str(profile),'--destination',str(backup)])
    assert result['database_count']==4 and result['data_class']=='PRIVATE_LOCAL' and result['cloud_publication']=='FORBIDDEN'
    assert result['financial_authority']=='NONE' and result['restore']=='NOT_PERFORMED'
    manifest=json.loads((backup/'manifest.json').read_bytes())
    assert manifest['source_provenance']['build_hash']==identity['build_hash']
    assert manifest['source_provenance']['worktree']=='UNAVAILABLE'
    report['snapshot_summary']=dict(result,manifest_sha256=digest((backup/'manifest.json').read_bytes()),
        logical_stores=sorted(row['logical_name'] for row in manifest['databases']),
        original_private_database_artifacts='LOCAL_ONLY_NOT_RETAINED_IN_GIT')
    scenarios.append(dict(name='ACTUAL_NATIVE_PRIVATE_FOUR_DATABASE_SNAPSHOT',passed=True))
    before=files()
    verified=command('05-read-only-verify',['verify-database-backup','--config',str(profile),'--destination',str(backup)])
    assert verified==result and files()==before
    scenarios.append(dict(name='NATIVE_READ_ONLY_VERIFICATION_PRESERVES_EVERY_ARTIFACT',passed=True))
    command('06-existing-backup-preserved',['backup-databases','--config',str(profile),'--destination',str(backup)],expected=2)
    assert files()==before
    scenarios.append(dict(name='NATIVE_EXISTING_DESTINATION_REJECTED_AND_PRESERVED',passed=True))
    with closing(sqlite3.connect(backup/'canonical.sqlite')) as db:
        db.execute('CREATE TABLE synthetic_tamper_probe(value TEXT)');db.commit()
    changed=files()
    command('07-tampered-backup-denied',['verify-database-backup','--config',str(profile),'--destination',str(backup)],expected=2)
    assert files()==changed
    scenarios.append(dict(name='NATIVE_CHANGED_BACKUP_REJECTED_WITHOUT_REPAIR_OR_RESTORE',passed=True))
    report.update(passed=all(row['passed'] and row['tree_reaped'] for row in commands),scenario_count=len(scenarios))
    assert len(commands)==7 and len(scenarios)==5 and report['passed']
except BaseException as error:
    report.update(passed=False,failure_class=type(error).__name__)
    raise
finally:
    persist()
print(json.dumps(dict(passed=report['passed'],scenarios=len(scenarios),commands=len(commands),build_hash=identity['build_hash'])))
