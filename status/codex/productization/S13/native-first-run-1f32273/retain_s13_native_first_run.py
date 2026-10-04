from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

project = Path(__file__).resolve().parent.parent
root = project / 'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0, str(root / 'src'))
from application.qualification import _sanitize, revision_fact
from application.platform.distribution import verify_distribution

revision = '1f322735a49fb76e7ea0b2408b2f045c13684f61'
assert revision_fact(root, revision, True) == dict(revision=revision, worktree='CLEAN')
build_root = project / 'artifacts/r7-native-windows-foundation-1f32273'
smoke_root = project / 'artifacts/r7-native-windows-first-run-1f32273'
package = build_root / 'dist/R7'
build = json.loads((build_root / 'build-result.json').read_bytes())
smoke = json.loads((smoke_root / 'native-smoke.json').read_bytes())
assert build['source']['revision'] == revision and build['source']['worktree'] == 'CLEAN'
assert smoke['passed'] and smoke['scenario_count'] == 5 and len(smoke['commands']) == 6
assert all(value['passed'] and value['tree_reaped'] for value in smoke['commands'])
assert all(value['passed'] for value in smoke['http_assertions'])
assert verify_distribution(package) == smoke['identity'] == build['identity']
assert smoke['licensed_packages']['CPython'] == '3.12.10'
archive = build_root / build['archive']
assert hashlib.sha256(archive.read_bytes()).hexdigest() == build['archive_sha256']

target = root / 'status/codex/productization/S13/native-first-run-1f32273'
assert not target.exists()
target.mkdir(parents=True)
entries = []

def retain(source, relative, *, sanitize=False):
    original = source.read_bytes()
    raw = _sanitize(original.decode('utf-8', errors='strict').replace('\r\n', '\n'), root).encode('utf-8') if sanitize else original
    destination = target / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    entries.append(dict(file=relative, original_sha256=hashlib.sha256(original).hexdigest(),
                        retained_sha256=hashlib.sha256(raw).hexdigest(), normalization='UTF8/CRLF_TO_LF/LOCAL_PATH_SANITIZATION' if sanitize else 'NONE'))

for source, relative in ((build_root / 'build-result.json', 'build-result.json'),
                         (package / 'distribution.json', 'distribution.json'),
                         (package / 'licenses/inventory.json', 'license-inventory.json'),
                         (smoke_root / 'native-smoke.json', 'native-smoke.json')):
    retain(source, relative)
retain(build_root / 'pyinstaller.log', 'pyinstaller.log', sanitize=True)
for command in smoke['commands']:
    source = smoke_root / command['log']
    assert hashlib.sha256(source.read_bytes()).hexdigest() == command['log_sha256']
    retain(source, 'smoke/' + source.name, sanitize=True)
for source in sorted((project / 'artifacts').glob('S13-*.log')):
    retain(source, 'development/' + source.name, sanitize=True)
for short in ('da55207', '423f30a', 'a9bcf37'):
    previous = project / ('artifacts/r7-native-windows-first-run-' + short)
    if (previous / 'native-smoke.json').exists():
        retain(previous / 'native-smoke.json', 'historical/' + short + '/native-smoke.json')
for source in (project / 'artifacts/native-build-dependency-license-inventory.json',
               project / 'artifacts/native-build-dependency-install.json'):
    retain(source, 'dependencies/' + source.name, sanitize=True)
retain(Path(__file__), 'retain_s13_native_first_run.py', sanitize=True)
context = dict(evidence_retained_at_utc=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
    source_before=build['source'], full_exact_clean_qualification='NOT_RUN_FOR_THIS_CANDIDATE',
    accepted_full_executable_revision='965bfb7bf8eca83831325a3ebce562764599dc1d',
    scope='Actual Windows native diagnostic first-run/control/migration/restart/auth/Host/Origin/resource-integrity smoke only',
    timing='Per-native-command UTC start/finish was not recorded by this first-run harness; final S15 acceptance must add actual timing',
    license_scope='Actual selected CPython and exact26 Python/build distributions plus3 JavaScript runtime packages',
    binary_retention=dict(location='LOCAL_PROJECT_ARTIFACT', project_relative_path=archive.relative_to(project).as_posix(),
                         bytes=archive.stat().st_size, sha256=build['archive_sha256']),
    limitations=['S12/S13 IN_PROGRESS', 'Research/runtime supervision/recovery NOT_RUN', 'Ubuntu24.04/26.04 NOT_RUN',
                 'No real cloud/dataset/forward/provider/capital commissioning', 'Unsigned inventory is not E7 admission/release authority'])
(target / 'context.json').write_text(json.dumps(context, indent=2) + '\n', encoding='utf-8', newline='\n')
(target / 'original-to-retained.json').write_text(json.dumps(entries, indent=2) + '\n', encoding='utf-8', newline='\n')
manifest = {path.relative_to(root).as_posix(): 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(target.rglob('*')) if path.is_file()}
(target.parent / 'native-first-run-artifact-hashes-1f32273.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
progress_path = root / 'coordination/CODEX/PROGRESS.json'
progress = json.loads(progress_path.read_bytes())
progress['platforms']['windows-11-x86_64'].update(native_package_status='IN_PROGRESS',
    native_first_run_status='PASS', native_first_run_revision=revision, native_first_run_scenarios=5,
    native_first_run_commands=6, native_first_run_build_hash=build['identity']['build_hash'],
    native_archive_sha256=build['archive_sha256'], native_full_product_acceptance='NOT_RUN')
progress['tests_executed'].append(dict(step='S13', phase='NATIVE_FIRST_RUN_ONLY', revision=revision,
    result='PASS', commands=6, scenarios=5, failures=0, errors=0, skips=0,
    build_hash=build['identity']['build_hash'], full_qualification='NOT_RUN_FOR_THIS_CANDIDATE'))
progress['evidence_refs'].append(target.relative_to(root).as_posix() + '/native-smoke.json')
progress_path.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
handoff_path = root / 'coordination/CODEX/HANDOFF.md'
handoff = handoff_path.read_text(encoding='utf-8')
marker = 'Active step: S13 native first-run/build foundation and remaining S12 production composition. S12 and S13 remain IN_PROGRESS; no milestone exit.'
assert marker in handoff
handoff = handoff.replace(marker, marker + '\n\nNative first-run candidate `' + revision + '` has actual local Windows build1035 files, '
    'CPython/exact dependencies license inventory, and5 native scenarios/6 owned commands PASS with empty product PATH/PYTHONPATH unset. '
    'Native build hash `' + build['identity']['build_hash'] + '`. Evidence: ' + target.relative_to(root).as_posix() + '. '
    'This is scoped native first-run/control evidence; full qualification for this source/native product remains NOT_RUN. '
    'The last complete qualified executable remains965bfb7. Continue actual research/runtime process supervision, services/SSH '
    'and backup/restore; then full native/product qualification. No checkpoint stop.\n', 1)
handoff_path.write_text(handoff, encoding='utf-8', newline='\n')
(target.parent / 'NATIVE_FIRST_RUN_RESULT.md').write_text('# S13 scoped native first-run result\n\n'
    'Executable `' + revision + '` built from exact CLEAN Windows11/CPython3.12.10 source;1035 files. '
    'Build hash `' + build['identity']['build_hash'] + '`. Actual native5 scenarios/6 commands PASS; all owned trees reaped. '
    'Empty product PATH and PYTHONPATH unset; Chinese/spaced roots,16 actual canonical migrations, control restart, '
    'anonymous/foreign Host/Origin denial and controlled tampered-migration denial. Matching interpreter/dependency/license file hashes verified.\n\n'
    'Scope is native first-run diagnostics and uncommissioned authenticated control only. Full exact-clean tests for this source, '
    'isolated research/runtime/service/recovery and final native acceptance remain pending. S12/S13 IN_PROGRESS, Ubuntu24.04/26.04 NOT_RUN. '
    'Accepted complete executable remains965bfb7bf8eca83831325a3ebce562764599dc1d. Per-command UTC timing was not recorded in the initial native harness '
    'and must be implemented for S15. Historical failed candidates are preserved, not inherited. SELF_REVIEW. Provider requests0, credentialsNONE, '
    'capitalNONE, trading/PAPER/LIVE NOT_STARTED, runtime LLM0, GitHub computeNOT_USED; main not merged.\n', encoding='utf-8', newline='\n')
subprocess.run(['git', '-c', 'core.autocrlf=false', 'add', '-f', *manifest], cwd=root, check=True)
for relative, expected in manifest.items():
    assert 'sha256:' + hashlib.sha256(subprocess.check_output(['git', 'show', ':' + relative], cwd=root)).hexdigest() == expected
print(json.dumps(dict(revision=revision, native_scenarios=5, native_commands=6, retained_artifacts=len(manifest),
                      full_qualification='NOT_RUN_FOR_THIS_CANDIDATE', native_build_hash=build['identity']['build_hash'])))
