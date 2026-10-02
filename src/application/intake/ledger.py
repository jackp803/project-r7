"""Local generation-fenced claims and an atomic result/outbox seam."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import sqlite3

from application.cloud.manifest import byte_hash, safe_component
from application.cloud.protocol import CloudError
from application.platform.resources import require_local_database_volume


class LeaseConflict(RuntimeError): pass
class ManifestConflict(RuntimeError): pass
class OutboxCapacityError(RuntimeError): pass


def _timestamp(now):
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() != timedelta(0):
        raise ValueError("Aware UTC time required")
    return now.isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class ClaimResult:
    submission_id: str
    manifest_hash: str
    owner_id: str
    lease_generation: int
    lease_deadline: str
    revision: int
    acquired: bool
    state: str
    effect_ref: str | None = None


@dataclass(frozen=True)
class SubmissionRecord:
    submission_id: str
    manifest_hash: str
    state: str
    revision: int
    effect_ref: str | None


@dataclass(frozen=True)
class OutboxItem:
    operation_id: str
    submission_id: str
    logical_path: str
    payload: bytes
    payload_hash: str
    state: str


class IntakeLedger:
    def __init__(self, database_path: Path, *, instance_id: str, lease_seconds=60,
                 outbox_max_items=1000, outbox_max_bytes=16*1024**2):
        self.instance_id = safe_component(instance_id)
        if type(lease_seconds) is not int or not 1 <= lease_seconds <= 300:
            raise ValueError("Bounded lease duration required")
        self.lease_seconds = lease_seconds
        if type(outbox_max_items) is not int or not 1 <= outbox_max_items <= 100000:
            raise ValueError("Bounded outbox item budget required")
        if type(outbox_max_bytes) is not int or not 64*1024 <= outbox_max_bytes <= 256*1024**2:
            raise ValueError("Bounded outbox byte budget required")
        self.outbox_max_items,self.outbox_max_bytes=outbox_max_items,outbox_max_bytes
        path = Path(database_path).absolute()
        require_local_database_volume(path)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._connection = sqlite3.connect(path, timeout=5)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._connection.execute("PRAGMA busy_timeout=5000")
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=FULL")
        migration = Path(__file__).parents[1] / "migrations/0001_intake_outbox.sql"
        self._connection.executescript(migration.read_text(encoding="utf-8"))

    def close(self): self._connection.close()
    def __enter__(self): return self
    def __exit__(self, *_): self.close()

    def operation_key(self, submission_id):
        safe_component(submission_id)
        return "r7-intake-" + hashlib.sha256((self.instance_id + "\x00" + submission_id).encode("ascii")).hexdigest()

    def get_submission(self, submission_id):
        row = self._connection.execute(
            "SELECT * FROM app_submissions WHERE instance_id=? AND submission_id=?",
            (self.instance_id, submission_id),
        ).fetchone()
        if row is None: return None
        return SubmissionRecord(row["submission_id"], row["manifest_hash"], row["state"], row["revision"], row["effect_ref"])

    def accepted_receipt(self,submission_id):
        """Read the immutable actual E6 intake receipt through its local outbox."""
        import json
        safe_component(submission_id)
        submission=self.get_submission(submission_id)
        if submission is None or submission.state!='INTAKE_ACCEPTED': return None
        row=self._connection.execute('SELECT payload,payload_hash FROM app_outbox WHERE operation_id=?',
            (self.operation_key(submission_id)+'-receipt',)).fetchone()
        if row is None or byte_hash(row['payload'])!=row['payload_hash']: raise ManifestConflict('Intake receipt integrity failed')
        payload=json.loads(row['payload'])
        if payload.get('submission_id')!=submission_id or payload.get('manifest_hash')!=submission.manifest_hash or payload.get('intake_id')!=submission.effect_ref:
            raise ManifestConflict('Intake receipt identity failed')
        return payload

    def submission_view(self,submission_id):
        safe_component(submission_id)
        row=self.get_submission(submission_id)
        observation=self._connection.execute('SELECT state,reason,observed_at,manifest_hash FROM app_submission_observations WHERE instance_id=? AND submission_id=? ORDER BY observation_id DESC LIMIT 1',
            (self.instance_id,submission_id)).fetchone()
        if row is None and observation is None: return None
        from dataclasses import asdict
        value=asdict(row) if row else dict(submission_id=submission_id,manifest_hash=observation['manifest_hash'],state=observation['state'],revision=0,effect_ref=None)
        value['latest_observation']=None if observation is None else dict(observation)
        value['receipt']=self.accepted_receipt(submission_id)
        publication=self._connection.execute('SELECT state,artifact_hash FROM app_outbox WHERE operation_id=?',(self.operation_key(submission_id)+'-receipt',)).fetchone()
        value['publication']=None if publication is None else dict(publication)
        return value

    def find_strategy_submission(self,strategy_id,strategy_version,content_hash):
        """Read one original author submission for an exact canonical subject."""
        row=self._connection.execute('''SELECT o.submission_id FROM app_outbox o
            JOIN app_submissions s ON s.instance_id=o.instance_id AND s.submission_id=o.submission_id
            WHERE o.instance_id=? AND s.state='INTAKE_ACCEPTED'
            AND json_extract(CAST(o.payload AS TEXT),'$.strategy_id')=?
            AND json_extract(CAST(o.payload AS TEXT),'$.strategy_version')=?
            AND json_extract(CAST(o.payload AS TEXT),'$.strategy_content_hash')=?
            ORDER BY o.submission_id LIMIT 1''',(self.instance_id,strategy_id,strategy_version,content_hash)).fetchone()
        if row is None: return None
        receipt=self.accepted_receipt(row['submission_id'])
        if receipt is None or (receipt['strategy_id'],receipt['strategy_version'],receipt['strategy_content_hash'])!=(strategy_id,strategy_version,content_hash):
            raise ManifestConflict('Original author subject integrity failed')
        return row['submission_id']

    def list_submissions(self,*,limit=50,offset=0):
        if type(limit) is not int or not 1<=limit<=200 or type(offset) is not int or not 0<=offset<=100000:
            raise ValueError('Bounded submission page required')
        rows=self._connection.execute('''SELECT submission_id FROM app_submissions WHERE instance_id=?
            UNION SELECT submission_id FROM app_submission_observations WHERE instance_id=? ORDER BY submission_id LIMIT ? OFFSET ?''',
            (self.instance_id,self.instance_id,limit,offset)).fetchall()
        return tuple(self.submission_view(row[0]) for row in rows)

    def claim(self, submission_id, manifest_hash, owner, now):
        safe_component(submission_id)
        safe_component(owner)
        from application.cloud.manifest import HASH
        if not isinstance(manifest_hash, str) or not HASH.fullmatch(manifest_hash):
            raise ValueError("Verified manifest hash required")
        current_time = _timestamp(now)
        deadline = _timestamp(now + timedelta(seconds=self.lease_seconds))
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            row = self._connection.execute("SELECT * FROM app_submissions WHERE instance_id=? AND submission_id=?",
                                            (self.instance_id, submission_id)).fetchone()
            if row is not None and row["manifest_hash"] != manifest_hash:
                raise ManifestConflict("Verified submission manifest is immutable")
            if row is not None and (row["state"] == "INTAKE_ACCEPTED" or row["lease_deadline"] > current_time):
                result = ClaimResult(submission_id, manifest_hash, row["owner_id"], row["lease_generation"],
                                     row["lease_deadline"], row["revision"], False, row["state"], row["effect_ref"])
            else:
                generation = 1 if row is None else row["lease_generation"] + 1
                revision = 0 if row is None else row["revision"] + 1
                self._connection.execute(
                    """INSERT INTO app_submissions(instance_id,submission_id,manifest_hash,owner_id,
                           lease_generation,lease_deadline,revision,state)
                           VALUES(?,?,?,?,?,?,?,'CLAIMED')
                           ON CONFLICT(instance_id,submission_id) DO UPDATE SET
                           owner_id=excluded.owner_id,lease_generation=excluded.lease_generation,
                           lease_deadline=excluded.lease_deadline,revision=excluded.revision,state='CLAIMED'""",
                    (self.instance_id, submission_id, manifest_hash, owner, generation, deadline, revision),
                )
                self._connection.execute("DELETE FROM app_sync_retry WHERE instance_id=? AND submission_id=?", (self.instance_id,submission_id))
                result = ClaimResult(submission_id, manifest_hash, owner, generation, deadline, revision, True, "CLAIMED")
            self._connection.commit()
            return result
        except BaseException:
            self._connection.rollback()
            raise

    def commit_effect(self, claim, effect_ref, outbox_item, *, now):
        timestamp = _timestamp(now)
        if not isinstance(effect_ref, str) or not effect_ref or len(effect_ref) > 256:
            raise ValueError("Bounded canonical effect reference required")
        if not isinstance(outbox_item, bytes) or len(outbox_item) > 64 * 1024:
            raise ValueError("Bounded receipt bytes required")
        payload_hash = byte_hash(outbox_item)
        operation_id = self.operation_key(claim.submission_id) + "-receipt"
        logical_path = f"receipts/{self.instance_id}/{claim.submission_id}/{payload_hash[7:]}"
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            self.ensure_outbox_capacity(len(outbox_item))
            row = self._connection.execute("SELECT * FROM app_submissions WHERE instance_id=? AND submission_id=?",
                                            (self.instance_id, claim.submission_id)).fetchone()
            if (row is None or row["manifest_hash"] != claim.manifest_hash or row["owner_id"] != claim.owner_id
                    or row["lease_generation"] != claim.lease_generation or row["revision"] != claim.revision
                    or row["state"] != "CLAIMED" or row["lease_deadline"] <= timestamp):
                raise LeaseConflict("Expired, superseded or completed claim cannot commit")
            self._connection.execute(
                """INSERT INTO app_outbox(operation_id,instance_id,submission_id,logical_path,payload,payload_hash,state)
                   VALUES(?,?,?,?,?,?,'PENDING')""",
                (operation_id,self.instance_id,claim.submission_id,logical_path,outbox_item,payload_hash),
            )
            self._connection.execute("UPDATE app_submissions SET state='INTAKE_ACCEPTED',effect_ref=?,revision=revision+1 WHERE instance_id=? AND submission_id=?",
                                     (effect_ref,self.instance_id,claim.submission_id))
            self._connection.commit()
            return self.get_submission(claim.submission_id)
        except BaseException:
            self._connection.rollback()
            raise

    def ensure_outbox_capacity(self,reserved_bytes=64*1024):
        row=self._connection.execute("SELECT COUNT(*) AS items,COALESCE(SUM(LENGTH(payload)),0) AS bytes FROM app_outbox WHERE instance_id=? AND state<>'CLOUD_ACKNOWLEDGED'", (self.instance_id,)).fetchone()
        if row["items"] >= self.outbox_max_items or row["bytes"]+reserved_bytes > self.outbox_max_bytes:
            raise OutboxCapacityError("OUTBOX_CAPACITY_REACHED")

    def observe(self, submission_id, state, reason, now, manifest_hash=None):
        safe_component(submission_id)
        if state not in {"BLOCKED", "INCOMPLETE_SYNC", "CONFLICT", "UNAVAILABLE", "SYNC_STALLED", "CLOUD_NOT_CONNECTED"}:
            raise ValueError("Unsupported observation state")
        safe_component(reason)
        stamp = _timestamp(now)
        with self._connection:
            if state == "INCOMPLETE_SYNC":
                retry = self._connection.execute("SELECT * FROM app_sync_retry WHERE instance_id=? AND submission_id=?", (self.instance_id,submission_id)).fetchone()
                same = retry is not None and retry["manifest_hash"] == manifest_hash
                first = retry["first_observed_at"] if same else stamp
                attempts = retry["attempts"] + 1 if same else 1
                first_time = datetime.fromisoformat(first.replace("Z", "+00:00"))
                if now - first_time >= timedelta(days=1):
                    state = "SYNC_STALLED"
                delay = min(300, 5 * 2**min(attempts - 1, 6))
                next_time = _timestamp(now + timedelta(seconds=delay))
                self._connection.execute("""INSERT INTO app_sync_retry(instance_id,submission_id,manifest_hash,first_observed_at,attempts,next_retry_at,state)
                    VALUES(?,?,?,?,?,?,?) ON CONFLICT(instance_id,submission_id) DO UPDATE SET
                    manifest_hash=excluded.manifest_hash,first_observed_at=excluded.first_observed_at,
                    attempts=excluded.attempts,next_retry_at=excluded.next_retry_at,state=excluded.state""",
                    (self.instance_id,submission_id,manifest_hash,first,attempts,next_time,state))
            self._connection.execute("INSERT INTO app_submission_observations(instance_id,submission_id,state,reason,observed_at,manifest_hash) VALUES(?,?,?,?,?,?)",
                                     (self.instance_id,submission_id,state,reason,stamp,manifest_hash))
        return state

    def retry_allowed(self, submission_id, now):
        stamp = _timestamp(now)
        row = self._connection.execute("SELECT state,next_retry_at FROM app_sync_retry WHERE instance_id=? AND submission_id=?", (self.instance_id,submission_id)).fetchone()
        return row is None or row["state"] != "SYNC_STALLED" and row["next_retry_at"] <= stamp

    def pending_outbox(self, limit):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("Bounded publication batch required")
        rows = self._connection.execute("SELECT * FROM app_outbox WHERE instance_id=? AND state IN ('PENDING','LOCAL_STAGED','UNAVAILABLE') ORDER BY operation_id LIMIT ?",
                                        (self.instance_id,limit)).fetchall()
        return tuple(OutboxItem(row["operation_id"],row["submission_id"],row["logical_path"],row["payload"],row["payload_hash"],row["state"]) for row in rows)

    def record_publication(self, operation_id, status, *, artifact_hash=None):
        if status not in {"LOCAL_STAGED", "CLOUD_ACKNOWLEDGED", "UNAVAILABLE", "CONFLICT"}:
            raise ValueError("Unsupported publication status")
        with self._connection:
            cursor = self._connection.execute("UPDATE app_outbox SET state=?,artifact_hash=?,attempts=attempts+1 WHERE instance_id=? AND operation_id=? AND state<>'CLOUD_ACKNOWLEDGED'",
                                               (status,artifact_hash,self.instance_id,operation_id))
            if cursor.rowcount != 1:
                raise LeaseConflict("Outbox operation missing or already acknowledged")
