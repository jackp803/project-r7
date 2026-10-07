"""Actual canonical-store software receipts; no qualified release/admission claim."""
import importlib,importlib.util,json,sqlite3,tempfile,unittest
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

from storage import open_sqlite_platform

NOW=datetime(2026,10,8,tzinfo=timezone.utc)
HASH='sha256:'+'1'*64

class QualificationReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='r7-qualification-receipt-')
        self.root=Path(self.temp.name).resolve();self.addCleanup(self.temp.cleanup)
        self.path=self.root/'canonical.sqlite3'
        with open_sqlite_platform(self.path,research_namespace='FIXTURE'):pass

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('storage.qualification'),
            'Internal qualification receipt store is not implemented')
        return importlib.import_module('storage.qualification')

    def subject(self,m,**changes):
        fields=dict(namespace='FIXTURE',executable_revision='1'*40,implementation_hash=HASH,
            build_hash='sha256:'+'2'*64,platform_id='windows-11-x86_64')
        fields.update(changes);return m.QualificationSubject(**fields)

    def check(self,m,**changes):
        fields=dict(check_id='fixture-check-01',command_ref='owned-command-01',log_ref='owned-log-01',
            log_hash=HASH,returncode=0,tree_reaped=True,tests_run=3,failures=0,errors=0,
            skipped=0,expected_failures=0,unexpected_successes=0,duration_ms=5)
        fields.update(changes);return m.QualificationCheck(**fields)

    def append(self,m,owner,**changes):
        fields=dict(execution_id='owned-run-01',subject=self.subject(m),profile_id='fixture-profile-v0.2',
            profile_hash=HASH,checks=(self.check(m),),started_at=NOW,finished_at=NOW+timedelta(seconds=1))
        fields.update(changes);return owner._append(**fields)

    def test_actual_read_facade_is_immutable_software_evidence_only(self):
        m=self.module()
        with m._open_qualification_receipt_owner(self.path,namespace='FIXTURE') as owner:
            receipt=self.append(m,owner)
        with m.open_qualification_receipts(self.path,namespace='FIXTURE') as reader:
            loaded=reader.get(receipt.receipt_id)
            self.assertEqual(loaded,receipt);self.assertTrue(loaded.passed)
            self.assertEqual(loaded.scope,'SOFTWARE_CHECK_EXECUTION_ONLY')
            for name in ('append','_append','connection','current_release','authorize'):
                self.assertFalse(hasattr(reader,name),name)
            with self.assertRaises((AttributeError,TypeError)):loaded.receipt_id='forged'
            self.assertIsNone(reader.get('qualification-'+'a'*64))

    def test_missing_or_deleted_database_is_never_created(self):
        m=self.module();missing=self.root/'missing.sqlite3'
        for factory in (m.open_qualification_receipts,m._open_qualification_receipt_owner):
            with self.assertRaises(m.QualificationReceiptError):factory(missing,namespace='FIXTURE')
            self.assertFalse(missing.exists())
        self.path.unlink()
        with self.assertRaises(m.QualificationReceiptError):m.open_qualification_receipts(self.path,namespace='FIXTURE')
        self.assertFalse(self.path.exists())

    def test_reader_sqlite_connection_is_actually_read_only(self):
        m=self.module()
        with m.open_qualification_receipts(self.path,namespace='FIXTURE') as reader:
            with self.assertRaises(sqlite3.OperationalError):
                reader._db.execute("DELETE FROM schema_migrations WHERE migration_name='0018_product_qualification_receipts.sql'")

    def test_namespace_mismatch_does_not_bind_or_migrate(self):
        m=self.module()
        with closing(sqlite3.connect(self.path)) as db,db:before=tuple(db.execute('SELECT name,sql FROM sqlite_master ORDER BY name'))
        for factory in (m.open_qualification_receipts,m._open_qualification_receipt_owner):
            with self.assertRaisesRegex(m.QualificationReceiptError,'NAMESPACE'):
                factory(self.path,namespace='LOCAL_RESEARCH')
        with closing(sqlite3.connect(self.path)) as db,db:
            self.assertEqual(tuple(db.execute('SELECT name,sql FROM sqlite_master ORDER BY name')),before)
            self.assertEqual(db.execute('SELECT namespace FROM registry_research_namespace').fetchone()[0],'FIXTURE')

    def test_absent_or_mutable_namespace_fails_closed(self):
        m=self.module()
        with closing(sqlite3.connect(self.path)) as db,db:db.execute('DROP TRIGGER registry_research_namespace_immutable')
        with self.assertRaisesRegex(m.QualificationReceiptError,'NAMESPACE'):
            m._open_qualification_receipt_owner(self.path,namespace='FIXTURE')
        with closing(sqlite3.connect(self.path)) as db,db:db.execute('DROP TABLE registry_research_namespace')
        with self.assertRaisesRegex(m.QualificationReceiptError,'NAMESPACE'):
            m.open_qualification_receipts(self.path,namespace='FIXTURE')

    def test_direct_writer_construction_and_caller_pass_are_rejected(self):
        m=self.module()
        with self.assertRaisesRegex(m.QualificationReceiptError,'CAPABILITY'):
            m._QualificationReceiptOwner(None,'FIXTURE',None,_writer_capability=object())
        with m._open_qualification_receipt_owner(self.path,namespace='FIXTURE') as owner:
            with self.assertRaises(m.QualificationReceiptError):self.append(m,owner,checks=({'passed':True},))
        with self.assertRaises(TypeError):m.QualificationCheck(check_id='x',passed=True)

    def test_exact_replay_survives_restart_and_changed_content_conflicts(self):
        m=self.module()
        with m._open_qualification_receipt_owner(self.path,namespace='FIXTURE') as owner:first=self.append(m,owner)
        with m._open_qualification_receipt_owner(self.path,namespace='FIXTURE') as owner:
            self.assertEqual(self.append(m,owner),first)
            with self.assertRaisesRegex(m.QualificationReceiptError,'CONFLICT'):
                self.append(m,owner,checks=(self.check(m,returncode=1,failures=1),))
            self.assertEqual(owner.get(first.receipt_id),first)

    def test_failure_and_unreaped_tree_are_historical_failure(self):
        m=self.module()
        with m._open_qualification_receipt_owner(self.path,namespace='FIXTURE') as owner:
            result=self.append(m,owner,checks=(self.check(m,returncode=124,tree_reaped=False),))
            self.assertFalse(result.passed);self.assertEqual(owner.get(result.receipt_id),result)
            self.assertEqual(result.scope,'SOFTWARE_CHECK_EXECUTION_ONLY')

    def test_bounded_ordered_inventory_strict_counts_and_time(self):
        m=self.module()
        with m._open_qualification_receipt_owner(self.path,namespace='FIXTURE') as owner:
            for checks in ((),(self.check(m),)*2,[self.check(m)],(self.check(m),)*257):
                with self.subTest(checks=len(checks)),self.assertRaises(m.QualificationReceiptError):
                    self.append(m,owner,checks=checks)
            with self.assertRaises(m.QualificationReceiptError):self.check(m,tests_run=True)
            with self.assertRaises(m.QualificationReceiptError):self.append(m,owner,finished_at=NOW-timedelta(seconds=1))
            with self.assertRaises(m.QualificationReceiptError):self.append(m,owner,subject=self.subject(m,namespace='LOCAL_RESEARCH'))

    def test_sql_update_and_delete_of_receipts_are_denied(self):
        m=self.module()
        with m._open_qualification_receipt_owner(self.path,namespace='FIXTURE') as owner:receipt=self.append(m,owner)
        with closing(sqlite3.connect(self.path)) as db,db:
            for statement in ('UPDATE product_qualification_receipts SET payload_json="{}"','DELETE FROM product_qualification_receipts'):
                with self.assertRaises(sqlite3.IntegrityError):db.execute(statement)
        with m.open_qualification_receipts(self.path,namespace='FIXTURE') as reader:self.assertEqual(reader.get(receipt.receipt_id),receipt)

    def replacement(self,m,execution_id):
        return m._payload(execution_id,self.subject(m,build_hash='sha256:'+'3'*64),'fixture-profile-v0.2',
            HASH,(self.check(m,returncode=1,failures=1),),NOW,NOW+timedelta(seconds=1))

    def test_sql_replace_cannot_change_existing_execution(self):
        m=self.module()
        with m._open_qualification_receipt_owner(self.path,namespace='FIXTURE') as owner:original=self.append(m,owner)
        replacement,raw=self.replacement(m,'owned-run-01')
        with closing(sqlite3.connect(self.path)) as db,db:
            self.assertEqual(db.execute('PRAGMA recursive_triggers').fetchone()[0],0)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT OR REPLACE INTO product_qualification_receipts VALUES(?,?,?,?,?,?,?,?,?)',m._columns(replacement,raw))
        with m.open_qualification_receipts(self.path,namespace='FIXTURE') as reader:self.assertEqual(reader.get(original.receipt_id),original)

    def test_sql_replace_cannot_reuse_existing_receipt_identity(self):
        m=self.module()
        with m._open_qualification_receipt_owner(self.path,namespace='FIXTURE') as owner:original=self.append(m,owner)
        replacement,raw=self.replacement(m,'owned-run-02');columns=list(m._columns(replacement,raw));columns[1]=original.receipt_id
        with closing(sqlite3.connect(self.path)) as db,db:
            self.assertEqual(db.execute('PRAGMA recursive_triggers').fetchone()[0],0)
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute('INSERT OR REPLACE INTO product_qualification_receipts VALUES(?,?,?,?,?,?,?,?,?)',columns)
        with m.open_qualification_receipts(self.path,namespace='FIXTURE') as reader:self.assertEqual(reader.get(original.receipt_id),original)

    def test_corrupt_noncanonical_and_duplicate_json_are_rejected(self):
        m=self.module()
        with m._open_qualification_receipt_owner(self.path,namespace='FIXTURE') as owner:receipt=self.append(m,owner)
        with closing(sqlite3.connect(self.path)) as db,db:
            row=db.execute('SELECT payload_json FROM product_qualification_receipts').fetchone()[0]
            trigger=db.execute("SELECT sql FROM sqlite_master WHERE name='product_qualification_receipts_no_update'").fetchone()[0]
        for raw in ('{',row+' ',row[:-1]+',"scope":"FORGED"}',json.dumps({**json.loads(row),'extra':'forged'})):
            with self.subTest(raw=raw[:20]):
                with closing(sqlite3.connect(self.path)) as db,db:
                    db.execute('DROP TRIGGER product_qualification_receipts_no_update')
                    db.execute('UPDATE product_qualification_receipts SET payload_json=?,payload_hash=?',(raw,m._digest(raw)))
                    db.execute(trigger)
                with m.open_qualification_receipts(self.path,namespace='FIXTURE') as reader:
                    with self.assertRaises(m.QualificationReceiptError):reader.get(receipt.receipt_id)

    def test_schema_tampering_after_open_is_detected(self):
        m=self.module()
        with m._open_qualification_receipt_owner(self.path,namespace='FIXTURE') as owner:
            result=self.append(m,owner)
            with closing(sqlite3.connect(self.path)) as db,db:db.execute('DROP TRIGGER product_qualification_receipts_no_delete')
            with self.assertRaisesRegex(m.QualificationReceiptError,'SCHEMA'):owner.get(result.receipt_id)
            with self.assertRaisesRegex(m.QualificationReceiptError,'SCHEMA'):self.append(m,owner)

    def old_store(self):
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute('DROP TABLE product_qualification_receipts')
            db.execute("DELETE FROM schema_migrations WHERE migration_name='0018_product_qualification_receipts.sql'")

    def test_read_facade_does_not_migrate_old_store(self):
        m=self.module();self.old_store()
        with self.assertRaisesRegex(m.QualificationReceiptError,'SCHEMA'):
            m.open_qualification_receipts(self.path,namespace='FIXTURE')
        with closing(sqlite3.connect(self.path)) as db,db:
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='product_qualification_receipts'").fetchone())
        with m._open_qualification_receipt_owner(self.path,namespace='FIXTURE') as owner:receipt=self.append(m,owner)
        with m.open_qualification_receipts(self.path,namespace='FIXTURE') as reader:self.assertEqual(reader.get(receipt.receipt_id),receipt)

    def test_migration_rollback_preserves_prior_canonical_store(self):
        m=self.module();self.old_store();original=m._execute_receipt_migration
        def fail(db,script):original(db,script);raise sqlite3.OperationalError('fixture migration interruption')
        with patch.object(m,'_execute_receipt_migration',side_effect=fail):
            with self.assertRaises(m.QualificationReceiptError):m._open_qualification_receipt_owner(self.path,namespace='FIXTURE')
        with closing(sqlite3.connect(self.path)) as db,db:
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='product_qualification_receipts'").fetchone())
            self.assertIsNone(db.execute("SELECT 1 FROM schema_migrations WHERE migration_name='0018_product_qualification_receipts.sql'").fetchone())
            self.assertEqual(db.execute('SELECT namespace FROM registry_research_namespace').fetchone()[0],'FIXTURE')
        with m._open_qualification_receipt_owner(self.path,namespace='FIXTURE') as owner:self.append(m,owner)

    def test_concurrent_first_migration_and_exact_append_have_one_logical_receipt(self):
        m=self.module();self.old_store();barrier=Barrier(2)
        def operation():
            barrier.wait(timeout=5)
            with m._open_qualification_receipt_owner(self.path,namespace='FIXTURE') as owner:return self.append(m,owner)
        with ThreadPoolExecutor(max_workers=2) as pool:
            tasks=[pool.submit(operation) for _ in range(2)];results=[task.result(timeout=15) for task in tasks]
        self.assertEqual(results[0],results[1])
        with closing(sqlite3.connect(self.path)) as db,db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM product_qualification_receipts').fetchone()[0],1)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM schema_migrations WHERE migration_name='0018_product_qualification_receipts.sql'").fetchone()[0],1)

if __name__=='__main__':unittest.main()
