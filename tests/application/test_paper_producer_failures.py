"""Controlled source producer failures retain actual negative E6 outcomes."""
from contextlib import ExitStack
import importlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from application.entrypoints import initialize_profile
from application.config import load_config
from application.platform.processes import process_alive
from application.platform.private_files import create_private_directory


class PaperProducerFailureTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(prefix='R7 PQR failure ');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source';self.source.mkdir()
        (self.source/'tests').mkdir()
        (self.source/'tests/test_owned.py').write_text('import unittest\nclass Actual(unittest.TestCase):\n def test_observed(self): self.assertTrue(True)\n')
        self.config=self.root/'product.json'
        initialize_profile(self.config,self.root/'data',instance_id='controlled-failure')
        create_private_directory(self.root/'data')
        self.m=importlib.import_module('application.paper.producer')
        self.facts=dict(executable_revision='a'*40,implementation_hash='sha256:'+'b'*64,
            build_hash='sha256:'+'c'*64)
        self.member=dict(member_id='PQR-01-001',kind='UNITTEST',command_ref='source-tests-001',
            directory='tests',pattern='test_owned.py',test_cases=['test_owned.Actual.test_observed'],
            assertions=[],timeout_seconds=20)
        self.profile=dict(profile_id='r7-qualified-paper-release-v0.2',groups=[dict(check_id='PQR-01',members=[self.member])])

    def execute(self,**overrides):
        with ExitStack() as stack:
            for name,value in dict(verify_distribution=self.facts,current_target='windows-11-x86_64',
                fixed_profile=self.profile,build_capability_snapshot=type('UnitCapabilities',(),dict(snapshot_hash='sha256:'+'d'*64))()).items():
                stack.enter_context(patch.object(self.m,name,return_value=value))
            stack.enter_context(patch.object(self.m,'_guard',**overrides.pop('guard',dict(return_value=None))))
            for name,value in overrides.items():stack.enter_context(patch.object(self.m,name,side_effect=value))
            result=self.m.qualify(self.config,self.source,self.root/'package')
        self.assertEqual(result['status'],'NATIVE_PAPER_SOFTWARE_NOT_QUALIFIED')
        output=load_config(self.config).local_data_root/'qualification'/result['execution_id']
        self.assertEqual(json.loads((output/'result.json').read_bytes()),result)
        from storage.qualification import open_qualification_receipts
        with open_qualification_receipts(load_config(self.config).database_path,namespace='LOCAL_RESEARCH') as store:
            receipt=store.get(result['receipt_ref'])
        self.assertFalse(receipt.passed)
        return output,receipt

    def test_spawn_failure_is_sanitized_and_retained_as_negative_receipt(self):
        output,receipt=self.execute(spawn_owned=OSError('UNTRUSTED_SECRET_SHOULD_NOT_APPEAR'))
        self.assertTrue((output/'execution-failure.log').exists())
        self.assertNotIn(b'UNTRUSTED_SECRET', (output/'execution-failure.log').read_bytes())

    def test_fresh_profile_data_is_initialized_under_owned_locks(self):
        (self.root/'data').rmdir()
        self.execute(spawn_owned=OSError('controlled unavailable child'))

    def test_post_command_source_guard_failure_cannot_leave_success_only_receipt(self):
        output,receipt=self.execute(guard=dict(side_effect=[None,None,ValueError('actual input drift')]))
        self.assertTrue((output/'PQR-01-001.log').exists())
        self.assertEqual(receipt.checks[0].tests_run,1)
        self.assertTrue(receipt.checks[0].passed)
        self.assertFalse(receipt.checks[-1].passed)

    def test_log_write_failure_preserves_original_raw_until_retention_succeeds(self):
        original=self.m.write_private_new
        def write(path,raw):
            if Path(path).name=='PQR-01-001.log':raise OSError('controlled retained-write failure')
            return original(path,raw)
        output,receipt=self.execute(write_private_new=write)
        self.assertIn(b'Ran 1 test', (output/'PQR-01-001.raw').read_bytes())

    def test_wait_failure_reaps_the_actual_spawned_child_before_negative_receipt(self):
        original=self.m.spawn_owned;owned=[]
        def spawn(*args,**kwargs):
            child=original(*args,**kwargs);owned.append(child)
            child.wait=lambda *a,**k:(_ for _ in ()).throw(OSError('controlled wait failure'))
            return child
        output,receipt=self.execute(spawn_owned=spawn)
        self.assertEqual(len(owned),1)
        self.assertFalse(process_alive(owned[0].process.pid))
        self.assertTrue(receipt.checks[-1].tree_reaped)


if __name__=='__main__':unittest.main()
