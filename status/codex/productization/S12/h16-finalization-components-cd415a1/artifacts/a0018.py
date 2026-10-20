"""Retain actual source components only; whole H16/PQR/Master still pending."""
from pathlib import Path
import hashlib,json,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
SUBJECT=PROJECT/'workspaces/project-r7-qualification-cd415a1'
sys.path[:0]=[str(SUBJECT/'src'),str(SUBJECT)]
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import _sanitize,revision_fact
from strategy.v02.capabilities import _revision
REV='cd415a11a97b4b04f490112f6d5ef319ad267395'
revision_fact(SUBJECT,REV,True)
prefixes=('h16-finalization-finalization-cd415a1','h16-finalization-finalization-tail-cd415a1')
a,b=[json.loads((BASE/p/'checkpoint.json').read_bytes()) for p in prefixes]
assert not a['passed'] and a['results'][-1]['status']=='NOT_RUN_RESOURCE_PREFLIGHT_BELOW_6GIB' and b['passed']
valid=a['results'][:-1]+b['results']
assert len(valid)==13 and sum(row['tests_run'] for row in valid)==15
ids=[case for row in valid for case in row['expected_case_ids']]
assert len(ids)==len(set(ids))==15 and len({row['module'] for row in valid})==13
for run in (a,b):
    assert run['executable_revision']==REV and run['implementation_hash']==_revision() and run['source_and_tests_unchanged']
for row in valid:
    assert row['passed'] and row['tree_reaped'] and row['source_and_tests_unchanged'] and row['within_original_wall_limit'] and row['wall_elapsed_seconds']<=900
review_ref='h16-finalization-implementation-review-final-20261020.json';raw=(BASE/review_ref).read_bytes()
assert hashlib.sha256(raw).hexdigest()=='b88f715d101d53c5db669e0c4bb69846f0534e053fd1ff58d781c2f97fbbc7df'
review=json.loads(raw);assert review['critical']==review['important']==0 and len(review['production_hashes'])==7
for ref,wanted in review['production_hashes'].items():
    assert hashlib.sha256((SUBJECT/ref).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==wanted
refs=[p+'/checkpoint.json' for p in prefixes]+['run_finalization_exact_source.py','run_finalization_exact_source_isolated.py','run_finalization_development.py','run_finalization_development_v02.py','run_finalization_review_faults_red.py','h16-finalization-review-faults-red/executed-subject-pin.json','h16-finalization-host-suspend-20261020.json','keep_awake_for_validation.py','h16-finalization-temporary-awake-cd415a1.json','h16-finalization-tail-temporary-awake-cd415a1.json','h16-finalization-implementation-review-initial-20261020.json','h16-finalization-implementation-review-revised-20261020.json',review_ref,'h16-finalization-regression-plan-20261020.json','h16-finalization-affected-module-plan-20261020.json','retain_finalization_components.py']
for prefix,run in zip(prefixes,(a,b)):
    for row in run['results']:
        if 'log_ref' in row:
            ref=prefix+'/'+row['log_ref'];assert 'sha256:'+hashlib.sha256((BASE/ref).read_bytes()).hexdigest()==row['log_hash'];refs.append(ref)
for prefix in ('h16-finalization-positive-red','h16-finalization-positive-green01','h16-finalization-positive-green02','h16-finalization-review-faults-red','h16-finalization-fixed-development','h16-finalization-clock-order-red','h16-finalization-clock-and-recovery-green01'):
    refs.extend([prefix+'/checkpoint.json',prefix+'/source.log'])
for pattern in ('*finalization*.unapplied','*k05*genuine*.unapplied','*h16*finalization*20261020.json','h01*.unapplied','*trading_orchestrator*.unapplied','h01*20261020.json','i04-j03*.unapplied','two_version*.unapplied','test_api_two_versions*.unapplied','i04-j03*20261020.json'):
    refs.extend(p.name for p in BASE.glob(pattern))
refs=list(dict.fromkeys(refs));prepared=[]
for ref in refs:
    raw=(BASE/ref).read_bytes();safe=_sanitize(raw.decode('utf-8'),ROOT)
    for path,label in ((ROOT,'<SOURCE_ROOT>'),(SUBJECT,'<QUALIFICATION_ROOT>'),(PROJECT,'<PROJECT_ROOT>'),(Path.home(),'<HOME>')):
        for spelling in (str(path),path.as_posix(),str(path).replace('\\','\\\\')):safe=safe.replace(spelling,label)
    prepared.append((ref,raw,('\n'.join(line.rstrip() for line in safe.splitlines()).rstrip()+'\n').encode()))
out=ROOT/'status/codex/productization/S12/h16-finalization-components-cd415a1'
create_private_directory(out);create_private_directory(out/'artifacts');items=[]
for index,(ref,raw,safe) in enumerate(prepared,1):
    path=out/'artifacts'/(f'a{index:04d}'+Path(ref).suffix);write_private_new(path,safe)
    items.append(dict(original_ref=ref,original_hash='sha256:'+hashlib.sha256(raw).hexdigest(),retained_ref=path.relative_to(out).as_posix(),retained_hash='sha256:'+hashlib.sha256(safe).hexdigest()))
doc=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',executable_revision=REV,implementation_hash=_revision(),status='GENUINE_FUNDED_FINALIZATION_RECOVERY_AND_K05_SOURCE_COMPONENTS_PASS',source_modules=13,source_cases=15,failures=0,errors=0,skips=0,source_and_tests_unchanged=True,all_children_reaped=True,per_module_limit_seconds=900,
 flows=['Actual original funded/terminal/native-zero graph invokes unchanged E5 TradeResult/CLOSED/full execution binding; exact original first-flat clock and repeat idempotence. Funding was durable before terminal stop.',
 'Actual commits then injected interruption after CLOSED, execution binding and TradeResult; genuine new generation2 owner/handles/issuer/empty provider drains same immutable outbox to READY without provider calls; original IDs/clocks retained and old lease denied.',
 'Copied/expired source objects, missing funding, cancel ACK substitution, unknown active inventory, changed terminal hash, under-lock expiry and impossible/nonUTC clocks all deny before durable finalization.',
 'Actual CLOSED graph uses protected K05 private readonly snapshot and public default OPT_OUT/explicit OPT_IN with exact original amounts. FIXTURE/FAKE_PROVIDER_VERIFICATION/SIMULATED_MECHANICS/BROKER_LEDGER, actual_live NOT_RUN, financial_authority NONE.'],
 actual_red='Initial3cases2FAIL1ERROR: stage freshness/hash/missing funding; fixed then development7PASS. Later future terminal receive RED1FAIL -> strict UTC/original order. Earlier writer-slot injection error and ENTRY-null-role test correction remain retained separately.',
 independent_review='FINAL_STATIC0C0I_EXECUTION_NONE',host_disposition='Development4OK9894.949s crossed actual sleep10:28:05Z–12:52:40Z; no clean/deadline credit. Fresh exact perfile recovery cases<=900s. User-authorized temporary system-awake request bound to each validation process; actual explicit release receipts, no permanent power/display/away-mode change.',
 resource_disposition='First exact aggregate6PASS then seventh NOT_RUN after6GiB preflight180s, retained as aggregate false; identical unchanged candidate resumed only remaining7modules/9cases. No thresholds changed or duplicate credit.',
 retainer_draft_correction='Initial nested-quote construction SyntaxError before helper/output creation; corrected before execution, not product/test-defect evidence.',
 affected_owner_regressions='RUNNING_SEPARATE_FROZEN_ISOLATED_CHECKOUT_26_MODULES',H16='COMPONENTS_ONLY_FULL_AFFECTED_AND_FINAL_ACCEPTANCE_PENDING',K05='GENUINE_CLOSED_SOURCE_POSITIVE_PASS_NATIVE_NOT_RUN',H01='FORMAL_E2_ENTRY_AND_ORIGINAL_MANAGEMENT_PENDING',native_full='NOT_RUN_FOR_THIS_SOURCE',master='IN_PROGRESS',preserved_qualified_windows='7d821f29837e95e46bcd5fe32f14d536a28c9aa8',public_requests_cumulative=8,public_responses_cumulative=8,additional_public_requests=0,private_requests=0,credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',artifacts=items)
write_private_new(out/'disposition.json',(json.dumps(doc,ensure_ascii=False,indent=2)+'\n').encode())
for item in items:assert 'sha256:'+hashlib.sha256((out/item['retained_ref']).read_bytes()).hexdigest()==item['retained_hash']
evidence=(out/'disposition.json').relative_to(ROOT).as_posix()
next_step='Finish frozen cd415 affected26/cleanup timings; continue original local F04/I04/J03/formal E2 entry+management/portable/audits/S16. Final settled inventory/examples/full/native remain; external oldPC/Ubuntu/cloud/policies/real-forward unaccepted.'
p=ROOT/'coordination/CODEX/PROGRESS.json';value=json.loads(p.read_bytes())
value.update(executable_revision=REV,candidate_executable_revision=REV,active_step='H16_GENUINE_FINALIZATION_K05_SOURCE15_PASS_AFFECTED_RUNNING',next_step=next_step)
value['h16_genuine_finalization_components']=dict(executable_revision=REV,implementation_hash=_revision(),status=doc['status'],source_modules=13,source_cases=15,evidence_ref=evidence,whole_H16='NOT_CLAIMED',native='NOT_RUN_FOR_THIS_SOURCE')
p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
note=f'''# H16 funded finalization/recovery and genuine K05 checkpoint — 2026-10-20

Source {REV}: disjoint13modules/15cases PASS, unchanged/reaped; each module<=900s.
Evidence: {evidence}.
Real guarded fake-provider entry/protection/single close/original zero plus
allocated fixture funding before terminal stop invokes unchanged E5 CLOSED,
TradeResult and full binding. Actual writer commits then interruptions at all
three effects recover with new owner/handles/issuer/process generation2, original
IDs/clocks, no provider calls. K05 protected private snapshot/public OPT_OUT and
explicit OPT_IN preserve exact amounts and honest fake-ledger provenance;
actual_live NOT_RUN and financial_authority NONE. Negative sources fail closed.

Actual2FAIL1ERROR -> minimal fixes/development7PASS; later future receive
RED1FAIL -> strict UTC/original order. Static0C0I executionNONE. Development
4OK9894.949s overlapped actual host sleep and earns no clean/deadline credit;
fresh exact perfile recoveries pass. Temporary awake only while validation
parents live was explicitly authorized; actual releases retained, no permanent
power/display/away-mode change. First exact group6PASS then resourceNOT_RUN
remains aggregate false; resumed only remaining7modules/9cases on same clean
candidate. No threshold lowering or duplicate-case credit.

Same original branch pushed source. Frozen project-contained qualification
checkout runs affected26modules; this15 is component proof, not wholeH16/PQR/
native/Master acceptance. Windows7d qualification preserved. Next F04/I04/J03,
formal E2 entry+management, portable/audits/S16 and settled full/native remain.
OldPC/Ubuntu/cloud/formal policies/real-forward not accepted; local work continues.
Public8/responses8/additional0/private0; credentialsNONE/capitalNONE/LIVENOT_STARTED/
GitHubNOT_USED. No main merge; original task and implementation branch retained.

'''
for ref in ('coordination/CODEX/HANDOFF.md','status/codex/R7_PRODUCTIZATION_MASTER_COMPLETION_20261002.md'):
    p=ROOT/ref;p.write_text(note+p.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print(json.dumps(dict(retained=len(items),evidence_ref=evidence,status=doc['status'])))
