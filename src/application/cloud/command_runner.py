"""Bounded owned local tool execution; raw output stays private.

The bridge constructs allowlisted argv. This internal runner never receives
package commands and never prints captured bytes or discarded tool stderr.
Output storage is an application soft bound, not a kernel disk quota.
"""
from dataclasses import dataclass, field
import os
from pathlib import Path
import subprocess
import time
import uuid

from application.platform.private_files import create_private_directory, require_private, write_private_new
from application.platform.processes import ResourceLimits, spawn_owned, terminate_owned
from application.platform.supervision import _local_path


@dataclass(frozen=True)
class CommandResult:
    status: str
    exit_code: int
    tree_reaped: bool
    stdout: bytes = field(repr=False)
    captured_bytes: int
    elapsed_seconds: float


def run_bounded(argv, *, private_root, timeout_seconds, stdout_limit):
    """Run trusted argv with an owned deadline and owner-private capture.

    Partial/overflow/timed-out output is never returned. Private files remain
    locally for diagnosis; this function has no cloud or public log sink.
    """
    if (type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 300
            or type(stdout_limit) is not int or not 1 <= stdout_limit <= 8 * 1024 * 1024):
        raise ValueError('Bounded local command policy required')
    if (not isinstance(argv, (list, tuple)) or not 1 <= len(argv) <= 64
            or any(not isinstance(value, str) or not value or '\x00' in value or len(value) > 4096 for value in argv)
            or not Path(argv[0]).is_absolute()):
        raise ValueError('Trusted absolute executable and bounded argv required')
    root = Path(private_root)
    if not root.is_absolute() or '..' in root.parts or not root.is_dir():
        raise ValueError('Existing private local work parent required')
    _local_path(root)
    work = root / ('cloud-command-' + uuid.uuid4().hex)
    create_private_directory(work)
    output = work / 'stdout.private'
    write_private_new(output, b'')
    # Never inherit RCLONE_* overrides, proxy credentials, tokens or Python
    # import settings. The bridge explicitly passes its protected config ref.
    env = {name: os.environ[name] for name in ('SystemRoot', 'WINDIR', 'SystemDrive', 'TEMP', 'TMP', 'TMPDIR') if name in os.environ}
    env.update(PATH='', PYTHONUTF8='1')
    owned = None
    started = time.monotonic()
    deadline = started + timeout_seconds
    status = 'COMPLETE'
    with output.open('ab', buffering=0) as stream:
        try:
            owned = spawn_owned(list(argv), cwd=work, limits=ResourceLimits(timeout_seconds),
                                stdout=stream, stderr=subprocess.DEVNULL, env=env)
            while owned.process.poll() is None:
                if output.stat().st_size > stdout_limit:
                    status = 'OUTPUT_LIMIT_EXCEEDED'
                    terminate_owned(owned, deadline_seconds=3, reason=status)
                    break
                if time.monotonic() >= deadline:
                    status = 'TIMEOUT'
                    terminate_owned(owned, deadline_seconds=3, reason=status)
                    break
                time.sleep(0.02)
            code = owned.wait()
            if owned.termination_report.reason == 'TIMEOUT':
                status = 'TIMEOUT'
            elif output.stat().st_size > stdout_limit:
                status = 'OUTPUT_LIMIT_EXCEEDED'
            elif status == 'COMPLETE' and code != 0:
                status = 'COMMAND_FAILED'
        finally:
            if owned is not None:
                cleanup = terminate_owned(owned, deadline_seconds=3, reason='CLOUD_COMMAND_CLEANUP')
                if not cleanup.reaped:
                    raise RuntimeError('CLOUD_COMMAND_TREE_NOT_REAPED')
    require_private(output)
    size = output.stat().st_size
    raw = b''
    if status == 'COMPLETE':
        with output.open('rb') as stream:
            raw = stream.read(stdout_limit + 1)
        if len(raw) > stdout_limit or len(raw) != size:
            status, raw = 'OUTPUT_LIMIT_EXCEEDED', b''
    return CommandResult(status, code, owned.termination_report.reaped, raw,
                         size, time.monotonic() - started)
