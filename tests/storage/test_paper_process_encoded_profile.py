"""Actual isolated E6 SQLite profiles; all original journal contracts rerun."""
from copy import deepcopy
import hashlib
import inspect
import json
import sqlite3
from unittest.mock import patch
from contextlib import closing

from storage.paper_state_codec import CODEC
from storage.runtime_models import RuntimeConflictError,RuntimeValidationError
from tests.storage import test_paper_process_journal as original


class PaperProcessEncodedProfileTests(original.PaperProcessJournalTests):
    def create(self,journal):
        self.assertIn('storage_profile',inspect.signature(journal.create_run).parameters,
            'New E6 run cannot explicitly select the immutable physical storage profile')
        return journal.create_run('run-1',self.binding(),self.state(),now=original.NOW,storage_profile=CODEC)

    def test_physical_envelope_preserves_logical_state_and_effect_identity_after_reopen(self):
        with self.journal() as journal:
            self.create(journal);state=self.state();state['runtime']['clock']=1
            journal.prepare('run-1','one',{'kind':'DEADLINE'},expected_revision=0,now=original.NOW)
            applied=journal.complete('run-1','one',state,{'status':'HOLD'},now=original.NOW)
            row=journal._db.execute('SELECT * FROM paper_process_checkpoints WHERE revision=1').fetchone()
            self.assertEqual(json.loads(row['state_json'])['codec'],CODEC)
            self.assertNotEqual(row['state_json'],applied.state_json)
            self.assertEqual(row['state_hash'],'sha256:'+hashlib.sha256(applied.state_json.encode()).hexdigest())
        with self.journal() as journal:
            recovered=journal.recover('run-1');self.assertEqual(recovered.state,state)
            self.assertEqual(journal.operation('run-1','one'),applied)

    def test_profile_is_immutable_even_with_replace_and_recursive_triggers_off(self):
        with self.journal() as journal:
            self.create(journal)
            statements=["UPDATE paper_process_storage_profiles SET profile='r7-paper-state-json-v0.1'",
                'DELETE FROM paper_process_storage_profiles',
                "INSERT OR REPLACE INTO paper_process_storage_profiles VALUES ('run-1','r7-paper-state-zlib-delta-v0.1','2026-10-03T00:00:00.000000Z')"]
            for statement in statements:
                with self.subTest(statement=statement),self.assertRaises(sqlite3.Error):journal._db.execute(statement)
            self.assertEqual(journal.recover('run-1').revision,0)
            with self.assertRaises(RuntimeConflictError):
                journal.create_run('run-1',self.binding(),self.state(),now=original.NOW,storage_profile='r7-paper-state-json-v0.1')
            self.assertEqual(journal.create_run('run-1',self.binding(),self.state(),now=original.NOW).revision,0)

    def test_initial_profile_and_checkpoint_rollback_together(self):
        with self.journal() as journal:
            journal._db.execute("CREATE TRIGGER fail_initial BEFORE INSERT ON paper_process_checkpoints "
                "WHEN NEW.revision=0 BEGIN SELECT RAISE(ABORT,'controlled'); END")
            with self.assertRaises(RuntimeValidationError):self.create(journal)
            self.assertEqual(journal._db.execute('SELECT count(*) FROM paper_process_runs').fetchone()[0],0)
            self.assertEqual(journal._db.execute('SELECT count(*) FROM paper_process_storage_profiles').fetchone()[0],0)

    def test_existing_legacy_run_cannot_be_silently_upgraded_or_gain_profile_marker(self):
        with self.journal() as journal:
            initial=journal.create_run('run-1',self.binding(),self.state(),now=original.NOW)
            raw=journal._db.execute('SELECT state_json FROM paper_process_checkpoints').fetchone()[0]
            self.assertEqual(raw,initial.state_json)
            with self.assertRaises(RuntimeConflictError):self.create(journal)
            with self.assertRaises(sqlite3.Error):
                journal._db.execute('INSERT INTO paper_process_storage_profiles VALUES (?,?,?)',
                    ('run-1',CODEC,'2026-10-03T00:00:00.000000Z'))
            self.assertEqual(journal.recover('run-1'),initial)

    def test_corrupt_historical_physical_row_refuses_full_recovery_even_with_independent_current_keyframe(self):
        with self.journal() as journal:
            self.create(journal)
            journal.prepare('run-1','one',{'kind':'DEADLINE'},expected_revision=0,now=original.NOW)
            applied=journal.complete('run-1','one',self.state(),{'status':'HOLD'},now=original.NOW)
            journal.mark_published('run-1','one',applied.effect_hash,now=original.NOW)
            with closing(sqlite3.connect(self.path)) as external,external:
                external.execute('DROP TRIGGER paper_process_checkpoints_no_update')
                external.execute("UPDATE paper_process_checkpoints SET state_json='{}' WHERE revision=0")
            with self.assertRaises(RuntimeValidationError):journal.recover('run-1')

    def test_changed_profile_type_or_unsupported_version_refuses_before_run_creation(self):
        with self.journal() as journal:
            self.create(journal)
            for value in ({},True,'future-v99'):
                with self.subTest(profile=value),self.assertRaises(RuntimeValidationError):
                    journal.create_run('other',self.binding(),self.state(),now=original.NOW,storage_profile=value)
            self.assertEqual(journal._db.execute('SELECT count(*) FROM paper_process_runs').fetchone()[0],1)

    def test_deltas_save_actual_sqlite_checkpoint_text_without_losing_any_revision(self):
        with self.journal() as journal:
            self.create(journal);previous=self.state()
            previous['runtime']['bars']=[{'at':i,'price':str(60000+i),'tag':hashlib.sha256(str(i).encode()).hexdigest()} for i in range(200)]
            logical_bytes=0
            for revision in range(1,17):
                state=deepcopy(previous);state['runtime']['clock']=revision
                operation='tick-'+str(revision)
                journal.prepare('run-1',operation,{'kind':'DEADLINE'},expected_revision=revision-1,now=original.NOW)
                completed=journal.complete('run-1',operation,state,{'status':'HOLD'},now=original.NOW)
                journal.mark_published('run-1',operation,completed.effect_hash,now=original.NOW)
                self.assertEqual(completed.state,state);logical_bytes+=len(completed.state_json.encode());previous=state
            retained=journal._db.execute('SELECT sum(length(CAST(state_json AS BLOB))) FROM paper_process_checkpoints').fetchone()[0]
            self.assertLess(retained,logical_bytes//4)
            self.assertEqual(journal.recover('run-1').revision,16)
            self.assertEqual(journal.recover('run-1').state,state)

    def test_identical_logical_effects_keep_exact_hashes_across_legacy_and_encoded_profiles(self):
        results=[];base=self.path
        for profile in (None,CODEC):
            self.path=base.parent/('legacy.sqlite' if profile is None else 'encoded.sqlite')
            with self.journal() as journal:
                journal.create_run('run-1',self.binding(),self.state(),now=original.NOW,storage_profile=profile)
                journal.prepare('run-1','one',{'kind':'DEADLINE'},expected_revision=0,now=original.NOW)
                applied=journal.complete('run-1','one',self.state(),{'status':'HOLD'},now=original.NOW)
                journal.mark_published('run-1','one',applied.effect_hash,now=original.NOW)
                results.append((journal.operation('run-1','one'),journal.recover('run-1')))
        self.assertEqual(results[0],results[1])

    def test_readonly_logical_reader_accepts_actual_0024_store_without_migrating_it(self):
        from storage._sqlite_registry import _connect,_apply_migrations
        from storage.paper_process import PaperProcessJournal,read_paper_checkpoint
        from storage.qualification import _readonly_uri
        db=_connect(self.path);_apply_migrations(db,through_migration='0024_product_original_exit.sql');db.isolation_level=None
        with PaperProcessJournal(db) as journal:
            original_state=journal.create_run('old-run',self.binding(),self.state(),now=original.NOW)
        with closing(sqlite3.connect(_readonly_uri(self.path),uri=True)) as reader:
            reader.row_factory=sqlite3.Row
            before=tuple(tuple(row) for row in reader.execute('SELECT * FROM schema_migrations ORDER BY migration_name'))
            checkpoint=read_paper_checkpoint(reader,'old-run')
            after=tuple(tuple(row) for row in reader.execute('SELECT * FROM schema_migrations ORDER BY migration_name'))
            self.assertEqual(checkpoint['state_json'],original_state.state_json)
            self.assertEqual(before,after)
            self.assertEqual(before[-1][0],'0024_product_original_exit.sql')
            self.assertIsNone(reader.execute("SELECT 1 FROM sqlite_master WHERE name='paper_process_storage_profiles'").fetchone())

    def test_wrong_encoded_effect_state_rolls_back_before_unreadable_checkpoint_is_committed(self):
        from storage.paper_state_codec import encode_state
        with self.journal() as journal:
            self.create(journal)
            journal.prepare('run-1','one',{'kind':'DEADLINE'},expected_revision=0,now=original.NOW)
            def wrong(raw,**kwargs):
                value=json.loads(raw);value['runtime']['controlled_encoder_fault']=True
                return encode_state(json.dumps(value,sort_keys=True,separators=(',',':')),**kwargs)
            with patch('storage.paper_process.encode_state',side_effect=wrong),self.assertRaises(RuntimeValidationError):
                journal.complete('run-1','one',self.state(),{'status':'HOLD'},now=original.NOW)
            self.assertEqual(journal._db.execute('SELECT count(*) FROM paper_process_effects').fetchone()[0],0,
                'A codec mismatch was detected only AFTER committing an unreadable immutable effect')
            self.assertEqual(journal.operation('run-1','one').status,'PREPARED')
            self.assertEqual(journal.recover('run-1').revision,0)
