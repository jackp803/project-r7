"""Trusted sequential E6 reuse, with original per-fact commits and ownership."""
import sqlite3
import unittest
from unittest.mock import patch

from storage.runtime import open_paper_runtime_journal
from storage.runtime_models import RuntimePersistenceError
from tests.storage import test_paper_history_audit as audit_fixture
from tests.storage.test_paper_process_journal import NOW
from tests.storage.test_paper_runtime_durability import risk_decision,approved_plan


class PaperBorrowedCanonicalTests(unittest.TestCase):
    def setUp(self):
        self.audit=audit_fixture.PaperHistoryAuditTests();self.audit.setUp();self.addCleanup(self.audit.doCleanups)
        self.process=self.audit.journal;self.db=self.process._db
        self.assertTrue(callable(getattr(self.process,'borrow_canonical_journal',None)),
            'Trusted non-owning canonical facade missing')

    def test_success_and_exact_replay_keep_process_connection_idle_and_audit_valid(self):
        self.audit.finish();mode=self.db.isolation_level
        with self.process.borrow_canonical_journal() as canonical:
            first=canonical.persist_risk_decision(risk_decision())
            self.assertEqual(canonical.persist_risk_decision(risk_decision()),first)
            self.assertFalse(self.db.in_transaction)
            self.assertTrue(self.process.history_audit_ready('run-1'))
            self.audit.helper.apply(1)
            self.assertTrue(self.process.history_audit_ready('run-1'))
        self.assertEqual(self.db.isolation_level,mode)
        self.assertEqual(self.process.recover_current('run-1').revision,1)
        with self.assertRaises(RuntimePersistenceError):canonical.persist_risk_decision(risk_decision())

    def test_actual_missing_parent_error_rolls_back_before_process_writer_resumes(self):
        with self.process.borrow_canonical_journal() as canonical:
            with self.assertRaises(RuntimePersistenceError):canonical.persist_approved_trade_plan(approved_plan())
            self.assertFalse(self.db.in_transaction,'Canonical validation failure left lender transaction active')
            self.audit.helper.apply(1)
            self.assertEqual(self.process.recover_current('run-1').revision,1)

    def test_active_lender_transaction_rejected_without_rollback_or_commit(self):
        with self.process.borrow_canonical_journal() as canonical:
            self.db.execute('CREATE TABLE controlled_lender(value INTEGER)')
            self.db.execute('BEGIN IMMEDIATE');self.db.execute('INSERT INTO controlled_lender VALUES(1)')
            try:
                with self.assertRaises(RuntimePersistenceError):canonical.persist_risk_decision(risk_decision())
                with self.assertRaises(RuntimePersistenceError):canonical.close()
                self.assertTrue(self.db.in_transaction)
                self.assertEqual(self.db.execute('SELECT count(*) FROM controlled_lender').fetchone()[0],1)
            finally:self.db.rollback()
            self.assertEqual(self.db.execute('SELECT count(*) FROM controlled_lender').fetchone()[0],0)

    def test_base_exception_rolls_back_actual_writer_and_revokes_history_proof(self):
        self.audit.finish()
        with self.process.borrow_canonical_journal() as canonical:
            def crash(*args):
                self.db.execute('BEGIN IMMEDIATE')
                self.db.execute("INSERT INTO paper_runtime_conflicts(reason_code,object_kind) VALUES('CONTROLLED','RISK_DECISION')")
                raise KeyboardInterrupt('controlled')
            with patch.object(canonical._store,'persist_immutable',side_effect=crash),self.assertRaises(KeyboardInterrupt):
                canonical.persist_risk_decision(risk_decision())
            self.assertFalse(self.db.in_transaction)
            self.assertEqual(self.db.execute('SELECT count(*) FROM paper_runtime_conflicts').fetchone()[0],0)
            self.assertFalse(self.process.history_audit_ready('run-1'))
            self.audit.helper.apply(1)

    def test_only_one_borrower_and_closing_it_never_closes_lender(self):
        first=self.process.borrow_canonical_journal()
        with self.assertRaises(RuntimePersistenceError):self.process.borrow_canonical_journal()
        first.close();first.close()
        with self.process.borrow_canonical_journal() as second:second.persist_risk_decision(risk_decision())
        self.assertEqual(self.db.execute('SELECT count(*) FROM paper_runtime_objects').fetchone()[0],1)

    def test_owning_close_retains_its_original_connection_ownership(self):
        owner=open_paper_runtime_journal(self.audit.helper.path)
        db=owner._store._connection;owner.close()
        with self.assertRaises(sqlite3.ProgrammingError):db.execute('SELECT 1')

    def test_conflict_is_still_durable_and_successful_prefix_is_not_rolled_back_as_bundle(self):
        with self.process.borrow_canonical_journal() as canonical:
            changed=risk_decision();changed['approved_quantity']='0.002'
            with self.assertRaises(RuntimePersistenceError):canonical.publish_canonical_effects([
                {'kind':'RISK_DECISION','payload':risk_decision()},
                {'kind':'RISK_DECISION','payload':changed}])
            self.assertFalse(self.db.in_transaction)
            self.assertEqual(self.db.execute('SELECT count(*) FROM paper_runtime_objects').fetchone()[0],1)
            self.assertEqual(self.db.execute('SELECT count(*) FROM paper_runtime_conflicts').fetchone()[0],1)

    def test_actual_position_subject_nested_read_uses_original_canonical_snapshot(self):
        from tests.storage.test_current_execution_subject_v02 import CurrentExecutionSubjectV02Tests
        fixture=CurrentExecutionSubjectV02Tests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.journal.close()
        with self.process.borrow_canonical_journal() as canonical:
            fixture.journal=canonical
            canonical.persist_risk_decision(fixture.risk)
            canonical.persist_approved_trade_plan(fixture.plan)
            fixture.test_actual_e5_genesis_binding_and_action_are_required_for_existing_position_read()
            self.assertFalse(self.db.in_transaction)


if __name__=='__main__':unittest.main()
