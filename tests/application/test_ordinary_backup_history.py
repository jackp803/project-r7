"""Draft actual ordinary backup/archival regression, no qualification issuance."""
from datetime import datetime,timezone
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch
import hashlib,json,unittest,uuid
import sqlite3
from application.config import load_config
from application.platform import product_backup
from application.platform.private_files import create_private_directory,write_private_new
from application.platform.restoration import require_valid_restoration
from storage.paper_selection import open_paper_selections
from storage.qualification import QualificationCheck,QualificationSubject,_open_qualification_receipt_owner,open_qualification_receipts
from registry.product_assessment import canonical,digest
from tests.application import test_ordinary_paper_composition as original

class OrdinaryBackupHistoryTests(unittest.TestCase):
    prepare=original.OrdinaryPaperCompositionTests.prepare

    def test_canonical_database_above_nondatabase_file_limit_still_verifies_and_restores(self):
        h,config,*_=self.prepare()
        # A real SQLite freelist enlarges the owned fixture without changing
        # canonical application schemas or introducing financial result rows.
        with sqlite3.connect(config.database_path) as db:
            db.execute('CREATE TABLE backup_size_fixture(value BLOB)')
            db.execute('INSERT INTO backup_size_fixture VALUES(zeroblob(?))',(65*1024*1024,))
            db.commit();db.execute('DROP TABLE backup_size_fixture');db.commit()
            db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        self.assertGreater(config.database_path.stat().st_size,product_backup.MAX_FILE_BYTES)
        backup=h.root/'large-canonical-backup';target=h.root/'large-canonical-restored'
        product_backup.create_product_backup(config,backup)
        product_backup.verify_product_backup(config,backup)
        product_backup.restore_product_backup(config,backup,target)
        restored=load_config(target/'restored-product.json')
        self.assertEqual(require_valid_restoration(restored)['status'],'RESTORED_INHIBITED')

    def test_ordinary_selected_and_receipt_history_backup_at_actual_long_captured_database_path(self):
        h,config,*_=self.prepare();self.failed_history(config)
        from tests.application.test_private_long_paths import PrivateLongPathTests
        fixture=PrivateLongPathTests();fixture.setUp()
        self.addCleanup(lambda:self.assertTrue(fixture.doCleanups(),'Owned long backup fixture cleanup failed'))
        destination=fixture.parent/'ordinary-complete-backup'
        self.assertGreater(len(str(destination/'databases/canonical.sqlite')),320)
        product_backup.create_product_backup(config,destination)
        product_backup.verify_product_backup(config,destination)
        target=h.root/'long-backup-restored';product_backup.restore_product_backup(config,destination,target)
        self.assertEqual(require_valid_restoration(load_config(target/'restored-product.json'))['status'],'RESTORED_INHIBITED')

    def failed_history(self,config):
        execution='pqr-'+uuid.uuid4().hex
        parent=config.local_data_root/'qualification'
        if not parent.exists():create_private_directory(parent)
        output=parent/execution;create_private_directory(output)
        raw=b'SYNTHETIC_STORAGE_ARCHIVE_FIXTURE_NOT_EXECUTED_NOT_QUALIFIED\n'
        ref='PQR-UNIT-FAILED.log';write_private_new(output/ref,raw)
        h='sha256:'+hashlib.sha256(raw).hexdigest()
        profile=dict(schema_version='r7-qualified-paper-inventory-v0.2',profile_id='r7-qualified-paper-release-v0.2',
            platform_id='windows-11-x86_64',capability_hash='sha256:'+'c'*64,
            groups=[dict(check_id='PQR-'+str(i).zfill(2),members=[dict(member_id='PQR-UNIT-FAILED' if i==1 else 'PQR-NOT-RUN-'+str(i))]) for i in range(1,8)])
        check=QualificationCheck(check_id='PQR-UNIT-FAILED',command_ref='not-executed-unit-model',log_ref=ref,
            log_hash=h,returncode=2,tree_reaped=True,duration_ms=0,tests_run=0,failures=0,errors=1,
            skipped=0,expected_failures=0,unexpected_successes=0)
        evidence=dict(schema_version='r7-qualified-paper-execution-evidence-v0.2',provenance='FIXTURE_SOFTWARE_CHECKS_ONLY',
            members=[dict(member_id=check.check_id,group_id='PQR-ERROR',test_cases=[],assertions=[],artifacts=[dict(ref=ref,hash=h)])])
        now=datetime.now(timezone.utc)
        with _open_qualification_receipt_owner(config.database_path,namespace='LOCAL_RESEARCH') as owner:
            receipt=owner._append(execution_id=execution,subject=QualificationSubject('LOCAL_RESEARCH','a'*40,
                'sha256:'+'b'*64,'sha256:'+'c'*64,'windows-11-x86_64'),profile_id=profile['profile_id'],
                profile_hash=digest(canonical(profile)),checks=(check,),started_at=now,finished_at=now,
                profile_manifest=profile,execution_evidence=evidence)
        self.assertFalse(receipt.passed)
        measured={key:value for key,value in asdict(receipt.subject).items() if key!='namespace'}
        measured.update(capability_hash=profile['capability_hash'],distribution_profile='r7-native-distribution-v0.2',
            financial_authority='NONE',worktree='UNAVAILABLE')
        preflight=dict(profile=profile,measured=measured,execution_id=execution,
            source_revision=receipt.subject.executable_revision,source_worktree='CLEAN')
        result=dict(status='NATIVE_PAPER_SOFTWARE_NOT_QUALIFIED',receipt_ref=receipt.receipt_id,execution_id=execution,
            profile_hash=receipt.profile_hash,platform_id=receipt.subject.platform_id,executable_revision=receipt.subject.executable_revision,
            build_hash=receipt.subject.build_hash,groups_completed=0,groups_required=7,provider_requests=0,
            credentials='NONE',capital='NONE',github_compute='NOT_USED',financial_authority='NONE')
        for name,value in [('preflight.json',preflight),('result.json',result)]:
            write_private_new(output/name,(canonical(value)+'\n').encode())
        return receipt,output/ref

    def test_actual_ordinary_inputs_and_failed_software_history_backup_verify_restore_inhibited(self):
        h,config,local,clock,selected,_=self.prepare()
        receipt,artifact=self.failed_history(config)
        with open_paper_selections(config.database_path) as reader:selection=reader.current()
        refs=set(selection.as_dict()['source_subject']['input_refs'].values())
        refs.add(artifact.relative_to(config.local_data_root).as_posix())
        original={ref:(config.local_data_root/ref).read_bytes() for ref in refs}
        backup=h.root/'ordinary-full-backup';target=h.root/'ordinary-full-restored'
        result=product_backup.create_product_backup(config,backup)
        self.assertEqual(result['status'],'PRODUCT_DATA_BACKUP_VERIFIED')
        manifest=json.loads((backup/'manifest.json').read_bytes())
        self.assertTrue(refs<={row['relative_path'] for row in manifest['files']})
        before={p.relative_to(backup).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in backup.rglob('*') if p.is_file()}
        from storage import paper_selection,qualification
        with patch.object(paper_selection,'open_paper_selections',wraps=paper_selection.open_paper_selections) as selections,\
                patch.object(qualification,'open_qualification_receipts',wraps=qualification.open_qualification_receipts) as receipts:
            product_backup.verify_product_backup(config,backup)
            self.assertTrue(selections.call_args_list);self.assertTrue(receipts.call_args_list)
            for call in selections.call_args_list+receipts.call_args_list:
                self.assertTrue(Path(call.args[0]).is_relative_to(backup/'databases'))
                self.assertIs(call.kwargs['immutable'],True)
        after={p.relative_to(backup).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in backup.rglob('*') if p.is_file()}
        self.assertEqual(before,after,'Sealed verification cannot add WAL/SHM sidecars or mutate captured bytes')
        product_backup.restore_product_backup(config,backup,target)
        restored=load_config(target/'restored-product.json')
        self.assertTrue(restored.diagnostic_only);self.assertFalse(restored.paper_runtime_enabled);self.assertIsNone(restored.cloud_root)
        self.assertEqual(require_valid_restoration(restored)['status'],'RESTORED_INHIBITED')
        for ref,raw in original.items():
            self.assertEqual((restored.local_data_root/ref).read_bytes(),raw)
            self.assertEqual((config.local_data_root/ref).read_bytes(),raw)
        with open_paper_selections(restored.database_path) as reader:self.assertEqual(reader.current(),selection)
        with open_qualification_receipts(restored.database_path,namespace='LOCAL_RESEARCH') as reader:
            self.assertEqual(reader.get(receipt.receipt_id),receipt)
        product_backup.create_product_backup(restored,h.root/'ordinary-restored-rebackup')

    def test_changed_ordinary_policy_is_not_covered_by_a_folder_whitelist(self):
        h,config,local,clock,selected,_=self.prepare()
        with open_paper_selections(config.database_path) as reader:record=reader.current().as_dict()
        policy=config.local_data_root/record['source_subject']['input_refs']['simulation_policy_ref']
        policy.write_bytes(policy.read_bytes()+b' ')
        with self.assertRaises(product_backup.ProductBackupError):product_backup.create_product_backup(config,h.root/'changed-policy-denied')

    def test_unbound_qualification_file_and_changed_bound_artifact_are_denied(self):
        h,config,local,clock,selected,_=self.prepare()
        _,artifact=self.failed_history(config)
        extra=artifact.parent/'unbound.json';write_private_new(extra,b'{}')
        with self.assertRaises(product_backup.ProductBackupError):product_backup.create_product_backup(config,h.root/'unbound-denied')
        extra.unlink();artifact.write_bytes(b'CHANGED')
        with self.assertRaises(product_backup.ProductBackupError):product_backup.create_product_backup(config,h.root/'changed-history-denied')

    def changed_selection(self,h,*,versioned):
        from application.paper.ordinary_setup import configure_ordinary_paper
        current=h.root/'paper-inputs.json';value=json.loads(current.read_bytes())
        policy=json.loads((h.data/value['simulation_policy_ref']).read_bytes());policy['quantity']='0.002'
        if versioned:value['simulation_policy_ref']='paper-sim-v2.json'
        (h.data/value['simulation_policy_ref']).write_text(json.dumps(policy),encoding='utf-8')
        changed=h.root/'paper-inputs-v2.json';changed.write_text(json.dumps(value),encoding='utf-8')
        self.assertEqual(configure_ordinary_paper(h.config_path,changed)['config_generation'],2)

    def test_conflicting_history_cannot_hide_changed_older_same_path_commitment(self):
        h,config,*_=self.prepare();self.changed_selection(h,versioned=False)
        with self.assertRaises(product_backup.ProductBackupError):product_backup.create_product_backup(config,h.root/'conflicting-history-denied')

    def test_versioned_ordinary_policy_history_retains_both_generations(self):
        h,config,*_=self.prepare();self.changed_selection(h,versioned=True)
        backup=h.root/'versioned-history';product_backup.create_product_backup(config,backup)
        files={row['relative_path'] for row in json.loads((backup/'manifest.json').read_bytes())['files']}
        self.assertTrue({'paper-sim.json','paper-sim-v2.json'}<=files)

    def test_preflight_validates_and_hashes_one_captured_byte_snapshot(self):
        h,config,*_=self.prepare();receipt,artifact=self.failed_history(config)
        from application.platform import paper_backup_history as history
        import time
        original_read=history.read_local;reads=[]
        preflight=artifact.parent/'preflight.json';raw=preflight.read_bytes()
        def alternating(root,ref,limit):
            if ref.endswith('/preflight.json'):
                reads.append(ref)
                return raw if len(reads)==1 else b'UNVALIDATED_REPLACEMENT'
            return original_read(root,ref,limit)
        with patch.object(history,'read_local',side_effect=alternating):
            refs,hashes=history._qualification_bindings(config.local_data_root,receipt,time.monotonic()+60)
        self.assertEqual(len(reads),1)
        relative=preflight.relative_to(config.local_data_root).as_posix()
        self.assertEqual(hashes[relative],'sha256:'+hashlib.sha256(raw).hexdigest())

if __name__=='__main__':unittest.main()
