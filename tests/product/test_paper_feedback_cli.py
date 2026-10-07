"""Actual historical E6 report publication via CLI; local fake transport only."""
from contextlib import redirect_stdout
from datetime import datetime, timezone
from io import StringIO
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from application.cli import main
from application.cloud.manifest import canonical_bytes
from application.platform.scope_lock import ProcessScopeLock, ScopeBusy, operational_lock_root
from storage.paper_feedback import PaperFeedbackOutbox
from storage.paper_process import open_paper_process_journal
from tests.application import test_cloud_bridge as bridge_fixtures
from tests.product import test_paper_runtime_v02 as paper_fixtures


class PaperFeedbackCliTests(unittest.TestCase):
    def setUp(self):
        self.cloud = bridge_fixtures.CloudBridgeTests()
        self.cloud.setUp()
        self.addCleanup(self.cloud.doCleanups)
        self.product = self.cloud.data / 'product.json'
        self.product.write_bytes(canonical_bytes(dict(
            schema_version=self.cloud.config.schema_version,
            product_instance_id=self.cloud.config.product_instance_id,
            local_data_root=str(self.cloud.data), cloud_root=str(self.cloud.stage))))

    def queue_historical(self):
        owner = paper_fixtures.PaperRuntimeV02Tests()
        owner.setUp()
        self.addCleanup(owner.doCleanups)
        runtime = owner.start()
        self.run_id = runtime.run_id
        self.operation = PaperFeedbackOutbox(owner.process).queue(runtime)
        self.before = owner.process.recover(self.run_id)
        self.registry_before = owner.registry.get_strategy(owner.identity)
        self.original_owner = owner
        # A real SQLite snapshot preserves the actual immutable historical
        # producer/checkpoint lineage. CLI must use this configured E6 store.
        with sqlite3.connect(self.cloud.config.database_path) as snapshot:
            owner.process._db.backup(snapshot)

    def records(self):
        with open_paper_process_journal(self.cloud.config.database_path) as journal:
            return PaperFeedbackOutbox(journal).publications()

    def invoke(self, limit=10):
        output = StringIO()
        with patch('application.cloud.rclone_bridge.run_bounded', self.cloud.fake), redirect_stdout(output):
            code = main(['cloud-publish-outbox', '--config', str(self.product),
                         '--bridge-profile', str(self.cloud.settings), '--limit', str(limit)])
        text = output.getvalue()
        for private in (str(self.cloud.data), str(self.cloud.reference), str(self.cloud.remote)):
            self.assertNotIn(private, text)
        return code, json.loads(text)

    def queue_receipt(self):
        from application.intake.ledger import IntakeLedger
        now = datetime(2026, 10, 7, tzinfo=timezone.utc)
        with IntakeLedger(self.cloud.data / 'intake.sqlite', instance_id=self.cloud.config.product_instance_id) as ledger:
            claim = ledger.claim('cli-submission', 'sha256:' + 'a' * 64, 'cli-fixture', now)
            ledger.commit_effect(claim, 'fixture-intake', canonical_bytes(dict(status='INTAKE_ACCEPTED')), now=now)

    def test_cli_publishes_configured_historical_owner_without_attaching_runtime_or_reading_credentials(self):
        self.queue_historical()
        original = Path.read_bytes
        def protected_read(path):
            if path == self.cloud.reference:
                raise AssertionError('CLI read protected credential reference')
            return original(path)
        with (patch('application.paper.service.PaperService.__init__', side_effect=AssertionError('Runtime attached')),
              patch('storage.paper_process.PaperProcessJournal.begin_process', side_effect=AssertionError('Lease renewed')),
              patch.object(Path, 'read_bytes', protected_read)):
            code, result = self.invoke(1)
            retry_code, retry = self.invoke(1)
        self.assertEqual((code, retry_code), (0, 0))
        self.assertEqual((result['attempted'], result['cloud_acknowledged']), (1, 1))
        self.assertEqual(retry['attempted'], 0)
        self.assertEqual(self.records()[0]['state'], 'CLOUD_ACKNOWLEDGED')
        self.assertEqual(self.records()[0]['operation_id'], self.operation)
        with open_paper_process_journal(self.cloud.config.database_path) as journal:
            self.assertEqual(journal.recover(self.run_id), self.before)
        self.assertEqual(self.original_owner.registry.get_strategy(self.original_owner.identity), self.registry_before)
        report = list(self.cloud.remote.glob('reports/feedback/paper/**/feedback.json'))
        self.assertEqual(len(report), 1)
        self.assertEqual(json.loads(report[0].read_bytes())['financial_authority'], 'NONE')

    def test_cli_outage_is_incomplete_then_same_historical_operation_retries(self):
        self.queue_historical()
        self.cloud.fake.outage = True
        code, result = self.invoke(1)
        self.assertEqual((code, result['status'], result['unavailable']), (2, 'INCOMPLETE', 1))
        self.assertEqual(self.records()[0]['state'], 'UNAVAILABLE')
        self.cloud.fake.outage = False
        code, result = self.invoke(1)
        self.assertEqual((code, result['cloud_acknowledged']), (0, 1))
        self.assertEqual([row['operation_id'] for row in self.records()], [self.operation])

    def test_cli_conflict_preserves_remote_bytes_and_durable_conflict(self):
        self.queue_historical()
        with open_paper_process_journal(self.cloud.config.database_path) as journal:
            _, bundle, _ = PaperFeedbackOutbox(journal).pending(1)[0]
        remote = self.cloud.remote / bundle.logical_path / 'feedback.json'
        remote.parent.mkdir(parents=True)
        original = b'{"fixture":"original conflicting remote bytes"}'
        remote.write_bytes(original)
        code, result = self.invoke(1)
        self.assertEqual((code, result['conflicts']), (2, 1))
        self.assertEqual(self.records()[0]['state'], 'CONFLICT')
        self.assertEqual(remote.read_bytes(), original)

    def test_cli_three_outboxes_share_one_total_budget_and_preserve_priority(self):
        from application.cloud.feedback import queue_feedback
        from application.research.service import ResearchService
        from tests.application.test_research_pipeline import configured
        from tests.validation.robustness_fixtures import subject
        self.queue_historical()
        configured(self.cloud.data)
        with ResearchService(local_root=self.cloud.data, database_path=self.cloud.data / 'research.sqlite',
                             registry_path=self.cloud.config.database_path, namespace='FIXTURE', owner_id='cli-feedback') as service:
            run = service.run(submission_id='fixture-submission', definition=subject(), dataset_ref='dataset.json',
                              split_policy_ref='split.json', cost_policy_ref='cost.json')
            queue_feedback(service, run.run_id)
        self.queue_receipt()
        for iteration, expected in enumerate((1, 1, 1, 0), 1):
            code, result = self.invoke(1)
            self.assertEqual(code, 0)
            self.assertEqual((result['attempted'], result['cloud_acknowledged']), (expected, expected))
            if iteration < 3:
                self.assertEqual(self.records()[0]['state'], 'PENDING')
        self.assertEqual(len(list(self.cloud.remote.glob('receipts/**/receipt.json'))), 1)
        self.assertEqual(len(list(self.cloud.remote.glob('reports/feedback/paper/**/feedback.json'))), 1)
        self.assertEqual(len(list(self.cloud.remote.glob('reports/feedback/**/feedback.json'))), 2)

    def test_cli_absent_canonical_store_does_not_create_or_open_paper_database(self):
        with patch('storage.paper_process.open_paper_process_journal', side_effect=AssertionError('Absent DB opened')):
            code, result = self.invoke(1)
        self.assertEqual((code, result['attempted']), (0, 0))
        self.assertFalse(self.cloud.config.database_path.exists())
        self.assertFalse((self.cloud.data / 'runtime.sqlite').exists())

    def test_cli_disappearing_existing_store_cannot_be_recreated_as_empty_success(self):
        from application.platform.supervision import _local_path
        self.queue_historical()
        database = self.cloud.config.database_path
        removed = False
        def disappear(path):
            nonlocal removed
            if path == database:
                self.assertFalse(removed)
                database.unlink()
                removed = True
            return _local_path(path)
        with patch('application.platform.supervision._local_path', disappear):
            with self.assertRaises(sqlite3.OperationalError):
                self.invoke(1)
        self.assertTrue(removed)
        self.assertFalse(database.exists(), 'Historical publication silently recreated the canonical store')

    def test_cli_exhausted_budget_does_not_open_paper_journal(self):
        self.queue_historical()
        self.queue_receipt()
        with patch('storage.paper_process.open_paper_process_journal', side_effect=AssertionError('Exhausted journal opened')):
            code, result = self.invoke(1)
        self.assertEqual((code, result['attempted'], result['cloud_acknowledged']), (0, 1, 1))
        self.assertEqual(self.records()[0]['state'], 'PENDING')

    def test_cli_cloud_scope_denial_precedes_any_canonical_paper_writer(self):
        self.queue_historical()
        with (ProcessScopeLock('cloud:' + self.cloud.config.product_instance_id, lock_root=operational_lock_root(self.cloud.config)),
              patch('storage.paper_process.open_paper_process_journal', side_effect=AssertionError('Scope bypass')),
              self.assertRaises(ScopeBusy)):
            self.invoke(1)
        self.assertEqual(self.records()[0]['state'], 'PENDING')


if __name__ == '__main__':
    unittest.main()
