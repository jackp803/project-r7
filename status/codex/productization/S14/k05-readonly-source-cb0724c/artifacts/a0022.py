"""Retain RO foundation source checks; K05 public summary remains unfinished."""
from pathlib import Path
import hashlib,json,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import _sanitize,revision_fact
REV='cb0724c0d292a0058435b07e76eec96d56356373';revision_fact(ROOT,REV,True)
refs=['k05-readonly-source-cb0724c/checkpoint.json','k05-readonly-source-cb0724c/source.log','run_k05_readonly_source.py',
    'k05-readonly-history-red.log','k05-readonly-history-green01.log','k05-readonly-history-green02.log',
    'diagnose_k05_readonly.py','k05-readonly-diagnostic01.log','k05-readonly-diagnostic02.log','k05-readonly-diagnostic03.log',
    'k05-readonly-history-green03.log','k05-readonly-review-red.log','k05-readonly-review-red-retry01.log',
    'k05-readonly-history-green04.log','k05-readonly-strategy-shape-red.log','k05-readonly-strategy-shape-green.log',
    'k05-readonly-history-source-review.json','k05-readonly-history-source-repair-review.json','k05-readonly-history-source-final-review.json',
    'k05-authority-and-local-plan.json','../k05-source-test-drafts-20261020/K05-test-design.json','retain_k05_readonly_source.py']
def digest(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
prepared=[]
for ref in refs:
    raw=(BASE/ref).read_bytes()
    value=_sanitize(raw.decode('utf-8'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>')
    safe=('\n'.join(line.rstrip() for line in value.splitlines()).rstrip()+'\n').encode()
    prepared.append((ref,raw,safe))
run=json.loads(prepared[0][1]);review=json.loads((BASE/'k05-readonly-history-source-final-review.json').read_bytes())
if not (run['executable_revision']==REV and run['passed'] and run['tests_run']==27
        and review['counts']=={'Critical':0,'Important':0}):raise ValueError('Actual clean27 and static0C/I required')
out=ROOT/'status/codex/productization/S14/k05-readonly-source-cb0724c';create_private_directory(out)
art=out/'artifacts';create_private_directory(art);items=[]
for number,(ref,raw,safe) in enumerate(prepared,1):
    target=art/(f'a{number:04d}'+Path(ref).suffix);write_private_new(target,safe)
    items.append(dict(original_ref=ref,original_hash=digest(raw),retained_ref=target.relative_to(out).as_posix(),retained_hash=digest(safe),
        normalization='SANITIZED_ROOTS_LF_TRAILING_WHITESPACE_SINGLE_FINAL_NEWLINE'))
document=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',executable_revision=REV,
    implementation_hash=run['implementation_hash'],scope='K05_READONLY_FOUNDATION_SOURCE_ONLY',
    source_cases=27,readonly_cases=14,dispatch_regression_cases=13,failures=0,errors=0,skips=0,
    clean_source_unchanged=True,owned_tree_reaped=True,independent_review='0_CRITICAL_0_IMPORTANT_EXECUTION_NONE',
    RED=dict(missing_reader='8_CASES_8_ERRORS',malformed_blob_retry='1_METHOD_2_REAL_ATTRIBUTE_ERRORS',
        malformed_strategy_object='1_METHOD_2_REAL_ATTRIBUTE_ERRORS'),
    implementation_corrections=[
        'Original ApprovedTradePlan has no strategy_content_hash; actual KeyError diagnosed and replaced with immutable E6 strategy version binding.',
        'Composite authority_hash is not plan hash; actual valid history refusal diagnosed and corrected to durable source_plan_hash with original E4 hash helper.',
        'Owned schema/namespace rechecked inside each snapshot transaction, not only context open; actual second-connection trigger removal refuses repeated reads.',
        'Exact-schema BLOB binding/request and nonobject definition refuse typed before string/mapping helpers; no broad AttributeError masking.'
    ],
    fixture_correction='First BLOB intent used invalid non-JSON bytes rejected by existing expression index before reader; retained. Retry uses exact original valid JSON bytes as BLOB. Current corruption helper restores every original row individually and exact triggers.',
    diagnostic_limit='First trace helper path separator filter missed locations; retained. Second trace proves missing field, third proves composite/plan commitment mismatch. No provider/DB payload was dumped.',
    actual_flow='Actual owner-created dispatch ACK and canonical pending history; RO URI/query_only with write authorizer; actual process successor and approval revocation preserve history; actual WAL-backed split-store successor append causes SNAPSHOT_CHANGED; no writer/admission/provider in normal read.',
    available_performance='NONE_FROM_OPEN_ACK_HISTORY;NOT_ZERO',public_summary='NOT_IMPLEMENTED',K05_acceptance='NOT_CLAIMED',
    H16_complete='NOT_CLAIMED',real_cloud='NOT_RUN',native_full='NOT_RUN_FOR_THIS_SOURCE',
    frozen_inventory='STALE_PENDING_FINAL_CANDIDATE',preserved_qualified_windows='7d821f29837e95e46bcd5fe32f14d536a28c9aa8',
    master='IN_PROGRESS',public_requests_cumulative=8,public_responses_cumulative=8,additional_public_requests=0,
    private_requests=0,credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',artifacts=items)
write_private_new(out/'disposition.json',(json.dumps(document,ensure_ascii=False,indent=2)+'\n').encode())
for item in items:
    if digest((out/item['retained_ref']).read_bytes())!=item['retained_hash']:raise ValueError('Retained mismatch')
progress=ROOT/'coordination/CODEX/PROGRESS.json';value=json.loads(progress.read_bytes())
value.update(executable_revision=REV,candidate_executable_revision=REV,active_step='K05_RO_FOUNDATION_SOURCE_PASS_CONTINUE_SANITIZED_SUMMARY_AND_H16',
    next_step='Implement strict additive K05 sanitized summary/consumer privacy and public dispatch using only the actual RO reader. Complete H16 owned stop cleanup, BROKER_LEDGER producer/source and TradeResult; genuine closed ProductDispatch positive remains missing. Preserve qualified Windows7d and valid CLOUD08 source6cd. Final inventory/examples/full/native remain pending.')
value['k05_readonly_foundation_checkpoint']=dict(executable_revision=REV,source_cases=27,readonly_cases=14,dispatch_cases=13,
    status='SOURCE_ONLY_PASS',public_summary='NOT_IMPLEMENTED',K05_acceptance='NOT_CLAIMED',
    evidence_ref=(out/'disposition.json').relative_to(ROOT).as_posix())
progress.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
prefix=f'''# K05 readonly history foundation source checkpoint — 2026-10-20

Source `{REV}` exact-clean2modules/27cases PASS (14RO+13dispatch),
unchanged/reaped; static review0C/I (execution NONE).
Evidence: `{(out/'disposition.json').relative_to(ROOT).as_posix()}`.
Actual original E6 strategy/plan/claimed request history uses protected RO
connections and existing E6 recovery only. Schema/namespace recheck occurs in
each snapshot transaction; one same-file transaction or split-store version
fence. Real successor generation/revocation leaves original history unchanged;
actual split-store append refuses. No owner/writer/admission/provider in GET.
Open ACK/pending history has no closed performance, not invented zero.
Missing-module8errors and implementation/shape/fixture failures preserved.
Actual diagnostics corrected absent plan content-hash field and composite
authority_hash versus source_plan_hash; schema/BLOB/object guards stay strict.
The public summary/formatter/schema is not yet implemented. K05 and full H16
are NOT accepted. Genuine funded/closed ProductDispatch fixture remains missing.
Continue strict additive sanitized K05 summary; H16 owned-stop cleanup,
BROKER_LEDGER source/producer and TradeResult. Later final inventory/examples/
full/native qualification required. Preserve valid CLOUD08 source6cd and
fully qualified Windows ZIP7d821f2, original task/branch, Master IN_PROGRESS.
Public8/responses8, additional0/private0/credentialsNONE/capitalNONE/
LIVENOT_STARTED/GitHubNOT_USED. TargetPC/Ubuntu/cloud/policies/forward remain
external or unselected; do not wait for them to finish independent local work.

'''
for relative in ('coordination/CODEX/HANDOFF.md','status/codex/R7_PRODUCTIZATION_MASTER_COMPLETION_20261002.md'):
    path=ROOT/relative;path.write_text(prefix+path.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print(json.dumps(dict(retained=len(items),evidence_ref=(out/'disposition.json').relative_to(ROOT).as_posix())))
