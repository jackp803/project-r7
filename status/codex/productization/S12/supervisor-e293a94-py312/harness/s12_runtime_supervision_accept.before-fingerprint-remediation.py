"""Verify one complete scoped candidate before publishing sanitized Git evidence."""
from pathlib import Path
import ast,hashlib,json,re,sys
base=Path(__file__).resolve().parent;project=base.parent;repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.qualification import revision_fact,_sanitize
from s13_installer_acceptance_integrity import read_bound_report,validate_installer_report
from s13_ssh_acceptance_integrity import validate_ssh_report
from s12_runtime_supervision_acceptance_core import validate_primary_artifacts,require_artifact,require_sequence,digest,publish_retention_manifest
from s12_runtime_supervision_review_integrity import validate_review_inventory,validate_primary_proof
revision=sys.argv[1];assert re.fullmatch('[0-9a-f]{40}',revision);short=revision[:7]
revision_fact(repo,revision,True);bound={}
load=lambda folder,name:read_bound_report(folder,name,bound,project)
source=base/f'r7-productization-S12-runtime-supervision-qualified-{short}'
browser=base/f'r7-productization-S12-runtime-supervision-ui-serial-{short}'
frontend=base/f'r7-productization-S12-runtime-supervision-ui-qualified-{short}-safe-logs'
buildroot=base/f'r7-native-windows-S12-runtime-supervision-{short}'
roots={name:base/f'r7-native-S12-runtime-supervision-{name}-{short}' for name in ('smoke','research','cloud','restore','service','ssh','installer')}
full=load(source,'qualification.json');ui=load(browser,'ui-qualification.json');front=load(frontend,'ui-qualification.json')
build=load(buildroot,'build-result.json');identity=build['identity']
assert full['passed'] is True and full['tests_run']==1940 and len(full['commands'])==33
assert full['source_before']==full['source_after']==dict(revision=revision,worktree='CLEAN')
assert full['execution']=='LOCAL' and full['github_compute']=='NOT_USED' and full['real_provider_calls']==0 and full['real_credentials']=='NONE' and full['capital']=='NONE'
assert all(row['passed'] is True and row['tree_reaped'] is True and row['failures']==row['errors']==row['skipped']==row['expected_failures']==row['unexpected_successes']==0 for row in full['commands'])
assert ui['passed'] is True and ui['tests_passed']==11 and ui['failures']==ui['skipped']==0 and front['passed'] is True
assert ui['source_before']==ui['source_after']==front['source_before']==front['source_after']==dict(revision=revision,worktree='CLEAN')
reports={kind:load(roots[kind],name) for kind,name in dict(smoke='native-smoke.json',research='native-selected-research.json',cloud='native-S14.json',restore='native-recovery.json').items()}
assert all(value['passed'] is True and value['identity']==identity for value in reports.values())
service=load(roots['service'],'native-service-denial.json');assert service['passed'] is True and service['identity']==identity
integrity=validate_primary_artifacts(repo,revision,source,full,browser,ui,frontend,front,buildroot,build,
 {kind:roots[kind] for kind in reports},reports,roots['service'],service,base/'s12_runtime_supervision_serial_browser_qualify.py')
ssh=load(roots['ssh'],'native-ssh-access.json');validate_ssh_report(roots['ssh'],ssh,identity,bound,project)
installer=load(roots['installer'],'native-installer-denial.json');validate_installer_report(roots['installer'],installer,identity,bound,project)
binding=load(base,f'S12-runtime-supervision-bound-installer-{short}.json')
assert binding['passed'] is True and binding['identity']==identity and binding['revision']==revision and binding['worktree']=='CLEAN'
assert binding['harness_binding']=='BEFORE_AND_AFTER_EXECUTION'
assert set(binding['harness_hashes'])=={'s12_runtime_supervision_bound_installer.py','s13_native_installer_denial_v2.py','s13_installer_package_binding.py'}
pipeline=load(base,f'S12-runtime-supervision-{short}-serial-pipeline.json')
require_sequence(pipeline['commands'],('frontend','native-build','native-service-denial','native-installer-denial','native-ssh-access',
 'native-smoke','native-research','native-cloud','native-restore','full-source','serial-browser'),key='label')
assert pipeline['passed'] is True and pipeline['revision']==revision and pipeline['worktree']=='CLEAN' and pipeline['native_build_identity']==identity
assert pipeline['harness_binding']=='BEFORE_AND_AFTER_EVERY_STAGE'
tree=ast.parse((base/'s12_runtime_supervision_candidate_pipeline.py').read_bytes())
expected_names=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='names' for t in node.targets))
assert len(expected_names)==14 and len(set(expected_names))==14 and set(pipeline['harness_hashes'])==set(expected_names)
for mapping in (pipeline['harness_hashes'],binding['harness_hashes']):
 for name,expected in mapping.items():
  path=require_artifact(base,name,expected);bound[path.relative_to(project).as_posix()]=expected
for row in [*pipeline['commands'],binding['command']]:
 assert row['tree_reaped'] is True and row['exit_code']==0
 if 'passed' in row:assert row['passed'] is True
 path=require_artifact(base,row['log'],row['log_sha256']);bound[path.relative_to(project).as_posix()]=row['log_sha256']
context=load(source,'qualification-context.json');hardware=load(source,'hardware-observations.json')
assert context['launcher_hash']==digest(base/'s12_runtime_supervision_source_qualify.py')
assert context['configuration']==dict(suites=['all'],include_focused=True,require_clean=True,timeout_seconds=900,expected_revision=revision)
assert hardware['samples'] and all(row['physical_memory_bytes']==33736265728 and row['existing_admission_minimum_bytes']==5060439859 for row in hardware['samples'])
source_review=load(base,'S12-runtime-supervision-independent-review.json')
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
for reference,expected in integrity['verified_artifact_hashes'].items():
 if reference in bound and bound[reference]!=expected:raise ValueError('Loaded report and validation commitments differ')
 bound[reference]=expected
private={(buildroot/build['archive']).relative_to(project).as_posix(),(base/'S14LocalFakeRclone.exe').relative_to(project).as_posix()}
target=repo/f'status/codex/productization/S12/supervisor-{short}-py312'
manifest=repo/f'status/codex/productization/S12/supervisor-artifact-hashes-{short}.json'
assert not target.exists() and not manifest.exists();target.mkdir(parents=True)
index=[];seen={}
labels={source:'full-source',browser:'browser',frontend:'frontend',buildroot:'native-build',**{folder:'native-'+name for name,folder in roots.items()}}
def retain(path,relative,expected=None):
 reference=path.relative_to(project).as_posix();raw=path.read_bytes();original='sha256:'+hashlib.sha256(raw).hexdigest()
 if expected is not None and original!=expected:raise ValueError('Evidence changed before retention')
 if reference in seen:
  if seen[reference]!=original:raise ValueError('Duplicate evidence changed')
  return
 require_artifact(path.parent,path.name,original)
 output=raw if path.suffix=='.png' else _sanitize(raw.decode('utf-8').replace('\r\n','\n'),repo).encode('utf-8')
 relative=Path(relative)
 if relative.is_absolute() or '..' in relative.parts:raise ValueError('Retained path escapes evidence root')
 destination=target/relative;assert len(str(destination))<250
 destination.parent.mkdir(parents=True,exist_ok=True)
 with destination.open('xb') as stream:stream.write(output)
 index.append(dict(original_ref=reference,retained_file=relative.as_posix(),original_sha256=original,
  retained_sha256='sha256:'+hashlib.sha256(output).hexdigest(),transformation='NONE' if path.suffix=='.png' else 'UTF8/CRLF_TO_LF/LOCAL_PATH_SANITIZATION'))
 seen[reference]=original
for reference,expected in sorted(bound.items()):
 if reference in private:continue
 path=project/reference
 if path.is_relative_to(repo):continue  # Exact reviewed source already exists in the executable commit.
 label=labels.get(path.parent)
 relative=(label+'/'+path.name) if label else ('harness/'+path.name if path.suffix in ('.py','.cs') else 'pipeline/'+path.name)
 retain(path,relative,expected)
for pattern in ('S12-runtime-supervision-*.log',):
 for log in sorted(base.glob(pattern)):
  retain(log,'development/'+log.name)
  if log.with_suffix('.json').is_file():retain(log.with_suffix('.json'),'development/'+log.with_suffix('.json').name)
for name in ('S14LocalFakeRclone.cs','prepare_s12_runtime_supervision_qualification.py',
 'prepare_s12_runtime_supervision_qualification_integrity.py','prepare_s12_runtime_supervision_qualification_integrity.before-initialization-repair.py',
 'run_s12_runtime_supervision_development.before-source-child-path-repair.py','s12_supervision.before-constraint-review-fix.py',
 's12_runtime_supervision_review_integrity.before-single-read-fix.py','run_s12_runtime_supervision_review_integrity.before-transitive-binding-fix.py',
 'integrate_s12_runtime_supervision.py','record_s12_runtime_supervision_source_checkpoint.py','record_s12_runtime_supervision_qualification_review.py',
 *retention_names,'s13_acceptance_integrity.py','s13_ssh_acceptance_integrity.py','s13_installer_acceptance_integrity.py'):
 retain(base/name,'harness/'+name)
required={reference:expected for reference,expected in bound.items() if reference not in private and not (project/reference).is_relative_to(repo)}
phase={name:sum(row['tests_run'] for row in full['commands'] if row['phase']==name) for name in ('phase_1','phase_2')}
assert phase==dict(phase_1=247,phase_2=1693)
disposition=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',spec_baseline='r7-product-v0.2',revision=revision,worktree='CLEAN',
 state='SCOPED_S12_RUNTIME_CLOUD_SUPERVISOR_AND_REGRESSION_PASS;MASTER_IN_PROGRESS',source=dict(passed=True,tests=1940,commands=33,phase=phase),
 native_build=identity,windows_native=dict(scenarios=integrity['native_scenarios']+15,commands=integrity['native_commands']+15,
  status='SCOPED_UNCHANGED_NATIVE_CONTROL_RESEARCH_MIGRATION_REGRESSION_PASS;RUNTIME_CLOUD_NATIVE_WORKERS_PENDING'),frontend=dict(tests=15,commands=5),browser=dict(cases=11,commands=7),
 memory=dict(samples=len(hardware['samples']),minimum_available_bytes=min(row['available_memory_bytes'] for row in hardware['samples']),
  below_unchanged_admission_threshold=sum(row['available_memory_bytes']<row['existing_admission_minimum_bytes'] for row in hardware['samples'])),
 normal_runtime_cloud_native_workers='NOT_RUN;SOURCE_ROLE_OWNERS_ONLY;NORMAL_S12_COMPOSITION_PENDING',
 production_qualification_profile='PROPOSED_NOT_ACTIVE;ISSUANCE_AND_DEPENDENT_ADMISSION_PENDING_PM_E6',
 independent_retention_review=dict(critical=0,important=0),
 real_cloud='NOT_RUN',real_forward='NOT_RUN',provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',ubuntu24='NOT_RUN',ubuntu26='NOT_RUN',
 independent_source_review=dict(critical=0,important=0),independent_harness_review=dict(critical=0,important=0),
 private_artifact_commitments={ref:bound[ref] for ref in private},accepted_prior_revision='82a6b9ec636236a25c830acad1c915499c5c6229',
 limitations=['S12 normal runtime/worker and restoration authority integration pending','S15 whole product acceptance and S16 pending','Native Ubuntu and real cloud/data/forward/provider commissioning NOT_RUN'])
assert disposition['windows_native']['scenarios']==51 and disposition['windows_native']['commands']==55
assert disposition['memory']['below_unchanged_admission_threshold']==0
(target/'disposition.json').write_text(json.dumps(disposition,indent=2)+'\n',encoding='utf-8',newline='\n')
(target/'retention-index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8',newline='\n')
for reference,expected in bound.items():
 if (project/reference).is_relative_to(repo):
  path=project/reference;require_artifact(path.parent,path.name,expected)
files=publish_retention_manifest(target,manifest,index,required,repository_root=repo)
revision_fact(repo,revision,False)
print(json.dumps(dict(passed=True,retained_files=len(files),source_tests=1940,native_scenarios=51,native_commands=55)))
