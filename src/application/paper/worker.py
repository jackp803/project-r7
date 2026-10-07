"""Independent local PAPER owner; qualification and release admission stay external.

The trusted factory opens actual owner connections on the calling owner thread.
Only immutable market events cross threads. No acquisition/network/research work
runs in this loop, and a process heartbeat never grants financial permission.
"""
from contextlib import ExitStack
import json
import threading

from application.config import ProductConfig
from application.platform.shutdown import ManagedStop
from application.platform.supervision import ProcessSupervisor
from application.platform.restoration import require_valid_restoration
from registry import EvidenceGateError
from storage.runtime_models import RuntimeConflictError
from .scheduler import PaperScheduler
from .service import PaperService, PaperMarketEvent, PaperMarketEventError


class PaperWorkerError(RuntimeError):
    pass


class PaperOwnerWorker:
    def __init__(self, config, service_factory, *, namespace, config_path=None,
                 maximum_active_runs=200, maximum_pending_events=32):
        if (not isinstance(config, ProductConfig) or not callable(service_factory)
                or namespace not in ('FIXTURE', 'LOCAL_RESEARCH')):
            raise ValueError('Actual configured PAPER service factory required')
        if (type(maximum_active_runs) is not int or not 1 <= maximum_active_runs <= 200
                or type(maximum_pending_events) is not int or not 1 <= maximum_pending_events <= 256):
            raise ValueError('Bounded PAPER owner capacity required')
        self.config, self.factory, self.namespace = config, service_factory, namespace
        self.config_path = config_path
        self.maximum_active_runs = maximum_active_runs
        self.maximum_pending_events = maximum_pending_events
        self.supervisor = None
        self.service = None
        self._stack = None
        self._thread_id = None
        self._used = False
        self._active = False
        self._lock = threading.Lock()
        self._schedulers = {}
        self._failures = {}
        self._discovery_offset = 0
        self._discovery_status = 'NOT_STARTED'
        self._capacity_exceeded = False
        self._sweep_capacity_exceeded = False
        self._inventory_exceeded = False
        self._restoration = None

    def __enter__(self):
        if self._used:
            raise PaperWorkerError('FRESH_PAPER_OWNER_REQUIRED')
        self._used = True
        self._thread_id = threading.get_ident()
        stack = ExitStack()
        try:
            # Scope is acquired before factory side effects or E6 attachment.
            self.supervisor = stack.enter_context(ProcessSupervisor(self.config, 'runtime', config_path=self.config_path))
            self.service = stack.enter_context(self.factory())
            if (not isinstance(self.service, PaperService) or self.service.namespace != self.namespace
                    or self.service.registry.research_namespace != self.namespace):
                raise PaperWorkerError('ACTUAL_SAME_NAMESPACE_PAPER_OWNER_REQUIRED')
            self.supervisor.require_current()
            self._restoration = require_valid_restoration(self.config)
        except BaseException:
            import sys
            stack.__exit__(*sys.exc_info())
            raise
        self._stack = stack
        with self._lock:
            self._active = True
        return self

    def _require_owner(self):
        if threading.get_ident() != self._thread_id:
            raise PaperWorkerError('PAPER_OWNER_THREAD_REQUIRED')
        if not self._active:
            raise PaperWorkerError('PAPER_OWNER_NOT_RUNNING')
        self.supervisor.require_current()

    def submit_event(self, run_id, event):
        """Acquisition producer port: bounded queue only, no SQLite or I/O."""
        if not isinstance(event, PaperMarketEvent):
            raise ValueError('Actual immutable E1 event required')
        expected = 'FIXTURE' if self.namespace == 'FIXTURE' else 'PUBLIC_MARKET'
        if event.source_kind != expected:
            raise PaperWorkerError('PAPER_MARKET_NAMESPACE_CONFLICT')
        with self._lock:
            if not self._active:
                raise PaperWorkerError('PAPER_OWNER_NOT_RUNNING')
            scheduler = self._schedulers.get(run_id)
            if scheduler is None:
                raise PaperWorkerError('PAPER_RUN_NOT_ATTACHED')
            return scheduler.submit_event(event)

    def _discover(self):
        # One bounded page per tick; repeated sweeps find starts made by the API
        # without a second owner or a long read transaction. Historical PAPER
        # transitions remain included after retirement/READY so open management
        # is never dropped merely because lifecycle state advanced.
        if self._discovery_offset == 0:
            self._sweep_capacity_exceeded = False
        records = self.service.registry.list_accepted_paper_starts(limit=50, offset=self._discovery_offset)
        self._discovery_status = 'PAGE_SCANNED'
        attached = []
        for record in records:
            self.supervisor.require_current()
            proof = json.loads(record.payload_json)
            run_id = proof['run_id']
            if run_id in self._schedulers:
                continue
            try:
                if self.service.is_quiescent(run_id):
                    self._failures.pop(run_id, None)
                    continue
                if len(self._schedulers) >= self.maximum_active_runs:
                    self._sweep_capacity_exceeded = self._capacity_exceeded = True
                    continue
                runtime = self.service.runtime(run_id)
            except (EvidenceGateError, RuntimeConflictError):
                # Existing owners still receive deadline management. The exact
                # owning runtime must reconcile before this run can attach.
                self._failures[run_id] = 'RUN_ATTACHMENT_RECONCILIATION_REQUIRED'
                continue
            scheduler = PaperScheduler(runtime, maximum_pending_events=self.maximum_pending_events)
            with self._lock:
                self._schedulers[run_id] = scheduler
            self._failures.pop(run_id, None)
            attached.append(run_id)
        if len(records) < 50:
            self._discovery_offset = 0
            self._capacity_exceeded = self._sweep_capacity_exceeded
        else:
            self._discovery_offset += 50
        if self._discovery_offset > 100000:
            self._discovery_offset = 0
            self._inventory_exceeded = True
        if self._inventory_exceeded:
            self._discovery_status = 'INVENTORY_LIMIT_EXCEEDED'
        elif self._capacity_exceeded:
            self._discovery_status = 'CAPACITY_EXCEEDED'
        # Bound diagnostic retention even for an arbitrarily large history.
        while len(self._failures) > self.maximum_active_runs:
            del self._failures[next(iter(self._failures))]
        return attached

    def _tick_run(self, run_id, outcomes):
        self.supervisor.require_current()
        try:
            if self._restoration['status'] == 'RESTORED_INHIBITED' and not self.service.process.entry_pause_requested(run_id):
                try:
                    self.service.process.request_entry_pause(run_id,
                        'restore-pause:'+self._restoration['restore_generation_id']+':'+run_id,
                        actor=self.service.actor, expected_revision=self.service.process.control_revision(run_id),
                        now=self.service.clock())
                except RuntimeConflictError:
                    # An API pause can win the same CAS. Continue protection
                    # only after re-reading the actual durable entry-deny flag.
                    if not self.service.process.entry_pause_requested(run_id):
                        raise
            outcomes[run_id] = self._schedulers[run_id].tick()
        except PaperMarketEventError:
            self._failures[run_id] = 'MARKET_EVENT_REJECTED'
            self._schedulers[run_id].acquisition_status = 'MARKET_EVENT_REJECTED'
        except (EvidenceGateError, RuntimeConflictError):
            self._failures[run_id] = 'RUN_MANAGEMENT_RECONCILIATION_REQUIRED'
        else:
            self._failures.pop(run_id, None)

    def tick(self):
        self._require_owner()
        self._restoration = require_valid_restoration(self.config)
        outcomes = {}
        # Manage already attached protection before scanning new accepted starts.
        for run_id in tuple(self._schedulers):
            self._tick_run(run_id, outcomes)
            try:
                if self.service.is_quiescent(run_id):
                    self.service.release_quiescent_runtime(run_id)
                    with self._lock:
                        del self._schedulers[run_id]
                    self._failures.pop(run_id, None)
            except (EvidenceGateError, RuntimeConflictError):
                self._failures[run_id] = 'RUN_MANAGEMENT_RECONCILIATION_REQUIRED'
        for run_id in self._discover():
            self._tick_run(run_id, outcomes)
        self.supervisor.require_current()
        return outcomes

    def snapshot(self):
        self._require_owner()
        with self._lock:
            runs = tuple(self._schedulers)
            acquisition = {key: dict(status=value.acquisition_status, pending_events=value.pending_events)
                           for key, value in self._schedulers.items()}
        return dict(status='DEGRADED' if self._failures or self._discovery_status in
            ('CAPACITY_EXCEEDED', 'INVENTORY_LIMIT_EXCEEDED') else 'RUNNING',
            active_runs=runs, run_failures=dict(self._failures), acquisition=acquisition,
            discovery_status=self._discovery_status, discovery_offset=self._discovery_offset,
            process_generation=self.supervisor.identity['generation'],
            process_generation_id=self.supervisor.identity['process_generation_id'],
            restoration=dict(self._restoration), financial_authority='NONE', exposure_status='NOT_AGGREGATED')

    def run(self, stop=None):
        self._require_owner()
        if stop is None:
            with ManagedStop() as managed:
                return self.run(managed)
        if not isinstance(stop, ManagedStop):
            raise ValueError('Explicit cooperative ManagedStop required')
        while not stop.requested:
            self.tick()
            wait = min([1.0] + [scheduler.next_wait_seconds() for scheduler in self._schedulers.values()])
            if any(scheduler.pending_events for scheduler in self._schedulers.values()):
                wait = .001
            stop.wait(wait)

    def __exit__(self, *exception):
        if threading.get_ident() != self._thread_id:
            raise PaperWorkerError('PAPER_OWNER_THREAD_REQUIRED')
        with self._lock:
            self._active = False
        # Closing journals does not claim flatness, clear protection or erase
        # accepted start/control facts. A successor must use actual E6 recovery.
        if self._stack is not None:
            stack, self._stack = self._stack, None
            return stack.__exit__(*exception)
