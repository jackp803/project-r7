import importlib.util
import sqlite3
import tempfile
import unittest
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from datetime import datetime, timezone
from pathlib import Path

from brokers.paper import PaperBroker
from storage.runtime_models import RuntimeConflictError, RuntimeValidationError
from tests.brokers.test_paper_broker import _request

NOW = datetime(2026, 10, 3, tzinfo=timezone.utc)


class PaperProcessJournalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'runtime.sqlite'

    def journal(self):
        self.assertIsNotNone(importlib.util.find_spec('storage.paper_process'),
                             'durable Paper operation/checkpoint owner is not implemented')
        from storage.paper_process import open_paper_process_journal
        return open_paper_process_journal(self.path)

    def binding(self):
        return dict(namespace='FIXTURE', mode='ACCELERATED_FIXTURE',
            strategy_id='fixture', strategy_version='0.2.0',
            strategy_content_hash='sha256:' + '1' * 64,
            implementation_hash='sha256:' + '2' * 64,
            config_hash='sha256:' + '3' * 64, risk_policy_hash='sha256:' + '4' * 64,
            paper_policy_hash='sha256:' + '5' * 64)

    def state(self, broker=None):
        return {'broker': (broker or PaperBroker()).export_state(), 'runtime': {'entries_enabled': False}}

    def create(self, journal):
        return journal.create_run('run-1', self.binding(), self.state(), now=NOW)

    def test_crash_after_effect_recovery_keeps_order_and_pending_canonical_publication(self):
        with self.journal() as journal:
            self.create(journal)
            prepared = journal.prepare('run-1', 'entry-boundary-1', {'kind': 'ENTRY'}, expected_revision=0, now=NOW)
            broker = PaperBroker.from_state(prepared.base_state['broker'])
            broker.submit_order(_request())
            journal.complete('run-1', 'entry-boundary-1', self.state(broker),
                             {'canonical_effects': [], 'status': 'ACKNOWLEDGED'}, now=NOW)
        with self.journal() as journal:
            recovered = journal.recover('run-1')
            self.assertEqual(recovered.revision, 1)
            self.assertEqual(recovered.status, 'PUBLICATION_PENDING')
            self.assertEqual(recovered.pending_operations, ('entry-boundary-1',))
            broker = PaperBroker.from_state(recovered.state['broker'])
            self.assertEqual(broker.query_order(_request().client_order_id).order_status.value, 'OPEN')
            effect = journal.operation('run-1', 'entry-boundary-1')
            self.assertEqual(effect.outcome['status'], 'ACKNOWLEDGED')
            journal.mark_published('run-1', 'entry-boundary-1', effect.effect_hash, now=NOW)
            self.assertEqual(journal.recover('run-1').status, 'RECONCILIATION_REQUIRED')

    def test_prepared_operation_resumes_original_base_and_fences_concurrent_boundary(self):
        with self.journal() as journal:
            self.create(journal)
            original = journal.prepare('run-1', 'one', {'kind': 'ENTRY'}, expected_revision=0, now=NOW)
        with self.journal() as journal:
            again = journal.prepare('run-1', 'one', {'kind': 'ENTRY'}, expected_revision=0, now=NOW)
            self.assertEqual(again.base_state, original.base_state)
            self.assertEqual(journal.recover('run-1').status, 'PREPARED_PENDING')
            with self.assertRaises(RuntimeConflictError):
                journal.prepare('run-1', 'two', {'kind': 'ENTRY'}, expected_revision=0, now=NOW)
            with self.assertRaises(RuntimeConflictError):
                journal.prepare('run-1', 'one', {'kind': 'EXIT'}, expected_revision=0, now=NOW)

    def test_identical_completed_retry_returns_original_without_new_checkpoint(self):
        with self.journal() as journal:
            self.create(journal)
            journal.prepare('run-1', 'one', {'kind': 'ENTRY'}, expected_revision=0, now=NOW)
            first = journal.complete('run-1', 'one', self.state(), {'status': 'NO_SIGNAL'}, now=NOW)
            again = journal.complete('run-1', 'one', self.state(), {'status': 'NO_SIGNAL'}, now=NOW)
            self.assertEqual(first, again)
            self.assertEqual(journal.recover('run-1').revision, 1)
            journal.prepare('run-1', 'one', {'kind': 'ENTRY'}, expected_revision=0, now=NOW)
            with self.assertRaises(RuntimeConflictError):
                journal.complete('run-1', 'one', self.state(), {'status': 'CHANGED'}, now=NOW)
            with self.assertRaises(RuntimeConflictError):
                journal.prepare('run-1', 'next', {'kind': 'ENTRY'}, expected_revision=0, now=NOW)

    def test_failure_during_checkpoint_commit_rolls_back_effect_and_retries_safely(self):
        with self.journal() as journal:
            self.create(journal)
            journal.prepare('run-1', 'one', {'kind': 'ENTRY'}, expected_revision=0, now=NOW)
            with closing(sqlite3.connect(self.path)) as connection, connection:
                connection.execute("CREATE TRIGGER test_crash BEFORE INSERT ON paper_process_checkpoints "
                                   "WHEN NEW.revision=1 BEGIN SELECT RAISE(ABORT,'injected'); END")
            with self.assertRaises(RuntimeValidationError):
                journal.complete('run-1', 'one', self.state(), {'status': 'NO_SIGNAL'}, now=NOW)
            recovered = journal.recover('run-1')
            self.assertEqual(recovered.revision, 0)
            self.assertEqual(journal.operation('run-1', 'one').status, 'PREPARED')
            with closing(sqlite3.connect(self.path)) as connection, connection:
                connection.execute('DROP TRIGGER test_crash')
            journal.complete('run-1', 'one', self.state(), {'status': 'NO_SIGNAL'}, now=NOW)
            self.assertEqual(journal.recover('run-1').revision, 1)

    def test_changed_identity_namespace_and_float_or_secret_fields_rejected(self):
        with self.journal() as journal:
            self.create(journal)
            for changed in (dict(self.binding(), namespace='LOCAL_RESEARCH'),
                            dict(self.binding(), config_hash='sha256:' + '6' * 64)):
                with self.assertRaises((RuntimeConflictError, RuntimeValidationError)):
                    journal.create_run('run-1', changed, self.state(), now=NOW)
            for request in ({'kind': 'ENTRY', 'capital': 0.1}, {'kind': 'ENTRY', 'api_key': 'forbidden'}):
                with self.assertRaises(RuntimeValidationError):
                    journal.prepare('run-1', 'one', request, expected_revision=0, now=NOW)

    def test_publication_requires_exact_effect_and_does_not_change_exposure(self):
        with self.journal() as journal:
            self.create(journal)
            journal.prepare('run-1', 'one', {'kind': 'ENTRY'}, expected_revision=0, now=NOW)
            effect = journal.complete('run-1', 'one', self.state(), {'status': 'NO_SIGNAL'}, now=NOW)
            with self.assertRaises(RuntimeConflictError):
                journal.mark_published('run-1', 'one', 'sha256:' + '0' * 64, now=NOW)
            before = journal.recover('run-1').state
            journal.mark_published('run-1', 'one', effect.effect_hash, now=NOW)
            journal.mark_published('run-1', 'one', effect.effect_hash, now=NOW)
            self.assertEqual(journal.recover('run-1').state, before)
            self.assertEqual(journal.recover('run-1').pending_operations, ())

    def test_runtime_generations_are_durable_and_cannot_rewrite_logical_history(self):
        with self.journal() as journal:
            self.create(journal)
            self.assertEqual(journal.begin_process('run-1', 'process-a', expected_generation=0, now=NOW), 1)
            self.assertEqual(journal.begin_process('run-1', 'process-a', expected_generation=0, now=NOW), 1)
        with self.journal() as journal:
            self.assertEqual(journal.begin_process('run-1', 'process-b', expected_generation=1, now=NOW), 2)
            with self.assertRaises(RuntimeConflictError):
                journal.begin_process('run-1', 'process-c', expected_generation=1, now=NOW)
            self.assertEqual(journal.recover('run-1').revision, 0)
            self.assertEqual(journal.recover('run-1').process_generation, 2)

    def test_new_effect_waits_for_previous_canonical_publication(self):
        with self.journal() as journal:
            self.create(journal)
            journal.prepare('run-1', 'one', {'kind': 'ENTRY'}, expected_revision=0, now=NOW)
            effect = journal.complete('run-1', 'one', self.state(), {'status': 'NO_SIGNAL'}, now=NOW)
            with self.assertRaises(RuntimeConflictError):
                journal.prepare('run-1', 'two', {'kind': 'ENTRY'}, expected_revision=1, now=NOW)
            journal.mark_published('run-1', 'one', effect.effect_hash, now=NOW)
            self.assertEqual(journal.prepare('run-1', 'two', {'kind': 'ENTRY'}, expected_revision=1, now=NOW).status, 'PREPARED')

    def test_old_process_cannot_complete_an_effect_after_restart(self):
        with self.journal() as journal:
            self.create(journal)
            journal.prepare('run-1', 'one', {'kind': 'ENTRY'}, expected_revision=0, now=NOW)
            journal.begin_process('run-1', 'new-process', expected_generation=0, now=NOW)
            with self.assertRaises(RuntimeConflictError):
                journal.complete('run-1', 'one', self.state(), {'status': 'NO_SIGNAL'}, now=NOW)
            effect = journal.complete('run-1', 'one', self.state(), {'status': 'NO_SIGNAL'}, now=NOW, process_generation=1)
            journal.mark_published('run-1', 'one', effect.effect_hash, now=NOW)
            with self.assertRaises(RuntimeConflictError):
                journal.prepare('run-1', 'two', {'kind': 'ENTRY'}, expected_revision=1, now=NOW)
            self.assertEqual(journal.prepare('run-1', 'two', {'kind': 'ENTRY'}, expected_revision=1, now=NOW, process_generation=1).status, 'PREPARED')

    def test_simultaneous_connections_admit_only_one_boundary_effect(self):
        with self.journal() as journal: self.create(journal)
        barrier = Barrier(2)
        def attempt(operation_id):
            with self.journal() as journal:
                barrier.wait(timeout=10)
                try:
                    journal.prepare('run-1', operation_id, {'kind': 'ENTRY'}, expected_revision=0, now=NOW)
                    return 'PREPARED'
                except RuntimeConflictError: return 'FENCED'
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(attempt, ('first', 'second')))
        self.assertEqual(sorted(outcomes), ['FENCED', 'PREPARED'])
        with self.journal() as journal:
            self.assertEqual(len(journal.recover('run-1').pending_operations), 1)

    def test_broker_domain_validation_runs_outside_database_transactions(self):
        with self.journal() as journal:
            self.create(journal)
            real = PaperBroker.from_state
            def validate(state):
                self.assertFalse(journal._db.in_transaction,
                                 'E4 broker work must precede/follow the mechanical transaction')
                return real(state)
            with patch.object(PaperBroker, 'from_state', side_effect=validate):
                journal.prepare('run-1', 'one', {'kind': 'ENTRY'}, expected_revision=0, now=NOW)
                effect = journal.complete('run-1', 'one', self.state(), {'status': 'NO_SIGNAL'}, now=NOW)
                journal.mark_published('run-1', 'one', effect.effect_hash, now=NOW)
                self.assertEqual(journal.recover('run-1').revision, 1)

    def test_legacy_secret_vocabulary_cannot_enter_checkpoint_outbox(self):
        with self.journal() as journal:
            self.create(journal)
            for name in ('apiKey', 'passphrase', 'session_token', 'nested_credentials'):
                run_id = 'run-' + name
                journal.create_run(run_id, self.binding(), self.state(), now=NOW)
                with self.subTest(name=name), self.assertRaises(RuntimeValidationError):
                    journal.prepare(run_id, 'one', {'kind': 'ENTRY', name: 'forbidden'}, expected_revision=0, now=NOW)

    def test_scalar_operation_request_or_outcome_cannot_poison_recovery(self):
        with self.journal() as journal:
            self.create(journal)
            with self.assertRaises(RuntimeValidationError):
                journal.prepare('run-1', 'one', 'ENTRY', expected_revision=0, now=NOW)
            journal.prepare('run-1', 'one', {'kind': 'ENTRY'}, expected_revision=0, now=NOW)
            with self.assertRaises(RuntimeValidationError):
                journal.complete('run-1', 'one', self.state(), 'DONE', now=NOW)
            self.assertEqual(journal.recover('run-1').revision, 0)


if __name__ == '__main__': unittest.main()
