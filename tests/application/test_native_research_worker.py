from dataclasses import asdict, replace
from contextlib import redirect_stderr,redirect_stdout
from datetime import datetime, timedelta, timezone
import importlib
import io
import json
from pathlib import Path
import sys
import threading
import time
import unittest
from unittest.mock import patch

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

    def test_research_worker_cli_forwards_default_and_explicit_timeout(self):
        from application.cli import main
        module=self.worker()
        with patch.object(module,'research_worker',return_value=0) as owner:
            for options,seconds in (([],900),(['--job-timeout-seconds','1'],1),(['--job-timeout-seconds','900'],900)):
                with self.subTest(seconds=seconds):
                    owner.reset_mock()
                    self.assertEqual(main(['research-worker','--config',str(self.config_path),'--once',*options]),0)
                    owner.assert_called_once_with(self.config_path,once=True,job_timeout_seconds=seconds)
            owner.reset_mock()
            with redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as denied:
                main(['research-worker','--config',str(self.config_path),'--job-timeout-seconds','0.2'])
            self.assertEqual(denied.exception.code,2)
            owner.assert_not_called()

    def test_public_research_timeout_rejects_before_owner_side_effects(self):
        module=self.worker()
        with patch.object(module,'load_config') as config,patch.object(module,'ProcessSupervisor') as supervisor, \
             patch.object(module,'LocalOwners') as owners,patch.object(module,'spawn_owned') as child:
            for invalid in (None,True,False,0.2,1.0,'1',0,-1,901):
                with self.subTest(value=invalid),self.assertRaises(ValueError):
                    module.research_worker(self.config_path,once=True,job_timeout_seconds=invalid)
            for boundary in (config,supervisor,owners,child):boundary.assert_not_called()

    def test_public_research_timeout_reaches_fixed_owned_job_limits(self):
        module=self.worker()
        for seconds in (1,900):
            with self.subTest(seconds=seconds),patch.object(module,'load_config',return_value=self.fixture.config), \
                 patch.object(module,'ProcessSupervisor'),patch('application.platform.service_stop.observe_service_stop',return_value=False), \
                 patch.object(module,'_worker_once',return_value=dict(status='IDLE')) as admitted,redirect_stdout(io.StringIO()):
                self.assertEqual(module.research_worker(self.config_path,once=True,job_timeout_seconds=seconds),0)
                admitted.assert_called_once()
                self.assertEqual(admitted.call_args.kwargs['limits'].timeout_seconds,seconds)
                self.assertIsNone(admitted.call_args.kwargs['job_argv_factory'])
                self.assertIs(admitted.call_args.kwargs['hardware_probe'],module.inspect_hardware)
        with self.assertRaises(TypeError):module.research_worker(self.config_path,job_argv_factory=self.child)
        with self.assertRaises(TypeError):module.research_worker(self.config_path,hardware_probe=lambda _:None)

    def test_persisted_stop_during_idle_is_observed_before_another_admission(self):
        from application.platform.shutdown import ManagedStop
        from application.platform.service_stop import request_service_stop
        from application.platform.supervision import process_health
        module=self.worker();waits=[];receipts=[];actual_wait=ManagedStop.wait
        def request_in_idle(stop,seconds):
            # The request is a real private, incarnation-fenced product request.
            # Check the bound rather than asserting a fragile wall-clock deadline.
            self.assertLessEqual(seconds,.2)
            waits.append(seconds)
            receipts.append(request_service_stop(self.fixture.config,'research'))
            return actual_wait(stop,seconds)
        with patch.object(module,'_worker_once',return_value=dict(status='IDLE')) as admission, \
             patch.object(ManagedStop,'wait',request_in_idle),redirect_stdout(io.StringIO()):
            self.assertEqual(module.research_worker(self.config_path),0)
        self.assertEqual(admission.call_count,1)
        self.assertEqual(len(waits),1)
        self.assertEqual(receipts[0]['status'],'COOPERATIVE_STOP_REQUESTED')
        health=process_health(self.fixture.config,'research')
        self.assertEqual(health['status'],'STOPPED')
        self.assertEqual(health['process_generation_id'],receipts[0]['process_generation_id'])

    def test_idle_polling_preserves_five_second_work_cadence_and_managed_stop(self):
        from application.platform.shutdown import ManagedStop
        module=self.worker();elapsed=[0.0];waits=[];stop=ManagedStop()
        def wait(seconds):
            self.assertGreater(seconds,0);self.assertLessEqual(seconds,.2)
            waits.append(seconds);elapsed[0]+=seconds
        with patch.object(module.time,'monotonic',side_effect=lambda:elapsed[0]), \
             patch.object(stop,'wait',side_effect=wait), \
             patch('application.platform.service_stop.observe_service_stop',return_value=False) as observe:
            module._wait_idle(object(),stop)
        self.assertAlmostEqual(sum(waits),5)
        self.assertGreater(observe.call_count,1)
        stop.request()
        with patch.object(stop,'wait') as blocked, \
             patch('application.platform.service_stop.observe_service_stop') as observe:
            module._wait_idle(object(),stop)
        blocked.assert_not_called();observe.assert_not_called()

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

    def test_stop_before_admission_leaves_job_queued_without_probing_or_starting_child(self):
        from application.platform.shutdown import ManagedStop
        owners,queued=self.enqueue();stop=ManagedStop();stop.request()
        result=self.worker().worker_once(self.config_path,namespace='FIXTURE',job_argv_factory=self.child,stop=stop,
            hardware_probe=lambda root:self.fail('Stopped worker must not admit work'))
        self.assertEqual(result['status'],'STOPPED')
        self.assertEqual(owners.queue.get(queued['run_id'])['state'],'QUEUED')

    def test_managed_stop_reaps_actual_child_grandchild_and_disposes_only_its_exact_claim(self):
        from application.platform.shutdown import ManagedStop
        from application.platform.supervision import process_health
        owners,queued=self.enqueue();stop=ManagedStop()
        target=self.fixture.root/'stop-tree.py'
        target.write_text("import subprocess,sys,time,os,json\nfrom pathlib import Path\n"
            "depth=int(sys.argv[1]);root=Path(sys.argv[2])\n"
            "(root/f'stop-pid-{depth}.json').write_text(json.dumps({'pid':os.getpid()}))\n"
            "if depth:subprocess.Popen([sys.executable,__file__,str(depth-1),str(root)])\n"
            "time.sleep(120)\n",encoding='utf-8')
        ready=[self.fixture.root/('stop-pid-'+str(depth)+'.json') for depth in (0,1)]
        def after_descendants_ready():
            deadline=time.monotonic()+8
            while not all(path.exists() for path in ready) and time.monotonic()<deadline:time.sleep(0.02)
            stop.request()
        stopper=threading.Thread(target=after_descendants_ready,daemon=True)
        def sleeping(config_path,run_id,generation):
            stopper.start()
            return [sys.executable,str(target),'1',str(self.fixture.root)]
        try:
            result=self.worker().worker_once(self.config_path,namespace='FIXTURE',job_argv_factory=sleeping,
                job_timeout_seconds=12,stop=stop)
        finally:
            if stopper.ident is not None:stopper.join(9)
        self.assertTrue(all(path.exists() for path in ready),'Actual descendant tree must have started')
        self.assertTrue(all(not process_alive(json.loads(path.read_bytes())['pid']) for path in ready))
        self.assertTrue(result['tree_reaped']);self.assertEqual(result['status'],'JOB_STOPPED')
        job=owners.queue.get(queued['run_id'])
        self.assertEqual(job['state'],'FAILED');self.assertEqual(job['reason_codes'],['OWNED_WORKER_STOPPED'])
        self.assertIsNone(owners.queue.claim_next(),'Restart must not replay a disposed or sealed owner job')
        self.assertEqual(process_health(self.fixture.config,'research')['status'],'STOPPED')
