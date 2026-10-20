"""Retain additive K05 consumer proof; no funded dispatch or native credit."""
from pathlib import Path
import hashlib,json,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import _sanitize,revision_fact
REV='77613c3e91460ba1fe364457aadfac7118e636cd';revision_fact(ROOT,REV,True)
refs=['k05-feedback-source-77613c3/checkpoint.json','k05-feedback-source-77613c3/source.log',
    'run_k05_feedback_relabel_source.py','run_k05_feedback_source.py',
    'k05-feedback-source-6d74ece/checkpoint.json','k05-feedback-source-6d74ece/source.log',
    'k05-feedback-privacy-red.log','k05-feedback-privacy-green01.log','k05-feedback-schema-red.log',
    'k05-feedback-privacy-green02.log','k05-feedback-public-constructor-green.log',
    'k05-feedback-provenance-shape-red.log','k05-feedback-provenance-shape-green.log',
    'k05-feedback-paper-zero-relabel-red.log','k05-feedback-paper-zero-relabel-green.log',
    'k05-public-summary-source-final-review.json','k05-public-summary-relabel-final-review.json',
    'k05-authority-and-local-plan.json','../k05-source-test-drafts-20261020/K05-test-design.json',
    'retain_k05_feedback_relabel_source.py']
def digest(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
prepared=[]
for ref in refs:
    raw=(BASE/ref).read_bytes()
    value=_sanitize(raw.decode('utf-8'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>')
    safe=('\n'.join(line.rstrip() for line in value.splitlines()).rstrip()+'\n').encode()
    prepared.append((ref,raw,safe))
run=json.loads(prepared[0][1]);review=json.loads((BASE/'k05-public-summary-relabel-final-review.json').read_bytes())
if not (run['executable_revision']==REV and run['passed'] and run['tests_run']==60
        and review['critical']==0 and review['important']==0):raise ValueError('Actual clean60 and final repair static0C/I required')
for ref,expected in review['subject_hashes'].items():
    if hashlib.sha256((ROOT/ref).read_bytes()).hexdigest()!=expected:raise ValueError('Review subject changed')
out=ROOT/'status/codex/productization/S14/k05-public-summary-source-77613c3';create_private_directory(out)
art=out/'artifacts';create_private_directory(art);items=[]
for number,(ref,raw,safe) in enumerate(prepared,1):
    target=art/(f'a{number:04d}'+Path(ref).suffix);write_private_new(target,safe)
    items.append(dict(original_ref=ref,original_hash=digest(raw),retained_ref=target.relative_to(out).as_posix(),retained_hash=digest(safe),
        normalization='SANITIZED_ROOTS_LF_TRAILING_WHITESPACE_SINGLE_FINAL_NEWLINE'))
document=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',executable_revision=REV,
    implementation_hash=run['implementation_hash'],scope='K05_PUBLIC_SUMMARY_CONSUMER_AND_PROTECTED_READONLY_SOURCE_ONLY',
    source_modules=7,source_cases=60,failures=0,errors=0,skips=0,clean_source_unchanged=True,owned_tree_reaped=True,
    independent_review='FINAL_RESERVED_VERSION_REPAIR_0_CRITICAL_0_IMPORTANT_EXECUTION_NONE',
    earlier_review='Earlier source0C/I preceded a later concrete reserved PaperZero version relabel counterexample; preserved and superseded for that defect.',
    prior_candidate=dict(revision='6d74ece479834650665e13a9f8d01f3a1ecc5bf8',cases=59,status='SOURCE_PASS_THEN_NEW_RELABEL_COUNTEREXAMPLE_FOUND_NOT_FINAL'),
    RED=dict(missing_module='8_ERRORS',missing_schema='1_ERROR',unhashable_provenance='1_METHOD_3_TYPE_ERRORS',
        reserved_paper_model_relabel='1_METHOD_2_FAILURES_BOTH_VALIDATORS'),
    implementation_and_fixture_corrections=[
        'Initial projection used nonexistent TradeResult calculated_at; actual closed_at is copied, no invented report clock.',
        'One actual-reader test missed json import; test import fixed, original failure retained.',
        'Malformed provenance string types are rejected before hash-set membership; no broad TypeError masking.',
        'Both runtime and committed JSON schema reserve paper-zero-funding-v0.1 against BROKER_LEDGER relabeling; targeted3 and final60 pass.'
    ],
    actual_flows='Paper owner closed consumer fixture validates source JSON/HTML/privacy opt-out and opt-in; actual protected ProductDispatch open ACK constructor returns UNAVAILABLE/null; existing legacy public dispatch/Paper bridge/outbox/research redaction remain compatible.',
    provenance='PAPER_OWNER_SOURCE_FIXTURE and FAKE_PROVIDER_VERIFICATION remain explicit; no actual-LIVE test or assertion.',
    performance='OPT_OUT null by default; opt-in copies canonical PnL/fees/funding only. No calculation or aggregation/new authority.',
    genuine_closed_dispatch='NOT_IMPLEMENTED_BY_THIS_SLICE',actual_live='NOT_RUN',financial_authority='NONE',
    K05_acceptance='NOT_CLAIMED',H16_complete='NOT_CLAIMED',native_full='NOT_RUN_FOR_THIS_SOURCE',real_cloud='NOT_RUN',
    frozen_inventory='STALE_PENDING_FINAL_CANDIDATE',preserved_qualified_windows='7d821f29837e95e46bcd5fe32f14d536a28c9aa8',
    master='IN_PROGRESS',public_requests_cumulative=8,public_responses_cumulative=8,additional_public_requests=0,
    private_requests=0,credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',artifacts=items)
write_private_new(out/'disposition.json',(json.dumps(document,ensure_ascii=False,indent=2)+'\n').encode())
for item in items:
    if digest((out/item['retained_ref']).read_bytes())!=item['retained_hash']:raise ValueError('Retained mismatch')
progress=ROOT/'coordination/CODEX/PROGRESS.json';value=json.loads(progress.read_bytes())
value.update(executable_revision=REV,candidate_executable_revision=REV,active_step='K05_PUBLIC_SUMMARY_SOURCE_PASS_CONTINUE_H16_FUNDED_CLOSED_OWNER',
    next_step='Complete provider-neutral E4 observed-ledger source and fixture-only acquisition/owner integration, exact owned-stop cleanup and canonical TradeResult. Join genuine funded/closed ProductDispatch K05 positive. Preserve qualified Windows7d and prior valid source evidence. Final inventory/examples/full/native remain pending.')
value['k05_public_summary_checkpoint']=dict(executable_revision=REV,status='SOURCE_ONLY_PASS',source_modules=7,source_cases=60,
    genuine_closed_dispatch='NOT_IMPLEMENTED',K05_acceptance='NOT_CLAIMED',evidence_ref=(out/'disposition.json').relative_to(ROOT).as_posix())
progress.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
prefix=f'''# K05 sanitized historical summary source checkpoint — 2026-10-20

Source `{REV}` exact-clean7modules/60cases PASS, unchanged/reaped.
Evidence: `{(out/'disposition.json').relative_to(ROOT).as_posix()}`.
Additive strict v0.3 JSON/schema/escaped HTML consumes original canonical
amounts and closed_at; default OPT_OUT exports no amounts. Protected actual
open dispatch returns UNAVAILABLE/null, not zero. Paper owner source fixture
consumer is separately labeled and does not supply actual broker funding.
Actual-LIVE HISTORICAL_CANONICAL_RECORDS branch remains unexecuted/unaccepted;
all exported financial authority NONE. Existing reports/bridge remain compatible.
Prior candidate6d74 passed59, then a concrete PaperZero relabel counterexample
failed both validators; exact reserved version now rejected, focused3 and
final60 passed. Earlier0C/I review predates that finding; fresh repair review
0C/I inspects exact final hashes (reviewer execution NONE). Every failure saved.
Genuine funded/closed ProductDispatch positive and H16 stop cleanup/funding/TR
remain unfinished; K05/H16/native/full acceptance is not claimed.
Continue E4 observed-ledger source/fixture-only acquisition and actual owner
integration under existing ADR, no real-provider mapping invented. Then final
inventory/examples/full/native qualification. Windows ZIP7d821f2 remains the
qualified release. Master IN_PROGRESS on original task/branch. Public8/responses8,
additional0/private0/credentialsNONE/capitalNONE/LIVENOT_STARTED/GitHubNOT_USED.
TargetPC/Ubuntu/cloud/policies/forward remain external or unselected.

'''
for relative in ('coordination/CODEX/HANDOFF.md','status/codex/R7_PRODUCTIZATION_MASTER_COMPLETION_20261002.md'):
    path=ROOT/relative;path.write_text(prefix+path.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print(json.dumps(dict(retained=len(items),evidence_ref=(out/'disposition.json').relative_to(ROOT).as_posix())))
