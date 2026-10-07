"""Adapt only scoped subject/inventories; retain accepted primary artifact gates."""
from pathlib import Path
import py_compile

base=Path(__file__).resolve().parent
core=base/'s12_runtime_supervision_acceptance_core.py'
collector=base/'s12_runtime_supervision_accept.py'
assert not core.exists() and not collector.exists()
original=(base/'s14_feedback_acceptance_core.py').read_text(encoding='utf-8')
assert original.count('s14_feedback_ui_frontend.py')==1
core.write_text(original.replace('s14_feedback_ui_frontend.py','s12_runtime_supervision_ui_frontend.py'),encoding='utf-8',newline='\n')
code=(base/'s14_feedback_accept.py').read_text(encoding='utf-8')
code=code.replace('s14_feedback_','s12_runtime_supervision_').replace('S14-feedback','S12-runtime-supervision')
code=code.replace('from s12_runtime_supervision_review_integrity import validate_review',
    'from s12_runtime_supervision_review_integrity import validate_review_inventory,validate_primary_proof')
code=code.replace('1922','1940').replace('1675','1693')
start=code.index("reviews=[load(base,'S14-paper-feedback-independent-source-review.json')")
end=code.index('for reference,expected in integrity[',start)
block='''source_review=load(base,'S12-runtime-supervision-independent-review.json')
source_files={
 'development/platform/supervision.py':repo/'src/application/platform/supervision.py',
 'development/migrations/0008_runtime_process_supervision.sql':repo/'src/application/migrations/0008_runtime_process_supervision.sql',
 'development/test_runtime_process_supervision.py':repo/'tests/application/test_runtime_process_supervision.py',
 'src/application/migrations/0006_process_supervision.sql':repo/'src/application/migrations/0006_process_supervision.sql',
 **{name:base/name for name in ('run_s12_runtime_supervision_development.py','s12_runtime_supervision_harness_integrity.py',
 'test_s12_runtime_supervision_harness_integrity.py','S12-runtime-supervision-increment-plan.md','S12-qualified-paper-release-profile-proposal.md')}}
validate_review_inventory(source_review,kind='INDEPENDENT_BOUNDED_READ_ONLY_SUPERVISOR_MIGRATION_AND_HARNESS_REVIEW',files=source_files,bound=bound,project=project)
development_inputs={
 'development/platform/supervision.py':repo/'src/application/platform/supervision.py',
 'development/migrations/0008_runtime_process_supervision.sql':repo/'src/application/migrations/0008_runtime_process_supervision.sql',
 'development/migrations/0006_process_supervision.sql':repo/'src/application/migrations/0006_process_supervision.sql',
 'development/test_runtime_process_supervision.py':repo/'tests/application/test_runtime_process_supervision.py',
 **{'harness/'+name:base/name for name in ('run_s12_runtime_supervision_development.py','s12_runtime_supervision_harness_integrity.py','test_s12_runtime_supervision_harness_integrity.py')}}
for stem,count in (('S12-runtime-supervision-reviewed-GREEN',18),('S12-runtime-supervision-reviewed-regression-GREEN',34),('S12-runtime-supervision-harness-GREEN',4)):
 proof=validate_primary_proof(base,stem,count,inputs=development_inputs,input_fields=('execution_input_sha256_before','execution_input_sha256_after'),bound=bound,project=project)
 assert proof['source_before']==proof['source_after'] and proof['inputs_unchanged'] is True
integrated_paths=(base/'run_s12_runtime_supervision_integrated.py',repo/'src/application/platform/supervision.py',
 repo/'src/application/migrations/0008_runtime_process_supervision.sql',repo/'src/application/migrations/0006_process_supervision.sql',
 repo/'tests/application/test_runtime_process_supervision.py',repo/'docs/product/v0_2/RUNTIME_PROCESS_SUPERVISION_IMPLEMENTATION.md')
integrated_inputs={path.relative_to(project).as_posix():path for path in integrated_paths}
integrated=validate_primary_proof(base,'S12-runtime-supervision-integrated-GREEN',52,inputs=integrated_inputs,
 input_fields=('execution_input_sha256_before','execution_input_sha256_after'),bound=bound,project=project)
assert integrated['source_before']==integrated['source_after']
assert integrated['implementation_hash_before']==integrated['implementation_hash_after']==identity['implementation_hash']
harness_review=load(base,'S12-runtime-supervision-independent-qualification-harness-review.json')
harness_names=('s12_runtime_supervision_candidate_pipeline.py','s12_runtime_supervision_ui_frontend.py','s12_runtime_supervision_bound_installer.py',
 's12_runtime_supervision_source_qualify.py','s12_runtime_supervision_serial_browser_qualify.py',
 'test_s12_runtime_supervision_qualification_integrity.py','run_s12_runtime_supervision_qualification_integrity.py','run_s12_runtime_supervision_integrated.py')
validate_review_inventory(harness_review,kind='INDEPENDENT_BOUNDED_READ_ONLY_PREEXECUTION_QUALIFICATION_HARNESS_REVIEW',
 files={name:base/name for name in harness_names},bound=bound,project=project)
document=harness_review['reviewed_document'];assert document['ref']=='docs/product/v0_2/RUNTIME_PROCESS_SUPERVISION_IMPLEMENTATION.md'
document_path=require_artifact(repo/'docs/product/v0_2','RUNTIME_PROCESS_SUPERVISION_IMPLEMENTATION.md',document['sha256'])
bound[document_path.relative_to(project).as_posix()]=document['sha256']
qualification_inputs={name:base/name for name in (*expected_names,'run_s12_runtime_supervision_qualification_integrity.py','test_s12_runtime_supervision_qualification_integrity.py')}
guard=validate_primary_proof(base,'S12-runtime-supervision-qualification-reviewed-integrity-GREEN',6,inputs=qualification_inputs,
 input_fields=('input_sha256_before','input_sha256_after'),bound=bound,project=project)
primary=harness_review['primary_regression']
assert primary==dict(report='S12-runtime-supervision-qualification-reviewed-integrity-GREEN.json',
 report_sha256=digest(base/'S12-runtime-supervision-qualification-reviewed-integrity-GREEN.json'),
 log='S12-runtime-supervision-qualification-reviewed-integrity-GREEN.log',log_sha256=guard['log_sha256'],tests=6)
retention_review=load(base,'S12-runtime-supervision-independent-retention-review.json')
retention_names=('s12_runtime_supervision_acceptance_core.py','prepare_s12_runtime_supervision_acceptance.py','s12_runtime_supervision_accept.py',
 's12_runtime_supervision_review_integrity.py','test_s12_runtime_supervision_review_integrity.py','run_s12_runtime_supervision_review_integrity.py')
validate_review_inventory(retention_review,kind='INDEPENDENT_BOUNDED_READ_ONLY_RETENTION_AND_PRIMARY_PROOF_REVIEW',
 files={name:base/name for name in retention_names},bound=bound,project=project)
retention_inputs={name:base/name for name in ('run_s12_runtime_supervision_review_integrity.py','s12_runtime_supervision_review_integrity.py',
 'test_s12_runtime_supervision_review_integrity.py','s13_installer_acceptance_integrity.py','s14_feedback_acceptance_core.py',
 's13_acceptance_integrity.py','s13_ssh_acceptance_integrity.py')}
retention_guard=validate_primary_proof(base,'S12-runtime-supervision-retention-review-GREEN-v2',8,inputs=retention_inputs,
 input_fields=('input_sha256_before','input_sha256_after'),bound=bound,project=project)
assert retention_review['primary_regression']==dict(report='S12-runtime-supervision-retention-review-GREEN-v2.json',
 report_sha256=digest(base/'S12-runtime-supervision-retention-review-GREEN-v2.json'),
 log='S12-runtime-supervision-retention-review-GREEN-v2.log',log_sha256=retention_guard['log_sha256'],tests=8)
'''
code=code[:start]+block+code[end:]
code=code.replace("status/codex/productization/S14/paper-feedback-{short}-py312", "status/codex/productization/S12/supervisor-{short}-py312")
code=code.replace("status/codex/productization/S14/paper-feedback-artifact-hashes-{short}.json", "status/codex/productization/S12/supervisor-artifact-hashes-{short}.json")
old_pattern="for pattern in ('S14-paper-feedback-*.log','S12-runtime-supervision-harness-*.log'):"
assert old_pattern in code
code=code.replace(old_pattern,"for pattern in ('S12-runtime-supervision-*.log',):")
start=code.index("for name in ('S14LocalFakeRclone.cs'")
end=code.index('required={reference:',start)
supplemental='''for name in ('S14LocalFakeRclone.cs','prepare_s12_runtime_supervision_qualification.py',
 'prepare_s12_runtime_supervision_qualification_integrity.py','prepare_s12_runtime_supervision_qualification_integrity.before-initialization-repair.py',
 'run_s12_runtime_supervision_development.before-source-child-path-repair.py','s12_supervision.before-constraint-review-fix.py',
 's12_runtime_supervision_review_integrity.before-single-read-fix.py','run_s12_runtime_supervision_review_integrity.before-transitive-binding-fix.py',
 'integrate_s12_runtime_supervision.py','record_s12_runtime_supervision_source_checkpoint.py','record_s12_runtime_supervision_qualification_review.py',
 *retention_names,'s13_acceptance_integrity.py','s13_ssh_acceptance_integrity.py','s13_installer_acceptance_integrity.py'):
 retain(base/name,'harness/'+name)
'''
code=code[:start]+supplemental+code[end:]
code=code.replace('SCOPED_S14_FEEDBACK_IMPLEMENTATION_AND_REGRESSION_PASS;MASTER_IN_PROGRESS','SCOPED_S12_RUNTIME_CLOUD_SUPERVISOR_AND_REGRESSION_PASS;MASTER_IN_PROGRESS')
code=code.replace('SCOPED_UNCHANGED_NATIVE_REGRESSION_PASS;PAPER_NATIVE_WORKER_PENDING','SCOPED_UNCHANGED_NATIVE_CONTROL_RESEARCH_MIGRATION_REGRESSION_PASS;RUNTIME_CLOUD_NATIVE_WORKERS_PENDING')
code=code.replace("new_paper_feedback_native_worker='NOT_RUN;SOURCE_OWNER_TESTS_ONLY;NORMAL_S12_COMPOSITION_PENDING'", "normal_runtime_cloud_native_workers='NOT_RUN;SOURCE_ROLE_OWNERS_ONLY;NORMAL_S12_COMPOSITION_PENDING',\n production_qualification_profile='PROPOSED_NOT_ACTIVE;ISSUANCE_AND_DEPENDENT_ADMISSION_PENDING_PM_E6',\n independent_retention_review=dict(critical=0,important=0)")
code=code.replace("accepted_prior_revision='fa3b786169144d298de640edb605db3c6d3cea99'", "accepted_prior_revision='82a6b9ec636236a25c830acad1c915499c5c6229'")
collector.write_text(code,encoding='utf-8',newline='\n')
for path in (core,collector):py_compile.compile(str(path),doraise=True)
print('Prepared scoped collector with exact nine/eight/six review inventories and primary18/34/4/52/6/8 bound proofs')
