"""Local native first-run smoke with no Python/Node/PYTHONPATH in product environment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from application.platform.distribution import verify_distribution
from application.platform.processes import ResourceLimits, spawn_owned, terminate_owned

DENIAL_STATUSES = {'HOST': 400, 'ORIGIN': 403, 'ANONYMOUS': 401}


def verify(package, output):
    package, output = Path(package).resolve(), Path(output)
    if not output.is_absolute() or output.exists() or output.resolve().is_relative_to(package):
        raise ValueError('Fresh absolute smoke root outside native installation required')
    identity = verify_distribution(package)
    manifest = json.loads((package / 'distribution.json').read_bytes())
    licenses = json.loads((package / 'licenses' / 'inventory.json').read_bytes())
    licensed = {value['package']: value['version'] for value in licenses}
    required = {value['name']: value['version'] for value in manifest['dependencies']}
    required['CPython'] = manifest['python']
    if any(licensed.get(name) != version for name, version in required.items()):
        raise ValueError('Exact native dependency/interpreter license inventory required')
    for value in licenses:
        relative = value['retained_file']
        if manifest['files'].get(relative) != 'sha256:' + value['sha256']:
            raise ValueError('Retained native license hash must match actual sealed file')
    executable = package / manifest['entrypoint']
    output.mkdir(parents=True, mode=0o700)
    cwd = output / '空白 中文 工作目錄'
    cwd.mkdir()
    env = {key: os.environ[key] for key in ('SystemRoot', 'WINDIR', 'SystemDrive', 'TEMP', 'TMP') if key in os.environ}
    env.update(PATH='', PYTHONUTF8='1')
    config, data = output / '設定 空格.json', output / '本機 中文 資料'
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    commands, scenarios = [], []
    report = dict(profile='r7-native-first-run-smoke-v0.2', identity=identity, passed=False,
        commands=commands, scenarios=scenarios, http_assertions=[], product_path='EMPTY', pythonpath='UNSET', node='UNAVAILABLE_ON_PATH',
        actual_provider_requests=0, credentials='NONE', capital='NONE', runtime='NOT_STARTED',
        paper='NOT_STARTED', github_compute='NOT_USED', ubuntu='NOT_RUN')
    report['licensed_packages'] = licensed

    def persist():
        (output / 'native-smoke.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')

    def command(label, arguments, expected=0):
        log = output / (label + '.log')
        with log.open('wb') as stream:
            owned = spawn_owned([str(executable), *arguments], cwd=cwd, limits=ResourceLimits(45),
                                stdout=stream, stderr=subprocess.STDOUT, env=env)
            code = owned.wait()
        record = dict(name=label, exit_code=code, expected_exit_code=expected,
            tree_reaped=owned.termination_report.reaped, log=log.name,
            log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(), passed=code == expected and owned.termination_report.reaped)
        commands.append(record)
        persist()
        if not record['passed']: raise ValueError('Native command smoke failed')
        return log.read_text(encoding='utf-8')

    def get(path, *, headers=None, expected=200):
        request = Request(f'http://127.0.0.1:{port}{path}', headers=headers or {})
        try:
            with urlopen(request, timeout=3) as response: code, raw = response.status, response.read(1024 * 1024)
        except HTTPError as error: code, raw = error.code, error.read(1024 * 1024)
        report['http_assertions'].append(dict(path=path, actual_status=code, expected_status=expected,
            passed=code == expected, response_sha256=hashlib.sha256(raw).hexdigest()))
        if code != expected: raise ValueError('Native loopback HTTP assertion failed')
        return raw

    def server(label):
        log = output / (label + '.log')
        with log.open('wb') as stream:
            owned = spawn_owned([str(executable), 'serve', '--config', str(config)], cwd=cwd,
                limits=ResourceLimits(90), stdout=stream, stderr=subprocess.STDOUT, env=env)
            succeeded = False
            try:
                deadline = time.monotonic() + 35
                while True:
                    if owned.process.poll() is not None: raise ValueError('Native server exited before readiness')
                    try:
                        status = json.loads(get('/api/v1/auth/status'))
                        break
                    except URLError:
                        if time.monotonic() >= deadline: raise ValueError('Native server readiness deadline') from None
                        time.sleep(0.1)
                if status != dict(configured=False, namespace='LOCAL_RESEARCH', enrollment='LOCAL_CLI_ONLY'):
                    raise ValueError('Native first-run authentication state mismatch')
                shell = get('/').decode('utf-8')
                if 'id="root"' not in shell: raise ValueError('Actual built native Control Center missing')
                get('/api/v1/health', expected=DENIAL_STATUSES['ANONYMOUS'])
                get('/api/v1/auth/status', headers={'Host': 'external.invalid'}, expected=DENIAL_STATUSES['HOST'])
                get('/api/v1/auth/status', headers={'Origin': 'http://external.invalid'}, expected=DENIAL_STATUSES['ORIGIN'])
                succeeded = True
            finally:
                termination = terminate_owned(owned, deadline_seconds=5)
                stream.flush()
                commands.append(dict(name=label, tree_reaped=termination.reaped, log=log.name,
                    log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(), passed=succeeded and termination.reaped,
                    assertions=['NATIVE_BUILT_UI', 'UNENROLLED_LOCAL_AUTH', 'ANONYMOUS_API_DENIED', 'FOREIGN_HOST_DENIED', 'FOREIGN_ORIGIN_DENIED']))
                persist()
        if not termination.reaped: raise ValueError('Native control process tree not reaped')

    try:
        doctor = json.loads(command('01-doctor', ['doctor', '--hardware', '--data-root', str(output), '--json']))
        if not doctor['physical_memory_bytes'] > 0 or doctor['gpu_status'] != 'NOT_REQUIRED':
            raise ValueError('Native measured hardware doctor failed')
        scenarios.append(dict(name='NATIVE_HARDWARE_WITH_EMPTY_PATH', result='PASS'))
        profile = json.loads(command('02-init-profile', ['init-profile', '--config', str(config),
            '--data-root', str(data), '--instance-id', 'native-smoke-fixture', '--port', str(port)]))
        settings = json.loads(config.read_bytes())
        if profile['status'] != 'PROFILE_CREATED' or not settings['diagnostic_only'] or settings['paper_runtime_enabled']:
            raise ValueError('Native diagnostic default failed')
        original = config.read_bytes()
        command('03-preserve-profile', ['init-profile', '--config', str(config), '--data-root', str(data)], expected=2)
        if config.read_bytes() != original: raise ValueError('Native existing profile was modified')
        scenarios.append(dict(name='CHINESE_PROFILE_DEFAULTS_AND_PRESERVATION', result='PASS'))
        server('04-first-control-start')
        with sqlite3.connect(data / 'canonical.sqlite3') as db:
            actual = {row[0] for row in db.execute('SELECT migration_name FROM schema_migrations')}
        expected = {Path(name).name for name in manifest['files'] if name.startswith('_internal/storage/migrations/') and name.endswith('.sql')}
        if actual != expected or not actual: raise ValueError('Actual native canonical migrations incomplete')
        scenarios.append(dict(name='ACTUAL_NATIVE_E6_MIGRATIONS', result='PASS', migrations=len(actual)))
        server('05-control-restart')
        scenarios.append(dict(name='CONTROL_RESTART_AUTH_AND_LOOPBACK_DENIAL', result='PASS'))
        migration = package / sorted(name for name in manifest['files'] if name.startswith('_internal/storage/migrations/') and name.endswith('.sql'))[0]
        original_migration = migration.read_bytes()
        try:
            migration.write_bytes(original_migration + b'\n-- SYNTHETIC_NATIVE_TAMPER_FIXTURE\n')
            command('06-tampered-resource-denied', ['doctor', '--hardware', '--data-root', str(output), '--json'], expected=2)
        finally:
            migration.write_bytes(original_migration)
        if verify_distribution(package) != identity: raise ValueError('Native package restoration identity mismatch')
        scenarios.append(dict(name='TAMPERED_MIGRATION_DENIED_BEFORE_START', result='PASS'))
        report['passed'] = True
        report['scenario_count'] = len(scenarios)
        persist()
        print(json.dumps(dict(passed=True, scenarios=len(scenarios), commands=len(commands), build_hash=identity['build_hash'])))
        return 0
    except Exception:
        report['failure'] = 'NATIVE_FIRST_RUN_SMOKE_FAILED'
        persist()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try: return verify(args.package_root, args.output)
    except Exception:
        print('R7 native first-run smoke failed; retain local report and logs', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
