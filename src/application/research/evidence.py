from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import platform
import sqlite3
import subprocess

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
        self._db.execute('PRAGMA busy_timeout=5000'); self._db.execute('PRAGMA journal_mode=WAL')
        self._db.execute('PRAGMA synchronous=FULL')
        migration=Path(__file__).resolve().parents[1]/'migrations/0002_research_attempts.sql'
        self._db.executescript(migration.read_text(encoding='utf-8'))
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
    def close(self): self._db.close()
    def __enter__(self): return self
    def __exit__(self,*_): self.close()
