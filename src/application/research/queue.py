"""Durable local dispatch of the actual research owner, with cooperative cancel.

resolve_request/service_factory are trusted local composition. HTTP supplies
only submission/policy identities; no caller definition, path, code or PASS.
Long owner work executes outside queue transactions in a separate worker.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3

from application.cloud.manifest import scan_untrusted, safe_component
from application.cloud.protocol import CloudError
from application.control_api.auth import _ClosingConnection
from application.datasets.catalog import canonical, digest, hash_value
from application.platform.resources import require_local_database_volume
from application.research.evidence import stamp
from application.research.service import ResearchService
from strategy.v02.capabilities import _revision
from registry.operational_authority import text as audit_text


class ResearchQueueError(ValueError):
    def __init__(self, code): self.code = code; super().__init__(code)


class ResearchCanceled(ResearchQueueError):
    def __init__(self): super().__init__('RESEARCH_CANCELED')


@dataclass(frozen=True)
class ResearchJobClaim:
    run_id: str
    generation: int


def _revision_int(value):
    if type(value) is not int or not 0 <= value < 2**63: raise ResearchQueueError('INVALID_REVISION')
    return value


class ResearchQueue:
    def __init__(self, database_path, *, namespace, owner_id, resolve_request, service_factory,
                 clock=lambda: datetime.now(timezone.utc), stage_observer=None):
        if namespace not in ('FIXTURE', 'LOCAL_RESEARCH') or not all(callable(value) for value in (resolve_request, service_factory, clock)):
            raise ResearchQueueError('EXPLICIT_QUEUE_COMPOSITION_REQUIRED')
        self.path = Path(database_path).absolute(); require_local_database_volume(self.path)
        if self.path.is_symlink(): raise ResearchQueueError('LOCAL_QUEUE_REQUIRED')
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.namespace, self.owner_id, self.clock = namespace, safe_component(owner_id), clock
        self.resolve_request, self.service_factory, self.stage_observer = resolve_request, service_factory, stage_observer
        with self._db() as db:
            db.executescript((Path(__file__).parents[1]/'migrations/0005_research_queue.sql').read_text(encoding='utf-8'))
            db.execute('INSERT OR IGNORE INTO research_queue_namespace VALUES(1,?)', (namespace,))
            if db.execute('SELECT namespace FROM research_queue_namespace').fetchone()[0] != namespace:
                raise ResearchQueueError('QUEUE_NAMESPACE_CONFLICT')

    def _db(self):
        db = sqlite3.connect(self.path, timeout=5); db.row_factory = sqlite3.Row
        db.execute('PRAGMA busy_timeout=5000'); db.execute('PRAGMA journal_mode=WAL'); db.execute('PRAGMA synchronous=FULL')
        return _ClosingConnection(db)

    def _resolve(self, submission_id, policy_id):
        try: selected = self.resolve_request(submission_id, policy_id)
        except Exception as error: raise ResearchQueueError('RESEARCH_SELECTION_NOT_CONFIGURED') from error
        if not isinstance(selected, dict) or set(selected) != {'submission_revision', 'arguments', 'selection_hash'}:
            raise ResearchQueueError('EXACT_SELECTED_RESEARCH_INPUT_REQUIRED')
        _revision_int(selected['submission_revision']); hash_value(selected['selection_hash'])
        arguments = selected['arguments']
        required = {'submission_id', 'definition', 'dataset_ref', 'split_policy_ref', 'cost_policy_ref'}
        optional = {'research_policy_ref', 'robustness_policy_ref', 'family_id', 'seed', 'risk_policy_ref'}
        if not isinstance(arguments, dict) or not required <= arguments.keys() or arguments.keys() - required - optional or arguments['submission_id'] != submission_id:
            raise ResearchQueueError('EXACT_SELECTED_RESEARCH_INPUT_REQUIRED')
        try: scan_untrusted(selected); raw = canonical(selected)
        except (CloudError, ValueError, TypeError): raise ResearchQueueError('RESEARCH_INPUT_INVALID') from None
        if len(raw.encode()) > 512*1024: raise ResearchQueueError('RESEARCH_INPUT_SIZE_LIMIT')
        return json.loads(raw)

    @staticmethod
    def _cached(db, command_id, request):
        row = db.execute('SELECT * FROM research_queue_commands WHERE command_id=?', (command_id,)).fetchone()
        if row is None: return None
        if row['request_json'] != request: raise ResearchQueueError('COMMAND_CONTENT_CONFLICT')
        return json.loads(row['receipt_json'])

    def selected_submission_revision(self,submission_id,policy_id):
        return self._resolve(submission_id,policy_id)['submission_revision']

    @staticmethod
    def _event(db, row, now):
        db.execute('INSERT INTO research_queue_events(run_id,state,generation,revision,observed_at) VALUES(?,?,?,?,?)',
                   (row['run_id'], row['state'], row['generation'], row['revision'], now))

    def enqueue(self, submission_id, policy_id, command_id, expected_revision, *, actor):
        for value in (submission_id,policy_id): safe_component(value)
        for value in (command_id,actor): audit_text(value)
        _revision_int(expected_revision)
        request = canonical(dict(operation='ENQUEUE', submission_id=submission_id, policy_id=policy_id,
            command_id=command_id, expected_revision=expected_revision, actor=actor, namespace=self.namespace))
        with self._db() as db:
            cached = self._cached(db, command_id, request)
            if cached is not None: return cached
        selected = self._resolve(submission_id, policy_id)
        if selected['submission_revision'] != expected_revision: raise ResearchQueueError('SUBMISSION_REVISION_CONFLICT')
        source = _revision()
        inputs = canonical(dict(namespace=self.namespace, selected=selected, implementation_hash=source))
        input_hash = digest(inputs.encode()); run_id = 'job-'+input_hash[7:]
        with self._db() as db:
            now = stamp(self.clock()); db.execute('BEGIN IMMEDIATE')
            cached = self._cached(db, command_id, request)
            if cached is not None: return cached
            if db.execute("SELECT COUNT(*) FROM research_queue_jobs WHERE state IN ('QUEUED','RUNNING','CANCEL_REQUESTED')").fetchone()[0] >= 1000:
                raise ResearchQueueError('RESEARCH_QUEUE_CAPACITY_REACHED')
            cursor = db.execute('''INSERT OR IGNORE INTO research_queue_jobs(run_id,submission_id,policy_id,input_json,input_hash,
                implementation_hash,state,revision,created_at,updated_at) VALUES(?,?,?,?,?,?,'QUEUED',0,?,?)''',
                (run_id, submission_id, policy_id, inputs, input_hash, source, now, now))
            row = db.execute('SELECT * FROM research_queue_jobs WHERE run_id=?', (run_id,)).fetchone()
            if row['input_json'] != inputs: raise ResearchQueueError('IMMUTABLE_JOB_CONFLICT')
            if cursor.rowcount: self._event(db, row, now)
            receipt = dict(run_id=run_id, status=row['state'], revision=row['revision'], submission_revision=expected_revision,
                           observed_at=now, input_hash=input_hash)
            db.execute('INSERT INTO research_queue_commands VALUES(?,?,?)', (command_id, request, canonical(receipt)))
            return receipt

    @staticmethod
    def _view(row):
        if row is None: raise ResearchQueueError('RESEARCH_JOB_NOT_FOUND')
        return dict(run_id=row['run_id'], submission_id=row['submission_id'], policy_id=row['policy_id'], state=row['state'],
            revision=row['revision'], generation=row['generation'], owner_run_id=row['owner_run_id'], stage=row['stage'],
            input_hash=row['input_hash'], implementation_hash=row['implementation_hash'], created_at=row['created_at'],
            observed_at=row['updated_at'], cancellation_requested=bool(row['cancel_requested']),
            outcome=None if row['outcome_json'] is None else json.loads(row['outcome_json']), reason_codes=json.loads(row['reason_codes_json']))

    def get(self, run_id):
        safe_component(run_id)
        with self._db() as db: return self._view(db.execute('SELECT * FROM research_queue_jobs WHERE run_id=?', (run_id,)).fetchone())

    def list(self, *, limit=50, offset=0):
        if type(limit) is not int or not 1 <= limit <= 200 or type(offset) is not int or not 0 <= offset <= 100000:
            raise ResearchQueueError('INVALID_PAGE')
        with self._db() as db:
            return [self._view(row) for row in db.execute('SELECT * FROM research_queue_jobs ORDER BY created_at,run_id LIMIT ? OFFSET ?', (limit, offset))]

    def counts(self):
        with self._db() as db:
            return dict(db.execute('SELECT state,COUNT(*) FROM research_queue_jobs GROUP BY state').fetchall())

    def evidence_view(self,run_id):
        """Bounded actual owner summary. A view never reruns research or OOS."""
        from application.research.service import ResearchError
        from backtest.metrics import MetricsSummary
        job=self.get(run_id)
        if job['owner_run_id'] is None: return None
        with self.service_factory() as owner:
            if not isinstance(owner,ResearchService) or owner.namespace!=self.namespace:
                raise ResearchQueueError('ACTUAL_SAME_NAMESPACE_RESEARCH_OWNER_REQUIRED')
            try: report=owner.report(job['owner_run_id'])
            except ResearchError:
                attempts=owner.journal.attempts(job['owner_run_id'])
                return dict(status='REPORT_NOT_READY',attempts=[{key:row[key] for key in ('stage','status','started_at','ended_at','input_hash','output_hash')} for row in attempts])
        backtest=report['backtest']
        metrics=None if backtest is None else {key:backtest[key] for key in MetricsSummary.__dataclass_fields__}
        return dict(status=report['status'],reason_codes=report['reason_codes'],provenance=report['provenance'],
            compatibility=dict(status=report['compatibility']['status'],reason_codes=report['compatibility']['reason_codes']),
            backtest=metrics,backtest_e6_evidence_id=report['backtest_e6_evidence_id'],
            split_resolution=report['split_resolution'],dataset_resolution=report['dataset_resolution'],
            candidate_gate=report['candidate_gate'],sealed_oos=report['sealed_oos'],frozen_finalist=report['frozen_finalist'],
            owner_report_ref='research:'+job['owner_run_id']+'/diagnostic_report',
            attempts=[{key:row[key] for key in ('stage','status','started_at','ended_at','input_hash','output_hash')} for row in report['attempts']])

    def cancel(self, run_id, expected_revision, command_id, *, actor):
        safe_component(run_id)
        for value in (command_id,actor): audit_text(value)
        _revision_int(expected_revision)
        request = canonical(dict(operation='CANCEL', run_id=run_id, expected_revision=expected_revision, command_id=command_id, actor=actor))
        with self._db() as db:
            now = stamp(self.clock()); db.execute('BEGIN IMMEDIATE')
            cached = self._cached(db, command_id, request)
            if cached is not None: return cached
            row = db.execute('SELECT * FROM research_queue_jobs WHERE run_id=?', (run_id,)).fetchone()
            if row is None: raise ResearchQueueError('RESEARCH_JOB_NOT_FOUND')
            if row['revision'] != expected_revision: raise ResearchQueueError('RESOURCE_REVISION_CONFLICT')
            if row['state'] not in ('QUEUED', 'RUNNING', 'CANCEL_REQUESTED', 'CANCELED'): raise ResearchQueueError('TERMINAL_JOB_CONFLICT')
            state = 'CANCELED' if row['state'] in ('QUEUED', 'CANCELED') else 'CANCEL_REQUESTED'
            revision = expected_revision+1
            db.execute('UPDATE research_queue_jobs SET cancel_requested=1,state=?,revision=?,updated_at=? WHERE run_id=?', (state, revision, now, run_id))
            row = db.execute('SELECT * FROM research_queue_jobs WHERE run_id=?', (run_id,)).fetchone(); self._event(db, row, now)
            receipt = dict(run_id=run_id, status=state, revision=revision, observed_at=now)
            db.execute('INSERT INTO research_queue_commands VALUES(?,?,?)', (command_id, request, canonical(receipt)))
            return receipt

    def claim_next(self):
        with self._db() as db:
            now = self.clock(); current = stamp(now); db.execute('BEGIN IMMEDIATE')
            # A canceled crashed worker never restarts computation.
            for row in db.execute("SELECT * FROM research_queue_jobs WHERE state='CANCEL_REQUESTED' AND lease_deadline<=?", (current,)).fetchall():
                db.execute("UPDATE research_queue_jobs SET state='CANCELED',revision=revision+1,updated_at=?,reason_codes_json='[\"RESEARCH_CANCELED\"]' WHERE run_id=?", (current, row['run_id']))
                self._event(db, db.execute('SELECT * FROM research_queue_jobs WHERE run_id=?', (row['run_id'],)).fetchone(), current)
            row = db.execute("SELECT * FROM research_queue_jobs WHERE state='QUEUED' OR (state='RUNNING' AND lease_deadline<=?) ORDER BY created_at,run_id LIMIT 1", (current,)).fetchone()
            if row is None: return None
            if current < row['updated_at']: raise ResearchQueueError('QUEUE_CLOCK_REGRESSION')
            generation = row['generation']+1
            db.execute("UPDATE research_queue_jobs SET state='RUNNING',revision=revision+1,owner_id=?,generation=?,lease_deadline=?,updated_at=? WHERE run_id=?",
                (self.owner_id, generation, stamp(now+timedelta(seconds=300)), current, row['run_id']))
            self._event(db, db.execute('SELECT * FROM research_queue_jobs WHERE run_id=?', (row['run_id'],)).fetchone(), current)
            return ResearchJobClaim(row['run_id'], generation)

    def _owned(self, db, run_id, generation, now):
        row = db.execute('SELECT * FROM research_queue_jobs WHERE run_id=?', (run_id,)).fetchone()
        if row is None or row['owner_id'] != self.owner_id or row['generation'] != generation or row['state'] not in ('RUNNING', 'CANCEL_REQUESTED') or not row['updated_at'] <= now < row['lease_deadline']:
            raise ResearchQueueError('RESEARCH_WORKER_FENCED')
        return row

    def _checkpoint(self, run_id, generation, owner_run_id, stage):
        if self.stage_observer is not None: self.stage_observer(owner_run_id, stage)
        with self._db() as db:
            now = self.clock(); current = stamp(now); db.execute('BEGIN IMMEDIATE')
            row = self._owned(db, run_id, generation, current)
            if row['cancel_requested']: raise ResearchCanceled()
            if row['owner_run_id'] is not None and row['owner_run_id'] != owner_run_id: raise ResearchQueueError('OWNER_RUN_IDENTITY_CONFLICT')
            db.execute('UPDATE research_queue_jobs SET owner_run_id=?,stage=?,lease_deadline=?,updated_at=? WHERE run_id=?',
                (owner_run_id, stage, stamp(now+timedelta(seconds=300)), current, run_id))

    def _finish(self, run_id, generation, state, *, outcome=None, reason_codes=()):
        with self._db() as db:
            now = stamp(self.clock()); db.execute('BEGIN IMMEDIATE'); self._owned(db, run_id, generation, now)
            db.execute('UPDATE research_queue_jobs SET state=?,revision=revision+1,updated_at=?,outcome_json=?,reason_codes_json=? WHERE run_id=?',
                (state, now, None if outcome is None else canonical(outcome), canonical(list(reason_codes)), run_id))
            self._event(db, db.execute('SELECT * FROM research_queue_jobs WHERE run_id=?', (run_id,)).fetchone(), now)
        return self.get(run_id)

    def step(self, run_id, lease_generation):
        safe_component(run_id); _revision_int(lease_generation)
        with self._db() as db:
            row = self._owned(db, run_id, lease_generation, stamp(self.clock())); original = json.loads(row['input_json'])
            if digest(row['input_json'].encode()) != row['input_hash']: raise ResearchQueueError('QUEUE_INPUT_CORRUPT')
        try:
            if row['cancel_requested']: raise ResearchCanceled()
            selected = self._resolve(row['submission_id'], row['policy_id'])
            if selected != original['selected'] or _revision() != original['implementation_hash']:
                return self._finish(run_id, lease_generation, 'BLOCKED', reason_codes=('QUEUED_SELECTION_CHANGED',))
            with self.service_factory() as owner:
                if not isinstance(owner, ResearchService) or owner.namespace != self.namespace:
                    raise ResearchQueueError('ACTUAL_SAME_NAMESPACE_RESEARCH_OWNER_REQUIRED')
                owner.orchestrator.checkpoint = lambda owner_run_id, stage: self._checkpoint(run_id, lease_generation, owner_run_id, stage)
                result = owner.run(**selected['arguments'])
            return self._finish(run_id, lease_generation, 'COMPLETE', outcome=asdict(result))
        except ResearchCanceled:
            return self._finish(run_id, lease_generation, 'CANCELED', reason_codes=('RESEARCH_CANCELED',))
        except ResearchQueueError as error:
            if error.code=='RESEARCH_WORKER_FENCED': raise
            return self._finish(run_id,lease_generation,'BLOCKED',reason_codes=(error.code,))
        except Exception as error:
            import re
            reason = getattr(error, 'code', type(error).__name__)
            if not isinstance(reason, str) or not re.fullmatch('[A-Za-z_]{1,64}', reason): reason = 'RESEARCH_OWNER_FAILED'
            return self._finish(run_id, lease_generation, 'FAILED', reason_codes=(reason,))

    def finish_terminated_worker(self, claim, owned):
        """Observed owned process death may fail its exact job, never another lease.

        The expired lease is not renewed. Existing sealed observations/owner
        results remain intact. Only the app dispatch ledger receives disposition.
        """
        from application.platform.processes import OwnedProcess
        if not isinstance(claim, ResearchJobClaim) or not isinstance(owned, OwnedProcess):
            raise ResearchQueueError('ACTUAL_OWNED_RESEARCH_PROCESS_REQUIRED')
        report = owned.termination_report
        if report is None or not report.reaped or owned.process.poll() is None:
            raise ResearchQueueError('OWNED_RESEARCH_PROCESS_NOT_REAPED')
        with self._db() as db:
            now = stamp(self.clock()); db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM research_queue_jobs WHERE run_id=?', (claim.run_id,)).fetchone()
            if row is None or row['owner_id'] != self.owner_id or row['generation'] != claim.generation:
                raise ResearchQueueError('RESEARCH_WORKER_FENCED')
            if row['state'] in ('COMPLETE', 'BLOCKED', 'FAILED', 'CANCELED'):
                return self.get(claim.run_id)
            if row['state'] not in ('RUNNING', 'CANCEL_REQUESTED'):
                raise ResearchQueueError('RESEARCH_WORKER_FENCED')
            if now < row['updated_at']: raise ResearchQueueError('QUEUE_CLOCK_REGRESSION')
            canceled = bool(row['cancel_requested'])
            reason = 'RESEARCH_CANCELED' if canceled else 'OWNED_WORKER_TIMEOUT' if report.reason == 'TIMEOUT' else 'OWNED_WORKER_EXITED_WITHOUT_RESULT'
            state = 'CANCELED' if canceled else 'FAILED'
            db.execute('UPDATE research_queue_jobs SET state=?,revision=revision+1,updated_at=?,reason_codes_json=? WHERE run_id=?',
                (state, now, canonical([reason]), claim.run_id))
            self._event(db, db.execute('SELECT * FROM research_queue_jobs WHERE run_id=?', (claim.run_id,)).fetchone(), now)
        return self.get(claim.run_id)
