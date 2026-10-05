"""Private recovery must retain actual selected data and accepted packages."""
from contextlib import closing, redirect_stdout
from dataclasses import asdict
import importlib, importlib.util, io, json, os, sqlite3, unittest
from pathlib import Path
from application.config import load_config
from application.platform.private_files import require_private
from tests.application import test_local_owner_composition


class ProductDataBackupTests(unittest.TestCase):
    def setUp(self):
        fixture = test_local_owner_composition.LocalOwnerCompositionTests()
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        self.fixture, self.config, self.data = fixture, fixture.config, fixture.root
        self.owners = fixture.configured()
        with self.owners.inbox_factory() as inbox:
            self.assertEqual(inbox.scan_once(fixture.clock()).accepted, 1)
        self.services = self.owners.control_services()
        self.services.execute('SETTINGS_UPDATE', 'settings',
            {'display_timezone': 'UTC', 'scan_interval': 45}, actor='synthetic-owner',
            human=None, command_id='backup-settings', expected_revision=0)
        self.backup = fixture.base / '完整 私密 備份'
        self.target = fixture.base / '還原 完整 世代'

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('application.platform.product_backup'),
            'Complete selected datasets, snapshots and settings recovery is missing')
        return importlib.import_module('application.platform.product_backup')

    def test_actual_selected_data_snapshots_and_settings_survive_fresh_restore(self):
        module = self.module()
        expected = {p.relative_to(self.data).as_posix(): p.read_bytes()
            for p in self.data.rglob('*') if p.is_file() and p.suffix not in ('.sqlite', '.sqlite3')
            and not p.name.endswith(('-wal', '-shm'))}
        result = module.create_product_backup(self.config, self.backup)
        self.assertEqual(result['status'], 'PRODUCT_DATA_BACKUP_VERIFIED')
        self.assertEqual(result['coverage'], 'COMPLETE_SUPPORTED_LOCAL_PROFILE')
        manifest = json.loads((self.backup / 'manifest.json').read_bytes())
        self.assertEqual({row['relative_path'] for row in manifest['files']}, set(expected))
        database_manifest = json.loads((self.backup / 'databases' / 'manifest.json').read_bytes())
        self.assertIn('settings', {row['logical_name'] for row in database_manifest['databases']})
        module.restore_product_backup(self.config, self.backup, self.target)
        restored = load_config(self.target / 'restored-product.json')
        self.assertIsNone(restored.cloud_root)
        self.assertTrue(restored.diagnostic_only)
        self.assertFalse(restored.paper_runtime_enabled)
        for relative, raw in expected.items():
            self.assertEqual((self.target / relative).read_bytes(), raw)
            self.assertEqual((self.data / relative).read_bytes(), raw)
            require_private(self.target / relative)
        from application.local_owners import LocalOwners
        owners = LocalOwners(restored, namespace='FIXTURE', clock=self.fixture.clock)
        services = owners.control_services()
        self.assertEqual(services.settings()['display_timezone'], 'UTC')
        self.assertIsNone(owners.inbox_factory)
        self.assertEqual(services.view('health')['restoration']['reconciliation'], 'REQUIRED')
        self.assertFalse(services.view('health')['live_authorized'])
        with owners.intake_factory() as intake:
            self.assertIsNotNone(intake.accepted_receipt('native-owner-fixture'))
        self.assertEqual(owners.resolver.manifest_view('native-owner-fixture')['submission_id'], 'native-owner-fixture')

    def test_unknown_durable_files_do_not_silently_receive_complete_coverage(self):
        module = self.module()
        unknown = self.data / 'unrecognized-durable.json'
        unknown.write_bytes(b'{"synthetic":"PRESERVE"}')
        with self.assertRaises(module.ProductBackupError) as error:
            module.create_product_backup(self.config, self.backup)
        self.assertIn('COVERAGE_GAP', str(error.exception))
        self.assertNotIn(str(self.data), str(error.exception))
        self.assertFalse((self.backup / 'manifest.json').exists())
        self.assertEqual(unknown.read_bytes(), b'{"synthetic":"PRESERVE"}')

    def test_transient_captures_are_excluded_without_opening_their_bytes(self):
        module = self.module()
        logs = self.data / 'worker-logs'
        logs.mkdir()
        (logs / 'synthetic-capture.log').write_bytes(b'SYNTHETIC_CAPTURE_EXCLUDED')
        result = module.create_product_backup(self.config, self.backup)
        self.assertIn('worker-logs', result['excluded_transient_roots'])
        self.assertFalse(any(p.name == 'synthetic-capture.log' for p in self.backup.rglob('*')))

    def test_same_size_tampering_and_extra_backup_files_fail_before_restore_creation(self):
        module = self.module()
        module.create_product_backup(self.config, self.backup)
        manifest = json.loads((self.backup / 'manifest.json').read_bytes())
        row = next(row for row in manifest['files'] if row['relative_path'] == 'cost.json')
        artifact = self.backup / 'files' / row['relative_path']
        raw = artifact.read_bytes()
        artifact.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
        with self.assertRaises(module.ProductBackupError):
            module.restore_product_backup(self.config, self.backup, self.target)
        self.assertFalse(self.target.exists())
        artifact.write_bytes(raw)
        (self.backup / 'unexpected.txt').write_bytes(b'EXTRA')
        with self.assertRaises(module.ProductBackupError):
            module.verify_product_backup(self.config, self.backup)

    def test_external_hard_links_are_refused_and_originals_remain_intact(self):
        module = self.module()
        original = (self.data / 'cost.json').read_bytes()
        os.link(self.data / 'cost.json', self.fixture.base / 'foreign-cost.json')
        with self.assertRaises(module.ProductBackupError):
            module.create_product_backup(self.config, self.backup)
        self.assertEqual((self.data / 'cost.json').read_bytes(), original)
        self.assertFalse((self.backup / 'manifest.json').exists())

    def test_source_change_during_copy_cannot_publish_complete_manifest(self):
        from unittest.mock import patch
        module = self.module()
        copier = module._copy_file
        def copy_then_change(source, target, row, end):
            result = copier(source, target, row, end)
            if source.name == 'cost.json':
                raw = source.read_bytes()
                source.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
            return result
        with patch.object(module, '_copy_file', copy_then_change), self.assertRaises(module.ProductBackupError):
            module.create_product_backup(self.config, self.backup)
        self.assertFalse((self.backup / 'manifest.json').exists())

    def test_actual_cli_returns_only_sanitized_backup_and_restore_facts(self):
        module = self.module()
        from application.cli import main
        profile = self.fixture.base / '設定.json'
        values = {key: str(value) if isinstance(value, Path) else value for key, value in asdict(self.config).items()}
        profile.write_text(json.dumps(values), encoding='utf-8')
        for command, extra, status in (
            ('backup-product-data', ['--destination', str(self.backup)], 'PRODUCT_DATA_BACKUP_VERIFIED'),
            ('verify-product-backup', ['--destination', str(self.backup)], 'PRODUCT_DATA_BACKUP_VERIFIED'),
            ('restore-product-data', ['--backup', str(self.backup), '--destination', str(self.target)], 'PRODUCT_DATA_RESTORE_STAGED')):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main([command, '--config', str(profile), *extra]), 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result['status'], status)
            self.assertEqual(result['financial_authority'], 'NONE')
            self.assertNotIn(str(self.fixture.base), output.getvalue())
    def test_complete_restored_generation_can_be_backed_up_again_without_reusing_its_profile(self):
        module=self.module();module.create_product_backup(self.config,self.backup)
        first=module.restore_product_backup(self.config,self.backup,self.target)
        selected=load_config(self.target/'restored-product.json')
        second_backup=self.fixture.base/'second-private-backup'
        third=self.fixture.base/'third-fresh-generation'
        try:result=module.create_product_backup(selected,second_backup)
        except module.ProductBackupError:self.fail('A complete inhibited restored product profile must support later private backups')
        self.assertEqual(result['coverage'],'COMPLETE_SUPPORTED_LOCAL_PROFILE')
        second=module.restore_product_backup(selected,second_backup,third)
        self.assertNotEqual(first['restore_generation_id'],second['restore_generation_id'])
        profile=load_config(third/'restored-product.json')
        self.assertEqual(profile.local_data_root,third)
        self.assertFalse(profile.paper_runtime_enabled)
        self.assertEqual((third/'dataset.json').read_bytes(),(self.data/'dataset.json').read_bytes())


if __name__ == '__main__':
    unittest.main()
