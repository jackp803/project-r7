"""Service boundary unit tests; simulated composition is not Ubuntu acceptance."""
from contextlib import redirect_stdout
from dataclasses import replace
import importlib, io, json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from application.config import ProductConfig
from application.platform.service_plan import ServiceSettings
from application.platform.supervision import config_hash

class ServiceGuardTests(unittest.TestCase):
    def setUp(self):
        project=Path(__file__).resolve().parents[4]
        self.temp=TemporaryDirectory(prefix='service-guard-',dir=project/'artifacts')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.path=self.root/'settings/profile.json'
        self.config=ProductConfig('r7-product-config-v0.2','service-fixture',self.root/'data',None,self.root/'data/canonical.sqlite')
        self.subject=ServiceSettings('/opt/r7/release','/etc/r7/settings/product.json','/var/lib/r7-data',None,'r7-worker',
            'a'*40,'sha256:'+'b'*64,config_hash(self.config),24*1024**3)
        self.expected=dict(expected_revision=self.subject.executable_revision,expected_build_hash=self.subject.build_hash,
            expected_config_hash=self.subject.config_hash,service_user=self.subject.service_user,
            expected_memory_bytes=self.subject.physical_memory_bytes)
    def module(self):
        return importlib.import_module('application.platform.service_guard')

    def test_source_interpreter_cannot_claim_native_service_validation_or_open_configuration(self):
        module=self.module()
        with patch.object(module,'load_config') as reader,self.assertRaises(ValueError):
            module.verify_service_subject(self.path,**self.expected)
        reader.assert_not_called()

    def test_windows_frozen_process_cannot_claim_ubuntu_service_validation(self):
        module=self.module()
        with patch('sys.frozen',True,create=True),patch.object(module.platform,'system',return_value='Windows'), \
                patch.object(module,'load_config') as reader,self.assertRaises(ValueError):
            module.verify_service_subject(self.path,**self.expected)
        reader.assert_not_called()

    def test_guarded_control_delegates_only_to_actual_existing_headless_entrypoint(self):
        module=self.module()
        with patch.object(module,'verify_service_subject',return_value=self.subject) as verify, \
                patch.object(module,'load_config',return_value=self.config),patch('application.entrypoints.serve',return_value=17) as serve:
            self.assertEqual(module.run_guarded_service(self.path,role='control',**self.expected),17)
        self.assertTrue(verify.call_args.kwargs['require_service_identity'])
        serve.assert_called_once_with(self.config,desktop=False,config_path=self.path)

    def test_guarded_research_transfers_exact_config_commitment_to_real_worker(self):
        module=self.module()
        with patch.object(module,'verify_service_subject',return_value=self.subject),patch.object(module,'load_config',return_value=self.config), \
                patch('application.research.worker.research_worker',return_value=19) as worker:
            self.assertEqual(module.run_guarded_service(self.path,role='research',**self.expected),19)
        worker.assert_called_once_with(self.path,expected_config_hash=self.subject.config_hash)

    def test_config_changed_between_subject_verification_and_composition_has_no_owner_start(self):
        module=self.module()
        with patch.object(module,'verify_service_subject',return_value=self.subject), \
                patch.object(module,'load_config',return_value=replace(self.config,scan_interval=45)), \
                patch('application.entrypoints.serve') as serve,self.assertRaises(ValueError):
            module.run_guarded_service(self.path,role='control',**self.expected)
        serve.assert_not_called()

    def test_runtime_and_unknown_roles_fail_before_native_or_profile_inspection(self):
        module=self.module()
        for role in ('runtime','cloud','control\nUser=root'):
            with patch.object(module,'verify_service_subject') as verify,self.assertRaises(ValueError):
                module.run_guarded_service(self.path,role=role,**self.expected)
            verify.assert_not_called()

    def test_research_changed_subject_is_denied_before_supervision_or_database_mutation(self):
        from application.research import worker
        with patch.object(worker,'load_config',return_value=self.config),patch.object(worker,'ProcessSupervisor') as supervisor, \
                self.assertRaises(ValueError):
            worker.research_worker(self.path,once=True,expected_config_hash='sha256:'+'f'*64)
        supervisor.assert_not_called()

    def test_fresh_plan_export_writes_exact_units_and_marker_without_install_or_start(self):
        module=self.module();output=self.root/'fresh-plan'
        with patch.object(module,'verify_service_subject',return_value=self.subject):
            result=module.export_service_plan(self.path,output,**self.expected)
        self.assertEqual(result['status'],'PLAN_EXPORTED')
        manifest=json.loads((output/'service-plan.json').read_bytes())
        for name,text in manifest['units'].items():
            self.assertEqual((output/name).read_text(encoding='utf-8'),text)
        self.assertEqual(result['service_installation'],'NOT_PERFORMED')
        self.assertEqual(result['service_start'],'NOT_PERFORMED')

    def test_export_preserves_existing_target_and_rejects_overlap_before_writing(self):
        module=self.module();output=self.root/'existing'
        output.mkdir();(output/'foreign').write_bytes(b'operator-owned')
        with patch.object(module,'verify_service_subject',return_value=self.subject),self.assertRaises(ValueError):
            module.export_service_plan(self.path,output,**self.expected)
        self.assertEqual((output/'foreign').read_bytes(),b'operator-owned')
        with patch.object(module,'verify_service_subject',return_value=self.subject),self.assertRaises(ValueError):
            module.export_service_plan(self.path,self.root,**self.expected)
        self.assertFalse((self.root/'service-plan.json').exists())

    def test_cli_parser_reports_native_plan_or_guard_denial_without_starting_runtime(self):
        from application import cli
        module=self.module()
        common=['--config',str(self.path),'--expected-revision',self.subject.executable_revision,
            '--expected-build-hash',self.subject.build_hash,'--expected-config-hash',self.subject.config_hash,
            '--service-user',self.subject.service_user,'--expected-memory-bytes',str(self.subject.physical_memory_bytes)]
        with patch.object(module,'export_service_plan',return_value={'status':'PLAN_EXPORTED'}) as export,redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main(['plan-services',*common,'--output',str(self.root/'plan')]),0)
        self.assertEqual(json.loads(output.getvalue())['status'],'PLAN_EXPORTED')
        export.assert_called_once()
        with patch.object(module,'run_guarded_service',return_value=23) as run:
            self.assertEqual(cli.main(['guarded-service',*common,'--role','control']),23)
        run.assert_called_once()

if __name__=='__main__':unittest.main()
