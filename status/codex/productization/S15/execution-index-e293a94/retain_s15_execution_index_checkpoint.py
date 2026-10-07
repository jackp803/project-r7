"""Retain reviewed working tools and actual named execution; no requirement PASS."""
from pathlib import Path
import hashlib
import json
import sys

base = Path(__file__).resolve().parent
repo = base.parent / 'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0, str(repo / 'src'))
from application.qualification import _sanitize, parse_result

revision = 'e293a947f886d9814c89983fd9e03151c1695788'
reviewed = {
    's15_execution_index.py': '3480116092811655ab57ad073cb9a97eab0b1d596ace97390d43ba9e7b1aa936',
    'test_s15_execution_index.py': '816d4c99eeeaad77c53eca0afe26a574e7b098f19f3307cf2c6d290c311c3351',
    'run_s15_execution_index_tests.py': '76097a6beaf4ea1dc337c9c5510c081f9c1c42d5a3b23ba95e7badc9037ba9ad',
    'prepare_s15_acceptance_coverage_inventory_v2.py': '94ae973289ff8a077e6201a1afa94ddcc4f7243fe1149ecf93707c61dc8b9c6b',
    'build_s15_execution_index.py': '62f97a46aee2ae6567c23829df172a65903d700d6d0db4de13c64c4caa9a5539',
}
for name, expected in reviewed.items():
    assert hashlib.sha256((base / name).read_bytes()).hexdigest() == expected
index = json.loads((base / 'S15-executed-case-index-e293a94.json').read_bytes())
assert index['candidate_revision'] == revision and index['indexed_execution_instances'] == 1942
assert index['distinct_reported_test_ids'] == 1695 and index['unresolved_static_definitions'] == 0
assert index['requirement_pass_claims'] == 0 and index['requirements_unmapped'] == 66
assert index['source_before'] == index['source_after'] == dict(revision=revision, worktree='CLEAN')
assert index['input_sha256_before'] == index['input_sha256_after']
guard = json.loads((base / 'S15-executed-case-index-reference-order-GREEN.json').read_bytes())
raw = (base / 'S15-executed-case-index-reference-order-GREEN.log').read_bytes()
assert 'sha256:' + hashlib.sha256(raw).hexdigest() == guard['log_sha256']
parsed = parse_result(raw.decode('utf-8').replace('\r\n', '\n'), returncode=guard['exit_code'])
assert parsed.passed and parsed.tests_run == 13 and guard['passed'] and guard['tree_reaped']
assert guard['input_sha256_before'] == guard['input_sha256_after']
for name, expected in guard['input_sha256_before'].items():
    assert 'sha256:' + hashlib.sha256((base / name).read_bytes()).hexdigest() == expected
ref = 'status/codex/productization/S15/execution-index-e293a94'
target = repo / ref
assert not target.exists()
target.mkdir(parents=True)
manifest = {}
mapping = {}
paths = [base / name for name in reviewed]
paths += [base / 'prepare_s15_acceptance_coverage_inventory.py',
          base / 'S15-acceptance-coverage-inventory-4ea0f61.json',
          base / 'S15-acceptance-coverage-inventory-e293a94.json',
          base / 's15_execution_index.before-provenance-review.py',
          base / 'build_s15_execution_index.before-provenance-review.py',
          base / 'build_s15_execution_index.before-source-reference-order-fix.py',
          Path(__file__)]
paths += sorted(base.glob('S15-executed-case-index-*.json'))
paths += sorted(base.glob('S15-executed-case-index-*.log'))
assert len(paths) == len(set(paths))
for path in paths:
    raw = path.read_bytes()
    public = _sanitize(raw.decode('utf-8').replace('\r\n', '\n'), repo).encode('utf-8')
    destination = target / path.name
    destination.write_bytes(public)
    public_ref = destination.relative_to(repo).as_posix()
    manifest[public_ref] = 'sha256:' + hashlib.sha256(public).hexdigest()
    mapping['artifacts/' + path.name] = dict(
        original_sha256='sha256:' + hashlib.sha256(raw).hexdigest(),
        retained_ref=public_ref, retained_sha256=manifest[public_ref])
def record(name, facts):
    path = target / name
    path.write_text(json.dumps(facts, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    manifest[path.relative_to(repo).as_posix()] = 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()
record('independent-tooling-review.json', dict(
    reviewer='/root/qualification_review', reviewer_execution='NONE',
    kind='INDEPENDENT_BOUNDED_READ_ONLY_EXECUTION_INDEX_TOOLING_REVIEW',
    remaining_critical=0, remaining_important=0,
    reviewed_original_files={'artifacts/' + key: 'sha256:' + value for key, value in reviewed.items()},
    resolved_important=['Recompute complete canonical AST inventory before binding supplied references',
                        'Validate real ordered UTC execution windows',
                        'Reject arbitrary source references before any dereference'],
    limits=['Read-only review; reviewer did not execute tests',
            'No whole-product, requirement, native or commissioning acceptance']))
record('retention-map.json', mapping)
record('disposition.json', dict(
    task_id=index['task_id'], spec_baseline='r7-product-v0.2', candidate_revision=revision,
    state='IN_PROGRESS', kind='ACTUAL_NAMED_SOURCE_EXECUTION_INDEX;NOT_REQUIREMENT_ACCEPTANCE',
    execution_instances=1942, distinct_reported_test_ids=1695, static_declared_test_methods=1681,
    unresolved_static_definitions=0, tests_source_files=210, source_commands=33,
    focused_harness_tests=13, remaining_review_critical=0, remaining_review_important=0,
    requirements_unmapped=66, legacy_applicability_or_mapping_pending=150, requirement_pass_claims=0,
    source_before=index['source_before'], source_after=index['source_after'],
    implementation_hash=index['implementation_hash_after'],
    primary_guard='S15-executed-case-index-reference-order-GREEN.json',
    historical_guards='HISTORY_ONLY;NOT_CURRENT_PASS',
    command_basis='SEALED_EXECUTED_RUNNER_POLICY;NOT_RAW_ARGV_TRACE',
    timing_basis='ACTUAL_FULL_SOURCE_QUALIFICATION_WINDOW;NO_PER_TEST_TIMESTAMPS',
    reviewer_execution='NONE', real_provider_requests=0, credentials='NONE', capital='NONE',
    github_compute='NOT_USED', limitations=index['limits']))
manifest_ref = 'status/codex/productization/S15/execution-index-artifact-hashes-e293a94.json'
(repo / manifest_ref).write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
progress_path = repo / 'coordination/CODEX/PROGRESS.json'
progress = json.loads(progress_path.read_bytes())
assert progress['qualified_executable_revision'] == revision and progress['steps']['S15'] == 'NOT_STARTED'
progress['steps']['S15'] = 'IN_PROGRESS'
progress['acceptance_execution_index_checkpoint'] = dict(
    status='IN_PROGRESS', executable_revision=revision, execution_instances=1942,
    distinct_reported_test_ids=1695, unresolved_static_definitions=0, requirement_pass_claims=0,
    requirements_unmapped=66, legacy_applicability_or_mapping_pending=150,
    focused_harness_tests=13, retained_files=len(manifest), evidence_ref=ref + '/disposition.json',
    manifest_ref=manifest_ref, independent_review='BOUNDED_READ_ONLY;0_CRITICAL_0_IMPORTANT;NO_REVIEWER_EXECUTION')
progress['evidence_refs'].append(ref + '/disposition.json')
progress_path.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
note = ('S15 working execution index: all1942 actual named source executions across33 commands bound to exact-clean '
        + revision + ';1695 distinct reported test IDs,0 unresolved static definitions,1681 static declared methods/210 files. '
        '13 owned/reaped tooling tests PASS after retained reference-order RED13/1; final five-file independent read-only review0 Critical/Important. '
        'This indexes executed source cases only:66 product requirements remain unmapped and150 legacy applicability/mapping decisions pending; requirement PASS claims0. '
        'Command argv derives from sealed runner policy; only the actual full-source qualification time window is claimed. '
        'S15 IN_PROGRESS; continue semantic mapping, complete product/native/capacity checks and independent work automatically.\n\n')
handoff = repo / 'coordination/CODEX/HANDOFF.md'
handoff.write_text(note + handoff.read_text(encoding='utf-8'), encoding='utf-8', newline='\n')
(repo / 'status/codex/productization/S15/EXECUTION_INDEX_CHECKPOINT_e293a94.md').write_text(
    '# Working source execution index\n\n' + note + 'Evidence: `execution-index-e293a94/disposition.json`; '
    'byte manifest: `execution-index-artifact-hashes-e293a94.json`. Source execution does not establish requirement acceptance.\n',
    encoding='utf-8', newline='\n')
print(json.dumps(dict(retained_files=len(manifest), execution_instances=1942, requirement_pass_claims=0)))
