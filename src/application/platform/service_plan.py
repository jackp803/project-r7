"""Bounded Ubuntu service configuration rendering, never service acceptance.

These units require guarded native startup, implemented separately from this
pure renderer. Rendering does not establish installation, systemd enforcement,
runtime composition, provider capability or financial authorization.
"""
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import PurePosixPath
import re

from application.platform.resources import GIB, ResourcePolicy
from application.platform.scope_lock import POSIX_SCOPE_ROOT


@dataclass(frozen=True)
class ServiceSettings:
    binary_root: str
    config_path: str
    data_root: str
    cloud_root: str | None
    service_user: str
    executable_revision: str
    build_hash: str
    config_hash: str
    physical_memory_bytes: int


def _linux_path(value):
    if (not isinstance(value, str) or not value or len(value.encode('utf-8')) > 3500
            or '\\' in value or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise ValueError('Bounded canonical Ubuntu path required')
    path = PurePosixPath(value)
    if (not path.is_absolute() or path.anchor != '/' or str(path) != value or len(path.parts) < 3
            or any(part in ('.', '..') or len(part.encode('utf-8')) > 255 for part in path.parts[1:])):
        raise ValueError('Bounded canonical Ubuntu path required')
    if path.parts[1] in ('root', 'home', 'dev', 'proc', 'sys', 'run', 'boot', 'tmp') or path.is_relative_to('/var/tmp'):
        raise ValueError('Service root incompatible with protected native sandbox')
    return path


def _validated(settings):
    if type(settings) is not ServiceSettings:
        raise ValueError('Typed service settings required')
    binary = _linux_path(settings.binary_root)
    config = _linux_path(settings.config_path)
    data = _linux_path(settings.data_root)
    cloud = None if settings.cloud_root is None else _linux_path(settings.cloud_root)
    if config.suffix != '.json' or len(config.parent.parts) < 3:
        raise ValueError('Dedicated protected JSON configuration directory required')
    roots = [binary, config.parent, data] + ([] if cloud is None else [cloud])
    for index, left in enumerate(roots):
        for right in roots[index+1:]:
            if left.is_relative_to(right) or right.is_relative_to(left):
                raise ValueError('Binary, configuration, data and staging roots must be disjoint')
    validate_service_identity(settings.service_user, settings.executable_revision,
        settings.build_hash, settings.config_hash, settings.physical_memory_bytes)
    return roots


def validate_service_identity(service_user, executable_revision, build_hash, config_hash, physical_memory_bytes):
    if (not isinstance(service_user, str)
            or not re.fullmatch(r'r7(?:-[a-z][a-z0-9_-]{0,27})?', service_user)):
        raise ValueError('Dedicated unprivileged R7 service identity required')
    if not isinstance(executable_revision, str) or not re.fullmatch(r'[0-9a-f]{40}', executable_revision):
        raise ValueError('Exact executable revision required')
    for commitment in (build_hash, config_hash):
        if not isinstance(commitment, str) or not re.fullmatch(r'sha256:[0-9a-f]{64}', commitment):
            raise ValueError('Exact native build and configuration commitments required')
    if type(physical_memory_bytes) is not int or not 4*GIB <= physical_memory_bytes <= 4096*GIB:
        raise ValueError('Measured supported physical memory required')


def _quote(value):
    # systemd unit percent specifiers are independent of environment expansion.
    # ':' disables Exec* environment substitution; JSON quoting escapes quotes.
    if not isinstance(value, str) or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError('Bounded literal service argument required')
    return json.dumps(value.replace('%', '%%'), ensure_ascii=False)


def render_service_plan(settings, *, roles=('control', 'research')):
    """Pure rendering. Actual Linux roots/account/build/config require preflight."""
    _validated(settings)
    if (type(roles) is not tuple or not 1 <= len(roles) <= 2 or len(set(roles)) != len(roles)
            or any(role not in ('control', 'research') for role in roles)):
        raise ValueError('Only implemented control/research roles may be rendered')
    policy = ResourcePolicy.conservative(settings.physical_memory_bytes)
    writable = [settings.data_root] + ([] if settings.cloud_root is None else [settings.cloud_root]) + [POSIX_SCOPE_ROOT]
    units = {}
    for role in sorted(roles):
        argv = [str(PurePosixPath(settings.binary_root) / 'r7'), 'guarded-service', '--role', role,
            '--config', settings.config_path, '--expected-revision', settings.executable_revision,
            '--expected-build-hash', settings.build_hash, '--expected-config-hash', settings.config_hash,
            '--service-user', settings.service_user, '--expected-memory-bytes', str(settings.physical_memory_bytes)]
        rows = ['# R7 generated service plan; install/enforcement acceptance is separate',
            '[Unit]', f'Description=R7 {role}', 'After=local-fs.target systemd-tmpfiles-setup.service',
            'Requires=systemd-tmpfiles-setup.service',
            'StartLimitIntervalSec=120', 'StartLimitBurst=3',
            'RequiresMountsFor=' + ' '.join(_quote(value) for value in [settings.binary_root, str(PurePosixPath(settings.config_path).parent), *writable]),
            '', '[Service]', 'Type=exec', 'User=' + settings.service_user, 'Group=' + settings.service_user,
            'UMask=0077', 'WorkingDirectory=' + _quote(settings.data_root),
            'ExecStart=:' + ' '.join(_quote(value) for value in argv),
            'Restart=on-failure', 'RestartSec=5', 'TimeoutStartSec=90', 'TimeoutStopSec=30',
            'KillMode=control-group', 'KillSignal=SIGTERM', 'SendSIGKILL=yes',
            'NoNewPrivileges=yes', 'CapabilityBoundingSet=', 'AmbientCapabilities=',
            'ProtectSystem=strict', 'ProtectHome=yes', 'PrivateTmp=yes', 'PrivateDevices=yes',
            'ProtectKernelTunables=yes', 'ProtectKernelModules=yes', 'ProtectControlGroups=yes',
            'RestrictSUIDSGID=yes', 'LockPersonality=yes', 'RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6',
            'ReadWritePaths=' + ' '.join(_quote(value) for value in writable),
            'Environment=PYTHONDONTWRITEBYTECODE=1', 'StandardOutput=journal', 'StandardError=journal']
        if role == 'research':
            rows += ['Nice=10', 'CPUQuota=100%',
                'MemoryHigh=' + str(policy.memory_soft_budget_bytes * 9 // 10),
                'MemoryMax=' + str(policy.memory_soft_budget_bytes), 'MemorySwapMax=0', 'TasksMax=64']
        rows += ['', '[Install]', 'WantedBy=multi-user.target', '']
        units[f'r7-{role}.service'] = '\n'.join(rows)
    result = dict(schema_version='r7-service-plan-v0.2', status='RENDERED_ONLY',
        settings=asdict(settings), units=units, writable_roots=writable, mutations=[],
        scope_lock_provisioning=dict(rule=f'd {POSIX_SCOPE_ROOT} :0700 :{settings.service_user} :{settings.service_user} -',
            existing_owner_mismatch='REFUSE_BEFORE_INSTALLATION',on_service_stop='PRESERVE_LOCK_FILES_AND_INODES',
            existing_inode='PRESERVE_MODE_USER_GROUP;GUARDED_STARTUP_REJECTS_MISMATCH',
            provisioning='EXPLICIT_OPERATOR_INSTALLATION_REQUIRED',installed='NOT_RUN'),
        financial_authority='NONE', runtime='NOT_DELIVERED_CONTINUOUS_COMPOSITION_REQUIRED',
        native_service_acceptance='NOT_RUN', linux_kernel_enforcement='NOT_RUN',
        restart_admission='ACTUAL_EXISTING_OWNERS_RECHECK_BUILD_CONFIG_AND_RESTORATION;NO_FINANCIAL_PERMISSION',
        research_policy=dict(worker_count=1, cpu_quota_one_cpu_percent=100,
            memory_high_bytes=policy.memory_soft_budget_bytes * 9 // 10, memory_max_bytes=policy.memory_soft_budget_bytes,
            measured_physical_memory_bytes=settings.physical_memory_bytes))
    canonical = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    result['plan_hash'] = 'sha256:' + hashlib.sha256(canonical).hexdigest()
    return result
