"""Headless acceptance-driver contracts; source mocks confer no native credit."""
import importlib
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from application.platform.private_files import create_private_directory, write_private_new

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))


class HeadlessNativeDriverTests(unittest.TestCase):
    def setUp(self):
        self.module=importlib.import_module('verify_headless_product')
        temporary=TemporaryDirectory(prefix='R7 headless driver ')
        self.addCleanup(temporary.cleanup)
        self.output=Path(temporary.name)/'scope'
        create_private_directory(self.output)
        self.flow=object.__new__(self.module.NativeHeadlessFlow)
        self.flow.output=self.output
        self.flow.data=self.output/'data'
        self.flow.config=self.output/'product.json'
        self.flow.operations=self.output/'operations.json'
        self.flow.observation={'passed':False,'commands':[],'sessions':[],'cases':[]}
        self.flow.commands=self.flow.observation['commands']
        self.flow.sessions=[]
        self.flow.guard=Mock()
        self.flow.persist=Mock()
        self.flow.research_input_root=None

    def snapshot(self):
        return {role:dict(pid=index+100,generation=1,process_generation_id=role+'-one',heartbeat_sequence=1)
            for index,role in enumerate(self.module.ROLES)}

    def test_operations_select_only_normal_idle_control_research_without_financial_schedules(self):
        value=self.module.operations_document()
        self.assertEqual(value['roles'],['control','research'])
        self.assertEqual(value['research_policy_ids'],[])
        self.assertIs(value['scan_inbox'],False)
        self.assertIs(value['queue_reports'],False)
        self.assertIs(value['workflow_authorized'],True)
        self.assertEqual((value['interval_seconds'],value['restart_budget'],value['restart_backoff_seconds']),(5,2,1))
        self.assertNotIn('runtime',value['roles'])

    def test_missing_explicit_public_inputs_denies_before_any_native_command(self):
        self.flow.command=Mock()
        with self.assertRaises(ValueError):self.flow._setup()
        self.flow.command.assert_not_called()

    def test_control_restart_changes_only_actual_control_incarnation(self):
        before=self.snapshot();after={key:dict(value) for key,value in before.items()}
        after['control'].update(pid=999,generation=2,process_generation_id='control-two')
        self.module.require_control_restart(before,after)
        after['research']['generation']=2
        with self.assertRaises(ValueError):self.module.require_control_restart(before,after)
        after={key:dict(value) for key,value in before.items()}
        with self.assertRaises(ValueError):self.module.require_control_restart(before,after)

    def test_kernel_termination_rejects_non_owned_pid_before_opening_any_handle(self):
        with patch.object(self.module,'owns_pid',return_value=False), patch('ctypes.WinDLL') as kernel:
            with self.assertRaises(ValueError):self.module.terminate_verified_pid(object(),123)
        kernel.assert_not_called()

    def test_crash_rechecks_role_incarnation_before_kernel_termination(self):
        before=self.snapshot()
        self.flow.health=Mock(return_value={**before['control'],'process_generation_id':'successor'})
        with patch.object(self.module,'terminate_verified_pid') as terminate:
            with self.assertRaises(ValueError):self.flow._crash_role(object(),'control',before)
        terminate.assert_not_called()

    def test_contender_requires_actual_typed_scope_denial_and_unchanged_original_tokens(self):
        snapshot=self.snapshot()
        self.flow._snapshot=Mock(return_value=snapshot)
        def command(label,args,**options):
            self.assertEqual(options['expected'],2)
            write_private_new(self.output/(label+'.log'),b'R7: local configuration or startup validation failed\n'+
                json.dumps(dict(schema_version='r7-startup-diagnostic-v0.2',error_kind='OWNER_SCOPE_BUSY',reason_code='LOCAL_STARTUP_VALIDATION_FAILED')).encode()+b'\n')
        self.flow.command=command
        self.flow._contender(object(),snapshot)
        self.assertEqual(self.flow.observation['cases'][-1]['case'],'SECOND_COORDINATOR_DENIED')

    def test_generic_startup_failure_cannot_establish_scope_denial(self):
        snapshot=self.snapshot();self.flow._snapshot=Mock(return_value=snapshot)
        def command(label,args,**options):
            write_private_new(self.output/(label+'.log'),b'R7: local configuration or startup validation failed\n'+
                json.dumps(dict(schema_version='r7-startup-diagnostic-v0.2',error_kind='VALIDATION',reason_code='LOCAL_STARTUP_VALIDATION_FAILED')).encode()+b'\n')
        self.flow.command=command
        with self.assertRaises(ValueError):self.flow._contender(object(),snapshot)

    def test_late_failure_cleans_all_owned_handles_and_cannot_leak_pass(self):
        self.flow._setup=Mock()
        self.flow._exercise=Mock(side_effect=ValueError('actual restart unconfirmed'))
        self.flow._cleanup_all=Mock()
        with self.assertRaises(ValueError):self.flow.run()
        self.flow._cleanup_all.assert_called_once()
        self.assertFalse(self.flow.observation['passed'])

    def test_cleanup_failure_overrides_success(self):
        self.flow._setup=Mock()
        self.flow._exercise=Mock()
        self.flow._cleanup_all=Mock(side_effect=ValueError('owned tree unreaped'))
        with self.assertRaises(ValueError):self.flow.run()
        self.assertFalse(self.flow.observation['passed'])

    def test_verify_returns_failure_instead_of_native_credit_from_exception(self):
        with patch.object(self.module,'NativeHeadlessFlow') as flow,patch.object(self.module.sys,'stderr',io.StringIO()):
            flow.return_value.run.side_effect=ValueError('internal private path must not escape')
            self.assertEqual(self.module.verify(self.output/'package',self.output/'new',research_input_root=self.output/'public'),2)
            self.assertNotIn('private path',self.module.sys.stderr.getvalue())


if __name__=='__main__':unittest.main()
