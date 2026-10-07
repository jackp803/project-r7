"""Separate owned research jobs; API/control never perform heavy owner replay."""
import os
import json
from pathlib import Path
import subprocess
import sys

from application.config import load_config
from application.local_owners import LocalOwners
from application.platform.processes import ResourceLimits, spawn_owned, terminate_owned
from application.platform.resources import ResourcePolicy, inspect_hardware
from application.platform.supervision import ProcessSupervisor, config_hash
from application.platform.shutdown import ManagedStop


def _job_argv(config_path, run_id, generation, *, expected_config_hash=None):
    prefix = [sys.executable] if getattr(sys, 'frozen', False) else [sys.executable, '-m', 'application']
    argv = [*prefix, '_research-job', '--config', str(config_path), '--run-id', run_id, '--generation', str(generation)]
    if expected_config_hash is not None:
        argv += ['--expected-config-hash', expected_config_hash]
    return argv


def run_research_job(config_path, run_id, generation, *, expected_config_hash=None):
    config = load_config(config_path)
    if expected_config_hash is not None and config_hash(config) != expected_config_hash:
        raise ValueError('Research child configuration changed before owner composition')
    owners = LocalOwners(config)
    if owners.queue is None: raise ValueError('Research selections are not configured')
    result = owners.queue.step(run_id, generation)
    return dict(status=result['state'], run_id=run_id, generation=generation)


def worker_once(config_path, *, namespace='LOCAL_RESEARCH', job_argv_factory=None,
                hardware_probe=inspect_hardware, job_timeout_seconds=900, stop=None):
    if namespace not in ('LOCAL_RESEARCH', 'FIXTURE') or (job_argv_factory is not None and namespace != 'FIXTURE'):
        raise ValueError('Executable overrides are limited to explicit fixture verification')
    limits = ResourceLimits(job_timeout_seconds)
    config_path = Path(config_path).absolute()
    config = load_config(config_path)
    stop=ManagedStop() if stop is None else stop
    if not isinstance(stop,ManagedStop):raise ValueError('Actual managed stop scope required')
    with stop, ProcessSupervisor(config, 'research', config_path=config_path) as supervisor:
        return _worker_once(config_path, config, namespace=namespace, job_argv_factory=job_argv_factory,
                            hardware_probe=hardware_probe, limits=limits, supervisor=supervisor,stop=stop)


def _worker_once(config_path, config, *, namespace, job_argv_factory, hardware_probe, limits, supervisor,stop):
    supervisor.require_current()
    if stop.requested:return dict(status='STOPPED',run_id=None,reason_codes=['SERVICE_STOP_REQUESTED'])
    hardware = hardware_probe(config.local_data_root)
    policy = ResourcePolicy.conservative(hardware.physical_memory_bytes)
    admission = policy.admission(available_memory_bytes=hardware.available_memory_bytes,
        disk_free_bytes=hardware.disk_free_bytes, disk_total_bytes=hardware.disk_total_bytes)
    if not admission.allowed:
        return dict(status='PAUSED_RESOURCE', run_id=None, reason_codes=list(admission.reason_codes),
                    memory_enforcement=policy.memory_enforcement)
    if stop.requested:return dict(status='STOPPED',run_id=None,reason_codes=['SERVICE_STOP_REQUESTED'])
    owners = LocalOwners(config, namespace=namespace)
    if owners.queue is None:
        return dict(status='NOT_CONFIGURED', run_id=None, reason_codes=['RESEARCH_SELECTIONS_NOT_CONFIGURED'])
    if stop.requested:return dict(status='STOPPED',run_id=None,reason_codes=['SERVICE_STOP_REQUESTED'])
    claim = owners.queue.claim_next()
    if claim is None: return dict(status='IDLE', run_id=None, reason_codes=[])
    argv = (job_argv_factory(config_path, claim.run_id, claim.generation) if job_argv_factory is not None
            else _job_argv(config_path, claim.run_id, claim.generation, expected_config_hash=config_hash(config)))
    log_dir = config.local_data_root / 'worker-logs'
    log_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    log = log_dir / (claim.run_id + '-' + str(claim.generation) + '.log')
    with log.open('xb') as stream:
        owned = spawn_owned(argv, cwd=Path.cwd(), limits=limits, stdout=stream, stderr=subprocess.STDOUT)
        interrupted=False
        try:
            while True:
                supervisor.require_current()
                if stop.requested:
                    interrupted=True
                    break
                try:
                    code = owned.wait(timeout=0.2)
                    break
                except subprocess.TimeoutExpired:
                    pass
        finally:
            terminate_owned(owned, deadline_seconds=5)
            result = owners.queue.finish_terminated_worker(claim, owned,stop_requested=interrupted)
    code=owned.process.returncode
    return dict(status='JOB_STOPPED' if interrupted else 'JOB_FINISHED' if code == 0 and result['state'] != 'FAILED' else 'JOB_TERMINATED', run_id=claim.run_id,
        generation=claim.generation, job_state=result['state'], parent_pid=os.getpid(), child_pid=owned.process.pid,
        exit_code=code, tree_reaped=owned.termination_report.reaped, memory_enforcement=policy.memory_enforcement,
        log_ref='worker-logs/' + log.name, reason_codes=result['reason_codes'])


def research_worker(config_path, *, once=False, expected_config_hash=None):
    config_path = Path(config_path).absolute()
    config = load_config(config_path)
    if expected_config_hash is not None and config_hash(config) != expected_config_hash:
        raise ValueError('Research service configuration changed before supervision')
    with ManagedStop() as stop, ProcessSupervisor(config, 'research', config_path=config_path) as supervisor:
        while not stop.requested:
            result = _worker_once(config_path, config, namespace='LOCAL_RESEARCH', job_argv_factory=None,
                                  hardware_probe=inspect_hardware, limits=ResourceLimits(900), supervisor=supervisor,stop=stop)
            print(json.dumps(result), flush=True)
            if once: return 0 if result['status'] != 'JOB_TERMINATED' else 2
            stop.wait(5)
    return 0
