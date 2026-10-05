from contextlib import closing
from dataclasses import replace
from datetime import datetime,timezone
import importlib,importlib.util,json,sqlite3,sys,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from application.config import ProductConfig,load_config
from application.platform.backup import create_database_backup
from application.platform.private_files import require_private
from application.intake.ledger import IntakeLedger,LeaseConflict
from application.control_api.auth import LocalAuth,AuthenticationError
class DatabaseRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(prefix='R7 還原 私密 ');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.data=self.root/'原始 資料';self.data.mkdir()
        self.cloud=self.root/'同步 暫存';self.cloud.mkdir()
        self.config=ProductConfig('r7-product-config-v0.2','restore-fixture',self.data,self.cloud,self.data/'canonical.sqlite3')
        with closing(sqlite3.connect(self.config.database_path)) as db:
            db.execute('CREATE TABLE preserved(value TEXT NOT NULL)');db.execute("INSERT INTO preserved VALUES('ORIGINAL_CANONICAL')");db.commit()
        self.backup=self.root/'私密 備份';self.target=self.root/'新的 generation'
    def module(self):
        return importlib.import_module('application.platform.database_restore')
    def backup_now(self):return create_database_backup(self.config,self.backup,timeout_seconds=5)
    def test_restoration_is_disjoint_private_and_emits_inhibited_new_configuration(self):
        self.backup_now();before=(self.config.database_path).read_bytes();module=self.module()
        first=module.restore_database_backup(self.config,self.backup,self.target)
        self.assertEqual(first['status'],'DATABASE_RESTORE_STAGED');self.assertEqual(first['financial_authority'],'NONE')
        config=load_config(self.target/'restored-product.json')
        self.assertEqual(config.local_data_root,self.target);self.assertIsNone(config.cloud_root)
        self.assertTrue(config.diagnostic_only);self.assertFalse(config.paper_runtime_enabled)
        marker=json.loads((self.target/'restore-generation.json').read_bytes())
        self.assertEqual(marker['reconciliation'],'REQUIRED');self.assertEqual(marker['reauthorization'],'REQUIRED')
        require_private(self.target,directory=True);require_private(config.database_path)
        with closing(sqlite3.connect(config.database_path)) as db:self.assertEqual(db.execute('SELECT value FROM preserved').fetchall(),[('ORIGINAL_CANONICAL',)])
        self.assertEqual(self.config.database_path.read_bytes(),before)
        with self.assertRaises(module.RestoreError):module.restore_database_backup(self.config,self.backup,self.target)
    def test_manifest_changed_after_verification_never_writes_outside_generation(self):
        from unittest.mock import patch
        self.backup_now();module=self.module();verify=module._verify_within_deadline
        calls=[]
        def verify_then_replace(*args,**kwargs):
            result=verify(*args,**kwargs)
            if not calls:
                calls.append(True)
                path=self.backup/'manifest.json';value=json.loads(path.read_bytes())
                value['databases'][0]['relative_path']='../escaped.sqlite'
                path.write_text(json.dumps(value),encoding='utf-8')
            return result
        with patch.object(module,'_verify_within_deadline',verify_then_replace),self.assertRaises(module.RestoreError):
            module.restore_database_backup(self.config,self.backup,self.target)
        self.assertFalse((self.root/'escaped.sqlite').exists())
    def test_stale_intake_claim_and_auth_session_cannot_survive_restore(self):
        now=datetime.now(timezone.utc)
        with IntakeLedger(self.data/'intake.sqlite',instance_id=self.config.product_instance_id) as ledger:
            claim=ledger.claim('claimed-fixture','sha256:'+'a'*64,'old-owner',now)
        auth=LocalAuth(self.data/'local-auth.sqlite',namespace='FIXTURE',clock=lambda:now)
        auth.create_owner('fixture-owner','synthetic-private-restore-password')
        grant=auth.login('fixture-owner','synthetic-private-restore-password',command_id='old-login',expected_revision=0)
        self.backup_now();module=self.module();module.restore_database_backup(self.config,self.backup,self.target)
        with IntakeLedger(self.target/'intake.sqlite',instance_id=self.config.product_instance_id) as ledger:
            with self.assertRaises(LeaseConflict):ledger.commit_effect(claim,'forbidden-old-effect',b'{}',now=now)
        restored=LocalAuth(self.target/'local-auth.sqlite',namespace='FIXTURE',clock=lambda:now)
        with self.assertRaises(AuthenticationError):restored.authenticate(grant.token)
        self.assertIsNotNone(auth.authenticate(grant.token),'Original source sessions remain untouched')
    def test_active_owner_and_foreign_target_or_changed_backup_are_denied(self):
        self.backup_now();module=self.module()
        from application.platform.scope_lock import ProcessScopeLock,operational_lock_root
        with ProcessScopeLock('runtime:'+self.config.product_instance_id,lock_root=operational_lock_root(self.config)):
            with self.assertRaises(module.RestoreError):module.restore_database_backup(self.config,self.backup,self.target)
        self.assertFalse(self.target.exists())
        self.target.mkdir();sentinel=self.target/'preserve.txt';sentinel.write_bytes(b'PRESERVE_FOREIGN_TARGET')
        with self.assertRaises(module.RestoreError):module.restore_database_backup(self.config,self.backup,self.target)
        self.assertEqual(sentinel.read_bytes(),b'PRESERVE_FOREIGN_TARGET')
        with (self.backup/'canonical.sqlite').open('ab') as stream:stream.write(b'corrupted')
        alternate=self.root/'fresh-other'
        with self.assertRaises(module.RestoreError):module.restore_database_backup(self.config,self.backup,alternate)
        self.assertFalse(alternate.exists())
    def test_source_backup_and_cloud_targets_are_never_overwritten(self):
        self.backup_now();module=self.module()
        for target in (self.data/'child',self.backup/'child',self.cloud/'child'):
            with self.subTest(target=target),self.assertRaises(module.RestoreError):module.restore_database_backup(self.config,self.backup,target)
            self.assertFalse(target.exists())
    def test_actual_e6_dispatch_and_paper_generations_advance_without_replaying_effects(self):
        from storage.product_dispatch import open_product_dispatch_journal,ProductDispatchError
        from storage.paper_process import open_paper_process_journal
        from storage.runtime_models import RuntimeConflictError
        from tests.storage.test_product_dispatch_v02 import ProductDispatchV02Tests
        from tests.storage.test_paper_process_journal import PaperProcessJournalTests
        now=datetime(2026,10,3,tzinfo=timezone.utc)
        fixture=ProductDispatchV02Tests();fixture.now=now
        with open_product_dispatch_journal(self.config.database_path) as journal:
            journal.ensure_run('run',fixture.permission(),now=now)
            old=journal.begin_process('run','original-process',expected_generation=0,now=now)
            journal.prepare('run','uncertain-operation',fixture.request(),lease=old,now=now)
            self.assertTrue(journal.claim_dispatch('run','uncertain-operation',lease=old,now=now))
        paper_fixture=PaperProcessJournalTests()
        with open_paper_process_journal(self.config.database_path) as journal:
            journal.create_run('paper-run',paper_fixture.binding(),paper_fixture.state(),now=now)
            self.assertEqual(journal.begin_process('paper-run','original-paper',expected_generation=0,now=now),1)
            previous=journal.recover('paper-run')
        self.backup_now();module=self.module();module.restore_database_backup(self.config,self.backup,self.target)
        restored_path=self.target/'canonical.sqlite3';current=datetime.now(timezone.utc)
        with open_product_dispatch_journal(restored_path) as journal:
            self.assertEqual(journal.operation('run','uncertain-operation').recovery_disposition,'READBACK_REQUIRED')
            self.assertEqual(journal.recover('run').process_generation,2)
            with self.assertRaises(ProductDispatchError):journal.prepare('run','old-lease-operation',fixture.request('r7other'),lease=old,now=current)
        with open_paper_process_journal(restored_path) as journal:
            recovered=journal.recover('paper-run')
            self.assertEqual(recovered.process_generation,2);self.assertEqual(recovered.state,previous.state)
            with self.assertRaises(RuntimeConflictError):journal.prepare('paper-run','old-paper-operation',{'kind':'SYNTHETIC'},expected_revision=0,now=current,process_generation=1)
        with open_product_dispatch_journal(self.config.database_path) as journal:self.assertEqual(journal.recover('run').process_generation,1)
    def test_actual_research_queue_lease_is_failed_and_retained_without_replay(self):
        from application.research.queue import ResearchQueue,ResearchQueueError
        now=datetime.now(timezone.utc)
        selected=dict(submission_revision=1,selection_hash='sha256:'+'b'*64,arguments=dict(submission_id='queue-fixture',
            definition={'synthetic':'NOT_EXECUTED'},dataset_ref='dataset.json',split_policy_ref='split.json',cost_policy_ref='cost.json'))
        def queue(path):
            return ResearchQueue(path,namespace='FIXTURE',owner_id='original-queue-owner',resolve_request=lambda *_:selected,
                service_factory=lambda:None,clock=lambda:now)
        original=queue(self.data/'queue.sqlite')
        receipt=original.enqueue('queue-fixture','fixture-policy','queue-command',1,actor='fixture-owner')
        claim=original.claim_next();self.assertIsNotNone(claim)
        self.backup_now();self.module().restore_database_backup(self.config,self.backup,self.target)
        restored=queue(self.target/'queue.sqlite')
        result=restored.get(claim.run_id)
        self.assertEqual(result['state'],'FAILED');self.assertGreater(result['generation'],claim.generation)
        self.assertIsNone(restored.claim_next())
        with self.assertRaises(ResearchQueueError):restored._checkpoint(claim.run_id,claim.generation,'forbidden-replay','development')
        self.assertEqual(original.get(claim.run_id)['state'],'RUNNING')
        with closing(sqlite3.connect(self.target/'queue.sqlite')) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM research_queue_events WHERE run_id=? AND state='FAILED'",(claim.run_id,)).fetchone()[0],1)
    def test_interrupted_private_generation_has_no_ready_marker_and_preserves_original(self):
        from unittest.mock import patch
        self.backup_now();module=self.module();write=module.write_private_new
        def interrupt(path,raw):
            if Path(path).name=='restored-product.json':raise OSError('SYNTHETIC_PRIVATE_LOCAL_FAILURE')
            return write(path,raw)
        original=self.config.database_path.read_bytes()
        with patch.object(module,'write_private_new',interrupt),self.assertRaises(module.RestoreError) as caught:
            module.restore_database_backup(self.config,self.backup,self.target)
        self.assertNotIn('SYNTHETIC_PRIVATE_LOCAL_FAILURE',str(caught.exception))
        self.assertTrue(self.target.is_dir());self.assertFalse((self.target/'restore-generation.json').exists())
        self.assertEqual(self.config.database_path.read_bytes(),original)
        from application.local_owners import LocalOwners
        from application.platform.supervision import ProcessSupervisor
        supplied=replace(self.config,local_data_root=self.target,database_path=self.target/'canonical.sqlite3',cloud_root=None)
        with self.assertRaises(ValueError):LocalOwners(supplied,namespace='FIXTURE')
        with self.assertRaises(ValueError):
            with ProcessSupervisor(supplied,'control'):pass
    def test_restored_profile_reports_persistent_fence_across_control_restarts(self):
        self.backup_now();self.module().restore_database_backup(self.config,self.backup,self.target)
        config=load_config(self.target/'restored-product.json')
        from application.platform.supervision import ProcessSupervisor
        from application.control_api.services import LocalControlServices
        now=lambda:datetime.now(timezone.utc)
        for _ in range(2):
            with ProcessSupervisor(config,'control',heartbeat_interval=0.02):
                services=LocalControlServices(config,namespace='FIXTURE',clock=now)
                health=services.view('health')
                self.assertIn('restoration',health)
                self.assertEqual(health['restoration']['reconciliation'],'REQUIRED')
                self.assertEqual(health['restoration']['runtime_new_exposure'],'INHIBITED')
                self.assertFalse(health['live_authorized'])
    def test_partial_or_changed_restored_profile_cannot_start_an_owner(self):
        self.backup_now();self.module().restore_database_backup(self.config,self.backup,self.target)
        config=load_config(self.target/'restored-product.json')
        from application.platform.supervision import ProcessSupervisor
        from application.local_owners import LocalOwners
        changed=replace(config,diagnostic_only=False,paper_runtime_enabled=True)
        for invalid in (changed,):
            with self.assertRaises(ValueError):LocalOwners(invalid,namespace='FIXTURE')
            with self.assertRaises(ValueError):
                with ProcessSupervisor(invalid,'control'):pass
        (self.target/'restore-generation.json').unlink() # Only this test's fresh synthetic generation.
        with self.assertRaises(ValueError):LocalOwners(config,namespace='FIXTURE')
        with self.assertRaises(ValueError):
            with ProcessSupervisor(config,'research'):pass
    def test_actual_database_restore_cli_never_prints_private_paths_or_rows(self):
        from dataclasses import asdict
        from contextlib import redirect_stdout
        import io
        from application.cli import main
        self.backup_now();profile=self.root/'original-product.json'
        profile.write_text(json.dumps({key:str(value) if isinstance(value,Path) else value for key,value in asdict(self.config).items()}),encoding='utf-8')
        output=io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(['restore-databases','--config',str(profile),'--backup',str(self.backup),'--destination',str(self.target)]),0)
        value=json.loads(output.getvalue());self.assertEqual(value['runtime_new_exposure'],'INHIBITED')
        self.assertNotIn(str(self.root),output.getvalue());self.assertNotIn('ORIGINAL_CANONICAL',output.getvalue())
    def test_running_research_attempt_is_fenced_without_changing_completed_evidence(self):
        from application.research.evidence import ResearchJournal,ResearchLeaseConflict
        now=datetime.now(timezone.utc)
        with ResearchJournal(self.data/'research.sqlite') as journal:
            inputs=journal.register_run('synthetic-restore-run',{'fixture':'NOT_EXECUTED'},now)
            completed=journal.claim('synthetic-restore-run','development',inputs,'old-owner',now)
            journal.finish(completed,{'preserved':'ACTUAL_COMPLETED_BYTES'},now)
            active=journal.claim('synthetic-restore-run','sealed_oos',inputs,'old-owner',now)
            previous=journal.attempts('synthetic-restore-run')[0]
        self.backup_now();self.module().restore_database_backup(self.config,self.backup,self.target)
        with ResearchJournal(self.target/'research.sqlite') as journal:
            attempts=journal.attempts('synthetic-restore-run')
            self.assertEqual(attempts[0],previous)
            self.assertEqual(attempts[1]['status'],'FAILED')
            self.assertEqual(json.loads(attempts[1]['reason_codes_json']),['RESTORED_RECONCILIATION_REQUIRED'])
            with self.assertRaises(ResearchLeaseConflict):journal.renew(active,now)
            with self.assertRaises(ResearchLeaseConflict):journal.finish(active,{'forbidden':'OLD_RESULT'},now)
        with ResearchJournal(self.data/'research.sqlite') as journal:
            self.assertEqual(journal.attempts('synthetic-restore-run')[1]['status'],'RUNNING')
    def test_deadline_expiry_during_actual_financial_fencing_stops_further_generations(self):
        from unittest.mock import patch
        import time
        from storage.product_dispatch import ProductDispatchJournal,open_product_dispatch_journal
        from tests.storage.test_product_dispatch_v02 import ProductDispatchV02Tests
        fixture=ProductDispatchV02Tests();now=datetime(2026,10,3,tzinfo=timezone.utc);fixture.now=now
        with open_product_dispatch_journal(self.config.database_path) as journal:
            for run in ('a-run','b-run'):
                journal.ensure_run(run,fixture.permission(),now=now)
                journal.begin_process(run,'original',expected_generation=0,now=now)
        self.backup_now();module=self.module();actual=ProductDispatchJournal.begin_process
        elapsed=[time.monotonic()];advanced=[]
        def advance_then_expire(journal,run,instance,**kwargs):
            result=actual(journal,run,instance,**kwargs)
            if instance.startswith('restore:'):
                advanced.append(run);elapsed[0]+=10
            return result
        with patch.object(ProductDispatchJournal,'begin_process',advance_then_expire),patch.object(module.time,'monotonic',lambda:elapsed[0]):
            with self.assertRaises(module.RestoreError):module.restore_database_backup(self.config,self.backup,self.target,timeout_seconds=5)
        self.assertEqual(advanced,['a-run'])
        self.assertFalse((self.target/'restore-generation.json').exists())
        with open_product_dispatch_journal(self.config.database_path) as journal:
            self.assertEqual(journal.recover('a-run').process_generation,1)
            self.assertEqual(journal.recover('b-run').process_generation,1)
    def test_authenticated_restored_health_surfaces_fence_and_refuses_copied_session(self):
        from application.entrypoints import create_local_app
        from fastapi.testclient import TestClient
        original=create_local_app(self.config)
        original.state.local_auth.create_owner('fixture-owner','synthetic-http-restore-password')
        old=original.state.local_auth.login('fixture-owner','synthetic-http-restore-password',command_id='old-http-login',expected_revision=0)
        self.backup_now();self.module().restore_database_backup(self.config,self.backup,self.target)
        config=load_config(self.target/'restored-product.json');app=create_local_app(config)
        with TestClient(app,base_url='http://127.0.0.1:8765',client=('127.0.0.1',41000)) as client:
            client.cookies.set('r7_session',old.token)
            self.assertEqual(client.get('/api/v1/health').status_code,401)
            client.cookies.clear()
            response=client.post('/api/v1/auth/login',json=dict(username='fixture-owner',password='synthetic-http-restore-password',command_id='fresh-http-login',expected_revision=0),headers={'Origin':'http://127.0.0.1:8765'})
            self.assertEqual(response.status_code,200,response.text)
            health=client.get('/api/v1/health')
            self.assertEqual(health.status_code,200,health.text)
            self.assertEqual(health.json()['data']['restoration']['status'],'RESTORED_INHIBITED')
            self.assertFalse(health.json()['data']['live_authorized'])
            self.assertEqual(health.json()['data']['provider_requests'],0)
if __name__=='__main__':unittest.main(verbosity=2)
