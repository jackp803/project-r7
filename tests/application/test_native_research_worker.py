from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import importlib
import json
from pathlib import Path
import sys
import threading
import time
import unittest

from application.platform.resources import inspect_hardware
from application.platform.processes import ResourceLimits, spawn_owned, process_alive
from application.platform.scope_lock import ProcessScopeLock, ScopeBusy
from application.research.queue import ResearchQueueError
from tests.application import test_local_owner_composition as fixture


class NativeResearchWorkerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixture.LocalOwnerCompositionTests(methodName='test_absent_local_selection_leaves_research_cloud_and_runtime_unconfigured')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.clock = lambda: datetime.now(timezone.utc)
        self.config_path = self.fixture.base / 'worker 設定.json'
        settings = {key: str(value) if isinstance(value, Path) else value for key, value in asdict(self.fixture.config).items()}
        self.config_path.write_text(json.dumps(settings, ensure_ascii=False), encoding='utf-8')

    def worker(self):
        return importlib.import_module('application.research.worker')

    def enqueue(self):
        owners = self.fixture.configured()
        with owners.inbox_factory() as inbox: inbox.scan_once(self.fixture.clock())
        revision = owners.queue.selected_submission_revision('native-owner-fixture', 'selected-fixture')
        queued = owners.queue.enqueue('native-owner-fixture', 'selected-fixture', 'worker-enqueue', revision, actor='fixture-owner')
        return owners, queued

    def child(self, config_path, run_id, generation):
        return [sys.executable, '-m', 'tests.application.native_research_job_fixture', '--config', str(config_path),
                '--run-id', run_id, '--generation', str(generation)]

    def test_actual_research_owner_runs_in_owned_child_and_publishes_canonical_candidate(self):
        owners, queued = self.enqueue()
        result = self.worker().worker_once(self.config_path, namespace='FIXTURE', job_argv_factory=self.child)
        self.assertEqual(result['status'], 'JOB_FINISHED')
        self.assertTrue(result['tree_reaped'])
        self.assertEqual(result['job_state'], 'COMPLETE')
        job = owners.queue.get(queued['run_id'])
        self.assertEqual(job['outcome']['strategy_lifecycle'], 'CANDIDATE')
        self.assertNotEqual(result['child_pid'], result['parent_pid'])

    def test_memory_pressure_leaves_job_queued_and_starts_no_child(self):
        owners, queued = self.enqueue()
        hardware = replace(inspect_hardware(self.fixture.root), available_memory_bytes=0)
        called = []
        def forbidden(*args): called.append(args); self.fail('Resource pressure must not construct child argv')
        result = self.worker().worker_once(self.config_path, namespace='FIXTURE', job_argv_factory=forbidden,
                                          hardware_probe=lambda root: hardware)
        self.assertEqual(result['status'], 'PAUSED_RESOURCE')
        self.assertEqual(owners.queue.get(queued['run_id'])['state'], 'QUEUED')
        self.assertEqual(called, [])

    def test_controlled_timeout_reaps_child_and_records_failed_owned_job(self):
        owners, queued = self.enqueue()
        def sleeping(config_path, run_id, generation):
            return [sys.executable, '-c', 'import time;time.sleep(120)']
        result = self.worker().worker_once(self.config_path, namespace='FIXTURE', job_argv_factory=sleeping,
                                          job_timeout_seconds=0.2)
        self.assertEqual(result['status'], 'JOB_TERMINATED')
        self.assertTrue(result['tree_reaped'])
        self.assertEqual(owners.queue.get(queued['run_id'])['state'], 'FAILED')
        self.assertIn('OWNED_WORKER_TIMEOUT', owners.queue.get(queued['run_id'])['reason_codes'])

    def test_production_namespace_refuses_fixture_executable_override(self):
        with self.assertRaises(ValueError):
            self.worker().worker_once(self.config_path, job_argv_factory=self.child)

    def test_unconfigured_worker_is_truthful_and_does_not_claim_work(self):
        result = self.worker().worker_once(self.config_path)
        self.assertEqual(result['status'], 'NOT_CONFIGURED')
        self.assertIsNone(result['run_id'])

    def test_terminated_old_generation_cannot_overwrite_a_successor_claim(self):
        owners, queued = self.enqueue()
        previous = owners.queue.claim_next()
        owners.queue.clock = lambda: datetime.now(timezone.utc) + timedelta(seconds=600)
        successor = owners.queue.claim_next()
        self.assertGreater(successor.generation, previous.generation)
        owned = spawn_owned([sys.executable, '-c', 'pass'], cwd=Path.cwd(), limits=ResourceLimits(5))
        owned.wait()
        with self.assertRaises(ResearchQueueError):
            owners.queue.finish_terminated_worker(previous, owned)
        current = owners.queue.get(queued['run_id'])
        self.assertEqual(current['state'], 'RUNNING')
        self.assertEqual(current['generation'], successor.generation)

    def test_zero_process_exit_without_owner_publication_is_not_a_finished_research_job(self):
        owners, queued = self.enqueue()
        def empty_child(config_path, run_id, generation):
            return [sys.executable, '-c', 'pass']
        result = self.worker().worker_once(self.config_path, namespace='FIXTURE', job_argv_factory=empty_child)
        self.assertEqual(owners.queue.get(queued['run_id'])['state'], 'FAILED')
        self.assertEqual(result['status'], 'JOB_TERMINATED')

    def test_second_worker_is_denied_before_hardware_or_queue_mutation(self):
        owners, queued = self.enqueue()
        with ProcessScopeLock('research:' + self.fixture.config.product_instance_id,
                              lock_root=self.fixture.root / 'locks'):
            with self.assertRaises(ScopeBusy):
                self.worker().worker_once(self.config_path, namespace='FIXTURE', job_argv_factory=self.child,
                    hardware_probe=lambda root: self.fail('Contender must not probe or initialize owners'))
        self.assertEqual(owners.queue.get(queued['run_id'])['state'], 'QUEUED')

    def test_config_change_terminates_actual_owned_job_and_preserves_failed_claim(self):
        owners, queued = self.enqueue()
        ready = self.fixture.root / 'actual-child.json'
        def change_after_actual_child_start():
            deadline = time.monotonic() + 5
            while not ready.exists() and time.monotonic() < deadline: time.sleep(0.02)
            if ready.exists():
                settings = json.loads(self.config_path.read_bytes())
                settings['scan_interval'] += 1
                self.config_path.write_text(json.dumps(settings, ensure_ascii=False), encoding='utf-8')
        changer = threading.Thread(target=change_after_actual_child_start, daemon=True)
        def sleeping(config_path, run_id, generation):
            changer.start()
            code = 'import os,time;from pathlib import Path;Path(' + repr(str(ready)) + ').write_text(str(os.getpid()));time.sleep(120)'
            return [sys.executable, '-c', code]
        from application.platform.supervision import SupervisionError
        try:
            with self.assertRaises(SupervisionError):
                self.worker().worker_once(self.config_path, namespace='FIXTURE', job_argv_factory=sleeping,
                                          job_timeout_seconds=7)
        finally:
            changer.join(6)
        self.assertTrue(ready.exists(), 'An actual owned child must have started')
        self.assertFalse(process_alive(int(ready.read_text())))
        self.assertEqual(owners.queue.get(queued['run_id'])['state'], 'FAILED')
