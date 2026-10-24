"""Reuse verified bytes only within one exact SQLite source epoch."""
import hashlib
import unittest
from unittest.mock import patch

from storage import paper_process as process
from storage.runtime_models import RuntimePersistenceError
from tests.storage import test_paper_process_prefix as fixture
from tests.storage.test_paper_process_journal import NOW


class PaperCheckpointCacheTests(unittest.TestCase):
    def setUp(self):
        self.helper=fixture.PaperPublishedPrefixTests();self.helper.setUp();self.addCleanup(self.helper.doCleanups)
        self.helper.create();self.journal=self.helper.journal
        for number in range(1,4):
            operation='tick-'+str(number);state=self.helper.helper.state()
            state['runtime'].update(clock=number,noise=[hashlib.sha256(str(i).encode()).hexdigest() for i in range(128)])
            self.journal.prepare('run-1',operation,{},expected_revision=number-1,now=NOW)
            applied=self.journal.complete('run-1',operation,state,{},now=NOW)
            self.journal.mark_published('run-1',operation,applied.effect_hash,now=NOW)

    def test_repeated_management_reads_reuse_verified_state_in_same_actual_source_epoch(self):
        with patch.object(process,'read_paper_checkpoint',wraps=process.read_paper_checkpoint) as decode:
            first=self.journal.recover_current('run-1');before=decode.call_count
            second=self.journal.recover_current('run-1')
            self.assertEqual(second,first)
            self.assertEqual(decode.call_count,before,'Same current chain decoded repeatedly in unchanged SQLite epoch')
        direct=process.read_paper_checkpoint(self.journal._db,'run-1')
        self.assertEqual(second.state_json,direct['state_json'])
        self.assertFalse(self.journal.history_audit_ready('run-1'))

    def test_unknown_own_mutation_forces_fresh_decode_without_granting_history_permission(self):
        db=self.journal._db;db.execute('CREATE TABLE controlled_counter(value INTEGER)')
        self.journal.recover_current('run-1')
        db.execute('INSERT INTO controlled_counter VALUES(1)')
        with patch.object(process,'read_paper_checkpoint',wraps=process.read_paper_checkpoint) as decode:
            self.journal.recover_current('run-1');self.assertGreater(decode.call_count,0)
        self.assertFalse(self.journal.history_audit_ready('run-1'))

    def test_altered_ancestor_cannot_hide_behind_cached_current_or_repeated_metadata(self):
        self.journal.recover_current('run-1');db=self.journal._db
        trigger=db.execute("SELECT sql FROM sqlite_master WHERE name='paper_process_checkpoints_no_update'").fetchone()[0]
        db.execute('DROP TRIGGER paper_process_checkpoints_no_update')
        db.execute("UPDATE paper_process_checkpoints SET state_json='{}' WHERE revision=2")
        db.execute(trigger)
        with self.assertRaises(RuntimePersistenceError):self.journal.recover_current('run-1')
        with self.assertRaises(RuntimePersistenceError):self.journal.audit_full('run-1')

    def test_returned_metadata_is_not_a_mutable_cache_or_a_permission_input(self):
        first=self.journal._checkpoint('run-1');expected=first['state_json']
        first['state_json']='{}';first['state_hash']='sha256:'+'0'*64
        self.assertEqual(self.journal._checkpoint('run-1')['state_json'],expected)
        self.assertFalse(self.journal.history_audit_ready('run-1'))

    def test_observed_trusted_append_keeps_already_verified_immutable_base_bytes(self):
        for _ in range(100):
            self.journal.history_audit_step('run-1',maximum_rows=8)
            if self.journal.history_audit_ready('run-1'):break
        self.assertTrue(self.journal.history_audit_ready('run-1'))
        self.journal.recover_current('run-1')
        with patch.object(process,'read_paper_checkpoint',wraps=process.read_paper_checkpoint) as decode:
            self.journal.prepare('run-1','tick-4',{},expected_revision=3,now=NOW)
            self.assertEqual(decode.call_count,0,'Trusted INSERT decoded unchanged original chain again')
        self.assertTrue(self.journal.history_audit_ready('run-1'))

    def test_unexpected_trigger_dml_even_on_allowed_table_never_extends_private_proof(self):
        db=self.journal._db
        db.execute('''CREATE TEMP TRIGGER controlled_attempt BEFORE INSERT ON main.paper_process_publications
            BEGIN INSERT INTO paper_process_publications SELECT * FROM paper_process_publications WHERE operation_id='never'; END''')
        for _ in range(100):
            self.journal.history_audit_step('run-1',maximum_rows=8)
            if self.journal.history_audit_ready('run-1'):break
        self.assertTrue(self.journal.history_audit_ready('run-1'))
        operation=self.journal.operation('run-1','tick-3')
        self.journal.mark_published('run-1','tick-3',operation.effect_hash,now=NOW)
        self.assertFalse(self.journal.history_audit_ready('run-1'))
        self.assertEqual(self.journal.recover_current('run-1').revision,3)


if __name__=='__main__':unittest.main()
