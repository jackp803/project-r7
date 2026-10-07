"""Verify a complete scoped candidate before sanitized evidence retention."""
from pathlib import Path
import ast,hashlib,json,re,sys
base=Path(__file__).resolve().parent;project=base.parent
repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.qualification import revision_fact,_sanitize
from s13_installer_acceptance_integrity import read_bound_report,validate_installer_report
from s13_ssh_acceptance_integrity import validate_ssh_report
from s12_runtime_supervision_review_integrity import validate_review_inventory,validate_primary_proof
from s14_feedback_cli_acceptance_core import validate_primary_artifacts,require_artifact,require_sequence,digest,publish_retention_manifest
from s14_feedback_cli_native_evidence import validate_native_paper

revision=sys.argv[1];assert re.fullmatch('[0-9a-f]{40}',revision);short=revision[:7]
revision_fact(repo,revision,True);bound={}
load=lambda folder,name:read_bound_report(folder,name,bound,project)
source=base/f'r7-productization-S14-feedback-cli-qualified-{short}'
browser=base/f'r7-productization-S14-feedback-cli-ui-serial-{short}'
frontend=base/f'r7-productization-S14-feedback-cli-ui-qualified-{short}-safe-logs'
buildroot=base/f'r7-native-windows-S14-feedback-cli-{short}'
roots={name:base/f'r7-native-S14-feedback-cli-{name}-{short}' for name in ('smoke','research','cloud','restore','service','ssh','installer','paper')}
full=load(source,'qualification.json');ui=load(browser,'ui-qualification.json');front=load(frontend,'ui-qualification.json')
build=load(buildroot,'build-result.json');identity=build['identity'];clean=dict(revision=revision,worktree='CLEAN')
assert full['passed'] is True and full['tests_run']==1953 and len(full['commands'])==33
assert full['source_before']==full['source_after']==clean
assert full['execution']=='LOCAL' and full['github_compute']=='NOT_USED' and full['real_provider_calls']==0 and full['real_credentials']=='NONE' and full['capital']=='NONE'
assert all(row['passed'] is True and row['tree_reaped'] is True and row['failures']==row['errors']==row['skipped']==row['expected_failures']==row['unexpected_successes']==0 for row in full['commands'])
assert ui['passed'] is True and ui['tests_passed']==11 and ui['failures']==ui['skipped']==0 and front['passed'] is True
assert ui['source_before']==ui['source_after']==front['source_before']==front['source_after']==clean
reports={kind:load(roots[kind],name) for kind,name in dict(smoke='native-smoke.json',research='native-selected-research.json',cloud='native-S14.json',restore='native-recovery.json').items()}
assert all(value['passed'] is True and value['identity']==identity for value in reports.values())
service=load(roots['service'],'native-service-denial.json');assert service['passed'] is True and service['identity']==identity
integrity=validate_primary_artifacts(repo,revision,source,full,browser,ui,frontend,front,buildroot,build,
    {kind:roots[kind] for kind in reports},reports,roots['service'],service,base/'s14_feedback_cli_serial_browser_qualify.py')
ssh=load(roots['ssh'],'native-ssh-access.json');validate_ssh_report(roots['ssh'],ssh,identity,bound,project)
installer=load(roots['installer'],'native-installer-denial.json');validate_installer_report(roots['installer'],installer,identity,bound,project)
binding=load(base,f'S14-feedback-cli-bound-installer-{short}.json')
assert binding['passed'] is True and binding['identity']==identity and binding['revision']==revision and binding['worktree']=='CLEAN'
assert binding['harness_binding']=='BEFORE_AND_AFTER_EXECUTION'
assert set(binding['harness_hashes'])=={'s14_feedback_cli_bound_installer.py','s13_native_installer_denial_v2.py','s13_installer_package_binding.py'}
pipeline=load(base,f'S14-feedback-cli-{short}-serial-pipeline.json')
require_sequence(pipeline['commands'],('frontend','native-build','native-service-denial','native-installer-denial','native-ssh-access',
    'native-smoke','native-research','native-cloud','native-restore','native-paper-feedback','full-source','serial-browser'),key='label')
assert pipeline['passed'] is True and pipeline['revision']==revision and pipeline['worktree']=='CLEAN' and pipeline['native_build_identity']==identity
assert pipeline['harness_binding']=='BEFORE_AND_AFTER_EVERY_STAGE'
tree=ast.parse((base/'s14_feedback_cli_candidate_pipeline.py').read_bytes())
expected_names=next(ast.literal_eval(node.value) for node in tree.body if isinstance(node,ast.Assign)
    and any(isinstance(target,ast.Name) and target.id=='names' for target in node.targets))
assert len(expected_names)==len(set(expected_names))==16 and set(pipeline['harness_hashes'])==set(expected_names)
for mapping in (pipeline['harness_hashes'],binding['harness_hashes']):
    for name,expected in mapping.items():
        path=require_artifact(base,name,expected);bound[path.relative_to(project).as_posix()]=expected
for row in [*pipeline['commands'],binding['command']]:
    assert row['tree_reaped'] is True and row['exit_code']==0
    if 'passed' in row:assert row['passed'] is True
    path=require_artifact(base,row['log'],row['log_sha256']);bound[path.relative_to(project).as_posix()]=row['log_sha256']
context=load(source,'qualification-context.json');hardware=load(source,'hardware-observations.json')
assert context['launcher_hash']==digest(base/'s14_feedback_cli_source_qualify.py')
assert context['configuration']==dict(suites=['all'],include_focused=True,require_clean=True,timeout_seconds=900,expected_revision=revision)
assert hardware['samples'] and all(row['physical_memory_bytes']==33736265728 and row['existing_admission_minimum_bytes']==5060439859 for row in hardware['samples'])
native=load(roots['paper'],'native-paper-feedback.json')
fixture_names=('tests/product/test_paper_runtime_v02.py','tests/registry/test_operational_lifecycle_v02.py',
    'tests/application/test_product_assessment_binding.py','tests/validation/test_paper_promotion_policy.py')
native_paths=(base/'s14_feedback_cli_native_paper.py',base/'S14LocalFakeRclone.exe',base/'S14LocalFakeRclone.cs',*(repo/name for name in fixture_names))
native_inputs={path.relative_to(project).as_posix():path for path in native_paths}
validate_native_paper(roots['paper'],native,identity,inputs=native_inputs,bound=bound,project=project)
source_review=load(base,'S14-paper-feedback-cli-independent-source-review.json')
source_names=('src/application/cli.py','src/storage/_sqlite_registry.py','src/storage/paper_process.py',
    'tests/product/test_paper_feedback_cli.py','tests/storage/test_paper_process_existing.py','docs/product/v0_2/PAPER_FEEDBACK_IMPLEMENTATION.md')
source_paths=(*(repo/name for name in source_names),base/'S14-paper-feedback-cli-increment-plan.md',base/'run_s14_paper_feedback_cli_increment.py')
validate_review_inventory(source_review,kind='INDEPENDENT_BOUNDED_READ_ONLY_HISTORICAL_PAPER_PUBLICATION_SOURCE_REVIEW',
    files={path.relative_to(project).as_posix():path for path in source_paths},bound=bound,project=project)
focused_paths=(base/'run_s14_paper_feedback_cli_increment.py',repo/'src/application/cli.py',repo/'tests/product/test_paper_feedback_cli.py',
    repo/'tests/storage/test_paper_process_existing.py',base/'S14-paper-feedback-cli-increment-plan.md')
for stem,count in (('S14-paper-feedback-cli-existing-race-GREEN',11),('S14-paper-feedback-cli-existing-race-affected-GREEN',90)):
    proof=validate_primary_proof(base,stem,count,inputs={path.relative_to(project).as_posix():path for path in focused_paths},
        input_fields=('input_sha256_before','input_sha256_after'),bound=bound,project=project)
    assert proof['source_before']==proof['source_after'] and proof['implementation_hash_before']==proof['implementation_hash_after']==identity['implementation_hash']
harness_names=('s14_feedback_cli_candidate_pipeline.py','s14_feedback_cli_ui_frontend.py','s14_feedback_cli_bound_installer.py',
    's14_feedback_cli_source_qualify.py','s14_feedback_cli_serial_browser_qualify.py','s14_feedback_cli_native_paper.py',
    'test_s14_feedback_cli_qualification_integrity.py','run_s14_feedback_cli_qualification_integrity.py',
    'prepare_s14_feedback_cli_qualification.py','prepare_s14_feedback_cli_integrity.py')
harness_review=load(base,'S14-paper-feedback-cli-independent-qualification-review.json')
validate_review_inventory(harness_review,kind='INDEPENDENT_BOUNDED_READ_ONLY_PREEXECUTION_QUALIFICATION_HARNESS_REVIEW',
    files={name:base/name for name in harness_names},bound=bound,project=project)
guard_inputs={name:base/name for name in (*expected_names,'run_s14_feedback_cli_qualification_integrity.py','test_s14_feedback_cli_qualification_integrity.py')}
guard=validate_primary_proof(base,'S14-paper-feedback-cli-cleanup-integrity-GREEN',10,inputs=guard_inputs,
    input_fields=('input_sha256_before','input_sha256_after'),bound=bound,project=project)
assert harness_review['primary_regression']==dict(report='S14-paper-feedback-cli-cleanup-integrity-GREEN.json',
    report_sha256=digest(base/'S14-paper-feedback-cli-cleanup-integrity-GREEN.json'),
    log='S14-paper-feedback-cli-cleanup-integrity-GREEN.log',log_sha256=guard['log_sha256'],tests=10)
retention_names=('s14_feedback_cli_accept.py','s14_feedback_cli_acceptance_core.py','s14_feedback_cli_native_evidence.py',
    'test_s14_feedback_cli_native_evidence.py','run_s14_feedback_cli_retention_integrity.py')
retention_review=load(base,'S14-paper-feedback-cli-independent-retention-review.json')
validate_review_inventory(retention_review,kind='INDEPENDENT_BOUNDED_READ_ONLY_RETENTION_AND_PRIMARY_PROOF_REVIEW',
    files={name:base/name for name in retention_names},bound=bound,project=project)
retention_dependencies=(*retention_names,'s12_runtime_supervision_review_integrity.py','s14_feedback_acceptance_core.py',
    's13_installer_acceptance_integrity.py','s13_ssh_acceptance_integrity.py','s13_acceptance_integrity.py')
retention_guard=validate_primary_proof(base,'S14-paper-feedback-cli-retention-reviewed-GREEN',6,
    inputs={name:base/name for name in retention_dependencies},input_fields=('input_sha256_before','input_sha256_after'),bound=bound,project=project)
assert retention_review['primary_regression']==dict(report='S14-paper-feedback-cli-retention-reviewed-GREEN.json',
    report_sha256=digest(base/'S14-paper-feedback-cli-retention-reviewed-GREEN.json'),
    log='S14-paper-feedback-cli-retention-reviewed-GREEN.log',log_sha256=retention_guard['log_sha256'],tests=6)
for reference,expected in integrity['verified_artifact_hashes'].items():
    if reference in bound and bound[reference]!=expected:raise ValueError('Loaded and validated commitments differ')
    bound[reference]=expected
private={(buildroot/build['archive']).relative_to(project).as_posix(),(base/'S14LocalFakeRclone.exe').relative_to(project).as_posix()}
target=repo/f'status/codex/productization/S14/cli-publisher-{short}-py312'
manifest=repo/f'status/codex/productization/S14/cli-publisher-artifact-hashes-{short}.json'
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
    if relative.is_absolute() or '..' in relative.parts:raise ValueError('Retained path escapes root')
    destination=target/relative
    if len(str(destination))>=250:
        relative=Path('short-names')/(hashlib.sha256(reference.encode()).hexdigest()[:24]+path.suffix);destination=target/relative
    assert len(str(destination))<250
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('xb') as stream:stream.write(output)
    index.append(dict(original_ref=reference,retained_file=relative.as_posix(),original_sha256=original,
        retained_sha256='sha256:'+hashlib.sha256(output).hexdigest(),transformation='NONE' if path.suffix=='.png' else 'UTF8/CRLF_TO_LF/LOCAL_PATH_SANITIZATION'))
    seen[reference]=original
for reference,expected in sorted(bound.items()):
    path=project/reference
    if reference in private or path.is_relative_to(repo):continue
    label=labels.get(path.parent)
    relative=label+'/'+path.name if label else ('harness/' if path.suffix in ('.py','.cs') else 'pipeline/')+path.name
    retain(path,relative,expected)
for log in sorted(base.glob('S14-paper-feedback-cli-*.log')):
    retain(log,'development/'+log.name)
    if log.with_suffix('.json').is_file():retain(log.with_suffix('.json'),'development/'+log.with_suffix('.json').name)
for name in (*retention_dependencies,'s14_cli.before-existing-only-race-fix.py','s14_feedback_cli_native_paper.before-cleanup-fix.py',
    'record_s14_feedback_cli_source_checkpoint.py','record_s14_feedback_cli_qualification_review.py'):
    retain(base/name,'harness/'+name)
phase={name:sum(row['tests_run'] for row in full['commands'] if row['phase']==name) for name in ('phase_1','phase_2')}
assert phase==dict(phase_1=247,phase_2=1706)
disposition=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',spec_baseline='r7-product-v0.2',revision=revision,worktree='CLEAN',
    state='SCOPED_HISTORICAL_PAPER_PUBLICATION_CLI_PASS;MASTER_IN_PROGRESS',
    source=dict(passed=True,tests=1953,commands=33,phase=phase),native_build=identity,
    windows_native=dict(scenarios=integrity['native_scenarios']+15+native['scenario_count'],
        commands=integrity['native_commands']+15+native['command_count'],status='SCOPED_NATIVE_CONTROL_RESEARCH_CLOUD_RECOVERY_AND_HISTORICAL_PAPER_PUBLICATION_PASS;NORMAL_RUNTIME_PENDING'),
    native_historical_paper=dict(scenarios=3,commands=2,fixture_origin=native['fixture_origin'],fixture_cleanup_complete=True),
    frontend=dict(tests=15,commands=5),browser=dict(cases=11,commands=7),
    memory=dict(samples=len(hardware['samples']),minimum_available_bytes=min(row['available_memory_bytes'] for row in hardware['samples']),
        below_unchanged_admission_threshold=sum(row['available_memory_bytes']<row['existing_admission_minimum_bytes'] for row in hardware['samples'])),
    normal_continuous_runtime='NOT_RUN',production_qualification_profile='PROPOSED_NOT_ACTIVE',
    independent_source_review=dict(critical=0,important=0),independent_harness_review=dict(critical=0,important=0),independent_retention_review=dict(critical=0,important=0),
    real_cloud='NOT_RUN',real_forward='NOT_RUN',provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',ubuntu24='NOT_RUN',ubuntu26='NOT_RUN',
    private_artifact_commitments={ref:bound[ref] for ref in private},accepted_prior_revision='e293a947f886d9814c89983fd9e03151c1695788',
    limitations=['Native historical publication consumes source-created accelerated history, not normal native PAPER composition',
        'Production qualified-release issuance,normal runtime and restoration integration pending',
        'S15 whole-product/capacity,S16,native Ubuntu and real cloud/data/forward/provider commissioning pending'])
assert disposition['windows_native']['scenarios']==54 and disposition['windows_native']['commands']==57
assert disposition['memory']['below_unchanged_admission_threshold']==0
(target/'disposition.json').write_text(json.dumps(disposition,indent=2)+'\n',encoding='utf-8',newline='\n')
(target/'retention-index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8',newline='\n')
for reference,expected in bound.items():
    if (project/reference).is_relative_to(repo):
        path=project/reference;require_artifact(path.parent,path.name,expected)
required={ref:value for ref,value in bound.items() if ref not in private and not (project/ref).is_relative_to(repo)}
files=publish_retention_manifest(target,manifest,index,required,repository_root=repo)
revision_fact(repo,revision,False)
print(json.dumps(dict(passed=True,retained_files=len(files),source_tests=1953,native_scenarios=54,native_commands=57)))
