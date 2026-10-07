"""Reproduce fixed native-source grammar mismatch without reading private paths."""
import unittest
from unittest.mock import patch
import s09_local_paper_control_native_regression as driver
import s09_local_paper_control_native_http as probe
from application.datasets.catalog import DatasetError


class FixedSourceInputTests(unittest.TestCase):
    def reader(self, module):
        return getattr(module, 'read_input',
            lambda path, limit: module.read_local(path.parent, path.name, limit))

    def test_exact_bound_native_helper_is_readable(self):
        for module in (driver, probe):
            with self.subTest(module=module.__name__):
                path=module.REPO/'src/application/platform/_loopback_probe.py'
                raw=self.reader(module)(path, 1024**2)
                self.assertIn(b'class NoRedirect', raw)

    def test_unbound_private_name_never_reaches_kernel_reader(self):
        for module in (driver, probe):
            with self.subTest(module=module.__name__):
                with patch.object(module, '_windows_read', create=True,
                    side_effect=AssertionError('Unexpected protected read')) as native:
                    with self.assertRaises(DatasetError):
                        self.reader(module)(module.BASE/'.env', 1024)
                    native.assert_not_called()

    def test_ordinary_public_input_remains_cloud_grammar_checked(self):
        for module in (driver, probe):
            with self.subTest(module=module.__name__):
                with patch.object(module, 'read_local', return_value=b'public') as reader:
                    path=module.BASE/'public.json'
                    self.assertEqual(self.reader(module)(path, 1024), b'public')
                    reader.assert_called_once_with(path.parent, path.name, 1024)


if __name__=='__main__':unittest.main()
