"""Bounded RO projections of original owner-produced report deliveries.

No owner attachment, report generation, migration on disk, or transport effects.
An ACK is historical byte-readback evidence, never current cloud connectivity.
"""
from contextlib import closing, contextmanager
from datetime import datetime
from functools import lru_cache
import json
from pathlib import Path
import sqlite3
import time

from application.datasets.catalog import digest
from application.research.evidence import ResearchEvidenceConflict, checked_feedback_record, stamp
from application.research.queue import ResearchQueue
from storage.paper_feedback import checked_paper_feedback_record
from storage.paper_process import _binding, _read_json
from storage.runtime_models import RuntimePersistenceError
from storage.qualification import _readonly_uri


class PublicationHistoryError(ValueError):
    def __init__(self, code='REPORT_PUBLICATION_HISTORY_UNAVAILABLE'):
        self.code=code
        super().__init__(code)


_TABLES={
    'queue':('research_queue_namespace','research_queue_jobs','research_queue_commands','research_queue_events'),
    'research':('research_runs','research_attempts','research_feedback_publications'),
    'paper':('paper_process_runs','paper_process_checkpoints','paper_process_generations','paper_feedback_publications'),
}
_STATES={'PENDING','LOCAL_STAGED','CLOUD_ACKNOWLEDGED','UNAVAILABLE','CONFLICT'}
_ERRORS=(sqlite3.Error,OSError,ValueError,TypeError,KeyError,IndexError,RecursionError,
         ResearchEvidenceConflict,RuntimePersistenceError)


def _schema(db,kind):
    tables=_TABLES[kind]
    rows=db.execute('SELECT type,name,tbl_name,sql FROM sqlite_master WHERE tbl_name IN ('+
        ','.join('?' for unused in tables)+') ORDER BY type,name',tables).fetchmany(129)
    if len(rows)>128:raise PublicationHistoryError()
    return tuple(tuple(row) for row in rows)


@lru_cache(maxsize=3)
def _expected(kind):
    with closing(sqlite3.connect(':memory:')) as db:
        db.row_factory=sqlite3.Row
        if kind=='paper':
            from storage._sqlite_registry import _apply_migrations
            _apply_migrations(db)
        else:
            names=('0005_research_queue.sql',) if kind=='queue' else ('0002_research_attempts.sql','0007_research_feedback_outbox.sql')
            for name in names:
                db.executescript((Path(__file__).parents[1]/'migrations'/name).read_text(encoding='utf-8'))
        return _schema(db,kind)


@contextmanager
def _snapshot(path,kind,end):
    identity=ResearchQueue._alert_file_identity(path)
    expected=_expected(kind)
    with closing(sqlite3.connect(_readonly_uri(path),uri=True,timeout=1)) as db:
        db.row_factory=sqlite3.Row
        # A Paper checkpoint can contain the bounded broker state, not only a
        # small report. Per-report/input limits are checked before retrieval.
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH,32*1024*1024 if kind=='paper' else 2*1024*1024)
        db.set_progress_handler(lambda:int(time.monotonic()>=end),1000)
        db.execute('PRAGMA query_only=ON');db.execute('PRAGMA trusted_schema=OFF')
        db.execute('PRAGMA busy_timeout=1000');db.execute('PRAGMA temp_store=MEMORY');db.execute('BEGIN')
        if _schema(db,kind)!=expected:raise PublicationHistoryError()
        yield db
        if time.monotonic()>=end or ResearchQueue._alert_file_identity(path)!=identity:
            raise PublicationHistoryError()


def _page_args(subject,limit,offset):
    if type(limit) is not int or not 1<=limit<=100 or type(offset) is not int or not 0<=offset<=100000:
        raise PublicationHistoryError('INVALID_PAGE')
    if not isinstance(subject,str) or not subject or len(subject)>256 or '\x00' in subject:
        raise PublicationHistoryError()


def _page(items,total,limit,offset,*,status='AVAILABLE',reasons=()):
    return dict(items=items,total=total,limit=limit,offset=offset,status=status,reason_codes=list(reasons))


def _bounded_row(db,table,where,parameters,columns):
    # Length predicates do not transfer an oversized input/payload to Python.
    condition=' AND '.join("typeof("+name+")='text' AND length(CAST("+name+' AS BLOB))<=?' for name in columns)
    row=db.execute('SELECT * FROM '+table+' WHERE '+where+' AND '+condition,
        (*parameters,*columns.values())).fetchone()
    if row is None:raise PublicationHistoryError()
    return row


def _metadata(row,*,paper=False):
    if row['state'] not in _STATES or type(row['attempts']) is not int or not 0<=row['attempts']<2**63:
        raise PublicationHistoryError()
    if stamp(datetime.fromisoformat(row['created_at'].replace('Z','+00:00')))!=row['created_at']:
        raise PublicationHistoryError()
    keys=('operation_id','run_id','state','feedback_hash','artifact_hash','attempts')
    if paper:keys+=('run_revision','process_generation')
    return dict({key:row[key] for key in keys},queued_at=row['created_at'])


def _rows(db,table,run_id,limit,offset):
    metadata={'operation_id':128,'run_id':256,'state':32,'feedback_hash':71,'artifact_hash':71,'created_at':32}
    if table=='paper_feedback_publications':metadata.update(binding_hash=71,checkpoint_state_hash=71)
    invalid=' OR '.join("typeof("+name+")!='text' OR length(CAST("+name+' AS BLOB))>'+str(bound) for name,bound in metadata.items())
    integer_keys=('attempts','run_revision','process_generation') if table=='paper_feedback_publications' else ('attempts',)
    invalid+=' OR '+' OR '.join("typeof("+key+")!='integer' OR "+key+'<0' for key in integer_keys)
    if db.execute('SELECT 1 FROM '+table+' WHERE run_id=? AND ('+invalid+') LIMIT 1',(run_id,)).fetchone():
        raise PublicationHistoryError()
    total=db.execute('SELECT COUNT(*) FROM '+table+' WHERE run_id=?',(run_id,)).fetchone()[0]
    # Project bounded identities first; fetch/validate only this requested page.
    identities=db.execute('SELECT operation_id FROM '+table+' WHERE run_id=? ORDER BY created_at,operation_id LIMIT ? OFFSET ?',
        (run_id,limit,offset)).fetchall()
    rows=(_bounded_row(db,table,'run_id=? AND operation_id=?',(run_id,row['operation_id']),
        {'feedback_json':256*1024,'payloads_json':1024*1024,'logical_path':4096,**metadata}) for row in identities)
    return total,rows


class ResearchPublicationReadPort:
    def __init__(self,*,queue_path,research_path,namespace):
        self.queue_path=Path(queue_path).absolute();self.research_path=Path(research_path).absolute()
        if namespace not in ('FIXTURE','LOCAL_RESEARCH'):raise PublicationHistoryError()
        self.namespace=namespace

    def _job(self,job_id,end):
        with _snapshot(self.queue_path,'queue',end) as db:
            if [tuple(row) for row in db.execute('SELECT singleton,namespace FROM research_queue_namespace LIMIT 2')]!=[(1,self.namespace)]:
                raise PublicationHistoryError()
            row=_bounded_row(db,'research_queue_jobs','run_id=?',(job_id,),{'input_json':512*1024})
            raw=row['input_json'];inputs=json.loads(raw)
            if (digest(raw.encode())!=row['input_hash'] or job_id!='job-'+row['input_hash'][7:]
                    or inputs['namespace']!=self.namespace or inputs['implementation_hash']!=row['implementation_hash']
                    or inputs['selected']['arguments']['submission_id']!=row['submission_id']):
                raise PublicationHistoryError()
            if row['outcome_json'] is not None and json.loads(row['outcome_json'])['run_id']!=row['owner_run_id']:
                raise PublicationHistoryError()
            return {key:row[key] for key in ('run_id','submission_id','input_json','input_hash','implementation_hash','owner_run_id')}

    def history(self,job_id,*,limit=20,offset=0):
        _page_args(job_id,limit,offset)
        try:
            end=time.monotonic()+2;job=self._job(job_id,end)
            if job['owner_run_id'] is None:
                page=_page([],0,limit,offset,status='NOT_RUN',reasons=('REPORT_NOT_READY',))
            else:
                with _snapshot(self.research_path,'research',end) as db:
                    run=_bounded_row(db,'research_runs','run_id=?',(job['owner_run_id'],),{'input_json':1024*1024})
                    inputs=json.loads(run['input_json'])
                    if (digest(run['input_json'].encode())!=run['input_hash'] or run['run_id']!='run-'+run['input_hash'][7:]
                            or inputs['namespace']!=self.namespace or inputs['submission_id']!=job['submission_id']
                            or inputs['implementation_hash']!=job['implementation_hash']):
                        raise PublicationHistoryError()
                    from strategy import parse_strategy_definition
                    arguments=json.loads(job['input_json'])['selected']['arguments']
                    if (json.loads(parse_strategy_definition(arguments['definition']).canonical_json)!=inputs['strategy']
                            or inputs['family_id']!=arguments.get('family_id') or inputs['random_seed']!=arguments.get('seed')):
                        raise PublicationHistoryError()
                    total,rows=_rows(db,'research_feedback_publications',run['run_id'],limit,offset)
                    items=[]
                    for row in rows:
                        checked_feedback_record(row,run);items.append(_metadata(row))
                    page=_page(items,total,limit,offset)
            # A separate queue snapshot catches a changed owner binding while
            # the original report store snapshot was being inspected.
            if self._job(job_id,end)!=job:raise PublicationHistoryError()
            return page
        except _ERRORS:raise PublicationHistoryError() from None


class PaperPublicationReadPort:
    def __init__(self,*,process_path,namespace):
        self.path=Path(process_path).absolute()
        if namespace not in ('FIXTURE','LOCAL_RESEARCH'):raise PublicationHistoryError()
        self.namespace=namespace

    def history(self,run_id,*,limit=20,offset=0):
        _page_args(run_id,limit,offset)
        try:
            end=time.monotonic()+2
            with _snapshot(self.path,'paper',end) as db:
                run=_bounded_row(db,'paper_process_runs','run_id=?',(run_id,),
                    {'binding_json':65536,'run_id':256,'binding_hash':71,'created_at':32})
                binding=_read_json(run['binding_json'],run['binding_hash']);_binding(binding)
                if binding['namespace']!=self.namespace:raise PublicationHistoryError()
                total,rows=_rows(db,'paper_feedback_publications',run_id,limit,offset)
                items=[]
                for row in rows:
                    checkpoint=db.execute('SELECT * FROM paper_process_checkpoints WHERE run_id=? AND revision=?',
                        (run_id,row['run_revision'])).fetchone()
                    generation=db.execute("SELECT instance_id FROM paper_process_generations WHERE run_id=? AND generation=? AND typeof(instance_id)='text' AND length(CAST(instance_id AS BLOB)) BETWEEN 1 AND 256",
                        (run_id,row['process_generation'])).fetchone()
                    if checkpoint is None or not isinstance(checkpoint['state_json'],str):raise PublicationHistoryError()
                    _read_json(checkpoint['state_json'],checkpoint['state_hash'])
                    checked_paper_feedback_record(row,run,checkpoint,generation)
                    items.append(_metadata(row,paper=True))
                return _page(items,total,limit,offset)
        except _ERRORS:raise PublicationHistoryError() from None
