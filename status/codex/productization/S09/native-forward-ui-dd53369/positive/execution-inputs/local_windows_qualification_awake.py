"""Temporary current-thread awake request for bounded local qualification only.

Microsoft reference:
https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setthreadexecutionstate
No display/away-mode request or persistent power-policy mutation. Explicit user
sleep/lid/power-button behavior is respected. This is not a sleep-proof guarantee.
"""
from contextlib import contextmanager
import ctypes,os

@contextmanager
def awake_request(*,set_state=None):
 if set_state is None:
  if os.name!='nt':raise OSError('WINDOWS_LOCAL_QUALIFICATION_HOST_REQUIRED')
  kernel=ctypes.WinDLL('kernel32',use_last_error=True)
  set_state=kernel.SetThreadExecutionState
  set_state.argtypes=[ctypes.c_uint32];set_state.restype=ctypes.c_uint32
 previous=set_state(0x80000001)
 if not previous:raise OSError('LOCAL_AWAKE_REQUEST_DENIED')
 evidence=dict(scope='CURRENT_THREAD_ACTIVE_QUALIFICATION_ONLY;NO_PERSISTENT_POWER_POLICY_CHANGE',
  requested=True,request_flags='ES_CONTINUOUS|ES_SYSTEM_REQUIRED',previous_state=int(previous),restored=False,
  explicit_user_sleep='NOT_PREVENTED',display_or_away_mode_request='NONE')
 try:yield evidence
 finally:
  restored=set_state(0x80000000|int(previous))
  if not restored:raise OSError('LOCAL_AWAKE_REQUEST_RESTORE_NOT_CONFIRMED')
  evidence['restored']=True
