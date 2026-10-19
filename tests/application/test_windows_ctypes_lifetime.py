"""Native file/resource checks keep fresh observations and bounded ABI types.

Windows exercises the repaired Win32 path; other hosts exercise their actual
platform branch without introducing skips into the owning source inventory.
"""
import ctypes
import gc
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from application.cloud.safe_files import read_bounded, stage_author_input
from application.platform.resources import inspect_hardware


def retained_pointer_inputs(module):
    # CPython strongly retains POINTER input classes. Observe the actual cache;
    # clearing it would conceal the leak and can invalidate unrelated ctypes users.
    gc.collect()
    return {kind for kind in ctypes._pointer_type_cache if getattr(kind, '__module__', None) == module}


class WindowsCtypesLifetimeTests(unittest.TestCase):
    def test_repeated_opened_reads_keep_fresh_bytes_without_retaining_per_read_types(self):
        with TemporaryDirectory(prefix='r7-abi-read-') as directory:
            root = Path(directory); target = root / 'result.json'
            target.write_bytes(b'first')
            self.assertEqual(read_bounded(root, 'result.json', 64), b'first')
            before = retained_pointer_inputs('application.cloud.safe_files')
            for number in range(32):
                raw = str(number).encode('ascii'); target.write_bytes(raw)
                self.assertEqual(read_bounded(root, 'result.json', 64), raw)
            self.assertEqual(len(retained_pointer_inputs('application.cloud.safe_files') - before), 0)

    def test_repeated_atomic_staging_does_not_retain_per_write_types(self):
        with TemporaryDirectory(prefix='r7-abi-stage-') as directory:
            root = Path(directory)
            relative = 'inbox/strategies/lifetime/strategy.json'
            stage_author_input(root, relative, b'first')
            self.assertEqual(read_bounded(root, relative, 64), b'first')
            before = retained_pointer_inputs('application.cloud.safe_files')
            for number in range(32):
                raw = str(number).encode('ascii')
                stage_author_input(root, relative, raw)
                self.assertEqual(read_bounded(root, relative, 64), raw)
            self.assertEqual(len(retained_pointer_inputs('application.cloud.safe_files') - before), 0)

    def test_repeated_actual_hardware_sampling_does_not_retain_per_sample_types(self):
        with TemporaryDirectory(prefix='r7-abi-resource-') as directory:
            first = inspect_hardware(Path(directory))
            before = retained_pointer_inputs('application.platform.resources')
            for _ in range(32):
                report = inspect_hardware(Path(directory))
                self.assertEqual(report.physical_memory_bytes, first.physical_memory_bytes)
                self.assertGreater(report.available_memory_bytes, 0)
                self.assertLessEqual(report.available_memory_bytes, report.physical_memory_bytes)
            self.assertEqual(len(retained_pointer_inputs('application.platform.resources') - before), 0)
