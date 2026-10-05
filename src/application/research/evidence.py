from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys

from application.datasets.catalog import canonical,digest,hash_value,text
from application.platform.resources import require_local_database_volume
from strategy.v02.capabilities import _revision

class ResearchLeaseConflict(RuntimeError): pass
class ResearchEvidenceConflict(RuntimeError): pass

def now_utc(): return datetime.now(timezone.utc)
def stamp(value):
    if not isinstance(value,datetime) or value.utcoffset()!=timedelta(0): raise ValueError('Aware UTC required')
    return value.isoformat(timespec='microseconds').replace('+00:00','Z')

def capture_provenance():
    if getattr(sys, 'frozen', False):
        from application.platform.distribution import verify_distribution
        identity=verify_distribution(Path(sys.executable).resolve().parent)
        return dict(identity, os=platform.system(), os_version=platform.version(), architecture=platform.machine(),
                    python=platform.python_version(), execution='LOCAL', provider_requests=0, credentials='NONE',
                    capital='NONE', github_compute='NOT_USED')
    root=Path(__file__).resolve().parents[3]
    def git(*args):
        try:
            return subprocess.run(['git',*args],cwd=root,check=True,capture_output=True,text=True,timeout=3).stdout.strip()
        except (OSError,subprocess.SubprocessError): return None
    revision=git('rev-parse','HEAD'); status=git('status','--porcelain')
    return dict(executable_revision=revision,implementation_hash=_revision(),
                worktree='UNAVAILABLE' if status is None else 'DIRTY' if status else 'CLEAN',
                os=platform.system(),os_version=platform.version(),architecture=platform.machine(),
                python=platform.python_version(),execution='LOCAL',provider_requests=0,credentials='NONE',
                capital='NONE',github_compute='NOT_USED')

@dataclass(frozen=True)
class ResearchClaim:
    attempt_id: int
    run_id: str
    stage: str
    input_hash: str
    owner_id: str
    lease_generation: int

class ResearchJournal:
    def __init__(self,path):
        path=Path(path).absolute(); require_local_database_volume(path)
        path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        self._db=sqlite3.connect(path,timeout=5); self._db.row_factory=sqlite3.Row
        self._db.execute('PRAGMA foreign_keys=ON')
        self._db.execute('PRAGMA busy_timeout=5000'); self._db.execute('PRAGMA journal_mode=WAL')
        self._db.execute('PRAGMA synchronous=FULL')
        migration=Path(__file__).resolve().parents[1]/'migrations/0002_research_attempts.sql'
        self._db.executescript(migration.read_text(encoding='utf-8'))
        feedback_migration=migration.parent/'0007_research_feedback_outbox.sql'
        self._db.executescript(feedback_migration.read_text(encoding='utf-8'))
    def register_run(self,run_id,inputs,now):
        text(run_id); raw=canonical(inputs); h=digest(raw.encode())
        if len(raw.encode())>1024*1024: raise ValueError('Research input size limit')
        with self._db:
            self._db.execute('INSERT OR IGNORE INTO research_runs VALUES(?,?,?,?)',(run_id,raw,h,stamp(now)))
            row=self._db.execute('SELECT input_hash FROM research_runs WHERE run_id=?',(run_id,)).fetchone()
            if row['input_hash']!=h: raise ResearchEvidenceConflict('Immutable run inputs changed')
        return h
    def claim(self,run_id,stage,input_hash,owner_id,now,*,lease_seconds=60):
        for value in (run_id,stage,owner_id): text(value)
        hash_value(input_hash)
        if type(lease_seconds) is not int or not 1<=lease_seconds<=300: raise ValueError('Bounded lease required')
        current=stamp(now); deadline=stamp(now+timedelta(seconds=lease_seconds))
        with self._db:
            self._db.execute('BEGIN IMMEDIATE')
            row=self._db.execute('SELECT * FROM research_attempts WHERE run_id=? AND stage=? ORDER BY lease_generation DESC LIMIT 1',(run_id,stage)).fetchone()
            generation=1
            if row:
                if row['input_hash']!=input_hash: raise ResearchEvidenceConflict('Stage input hash changed')
                if row['status']=='COMPLETE' or row['status']=='RUNNING' and row['lease_deadline']>current:
                    raise ResearchLeaseConflict('Stage complete or lease busy')
                generation=row['lease_generation']+1
                if row['status']=='RUNNING':
                    raw=canonical({'reason_codes':['LEASE_EXPIRED']})
                    self._db.execute("UPDATE research_attempts SET status='ABORTED',ended_at=?,output_json=?,output_hash=?,reason_codes_json='[\"LEASE_EXPIRED\"]' WHERE attempt_id=?",
                                     (current,raw,digest(raw.encode()),row['attempt_id']))
            cursor=self._db.execute("INSERT INTO research_attempts(run_id,stage,input_hash,owner_id,lease_generation,lease_deadline,started_at,status) VALUES(?,?,?,?,?,?,?,'RUNNING')",
                                    (run_id,stage,input_hash,owner_id,generation,deadline,current))
            return ResearchClaim(cursor.lastrowid,run_id,stage,input_hash,owner_id,generation)
    def renew(self,claim,now,*,lease_seconds=60):
        if type(lease_seconds) is not int or not 1<=lease_seconds<=300: raise ValueError('Bounded lease required')
        with self._db:
            cursor=self._db.execute("UPDATE research_attempts SET lease_deadline=? WHERE attempt_id=? AND owner_id=? AND lease_generation=? AND status='RUNNING' AND lease_deadline>?",
                                    (stamp(now+timedelta(seconds=lease_seconds)),claim.attempt_id,claim.owner_id,claim.lease_generation,stamp(now)))
            if cursor.rowcount!=1: raise ResearchLeaseConflict('Expired or fenced lease')
    def finish(self,claim,output,now,*,status='COMPLETE',reason_codes=()):
        if status not in ('COMPLETE','FAILED'): raise ValueError('Invalid terminal attempt status')
        raw=canonical(output)
        if len(raw.encode())>8*1024*1024: raise ValueError('Research output size limit')
        with self._db:
            cursor=self._db.execute("UPDATE research_attempts SET status=?,ended_at=?,output_json=?,output_hash=?,reason_codes_json=? WHERE attempt_id=? AND run_id=? AND stage=? AND input_hash=? AND owner_id=? AND lease_generation=? AND status='RUNNING' AND started_at<=? AND lease_deadline>?",
                (status,stamp(now),raw,digest(raw.encode()),canonical(list(reason_codes)),claim.attempt_id,claim.run_id,claim.stage,claim.input_hash,claim.owner_id,claim.lease_generation,stamp(now),stamp(now)))
            if cursor.rowcount!=1: raise ResearchLeaseConflict('Expired or fenced lease')
        return 'research:'+claim.run_id+'/'+claim.stage+'/'+digest(raw.encode())
    def result(self,run_id,stage):
        row=self._db.execute("SELECT * FROM research_attempts WHERE run_id=? AND stage=? AND status='COMPLETE' ORDER BY lease_generation DESC LIMIT 1",(run_id,stage)).fetchone()
        if not row: return None
        if digest(row['output_json'].encode())!=row['output_hash']: raise ResearchEvidenceConflict('Stored output hash mismatch')
        return json.loads(row['output_json'])
    def attempts(self,run_id):
        rows=self._db.execute('SELECT * FROM research_attempts WHERE run_id=? ORDER BY attempt_id',(run_id,)).fetchall()
        return [dict(row) for row in rows]
    def runs(self):
        return [dict(row) for row in self._db.execute('SELECT run_id,input_hash,created_at FROM research_runs ORDER BY created_at,run_id').fetchall()]
    def enqueue_feedback(self,feedback,now):
        from application.cloud.feedback import feedback_bundle
        from application.cloud.manifest import byte_hash,canonical_bytes
        bundle=feedback_bundle(feedback)
        run_id=feedback['run_id'];row=self._db.execute('SELECT * FROM research_runs WHERE run_id=?',(run_id,)).fetchone()
        if row is None or digest(row['input_json'].encode())!=row['input_hash']:
            raise ResearchEvidenceConflict('Actual feedback run required')
        inputs=json.loads(row['input_json']);strategy=inputs['strategy']
        if (feedback['namespace']!=inputs['namespace'] or feedback['strategy']!={
                **{key:strategy[key] for key in ('strategy_id','strategy_version','content_hash')},**strategy['runtime_compatibility']}
                or feedback['dataset']['manifest_hash']!=inputs['dataset_manifest_hash']
                or feedback['split']['policy_hash']!=inputs['split_policy_hash']):
            raise ResearchEvidenceConflict('Actual feedback subject required')
        raw=canonical_bytes(feedback);h=byte_hash(raw)
        payloads=canonical({name:value.decode('utf-8') for name,value in bundle.payloads.items()})
        artifact=byte_hash(canonical_bytes({name:byte_hash(value) for name,value in bundle.payloads.items()}))
        operation='r7-feedback-'+h[7:]
        if len(raw)>256*1024 or len(payloads.encode())>1024*1024:
            raise ResearchEvidenceConflict('Bounded feedback publication required')
        with self._db:
            self._db.execute('BEGIN IMMEDIATE')
            existing=self._db.execute('SELECT * FROM research_feedback_publications WHERE operation_id=?',(operation,)).fetchone()
            if existing is not None:
                if existing['feedback_hash']!=h or existing['payloads_json']!=payloads or existing['artifact_hash']!=artifact:
                    raise ResearchEvidenceConflict('Immutable feedback publication changed')
                return operation
            count,size=self._db.execute("SELECT count(*),coalesce(sum(length(CAST(payloads_json AS BLOB))),0) FROM research_feedback_publications WHERE state!='CLOUD_ACKNOWLEDGED'").fetchone()
            if count>=1000 or size+len(payloads.encode())>16*1024*1024:
                raise ResearchEvidenceConflict('Feedback outbox capacity reached')
            # The public stage-result bytes/reference and outbox state become
            # durable together in this owning research-store transaction.
            self._db.execute('INSERT INTO research_feedback_publications VALUES(?,?,?,?,?,?,?,?,?,?)',
                (operation,run_id,raw.decode('utf-8'),h,bundle.logical_path,payloads,artifact,'PENDING',0,stamp(now)))
        return operation
    def pending_feedback_publications(self,limit):
        from application.cloud.feedback import validate_feedback_publication
        from application.cloud.manifest import byte_hash,canonical_bytes
        from application.cloud.protocol import ArtifactBundle
        if type(limit) is not int or not 1<=limit<=100:raise ValueError('Bounded feedback batch required')
        result=[]
        for row in self._db.execute("SELECT * FROM research_feedback_publications WHERE state IN ('PENDING','LOCAL_STAGED','UNAVAILABLE') ORDER BY operation_id LIMIT ?",(limit,)).fetchall():
            if byte_hash(row['feedback_json'].encode('utf-8'))!=row['feedback_hash']:
                raise ResearchEvidenceConflict('Feedback output hash mismatch')
            payloads={name:value.encode('utf-8') for name,value in json.loads(row['payloads_json']).items()}
            validate_feedback_publication(row['logical_path'],payloads)
            if payloads['feedback.json']!=row['feedback_json'].encode('utf-8') or byte_hash(canonical_bytes({name:byte_hash(raw) for name,raw in payloads.items()}))!=row['artifact_hash']:
                raise ResearchEvidenceConflict('Feedback bundle hash mismatch')
            result.append((row['operation_id'],ArtifactBundle(row['logical_path'],payloads),row['artifact_hash']))
        return tuple(result)
    def record_feedback_publication(self,operation_id,status,*,artifact_hash=None):
        if status not in ('LOCAL_STAGED','CLOUD_ACKNOWLEDGED','UNAVAILABLE','CONFLICT'):raise ValueError('Exact publication status required')
        with self._db:
            row=self._db.execute('SELECT artifact_hash,state FROM research_feedback_publications WHERE operation_id=?',(operation_id,)).fetchone()
            if row is None or status in ('LOCAL_STAGED','CLOUD_ACKNOWLEDGED') and row['artifact_hash']!=artifact_hash:
                raise ResearchEvidenceConflict('Feedback acknowledgment identity mismatch')
            if row['state']=='CLOUD_ACKNOWLEDGED':
                if status!='CLOUD_ACKNOWLEDGED':raise ResearchEvidenceConflict('Acknowledged feedback cannot regress')
                return
            self._db.execute('UPDATE research_feedback_publications SET state=?,attempts=attempts+1 WHERE operation_id=?',(status,operation_id))
    def close(self): self._db.close()
    def __enter__(self): return self
    def __exit__(self,*_): self.close()
