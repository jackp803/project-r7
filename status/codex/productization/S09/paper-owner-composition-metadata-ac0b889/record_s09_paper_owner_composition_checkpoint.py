"""Project one verified immutable public qualification snapshot into handoff metadata."""
from pathlib import Path
import hashlib,json,sys
BASE=Path(__file__).resolve().parent
REPO=BASE.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(REPO/'src'))
from application.datasets.catalog import read_local

REVISION='ac0b889829777db884666f82bd2d18f2c38ba4cb'
REF='status/codex/productization/S09/paper-owner-composition-qualified-ac0b889-py312'
MANIFEST='status/codex/productization/S09/paper-owner-composition-qualified-artifact-hashes-ac0b889.json'
sha=lambda raw:'sha256:'+hashlib.sha256(raw).hexdigest()

def read(name):return read_local(REPO,name,64*1024**2)
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')

def main():
    manifest_raw=read(MANIFEST);manifest=json.loads(manifest_raw)
    assert len(manifest['files'])==77
    mandatory={REF+'/disposition.json',REF+'/native-build/build-result.json'}
    assert mandatory<=manifest['files'].keys()
    snapshots={}
    for name,expected in manifest['files'].items():
        assert name.startswith(REF+'/') and '..' not in Path(name).parts
        raw=read(name);assert sha(raw)==expected;snapshots[name]=raw
    facts=json.loads(snapshots[REF+'/disposition.json'])
    build=json.loads(snapshots[REF+'/native-build/build-result.json'])
    assert facts['revision']==REVISION
    assert facts['source']==dict(passed=True,tests=2035,commands=33,phase=dict(phase_1=247,phase_2=1788))
    assert facts['source_input_files']==621 and facts['new_component_cases']==19
    assert facts['native_scoped']==dict(passed=True,scenarios=13,commands=13,wrapper_stages=4)
    assert build['identity']==facts['native_build']
    assert facts['native_owner_composition_factory']=='NOT_INVOKED' and facts['native_worker_invoked'] is False
    assert facts['ordinary_native_paper']=='NOT_RUN' and facts['production_profile']=='PROPOSED_NOT_ACTIVE'
    assert facts['provider_requests']==0 and facts['credentials']=='NONE' and facts['capital']=='NONE'
    assert facts['source_awake_request']['restored'] and facts['native_awake_request']['restored']
    path=REPO/'coordination/CODEX/PROGRESS.json';progress=json.loads(path.read_bytes())
    assert progress['state']=='IN_PROGRESS' and progress['qualified_executable_revision']==facts['accepted_prior_revision']
    assert progress['paper_owner_composition']['status']=='SOURCE_COMPONENT_PASS;EXACT_CLEAN_QUALIFICATION_PENDING'
    checkpoint=dict(status='EXACT_CLEAN_FULL_SOURCE_PASS;CURRENT_NATIVE_BUILD_EXISTING13_SCOPED_REGRESSIONS_PASS;NATIVE_FACTORY_NOT_INVOKED;NO_RELEASE_ADMISSION',
        qualified_executable_revision=REVISION,implementation_hash=facts['implementation_hash'],
        new_cases=19,affected_regression_cases=62,source_tests=2035,source_commands=33,phase_1=247,phase_2=1788,
        failures=0,errors=0,skipped=0,source_input_files=621,native_build=facts['native_build'],
        native_scoped_scenarios=13,native_scoped_commands=13,native_owner_composition_factory='NOT_INVOKED',
        native_worker_invoked=False,ordinary_native_paper='NOT_RUN',browser='NOT_RUN_FOR_THIS_CANDIDATE',
        production_profile='PROPOSED_NOT_ACTIVE',memory=facts['memory'],external_native_guard_tests=4,
        external_retention_guard_tests=0,evidence_ref=REF+'/disposition.json',manifest_ref=MANIFEST,retained_files=77,
        independent_review='BOUNDED_SOURCE_AND_TOOLING0_CRITICAL0_IMPORTANT;REVIEWER_EXECUTION_NONE;NOT_WHOLE_PRODUCT_ACCEPTANCE')
    progress['paper_owner_composition'].update(checkpoint)
    progress.update(qualified_executable_revision=REVISION,candidate_executable_revision=REVISION,
        active_step='S09/S12/S13',next_step='Continue owning fixed-check producer/current-release adapter and packaged PAPER worker integration. Production release profile remains PROPOSED_NOT_ACTIVE pending PM/E6 mapping acceptance. Complete current browser/S15 mapping and mandatory Ubuntu/S16 evidence without transferring historical or FIXTURE PASS.')
    progress['tests_executed'].append({**checkpoint,'step':'S09/S12/S13','phase':'TRUSTED_PAPER_OWNER_SOURCE_AND_CURRENT_EXISTING_NATIVE_REGRESSIONS','status':'PASS'})
    progress['evidence_refs'].append(REF+'/disposition.json')
    progress['platforms']['windows-11-x86_64'].update(native_package_status='PASS',native_first_run_status='PASS',
        native_first_run_revision=REVISION,native_first_run_scenarios=8,native_first_run_commands=9,
        native_first_run_build_hash=facts['native_build']['build_hash'],native_archive_sha256=build['archive_sha256'],
        native_full_product_acceptance='NOT_RUN',native_package_scope='CURRENT_BUILD8_FIRST_RUN3_HISTORICAL2_SOURCE_AUTH_EMPTY_READ_START_DENIAL;NEW_NATIVE_FACTORY_WORKER_BROWSER_NOT_RUN')
    assert all(progress['steps'][step]=='IN_PROGRESS' for step in ('S09','S12','S13','S14','S15'))
    assert read(MANIFEST)==manifest_raw and all(read(name)==raw for name,raw in snapshots.items())
    save(path,progress)
    note=(f'S09/S12/S13 trusted PAPER owner composition exact-clean executable {REVISION}:33 source commands/2035 execution instances PASS '
        '(phase1 247,phase2 1788),0 failures/errors/skips,621 unchanged bound inputs,all owned trees reaped. '
        '19 component cases and62 affected precommit regression cases use actual canonical services/SQLite and isolated FIXTURE mechanics. '
        'Current Windows build/existing13 native scenarios13 commands PASS across4 stages:8 first-run,3 historical publication,2 source-created synthetic auth empty inventory/start denial. '
        'New composition factory/worker are NOT invoked by those native scenarios;ordinary native PAPER/current browser NOT_RUN. '
        f'Implementation {facts["implementation_hash"]};build {facts["native_build"]["build_hash"]}. '
        f'77 sanitized fixed public artifacts at {REF};4 external current handoff/final guards are separate from2035 source executions. '
        f'Actual host memory samples{facts["memory"]["samples"]},minimum available{facts["memory"]["minimum_available_bytes"]};no24GB/pressure capacity claim. '
        'Initial16FAIL reproduced missing composition/existing-only options and actual runtime migration connection leak;additional2 parent-path subtest failures fixed before restoration/opening. '
        'Caller-thread ExitStack closes3 actual connections; API start prepares generation0 and independent owner preserves actual protection/flat closure. '
        'Source/native temporary idle-sleep requests restored;no permanent host policy change. Bounded source/tool independent review0C/I,reviewer_executionNONE;no whole-product acceptance. '
        'Production release profilePROPOSED_NOT_ACTIVE;owning producer/current adapter,packaged worker,restored reauthorization and PM/E6 mappings pending. '
        'Continue same master task/branch;S09/S12/S13/S14/S15 IN_PROGRESS,S16 pending;Ubuntu24/26/realcloud/dataset/forward/provider commissioningNOT_RUN. '
        'Provider0,credentialsNONE,capitalNONE,runtimeLLM0,GitHubcomputeNOT_USED,mainmergeNOT_PERFORMED;all project folders inside project root.\n\n')
    hand=REPO/'coordination/CODEX/HANDOFF.md';hand.write_text(note+hand.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
    result=REPO/'status/codex/productization/S09/PAPER_OWNER_COMPOSITION_QUALIFICATION_ac0b889.md'
    with result.open('x',encoding='utf-8',newline='\n') as stream:stream.write('# Trusted PAPER owner composition scoped qualification\n\n'+note.rstrip()+'\n')
    print(json.dumps(dict(recorded=True,qualified_executable=REVISION,retained_files=77,state=progress['state'])))

if __name__=='__main__':main()
