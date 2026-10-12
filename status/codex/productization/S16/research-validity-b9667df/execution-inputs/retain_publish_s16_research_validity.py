"""Publish bounded source expiry evidence; current native credit stays separate."""
import json,os,re
from pathlib import Path
from s09_normal_fixture_source_qualify import BASE,REPO,inputs
from s09_owner_worker_native_regression import PROJECT,OwnedProof,sha,capture_qualification,stamp
from s09_local_paper_control_native_regression import read_input
from application.qualification import revision_fact,FOCUSED,discover_suites,parse_result
from dataclasses import asdict

REV='b9667dffc6de71b3dc03e2be0f170ab39830d489';NATIVE='13d7375d6297c8df94124e95856821df6dee7f09'
S16=REPO/'status/codex/productization/S16';DEST=S16/'research-validity-b9667df'
MANIFEST=S16/'research-validity-artifact-hashes-b9667df.json'
revision_fact(REPO,REV,True)
q,context,qhash=capture_qualification(BASE/'r7-productization-S09-normal-fixture-qualified-b9667df',REV)
assert q['tests_run']==2115 and len(q['commands'])==33 and len(inputs())==638
assert all(r['passed'] and r['returncode']==0 and r['tree_reaped'] and
           r['source_after']==dict(revision=REV,worktree='CLEAN') and
           all(r[k]==0 for k in ('failures','errors','skipped','expected_failures','unexpected_successes'))
           for r in q['commands'])
assert sum(r['tests_run'] for r in q['commands'])==q['tests_run']
assert context['inputs_unchanged'] and context['awake_request']['restored'] and context['source_input_hashes']==inputs()
captures={};targets={};runs={}
def capture(path,target=None):
    raw=read_input(path,8*1024**2)
    if path in captures:assert captures[path]==raw
    captures[path]=raw
    if target is not None:
        assert target not in targets;targets[target]=(path,raw)
    return raw
for path,digest in qhash.items():assert sha(capture(path))==digest
policy=dict(suites=['all'],include_focused=True,require_clean=True,timeout_seconds=900,expected_revision=REV)
assert context['configuration']==policy
assert context['config_hash']==sha(json.dumps(policy,sort_keys=True,separators=(',',':')).encode())
assert sha(capture(BASE/'s09_normal_fixture_source_qualify.py'))==context['launcher_sha256']
assert sha(capture(BASE/'local_windows_qualification_awake.py'))==context['awake_helper_sha256_before']==context['awake_helper_sha256_after']
inventory=discover_suites(REPO)
assert q['inventory']==[dict(suite=s.name,files=len(s.test_files)) for s in inventory]
ordered=[('phase_1',s,p) for s,p in FOCUSED]+[('phase_2',s.name,'test_*.py') for s in inventory]
assert [(r['phase'],r['suite'],r['pattern']) for r in q['commands']]==ordered
full_folder=BASE/'r7-productization-S09-normal-fixture-qualified-b9667df'
capture(full_folder/'hardware-observations.json')
for index,row in enumerate(q['commands'],1):
    assert row['log']==f"{index:03d}-{row['phase']}-{row['suite'].replace('/','-')}.log"
    log=capture(full_folder/row['log'])
    assert sha(log)=='sha256:'+row['log_sha256']
    parsed=parse_result(log.decode('utf-8'),returncode=row['returncode'])
    assert all(row[k]==v for k,v in asdict(parsed).items()) and row['tests_passed']==parsed.tests_passed
source_manifest_path=REPO/'status/codex/productization/S15/source-artifact-hashes-b9667df.json'
source_manifest=json.loads(capture(source_manifest_path))
assert source_manifest['executable_revision']==REV and source_manifest['qualification_passed'] is True
source_rows={r['path']:r for r in source_manifest['artifacts']}
assert len(source_rows)==len(source_manifest['artifacts'])
expected_public=set()
source_destination=REPO/'status/codex/productization/S15/source-b9667df'
for name in ['qualification.json','qualification-context.json','hardware-observations.json']+[r['log'] for r in q['commands']]:
    raw=captures[full_folder/name];normalized=raw.replace(b'\r\n',b'\n')
    path=source_destination/name;relative=path.relative_to(REPO).as_posix();expected_public.add(relative)
    row=source_rows[relative]
    assert capture(path)==normalized and row['sha256']==sha(normalized) and row['bytes']==len(normalized)
    assert row['original_sha256']==sha(raw)
    if raw!=normalized:
        raw_path=source_destination/(name+'.raw');raw_relative=raw_path.relative_to(REPO).as_posix();expected_public.add(raw_relative)
        assert row['raw_subject_path']==raw_relative and capture(raw_path)==raw
        assert source_rows[raw_relative]['sha256']==sha(raw) and source_rows[raw_relative]['bytes']==len(raw)
assert set(source_rows)==expected_public
for label,counts in [('RED',(6,5,0)),('GREEN',(6,0,0)),('AFFECTED',(67,3,7)),('RED_BOUND',(7,6,0)),('GREEN_BOUND',(7,0,0))]:
    folder=BASE/('S16-validity-research-'+label)
    result=json.loads(capture(folder/'result.json',Path(label)/'result.json'))
    assert (result['tests'],result['failures'],result['errors'])==counts and result['skipped']==0
    assert result['tree_reaped'] and result['awake_request']['restored'] and result['inputs_unchanged']
    log_raw=capture(folder/'tests.log',Path(label)/'tests.log')
    assert sha(log_raw)==result['log_sha256']
    log_text=log_raw.decode('utf-8')
    summaries=re.findall(r'^Ran (\d+) tests? in [0-9.]+s$',log_text,re.MULTILINE)
    assert summaries==[str(counts[0])]
    outcome=re.search(r'\n(OK|FAILED)(?: \(([^\r\n]+)\))?\s*$',log_text)
    assert outcome is not None
    observed={}
    if outcome[2]:
        for item in outcome[2].split(', '):
            key,value=item.split('=');assert key not in observed;observed[key]=int(value)
    assert set(observed).issubset({'failures','errors','skipped'})
    assert (observed.get('failures',0),observed.get('errors',0),observed.get('skipped',0))==(*counts[1:],0)
    assert outcome[1]==('FAILED' if counts[1] or counts[2] else 'OK')
    assert result['exit_code']==(1 if counts[1] or counts[2] else 0) and result['label']==label
    expected_modules=['tests.application.test_submission_validity_research']
    if label=='AFFECTED':
        expected_modules+=['tests.application.test_submission_validity_intake','tests.product.test_research_queue',
            'tests.application.test_fixture_recipe_flow','tests.application.test_normal_fixture_paper',
            'tests.application.test_normal_fixture_worker','tests.application.test_native_research_worker',
            'tests.application.test_research_setup_flow']
    assert result['modules']==expected_modules
    executed=re.findall(r'^(test\S+) \((tests\.[A-Za-z0-9_.]+)\) \.\.\. ',log_text,re.MULTILINE)
    assert len(executed)==counts[0] and len(set(executed))==counts[0]
    assert {identity.rsplit('.',2)[0] for _,identity in executed}==set(expected_modules)
    helper=BASE/('run_s16_validity_research.py' if label in ('RED','GREEN') else 'run_s16_validity_research_v2.py')
    assert sha(capture(helper))==result['helper_sha256']
    runs[label]=result
assert runs['GREEN_BOUND']['source_input_hashes']==context['source_input_hashes']
test='tests/application/test_submission_validity_research.py'
assert runs['RED_BOUND']['source_input_hashes'][test]==runs['GREEN_BOUND']['source_input_hashes'][test]
for name in ['run_s16_validity_research.py','run_s16_validity_research_v2.py','s09_normal_fixture_source_qualify.py','local_windows_qualification_awake.py',Path(__file__).name]:
    capture(BASE/name,Path('execution-inputs')/name)
snapshots=BASE/'S16-validity-research-source-snapshots'
subjects=json.loads(capture(snapshots/'subjects.json',Path('source-snapshots')/'subjects.json'))
for row in subjects:
    name=Path(row['path']).name
    assert sha(capture(snapshots/name,Path('source-snapshots')/name))=='sha256:'+row['repaired_sha256']
    assert context['source_input_hashes'][row['path']]=='sha256:'+row['repaired_sha256']
review=json.loads(capture(BASE/'S16-validity-research-review.json',Path('execution-inputs')/'review.json'))
assert review['critical']==review['important']==0 and review['reviewer_execution']=='NONE'
assert review['source_revision']==REV and review['base_revision']=='8b4995c143ff7480e4f7ed6ace4155b4e9573dfa'
reviewed=['src/application/local_owners.py','src/application/research/selection.py','src/application/research/queue.py',test]
assert set(review['subject_hashes'])==set(reviewed)
assert all(review['subject_hashes'][name]==context['source_input_hashes'][name] for name in reviewed)
published_files={}
def guard():
    assert inputs()==context['source_input_hashes']
    for path,raw in captures.items():assert read_input(path,8*1024**2)==raw
    for path,raw in published_files.items():assert read_input(path,8*1024**2)==raw
guard()
assert not os.path.lexists(DEST) and not os.path.lexists(MANIFEST);DEST.mkdir(parents=True)
rows=[]
for target,(path,raw) in targets.items():
    text=raw.decode('utf-8')
    for actual,label in [(REPO,'<SOURCE_ROOT>'),(PROJECT,'<PROJECT_ROOT>')]:
        for value in [str(actual),str(actual).replace('\\','/'),json.dumps(str(actual),ensure_ascii=False)[1:-1],json.dumps(str(actual),ensure_ascii=True)[1:-1]]:text=text.replace(value,label)
    published=text.replace('\r\n','\n').encode();destination=DEST/target;destination.parent.mkdir(parents=True,exist_ok=True)
    with OwnedProof(destination) as owner:owner.stream.write(published);owner.stream.flush();owner.require_owned()
    assert read_input(destination,8*1024**2)==published
    published_files[destination]=published
    rows.append(dict(path=destination.relative_to(REPO).as_posix(),sha256=sha(published),original_sha256=sha(raw),bytes=len(published)))
guard()
report=dict(executable_revision=REV,state='IN_PROGRESS',scope='BOUNDED_REQUEST_EXPIRY_SOURCE_REMEDIATION;NO_NATIVE_OR_WHOLE_STR09_STR10_MASTER_ACCEPTANCE',
 canonical_red=dict(tests=7,failures=6,errors=0),canonical_green=dict(tests=7,failures=0,errors=0),
 earlier_six_case_observations='DIAGNOSTIC_ONLY;NEW_UNTRACKED_TEST_HASH_NOT_CAPTURED;NO_BYTE_CLOSURE_CREDIT',
 dirty_affected=dict(tests=67,failures=3,errors=7,reason='EXISTING_EXACT_REVISION_GATES_REFUSE_DIRTY_SOURCE;NO_THRESHOLD_RELAXED'),
 full_source=dict(revision=REV,commands=33,tests=q['tests_run'],phase_1=sum(r['tests_run'] for r in q['commands'] if r['phase']=='phase_1'),
 phase_2=sum(r['tests_run'] for r in q['commands'] if r['phase']=='phase_2'),failures=0,errors=0,skipped=0,input_files=638,implementation_hash=context['implementation_hash'],
 report_ref='status/codex/productization/S15/source-b9667df/qualification.json',manifest_ref='status/codex/productization/S15/source-artifact-hashes-b9667df.json'),
 behavior='SEALED_ENVELOPE_CURRENT_AT_RESOLUTION_EACH_STAGE_AND_COMPLETION;EXPIRED_APP_JOB;IMMUTABLE_EVIDENCE_AND_E6_LIFECYCLE_PRESERVED',
 existing_management='PACKAGE_AND_MANIFEST_HISTORY_READERS_UNCHANGED;NO_NEW_PAPER_MANAGEMENT_VALIDITY_GATE',review=review,
 native_revision=NATIVE,native_current_candidate='NOT_RUN',native_history='EXACT13D_NORMAL3_AND_SEPARATE_NEGATIVE_INTAKE5_PASS;NO_TRANSFER',
 ubuntu24='NOT_RUN',ubuntu26='NOT_RUN',ordinary_paper='NOT_RUN',production_profile='PROPOSED_NOT_ACTIVE',real_cloud='NOT_RUN',real_forward='NOT_RUN',
 provider_requests=0,credentials='NONE',capital='NONE',runtime_llm_calls=0,github_compute='NOT_USED',main_merge='NOT_PERFORMED',created_at_utc=stamp())
with OwnedProof(DEST/'disposition.json') as owner:owner.persist(report)
raw=read_input(DEST/'disposition.json',8*1024**2)
assert raw==(json.dumps(report,indent=2)+'\n').encode('utf-8')
published_files[DEST/'disposition.json']=raw
rows.append(dict(path=(DEST/'disposition.json').relative_to(REPO).as_posix(),sha256=sha(raw),original_sha256=sha(raw),bytes=len(raw)))
manifest_value=dict(executable_revision=REV,artifacts=rows,scope=report['scope'],private_profiles_databases_datasets='EXCLUDED')
with OwnedProof(MANIFEST) as owner:owner.persist(manifest_value)
manifest_raw=read_input(MANIFEST,8*1024**2)
assert manifest_raw==(json.dumps(manifest_value,indent=2)+'\n').encode('utf-8')
published_files[MANIFEST]=manifest_raw
text='''# Research request validity checkpoint

Same Master task/branch;IN_PROGRESS. Source candidate `{rev}` fixes accepted finite submission expiry in normal selected research:resolution,each actual owner checkpoint and final job completion recheck the sealed envelope and frozen selection. Expired requests leave EXPIRED application disposition;canonical E6 vocabulary and completed evidence stay intact. Historical author context and existing Paper package/management readers are unchanged.

Seven actual selected-owner regressions:expired enqueue denial;expiry after enqueue;first-stage expiry;expiry before robustness;expiry before candidate assessment with sealed OOS retained;exclusive upper boundary;reaped parent preserving EXPIRED. Bound RED7/6 failures/0 errors -> GREEN7/0 failures/errors. Earlier6-case observations did not capture the untracked new-test hash and remain diagnostic. The DIRTY affected attempt had67 tests/3 failures/7 errors at exact-revision gates;those guards stayed unchanged. The full exact-clean candidate qualification subsequently executed33 commands/{tests} instances (phase1 {p1},phase2 {p2}),0 failures/errors/skips,638 unchanged inputs,all owned trees reaped and awake restored.

Bounded read-only review found0 Critical/Important in the3 source files/initial6 tests;the additional owned-parent test was separately checked. Reviewer executionNONE;no native,whole-branch or whole-STR-09/10 acceptance.

The available Windows package remains13d7375:normal public3-outcome Paper flow PASS and separate5 negative-intake cases PASS on that exact package. See [package/start steps/workflow/platforms/PM decisions](../S09/PRODUCT_USABILITY_CHECKPOINT_13d7375.md). This source repair is not in that package;new native build/workflow qualification remains NOT_RUN. Ubuntu24/26,real cloud/data,ordinary qualified Paper and real-forward commissioning remain NOT_RUN;four ordinary release PM/E6 mappings remain PROPOSED_NOT_ACTIVE. Full M1-M11 and requirement acceptance stay incomplete.

Evidence:[source](../S15/source-artifact-hashes-b9667df.json),[focused subjects](research-validity-artifact-hashes-b9667df.json),[disposition](research-validity-b9667df/disposition.json). Private profiles/auth/config/DB/datasets/backups excluded. Provider0;credentialsNONE;capitalNONE;runtimeLLM0;GitHub computeNOT_USED;main mergeNOT_PERFORMED. Continue the same Master with current-native qualification and remaining recovery/capacity/temporal/platform acceptance.
'''.format(rev=REV,tests=q['tests_run'],p1=report['full_source']['phase_1'],p2=report['full_source']['phase_2'])
target=S16/'RESEARCH_REQUEST_VALIDITY_CHECKPOINT_b9667df.md'
with OwnedProof(target) as owner:owner.stream.write(text.encode());owner.stream.flush();owner.require_owned()
published_files[target]=text.encode()
guard()
p_path=REPO/'coordination/CODEX/PROGRESS.json';p=json.loads(read_input(p_path,8*1024**2))
assert p['state']=='IN_PROGRESS' and p['executable_revision']==NATIVE
p['executable_revision']=p['qualified_executable_revision']=p['candidate_executable_revision']=REV
p['research_request_validity_checkpoint']=dict(report,evidence_ref=(DEST/'disposition.json').relative_to(REPO).as_posix(),report_ref=target.relative_to(REPO).as_posix(),manifest_ref=MANIFEST.relative_to(REPO).as_posix())
p['active_step']='S16_RESEARCH_REQUEST_EXPIRY_SOURCE_PASS;CURRENT_NATIVE_AND_REMAINING_MASTER_PENDING'
p['next_step']='Current b966 source33/2115 PASS. Build/qualify the changed native subject without transferring13d normal3/intake5 credit;continue remaining expiry/authority/recovery/capacity/66-requirement audit. Four PM/E6 mappings and approved Ubuntu24/26 plus real commissioning remain separate.'
p['normal_fixture_product_checkpoint']['currentness']='HISTORICAL_NATIVE13D_PACKAGE;AVAILABLE_USER_WORKFLOW;NO_TRANSFER_TO_B966_SOURCE'
p['negative_intake_checkpoint']['currentness']='HISTORICAL_NATIVE13D_PACKAGE;NO_TRANSFER_TO_B966_SOURCE'
p['status_semantics']['correction']='Current exact source b96633/2115 PASS;normal3/intake5 native scopes remain exact13d history. All M1-M11 IN_PROGRESS;full requirement PASS0.'
w=p['platforms']['windows-11-x86_64']
w.update(native_package_status='HISTORICAL13D_NORMAL3_AND_INTAKE5_PASS;CURRENT_B966_NOT_RUN',
 native_ui_current_status='CURRENT_B966_NOT_RUN;EXACT13D_NORMAL11_AND_INTAKE3_STAGES_HISTORICAL',
 native_normal_fixture_status='EXACT13D_NORMAL3_PASS;CURRENT_B966_NOT_RUN',candidate_native_ui_status='CURRENT_B966_NOT_RUN',
 current_source_regression=dict(revision=REV,commands=33,execution_instances=q['tests_run'],phase_1=report['full_source']['phase_1'],phase_2=report['full_source']['phase_2'],failures=0,errors=0,skipped=0,input_files=638))
for ref in [target.relative_to(REPO).as_posix(),MANIFEST.relative_to(REPO).as_posix(),(DEST/'disposition.json').relative_to(REPO).as_posix(),report['full_source']['manifest_ref']]:
    if ref not in p['evidence_refs']:p['evidence_refs'].append(ref)
assert all(v=='IN_PROGRESS' for v in p['milestones'].values())
p_path.write_text(json.dumps(p,indent=2)+'\n',encoding='utf-8')
handoff=REPO/'coordination/CODEX/HANDOFF.md';prior=handoff.read_text(encoding='utf-8')
handoff.write_text(('Current source checkpoint:b9667dffc6de71b3dc03e2be0f170ab39830d489,same Master/branch IN_PROGRESS. Tactical validity is now rechecked at selected research resolution,every owner checkpoint and completion;EXPIRED application jobs retain canonical E6/evidence history. Bound7-test RED6F/0E ->GREEN7/0F/E;real reaped parent preserves EXPIRED. Exact-clean full source33/2115/638inputs/0F/E/skips PASS,allownedreaped/awake restored. DIRTY affected67/3F/7E and earlier6 untracked-test-hash observations remain diagnostic,no guard relaxed. Bounded source/test review0C/I;reviewer_executionNONE,no whole-Master approval.\n\n'
 'Available native package remains exact13d7375 normal3/intake5 PASS,now historical versus changed b966 source;no native credit transfer. New native candidate build/qualification pending. Source/focused report:status/codex/productization/S16/RESEARCH_REQUEST_VALIDITY_CHECKPOINT_b9667df.md. Available user startup/workflow/PM bundle:status/codex/productization/S09/PRODUCT_USABILITY_CHECKPOINT_13d7375.md. Full M1-M11/requirementPASS0;four PM/E6 release mappings PROPOSED_NOT_ACTIVE;Ubuntu24/26 and realcloud/data/forward NOT_RUN. Provider0/credentialsNONE/capitalNONE/runtimeLLM0/GitHubcomputeNOT_USED/no mainmerge;all files inside project. Continue current-native and remaining temporal/recovery/capacity/Master acceptance.\n\n'
 'Historical checkpoint records follow;their currentness is local to their recorded exact subjects.\n\n')+prior,encoding='utf-8')
guard()
print(json.dumps(dict(retained=len(rows),full_source=q['tests_run'],phase1=report['full_source']['phase_1'],phase2=report['full_source']['phase_2'],master='IN_PROGRESS',native_current='NOT_RUN')))
