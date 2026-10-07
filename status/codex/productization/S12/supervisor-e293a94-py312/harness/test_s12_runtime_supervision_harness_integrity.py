import importlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


class RuntimeSupervisionHarnessIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='R7 supervision harness ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.development = self.root / 'development'
        self.development.mkdir()
        (self.development / 'owner.py').write_text('ORIGINAL = 1\n', encoding='utf-8')
        self.wrapper = self.root / 'runner.py'
        self.wrapper.write_text('ORIGINAL = 1\n', encoding='utf-8')

    def module(self):
        return importlib.import_module('s12_runtime_supervision_harness_integrity')

    def capture(self):
        return self.module().capture_inputs(self.development, (self.wrapper,))

    def test_unchanged_nonempty_actual_file_inventory_is_accepted(self):
        before = self.capture()
        self.assertEqual(set(before), {'development/owner.py','harness/runner.py'})
        self.module().require_unchanged_inputs(before, self.capture())
        with self.assertRaises(ValueError):
            self.module().require_unchanged_inputs({}, {})

    def test_replaced_consumed_source_is_denied(self):
        before = self.capture()
        (self.development / 'owner.py').write_text('REPLACEMENT = 2\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.module().require_unchanged_inputs(before, self.capture())

    def test_added_or_removed_executable_inventory_is_denied(self):
        before = self.capture()
        added = self.development / 'new.sql'
        added.write_text('SELECT 1;\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.module().require_unchanged_inputs(before, self.capture())
        added.unlink()
        (self.development / 'owner.py').unlink()
        with self.assertRaises(ValueError):
            self.module().require_unchanged_inputs(before, self.capture())

    def test_replaced_execution_wrapper_is_denied(self):
        before = self.capture()
        self.wrapper.write_text('UNEXECUTED_REPLACEMENT = 2\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.module().require_unchanged_inputs(before, self.capture())
