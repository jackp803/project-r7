"""Explicit headless local operations; no OS installation or financial grant."""
from contextlib import redirect_stdout
import io,json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from application import cli
from application.config import load_config
from application.datasets.catalog import canonical
from tests.application import test_research_setup_flow as setup_flow

def selection(**changes):
    value=dict(schema_version='r7-local-operations-v0.2',workflow_authorized=True,actor='local-operator',
        roles=['research'],scan_inbox=False,research_policy_ids=[],queue_reports=False,interval_seconds=5,
        restart_budget=2,restart_backoff_seconds=1)
    value.update(changes);return value

class ProductCoordinatorTests(unittest.TestCase):
    def module(self):
        import importlib
        return importlib.import_module('application.coordinator')

    def test_closed_operations_profile_rejects_implicit_workflow_arbitrary_commands_and_authority(self):
        module=self.module()
        self.assertEqual(module.validate_operations(selection()),selection())
        for change in (dict(workflow_authorized=False),dict(roles=['research','research']),dict(roles=['LIVE']),
                       dict(roles=['control'],research_policy_ids=['diagnostic']),dict(qualified_release='PASS'),
                       dict(argv=['arbitrary']),dict(interval_seconds=True),dict(restart_budget=999),dict(actor='')):
            with self.subTest(change=change),self.assertRaises(ValueError):module.validate_operations(selection(**change))

    def prepared(self):
        helper=setup_flow.ResearchSetupFlowTests();helper.setUp();self.addCleanup(helper.doCleanups)
        config=helper.prepare('DIAGNOSTIC');helper.configure()
        return helper,config

    def test_normal_owner_scan_enqueue_repeats_idempotently_without_promoting_diagnostic(self):
        helper,config=self.prepared();module=self.module()
        from application.local_owners import LocalOwners
        owners=LocalOwners(config,namespace='LOCAL_RESEARCH');services=owners.control_services()
        operations=module.validate_operations(selection(scan_inbox=True,research_policy_ids=['selected-test']))
        first=module.schedule_once(owners,services,operations)
        second=module.schedule_once(owners,services,operations)
        self.assertEqual(first['enqueued'],1);self.assertEqual(second['enqueued'],1)
        jobs=owners.queue.list();self.assertEqual(len(jobs),1);self.assertEqual(jobs[0]['state'],'QUEUED')
        self.assertEqual(first['paper'],'NOT_COMMANDED');self.assertEqual(second['provider_requests'],0)

    def test_actual_headless_research_child_stops_and_reaps_without_browser_or_network(self):
        helper,config=self.prepared();module=self.module()
        operations=helper.root/'operations.json';operations.write_text(canonical(selection()),encoding='utf-8')
        with redirect_stdout(io.StringIO()):result=module.run_product(helper.config_path,operations,maximum_cycles=15)
        self.assertEqual(result['status'],'STOPPED');self.assertTrue(result['all_owned_trees_reaped'])
        role=result['roles']['research']
        self.assertTrue(role['actual_process_generation_id']);self.assertEqual(role['stop'],'COOPERATIVE_STOP_REQUESTED')
        self.assertTrue(role['tree_reaped']);self.assertFalse(role['forced_stop'])
        self.assertEqual(result['host_settings'],'UNCHANGED');self.assertEqual(result['financial_authority'],'NONE')

    def test_existing_external_research_owner_is_not_stopped_or_adopted(self):
        helper,config=self.prepared();module=self.module()
        from application.platform.supervision import ProcessSupervisor
        operations=helper.root/'operations.json';operations.write_text(canonical(selection()),encoding='utf-8')
        with ProcessSupervisor(config,'research',config_path=helper.config_path) as external,redirect_stdout(io.StringIO()):
            token=external.identity['process_generation_id']
            result=module.run_product(helper.config_path,operations,maximum_cycles=1)
            external.require_current()
            self.assertEqual(result['roles']['research']['status'],'EXTERNALLY_OWNED')
            self.assertEqual(external.identity['process_generation_id'],token)
            self.assertNotIn('stop',result['roles']['research'])

    def test_duplicate_coordinator_fails_before_spawning_or_changing_queue(self):
        helper,config=self.prepared();module=self.module()
        from application.platform.supervision import ProcessSupervisor
        from application.platform.scope_lock import ScopeBusy
        from unittest.mock import patch
        operations=helper.root/'operations.json';operations.write_text(canonical(selection()),encoding='utf-8')
        with ProcessSupervisor(config,'coordinator',config_path=helper.config_path), \
             patch.object(module,'_compose',side_effect=AssertionError('duplicate must not initialize owners')) as compose, \
             patch.object(module,'spawn_owned_service') as spawn,self.assertRaises(ScopeBusy):
            module.run_product(helper.config_path,operations,maximum_cycles=1)
        spawn.assert_not_called();compose.assert_not_called()

    def test_stop_identity_refusal_still_reaps_only_the_owned_child(self):
        helper,config=self.prepared();module=self.module()
        from unittest.mock import patch
        operations=helper.root/'operations.json';operations.write_text(canonical(selection()),encoding='utf-8')
        with patch.object(module,'request_service_stop',side_effect=ValueError('changed incarnation')),redirect_stdout(io.StringIO()):
            result=module.run_product(helper.config_path,operations,maximum_cycles=12)
        self.assertTrue(result['all_owned_trees_reaped']);self.assertTrue(result['roles']['research']['forced_stop'])
        self.assertEqual(result['roles']['research']['stop_error'],'ValueError')

    def test_actual_research_service_crash_restarts_to_new_generation_with_bounded_budget(self):
        import threading,time
        from unittest.mock import patch
        from application.platform.processes import terminate_owned,owned_contains_pid
        from application.platform.supervision import process_health
        helper,config=self.prepared();module=self.module()
        operations=helper.root/'operations.json';operations.write_text(canonical(selection()),encoding='utf-8')
        real_spawn=module.spawn_owned_service;crashed=[];threads=[]
        def crash_actual_child(handle):
            end=time.monotonic()+5
            while time.monotonic()<end:
                health=process_health(config,'research')
                if health.get('pid') and owned_contains_pid(handle,health['pid']):
                    crashed.append(health['process_generation_id']);terminate_owned(handle,reason='SOURCE_TEST_SERVICE_CRASH');return
                time.sleep(.05)
        def launch(*args,**kwargs):
            handle=real_spawn(*args,**kwargs)
            if not threads:
                thread=threading.Thread(target=crash_actual_child,args=(handle,));threads.append(thread);thread.start()
            return handle
        try:
            with patch.object(module,'spawn_owned_service',side_effect=launch),redirect_stdout(io.StringIO()):
                result=module.run_product(helper.config_path,operations,maximum_cycles=25)
        finally:
            for thread in threads:thread.join(timeout=6)
        self.assertEqual(len(crashed),1);self.assertEqual(result['roles']['research']['launches'],2)
        self.assertNotEqual(result['roles']['research']['actual_process_generation_id'],crashed[0])
        self.assertTrue(result['all_owned_trees_reaped']);self.assertFalse(result['roles']['research']['forced_stop'])

    def test_cli_has_one_local_launcher_and_coordinator_stop_without_os_installation(self):
        helper,config=self.prepared()
        from unittest.mock import patch
        operations=helper.root/'operations.json'
        with patch('application.coordinator.run_product',return_value=dict(status='STOPPED',all_owned_trees_reaped=True,roles={})) as run,redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['run-product','--config',str(helper.config_path),'--operations-profile',str(operations)]),0)
            self.assertEqual(run.call_args.args,(helper.config_path,operations))

    def test_changed_profile_at_child_handoff_creates_no_store_in_changed_root(self):
        helper,config=self.prepared();module=self.module()
        from unittest.mock import patch
        from application.platform.supervision import SupervisionError
        operations=helper.root/'operations.json';operations.write_text(canonical(selection()),encoding='utf-8')
        other=helper.root/'unselected-other-root';handles=[];real_spawn=module.spawn_owned_service
        def changed(*args,**kwargs):
            value=json.loads(helper.config_path.read_bytes())
            value.update(local_data_root=str(other),database_path=str(other/'canonical.sqlite3'),product_instance_id='not-selected-at-start')
            helper.config_path.write_text(canonical(value),encoding='utf-8')
            handle=real_spawn(*args,**kwargs);handles.append(handle);return handle
        with patch.object(module,'spawn_owned_service',side_effect=changed),redirect_stdout(io.StringIO()):
            try:module.run_product(helper.config_path,operations,maximum_cycles=1)
            except SupervisionError:pass
        self.assertFalse(other.exists(),'Changed subject must be denied before creating any owner store')
        self.assertEqual(len(handles),1);self.assertTrue(handles[0].termination_report.reaped)

    def test_unconfirmed_exited_tree_stays_registered_for_cleanup_and_cannot_restart(self):
        import sys
        from unittest.mock import patch
        from application.platform import processes
        helper,config=self.prepared();module=self.module()
        operations=helper.root/'operations.json';operations.write_text(canonical(selection()),encoding='utf-8')
        real_spawn=module.spawn_owned_service;real_terminate=processes.terminate_owned;handles=[];attempts=[]
        def launch(*args,**kwargs):
            handle=real_spawn([sys.executable,'-c','import subprocess,sys;subprocess.Popen([sys.executable,"-c","import time;time.sleep(120)"])'],**kwargs)
            handles.append(handle);return handle
        def first_unconfirmed(handle,**kwargs):
            attempts.append(handle)
            if len(attempts)==1:
                handle.termination_report=processes.TerminationReport(True,False,'SOURCE_TEST_UNCONFIRMED')
                return handle.termination_report
            return real_terminate(handle,**kwargs)
        try:
            with patch.object(module,'spawn_owned_service',side_effect=launch), \
                 patch.object(processes,'terminate_owned',side_effect=first_unconfirmed),redirect_stdout(io.StringIO()), \
                 self.assertRaises(RuntimeError):
                module.run_product(helper.config_path,operations,maximum_cycles=15)
            self.assertEqual(len(handles),1);self.assertGreaterEqual(len(attempts),2)
            self.assertTrue(handles[0].termination_report.reaped)
        finally:
            for handle in handles:real_terminate(handle)
