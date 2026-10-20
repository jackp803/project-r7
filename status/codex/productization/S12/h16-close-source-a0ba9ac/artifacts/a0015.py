"""Named source-only H16 first slice and original failures, no native credit."""
from pathlib import Path
import hashlib,json,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import _sanitize,revision_fact
REV='a0ba9ac41929fa61535ee917624dd145d24f84e0'
revision_fact(ROOT,REV,True)
refs=['h16-close-source-a0ba9ac/checkpoint.json','h16-close-source-a0ba9ac/source.log','run_h16_close_source.py',
    'h16-pure-close-projection-red.log','h16-pure-close-projection-development.log',
    'h16-pure-close-projection-development-retry01.log','h16-close-action-clock-red.log',
    'h16-e4-close-action-clock-red.log','h16-close-clock-development-green.log',
    'h16-pure-close-projection-review.json','h16-pure-close-projection-final-review.json',
    'h16-close-projection-builder-plan.json','h16-close-owner-mechanical-binding-plan.json',
    'cloud08-visible-delivery-plan.json','retain_h16_close_source.py']
prepared=[]
for ref in refs:
    raw=(BASE/ref).read_bytes()
    text=_sanitize(raw.decode('utf-8'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>')
    safe=('\n'.join(line.rstrip() for line in text.splitlines()).rstrip()+'\n').encode()
    prepared.append((ref,raw,safe))
run=json.loads(prepared[0][1])
if not (run['revision']==REV and run['passed'] and run['tests_run']==88 and run['source_unchanged'] and run['tree_reaped']):
    raise ValueError('Actual clean source88PASS required')
out=ROOT/'status/codex/productization/S12/h16-close-source-a0ba9ac';create_private_directory(out)
art=out/'artifacts';create_private_directory(art)
def digest(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
files=[]
for index,(ref,raw,safe) in enumerate(prepared,1):
    target=art/(f'a{index:04d}'+Path(ref).suffix);write_private_new(target,safe)
    files.append(dict(original_ref=ref,original_hash=digest(raw),retained_ref=target.relative_to(out).as_posix(),
        retained_hash=digest(safe),normalization='SANITIZED_ROOTS_LF_TRAILING_LINE_WHITESPACE_SINGLE_FINAL_NEWLINE'))
document=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',executable_revision=REV,
    branch='codex/r7-productization-master-20261002',scope='PURE_E5_ONE_EXPLICIT_CLOSE_SOURCE_ONLY',
    source_cases=88,failures=0,errors=0,skips=0,source_unchanged=True,tree_reaped=True,
    red_missing_module=dict(cases=7,errors=7),intermediate_fixture_error='validator missing lifecycle projection argument;fixed',
    clock_red=dict(pure_cases=1,pure_failures=1,E4_cases=1,E4_subtest_failures=2),
    repair='Original E4 close consumer rejects execution before action.created_at; inclusive creation and original expiry preserved',
    review='0_CRITICAL_0_IMPORTANT_EXECUTION_NONE',
    supported='One original entry and explicit close; cumulative actual partial/full fills; signed native magnitude; source-basis preservation; existing EXIT_REQUESTED lifecycle/binding',
    source_fixture='PAPER_OWNER_SOURCE_FIXTURE;NO_PRODUCT_FAKE_NATIVE_OWNER_CREDIT',
    whole_H16='INCOMPLETE_NATIVE_CLOSE_OWNER_FUNDING_TRADE_RESULT_AND_PROTECTION_CLEANUP',
    native_full='NOT_RUN_FOR_THIS_SOURCE',frozen_inventory='STALE_PENDING_NEXT_FINAL_CANDIDATE',
    preserved_qualified_windows='7d821f29837e95e46bcd5fe32f14d536a28c9aa8',master='IN_PROGRESS',
    remaining_local=['Native close ownership/mechanical adapter and final cross-role claim guard',
        'Actual native close readback/flat/funding/TradeResult/recovery','K05 canonical sanitized history','CLOUD08 visible delivery proof'],
    real_data_cumulative_public_requests=8,real_data_cumulative_public_responses=8,additional_public_requests=0,
    private_requests=0,credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',artifacts=files)
write_private_new(out/'disposition.json',(json.dumps(document,ensure_ascii=False,indent=2)+'\n').encode())
for item in files:
    if digest((out/item['retained_ref']).read_bytes())!=item['retained_hash']:raise ValueError('Retained hash mismatch')
progress=ROOT/'coordination/CODEX/PROGRESS.json';v=json.loads(progress.read_bytes())
v.update(executable_revision=REV,candidate_executable_revision=REV)
v['h16_close_source_slice']=dict(executable_revision=REV,status='SOURCE88PASS_ONLY;WHOLE_H16_INCOMPLETE',
    evidence_ref=(out/'disposition.json').relative_to(ROOT).as_posix(),native='NOT_RUN',frozen_inventory='STALE_PENDING_NEXT_CANDIDATE')
progress.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
handoff=ROOT/'coordination/CODEX/HANDOFF.md'
prefix=f'''# H16 first E5 close source slice — 2026-10-20

Source `{REV}` exact-clean8modules/88cases PASS, unchanged/reaped, static review0C/I.
Original source RED and E4 future-action RED retained; original close consumer
now denies execution before action creation. Existing lifecycle and TradeResult
semantics unchanged. Evidence: `{(out/'disposition.json').relative_to(ROOT).as_posix()}`.
Pure source fixtures only: native close owner/flat/funding/TradeResult and stop
cleanup integration remain INCOMPLETE. No H16 or native qualification PASS.
Frozen PQR inventory is stale until the next final candidate regeneration.
Qualified Windows delivery remains7d821f2; no active guarded run.
Next implement actual native close owner/mechanical profile plus cross-role
claim guard; K05/CLOUD08 and final clause review remain. Public8/responses8,
additional0/private0/credentialsNONE/capitalNONE/LIVENOT_STARTED/GitHubNOT_USED.

'''
handoff.write_text(prefix+handoff.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print(json.dumps(dict(retained=len(files),evidence_ref=(out/'disposition.json').relative_to(ROOT).as_posix())))
