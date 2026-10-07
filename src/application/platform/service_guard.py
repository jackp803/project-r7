"""Exact-subject native control/research startup, with no trading admission.

Actual native validation requires an installed Ubuntu product and a dedicated
operator-provisioned identity. Portable rendering/unit mocks do not meet it.
"""
import ipaddress
from itertools import chain
import json
import os
from pathlib import Path
import platform
import stat
import sys

from application.config import load_config
from application.platform.distribution import verify_distribution
from application.platform.paths import overlapping
from application.platform.private_files import create_private_directory, write_private_new
from application.platform.resources import inspect_hardware
from application.platform.service_plan import ServiceSettings, render_service_plan, validate_service_identity, _linux_path
from application.platform.supervision import _local_path, config_hash
from application.platform.scope_lock import operational_lock_root


def _native_ubuntu():
    if not getattr(sys, 'frozen', False) or platform.system() != 'Linux':
        raise ValueError('Native Ubuntu service product required')
    if platform.machine().lower() not in ('amd64', 'x86_64'):
        raise ValueError('Native Ubuntu x86-64 required')
    release = platform.freedesktop_os_release()
    if release.get('ID') != 'ubuntu' or release.get('VERSION_ID') not in ('24.04', '26.04'):
        raise ValueError('Qualified target Ubuntu version required')


def _service_account(name, require_service_identity):
    import grp
    import pwd
    try:
        user = pwd.getpwnam(name)
        group = grp.getgrnam(name)
    except KeyError:
        raise ValueError('Operator-provisioned R7 service account required') from None
    if user.pw_uid <= 0 or group.gr_gid <= 0 or user.pw_gid != group.gr_gid:
        raise ValueError('Dedicated unprivileged matching service identity required')
    if require_service_identity:
        if os.geteuid() != user.pw_uid or os.getegid() != group.gr_gid:
            raise ValueError('Exact unprivileged service identity required')
    elif os.geteuid() not in (0, user.pw_uid):
        raise ValueError('Local installer or exact service identity required')
    return user.pw_uid, group.gr_gid


def _access(info, uid, gid, mask):
    shift = 6 if info.st_uid == uid else 3 if info.st_gid == gid else 0
    return (info.st_mode >> shift) & mask == mask


def _protected_installation(root, uid, gid):
    _local_path(root)
    for index, path in enumerate(chain((root,), root.rglob('*'))):
        if index > 20000:
            raise ValueError('Bounded installed service inventory required')
        info = path.lstat()
        if (info.st_uid != 0 or info.st_mode & 0o022 or stat.S_ISLNK(info.st_mode)
                or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode))):
            raise ValueError('Immutable root-owned native installation required')
        if not _access(info, uid, gid, 5 if stat.S_ISDIR(info.st_mode) or path == root/'r7' else 4):
            raise ValueError('Native installation must be readable/executable by its service account')
    for parent in root.parents:
        info = parent.lstat()
        if info.st_uid != 0 or info.st_mode & 0o022 or not _access(info, uid, gid, 1):
            raise ValueError('Protected installation ancestors required')


def _protected_config(path, service_gid):
    _local_path(path)
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o027
            or not info.st_mode & 0o040 or info.st_gid != service_gid):
        raise ValueError('Root-owned protected readable service configuration required')
    for parent in path.parents:
        info = parent.lstat()
        if info.st_uid != 0 or info.st_mode & 0o022 or not _access(info, -1, service_gid, 1):
            raise ValueError('Protected configuration ancestors required')


def _private_service_root(path, uid, gid):
    _local_path(path)
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != uid or info.st_gid != gid
            or info.st_mode & 0o077 or not _access(info, uid, gid, 7)):
        raise ValueError('Existing private service-owned local writable root required')
    for parent in path.parents:
        info = parent.lstat()
        if info.st_uid not in (0, uid) or info.st_mode & 0o022 or not _access(info, uid, gid, 1):
            raise ValueError('Protected writable-root ancestors required')


def _read_local_config(path):
    """Reuse actual ancestor-pinned local reads, preserving Unicode filenames."""
    from application.platform.product_backup import _opened_source
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('Absolute local service configuration required')
    with _opened_source(path) as stream:
        before = os.fstat(stream.fileno())
        raw = stream.read(64*1024 + 1)
        after = os.fstat(stream.fileno())
    if len(raw) > 64*1024:
        raise ValueError('Bounded local service configuration required')
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino) or len(raw) != before.st_size:
        raise ValueError('Local service configuration changed during pinned read')
    return raw


def verify_service_subject(config_path, *, expected_revision, expected_build_hash,
        expected_config_hash, service_user, expected_memory_bytes, require_service_identity=False):
    """Validate actual files/account/hardware before any owner/database starts."""
    _native_ubuntu()
    config_path = Path(config_path)
    binary_root = Path(sys.executable).absolute().parent
    if not config_path.is_absolute() or type(require_service_identity) is not bool:
        raise ValueError('Explicit native service subject required')
    # Validate the identity and commitments before account/filesystem inspection.
    _linux_path(str(binary_root)); _linux_path(str(config_path))
    validate_service_identity(service_user, expected_revision, expected_build_hash, expected_config_hash, expected_memory_bytes)
    uid, gid = _service_account(service_user, require_service_identity)
    identity = verify_distribution(binary_root)
    _protected_installation(binary_root, uid, gid)
    if identity['executable_revision'] != expected_revision or identity['build_hash'] != expected_build_hash:
        raise ValueError('Native service build/revision changed')
    _protected_config(config_path, gid)
    before = _read_local_config(config_path)
    config = load_config(config_path)
    after = _read_local_config(config_path)
    if before != after or config_hash(config) != expected_config_hash:
        raise ValueError('Native service configuration changed')
    raw = json.loads(before)
    for key in ('local_data_root', 'cloud_root', 'database_path'):
        if raw.get(key) is not None:
            # load_config normalizes roots; inspect original paths as well so a
            # linked original cannot hide behind its resolved target.
            _local_path(Path(raw[key]))
    if config.research_worker_count != 1 or not ipaddress.ip_address(config.control_api_host).is_loopback:
        raise ValueError('One-worker loopback service profile required')
    subject = ServiceSettings(str(binary_root), str(config_path), str(config.local_data_root),
        None if config.cloud_root is None else str(config.cloud_root), service_user,
        expected_revision, expected_build_hash, expected_config_hash, expected_memory_bytes)
    render_service_plan(subject)
    for root in (config.local_data_root, config.cloud_root):
        if root is not None:
            _private_service_root(root, uid, gid)
    # Shared locks must exist with the provisioned one-host account; never use a
    # per-profile fallback or remove files/inodes during service shutdown.
    _private_service_root(operational_lock_root(config), uid, gid)
    hardware = inspect_hardware(config.local_data_root)
    if hardware.physical_memory_bytes != expected_memory_bytes:
        raise ValueError('Measured native service hardware profile changed')
    from application.platform.restoration import require_valid_restoration
    require_valid_restoration(config)
    if verify_distribution(binary_root) != identity or config_hash(load_config(config_path)) != expected_config_hash:
        raise ValueError('Native service subject changed during preflight')
    return subject


def run_guarded_service(config_path, *, role, **expected):
    if role not in ('control', 'research'):
        raise ValueError('Continuous runtime composition is not delivered by this service surface')
    config_path = Path(config_path)
    subject = verify_service_subject(config_path, require_service_identity=True, **expected)
    config = load_config(config_path)
    if config_hash(config) != subject.config_hash:
        raise ValueError('Native service configuration changed before owner composition')
    if role == 'control':
        from application.entrypoints import serve
        return serve(config, desktop=False, config_path=config_path)
    from application.research.worker import research_worker
    return research_worker(config_path, expected_config_hash=subject.config_hash)


def export_service_plan(config_path, destination, **expected):
    subject = verify_service_subject(config_path, **expected)
    plan = render_service_plan(subject)
    destination = Path(destination)
    if not destination.is_absolute() or '..' in destination.parts:
        raise ValueError('Fresh absolute local service-plan destination required')
    _local_path(destination)
    from application.platform.scope_lock import POSIX_SCOPE_ROOT
    protected = [Path(config_path).parent, Path(subject.binary_root), Path(subject.data_root), Path(POSIX_SCOPE_ROOT)]
    if subject.cloud_root is not None:
        protected.append(Path(subject.cloud_root))
    if destination.exists() or any(overlapping(destination, root) for root in protected):
        raise ValueError('Fresh service-plan output outside protected roots required')
    # No installer/systemctl/migration action. The complete private manifest is
    # written last; a partial export is never a ready installation plan.
    create_private_directory(destination)
    for name, text in plan['units'].items():
        write_private_new(destination/name, text.encode('utf-8'))
    write_private_new(destination/'r7-scopes.conf', (plan['scope_lock_provisioning']['rule']+'\n').encode('utf-8'))
    write_private_new(destination/'service-plan.json',
        (json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode('utf-8'))
    return dict(status='PLAN_EXPORTED', plan_hash=plan['plan_hash'], units=list(plan['units']),
        service_installation='NOT_PERFORMED', service_start='NOT_PERFORMED',
        native_service_acceptance='NOT_RUN', financial_authority='NONE',
        runtime='NOT_DELIVERED_CONTINUOUS_COMPOSITION_REQUIRED')
