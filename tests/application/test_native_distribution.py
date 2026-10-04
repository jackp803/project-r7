"""Native code/resource identities are measured locally and confer no authority."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from strategy.v02.capabilities import _revision, _source_revision


class NativeDistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='R7 封裝 識別 ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / '_internal' / 'source'
        (self.source / 'storage' / 'migrations').mkdir(parents=True)
        (self.source / 'module.py').write_bytes(b'VALUE = 7\n')
        (self.source / 'storage' / 'migrations' / '0001.sql').write_bytes(b'SELECT 1;\n')
        (self.root / 'R7.exe').write_bytes(b'SYNTHETIC_NATIVE_INVENTORY_FIXTURE')
        (self.root / '_internal' / 'native-code.bin').write_bytes(b'SYNTHETIC_COMPILED_CODE_FIXTURE')

    def distribution(self):
        return importlib.import_module('application.platform.distribution')

    def seal(self):
        return self.distribution().seal_distribution(self.root, source_revision='a' * 40,
            entrypoint='R7.exe', dependencies=[{'name': 'fixture-only', 'version': '0'}])

    def test_code_and_sql_inventory_must_not_be_empty(self):
        with TemporaryDirectory() as empty, self.assertRaises(ValueError):
            _source_revision(Path(empty))

    def test_frozen_source_hash_uses_complete_bundled_resources(self):
        with patch.object(sys, 'frozen', True, create=True), patch.object(sys, '_MEIPASS', str(self.root / '_internal'), create=True):
            self.assertEqual(_revision(), _source_revision(self.source))
            original = _revision()
            (self.source / 'storage' / 'migrations' / '0001.sql').write_bytes(b'SELECT 2;\n')
            self.assertNotEqual(_revision(), original)

    def test_sealed_inventory_binds_binary_source_resources_and_exact_dependencies(self):
        self.seal()
        identity = self.distribution().verify_distribution(self.root)
        self.assertEqual(identity['executable_revision'], 'a' * 40)
        self.assertEqual(identity['implementation_hash'], _source_revision(self.source))
        self.assertRegex(identity['build_hash'], '^sha256:[0-9a-f]{64}$')
        self.assertEqual(identity['worktree'], 'UNAVAILABLE')
        self.assertEqual(identity['financial_authority'], 'NONE')

    def test_binary_sql_missing_and_unexpected_file_changes_are_rejected(self):
        self.seal()
        native = self.root / '_internal' / 'native-code.bin'
        original = native.read_bytes()
        native.write_bytes(original + b'CHANGE')
        with self.assertRaises(ValueError): self.distribution().verify_distribution(self.root)
        native.write_bytes(original)
        migration = self.source / 'storage' / 'migrations' / '0001.sql'
        migration.unlink()
        with self.assertRaises(ValueError): self.distribution().verify_distribution(self.root)
        migration.write_bytes(b'SELECT 1;\n')
        (self.root / 'unexpected.py').write_bytes(b'UNTRUSTED = True\n')
        with self.assertRaises(ValueError): self.distribution().verify_distribution(self.root)

    def test_manifest_escape_duplicate_keys_and_wrong_platform_are_rejected(self):
        self.seal()
        path = self.root / 'distribution.json'
        original = path.read_bytes()
        payload = json.loads(original)
        payload['files']['../outside.exe'] = 'sha256:' + '0' * 64
        path.write_text(json.dumps(payload), encoding='utf-8')
        with self.assertRaises(ValueError): self.distribution().verify_distribution(self.root)
        path.write_bytes(b'{"profile":"x","profile":"y"}')
        with self.assertRaises(ValueError): self.distribution().verify_distribution(self.root)
        payload = json.loads(original)
        payload['os'] = 'UnsupportedOS'
        path.write_text(json.dumps(payload), encoding='utf-8')
        with self.assertRaises(ValueError): self.distribution().verify_distribution(self.root)

    def test_frozen_provenance_does_not_borrow_git_from_the_calling_directory(self):
        self.seal()
        from application.research.evidence import capture_provenance
        with patch.object(sys, 'frozen', True, create=True), \
                patch.object(sys, '_MEIPASS', str(self.root / '_internal'), create=True), \
                patch.object(sys, 'executable', str(self.root / 'R7.exe')), \
                patch('subprocess.run', side_effect=AssertionError('Native provenance must not invoke Git')):
            identity = capture_provenance()
        self.assertEqual(identity['executable_revision'], 'a' * 40)
        self.assertEqual(identity['worktree'], 'UNAVAILABLE')
        self.assertRegex(identity['build_hash'], '^sha256:[0-9a-f]{64}$')

    def test_resealing_an_existing_distribution_is_refused(self):
        self.seal()
        original = (self.root / 'distribution.json').read_bytes()
        with self.assertRaises(ValueError): self.seal()
        self.assertEqual((self.root / 'distribution.json').read_bytes(), original)

    def test_linked_root_is_refused_before_reading_manifest_or_source(self):
        self.seal()
        with TemporaryDirectory(prefix='R7 封裝 連結 ') as temporary:
            alias = Path(temporary) / 'linked-root'
            if os.name == 'nt':
                subprocess.run(['cmd', '/c', 'mklink', '/J', str(alias), str(self.root)],
                               check=True, capture_output=True)
            else:
                alias.symlink_to(self.root, target_is_directory=True)
            with patch.object(Path, 'open', side_effect=AssertionError('Linked manifest must not be read')):
                with self.assertRaises(ValueError): self.distribution().verify_distribution(alias)
