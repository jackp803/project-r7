"""Persist a source-only checkpoint and non-active review proposal."""
import hashlib,json
from pathlib import Path
base=Path(__file__).resolve().parent
repo=base.parent/'workspaces/project-r7-productization-master-20261002'
proof=json.loads((base/'S12-runtime-supervision-integrated-GREEN.json').read_bytes())
assert proof['passed'] and proof['tests_run']==52 and proof['failures']==proof['errors']==proof['skipped']==0
assert proof['source_before']==proof['source_after']
assert proof['implementation_hash_before']==proof['implementation_hash_after']
assert proof['execution_input_sha256_before']==proof['execution_input_sha256_after']
assert proof['log_sha256']=='sha256:'+hashlib.sha256((base/'S12-runtime-supervision-integrated-GREEN.log').read_bytes()).hexdigest()
proposal=base/'S12-qualified-paper-release-profile-proposal.md'
assert hashlib.sha256(proposal.read_bytes()).hexdigest()=='5af8ff6bc569140e047277f9f43eb2b17b18900d36a5e7f9892ca5f9b18b56e3'
destination=repo/'status/codex/productization/S12/QUALIFIED_PAPER_RELEASE_PROFILE_PROPOSAL.md'
assert not destination.exists()
destination.write_bytes(proposal.read_bytes())
path=repo/'coordination/CODEX/PROGRESS.json'
progress=json.loads(path.read_bytes())
assert progress['qualified_executable_revision']=='82a6b9ec636236a25c830acad1c915499c5c6229'
progress.update(active_step='S12',candidate_executable_revision=None,
    next_step='Freeze the reviewed runtime/cloud supervisor source and qualify a new exact-clean candidate; preserve unchanged source/native/browser policies. Continue independent S12 issuer/store/adapter and normal-worker plumbing; production qualification profile awaits PM/E6 acceptance only for qualified issuance/dependent admission. No full-product PASS.')
progress['runtime_supervision_increment']=dict(status='INTEGRATED_SOURCE_PASS;EXACT_CLEAN_QUALIFICATION_PENDING',
    new_source_tests=18,existing_supervisor_control_backup_regressions=34,integrated_total=52,
    external_input_guard_tests=4,serial_qualification_guard_tests=6,
    implementation_hash=proof['implementation_hash_after'],financial_authority='NONE',normal_paper_runtime='NOT_STARTED',
    independent_source_review='BOUNDED_READ_ONLY;0_REMAINING_CRITICAL_OR_IMPORTANT_AFTER2_REPAIRS',
    native_new_roles='NOT_RUN',native_ubuntu='NOT_RUN',
    production_release_profile='PROPOSED_NOT_ACTIVE;PM_E6_ACCEPTANCE_PENDING',
    proposal_ref=destination.relative_to(repo).as_posix(),
    independent_profile_wording_review='0_CRITICAL_OR_IMPORTANT;NO_ACTIVATION_AUTHORITY',
    prior_development_collection_hashes='COLLECTION_ONLY;NOT_BEFORE_AFTER_EXECUTION_PROOF;REPLACED_BY_FRESH_BOUND_RUNS',
    original_regression_failure='2_CONTROL_CHILD_READY_FAILURES;SOURCE_MODULE_UNDISCOVERABILITY_REPRODUCED;PATH_REPAIR_RERUN34PASS;NO_PRODUCT_TEST_WEAKENING')
path.write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
handoff=repo/'coordination/CODEX/HANDOFF.md'
note=('S12 runtime/cloud supervisor source increment integrated:18 new ownership/heartbeat/schema regressions plus34 existing actual supervisor/control/backup regressions =52PASS,0failures/errors/skips. '
    'The integrated runner inherited the real changed source path for child control processes and bound full Python/SQL implementation plus exact files before/after; owned tree reaped. '
    '4 external input-binding tests and6 serial qualification guard tests PASS. '
    'Read-only independent source review0 remaining C/I after exact legacy/receipt-backed table constraint signatures and pre/post execution inventory binding repairs. '
    'Legacy migration0006 remains unchanged,0008 is atomic/additive in the same DB; financial authorityNONE. '
    'Original source RED18/failures2,development paths,collection-only hashes and initialization failures remain outside Git for later sanitized retention. '
    'New exact-clean full-source/native/browser qualification PENDING; accepted executable remains82a6b9ec636236a25c830acad1c915499c5c6229. '
    'Status proposal status/codex/productization/S12/QUALIFIED_PAPER_RELEASE_PROFILE_PROPOSAL.md is PROPOSED_NOT_ACTIVE and received independent wording review0C/I. '
    'Only production qualified issuance/dependent admission await PM/E6 profile acceptance; independent issuer/store/adapter/worker implementation remains authorized. '
    'Normal PAPER/runtime/feedback/restoration composition and S15-S16 remain pending; native Ubuntu/real commissioningNOT_RUN. Continue automatically; real provider0,credentialsNONE,capitalNONE,GitHub computeNOT_USED,main mergeNOT_PERFORMED.\n\n')
handoff.write_text(note+handoff.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print('Recorded integrated source checkpoint and non-active qualification-profile proposal')
