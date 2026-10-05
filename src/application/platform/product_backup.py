"""Versioned owner-private backup of the supported local product profile.

Only selected policies, dataset bytes, sealed packages and owned stores are
durable product data. Unknown files are a coverage failure. No credential
reference, command capture or cloud tree is read or published here.
"""
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
import hashlib, json, math, os, stat, time, uuid
from pathlib import Path

from application.platform.backup import (_capture_database_bundle, _inventory,
    _destination, _deadline, _profile_current, _unique_pairs, CONSISTENCY, _verify_database_backup_snapshot)
from application.platform.private_files import create_private_directory, require_private, write_private_new
from application.platform.scope_lock import ProcessScopeLock, operational_lock_root
from application.platform.supervision import _local_path, config_hash
from application.cloud.manifest import safe_relative, parse_manifest, validate_package, scan_untrusted
from application.cloud.protocol import PackageSnapshot
from application.cloud.safe_files import read_bounded
from application.datasets.catalog import DatasetCatalog, decode, read_local
from application.research.evidence import stamp, capture_provenance

SCHEMA = 'r7-private-product-data-backup-v0.2'
MAX_FILES, MAX_BYTES, MAX_FILE_BYTES = 4096, 16 * 1024**3, 64 * 1024**2
TRANSIENT_ROOTS = frozenset({'process-scopes', 'worker-logs'})
RESTORE_METADATA = frozenset({'restore-generation.json','restore-in-progress.json','restored-product.json'})
TOP_KEYS = {'schema_version', 'backup_id', 'created_at', 'product_instance_id', 'config_hash',
    'data_class', 'cloud_publication', 'consistency', 'source_provenance', 'database_manifest_sha256',
    'files', 'coverage', 'excluded_transient_roots', 'source_restoration'}
ROW_KEYS = {'relative_path', 'bytes', 'sha256'}


class ProductBackupError(RuntimeError):
    """Sanitized failure; a retained partial generation is never ready."""


def _bound(seconds, *, minimum=5):
    if type(seconds) is not int or not minimum <= seconds <= 300:
        raise ProductBackupError('BOUNDED_PRODUCT_BACKUP_DEADLINE_REQUIRED')
    return time.monotonic() + seconds


def _safe_backup_relative(relative):
    if (isinstance(relative, str) and relative.startswith('snapshots/')
            and len(relative.split('/')) == 3 and relative.endswith('/.seal.json')):
        safe_relative(relative[:-len('/.seal.json')])
    else:
        safe_relative(relative)
    return relative


def _remaining(end):
    _deadline(end)
    return min(300, max(1, math.ceil(end - time.monotonic())))


def _walk(root, end, *, exclusions=True):
    _local_path(root)
    paths, excluded, pending, visited = {}, [], [root], 0
    while pending:
        directory = pending.pop()
        _local_path(directory)
        for path in directory.iterdir():
            _deadline(end)
            visited += 1
            if visited > MAX_FILES * 2:
                raise ProductBackupError('PRODUCT_BACKUP_INVENTORY_LIMIT')
            relative = path.relative_to(root).as_posix()
            if exclusions and path.parent == root and path.name in TRANSIENT_ROOTS:
                excluded.append(path.name)
                continue  # Deliberately do not open or enumerate captures/locks.
            _safe_backup_relative(relative)
            _local_path(path)
            information = path.lstat()
            if stat.S_ISDIR(information.st_mode):
                pending.append(path)
            elif stat.S_ISREG(information.st_mode) and information.st_nlink == 1:
                paths[relative] = path
            else:
                raise ProductBackupError('PRODUCT_BACKUP_REGULAR_SINGLE_LINK_REQUIRED')
    if len(paths) > MAX_FILES or len({name.casefold() for name in paths}) != len(paths):
        raise ProductBackupError('PRODUCT_BACKUP_INVENTORY_CONFLICT')
    return paths, sorted(excluded)


@contextmanager
def _opened_source(path):
    """Pin every ancestor without following links; Windows also denies writers."""
    _local_path(path)
    with ExitStack() as stack:
        if os.name == 'nt':
            import ctypes, msvcrt
            from ctypes import wintypes as w
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.CreateFileW.argtypes = [w.LPCWSTR,w.DWORD,w.DWORD,ctypes.c_void_p,w.DWORD,w.DWORD,w.HANDLE]
            kernel.CreateFileW.restype = w.HANDLE
            kernel.CloseHandle.argtypes = [w.HANDLE]
            current = Path(path.anchor)
            for index, part in enumerate(path.parts[1:]):
                current = current / part
                directory = index < len(path.parts) - 2
                handle = kernel.CreateFileW(str(current), 0x80 if directory else 0x80000000,
                    1, None, 3, 0x200000 | (0x2000000 if directory else 0), None)
                if handle == ctypes.c_void_p(-1).value:
                    raise ProductBackupError('PRODUCT_BACKUP_PINNED_READ_DENIED')
                if directory:
                    stack.callback(kernel.CloseHandle, handle)
                else:
                    try:
                        descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
                    except Exception:
                        kernel.CloseHandle(handle)
                        raise
            stream = stack.enter_context(os.fdopen(descriptor, 'rb'))
            _local_path(path)  # Pinned ancestors cannot be replaced on Windows.
        else:
            descriptor = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY)
            stack.callback(os.close, descriptor)
            for index, part in enumerate(path.parts[1:]):
                directory = index < len(path.parts) - 2
                descriptor = os.open(part, os.O_RDONLY | os.O_NOFOLLOW | (os.O_DIRECTORY if directory else 0), dir_fd=descriptor)
                stack.callback(os.close, descriptor)
            stream = stack.enter_context(os.fdopen(os.dup(descriptor), 'rb'))
        information = os.fstat(stream.fileno())
        if not stat.S_ISREG(information.st_mode) or information.st_nlink != 1:
            raise ProductBackupError('PRODUCT_BACKUP_REGULAR_SINGLE_LINK_REQUIRED')
        yield stream


def _file_facts(path, end):
    digest, count = hashlib.sha256(), 0
    with _opened_source(path) as stream:
        before = os.fstat(stream.fileno())
        while chunk := stream.read(1024 * 1024):
            _deadline(end)
            count += len(chunk)
            if count > MAX_FILE_BYTES:
                raise ProductBackupError('PRODUCT_BACKUP_FILE_LIMIT')
            digest.update(chunk)
        after = os.fstat(stream.fileno())
    if (count != before.st_size or (before.st_size,before.st_mtime_ns,before.st_ino)
            != (after.st_size,after.st_mtime_ns,after.st_ino)):
        raise ProductBackupError('PRODUCT_BACKUP_SOURCE_CHANGED')
    return dict(bytes=count, sha256='sha256:' + digest.hexdigest())


def _data_inventory(root, end, *, databases=(), exclusions=True, restore_metadata=False):
    paths, excluded = _walk(root, end, exclusions=exclusions)
    ignored = {name + suffix for name in databases for suffix in ('', '-wal', '-shm', '-journal')}
    if restore_metadata:
        ignored.update(RESTORE_METADATA)
    allowed, expected_hashes = set(), {}
    selection = 'owner-selections.json'
    if selection in paths:
        selected = decode(read_local(root, selection, 65536))
        if (not isinstance(selected, dict) or set(selected) != {'schema_version','cloud_root_id','research_policies'}
                or selected['schema_version'] != 'r7-owner-selections-v0.2'):
            raise ProductBackupError('PRODUCT_BACKUP_SELECTION_INVALID')
        from application.research.selection import ResearchRequestResolver
        resolver = ResearchRequestResolver(root, snapshot_root=root/'snapshots', intake_factory=lambda: None,
            registry_factory=lambda: None, policies=selected['research_policies'])
        allowed.add(selection)
        dataset_refs = set()
        for policy in resolver.policies.values():
            for name, relative in policy.items():
                if name.endswith('_ref'):
                    if not relative.endswith('.json') or relative in ignored or relative.split('/')[0] in TRANSIENT_ROOTS:
                        raise ProductBackupError('PRODUCT_BACKUP_POLICY_PATH_INVALID')
                    scan_untrusted(decode(read_local(root, relative, 262144)))
                    allowed.add(relative)
                    if name == 'dataset_ref':
                        dataset_refs.add(relative)
    else:
        dataset_refs = set()
    # Retain all supported imported revisions, including currently unselected ones.
    dataset_refs.update(name for name in paths if name.startswith('datasets/')
        and len(name.split('/')) == 4 and name.endswith('/dataset.json'))
    catalog = DatasetCatalog(root)
    for relative in sorted(dataset_refs):
        value = catalog.load(relative).as_dict()
        allowed.add(relative)
        containers = list(value['candles'])
        if value['funding']['mode'] == 'RECORDED':
            containers.append(value['funding'])
        for container in containers:
            path = (Path(relative).parent / container['path']).as_posix()
            safe_relative(path)
            allowed.add(path)
            expected_hashes[path] = container['byte_hash']
    for relative in sorted(paths):
        if relative.startswith('snapshots/') and len(relative.split('/')) == 3 and relative.endswith('/manifest.json'):
            directory = root / Path(relative).parent
            manifest = parse_manifest(read_local(root, relative, 65536))
            validated = validate_package(PackageSnapshot(directory, manifest.manifest_hash,
                {spec.role: directory/spec.relative_path for spec in manifest.payloads}))
            if validated.manifest.manifest_hash != manifest.manifest_hash:
                raise ProductBackupError('PRODUCT_BACKUP_SNAPSHOT_INVALID')
            if directory.name != manifest.submission_id + '-' + manifest.manifest_hash[7:]:
                raise ProductBackupError('PRODUCT_BACKUP_SNAPSHOT_IDENTITY_INVALID')
            allowed.add(relative)
            allowed.update((Path(relative).parent/spec.relative_path).as_posix() for spec in manifest.payloads)
            seal = decode(read_bounded(directory, '.seal.json', 65536))
            expected_seal = dict(schema_version='r7-package-snapshot-v0.2',manifest_hash=manifest.manifest_hash,
                manifest_byte_hash='sha256:'+hashlib.sha256(read_bounded(directory,'manifest.json',65536)).hexdigest(),
                payload_hashes={spec.role:'sha256:'+hashlib.sha256(read_bounded(directory,spec.relative_path,256*1024)).hexdigest()
                    for spec in manifest.payloads})
            if seal != expected_seal:
                raise ProductBackupError('PRODUCT_BACKUP_SNAPSHOT_SEAL_INVALID')
            allowed.add((Path(relative).parent/'.seal.json').as_posix())
    if set(paths) - ignored != allowed or allowed & ignored:
        raise ProductBackupError('PRODUCT_BACKUP_COVERAGE_GAP')
    rows = [dict(relative_path=name, **_file_facts(root/name, end)) for name in sorted(allowed)]
    if sum(row['bytes'] for row in rows) > MAX_BYTES:
        raise ProductBackupError('PRODUCT_BACKUP_TRANSFER_LIMIT')
    if any(row['relative_path'] in expected_hashes and row['sha256'] != expected_hashes[row['relative_path']] for row in rows):
        raise ProductBackupError('PRODUCT_BACKUP_DATASET_HASH_MISMATCH')
    return rows, excluded


def _copy_file(source, target, row, end):
    for parent in reversed(target.parent.parents):
        # Caller establishes the private root; create only missing descendants.
        if not parent.exists():
            create_private_directory(parent)
    if not target.parent.exists():
        create_private_directory(target.parent)
    write_private_new(target, b'')
    count, digest = 0, hashlib.sha256()
    with _opened_source(source) as incoming, target.open('wb') as outgoing:
        while chunk := incoming.read(1024 * 1024):
            _deadline(end)
            count += len(chunk)
            if count > row['bytes']:
                raise ProductBackupError('PRODUCT_BACKUP_SOURCE_CHANGED')
            outgoing.write(chunk)
            digest.update(chunk)
        outgoing.flush()
        os.fsync(outgoing.fileno())
    require_private(target)
    if count != row['bytes'] or 'sha256:' + digest.hexdigest() != row['sha256']:
        raise ProductBackupError('PRODUCT_BACKUP_SOURCE_CHANGED')


def _valid_source_restoration(value):
    if value == dict(status='NOT_RESTORED',financial_authority='NONE'):
        return True
    try:
        token=value['restore_generation_id']
        if str(uuid.UUID(token))!=token:
            return False
        return value == dict(status='RESTORED_INHIBITED',restore_generation_id=token,scope='PRODUCT_DATA',
            user_data_restore='COMPLETE_SUPPORTED_LOCAL_PROFILE',reconciliation='REQUIRED',reauthorization='REQUIRED',
            runtime_new_exposure='INHIBITED',cloud='DISCONNECTED',financial_authority='NONE',
            reason_codes=['RESTORE_RECONCILIATION_AND_REAUTHORIZATION_REQUIRED'])
    except (TypeError,ValueError,KeyError,AttributeError):
        return False


def _source_restoration(config):
    from application.platform.restoration import require_valid_restoration
    value=require_valid_restoration(config)
    if not _valid_source_restoration(value):
        raise ProductBackupError('PRODUCT_BACKUP_RESTORATION_COVERAGE_GAP')
    return value


def create_product_backup(config, destination, *, config_path=None, timeout_seconds=60):
    end = _bound(timeout_seconds)
    try:
        target = _destination(config, destination)
        inventory = _inventory(config, include_settings=True)
        _profile_current(config, config_path)
        with ExitStack() as stack:
            for role in ('control','research','runtime','cloud'):
                stack.enter_context(ProcessScopeLock(role+':'+config.product_instance_id, lock_root=operational_lock_root(config)))
            restoration=_source_restoration(config)
            restored=restoration['status']=='RESTORED_INHIBITED'
            relatives = [path.relative_to(config.local_data_root).as_posix() for path in inventory.values()]
            rows, excluded = _data_inventory(config.local_data_root, end, databases=relatives,restore_metadata=restored)
            create_private_directory(target)
            db_manifest = _capture_database_bundle(config, target/'databases', inventory, end, stack, config_path=config_path)
            if sum(row['bytes'] for row in rows + db_manifest['databases']) > MAX_BYTES:
                raise ProductBackupError('PRODUCT_BACKUP_TRANSFER_LIMIT')
            create_private_directory(target/'files')
            for row in rows:
                _copy_file(config.local_data_root/row['relative_path'], target/'files'/row['relative_path'], row, end)
            if (_data_inventory(config.local_data_root, end, databases=relatives,restore_metadata=restored) != (rows, excluded)
                    or _source_restoration(config)!=restoration):
                raise ProductBackupError('PRODUCT_BACKUP_SOURCE_CHANGED')
            _profile_current(config, config_path)
            manifest = dict(schema_version=SCHEMA, backup_id=db_manifest['backup_id'], created_at=stamp(datetime.now(timezone.utc)),
                product_instance_id=config.product_instance_id, config_hash=config_hash(config), data_class='PRIVATE_LOCAL',
                cloud_publication='FORBIDDEN', consistency=CONSISTENCY, source_provenance=capture_provenance(),
                database_manifest_sha256='sha256:'+hashlib.sha256((target/'databases'/'manifest.json').read_bytes()).hexdigest(),
                files=rows, coverage='COMPLETE_SUPPORTED_LOCAL_PROFILE', excluded_transient_roots=excluded,
                source_restoration=restoration)
            _deadline(end)
            write_private_new(target/'manifest.json', (json.dumps(manifest, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
            return verify_product_backup(config, target, timeout_seconds=_remaining(end))
    except ProductBackupError:
        raise
    except Exception:
        raise ProductBackupError('PRIVATE_PRODUCT_BACKUP_FAILED') from None


def _verified_manifest(config, destination, end):
    path = _destination(config, destination)
    require_private(path, directory=True)
    require_private(path/'manifest.json')
    raw = read_local(path, 'manifest.json', 2*1024**2)
    manifest = json.loads(raw, object_pairs_hook=_unique_pairs, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    if (not isinstance(manifest, dict) or set(manifest) != TOP_KEYS or manifest['schema_version'] != SCHEMA
            or manifest['product_instance_id'] != config.product_instance_id or manifest['config_hash'] != config_hash(config)
            or manifest['data_class'] != 'PRIVATE_LOCAL' or manifest['cloud_publication'] != 'FORBIDDEN'
            or manifest['consistency'] != CONSISTENCY or manifest['coverage'] != 'COMPLETE_SUPPORTED_LOCAL_PROFILE'
            or not isinstance(manifest['source_provenance'], dict) or not _valid_source_restoration(manifest['source_restoration'])):
        raise ProductBackupError('PRODUCT_BACKUP_MANIFEST_INVALID')
    if str(uuid.UUID(manifest['backup_id'])) != manifest['backup_id']:
        raise ProductBackupError('PRODUCT_BACKUP_MANIFEST_INVALID')
    stamp(datetime.fromisoformat(manifest['created_at'].replace('Z','+00:00')))
    excluded = manifest['excluded_transient_roots']
    if not isinstance(excluded,list) or excluded != sorted(set(excluded)) or set(excluded) - TRANSIENT_ROOTS:
        raise ProductBackupError('PRODUCT_BACKUP_MANIFEST_INVALID')
    rows = manifest['files']
    if not isinstance(rows,list) or len(rows) > MAX_FILES:
        raise ProductBackupError('PRODUCT_BACKUP_MANIFEST_INVALID')
    for row in rows:
        if (not isinstance(row,dict) or set(row) != ROW_KEYS or type(row['bytes']) is not int
                or not 0 <= row['bytes'] <= MAX_FILE_BYTES):
            raise ProductBackupError('PRODUCT_BACKUP_MANIFEST_INVALID')
        _safe_backup_relative(row['relative_path'])
    if len({row['relative_path'].casefold() for row in rows}) != len(rows):
        raise ProductBackupError('PRODUCT_BACKUP_MANIFEST_INVALID')
    if {p.name for p in path.iterdir()} != {'databases','files','manifest.json'}:
        raise ProductBackupError('PRODUCT_BACKUP_UNEXPECTED_ARTIFACT')
    require_private(path/'files', directory=True)
    actual, _ = _data_inventory(path/'files', end, exclusions=False)
    for row in actual:
        require_private(path/'files'/row['relative_path'])
    if actual != rows:
        raise ProductBackupError('PRODUCT_BACKUP_DATA_HASH_MISMATCH')
    database,db_manifest,db_raw = _verify_database_backup_snapshot(config, path/'databases', timeout_seconds=_remaining(end), _include_settings=True)
    if database['backup_id'] != manifest['backup_id'] or 'sha256:'+hashlib.sha256(db_raw).hexdigest() != manifest['database_manifest_sha256']:
        raise ProductBackupError('PRODUCT_BACKUP_DATABASE_BINDING_MISMATCH')
    if sum(row['bytes'] for row in rows + db_manifest['databases']) > MAX_BYTES:
        raise ProductBackupError('PRODUCT_BACKUP_TRANSFER_LIMIT')
    _deadline(end)
    if read_local(path,'manifest.json',2*1024**2)!=raw:
        raise ProductBackupError('PRODUCT_BACKUP_MANIFEST_CHANGED')
    return manifest, raw, database, db_manifest, db_raw


def verify_product_backup(config, destination, *, timeout_seconds=60):
    end = _bound(timeout_seconds, minimum=1)
    try:
        manifest, _, database, _, _ = _verified_manifest(config, destination, end)
        return dict(status='PRODUCT_DATA_BACKUP_VERIFIED', schema_version=SCHEMA, backup_id=manifest['backup_id'],
            database_count=database['database_count'], file_count=len(manifest['files']), coverage=manifest['coverage'],
            excluded_transient_roots=manifest['excluded_transient_roots'], data_class='PRIVATE_LOCAL',
            cloud_publication='FORBIDDEN', financial_authority='NONE', restore='NOT_PERFORMED')
    except ProductBackupError:
        raise
    except Exception:
        raise ProductBackupError('PRIVATE_PRODUCT_BACKUP_VERIFICATION_FAILED') from None


def restore_product_backup(config, backup, destination, *, config_path=None, timeout_seconds=60):
    from application.platform.database_restore import _restore_backup
    try:
        return _restore_backup(config, backup, destination, config_path=config_path,
            timeout_seconds=timeout_seconds, product_data=True)
    except ProductBackupError:
        raise
    except Exception:
        raise ProductBackupError('PRIVATE_PRODUCT_RESTORE_FAILED') from None
