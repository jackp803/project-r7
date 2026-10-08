"""Fresh owner-private local artifacts, never a cloud/credential transport."""
import ctypes
import os
from pathlib import Path
import stat

from application.platform.supervision import _local_path
from application.cloud.safe_files import _windows_native_path


def _filesystem_path(path):
    """Native spelling only; original logical path checks still precede I/O."""
    return Path(_windows_native_path(path)) if os.name=='nt' else Path(path)


def _windows_security():
    from ctypes import wintypes as w
    security = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    signatures = {
        'OpenProcessToken': ([w.HANDLE, w.DWORD, ctypes.POINTER(w.HANDLE)], w.BOOL),
        'GetTokenInformation': ([w.HANDLE, w.DWORD, ctypes.c_void_p, w.DWORD, ctypes.POINTER(w.DWORD)], w.BOOL),
        'ConvertSidToStringSidW': ([ctypes.c_void_p, ctypes.POINTER(w.LPWSTR)], w.BOOL),
        'ConvertStringSecurityDescriptorToSecurityDescriptorW': ([w.LPCWSTR, w.DWORD, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(w.DWORD)], w.BOOL),
        'SetFileSecurityW': ([w.LPCWSTR, w.DWORD, ctypes.c_void_p], w.BOOL),
        'GetFileSecurityW': ([w.LPCWSTR, w.DWORD, ctypes.c_void_p, w.DWORD, ctypes.POINTER(w.DWORD)], w.BOOL),
        'GetSecurityDescriptorDacl': ([ctypes.c_void_p, ctypes.POINTER(w.BOOL), ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(w.BOOL)], w.BOOL),
        'GetSecurityDescriptorControl': ([ctypes.c_void_p, ctypes.POINTER(w.WORD), ctypes.POINTER(w.DWORD)], w.BOOL),
        'GetAce': ([ctypes.c_void_p, w.DWORD, ctypes.POINTER(ctypes.c_void_p)], w.BOOL),
    }
    for name, (arguments, result) in signatures.items():
        function = getattr(security, name)
        function.argtypes, function.restype = arguments, result
    kernel.GetCurrentProcess.restype = w.HANDLE
    kernel.CloseHandle.argtypes, kernel.CloseHandle.restype = [w.HANDLE], w.BOOL
    kernel.LocalFree.argtypes, kernel.LocalFree.restype = [ctypes.c_void_p], ctypes.c_void_p
    return security, kernel


def _sid_string(security, kernel, sid):
    from ctypes import wintypes as w
    value = w.LPWSTR()
    if not security.ConvertSidToStringSidW(sid, ctypes.byref(value)):
        raise OSError('Private SID verification failed')
    try:
        return value.value
    finally:
        kernel.LocalFree(value)


def _current_sid(security, kernel):
    from ctypes import wintypes as w
    token = w.HANDLE()
    if not security.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
        raise OSError('Private owner verification failed')
    try:
        size = w.DWORD()
        security.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        if not 0 < size.value <= 65536:
            raise OSError('Private owner verification failed')
        buffer = ctypes.create_string_buffer(size.value)
        if not security.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size)):
            raise OSError('Private owner verification failed')
        return _sid_string(security, kernel, ctypes.c_void_p.from_buffer(buffer))
    finally:
        kernel.CloseHandle(token)


def require_private(path, *, directory=False):
    path = Path(path)
    _local_path(path)
    information = _filesystem_path(path).lstat()
    if (directory and not stat.S_ISDIR(information.st_mode)) or (not directory and not stat.S_ISREG(information.st_mode)):
        raise ValueError('Private regular artifact required')
    if not directory and information.st_nlink != 1:
        raise ValueError('Private single-link artifact required')
    if os.name != 'nt':
        if information.st_uid != os.getuid() or information.st_mode & 0o077:
            raise ValueError('Owner-private artifact required')
        return
    from ctypes import wintypes as w
    security, kernel = _windows_security()
    size = w.DWORD()
    security.GetFileSecurityW(_windows_native_path(path), 4, None, 0, ctypes.byref(size))
    if not 0 < size.value <= 65536:
        raise OSError('Private permissions unavailable')
    descriptor = ctypes.create_string_buffer(size.value)
    if not security.GetFileSecurityW(_windows_native_path(path), 4, descriptor, size, ctypes.byref(size)):
        raise OSError('Private permissions unavailable')
    control, revision = w.WORD(), w.DWORD()
    if not security.GetSecurityDescriptorControl(descriptor, ctypes.byref(control), ctypes.byref(revision)):
        raise OSError('Private permissions unavailable')
    if directory and not control.value & 0x1000:
        raise ValueError('Protected private directory required')
    present, defaulted, acl = w.BOOL(), w.BOOL(), ctypes.c_void_p()
    if not security.GetSecurityDescriptorDacl(descriptor, ctypes.byref(present), ctypes.byref(acl), ctypes.byref(defaulted)) or not present.value or not acl.value:
        raise ValueError('Owner-private permissions required')
    # ACL header has AceCount at byte offset four; only one explicit/inherited
    # ACCESS_ALLOWED_ACE for the current user is accepted, never Everyone.
    if ctypes.c_ushort.from_address(acl.value + 4).value != 1:
        raise ValueError('Owner-private permissions required')
    ace = ctypes.c_void_p()
    if not security.GetAce(acl, 0, ctypes.byref(ace)):
        raise OSError('Private permissions unavailable')
    if (ctypes.c_ubyte.from_address(ace.value).value != 0
            or ctypes.c_uint32.from_address(ace.value + 4).value != 0x1f01ff
            or _sid_string(security, kernel, ctypes.c_void_p(ace.value + 8)) != _current_sid(security, kernel)):
        raise ValueError('Owner-private permissions required')


def create_private_directory(path):
    path = Path(path)
    _local_path(path)
    _filesystem_path(path).mkdir(mode=0o700)  # Explicit existing parent; never replace/merge.
    if os.name == 'nt':
        security, kernel = _windows_security()
        descriptor = ctypes.c_void_p()
        sddl = 'D:P(A;OICI;FA;;;' + _current_sid(security, kernel) + ')'
        if not security.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, ctypes.byref(descriptor), None):
            raise OSError('Private permissions initialization failed')
        try:
            if not security.SetFileSecurityW(_windows_native_path(path), 4 | 0x80000000, descriptor):
                raise OSError('Private permissions initialization failed')
        finally:
            kernel.LocalFree(descriptor)
    require_private(path, directory=True)


def write_private_new(path, raw):
    path=Path(path)
    _local_path(path)
    descriptor = os.open(_filesystem_path(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    require_private(path)
