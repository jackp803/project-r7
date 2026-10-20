"""Source-only wrapper binding checks; no native or qualification credit."""
from pathlib import Path
import importlib.util
import unittest
from unittest.mock import patch

class IsolationProbeBindingTests(unittest.TestCase):
    def test_parent_rejects_metadata_ancestor_package_before_guard_or_output(self):
        self.check('parent')

    def test_child_rejects_metadata_ancestor_package_before_guard_or_flow(self):
        self.check('child')

    def check(self,entry):
        path=Path(__file__).with_name('verify_isolation_owning_depth.py')
        spec=importlib.util.spec_from_file_location('outside_isolation_probe',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with patch.object(module,'revision_fact'),patch.object(module,'verify_distribution',return_value={'executable_revision':'b'*40}), \
             patch.object(module,'fixed_profile',return_value={}),patch.object(module,'current_target',return_value='windows-11-x86_64'), \
             patch.object(module,'_guard',side_effect=AssertionError('Unbound package reached guard')) as guard, \
             patch.object(module,'create_private_directory') as output:
            with self.assertRaises(ValueError):
                if entry=='parent':module.run('a'*40,'probe99')
                else:module.child('a'*40,Path('UNUSED_SOURCE_ONLY_OUTPUT'))
            guard.assert_not_called();output.assert_not_called()

if __name__=='__main__':unittest.main()
