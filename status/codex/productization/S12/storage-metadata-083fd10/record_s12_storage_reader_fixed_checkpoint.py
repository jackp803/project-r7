"""Record scoped actual evidence without granting release or financial authority."""
from pathlib import Path
import hashlib,json,sys

BASE=Path(__file__).resolve().parent
REPO=BASE.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(REPO/'src'))
from application.datasets.catalog import read_local

REVISION='083fd10e419e3eec903c3597093ea56e465f57cd'
REF='status/codex/productization/S12/storage-qualified-083fd10-py312'
MANIFEST='status/codex/productization/S12/storage-qualified-artifact-hashes-083fd10.json'
sha=lambda raw:'sha256:'+hashlib.sha256(raw).hexdigest()
def read(name):return read_local(REPO,name,64*1024**2)
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')

def main():
    manifest=json.loads(read(MANIFEST))
    mandatory={REF+'/disposition.json',REF+'/native-build/build-result.json'}
    assert mandatory<=manifest['files'].keys(),'MISSING_MANDATORY_QUALIFICATION_ARTIFACTS'
    assert len(manifest['files'])==188 and all(name.startswith(REF+'/') for name in manifest['files'])
    snapshots={}
    for name,expected in manifest['files'].items():
        raw=read(name);assert sha(raw)==expected;snapshots[name]=raw
    facts=json.loads(snapshots[REF+'/disposition.json'])
    build=json.loads(snapshots[REF+'/native-build/build-result.json'])
    assert build['identity']==facts['native_build']
    assert facts['revision']==REVISION and facts['source']==dict(passed=True,tests=1991,commands=33,
        phase=dict(phase_1=247,phase_2=1744))
    assert facts['native_scoped']==dict(passed=True,scenarios=13,commands=13,wrapper_stages=4)
    assert facts['ordinary_native_paper']=='NOT_RUN' and facts['native_worker_invoked'] is False
    assert facts['provider_requests']==0 and facts['credentials']=='NONE' and facts['capital']=='NONE'
    progress_path=REPO/'coordination/CODEX/PROGRESS.json';progress=json.loads(progress_path.read_bytes())
    assert progress['qualified_executable_revision']==facts['accepted_prior_revision'] and progress['state']=='IN_PROGRESS'
    assert progress['qualification_receipt_storage']['status']=='SOURCE_STORAGE_COMPONENT_PASS;EXACT_CLEAN_QUALIFICATION_PENDING'
    progress.update(qualified_executable_revision=REVISION,candidate_executable_revision=REVISION,active_step='S09/S12/S13',
        next_step='Continue bounded owning fixed-check producer/current-release adapter with isolated fixtures and actual native PAPER owner composition/probes. '
        'Production release profile remains PROPOSED_NOT_ACTIVE pending PM/E6 acceptance. Full master/S15/S16 and mandatory Ubuntu evidence remain open.')
    checkpoint=dict(status='EXACT_CLEAN_SOURCE_PASS;SCOPED_NATIVE_BUILD_AND_EXISTING_REGRESSION_PASS;NO_RECEIPT_PRODUCER_OR_RELEASE_ADMISSION',
        qualified_executable_revision=REVISION,implementation_hash=facts['implementation_hash'],
        source_tests=1991,source_commands=33,phase_1=247,phase_2=1744,failures=0,errors=0,skipped=0,
        native_build=facts['native_build'],native_scoped_scenarios=13,native_scoped_commands=13,
        native_paper_inventory_and_start_denial_scenarios=2,native_auth_origin='NEW_SOURCE_CREATED_SYNTHETIC_FIXTURE;NOT_NATIVE_CLI_ENROLLMENT',
        ordinary_native_paper='NOT_RUN',native_worker_invoked=False,browser='NOT_RUN_FOR_THIS_CANDIDATE',
        production_qualification_profile='PROPOSED_NOT_ACTIVE',memory=facts['memory'],
        external_native_final_guard_regressions=3,external_retention_scope_regressions=2,external_awake_guard_regressions=4,preserved_failed_attempt=facts['preserved_failed_attempt'],preserved_memory_pressure_attempt=facts['preserved_memory_pressure_attempt'],external_memory_recovery_cases=2,external_native_reader_subject_guards=3,preserved_native_reader_attempt=facts['preserved_native_reader_attempt'],owning_producer='NOT_IMPLEMENTED',source_input_files=614,
        evidence_ref=REF+'/disposition.json',manifest_ref=MANIFEST,retained_files=len(manifest['files']),
        independent_review='BOUNDED_SOURCE_AND_EXTERNAL_TOOLING;0_CRITICAL_0_IMPORTANT;REVIEWER_EXECUTION_NONE;NO_WHOLE_PRODUCT_REVIEW')
    progress['qualification_receipt_storage'].update(checkpoint)
    progress['tests_executed'].append({**checkpoint,'step':'S12/S09/S13',
        'phase':'EXACT_CLEAN_INTERNAL_SOFTWARE_RECEIPT_STORAGE_AND_EXISTING_SCOPED_NATIVE_REGRESSION','status':'PASS',
        'qualification_scope_status':checkpoint['status']})
    progress['evidence_refs'].append(REF+'/disposition.json')
    progress['platforms']['windows-11-x86_64'].update(native_package_status='PASS',native_first_run_status='PASS',
        native_first_run_revision=REVISION,native_first_run_scenarios=8,native_first_run_commands=9,
        native_first_run_build_hash=facts['native_build']['build_hash'],native_full_product_acceptance='NOT_RUN',
        native_package_scope='SCOPED_BUILD_8_FIRST_RUN_3_HISTORICAL_PUBLICATION_2_AUTHENTICATED_PAPER_READ_START_DENIAL;WORKER_NOT_INVOKED;BROWSER_NOT_RUN',
        native_archive_sha256=build['archive_sha256'])
    assert all(progress['steps'][step]=='IN_PROGRESS' for step in ('S09','S12','S13','S14','S15'))
    save(progress_path,progress)
    note=(f'S12 internal software qualification receipt storage increment qualified at exact-clean executable {REVISION}: '
        '33 source commands/1991 execution instances PASS (phase1 247,phase2 1744),0 failures/errors/skips,614 bound source inputs unchanged,all owned trees reaped. '
        'Windows native build,8 first-run,3 historical-publication and2 authenticated empty inventory/start-denial scenarios PASS;13 native commands across4 wrapper stages. '
        'Fresh local auth is a source-created synthetic fixture;no native CLI enrollment or existing user auth access. '
        'Reader control teardown uses owned kernel termination;no managed-stop claim. '
        f'Build {facts["native_build"]["build_hash"]}; implementation {facts["implementation_hash"]}. '
        f'{facts["memory"]["samples"]} actual host memory samples,min{facts["memory"]["minimum_available_bytes"]} available bytes,'
        f'{facts["memory"]["below_unchanged_admission_threshold"]} below unchanged admission threshold;no24GB or pressure qualification. '
        f'{len(manifest["files"])} sanitized public artifacts retained at {REF}. '
        'Final native proof gap reproduced with3 failing guard tests,then3PASS after final input/revision/package identity revalidation;private scope2PASS at exact allowlist guards. '
        'These12 external guard tests are separate from1991 source executions; preserved prior32-command/1946-execution attempt has1sleep-related error and receives no qualification credit. A second33-command/1991-execution attempt had2actual memory-pressure errors; its same2cases later passed separately, with no full qualification credit and no admission threshold change. The first native wrapper completed3stages then its historical41fa reader rejected the083 subject beforecreating a fixture; no native qualification credit. A3-case subject boundary regression reproduced1failure then3PASS after full revision/package/output binding repair, followed by a fresh complete4-stage native run. Scoped idle-sleep requests were restored after source/native execution; no persistent power policy change or manual sleep prevention. Bounded independent source/native-tool/retention review0 remainingC/I;reviewerexecutionNONE;no whole-product acceptance. '
        'Ordinary native PAPER/worker invocation,current browser,owning release/restoration integration remain pending;productionprofilePROPOSED_NOT_ACTIVE. '
        'Continue authorized issuer/store/adapter fixture work and actual native composition on same task/branch;S09/S12/S13/S14/S15 IN_PROGRESS,S16 pending. '
        'Ubuntu24/26 and realcloud/dataset/forward/provider commissioningNOT_RUN;provider0,credentialsNONE,capitalNONE,runtimeLLM0,GitHubcomputeNOT_USED,mainmergeNOT_PERFORMED. '
        'All project folders/artifacts stay inside project root.\n\n')
    handoff=REPO/'coordination/CODEX/HANDOFF.md'
    handoff.write_text(note+handoff.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
    result=REPO/'status/codex/productization/S12/STORAGE_QUALIFICATION_083fd10.md'
    with result.open('x',encoding='utf-8',newline='\n') as stream:
        stream.write('# Internal software qualification receipt storage scoped qualification\n\n'+note+
            '\nActual facts: `storage-qualified-083fd10-py312/disposition.json`. '
            'Byte manifest: `storage-qualified-artifact-hashes-083fd10.json`. '
            'The exact tested executable is distinct from its later evidence commit.\n')
    print(json.dumps(dict(recorded=True,qualified_executable=REVISION,retained_files=len(manifest['files']),state=progress['state'])))

if __name__=='__main__':main()
