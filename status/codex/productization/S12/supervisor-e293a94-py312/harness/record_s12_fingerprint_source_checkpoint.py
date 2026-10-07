"""Preserve the failed qualification and record only fresh scoped source proofs."""
from pathlib import Path
import hashlib,json
base=Path(__file__).resolve().parent
repo=base.parent/'workspaces/project-r7-productization-master-20261002'
load=lambda p:json.loads(p.read_bytes())
digest=lambda p:'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()
proofs=[]
for stem,count in (('S12-runtime-supervision-fingerprint-remediation-reviewed-safety',21),
                   ('S12-runtime-supervision-fingerprint-remediation-reviewed-product-case',1),
                   ('S12-runtime-supervision-fingerprint-proof-GREEN',2),
                   ('S12-runtime-supervision-integrated-fingerprint-GREEN',52)):
    p=load(base/(stem+'.json'))
    assert p['passed'] is True and p['tests_run']==count and p['tree_reaped'] is True
    assert p['failures']==p['errors']==p['skipped']==p['exit_code']==0
    assert p['source_before']==p['source_after']
    assert p['log_sha256']==digest(base/(stem+'.log'))
    before='execution_input_sha256_before' if stem.endswith('integrated-fingerprint-GREEN') else 'input_sha256_before'
    after=before.replace('_before','_after')
    assert p[before]==p[after] and p[before]
    for ref,expected in p[before].items():
        path=(base/ref) if before=='input_sha256_before' and stem.endswith('proof-GREEN') else (base.parent/ref)
        assert digest(path)==expected
    if 'implementation_hash_before' in p:
        assert p['implementation_hash_before']==p['implementation_hash_after']=='sha256:4a55f12f3b2c66b18088ed982c438b63e9bbb7abe71bfe069db786e2740eee11'
    proofs.append(dict(report=stem+'.json',report_sha256=digest(base/(stem+'.json')),tests=count,log_sha256=p['log_sha256']))
review=load(base/'S12-runtime-supervision-fingerprint-independent-review.json')
assert review['remaining_critical']==review['remaining_important']==0 and len(review['reviewed_files'])==9
for ref,expected in review['reviewed_files'].items():assert digest(base.parent/ref)==expected
failed=load(base/'r7-productization-S12-runtime-supervision-qualified-4ea0f61/qualification.json')
assert failed['passed'] is False and failed['tests_run']==1701 and len(failed['commands'])==32
assert failed['source_before']==failed['source_after']==dict(revision='4ea0f61c62984eaca1cbfae8b745cffb9cdec901',worktree='CLEAN')
assert failed['commands'][-1]['returncode']==124 and failed['commands'][-1]['tree_reaped'] is True
path=repo/'coordination/CODEX/PROGRESS.json';progress=load(path)
assert progress['qualified_executable_revision']=='82a6b9ec636236a25c830acad1c915499c5c6229'
progress.update(candidate_executable_revision=None,active_step='S12',next_step='Qualify the exact-clean fresh-source traversal remediation with the original900-second suite limit and a new native build; preserve failed4ea qualification and all proof repairs. Continue normal runtime/cloud/issuer/store plumbing and S15 named requirement mapping. Production qualification profile remains PROPOSED_NOT_ACTIVE; native Ubuntu and real commissioning NOT_RUN.')
progress['runtime_supervision_failed_qualification']=dict(revision=failed['source_before']['revision'],
    status='FAIL',source_tests_completed=1701,commands=32,failed_suite='product',returncode=124,
    owned_tree_reaped=True,unchanged_timeout_seconds=900,completed_verbose_product_cases=193,
    browser='NOT_RUN',accepted_executable_unchanged=True,
    cause='Measured repeated fresh-source inventory cost; no claim this explains all host timing variation',
    full_source_report_sha256=digest(base/'r7-productization-S12-runtime-supervision-qualified-4ea0f61/qualification.json'))
progress['source_fingerprint_remediation']=dict(status='INTEGRATED_SOURCE_PASS;EXACT_CLEAN_QUALIFICATION_PENDING',
    focused_tests=21,unchanged_last_product_case=1,proof_guard_tests=2,integrated_supervision_tests=52,
    new_source_tests=2,implementation_hash='sha256:4a55f12f3b2c66b18088ed982c438b63e9bbb7abe71bfe069db786e2740eee11',
    fresh_byte_reads='EVERY_INVOCATION',cross_call_cache='NONE',original_timeout_seconds=900,
    independent_review='BOUNDED_READ_ONLY;0_REMAINING_CRITICAL_OR_IMPORTANT_AFTER_RETAINED_PASS_REPAIR',
    proof_refs=proofs,normal_runtime_cloud_native_workers='NOT_RUN',native_ubuntu='NOT_RUN',
    real_provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
progress['runtime_supervision_increment'].update(status='INTEGRATED_SOURCE_PASS;NEW_EXACT_CLEAN_CANDIDATE_PENDING',
    implementation_hash=progress['source_fingerprint_remediation']['implementation_hash'])
path.write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
note=('S12 exact-clean4ea0f61 qualification failed at unchanged900-second product timeout after193/194 verbose cases;1701 completed source tests/32 commands,returncode124 and owned tree reaped. '
    'Browser NOT_RUN; prior accepted executable82a6b9e unchanged. Measured last unchanged case made883 fresh source captures/31.7 profiled seconds. '
    'Minimal source traversal remediation preserves every fresh Python/SQL byte read and every authority check, adds unreadable-directory fail-closed behavior. '
    'Actual21 focused tests,1 unchanged final product case,2 owned-proof guard tests and52 integrated supervisor/control/backup regressions PASS with beforeafter bindings;2 new source tests. '
    'Independent bounded source/harness review0 remaining C/I after retained-pass/reaping repair. Original failed qualification and diagnostic/test evidence preserved outside Git for later sanitized retention. '
    'Commit a new exact-clean executable and rebuild/requalify under unchanged policy. Runtime/cloud normal workers, issuer/store/adapter and S15-S16 remain authorized independent work. '
    'Production qualification profile PROPOSED_NOT_ACTIVE; native Ubuntu and real cloud/data/forward/provider commissioning NOT_RUN. Real provider0,credentialsNONE,capitalNONE,GitHubcomputeNOT_USED,mainmergeNOT_PERFORMED. Continue automatically.\n\n')
handoff=repo/'coordination/CODEX/HANDOFF.md';handoff.write_text(note+handoff.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print('Recorded source-only remediation and preserved failed candidate; clean qualification PENDING')
