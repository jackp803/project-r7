from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from application.datasets.catalog import canonical, digest
from application.research.service import ResearchService
from storage.platform import open_sqlite_platform
from registry import StrategyIdentity
from tests.application.test_product_assessment_binding import risk_fixture
from tests.application.test_research_robustness import selected
from tests.application.dataset_fixtures import encoded
from tests.validation.robustness_fixtures import subject


class ResearchQueueTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('application.research.queue'),
                             'Durable asynchronous actual-owner research queue is missing')
        from application.research.queue import ResearchQueue, ResearchQueueError
        self.type, self.error = ResearchQueue, ResearchQueueError
        self.temp = TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); selected(self.root)
        (self.root/'risk.json').write_bytes(encoded(risk_fixture()))
        self.clock = [datetime(2026, 10, 3, tzinfo=timezone.utc)]
        self.resolver_calls = 0
        self.queue = self.make_queue()

    def service(self):
        return ResearchService(local_root=self.root, database_path=self.root/'research.sqlite',
            registry_path=self.root/'registry.sqlite', namespace='FIXTURE', owner_id='fixture-queue-worker')

    def resolve(self, submission_id, policy_id):
        self.resolver_calls += 1
        if submission_id != 'fixture-product' or policy_id != 'selected-fixture': raise ValueError('NOT_CONFIGURED')
        arguments = dict(submission_id=submission_id, definition=subject(), dataset_ref='dataset.json',
            split_policy_ref='split.json', cost_policy_ref='cost.json', research_policy_ref='research.json',
            robustness_policy_ref='robustness.json', family_id='fixture-family', seed=42, risk_policy_ref='risk.json')
        hashes = {name: digest((self.root/name).read_bytes()) for name in ('dataset.json', 'split.json', 'cost.json', 'research.json', 'robustness.json', 'risk.json')}
        return dict(submission_revision=1, arguments=arguments, selection_hash=digest(canonical(hashes).encode()))

    def make_queue(self, *, observer=None):
        return self.type(self.root/'queue.sqlite', namespace='FIXTURE', owner_id='fixture-queue-worker',
            resolve_request=self.resolve, service_factory=self.service, clock=lambda: self.clock[0], stage_observer=observer)

    def enqueue(self, command='queue-one', **kwargs):
        values = dict(submission_id='fixture-product', policy_id='selected-fixture', command_id=command, expected_revision=1, actor='local-owner')
        values.update(kwargs)
        return self.queue.enqueue(**values)

    def test_failed_alert_projection_filters_before_paging_and_retains_actual_failure_time(self):
        from contextlib import contextmanager
        from unittest.mock import patch
        base_resolver = self.queue.resolve_request
        def resolve_distinct(submission_id, policy_id):
            selected_input = base_resolver('fixture-product', policy_id)
            selected_input['arguments']['submission_id'] = submission_id
            return selected_input
        self.queue.resolve_request = resolve_distinct
        refs = [self.enqueue('alert-'+str(number), submission_id='alert-'+str(number)) for number in range(4)]
        refs.sort(key=lambda value: value['run_id'])
        self.queue.cancel(refs[0]['run_id'], refs[0]['revision'], 'cancel-first-alert-fixture', actor='local-owner')
        @contextmanager
        def failing_actual_owner():
            with self.service() as owner, patch.object(owner, 'run', side_effect=RuntimeError('SOURCE_ONLY_PRIVATE_TEXT_NOT_DISCLOSED')):
                yield owner
        self.queue.service_factory = failing_actual_owner
        failed = []
        for unused in range(2):
            claim = self.queue.claim_next()
            failed.append(self.queue.step(claim.run_id, claim.generation))
        self.assertEqual([row['state'] for row in failed], ['FAILED','FAILED'])
        self.assertEqual([row['reason_codes'] for row in failed], [['RuntimeError'],['RuntimeError']])
        self.clock[0] += timedelta(seconds=10)
        before_bytes = self.queue.path.read_bytes()
        calls = self.resolver_calls
        first = self.queue.failed_alert_page(limit=1, offset=0)
        second = self.queue.failed_alert_page(limit=1, offset=1)
        self.assertEqual(first['total'], 2)
        self.assertEqual(second['total'], 2)
        observed = first['items'] + second['items']
        self.assertEqual([row['run_id'] for row in observed], [row['run_id'] for row in failed])
        for actual, source in zip(observed, failed):
            self.assertEqual(set(actual), {'namespace','run_id','state','revision','generation','recorded_at','reason_codes'})
            self.assertEqual(actual, dict(namespace='FIXTURE',run_id=source['run_id'],state='FAILED',
                revision=source['revision'],generation=source['generation'],recorded_at=source['observed_at'],reason_codes=['RuntimeError']))
        self.assertNotIn('SOURCE_ONLY_PRIVATE_TEXT_NOT_DISCLOSED', json.dumps(first))
        self.assertEqual(first, self.queue.failed_alert_page(limit=1, offset=0))
        self.assertEqual(self.resolver_calls, calls)
        self.assertEqual(self.queue.path.read_bytes(), before_bytes)

    def test_failed_alert_projection_empty_missing_and_wrong_namespace_are_distinct(self):
        self.assertEqual(self.queue.failed_alert_page(limit=1, offset=0), dict(items=[], total=0))
        original = self.queue.path
        try:
            missing = self.root/'missing-alert-source.sqlite'
            self.queue.path = missing
            with self.assertRaises(self.error): self.queue.failed_alert_page(limit=1, offset=0)
            self.assertFalse(missing.exists())
            other = self.type(self.root/'other-namespace.sqlite', namespace='LOCAL_RESEARCH',
                owner_id='other-namespace-owner',resolve_request=self.resolve,service_factory=self.service,clock=lambda:self.clock[0])
            self.queue.path = other.path
            with self.assertRaises(self.error): self.queue.failed_alert_page(limit=1, offset=0)
        finally:
            self.queue.path = original

    def test_failed_alert_projection_rejects_invalid_pages(self):
        for limit,offset in ((True,0),(1,True),(0,0),(201,0),(1,-1),(1,100001)):
            with self.subTest(limit=limit,offset=offset),self.assertRaises(self.error):
                self.queue.failed_alert_page(limit=limit,offset=offset)

    def test_enqueue_is_durable_queued_not_inline_replay_or_candidate(self):
        ref = self.enqueue()
        self.assertEqual(ref['status'], 'QUEUED')
        self.assertFalse((self.root/'research.sqlite').exists())
        other = self.make_queue()
        job = other.get(ref['run_id'])
        self.assertEqual(job['state'], 'QUEUED')
        self.assertIsNone(job['owner_run_id'])
        self.assertEqual(job['revision'], 0)

    def test_actual_worker_composes_existing_owners_and_retains_candidate_lineage(self):
        ref = self.enqueue(); claim = self.queue.claim_next()
        result = self.queue.step(claim.run_id, claim.generation)
        self.assertEqual(result['state'], 'COMPLETE')
        self.assertEqual(result['outcome']['strategy_lifecycle'], 'CANDIDATE')
        self.assertEqual(result['owner_run_id'], result['outcome']['run_id'])
        with open_sqlite_platform(self.root/'registry.sqlite', research_namespace='FIXTURE') as e6:
            record = e6.get_strategy(StrategyIdentity(subject()['strategy_id'], subject()['strategy_version']))
            self.assertEqual(record.current_lifecycle_state, 'CANDIDATE')
            self.assertEqual(e6.product_assessment(result['owner_run_id']).status, 'PASS')
        with self.service() as owner:
            report = owner.report(result['owner_run_id'])
            self.assertEqual(report['provenance']['provider_requests'], 0)
            self.assertGreater(report['backtest']['reproducibility']['runtime_invocations'], 0)
        self.assertIsNone(self.queue.claim_next())

    def test_identical_enqueue_retries_are_one_logical_job_and_changed_identity_conflicts(self):
        first = self.enqueue()
        self.assertEqual(first, self.enqueue())
        self.assertEqual(first['run_id'], self.enqueue('queue-two')['run_id'])
        self.assertEqual(len(self.queue.list()), 1)
        for values in ({'actor': 'another-owner'}, {'expected_revision': 0}):
            with self.subTest(values=values):
                with self.assertRaises(self.error): self.enqueue(**values)

    def test_cancel_queued_job_is_actual_cas_and_retains_immutable_inputs(self):
        ref = self.enqueue(); original = self.queue.get(ref['run_id'])
        receipt = self.queue.cancel(ref['run_id'], 0, 'cancel-one', actor='local-owner')
        self.assertEqual(receipt['status'], 'CANCELED')
        self.assertEqual(self.queue.get(ref['run_id'])['state'], 'CANCELED')
        self.assertEqual(self.queue.get(ref['run_id'])['input_hash'], original['input_hash'])
        self.assertEqual(receipt, self.queue.cancel(ref['run_id'], 0, 'cancel-one', actor='local-owner'))
        with self.assertRaises(self.error): self.queue.cancel(ref['run_id'], 0, 'cancel-two', actor='local-owner')
        self.assertIsNone(self.queue.claim_next())

    def test_cooperative_cancel_before_robustness_retains_completed_development_evidence(self):
        def cancel_at_stage(run_id, stage):
            if stage == 'robustness':
                job = self.queue.get(ref['run_id'])
                self.queue.cancel(ref['run_id'], job['revision'], 'cancel-running', actor='local-owner')
        self.queue = self.make_queue(observer=cancel_at_stage)
        ref = self.enqueue(); claim = self.queue.claim_next()
        result = self.queue.step(claim.run_id, claim.generation)
        self.assertEqual(result['state'], 'CANCELED')
        self.assertIn('RESEARCH_CANCELED', result['reason_codes'])
        with self.service() as owner:
            attempts = owner.journal.attempts(result['owner_run_id'])
            self.assertTrue(any(row['stage'] == 'development_replay' and row['status'] == 'COMPLETE' for row in attempts))
            self.assertFalse(any(row['stage'] == 'sealed_oos' for row in attempts))

    def test_expired_worker_generation_is_fenced_and_recovery_keeps_same_job(self):
        ref = self.enqueue(); old = self.queue.claim_next()
        self.clock[0] += timedelta(seconds=301)
        newer = self.queue.claim_next()
        self.assertEqual(newer.run_id, old.run_id)
        self.assertGreater(newer.generation, old.generation)
        with self.assertRaises(self.error): self.queue.step(old.run_id, old.generation)
        self.assertEqual(self.queue.get(ref['run_id'])['state'], 'RUNNING')

    def test_changed_selected_files_block_before_replay_without_replacing_frozen_inputs(self):
        ref = self.enqueue(); original = self.queue.get(ref['run_id'])
        path = self.root/'risk.json'; value = json.loads(path.read_bytes()); value['generation'] = 2; path.write_bytes(encoded(value))
        claim = self.queue.claim_next(); result = self.queue.step(claim.run_id, claim.generation)
        self.assertEqual(result['state'], 'BLOCKED')
        self.assertIn('QUEUED_SELECTION_CHANGED', result['reason_codes'])
        self.assertEqual(result['input_hash'], original['input_hash'])
        self.assertFalse((self.root/'research.sqlite').exists())

    def test_stale_submission_or_unconfigured_policy_cannot_queue(self):
        with self.assertRaises(self.error): self.enqueue(expected_revision=0)
        with self.assertRaises(self.error): self.enqueue(policy_id='unconfigured')
        self.assertEqual(self.queue.list(), [])

    def test_lost_selected_configuration_blocks_job_without_leaving_running_or_echoing_exception(self):
        ref=self.enqueue(); claim=self.queue.claim_next()
        def unavailable(*args): raise RuntimeError('fixture-private-selection-detail')
        self.queue.resolve_request=unavailable
        try: result=self.queue.step(claim.run_id,claim.generation)
        except self.error: self.fail('Lost selected inputs must leave a durable BLOCKED job')
        self.assertEqual(result['state'],'BLOCKED')
        self.assertEqual(result['reason_codes'],['RESEARCH_SELECTION_NOT_CONFIGURED'])
        self.assertNotIn('fixture-private-selection-detail',repr(result))

    def test_valid_actor_and_command_identifiers_are_not_treated_as_filesystem_paths(self):
        from application.cloud.protocol import CloudError
        try: ref=self.enqueue('queue:one',actor='local:owner')
        except CloudError: self.fail('Valid server actor/command IDs are audit text, not package paths')
        result=self.queue.cancel(ref['run_id'],0,'cancel:one',actor='local:owner')
        self.assertEqual(result['status'],'CANCELED')


if __name__ == '__main__': unittest.main()
