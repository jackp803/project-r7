"""Exact-clean local native PyInstaller build; no download, credentials or hosted compute."""
import argparse
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from application.platform.distribution import seal_distribution, verify_distribution
from application.platform.processes import ResourceLimits, spawn_owned
from strategy.v02.capabilities import _source_revision


def _source(revision):
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    status = subprocess.check_output(['git', 'status', '--porcelain=v1'], cwd=ROOT, text=True).strip()
    if not re.fullmatch(r'[0-9a-f]{40}', revision) or actual != revision or status:
        raise ValueError('Exact clean source revision required for native build')
    return dict(revision=actual, worktree='CLEAN', implementation_hash=_source_revision(ROOT / 'src'))


def _target():
    if sys.version_info[:2] != (3, 12) or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise ValueError('Selected native CPython3.12 x86-64 interpreter required')
    if platform.system() == 'Windows': return 'windows'
    if platform.system() == 'Linux':
        rows = dict(line.split('=', 1) for line in Path('/etc/os-release').read_text(encoding='utf-8').splitlines() if '=' in line)
        if rows.get('ID', '').strip('"') == 'ubuntu' and rows.get('VERSION_ID', '').strip('"') in ('24.04', '26.04'):
            return 'linux'
    raise ValueError('Authorized native Windows or Ubuntu build host required')


def _dependencies(lock):
    values = []
    for line in lock.read_text(encoding='utf-8').splitlines():
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([^\s]+) --hash=sha256:([0-9a-f]{64})', line)
        if match is None: raise ValueError('Complete exact wheel-hash build lock required')
        name, version, wheel_hash = match.groups()
        installed = metadata.distribution(name)
        if installed.version != version: raise ValueError('Installed build dependency does not match lock')
        license_files = []
        for entry in installed.files or ():
            if 'license' in str(entry).casefold() or 'copying' in str(entry).casefold() or 'notice' in str(entry).casefold():
                path = installed.locate_file(entry)
                if path.is_file(): license_files.append((str(entry), path))
        if not license_files: raise ValueError('Dependency license material required before native build')
        values.append(dict(name=name, version=version, wheel_sha256=wheel_hash, licenses=license_files))
    if not values: raise ValueError('Native dependency lock must not be empty')
    return values


def build(output, revision):
    source = _source(revision)
    target = _target()
    output = Path(output)
    if not output.is_absolute(): raise ValueError('Absolute native output root required')
    output = output.resolve()
    if output.is_relative_to(ROOT) or ROOT.is_relative_to(output) or output.exists():
        raise ValueError('Fresh native build root outside executable worktree required')
    lock = ROOT / 'packaging' / target / 'requirements-build-py312.lock'
    dependencies = _dependencies(lock)
    ui = ROOT / 'ui' / 'dist'
    from application.control_api.assets import validate_control_center_assets
    validate_control_center_assets(ui)
    output.mkdir(parents=True, mode=0o700)
    name = 'R7' if target == 'windows' else 'r7'
    argv = [sys.executable, '-m', 'PyInstaller', '--onedir', '--console', '--noupx', '--clean', '--noconfirm',
        '--name', name, '--distpath', str(output / 'dist'), '--workpath', str(output / 'work'),
        '--specpath', str(output / 'spec'), '--paths', str(ROOT / 'src'),
        '--add-data', str(ui) + ':ui', '--collect-submodules', 'uvicorn', '--hidden-import', 'pyarrow.parquet']
    # All canonical modules include trusted late-import owner composition paths.
    # Raw source is additionally retained for the existing Python/SQL commitment.
    for path in sorted((ROOT / 'src').rglob('*')):
        if not path.is_file() or path.suffix not in ('.py', '.sql'): continue
        relative = path.relative_to(ROOT / 'src')
        argv += ['--add-data', str(path) + ':' + (Path('source') / relative.parent).as_posix()]
        if path.suffix == '.py':
            module = '.'.join(relative.with_suffix('').parts)
            if module.endswith('.__init__'): module = module[:-9]
            argv += ['--hidden-import', module]
        else:
            argv += ['--add-data', str(path) + ':' + relative.parent.as_posix()]
    argv.append(str(ROOT / 'packaging' / 'entrypoint.py'))
    log = output / 'pyinstaller.log'
    with log.open('wb') as stream:
        owned = spawn_owned(argv, cwd=ROOT, limits=ResourceLimits(900), stdout=stream, stderr=subprocess.STDOUT)
        code = owned.wait()
    if code != 0 or not owned.termination_report.reaped:
        raise ValueError('Native PyInstaller build failed; retain local build log')
    package = output / 'dist' / name
    shutil.copyfile(ROOT / 'packaging' / target / 'FIRST_RUN.md', package / 'FIRST_RUN.md')
    shutil.copyfile(lock, package / 'requirements-build-py312.lock')
    licenses = package / 'licenses'
    licenses.mkdir()
    license_inventory = []
    for dependency in dependencies:
        for index, (relative, path) in enumerate(dependency['licenses']):
            destination = licenses / (dependency['name'] + '-' + str(index) + '-' + path.name)
            shutil.copyfile(path, destination)
            license_inventory.append(dict(package=dependency['name'], version=dependency['version'],
                installed_relative_path=relative, retained_file=destination.relative_to(package).as_posix(),
                sha256=hashlib.sha256(destination.read_bytes()).hexdigest()))
    # Browser runtime dependencies are separately pinned by package-lock.json.
    for dependency in ('react', 'react-dom', 'scheduler'):
        folder = ROOT / 'ui' / 'node_modules' / dependency
        version = json.loads((folder / 'package.json').read_bytes())['version']
        destination = licenses / ('javascript-' + dependency + '-LICENSE')
        shutil.copyfile(folder / 'LICENSE', destination)
        license_inventory.append(dict(package=dependency, version=version,
            retained_file=destination.relative_to(package).as_posix(), sha256=hashlib.sha256(destination.read_bytes()).hexdigest()))
    (licenses / 'inventory.json').write_text(json.dumps(license_inventory, indent=2) + '\n', encoding='utf-8', newline='\n')
    shutil.copyfile(ROOT / 'ui' / 'package-lock.json', licenses / 'javascript-package-lock.json')
    if _source(revision) != source: raise ValueError('Source changed during native build')
    manifest = seal_distribution(package, source_revision=revision, entrypoint=name + ('.exe' if target == 'windows' else ''),
        dependencies=[dict(name=value['name'], version=value['version']) for value in dependencies])
    if manifest['implementation_hash'] != source['implementation_hash']:
        raise ValueError('Bundled code/resources differ from exact clean source')
    identity = verify_distribution(package)
    archive = output / ('r7-product-0.2.0-' + target + '-' + revision[:7] + '.zip')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as stream:
        for path in sorted(package.rglob('*')):
            if path.is_file(): stream.write(path, path.relative_to(package.parent).as_posix())
    result = dict(source=source, identity=identity, target=target, package_name=name,
        archive=archive.name, archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        files=len(manifest['files']), python=platform.python_version(), os_version=platform.version(),
        glibc=platform.libc_ver() if target == 'linux' else None, build='LOCAL_NATIVE', native_acceptance='NOT_RUN',
        provider_requests=0, credentials='NONE', capital='NONE', github_compute='NOT_USED')
    (output / 'build-result.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(result))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--expected-revision', required=True)
    args = parser.parse_args()
    try:
        build(args.output, args.expected_revision)
        return 0
    except (ValueError, OSError, subprocess.SubprocessError):
        print('R7 native build failed validation; retain available build log', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
