"""Owned process trees, bounded deadlines and kernel-scoped termination.

Windows descendants inherit a private Job Object. The bootstrap gate prevents
children racing assignment. Linux uses a new session/process group. No process
name matching or machine-wide termination is performed.
Reference: https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
"""

from dataclasses import dataclass, field
import ctypes
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time


@dataclass(frozen=True)
class ResourceLimits:
    timeout_seconds: float = 300
    memory_enforcement: str = field(default="SOFT_LIMIT_ONLY", init=False)

    def __post_init__(self):
        if (isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float))
                or not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0):
            raise ValueError("Positive finite process timeout required")


class _WindowsJob:
    def __init__(self):
        from ctypes import wintypes as w
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        declarations = {
            "CreateJobObjectW": ([ctypes.c_void_p, w.LPCWSTR], w.HANDLE),
            "SetInformationJobObject": ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD], w.BOOL),
            "QueryInformationJobObject": ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p], w.BOOL),
            "AssignProcessToJobObject": ([w.HANDLE, w.HANDLE], w.BOOL),
            "OpenProcess": ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
            "TerminateJobObject": ([w.HANDLE, w.UINT], w.BOOL),
            "CloseHandle": ([w.HANDLE], w.BOOL),
            "WaitForSingleObject": ([w.HANDLE, w.DWORD], w.DWORD),
        }
        for name, (arguments, result) in declarations.items():
            function = getattr(self.kernel, name)
            function.argtypes, function.restype = arguments, result

        class BasicLimits(ctypes.Structure):
            _fields_ = [("process_time", ctypes.c_longlong), ("job_time", ctypes.c_longlong),
                        ("flags", w.DWORD), ("min_working", ctypes.c_size_t),
                        ("max_working", ctypes.c_size_t), ("active_limit", w.DWORD),
                        ("affinity", ctypes.c_size_t), ("priority", w.DWORD), ("scheduling", w.DWORD)]

        class IoCounters(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in
                        ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]

        class ExtendedLimits(ctypes.Structure):
            _fields_ = [("basic", BasicLimits), ("io", IoCounters), ("process_memory", ctypes.c_size_t),
                        ("job_memory", ctypes.c_size_t), ("peak_process", ctypes.c_size_t),
                        ("peak_job", ctypes.c_size_t)]

        class Accounting(ctypes.Structure):
            _fields_ = [(name, ctypes.c_longlong) for name in ("user", "kernel", "period_user", "period_kernel")]
            _fields_ += [(name, w.DWORD) for name in ("faults", "total", "active", "terminated")]

        self.Accounting = Accounting
        self.handle = self.kernel.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = ExtendedLimits()
        limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.WinError(ctypes.get_last_error())
            self.close()
            raise error

    def assign(self, pid):
        process = self.kernel.OpenProcess(0x0101, False, pid)  # SET_QUOTA | TERMINATE
        if not process:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not self.kernel.AssignProcessToJobObject(self.handle, process):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            self.kernel.CloseHandle(process)

    def active_count(self):
        accounting = self.Accounting()
        if not self.kernel.QueryInformationJobObject(self.handle, 1, ctypes.byref(accounting),
                                                     ctypes.sizeof(accounting), None):
            raise ctypes.WinError(ctypes.get_last_error())
        return accounting.active

    def terminate(self):
        if not self.kernel.TerminateJobObject(self.handle, 124):
            raise ctypes.WinError(ctypes.get_last_error())

    def terminate_and_wait(self, deadline):
        """Accounting zero is not sufficient: wait on stable process handles."""
        from ctypes import wintypes as w
        count = 64
        handles = []
        try:
            while True:
                class ProcessIds(ctypes.Structure):
                    _fields_ = [("assigned", w.DWORD), ("listed", w.DWORD),
                                ("pids", ctypes.c_size_t * count)]
                ids = ProcessIds()
                if self.kernel.QueryInformationJobObject(self.handle, 3, ctypes.byref(ids),
                                                          ctypes.sizeof(ids), None):
                    break
                error = ctypes.get_last_error()
                if error != 234 or count >= 4096:  # ERROR_MORE_DATA
                    raise ctypes.WinError(error)
                count *= 2
            for pid in list(ids.pids)[:ids.listed]:
                process = self.kernel.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE
                if process:
                    handles.append(process)
                elif ctypes.get_last_error() != 87:  # Already exited PID is absent.
                    raise ctypes.WinError(ctypes.get_last_error())
            self.terminate()
            for process in handles:
                remaining_ms = max(0, math.ceil((deadline - time.monotonic()) * 1000))
                state = self.kernel.WaitForSingleObject(process, min(remaining_ms, 0xFFFFFFFE))
                if state == 258:
                    return False
                if state != 0:
                    raise ctypes.WinError(ctypes.get_last_error())
            while self.active_count() and time.monotonic() < deadline:
                time.sleep(0.01)
            return self.active_count() == 0
        finally:
            for process in handles:
                self.kernel.CloseHandle(process)

    def close(self):
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


@dataclass(frozen=True)
class TerminationReport:
    terminated: bool
    reaped: bool
    reason: str


@dataclass
class OwnedProcess:
    process: subprocess.Popen
    limits: ResourceLimits
    started_monotonic: float
    _job: object = field(default=None, repr=False)
    _lock: object = field(default_factory=threading.RLock, repr=False)
    _timer: object = field(default=None, repr=False)
    termination_report: TerminationReport | None = None

    def wait(self, timeout=None):
        """Reap a completed worker and its descendants, retaining the exit code."""
        code = self.process.wait(timeout=timeout)
        terminate_owned(self, deadline_seconds=5, reason="COMPLETED")
        return code


def spawn_owned(argv, *, cwd: Path, limits: ResourceLimits, stdout=None, stderr=None, env=None) -> OwnedProcess:
    if (not isinstance(argv, (list, tuple)) or not argv
            or any(not isinstance(arg, str) or not arg or "\x00" in arg for arg in argv)):
        raise ValueError("Nonempty argv strings required; shell commands forbidden")
    if not isinstance(limits, ResourceLimits):
        raise ValueError("ResourceLimits required")
    if getattr(sys, "frozen", False):
        bootstrap = [sys.executable, "_owned-process-bootstrap"]
    else:
        bootstrap = [sys.executable, str(Path(__file__).with_name("_process_bootstrap.py"))]
    job = _WindowsJob() if os.name == "nt" else None
    process = None
    try:
        process = subprocess.Popen(
            bootstrap + list(argv), cwd=Path(cwd), shell=False, stdin=subprocess.PIPE,
            stdout=stdout, stderr=stderr, env=env,
            creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS if os.name == "nt" else 0,
            start_new_session=os.name != "nt")
        if job is not None:
            job.assign(process.pid)
        elif hasattr(os, "setpriority"):
            os.setpriority(os.PRIO_PROCESS, process.pid, 10)
        handle = OwnedProcess(process, limits, time.monotonic(), job)
        process.stdin.write(b"GO\n")
        process.stdin.flush()
        process.stdin.close()
        handle._timer = threading.Timer(limits.timeout_seconds, terminate_owned,
                                         args=(handle,), kwargs={"deadline_seconds": 5, "reason": "TIMEOUT"})
        handle._timer.daemon = True
        handle._timer.start()
        return handle
    except BaseException:
        # Before GO the bootstrap cannot have launched any target descendants.
        if job is not None:
            job.close()
        if process is not None:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            if process.stdin is not None:
                process.stdin.close()
        raise


def terminate_owned(handle: OwnedProcess, *, deadline_seconds=5, reason="CANCELLED") -> TerminationReport:
    if (isinstance(deadline_seconds, bool) or not isinstance(deadline_seconds, (int, float))
            or not math.isfinite(deadline_seconds) or deadline_seconds <= 0):
        raise ValueError("Positive finite termination deadline required")
    with handle._lock:
        if handle.termination_report is not None and handle.termination_report.reaped:
            return handle.termination_report
        if handle._timer is not None:
            handle._timer.cancel()
        deadline = time.monotonic() + deadline_seconds
        if handle._job is not None:
            tree_reaped = handle._job.terminate_and_wait(deadline)
        else:
            try:
                os.killpg(handle.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            tree_reaped = False
        try:
            handle.process.wait(timeout=max(0.01, deadline - time.monotonic()))
            parent_reaped = True
        except subprocess.TimeoutExpired:
            parent_reaped = False
        if os.name != "nt":
            while time.monotonic() < deadline:
                try:
                    os.killpg(handle.process.pid, 0)
                except ProcessLookupError:
                    tree_reaped = True
                    break
                time.sleep(0.01)
        if handle._job is not None and tree_reaped:
            handle._job.close()
            handle._job = None
        handle.termination_report = TerminationReport(True, parent_reaped and tree_reaped, reason)
        return handle.termination_report


def process_alive(pid: int) -> bool:
    if type(pid) is not int or pid <= 0:
        raise ValueError("Positive process identifier required")
    if os.name == "nt":
        from ctypes import wintypes as w
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        kernel.OpenProcess.restype = w.HANDLE
        kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
        kernel.WaitForSingleObject.restype = w.DWORD
        kernel.CloseHandle.argtypes = [w.HANDLE]
        kernel.CloseHandle.restype = w.BOOL
        process = kernel.OpenProcess(0x100000, False, pid)
        if not process:
            error = ctypes.get_last_error()
            if error == 87:  # ERROR_INVALID_PARAMETER: PID absent
                return False
            raise ctypes.WinError(error)
        try:
            result = kernel.WaitForSingleObject(process, 0)
            if result == 0xFFFFFFFF:
                raise ctypes.WinError(ctypes.get_last_error())
            return result == 258
        finally:
            kernel.CloseHandle(process)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
