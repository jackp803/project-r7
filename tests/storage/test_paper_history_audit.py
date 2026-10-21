"""Private bounded audit eligibility; current snapshots/progress are not PASS inputs."""
import sqlite3
import unittest
from unittest.mock import patch

from brokers.paper import PaperBroker
from storage.paper_process import open_paper_process_journal
from storage.runtime_models import RuntimeValidationError
from tests.storage import test_paper_process_prefix as prefix_fixture


class PaperHistoryAuditTests(unittest.TestCase):
    def setUp(self):
        self.helper=prefix_fixture.PaperPublishedPrefixTests();self.helper.setUp();self.addCleanup(self.helper.doCleanups)
        self.helper.create();self.journal=self.helper.journal
        for name in ('history_audit_step','history_audit_ready','history_audit_progress'):
            self.assertTrue(callable(getattr(self.journal,name,None)),
                'Private bounded history audit API missing: '+name)

    def finish(self,*,budget=2):
        for _ in range(500):
            progress=self.journal.history_audit_step('run-1',maximum_rows=budget)
            self.assertLessEqual(progress.rows_in_step,budget)
            if self.journal.history_audit_ready('run-1'):return progress
        self.fail('A finite stable history never completed its bounded audit')

    def test_current_facts_cannot_replace_complete_bounded_audit_and_no_db_writes_are_needed(self):
        for number in range(1,4):self.helper.apply(number)
        self.assertEqual(self.journal.recover_current('run-1').history_verification,'CURRENT_FACTS_ONLY')
        self.assertFalse(self.journal.history_audit_ready('run-1'))
        changes=self.journal._db.total_changes
        self.journal._db.execute('PRAGMA query_only=ON')
        progress=self.finish(budget=1)
        self.assertEqual(progress.status,'HISTORY_VERIFIED_IN_CURRENT_INSTANCE')
        self.assertEqual(progress.target_prefix_revision,3)
        self.assertEqual(self.journal._db.total_changes,changes)

    def test_new_connection_has_no_importable_or_restored_audit_permission(self):
        self.finish()
        with open_paper_process_journal(self.helper.path) as another:
            self.assertFalse(another.history_audit_ready('run-1'))
            self.assertNotEqual(another.history_audit_progress('run-1').status,
                'HISTORY_VERIFIED_IN_CURRENT_INSTANCE')

    def test_external_and_unknown_same_connection_changes_invalidate_completed_proof(self):
        db=self.journal._db
        db.execute('CREATE TABLE controlled_nonhistory_counter(value INTEGER)')
        self.finish();self.assertTrue(self.journal.history_audit_ready('run-1'))
        db.execute('INSERT INTO controlled_nonhistory_counter VALUES(1)')
        self.assertFalse(self.journal.history_audit_ready('run-1'))
        self.finish()
        with sqlite3.connect(self.helper.path) as external:
            external.execute('INSERT INTO controlled_nonhistory_counter VALUES(2)')
        self.assertFalse(self.journal.history_audit_ready('run-1'))

    def test_corrupt_older_prefix_never_inherits_a_valid_current_snapshot_or_cached_proof(self):
        for number in range(1,4):self.helper.apply(number)
        self.finish();db=self.journal._db
        trigger=db.execute("SELECT sql FROM sqlite_master WHERE name='paper_process_published_prefixes_no_update'").fetchone()[0]
        db.execute('DROP TRIGGER paper_process_published_prefixes_no_update')
        db.execute('UPDATE paper_process_published_prefixes SET prefix_hash=? WHERE revision=1',('sha256:'+'0'*64,))
        db.execute(trigger)
        self.assertEqual(self.journal.recover_current('run-1').history_verification,'CURRENT_FACTS_ONLY')
        self.assertFalse(self.journal.history_audit_ready('run-1'))
        with self.assertRaises(RuntimeValidationError):self.finish(budget=1)

    def test_audit_state_copied_from_another_instance_is_not_a_proof_input(self):
        self.finish()
        with open_paper_process_journal(self.helper.path) as another:
            another._history._states['run-1']=self.journal._history._states['run-1']
            self.assertFalse(another.history_audit_ready('run-1'))
            self.assertEqual(another.history_audit_progress('run-1').verified_rows,0)

    def test_invalid_budget_or_active_writer_cannot_start_an_audit(self):
        for budget in (False,0,129,'1'):
            with self.subTest(budget=budget),self.assertRaises(RuntimeValidationError):
                self.journal.history_audit_step('run-1',maximum_rows=budget)
        self.journal._db.execute('BEGIN IMMEDIATE')
        try:
            with self.assertRaises(RuntimeValidationError):self.journal.history_audit_step('run-1')
        finally:self.journal._db.rollback()
        self.assertFalse(self.journal.history_audit_ready('run-1'))

    def test_orphan_publication_not_reachable_from_valid_operations_refuses(self):
        self.helper.apply(1);db=self.journal._db
        db.execute('PRAGMA foreign_keys=OFF')
        db.execute('INSERT INTO paper_process_publications VALUES(?,?,?,?)',
            ('run-1','controlled-orphan','sha256:'+'0'*64,'2026-10-03T00:00:00.000000Z'))
        db.execute('PRAGMA foreign_keys=ON')
        with self.assertRaises(RuntimeValidationError):self.finish(budget=1)
        self.assertFalse(self.journal.history_audit_ready('run-1'))

    def test_orphan_effect_inventory_cannot_be_omitted_by_joining_only_valid_operations(self):
        self.helper.apply(1);db=self.journal._db
        effect=list(db.execute('SELECT * FROM paper_process_effects LIMIT 1').fetchone());effect[1]='controlled-orphan'
        db.execute('PRAGMA foreign_keys=OFF')
        db.execute('INSERT INTO paper_process_effects VALUES(?,?,?,?,?,?,?)',effect)
        db.execute('PRAGMA foreign_keys=ON')
        with self.assertRaises(RuntimeValidationError):self.finish(budget=1)
        self.assertFalse(self.journal.history_audit_ready('run-1'))

    def test_broker_domain_validation_stays_outside_all_audit_read_snapshots(self):
        original=PaperBroker.from_state
        def validate(value):
            self.assertFalse(self.journal._db.in_transaction)
            return original(value)
        with patch.object(PaperBroker,'from_state',side_effect=validate):self.finish(budget=1)

    def test_schema_change_during_partial_audit_invalidates_cursor_and_expected_schema(self):
        self.helper.apply(1);progress=self.journal.history_audit_step('run-1',maximum_rows=1)
        self.assertGreater(progress.verified_rows,0)
        db=self.journal._db;db.execute('DROP TRIGGER paper_process_operations_no_delete')
        self.assertFalse(self.journal.history_audit_ready('run-1'))
        self.assertEqual(self.journal.history_audit_progress('run-1').verified_rows,0)
        with self.assertRaises(RuntimeValidationError):self.finish(budget=1)

    def test_unknown_migration_ledger_change_cannot_regain_history_eligibility(self):
        self.finish()
        self.journal._db.execute('INSERT INTO schema_migrations(migration_name) VALUES(?)',('9999_controlled_unknown.sql',))
        self.assertFalse(self.journal.history_audit_ready('run-1'))
        with self.assertRaises(RuntimeValidationError):self.finish(budget=1)
