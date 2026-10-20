"""Retain exact-clean close-owner source evidence and all named failed attempts."""
from pathlib import Path
import hashlib,json,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.qualification import _sanitize,revision_fact
from application.platform.private_files import create_private_directory,write_private_new
REV='9c4a74108d4c1960d6213357f9fc32e4785fce25'
revision_fact(ROOT,REV,True)
refs=['h16-native-close-source-9c4a741/checkpoint.json','h16-native-close-source-9c4a741/source.log',
    'run_h16_native_close_source.py','retain_h16_native_close_source.py',
    'h16-cross-role-claim-inventory-red.log','h16-cross-role-claim-inventory-development-green.log',
    'h16-native-close-preparation-red.log','h16-native-close-preparation-red-retry01.log',
    'h16-native-close-preparation-development.log','h16-close-final-provider-guard-red.log',
    'h16-close-final-provider-guard-red-retry01.log','h16-close-preparation-guard-development-green.log',
    'h16-close-preparation-guard-development-retry01.log','h16-close-preparation-guard-review.json',
    'h16-close-foreign-entry-final-guard-red.log','h16-close-entry-and-role-final-guard-green.log',
    'h16-close-preparation-guard-final-review.json','h16-close-preparation-expanded-regression.log',
    'h16-close-preparation-protection-failure-isolated.log','h16-native-close-projection-red.log',
    'h16-native-close-projection-development-first.log','h16-native-close-projection-development-suite.log',
    'h16-close-historical-entry-red.log','h16-close-historical-entry-green.log',
    'h16-close-backdated-outbox-red.log','h16-native-close-projection-development-retry01.log',
    'h16-native-close-observation-source-review.json','h16-native-close-observation-source-final-review.json',
    'h16-genuine-close-owner-plan.json','h16-close-owner-mechanical-binding-plan.json',
    'h16-close-intent-outbox-plan-9c4a741.json','h16_close_intent_tests_draft.py.unapplied',
    'cloud08-report-history-readonly-design-20261020.json']
prepared=[]
for ref in refs:
    raw=(BASE/ref).read_bytes()
    safe=_sanitize(raw.decode('utf-8'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>')
    safe=('\n'.join(line.rstrip() for line in safe.splitlines()).rstrip()+'\n').encode()
    prepared.append((ref,raw,safe))
run=json.loads(prepared[0][1])
if not (run['revision']==REV and run['passed'] and run['tests_run']==76 and run['source_unchanged'] and run['tree_reaped']):
    raise ValueError('Actual exact-clean76PASS/source unchanged/reaped required')
out=ROOT/'status/codex/productization/S12/h16-native-close-source-9c4a741'
create_private_directory(out);art=out/'artifacts';create_private_directory(art)
def digest(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
files=[]
for index,(ref,raw,safe) in enumerate(prepared,1):
    target=art/(f'a{index:04d}'+Path(ref).suffix);write_private_new(target,safe)
    files.append(dict(original_ref=ref,original_hash=digest(raw),retained_ref=target.relative_to(out).as_posix(),
        retained_hash=digest(safe),normalization='SANITIZED_ROOTS_LF_TRAILING_LINE_WHITESPACE_SINGLE_FINAL_NEWLINE'))
doc=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',branch='codex/r7-productization-master-20261002',
    executable_revision=REV,implementation_hash=run['implementation_hash'],scope='NATIVE_CLOSE_OWNER_SOURCE_ONLY',
    source_cases=76,source_commands=1,source_modules=8,failures=0,errors=0,skips=0,source_unchanged=True,tree_reaped=True,
    review='0_CRITICAL_0_IMPORTANT_FINAL_STATIC;EXECUTION_NONE',
    supported=['Actual original issued native position and E5 action/FP04/close-role mechanical binding',
        'Current consent/process/provider/native issuer and cross-role/account-entry claim final guards',
        'Actual scripted-native partial close then explicit original-posId zero, preserves original basis',
        'Historical real entry result at original source anchor; all later actual results retained',
        'Writer transaction inventory fence, delayed older bundle denial, exact idempotent outbox replay after successor process'],
    fixture='ACTUAL_PRODUCT_OWNER_COMPOSITION_FAKE_PROVIDER_TRANSPORT;NO_REAL_ACCOUNT_AUTHORITY',
    original_development_52=dict(cases=52,errors=1,status='FAILED_PRESERVED',
        original_inner_authority_exception='NOT_CAPTURED',source_mutation_overlapped_final_case=True,
        cause='SOURCE_DRIFT_INFERRED_FROM_TIMING_AND_FRESH_WHOLE_SOURCE_HASH_OWNER_CHECK;NOT_PROVEN',
        isolated_same_case=dict(cases=1,failures=0,errors=0,skips=0),qualification_credit='NONE'),
    regression_red=dict(missing_close_projection=1,historical_entry_observation=1,delayed_older_outbox=1,
        account_entry_after_close_claim=1,cross_role_after_close_claim=1,provider_replacement=1),
    whole_H16='INCOMPLETE_ACK_INTENT_STOP_CLEANUP_FUNDING_TRADE_RESULT',
    native_full='NOT_RUN_FOR_THIS_SOURCE',frozen_inventory='STALE_UNTIL_NEXT_FINAL_CANDIDATE',
    qualified_windows_executable='7d821f29837e95e46bcd5fe32f14d536a28c9aa8',master='IN_PROGRESS',
    real_data_cumulative_public_requests=8,real_data_cumulative_public_responses=8,additional_public_requests=0,
    private_requests=0,credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',artifacts=files)
write_private_new(out/'disposition.json',(json.dumps(doc,ensure_ascii=False,indent=2)+'\n').encode())
for row in files:
    if digest((out/row['retained_ref']).read_bytes())!=row['retained_hash']:raise ValueError('Retained evidence mismatch')
progress=ROOT/'coordination/CODEX/PROGRESS.json';state=json.loads(progress.read_bytes())
state.update(executable_revision=REV,candidate_executable_revision=REV)
state['h16_native_close_source_checkpoint']=dict(executable_revision=REV,source_cases=76,
    status='EIGHT_AFFECTED_MODULES_SOURCE_PASS_ONLY',whole_H16=doc['whole_H16'],native='NOT_RUN',
    evidence_ref=(out/'disposition.json').relative_to(ROOT).as_posix())
progress.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
handoff=ROOT/'coordination/CODEX/HANDOFF.md'
prefix=f'''# H16 native close owner source checkpoint — 2026-10-20

Source `{REV}` exact-clean8modules/76cases PASS, source unchanged/tree reaped.
Evidence: `{(out/'disposition.json').relative_to(ROOT).as_posix()}`.
Real owner preparation, final account-entry/cross-role claim/issuer guards and
actual scripted-native partial-to-explicit-same-posId-zero E5 exposure now exist.
Zero remains EXIT_REQUESTED, with no TradeResult/funding/stop-removal inference.
Historical actual entry readback and delayed older outbox regressions repaired.
Final static reviews0C/I, execution NONE. Original52-case development failure
and isolated pass retained: original inner authority exception not captured;
source drift is inferred from overlapping source creation, not proven.
No source writes are allowed during any subsequent source/qualification run.
ACK intent, exact stop cleanup, BROKER_LEDGER funding and final TradeResult
owner flow remain INCOMPLETE. Frozen PQR/examples need regeneration after the
next final source candidate. No native/full qualification credit for this source.
Qualified Windows portable package remains7d821f2. Continue same task/branch:
H16 remaining owner integration, K05 canonical history, report outbox visibility,
semantic/final review. Old-PC/Ubuntu/cloud/policy/real-forward acceptance stays
external or unselected; no requests for old-PC hardware proof now.
Public8/responses8, additional0/private0/credentialsNONE/capitalNONE/LIVENOT_STARTED/GitHubNOT_USED.

'''
handoff.write_text(prefix+handoff.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print(json.dumps(dict(retained=len(files),evidence_ref=(out/'disposition.json').relative_to(ROOT).as_posix())))
