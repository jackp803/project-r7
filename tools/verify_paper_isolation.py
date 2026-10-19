"""Actual bounded Windows research-fault/Paper isolation slice, not PQR-05 PASS.

Only owned native jobs are measured. Sampled finite concurrency does not prove
maximum load, hard memory enforcement, timing conformance or a 24 GiB host.
"""
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
import ctypes
import json
import os
import secrets
import subprocess
import time

import verify_paper_product as product
from verify_paper_faults import NativeFixtureFaultFlow, NativeFixtureCleanupError
from application.config import load_config
from application.platform.processes import ResourceLimits, spawn_owned, terminate_owned
from application.platform.resources import inspect_hardware, ResourcePolicy
from application.platform.supervision import process_health
from brokers.paper import PaperBroker
from brokers.paper_state import decode_fact
from execution.models import OrderRequest, OrderStatus

MAX_SAMPLES = 128
MAX_JOB_PROCESSES = 64
SAMPLE_SECONDS = .2
OBSERVATION_SECONDS = 20
TERMINAL_GRACE_SECONDS = 6
METRIC_KEYS = {'pid', 'parent_pid', 'created_100ns', 'rss_bytes', 'private_bytes',
               'kernel_cpu_100ns', 'user_cpu_100ns', 'priority_class'}


class NativeIsolationCleanupError(NativeFixtureCleanupError):
    pass


class MeasurementProcessExited(ValueError):
    """A real owned PID exited; this is not a successful resource sample."""


def is_expected_research_stop(health, identity):
    return (isinstance(health, dict) and isinstance(identity, dict) and health.get('state') == 'STOPPED'
            and all(health.get(key) == identity[key] for key in
                    ('pid', 'generation', 'process_generation_id', 'config_hash')))


class WindowsOwnedProcessSampler:
    def __init__(self):
        if os.name != 'nt':
            raise ValueError('Actual Windows owned-process measurement required')
        from ctypes import wintypes as w
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.ntdll = ctypes.WinDLL('ntdll')
        declarations = {
            'OpenProcess': ([w.DWORD, w.BOOL, w.DWORD], w.HANDLE),
            'CloseHandle': ([w.HANDLE], w.BOOL),
            'IsProcessInJob': ([w.HANDLE, w.HANDLE, ctypes.POINTER(w.BOOL)], w.BOOL),
            'GetProcessTimes': ([w.HANDLE, ctypes.POINTER(w.FILETIME), ctypes.POINTER(w.FILETIME),
                                 ctypes.POINTER(w.FILETIME), ctypes.POINTER(w.FILETIME)], w.BOOL),
            'GetPriorityClass': ([w.HANDLE], w.DWORD),
            'WaitForSingleObject': ([w.HANDLE, w.DWORD], w.DWORD),
            'K32GetProcessMemoryInfo': ([w.HANDLE, ctypes.c_void_p, w.DWORD], w.BOOL),
        }
        for name, (arguments, result) in declarations.items():
            function = getattr(self.kernel, name)
            function.argtypes, function.restype = arguments, result
        self.ntdll.NtQueryInformationProcess.argtypes = [w.HANDLE, w.ULONG, ctypes.c_void_p,
                                                        w.ULONG, ctypes.POINTER(w.ULONG)]
        self.ntdll.NtQueryInformationProcess.restype = w.LONG

    def _job_pids(self, owned):
        from ctypes import wintypes as w
        if owned._job is None:
            raise ValueError('Live private Windows job required for measurement')
        class Pids(ctypes.Structure):
            _fields_ = [('assigned', w.DWORD), ('listed', w.DWORD),
                        ('pids', ctypes.c_size_t * MAX_JOB_PROCESSES)]
        value = Pids()
        if not owned._job.kernel.QueryInformationJobObject(owned._job.handle, 3, ctypes.byref(value),
                                                          ctypes.sizeof(value), None):
            raise ValueError('Complete bounded native job inventory unavailable')
        if value.assigned == value.listed == 0 and owned.process.poll() is not None:
            raise MeasurementProcessExited('Owned job exited before resource sample')
        if not 1 <= value.assigned == value.listed <= MAX_JOB_PROCESSES:
            raise ValueError('Incomplete bounded native job inventory')
        pids = tuple(sorted(int(pid) for pid in value.pids[:value.listed]))
        if len(set(pids)) != len(pids) or any(pid <= 0 for pid in pids):
            raise ValueError('Exact native owned PID inventory required')
        return pids

    def _read_process(self, owned, pid):
        from ctypes import wintypes as w
        class Memory(ctypes.Structure):
            _fields_ = [('cb', w.DWORD), ('PageFaultCount', w.DWORD)] + [
                (name, ctypes.c_size_t) for name in ('PeakWorkingSetSize', 'WorkingSetSize',
                'QuotaPeakPagedPoolUsage', 'QuotaPagedPoolUsage', 'QuotaPeakNonPagedPoolUsage',
                'QuotaNonPagedPoolUsage', 'PagefileUsage', 'PeakPagefileUsage', 'PrivateUsage')]
        class Basic(ctypes.Structure):
            _fields_ = [('ExitStatus', w.LONG), ('PebBaseAddress', ctypes.c_void_p),
                        ('AffinityMask', ctypes.c_size_t), ('BasePriority', w.LONG),
                        ('UniqueProcessId', ctypes.c_size_t), ('InheritedFromUniqueProcessId', ctypes.c_size_t)]
        handle = self.kernel.OpenProcess(0x100410, False, pid)  # SYNCHRONIZE|QUERY_INFORMATION|VM_READ
        if not handle:
            if ctypes.get_last_error() in (87, 1168):
                raise MeasurementProcessExited('Owned PID exited before resource sample')
            raise ValueError('Owned process vanished or could not be measured')
        try:
            inside = w.BOOL()
            if (not self.kernel.IsProcessInJob(handle, owned._job.handle, ctypes.byref(inside))
                    or not inside.value):
                raise ValueError('Stable live owned process handle required')
            def require_live():
                state = self.kernel.WaitForSingleObject(handle, 0)
                if state == 0:
                    raise MeasurementProcessExited('Owned process exited during resource sample')
                if state != 258:
                    raise ValueError('Owned process liveness could not be measured')
            require_live()
            basic, returned = Basic(), w.ULONG()
            if self.ntdll.NtQueryInformationProcess(handle, 0, ctypes.byref(basic), ctypes.sizeof(basic),
                                                    ctypes.byref(returned)) != 0 or basic.UniqueProcessId != pid:
                require_live()
                raise ValueError('Actual owned process ancestry unavailable')
            memory = Memory(); memory.cb = ctypes.sizeof(memory)
            created, exited, kernel, user = (w.FILETIME() for _ in range(4))
            if (not self.kernel.K32GetProcessMemoryInfo(handle, ctypes.byref(memory), ctypes.sizeof(memory))
                    or not self.kernel.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited),
                                                      ctypes.byref(kernel), ctypes.byref(user))):
                require_live()
                raise ValueError('Actual owned memory/CPU counters unavailable')
            priority = self.kernel.GetPriorityClass(handle)
            require_live()
            if not priority:
                raise ValueError('Actual owned process priority unavailable')
            ticks = lambda value: (value.dwHighDateTime << 32) | value.dwLowDateTime
            return dict(pid=pid, parent_pid=int(basic.InheritedFromUniqueProcessId),
                        created_100ns=ticks(created), rss_bytes=int(memory.WorkingSetSize),
                        private_bytes=int(memory.PrivateUsage), kernel_cpu_100ns=ticks(kernel),
                        user_cpu_100ns=ticks(user), priority_class=int(priority))
        finally:
            self.kernel.CloseHandle(handle)

    def sample_owned(self, owned):
        pids = self._job_pids(owned)
        rows = [self._read_process(owned, pid) for pid in pids]
        if (len(rows) != len(pids) or any(set(row) != METRIC_KEYS
                or any(type(value) is not int or value < 0 for value in row.values())
                or row['pid'] != pid or row['rss_bytes'] <= 0 or row['created_100ns'] <= 0
                or row['priority_class'] <= 0 for pid, row in zip(pids, rows))):
            raise ValueError('Complete actual process metrics required; no synthetic zeros')
        return rows


def require_timeout(result, *, run_id, process_exit_code):
    if (not isinstance(result, dict) or result.get('status') != 'JOB_TERMINATED'
            or result.get('run_id') != run_id or result.get('job_state') != 'FAILED'
            or result.get('reason_codes') != ['OWNED_WORKER_TIMEOUT']
            or result.get('tree_reaped') is not True or process_exit_code != 2
            or result.get('memory_enforcement') != 'SOFT_LIMIT_ONLY'
            or any(type(result.get(key)) is not int or result[key] <= 0 for key in ('parent_pid', 'child_pid'))
            or result['parent_pid'] == result['child_pid']
            or type(result.get('exit_code')) is not int or result['exit_code'] == 0):
        raise ValueError('Actual fixed native research timeout and disposed exact claim required')


def require_research_target(samples, result):
    targets = set()
    for sample in samples:
        rows = {row['pid']: row for row in sample['processes']['research']}
        bootstrap = rows.get(result['child_pid'])
        if (result['parent_pid'] in rows and bootstrap is not None
                and bootstrap['parent_pid'] == result['parent_pid']):
            targets.update(row['pid'] for row in rows.values() if row['parent_pid'] == result['child_pid'])
    if not targets:
        raise ValueError('Actual research target descendant not measured; bootstrap is not target')
    return sorted(targets)


def progress_report(samples, *, selected_deadline_seconds):
    if type(selected_deadline_seconds) is not int or selected_deadline_seconds <= 0 or len(samples) < 3:
        raise ValueError('Actual before/during/after protection observations required')
    revisions, broker = [samples[0]], [samples[0]]
    for previous, current in zip(samples, samples[1:]):
        if (current['monotonic_ns'] <= previous['monotonic_ns']
                or current['checkpoint_revision'] < previous['checkpoint_revision']
                or datetime.fromisoformat(current['broker_observed_at'].replace('Z', '+00:00')) <
                    datetime.fromisoformat(previous['broker_observed_at'].replace('Z', '+00:00'))):
            raise ValueError('Actual owner progress regressed')
        if current['checkpoint_revision'] > revisions[-1]['checkpoint_revision']:
            revisions.append(current)
        if current['broker_observed_at'] != broker[-1]['broker_observed_at']:
            broker.append(current)
    if len(revisions) < 3 or len(broker) < 3:
        raise ValueError('Two advancing actual checkpoint/broker observations required')
    gap = lambda rows: max((b['monotonic_ns'] - a['monotonic_ns']) / 1e9 for a, b in zip(rows, rows[1:]))
    checkpoint_gap, broker_gap = gap(revisions), gap(broker)
    return dict(selected_protection_poll_seconds=selected_deadline_seconds,
                max_observed_checkpoint_gap_seconds=checkpoint_gap,
                max_observed_position_broker_gap_seconds=broker_gap,
                observed_gap_exceeds_selected_interval=max(checkpoint_gap, broker_gap) > selected_deadline_seconds,
                deadline_conformance='NOT_ESTABLISHED_BY_SAMPLED_FIXTURE',
                observation_clock='ACTUAL_MONOTONIC_NS', broker_clock='SYNTHETIC_FIXTURE_UTC',
                broker_advances=len(broker) - 1, checkpoint_advances=len(revisions) - 1)


class NativeResearchIsolationFlow(NativeFixtureFaultFlow):
    def __init__(self, package, output, *, expected_identity=None):
        super().__init__(package, output, 'hold-for-recovery', expected_identity=expected_identity)
        self.research_child = self.research_stream = None
        self.observation.update(case='research-isolation', scope='ACTUAL_WINDOWS_FINITE_CONCURRENCY_SLICE',
                                full_pqr05='NOT_QUALIFIED')

    def input_commitments(self):
        return {name: product.sha(product.read_local(self.data, 'fixture-inputs/' + name + '.json', 65536))
                for name in ('dataset', 'split', 'cost', 'research', 'robustness', 'risk', 'simulation',
                             'promotion', 'selection', 'paper-selection', 'paper-case')}

    def prepare_research_submission(self):
        original_receipt = self.submission()['receipt']
        original_inputs = self.input_commitments()
        source = 'inbox/strategies/' + self.generated['submission_id'] + '/strategy.json'
        definition = json.loads(product.read_local(self.cloud, source, 262144))
        definition.update(strategy_id='r7-native-isolation-research', name='SYNTHETIC FIXTURE isolation research')
        path = self.output / 'research-definition.json'
        product.write_private_new(path, product.canonical(definition).encode())
        submission = 'r7-native-isolation-second-input'
        result = self.command('author-second-research', ['author-package', '--definition', path,
            '--destination', self.cloud / 'inbox/strategies' / submission, '--submission-id', submission,
            '--dataset-profile', 'synthetic-fixture', '--validation-profile', 'synthetic-fixture',
            '--robustness-profile', 'synthetic-fixture'])
        if result.get('execution_evidence') != 'NOT_RUN' or result.get('status') != 'AUTHORING_PACKAGE_CREATED':
            raise ValueError('Fresh actual native unexecuted second author input required')
        _, _, summary = self.scan()
        if summary.get('accepted') != 1:
            raise ValueError('Actual second submission intake required')
        row = self.view('submissions/' + submission)['payload']
        receipt = self.request('POST', '/api/v1/research/runs', dict(command_id='enqueue-' + secrets.token_hex(12),
            expected_revision=row['revision'], submission_id=submission, policy_id=self.generated['policy_id']), expected=202)
        if (receipt.get('status') != 'QUEUED' or self.submission()['receipt'] != original_receipt
                or self.input_commitments() != original_inputs):
            raise ValueError('Second research modified original sealed recipe or receipt')
        self.original_inputs, self.original_receipt = original_inputs, original_receipt
        self.observation.update(second_submission_id=submission, original_sealed_inputs_preserved=True,
                                original_input_hashes=original_inputs,
                                original_intake_receipt_hash=product.sha(product.canonical(original_receipt).encode()),
                                second_definition_hash=product.sha(product.canonical(definition).encode()))
        return receipt['effect_ref'].removeprefix('research-job:')

    def observe_paper(self, before, identity):
        self.require_api_control()
        actual = self.health('runtime', self.runtime_child)
        if any(actual[key] != identity[key] for key in ('pid', 'generation', 'process_generation_id', 'config_hash')):
            raise ValueError('Research fault changed actual native Paper supervisor')
        current = self.journal(self.paper_run)
        self.require_original(before, current)
        runtime = current.state['runtime']; position = runtime['position']
        if (current.process_generation != before.process_generation or position['lifecycle_state'] != 'OPEN_PROTECTED'
                or Decimal(position['actual_quantity']) <= 0 or runtime['paper_entries_allowed'] is not False):
            raise ValueError('Original positive paused protected Paper owner must continue')
        request = decode_fact(OrderRequest, runtime['protection_request'])
        order = PaperBroker.from_state(current.state['broker']).query_order(request.client_order_id)
        if order is None or order.order_status != OrderStatus.OPEN:
            raise ValueError('Original standing broker protection not observed')
        return dict(monotonic_ns=time.monotonic_ns(), actual_at=datetime.now(timezone.utc).isoformat(),
            checkpoint_revision=current.revision, broker_observed_at=position['broker_state_observed_at'],
            protection_order_observed_at=order.observed_at.isoformat(), protection_order_status=order.order_status.value,
            quantity=position['actual_quantity'], entries_paused=True,
            run_generation=current.process_generation, runtime_identity={key: actual[key] for key in
            ('pid', 'generation', 'process_generation_id', 'config_hash')})

    def start_research(self):
        self.research_log = self.output / 'concurrent-research.log'
        self.research_stream = self.research_log.open('xb')
        self.research_child = spawn_owned([str(self.executable), 'research-worker', '--config', str(self.config),
            '--once', '--job-timeout-seconds', '5'], cwd=self.output, limits=ResourceLimits(25),
            stdout=self.research_stream, stderr=subprocess.STDOUT, env=self.env)

    def cleanup_research(self):
        if self.research_child is None:
            return
        owned = self.research_child
        cleanup = None
        try:
            cleanup = terminate_owned(owned, deadline_seconds=5)
        finally:
            if self.research_stream is not None:
                self.research_stream.close(); self.research_stream = None
        reaped = cleanup is not None and cleanup.reaped
        self.commands.append(dict(command='concurrent-research-cleanup', tree_reaped=reaped))
        self.persist()
        if not reaped:
            raise NativeIsolationCleanupError('Native research cleanup unconfirmed')
        self.research_child = None
        raw = product.read_local(self.output, self.research_log.name, 1024 * 1024).decode('utf-8', errors='replace')
        clean = product._sanitize(raw, product.ROOT).replace(self.password, '<SYNTHETIC_TEST_INPUT>')
        clean = clean.replace(str(self.output), '<PRIVATE_FIXTURE_ROOT>')
        self.research_log.write_text(clean, encoding='utf-8')
        self.commands.append(dict(command='concurrent-research', tree_reaped=True, exit_code=owned.process.returncode,
                                  log=self.research_log.name, log_hash=product.sha(self.research_log.read_bytes())))
        self.persist()

    def cleanup_control(self):
        if self.control is None:
            return
        owned = self.control; managed = False; cleanup = None
        try:
            self.command('stop-isolation-' + self.control_log.stem,
                         ['stop-product', '--config', self.config, '--role', 'control'], timeout=30)
            managed = owned.wait(timeout=10) == 0 and process_health(load_config(self.config), 'control')['state'] == 'STOPPED'
            if not managed:
                raise ValueError('Actual graceful isolation control stop unconfirmed')
        finally:
            try:
                cleanup = terminate_owned(owned, deadline_seconds=5)
            finally:
                if self.control_stream is not None:
                    self.control_stream.close(); self.control_stream = None
            reaped = cleanup is not None and cleanup.reaped
            self.commands.append(dict(command='isolation-control-cleanup', tree_reaped=reaped, managed_stop=managed))
            self.persist()
            if not reaped:
                raise NativeIsolationCleanupError('Native control cleanup unconfirmed')
            self.control = None
            raw = product.read_local(self.output, self.control_log.name, 1024 * 1024).decode('utf-8', errors='replace')
            clean = product._sanitize(raw, product.ROOT).replace(self.password, '<SYNTHETIC_TEST_INPUT>')
            self.control_log.write_text(clean.replace(str(self.output), '<PRIVATE_FIXTURE_ROOT>'), encoding='utf-8')
            self.commands.append(dict(command=self.control_log.stem, tree_reaped=True, managed_stop=managed,
                log=self.control_log.name, log_hash=product.sha(self.control_log.read_bytes())))
            self.persist()

    def stop_control(self):
        # The inherited setup stops its first control before Paper selection.
        # Keep that stage under the same handle-retaining cleanup policy.
        return self.cleanup_control()

    def cleanup_all(self):
        failures = []
        for operation in (self.cleanup_research, lambda: self.finish_runtime(crash=False), self.cleanup_control):
            try:
                operation()
            except Exception as error:
                failures.append(type(error).__name__)
        if failures:
            self.observation['cleanup_error_types'] = failures
            raise NativeIsolationCleanupError('Isolation owner cleanup incomplete')

    def wait_terminal_research(self, owned, before, identity, paper_samples, *, end):
        # A dying descendant is not a zero-valued metric. Keep managing the
        # observation of Paper while awaiting the finite actual outer result.
        deadline = min(end, time.monotonic() + TERMINAL_GRACE_SECONDS)
        while owned.process.poll() is None:
            if time.monotonic() >= deadline or len(paper_samples) >= MAX_SAMPLES:
                raise ValueError('Research terminal transition was not confirmed within its bound')
            paper_samples.append(self.observe_paper(before, identity))
            self.persist()
            time.sleep(SAMPLE_SECONDS)

    def run_checks(self):
        sampler = WindowsOwnedProcessSampler()  # Unsupported target fails before launching the fixture.
        self.setup()
        research_run = self.prepare_research_submission()
        self.paper_start(); identity = self.start_runtime('isolation-paper')
        self.wait_position('OPEN_PROTECTED', generation=1)
        self.pause()
        before = self.wait_position('OPEN_PROTECTED', generation=1, entries_paused=True)
        baseline = self.observe_paper(before, identity)
        hardware_before = inspect_hardware(self.data)
        policy = ResourcePolicy.conservative(hardware_before.physical_memory_bytes)
        selected = json.loads(product.read_local(self.data, 'fixture-inputs/simulation.json', 65536))
        paper_samples = [baseline]; samples = []; terminal_nonmeasurements = []
        self.observation.update(process_samples=samples, protected_observations=paper_samples,
            terminal_nonmeasurements=terminal_nonmeasurements,
            hardware_before=hardware_before.to_dict(), resource_policy=asdict(policy),
            driver_admission_before=asdict(policy.admission(available_memory_bytes=hardware_before.available_memory_bytes,
                disk_free_bytes=hardware_before.disk_free_bytes, disk_total_bytes=hardware_before.disk_total_bytes)),
            selected_protection_poll_seconds=selected['protection_poll_seconds'],
            runtime_identity=baseline['runtime_identity'], capacity_scope='ONE_PAPER_OWNER_ONE_RESEARCH_JOB_AND_CONTROL',
            memory_enforcement='SOFT_LIMIT_ONLY', maximum_load_qualification='NOT_ESTABLISHED',
            target_24gb_qualification='NOT_ESTABLISHED')
        self.start_research(); owned = self.research_child
        end = time.monotonic() + OBSERVATION_SECONDS
        research_identity = None
        while owned.process.poll() is None:
            if len(samples) >= MAX_SAMPLES or time.monotonic() >= end:
                raise ValueError('Actual finite concurrency observation exceeded its bound')
            observation = self.observe_paper(before, identity)
            paper_samples.append(observation)
            try:
                current_research = self.health('research', owned)
            except ValueError:
                if research_identity is not None:
                    state = process_health(load_config(self.config), 'research')
                    if not is_expected_research_stop(state, research_identity):
                        raise
                    terminal_nonmeasurements.append(dict(monotonic_ns=time.monotonic_ns(),
                        reason='SAME_RESEARCH_SUPERVISOR_STOPPED', counted_as_process_sample=False))
                    self.wait_terminal_research(owned, before, identity, paper_samples, end=end)
                    break
            else:
                projected = {key: current_research[key] for key in ('pid', 'generation', 'process_generation_id', 'config_hash')}
                if research_identity is not None and projected != research_identity:
                    raise ValueError('Actual research supervisor changed during owned job')
                research_identity = projected
            processes = {role: sampler.sample_owned(handle) for role, handle in
                         (('control', self.control), ('runtime', self.runtime_child))}
            try:
                processes['research'] = sampler.sample_owned(owned)
            except MeasurementProcessExited:
                if research_identity is None or not samples:
                    raise
                terminal_nonmeasurements.append(dict(monotonic_ns=time.monotonic_ns(),
                    reason='RESEARCH_OWNED_PROCESS_EXITED_DURING_SAMPLE', counted_as_process_sample=False))
                self.wait_terminal_research(owned, before, identity, paper_samples, end=end)
                break
            pids = [row['pid'] for rows in processes.values() for row in rows]
            if len(pids) != len(set(pids)):
                raise ValueError('One measured process cannot impersonate multiple owner scopes')
            samples.append(dict(monotonic_ns=time.monotonic_ns(), actual_at=datetime.now(timezone.utc).isoformat(),
                                processes=processes, protected_observation=observation))
            self.persist()
            time.sleep(SAMPLE_SECONDS)
        code = owned.wait(timeout=2)
        self.cleanup_research()
        raw = product.read_local(self.output, self.research_log.name, 1024 * 1024)
        lines = [line for line in raw.splitlines() if line.startswith(b'{')]
        if len(lines) != 1:
            raise ValueError('One actual native research owner result required')
        result = json.loads(lines[0]); require_timeout(result, run_id=research_run, process_exit_code=code)
        if research_identity is None or result['parent_pid'] != research_identity['pid']:
            raise ValueError('Actual native research supervisor was not observed')
        targets = require_research_target(samples, result)
        job = self.view('research/runs/' + research_run)['payload']
        if job['state'] != 'FAILED' or job['reason_codes'] != ['OWNED_WORKER_TIMEOUT']:
            raise ValueError('Actual authenticated failed research claim required')
        concurrent = [sample['protected_observation'] for sample in samples
                      if any(row['pid'] in targets for row in sample['processes']['research'])]
        during_max = max((sample['broker_observed_at'] for sample in concurrent), default=baseline['broker_observed_at'])
        if self.utc(during_max) <= self.utc(baseline['broker_observed_at']):
            raise ValueError('No broker progress observed during actual research lifetime')
        while time.monotonic() < end and len(paper_samples) < MAX_SAMPLES:
            after = self.observe_paper(before, identity); paper_samples.append(after)
            if self.utc(after['broker_observed_at']) > self.utc(during_max):
                break
            time.sleep(SAMPLE_SECONDS)
        else:
            raise ValueError('No actual broker progress after research fault')
        progress = progress_report(paper_samples, selected_deadline_seconds=selected['protection_poll_seconds'])
        hardware_after = inspect_hardware(self.data)
        self.observation.update(research_result=result, actual_research_target_pids=targets, progress=progress,
            research_identity=research_identity,
            terminal_nonmeasurement_confirmed_by_actual_timeout=bool(terminal_nonmeasurements),
            actual_target_concurrent_protected_samples=len(concurrent),
            hardware_after=hardware_after.to_dict(), sample_count=len(samples),
            driver_admission_after=asdict(policy.admission(available_memory_bytes=hardware_after.available_memory_bytes,
                disk_free_bytes=hardware_after.disk_free_bytes, disk_total_bytes=hardware_after.disk_total_bytes)),
            sampled_peak_total_rss_bytes=max(sum(row['rss_bytes'] for rows in s['processes'].values() for row in rows) for s in samples),
            sampled_peak_total_private_bytes=max(sum(row['private_bytes'] for rows in s['processes'].values() for row in rows) for s in samples))
        if self.input_commitments() != self.original_inputs or self.submission()['receipt'] != self.original_receipt:
            raise ValueError('Concurrent research modified original sealed owner input')
        self.finish_runtime(crash=False)
        self.finish_trade(self.journal(self.paper_run))
        self.guard()

    def run(self):
        self.observation.update(passed=False, research_fault_protection_isolation=False,
                                host_bounded_capacity_measured=False, full_pqr05='NOT_QUALIFIED')
        try:
            self.run_checks()
        except Exception as error:
            self.observation['error_type'] = type(error).__name__
            raise
        finally:
            try:
                self.cleanup_all()
            finally:
                self.persist()
        self.observation.update(passed=True, research_fault_protection_isolation=True,
                                host_bounded_capacity_measured=True)
        self.persist()
        return self.observation


def verify_slice(package, output, identity):
    flow = NativeResearchIsolationFlow(package, output / 'research-isolation', expected_identity=identity)
    try:
        return [flow.run()]
    except Exception as error:
        flow.observation.update(passed=False, research_fault_protection_isolation=False,
                                host_bounded_capacity_measured=False, error_type=type(error).__name__)
        flow.persist()
        if flow.research_child is not None or flow.runtime_child is not None or flow.control is not None:
            failure = NativeIsolationCleanupError('Native isolation scope cleanup unconfirmed')
            failure.flow = flow  # Retain exact handles for owning cleanup retry; never launch another case.
            raise failure from None
        return [flow.observation]
