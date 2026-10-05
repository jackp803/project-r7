import importlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time
import unittest

from application.platform.processes import ResourceLimits, spawn_owned, terminate_owned


class ProcessScopeLockTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='R7 程序 排他 ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def module(self):
        return importlib.import_module('application.platform.scope_lock')

    def child(self, scope, name):
        ready = self.root / (name + '.json')
        owned = spawn_owned([sys.executable, '-m', 'tests.application.process_scope_fixture',
            '--scope', scope, '--root', str(self.root / 'locks'), '--ready', str(ready)],
            cwd=Path.cwd(), limits=ResourceLimits(10))
        self.addCleanup(lambda: terminate_owned(owned, deadline_seconds=5))
        deadline = time.monotonic() + 5
        while not ready.exists():
            if time.monotonic() >= deadline or owned.process.poll() is not None:
                self.fail('Actual scoped process did not publish readiness')
            time.sleep(0.02)
        return owned, json.loads(ready.read_bytes())

    def test_same_thread_reentrant_mutex_cannot_create_two_writer_instances(self):
        module = self.module()
        with module.ProcessScopeLock('fixture-same-process', lock_root=self.root / 'locks'):
            with self.assertRaises(module.ScopeBusy):
                with module.ProcessScopeLock('fixture-same-process', lock_root=self.root / 'locks'): pass

    def test_other_process_cannot_acquire_scope_and_normal_release_allows_successor(self):
        module = self.module()
        with module.ProcessScopeLock('fixture-contention', lock_root=self.root / 'locks'):
            owned, result = self.child('fixture-contention', 'contender')
            self.assertEqual(result['status'], 'BUSY')
            self.assertEqual(owned.wait(), 2)
        with module.ProcessScopeLock('fixture-contention', lock_root=self.root / 'locks'):
            pass

    def test_owned_process_death_releases_kernel_scope(self):
        module = self.module()
        owned, result = self.child('fixture-crash-release', 'owner')
        self.assertEqual(result['status'], 'LOCKED')
        self.assertTrue(terminate_owned(owned, deadline_seconds=5).reaped)
        with module.ProcessScopeLock('fixture-crash-release', lock_root=self.root / 'locks'):
            pass

    def test_independent_scopes_can_coexist_and_invalid_names_are_rejected(self):
        module = self.module()
        with module.ProcessScopeLock('fixture-one', lock_root=self.root / 'locks'):
            with module.ProcessScopeLock('fixture-two', lock_root=self.root / 'locks'): pass
        for scope in ('', '../escape', 'private\\name', 'name with spaces', 'x' * 257):
            with self.subTest(scope=scope), self.assertRaises(ValueError):
                module.ProcessScopeLock(scope, lock_root=self.root / 'locks')

    @unittest.skipUnless(sys.platform == 'win32', 'Actual Windows global kernel namespace required')
    def test_windows_scope_cannot_be_bypassed_with_a_different_local_directory(self):
        module = self.module()
        with module.ProcessScopeLock('fixture-other-root', lock_root=self.root / 'different-root'):
            owned, result = self.child('fixture-other-root', 'other-root')
            self.assertEqual(result['status'], 'BUSY')
            self.assertEqual(owned.wait(), 2)
