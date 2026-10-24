"""Reuse verified bytes only within one exact SQLite source epoch."""
import hashlib
import unittest
from unittest.mock import patch
import inspect
import json

from storage import paper_process as process
from storage import paper_state_codec as codec
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
        with patch.object(process,'_read_paper_checkpoint_record',wraps=process._read_paper_checkpoint_record) as decode:
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
        with patch.object(process,'_read_paper_checkpoint_record',wraps=process._read_paper_checkpoint_record) as decode:
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
        with patch.object(process,'_read_paper_checkpoint_record',wraps=process._read_paper_checkpoint_record) as decode:
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

    def test_fresh_same_epoch_reader_verifies_successor_without_replaying_verified_ancestors(self):
        with process.open_paper_process_journal(self.helper.path) as reader:
            previous=reader._checkpoint('run-1',2)
            with patch.object(codec,'_unpack',wraps=codec._unpack) as unpack:
                current=reader._checkpoint('run-1',3)
                self.assertEqual(unpack.call_count,1,'Original ancestors decoded again after actual source verification')
            self.assertEqual(current['state_json'],process.read_paper_checkpoint(reader._db,'run-1',3)['state_json'])
            self.assertNotEqual(previous['state_hash'],current['state_hash'])
            self.assertFalse(reader.history_audit_ready('run-1'))

    def test_public_reader_stays_plain_complete_and_has_no_base_proof_input(self):
        self.assertEqual(list(inspect.signature(process.read_paper_checkpoint).parameters),['connection','run_id','revision'])
        with patch.object(codec,'_unpack',wraps=codec._unpack) as unpack:
            current=process.read_paper_checkpoint(self.journal._db,'run-1',3)
            self.assertGreater(unpack.call_count,1)
        self.assertIs(type(current),dict)
        self.assertEqual(set(current),{'run_id','revision','operation_id','state_json','state_hash','recorded_at'})

    def test_fresh_current_reuses_predecessors_already_reconstructed_from_actual_source(self):
        with process.open_paper_process_journal(self.helper.path) as reader:
            with patch.object(codec,'_unpack',wraps=codec._unpack) as unpack:
                current=reader.recover_current('run-1')
            revisions=[call.args[2] for call in unpack.call_args_list]
            self.assertEqual(current.revision,3)
            for revision in (1,2,3):
                self.assertEqual(revisions.count(revision),1,'Already reconstructed predecessor decoded again')
            self.assertFalse(reader.history_audit_ready('run-1'))

    def test_applied_tail_reuses_two_predecessors_without_history_permission(self):
        state=json.loads(self.journal._checkpoint('run-1',3)['state_json']);state['runtime']['clock']=4
        self.journal.prepare('run-1','tick-4',{},expected_revision=3,now=NOW)
        self.journal.complete('run-1','tick-4',state,{},now=NOW)
        with process.open_paper_process_journal(self.helper.path) as reader:
            with patch.object(codec,'_unpack',wraps=codec._unpack) as unpack:
                current=reader.recover_current('run-1')
            revisions=[call.args[2] for call in unpack.call_args_list]
            self.assertEqual(current.status,'PUBLICATION_PENDING')
            for revision in (1,2,3,4):self.assertEqual(revisions.count(revision),1)
            self.assertFalse(reader.history_audit_ready('run-1'))

    def test_retained_predecessors_keep_individual_metadata_bounds_and_eviction(self):
        with process.open_paper_process_journal(self.helper.path) as reader:
            reader._checkpoint('run-1',3)
            self.assertEqual(set(reader._checkpoint_cache),{('run-1',1),('run-1',2),('run-1',3)})
            for (run,revision),(row,size,record) in reader._checkpoint_cache.items():
                self.assertEqual(row,process.read_paper_checkpoint(reader._db,run,revision))
                self.assertEqual((record.revision,record.state_hash),(revision,row['state_hash']))
                self.assertEqual(record.chain_links,revision+1)
                self.assertGreater(record.chain_payload_bytes,0)
                self.assertEqual(size,sum(len(value.encode('utf-8')) for value in row.values() if type(value) is str))
            size=reader._checkpoint_cache[('run-1',3)][1]
        with process.open_paper_process_journal(self.helper.path) as reader:
            with patch.object(process,'_CHECKPOINT_CACHE_MAX_BYTES',size):reader._checkpoint('run-1',3)
            self.assertLessEqual(reader._checkpoint_cache_bytes,size)
            self.assertEqual(list(reader._checkpoint_cache),[('run-1',3)])

    def test_optional_invalid_historical_payload_is_not_cached_or_a_new_current_gate(self):
        db=self.journal._db
        originals=[process.read_paper_checkpoint(db,'run-1',rev) for rev in range(4)]
        altered=json.loads(originals[1]['state_json']);altered['runtime']['credentials']='forbidden'
        raw=json.dumps(altered,sort_keys=True,separators=(',',':'),ensure_ascii=False)
        trigger=db.execute("SELECT sql FROM sqlite_master WHERE name='paper_process_checkpoints_no_update'").fetchone()[0]
        db.execute('DROP TRIGGER paper_process_checkpoints_no_update')
        previous=originals[0]['state_json']
        for rev in range(1,4):
            current=raw if rev==1 else originals[rev]['state_json']
            encoded=codec.encode_state(current,run_id='run-1',revision=rev,previous_raw=previous)
            db.execute('UPDATE paper_process_checkpoints SET state_json=?,state_hash=? WHERE run_id=? AND revision=?',
                (encoded,process._digest(current),'run-1',rev));previous=current
        db.execute(trigger)
        with process.open_paper_process_journal(self.helper.path) as reader:
            self.assertEqual(reader._checkpoint('run-1',3)['state_json'],originals[3]['state_json'])
            self.assertNotIn(('run-1',1),reader._checkpoint_cache)
            with self.assertRaises(RuntimePersistenceError):reader._checkpoint('run-1',1)


if __name__=='__main__':unittest.main()
