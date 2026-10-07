"""Actual product CLI bindings; public local diagnostics only."""
from contextlib import redirect_stdout,redirect_stderr
import importlib,io,json,sys,unittest
from unittest.mock import patch
from application import cli

class SSHAccessCLITests(unittest.TestCase):
    def output(self,argv):
        with redirect_stdout(io.StringIO()) as stream:
            code=cli.main(argv)
        return code,json.loads(stream.getvalue())

    def test_plan_cli_generates_literal_argv_without_starting_connection(self):
        with patch('subprocess.Popen',side_effect=AssertionError('SSH planning never executes')):
            code,result=self.output(['plan-ssh-tunnel','--host','r7.example.test','--username','operator','--port','8765','--ssh-port','2222'])
        self.assertEqual(code,0)
        self.assertEqual(result['argv'][-1],'r7.example.test')
        self.assertEqual(result['argv'][-2],'127.0.0.1:8765:127.0.0.1:8765')
        self.assertEqual(result['ssh_connection'],'NOT_STARTED')
        self.assertEqual(result['financial_authority'],'NONE')

    def test_probe_cli_passes_explicit_namespace_and_bounded_deadline(self):
        result=dict(status='PUBLIC_AUTH_STATUS_AVAILABLE',tree_reaped=True)
        with patch('application.platform.ssh_access.probe_loopback_auth_status',return_value=result) as probe:
            code,observed=self.output(['probe-control-access','--port','8765','--expected-namespace','FIXTURE','--deadline-seconds','3'])
        probe.assert_called_once_with(8765,expected_namespace='FIXTURE',deadline_seconds=3)
        self.assertEqual(code,0);self.assertEqual(observed,result)

    def test_probe_unavailable_is_an_explicit_nonzero_result(self):
        result=dict(status='UNAVAILABLE',reason_code='PUBLIC_STATUS_UNAVAILABLE',tree_reaped=True)
        with patch('application.platform.ssh_access.probe_loopback_auth_status',return_value=result):
            code,observed=self.output(['probe-control-access','--port','8765'])
        self.assertEqual(code,2);self.assertEqual(observed,result)

    def test_owned_probe_helper_cli_is_bound_to_actual_helper(self):
        with patch('application.platform._loopback_probe.main',return_value=2) as helper:
            self.assertEqual(cli.main(['_auth-status-probe','--port','8765','--expected-namespace','FIXTURE']),2)
        helper.assert_called_once_with(['--port','8765','--expected-namespace','FIXTURE'])

    def test_frozen_probe_helper_still_verifies_distribution_at_executable_boundary(self):
        argv=['r7.exe','_auth-status-probe','--port','8765','--expected-namespace','LOCAL_RESEARCH']
        with patch.object(sys,'argv',argv),patch.object(sys,'frozen',True,create=True), \
                patch('application.platform.distribution.verify_distribution') as verify, \
                patch('application.platform._loopback_probe.main',return_value=0) as helper:
            self.assertEqual(cli.run(),0)
        verify.assert_called_once();helper.assert_called_once()

    def test_unknown_namespace_and_absent_operator_host_are_denied_before_execution(self):
        for argv in (['probe-control-access','--port','8765','--expected-namespace','LIVE'],['plan-ssh-tunnel','--username','operator']):
            with self.subTest(command=argv[0]),redirect_stderr(io.StringIO()), \
                    patch('subprocess.Popen',side_effect=AssertionError('Invalid command must not execute')),self.assertRaises(SystemExit) as error:
                cli.main(argv)
            self.assertEqual(error.exception.code,2)

    def test_native_parent_invokes_same_executable_and_actual_helper_command(self):
        module=importlib.import_module('application.platform.ssh_access')
        with patch.object(sys,'frozen',True,create=True):
            self.assertEqual(module._probe_argv(8765,'LOCAL_RESEARCH'),[sys.executable,'_auth-status-probe','--port','8765','--expected-namespace','LOCAL_RESEARCH'])

if __name__=='__main__':unittest.main()
