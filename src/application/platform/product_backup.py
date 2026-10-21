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
    _destination, _deadline, _profile_current, _unique_pairs, CONSISTENCY, _verify_database_backup_snapshot,_hash_file)
from application.platform.private_files import create_private_directory, require_private, write_private_new, _filesystem_path
from application.platform.scope_lock import ProcessScopeLock, operational_lock_root
from application.platform.supervision import _local_path, config_hash, PROCESS_ROLES
from application.cloud.manifest import safe_relative, parse_manifest, validate_package, scan_untrusted
from application.cloud.protocol import PackageSnapshot
from application.cloud.safe_files import read_bounded, _windows_native_path
from application.datasets.catalog import DatasetCatalog, decode, read_local
from application.research.evidence import stamp, capture_provenance

SCHEMA = 'r7-private-product-data-backup-v0.2'
MAX_FILES, MAX_BYTES, MAX_FILE_BYTES = 4096, 16 * 1024**3, 64 * 1024**2
TRANSIENT_ROOTS = frozenset({'process-scopes', 'worker-logs', 'paper-release-observations', 'managed-stop-requests',
    'public-market-observations','public-funding-observations'})
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
        for entry in _filesystem_path(directory).iterdir():
            path = directory / entry.name
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
            information = entry.lstat()
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
                handle = kernel.CreateFileW(_windows_native_path(current), 0x80 if directory else 0x80000000,
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


def _sealed_fixture_auxiliary(root,manifest,snapshot,selected):
    """Only the exact auxiliary bytes already bound by selected author notes."""
    from application.fixtures import faults,temporal
    from application.cloud.manifest import byte_hash
    notes=[spec for spec in manifest.payloads if spec.role=='research_notes']
    if not notes:return set(),{}
    raw=read_local(root,snapshot+'/'+notes[0].relative_path,65536)
    try:value=decode(raw)
    except ValueError:return set(),{}
    if not isinstance(value,dict):return set(),{}
    schema=value.get('schema_version')
    if schema==faults.SCHEMA:
        document=faults.validate(value);reference=faults.REFERENCE
        faults.require_selection(document,selected)
        intent='EVERGREEN_STRATEGY';validity={'from':None,'until':None}
    elif schema==temporal.SCHEMA:
        document=temporal.validate(value);reference=temporal.REFERENCE
        if selected['paper_policy_ref']!=temporal.policy_ref(document):
            raise ProductBackupError('PRODUCT_BACKUP_FIXTURE_AUXILIARY_POLICY_MISMATCH')
        intent='TACTICAL_STRATEGY';validity=document['validity']
    else:return set(),{}
    if (manifest.submission_id!=document['submission_id'] or manifest.raw['intent_class']!=intent
            or manifest.raw['validity']!=validity or read_local(root,reference,65536)!=raw):
        raise ProductBackupError('PRODUCT_BACKUP_FIXTURE_AUXILIARY_SEAL_MISMATCH')
    return {reference},{reference:byte_hash(raw)}


def _fixture_paper_inputs(root,paths,selected):
    """Exact typed fixture metadata/input coverage; never a release admission."""
    from application.paper.setup import INPUT_KEYS,INPUT_SCHEMA,RECORD_KEYS,SELECTION_SCHEMA,SELECTION_FILE
    from application.paper.owners import PaperOwnerSelection
    from application.paper.policy import parse_simulation_policy
    from registry.operational_authority import ReleaseBinding
    from risk.product_policy import parse_product_risk_policy
    from validation.paper_policy import parse_paper_promotion_policy
    from application.cloud.manifest import safe_component,byte_hash
    allowed,hashes=set(),{}
    profile='fixture-inputs/selection.json'
    if profile in paths:
        if selected is None or decode(read_local(root,profile,65536))!=selected:
            raise ProductBackupError('PRODUCT_BACKUP_FIXTURE_SELECTION_MISMATCH')
        allowed.add(profile)
    operator='fixture-inputs/paper-selection.json'
    inputs=None
    if operator in paths:
        inputs=decode(read_local(root,operator,65536))
        if not isinstance(inputs,dict) or set(inputs)!=INPUT_KEYS or inputs['schema_version']!=INPUT_SCHEMA:
            raise ProductBackupError('PRODUCT_BACKUP_FIXTURE_PAPER_INPUT_INVALID')
        safe_component(inputs['submission_id']);safe_component(inputs['paper_policy_ref'])
        allowed.add(operator)
    record=None
    if SELECTION_FILE in paths:
        record=decode(read_local(root,SELECTION_FILE,65536))
        if not isinstance(record,dict) or set(record)!=RECORD_KEYS or record['schema_version']!=SELECTION_SCHEMA:
            raise ProductBackupError('PRODUCT_BACKUP_FIXTURE_PAPER_SUBJECT_INVALID')
        owner=PaperOwnerSelection(**record['owner'])
        release=ReleaseBinding(**record['release'])
        refs=record['input_refs']
        keys={'simulation_policy_ref','risk_policy_ref','promotion_policy_ref'}
        if (owner.namespace!='FIXTURE' or release.namespace!='FIXTURE' or release.release_kind!='FIXTURE' or
                not isinstance(refs,dict) or set(refs)!=keys or not isinstance(record['input_hashes'],dict) or
                set(record['input_hashes'])!=keys):
            raise ProductBackupError('PRODUCT_BACKUP_FIXTURE_PAPER_SUBJECT_INVALID')
        safe_component(record['submission_id'])
        snapshot='snapshots/'+record['submission_id']+'-'+record['manifest_hash'][7:]
        manifest=parse_manifest(read_local(root,snapshot+'/manifest.json',65536))
        if (manifest.manifest_hash!=record['manifest_hash'] or record['strategy']!=dict(
                strategy_id=manifest.strategy_id,strategy_version=manifest.strategy_version,content_hash=manifest.strategy_content_hash) or
                owner.as_dict()['submission_validity']!={key:manifest.raw[key] for key in ('intent_class','validity')}):
            raise ProductBackupError('PRODUCT_BACKUP_FIXTURE_PAPER_MANIFEST_MISMATCH')
        if inputs is not None and inputs!={**refs,'schema_version':INPUT_SCHEMA,
                'submission_id':record['submission_id'],'paper_policy_ref':owner.as_dict()['paper_policy_ref']}:
            raise ProductBackupError('PRODUCT_BACKUP_FIXTURE_PAPER_INPUT_MISMATCH')
        inputs=refs
        allowed.add(SELECTION_FILE)
    if inputs is not None:
        values={}
        for field,validator in (('simulation_policy',parse_simulation_policy),('risk_policy',parse_product_risk_policy),
                ('promotion_policy',parse_paper_promotion_policy)):
            relative=safe_relative(inputs[field+'_ref'])
            if not relative.endswith('.json') or relative.split('/')[0] in TRANSIENT_ROOTS:
                raise ProductBackupError('PRODUCT_BACKUP_POLICY_PATH_INVALID')
            raw=read_local(root,relative,65536);value=decode(raw);scan_untrusted(value)
            validator(value,namespace='FIXTURE')
            values[field]=value;allowed.add(relative)
            if record is not None:
                if byte_hash(raw)!=record['input_hashes'][field+'_ref']:
                    raise ProductBackupError('PRODUCT_BACKUP_FIXTURE_PAPER_INPUT_CHANGED')
                hashes[relative]=byte_hash(raw)
        if record is not None:
            observed={**owner.as_dict(),**values}
            if PaperOwnerSelection(**observed).selection_hash!=owner.selection_hash:
                raise ProductBackupError('PRODUCT_BACKUP_FIXTURE_PAPER_POLICY_MISMATCH')
            auxiliary,auxiliary_hashes=_sealed_fixture_auxiliary(root,manifest,snapshot,observed)
            allowed.update(auxiliary);hashes.update(auxiliary_hashes)
    return allowed,hashes


def _data_inventory(root, end, *, databases=(), exclusions=True, restore_metadata=False,
                    canonical_database=None,namespace=None,sealed_database=False):
    paths, excluded = _walk(root, end, exclusions=exclusions)
    ignored = {name + suffix for name in databases for suffix in ('', '-wal', '-shm', '-journal')}
    if restore_metadata:
        ignored.update(RESTORE_METADATA)
    allowed, expected_hashes = set(), {}
    from application.paper.capture_archive import PublicCaptureArchive,ROOT as archive_root
    archive_paths={name for name in paths if name.startswith(archive_root+'/')}
    if archive_paths:
        try:
            # Immutable frame/index/seal/counter closure, not restored operation
            # permission. Old live health projections are deliberately transient.
            PublicCaptureArchive(root/archive_root,_deadline=lambda:_deadline(end))
        except (ValueError,TypeError,KeyError,OSError,RuntimeError) as error:
            raise ProductBackupError('PRODUCT_BACKUP_PUBLIC_ARCHIVE_INVALID') from error
        allowed.update(archive_paths)
    from application.paper.public_market import SELECTION_FILE as public_selection,validate_profile
    if public_selection in paths:
        validate_profile(decode(read_local(root,public_selection,16384)))
        allowed.add(public_selection)
    selected=None
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
    fixture_files,fixture_hashes=_fixture_paper_inputs(root,paths,selected)
    allowed.update(fixture_files);expected_hashes.update(fixture_hashes)
    if namespace=='LOCAL_RESEARCH':
        from .paper_backup_history import ordinary_history_inventory
        paper_files,paper_hashes=ordinary_history_inventory(root,paths,canonical_database,end,sealed_database=sealed_database)
        allowed.update(paper_files);expected_hashes.update(paper_hashes)
    # Public read-only captures include raw audit bytes, even rejected or
    # interrupted attempts. They never imply dataset/research readiness.
    public_roots=set()
    for name in paths:
        parts=name.split('/')
        if len(parts)>=3 and parts[0]=='datasets' and (parts[2]=='acquisition.json' or
                len(parts)==4 and parts[2]=='requests' and parts[3].endswith('-attempt.json')):
            public_roots.add('/'.join(parts[:2]))
    from application.datasets.public_capture import public_capture_inventory
    for base in sorted(public_roots):
        try:
            refs,hashes,manifest_ref=public_capture_inventory(root,base,paths,deadline=lambda:_deadline(end))
        except (ValueError,TypeError,KeyError,RuntimeError) as error:
            raise ProductBackupError('PRODUCT_BACKUP_PUBLIC_CAPTURE_INVALID') from error
        allowed.update(refs);expected_hashes.update(hashes)
        if manifest_ref is not None:dataset_refs.add(manifest_ref)
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
        if not _filesystem_path(parent).exists():
            create_private_directory(parent)
    if not _filesystem_path(target.parent).exists():
        create_private_directory(target.parent)
    write_private_new(target, b'')
    count, digest = 0, hashlib.sha256()
    with _opened_source(source) as incoming, _filesystem_path(target).open('wb') as outgoing:
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
            for role in PROCESS_ROLES:
                stack.enter_context(ProcessScopeLock(role+':'+config.product_instance_id, lock_root=operational_lock_root(config)))
            restoration=_source_restoration(config)
            restored=restoration['status']=='RESTORED_INHIBITED'
            relatives = [path.relative_to(config.local_data_root).as_posix() for path in inventory.values()]
            from application.config import product_namespace
            history=dict(canonical_database=config.database_path,namespace=product_namespace(config))
            rows, excluded = _data_inventory(config.local_data_root, end, databases=relatives,restore_metadata=restored,**history)
            create_private_directory(target)
            db_manifest = _capture_database_bundle(config, target/'databases', inventory, end, stack, config_path=config_path)
            if sum(row['bytes'] for row in rows + db_manifest['databases']) > MAX_BYTES:
                raise ProductBackupError('PRODUCT_BACKUP_TRANSFER_LIMIT')
            create_private_directory(target/'files')
            for row in rows:
                _copy_file(config.local_data_root/row['relative_path'], target/'files'/row['relative_path'], row, end)
            if (_data_inventory(config.local_data_root, end, databases=relatives,restore_metadata=restored,**history) != (rows, excluded)
                    or _source_restoration(config)!=restoration):
                raise ProductBackupError('PRODUCT_BACKUP_SOURCE_CHANGED')
            _profile_current(config, config_path)
            manifest = dict(schema_version=SCHEMA, backup_id=db_manifest['backup_id'], created_at=stamp(datetime.now(timezone.utc)),
                product_instance_id=config.product_instance_id, config_hash=config_hash(config), data_class='PRIVATE_LOCAL',
                cloud_publication='FORBIDDEN', consistency=CONSISTENCY, source_provenance=capture_provenance(),
                database_manifest_sha256='sha256:'+hashlib.sha256(_filesystem_path(target/'databases'/'manifest.json').read_bytes()).hexdigest(),
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
    if {p.name for p in _filesystem_path(path).iterdir()} != {'databases','files','manifest.json'}:
        raise ProductBackupError('PRODUCT_BACKUP_UNEXPECTED_ARTIFACT')
    require_private(path/'files', directory=True)
    # Bind file closure to the verified captured ledger, never the live store.
    database,db_manifest,db_raw = _verify_database_backup_snapshot(config, path/'databases', timeout_seconds=_remaining(end), _include_settings=True)
    if database['backup_id'] != manifest['backup_id'] or 'sha256:'+hashlib.sha256(db_raw).hexdigest() != manifest['database_manifest_sha256']:
        raise ProductBackupError('PRODUCT_BACKUP_DATABASE_BINDING_MISMATCH')
    canonical=next((row for row in db_manifest['databases'] if row['logical_name']=='canonical'),None)
    captured=None if canonical is None else path/'databases'/canonical['artifact']
    from application.config import product_namespace
    actual, _ = _data_inventory(path/'files', end, exclusions=False,canonical_database=captured,
        namespace=product_namespace(config),sealed_database=True)
    for row in actual:
        require_private(path/'files'/row['relative_path'])
    if actual != rows:
        raise ProductBackupError('PRODUCT_BACKUP_DATA_HASH_MISMATCH')
    if canonical is not None and _hash_file(captured,end)!={key:canonical[key] for key in ('bytes','sha256')}:
        raise ProductBackupError('PRODUCT_BACKUP_CAPTURED_CANONICAL_CHANGED')
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
