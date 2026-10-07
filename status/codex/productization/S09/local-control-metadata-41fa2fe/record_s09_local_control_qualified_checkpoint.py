"""Record scoped actual evidence without granting release or financial authority."""
from pathlib import Path
import hashlib,json,sys

BASE=Path(__file__).resolve().parent
REPO=BASE.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(REPO/'src'))
from application.datasets.catalog import read_local

REVISION='41fa2fe0d74435fed5831ed728af8b87c28883f0'
REF='status/codex/productization/S09/local-control-qualified-41fa2fe-py312'
MANIFEST='status/codex/productization/S09/local-control-qualified-artifact-hashes-41fa2fe.json'
sha=lambda raw:'sha256:'+hashlib.sha256(raw).hexdigest()
def read(name):return read_local(REPO,name,64*1024**2)
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')

def main():
    manifest=json.loads(read(MANIFEST))
    mandatory={REF+'/disposition.json',REF+'/native-build/build-result.json'}
    assert mandatory<=manifest['files'].keys(),'MISSING_MANDATORY_QUALIFICATION_ARTIFACTS'
    assert len(manifest['files'])==74 and all(name.startswith(REF+'/') for name in manifest['files'])
    snapshots={}
    for name,expected in manifest['files'].items():
        raw=read(name);assert sha(raw)==expected;snapshots[name]=raw
    facts=json.loads(snapshots[REF+'/disposition.json'])
    build=json.loads(snapshots[REF+'/native-build/build-result.json'])
    assert build['identity']==facts['native_build']
    assert facts['revision']==REVISION and facts['source']==dict(passed=True,tests=1974,commands=33,
        phase=dict(phase_1=247,phase_2=1727))
    assert facts['native_scoped']==dict(passed=True,scenarios=13,commands=13,wrapper_stages=4)
    assert facts['ordinary_native_paper']=='NOT_RUN' and facts['native_worker_invoked'] is False
    assert facts['provider_requests']==0 and facts['credentials']=='NONE' and facts['capital']=='NONE'
    progress_path=REPO/'coordination/CODEX/PROGRESS.json';progress=json.loads(progress_path.read_bytes())
    assert progress['qualified_executable_revision']==facts['accepted_prior_revision'] and progress['state']=='IN_PROGRESS'
    assert progress['paper_read_control_composition']['status']=='SOURCE_4_NEW_34_REGRESSION_PASS;EXACT_CLEAN_PENDING'
    progress.update(qualified_executable_revision=REVISION,candidate_executable_revision=REVISION,active_step='S09/S12/S13',
        next_step='Implement bounded internal qualification receipt issuer/store/adapter with isolated fixtures and actual native PAPER owner composition/probes. '
        'Production release profile remains PROPOSED_NOT_ACTIVE pending PM/E6 acceptance. Full master/S15/S16 and mandatory Ubuntu evidence remain open.')
    checkpoint=dict(status='EXACT_CLEAN_SOURCE_PASS;SCOPED_NATIVE_READ_START_DENIAL_AND_REGRESSION_PASS',
        qualified_executable_revision=REVISION,implementation_hash=facts['implementation_hash'],
        source_tests=1974,source_commands=33,phase_1=247,phase_2=1727,failures=0,errors=0,skipped=0,
        native_build=facts['native_build'],native_scoped_scenarios=13,native_scoped_commands=13,
        native_paper_inventory_and_start_denial_scenarios=2,native_auth_origin='NEW_SOURCE_CREATED_SYNTHETIC_FIXTURE;NOT_NATIVE_CLI_ENROLLMENT',
        ordinary_native_paper='NOT_RUN',native_worker_invoked=False,browser='NOT_RUN_FOR_THIS_CANDIDATE',
        production_qualification_profile='PROPOSED_NOT_ACTIVE',memory=facts['memory'],
        external_fixed_input_regressions=3,external_retention_scope_regressions=2,
        evidence_ref=REF+'/disposition.json',manifest_ref=MANIFEST,retained_files=len(manifest['files']),
        independent_review='BOUNDED_SOURCE_AND_EXTERNAL_TOOLING;0_CRITICAL_0_IMPORTANT;REVIEWER_EXECUTION_NONE;NO_WHOLE_PRODUCT_REVIEW')
    progress['paper_read_control_composition'].update(checkpoint)
    progress['tests_executed'].append({**checkpoint,'step':'S09/S13',
        'phase':'EXACT_CLEAN_LOCAL_PAPER_READ_CONTROL_AND_SCOPED_NATIVE_REGRESSION','status':'PASS',
        'qualification_scope_status':checkpoint['status']})
    progress['evidence_refs'].append(REF+'/disposition.json')
    progress['platforms']['windows-11-x86_64'].update(native_package_status='PASS',native_first_run_status='PASS',
        native_first_run_revision=REVISION,native_first_run_scenarios=8,native_first_run_commands=9,
        native_first_run_build_hash=facts['native_build']['build_hash'],native_full_product_acceptance='NOT_RUN',
        native_package_scope='SCOPED_BUILD_8_FIRST_RUN_3_HISTORICAL_PUBLICATION_2_AUTHENTICATED_PAPER_READ_START_DENIAL;WORKER_NOT_INVOKED;BROWSER_NOT_RUN',
        native_archive_sha256=build['archive_sha256'])
    assert all(progress['steps'][step]=='IN_PROGRESS' for step in ('S09','S12','S13','S14','S15'))
    save(progress_path,progress)
    note=(f'S09/S13 ordinary Control Center PAPER read/pause composition qualified at exact-clean executable {REVISION}: '
        '33 source commands/1974 execution instances PASS (phase1 247,phase2 1727),0 failures/errors/skips,610 bound source inputs unchanged,all owned trees reaped. '
        'Windows native build,8 first-run,3 historical-publication and2 authenticated empty inventory/start-denial scenarios PASS;13 native commands across4 wrapper stages. '
        'Fresh local auth is a source-created synthetic fixture;no native CLI enrollment or existing user auth access. '
        'Reader control teardown uses owned kernel termination;no managed-stop claim. '
        f'Build {facts["native_build"]["build_hash"]}; implementation {facts["implementation_hash"]}. '
        f'{facts["memory"]["samples"]} actual host memory samples,min{facts["memory"]["minimum_available_bytes"]} available bytes,'
        f'{facts["memory"]["below_unchanged_admission_threshold"]} below unchanged admission threshold;no24GB or pressure qualification. '
        f'{len(manifest["files"])} sanitized public artifacts retained at {REF}. '
        'Pre-native fixed-source/cloud-name mismatch reproduced with3 tests/2 subtest errors,then3PASS after an exact protected-read exception;private scope2PASS at exact allowlist guards. '
        'These5 external tool tests are separate from1974 source executions. Bounded independent source/native-tool/retention review0 remainingC/I;reviewerexecutionNONE;no whole-product acceptance. '
        'Ordinary native PAPER/worker invocation,current browser,owning release/restoration integration remain pending;productionprofilePROPOSED_NOT_ACTIVE. '
        'Continue authorized issuer/store/adapter fixture work and actual native composition on same task/branch;S09/S12/S13/S14/S15 IN_PROGRESS,S16 pending. '
        'Ubuntu24/26 and realcloud/dataset/forward/provider commissioningNOT_RUN;provider0,credentialsNONE,capitalNONE,runtimeLLM0,GitHubcomputeNOT_USED,mainmergeNOT_PERFORMED. '
        'All project folders/artifacts stay inside project root.\n\n')
    handoff=REPO/'coordination/CODEX/HANDOFF.md'
    handoff.write_text(note+handoff.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
    result=REPO/'status/codex/productization/S09/LOCAL_CONTROL_QUALIFICATION_41fa2fe.md'
    with result.open('x',encoding='utf-8',newline='\n') as stream:
        stream.write('# Ordinary PAPER read/control scoped qualification\n\n'+note+
            '\nActual facts: `local-control-qualified-41fa2fe-py312/disposition.json`. '
            'Byte manifest: `local-control-qualified-artifact-hashes-41fa2fe.json`. '
            'The exact tested executable is distinct from its later evidence commit.\n')
    print(json.dumps(dict(recorded=True,qualified_executable=REVISION,retained_files=len(manifest['files']),state=progress['state'])))

if __name__=='__main__':main()
