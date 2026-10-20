"""User-authorized temporary system-awake request bound to one validation process."""
from datetime import datetime,timezone
from pathlib import Path
from ctypes import wintypes as w
import ctypes,json,sys
pid=int(sys.argv[1]);expected=datetime.fromisoformat(sys.argv[2]);output=Path(sys.argv[3])
if output.exists():raise ValueError('Fresh evidence file required')
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
k.CloseHandle.argtypes=[w.HANDLE];k.CloseHandle.restype=w.BOOL
k.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)];k.GetProcessTimes.restype=w.BOOL
k.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];k.WaitForSingleObject.restype=w.DWORD
k.SetThreadExecutionState.argtypes=[w.DWORD];k.SetThreadExecutionState.restype=w.DWORD
handle=k.OpenProcess(0x00100000|0x1000,False,pid)
if not handle:raise ctypes.WinError(ctypes.get_last_error())
start=datetime.now(timezone.utc);acquired=False;released=False;failure=None
try:
    stamps=[w.FILETIME() for _ in range(4)]
    if not k.GetProcessTimes(handle,*[ctypes.byref(item) for item in stamps]):raise ctypes.WinError(ctypes.get_last_error())
    ticks=(stamps[0].dwHighDateTime<<32)|stamps[0].dwLowDateTime
    created=datetime.fromtimestamp((ticks-116444736000000000)/10000000,tz=timezone.utc)
    if abs((created-expected).total_seconds())>0.001:raise ValueError('Validation process creation identity mismatch')
    if k.WaitForSingleObject(handle,0)!=258:raise ValueError('Validation process no longer running')
    if not k.SetThreadExecutionState(0x80000001):raise ctypes.WinError(ctypes.get_last_error())
    acquired=True
    print(json.dumps(dict(status='TEMPORARY_SYSTEM_AWAKE_ACQUIRED',validation_pid=pid,
        validation_created_at=created.isoformat(),acquired_at=start.isoformat(),display_required=False,
        permanent_settings_changed=False)),flush=True)
    while True:
        result=k.WaitForSingleObject(handle,30000)
        if result==0:break
        if result!=258:raise ctypes.WinError(ctypes.get_last_error())
except BaseException as error:
    failure=type(error).__name__;raise
finally:
    if acquired:released=bool(k.SetThreadExecutionState(0x80000000))
    k.CloseHandle(handle)
    report=dict(status='RELEASED_AFTER_VALIDATION_EXIT' if acquired and released and failure is None else 'ERROR',
        validation_pid=pid,acquired=acquired,explicitly_released=released,thread_exit_also_releases_request=True,
        started_at=start.isoformat(),finished_at=datetime.now(timezone.utc).isoformat(),failure_type=failure,
        user_authorization='Only while validation process lives; screen may turn off; no permanent power settings',
        display_required=False,away_mode=False,permanent_settings_changed=False)
    with output.open('x',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
