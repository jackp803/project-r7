"""Fixed read-only source snapshot, not an importable runtime audit proof."""
import importlib
import sqlite3
import unittest

from storage.runtime_models import RuntimePersistenceError
from tests.storage import test_paper_history_audit as fixture


class PaperHistorySnapshotTests(unittest.TestCase):
    def setUp(self):
        self.helper=fixture.PaperHistoryAuditTests();self.helper.setUp();self.addCleanup(self.helper.doCleanups)
        self.module=importlib.import_module('storage.paper_history_audit')
        self.assertTrue(callable(getattr(self.module,'audit_paper_history_snapshot',None)),
            'Independent readonly pinned source audit missing')

    def run_audit(self,**kwargs):
        return self.module.audit_paper_history_snapshot(self.helper.helper.path,'run-1',maximum_rows=1,**kwargs)

    def test_actual_fixed_snapshot_finishes_while_real_owner_appends_without_history_restarts(self):
        for number in range(1,4):self.helper.helper.apply(number)
        appended=[];progress=[]
        def observe(value):
            progress.append(value)
            if not appended:self.helper.helper.apply(4);appended.append(4)
        result=self.run_audit(on_progress=observe)
        self.assertEqual(result['scope'],'DIAGNOSTIC_SNAPSHOT_NOT_RUNTIME_AUTHORITY')
        self.assertEqual(result['verified_prefix_revision'],3)
        self.assertEqual(result['current_revision'],3)
        self.assertTrue(result['source_changed_during_snapshot'])
        self.assertEqual(self.helper.journal.recover_current('run-1').revision,4)
        self.assertTrue(all(item.rows_in_step<=1 for item in progress))
        self.assertFalse(self.helper.journal.history_audit_ready('run-1'))

    def test_separate_snapshot_never_migrates_writes_or_installs_owner_proof(self):
        db=self.helper.journal._db
        before=tuple(db.execute('SELECT migration_name,applied_at FROM schema_migrations ORDER BY migration_name'))
        changes=db.total_changes
        result=self.run_audit()
        self.assertFalse(result['source_changed_during_snapshot'])
        self.assertEqual(result['snapshot_write_count'],0)
        self.assertEqual(db.total_changes,changes)
        self.assertEqual(tuple(db.execute('SELECT migration_name,applied_at FROM schema_migrations ORDER BY migration_name')),before)
        self.assertFalse(self.helper.journal.history_audit_ready('run-1'))

    def test_ancient_actual_prefix_corruption_refuses_snapshot_despite_valid_current_facts(self):
        for number in range(1,4):self.helper.helper.apply(number)
        db=self.helper.journal._db
        trigger=db.execute("SELECT sql FROM sqlite_master WHERE name='paper_process_published_prefixes_no_update'").fetchone()[0]
        db.execute('DROP TRIGGER paper_process_published_prefixes_no_update')
        db.execute("UPDATE paper_process_published_prefixes SET prefix_hash=? WHERE revision=1",('sha256:'+'0'*64,))
        db.execute(trigger)
        self.assertEqual(self.helper.journal.recover_current('run-1').history_verification,'CURRENT_FACTS_ONLY')
        with self.assertRaises(RuntimePersistenceError):self.run_audit()

    def test_cancelled_observer_releases_read_snapshot_without_mutation_or_permission(self):
        def cancel(value):raise InterruptedError('controlled source audit cancellation')
        with self.assertRaises(InterruptedError):self.run_audit(on_progress=cancel)
        self.helper.helper.apply(1)
        self.assertFalse(self.helper.journal.history_audit_ready('run-1'))
        with sqlite3.connect(self.helper.helper.path) as external:
            self.assertEqual(external.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0],0)


if __name__=='__main__':unittest.main()
