"""Internal immutable software-check records in the existing E6 canonical store.

The public facade only resolves records. A storage-private writer is installed
by trusted producer composition; no API/cloud PASS importer exists. These rows
do not issue ReleaseBinding, qualified admission, lifecycle or financial authority.
"""
from contextlib import closing
from dataclasses import asdict,dataclass
from datetime import datetime,timedelta,timezone
import hashlib,json,re,sqlite3
from pathlib import Path

from ._sqlite_registry import _connect,_MIGRATIONS_DIR

_MIGRATION='0018_product_qualification_receipts.sql'
_TABLE='product_qualification_receipts'
_LIMIT=1048576
_HASH=re.compile(r'sha256:[0-9a-f]{64}')
_ATOM=re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}')
_WRITER_CAPABILITY=object()
_NAMESPACE_SQL=(
    'CREATE TABLE registry_research_namespace(singleton INTEGER PRIMARY KEY CHECK(singleton=1), namespace TEXT NOT NULL)',
    "CREATE TRIGGER registry_research_namespace_immutable BEFORE UPDATE ON registry_research_namespace BEGIN SELECT RAISE(ABORT,'registry namespace is immutable'); END",
    "CREATE TRIGGER registry_research_namespace_no_delete BEFORE DELETE ON registry_research_namespace BEGIN SELECT RAISE(ABORT,'registry namespace cannot be deleted'); END")

class QualificationReceiptError(ValueError):pass

def _fail(reason):raise QualificationReceiptError(reason)
def _digest(raw):return 'sha256:'+hashlib.sha256(raw.encode('utf-8')).hexdigest()
def _canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def _atom(value):
    if not isinstance(value,str) or not _ATOM.fullmatch(value):_fail('QUALIFICATION_IDENTITY_INVALID')
def _hash(value):
    if not isinstance(value,str) or not _HASH.fullmatch(value):_fail('QUALIFICATION_HASH_INVALID')
def _namespace(value):
    if value not in ('FIXTURE','LOCAL_RESEARCH'):_fail('QUALIFICATION_NAMESPACE_INVALID')
def _stamp(value):
    if not isinstance(value,datetime) or value.utcoffset()!=timedelta(0):_fail('QUALIFICATION_UTC_REQUIRED')
    return value.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
def _utc(value):
    if not isinstance(value,str) or len(value)>40:_fail('QUALIFICATION_UTC_REQUIRED')
    try:result=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:_fail('QUALIFICATION_UTC_REQUIRED')
    if _stamp(result)!=value:_fail('QUALIFICATION_UTC_REQUIRED')
    return result

@dataclass(frozen=True)
class QualificationSubject:
    namespace:str
    executable_revision:str
    implementation_hash:str
    build_hash:str
    platform_id:str
    def __post_init__(self):
        _namespace(self.namespace);_hash(self.implementation_hash);_hash(self.build_hash);_atom(self.platform_id)
        if not isinstance(self.executable_revision,str) or not re.fullmatch('[0-9a-f]{40}',self.executable_revision):
            _fail('QUALIFICATION_EXECUTABLE_REVISION_INVALID')

@dataclass(frozen=True)
class QualificationCheck:
    check_id:str
    command_ref:str
    log_ref:str
    log_hash:str
    returncode:int
    tree_reaped:bool
    tests_run:int
    failures:int
    errors:int
    skipped:int
    expected_failures:int
    unexpected_successes:int
    duration_ms:int
    def __post_init__(self):
        for name in ('check_id','command_ref','log_ref'):_atom(getattr(self,name))
        _hash(self.log_hash)
        if type(self.returncode) is not int or not -2147483648<=self.returncode<=4294967295:
            _fail('QUALIFICATION_EXIT_INVALID')
        if type(self.tree_reaped) is not bool:_fail('QUALIFICATION_CLEANUP_REQUIRED')
        for name in ('tests_run','failures','errors','skipped','expected_failures','unexpected_successes','duration_ms'):
            value=getattr(self,name)
            if type(value) is not int or not 0<=value<=2147483647:_fail('QUALIFICATION_COUNT_INVALID')
    @property
    def passed(self):
        return self.returncode==0 and self.tree_reaped and not any((self.failures,self.errors,
            self.skipped,self.expected_failures,self.unexpected_successes))

@dataclass(frozen=True)
class QualificationReceipt:
    receipt_id:str
    execution_id:str
    subject:QualificationSubject
    profile_id:str
    profile_hash:str
    checks:tuple[QualificationCheck,...]
    started_at:str
    finished_at:str
    @property
    def scope(self):return 'SOFTWARE_CHECK_EXECUTION_ONLY'
    @property
    def passed(self):return all(check.passed for check in self.checks)

def _payload(execution_id,subject,profile_id,profile_hash,checks,started_at,finished_at):
    _atom(execution_id);_atom(profile_id);_hash(profile_hash)
    if not isinstance(subject,QualificationSubject):_fail('QUALIFICATION_SUBJECT_REQUIRED')
    if (not isinstance(checks,tuple) or not 1<=len(checks)<=256 or
        any(not isinstance(check,QualificationCheck) for check in checks) or
        len({check.check_id for check in checks})!=len(checks)):_fail('QUALIFICATION_INVENTORY_INVALID')
    # Revalidate even trusted dataclass instances before serialization.
    subject=QualificationSubject(**asdict(subject))
    checks=tuple(QualificationCheck(**asdict(check)) for check in checks)
    started=_stamp(started_at);finished=_stamp(finished_at)
    if finished_at<started_at:_fail('QUALIFICATION_TIME_ORDER_INVALID')
    value=dict(schema_version='r7-owned-software-check-receipt-v0.2',scope='SOFTWARE_CHECK_EXECUTION_ONLY',
        execution_id=execution_id,subject=asdict(subject),profile_id=profile_id,profile_hash=profile_hash,
        checks=[asdict(check) for check in checks],started_at=started,finished_at=finished)
    raw=_canonical(value)
    if len(raw.encode('utf-8'))>_LIMIT:_fail('QUALIFICATION_PAYLOAD_TOO_LARGE')
    receipt=QualificationReceipt('qualification-'+_digest(raw)[7:],execution_id,subject,profile_id,profile_hash,checks,started,finished)
    return receipt,raw

def _columns(receipt,raw):
    return (receipt.execution_id,receipt.receipt_id,receipt.subject.namespace,_digest(_canonical(asdict(receipt.subject))),
        _digest(_canonical([check.check_id for check in receipt.checks])),raw,_digest(raw),receipt.started_at,receipt.finished_at)

def _pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:_fail('QUALIFICATION_DUPLICATE_JSON_KEY')
        result[key]=value
    return result

def _decode(row):
    raw=row['payload_json']
    if not isinstance(raw,str) or len(raw.encode('utf-8'))>_LIMIT or _digest(raw)!=row['payload_hash']:
        _fail('QUALIFICATION_PAYLOAD_INVALID')
    try:
        value=json.loads(raw,object_pairs_hook=_pairs,parse_constant=lambda _: _fail('QUALIFICATION_JSON_INVALID'))
        expected={'schema_version','scope','execution_id','subject','profile_id','profile_hash','checks','started_at','finished_at'}
        if (not isinstance(value,dict) or set(value)!=expected or value['schema_version']!='r7-owned-software-check-receipt-v0.2'
            or value['scope']!='SOFTWARE_CHECK_EXECUTION_ONLY' or not isinstance(value['checks'],list)
            or not 1<=len(value['checks'])<=256):_fail('QUALIFICATION_PAYLOAD_INVALID')
        subject=QualificationSubject(**value['subject'])
        checks=tuple(QualificationCheck(**check) for check in value['checks'])
        receipt,canonical=_payload(value['execution_id'],subject,value['profile_id'],value['profile_hash'],checks,
            _utc(value['started_at']),_utc(value['finished_at']))
        if canonical!=raw or tuple(row)!=_columns(receipt,raw):_fail('QUALIFICATION_ROW_INVALID')
        return receipt
    except (ValueError,TypeError,KeyError,UnicodeError) as error:
        if isinstance(error,QualificationReceiptError):raise
        raise QualificationReceiptError('QUALIFICATION_PAYLOAD_INVALID') from error

def _schema(db,table):
    return tuple(tuple(row) for row in db.execute('SELECT type,name,tbl_name,sql FROM sqlite_master WHERE tbl_name=? ORDER BY type,name',(table,)))

def _signatures():
    script=(_MIGRATIONS_DIR/_MIGRATION).read_text(encoding='utf-8').replace('\r\n','\n')
    if len(script)>16384 or not script.startswith('-- r7-migration-transaction: atomic'):_fail('QUALIFICATION_MIGRATION_INVALID')
    with closing(sqlite3.connect(':memory:')) as model:
        for sql in _NAMESPACE_SQL:model.execute(sql)
        namespace=_schema(model,'registry_research_namespace')
        model.executescript(script);receipts=_schema(model,_TABLE)
    return script,namespace,receipts

def _require_namespace(db,namespace,signature):
    if _schema(db,'registry_research_namespace')!=signature:_fail('QUALIFICATION_NAMESPACE_UNRECOGNIZED')
    rows=db.execute('SELECT singleton,namespace FROM registry_research_namespace').fetchall()
    if len(rows)!=1 or tuple(rows[0])!=(1,namespace):_fail('QUALIFICATION_NAMESPACE_MISMATCH')

def _require_schema(db,signature):
    if _schema(db,_TABLE)!=signature:_fail('QUALIFICATION_SCHEMA_UNRECOGNIZED')
    row=db.execute('SELECT migration_name FROM schema_migrations WHERE migration_name=?',(_MIGRATION,)).fetchone()
    if row is None:_fail('QUALIFICATION_SCHEMA_RECEIPT_MISSING')

def _execute_receipt_migration(db,script):
    statement=''
    for line in script.splitlines(keepends=True):
        statement+=line
        if sqlite3.complete_statement(statement):db.execute(statement);statement=''
    if statement.strip():_fail('QUALIFICATION_MIGRATION_INCOMPLETE')

def _ensure_owner_schema(db,namespace,signatures):
    script,namespace_signature,receipt_signature=signatures
    db.execute('BEGIN IMMEDIATE')
    try:
        _require_namespace(db,namespace,namespace_signature)
        expected={p.name for p in _MIGRATIONS_DIR.glob('*.sql') if p.name<=_MIGRATION}
        applied={row[0] for row in db.execute('SELECT migration_name FROM schema_migrations')}
        if applied not in (expected,expected-{_MIGRATION}):_fail('QUALIFICATION_CANONICAL_MIGRATION_UNRECOGNIZED')
        if _MIGRATION not in applied:
            if _schema(db,_TABLE):_fail('QUALIFICATION_SCHEMA_UNRECEIPTED')
            _execute_receipt_migration(db,script)
            if _schema(db,_TABLE)!=receipt_signature:_fail('QUALIFICATION_SCHEMA_UNRECOGNIZED')
            db.execute('INSERT INTO schema_migrations(migration_name) VALUES(?)',(_MIGRATION,))
        _require_schema(db,receipt_signature);db.commit()
    except BaseException:
        db.rollback();raise

class _QualificationReceiptReader:
    def __init__(self,db,namespace,signatures):self._db,self.namespace,self._signatures=db,namespace,signatures
    def close(self):self._db.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def get(self,receipt_id):
        if not isinstance(receipt_id,str) or not re.fullmatch('qualification-[0-9a-f]{64}',receipt_id):
            _fail('QUALIFICATION_RECEIPT_REFERENCE_INVALID')
        self._db.execute('BEGIN')
        try:
            _require_namespace(self._db,self.namespace,self._signatures[1])
            _require_schema(self._db,self._signatures[2])
            row=self._db.execute('SELECT * FROM product_qualification_receipts WHERE receipt_id=? AND namespace=?',
                (receipt_id,self.namespace)).fetchone()
        except sqlite3.Error as error:raise QualificationReceiptError('QUALIFICATION_READ_FAILED') from error
        finally:self._db.rollback()
        return None if row is None else _decode(row)

class _QualificationReceiptOwner(_QualificationReceiptReader):
    def __init__(self,db,namespace,signatures,*,_writer_capability=None):
        if _writer_capability is not _WRITER_CAPABILITY:_fail('QUALIFICATION_WRITER_CAPABILITY_REQUIRED')
        super().__init__(db,namespace,signatures)
    def _append(self,*,execution_id,subject,profile_id,profile_hash,checks,started_at,finished_at):
        receipt,raw=_payload(execution_id,subject,profile_id,profile_hash,checks,started_at,finished_at)
        if subject.namespace!=self.namespace:_fail('QUALIFICATION_NAMESPACE_MISMATCH')
        columns=_columns(receipt,raw);existing=None
        self._db.execute('BEGIN IMMEDIATE')
        try:
            _require_namespace(self._db,self.namespace,self._signatures[1]);_require_schema(self._db,self._signatures[2])
            existing=self._db.execute('SELECT * FROM product_qualification_receipts WHERE execution_id=?',(execution_id,)).fetchone()
            if existing is None:
                self._db.execute('INSERT INTO product_qualification_receipts VALUES(?,?,?,?,?,?,?,?,?)',columns)
                self._db.commit()
            else:self._db.rollback()
        except sqlite3.Error as error:
            self._db.rollback();raise QualificationReceiptError('QUALIFICATION_WRITE_FAILED') from error
        except BaseException:self._db.rollback();raise
        if existing is not None and tuple(existing)!=columns:
            _decode(existing)  # Validate bounded historical bytes outside the writer transaction.
            _fail('QUALIFICATION_EXECUTION_CONFLICT')
        return receipt

def _open(path,namespace,*,writer):
    _namespace(namespace);db=None
    try:
        from application.platform.resources import require_local_database_volume
        from application.platform.supervision import _local_path
        path=Path(path).absolute();require_local_database_volume(path);_local_path(path)
        signatures=_signatures()
        if writer:db=_connect(path,require_existing=True)
        else:
            db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
        db.isolation_level=None;db.execute('PRAGMA busy_timeout=5000')
        # Validation never calls the namespace binder or creates a replacement DB.
        _require_namespace(db,namespace,signatures[1])
        if writer:
            _ensure_owner_schema(db,namespace,signatures)
            db.execute('PRAGMA synchronous=FULL')
            return _QualificationReceiptOwner(db,namespace,signatures,_writer_capability=_WRITER_CAPABILITY)
        _require_schema(db,signatures[2]);db.execute('PRAGMA query_only=ON')
        return _QualificationReceiptReader(db,namespace,signatures)
    except BaseException as error:
        if db is not None:db.close()
        if isinstance(error,(sqlite3.Error,OSError)):raise QualificationReceiptError('QUALIFICATION_STORE_UNAVAILABLE') from error
        raise

def open_qualification_receipts(path:str|Path,*,namespace:str):
    """Existing-store, SQLite read-only software evidence resolution; no admission."""
    return _open(path,namespace,writer=False)

def _open_qualification_receipt_owner(path:str|Path,*,namespace:str):
    """Trusted owning producer composition only; never an HTTP/package factory."""
    return _open(path,namespace,writer=True)

__all__=['QualificationSubject','QualificationCheck','QualificationReceipt','QualificationReceiptError','open_qualification_receipts']
