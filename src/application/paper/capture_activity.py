"""Actual runtime/child exclusion for nonfinancial archive recovery only."""
from contextlib import contextmanager,ExitStack
import hashlib
import os
from pathlib import Path
import threading

from application.platform.scope_lock import ProcessScopeLock,operational_lock_root
from application.platform.supervision import ProcessSupervisor,_local_path

_gate=threading.Lock()
_active={}
_recovering={}
_mint=object()


def _key(root):
    root=Path(root).absolute(); _local_path(root)
    return os.path.normcase(str(root))


@contextmanager
def capture_activity(root):
    key=_key(root); token=object()
    with _gate:
        if key in _recovering:raise ValueError('PUBLIC_CAPTURE_RECOVERY_IN_PROGRESS')
        _active.setdefault(key,set()).add(token)
    try:yield
    finally:
        with _gate:
            _active[key].discard(token)
            if not _active[key]:_active.pop(key)


def capture_lease(config,kind):
    if kind not in ('market','funding','preflight'):
        raise ValueError('Fixed public capture kind required')
    scope='public-capture:'+hashlib.sha256(_key(config.local_data_root).encode()).hexdigest()+':'+kind
    return ProcessScopeLock(scope,lock_root=operational_lock_root(config))


class _RecoveryFence:
    __slots__=('config','owner','key','generation')
    def __init__(self,config,owner,*,mint):
        if mint is not _mint:raise ValueError('Actual recovery scope required')
        self.config=config;self.owner=owner;self.key=_key(config.local_data_root)
        self.generation=owner.identity['process_generation_id']

    def require(self,root):
        if (_key(root)!=self.key or _recovering.get(self.key) is not self
                or self.owner.scope.handle is None or self.owner.scope.owner_thread!=threading.get_ident()
                or self.owner.identity['process_generation_id']!=self.generation):
            raise ValueError('Actual unchanged quiescent recovery owner required')
        self.owner.require_current()


@contextmanager
def fenced_recovery(config,owner):
    if (not isinstance(owner,ProcessSupervisor) or owner.role!='runtime' or owner.config!=config
            or owner.scope.handle is None or owner.scope.owner_thread!=threading.get_ident()
            or owner.identity is None or owner.identity['pid']!=os.getpid()):
        raise ValueError('Actual current runtime owner required for archive recovery')
    owner.require_current();key=_key(config.local_data_root)
    from . import public_feed,funding_feed
    if public_feed._unreaped or funding_feed._unreaped:
        raise ValueError('PUBLIC_CAPTURE_PRIOR_CHILD_REAP_UNCONFIRMED')
    with _gate:
        if _active.get(key) or key in _recovering:raise ValueError('PUBLIC_CAPTURE_NOT_QUIESCENT')
        fence=_RecoveryFence(config,owner,mint=_mint);_recovering[key]=fence
    try:
        with ExitStack() as stack:
            for kind in ('funding','market','preflight'):
                stack.enter_context(capture_lease(config,kind))
            fence.require(config.local_data_root)
            yield fence
            fence.require(config.local_data_root)
    finally:
        with _gate:
            if _recovering.get(key) is fence:_recovering.pop(key)
