"""Actual SQLite immutable published prefix, not an imported audit permission."""
import sqlite3
import unittest

from storage.paper_process import open_paper_process_journal,PaperProcessJournal
from storage.paper_state_codec import CODEC
from storage.paper_state_codec import encode_state
from storage.runtime_models import RuntimeValidationError
from tests.storage import test_paper_process_journal as fixture


class PaperPublishedPrefixTests(unittest.TestCase):
    def setUp(self):
        self.helper=fixture.PaperProcessJournalTests();self.helper.setUp();self.addCleanup(self.helper.doCleanups)
        self.path=self.helper.path;self.journal=self.enterContext(open_paper_process_journal(self.path))

    def create(self):
        self.assertTrue(callable(getattr(self.journal,'audit_full',None)),
            'E6 has no explicit complete logical/history/published-prefix audit')
        return self.journal.create_run('run-1',self.helper.binding(),self.helper.state(),now=fixture.NOW,storage_profile=CODEC)

    def apply(self,number,*,publish=True):
        operation='tick-'+str(number)
        self.journal.prepare('run-1',operation,{'kind':'DEADLINE'},expected_revision=number-1,now=fixture.NOW)
        value=self.helper.state();value['runtime']['clock']=number
        applied=self.journal.complete('run-1',operation,value,{'status':'HOLD'},now=fixture.NOW)
        if publish:self.journal.mark_published('run-1',operation,applied.effect_hash,now=fixture.NOW)
        return applied

    def rows(self):
        return [tuple(row) for row in self.journal._db.execute('SELECT * FROM paper_process_published_prefixes ORDER BY revision')]

    def test_root_and_exact_publication_advance_once_not_on_intent_or_applied_effect(self):
        self.create();root=self.rows();self.assertEqual(len(root),1)
        self.journal.prepare('run-1','tick-1',{'kind':'DEADLINE'},expected_revision=0,now=fixture.NOW)
        self.assertEqual(self.rows(),root)
        applied=self.journal.complete('run-1','tick-1',self.helper.state(),{'status':'HOLD'},now=fixture.NOW)
        self.assertEqual(self.rows(),root)
        self.assertEqual(self.journal.audit_full('run-1').pending_operations,('tick-1',))
        self.journal.mark_published('run-1','tick-1',applied.effect_hash,now=fixture.NOW)
        published=self.rows();self.assertEqual(len(published),2)
        self.journal.mark_published('run-1','tick-1',applied.effect_hash,now=fixture.NOW)
        self.assertEqual(self.rows(),published)
        self.assertEqual(self.journal.audit_full('run-1').pending_operations,())

    def test_publication_and_prefix_roll_back_together_then_replay_original_effect(self):
        self.create();applied=self.apply(1,publish=False);db=self.journal._db
        db.execute("CREATE TRIGGER prefix_crash BEFORE INSERT ON paper_process_published_prefixes WHEN NEW.revision=1 BEGIN SELECT RAISE(ABORT,'controlled'); END")
        with self.assertRaises(RuntimeValidationError):
            self.journal.mark_published('run-1','tick-1',applied.effect_hash,now=fixture.NOW)
        self.assertEqual(self.journal.operation('run-1','tick-1').status,'APPLIED');self.assertEqual(len(self.rows()),1)
        db.execute('DROP TRIGGER prefix_crash')
        self.journal.mark_published('run-1','tick-1',applied.effect_hash,now=fixture.NOW)
        self.assertEqual(self.journal.audit_full('run-1').revision,1)

    def test_prefix_and_protocol_marker_forbid_update_delete_and_replace(self):
        self.create();self.apply(1);db=self.journal._db
        self.assertEqual(db.execute('PRAGMA recursive_triggers').fetchone()[0],0)
        for table in ('paper_process_prefix_profiles','paper_process_published_prefixes'):
            columns=[row[1] for row in db.execute('PRAGMA table_info('+table+')')]
            values=tuple(db.execute('SELECT * FROM '+table+' LIMIT 1').fetchone())
            field='profile' if table.endswith('profiles') else 'prefix_hash'
            for sql,args in (('UPDATE '+table+' SET '+field+'=?',('changed',)),('DELETE FROM '+table,()),
                    ('INSERT OR REPLACE INTO '+table+' VALUES('+','.join('?' for key in columns)+')',values)):
                with self.subTest(table=table,sql=sql),self.assertRaises(sqlite3.Error):db.execute(sql,args)
        self.assertEqual(self.journal.audit_full('run-1').revision,1)

    def test_missing_marked_root_or_altered_past_prefix_refuses_full_audit(self):
        self.create();self.apply(1);self.apply(2);db=self.journal._db
        trigger=db.execute("SELECT sql FROM sqlite_master WHERE name='paper_process_published_prefixes_no_update'").fetchone()[0]
        db.execute('DROP TRIGGER paper_process_published_prefixes_no_update')
        db.execute("UPDATE paper_process_published_prefixes SET prefix_hash=? WHERE revision=1",('sha256:'+'0'*64,))
        db.execute(trigger)
        with self.assertRaises(RuntimeValidationError):self.journal.audit_full('run-1')

    def test_missing_root_is_not_silently_downgraded_to_codec_only_profile(self):
        self.create();db=self.journal._db
        db.execute('DROP TRIGGER paper_process_published_prefixes_no_delete')
        db.execute('DELETE FROM paper_process_published_prefixes')
        with self.assertRaises(RuntimeValidationError):self.journal.audit_full('run-1')

    def test_old_unfinished_intent_cannot_hide_behind_indexed_prefix_tip(self):
        self.create();self.apply(1);db=self.journal._db
        row=db.execute('SELECT * FROM paper_process_operations LIMIT 1').fetchone()
        values=list(row);values[1]='controlled-old-unfinished'
        db.execute('INSERT INTO paper_process_operations VALUES(?,?,?,?,?,?)',values)
        with self.assertRaises(RuntimeValidationError):self.journal.audit_full('run-1')
        plan=db.execute('EXPLAIN QUERY PLAN SELECT operation_id FROM paper_process_operations WHERE run_id=? AND base_revision>=? ORDER BY base_revision,operation_id LIMIT 2',('run-1',1)).fetchall()
        self.assertTrue(any('paper_process_operations_base' in row[3] for row in plan))

    def test_codec_only_0025_run_is_preserved_without_automatic_prefix_upgrade(self):
        self.journal.close()
        from storage._sqlite_registry import _connect,_apply_migrations
        path=self.path.parent/'old-codec.sqlite';db=_connect(path)
        _apply_migrations(db,through_migration='0025_paper_state_storage_profiles.sql');db.isolation_level=None
        with PaperProcessJournal(db) as old:
            state=old.create_run('run-1',self.helper.binding(),self.helper.state(),now=fixture.NOW,storage_profile=CODEC)
        with open_paper_process_journal(path) as migrated:
            self.assertTrue(callable(getattr(migrated,'audit_full',None)),
                'E6 full audit API missing')
            self.assertEqual(migrated.audit_full('run-1').state,state.state)
            self.assertEqual(migrated._db.execute('SELECT count(*) FROM paper_process_prefix_profiles').fetchone()[0],0)
            self.assertEqual(migrated._db.execute('SELECT count(*) FROM paper_process_published_prefixes').fetchone()[0],0)

    def test_orphan_validly_encoded_current_checkpoint_is_not_complete_history(self):
        self.create();applied=self.apply(1);db=self.journal._db
        physical=encode_state(applied.state_json,run_id='run-1',revision=2)
        state_hash=db.execute('SELECT state_hash FROM paper_process_checkpoints WHERE revision=1').fetchone()[0]
        db.execute('PRAGMA foreign_keys=OFF')
        db.execute('INSERT INTO paper_process_checkpoints VALUES(?,?,?,?,?,?)',
            ('run-1',2,'controlled-orphan',physical,state_hash,'2026-10-03T00:00:00.000000Z'))
        db.execute('PRAGMA foreign_keys=ON')
        with self.assertRaises(RuntimeValidationError):self.journal.audit_full('run-1')

    def test_orphan_publication_cannot_be_ignored_by_complete_prefix_audit(self):
        self.create();self.apply(1);db=self.journal._db
        db.execute('PRAGMA foreign_keys=OFF')
        db.execute('INSERT INTO paper_process_publications VALUES(?,?,?,?)',
            ('run-1','controlled-orphan','sha256:'+'0'*64,'2026-10-03T00:00:00.000000Z'))
        db.execute('PRAGMA foreign_keys=ON')
        with self.assertRaises(RuntimeValidationError):self.journal.audit_full('run-1')

    def test_root_commits_original_run_and_both_profile_selection_clocks(self):
        self.create();db=self.journal._db
        for table in ('paper_process_runs','paper_process_storage_profiles','paper_process_prefix_profiles'):
            trigger_name=table+'_no_update'
            trigger=db.execute('SELECT sql FROM sqlite_master WHERE name=?',(trigger_name,)).fetchone()[0]
            original=db.execute('SELECT created_at FROM '+table+' WHERE run_id=?',('run-1',)).fetchone()[0]
            db.execute('DROP TRIGGER '+trigger_name)
            db.execute('UPDATE '+table+' SET created_at=? WHERE run_id=?',('2026-10-04T00:00:00.000000Z','run-1'))
            db.execute(trigger)
            with self.subTest(table=table),self.assertRaises(RuntimeValidationError):self.journal.audit_full('run-1')
            db.execute('DROP TRIGGER '+trigger_name)
            db.execute('UPDATE '+table+' SET created_at=? WHERE run_id=?',(original,'run-1'))
            db.execute(trigger)

    def test_operation_and_effect_clocks_are_bound_to_the_published_prefix(self):
        self.create();self.apply(1);db=self.journal._db
        for table,field in (('paper_process_operations','prepared_at'),('paper_process_effects','completed_at')):
            trigger_name=table+'_no_update'
            trigger=db.execute('SELECT sql FROM sqlite_master WHERE name=?',(trigger_name,)).fetchone()[0]
            original=db.execute('SELECT '+field+' FROM '+table+' LIMIT 1').fetchone()[0]
            db.execute('DROP TRIGGER '+trigger_name)
            db.execute('UPDATE '+table+' SET '+field+'=?',('2026-10-04T00:00:00.000000Z',))
            db.execute(trigger)
            with self.subTest(table=table),self.assertRaises(RuntimeValidationError):self.journal.audit_full('run-1')
            db.execute('DROP TRIGGER '+trigger_name)
            db.execute('UPDATE '+table+' SET '+field+'=?',(original,))
            db.execute(trigger)
