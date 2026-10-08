"""Record observed scoped evidence from one verified immutable public snapshot."""
from pathlib import Path
import hashlib,json,sys
BASE=Path(__file__).resolve().parent
REPO=BASE.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(REPO/'src'))
from application.datasets.catalog import read_local
REVISION='a21f2647af65fa6766603f8ad48df93a3e2502e5'
REF='status/codex/productization/S12/runtime-identity-sharing-fixed-qualified-a21f264-py312'
MANIFEST='status/codex/productization/S12/runtime-identity-sharing-fixed-qualified-artifact-hashes-a21f264.json'
sha=lambda raw:'sha256:'+hashlib.sha256(raw).hexdigest()
def read(name):return read_local(REPO,name,64*1024**2)
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def main():
 manifest=json.loads(read(MANIFEST))
 mandatory={REF+'/disposition.json',REF+'/native-build/build-result.json'}
 assert mandatory<=manifest['files'].keys(),'MISSING_MANDATORY_QUALIFICATION_ARTIFACTS'
 assert len(manifest['files'])==81 and all(name.startswith(REF+'/') for name in manifest['files'])
 snapshots={}
 for name,expected in manifest['files'].items():
  raw=read(name);assert sha(raw)==expected;snapshots[name]=raw
 facts=json.loads(snapshots[REF+'/disposition.json']);build=json.loads(snapshots[REF+'/native-build/build-result.json'])
 assert build['identity']==facts['native_build']
 assert facts['revision']==REVISION and facts['source']==dict(passed=True,tests=2016,commands=33,phase=dict(phase_1=247,phase_2=1769))
 assert facts['source_input_files']==618 and facts['native_scoped']==dict(passed=True,scenarios=13,commands=13,wrapper_stages=4)
 assert facts['native_runtime_identity_accessor']=='NOT_INVOKED' and facts['ordinary_native_paper']=='NOT_RUN' and facts['native_worker_invoked'] is False
 assert facts['provider_requests']==0 and facts['credentials']=='NONE' and facts['capital']=='NONE'
 path=REPO/'coordination/CODEX/PROGRESS.json';progress=json.loads(path.read_bytes())
 assert progress['qualified_executable_revision']==facts['accepted_prior_revision'] and progress['state']=='IN_PROGRESS'
 assert progress['runtime_identity_read']['status']=='SOURCE_COMPONENT22_PASS;3C7_FULL_SOURCE_FAILED;SHARING_FIX_NEW_EXACT_CLEAN_CANDIDATE_PENDING'
 checkpoint=dict(status='EXACT_CLEAN_FULL_SOURCE_PASS;CURRENT_NATIVE_BUILD_EXISTING13_SCOPED_REGRESSIONS_PASS;NATIVE_ACCESSOR_NOT_INVOKED;NO_RELEASE_ADMISSION',
  qualified_executable_revision=REVISION,implementation_hash=facts['implementation_hash'],source_tests=2016,source_commands=33,phase_1=247,phase_2=1769,
  failures=0,errors=0,skipped=0,source_input_files=618,new_cases=22,native_build=facts['native_build'],native_scoped_scenarios=13,native_scoped_commands=13,
  native_runtime_identity_accessor='NOT_INVOKED',native_worker_invoked=False,ordinary_native_paper='NOT_RUN',browser='NOT_RUN_FOR_THIS_CANDIDATE',
  production_profile='PROPOSED_NOT_ACTIVE',owning_producer='NOT_IMPLEMENTED',memory=facts['memory'],
  external_native_guard_tests=4,external_retention_guard_tests=2,evidence_ref=REF+'/disposition.json',manifest_ref=MANIFEST,retained_files=81,
  independent_review='BOUNDED_SOURCE_AND_TOOLING0_CRITICAL0_IMPORTANT;REVIEWER_EXECUTION_NONE;NOT_WHOLE_PRODUCT_ACCEPTANCE')
 progress['runtime_identity_read'].update(checkpoint)
 assert facts['fixture_sharing_cases']==3
 progress['runtime_identity_read']['fixture_sharing_fix'].update(status='EXACT_CLEAN_FULL_SOURCE_PASS;FIXTURE_ONLY',qualified_executable_revision=REVISION)
 progress.update(qualified_executable_revision=REVISION,candidate_executable_revision=REVISION,active_step='S09/S12/S13',
  next_step='Continue owning fixed-check producer/current-release adapter and isolated native PAPER owner composition. Production release profile remains PROPOSED_NOT_ACTIVE pending PM/E6 mapping acceptance. Complete current browser/S15 mapping and mandatory Ubuntu/S16 evidence without transferring historical or fixture PASS.')
 progress['tests_executed'].append({**checkpoint,'step':'S09/S12/S13','phase':'READ_ONLY_RUNTIME_IDENTITY_SOURCE_AND_CURRENT_EXISTING_NATIVE_REGRESSIONS','status':'PASS'})
 progress['evidence_refs'].append(REF+'/disposition.json')
 progress['platforms']['windows-11-x86_64'].update(native_package_status='PASS',native_first_run_status='PASS',native_first_run_revision=REVISION,
  native_first_run_scenarios=8,native_first_run_commands=9,native_first_run_build_hash=facts['native_build']['build_hash'],native_archive_sha256=build['archive_sha256'],
  native_full_product_acceptance='NOT_RUN',native_package_scope='CURRENT_BUILD8_FIRST_RUN3_HISTORICAL2_SOURCE_AUTH_EMPTY_READ_START_DENIAL;NEW_NATIVE_ACCESSOR_WORKER_BROWSER_NOT_RUN')
 assert all(progress['steps'][step]=='IN_PROGRESS' for step in ('S09','S12','S13','S14','S15'))
 save(path,progress)
 note=(f'S09/S12/S13 read-only runtime identity increment exact-clean executable {REVISION}:33 source commands/2016 execution instances PASS '
  '(phase1 247,phase2 1769),0 failures/errors/skips,618 unchanged bound inputs,all owned trees reaped. '
  'Current Windows build/existing13 native scenarios13 commands PASS across4 wrapper stages;8 first-run,3 historical publication,2 source-created synthetic auth empty inventory/start denial. '
  'New runtime identity accessor is NOT invoked by those native scenarios;bundled worker/ordinary native PAPER/current browser NOT_RUN. '
  f'Implementation {facts["implementation_hash"]}; build {facts["native_build"]["build_hash"]}. '
  f'Actual host memory samples{facts["memory"]["samples"]},minimum available{facts["memory"]["minimum_available_bytes"]} bytes;no24GB/pressure capacity claim. '
  f'81 sanitized public artifacts at {REF};4 native handoff/final guards and2 private-scope guards are separate from2016 source executions. '
  'Source22 focused cases include reproduced/fixed per-field type and actual Windows PID ABI faults;3 fixture sharing regressions cover actual transient/permanent Windows locks and unrelated errors. Prior3c7 source1failure remains unqualified, exact original child cause unproven;compatible deterministic Windows race fixed with no observation/process threshold weakening. Source/native temporary idle-sleep requests restored;no persistent policy change. '
  'Independent bounded source/tool review0C/I remaining,reviewer_executionNONE;no whole-product acceptance. '
  'Immutable observed snapshot is not proof of honest DB provenance,PID non-reuse,current native files or continuing financial authority. '
  'Production release profilePROPOSED_NOT_ACTIVE;owning issuer/current adapter/native PAPER and restored reauthorization integration pending. '
  'Continue same task/branch;S09/S12/S13/S14/S15 IN_PROGRESS,S16 pending. Ubuntu24/26/realcloud/dataset/forward/provider commissioningNOT_RUN. '
  'Provider0,credentialsNONE,capitalNONE,runtimeLLM0,GitHubcomputeNOT_USED,mainmergeNOT_PERFORMED;all folders inside project root.\n\n')
 hand=REPO/'coordination/CODEX/HANDOFF.md';hand.write_text(note+hand.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
 result=REPO/'status/codex/productization/S12/RUNTIME_IDENTITY_QUALIFICATION_a21f264.md'
 with result.open('x',encoding='utf-8',newline='\n') as stream:stream.write('# Read-only runtime identity scoped qualification\n\n'+note)
 print(json.dumps(dict(recorded=True,qualified_executable=REVISION,retained_files=81,state=progress['state'])))
if __name__=='__main__':main()
