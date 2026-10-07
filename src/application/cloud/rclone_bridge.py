"""Locally provisioned copy-only Drive bridge; no OAuth enrollment or secrets read.

The runner seam is trusted application composition for offline transport tests.
Packages never select a program, config reference, remote or command flag.
"""
from dataclasses import dataclass
from functools import wraps
import hashlib
import json
import math
from pathlib import Path
import os
import re
import time
import uuid

from application.cloud.command_runner import CommandResult, run_bounded
from application.cloud.manifest import _unique, byte_hash, canonical_bytes, load_json, safe_component, safe_relative
from application.cloud.protocol import CloudError, PublishReceipt
from application.cloud.safe_files import read_bounded, stage_author_input
from application.cloud.synced_folder import SyncedFolderCloudTransport
from application.config import ProductConfig
from application.platform.paths import overlapping
from application.platform.private_files import create_private_directory, require_private, write_private_new
from application.platform.supervision import _local_path


PROFILE_KEYS = {'schema_version', 'executable', 'executable_sha256', 'rclone_config_ref', 'remote_alias',
                'drive_root_folder_id', 'root_id', 'private_work_root', 'timeout_seconds', 'max_listing_bytes', 'max_transfer_bytes'}
RESULT_PREFIXES = ('receipts/', 'reports/', 'capabilities/', 'research/', 'candidates/', 'paper/', 'live/')
AUTHOR_PREFIXES = ('inbox/strategies/', 'datasets/')
PRIVATE_FIELDS = {'provider_account_id', 'account_id', 'account_ref', 'order_id', 'fill_id', 'provider_order_id',
                  'provider_fill_id', 'raw_response', 'raw_provider_response', 'signature', 'signatures', 'local_path',
                  'machine_username', 'account_balance', 'private_ip', 'ip_inventory', 'local_ip', 'host_ip'}


def _operational_boundary(function):
    @wraps(function)
    def call(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except CloudError:
            raise
        except (OSError, ValueError):
            raise CloudError('UNAVAILABLE', 'BRIDGE_LOCAL_IO_UNAVAILABLE') from None
    return call


def _private_key(name):
    normalized = re.sub(r'[\s-]+', '_', name.strip()).lower()
    return normalized in PRIVATE_FIELDS or normalized.replace('_', '') in {name.replace('_', '') for name in PRIVATE_FIELDS}


def _private_text(value):
    return re.search(r'(?i)(api[_ -]?(key|secret)|password|access[_ -]?token)\s*[:=]|-----BEGIN .*PRIVATE KEY|[A-Z]:[\\/]|\\\\[^\\]+\\|/(?:home|Users|root)/', value) is not None


def _digest(path):
    _local_path(path)
    if not path.is_file():
        raise CloudError('CLOUD_NOT_CONNECTED', 'BRIDGE_LOCAL_REFERENCE_MISSING')
    result = hashlib.sha256()
    with path.open('rb') as stream:
        while raw := stream.read(1024 * 1024):
            result.update(raw)
    return 'sha256:' + result.hexdigest()


def _absolute(value):
    if not isinstance(value, str):
        raise CloudError('BLOCKED', 'BRIDGE_LOCAL_PATH_REQUIRED')
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts or '\x00' in value:
        raise CloudError('BLOCKED', 'BRIDGE_LOCAL_PATH_REQUIRED')
    _local_path(path)
    return path


def _integer(value, lower, upper):
    if type(value) is not int or not lower <= value <= upper:
        raise CloudError('BLOCKED', 'BRIDGE_BOUNDED_POLICY_REQUIRED')
    return value


@dataclass(frozen=True)
class BridgeProfile:
    product_config: ProductConfig
    profile_path: Path
    profile_hash: str
    executable: Path
    executable_sha256: str
    rclone_config_ref: Path
    remote_alias: str
    drive_root_folder_id: str
    root_id: str
    private_work_root: Path
    timeout_seconds: int
    max_listing_bytes: int
    max_transfer_bytes: int


def load_bridge_profile(path, config):
    if not isinstance(config, ProductConfig) or config.cloud_root is None:
        raise CloudError('CLOUD_NOT_CONNECTED', 'BRIDGE_PROFILE_NOT_CONFIGURED')
    try:
        path = _absolute(str(path))
        if overlapping(path, config.cloud_root):
            raise CloudError('BLOCKED', 'BRIDGE_PROFILE_MUST_BE_LOCAL')
        with path.open('rb') as stream:
            raw = stream.read(65537)
        values = load_json(raw)
        if set(values) != PROFILE_KEYS or values['schema_version'] != 'r7-rclone-bridge-config-v0.2':
            raise CloudError('BLOCKED', 'BRIDGE_PROFILE_SCHEMA_INVALID')
        executable = _absolute(values['executable'])
        expected = values['executable_sha256']
        if not isinstance(expected, str) or not re.fullmatch('sha256:[0-9a-f]{64}', expected) or _digest(executable) != expected:
            raise CloudError('BLOCKED', 'BRIDGE_EXECUTABLE_IDENTITY_MISMATCH')
        reference, work = _absolute(values['rclone_config_ref']), _absolute(values['private_work_root'])
        if (overlapping(reference, config.cloud_root) or overlapping(work, config.cloud_root)
                or not work.is_relative_to(config.local_data_root) or work == config.local_data_root):
            raise CloudError('BLOCKED', 'BRIDGE_PRIVATE_REFERENCES_MUST_BE_LOCAL')
        require_private(reference)  # Permissions only; never open OAuth bytes.
        require_private(work, directory=True)
        alias, drive_id = values['remote_alias'], values['drive_root_folder_id']
        if not isinstance(alias, str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_-]{0,63}', alias):
            raise CloudError('BLOCKED', 'BRIDGE_REMOTE_ALIAS_INVALID')
        if not isinstance(drive_id, str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{9,127}', drive_id):
            raise CloudError('BLOCKED', 'BRIDGE_SELECTED_ROOT_ID_REQUIRED')
        root_id = safe_component(values['root_id'])
        SyncedFolderCloudTransport(config.cloud_root, expected_root_id=root_id)._check_root()
        return BridgeProfile(config, path, byte_hash(raw), executable, expected, reference, alias, drive_id, root_id, work,
            _integer(values['timeout_seconds'], 1, 300), _integer(values['max_listing_bytes'], 4096, 8*1024*1024),
            _integer(values['max_transfer_bytes'], 4096, 16*1024**3))
    except CloudError:
        raise
    except Exception:
        raise CloudError('CLOUD_NOT_CONNECTED', 'BRIDGE_LOCAL_PROFILE_UNAVAILABLE') from None


class RcloneBridge:
    def __init__(self, profile, *, runner=None):
        runner = run_bounded if runner is None else runner
        if type(profile) is not BridgeProfile or not callable(runner):
            raise ValueError('Trusted locally provisioned bridge required')
        self.profile, self.runner = profile, runner
        self.stage = SyncedFolderCloudTransport(profile.product_config.cloud_root, expected_root_id=profile.root_id)
        self.deadline = None

    def validate_publication(self, logical_path, payloads, manifest_bytes):
        """Validate the same immutable bytes before staging and before upload.

        The configured stage may have its own synchronization client. Rejected
        content must never reach that folder, even if our copy bridge is offline.
        """
        safe_relative(logical_path)
        if not logical_path.startswith(RESULT_PREFIXES):
            raise CloudError('BLOCKED', 'BRIDGE_AUTHOR_NAMESPACE_READ_ONLY')
        if not payloads or len(payloads) > 32:
            raise CloudError('BLOCKED', 'BRIDGE_RESULT_MANIFEST_INVALID')
        folded = set()
        for relative, raw in payloads.items():
            safe_relative(relative)
            if relative.casefold() in folded or relative.casefold() == 'manifest.json':
                raise CloudError('BLOCKED', 'BRIDGE_RESULT_PATH_COLLISION')
            folded.add(relative.casefold())
            if not isinstance(raw, bytes) or len(raw) > 256*1024:
                raise CloudError('BLOCKED', 'BRIDGE_PUBLICATION_PAYLOAD_LIMIT')
            if logical_path.startswith('reports/feedback/'):
                continue
            if not relative.endswith('.json'):
                raise CloudError('BLOCKED', 'BRIDGE_PUBLICATION_MEDIA_NOT_IMPLEMENTED')
            stack = [load_json(raw, 256*1024)]
            while stack:
                value = stack.pop()
                if isinstance(value, dict):
                    if any(_private_key(key) for key in value):
                        raise CloudError('BLOCKED', 'BRIDGE_PRIVATE_PROVIDER_FIELD_FORBIDDEN')
                    stack.extend(value.values())
                elif isinstance(value, list):
                    stack.extend(value)
                elif isinstance(value, str) and _private_text(value):
                    raise CloudError('BLOCKED', 'BRIDGE_PRIVATE_CONTENT_FORBIDDEN')
        if logical_path.startswith('reports/feedback/'):
            from application.cloud.feedback import FeedbackError
            from application.cloud.public_feedback import validate_public_feedback_publication
            try:
                validate_public_feedback_publication(logical_path, payloads)
            except (FeedbackError, ValueError, TypeError):
                raise CloudError('BLOCKED', 'BRIDGE_FEEDBACK_BUNDLE_INVALID') from None
        if sum(map(len, payloads.values())) + manifest_bytes > self.profile.max_transfer_bytes:
            raise CloudError('BLOCKED', 'BRIDGE_TRANSFER_BUDGET')

    def _start(self):
        self.deadline = time.monotonic() + self.profile.timeout_seconds
        self.stage._check_root()

    def _remote(self, relative=''):
        if relative and relative != '.r7-root.json':
            safe_relative(relative)
        return self.profile.remote_alias + ':' + relative

    def _execute(self, operation, *arguments, limit=None):
        if operation not in ('lsjson', 'cat', 'copyto', 'copy'):
            raise ValueError('Copy-only bridge operation required')
        remaining = math.ceil(self.deadline - time.monotonic())
        if remaining <= 0:
            raise CloudError('UNAVAILABLE', 'BRIDGE_DEADLINE_EXCEEDED')
        profile = self.profile
        if _digest(profile.profile_path) != profile.profile_hash or _digest(profile.executable) != profile.executable_sha256:
            raise CloudError('CONFLICT', 'BRIDGE_LOCAL_CONFIGURATION_CHANGED')
        require_private(profile.rclone_config_ref)
        require_private(profile.private_work_root, directory=True)
        argv = [str(profile.executable), operation, *arguments, '--config', str(profile.rclone_config_ref),
                '--drive-root-folder-id', profile.drive_root_folder_id, '--drive-skip-shortcuts',
                '--retries', '1', '--low-level-retries', '1', '--log-level', 'ERROR',
                '--cache-dir', str(profile.private_work_root / 'rclone-cache')]
        result = self.runner(argv, private_root=profile.private_work_root, timeout_seconds=min(profile.timeout_seconds, remaining),
                             stdout_limit=profile.max_listing_bytes if limit is None else limit)
        if (type(result) is not CommandResult or not result.tree_reaped or result.status != 'COMPLETE'
                or result.exit_code != 0 or not isinstance(result.stdout, bytes)):
            raise CloudError('UNAVAILABLE', 'BRIDGE_OWNED_COMMAND_FAILED')
        bound = profile.max_listing_bytes if limit is None else limit
        if len(result.stdout) > bound:
            raise CloudError('BLOCKED', 'BRIDGE_OUTPUT_LIMIT')
        return result.stdout

    def _listing(self):
        raw = self._execute('lsjson', self._remote(), '--recursive', '--hash', '--no-modtime')
        try:
            rows = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique,
                              parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
                              parse_float=lambda _: (_ for _ in ()).throw(ValueError()))
        except (ValueError, UnicodeError, RecursionError):
            raise CloudError('BLOCKED', 'BRIDGE_REMOTE_LIST_INVALID') from None
        if not isinstance(rows, list) or len(rows) > 4096:
            raise CloudError('BLOCKED', 'BRIDGE_REMOTE_LIST_LIMIT')
        result, folded = {}, set()
        for row in rows:
            if not isinstance(row, dict) or type(row.get('IsDir')) is not bool or not isinstance(row.get('Path'), str):
                raise CloudError('BLOCKED', 'BRIDGE_REMOTE_ENTRY_INVALID')
            path = row['Path']
            if path != '.r7-root.json':
                safe_relative(path)
            if row.get('Name') != path.rsplit('/', 1)[-1]:
                raise CloudError('BLOCKED', 'BRIDGE_REMOTE_NAME_MISMATCH')
            if path.casefold() in folded:
                raise CloudError('CONFLICT', 'BRIDGE_DUPLICATE_REMOTE_NAME')
            folded.add(path.casefold())
            if not row['IsDir']:
                _integer(row.get('Size'), 0, 16*1024**3)
                result[path] = row
        try:
            marker = load_json(self._execute('cat', self._remote('.r7-root.json'), '--head', '4097', limit=4097), 4096)
        except CloudError:
            raise CloudError('CLOUD_NOT_CONNECTED', 'BRIDGE_REMOTE_ROOT_UNAVAILABLE') from None
        if marker != {'root_id': self.profile.root_id}:
            raise CloudError('CLOUD_NOT_CONNECTED', 'BRIDGE_REMOTE_ROOT_IDENTITY_MISMATCH')
        return result

    def _readback(self, relative, expected):
        raw = self._execute('cat', self._remote(relative), '--head', str(len(expected)+1), limit=len(expected)+1)
        if raw != expected:
            raise CloudError('CONFLICT', 'BRIDGE_REMOTE_BYTES_DIFFER')

    @_operational_boundary
    def pull_once(self):
        """Download a bounded author batch, then stage payloads before envelopes.

        Downloads stay in a fresh private generation until the entire batch
        passes listing/actual-byte checks. Intake owns readiness, E2 validation
        and accepted-submission conflict handling; no cloud file is executed.
        """
        self._start()
        listing = self._listing()
        selected = {path: row for path, row in listing.items() if path.startswith(AUTHOR_PREFIXES)}
        total = sum(row['Size'] for row in selected.values())
        if len(selected) > 4096 or total > self.profile.max_transfer_bytes:
            raise CloudError('BLOCKED', 'BRIDGE_TRANSFER_BUDGET')
        for relative, row in selected.items():
            suffix = Path(relative).suffix.lower()
            limit = 64*1024*1024 if relative.startswith('datasets/') and suffix == '.parquet' else (
                64*1024 if suffix == '.md' or Path(relative).name in ('manifest.json', 'dataset.json') else 256*1024)
            if suffix not in ('.json', '.md', '.parquet') or (suffix == '.parquet' and not relative.startswith('datasets/')):
                raise CloudError('BLOCKED', 'BRIDGE_AUTHOR_MEDIA_FORBIDDEN')
            if row['Size'] > limit:
                raise CloudError('BLOCKED', 'BRIDGE_AUTHOR_FILE_LIMIT')
            hashes = row.get('Hashes')
            if not isinstance(hashes, dict) or not any(
                isinstance(hashes.get(name), str) and re.fullmatch(pattern, hashes[name])
                for name, pattern in (('SHA-256', '[0-9a-f]{64}'), ('MD5', '[0-9a-f]{32}'))):
                raise CloudError('BLOCKED', 'BRIDGE_REMOTE_BYTE_HASH_REQUIRED')
        generation = self.profile.private_work_root / ('download-' + uuid.uuid4().hex)
        create_private_directory(generation)
        for relative, row in sorted(selected.items()):
            target = generation / relative
            for parent in reversed(target.parent.parents):
                if parent.is_relative_to(generation) and not parent.exists():
                    create_private_directory(parent)
            if not target.parent.exists():
                create_private_directory(target.parent)
            self._execute('copyto', self._remote(relative), str(target), '--immutable', '--checksum',
                          '--transfers', '1', '--checkers', '1', '--max-size', str(row['Size'])+'B',
                          '--max-transfer', str(self.profile.max_transfer_bytes)+'B',
                          '--max-duration', str(self.profile.timeout_seconds)+'s', limit=4096)
            require_private(target)
            if target.stat().st_size != row['Size']:
                raise CloudError('INCOMPLETE_SYNC', 'BRIDGE_DOWNLOAD_SIZE_CHANGED')
            hashes = row['Hashes']
            algorithm = 'sha256' if hashes.get('SHA-256') else 'md5'
            digest = hashlib.new(algorithm)
            with target.open('rb') as stream:
                while chunk := stream.read(1024*1024):
                    digest.update(chunk)
            if digest.hexdigest() != hashes['SHA-256' if algorithm == 'sha256' else 'MD5']:
                raise CloudError('INCOMPLETE_SYNC', 'BRIDGE_DOWNLOAD_BYTES_CHANGED')
        current = {path: row for path, row in self._listing().items() if path.startswith(AUTHOR_PREFIXES)}
        if selected != current:
            raise CloudError('INCOMPLETE_SYNC', 'BRIDGE_AUTHOR_BATCH_CHANGED')
        self.stage._check_root()
        for relative in sorted(selected, key=lambda path: (Path(path).name in ('manifest.json', 'dataset.json'), path)):
            target = generation / relative
            require_private(target)
            with target.open('rb') as stream:
                raw = stream.read(selected[relative]['Size']+1)
            if len(raw) != selected[relative]['Size']:
                raise CloudError('INCOMPLETE_SYNC', 'BRIDGE_DOWNLOAD_SIZE_CHANGED')
            hashes = selected[relative]['Hashes']
            algorithm = 'sha256' if hashes.get('SHA-256') else 'md5'
            if hashlib.new(algorithm, raw).hexdigest() != hashes['SHA-256' if algorithm == 'sha256' else 'MD5']:
                raise CloudError('INCOMPLETE_SYNC', 'BRIDGE_DOWNLOAD_BYTES_CHANGED')
            stage_author_input(self.profile.product_config.cloud_root, relative, raw)
        return dict(status='LOCAL_STAGED', files_staged=len(selected), bytes_staged=total,
                    transport_kind='COPY_BRIDGE', root_id=self.profile.root_id)

    @_operational_boundary
    def import_dataset(self, dataset_id, revision):
        """Seal transport bytes locally; E1 logical/OOS verification stays later.

        This explicit offline step does not select a dataset/research policy,
        relabel its namespace or decode any Parquet financial columns.
        """
        from application.datasets.catalog import DatasetCatalog, DatasetError, read_local
        safe_component(dataset_id);safe_component(revision)
        self.stage._check_root()
        source=self.profile.product_config.cloud_root/'datasets'/dataset_id/revision
        try:
            raw_manifest=read_bounded(source,'dataset.json',65536)
            manifest=DatasetCatalog(source).load('dataset.json')
            value=manifest.as_dict()
            if (value['dataset_id'],value['dataset_version'])!=(dataset_id,revision):
                raise CloudError('BLOCKED','BRIDGE_DATASET_IDENTITY_MISMATCH')
            containers=list(value['candles'])
            if value['funding']['mode']=='RECORDED':containers.append(value['funding'])
            payloads={'dataset.json':raw_manifest}
            for container in containers:
                raw=read_local(source,container['path'],64*1024*1024)
                if byte_hash(raw)!=container['byte_hash']:
                    raise CloudError('INCOMPLETE_SYNC','BRIDGE_DATASET_BYTE_HASH_MISMATCH')
                payloads[container['path']]=raw
            if read_bounded(source,'dataset.json',65536)!=raw_manifest:
                raise CloudError('INCOMPLETE_SYNC','BRIDGE_DATASET_MANIFEST_CHANGED')
            if sum(map(len,payloads.values()))>self.profile.max_transfer_bytes:
                raise CloudError('BLOCKED','BRIDGE_TRANSFER_BUDGET')
            target=self.profile.product_config.local_data_root/'datasets'/dataset_id/revision
            _local_path(target)
            if target.exists():
                require_private(target,directory=True)
                for relative,raw in payloads.items():
                    require_private(target/relative)
                    if read_local(target,relative,64*1024*1024)!=raw:
                        raise CloudError('CONFLICT','BRIDGE_LOCAL_DATASET_CHANGED')
            else:
                generation=self.profile.private_work_root/('dataset-import-'+uuid.uuid4().hex)
                create_private_directory(generation)
                for relative,raw in payloads.items():
                    path=generation/relative
                    for parent in reversed(path.parent.parents):
                        if parent.is_relative_to(generation) and not parent.exists():create_private_directory(parent)
                    if not path.parent.exists():create_private_directory(path.parent)
                    write_private_new(path,raw)
                for parent in (target.parent.parent,target.parent):
                    if not parent.exists():create_private_directory(parent)
                    require_private(parent,directory=True)
                os.rename(generation,target)  # Fresh generation only; never merge/replace.
            return dict(status='LOCAL_DATASET_STAGED',dataset_id=dataset_id,dataset_version=revision,
                        manifest_hash=manifest.manifest_hash,files_staged=len(payloads),
                        logical_verification='NOT_RUN',namespace=value['namespace'],financial_authority='NONE')
        except CloudError:
            raise
        except DatasetError:
            raise CloudError('BLOCKED','BRIDGE_DATASET_MANIFEST_INVALID') from None
        except (OSError,ValueError):
            raise CloudError('UNAVAILABLE','BRIDGE_LOCAL_DATASET_STAGE_FAILED') from None

    @_operational_boundary
    def push_bundle(self, logical_path):
        safe_relative(logical_path)
        if not logical_path.startswith(RESULT_PREFIXES):
            raise CloudError('BLOCKED', 'BRIDGE_AUTHOR_NAMESPACE_READ_ONLY')
        self._start()
        root = self.profile.product_config.cloud_root
        raw_manifest = read_bounded(root, logical_path + '/manifest.json', 65536)
        manifest = load_json(raw_manifest)
        if (set(manifest) != {'schema_version', 'operation_id', 'artifact_hash', 'payload_hashes'}
                or manifest['schema_version'] != 'r7-result-bundle-v0.2'
                or not isinstance(manifest['operation_id'], str) or not 1 <= len(manifest['operation_id']) <= 256
                or not isinstance(manifest['payload_hashes'], dict) or not 1 <= len(manifest['payload_hashes']) <= 32):
            raise CloudError('BLOCKED', 'BRIDGE_RESULT_MANIFEST_INVALID')
        payloads, folded = {}, set()
        for relative, expected in manifest['payload_hashes'].items():
            safe_relative(relative)
            if relative.casefold() in folded or relative.casefold() == 'manifest.json':
                raise CloudError('BLOCKED', 'BRIDGE_RESULT_PATH_COLLISION')
            folded.add(relative.casefold())
            raw = read_bounded(root, logical_path + '/' + relative, 256*1024)
            if byte_hash(raw) != expected:
                raise CloudError('CONFLICT', 'BRIDGE_LOCAL_RESULT_HASH_MISMATCH')
            payloads[relative] = raw
        if byte_hash(canonical_bytes(manifest['payload_hashes'])) != manifest['artifact_hash']:
            raise CloudError('CONFLICT', 'BRIDGE_RESULT_IDENTITY_MISMATCH')
        self.validate_publication(logical_path, payloads, len(raw_manifest))
        # Upload the exact validated bytes from a fresh owner-private generation.
        # The synchronized producer files can change while a tool is running.
        snapshot = self.profile.private_work_root / ('publication-' + uuid.uuid4().hex)
        create_private_directory(snapshot)
        for relative, raw in (*sorted(payloads.items()), ('manifest.json', raw_manifest)):
            target = snapshot / relative
            for parent in reversed(target.parent.parents):
                if parent.is_relative_to(snapshot) and not parent.exists():
                    create_private_directory(parent)
            if not target.parent.exists():
                create_private_directory(target.parent)
            write_private_new(target, raw)
        listing = self._listing()
        for relative, raw in (*sorted(payloads.items()), ('manifest.json', raw_manifest)):
            remote = logical_path + '/' + relative
            if remote in listing:
                self._readback(remote, raw)  # Differing originals remain untouched.
            else:
                self._execute('copyto', str(snapshot / relative), self._remote(remote), '--immutable', '--checksum',
                              '--transfers', '1', '--checkers', '1', '--max-transfer', str(self.profile.max_transfer_bytes)+'B',
                              '--max-duration', str(self.profile.timeout_seconds)+'s', limit=4096)
                self._readback(remote, raw)
        # Do not ACK a generation whose producer changed even when the remote
        # safely received the original validated snapshot.
        for relative, raw in (*sorted(payloads.items()), ('manifest.json', raw_manifest)):
            if read_bounded(root, logical_path+'/'+relative, 256*1024) != raw:
                raise CloudError('CONFLICT', 'BRIDGE_LOCAL_RESULT_CHANGED')
        self._listing()  # Detect duplicates added during upload before ACK.
        for relative, raw in (*sorted(payloads.items()), ('manifest.json', raw_manifest)):
            self._readback(logical_path+'/'+relative, raw)
        return PublishReceipt(manifest['operation_id'], 'CLOUD_ACKNOWLEDGED', manifest['artifact_hash'])
