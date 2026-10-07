"""Retain exact-clean successful scoped service-subject and Windows recovery evidence, never private bundles."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
project=Path(__file__).resolve().parent.parent
root=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(root/'src'))
from application.qualification import _sanitize,revision_fact
revision=sys.argv[1];assert __import__('re').fullmatch('[0-9a-f]{40}',revision);short=revision[:7]
assert revision_fact(root,revision,True)==dict(revision=revision,worktree='CLEAN')
load=lambda p:json.loads(p.read_bytes())
hash_bytes=lambda raw:'sha256:'+hashlib.sha256(raw).hexdigest()
source=project/f'artifacts/r7-productization-S13-recovery-qualified-{short}'
full=load(source/'qualification.json')
assert full['passed'] and full['tests_run']==1828 and len(full['commands'])==33
assert full['source_before']==full['source_after']==dict(revision=revision,worktree='CLEAN')
assert all(c['passed'] and c['tree_reaped'] and c['failures']==c['errors']==c['skipped']==0 for c in full['commands'])
ui_root=project/f'artifacts/r7-productization-S13-recovery-ui-serial-{short}'
ui=load(ui_root/'ui-qualification.json')
assert ui['passed'] and len(ui['commands'])==7 and ui['source_before']==ui['source_after']==full['source_before']
assert ui['frontend_commands'][3]['tests_passed']==15 and ui['tests_passed']==11
assert ui['qualification_mode']=='SERIAL_FIXTURE_BROWSER_QUALIFICATION'
assert len(ui['browser_cases_observed'])==len(set(ui['browser_cases_observed']))==11
assert set(ui['browser_cases_observed'])==set(ui['expected_cases'])
assert all(c['passed'] and c['tree_reaped'] and c['browser_stats']['unexpected']==c['browser_stats']['skipped']==c['browser_stats']['flaky']==0 and c['errors_count']==0 for c in ui['commands'])
assert ui['missing_screenshots']==[] and len(ui['screenshot_hashes'])==6
build_root=project/f'artifacts/r7-native-windows-S13-recovery-{short}'
build=load(build_root/'build-result.json')
identity=build['identity'];assert identity['executable_revision']==revision and identity['financial_authority']=='NONE'
native_roots={name:project/f'artifacts/r7-native-S13-recovery-{name}-{short}' for name in ('smoke','research','cloud','restore')}
smoke=load(native_roots['smoke']/'native-smoke.json')
research=load(native_roots['research']/'native-selected-research.json')
cloud=load(native_roots['cloud']/'native-S14.json')
restore=load(native_roots['restore']/'native-recovery.json')
assert all(report['passed'] and report['identity']==identity for report in (smoke,research,cloud,restore))
assert smoke['scenario_count']==8 and len(smoke['commands'])==9
assert cloud['scenario_count']==12 and len(cloud['commands'])==12
assert research['exit_code']==0 and research['tree_reaped'] and research['actual_job']['state']=='COMPLETE'
assert restore['scenario_count']>=12 and restore['command_count']>=15
assert all(c['passed'] and c['tree_reaped'] for c in restore['commands'])
review=load(project/'artifacts/S13-independent-recovery-review.json')
assert review['source_review']['remaining_important_findings']==review['native_harness_review']['remaining_important_findings']==0
pipeline=load(project/f'artifacts/S13-recovery-{short}-serial-pipeline.json')
assert pipeline['passed'] and len(pipeline['commands'])==7 and all(c['passed'] and c['tree_reaped'] for c in pipeline['commands'])
assert pipeline['revision']==revision and pipeline['worktree']=='CLEAN'
long_review=load(project/'artifacts/S13-independent-long-path-review.json')
assert long_review['critical_findings']==long_review['important_findings']==0
service_review=load(project/'artifacts/S13-service-independent-review-v2.json')
assert service_review['remaining_critical']==service_review['remaining_important']==0
for name,expected in service_review['reviewed_source_hashes'].items():assert hash_bytes((root/name).read_bytes())==expected
browser_review=load(project/'artifacts/S13-service-launcher-review-v2.json')
assert browser_review['remaining_critical']==browser_review['remaining_important']==0
for name,expected in browser_review['harness_hashes'].items():assert hash_bytes((project/'artifacts'/name).read_bytes())==expected
denial_root=project/f'artifacts/r7-native-S13-service-denial-{short}'
denial=load(denial_root/'native-service-denial.json')
assert denial['passed'] and denial['identity']==identity
assert len(denial['commands'])==len(denial['scenarios'])==3
assert all(c['passed'] and c['tree_reaped'] and c['exit_code']==2 for c in denial['commands'])
assert all(c['passed'] for c in denial['scenarios'])
assert ui['initial_attempt']['status']=='NOT_RUN_PENDING_SERIAL_BROWSER'
assert ui['initial_attempt']['qualification_scope']=='FRONTEND_ONLY'
from s13_acceptance_integrity import validate_primary_artifacts,publish_retention_manifest
initial=project/f'artifacts/r7-productization-S13-recovery-ui-qualified-{short}-safe-logs'
frontend=load(initial/'ui-qualification.json')
integrity=validate_primary_artifacts(root,revision,source,full,ui_root,ui,initial,frontend,build_root,build,
    native_roots,dict(smoke=smoke,research=research,cloud=cloud,restore=restore),denial_root,denial,
    project/'artifacts/s13_service_serial_browser_qualify_v2.py')
assert integrity['source_commands']==33 and integrity['native_scenarios']==36 and integrity['native_commands']==40
phase_counts={phase:sum(c['tests_run'] for c in full['commands'] if c['phase']==phase) for phase in ('phase_1','phase_2')}
assert sum(phase_counts.values())==full['tests_run']
target=root/f'status/codex/productization/S13/service-{short}-py312';assert not target.exists()
target.mkdir(parents=True);index=[]
def retain(file,relative,binary=False):
    original=file.read_bytes()
    original_ref=file.relative_to(project).as_posix()
    expected=integrity['verified_artifact_hashes'].get(original_ref)
    if expected is not None and hash_bytes(original)!=expected:raise ValueError('Verified evidence changed before copying')
    raw=original if binary else _sanitize(original.decode('utf-8',errors='replace').replace('\r\n','\n'),root).encode('utf-8')
    destination=target/relative;assert len(str(destination))<250
    destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(raw)
    index.append(dict(original_ref=file.relative_to(project).as_posix(),retained_file=relative,
        original_sha256=hash_bytes(original),retained_sha256=hash_bytes(raw),
        integrity='RECORDED_OR_LOADED_REPORT_HASH_VERIFIED' if expected is not None else 'COLLECTION_HASH_ONLY;SUPPLEMENTAL_NOT_USED_FOR_PASS',transformation='NONE' if binary else 'UTF8_REPLACEMENT_DECODE/CRLF_TO_LF/LOCAL_PATH_SANITIZATION'))
def top(folder,label,images=False):
    for file in sorted(folder.iterdir()):
        if not file.is_file():continue
        if file.suffix=='.log' or file.name.endswith('-browser-results.json') or file.name in ('qualification.json','qualification-context.json','hardware-observations.json',
            'ui-qualification.json','browser-results.json','native-smoke.json','native-selected-research.json','native-S14.json','native-recovery.json','native-service-denial.json'):
            retain(file,label+'/'+file.name)
        elif images and file.suffix=='.png':retain(file,label+'/'+file.name,True)
top(source,'full-source');top(ui_root,'browser',True)
for profile in ('empty','research','paper','protected','temporal','approval','deployment'):
    retain(ui_root/(profile+'.config.mjs'),'browser/'+profile+'.config.mjs')
initial=project/f'artifacts/r7-productization-S13-recovery-ui-qualified-{short}-safe-logs'
top(initial,'frontend-only')
top(denial_root,'native-service-denial')
retain(project/f'artifacts/S13-recovery-{short}-serial-pipeline.json','pipeline/serial-pipeline.json')
for name,folder in native_roots.items():top(folder,'native-'+name)
retain(build_root/'build-result.json','native-build/build-result.json')
for pattern in ('S13-service-*.log','S13-control-asset-junction-*.log',f'S13-recovery-{short}-*.log'):
    for file in sorted((project/'artifacts').glob(pattern)):
        retain(file,'development/'+file.name)
        summary=file.with_suffix('.json')
        if summary.is_file():retain(summary,'development/'+summary.name)
retain(project/'artifacts/S13-independent-recovery-review.json','review/retained-recovery-harness-review.json')
retain(project/'artifacts/S13-independent-long-path-review.json','review/retained-long-path-review.json')
retain(project/'artifacts/S13-service-independent-review-v2.json','review/service-source-review.json')
retain(project/'artifacts/S13-service-launcher-review-v2.json','review/service-launcher-review.json')
for name in ('s13_service_ui_frontend.py','s13_service_candidate_pipeline.py','s13_service_serial_browser_qualify_v2.py',
    's13_native_service_denial.py','s13_service_qualify.py','s13_prepare_service_qualification.py',
    's13_prepare_service_accept.py','s13_service_accept_v2.py','s13_prepare_service_integrity_v2.py','s13_acceptance_integrity.py','s13_acceptance_integrity_tests.py','run_s13_integrity_tests.py','s13_record_service_reviews.py',
    'run_bounded_unittest.py','run_bounded_suite_unittest.py','s13_native_recovery_probe.py',
    's13_native_research_probe.py','s14_native_probe.py','s13_refresh_authoring_examples_v5.py',
    's13_retain_withdrawn_service_5f42a84.py'):
    retain(project/'artifacts'/name,'harness/'+name)
# Retain every verified public artifact explicitly; directory enumeration cannot
# silently omit an artifact deleted after validation. Native archives stay private.
private_archive_ref=(build_root/build['archive']).relative_to(project).as_posix()
required={name:value for name,value in integrity['verified_artifact_hashes'].items() if name!=private_archive_ref}
labels={source:'full-source',ui_root:'browser',initial:'frontend-only',build_root:'native-build',denial_root:'native-service-denial',
    **{folder:'native-'+name for name,folder in native_roots.items()}}
retained_refs={row['original_ref'] for row in index}
for reference in sorted(required):
    if reference not in retained_refs:
        file=project/reference
        retain(file,labels[file.parent]+'/'+file.name,file.suffix=='.png')
measurements=load(source/'hardware-observations.json')['samples']
facts=dict(schema_version='r7-scoped-service-qualification-v0.2',task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',
    spec_baseline='r7-product-v0.2',qualified_executable_revision=revision,
    previous_qualified_executable_revision='86643c4b0444db2cfb33ce071618c1e3f708ad37',result='PASS',scope='GUARDED_SERVICE_SOURCE_AND_SCOPED_WINDOWS_RECOVERY;UBUNTU_SERVICE_NOT_RUN',
    full_source=dict(result='PASS',commands=33,tests=full['tests_run'],phase_1=phase_counts['phase_1'],phase_2=phase_counts['phase_2'],failures=0,errors=0,skipped=0),
    browser=dict(result='PASS',frontend_commands=5,fixture_commands=7,unit_tests=15,browser_tests=11,screenshots=6,
        browser_version=ui['browser_version'],mode='ACTUAL_EDGE_SERIAL_ISOLATED_SYNTHETIC_FIXTURES',
        initial_frontend_scope='FRONTEND_ONLY;BROWSER_PENDING_UNTIL_SERIAL_RUN',assertions='SAME11UNCHANGED_CASES',
        resource_admission='UNCHANGED',orchestration='ONE_ACTUAL_SOURCE_FIXTURE_AT_A_TIME',
        restored_native_http='COVERED_SEPARATELY;NO_NEW_RESTORED_BROWSER_CASE'),
    native=dict(result='PASS',scope='SCOPED_WINDOWS_NATIVE_ONLY',scenarios=smoke['scenario_count']+1+cloud['scenario_count']+restore['scenario_count']+len(denial['scenarios']),
        commands=len(smoke['commands'])+1+len(cloud['commands'])+restore['command_count']+len(denial['commands']),
        windows_service_platform_denial=3,smoke=smoke['scenario_count'],selected_research=1,offline_cloud=cloud['scenario_count'],private_recovery=restore['scenario_count'],
        identity=identity,archive_sha256=build['archive_sha256'],archive_files=build['files'],
        product_path='EMPTY',pythonpath='UNSET',ubuntu='NOT_RUN'),
    memory=dict(actual_samples=len(measurements),physical_memory_bytes=measurements[0]['physical_memory_bytes'],
        minimum_available_bytes=min(r['available_memory_bytes'] for r in measurements),
        below_existing_admission_threshold_samples=sum(r['available_memory_bytes']<r['existing_admission_minimum_bytes'] for r in measurements),
        threshold_changes='NONE',previous_failure_instantaneous_cause='UNPROVEN'),
    independent_review='BOUNDED_SOURCE_AND_HARNESS_REVIEW;NO_REMAINING_CRITICAL_OR_IMPORTANT;NOT_WHOLE_BRANCH',
    private_artifacts='DATABASES/BACKUPS/AUTH/SESSION/RAW_CAPTURE/PRIVATE_CONFIG/NATIVE_ARCHIVE_REMAIN_LOCAL',
    real_provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED',real_cloud='NOT_RUN',
    real_forward_paper='NOT_RUN',live='NOT_AUTHORIZED',
    evidence_integrity={k:v for k,v in integrity.items() if k!='verified_artifact_hashes'},
    pending=['S13 native service install/uninstall/SSH code and actual Ubuntu package/systemd/reboot qualification',
        'S12 continuous runtime composition and restoration release/preflight integration',
        'S14 forward/performance feedback','S15 capacity/whole-product mapping','S16 whole-branch review'])
(target/'disposition.json').write_text(json.dumps(facts,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
(target/'original-to-retained.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
manifest=root/f'status/codex/productization/S13/service-artifact-hashes-{short}.json'
assert not manifest.exists()
files=publish_retention_manifest(target,manifest,index,required,repository_root=root)
ref=target.relative_to(root).as_posix()
path=root/'coordination/CODEX/PROGRESS.json';progress=load(path)
assert progress['qualified_executable_revision']==facts['previous_qualified_executable_revision']
progress.update(candidate_executable_revision=revision,qualified_executable_revision=revision,active_step='S13',
    next_step='Implement bounded native install/service configuration and SSH health tooling; continue S12 actual continuous runtime/restoration authority integration, S14 forward feedback and S15-S16. Ubuntu/real cloud/real forward/provider commissioning remain NOT_RUN; no full-product PASS.')
progress['steps']['S13']='IN_PROGRESS'
progress['service_increment'].update(status='SCOPED_WINDOWS_AND_SOURCE_PASS;UBUNTU_SERVICE_NOT_RUN',source_checkpoint=revision,full_source='PASS',native='SCOPED_WINDOWS_PASS',browser='SERIAL_SAME11CASES_PASS',evidence_ref=ref+'/disposition.json')
progress['tests_executed'].append(dict(step='S13',phase='EXACT_CLEAN_SERVICE_SUBJECT_AND_WINDOWS_RECOVERY_QUALIFICATION',
    status='PASS',evidence_ref=ref+'/disposition.json',**{k:v for k,v in facts.items() if k!='schema_version'}))
progress['evidence_refs'].append(ref+'/disposition.json')
progress['service_qualified_checkpoint']=dict(status='PASS',scope='SERVICE_SOURCE_AND_WINDOWS_RECOVERY_ONLY;UBUNTU_NOT_RUN',qualified_executable_revision=revision,
    evidence_ref=ref+'/disposition.json',source_tests=full['tests_run'],native_scoped_scenarios=facts['native']['scenarios'],
    native_commands=facts['native']['commands'],ui_unit_tests=15,browser_tests=11,remaining=facts['pending'])
progress['platforms']['windows-11-x86_64'].update(native_package_status='PASS',native_package_scope='SERVICE_PLATFORM_DENIAL_AND_RETAINED_PRIVATE_RECOVERY_OFFLINE_BRIDGE',
    native_first_run_status='PASS',native_first_run_revision=revision,native_first_run_scenarios=8,native_first_run_commands=9,
    native_first_run_build_hash=identity['build_hash'],native_archive_sha256=build['archive_sha256'],native_full_product_acceptance='NOT_RUN')
path.write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
handoff=root/'coordination/CODEX/HANDOFF.md'
note=(f'S13 scoped service/recovery executable {revision} qualified CLEAN:33 full commands/{full['tests_run']} tests ({phase_counts['phase_1']} focused+{phase_counts['phase_2']} full),0 failures/errors/skips;15 UI tests+11 unchanged actual Edge browser cases across7 serial fixtures/6 screenshots (frontend-only preparation followed by exact serial browser qualification);'
    f'Windows native {facts["native"]["scenarios"]} scoped scenarios/{facts["native"]["commands"]} commands across service platform denial/smoke/research/offline bridge/private recovery PASS;actual Ubuntu service/kernel/installNOT_RUN;build {identity["build_hash"]};archive {build["archive_sha256"]}. '
    f'{len(measurements)} actual memory samples,minimum{facts["memory"]["minimum_available_bytes"]} bytes,{facts["memory"]["below_existing_admission_threshold_samples"]} sampled values below unchanged admission threshold;prior historical failure instantaneous cause remains UNPROVEN. '
    f'Independent bounded source/harness review has no remaining Critical/Important findings;not whole-branch review. Evidence {ref}/disposition.json. '
    f'S13 remains IN_PROGRESS:Ubuntu native/services/install/reboot/SSH, S12 runtime/restoration integration, S14 forward feedback, S15-S16 pending. '
    f'All private bundles/DBs/auth/session/config/raw captures/native archives remain local within project root. Real provider0,credentialsNONE,capitalNONE,GitHub computeNOT_USED,main mergeNOT_PERFORMED. Continue automatically.\n\n')
handoff.write_text(note+handoff.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print(json.dumps(dict(retained_files=len(files),result=facts['result'],qualified_executable=revision,
    native_scenarios=facts['native']['scenarios'],native_commands=facts['native']['commands'])))
