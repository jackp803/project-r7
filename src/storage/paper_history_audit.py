"""Instance-owned complete process-history audit in bounded metadata batches.

Conservative component: ANY observed DB change invalidates progress/readiness.
No production caller uses this yet. Qualified own-write tracking, independent
resource scheduling and actual entry/healthy gates are separate required work.
No serialized progress object can be accepted as an audit proof.
"""
from contextlib import closing
from dataclasses import dataclass,field
from functools import lru_cache
import sqlite3

from ._sqlite_registry import _apply_migrations,check_migration_compatibility
from .paper_process_prefix import _clock
from .runtime_models import RuntimePersistenceError,RuntimeValidationError
from registry import EvidenceGateError

_PHASES=('OPERATIONS','EFFECTS','CHECKPOINTS','PUBLICATIONS','PREFIXES','GENERATIONS')
_QUERIES={
    'OPERATIONS':('paper_process_operations','base_revision AS sequence,operation_id','base_revision,operation_id'),
    'EFFECTS':('paper_process_effects','checkpoint_revision AS sequence,operation_id','checkpoint_revision,operation_id'),
    'CHECKPOINTS':('paper_process_checkpoints','revision AS sequence,operation_id','revision'),
    'PUBLICATIONS':('paper_process_publications','operation_id,effect_hash','operation_id'),
    'PREFIXES':('paper_process_published_prefixes','revision AS sequence,prefix_hash','revision'),
    'GENERATIONS':('paper_process_generations','generation AS sequence,instance_id,started_at','generation'),
}


def _invalid():raise RuntimeValidationError('PAPER_HISTORY_AUDIT_INVALID','Paper history audit refused inconsistent source facts')


def _text(value):
    if type(value) is not str or not value.strip() or len(value)>256 or '\x00' in value:_invalid()
    return value


def _schema(db):
    rows=db.execute('''SELECT type,name,tbl_name,
        CASE WHEN length(CAST(sql AS BLOB))<=262144 THEN sql ELSE NULL END
        FROM sqlite_master WHERE tbl_name GLOB 'paper_process_*' OR tbl_name='paper_entry_pause_requests'
        ORDER BY type,name''').fetchmany(257)
    if len(rows)>256:_invalid()
    return tuple(tuple(row) for row in rows)


@lru_cache(maxsize=1)
def _expected_schema():
    # Only a disposable in-memory packaged model; never migrate the audited DB.
    with closing(sqlite3.connect(':memory:')) as db:
        db.row_factory=sqlite3.Row;_apply_migrations(db)
        return _schema(db)


@dataclass(frozen=True)
class HistoryAuditProgress:
    status:str
    phase:str
    verified_rows:int
    rows_in_step:int
    target_prefix_revision:int|None
    verified_prefix_revision:int
    reason_code:str|None
    scope:str=field(default='CORE_PROCESS_AND_PREFIX_HISTORY',init=False)


@dataclass
class _AuditState:
    issuer:object
    epoch:tuple
    run_id:str
    target:int
    target_hash:str
    current_revision:int
    generation:int
    run_created_at:str
    prefix:dict
    expected:dict
    phase:int=0
    cursors:dict=field(default_factory=dict)
    counts:dict=field(default_factory=lambda:{name:0 for name in _PHASES})
    generation_clock:str|None=None
    status:str='HISTORY_AUDIT_IN_PROGRESS'
    reason:str|None=None


class PaperHistoryAudit:
    def __init__(self,journal):
        self.journal=journal;self.db=journal._db;self._issuer=object();self._states={}

    def _epoch(self):
        return (self.db.execute('PRAGMA schema_version').fetchone()[0],
            self.db.execute('PRAGMA data_version').fetchone()[0],self.db.total_changes)

    def _current(self,run_id):
        _text(run_id);state=self._states.get(run_id)
        if state is not None and (type(state) is not _AuditState or state.issuer is not self._issuer or state.epoch!=self._epoch()):
            self._states.pop(run_id,None);return None
        return state

    def ready(self,run_id):
        state=self._current(run_id)
        return state is not None and state.status=='HISTORY_VERIFIED_IN_CURRENT_INSTANCE'

    def progress(self,run_id,*,rows=0):
        state=self._current(run_id)
        if state is None:
            return HistoryAuditProgress('HISTORY_AUDIT_REQUIRED','NOT_STARTED',0,rows,None,0,'INSTANCE_HISTORY_AUDIT_REQUIRED')
        phase='COMPLETE' if state.phase==len(_PHASES) else _PHASES[state.phase]
        return HistoryAuditProgress(state.status,phase,sum(state.counts.values()),rows,state.target,
            state.prefix['revision'],state.reason)

    def _begin(self,run_id,epoch):
        try:migrations=check_migration_compatibility(self.db)
        except EvidenceGateError:_invalid()
        if migrations['pending']:_invalid()
        if _schema(self.db)!=_expected_schema():_invalid()
        current=self.journal.recover_current(run_id)
        context=self.journal._prefixes.current_context(run_id)
        if context is None:_invalid()
        root=self.journal._prefixes.audit_start(run_id)
        run=self.journal._run(run_id)
        applied=int(bool(current.pending_operations) and current.status=='PUBLICATION_PENDING')
        target=context['revision'];pending=len(current.pending_operations)
        expected=dict(OPERATIONS=target+pending,EFFECTS=target+applied,CHECKPOINTS=target+applied+1,
            PUBLICATIONS=target,PREFIXES=target+1,GENERATIONS=current.process_generation)
        return _AuditState(self._issuer,epoch,run_id,target,context['prefix_hash'],current.revision,
            current.process_generation,_clock(run['created_at']),root,expected)

    def _query(self,state,limit):
        phase=_PHASES[state.phase];table,columns,order=_QUERIES[phase]
        cursor=state.cursors.get(phase);arguments=[state.run_id];condition=''
        if cursor is not None:
            fields=order.split(',')
            if len(fields)==2:
                condition=' AND ('+order+')>(?,?)';arguments.extend(cursor)
            else:condition=' AND '+order+'>?';arguments.append(cursor)
        arguments.append(limit)
        # Names come only from the closed module-owned phase table above.
        return self.db.execute('SELECT '+columns+' FROM '+table+' WHERE run_id=?'+condition+
            ' ORDER BY '+order+' LIMIT ?',arguments).fetchall()

    def _check(self,state,row):
        phase=_PHASES[state.phase];before=state.counts[phase]
        if phase=='PUBLICATIONS':
            operation_id=_text(row['operation_id']);operation=self.journal.operation(state.run_id,operation_id)
            if (operation is None or operation.status!='PUBLISHED' or operation.effect_hash!=row['effect_hash']
                    or not 1<=operation.checkpoint_revision<=state.target):_invalid()
            state.cursors[phase]=operation_id
        else:
            sequence=row['sequence']
            if type(sequence) is not int or sequence<0:_invalid()
            if phase in ('OPERATIONS','EFFECTS'):
                operation_id=_text(row['operation_id']);operation=self.journal.operation(state.run_id,operation_id)
                if operation is None:_invalid()
                if phase=='OPERATIONS':
                    if sequence!=before:_invalid()
                    self.journal._prefixes.audit_operation(state.prefix,operation)
                elif (sequence!=before+1 or operation.status not in ('APPLIED','PUBLISHED')
                        or operation.checkpoint_revision!=sequence):_invalid()
                state.cursors[phase]=(sequence,operation_id)
            elif phase=='CHECKPOINTS':
                if sequence!=before:_invalid()
                checkpoint=self.journal._checkpoint(state.run_id,sequence)
                if sequence==0:
                    if row['operation_id'] is not None:_invalid()
                else:
                    operation=self.journal.operation(state.run_id,_text(row['operation_id']))
                    if operation is None or operation.checkpoint_revision!=sequence or operation.state_json!=checkpoint['state_json']:_invalid()
                state.cursors[phase]=sequence
            elif phase=='PREFIXES':
                if sequence!=before or sequence>state.target:_invalid()
                if sequence==state.target and row['prefix_hash']!=state.target_hash:_invalid()
                state.cursors[phase]=sequence
            elif phase=='GENERATIONS':
                if sequence!=before+1:_invalid()
                _text(row['instance_id']);at=_clock(row['started_at'])
                if at<(state.generation_clock or state.run_created_at):_invalid()
                state.generation_clock=at;state.cursors[phase]=sequence
        state.counts[phase]+=1

    def _finish_phase(self,state):
        phase=_PHASES[state.phase]
        if state.counts[phase]!=state.expected[phase]:_invalid()
        if phase=='OPERATIONS' and (state.prefix['revision']!=state.target or state.prefix['prefix_hash']!=state.target_hash):_invalid()
        state.phase+=1

    def step(self,run_id,*,maximum_rows):
        _text(run_id)
        if type(maximum_rows) is not int or not 1<=maximum_rows<=128:_invalid()
        if self.db.in_transaction:raise RuntimeValidationError('PAPER_HISTORY_AUDIT_IDLE_OWNER_REQUIRED','History audit needs an idle read owner')
        state=self._current(run_id);epoch=self._epoch();rows=0
        if state is not None:
            if state.status=='HISTORY_VERIFIED_IN_CURRENT_INSTANCE':return self.progress(run_id)
            if state.status=='HISTORY_AUDIT_FAILED':_invalid()
        self.db.execute('BEGIN')
        try:
            if state is None:
                state=self._begin(run_id,epoch);self._states[run_id]=state
            while rows<maximum_rows and state.phase<len(_PHASES):
                remaining=maximum_rows-rows;found=self._query(state,remaining)
                for row in found:self._check(state,row);rows+=1
                if len(found)<remaining:self._finish_phase(state)
        except (RuntimePersistenceError,sqlite3.Error,ValueError,TypeError,KeyError,IndexError):
            if state is not None:
                state.status='HISTORY_AUDIT_FAILED';state.reason='CORE_PROCESS_HISTORY_INVALID'
            raise RuntimeValidationError('PAPER_HISTORY_AUDIT_INVALID','Core process history audit refused') from None
        finally:self.db.rollback()
        if self._epoch()!=epoch:
            self._states.pop(run_id,None);return self.progress(run_id,rows=rows)
        if state.phase==len(_PHASES):
            # E4 broker validation happens in recover_current AFTER its own read
            # snapshot is released, never inside this audit's read transaction.
            try:current=self.journal.recover_current(run_id)
            except RuntimePersistenceError:
                state.status='HISTORY_AUDIT_FAILED';state.reason='CURRENT_MANAGEMENT_FACTS_INVALID';raise
            if self._epoch()!=epoch:
                self._states.pop(run_id,None);return self.progress(run_id,rows=rows)
            if current.revision!=state.current_revision or current.process_generation!=state.generation:_invalid()
            state.status='HISTORY_VERIFIED_IN_CURRENT_INSTANCE';state.reason=None
        return self.progress(run_id,rows=rows)
