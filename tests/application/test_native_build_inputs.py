"""Native build rejects dirty/stale source and unsafe output before mutations."""
import importlib
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


class NativeBuildInputTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='R7 建置 輸入 ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'source'
        (self.root / 'src').mkdir(parents=True)
        (self.root / 'src' / 'fixture.py').write_bytes(b'FIXTURE_ONLY = True\n')
        for argv in (['git', 'init', '--quiet'], ['git', 'add', 'src/fixture.py'],
                     ['git', '-c', 'user.name=R7Fixture', '-c', 'user.email=fixture@example.invalid',
                      'commit', '--quiet', '-m', 'synthetic fixture']):
            subprocess.run(argv, cwd=self.root, check=True, capture_output=True)
        self.revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.root, text=True).strip()
        self.builder = importlib.import_module('tools.build_product')
        override = patch.object(self.builder, 'ROOT', self.root)
        override.start()
        self.addCleanup(override.stop)

    def test_exact_source_requires_clean_full_revision(self):
        identity = self.builder._source(self.revision)
        self.assertEqual(identity['worktree'], 'CLEAN')
        self.assertEqual(identity['revision'], self.revision)
        for revision in ('0' * 40, self.revision[:7], 'HEAD'):
            with self.subTest(revision=revision), self.assertRaises(ValueError):
                self.builder._source(revision)
        (self.root / 'src' / 'fixture.py').write_bytes(b'FIXTURE_ONLY = False\n')
        with self.assertRaises(ValueError): self.builder._source(self.revision)

    def test_inside_parent_and_relative_output_are_rejected_before_creation(self):
        for output in (self.root / 'output', self.root.parent, Path('relative-output')):
            with self.subTest(output=output), self.assertRaises(ValueError):
                self.builder.build(output, self.revision)
        self.assertFalse((self.root / 'output').exists())

    def test_existing_foreign_output_is_preserved(self):
        output = Path(self.temp.name) / 'existing'
        output.mkdir()
        sentinel = output / 'owner-content.txt'
        sentinel.write_bytes(b'PRESERVE_EXISTING_USER_CONTENT')
        with self.assertRaises(ValueError): self.builder.build(output, self.revision)
        self.assertEqual(sentinel.read_bytes(), b'PRESERVE_EXISTING_USER_CONTENT')
        self.assertEqual(list(output.iterdir()), [sentinel])

    def test_wrong_interpreter_fails_before_creating_build_root(self):
        output = Path(self.temp.name) / 'new-output'
        with patch.object(sys, 'version_info', (3, 14, 3)), self.assertRaises(ValueError):
            self.builder.build(output, self.revision)
        self.assertFalse(output.exists())

    def test_staged_resource_whitelist_bounds_windows_command_without_copying_other_data(self):
        migration = self.root / 'src' / 'storage' / 'migrations' / '0001.sql'
        migration.parent.mkdir(parents=True)
        migration.write_bytes(b'SELECT 1;\n')
        (self.root / 'src' / 'synthetic.env').write_bytes(b'SYNTHETIC_FORBIDDEN_PAYLOAD')
        cache = self.root / 'src' / '__pycache__'
        cache.mkdir()
        (cache / 'fixture.pyc').write_bytes(b'SYNTHETIC_CACHE')
        stage = Path(self.temp.name) / 'staged'
        resources = self.builder._stage_resources(stage)
        source = stage / 'source'
        copied = {path.relative_to(source).as_posix() for path in source.rglob('*') if path.is_file()}
        self.assertEqual(copied, {'fixture.py', 'storage/migrations/0001.sql'})
        self.assertEqual((source / 'storage/migrations/0001.sql').read_bytes(), migration.read_bytes())
        self.assertEqual(len(resources), 2)
        argv = [argument for origin, destination in resources for argument in ('--add-data', str(origin) + ':' + destination)]
        self.assertLess(len(subprocess.list2cmdline(argv)), 4096)

    def test_native_package_retains_selected_interpreter_license_material(self):
        interpreter = Path(self.temp.name) / 'interpreter'
        interpreter.mkdir()
        material = b'SYNTHETIC_INTERPRETER_LICENSE_FIXTURE\n'
        (interpreter / 'LICENSE.txt').write_bytes(material)
        licenses = Path(self.temp.name) / 'licenses'
        licenses.mkdir()
        with patch.object(sys, 'base_prefix', str(interpreter)):
            retained = self.builder._retain_interpreter_license(licenses)
        self.assertEqual(retained['package'], 'CPython')
        self.assertEqual((licenses / 'CPython-LICENSE.txt').read_bytes(), material)
