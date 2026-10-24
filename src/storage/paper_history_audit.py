"""Instance-owned complete process-history audit in bounded metadata batches.

Only observed, closed E6 writer scopes may extend progress/readiness. Unknown
own/external writes revoke it. No production caller uses this yet. Independent
resource scheduling and actual entry/healthy gates are separate required work.
No serialized progress object can be accepted as an audit proof.
"""
from contextlib import closing,contextmanager
from dataclasses import dataclass,field
from functools import lru_cache
from pathlib import Path
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
_OWN_WRITES={
    'PREPARE':(1,{'paper_process_operations'}),
    'COMPLETE':(2,{'paper_process_effects','paper_process_checkpoints'}),
    'PUBLISH':(2,{'paper_process_publications','paper_process_published_prefixes'}),
    'GENERATION':(1,{'paper_process_generations'}),
    'PAUSE':(1,{'paper_entry_pause_requests'}),
    'FEEDBACK_QUEUE':(1,{'paper_feedback_publications'}),
    'FEEDBACK_STATUS':(1,{'paper_feedback_publications'}),
    'CANONICAL':(2,{'paper_runtime_objects','paper_runtime_conflicts',
        'paper_position_lifecycle_projections','paper_position_current_projection',
        'paper_position_broker_observations','paper_order_result_observations','paper_order_result_current',
        'paper_funding_evidence','paper_funding_observations','paper_trade_results',
        'paper_position_lifecycle_execution_bindings'}),
}
_CANONICAL_UPDATES={'paper_position_current_projection','paper_order_result_current'}
_NONHISTORY_WRITES={'CANONICAL','FEEDBACK_QUEUE','FEEDBACK_STATUS'}
_READ_ACTIONS={sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION,
    sqlite3.SQLITE_RECURSIVE,sqlite3.SQLITE_TRANSACTION,sqlite3.SQLITE_SAVEPOINT}


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
    bounds:dict
    original_pending:dict
    live_revision:int
    live_generation:int
    live_prefix:int
    phase:int=0
    cursors:dict=field(default_factory=dict)
    counts:dict=field(default_factory=lambda:{name:0 for name in _PHASES})
    generation_clock:str|None=None
    status:str='HISTORY_AUDIT_IN_PROGRESS'
    reason:str|None=None


class PaperHistoryAudit:
    def __init__(self,journal):
        self.journal=journal;self.db=journal._db;self._issuer=object();self._states={};self._write_active=None;self._pinned=None

    @contextmanager
    def _pin_readonly_snapshot(self):
        """Independent readonly child use only; never the live writer connection.

        Keep one source snapshot while bounded audit batches run. Later source
        appends cannot restart this audit. The containing runtime must still
        validate its actual owned child and all intervening writes independently.
        """
        if self.db.in_transaction or self._pinned is not None or self.db.execute('PRAGMA query_only').fetchone()[0]!=1:
            _invalid()
        self.db.execute('BEGIN');self._pinned=object()
        try:yield
        finally:
            self.db.rollback();self._pinned=None;self._states.clear()

    def _epoch(self):
        return (self.db.execute('PRAGMA schema_version').fetchone()[0],
            self.db.execute('PRAGMA temp.schema_version').fetchone()[0],
            self.db.execute('PRAGMA data_version').fetchone()[0],self.db.total_changes)

    def _current(self,run_id):
        _text(run_id);state=self._states.get(run_id)
        if state is not None and (type(state) is not _AuditState or state.issuer is not self._issuer or state.epoch!=self._epoch()):
            self._states.pop(run_id,None);return None
        return state

    def ready(self,run_id):
        state=self._current(run_id)
        return state is not None and state.status=='HISTORY_VERIFIED_IN_CURRENT_INSTANCE'

    @contextmanager
    def owned_write(self,kind,run_id):
        """Observe fixed E6 implementations, never certify arbitrary caller SQL.

        The authorizer records compiled write footprints (including triggers),
        but ALWAYS permits SQLite to apply its original guards/transactions.
        Unknown work revokes permission; it never blocks protective persistence.
        """
        for key in tuple(self._states):self._current(key)
        if self._write_active is not None:
            self._write_active['invalid']=True;self._states.clear()
            yield;return
        if kind not in _OWN_WRITES or not self._states or (kind not in _NONHISTORY_WRITES and not self.journal._prefixes.enabled(run_id)):
            if kind not in _OWN_WRITES or self._states:self._states.clear()
            yield;return
        before=self._epoch();maximum,tables=_OWN_WRITES[kind];observation={'invalid':False}
        self._write_active=observation
        def observe(action,first,second,database,source):
            if source is not None and action in (sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE):
                observation['invalid']=True  # No packaged E6 guard performs DML.
            if action==sqlite3.SQLITE_INSERT:
                if database!='main' or first not in tables:observation['invalid']=True
            elif action==sqlite3.SQLITE_UPDATE and kind=='CANONICAL':
                if database!='main' or first not in _CANONICAL_UPDATES:observation['invalid']=True
            elif action==sqlite3.SQLITE_UPDATE and kind=='FEEDBACK_STATUS':
                if database!='main' or first!='paper_feedback_publications':observation['invalid']=True
            elif action==sqlite3.SQLITE_PRAGMA:
                if second is not None:observation['invalid']=True
            elif action not in _READ_ACTIONS:observation['invalid']=True
            return sqlite3.SQLITE_OK
        try:
            self.db.set_authorizer(observe)
            yield
            after=self._epoch()
            if (observation['invalid'] or self.db.in_transaction or after[:-1]!=before[:-1]
                    or not 0<=after[-1]-before[-1]<=maximum):
                self._states.clear();return
            self.journal._advance_checkpoint_cache(before,after)
            current=context=None
            if kind not in _NONHISTORY_WRITES:
                current=self.journal.recover_current(run_id)
                context=self.journal._prefixes.current_context(run_id)
            if self._epoch()!=after:self._states.clear();return
            for state in self._states.values():
                state.epoch=after
                if current is not None and state.run_id==run_id:
                    state.live_revision=current.revision;state.live_generation=current.process_generation
                    state.live_prefix=context['revision']
        except BaseException:
            self._states.clear();raise
        finally:
            self.db.set_authorizer(None);self._write_active=None

    def progress(self,run_id,*,rows=0):
        state=self._current(run_id)
        if state is None:
            return HistoryAuditProgress('HISTORY_AUDIT_REQUIRED','NOT_STARTED',0,rows,None,0,'INSTANCE_HISTORY_AUDIT_REQUIRED')
        phase='COMPLETE' if state.phase==len(_PHASES) else _PHASES[state.phase]
        return HistoryAuditProgress(state.status,phase,sum(state.counts.values()),rows,state.target,
            state.live_prefix if state.phase==len(_PHASES) else state.prefix['revision'],state.reason)

    def _begin(self,run_id,epoch):
        if self.db.execute("""SELECT 1 FROM sqlite_temp_master WHERE type IN ('table','view') AND
                (lower(name) GLOB 'paper_process_*' OR lower(name) IN ('paper_entry_pause_requests','schema_migrations')) LIMIT 1""").fetchone():_invalid()
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
        # Freeze original inventories, including orphan/negative/empty keys.
        # Later verified appends cannot extend a scan or insert a publication ID
        # behind its lexical cursor. No retained row or proof is rewritten.
        bounds={}
        for phase,(table,columns,order) in _QUERIES.items():
            top=self.db.execute('SELECT '+order+' FROM '+table+' WHERE run_id=? ORDER BY '+
                ','.join(key+' DESC' for key in order.split(','))+' LIMIT 1',(run_id,)).fetchone()
            rowid=self.db.execute('SELECT max(rowid) FROM '+table).fetchone()[0]
            bounds[phase]=(None if top is None else tuple(top),rowid)
        original={key:self.journal.operation(run_id,key) for key in current.pending_operations}
        return _AuditState(self._issuer,epoch,run_id,target,context['prefix_hash'],current.revision,
            current.process_generation,_clock(run['created_at']),root,expected,bounds,original,
            current.revision,current.process_generation,target)

    def _query(self,state,limit):
        phase=_PHASES[state.phase];table,columns,order=_QUERIES[phase]
        upper,rowid=state.bounds[phase]
        if upper is None:return []
        fields=order.split(',');key='('+order+')' if len(fields)==2 else order
        markers='(?,?)' if len(fields)==2 else '?'
        cursor=state.cursors.get(phase);arguments=[state.run_id,rowid,*upper]
        condition=' AND rowid<=? AND '+key+'<='+markers
        if cursor is not None:
            if len(fields)==2:
                condition+=' AND ('+order+')>(?,?)';arguments.extend(cursor)
            else:condition+=' AND '+order+'>?';arguments.append(cursor)
        arguments.append(limit)
        # Names come only from the closed module-owned phase table above.
        return self.db.execute('SELECT '+columns+' FROM '+table+' WHERE run_id=?'+condition+
            ' ORDER BY '+order+' LIMIT ?',arguments).fetchall()

    def _original_operation(self,state,operation_id):
        current=self.journal.operation(state.run_id,operation_id)
        original=state.original_pending.get(operation_id)
        if original is None:return current
        if (current is None or current.base_revision!=original.base_revision
                or current.request_json!=original.request_json or current.base_state_json!=original.base_state_json):_invalid()
        if original.status=='APPLIED' and (current.state_json!=original.state_json
                or current.outcome_json!=original.outcome_json or current.effect_hash!=original.effect_hash):_invalid()
        return original

    def _verified_operation_refs(self,state,operation_id):
        """Inventory links AFTER every original operation's bytes were checked.

        The exact source snapshot/qualified immutable epoch is still mandatory.
        Unknown writes discard this state before another phase may use it. This
        independently checks orphan inventories without decoding old bytes again.
        """
        if state.phase==0 or state.counts['OPERATIONS']!=state.expected['OPERATIONS']:_invalid()
        row=self.db.execute('''SELECT o.base_revision,e.checkpoint_revision,e.effect_hash,
            p.effect_hash AS published_hash FROM paper_process_operations o
            LEFT JOIN paper_process_effects e USING(run_id,operation_id)
            LEFT JOIN paper_process_publications p USING(run_id,operation_id)
            WHERE o.run_id=? AND o.operation_id=?''',(state.run_id,operation_id)).fetchone()
        if row is None:_invalid()
        if row['published_hash'] is not None and row['published_hash']!=row['effect_hash']:_invalid()
        original=state.original_pending.get(operation_id)
        if original is not None:
            if (row['base_revision']!=original.base_revision or original.status=='APPLIED' and
                    (row['checkpoint_revision']!=original.checkpoint_revision or row['effect_hash']!=original.effect_hash)):_invalid()
            return dict(status=original.status,base_revision=original.base_revision,
                checkpoint_revision=original.checkpoint_revision,effect_hash=original.effect_hash)
        return dict(status='PREPARED' if row['checkpoint_revision'] is None else
            'APPLIED' if row['published_hash'] is None else 'PUBLISHED',base_revision=row['base_revision'],
            checkpoint_revision=row['checkpoint_revision'],effect_hash=row['effect_hash'])

    def _check(self,state,row):
        phase=_PHASES[state.phase];before=state.counts[phase]
        if phase=='PUBLICATIONS':
            operation_id=_text(row['operation_id']);operation=self._verified_operation_refs(state,operation_id)
            if (operation['status']!='PUBLISHED' or operation['effect_hash']!=row['effect_hash']
                    or type(operation['checkpoint_revision']) is not int
                    or not 1<=operation['checkpoint_revision']<=state.target):_invalid()
            state.cursors[phase]=operation_id
        else:
            sequence=row['sequence']
            if type(sequence) is not int or sequence<0:_invalid()
            if phase in ('OPERATIONS','EFFECTS'):
                operation_id=_text(row['operation_id'])
                if phase=='OPERATIONS':
                    if sequence!=before:_invalid()
                    operation=self._original_operation(state,operation_id)
                    if operation is None:_invalid()
                    self.journal._prefixes.audit_operation(state.prefix,operation)
                else:
                    operation=self._verified_operation_refs(state,operation_id)
                    if (sequence!=before+1 or operation['status'] not in ('APPLIED','PUBLISHED')
                            or operation['checkpoint_revision']!=sequence or operation['base_revision']!=sequence-1):_invalid()
                state.cursors[phase]=(sequence,operation_id)
            elif phase=='CHECKPOINTS':
                if sequence!=before:_invalid()
                if sequence==0:
                    if row['operation_id'] is not None:_invalid()
                else:
                    operation=self._verified_operation_refs(state,_text(row['operation_id']))
                    if operation['checkpoint_revision']!=sequence or operation['base_revision']!=sequence-1:_invalid()
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
        if self.db.in_transaction and self._pinned is None:raise RuntimeValidationError('PAPER_HISTORY_AUDIT_IDLE_OWNER_REQUIRED','History audit needs an idle read owner')
        if self._pinned is not None and not self.db.in_transaction:_invalid()
        state=self._current(run_id);epoch=self._epoch();rows=0
        if state is not None:
            if state.status=='HISTORY_VERIFIED_IN_CURRENT_INSTANCE':return self.progress(run_id)
            if state.status=='HISTORY_AUDIT_FAILED':_invalid()
        if self._pinned is None:self.db.execute('BEGIN')
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
        finally:
            if self._pinned is None:self.db.rollback()
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
            if current.revision!=state.live_revision or current.process_generation!=state.live_generation:_invalid()
            state.status='HISTORY_VERIFIED_IN_CURRENT_INSTANCE';state.reason=None
        return self.progress(run_id,rows=rows)


def audit_paper_history_snapshot(path,run_id,*,maximum_rows=32,on_progress=None):
    """Actual fixed readonly source diagnostic. This result is NOT a proof input.

    No migration, broker producer, network, new active database or durable audit
    flag. The future owned-process receiver must bind the real child and source
    epoch before any private runtime eligibility can be extended from its work.
    """
    from .paper_process import PaperProcessJournal,_digest,_state
    from application.platform.resources import require_local_database_volume
    target=Path(path)
    if not target.is_absolute() or '..' in target.parts or not target.is_file():_invalid()
    if on_progress is not None and not callable(on_progress):_invalid()
    require_local_database_volume(target)
    source=target.stat();file_key=(source.st_dev,source.st_ino)
    with closing(sqlite3.connect(target.as_uri()+'?mode=ro',uri=True,isolation_level=None)) as db:
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA query_only=ON');db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA busy_timeout=5000')
        journal=PaperProcessJournal(db);history=journal._history
        with history._pin_readonly_snapshot():
            while True:
                progress=history.step(run_id,maximum_rows=maximum_rows)
                if on_progress is not None:on_progress(progress)
                if history.ready(run_id):break
            original=history._current(run_id);current=journal.recover_current(run_id)
            epoch=history._epoch()
            result=dict(scope='DIAGNOSTIC_SNAPSHOT_NOT_RUNTIME_AUTHORITY',run_id=run_id,
                verified_prefix_revision=original.target,verified_prefix_hash=original.target_hash,
                current_revision=current.revision,process_generation=current.process_generation,
                binding_hash=_digest(current.binding_json),current_state_hash=_digest(current.state_json),
                inventories=dict(original.counts),source_file_key=file_key,source_schema_version=epoch[0],
                snapshot_write_count=db.total_changes)
        # E4 domain validation occurs after releasing the snapshot, never inside
        # its SQLite transaction. It validates the actual captured state bytes.
        _state(current.state)
        result['source_changed_during_snapshot']=history._epoch()!=epoch
    after=target.stat()
    if (after.st_dev,after.st_ino)!=file_key:_invalid()
    return result
