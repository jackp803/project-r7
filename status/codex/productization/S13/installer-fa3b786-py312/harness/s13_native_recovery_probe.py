"""Fresh synthetic native recovery acceptance; never real trading or credentials."""
from contextlib import closing
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib, json, os, socket, sqlite3, sys, time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPCookieProcessor, ProxyHandler, HTTPRedirectHandler
import http.cookiejar

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url,code,'NATIVE_QUALIFICATION_REDIRECT_DENIED',headers,fp)

project = Path(__file__).resolve().parent.parent
repo = project / 'workspaces/project-r7-productization-master-20261002'
sys.path[:0] = [str(repo), str(repo / 'src')]
from application.config import ProductConfig, load_config
from application.datasets.catalog import canonical, digest
from application.local_owners import LocalOwners
from application.platform.distribution import verify_distribution
from application.platform.private_files import create_private_directory, require_private
from application.platform.processes import ResourceLimits, spawn_owned, terminate_owned
from application.platform.scope_lock import ProcessScopeLock, operational_lock_root
from application.platform.supervision import config_hash
from application.platform.supervision import ProcessSupervisor
from application.qualification import _sanitize
from application.control_api.auth import LocalAuth, AuthenticationError
from application.control_api.commands import CommandLedger
from application.research.evidence import ResearchJournal
from application.intake.ledger import IntakeLedger, LeaseConflict
from application.research.queue import ResearchQueueError
from storage.product_dispatch import open_product_dispatch_journal, ProductDispatchError
from storage.paper_process import open_paper_process_journal
from storage.runtime_models import RuntimeConflictError
from tests.application.test_local_owner_composition import LocalOwnerCompositionTests
from tests.storage.test_product_dispatch_v02 import ProductDispatchV02Tests
from tests.storage.test_paper_process_journal import PaperProcessJournalTests

package, output = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).absolute()
if output.exists() or output.is_relative_to(repo) or not output.is_relative_to(project / 'artifacts'):
    raise ValueError('Fresh project artifact root required')
identity = verify_distribution(package)
executable = package / json.loads((package / 'distribution.json').read_bytes())['entrypoint']
create_private_directory(output)
stamp = lambda: datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
sha = lambda p: 'sha256:' + hashlib.sha256(p.read_bytes()).hexdigest()
report = dict(schema_version='r7-native-private-recovery-acceptance-v0.2', identity=identity,
    started_at_utc=stamp(), passed=False, commands=[], scenarios=[], http_assertions=[],
    fixture='SYNTHETIC_DATA_LOCAL_FOLDER_AND_E6_JOURNALS_ONLY', real_provider_requests=0,
    credentials='NONE', capital='NONE', trading_runtime='NOT_STARTED', paper='NOT_STARTED',
    live='NOT_STARTED', github_compute='NOT_USED', product_path='EMPTY', pythonpath='UNSET',
    limitations=['No OS service/reboot qualification', 'No restoration release/reconciliation authorization',
                 'No real cloud/Ubuntu/forward/provider acceptance'])
def persist():
    (output / 'native-recovery.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
def scenario(name):
    report['scenarios'].append(dict(name=name, result='PASS')); persist()
    print(name + ': PASS', flush=True)
env = {key: os.environ[key] for key in ('SystemRoot', 'WINDIR', 'SystemDrive', 'TEMP', 'TMP') if key in os.environ}
env.update(PATH='', PYTHONUTF8='1')
cwd = output / '空白 工作目錄'; create_private_directory(cwd)
def command(label, arguments, expected=0):
    log = output / (label + '.log'); started = stamp()
    with log.open('xb') as stream:
        handle = spawn_owned([str(executable), *map(str, arguments)], cwd=cwd,
            limits=ResourceLimits(90), stdout=stream, stderr=-2, env=env)
        code = handle.wait()
    raw = log.read_bytes(); text = raw.decode('utf-8', errors='strict')
    safe = _sanitize(text, repo).replace(str(output), '<PRIVATE_FIXTURE_ROOT>').replace(str(project), '<PROJECT_ROOT>')
    log.write_text(safe, encoding='utf-8', newline='\n')
    row = dict(name=label, started_at_utc=started, finished_at_utc=stamp(), exit_code=code,
        expected_exit_code=expected, tree_reaped=handle.termination_report.reaped,
        log=log.name, raw_log_sha256='sha256:' + hashlib.sha256(raw).hexdigest(), log_sha256=sha(log),
        passed=code == expected and handle.termination_report.reaped,
        private_paths_in_cli_stdout=str(output) in text or str(project) in text)
    report['commands'].append(row); persist()
    if not row['passed'] or row['private_paths_in_cli_stdout']:
        raise AssertionError('Native recovery command or sanitized output failed: ' + label)
    if expected:
        try: return json.loads(text)
        except json.JSONDecodeError: return dict(status='DENIED',exit_code=code)
    return json.loads(text)
def profile(path, config):
    path.write_text(json.dumps({k: str(v) if isinstance(v, Path) else v for k,v in asdict(config).items()}, ensure_ascii=False), encoding='utf-8')
    require_private(path)

case = LocalOwnerCompositionTests()
case.base = output
case.root, case.cloud = output / '原始 合成資料', output / '模擬 同步暫存'
create_private_directory(case.root); create_private_directory(case.cloud)
with socket.socket() as probe:
    probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
case.config = ProductConfig('r7-product-config-v0.2', 'native-recovery-synthetic', case.root,
    case.cloud, case.root / 'canonical.sqlite3', control_api_port=port)
case.selection = case.root / 'owner-selections.json'
case.clock = lambda: datetime.now(timezone.utc)
def compose():
    if case.config.database_path.exists(): raise ValueError('Fresh synthetic input conversion required')
    values = {}
    for name in ('dataset', 'split', 'cost', 'risk'):
        path = case.root / (name + '.json'); value = json.loads(path.read_bytes())
        value['namespace'] = 'LOCAL_RESEARCH'; path.write_text(canonical(value), encoding='utf-8'); values[name] = value
    for name in ('research', 'robustness'):
        path = case.root / (name + '.json'); value = json.loads(path.read_bytes())
        value.update(namespace='LOCAL_RESEARCH', split_policy_hash=digest(canonical(values['split']).encode()),
            cost_policy_hash=digest(canonical(values['cost']).encode()))
        path.write_text(canonical(value), encoding='utf-8')
    return LocalOwners(case.config, namespace='LOCAL_RESEARCH', clock=case.clock)
case.compose = compose
owner = None
try:
    owner = case.configured()
    with owner.inbox_factory() as inbox: assert inbox.scan_once(case.clock()).accepted == 1
    services = owner.control_services()
    services.execute('SETTINGS_UPDATE', 'settings', {'display_timezone':'UTC', 'scan_interval':45},
        actor='synthetic-owner', human=None, command_id='native-backup-settings', expected_revision=0)
    selection_rev = owner.queue.selected_submission_revision('native-owner-fixture','selected-fixture')
    job = owner.queue.enqueue('native-owner-fixture','selected-fixture','native-backup-pending',selection_rev,actor='synthetic-owner')
    queue_claim = owner.queue.claim_next(); assert queue_claim.run_id == job['run_id']
    with owner.intake_factory() as intake:
        intake_claim = intake.claim('pending-native-fixture','sha256:'+'a'*64,'old-intake-owner',case.clock())
    auth = LocalAuth(case.root / 'local-auth.sqlite', namespace='LOCAL_RESEARCH', clock=case.clock)
    auth.create_owner('fixture-owner','synthetic-native-restore-password')
    old_session = auth.login('fixture-owner','synthetic-native-restore-password',command_id='old-native-login',expected_revision=0)
    CommandLedger(case.root/'control-commands.sqlite',namespace='LOCAL_RESEARCH',clock=case.clock)
    with ResearchJournal(case.root/'research.sqlite'):
        pass
    with ProcessSupervisor(case.config,'control',heartbeat_interval=0.02):
        pass
    now = case.clock(); dispatch_fixture = ProductDispatchV02Tests(); dispatch_fixture.now = now
    with open_product_dispatch_journal(case.config.database_path) as journal:
        journal.ensure_run('dispatch-fixture',dispatch_fixture.permission(),now=now)
        dispatch_lease = journal.begin_process('dispatch-fixture','old-native-process',expected_generation=0,now=now)
        journal.prepare('dispatch-fixture','uncertain-fixture',dispatch_fixture.request(),lease=dispatch_lease,now=now)
        assert journal.claim_dispatch('dispatch-fixture','uncertain-fixture',lease=dispatch_lease,now=now)
    paper_fixture = PaperProcessJournalTests()
    with open_paper_process_journal(case.config.database_path) as journal:
        journal.create_run('paper-fixture',paper_fixture.binding(),paper_fixture.state(),now=now)
        assert journal.begin_process('paper-fixture','old-fixture-paper',expected_generation=0,now=now) == 1
        paper_state = journal.recover('paper-fixture').state
    source_profile = output / '原始 設定.json'; profile(source_profile,case.config)
    report['source_config_hash'] = config_hash(case.config)
    source_files = {p.relative_to(case.root).as_posix():sha(p) for p in case.root.rglob('*') if p.is_file()
        and p.relative_to(case.root).parts[0] not in ('worker-logs','process-scopes')
        and p.suffix not in ('.sqlite','.sqlite3') and not p.name.endswith(('-wal','-shm'))}
    backup, target = output / '完整 私密備份', output / '新 還原世代'
    backed = command('01-backup-product-data',['backup-product-data','--config',source_profile,'--destination',backup])
    assert backed['status'] == 'PRODUCT_DATA_BACKUP_VERIFIED' and backed['coverage'] == 'COMPLETE_SUPPORTED_LOCAL_PROFILE'
    db_manifest = json.loads((backup/'databases/manifest.json').read_bytes())
    assert len(db_manifest['databases']) == 8 and 'settings' in {r['logical_name'] for r in db_manifest['databases']}
    scenario('NATIVE_COMPLETE_EIGHT_STORE_AND_SELECTED_FILE_BACKUP')
    verified = command('02-verify-product-backup',['verify-product-backup','--config',source_profile,'--destination',backup])
    assert verified['status'] == 'PRODUCT_DATA_BACKUP_VERIFIED'
    scenario('NATIVE_PRIVATE_BUNDLE_VERIFICATION')
    restored = command('03-restore-product-data',['restore-product-data','--config',source_profile,'--backup',backup,'--destination',target])
    assert restored['status'] == 'PRODUCT_DATA_RESTORE_STAGED' and restored['runtime_new_exposure'] == 'INHIBITED'
    new_config = load_config(target/'restored-product.json')
    assert new_config.cloud_root is None and new_config.diagnostic_only and not new_config.paper_runtime_enabled
    report['restored_config_hash'] = config_hash(new_config)
    for relative, expected in source_files.items():
        assert sha(target/relative) == expected == sha(case.root/relative); require_private(target/relative)
    for p in target.rglob('*'):
        if p.is_file(): require_private(p)
    require_private(target,directory=True)
    scenario('NATIVE_FRESH_INHIBITED_RESTORE_PRIVATE_ACL_AND_BYTE_PRESERVATION')
    reopened = LocalOwners(new_config,namespace='LOCAL_RESEARCH',clock=case.clock)
    assert reopened.inbox_factory is None and reopened.control_services().settings()['display_timezone'] == 'UTC'
    assert reopened.resolver.manifest_view('native-owner-fixture')['submission_id'] == 'native-owner-fixture'
    with reopened.intake_factory() as intake:
        assert intake.accepted_receipt('native-owner-fixture') is not None
        try: intake.commit_effect(intake_claim,'forbidden-stale',b'{}',now=case.clock())
        except LeaseConflict: pass
        else: raise AssertionError('Copied intake lease remained active')
    assert reopened.queue.get(queue_claim.run_id)['state'] == 'FAILED'
    assert reopened.queue.claim_next() is None
    try: reopened.queue._checkpoint(queue_claim.run_id,queue_claim.generation,'forbidden-stale','development')
    except ResearchQueueError: pass
    else: raise AssertionError('Copied queue lease remained active')
    assert owner.queue.get(queue_claim.run_id)['state'] == 'RUNNING'
    assert auth.authenticate(old_session.token) is not None
    scenario('RESTORED_SELECTED_SNAPSHOT_SETTINGS_AND_APPLICATION_LEASE_FENCES')
    with open_product_dispatch_journal(new_config.database_path) as journal:
        assert journal.recover('dispatch-fixture').process_generation == 2
        assert journal.operation('dispatch-fixture','uncertain-fixture').recovery_disposition == 'READBACK_REQUIRED'
        try: journal.prepare('dispatch-fixture','forbidden-old-lease',dispatch_fixture.request('r7other'),lease=dispatch_lease,now=case.clock())
        except ProductDispatchError: pass
        else: raise AssertionError('Copied E6 lease remained active')
    with open_paper_process_journal(new_config.database_path) as journal:
        recovery = journal.recover('paper-fixture'); assert recovery.process_generation == 2 and recovery.state == paper_state
        try: journal.prepare('paper-fixture','forbidden-old-generation',{'kind':'SYNTHETIC'},expected_revision=0,now=case.clock(),process_generation=1)
        except RuntimeConflictError: pass
        else: raise AssertionError('Copied PAPER generation remained active')
    with open_product_dispatch_journal(case.config.database_path) as journal:
        assert journal.recover('dispatch-fixture').process_generation == 1
    scenario('E6_UNCERTAINTY_AND_PAPER_STATE_PRESERVED_WITH_NEW_PROCESS_GENERATIONS')
    command('04-existing-generation-denied',['restore-product-data','--config',source_profile,'--backup',backup,'--destination',target],2)
    scenario('EXISTING_RESTORATION_GENERATION_PRESERVED')
    narrow_backup, narrow_target = output/'七個資料庫 備份', output/'僅資料庫 還原'
    command('04a-backup-databases',['backup-databases','--config',source_profile,'--destination',narrow_backup])
    command('04b-verify-databases',['verify-database-backup','--config',source_profile,'--destination',narrow_backup])
    narrow=command('04c-restore-databases',['restore-databases','--config',source_profile,'--backup',narrow_backup,'--destination',narrow_target])
    assert narrow['scope'] == 'DATABASES_ONLY' and narrow['user_data_restore'] == 'PENDING' and narrow['database_count'] == 7
    assert narrow['runtime_new_exposure'] == 'INHIBITED'
    assert not (narrow_target/'dataset.json').exists()
    scenario('LEGACY_SEVEN_STORE_NATIVE_RECOVERY_REMAINS_EXPLICITLY_INCOMPLETE')
    blocked_target = output/'active-owner-target'
    with ProcessScopeLock('runtime:'+case.config.product_instance_id,lock_root=operational_lock_root(case.config)):
        command('05-active-owner-denied',['restore-product-data','--config',source_profile,'--backup',backup,'--destination',blocked_target],2)
    assert not blocked_target.exists()
    scenario('ACTIVE_RUNTIME_OWNER_BLOCKS_RESTORATION')
    # Each actual native control restart must retain inhibition and reject the copied cookie.
    for number in (1,2):
        log = output/f'06-control-restart-{number}.log'; started = stamp(); assertions=[]
        with log.open('xb') as stream:
            handle = spawn_owned([str(executable),'serve','--config',str(target/'restored-product.json')],cwd=cwd,
                limits=ResourceLimits(90),stdout=stream,stderr=-2,env=env)
            succeeded = False
            try:
                opener = build_opener(ProxyHandler({}),NoRedirect(),HTTPCookieProcessor(http.cookiejar.CookieJar()))
                def request(path,payload=None,cookie=None):
                    headers={'Origin':f'http://127.0.0.1:{port}'}
                    if cookie: headers['Cookie']='r7_session='+cookie
                    if payload is not None: headers['Content-Type']='application/json'
                    req=Request(f'http://127.0.0.1:{port}'+path,data=json.dumps(payload).encode() if payload is not None else None,headers=headers)
                    try:
                        with opener.open(req,timeout=3) as response: code,raw=response.status,response.read(1024*1024)
                    except HTTPError as error: code,raw=error.code,error.read(1024*1024)
                    assertions.append(dict(path=path,status=code,response_sha256='sha256:'+hashlib.sha256(raw).hexdigest()))
                    return code,json.loads(raw)
                deadline=time.monotonic()+35
                while True:
                    if handle.process.poll() is not None: raise AssertionError('Restored native control exited')
                    try: status=request('/api/v1/auth/status'); break
                    except URLError:
                        if time.monotonic()>=deadline: raise AssertionError('Native restored readiness deadline')
                        time.sleep(0.1)
                assert status[0] == 200 and status[1]['configured']
                assert request('/api/v1/health',cookie=old_session.token)[0] == 401
                login=request('/api/v1/auth/login',dict(username='fixture-owner',password='synthetic-native-restore-password',command_id=f'fresh-native-login-{number}',expected_revision=0))
                assert login[0] == 200
                code,health=request('/api/v1/health'); assert code == 200
                assert health['data']['restoration']['status'] == 'RESTORED_INHIBITED'
                assert health['data']['restoration']['runtime_new_exposure'] == 'INHIBITED'
                assert not health['data']['live_authorized'] and health['data']['provider_requests'] == 0
                succeeded=True
            finally:
                termination=terminate_owned(handle,deadline_seconds=5)
        safe=_sanitize(log.read_text(encoding='utf-8'),repo).replace(str(output),'<PRIVATE_FIXTURE_ROOT>')
        log.write_text(safe,encoding='utf-8',newline='\n')
        report['commands'].append(dict(name=f'06-control-restart-{number}',started_at_utc=started,finished_at_utc=stamp(),
            passed=succeeded and termination.reaped,tree_reaped=termination.reaped,log=log.name,log_sha256=sha(log)))
        report['http_assertions'].extend(assertions); persist()
        assert succeeded and termination.reaped
    scenario('TWO_ACTUAL_NATIVE_CONTROL_RESTARTS_REJECT_COPIED_SESSION_AND_RETAIN_FENCE')
    second_backup, third = output/'再次 完整備份', output/'第三 私密世代'
    command('07-backup-restored-product',['backup-product-data','--config',target/'restored-product.json','--destination',second_backup])
    third_result=command('08-restore-second-product',['restore-product-data','--config',target/'restored-product.json','--backup',second_backup,'--destination',third])
    assert third_result['restore_generation_id'] != restored['restore_generation_id']
    assert load_config(third/'restored-product.json').local_data_root == third
    assert sha(third/'dataset.json') == sha(case.root/'dataset.json')
    scenario('NATIVE_COMPLETE_RESTORED_PRODUCT_SUPPORTS_LATER_FRESH_BACKUP_AND_RESTORE')
    # Move only this probe's marker within its verified private fixture generation.
    marker=target/'restore-generation.json'; marker.rename(target/'held-ready-marker.json')
    command('09-missing-ready-marker-denied',['serve','--config',target/'restored-product.json'],2)
    marker.with_name('held-ready-marker.json').rename(marker)
    scenario('PARTIAL_RESTORATION_CANNOT_START_NATIVE_CONTROL')
    artifact=backup/'files/cost.json'; original=artifact.read_bytes()
    artifact.write_bytes(bytes([original[0]^1])+original[1:])
    command('10-tampered-bundle-denied',['verify-product-backup','--config',source_profile,'--destination',backup],2)
    bad_target=output/'tampered-target'
    command('11-tampered-restore-denied',['restore-product-data','--config',source_profile,'--backup',backup,'--destination',bad_target],2)
    assert not bad_target.exists(); artifact.write_bytes(original)
    scenario('SAME_SIZE_BUNDLE_TAMPER_FAILS_BEFORE_RESTORATION_CREATION')
    report.update(passed=all(row['passed'] for row in report['commands']),finished_at_utc=stamp(),
        scenario_count=len(report['scenarios']),command_count=len(report['commands']))
finally:
    persist()
print(json.dumps(dict(passed=report['passed'],scenarios=len(report['scenarios']),commands=len(report['commands']))))
raise SystemExit(0 if report['passed'] else 1)
