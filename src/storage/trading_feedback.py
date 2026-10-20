"""Protected historical E6/dispatch reads; no trading or writer capability.

Current process generations are private coherence fences, never the original
financial-result producer or permission. Existing E6 recovery validates the
canonical reference graph. Read budgets deny oversized history rather than
truncating financial evidence or returning invented zero performance.
"""
from contextlib import ExitStack,contextmanager,closing
from dataclasses import dataclass,fields
from functools import lru_cache
import json
from pathlib import Path
import sqlite3
import time

from application.platform.supervision import _local_path
from application.platform.private_files import _filesystem_path
import stat
from brokers.okx_product_state import restore_product_readback
from ._paper_runtime import _PaperRuntimeStore
from ._runtime_validation import canonical_payload
from .product_dispatch import _read
from .qualification import _readonly_uri,_NAMESPACE_SQL
from .runtime import PaperRuntimeJournal
from .runtime_models import PaperRuntimeRecovery,StoredCanonicalObject,RuntimePersistenceError


class TradingFeedbackReadError(ValueError):
    def __init__(self,code='TRADING_HISTORY_UNAVAILABLE'):
        self.code=code;super().__init__(code)


@dataclass(frozen=True)
class TradingFeedbackSnapshot:
    namespace:str
    execution:str
    observed_process_generation:int
    original_binding_json:str
    canonical:PaperRuntimeRecovery

    @property
    def available(self):
        return (self.canonical.status=='READY' and self.canonical.trade_result is not None
            and self.canonical.current_position_projection is not None
            and self.canonical.current_position_projection.payload['lifecycle_state']=='CLOSED')


def _identity(path):
    _local_path(path);identity=None
    for candidate in (path,Path(str(path)+'-wal'),Path(str(path)+'-shm')):
        try:info=_filesystem_path(candidate).lstat()
        except FileNotFoundError:
            if candidate==path:raise
            continue
        _local_path(candidate)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1:raise TradingFeedbackReadError()
        if candidate==path:identity=(info.st_dev,info.st_ino)
    return identity


def _schema(db,kind):
    expression=("tbl_name GLOB 'product_dispatch_*'" if kind=='dispatch' else
        "tbl_name GLOB 'paper_runtime_*' OR tbl_name GLOB 'paper_position_*' OR tbl_name GLOB 'paper_order_*' "
        "OR tbl_name IN ('paper_funding_evidence','paper_trade_results','registry_research_namespace','strategy_versions')")
    rows=db.execute('SELECT type,name,tbl_name,sql FROM sqlite_master WHERE '+expression+' ORDER BY type,name').fetchmany(513)
    if len(rows)>512:raise TradingFeedbackReadError()
    return tuple(tuple(row) for row in rows)


@lru_cache(maxsize=1)
def _expected():
    # Model creation is in memory only, never in a historical data store.
    from ._sqlite_registry import _apply_migrations
    with closing(sqlite3.connect(':memory:')) as model:
        model.row_factory=sqlite3.Row;_apply_migrations(model)
        for statement in _NAMESPACE_SQL:model.execute(statement)
        return {kind:_schema(model,kind) for kind in ('canonical','dispatch')}


def _text(value):
    if not isinstance(value,str) or not 1<=len(value)<=256 or any(c in value for c in '\x00\r\n'):
        raise TradingFeedbackReadError()
    return value


def _require_subject_store(db,kind,namespace):
    table='registry_research_namespace' if kind=='canonical' else 'product_dispatch_namespace'
    if (_schema(db,kind)!=_expected()[kind] or
            [tuple(row) for row in db.execute('SELECT singleton,namespace FROM '+table+' LIMIT 2')]!=[(1,namespace)]):
        raise TradingFeedbackReadError()


def _dispatch_document(raw,commitment):
    if not isinstance(raw,str) or not isinstance(commitment,str) or len(commitment)!=71:
        raise TradingFeedbackReadError()
    return _read(raw,commitment)


class _TradingFeedbackReader:
    def __init__(self,canonical,dispatch,namespace,identities,budget,deadline):
        self._canonical,self._dispatch=canonical,dispatch
        self.namespace=namespace;self._identities=identities
        self._budget,self._deadline=budget,deadline

    def snapshot(self,run_id,trade_plan_id):
        _text(run_id);_text(trade_plan_id)
        connections=tuple(dict.fromkeys((self._canonical,self._dispatch)))
        self._budget[:]=[0,0];self._deadline[0]=time.monotonic()+5
        try:
            versions=[db.execute('PRAGMA data_version').fetchone()[0] for db in connections]
            for db in connections:db.execute('BEGIN')
            _require_subject_store(self._canonical,'canonical',self.namespace)
            _require_subject_store(self._dispatch,'dispatch',self.namespace)
            row=self._dispatch.execute('SELECT binding_json,binding_hash FROM product_dispatch_runs WHERE run_id=?',(run_id,)).fetchone()
            if row is None:raise TradingFeedbackReadError()
            binding=_dispatch_document(row['binding_json'],row['binding_hash'])
            execution='SIMULATED_MECHANICS' if self.namespace=='FIXTURE' else 'ACTUAL_OWNER'
            if (binding['namespace']!=self.namespace or binding['execution']!=execution
                    or binding['release']['namespace']!=self.namespace):raise TradingFeedbackReadError()
            # Constructors below attach no owner and perform no I/O. Only
            # existing E6 recovery methods receive our query_only RO connection.
            graph=PaperRuntimeJournal(_PaperRuntimeStore(self._canonical)).recover(trade_plan_id=trade_plan_id)
            plan=graph.approved_trade_plan
            if plan is None or graph.trade_plan_id!=trade_plan_id:raise TradingFeedbackReadError()
            if binding['identity']!={key:plan.payload[key] for key in ('strategy_id','strategy_version')}:raise TradingFeedbackReadError()
            # Canonical ApprovedTradePlan carries strategy ID/version, not a
            # content_hash field. Bind the immutable original E6 version row;
            # never invent a plan field or require current trading permission.
            strategy=self._canonical.execute('SELECT content_hash,definition_json FROM strategy_versions WHERE strategy_id=? AND strategy_version=?',
                (plan.payload['strategy_id'],plan.payload['strategy_version'])).fetchone()
            from strategy import compute_content_hash
            if strategy is None or not isinstance(strategy['definition_json'],str):raise TradingFeedbackReadError()
            definition=json.loads(strategy['definition_json'])
            if (not isinstance(definition,dict) or strategy['content_hash']!=binding['strategy_content_hash']
                    or compute_content_hash(definition)!=strategy['content_hash']):raise TradingFeedbackReadError()
            claims=self._dispatch.execute('SELECT i.operation_id,i.request_json,i.request_hash FROM product_dispatch_intents i '
                'JOIN product_dispatch_claims c ON c.run_id=i.run_id AND c.operation_id=i.operation_id '
                'WHERE i.run_id=? ORDER BY i.operation_id',(run_id,)).fetchall()
            matched={};entries=0
            for claim in claims:
                request=_dispatch_document(claim['request_json'],claim['request_hash'])
                prepared=restore_product_readback(request)
                if prepared.canonical_request.trade_plan_id!=trade_plan_id:continue
                if claim['operation_id']!=prepared.canonical_request.order_request_id:raise TradingFeedbackReadError()
                from brokers.okx_close_sizing import canonical_okx_close_sizing_hash
                if prepared.source_plan_hash!=canonical_okx_close_sizing_hash(plan.payload):raise TradingFeedbackReadError()
                matched[claim['operation_id']]=request
                if request['role']=='ENTRY':
                    entries+=1
            if entries!=1:raise TradingFeedbackReadError()
            for request in graph.order_requests:
                if (request.canonical_id not in matched
                        or request.payload!=matched[request.canonical_id]['canonical_request']):raise TradingFeedbackReadError()
            # Recovery retains immutable serialized objects. Recheck bytes for
            # every returned fact; do not implement a second financial engine.
            for field in fields(graph):
                value=getattr(graph,field.name)
                values=value if isinstance(value,tuple) else (value,)
                for item in values:
                    if isinstance(item,StoredCanonicalObject):
                        unused,raw,commitment=canonical_payload(item.payload)
                        if raw!=item.payload_json or commitment!=item.payload_hash:raise TradingFeedbackReadError()
            generation=self._dispatch.execute('SELECT coalesce(max(generation),0) FROM product_dispatch_generations WHERE run_id=?',(run_id,)).fetchone()[0]
            if type(generation) is not int or generation<1:raise TradingFeedbackReadError()
            result=TradingFeedbackSnapshot(self.namespace,execution,generation,row['binding_json'],graph)
            for db in connections:db.rollback()
            if versions!=[db.execute('PRAGMA data_version').fetchone()[0] for db in connections]:
                raise TradingFeedbackReadError('TRADING_HISTORY_SNAPSHOT_CHANGED')
            if time.monotonic()>=self._deadline[0] or any(_identity(path)!=identity for path,identity in self._identities.items()):
                raise TradingFeedbackReadError()
            return result
        except TradingFeedbackReadError:raise
        except (sqlite3.Error,OSError,ValueError,TypeError,KeyError,IndexError,RecursionError,RuntimePersistenceError):
            raise TradingFeedbackReadError() from None
        finally:
            for db in connections:db.rollback()


@contextmanager
def open_trading_feedback_reader(canonical_path,dispatch_path,*,namespace):
    if namespace not in ('FIXTURE','LOCAL_RESEARCH'):raise TradingFeedbackReadError()
    paths=tuple(dict.fromkeys((Path(canonical_path).absolute(),Path(dispatch_path).absolute())))
    with ExitStack() as stack:
        try:
            identities={path:_identity(path) for path in paths};_expected()
            budget=[0,0];deadline=[time.monotonic()+2]
            def row_factory(cursor,values):
                budget[0]+=1
                budget[1]+=sum(len(value.encode('utf-8')) if isinstance(value,str) else len(value) if isinstance(value,bytes) else 8 for value in values)
                if budget[0]>10000 or budget[1]>16*1024*1024:raise TradingFeedbackReadError('TRADING_HISTORY_READ_BUDGET_EXCEEDED')
                return sqlite3.Row(cursor,values)
            stores={}
            for path in paths:
                db=stack.enter_context(closing(sqlite3.connect(_readonly_uri(path),uri=True,timeout=1)))
                db.row_factory=row_factory;db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,2*1024*1024)
                db.set_progress_handler(lambda:int(time.monotonic()>=deadline[0]),1000)
                db.execute('PRAGMA query_only=ON');db.execute('PRAGMA trusted_schema=OFF')
                db.execute('PRAGMA busy_timeout=1000');db.execute('PRAGMA temp_store=MEMORY')
                stores[path]=db
            canonical=stores[Path(canonical_path).absolute()];dispatch=stores[Path(dispatch_path).absolute()]
            for db,kind,table in ((canonical,'canonical','registry_research_namespace'),(dispatch,'dispatch','product_dispatch_namespace')):
                db.execute('BEGIN')
                try:
                    _require_subject_store(db,kind,namespace)
                finally:db.rollback()
            if any(_identity(path)!=identity for path,identity in identities.items()):raise TradingFeedbackReadError()
            yield _TradingFeedbackReader(canonical,dispatch,namespace,identities,budget,deadline)
        except TradingFeedbackReadError:raise
        except (sqlite3.Error,OSError,ValueError,TypeError,KeyError,IndexError,RecursionError,RuntimePersistenceError):
            raise TradingFeedbackReadError() from None
