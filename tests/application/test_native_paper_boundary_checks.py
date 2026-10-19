"""Native component models are synthetic in memory, never issued receipts."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest,uuid
from unittest.mock import patch
from types import SimpleNamespace
import json,subprocess

from application.config import ProductConfig
from application.platform.private_files import create_private_directory
from application.platform.supervision import config_hash

class NativeBoundaryCheckTests(unittest.TestCase):
    def module(self):
        import importlib
        return importlib.import_module('application.paper.native_boundary_checks')
    def subject(self,root):
        config=ProductConfig('r7-product-config-v0.2','native-boundary-unit',root,None,root/'canonical.sqlite3')
        facts=dict(executable_revision='1'*40,implementation_hash='sha256:'+'2'*64,build_hash='sha256:'+'3'*64,
            platform_id='windows-11-x86_64',capability_hash='sha256:'+'4'*64,distribution_profile='r7-native-distribution-v0.2',
            worktree='UNAVAILABLE',financial_authority='NONE')
        identity=dict(role='runtime',pid=123,generation=1,process_generation_id=str(uuid.uuid4()),
            product_instance_id=config.product_instance_id,config_hash=config_hash(config),
            **{key:facts[key] for key in ('executable_revision','implementation_hash','build_hash','distribution_profile')})
        return config,facts,identity
    def test_source_command_refuses_before_any_data_or_child_side_effect(self):
        module=self.module()
        with TemporaryDirectory() as directory:
            root=Path(directory)
            with self.assertRaises(ValueError):module.run_native_boundary_checks(root/'not-created.json')
            self.assertEqual(list(root.iterdir()),[])

    def test_partial_diagnostic_record_has_companion_evidence_and_no_pqr_member_claim(self):
        from datetime import datetime,timezone
        from storage.qualification import QualificationCheck,_payload
        module=self.module()
        with TemporaryDirectory() as directory:
            root=Path(directory);_,facts,_=self.subject(root)
            check=QualificationCheck('source-only-in-memory-check','source-unit','source.log','sha256:'+'a'*64,
                0,True,0,0,0,0,0,0,1)
            now=datetime.now(timezone.utc)
            captured=module.diagnostic_receipt_input(facts,{'source_fixture':'IN_MEMORY_ONLY'},check,now,now)
            receipt,_=_payload(**captured)
            self.assertEqual(receipt.execution_evidence['executed_pqr_members'],[])
            self.assertFalse(receipt.execution_evidence['qualification_complete'])
            self.assertEqual(receipt.execution_evidence['observed_checks'][0]['log_hash'],check.log_hash)
            self.assertFalse(list(root.iterdir()),'Source model must remain in memory, without storage or authority')
    def test_synthetic_models_exercise_real_guards_without_any_receipt_or_selection_storage(self):
        module=self.module()
        with TemporaryDirectory() as directory:
            root=Path(directory)/'private';create_private_directory(root);config,facts,identity=self.subject(root)
            results=module.memory_component_checks(root,config,facts,identity)
            self.assertGreaterEqual(len(results),12);self.assertEqual(len(results),len(set(results)))
            self.assertFalse(list(root.rglob('*.sqlite*')));self.assertFalse(list(root.rglob('*selection*')))
    def test_accepting_a_negative_model_is_a_failed_check_not_a_fabricated_pass(self):
        module=self.module()
        with TemporaryDirectory() as directory:
            root=Path(directory)/'private';create_private_directory(root);config,facts,identity=self.subject(root)
            with patch('application.paper.qualification.validate_qualified_receipt',return_value=None),self.assertRaises(RuntimeError):
                module.memory_component_checks(root,config,facts,identity)

    def test_actual_old_e6_generation_cannot_prepare_any_operation_after_successor(self):
        from tests.application.paper_owner_fixtures import PaperOwnerFixture
        from dataclasses import replace
        helper=PaperOwnerFixture(self)
        helper.config=helper.h.config=replace(helper.config,execution_mode='FIXTURE')
        run=helper.start()
        with helper.factory() as first:first.runtime(run)
        with helper.factory() as second:second.runtime(run)
        before=helper.recover(run);module=self.module()
        result=module.stale_paper_operation_check(helper.config,run,before.binding['implementation_hash'])
        self.assertEqual(result['status'],'STALE_OPERATION_DENIED');self.assertTrue(result['original_checkpoint_unchanged'])
        self.assertEqual(helper.recover(run),before)

    def test_failed_doctor_preserves_actual_log_exit_and_cleanup_without_receipt(self):
        module=self.module()
        for raw,code,error in ((b'actual rejected diagnostic',2,None),(b'{invalid json',0,None),
                (b'partial timeout output',None,subprocess.TimeoutExpired('fixed-doctor',35))):
            with self.subTest(code=code,error=type(error).__name__),TemporaryDirectory() as directory:
                output=Path(directory)/'private';create_private_directory(output)
                config,_,_=self.subject(output)
                def spawn(argv,**kwargs):
                    kwargs['stdout'].write(raw);kwargs['stdout'].flush()
                    def wait(**_):
                        if error:raise error
                        return code
                    return SimpleNamespace(wait=wait,process=SimpleNamespace(poll=lambda:code),
                        termination_report=SimpleNamespace(reaped=True))
                with patch.object(module,'spawn_owned',side_effect=spawn),patch.object(module,'terminate_owned',
                        return_value=SimpleNamespace(reaped=True,reason='TEST_ACTUAL_CLEANUP')):
                    with self.assertRaises(Exception):module._doctor(config,output/'config.json',output)
                self.assertEqual((output/'doctor.log').read_bytes(),raw)
                facts=json.loads((output/'doctor-execution.json').read_bytes())
                self.assertEqual(facts['exit_code'],code);self.assertTrue(facts['tree_reaped'])
                self.assertEqual(facts['qualification'],'NOT_ISSUED')
                self.assertFalse(list(output.rglob('*.sqlite*')))

    def test_unconfirmed_doctor_cleanup_retains_handle_and_failure_facts(self):
        module=self.module();old=list(module._unreaped)
        self.addCleanup(lambda:module._unreaped.__setitem__(slice(None),old))
        with TemporaryDirectory() as directory:
            output=Path(directory)/'private';create_private_directory(output);config,_,_=self.subject(output)
            owned=SimpleNamespace(wait=lambda **_:0,process=SimpleNamespace(poll=lambda:0),
                termination_report=SimpleNamespace(reaped=True))
            def spawn(argv,**kwargs):
                kwargs['stdout'].write(b'{"physical_memory_bytes":34359738368}')
                return owned
            with patch.object(module,'spawn_owned',side_effect=spawn),patch.object(module,'terminate_owned',
                    return_value=SimpleNamespace(reaped=False)),self.assertRaisesRegex(RuntimeError,'cleanup unconfirmed'):
                module._doctor(config,output/'config.json',output)
            self.assertIs(module._unreaped[-1],owned)
            facts=json.loads((output/'doctor-execution.json').read_bytes())
            self.assertFalse(facts['tree_reaped']);self.assertEqual(facts['exit_code'],0)
            self.assertEqual(facts['qualification'],'NOT_ISSUED')
