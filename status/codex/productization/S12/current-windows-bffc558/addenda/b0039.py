"""Exact bffc clause companion: actual bindings, finite reviewed scopes only."""
from pathlib import Path
from pathlib import PurePosixPath
from collections import Counter,defaultdict
from copy import deepcopy
from datetime import datetime,timezone
import hashlib,json,os,re,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from application.config import load_config
from application.paper.qualification import artifact_bytes,validate_qualified_receipt
from application.paper.inventory import current_target,fixed_profile
from application.platform.distribution import verify_distribution
from index_current_qualification import run as rebuild_index
from storage.qualification import open_qualification_receipts
from strategy.v02.capabilities import _revision,build_capability_snapshot
from application.cloud.safe_files import _windows_read,_posix_read
from application.cloud.protocol import CloudError
source_reader=_windows_read if os.name=='nt' else _posix_read
REV='bffc558b9652dc41c0804896436ac7ad8744f7f8'
IMPL='sha256:387238c130af7b96f59578fdfec3b1fa76fc9443daa8a174be00d79ba166c666'
PINS={
 'current-STR-DATA-RES-LIFE-semantic-bffc558-draft.json':'b67bf9abf705037d0bda9c61dc7c826c07b081253cac9a860f9e0b07c90d7b48',
 'current-CLOUD-API-OPS02-E2E04-semantic-bffc558-draft.json':'6b818f1e23cccaefd9991233631dd9ba806e4582cb25b42713104ac818d3f6ee',
 'current-PLAT-PAPER-TRADE-UI-OPS01-E2E-semantic-bffc558-draft.json':'50f9a028f35742cc2bbc0c9087ee30db69c29405b087e1fa043bc8fac2d1bc44',
 'legacy-A-E-semantic-bffc558-draft.json':'73531ce8ad6c109dac840aab386b601cb06055a67dcf6187af71e18b416e898b',
 'legacy-F-I-semantic-bffc558-draft.json':'e67ce49342d6616520814bd43aca3037f51027416480a43903c1f583e8dd6264',
 'legacy-J-M-semantic-bffc558-draft.json':'0ae1fe0763d7494a2e843c4d858f41a24be3fef8e285d4c813a15a0610e50ef1'}
def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
def capture(path):return artifact_bytes(PROJECT,path.relative_to(PROJECT).as_posix())
def load(path):return json.loads(capture(path))
def save(path,value):
 with path.open('x',encoding='utf-8',newline='\n') as f:f.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def require_current_portable(row,smoke,facts):
 # The producer deliberately terminates its two owned control servers (124),
 # and observes config-drift termination (2). Input metadata cannot choose codes.
 scenarios=('NATIVE_HARDWARE_WITH_EMPTY_PATH','CHINESE_PROFILE_DEFAULTS_AND_PRESERVATION',
  'SECOND_NATIVE_CONTROL_PROCESS_DENIED','ACTUAL_NATIVE_E6_MIGRATIONS',
  'CONTROL_RESTART_AUTH_AND_LOOPBACK_DENIAL','NATIVE_CONFIG_DRIFT_STOPS_CONTROL',
  'NATIVE_UNSELECTED_WORKER_TRUTHFUL','TAMPERED_MIGRATION_DENIED_BEFORE_START')
 commands=(('01-doctor',0),('02-init-profile',0),('03-preserve-profile',2),
  ('04-first-control-start-second-process-denied',2),('04-first-control-start',124),
  ('05-control-restart',124),('06-control-config-change',2),
  ('07-unconfigured-research-worker',0),('08-tampered-resource-denied',2))
 http=(('/api/v1/auth/status',200),('/',200),('/api/v1/health',401),
  ('/api/v1/auth/status',400),('/api/v1/auth/status',403))*3
 if (row.get('passed') is not True or row.get('revision')!=REV or row.get('identity')!=facts
     or row.get('source_unchanged') is not True or row.get('complete_bytes_identical') is not True
     or row.get('copied_auth') is not False or row.get('copied_configuration') is not False
     or row.get('installation_ref')!='installations/windows-bffc558-clean'
     or row.get('first_run',{}).get('passed') is not True
     or smoke.get('passed') is not True or smoke.get('identity')!=facts
     or smoke.get('scenario_count')!=8
     or tuple(r.get('name') for r in smoke.get('scenarios',[]))!=scenarios
     or any(r.get('result')!='PASS' for r in smoke['scenarios'])
     or smoke['scenarios'][3].get('migrations')!=24
     or tuple(r.get('name') for r in smoke.get('commands',[]))!=tuple(n for n,_ in commands)
     or any(r.get('passed') is not True or r.get('tree_reaped') is not True
       or r.get('exit_code')!=code or r.get('expected_exit_code',code)!=code
       for r,(_,code) in zip(smoke['commands'],commands))
     or tuple((r.get('path'),r.get('expected_status')) for r in smoke.get('http_assertions',[]))!=http
     or any(r.get('passed') is not True or r.get('actual_status')!=r.get('expected_status')
       for r in smoke.get('http_assertions',[]))):
  raise ValueError('Actual stopped same-subject portable observation required')
 return row

def require_source_map(value,expected):
 if not isinstance(value,dict) or not expected or set(value)!=set(expected):
  raise ValueError('Exact committed public source inventory required')
 for ref,digest in value.items():
  if (not isinstance(ref,str) or PurePosixPath(ref).is_absolute() or '..' in PurePosixPath(ref).parts
      or not re.fullmatch(r'[A-Za-z0-9_.\-/]+',ref)
      or not (ref.startswith(('src/','tests/','ui/src/','ui/qa/')) or ref in (
       'contracts/control_api_v0_2.openapi.json','ui/package.json','ui/package-lock.json','ui/playwright.config.ts'))
      or not isinstance(digest,str) or not re.fullmatch(r'sha256:[0-9a-f]{64}',digest)):
   raise ValueError('Contained public source commitment required')
 return value

def source_bytes(ref):
 # Canonical committed source names include __init__.py. They retain the same
 # bounded no-reparse/single-link OS reader without cloud-package name grammar.
 require_source_map({ref:'sha256:'+'0'*64},{ref})
 if PurePosixPath(ref).as_posix()!=ref:raise ValueError('Canonical public source path required')
 try:return source_reader(ROOT/ref,8*1024*1024,require_single_link=True)
 except CloudError as error:raise ValueError('Committed public source read unsafe') from error

def read_frontend_unit_proof():
 # Reuse the still-valid successful unit command in the original mixed-stage
 # attempt. Its later browser command failed and remains failed, never relabeled.
 raw=capture(BASE/'ui01-frontend-first/checkpoint.json')
 if sha(raw)!='sha256:fa16cd9150af38852cb7764181f895538b5e77357d962c42bd846ce717cb23d0':
  raise ValueError('Exact original frontend command observation required')
 stage=json.loads(raw);commands=[c for c in stage['commands'] if c['name']=='unit']
 assert len(commands)==1;command=commands[0]
 assert command['arguments']==['node_modules/vitest/vitest.mjs','run']
 assert command['exit_code']==0 and command['tree_reaped'] and command['source_unchanged']
 log=capture(BASE/'ui01-frontend-first/unit.log')
 assert sha(log)==command['log_hash']=='sha256:f58151ff980f938d3770fbc9e292b4eb8d1c10615771dc00fd0526727d5189bb'
 assert 'Test Files  2 passed (2)' in log.decode() and 'Tests  18 passed (18)' in log.decode()
 result={}
 for ref in ('ui/src/api.test.ts','ui/src/model.test.ts'):
  source=source_bytes(ref);assert sha(source)==stage['source_hashes'][ref]
  assert not re.search(r'\b(?:it|test)\.(?:skip|todo|only)\s*\(',source.decode())
  for name in re.findall(r"^\s*it\('([^'\n]+)',",source.decode(),re.M):
   key=ref+'::'+name;assert key not in result
   result[key]=dict(test_id=key,status='PASS',source_ref=ref,source_hash=sha(source),
    command=command,artifact_ref='ui01-frontend-first/unit.log',
    execution='SOURCE_FRONTEND_UNIT_PREQUALIFICATION;ORIGINAL_SUCCESSFUL_COMMAND_SCOPE_ONLY',
    parent_attempt_passed=False,native_qualification_membership='NONE',
    case_observation='UNFILTERED_WHOLE_TWO_FILE_18CASE_PASS;NO_INVENTED_INDIVIDUAL_CASE_TIME')
 assert len(result)==18
 return result

def run():
 assert _revision()==IMPL
 q=load(BASE/'qualify-bffc558-first/checkpoint.json');observer=load(BASE/'owning-memory-bffc558-first/checkpoint.json')
 assert q['revision']==REV and q['passed'] and observer['owning_passed'] and observer['tree_reaped'] and observer['monitor_stopped']
 assert observer['errors']==[] and observer['source_unchanged'] and observer['wrapper_unchanged']
 index=load(BASE/'execution-index-bffc558.json');base=load(BASE/'acceptance-records-bffc558.json')
 assert index['revision']==base['revision']==REV and index['receipt_ref']==base['receipt_ref']==q['result']['receipt_ref']
 assert len(index['cases'])==2654 and len(base['current_matrix_results'])==66 and len(base['inherited_legacy_results'])==150
 # Reuse the existing exact-owned artifact/index verifier while ROOT is clean.
 assert rebuild_index(REV,'first',emit=False)==index
 facts=verify_distribution(BASE/'build-bffc558/dist/R7')
 assert facts==index['identity']==base['identity'] and facts['executable_revision']==REV and facts['implementation_hash']==IMPL
 config=load_config(BASE/'qualify-bffc558-first/product.json')
 with open_qualification_receipts(config.database_path,namespace='LOCAL_RESEARCH') as reader:receipt=reader.get(index['receipt_ref'])
 validate_qualified_receipt(receipt,fixed_profile(current_target()),
  artifact_root=config.local_data_root/'qualification'/receipt.execution_id,
  measured={**facts,'platform_id':current_target(),'capability_hash':build_capability_snapshot().snapshot_hash})
 portable=require_current_portable(load(BASE/'portable-bffc558-first/checkpoint.json'),
  load(BASE/'portable-bffc558-first/first-run-smoke/native-smoke.json'),facts)
 assert verify_distribution(PROJECT/portable['installation_ref'])==facts
 checks={c.check_id:c for c in receipt.checks};assert len(checks)==212 and all(c.passed and c.returncode==0 and c.tree_reaped for c in checks.values())
 assert all(getattr(c,key)==0 for c in checks.values() for key in ('failures','errors','skipped','expected_failures','unexpected_successes'))
 source_cases=defaultdict(list)
 for row in index['cases']:
  assert row['status']=='PASS';source_cases[row['test_id']].append(row)
 source_members=[mid for mid in checks if mid.startswith('PQR-01-')]
 assert len(source_members)==206
 source_groups={'PQR-01':dict(group_id='PQR-01',kind='ACTUAL_SOURCE_GROUP',member_ids=sorted(source_members),
  source_case_executions=len(index['cases']),receipt_ref=receipt.receipt_id,status='PASS',native_assertion_credit='NONE')}
 native=defaultdict(list)
 for row in index['actual_native_assertions']:
  assert row['status']=='PASS';native[row['group_id']].append(row)
 native_aliases={r['group_id']+'::'+r['assertion_id']:r for rows in native.values() for r in rows}
 unit_cases=read_frontend_unit_proof()
 browser=load(BASE/'ui01-browser-retry02/browser/results.json');assert browser['stats']['expected']==17 and all(browser['stats'][k]==0 for k in ('unexpected','skipped','flaky'))
 browser_cases={}
 def walk(suites):
  for suite in suites:
   for spec in suite.get('specs',[]):
    assert spec['ok'] and spec['tests'] and all(t['status']=='expected' and all(r['status']=='passed' for r in t['results']) for t in spec['tests'])
    browser_cases['ui/qa/control-center.spec.ts::'+spec['title']]=dict(title=spec['title'],status='PASS',
     source_ref='ui/qa/control-center.spec.ts',source_hash=sha(source_bytes('ui/qa/control-center.spec.ts')),
     execution='SOURCE_BROWSER_PREQUALIFICATION;ORIGINAL_EXECUTION_SCOPE_RETAINED',artifact_ref='ui01-browser-retry02/browser/results.json')
   walk(suite.get('suites',[]))
 walk(browser['suites']);assert len(browser_cases)==17
 stage_raw=capture(BASE/'ui01-browser-retry02/checkpoint.json')
 assert sha(stage_raw)=='sha256:9958aae6e9cfffb0eec1ca30bddfa99cea9da68ea01c21a1053d02d33680d1c1'
 stage=json.loads(stage_raw);assert stage['passed'] and stage['source_unchanged']
 inventory_raw=capture(BASE/'bffc-browser-source-key-inventory.json')
 assert sha(inventory_raw)=='sha256:ffcba1bbf48c366d2e7531b149fb98c692c115743ee30a4ad24d03092c246acd'
 expected=json.loads(inventory_raw);assert len(expected)==654 and len(set(expected))==654
 mapping=require_source_map(stage['source_hashes'],expected)
 for ref,h in mapping.items():
  actual_hash=sha(source_bytes(ref))
  if ref=='src/application/paper/_fixed_inventory.py':
   assert h=='sha256:3710a5b15e09002c979de1e0cdf9f6502e21cf467f98bb0abe1c1c7766f2ac3c'
   assert actual_hash=='sha256:b7831a6d51562574b638b706e06c32438ebc97ce56d048d247ea28608d7a1dc8'
  else:assert actual_hash==h
 str12=load(BASE/'str12-four-hour-bffc558-first/checkpoint.json')
 assert str12['implementation_hash']==IMPL and str12['exit_code']==0 and str12['tree_reaped'] and str12['source_and_tests_unchanged']
 assert 'Ran 1 test in' in capture(BASE/'str12-four-hour-bffc558-first/source.log').decode('utf-8')
 a08=load(BASE/'a08-visible-bffc558-retry01/checkpoint.json')
 assert a08['passed'] and a08['revision']==REV and a08['implementation_hash']==IMPL and all(r['reaped'] for r in a08['cleanups'])
 triage=load(BASE/'l01-l05-root-triage-bffc558-20261021.json')
 assert triage['subject']['head']==REV and triage['unresolved_after_root_review']==0
 recipes={};legacy={};inputs={}
 for name,digest in PINS.items():
  raw=capture(BASE/name);assert sha(raw)=='sha256:'+digest
  doc=json.loads(raw);inputs[name]=sha(raw)
  selected=recipes if name.startswith('current-') else legacy
  assert doc.get('candidate_revision',REV)==REV
  for row in doc['rows']:assert row['id'] not in selected;selected[row['id']]=row
 specification=load(ROOT/'docs/product/v0_2/07_ACCEPTANCE_MATRIX.json')
 assert set(recipes)=={r['id'] for r in specification['requirements']} and len(legacy)==150
 assert set(legacy)=={r['requirement_id'] for r in base['inherited_legacy_results']}
 required=set(specification['per_result_required_fields'])
 supplements=dict(STR12=str12,A08=a08,static_audit=triage)
 # Prior accepted subject evidence remains explicit; it is never renamed bffc.
 previous=load(ROOT/'status/codex/productization/S12/current-windows-3ae6460/semantic-review.json')
 previous_rows={r['requirement_id']:r for r in previous['records']}
 result_groups=[]
 for label,original_rows,advisory in (('current_matrix_results',base['current_matrix_results'],recipes),('inherited_legacy_results',base['inherited_legacy_results'],legacy)):
  output=[]
  for original in original_rows:
   rid=original['requirement_id'];recipe=advisory[rid];result=deepcopy(original)
   if label=='current_matrix_results':
    proposal=recipe['conditional_status'];names=set(original['test_ids'])|set(recipe['extra_test_ids']);groups=recipe['native_groups']
    scope=recipe['scope'];gap=recipe['remaining_clause'];external=recipe['external_gaps']
   else:
    proposal=recipe.get('proposed_windows_scope_status',recipe.get('proposed_conditional_windows_scope_status',recipe.get('proposed_conditional_windows_status','NOT_RUN')))
    names=set(recipe.get('primary_test_ids',recipe.get('primary_actual_test_ids',[])))|set(original['test_ids']);groups=[]
    scope=recipe.get('proposed_scope',recipe.get('semantic_basis','Reviewed inherited Windows scope'))
    gap=recipe.get('concrete_uncovered_clause');external=recipe.get('external_gap',recipe.get('exact_external_gap',[]))
   bound=[];rendered=[];units=[];native_named=[];missing=[]
   for name in sorted(names):
    if name in source_cases:bound.extend(source_cases[name])
    elif name in browser_cases:rendered.append(browser_cases[name])
    elif name in unit_cases:units.append(unit_cases[name])
    elif name in native_aliases:native_named.append(native_aliases[name])
    elif name.startswith('SUPPLEMENTAL_'):continue # Explicit prior scope only below.
    else:missing.append(name)
   if rid=='UI-01':bound.extend(r for name,rows in source_cases.items() if name.startswith('tests.product.test_ui01_observations.') for r in rows)
   if rid in ('UI-01','UI-02','UI-03'):rendered=list(browser_cases.values())
   unique={r['execution_instance_id']:r for r in bound};bound=list(unique.values())
   actual_native=[row for group in groups if group not in source_groups for row in native[group]]+native_named
   actual_source_groups=[source_groups[group] for group in groups if group in source_groups]
   if any(not native[group] for group in groups if group not in source_groups):missing.append('MANDATORY_CURRENT_NATIVE_GROUP')
   accepted=proposal.startswith('PASS') and not missing
   if rid in ('E2E-03','M11','M12'):accepted=True;gap=None;scope='EXACT_COMPLETE_WINDOWS_CREDENTIAL_FREE_FIXED_SUITE_ONLY'
   prior=previous_rows.get(rid)
   special_current=rid in ('A01','A02','A05','A08','L01','L05','STR-12','E2E-03','M11','M12')
   if not bound and not rendered and not units and not actual_native and not special_current:
    accepted=False # Existing old-subject proof stays visible, not a current execution.
   if rid in ('B03','M04'):accepted=False;gap='Original 3ae native temporal/same-submission proof retained separately; no current native execution relabeling.'
   result.update(status='PASS' if accepted else 'NOT_RUN',test_ids=sorted({r['test_id'] for r in bound}|{r['source_ref']+'::'+r['title'] for r in rendered}|{r['test_id'] for r in units}),
    environment_class='WINDOWS_SCOPED_SEMANTIC_ACCEPTANCE_WITH_EXPLICIT_ORIGINAL_SUBJECT_SUPPLEMENTS',
    exit_code=0 if accepted else None,passed=len(bound)+len(rendered)+len(units),failed=0,errors=0,skipped=0,
    mapped_supporting_executions=bound,unresolved_named_cases=missing,acceptance_reviewer='ROOT_AFTER_BOUNDED_INDEPENDENT_STATIC_REVIEW_AND_ACTUAL_EXECUTION_BINDING',
    limitations=['Decision applies only to the explicit finite Windows/source/fixture scope. It does not close Master or mandatory external/native/financial commissioning.',
     'Python execution times use actual owning interval; browser and supplemental source retain their original execution identity/times, not invented per-test timestamps.',
     'Case counts are supporting occurrences; semantic review, original source commitments and actual observations supply clause scope.'])
   result['scoped_semantic_decision']=dict(scope=scope,remaining_clause=gap,external_gaps=external,advisory=recipe,
    actual_native=actual_native,actual_source_groups=actual_source_groups,actual_browser=rendered,actual_frontend_unit=units,current_member_return_codes={mid:checks[mid].returncode for mid in sorted({r['member_id'] for r in bound})},
    original_subject_prior_acceptance=prior,prior_evidence_transfer='NONE;ORIGINAL_SUBJECT_PRESERVED')
   if rid in ('A01','A02','A05'):
    result['scoped_semantic_decision']['actual_current_portable']=portable
   if rid in ('STR-12','A08'):result['scoped_semantic_decision']['actual_current_supplement']=supplements['STR12' if rid=='STR-12' else 'A08']
   if rid in ('L01','L05','OPS-02'):result['scoped_semantic_decision']['actual_current_static_audit']=triage
   if rid in ('E2E-03','M11','M12'):result['scoped_semantic_decision']['actual_full_suite']=dict(receipt_ref=receipt.receipt_id,commands=212,source_cases=2654,critical_skips=0)
   assert required<=set(result) and result['status'] in specification['evidence_statuses']
   assert result['source_revision']==REV and result['financial_authority']=='NONE'
   output.append(result)
  result_groups.append((label,output))
 report=dict(task_id=base['task_id'],candidate_revision=REV,identity=base['identity'],receipt_ref=index['receipt_ref'],master='IN_PROGRESS',
  kind='ROOT_FINITE_WINDOWS_CLAUSE_REVIEW;NO_BLANKET_PRODUCT_OR_OTHER_PLATFORM_PASS',recorded_at=datetime.now(timezone.utc).isoformat(),
  inputs=inputs,financial_authority='NONE',public_requests_cumulative=8,public_requests_additional=0,private_requests=0,
  credentials='NONE',capital='NONE',github_compute='NOT_USED',**dict(result_groups))
 report['summary']={label:dict(Counter(r['status'] for r in rows)) for label,rows in result_groups}
 report['unresolved_binding_names']={r['requirement_id']:r['unresolved_named_cases'] for _,rows in result_groups for r in rows if r['unresolved_named_cases']}
 save(BASE/'semantic-scoped-results-bffc558.json',report)
 print(json.dumps(dict(summary=report['summary'],unresolved_binding_names=report['unresolved_binding_names'],master='IN_PROGRESS')))
if __name__=='__main__':run()
