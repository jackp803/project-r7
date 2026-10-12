"""Reconcile scoped native/source evidence, without closing Master requirements."""
from pathlib import Path
import hashlib,json,sys,re,os
from s09_ui_dependency_inputs import protected_bytes
BASE=Path(__file__).resolve().parent
REPO=BASE.parent/'workspaces/project-r7-productization-master-20261002'
REV=sys.argv[1];short=REV[:7];S15=REPO/'status/codex/productization/S15'
assert re.fullmatch('[0-9a-f]{40}',REV)
def digest(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
retained_hashes={}
def verify_retained(local,relative,manifest):
    raw=protected_bytes(local,8*1024**2)
    rows=[row for row in manifest['artifacts'] if row['path']==relative]
    assert len(rows)==1
    row=rows[0];published=protected_bytes(REPO/relative,8*1024**2)
    assert published==raw.replace(b'\r\n',b'\n')
    assert row['sha256']==digest(published) and row['bytes']==len(published)
    assert row['original_sha256']==digest(raw)
    if published!=raw:
        raw_relative=row['raw_subject_path']
        raw_rows=[item for item in manifest['artifacts'] if item['path']==raw_relative]
        assert len(raw_rows)==1 and raw_rows[0]['sha256']==digest(raw)
        assert protected_bytes(REPO/raw_relative,8*1024**2)==raw
    retained_hashes[relative]=digest(published)
    return json.loads(published)
source_manifest=json.loads(protected_bytes(S15/f'source-artifact-hashes-{short}.json',8*1024**2))
native_manifest=json.loads(protected_bytes(S15/f'native-negative-intake-artifact-hashes-{short}.json',8*1024**2))
assert source_manifest['executable_revision']==native_manifest['source_revision']==REV
for manifest in (source_manifest,native_manifest):
    for row in manifest['artifacts']:
        path=REPO/row['path']
        assert path.is_relative_to(S15) and '..' not in Path(row['path']).parts
        raw=protected_bytes(path,8*1024**2)
        assert row['sha256']==digest(raw) and row['bytes']==len(raw)
q=verify_retained(BASE/f'r7-productization-S09-normal-fixture-qualified-{short}/qualification.json',
    f'status/codex/productization/S15/source-{short}/qualification.json',source_manifest)
context=verify_retained(BASE/f'r7-productization-S09-normal-fixture-qualified-{short}/qualification-context.json',
    f'status/codex/productization/S15/source-{short}/qualification-context.json',source_manifest)
build=verify_retained(BASE/f'S15-negative-intake-{short}-native-build.json',
    f'status/codex/productization/S15/native-build-{short}.json',native_manifest)
flow=verify_retained(BASE/f'r7-native-S15-negative-intake-{short}/outcome.json',
    f'status/codex/productization/S15/native-negative-intake-{short}/outcome.json',native_manifest)
assert q['passed'] and len(q['commands'])==33 and context['inputs_unchanged']
assert q['source_before']==q['source_after']==context['source_before']==context['source_after']==dict(revision=REV,worktree='CLEAN')
assert build['passed'] and build['full_source_qualification_revision']==REV
assert flow['passed'] and len(flow['cases'])==5 and all(row['passed'] for row in flow['cases'])
assert flow['source_revision']==flow['executable_revision']==REV and flow['native_build_identity']==build['native_build_identity']
assert flow['phase']=='COMPLETE' and all(row['tree_reaped'] for row in flow['commands']+flow['control_sessions'])
assert len(flow['browser'])==3 and all(row['expired_receipt_absent'] and row['distinct_expired_subject_absent'] for row in flow['browser'])
assert flow['awake_request']['restored'] and build['awake_request']['restored']
assert all(flow[key] for key in ('source_inputs_unchanged','execution_inputs_unchanged','native_distribution_unchanged'))
phase={name:dict(passed=sum(row['tests_passed'] for row in q['commands'] if row['phase']==name),
    failed=sum(row['failures'] for row in q['commands'] if row['phase']==name),
    errors=sum(row['errors'] for row in q['commands'] if row['phase']==name),
    skipped=sum(row['skipped'] for row in q['commands'] if row['phase']==name)) for name in ['phase_1','phase_2']}
assert all(all(item[key]==0 for key in ['failed','errors','skipped']) for item in phase.values())
report=dict(requirement_id='E2E-02',status='NOT_RUN',scope_status='PASS',scope='WINDOWS_NATIVE_NEGATIVE_INTAKE',full_requirement_status='NOT_COMPLETE',
    test_ids=[row['test_id'] for row in flow['cases']],source_revision=REV,executable_revision=REV,
    spec_revision='9fd277798b1c51d1bc79b29a61bec81b552efeb1',environment_class='WINDOWS_NATIVE_PUBLIC_FIXTURE',
    os_version=q['os_version'],architecture=q['architecture'],runtime_versions=dict(python=q['python'],browser=flow['browser'][0]['browser_version']),
    config_hash=flow['initial_profile_sha256'],started_at_utc=flow['started_at_utc'],finished_at_utc=flow['finished_at_utc'],
    command=f'python -X utf8 s15_native_negative_intake_v2.py {REV} {REV} resume',exit_code=0,
    passed=5,failed=0,errors=0,skipped=0,phase_counts=phase,source_execution_instances=q['tests_run'],
    native_build_identity=build['native_build_identity'],archive_sha256=build['archive_sha256'],
    native_recorded_commands=len(flow['commands']),native_browser_stages=len(flow['browser']),actual_tty_enrollments=1,
    control_stop='FORCED_OWNED_CONTROL_CLEANUP;NO_GRACEFUL_STOP_CREDIT',trading_runtime='NOT_STARTED',paper_runs=0,
    provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',
    review=dict(initial_critical=0,initial_important=1,remaining_critical=0,remaining_important=0,reviewer_execution='NONE',scope='INTAKE_AND_HEALTH_SNAPSHOT_ORDER_ONLY'),
    limitations=['Ubuntu24/26 NOT_RUN','Not full E2E-02 all-platform acceptance','Expiry after enqueue/during validation pending',
        'New native package has intake proof only; previous dd53369 three-outcome native Paper proof remains historical',
        'Ordinary qualified-release proposal PROPOSED_NOT_ACTIVE','Real cloud/dataset/forward/provider/capital NOT_RUN'],
    artifact_refs=[f'status/codex/productization/S15/native-negative-intake-{short}/outcome.json',
        f'status/codex/productization/S15/source-{short}/qualification.json',
        f'status/codex/productization/S15/native-build-{short}.json'])
hashes={path:retained_hashes[path] for path in report['artifact_refs']}
report['artifact_hashes']=hashes
assert all(digest(protected_bytes(REPO/path,8*1024**2))==commitment for path,commitment in retained_hashes.items())
assert not os.path.lexists(S15/f'NEGATIVE_INTAKE_CHECKPOINT_{short}.json')
assert not os.path.lexists(S15/f'NEGATIVE_INTAKE_CHECKPOINT_{short}.md')
(S15/f'NEGATIVE_INTAKE_CHECKPOINT_{short}.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
text=f'''# Windows native negative intake checkpoint

Executable/source revision: `{REV}`. Master branch remains `codex/r7-productization-master-20261002`, IN_PROGRESS. Complete credential-free source verification passed {q['tests_run']} execution instances in 33 commands; phase 1 {phase['phase_1']['passed']}, phase 2 {phase['phase_2']['passed']}, zero failures/errors/skips. The resource-limited failed first candidate is retained without credit; the passing retry followed user-restored available memory and kept the same threshold.

Native public negative inputs passed 5/5: malformed -> BLOCKED/MALFORMED_JSON; partial sync -> INCOMPLETE_SYNC then INTAKE_ACCEPTED after actual backoff and restored bytes; unsupported package version -> BLOCKED; immutable accepted submission mutation -> CONFLICT with original receipt preserved; expired tactical submission -> EXPIRED before E6 intake. Actual hidden TTY enrollment, packaged UI scan, public local owner API and native author-package CLI were used. One canonical DRAFT remained, research jobs and Paper runs stayed zero. {len(flow['commands'])} recorded commands, three browser stages and one actual TTY enrollment; all owned trees reaped, temporary awake request restored. Control cleanup is forced, with no graceful-stop credit. Screenshots were visually checked for the corrected EXPIRED row.

The intake repair verifies initial/sealed manifest identity, applies the existing temporal decision to the verified manifest before claim and preserves immutable receipt/lifecycle history. Six intake regression cases were red before their corresponding repairs; focused 37-test regression is green. A second complete attempt uncovered a false CLOCK_REGRESSION due to live time sampled before the heartbeat snapshot. Its deterministic regression was red before repair; focused supervision/worker/fixture/API regression passed 58. Live observation now samples time after the snapshot while explicit now, true regression, freshness15seconds, generation/config/failure fences remain intact. Both bounded independent rechecks: 0 Critical / 0 Important, reviewer execution NONE. New proof tools are SELF_REVIEW; no whole-Master independent review is claimed.

New package: `artifacts/r7-native-windows-S15-negative-intake-{short}/dist/R7/R7.exe`.
Archive: `artifacts/r7-native-windows-S15-negative-intake-{short}/{build['archive_name']}`.
Build identity: `{build['native_build_identity']['build_hash']}`.
Archive hash: `{build['archive_sha256']}`.

This package has scoped native intake proof. The previous `dd53369` package retains the separately proven three-outcome normal Paper workflow; that native credit is not transferred to changed executable inputs. User setup/commands for that historical package remain in the S09 usability guide. Ordinary LOCAL_RESEARCH release still needs the four Git PM/E6 mappings. Ubuntu24/26, real cloud, real dataset, real-time Paper and actual capital/provider activation are separate pending stages. Nothing here establishes expected profit or an activation date. Full requirement PASS remains zero; the E2E-02 machine row is explicitly scoped Windows evidence, not whole-platform completion.

Next: continue the remaining S16 requirement audit, including expiry after enqueue/during validation and independent Windows/native work. No main merge, hosted compute, real credentials, provider requests or capital.
'''
(S15/f'NEGATIVE_INTAKE_CHECKPOINT_{short}.md').write_text(text,encoding='utf-8',newline='\n')
progress_path=REPO/'coordination/CODEX/PROGRESS.json';progress=json.loads(progress_path.read_bytes())
progress.update(active_step='S15_SCOPED_NATIVE_NEGATIVE_INTAKE_PASS;CONTINUE_S16_REMAINING_MASTER',
    next_step='Continue requirement-by-requirement source/native audit, including expiry after enqueue/during validation. New native package proves intake only; dd53369 three-outcome native Paper evidence remains historical. Four PM/E6 release decisions, approved Ubuntu24/26 and real commissioning stay separate.',
    executable_revision=REV,candidate_executable_revision=REV,qualified_executable_revision=REV)
progress['negative_intake_checkpoint']=report
progress_path.write_text(json.dumps(progress,indent=2)+'\n',encoding='utf-8',newline='\n')
handoff=REPO/'coordination/CODEX/HANDOFF.md';prior=handoff.read_text(encoding='utf-8')
lead=f'Current S15 scoped native negative intake checkpoint: {REV},5/5 Windows public cases PASS; complete source {q["tests_run"]}/33commands PASS,0F/E/skip. Native build/source binding current637inputs; bounded incoming-validity review0Critical/0Important. Earlier a3a6a1c full attempt failed on memory pressure and is retained without credit. New package proves intake only; previous dd53369 normal three-outcome native Paper proof remains historical and is not transferred. Expiry after enqueue/during validation remains pending; full Master IN_PROGRESS,full requirement PASS0. See status/codex/productization/S15/NEGATIVE_INTAKE_CHECKPOINT_{short}.md/json. Provider0,credentialsNONE,capitalNONE,GitHubcomputeNOT_USED; no main merge. Continue remaining S16 audit on the same branch.\n\n'
handoff.write_text(lead+prior,encoding='utf-8',newline='\n')
print(json.dumps(dict(source_instances=q['tests_run'],phase_counts=phase,native_cases=5,master='IN_PROGRESS')))
