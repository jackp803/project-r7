"""Measured native distribution inventory; neither admission nor signed release authority."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import stat


MANIFEST_NAME = 'distribution.json'
PROFILE = 'r7-native-distribution-v0.2'
_HASH = re.compile(r'sha256:[0-9a-f]{64}')


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('Duplicate native inventory field')
        result[key] = value
    return result


def _relative(value):
    if not isinstance(value, str) or not value or len(value) > 512 or '\\' in value or '\x00' in value:
        raise ValueError('Invalid native inventory path')
    path = PurePosixPath(value)
    if path.is_absolute() or str(path) != value or any(part in ('', '.', '..') or ':' in part for part in path.parts):
        raise ValueError('Invalid native inventory path')
    return value


def _regular(path):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise ValueError('Linked native distribution content forbidden')
    if not stat.S_ISREG(info.st_mode) and not stat.S_ISDIR(info.st_mode):
        raise ValueError('Unsupported native distribution content')
    return info


def _hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024): digest.update(chunk)
    return 'sha256:' + digest.hexdigest()


def _inventory(root):
    root = Path(root).absolute()
    if not stat.S_ISDIR(_regular(root).st_mode): raise ValueError('Native distribution directory required')
    result, names, size = {}, set(), 0
    directories = [root]
    while directories:
        directory = directories.pop()
        with os.scandir(directory) as entries:
            children = sorted(entries, key=lambda item: item.name)
        for child in children:
            path = Path(child.path)
            info = _regular(path)
            if stat.S_ISDIR(info.st_mode):
                directories.append(path)
                continue
            name = _relative(path.relative_to(root).as_posix())
            if name == MANIFEST_NAME: continue
            if name.casefold() in names: raise ValueError('Ambiguous native distribution identity')
            names.add(name.casefold())
            size += info.st_size
            if len(result) >= 10000 or size > 4 * 1024**3:
                raise ValueError('Native distribution inventory limit')
            result[name] = _hash(path)
    return result


def _architecture():
    value = platform.machine().lower()
    if value not in ('amd64', 'x86_64'): raise ValueError('Native x86-64 product required')
    return 'x86_64'


def _validate(payload):
    required = {'profile', 'source_revision', 'implementation_hash', 'entrypoint', 'os', 'architecture',
                'python', 'built_at_utc', 'dependencies', 'files', 'financial_authority'}
    if not isinstance(payload, dict) or set(payload) != required or payload['profile'] != PROFILE:
        raise ValueError('Unsupported native inventory')
    if not isinstance(payload['source_revision'], str) or not re.fullmatch(r'[0-9a-f]{40}', payload['source_revision']):
        raise ValueError('Exact recorded source revision required')
    if not isinstance(payload['implementation_hash'], str) or not _HASH.fullmatch(payload['implementation_hash']):
        raise ValueError('Exact source resource commitment required')
    if payload['os'] not in ('Windows', 'Linux') or payload['os'] != platform.system():
        raise ValueError('Native operating system mismatch')
    if payload['architecture'] != _architecture() or payload['python'] != platform.python_version():
        raise ValueError('Native interpreter or architecture mismatch')
    if not payload['python'].startswith('3.12.') or payload['financial_authority'] != 'NONE':
        raise ValueError('Unsupported native build profile')
    try:
        clock = datetime.fromisoformat(payload['built_at_utc'].replace('Z', '+00:00'))
        if clock.utcoffset() != timezone.utc.utcoffset(clock): raise ValueError()
    except (TypeError, AttributeError, ValueError): raise ValueError('Native build UTC required') from None
    dependencies = payload['dependencies']
    if not isinstance(dependencies, list) or not 1 <= len(dependencies) <= 256:
        raise ValueError('Bounded exact dependency inventory required')
    names = set()
    for dependency in dependencies:
        if not isinstance(dependency, dict) or set(dependency) != {'name', 'version'}:
            raise ValueError('Exact dependency identity required')
        for value in dependency.values():
            if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.+-]{1,128}', value):
                raise ValueError('Invalid dependency identity')
        name = dependency['name'].lower().replace('_', '-').replace('.', '-')
        if name in names: raise ValueError('Duplicate dependency identity')
        names.add(name)
    files = payload['files']
    if not isinstance(files, dict) or not 1 <= len(files) <= 10000:
        raise ValueError('Bounded native file inventory required')
    for name, digest in files.items():
        _relative(name)
        if name == MANIFEST_NAME or not isinstance(digest, str) or not _HASH.fullmatch(digest):
            raise ValueError('Invalid native file commitment')
    entry = _relative(payload['entrypoint'])
    if '/' in entry or entry not in files: raise ValueError('Native executable commitment required')
    return payload


def seal_distribution(root, *, source_revision, entrypoint, dependencies):
    """Build tool only: immutable local inventory with actual bundled source hash."""
    root = Path(root).absolute()
    if (root / MANIFEST_NAME).exists(): raise ValueError('Existing native inventory must be preserved')
    inventory = _inventory(root)
    from strategy.v02.capabilities import _source_revision
    payload = dict(profile=PROFILE, source_revision=source_revision,
        implementation_hash=_source_revision(root / '_internal' / 'source'), entrypoint=entrypoint,
        os=platform.system(), architecture=_architecture(), python=platform.python_version(),
        built_at_utc=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        dependencies=dependencies, files=inventory, financial_authority='NONE')
    _validate(payload)
    raw = _canonical(payload) + b'\n'
    if len(raw) > 1024 * 1024: raise ValueError('Native manifest size limit')
    with (root / MANIFEST_NAME).open('xb') as stream: stream.write(raw)
    return payload


def verify_distribution(root):
    """Verify actual current files. A caller JSON/hash cannot grant any financial permission."""
    root = Path(root).absolute()
    if not stat.S_ISDIR(_regular(root).st_mode): raise ValueError('Native distribution directory required')
    path = root / MANIFEST_NAME
    if not stat.S_ISREG(_regular(path).st_mode): raise ValueError('Native inventory file required')
    with path.open('rb') as stream: raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024: raise ValueError('Native manifest size limit')
    payload = _validate(json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Non-finite native inventory'))))
    if _inventory(root) != payload['files']: raise ValueError('Native code/resource inventory mismatch')
    from strategy.v02.capabilities import _source_revision
    if _source_revision(root / '_internal' / 'source') != payload['implementation_hash']:
        raise ValueError('Native source commitment mismatch')
    return dict(executable_revision=payload['source_revision'], implementation_hash=payload['implementation_hash'],
                build_hash='sha256:' + hashlib.sha256(_canonical(payload)).hexdigest(),
                worktree='UNAVAILABLE', financial_authority='NONE', distribution_profile=PROFILE)
