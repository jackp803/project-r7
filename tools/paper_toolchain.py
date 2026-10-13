"""Read actual local PQR execution identities; no provider or browser navigation."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import tempfile
import unittest

from application.platform.processes import ResourceLimits,spawn_owned
from registry.product_assessment import canonical


def _hash(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):value.update(chunk)
    return 'sha256:'+value.hexdigest()


def _inventory(root,suffixes):
    values={p.relative_to(root).as_posix():_hash(p) for p in sorted(root.rglob('*'))
            if p.is_file() and p.suffix in suffixes and '__pycache__' not in p.parts}
    if not values:raise ValueError('Actual execution tool files unavailable')
    return 'sha256:'+hashlib.sha256(canonical(values).encode('utf-8')).hexdigest()


def _version(argv,root):
    with tempfile.TemporaryFile() as stream:
        owned=spawn_owned(list(map(str,argv)),cwd=root,limits=ResourceLimits(15),stdout=stream,stderr=subprocess.STDOUT)
        code=owned.wait();stream.seek(0);raw=stream.read(4096)
    if code!=0 or not owned.termination_report.reaped:raise ValueError('Actual local tool identity failed')
    return raw.decode('utf-8').strip()


def _windows_version(path):
    from ctypes import wintypes as w
    dll=ctypes.WinDLL('version',use_last_error=True)
    dll.GetFileVersionInfoSizeW.argtypes=[w.LPCWSTR,ctypes.POINTER(w.DWORD)];dll.GetFileVersionInfoSizeW.restype=w.DWORD
    dll.GetFileVersionInfoW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,ctypes.c_void_p];dll.GetFileVersionInfoW.restype=w.BOOL
    dll.VerQueryValueW.argtypes=[ctypes.c_void_p,w.LPCWSTR,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(w.UINT)]
    dll.VerQueryValueW.restype=w.BOOL
    size=dll.GetFileVersionInfoSizeW(str(path),None)
    if not size:raise ValueError('Actual Windows browser file version unavailable')
    data=ctypes.create_string_buffer(size);pointer=ctypes.c_void_p();length=w.UINT()
    if (not dll.GetFileVersionInfoW(str(path),0,size,data)
            or not dll.VerQueryValueW(data,'\\',ctypes.byref(pointer),ctypes.byref(length)) or length.value<52):
        raise ValueError('Actual Windows browser file version invalid')
    words=ctypes.cast(pointer,ctypes.POINTER(w.DWORD))
    if words[0]!=0xFEEF04BD:raise ValueError('Actual Windows file version signature invalid')
    return '.'.join(str(v) for v in (words[2]>>16,words[2]&65535,words[3]>>16,words[3]&65535))


def measure(root):
    root=Path(root)
    python_files={'interpreter':_hash(sys.executable),
                  'unittest':_inventory(Path(unittest.__file__).parent,{'.py'})}
    library=(Path(sys.executable).parent/'python312.dll') if os.name=='nt' else (
        Path(sysconfig.get_config_var('LIBDIR'))/sysconfig.get_config_var('INSTSONAME'))
    python_files['library']=_hash(library)
    node=Path('C:/Program Files/nodejs/node.exe') if os.name=='nt' else Path('/usr/bin/node')
    browser=Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe') if os.name=='nt' else Path('/usr/bin/chromium')
    playwright=root/'ui/node_modules/playwright-core'
    version=json.loads((playwright/'package.json').read_bytes())['version']
    return {key:dict(version=version,hash=commitment,scope='LOCAL_EXECUTION_TOOL_ONLY')
        for key,version,commitment in (
            ('python',sys.version.split()[0],'sha256:'+hashlib.sha256(canonical(python_files).encode('utf-8')).hexdigest()),
            ('node',_version([node,'--version'],root),_hash(node)),
            ('browser',_windows_version(browser) if os.name=='nt' else _version([browser,'--version'],root),_hash(browser)),
            ('playwright',version,_inventory(playwright,{'.js','.mjs','.cjs','.json'})))}


def require_same(observed,frozen):
    if observed!=frozen:raise ValueError('Actual local execution toolchain differs from committed inventory')
