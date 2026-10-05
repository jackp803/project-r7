"""Read the opened bytes without following symlinks/reparse points."""

import ctypes
import os
from pathlib import Path
import stat
import uuid

from application.cloud.protocol import CloudError


def _windows_read(path: Path, limit):
    from ctypes import wintypes as w
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, ctypes.c_void_p, w.DWORD, w.DWORD, w.HANDLE]
    kernel.CreateFileW.restype = w.HANDLE
    kernel.CloseHandle.argtypes, kernel.CloseHandle.restype = [w.HANDLE], w.BOOL
    kernel.ReadFile.argtypes, kernel.ReadFile.restype = [w.HANDLE, ctypes.c_void_p, w.DWORD, ctypes.POINTER(w.DWORD), ctypes.c_void_p], w.BOOL
    class Information(ctypes.Structure):
        _fields_ = [("attributes", w.DWORD), ("creation", w.FILETIME), ("access", w.FILETIME),
                    ("write", w.FILETIME), ("volume", w.DWORD), ("size_high", w.DWORD),
                    ("size_low", w.DWORD), ("links", w.DWORD), ("index_high", w.DWORD), ("index_low", w.DWORD)]
    kernel.GetFileInformationByHandle.argtypes, kernel.GetFileInformationByHandle.restype = [w.HANDLE, ctypes.POINTER(Information)], w.BOOL
    handles = []
    try:
        current = Path(path.anchor)
        parts = path.parts[1:]
        for index, part in enumerate(parts):
            current = current / part
            directory = index < len(parts) - 1
            # No write/delete sharing while ancestors are pinned. OPEN_REPARSE_POINT
            # returns the link itself, never its target; reject its actual attributes.
            handle = kernel.CreateFileW(str(current), 0x80 if directory else 0x80000000,
                                        1, None, 3, 0x200000 | (0x2000000 if directory else 0), None)
            if handle == ctypes.c_void_p(-1).value:
                error = ctypes.get_last_error()
                if error in {2, 3}:
                    raise CloudError("INCOMPLETE_SYNC", "ARTIFACT_MISSING")
                raise CloudError("BLOCKED", "ARTIFACT_READ_DENIED")
            handles.append(handle)
            info = Information()
            if not kernel.GetFileInformationByHandle(handle, ctypes.byref(info)):
                raise CloudError("BLOCKED", "ARTIFACT_METADATA_UNAVAILABLE")
            if info.attributes & 0x400:
                raise CloudError("BLOCKED", "REPARSE_POINT_FORBIDDEN")
            if bool(info.attributes & 0x10) != directory:
                raise CloudError("BLOCKED", "ARTIFACT_TYPE_INVALID")
        chunks, size = [], 0
        while size <= limit:
            buffer = ctypes.create_string_buffer(min(65536, limit + 1 - size))
            read = w.DWORD()
            if not kernel.ReadFile(handles[-1], buffer, len(buffer), ctypes.byref(read), None):
                raise CloudError("INCOMPLETE_SYNC", "ARTIFACT_READ_INTERRUPTED")
            if not read.value:
                break
            chunks.append(buffer.raw[:read.value])
            size += read.value
        if size > limit:
            raise CloudError("BLOCKED", "ARTIFACT_SIZE_LIMIT")
        return b"".join(chunks)
    finally:
        for handle in reversed(handles):
            kernel.CloseHandle(handle)


def _posix_read(path: Path, limit):
    descriptors = []
    try:
        descriptor = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
        descriptors.append(descriptor)
        for index, part in enumerate(path.parts[1:]):
            directory = index < len(path.parts) - 2
            descriptor = os.open(part, os.O_RDONLY | os.O_NOFOLLOW | (os.O_DIRECTORY if directory else 0), dir_fd=descriptor)
            descriptors.append(descriptor)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise CloudError("BLOCKED", "ARTIFACT_TYPE_INVALID")
        chunks, size = [], 0
        while size <= limit:
            raw = os.read(descriptor, min(65536, limit + 1 - size))
            if not raw:
                break
            chunks.append(raw)
            size += len(raw)
        if size > limit:
            raise CloudError("BLOCKED", "ARTIFACT_SIZE_LIMIT")
        return b"".join(chunks)
    except FileNotFoundError:
        raise CloudError("INCOMPLETE_SYNC", "ARTIFACT_MISSING") from None
    except OSError:
        raise CloudError("BLOCKED", "ARTIFACT_LINK_OR_READ_DENIED") from None
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def read_bounded(root: Path, relative: str, limit: int) -> bytes:
    if type(limit) is not int or not 0 < limit <= 256 * 1024:
        raise CloudError("BLOCKED", "READ_LIMIT_INVALID")
    if relative not in {".r7-root.json", ".seal.json"}:
        from application.cloud.manifest import safe_relative
        safe_relative(relative)
    path = Path(root).absolute() / relative
    return _windows_read(path, limit) if os.name == "nt" else _posix_read(path, limit)


def _windows_stage(root, relative, raw, fault_hook, *, replace=False):
    from ctypes import wintypes as w
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    class Information(ctypes.Structure):
        _fields_ = [("attributes", w.DWORD), ("creation", w.FILETIME), ("access", w.FILETIME),
                    ("write", w.FILETIME), ("volume", w.DWORD), ("size_high", w.DWORD),
                    ("size_low", w.DWORD), ("links", w.DWORD), ("index_high", w.DWORD), ("index_low", w.DWORD)]
    signatures = {
        "CreateFileW": ([w.LPCWSTR,w.DWORD,w.DWORD,ctypes.c_void_p,w.DWORD,w.DWORD,w.HANDLE],w.HANDLE),
        "CreateDirectoryW": ([w.LPCWSTR,ctypes.c_void_p],w.BOOL),
        "GetFileInformationByHandle": ([w.HANDLE,ctypes.POINTER(Information)],w.BOOL),
        "CloseHandle": ([w.HANDLE],w.BOOL),
        "WriteFile": ([w.HANDLE,ctypes.c_void_p,w.DWORD,ctypes.POINTER(w.DWORD),ctypes.c_void_p],w.BOOL),
        "FlushFileBuffers": ([w.HANDLE],w.BOOL),
        "MoveFileExW": ([w.LPCWSTR,w.LPCWSTR,w.DWORD],w.BOOL),
    }
    for name,(args,result) in signatures.items():
        function = getattr(kernel,name)
        function.argtypes,function.restype = args,result
    target = root / relative
    current = Path(target.anchor)
    handles = []
    file_handle = None
    try:
        for part in target.parent.parts[1:]:
            current /= part
            handle = kernel.CreateFileW(str(current),0x80,1,None,3,0x200000|0x2000000,None)
            if handle == ctypes.c_void_p(-1).value:
                if ctypes.get_last_error() not in {2,3} or current == root or not current.is_relative_to(root):
                    raise CloudError("UNAVAILABLE","PUBLICATION_PARENT_UNAVAILABLE")
                if not kernel.CreateDirectoryW(str(current),None) and ctypes.get_last_error() != 183:
                    raise CloudError("UNAVAILABLE","PUBLICATION_PARENT_WRITE_FAILED")
                handle = kernel.CreateFileW(str(current),0x80,1,None,3,0x200000|0x2000000,None)
                if handle == ctypes.c_void_p(-1).value:
                    raise CloudError("UNAVAILABLE","PUBLICATION_PARENT_UNAVAILABLE")
            handles.append(handle)
            info=Information()
            if not kernel.GetFileInformationByHandle(handle,ctypes.byref(info)) or not info.attributes & 0x10:
                raise CloudError("BLOCKED","PUBLICATION_PARENT_INVALID")
            if info.attributes & 0x400:
                raise CloudError("BLOCKED","PUBLICATION_REPARSE_FORBIDDEN")
        stage = target.parent / (".r7-stage-" + uuid.uuid4().hex + ".tmp")
        file_handle=kernel.CreateFileW(str(stage),0x40000000,0,None,1,0x200000,None)  # CREATE_NEW
        if file_handle == ctypes.c_void_p(-1).value:
            file_handle=None
            raise CloudError("UNAVAILABLE","PUBLICATION_STAGE_WRITE_FAILED")
        midpoint=max(1,len(raw)//2)
        for index,chunk in enumerate((raw[:midpoint],raw[midpoint:])):
            offset=0
            while offset < len(chunk):
                data=ctypes.create_string_buffer(chunk[offset:])
                written=w.DWORD()
                if not kernel.WriteFile(file_handle,data,len(chunk)-offset,ctypes.byref(written),None) or not written.value:
                    raise CloudError("UNAVAILABLE","PUBLICATION_STAGE_WRITE_FAILED")
                offset += written.value
            if index == 0 and fault_hook is not None: fault_hook("AFTER_PARTIAL_STAGE_WRITE")
        if not kernel.FlushFileBuffers(file_handle):
            raise CloudError("UNAVAILABLE","PUBLICATION_STAGE_FLUSH_FAILED")
        kernel.CloseHandle(file_handle)
        file_handle=None
        if not kernel.MoveFileExW(str(stage),str(target),0x8 | (1 if replace else 0)):
            error=ctypes.get_last_error()
            if error in {80,183}:
                if read_bounded(root,relative,256*1024) != raw:
                    raise CloudError("CONFLICT","IMMUTABLE_DESTINATION_CHANGED")
            else:
                raise CloudError("UNAVAILABLE","PUBLICATION_FINALIZE_FAILED")
    finally:
        if file_handle is not None: kernel.CloseHandle(file_handle)
        for handle in reversed(handles): kernel.CloseHandle(handle)


def _posix_stage(root,relative,raw,fault_hook,*,replace=False):
    descriptors=[]
    file_descriptor=None
    target=root/relative
    try:
        descriptor=os.open(target.anchor,os.O_RDONLY|os.O_DIRECTORY)
        descriptors.append(descriptor)
        current=Path(target.anchor)
        for part in target.parent.parts[1:]:
            current /= part
            if current != root and current.is_relative_to(root):
                try: os.mkdir(part,mode=0o700,dir_fd=descriptor)
                except FileExistsError: pass
            descriptor=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=descriptor)
            descriptors.append(descriptor)
        stage=".r7-stage-"+uuid.uuid4().hex+".tmp"
        file_descriptor=os.open(stage,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=descriptor)
        midpoint=max(1,len(raw)//2)
        for index,chunk in enumerate((raw[:midpoint],raw[midpoint:])):
            view=memoryview(chunk)
            while view:
                written=os.write(file_descriptor,view)
                if not written: raise OSError("Stage write failed")
                view=view[written:]
            if index == 0 and fault_hook is not None: fault_hook("AFTER_PARTIAL_STAGE_WRITE")
        os.fsync(file_descriptor)
        os.close(file_descriptor)
        file_descriptor=None
        if replace:
            os.rename(stage,target.name,src_dir_fd=descriptor,dst_dir_fd=descriptor)
            os.fsync(descriptor)
            return
        try:
            os.link(stage,target.name,src_dir_fd=descriptor,dst_dir_fd=descriptor,follow_symlinks=False)
            os.fsync(descriptor)
        except FileExistsError:
            if read_bounded(root,relative,256*1024) != raw:
                raise CloudError("CONFLICT","IMMUTABLE_DESTINATION_CHANGED") from None
        # Temporary runtime-owned staging aliases are retained; this adapter never
        # deletes cloud artifacts. Explicit bounded housekeeping is separate.
    finally:
        if file_descriptor is not None: os.close(file_descriptor)
        for descriptor in reversed(descriptors): os.close(descriptor)


def write_immutable(root: Path, relative: str, raw: bytes, *, fault_hook=None):
    from application.cloud.manifest import safe_relative
    safe_relative(relative)
    root=Path(root).absolute()
    try:
        existing=read_bounded(root,relative,256*1024)
    except CloudError as error:
        if error.code != "INCOMPLETE_SYNC": raise
    else:
        if existing != raw:
            raise CloudError("CONFLICT","IMMUTABLE_DESTINATION_CHANGED")
        return
    try:
        if os.name == "nt": _windows_stage(root,relative,raw,fault_hook)
        else: _posix_stage(root,relative,raw,fault_hook)
    except CloudError:
        raise
    except OSError:
        raise CloudError("UNAVAILABLE","PUBLICATION_WRITE_FAILED") from None


def stage_author_input(root: Path, relative: str, raw: bytes):
    """Atomic copy-only bridge handoff; consumer snapshots remain immutable.

    Only unaccepted author inbox bytes may evolve. Dataset revision artifacts
    are immutable. Ancestors are pinned and links/reparse points rejected by
    the same native writer used for result publication.
    """
    from application.cloud.manifest import safe_relative
    safe_relative(relative)
    root = Path(root).absolute()
    mutable = relative.startswith('inbox/strategies/')
    if not mutable and not relative.startswith('datasets/'):
        raise CloudError('BLOCKED', 'AUTHOR_INPUT_NAMESPACE_REQUIRED')
    if not isinstance(raw, bytes) or len(raw) > 64*1024*1024:
        raise CloudError('BLOCKED', 'AUTHOR_INPUT_SIZE_LIMIT')
    read = _windows_read if os.name == 'nt' else _posix_read
    try:
        existing = read(root/relative, 64*1024*1024)
    except CloudError as error:
        if error.code != 'INCOMPLETE_SYNC':
            raise
    else:
        if existing == raw:
            return
        if not mutable:
            raise CloudError('CONFLICT', 'IMMUTABLE_DATASET_ARTIFACT_CHANGED')
    try:
        writer = _windows_stage if os.name == 'nt' else _posix_stage
        writer(root, relative, raw, None, replace=mutable)
    except CloudError:
        raise
    except OSError:
        raise CloudError('UNAVAILABLE', 'AUTHOR_INPUT_STAGE_FAILED') from None
