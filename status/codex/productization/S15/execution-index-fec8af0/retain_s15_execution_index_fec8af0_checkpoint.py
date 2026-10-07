"""Retain the reviewed actual current-candidate index with explicit evidence closure."""
from pathlib import Path
import hashlib,json,sys
base=Path(__file__).resolve().parent;project=base.parent;repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.datasets.catalog import read_local
from application.qualification import _sanitize,FOCUSED,discover_suites
from s15_execution_index import validate_static_inventory
from s12_runtime_supervision_review_integrity import validate_primary_proof
from s14_feedback_cli_acceptance_core import require_artifact,publish_retention_manifest
revision='fec8af0f70d787deea720b1e7f952c4fca9487b5';short=revision[:7]
reviewed={
 's15_execution_index.py':'3480116092811655ab57ad073cb9a97eab0b1d596ace97390d43ba9e7b1aa936',
 'prepare_s15_acceptance_coverage_inventory_v2.py':'94ae973289ff8a077e6201a1afa94ddcc4f7243fe1149ecf93707c61dc8b9c6b',
 'test_s15_execution_index_fec8af0.py':'e75384be93509e3f25a590a7b9a6b301be4d471c5f44d19ec391238a49916543',
 'run_s15_execution_index_fec8af0_tests.py':'5489bc27fc8c0d031e83c8b1d47af72848c36d85a226cfa0e563d1f82643e54d',
 'build_s15_execution_index_fec8af0.py':'de7b4588d080b39a1cda6ce5e17690e53b5112dcc22044ceaed6bfaa25155a15'}
digest=lambda raw:'sha256:'+hashlib.sha256(raw).hexdigest()
def raw(path,expected=None):
    value=read_local(path.parent,path.name,8*1024*1024);actual=digest(value)
    if expected is not None and actual!=expected:raise ValueError('Consumed evidence changed')
    require_artifact(path.parent,path.name,actual);return value
def load(path):return json.loads(raw(path))
for name,expected in reviewed.items():raw(base/name,'sha256:'+expected)
inventory=load(base/f'S15-acceptance-coverage-inventory-{short}.json')
assert inventory['candidate_revision']==revision
declared=validate_static_inventory(repo,inventory)
index=load(base/f'S15-executed-case-index-{short}.json')
assert index['candidate_revision']==revision and index['indexed_execution_instances']==1953
assert index['distinct_reported_test_ids']==1706 and index['unresolved_static_definitions']==0
assert index['requirement_pass_claims']==0 and index['requirements_unmapped']==66 and index['legacy_applicability_or_mapping_pending']==150
assert index['source_before']==index['source_after']==dict(revision=revision,worktree='CLEAN')
assert index['input_sha256_before']==index['input_sha256_after']
assert index['implementation_hash_before']==index['implementation_hash_after']=='sha256:ba01027908e0e8ddf694eb8619d28b5d7a1bd9f94de0df804dc1471afe189576'
assert len(index['cases'])==len({row['execution_instance_id'] for row in index['cases']})==1953
stem='S15-executed-case-index-fec8af0-log-reference-GREEN'
guard_inputs={name:base/name for name in ('run_s15_execution_index_fec8af0_tests.py','test_s15_execution_index_fec8af0.py','s15_execution_index.py','build_s15_execution_index_fec8af0.py')}
guard=validate_primary_proof(base,stem,14,inputs=guard_inputs,input_fields=('input_sha256_before','input_sha256_after'),bound={},project=project)
assert guard['source_before']==guard['source_after']==index['source_before']
assert guard['implementation_hash_before']==guard['implementation_hash_after']==index['implementation_hash_after']
source=base/f'r7-productization-S14-feedback-cli-qualified-{short}';full=load(source/'qualification.json')
assert full['passed'] is True and full['tests_run']==1953 and len(full['commands'])==33
expected=[('phase_1',name,pattern) for name,pattern in FOCUSED]+[('phase_2',suite.name,'test_*.py') for suite in discover_suites(repo)]
assert [(row['phase'],row['suite'],row['pattern']) for row in full['commands']]==expected
paths=[base/name for name in reviewed]
paths+=[base/f'S15-acceptance-coverage-inventory-{short}.json',base/(stem+'.json'),base/(stem+'.log'),
 source/'qualification.json',source/'qualification-context.json',base/'s14_feedback_cli_source_qualify.py',
 repo/'docs/product/v0_2/07_ACCEPTANCE_MATRIX.json',repo/'docs/product/R7_PRODUCT_ACCEPTANCE_MATRIX_V0_1.md']
paths+=[repo/row for row in inventory['test_source_hashes']]
for number,row in enumerate(full['commands'],1):
    name=f'{number:03d}-{row["phase"]}-{row["suite"].replace("/","-")}.log'
    assert row['log']==name;paths.append(source/name)
allowed={path.relative_to(project).as_posix():path for path in paths}
assert len(paths)==len(allowed) and set(index['input_sha256_before'])==set(allowed)
for reference,path in allowed.items():raw(path,index['input_sha256_before'][reference])
prior_ref='status/codex/productization/S14/cli-publisher-fec8af0-py312'
prior_manifest=load(repo/'status/codex/productization/S14/cli-publisher-artifact-hashes-fec8af0.json')
for reference,expected_hash in prior_manifest.items():
    assert not Path(reference).is_absolute() and '..' not in Path(reference).parts
    raw(repo/reference,expected_hash)
prior_index=load(repo/prior_ref/'retention-index.json')
lookup={row['original_ref']:row for row in prior_index};assert len(lookup)==len(prior_index)
crosslinks=[]
for reference in allowed:
    if not reference.startswith('artifacts/r7-productization-S14-feedback-cli-qualified-') and reference!='artifacts/s14_feedback_cli_source_qualify.py':continue
    row=lookup[reference];assert row['original_sha256']==index['input_sha256_before'][reference]
    retained_ref=(Path(prior_ref)/row['retained_file']).as_posix()
    assert retained_ref in prior_manifest and prior_manifest[retained_ref]==row['retained_sha256']
    crosslinks.append(dict(original_ref=reference,original_sha256=row['original_sha256'],retained_ref=retained_ref,retained_sha256=row['retained_sha256']))
ref='status/codex/productization/S15/execution-index-fec8af0';target=repo/ref
manifest_path=repo/'status/codex/productization/S15/execution-index-artifact-hashes-fec8af0.json'
assert not target.exists() and not manifest_path.exists();target.mkdir(parents=True)
retained=[];required={}
paths=[base/name for name in reviewed]+[base/f'S15-acceptance-coverage-inventory-{short}.json',base/f'S15-executed-case-index-{short}.json',
 base/'prepare_s15_execution_index_fec8af0.py',base/'build_s15_execution_index_fec8af0.before-command-reference-fix.py',
 base/'S15-executed-case-index-fec8af0.before-command-reference-fix.json',
 base/'run_s15_fec8af0_clean_index_refresh.py',base/'S15-fec8af0-clean-index-refresh-staging.json',Path(__file__)]
for suffix in ('.json','.log'):
    for label in ('current-GREEN','log-reference-RED','log-reference-GREEN'):
        paths.append(base/('S15-executed-case-index-fec8af0-'+label+suffix))
assert len(paths)==len(set(paths))
for path in paths:
    value=raw(path);original_ref=path.relative_to(project).as_posix()
    public=_sanitize(value.decode('utf-8').replace('\r\n','\n'),repo).encode('utf-8')
    destination=target/path.name;destination.write_bytes(public)
    required[original_ref]=digest(value)
    retained.append(dict(original_ref=original_ref,original_sha256=digest(value),retained_file=path.name,retained_sha256=digest(public),
        transformation='UTF8/CRLF_TO_LF/LOCAL_PATH_SANITIZATION'))
receipt=dict(kind='INDEPENDENT_BOUNDED_READ_ONLY_EXECUTION_INDEX_TOOLING_REVIEW',reviewer='/root/qualification_review',reviewer_execution='NONE',
 remaining_critical=0,remaining_important=0,reviewed_original_files={'artifacts/'+name:'sha256:'+value for name,value in reviewed.items()},
 primary_regression=dict(report=stem+'.json',report_sha256=digest(raw(base/(stem+'.json'))),log=stem+'.log',log_sha256=guard['log_sha256'],tests=14),
 resolved_important=['Canonical command/log references checked before any prebinding read'],
 limits='NO_REVIEWER_EXECUTION;NO_REQUIREMENT_NATIVE_OR_WHOLE_PRODUCT_ACCEPTANCE')
facts=dict(task_id=index['task_id'],spec_baseline='r7-product-v0.2',candidate_revision=revision,state='IN_PROGRESS',
 kind='ACTUAL_NAMED_SOURCE_EXECUTION_INDEX;NOT_REQUIREMENT_ACCEPTANCE',execution_instances=1953,distinct_reported_test_ids=1706,
 static_declared_test_methods=len(declared),unresolved_static_definitions=0,tests_source_files=len(inventory['test_source_hashes']),source_commands=33,
 focused_harness_tests=14,remaining_review_critical=0,remaining_review_important=0,requirements_unmapped=66,legacy_applicability_or_mapping_pending=150,requirement_pass_claims=0,
 source_before=index['source_before'],source_after=index['source_after'],implementation_hash=index['implementation_hash_after'],
 primary_guard=stem+'.json',historical_guards='HISTORY_ONLY;NOT_CURRENT_PASS',command_basis='SEALED_EXECUTED_RUNNER_POLICY;NOT_RAW_ARGV_TRACE',
 timing_basis='ACTUAL_FULL_SOURCE_QUALIFICATION_WINDOW;NO_PER_TEST_TIMESTAMPS',reviewer_execution='NONE',real_provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',limitations=index['limits'])
for name,value in (('independent-tooling-review.json',receipt),('source-evidence-crosslinks.json',crosslinks),('retention-index.json',retained),('disposition.json',facts)):
    (target/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
manifest=publish_retention_manifest(target,manifest_path,retained,required,repository_root=repo)
progress_path=repo/'coordination/CODEX/PROGRESS.json';progress=load(progress_path)
assert progress['qualified_executable_revision']==revision and progress['steps']['S15']=='IN_PROGRESS'
progress['acceptance_execution_index_checkpoint']=dict(status='IN_PROGRESS',executable_revision=revision,execution_instances=1953,distinct_reported_test_ids=1706,
 unresolved_static_definitions=0,requirement_pass_claims=0,requirements_unmapped=66,legacy_applicability_or_mapping_pending=150,focused_harness_tests=14,
 retained_files=len(manifest),evidence_ref=ref+'/disposition.json',manifest_ref=manifest_path.relative_to(repo).as_posix(),independent_review='BOUNDED_READ_ONLY;0_CRITICAL_0_IMPORTANT;NO_REVIEWER_EXECUTION')
progress['evidence_refs'].append(ref+'/disposition.json')
progress_path.write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
note=(f'S15 current execution index: all1953 actual source executions/33 commands bound to exact-clean {revision};1706 distinct reported IDs,0 unresolved origins,1692 static methods/212 files. '
 'Fresh14 owned tooling tests PASS after retained14-test RED with2 escaping-reference subtest failures; final five-file read-only review0 Critical/Important. '
 f'{len(manifest)} sanitized files retained at {ref}; source evidence crosslinks verify existing S14 commitments. '
 'Requirement PASS0:66 product requirements remain semantically unmapped and150 legacy applicability/mapping decisions pending. '
 'S15 IN_PROGRESS; continue semantic requirement mapping and whole-product/native/capacity work automatically.\n\n')
handoff=repo/'coordination/CODEX/HANDOFF.md';handoff.write_text(note+handoff.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
report=repo/'status/codex/productization/S15/EXECUTION_INDEX_CHECKPOINT_fec8af0.md';assert not report.exists()
report.write_text('# Current source execution index\n\n'+note+'Evidence: `execution-index-fec8af0/disposition.json`; byte manifest: `execution-index-artifact-hashes-fec8af0.json`.\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(retained_files=len(manifest),execution_instances=1953,requirement_pass_claims=0)))
