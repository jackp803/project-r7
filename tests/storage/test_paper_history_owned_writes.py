"""An actual E6 append extends private audit work; unknown SQL never does."""
import sqlite3
import unittest

from storage.runtime_models import RuntimePersistenceError
from tests.storage import test_paper_history_audit as audit_fixture
from tests.storage.test_paper_process_journal import NOW


class PaperHistoryOwnedWriteTests(unittest.TestCase):
    def setUp(self):
        self.audit=audit_fixture.PaperHistoryAuditTests();self.audit.setUp();self.addCleanup(self.audit.doCleanups)
        self.journal=self.audit.journal;self.helper=self.audit.helper

    def finish(self):return self.audit.finish(budget=1)

    def test_each_real_intent_effect_publication_and_exact_replay_preserves_completed_audit(self):
        self.finish()
        self.journal.prepare('run-1','tick-1',{'kind':'DEADLINE'},expected_revision=0,now=NOW)
        self.assertTrue(self.journal.history_audit_ready('run-1'),'Qualified PREPARE lost owned audit')
        state=self.helper.helper.state();state['runtime']['clock']=1
        applied=self.journal.complete('run-1','tick-1',state,{'status':'HOLD'},now=NOW)
        self.assertTrue(self.journal.history_audit_ready('run-1'),'Qualified COMPLETE lost owned audit')
        for _ in range(2):
            self.journal.mark_published('run-1','tick-1',applied.effect_hash,now=NOW)
            self.assertTrue(self.journal.history_audit_ready('run-1'))
            self.assertEqual(self.journal.history_audit_progress('run-1').verified_prefix_revision,1)

    def test_partial_audit_completes_original_inventory_while_valid_appends_continue(self):
        self.helper.apply(1)
        before=self.journal.history_audit_step('run-1',maximum_rows=1)
        self.helper.apply(2)
        after=self.journal.history_audit_progress('run-1')
        self.assertEqual(after.verified_rows,before.verified_rows,'Normal append reset partial audit cursor')
        progress=self.finish()
        self.assertEqual(progress.target_prefix_revision,1)
        self.assertEqual(progress.verified_prefix_revision,2)
        self.assertEqual(self.journal.audit_full('run-1').revision,2)

    def test_original_unfinished_intent_can_complete_without_changing_frozen_audit_inventory(self):
        self.journal.prepare('run-1','tick-1',{'kind':'DEADLINE'},expected_revision=0,now=NOW)
        self.journal.history_audit_step('run-1',maximum_rows=1)
        state=self.helper.helper.state();state['runtime']['clock']=1
        applied=self.journal.complete('run-1','tick-1',state,{'status':'HOLD'},now=NOW)
        self.journal.mark_published('run-1','tick-1',applied.effect_hash,now=NOW)
        self.assertNotEqual(self.journal.history_audit_progress('run-1').status,'HISTORY_AUDIT_REQUIRED')
        self.assertEqual(self.finish().verified_prefix_revision,1)

    def test_original_applied_tail_can_publish_during_partial_audit(self):
        applied=self.helper.apply(1,publish=False)
        self.journal.history_audit_step('run-1',maximum_rows=1)
        self.journal.mark_published('run-1','tick-1',applied.effect_hash,now=NOW)
        self.assertNotEqual(self.journal.history_audit_progress('run-1').status,'HISTORY_AUDIT_REQUIRED')
        self.assertEqual(self.finish().verified_prefix_revision,1)

    def test_generation_and_same_owner_pause_preserve_proof_without_granting_entry(self):
        self.finish()
        self.journal.begin_process('run-1','successor',expected_generation=0,now=NOW)
        self.assertTrue(self.journal.history_audit_ready('run-1'))
        self.journal.request_entry_pause('run-1','pause-1',actor='local-owner',expected_revision=0,now=NOW)
        self.assertTrue(self.journal.history_audit_ready('run-1'))
        self.assertTrue(self.journal.entry_pause_requested('run-1'))

    def test_unknown_sql_before_qualified_call_cannot_be_laundered_as_owned_append(self):
        self.journal._db.execute('CREATE TABLE controlled_counter(value INTEGER)');self.finish()
        self.journal._db.execute('INSERT INTO controlled_counter VALUES(1)')
        self.helper.apply(1)
        self.assertFalse(self.journal.history_audit_ready('run-1'))

    def test_external_commit_during_owned_write_and_failed_effect_never_preserve_proof(self):
        db=self.journal._db;db.execute('CREATE TABLE controlled_counter(value INTEGER)');self.finish()
        with sqlite3.connect(self.helper.path) as external:external.execute('INSERT INTO controlled_counter VALUES(1)')
        self.helper.apply(1)
        self.assertFalse(self.journal.history_audit_ready('run-1'))
        self.finish()
        self.journal.prepare('run-1','tick-2',{'kind':'DEADLINE'},expected_revision=1,now=NOW)
        with self.assertRaises(RuntimePersistenceError):
            self.journal.complete('run-1','tick-2',self.helper.helper.state(),{},now=NOW,process_generation=99)
        self.assertFalse(self.journal.history_audit_ready('run-1'))
        self.assertEqual(self.journal.operation('run-1','tick-2').status,'PREPARED')

    def test_existing_trigger_outside_closed_write_footprint_revokes_not_blocks_management(self):
        db=self.journal._db;db.execute('CREATE TABLE controlled_counter(value INTEGER)')
        db.execute('''CREATE TEMP TRIGGER controlled_extra AFTER INSERT ON main.paper_process_operations
            BEGIN INSERT INTO controlled_counter VALUES(1); END''')
        self.finish()
        self.helper.apply(1)
        self.assertFalse(self.journal.history_audit_ready('run-1'))
        self.assertEqual(self.journal.recover_current('run-1').revision,1)

    def test_other_legacy_run_can_write_without_using_new_profile_reader(self):
        self.journal.create_run('legacy',self.helper.helper.binding(),self.helper.helper.state(),now=NOW)
        self.finish()
        self.journal.prepare('legacy','legacy-tick',{},expected_revision=0,now=NOW)
        self.assertEqual(self.journal.operation('legacy','legacy-tick').status,'PREPARED')

    def test_new_publication_before_original_lexical_cursor_is_not_part_of_frozen_inventory(self):
        self.helper.apply(1)
        before=self.journal.history_audit_step('run-1',maximum_rows=1)
        self.journal.prepare('run-1','a-new',{},expected_revision=1,now=NOW)
        result=self.journal.complete('run-1','a-new',self.helper.helper.state(),{},now=NOW)
        self.journal.mark_published('run-1','a-new',result.effect_hash,now=NOW)
        self.assertEqual(self.journal.history_audit_progress('run-1').verified_rows,before.verified_rows)
        self.assertEqual(self.finish().verified_prefix_revision,2)

    def test_temp_schema_change_revokes_proof_and_shadow_history_cannot_regain_it(self):
        self.finish();db=self.journal._db
        db.execute('CREATE TEMP VIEW controlled_view AS SELECT 1 AS value')
        self.assertFalse(self.journal.history_audit_ready('run-1'),'TEMP schema change kept stale proof')
        self.finish()
        db.execute('CREATE TEMP VIEW paper_process_checkpoints AS SELECT * FROM main.paper_process_checkpoints')
        self.assertFalse(self.journal.history_audit_ready('run-1'))
        with self.assertRaises(RuntimePersistenceError):self.finish()

    def test_case_insensitive_preexisting_temp_ledger_shadow_cannot_issue_proof(self):
        self.journal._db.execute('CREATE TEMP VIEW SCHEMA_MIGRATIONS AS SELECT * FROM main.schema_migrations')
        with self.assertRaises(RuntimePersistenceError):self.finish()

    def test_mixed_case_checkpoint_view_with_real_rowids_cannot_shadow_original_inventory(self):
        self.journal._db.execute('CREATE TEMP VIEW PaPeR_PrOcEsS_Checkpoints AS SELECT rowid AS rowid,* FROM main.paper_process_checkpoints')
        with self.assertRaises(RuntimePersistenceError):self.finish()


if __name__=='__main__':unittest.main()
