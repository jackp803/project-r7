"""Bounded current facts are explicitly NOT a historical audit or entry lease."""
import unittest
from unittest.mock import patch

from brokers.paper import PaperBroker
from storage.paper_process import open_paper_process_journal,PaperProcessJournal
from storage.paper_state_codec import CODEC
from storage.runtime_models import RuntimeValidationError
from tests.storage import test_paper_process_prefix as prefix_fixture
from tests.storage.test_paper_process_journal import NOW


class PaperCurrentRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.helper=prefix_fixture.PaperPublishedPrefixTests();self.helper.setUp();self.addCleanup(self.helper.doCleanups)
        self.helper.create();self.journal=self.helper.journal

    def current(self):
        self.assertTrue(callable(getattr(self.journal,'recover_current',None)),
            'Bounded current E6 management recovery is not implemented')
        return self.journal.recover_current('run-1')

    def test_current_facts_do_not_enumerate_old_operations_or_claim_full_history(self):
        for number in range(1,21):self.helper.apply(number)
        queries=[];self.journal._db.set_trace_callback(queries.append)
        with (patch.object(self.journal,'recover',side_effect=AssertionError('No hot full audit')),
                patch.object(self.journal._prefixes,'audit_operation',side_effect=AssertionError('No old-operation scan'))):
            recovered=self.current()
        self.journal._db.set_trace_callback(None)
        self.assertEqual(recovered.revision,20)
        self.assertEqual(recovered.history_verification,'CURRENT_FACTS_ONLY')
        self.assertEqual(recovered.pending_operations,())
        self.assertFalse(any('SELECT operation_id FROM paper_process_operations WHERE' in query for query in queries))

    def test_prepared_and_applied_tail_keep_exact_original_pending_identity(self):
        self.journal.prepare('run-1','tick-1',{'kind':'DEADLINE'},expected_revision=0,now=NOW)
        prepared=self.current();self.assertEqual(prepared.revision,0)
        self.assertEqual(prepared.status,'PREPARED_PENDING');self.assertEqual(prepared.pending_operations,('tick-1',))
        applied=self.journal.complete('run-1','tick-1',self.helper.helper.state(),{'status':'HOLD'},now=NOW)
        current=self.current();self.assertEqual(current.revision,1)
        self.assertEqual(current.status,'PUBLICATION_PENDING');self.assertEqual(current.pending_operations,('tick-1',))
        self.journal.mark_published('run-1','tick-1',applied.effect_hash,now=NOW)
        self.assertEqual(self.current().pending_operations,())

    def test_old_corruption_is_not_disguised_as_full_audit_by_valid_current_facts(self):
        for number in range(1,4):self.helper.apply(number)
        db=self.journal._db
        trigger=db.execute("SELECT sql FROM sqlite_master WHERE name='paper_process_published_prefixes_no_update'").fetchone()[0]
        db.execute('DROP TRIGGER paper_process_published_prefixes_no_update')
        db.execute("UPDATE paper_process_published_prefixes SET prefix_hash=? WHERE revision=1",('sha256:'+'0'*64,))
        db.execute(trigger)
        current=self.current();self.assertEqual(current.history_verification,'CURRENT_FACTS_ONLY')
        with self.assertRaises(RuntimeValidationError):self.journal.audit_full('run-1')

    def test_current_tip_corruption_and_missing_marked_root_refuse(self):
        self.helper.apply(1);db=self.journal._db
        db.execute('DROP TRIGGER paper_process_published_prefixes_no_update')
        db.execute('UPDATE paper_process_published_prefixes SET prefix_hash=? WHERE revision=1',('sha256:'+'0'*64,))
        with self.assertRaises(RuntimeValidationError):self.current()
        db.execute('DROP TRIGGER paper_process_published_prefixes_no_delete')
        db.execute('DELETE FROM paper_process_published_prefixes')
        with self.assertRaises(RuntimeValidationError):self.current()

    def test_concurrent_valid_append_cannot_mix_snapshot_state_and_pending_tail(self):
        self.helper.apply(1)
        self.assertTrue(callable(getattr(self.journal._prefixes,'current_context',None)),
            'Bounded current prefix context is not implemented')
        original=self.journal._prefixes.current_context
        with open_paper_process_journal(self.helper.path) as writer:
            def append_after_tip(run_id):
                result=original(run_id)
                writer.prepare('run-1','tick-2',{'kind':'DEADLINE'},expected_revision=1,now=NOW)
                applied=writer.complete('run-1','tick-2',self.helper.helper.state(),{'status':'HOLD'},now=NOW)
                writer.mark_published('run-1','tick-2',applied.effect_hash,now=NOW)
                return result
            with patch.object(self.journal._prefixes,'current_context',side_effect=append_after_tip):
                self.assertEqual(self.current().revision,1)
        self.assertEqual(self.current().revision,2)

    def test_broker_domain_validation_occurs_after_read_snapshot_is_released(self):
        self.helper.apply(1);original=PaperBroker.from_state
        def validate(value):
            self.assertFalse(self.journal._db.in_transaction)
            return original(value)
        with patch.object(PaperBroker,'from_state',side_effect=validate):self.current()

    def test_codec_only_old_profile_cannot_be_mislabeled_bounded_recovery(self):
        from storage._sqlite_registry import _connect,_apply_migrations
        path=self.helper.path.parent/'old-codec-current.sqlite';db=_connect(path)
        _apply_migrations(db,through_migration='0025_paper_state_storage_profiles.sql');db.isolation_level=None
        with PaperProcessJournal(db) as old:
            old.create_run('run-1',self.helper.helper.binding(),self.helper.helper.state(),now=NOW,storage_profile=CODEC)
        with open_paper_process_journal(path) as upgraded:
            self.assertTrue(callable(getattr(upgraded,'recover_current',None)),
                'Bounded current recovery API missing')
            with self.assertRaises(RuntimeValidationError):upgraded.recover_current('run-1')
            self.assertEqual(upgraded.audit_full('run-1').revision,0)
