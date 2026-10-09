"""Actual external-tool dependency mutation guards; no product acceptance credit."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

BASE=Path(__file__).absolute().parent
spec=importlib.util.spec_from_file_location('public_setup_runner',BASE/'run_s09_public_research_setup_tests.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
DEPENDENCIES=('run_s09_public_research_setup_tests.py','s09_owner_worker_native_regression.py',
              's09_owner_worker_source_qualify.py','local_windows_qualification_awake.py','test_s09_public_setup_runner_bindings.py')

class RunnerBindingGuards(unittest.TestCase):
    def test_default_capture_binds_actual_external_launcher_and_helper_bytes(self):
        captured=runner.capture()
        for name in DEPENDENCIES:
            with self.subTest(name=name):
                self.assertTrue('external/'+name in captured,'Missing execution dependency: '+name)
                self.assertEqual(captured['external/'+name],runner.sha((BASE/name).read_bytes()))

    def test_changed_owned_copies_of_each_real_dependency_are_detected(self):
        self.assertTrue(callable(getattr(runner,'execution_inputs',None)),'External execution inputs are not bound')
        with TemporaryDirectory(prefix='public-setup-proof-guards-',dir=BASE) as temporary:
            paths=[]
            for name in DEPENDENCIES:
                path=Path(temporary)/name;path.write_bytes((BASE/name).read_bytes());paths.append(path)
            before=runner.execution_inputs(paths)
            for path in paths:
                original=path.read_bytes()
                with self.subTest(name=path.name):
                    path.write_bytes(original+b'\n# bounded actual helper mutation\n')
                    self.assertNotEqual(before,runner.execution_inputs(paths))
                    path.write_bytes(original)
                    self.assertEqual(before,runner.execution_inputs(paths))

if __name__=='__main__':unittest.main(verbosity=2)
