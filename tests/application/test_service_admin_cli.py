"""Bounded operator CLI dispatch; controlled backend is not Linux acceptance."""
from contextlib import redirect_stdout,redirect_stderr
import importlib,io,json,unittest
from pathlib import Path
from unittest.mock import patch
from application import cli

class ServiceAdminCliTests(unittest.TestCase):
    def args(self,command='install-services'):
        return [command,'--config','/etc/r7/設定 空格.json','--expected-revision','a'*40,
            '--expected-build-hash','sha256:'+'b'*64,'--expected-config-hash','sha256:'+'c'*64,
            '--expected-memory-bytes',str(24*1024**3),'--service-user','r7-worker']
    def call(self,argv):
        with redirect_stdout(io.StringIO()) as output:
            code=cli.main(argv)
        return code,json.loads(output.getvalue())
    def test_dry_run_forwards_only_typed_subject_and_never_applies_by_default(self):
        for command,action in (('install-services','install'),('uninstall-services','uninstall')):
            with self.subTest(command=command),patch('application.platform.service_admin.manage_services',return_value=dict(status='DRY_RUN')) as manage:
                code,result=self.call(self.args(command))
            self.assertEqual(code,0);self.assertEqual(result['status'],'DRY_RUN')
            self.assertEqual(manage.call_args.args,(Path('/etc/r7/設定 空格.json'),))
            self.assertEqual(manage.call_args.kwargs,dict(action=action,apply=False,operation_hash=None,
                expected_revision='a'*40,expected_build_hash='sha256:'+'b'*64,expected_config_hash='sha256:'+'c'*64,
                expected_memory_bytes=24*1024**3,service_user='r7-worker'))
    def test_apply_forwards_the_explicit_displayed_commitment(self):
        commitment='sha256:'+'d'*64
        with patch('application.platform.service_admin.manage_services',return_value=dict(status='FILES_REMOVED')) as manage:
            code,_=self.call(self.args('uninstall-services')+['--apply','--operation-hash',commitment])
        self.assertEqual(code,0);self.assertTrue(manage.call_args.kwargs['apply'])
        self.assertEqual(manage.call_args.kwargs['operation_hash'],commitment)
    def test_incomplete_reload_failure_and_prerequisite_return_nonzero(self):
        for status in ('INCOMPLETE','PREREQUISITE_REQUIRED','FILES_INSTALLED_RELOAD_FAILED','FILES_REMOVED_RELOAD_FAILED'):
            with self.subTest(status=status),patch('application.platform.service_admin.manage_services',return_value=dict(status=status)):
                self.assertEqual(self.call(self.args())[0],2)
    def test_unknown_success_status_is_never_accepted(self):
        with patch('application.platform.service_admin.manage_services',return_value=dict(status='STARTED')):
            self.assertEqual(self.call(self.args())[0],2)
    def test_arbitrary_backend_unit_body_or_system_root_options_are_rejected(self):
        for option in ('--backend','--system-root','--unit-body','--output'):
            with self.subTest(option=option),redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as error:
                cli.main(self.args()+[option,'arbitrary'])
            self.assertEqual(error.exception.code,2)
    def test_source_or_windows_is_denied_before_configuration_read_or_mutation(self):
        module=importlib.import_module('application.platform.service_admin_files')
        with patch('application.platform.service_guard.load_config') as reader,patch.object(module.os,'open') as opened, \
                self.assertRaises(ValueError):cli.main(self.args())
        reader.assert_not_called();opened.assert_not_called()
