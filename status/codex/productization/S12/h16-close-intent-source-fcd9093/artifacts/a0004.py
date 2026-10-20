"""Named exact source intent checkpoint; preserve failed setup, no native credit."""
from pathlib import Path
import hashlib,json,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.qualification import revision_fact,_sanitize
from application.platform.private_files import create_private_directory,write_private_new
REV='fcd909367373cf5a5362a179e0c8b7cc6eb4143b'
revision_fact(ROOT,REV,True)
refs=['h16-close-intent-source-fcd9093/checkpoint.json','h16-close-intent-source-fcd9093/source.log',
    'run_h16_close_intent_source.py','retain_h16_close_intent_source.py','h16-close-intent-red.log',
    'h16-close-intent-development-first.log','h16-close-intent-projection-development.log',
    'h16-close-intent-clock-and-inventory-retry01.log','h16-close-intent-source-review.json',
    'h16-close-intent-source-final-review.json','h16-close-intent-outbox-plan-9c4a741.json',
    'h16-broker-ledger-source-plan-20261020.json','cloud08-report-history-readonly-design-20261020.json']
prepared=[]
for ref in refs:
    raw=(BASE/ref).read_bytes();safe=_sanitize(raw.decode('utf-8'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>')
    safe=('\n'.join(line.rstrip() for line in safe.splitlines()).rstrip()+'\n').encode()
    prepared.append((ref,raw,safe))
run=json.loads(prepared[0][1])
if not (run['revision']==REV and run['passed'] and run['tests_run']==86 and run['source_unchanged'] and run['tree_reaped']):
    raise ValueError('Actual exact-clean86PASS/source unchanged/reaped required')
out=ROOT/'status/codex/productization/S12/h16-close-intent-source-fcd9093'
create_private_directory(out);art=out/'artifacts';create_private_directory(art)
def digest(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
files=[]
for number,(ref,raw,safe) in enumerate(prepared,1):
    target=art/(f'a{number:04d}'+Path(ref).suffix);write_private_new(target,safe)
    files.append(dict(original_ref=ref,original_hash=digest(raw),retained_ref=target.relative_to(out).as_posix(),
        retained_hash=digest(safe),normalization='SANITIZED_ROOTS_LF_TRAILING_LINE_WHITESPACE_SINGLE_FINAL_NEWLINE'))
document=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',branch='codex/r7-productization-master-20261002',
    executable_revision=REV,implementation_hash=run['implementation_hash'],scope='CLOSE_INTENT_AND_NATIVE_CLOSE_SOURCE_ONLY',
    source_cases=86,source_modules=9,source_commands=1,failures=0,errors=0,skips=0,source_unchanged=True,tree_reaped=True,
    initial_red=dict(cases=2,failures=2),first_development=dict(cases=5,failures=0,errors=0),
    original_integration=dict(cases=17,errors=1,reason='FIXTURE_DIFFERENT_DISPATCH_OBSERVATIONS_AT_EQUAL_IMMUTABLE_CLOCK',
        product_change_for_fixture_error='NONE',corrected='Actual guarded POST then process loss before observation commit',
        selected_corrected_and_new_selector_cases=3,selected_failures=0,selected_errors=0),
    static_review='0_CRITICAL_0_IMPORTANT_FINAL;EXECUTION_NONE',
    supported=['Original positive source unchanged through final provider guard',
        'Actual ACK/uncertainty/claim-only recovery records exact original request and local EXIT_REQUESTED intent',
        'Immutable claim, original broker and local interpretation clocks remain separate',
        'No invented ACK/fill/flatness; successor-process outbox replay without HTTP',
        'Exact intent predecessor to actual native partial/flat, equal-time refusal and actual later observation',
        'Bounded own-run selector and real second-connection generation fences'],
    whole_H16='INCOMPLETE_STOP_CLEANUP_BROKER_LEDGER_FUNDING_TRADE_RESULT',native_full='NOT_RUN_FOR_THIS_SOURCE',
    frozen_inventory='STALE_UNTIL_NEXT_FINAL_CANDIDATE',qualified_windows_executable='7d821f29837e95e46bcd5fe32f14d536a28c9aa8',
    master='IN_PROGRESS',plans='DESIGN_ONLY_NOT_EXECUTED_NO_ACCEPTANCE_CREDIT',
    real_data_cumulative_public_requests=8,real_data_cumulative_public_responses=8,additional_public_requests=0,
    private_requests=0,credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',artifacts=files)
write_private_new(out/'disposition.json',(json.dumps(document,ensure_ascii=False,indent=2)+'\n').encode())
for item in files:
    if digest((out/item['retained_ref']).read_bytes())!=item['retained_hash']:raise ValueError('Retained hash mismatch')
progress=ROOT/'coordination/CODEX/PROGRESS.json';state=json.loads(progress.read_bytes())
state.update(executable_revision=REV,candidate_executable_revision=REV,
    active_step='S16_CLOSE_INTENT_SOURCE_PASS_CONTINUE_REPORT_HISTORY_K05_AND_CLOSE_ACCOUNTING',
    next_step='Continue actual readonly research/Paper report delivery history and K05; finish H16 exact stop cleanup, source-owned broker funding and TradeResult. Sourcefcd86PASS only; preserve fully qualified7d Windows ZIP. Regenerate final PQR/examples and rerun full/native after final source is settled. OldPC/Ubuntu/cloud/policies/forward remain external or unselected.')
state['h16_close_intent_source_checkpoint']=dict(executable_revision=REV,source_cases=86,source_modules=9,
    status='AFFECTED_SOURCE_PASS_ONLY',whole_H16=document['whole_H16'],native='NOT_RUN',
    evidence_ref=(out/'disposition.json').relative_to(ROOT).as_posix())
progress.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
handoff=ROOT/'coordination/CODEX/HANDOFF.md'
prefix=f'''# H16 committed close intent source checkpoint — 2026-10-20

Source `{REV}` exact-clean9modules/86cases PASS, source unchanged/tree reaped.
Evidence: `{(out/'disposition.json').relative_to(ROOT).as_posix()}`.
Actual guarded POST keeps original positive E5 source through the final effect
guard. ACK/uncertainty and claim-only crash now record immutable local intent;
the original request is legitimate, no ACK/fill/provider submission is invented.
Claim time, original broker clock and local interpretation stay distinct.
Actual native partial/zero chains from intent; equal-time replacement refuses,
then a genuine later read succeeds. Successor lease replay performs no HTTP.
Final static review0C/I, execution NONE; original fixture clock error preserved.
H16 still needs exact owned-stop cleanup, BROKER_LEDGER source and TradeResult.
No guessed OKX funding fields/completeness/position attribution are authorized.
ADR-0006 permits independent provider-neutral producer and controlled fixture
source work; source plan is retained as DESIGN_ONLY, not executed acceptance.
Continue readonly research/Paper report-delivery history and K05 independently.
Final frozen PQR/examples and full/native qualification remain pending for
changed source. Fully qualified Windows portable candidate remains7d821f2.
All source must stay frozen throughout every next verification run.
Master IN_PROGRESS; targetPC/Ubuntu/cloud/policies/real-forward remain external
or unselected. Public8/responses8, additional0/private0/credentialsNONE/capitalNONE,
LIVENOT_STARTED/GitHubNOT_USED. Preserve same task/branch and every prior failure.

'''
handoff.write_text(prefix+handoff.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print(json.dumps(dict(retained=len(files),evidence_ref=(out/'disposition.json').relative_to(ROOT).as_posix())))
