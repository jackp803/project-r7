"""Retain exact terminal-reader source proof, without whole-H16/PQR credit."""
from pathlib import Path
import hashlib,json,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import _sanitize,revision_fact
from strategy.v02.capabilities import _revision
REV=sys.argv[1];revision_fact(ROOT,REV,True)
prefix='h16-terminal-owner-source-'+REV[:7]
refs=[prefix+'/checkpoint.json',prefix+'/source.log','run_terminal_owner_source.py',
 'run_terminal_stop_owner_red_retry01.py','h16-terminal-stop-owner-red-retry01/checkpoint.json',
 'h16-terminal-stop-owner-red-retry01/source.log','run_terminal_stop_owner_green01.py',
 'h16-terminal-stop-owner-green01/checkpoint.json','h16-terminal-stop-owner-green01/source.log',
 'run_terminal_stop_owner_issuer_red.py','h16-terminal-stop-owner-issuer-red/checkpoint.json',
 'h16-terminal-stop-owner-issuer-red/source.log','run_terminal_stop_owner_issuer_red_retry01.py',
 'h16-terminal-stop-owner-issuer-red-retry01/checkpoint.json','h16-terminal-stop-owner-issuer-red-retry01/source.log',
 'h16-terminal-owner-review-initial-20261020.json','h16-terminal-owner-review-final-20261020.json',
 'h16-finalization-bounded-positive-plan-20261020.json','trading_finalization_fixtures.py.unapplied',
 'test_trading_finalization_positive_v02.py.unapplied','retain_terminal_owner_source.py']
def digest(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
prepared=[]
for ref in refs:
    raw=(BASE/ref).read_bytes();safe=_sanitize(raw.decode('utf-8'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>')
    safe=('\n'.join(line.rstrip() for line in safe.splitlines()).rstrip()+'\n').encode()
    prepared.append((ref,raw,safe))
run=json.loads(prepared[0][1])
if not (run['executable_revision']==REV and run['passed'] and run['tests_run']==20 and len(run['modules'])==6 and
        run['source_unchanged'] and run['tree_reaped'] and run['implementation_hash']==_revision()):
    raise ValueError('Actual completed exact clean20 required')
review_raw=(BASE/'h16-terminal-owner-review-final-20261020.json').read_bytes()
if digest(review_raw)!='sha256:87b044f1bd76d7b2be770bdf7700e470a2e2f2a76f26ece7e238c722ccf24338':
    raise ValueError('Exact reviewed three-file map required before path interpretation')
review=json.loads(review_raw)
if review['critical']!=0 or review['important']!=0 or len(review['subject_hashes'])!=3:raise ValueError('Review mismatch')
for ref,wanted in review['subject_hashes'].items():
    if hashlib.sha256((ROOT/ref).read_bytes()).hexdigest()!=wanted:raise ValueError('Reviewed source changed')
if digest(prepared[1][1])!=run['log_hash']:raise ValueError('Exact source log mismatch')
out=ROOT/'status/codex/productization/S12'/('h16-terminal-owner-'+REV[:7]);create_private_directory(out)
art=out/'artifacts';create_private_directory(art);items=[]
for n,(ref,raw,safe) in enumerate(prepared,1):
    path=art/(f'a{n:04d}'+Path(ref).suffix);write_private_new(path,safe)
    items.append(dict(original_ref=ref,original_hash=digest(raw),retained_ref=path.relative_to(out).as_posix(),retained_hash=digest(safe)))
doc=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',executable_revision=REV,
 implementation_hash=run['implementation_hash'],status='FIXTURE_TERMINAL_OWNER_SOURCE20_PASS',source_modules=6,source_cases=20,
 failures=0,errors=0,skips=0,source_unchanged=True,tree_reaped=True,
 genuine_owner_flow='Real guarded FakeProductProvider full entry/protection/single close/partial/original native zero, durable exact cleanup, actual canonical CANCELED reconcile then additional exact target GET. Issued fact preserves native creation/update/receive clocks. No Position/TradeResult mutation and no second cancel.',
 issuer_fences='Original E6 stop/close/cleanup/flat/protection/entry/plan/current canonical graph and all account entries; current provider/process, actual claim inventory generation, exact local issued-object/cache identity/hash and unchanged5second read window. Actual other-connection unknownENTRY append after GET denies issuance.',
 source_boundary_regression='Initial static0C1I: a provider replaced after the actual final source scan was accepted. Actual valid regression RED1FAIL ValueError notraised74.791s. Final local recheck of exact cache/issuer/provider/lease/hash/window, actual process and generation closes gap without renewing source time. Current genuinepositive also probes post-source lease/cache/actual independent claim changes.',
 fixture_correction='First issuer fault-injection attempt ERROR: PaperRuntimeJournal slot method is read-only at instance. Original preserved; patch class descriptor invokes actual bound method before replacement. That instrumentation error earns no product-defect evidence; corrected actual RED does.',
 genuine_valid_fk_oracle='Original cleanup immutability test now actually passes with alternatePK referencing real existing claimedENTRY; schema-only1PASS also verifies exact native replacement trigger error. Earlier isolated migrated testDB mutation proof removes only native-unique OR branch and fails as expected; preserved separate b5cfc0c evidence. No missing-FK mask credit.',
 independent_review='INITIAL0C1I_THEN_FINAL0C0I_REVIEWER_EXECUTION_NONE',
 prior_source158='7de FAILED92actualRESEARCH_MEMORY_PRESSURE/66PASS including cleanup11, unchanged/reaped; not overwritten or promoted to PASS.',
 resource='User freed applications; actual current runs admit normally. Existing product memory floor, read windows, perfile900second qualification limit and host settings unchanged. This aggregate20 source run is not owning PQR or whole cleanup partition timing.',
 next='Apply preserved bounded one-case genuine finalization positive+non-TestCase helpers, observe missing-finalizer RED, implement existing E5 funded TradeResult/CLOSED/binding and immutable recovery outbox. Funding must be durable while READY before canonical terminal stop; no first-flat rebase. Then genuine K05closed positive. Other4planned negatives preserved; recovery cases and all11cleanup partition timings/final settled inventory/full/native remain.',
 H16='INCOMPLETE_FUNDED_CLOSED_TRADE_RESULT_AND_RECOVERY_PENDING',K05='INCOMPLETE_GENUINE_CLOSED_DISPATCH_PENDING',
 H01='INCOMPLETE_FORMAL_E2_TRADING_RUNNER',native_full='NOT_RUN_FOR_THIS_SOURCE',master='IN_PROGRESS',
 preserved_qualified_windows='7d821f29837e95e46bcd5fe32f14d536a28c9aa8',
 actual_production_cleanup='UNSUPPORTED_NOT_CALLED',actual_production_funding='UNSUPPORTED_NOT_CALLED',
 public_requests_cumulative=8,public_responses_cumulative=8,additional_public_requests=0,private_requests=0,
 credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',artifacts=items)
write_private_new(out/'disposition.json',(json.dumps(doc,ensure_ascii=False,indent=2)+'\n').encode())
for item in items:
    if digest((out/item['retained_ref']).read_bytes())!=item['retained_hash']:raise ValueError('Retained mismatch')
evidence=(out/'disposition.json').relative_to(ROOT).as_posix()
p=ROOT/'coordination/CODEX/PROGRESS.json';value=json.loads(p.read_bytes())
value.update(executable_revision=REV,candidate_executable_revision=REV,active_step='H16_TERMINAL_OWNER_SOURCE20_PASS_CONTINUE_FUNDED_FINALIZATION',next_step=doc['next'])
value['h16_terminal_stop_owner_checkpoint']=dict(executable_revision=REV,status=doc['status'],source_modules=6,source_cases=20,evidence_ref=evidence,H16_acceptance='NOT_CLAIMED')
p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
note=f'''# H16 terminal-stop owner checkpoint — 2026-10-20

Source `{REV}` exact-clean6modules/20cases PASS, unchanged/tree reaped.
Evidence: `{evidence}`.
Actual guarded original entry/protection/close/flat/cleanup/CANCELED reconcile
then exact target GET issues a local fact only; no canonical change/new cancel.
Original graph/plan/claim/firstflat/protection/native clocks, actual account
claims/process/generation/provider and local issuer/hash/original5s all fenced.
Actual unknownENTRY append after real GET denies issuance; post-source provider,
lease/cache and real independent claim changes deny consumption. Static0C1I
then actualRED1FAIL ValueError notraised74.791s exposed final issuer gap; fixed
final local/generation/process fence, static0C0I executionNONE. Earlier fault
injection ERROR due instance read-only slot retained; class-descriptor correction
calls actual original source method. No defect credit for instrumentation error.
Genuine alternatePK immutability test now passes with real claimedENTRY validFK,
alongside exact schema guard test. Earlier isolated mutation oracle retained.
Original7de158FAILED92memoryerrors/66PASS inclcleanup11 remains failed. Product
floor/deadlines/TTL/OS settings unchanged. This20 is source component proof,
not PQR/native/all cleanup partition timing or H16/K05 acceptance.

Next apply bounded one-case genuine funded finalization positive/helpers and
observe missingfinalizer RED. Funding durable whileREADY BEFORE terminal stop;
exact firstflat unchanged; real existing E5 TradeResult/CLOSED/full binding plus
immutable outbox replay and genuine K05positive. Fournegative drafts preserved;
all11cleanup partitions/final settled inventory/examples/full/native pending.
H01 formalE2trading runner, F04/I04/J03/portable/audits/clause binder remain local.
Windows7d qualified package/evidence preserved; Master IN_PROGRESS. Original
task/branch, no merge. Public8/responses8/additional0/private0; credentialsNONE/
capitalNONE/LIVE notstarted/GitHubnotused. External oldPC/Ubuntu/cloud/policies/
realforward not accepted; independent local work continues.

'''
for ref in ('coordination/CODEX/HANDOFF.md','status/codex/R7_PRODUCTIZATION_MASTER_COMPLETION_20261002.md'):
    p=ROOT/ref;p.write_text(note+p.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print(json.dumps(dict(retained=len(items),evidence_ref=evidence,status=doc['status'])))
