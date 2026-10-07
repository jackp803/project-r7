"""Run all unchanged browser cases against one real source fixture at a time.

This is local qualification orchestration, not a product memory-gate override.
This run intentionally stages frontend/native build before serial fixtures; earlier failure evidence is not relabelled.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, re, shutil, stat, subprocess, sys, time

project = Path(__file__).resolve().parent.parent
repo = project / 'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0, str(repo / 'src'))
from application.qualification import revision_fact, _sanitize
from application.platform.processes import ResourceLimits, spawn_owned

revision = sys.argv[1]
assert re.fullmatch('[0-9a-f]{40}', revision)
output = project / f'artifacts/r7-productization-S14-feedback-ui-serial-{revision[:7]}'
assert not output.exists()
output.mkdir()
initial = project / f'artifacts/r7-productization-S14-feedback-ui-qualified-{revision[:7]}-safe-logs'
initial_report = json.loads((initial / 'ui-qualification.json').read_bytes())
assert initial_report['qualification_scope'] == 'FRONTEND_ONLY'
assert initial_report['browser_status'] == 'NOT_RUN_PENDING_SERIAL_BROWSER'
assert initial_report['source_before'] == dict(revision=revision, worktree='CLEAN')
assert len(initial_report['commands']) >= 5
assert all(c['passed'] for c in initial_report['commands'][:5])
assert initial_report['commands'][4]['command'] == ['npm', '--prefix', 'ui', 'run', 'build']
node = shutil.which('node')
assert node
cli = repo / 'ui/node_modules/@playwright/test/cli.js'
module = repo / 'ui/node_modules/@playwright/test/index.mjs'
assert cli.is_file() and module.is_file()
profiles = ['empty', 'research', 'paper', 'protected', 'temporal', 'approval', 'deployment']
spec = repo / 'ui/qa/control-center.spec.ts'
source = spec.read_text(encoding='utf-8')
cases = re.findall(r"test\('([^']+)',async\(\{page\}\)=>\{(.*?)(?=\ntest\(|\Z)", source, re.S)
assert len(cases) == 11 and len({title for title, body in cases}) == 11
groups = {profile: [] for profile in profiles}
for title, body in cases:
    found = re.findall(r"await login\(page,'([^']+)'\)", body)
    assert len(found) == 1 and found[0] in groups
    groups[found[0]].append(title)
assert all(groups.values())
stamp = lambda: datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
digest = lambda p: 'sha256:' + hashlib.sha256(p.read_bytes()).hexdigest()

def build_inventory(folder):
    folder = Path(folder)
    root_info = folder.lstat()
    if not stat.S_ISDIR(root_info.st_mode) or stat.S_ISLNK(root_info.st_mode) or getattr(root_info, 'st_file_attributes', 0) & 0x400:
        raise ValueError('LINKED_BROWSER_BUILD_FORBIDDEN')
    result = {}
    for entry in sorted(folder.rglob('*')):
        info = entry.lstat()
        if entry.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('LINKED_BROWSER_BUILD_FORBIDDEN')
        if entry.is_file():
            result[entry.relative_to(folder).as_posix()] = 'sha256:' + hashlib.sha256(entry.read_bytes()).hexdigest()
    if not result or 'index.html' not in result:
        raise ValueError('COMPLETE_BROWSER_BUILD_REQUIRED')
    return result

def require_build(folder, expected):
    if build_inventory(folder) != expected:
        raise ValueError('BROWSER_BUILD_CHANGED')

build_hashes = build_inventory(repo / 'ui/dist')
if 'build_hashes' in initial_report:
    assert build_hashes == initial_report['build_hashes']
native_root = project / f'artifacts/r7-native-windows-S14-feedback-{revision[:7]}'
native_build = json.loads((native_root / 'build-result.json').read_bytes())
assert native_build['identity']['executable_revision'] == revision
native_inventory = json.loads((native_root / 'dist/R7/distribution.json').read_bytes())
assert native_inventory['source_revision'] == revision
native_assets = {name[len('_internal/ui/'):]: value for name, value in native_inventory['files'].items() if name.startswith('_internal/ui/')}
assert native_assets == build_hashes
report = dict(schema_version='r7-local-ui-qualification-v0.2',
    qualification_mode='SERIAL_FIXTURE_BROWSER_QUALIFICATION',
    source_before=revision_fact(repo, revision, True), started_at_utc=stamp(),
    launcher_hash=digest(Path(__file__)), execution='LOCAL', github_compute='NOT_USED',
    real_provider_calls=0, real_credentials='NONE', capital='NONE', passed=False,
    browser_channel='msedge', browser_mode='HEADLESS_ISOLATED_FIXTURE',
    platform=initial_report['platform'], node=initial_report['node'], npm=initial_report['npm'],
    browser_version=initial_report['browser_version'], commands=[],
    frontend_commands=initial_report['commands'][:5],
    initial_attempt=dict(report_sha256=digest(initial / 'ui-qualification.json'),
        status='NOT_RUN_PENDING_SERIAL_BROWSER', browser_cases_executed=0, qualification_scope='FRONTEND_ONLY'),
    expected_cases=[title for title, body in cases],
    original_spec_sha256=digest(spec), original_config_sha256=digest(repo / 'ui/playwright.config.ts'),
    build_hashes=build_hashes, build_hash_capture='SERIAL_BROWSER_START;COMPLETE_INVENTORY_RECHECKED_BEFORE_AND_AFTER_EVERY_FIXTURE',
    native_build_identity=native_build['identity'], native_browser_assets='EXACT_INVENTORY_MATCH',
    unchanged_assertions=True, workers=1, retries=0,
    resource_admission='UNCHANGED_PRODUCT_GATES;ONE_FIXTURE_PROCESS_AT_A_TIME',
    semantics='All unchanged browser assertions run against actual source owners on isolated synthetic profiles. Serial fixture orchestration proves the same browser cases, not seven simultaneous fixture startups, a real trading runtime, external cloud or Linux commissioning.')

def save():
    (output / 'ui-qualification.json').write_text(_sanitize(json.dumps(report, ensure_ascii=False, indent=2), repo) + '\n', encoding='utf-8', newline='\n')

def tests_from(suites):
    for suite in suites:
        for item in suite.get('specs', []):
            yield item
        yield from tests_from(suite.get('suites', []))

save()
observed = []
for index, profile in enumerate(profiles):
    revision_fact(repo, revision, True)
    require_build(repo / 'ui/dist', build_hashes)
    group = output / profile
    group.mkdir()
    config = output / f'{profile}.config.mjs'
    settings = dict(testDir=str(repo / 'ui/qa'), testMatch='*.spec.ts', fullyParallel=False,
        workers=1, timeout=25000, expect=dict(timeout=4000), retries=0,
        outputDir=str(group / 'results'), reporter=[['line'], ['json', dict(outputFile=str(group / 'results.json'))]],
        use=dict(browserName='chromium', channel='msedge', headless=True,
            viewport=dict(width=1440, height=960), actionTimeout=8000, trace='off', video='off', screenshot='off'),
        webServer=dict(command=f'py -3.12 qa/serve_fixture.py --profile {profile} --port {8766+index}',
            cwd=str(repo / 'ui'), url=f'http://127.0.0.1:{8766+index}/api/v1/auth/status',
            reuseExistingServer=False, timeout=90000, stdout='ignore', stderr='pipe'))
    config.write_text('import {defineConfig} from ' + json.dumps(module.as_uri()) + ';\nexport default defineConfig(' + json.dumps(settings) + ');\n', encoding='utf-8', newline='\n')
    pattern = '(?:' + '|'.join(re.escape(title) for title in groups[profile]) + ')$'
    argv = [node, str(cli), 'test', '--config', str(config), '--grep', pattern]
    env = os.environ.copy()
    env.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1', NO_COLOR='1', R7_BROWSER_ARTIFACT_ROOT=str(group))
    log = output / f'{profile}.log'
    started, start = stamp(), time.monotonic()
    item = dict(profile=profile, expected_cases=groups[profile], started_at_utc=started,
        config_sha256=digest(config), command=['node', '<repo>/ui/node_modules/@playwright/test/cli.js', 'test', '--config', config.name, '--grep', pattern],
        passed=False)
    try:
        with log.open('xb') as stream:
            owned = spawn_owned(argv, cwd=repo / 'ui', limits=ResourceLimits(300), stdout=stream, stderr=subprocess.STDOUT, env=env)
            code = owned.wait(timeout=310)
        raw = log.read_bytes()
        text = _sanitize(raw.decode('utf-8', errors='replace'), repo)
        text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text).replace('\r\n', '\n')
        log.write_text(text, encoding='utf-8', newline='\n')
        item.update(exit_code=code, tree_reaped=owned.termination_report.reaped,
            original_log_sha256='sha256:' + hashlib.sha256(raw).hexdigest(), log=log.name, log_sha256=digest(log))
        results_path = group / 'results.json'
        if results_path.is_file():
            actual = json.loads(results_path.read_bytes())
            (output / f'{profile}-browser-results.json').write_text(_sanitize(json.dumps(actual, ensure_ascii=False, indent=2), repo) + '\n', encoding='utf-8', newline='\n')
            entries = list(tests_from(actual['suites']))
            names = [entry['title'] for entry in entries]
            stats = actual['stats']
            item.update(browser_stats=stats, observed_cases=names, errors_count=len(actual.get('errors', [])))
            item['browser_results_sha256'] = digest(output / f'{profile}-browser-results.json')
            details_pass = all(entry['ok'] and len(entry['tests']) == 1 and entry['tests'][0]['status'] == 'expected'
                and len(entry['tests'][0]['results']) == 1 and entry['tests'][0]['results'][0]['status'] == 'passed' for entry in entries)
            item['passed'] = (code == 0 and owned.termination_report.reaped and len(names) == len(groups[profile])
                and set(names) == set(groups[profile]) and stats['expected'] == len(names)
                and stats['unexpected'] == stats['skipped'] == stats['flaky'] == 0
                and not actual.get('errors') and details_pass)
            if item['passed']:
                observed.extend(names)
        else:
            item['failure'] = 'BROWSER_RESULTS_UNAVAILABLE'
    except Exception as exc:
        item.update(failure=type(exc).__name__, passed=False)
        if log.is_file():
            text = _sanitize(log.read_text(encoding='utf-8', errors='replace'), repo)
            log.write_text(re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text).replace('\r\n', '\n'), encoding='utf-8', newline='\n')
            item.update(log=log.name, log_sha256=digest(log))
    item.update(finished_at_utc=stamp(), duration_seconds=time.monotonic()-start, source_after=revision_fact(repo, revision, True))
    try:
        require_build(repo / 'ui/dist', build_hashes)
        item['build_inventory_after'] = 'MATCH'
    except ValueError:
        item.update(build_inventory_after='CHANGED', failure='BROWSER_BUILD_CHANGED', passed=False)
    report['commands'].append(item)
    save()
    print(f'{profile}: {"PASS" if item["passed"] else "FAIL"} ({len(groups[profile])} required cases)', flush=True)
    if not item['passed']:
        break

report['browser_cases_observed'] = observed
complete = len(report['commands']) == len(profiles) and all(c['passed'] for c in report['commands'])
complete = complete and len(observed) == 11 and len(set(observed)) == 11 and set(observed) == set(report['expected_cases'])
if complete:
    images = {'overview.png': 'empty', 'health.png': 'empty', 'supervised-health.png': 'research',
        'protected-paper.png': 'protected', 'approval-preview.png': 'approval', 'deployment-pause.png': 'deployment'}
    missing = [name for name, profile in images.items() if not (output / profile / name).is_file()]
    report['missing_screenshots'] = missing
    complete = not missing
    if complete:
        for name, profile in images.items():
            shutil.copyfile(output / profile / name, output / name)
        report['screenshot_hashes'] = {name: digest(output / name) for name in images}
report.update(source_after=revision_fact(repo, revision, True), finished_at_utc=stamp(), passed=complete,
    tests_passed=len(observed), failures=sum(c.get('browser_stats', {}).get('unexpected', 0) for c in report['commands']),
    skipped=sum(c.get('browser_stats', {}).get('skipped', 0) for c in report['commands']),
    build_hashes=build_hashes,
    input_hashes={name: digest(repo / name) for name in ['ui/package-lock.json', 'ui/src/api.generated.ts', 'contracts/control_api_v0_2.openapi.json']})
save()
print(json.dumps(dict(passed=complete, tests_passed=len(observed), fixture_commands=len(report['commands']))), flush=True)
raise SystemExit(0 if complete else 1)
