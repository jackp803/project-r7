"""Retain exact controlled funding source evidence; H16 still in progress."""
from pathlib import Path
import hashlib,json,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import _sanitize,revision_fact
REV='53358976b1f5c3aa66b5948d8aa068860a6330eb';revision_fact(ROOT,REV,True)
refs=['h16-ledger-source-5335897/checkpoint.json','h16-ledger-source-5335897/source.log','run_h16_ledger_source.py',
    'h16-ledger-source-red.log','h16-ledger-source-green01.log','h16-ledger-source-green02.log',
    'h16-ledger-clock-red.log','h16-ledger-clock-green.log','h16-ledger-owner-red.log',
    'h16-ledger-owner-green01.log','h16-ledger-owner-account-repair.log',
    'diagnose_h16_funding_replay.py','h16-ledger-replay-diagnostic.log',
    'h16-ledger-owner-review-red.log','h16-ledger-owner-green02.log',
    'h16-ledger-source-review.json','h16-ledger-owner-review-initial.json','h16-ledger-owner-review-final.json',
    'h16-broker-ledger-source-plan-20261020.json','h16-owned-stop-finalization-plan-20261020.json',
    'retain_h16_ledger_source.py']
def digest(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
prepared=[]
for ref in refs:
    raw=(BASE/ref).read_bytes()
    value=_sanitize(raw.decode('utf-8'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>')
    safe=('\n'.join(line.rstrip() for line in value.splitlines()).rstrip()+'\n').encode()
    prepared.append((ref,raw,safe))
run=json.loads(prepared[0][1]);review=json.loads((BASE/'h16-ledger-owner-review-final.json').read_bytes())
if not (run['executable_revision']==REV and run['passed'] and run['tests_run']==146
        and review['critical']==0 and review['important']==0):raise ValueError('Actual clean146 and final static0C/I required')
for ref,expected in review['subject_hashes'].items():
    if hashlib.sha256((ROOT/ref).read_bytes()).hexdigest()!=expected:raise ValueError('Review subject changed')
out=ROOT/'status/codex/productization/S12/h16-ledger-source-5335897';create_private_directory(out)
art=out/'artifacts';create_private_directory(art);items=[]
for number,(ref,raw,safe) in enumerate(prepared,1):
    target=art/(f'a{number:04d}'+Path(ref).suffix);write_private_new(target,safe)
    items.append(dict(original_ref=ref,original_hash=digest(raw),retained_ref=target.relative_to(out).as_posix(),retained_hash=digest(safe),
        normalization='SANITIZED_ROOTS_LF_TRAILING_WHITESPACE_SINGLE_FINAL_NEWLINE'))
document=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',executable_revision=REV,
    implementation_hash=run['implementation_hash'],scope='CONTROLLED_ALLOCATED_LEDGER_AND_ORIGINAL_OWNER_SOURCE_ONLY',
    source_modules=14,source_cases=146,new_ledger_cases=11,new_owner_cases=8,failures=0,errors=0,skips=0,
    clean_source_unchanged=True,owned_tree_reaped=True,independent_review='FINAL_0_CRITICAL_0_IMPORTANT_EXECUTION_NONE',
    source_wire='R7 controlled FIXTURE-only versioned per-position allocated ledger; no actual OKX route, field, event-time or completeness mapping asserted.',
    actual_flow='Full actual FakeProductProvider entry/close/partial/native same-position zero with original E5 graph; only after flat, current guard issues source reads across actual two pages. Original source-issued allocation emits canonical funding and durable immutable outbox, never CLOSED or TradeResult.',
    semantics='Complete source coverage and final cursor required; half-open interval; exact native/account/plan/position scope. One zero/canceling rows INCLUDED with actual count; only affirmative complete empty ZERO_CONFIRMED; signed exact Decimal independent of ambient context.',
    identity='Complete page content hashes and private scope commitment bind normalized material; original typed instance/source/provider/lease/TTL and full canonical graph/current claim inventory are fenced. Receive/calculation clocks excluded from financial identity.',
    recovery='Actual canonical write failure after durable stage then successor lease replays original funding with zero new ledger/order calls. Source observation hash/material and original entry/flat link are validated before recovery publication; damaged exact-owned fixture rows refuse, restored bytes replay.',
    immutability='Actual INSERT OR REPLACE on both new tables with recursive_triggers OFF refuses; explicit duplicate-key BEFORE INSERT guards plus exact existing receipt validation preserve original rows/replay.',
    corrections=[
        'Pure source initial10 missing-module errors; first10 one fixture failure because test helper replaced empty invalid subject via truthiness. Explicit None correction;25 then26 pass.',
        'Post-page actual receive-clock support RED1error, then26 pass; sampled once after all pages before issuance.',
        'Owner missing-method RED1error; first6 errors because restored readback deliberately has no ephemeral mechanical_proof. Source account_scope now commits original E6 selected provider/account reference, explicitly not exchange UID/mechanical proof.',
        'Account repair firstpositive reached canonical funding but repeat failed. Field-names-only trace proves only broad claim-generation counter changed, recovery graph unchanged. Existing receipt path now revalidates full current context/source batch and fresh claim scan, returns history without restaging; every new writer retains original generation fence.',
        'Initial independent review0C/2I, actual3methods4failures expose REPLACE and damaged-source recovery. Fixed both; development34 pass, final146 pass, final static0C/I. Initial review and all original failures retained.'
    ],
    actual_production_ledger='UNSUPPORTED_NOT_CALLED',H16_complete='NOT_CLAIMED_STOP_CLEANUP_AND_TRADE_RESULT_PENDING',
    genuine_closed_dispatch='PENDING',K05_acceptance='NOT_CLAIMED',native_full='NOT_RUN_FOR_THIS_SOURCE',real_cloud='NOT_RUN',
    remaining='Use actual full-filled entry and active owned stop, specific durable cancel claim/targeted terminal readback plus complete inventory, original funding and real E5 TradeResult/closed_transition. Preserve single-close consumer and no blind cancel-all. Regenerate final inventory/examples/full/native after source settles.',
    frozen_inventory='STALE_PENDING_FINAL_CANDIDATE',preserved_qualified_windows='7d821f29837e95e46bcd5fe32f14d536a28c9aa8',
    master='IN_PROGRESS',public_requests_cumulative=8,public_responses_cumulative=8,additional_public_requests=0,
    private_requests=0,credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',artifacts=items)
write_private_new(out/'disposition.json',(json.dumps(document,ensure_ascii=False,indent=2)+'\n').encode())
for item in items:
    if digest((out/item['retained_ref']).read_bytes())!=item['retained_hash']:raise ValueError('Retained mismatch')
progress=ROOT/'coordination/CODEX/PROGRESS.json';value=json.loads(progress.read_bytes())
value.update(executable_revision=REV,candidate_executable_revision=REV,active_step='H16_FIXTURE_LEDGER_SOURCE_PASS_CONTINUE_OWNED_STOP_AND_TRADE_RESULT',
    next_step='Complete genuine fully-filled entry/protected/close/flat fixture, narrow durable exact-owned stop cleanup and terminal native readback/full inventory, E5 TradeResult and CLOSED transition with replay. Join genuine closed ProductDispatch K05 positive. Preserve qualified Windows7d. Final inventory/examples/full/native remain pending.')
value['h16_fixture_ledger_checkpoint']=dict(executable_revision=REV,status='SOURCE_ONLY_PASS',source_modules=14,source_cases=146,
    production_ledger='UNSUPPORTED_NOT_CALLED',H16_acceptance='NOT_CLAIMED',evidence_ref=(out/'disposition.json').relative_to(ROOT).as_posix())
progress.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
prefix=f'''# H16 controlled allocated-ledger owner source checkpoint — 2026-10-20

Source `{REV}` exact-clean14modules/146cases PASS, unchanged/reaped.
Evidence: `{(out/'disposition.json').relative_to(ROOT).as_posix()}`.
E4 registered FIXTURE-only source performs actual guarded fake GETs, bounded
complete page acquisition and exact allocated signed-cost normalization. It
binds original owner plan/position/native scope and actual flat EXIT_REQUESTED;
only canonical funding is emitted. No CLOSED/result/stop cancellation inferred.
Actual pending write failure then successor replays original fact without HTTP;
damaged source/hash/original-link recovery refuses. INSERT OR REPLACE on both
tables with recursive_triggers OFF refuses; exact receipt replay stays stable.
All RED/implementation/test-fixture failures and field-only replay diagnosis
retained. Initial static0C/2I and actual3method4fail counterexamples are followed
by development34 PASS and final146 PASS/static0C/I (reviewer execution NONE).
Logical account scope commits original E6 provider/account references; restored
readback deliberately contains no ephemeral mechanical proof. Actual production
ledger route/completeness/position allocation remains unsupported/not called.
H16/K05 still incomplete: genuine full-entry/active-stop/close flow, exact owned
durable stop cleanup/terminal evidence, E5 TradeResult and CLOSED publication.
Unapplied next-step plans have no execution credit. Continue this local work;
then regenerate final inventory/examples/full/native qualification. Preserve
qualified Windows ZIP7d821f2 and all earlier valid evidence. Master IN_PROGRESS,
original task/branch, public8/responses8/additional0/private0/credentialsNONE/
capitalNONE/LIVENOT_STARTED/GitHubNOT_USED. TargetPC/Ubuntu/cloud/policies/forward
remain external or unselected; no external environment wait for local work.

'''
for relative in ('coordination/CODEX/HANDOFF.md','status/codex/R7_PRODUCTIZATION_MASTER_COMPLETION_20261002.md'):
    path=ROOT/relative;path.write_text(prefix+path.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print(json.dumps(dict(retained=len(items),evidence_ref=(out/'disposition.json').relative_to(ROOT).as_posix())))
