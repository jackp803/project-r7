"""Actual owned readonly audit process; no provider/native/elapsed credit."""
import importlib
import sqlite3
import sys
import time
import unittest
from unittest.mock import patch

from tests.storage import test_paper_history_audit as fixture


class PaperHistoryWorkerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('storage.paper_history_worker'),
            'No independent owned Paper history auditor')
        self.module=importlib.import_module('storage.paper_history_worker')
        self.helper=fixture.PaperHistoryAuditTests();self.helper.setUp();self.addCleanup(self.helper.doCleanups)
        self.journal=self.helper.journal
        self.worker=self.module.OwnedPaperHistoryAudit(self.journal);self.addCleanup(self.worker.close)

    def complete(self):
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            result=self.worker.poll('run-1')
            if result.status not in ('HISTORY_AUDIT_REQUIRED','HISTORY_AUDIT_IN_PROGRESS'):return result
            time.sleep(.02)
        self.fail('Actual local owned audit did not complete within test deadline')

    def test_actual_readonly_child_can_extend_only_its_launching_owner_after_known_appends(self):
        for number in range(1,4):self.helper.helper.apply(number)
        self.worker.start('run-1')
        self.helper.helper.apply(4)
        result=self.complete()
        self.assertEqual(result.status,'HISTORY_VERIFIED_IN_CURRENT_INSTANCE')
        self.assertEqual(result.verified_prefix_revision,4)
        self.assertTrue(self.journal.history_audit_ready('run-1'))
        self.assertEqual(self.journal.recover_current('run-1').revision,4)
        self.assertTrue(self.worker.summary()['reaped'])
        self.assertEqual(self.worker.summary()['snapshot_writes'],0)

    def test_unknown_same_connection_write_revokes_actual_child_result(self):
        self.journal._db.execute('CREATE TABLE controlled_counter(value INTEGER)')
        self.worker.start('run-1')
        self.journal._db.execute('INSERT INTO controlled_counter VALUES(1)')
        deadline=time.monotonic()+20
        while self.worker.summary()['active'] and time.monotonic()<deadline:
            self.worker.poll('run-1');time.sleep(.02)
        self.assertFalse(self.journal.history_audit_ready('run-1'))
        self.assertNotEqual(self.worker.poll('run-1').status,'HISTORY_VERIFIED_IN_CURRENT_INSTANCE')

    def test_corrupt_old_prefix_child_refuses_without_disabling_current_management(self):
        for number in range(1,4):self.helper.helper.apply(number)
        db=self.journal._db
        trigger=db.execute("SELECT sql FROM sqlite_master WHERE name='paper_process_published_prefixes_no_update'").fetchone()[0]
        db.execute('DROP TRIGGER paper_process_published_prefixes_no_update')
        db.execute('UPDATE paper_process_published_prefixes SET prefix_hash=? WHERE revision=1',('sha256:'+'0'*64,))
        db.execute(trigger)
        self.worker.start('run-1');result=self.complete()
        self.assertEqual(result.status,'HISTORY_AUDIT_FAILED')
        self.assertFalse(self.journal.history_audit_ready('run-1'))
        self.assertEqual(self.journal.recover_current('run-1').revision,3)

    def test_close_cancels_and_reaps_only_the_owned_process_without_importing_a_proof(self):
        self.worker.start('run-1');self.worker.close()
        self.assertFalse(self.worker.summary()['active'])
        self.assertTrue(self.worker.summary()['reaped'])
        self.assertFalse(self.journal.history_audit_ready('run-1'))
        self.helper.helper.apply(1)

    def test_failed_reap_keeps_real_child_handle_and_blocks_successor_until_close_retries(self):
        original_spawn=self.module.spawn_owned;original_terminate=self.module.terminate_owned;handles=[];calls=[]
        from application.platform.processes import TerminationReport
        def sleeping_child(argv,**options):
            owned=original_spawn([sys.executable,'-c','import time;time.sleep(120)'],**options)
            handles.append(owned);self.addCleanup(lambda:original_terminate(owned,deadline_seconds=5))
            return owned
        def refuse_twice(owned,**options):
            calls.append(owned)
            if len(calls)<=2:return TerminationReport(True,False,'CONTROLLED_REAP_REFUSAL')
            return original_terminate(owned,**options)
        with patch.object(self.module,'spawn_owned',side_effect=sleeping_child),patch.object(self.module,'terminate_owned',side_effect=refuse_twice):
            self.worker.start('run-1');session=self.worker._session
            deadline=time.monotonic()+5
            while session.handle is None and time.monotonic()<deadline:time.sleep(.02)
            self.assertIsNotNone(session.handle)
            session.cancel.set();session.thread.join(timeout=5)
            self.assertTrue(session.done);self.assertFalse(session.reaped)
            with self.assertRaises(RuntimeError):self.worker.poll('run-1')
            self.assertIs(self.worker._session,session,'Failed reap discarded actual process handle')
            with self.assertRaises(RuntimeError):self.worker.start('run-1')
            with self.assertRaises(RuntimeError):self.worker.close()
            self.assertIs(self.worker._session,session)
            self.worker.close()
            self.assertTrue(self.worker.summary()['reaped'])
            self.assertEqual(len(handles),1)
            self.assertFalse(self.journal.history_audit_ready('run-1'))
            self.helper.helper.apply(1)

    def test_thread_start_failure_unwinds_only_its_unstarted_session_and_leaves_owner_closable(self):
        with patch.object(self.module.threading.Thread,'start',side_effect=RuntimeError('controlled thread startup refusal')):
            with self.assertRaises(RuntimeError):self.worker.start('run-1')
        self.assertFalse(self.worker.summary()['active'])
        self.assertIsNone(self.worker._session)
        self.assertFalse(self.journal.history_audit_ready('run-1'))
        self.worker.close();self.helper.helper.apply(1)

    def test_actual_child_packet_with_foreign_session_identity_cannot_grant_owner_eligibility(self):
        self.worker.start('run-1');session=self.worker._session
        session.thread.join(timeout=20)
        self.assertTrue(session.done);self.assertTrue(session.reaped)
        self.assertIsInstance(session.result,dict)
        session.result['session_id']='0'*32
        self.assertEqual(self.worker.poll('run-1').status,'HISTORY_AUDIT_FAILED')
        self.assertFalse(self.journal.history_audit_ready('run-1'))

    def test_actual_external_commit_during_worker_invalidates_parent_extension(self):
        self.journal._db.execute('CREATE TABLE controlled_counter(value INTEGER)')
        self.worker.start('run-1');session=self.worker._session
        with sqlite3.connect(self.helper.helper.path) as external:
            external.execute('INSERT INTO controlled_counter VALUES(1)')
        session.thread.join(timeout=20)
        self.assertTrue(session.done);self.assertTrue(session.reaped)
        self.assertEqual(self.worker.poll('run-1').status,'HISTORY_AUDIT_REQUIRED')
        self.assertFalse(self.journal.history_audit_ready('run-1'))


if __name__=='__main__':unittest.main()
