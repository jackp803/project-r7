"""Single-host process exclusion; acquisition never grants financial authority.

Windows uses a Global named kernel mutex, independent of local data roots.
POSIX uses a provisioned shared local lock directory and never unlinks locks.
Reference: https://learn.microsoft.com/en-us/windows/win32/sync/object-names
"""

import ctypes
import hashlib
import os
from pathlib import Path
import re
import stat
import threading


class ScopeBusy(RuntimeError):
    """Another local owner already holds this scope."""


_guard = threading.Lock()
_held = set()
POSIX_SCOPE_ROOT = '/run/r7/scopes'


def operational_lock_root(config):
    # Ubuntu service installation provisions this shared, protected directory
    # for the one dedicated R7 user. Never fall back to a per-profile lock root.
    return config.local_data_root / 'process-scopes' if os.name == 'nt' else Path(POSIX_SCOPE_ROOT)


class ProcessScopeLock:
    def __init__(self, scope, *, lock_root):
        if not isinstance(scope, str) or not re.fullmatch(r'[A-Za-z0-9_:-][A-Za-z0-9_.:-]{0,255}', scope):
            raise ValueError('Bounded local process scope required')
        root = Path(lock_root)
        if not root.is_absolute() or str(root).startswith(('\\\\', '//')) or '..' in root.parts:
            raise ValueError('Explicit local scope directory required')
        self.root = root
        self.key = hashlib.sha256(scope.encode('ascii')).hexdigest()
        self.handle = None
        self.kernel = None
        self.owner_thread = None
        self.abandoned = False

    def _windows_acquire(self):
        from ctypes import wintypes as w
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        signatures = {
            'CreateMutexW': ([ctypes.c_void_p, w.BOOL, w.LPCWSTR], w.HANDLE),
            'WaitForSingleObject': ([w.HANDLE, w.DWORD], w.DWORD),
            'ReleaseMutex': ([w.HANDLE], w.BOOL),
            'CloseHandle': ([w.HANDLE], w.BOOL),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(kernel, name)
            function.argtypes, function.restype = arguments, result
        handle = kernel.CreateMutexW(None, False, 'Global\\R7ProcessScope-' + self.key)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        outcome = kernel.WaitForSingleObject(handle, 0)
        if outcome not in (0, 0x80):  # WAIT_OBJECT_0 / WAIT_ABANDONED
            error = ctypes.get_last_error()
            kernel.CloseHandle(handle)
            if outcome == 0x102:
                raise ScopeBusy('Local process scope is already owned')
            raise ctypes.WinError(error)
        self.kernel, self.handle = kernel, handle
        self.abandoned = outcome == 0x80

    def _posix_acquire(self):
        import fcntl
        descriptors = []
        handle = None
        try:
            # Pin ancestors rather than following links or a replaced lock root.
            descriptor = os.open(self.root.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            descriptors.append(descriptor)
            for part in self.root.parts[1:]:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
                descriptor = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                                     dir_fd=descriptor)
                descriptors.append(descriptor)
            handle = os.open(self.key + '.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC,
                             0o600, dir_fd=descriptor)
            information = os.fstat(handle)
            if not stat.S_ISREG(information.st_mode) or information.st_nlink != 1:
                raise ValueError('Protected regular scope lock required')
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ScopeBusy('Local process scope is already owned') from None
            self.handle, handle = handle, None
        finally:
            if handle is not None:
                os.close(handle)
            for descriptor in reversed(descriptors):
                os.close(descriptor)

    def __enter__(self):
        key = (os.getpid(), self.key)
        with _guard:
            # Win32 mutexes are reentrant on the same thread. A second writer
            # object is forbidden even when the kernel would allow recursion.
            if key in _held:
                raise ScopeBusy('Local process scope is already owned')
            _held.add(key)
        try:
            if os.name == 'nt':
                self._windows_acquire()
            else:
                self._posix_acquire()
            self.owner_thread = threading.get_ident()
            return self
        except BaseException:
            with _guard:
                _held.discard(key)
            raise

    def __exit__(self, *unused):
        if self.handle is None:
            return
        if self.owner_thread != threading.get_ident():
            raise RuntimeError('Process scope must be released by its acquiring thread')
        try:
            if os.name == 'nt':
                released = self.kernel.ReleaseMutex(self.handle)
                error = ctypes.get_last_error()
                self.kernel.CloseHandle(self.handle)
                if not released:
                    raise ctypes.WinError(error)
            else:
                os.close(self.handle)
        finally:
            self.handle = None
            with _guard:
                _held.discard((os.getpid(), self.key))
