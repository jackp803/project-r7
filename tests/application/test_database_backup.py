from contextlib import closing
from contextlib import redirect_stdout
from dataclasses import asdict
import hashlib
import importlib
import importlib.util
import json
import os
import io
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import time
import unittest

from application.config import ProductConfig
from application.platform.scope_lock import ProcessScopeLock, operational_lock_root
from application.platform.scope_lock import ScopeBusy


class DatabaseBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='R7 私密 備份 ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / '本機 資料'
        self.data.mkdir()
        self.config = ProductConfig('r7-product-config-v0.2', 'backup-fixture', self.data,
                                    self.root / '雲端', self.data / 'canonical.sqlite3')
        self.destination = self.root / '私密 快照'
        self.writer = sqlite3.connect(self.config.database_path)
        self.addCleanup(self.writer.close)
        self.writer.execute('PRAGMA journal_mode=WAL')
        self.writer.execute('CREATE TABLE probe(value TEXT NOT NULL)')
        self.writer.execute("INSERT INTO probe VALUES('committed canonical')")
        self.writer.commit()

    def module(self):
        self.assertIsNotNone(importlib.util.find_spec('application.platform.backup'),
                             'The delegated local database snapshot feature is not implemented')
        return importlib.import_module('application.platform.backup')

    def backup(self):
        return self.module().create_database_backup(self.config, self.destination, timeout_seconds=5)

    def test_committed_wal_and_separate_databases_are_backed_up_without_copying_wal(self):
        with closing(sqlite3.connect(self.data / 'intake.sqlite')) as db:
            db.execute('CREATE TABLE probe(value TEXT NOT NULL)')
            db.execute("INSERT INTO probe VALUES('committed intake')")
            db.commit()
        self.assertTrue(Path(str(self.config.database_path) + '-wal').exists())
        result = self.backup()
        self.assertEqual(result['status'], 'DATABASE_BACKUP_VERIFIED')
        self.assertEqual(result['financial_authority'], 'NONE')
        self.assertEqual(result['cloud_publication'], 'FORBIDDEN')
        manifest = json.loads((self.destination / 'manifest.json').read_bytes())
        self.assertEqual(manifest['data_class'], 'PRIVATE_LOCAL')
        self.assertEqual({row['logical_name'] for row in manifest['databases']}, {'canonical', 'intake'})
        self.assertEqual(set(manifest['absent_databases']), {'queue', 'research', 'control', 'auth', 'supervision'})
        for name, expected in (('canonical', 'committed canonical'), ('intake', 'committed intake')):
            with closing(sqlite3.connect((self.destination / (name + '.sqlite')).as_uri() + '?mode=ro', uri=True)) as db:
                self.assertEqual(db.execute('SELECT value FROM probe').fetchall(), [(expected,)])
        self.assertFalse(list(self.destination.glob('*-wal')))
        self.assertFalse(list(self.destination.glob('*-shm')))
        self.assertEqual(self.writer.execute('SELECT value FROM probe').fetchall(), [('committed canonical',)])
        self.assertEqual(self.module().verify_database_backup(self.config, self.destination)['status'], 'DATABASE_BACKUP_VERIFIED')

    def test_active_native_owner_excludes_backup_before_destination_creation(self):
        module = self.module()
        for role in ('control', 'research', 'runtime', 'cloud'):
            with self.subTest(role=role), ProcessScopeLock(role + ':' + self.config.product_instance_id,
                                                         lock_root=operational_lock_root(self.config)):
                with self.assertRaises(module.BackupError):
                    self.backup()
                self.assertFalse(self.destination.exists())

    def test_external_uncommitted_sqlite_writer_blocks_without_hanging_or_leaking(self):
        module = self.module()
        self.writer.execute('BEGIN IMMEDIATE')
        self.writer.execute("INSERT INTO probe VALUES('uncommitted must not leak')")
        started = time.monotonic()
        with self.assertRaises(module.BackupError):
            self.backup()
        self.assertLess(time.monotonic() - started, 4)
        self.assertFalse((self.destination / 'manifest.json').exists())
        self.writer.rollback()
        self.assertEqual(self.writer.execute('SELECT COUNT(*) FROM probe').fetchone()[0], 1)

    def test_corrupt_database_cannot_publish_ready_manifest_or_modify_source(self):
        module = self.module()
        damaged = self.data / 'queue.sqlite'
        damaged.write_bytes(b'not a sqlite database')
        with self.assertRaises(module.BackupError):
            self.backup()
        self.assertEqual(damaged.read_bytes(), b'not a sqlite database')
        self.assertFalse((self.destination / 'manifest.json').exists())

    def test_existing_destination_is_preserved_and_not_merged(self):
        module = self.module()
        self.destination.mkdir()
        marker = self.destination / 'operator-file.txt'
        marker.write_text('keep this', encoding='utf-8')
        with self.assertRaises(module.BackupError):
            self.backup()
        self.assertEqual(list(self.destination.iterdir()), [marker])
        self.assertEqual(marker.read_text(encoding='utf-8'), 'keep this')

    def test_cloud_or_source_destination_cannot_receive_private_database_backup(self):
        module = self.module()
        for destination in (self.config.cloud_root / 'private', self.data / 'private', self.data.parent):
            with self.subTest(destination=destination), self.assertRaises(module.BackupError):
                module.create_database_backup(self.config, destination)

    def test_changed_backup_bytes_are_rejected_by_read_only_verification(self):
        module = self.module()
        self.backup()
        path = self.destination / 'canonical.sqlite'
        with closing(sqlite3.connect(path)) as db:
            db.execute("INSERT INTO probe VALUES('tampered')")
            db.commit()
        before = path.read_bytes()
        with self.assertRaises(module.BackupError):
            module.verify_database_backup(self.config, self.destination)
        self.assertEqual(path.read_bytes(), before)

    def test_manifest_traversal_unknown_schema_and_duplicate_subjects_are_rejected(self):
        module = self.module()
        self.backup()
        path = self.destination / 'manifest.json'
        original = json.loads(path.read_bytes())
        for change in ('traversal', 'schema', 'duplicate', 'unknown'):
            altered = json.loads(json.dumps(original))
            if change == 'traversal': altered['databases'][0]['artifact'] = '../canonical.sqlite3'
            elif change == 'schema': altered['schema_version'] = 'future-unverified'
            elif change == 'duplicate': altered['databases'].append(altered['databases'][0])
            else: altered['authorization'] = 'LIVE'
            path.write_text(json.dumps(altered), encoding='utf-8')
            with self.subTest(change=change), self.assertRaises(module.BackupError):
                module.verify_database_backup(self.config, self.destination)

    def test_missing_canonical_store_cannot_be_certified_as_an_empty_backup(self):
        module = self.module()
        self.writer.close()
        self.config.database_path.unlink()
        with self.assertRaises(module.BackupError):
            self.backup()
        self.assertFalse((self.destination / 'manifest.json').exists())

    def test_snapshot_root_has_real_owner_private_filesystem_permissions(self):
        self.backup()
        if os.name != 'nt':
            self.assertEqual(self.destination.stat().st_mode & 0o777, 0o700)
            self.assertEqual((self.destination / 'manifest.json').stat().st_mode & 0o077, 0)
            return
        import ctypes
        from ctypes import wintypes as w
        security = ctypes.WinDLL('advapi32', use_last_error=True)
        security.GetFileSecurityW.argtypes = [w.LPCWSTR, w.DWORD, ctypes.c_void_p, w.DWORD, ctypes.POINTER(w.DWORD)]
        security.GetFileSecurityW.restype = w.BOOL
        size = w.DWORD()
        security.GetFileSecurityW(str(self.destination), 5, None, 0, ctypes.byref(size))
        descriptor = ctypes.create_string_buffer(size.value)
        self.assertTrue(security.GetFileSecurityW(str(self.destination), 5, descriptor, size, ctypes.byref(size)))
        control, revision = w.WORD(), w.DWORD()
        security.GetSecurityDescriptorControl.argtypes = [ctypes.c_void_p, ctypes.POINTER(w.WORD), ctypes.POINTER(w.DWORD)]
        self.assertTrue(security.GetSecurityDescriptorControl(descriptor, ctypes.byref(control), ctypes.byref(revision)))
        self.assertTrue(control.value & 0x1000, 'The actual Windows DACL must be protected from inherited grants')
        present, defaulted, acl = w.BOOL(), w.BOOL(), ctypes.c_void_p()
        security.GetSecurityDescriptorDacl.argtypes = [ctypes.c_void_p, ctypes.POINTER(w.BOOL), ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(w.BOOL)]
        self.assertTrue(security.GetSecurityDescriptorDacl(descriptor, ctypes.byref(present), ctypes.byref(acl), ctypes.byref(defaulted)))
        self.assertTrue(present.value and acl.value)
        class ACL(ctypes.Structure):
            _fields_ = [('revision', w.BYTE), ('unused', w.BYTE), ('size', w.WORD), ('count', w.WORD), ('unused2', w.WORD)]
        self.assertEqual(ctypes.cast(acl, ctypes.POINTER(ACL)).contents.count, 1)
        ace = ctypes.c_void_p()
        security.GetAce.argtypes = [ctypes.c_void_p, w.DWORD, ctypes.POINTER(ctypes.c_void_p)]
        self.assertTrue(security.GetAce(acl, 0, ctypes.byref(ace)))
        self.assertEqual(ctypes.c_ubyte.from_address(ace.value).value, 0, 'Only the creating owner receives an allow ACE')
        owner = ctypes.c_void_p()
        security.GetSecurityDescriptorOwner.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(w.BOOL)]
        self.assertTrue(security.GetSecurityDescriptorOwner(descriptor, ctypes.byref(owner), ctypes.byref(defaulted)))
        security.EqualSid.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self.assertTrue(security.EqualSid(owner, ctypes.c_void_p(ace.value + 8)))

    def test_read_only_verification_of_a_sealed_wal_header_never_creates_sidecars(self):
        module = self.module()
        self.backup()
        database = self.destination / 'canonical.sqlite'
        with closing(sqlite3.connect(database)) as db:
            self.assertEqual(db.execute('PRAGMA journal_mode=WAL').fetchone()[0], 'wal')
        self.assertFalse(list(self.destination.glob('*-wal')))
        manifest_path = self.destination / 'manifest.json'
        manifest = json.loads(manifest_path.read_bytes())
        row = next(row for row in manifest['databases'] if row['logical_name'] == 'canonical')
        row['sha256'] = 'sha256:' + hashlib.sha256(database.read_bytes()).hexdigest()
        row['bytes'] = database.stat().st_size
        manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
        before = {path.name: path.read_bytes() for path in self.destination.iterdir()}
        self.assertEqual(module.verify_database_backup(self.config, self.destination)['financial_authority'], 'NONE')
        self.assertEqual({path.name: path.read_bytes() for path in self.destination.iterdir()}, before)

    def test_backup_artifact_with_an_external_hard_link_is_not_certified_private(self):
        module = self.module()
        self.backup()
        os.link(self.destination / 'canonical.sqlite', self.root / 'alias.sqlite')
        with self.assertRaises(module.BackupError):
            module.verify_database_backup(self.config, self.destination)

    def test_actual_local_cli_creates_and_verifies_private_backup_without_printing_rows(self):
        from application.cli import main
        profile = self.root / '非機密 設定.json'
        values = {key: str(value) if isinstance(value, Path) else value for key, value in asdict(self.config).items()}
        profile.write_text(json.dumps(values), encoding='utf-8')
        for command in ('backup-databases', 'verify-database-backup'):
            output = io.StringIO()
            with redirect_stdout(output):
                try:
                    result = main([command, '--config', str(profile), '--destination', str(self.destination)])
                except SystemExit as error:
                    result = error.code
            with self.subTest(command=command):
                self.assertEqual(result, 0)
                payload = json.loads(output.getvalue())
                self.assertEqual(payload['status'], 'DATABASE_BACKUP_VERIFIED')
                self.assertEqual(payload['database_count'], 1)
                self.assertEqual(payload['restore'], 'NOT_PERFORMED')
                self.assertNotIn('committed canonical', output.getvalue())
                self.assertNotIn(str(self.root), output.getvalue())

    def test_trusted_owner_enrollment_cannot_create_an_unfenced_auth_store_during_backup(self):
        from unittest.mock import patch
        from application.entrypoints import enroll_owner
        class LocalTerminal:
            def isatty(self):
                return True
        with ProcessScopeLock('control:' + self.config.product_instance_id, lock_root=operational_lock_root(self.config)):
            with patch('sys.stdin', LocalTerminal()), patch('application.entrypoints.getpass.getpass', side_effect=AssertionError('A busy profile must not request a password')):
                with self.assertRaises(ScopeBusy):
                    enroll_owner(self.config, 'fixture-owner')
        self.assertFalse((self.data / 'local-auth.sqlite').exists())

    def test_backup_changed_during_schema_inspection_cannot_receive_verified_result(self):
        from unittest.mock import patch
        module = self.module()
        self.backup()
        facts = module._database_facts
        def inspect_then_change(db):
            result = facts(db)
            with closing(sqlite3.connect(self.destination / 'canonical.sqlite')) as writer:
                writer.execute("UPDATE probe SET value='changed at inspection'")
                writer.commit()
            return result
        with patch.object(module, '_database_facts', side_effect=inspect_then_change):
            with self.assertRaises(module.BackupError):
                module.verify_database_backup(self.config, self.destination)


if __name__ == '__main__':
    unittest.main()
