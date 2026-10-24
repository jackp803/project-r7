"""E6-owned readonly history work; no public proof/result import capability.

SQLite source/proof and the actual registered internal producer stay with E6.
Reuse only existing low-level platform process ownership and cancellation.
Not yet wired into ordinary runtime admission or a protection callback.
"""
from dataclasses import dataclass,field
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid

from application.platform.processes import ResourceLimits,spawn_owned,terminate_owned
from storage.paper_process import PaperProcessJournal,_digest
from storage.runtime_models import RuntimeValidationError
from strategy.v02.capabilities import _revision

DEADLINE_SECONDS=300
MAX_PACKET_BYTES=16384


def _invalid():
    raise RuntimeValidationError('PAPER_HISTORY_WORKER_INVALID','Actual same-instance owned Paper audit required')


@dataclass
class _Session:
    token:str
    run_id:str
    state:object
    source_file_key:tuple
    cancel:object=field(default_factory=threading.Event)
    lock:object=field(default_factory=threading.Lock)
    thread:object=None
    handle:object=None
    result:object=None
    done:bool=False
    reaped:bool=False


class OwnedPaperHistoryAudit:
    def __init__(self,journal):
        if type(journal) is not PaperProcessJournal or journal._background_history is not None:_invalid()
        self.journal=journal;self._thread=threading.get_ident();self._session=None;self._closed=False
        self._implementation=_revision()
        self._last=dict(active=False,reaped=True,status='NOT_STARTED',snapshot_writes=None)
        journal._background_history=self

    def _owner(self):
        if self._closed or threading.get_ident()!=self._thread:_invalid()

    def start(self,run_id):
        self._owner()
        if self._session is not None:_invalid()  # At most one audit process.
        journal=self.journal;db=journal._db;history=journal._history
        if db.in_transaction:_invalid()
        journal.recover_current(run_id)  # E4 checks outside the read transaction.
        epoch=history._epoch();db.execute('BEGIN')
        try:state=history._begin(run_id,epoch)
        finally:db.rollback()
        if history._epoch()!=epoch:_invalid()
        source=next(row[2] for row in db.execute('PRAGMA database_list') if row[1]=='main')
        source=Path(source);stat=source.stat()
        if not source.is_absolute():_invalid()
        session=_Session(uuid.uuid4().hex,run_id,state,(stat.st_dev,stat.st_ino))
        history._states[run_id]=state;self._session=session
        self._last=dict(active=True,reaped=False,status='HISTORY_AUDIT_IN_PROGRESS',snapshot_writes=None)
        session.thread=threading.Thread(target=self._run,args=(session,source),daemon=True,
            name='r7-paper-history-readonly')
        try:session.thread.start()
        except BaseException as error:
            session.cancel.set()
            # Native Thread.start reports a pre-dispatch refusal as RuntimeError.
            # If dispatch did occur, retain the session for confirmed cleanup.
            if isinstance(error,RuntimeError) and session.thread.ident is None:
                if history._states.get(run_id) is state:history._states.pop(run_id)
                self._session=None
                self._last=dict(active=False,reaped=True,status='HISTORY_WORKER_START_FAILED',snapshot_writes=None)
            raise
        return history.progress(run_id)

    def _run(self,session,source):
        owned=None;packet=None;reaped=False
        prefix=[sys.executable] if getattr(sys,'frozen',False) else [sys.executable,'-m','application']
        argv=prefix+['_paper-history-audit','--database',str(source),'--run-id',session.run_id,
            '--session-id',session.token,'--expected-implementation-hash',self._implementation]
        try:
            if session.cancel.is_set():raise InterruptedError()
            cwd=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parents[2]
            owned=spawn_owned(argv,cwd=cwd,
                limits=ResourceLimits(DEADLINE_SECONDS),stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            with session.lock:session.handle=owned
            descriptor=owned.process.stdout.fileno();os.set_blocking(descriptor,False)
            chunks=[];size=0;started=time.monotonic()
            while True:
                if session.cancel.is_set() or time.monotonic()-started>=DEADLINE_SECONDS:raise InterruptedError()
                try:chunk=os.read(descriptor,min(65536,MAX_PACKET_BYTES+1-size))
                except BlockingIOError:session.cancel.wait(.02);continue
                if not chunk:break
                size+=len(chunk)
                if size>MAX_PACKET_BYTES:raise ValueError()
                chunks.append(chunk)
            if owned.wait(timeout=2)!=0 or not owned.termination_report.reaped:raise ValueError()
            packet=json.loads(b''.join(chunks))
        except (OSError,ValueError,RuntimeError,subprocess.SubprocessError):packet=None
        finally:
            if owned is None:reaped=True
            else:
                try:reaped=terminate_owned(owned,deadline_seconds=5).reaped
                except (OSError,RuntimeError,subprocess.SubprocessError):reaped=False
                finally:owned.process.stdout.close()
            with session.lock:
                session.result=packet;session.reaped=reaped;session.done=True

    def _matches(self,session,packet):
        if (type(packet) is not dict or set(packet)!={'schema_version','session_id','implementation_hash','snapshot'}
                or packet['schema_version']!='r7-owned-paper-history-audit-v0.1'
                or packet['session_id']!=session.token or packet['implementation_hash']!=self._implementation):return False
        value=packet['snapshot'];state=session.state;db=self.journal._db
        if type(value) is not dict:return False
        for key in ('verified_prefix_revision','current_revision','process_generation','snapshot_write_count'):
            if type(value.get(key)) is not int or value[key]<0:return False
        if (value.get('scope')!='DIAGNOSTIC_SNAPSHOT_NOT_RUNTIME_AUTHORITY' or value.get('run_id')!=session.run_id
                or value['snapshot_write_count']!=0 or value.get('source_file_key')!=list(session.source_file_key)
                or value.get('source_schema_version')!=state.epoch[0]
                or not state.target<=value['verified_prefix_revision']<=state.live_prefix
                or not state.current_revision<=value['current_revision']<=state.live_revision
                or not state.generation<=value['process_generation']<=state.live_generation):return False
        source=next(row[2] for row in db.execute('PRAGMA database_list') if row[1]=='main');stat=Path(source).stat()
        if (stat.st_dev,stat.st_ino)!=session.source_file_key:return False
        row=db.execute('SELECT prefix_hash FROM paper_process_published_prefixes WHERE run_id=? AND revision=?',
            (session.run_id,value['verified_prefix_revision'])).fetchone()
        checkpoint=db.execute('SELECT state_hash FROM paper_process_checkpoints WHERE run_id=? AND revision=?',
            (session.run_id,value['current_revision'])).fetchone()
        if (row is None or row[0]!=value.get('verified_prefix_hash') or checkpoint is None
                or checkpoint[0]!=value.get('current_state_hash')
                or _digest(self.journal._run(session.run_id)['binding_json'])!=value.get('binding_hash')):return False
        return True

    def poll(self,run_id):
        self._owner();session=self._session;history=self.journal._history
        if session is None:return history.progress(run_id)
        if session.run_id!=run_id:_invalid()
        with session.lock:done,reaped,packet=session.done,session.reaped,session.result
        if not done:return history.progress(run_id)
        state=history._current(run_id)
        if state is session.state:
            try:matches=reaped and self._matches(session,packet)
            except (OSError,ValueError,TypeError,KeyError,StopIteration):matches=False
            if history._current(run_id) is not state:state=None
            elif matches:
                state.phase=6;state.counts=dict(state.expected)
                state.prefix.update(revision=state.target,prefix_hash=state.target_hash)
                state.status='HISTORY_VERIFIED_IN_CURRENT_INSTANCE';state.reason=None
            else:
                state.status='HISTORY_AUDIT_FAILED';state.reason='OWNED_HISTORY_AUDIT_REFUSED'
        self._last=dict(active=not reaped,reaped=reaped,status=history.progress(run_id).status,
            snapshot_writes=packet['snapshot'].get('snapshot_write_count') if type(packet) is dict and type(packet.get('snapshot')) is dict else None)
        if not reaped:raise RuntimeError('PAPER_HISTORY_WORKER_NOT_REAPED')
        self._session=None
        return history.progress(run_id)

    def summary(self):
        if threading.get_ident()!=self._thread:_invalid()
        return dict(self._last)  # Diagnostic read remains available after close.

    def close(self):
        if self._closed:return
        self._owner();session=self._session
        if session is not None:
            session.cancel.set();session.thread.join(timeout=8)
            with session.lock:reaped=session.done and session.reaped
            if session.done and not reaped and session.handle is not None:
                try:reaped=terminate_owned(session.handle,deadline_seconds=5).reaped
                except (OSError,RuntimeError,subprocess.SubprocessError):reaped=False
                with session.lock:session.reaped=reaped
            if self.journal._history._states.get(session.run_id) is session.state:
                self.journal._history._states.pop(session.run_id)
            self._last=dict(active=not reaped,reaped=reaped,status='CANCELED' if reaped else 'REAP_REQUIRED',snapshot_writes=None)
            if not reaped:raise RuntimeError('PAPER_HISTORY_WORKER_NOT_REAPED')
        self._session=None;self._closed=True;self.journal._background_history=None


def run_history_audit_child(database,run_id,session_id,expected_implementation_hash):
    from storage.paper_history_audit import audit_paper_history_snapshot
    if (type(session_id) is not str or len(session_id)!=32 or uuid.UUID(hex=session_id).hex!=session_id
            or _revision()!=expected_implementation_hash):_invalid()
    result=audit_paper_history_snapshot(database,run_id)
    if _revision()!=expected_implementation_hash:_invalid()
    return dict(schema_version='r7-owned-paper-history-audit-v0.1',session_id=session_id,
        implementation_hash=expected_implementation_hash,snapshot=result)
