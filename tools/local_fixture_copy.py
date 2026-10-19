"""Copy-only filesystem peer for explicitly synthetic native software checks.

This is an executable protocol peer, not an ACK producer or a transport override.
It implements only the three argv shapes emitted by RcloneBridge publishing.
No networking, subprocesses, environment configuration or credential APIs exist.
The normal product bridge owns validation, remote byte comparison and ACKs.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from application.cloud.manifest import safe_relative
from application.cloud.safe_files import _windows_read, _posix_read, _windows_native_path
from application.datasets.catalog import decode
from application.platform.private_files import (
    create_private_directory, require_private, _filesystem_path)
from application.platform.supervision import _local_path


SCHEMA = 'r7-local-fixture-copy-v1'
ROOT_ID = 'r7-synthetic-fixture-cloud-v1'
KEYS = {'schema_version', 'data_class', 'scope_root', 'stage_root', 'work_root',
        'remote_root', 'remote_alias', 'drive_root_folder_id'}
PREFIXES = ('receipts/', 'reports/', 'capabilities/', 'research/', 'candidates/', 'paper/', 'live/')
MAX_FILE_BYTES = 256 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
MAX_ENTRIES = 4096
MAX_LIST_BYTES = 8 * 1024 * 1024


class LocalCopyError(ValueError):
    pass


def _reject():
    raise LocalCopyError('LOCAL_FIXTURE_COPY_REJECTED')


def _absolute(value):
    if (not isinstance(value, str) or not value or '\x00' in value or
            value.startswith(('\\\\', '//')) or '..' in value.replace('\\', '/').split('/')):
        _reject()
    path = Path(value)
    if not path.is_absolute():
        _reject()
    _local_path(path)
    return path


def _read(path, limit=MAX_FILE_BYTES):
    require_private(path)
    reader = _windows_read if os.name == 'nt' else _posix_read
    return reader(path, limit, require_single_link=True)


def _directory(path):
    _local_path(path)
    require_private(path, directory=True)


def _bounded_integer(value, lower, upper, suffix=''):
    pattern = r'([1-9][0-9]{0,10})' + re.escape(suffix)
    matched = re.fullmatch(pattern, value) if isinstance(value, str) else None
    if matched is None or not lower <= int(matched[1]) <= upper:
        _reject()
    return int(matched[1])


def _config(argv):
    if (not isinstance(argv, (list, tuple)) or not all(isinstance(value, str) for value in argv)
            or len(argv) < 15):
        _reject()
    tail = argv[-13:]
    if (tail[0] != '--config' or tail[2] != '--drive-root-folder-id' or
            tail[4:11] != ['--drive-skip-shortcuts', '--retries', '1', '--low-level-retries', '1', '--log-level', 'ERROR']
            or tail[11] != '--cache-dir'):
        _reject()
    profile = _absolute(tail[1])
    value = decode(_read(profile, 65536))
    if (not isinstance(value, dict) or set(value) != KEYS or value['schema_version'] != SCHEMA
            or value['data_class'] != 'SYNTHETIC_FIXTURE_ONLY'):
        _reject()
    roots = {name: _absolute(value[name]) for name in ('scope_root', 'stage_root', 'work_root', 'remote_root')}
    scope = roots['scope_root']
    for root in roots.values():
        _directory(root)
    children = [roots[name] for name in ('stage_root', 'work_root', 'remote_root')]
    if (profile.parent != scope or any(not root.is_relative_to(scope) or root == scope for root in children)
            or len({str(root).casefold() for root in children}) != 3
            or any(left.is_relative_to(right) or right.is_relative_to(left)
                   for index, left in enumerate(children) for right in children[index+1:])):
        _reject()
    for root in children:
        current = scope
        for part in root.relative_to(scope).parts:
            current /= part
            _directory(current)
    alias, drive = value['remote_alias'], value['drive_root_folder_id']
    if (not isinstance(alias, str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_-]{0,63}', alias)
            or not isinstance(drive, str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{9,127}', drive)
            or tail[3] != drive or _absolute(tail[12]) != roots['work_root'] / 'rclone-cache'):
        _reject()
    marker = {'root_id': ROOT_ID}
    for name in ('stage_root', 'remote_root'):
        if decode(_read(roots[name] / '.r7-root.json', 4096)) != marker:
            _reject()
    return roots, alias, argv[:-13]


def _remote(value, alias, *, root=False, marker=False):
    prefix = alias + ':'
    if not value.startswith(prefix):
        _reject()
    relative = value[len(prefix):]
    if root and relative == '':
        return relative
    if marker and relative == '.r7-root.json':
        return relative
    safe_relative(relative)
    if '\\' in relative or not relative.startswith(PREFIXES):
        _reject()
    return relative


def _below(root, path):
    if not path.is_relative_to(root) or path == root:
        _reject()
    current = root
    for part in path.relative_to(root).parts[:-1]:
        current /= part
        _directory(current)


@contextmanager
def _pinned_parent(path):
    """Pin ancestors; POSIX callers write relative to the final directory fd."""
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes as w
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, ctypes.c_void_p, w.DWORD, w.DWORD, w.HANDLE]
        kernel.CreateFileW.restype = w.HANDLE
        kernel.CloseHandle.argtypes = [w.HANDLE]
        handles = []
        try:
            current = Path(path.anchor)
            for part in path.parts[1:-1]:
                current /= part
                handle = kernel.CreateFileW(_windows_native_path(current), 0x80, 1, None, 3, 0x2200000, None)
                if handle == ctypes.c_void_p(-1).value:
                    _reject()
                handles.append(handle)
            _local_path(path)
            yield None
        finally:
            for handle in reversed(handles):
                kernel.CloseHandle(handle)
    else:
        descriptors = []
        try:
            descriptor = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
            descriptors.append(descriptor)
            for part in path.parts[1:-1]:
                descriptor = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                descriptors.append(descriptor)
            yield descriptor
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)


def _listing(remote):
    rows, pending, folded, total = [], [remote], set(), 0
    while pending:
        parent = pending.pop()
        _directory(parent)
        for entry in sorted(_filesystem_path(parent).iterdir()):
            path = parent / entry.name
            relative = path.relative_to(remote).as_posix()
            if relative != '.r7-root.json':
                safe_relative(relative)
                if relative.split('/')[0] not in {part[:-1] for part in PREFIXES}:
                    _reject()
            if relative.casefold() in folded or len(rows) >= MAX_ENTRIES:
                _reject()
            folded.add(relative.casefold())
            _local_path(path)
            directory = _filesystem_path(path).is_dir()
            if directory:
                _directory(path)
                pending.append(path)
                rows.append(dict(Path=relative, Name=path.name, IsDir=True, Size=0))
            else:
                raw = _read(path)
                total += len(raw)
                if total > MAX_TOTAL_BYTES:
                    _reject()
                rows.append(dict(Path=relative, Name=path.name, IsDir=False, Size=len(raw),
                    Hashes={'SHA-256': hashlib.sha256(raw).hexdigest()}))
    result = json.dumps(sorted(rows, key=lambda row: row['Path']), separators=(',', ':')).encode('utf-8')
    if len(result) > MAX_LIST_BYTES:
        _reject()
    return result


def _copy(roots, alias, arguments):
    if (len(arguments) != 12 or arguments[2:8] != ['--immutable', '--checksum', '--transfers', '1', '--checkers', '1']
            or arguments[8] != '--max-transfer' or arguments[10] != '--max-duration'):
        _reject()
    maximum = _bounded_integer(arguments[9], 4096, 16 * 1024**3, 'B')
    _bounded_integer(arguments[11], 1, 300, 's')
    source = _absolute(arguments[0])
    candidates = [roots[name] for name in ('stage_root', 'work_root') if source.is_relative_to(roots[name])]
    if len(candidates) != 1:
        _reject()
    _below(candidates[0], source)
    raw = _read(source, min(MAX_FILE_BYTES, maximum))
    relative = _remote(arguments[1], alias)
    destination = roots['remote_root'] / relative
    # Validate the complete existing peer before any mutation, including aliases
    # and total retained bytes. Existing immutable bytes are never replaced.
    listing = json.loads(_listing(roots['remote_root']))
    ancestors = ['/'.join(relative.split('/')[:index]) for index in range(1, len(relative.split('/')) + 1)]
    for component in ancestors:
        if any(row['Path'].casefold() == component.casefold() and row['Path'] != component for row in listing):
            _reject()
    present = {row['Path'] for row in listing}
    if relative in present:
        if _read(destination) != raw:
            _reject()
        return b''
    additions = sum(component not in present for component in ancestors)
    if sum(row['Size'] for row in listing) + len(raw) > MAX_TOTAL_BYTES or len(listing) + additions > MAX_ENTRIES:
        _reject()
    current = roots['remote_root']
    for part in Path(relative).parts[:-1]:
        current /= part
        if not _filesystem_path(current).exists():
            # Pin existing ancestors across creation to prevent alias races.
            with _pinned_parent(current):
                create_private_directory(current)
        _directory(current)
    with _pinned_parent(destination) as parent_fd:
        _below(roots['remote_root'], destination)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
        try:
            descriptor = os.open(_filesystem_path(destination) if parent_fd is None else destination.name,
                flags, 0o600, **({} if parent_fd is None else {'dir_fd': parent_fd}))
        except FileExistsError:
            if _read(destination) != raw:
                _reject()
            return b''
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if _read(destination) != raw:
            _reject()
    return b''


def run(argv):
    """Return actual protocol bytes, raising on every unsupported input/fault."""
    original = _config(list(argv))
    roots, alias, arguments = original
    operation, arguments = arguments[0], arguments[1:]
    if operation == 'lsjson' and arguments == [alias + ':', '--recursive', '--hash', '--no-modtime']:
        result = _listing(roots['remote_root'])
    elif operation == 'cat' and len(arguments) == 3 and arguments[1] == '--head':
        head = _bounded_integer(arguments[2], 1, MAX_FILE_BYTES + 1)
        relative = _remote(arguments[0], alias, marker=True)
        path = roots['remote_root'] / relative
        _below(roots['remote_root'], path)
        result = _read(path)[:head]
    elif operation == 'copyto':
        result = _copy(roots, alias, arguments)
    else:
        _reject()
    if _config(list(argv)) != original:
        _reject()
    return result


def main(argv=None, *, stdout=None, stderr=None):
    """Executable entry; diagnostics never echo paths, config or payload bytes."""
    stdout = sys.stdout.buffer if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    try:
        result = run(sys.argv[1:] if argv is None else argv)
    except (ValueError, OSError, RuntimeError, KeyError, TypeError):
        stderr.write('LOCAL_FIXTURE_COPY_REJECTED\n')
        return 2
    stdout.write(result)
    stdout.flush()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
