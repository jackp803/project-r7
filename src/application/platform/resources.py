"""Measured hardware and conservative research admission, without GPU startup."""

from dataclasses import asdict, dataclass
import ctypes
import os
from pathlib import Path
import platform
import shutil

from application.platform.paths import existing_ancestor

GIB = 1024**3


@dataclass(frozen=True)
class HardwareReport:
    cpu_model: str
    logical_cores: int
    physical_memory_bytes: int
    available_memory_bytes: int
    disk_free_bytes: int
    disk_total_bytes: int
    filesystem: str
    os_name: str
    os_version: str
    architecture: str
    gpu_status: str = "NOT_REQUIRED"
    memory_enforcement: str = "SOFT_LIMIT_ONLY"

    def to_dict(self):
        return asdict(self)


def _windows_memory():
    class MemoryStatus(ctypes.Structure):
        _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
            (name, ctypes.c_ulonglong) for name in (
                "total_phys", "avail_phys", "total_page", "avail_page",
                "total_virtual", "avail_virtual", "avail_extended")]
    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    function = ctypes.WinDLL("kernel32", use_last_error=True).GlobalMemoryStatusEx
    function.argtypes = [ctypes.POINTER(MemoryStatus)]
    function.restype = ctypes.c_int
    if not function(ctypes.byref(status)):
        raise ctypes.WinError(ctypes.get_last_error())
    return status.total_phys, status.avail_phys


def _memory():
    if os.name == "nt":
        return _windows_memory()
    if platform.system() == "Linux":
        rows = {}
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            key, value = line.split(":", 1)
            rows[key] = int(value.split()[0]) * 1024
        return rows["MemTotal"], rows["MemAvailable"]
    raise RuntimeError("Unsupported hardware diagnostic platform")


def _cpu():
    if os.name == "nt":
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                           r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
            return str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
    for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return platform.processor() or "UNKNOWN"


def _filesystem(path):
    if os.name == "nt":
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        volume = ctypes.create_unicode_buffer(32768)
        get_path = kernel.GetVolumePathNameW
        get_path.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        get_path.restype = wintypes.BOOL
        if not get_path(str(path), volume, len(volume)):
            raise ctypes.WinError(ctypes.get_last_error())
        drive_type = kernel.GetDriveTypeW
        drive_type.argtypes, drive_type.restype = [wintypes.LPCWSTR], wintypes.UINT
        if drive_type(volume) == 4:  # DRIVE_REMOTE includes mapped network drives.
            return "NETWORK"
        name = ctypes.create_unicode_buffer(256)
        get_info = kernel.GetVolumeInformationW
        get_info.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD,
                             ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
                             ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR, wintypes.DWORD]
        get_info.restype = wintypes.BOOL
        if not get_info(volume, None, 0, None, None, None, name, len(name)):
            raise ctypes.WinError(ctypes.get_last_error())
        return name.value
    # Longest matching mount; decode mount-table escapes, never invoke a shell.
    selected = (0, "UNKNOWN")
    for line in Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines():
        before, after = line.split(" - ", 1)
        mount = before.split()[4]
        for encoded, decoded in ((r"\040", " "), (r"\011", "\t"), (r"\134", "\\")):
            mount = mount.replace(encoded, decoded)
        if path.is_relative_to(Path(mount)) and len(mount) > selected[0]:
            selected = (len(mount), after.split()[0])
    return selected[1]


def require_local_database_volume(database_path: Path):
    filesystem = _filesystem(existing_ancestor(database_path)).lower()
    if (filesystem in {"unknown", "network", "nfs", "nfs4", "cifs", "smbfs", "9p"}
            or filesystem.startswith("fuse")):
        raise ValueError("Canonical database requires a verified local filesystem")


def inspect_hardware(data_root: Path) -> HardwareReport:
    root = existing_ancestor(Path(data_root))
    total, available = _memory()
    disk = shutil.disk_usage(root)
    return HardwareReport(_cpu(), os.cpu_count() or 1, total, available,
                          disk.free, disk.total, _filesystem(root),
                          platform.system(), platform.version(), platform.machine())


@dataclass(frozen=True)
class AdmissionDecision:
    allowed: bool
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ResourcePolicy:
    physical_memory_bytes: int
    memory_soft_budget_bytes: int
    worker_count: int = 1
    memory_enforcement: str = "SOFT_LIMIT_ONLY"

    @classmethod
    def conservative(cls, physical_memory_bytes: int):
        if type(physical_memory_bytes) is not int or physical_memory_bytes <= 0:
            raise ValueError("Measured physical memory required")
        return cls(physical_memory_bytes, min(8 * GIB, physical_memory_bytes * 2 // 5))

    def admission(self, *, available_memory_bytes, disk_free_bytes, disk_total_bytes):
        reasons = []
        for value in (available_memory_bytes, disk_free_bytes, disk_total_bytes):
            if type(value) is not int or value < 0:
                raise ValueError("Measured nonnegative resource counts required")
        if disk_total_bytes == 0 or disk_free_bytes > disk_total_bytes:
            raise ValueError("Invalid measured disk capacity")
        if available_memory_bytes < max(2 * GIB, self.physical_memory_bytes * 15 // 100):
            reasons.append("RESEARCH_MEMORY_PRESSURE")
        if disk_free_bytes < max(2 * GIB, disk_total_bytes * 5 // 100):
            reasons.append("RESEARCH_DISK_PRESSURE")
        return AdmissionDecision(not reasons, tuple(reasons))
