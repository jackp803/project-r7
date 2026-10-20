"""Retain exact cleanup evidence after successful clean source regression."""
from pathlib import Path
import hashlib,json,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import _sanitize,revision_fact
REV=sys.argv[1];revision_fact(ROOT,REV,True)
prefix='h16-stop-cleanup-source-'+REV[:7]
refs=[prefix+'/checkpoint.json',prefix+'/source.log','run_h16_stop_cleanup_source.py',
    'h16-protected-close-fixture-first.log','h16-protected-close-fixture.py.unapplied',
    'h16-stop-cleanup-owner-red.log','h16-stop-cleanup-owner-green01.log','h16-stop-cleanup-owner-green02.log',
    'h16-stop-cleanup-expiry-red.log','h16-stop-cleanup-expiry-successor-green01.log',
    'h16-stop-cleanup-owner-review-initial.json','h16-stop-cleanup-owner-review-final.json',
    'h16-stop-cleanup-owner-review-final-retry01.json','h16-stop-cleanup-precommit-whitespace.json',
    'h16-cleanup-successor-fixture-plan-20261020.json','h16-finalizer-exact-seam-plan-20261020.json',
    'h16-owned-stop-finalization-plan-20261020.json','retain_h16_stop_cleanup_source.py']
refs.extend(['h16-finalization-root-decisions-20261020.json','test_trading_finalization_v02.py.initial.unapplied',
    'test_trading_finalization_v02.py.unapplied','h16-finalizer-test-recipe-20261020.json',
    's16-current-local-gap-reconciliation-20261020.json','plat08-portable-upgrade-removal-plan-20261020.json',
    'f04-paper-risk-reject-test.py.unapplied','f04-paper-risk-reject-test-recipe.json',
    'i04-j03-two-version-root-plan-20261020.json','h01-j10-l03-architecture-review-7de014e.json'])
refs.append('h16-stop-cleanup-unique-fixture-review-20261020.json')
refs.extend(['h16-cleanup-partition-plan-20261020.json','f04-paper-risk-reject-test.py.initial.unapplied'])
refs.append('partition_h16_cleanup_tests.py')
def digest(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
prepared=[]
for ref in refs:
    raw=(BASE/ref).read_bytes()
    value=_sanitize(raw.decode('utf-8'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>')
    safe=('\n'.join(line.rstrip() for line in value.splitlines()).rstrip()+'\n').encode()
    prepared.append((ref,raw,safe))
run=json.loads(prepared[0][1]);review_bytes=(BASE/'h16-stop-cleanup-owner-review-final-retry01.json').read_bytes()
if hashlib.sha256(review_bytes).hexdigest()!='c00e4267598d2d9a9a0284d39116d5af7379c0a0d255cc973799b3bc2fcb9ba7':
    raise ValueError('Exact retained nine-file review bytes required before interpreting paths')
review=json.loads(review_bytes)
if not (run['executable_revision']==REV and run['passed'] and run['tests_run']==158 and
        len(run['modules'])==16 and run['source_unchanged'] and run['tree_reaped'] and
        review['critical']==0 and review['important']==0):raise ValueError('Actual clean158 and final static0C/I required')
for ref,expected in review['subject_hashes'].items():
    if hashlib.sha256((ROOT/ref).read_bytes()).hexdigest()!=expected:raise ValueError('Review subject changed')
out=ROOT/'status/codex/productization/S12'/prefix;create_private_directory(out)
art=out/'artifacts';create_private_directory(art);items=[]
for number,(ref,raw,safe) in enumerate(prepared,1):
    target=art/(f'a{number:04d}'+Path(ref).suffix);write_private_new(target,safe)
    items.append(dict(original_ref=ref,original_hash=digest(raw),retained_ref=target.relative_to(out).as_posix(),
        retained_hash=digest(safe),normalization='SANITIZED_ROOTS_LF_TRAILING_WHITESPACE_SINGLE_FINAL_NEWLINE'))
document=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',executable_revision=REV,
    implementation_hash=run['implementation_hash'],scope='FIXTURE_OWNED_STOP_CLEANUP_AND_AFFECTED_OWNERS_SOURCE_ONLY',
    source_modules=16,source_cases=158,new_cleanup_cases=11,genuine_protected_close_cases=1,
    failures=0,errors=0,skips=0,clean_source_unchanged=True,owned_tree_reaped=True,
    independent_review='CLEANUP_REPAIR_0C_0I_BEFORE_LATER_COVERAGE_FINDING;H01_0C_1I;REVIEWER_EXECUTION_NONE',
    open_cleanup_finding='STOP-CLEANUP-NATIVE-UNIQUE-FK-MASK: alternative replacement test uses missing FK. Production SQL guard has no observed defect; strengthen valid existing claim fixture after this frozen run. No independent native-unique regression credit yet.',
    prospective_qualification_issue='Single cleanup module observed9cases1864.525s exceeds fixed900s source member limit. No actual owning failure asserted. After guard, split existing11cases across bounded files with non-TestCase helper and unchanged900s limit; regenerate inventory for final subject. Future partitions not executed.',
    actual_flow='Same actual FakeProductProvider performs fully FILLED entry, actual E5 protection and native active inventory to OPEN_PROTECTED, original single close, partial and same-position native zero. Original issued current reads and complete single-object inventory authorize one exact owned-stop cancel only after original flat.',
    durability='Immutable E6 local cleanup phase claim before cancel; duplicate or lost ACK never resends, creates terminality or alters original canonical graph. Original targeted CANCELED is separately observed by existing reconciliation.',
    recovery='Actual new admission/capability/translator/provider/journal handles and new process instance advance E6 dispatch lease to generation2, preserving accepted E7 release generation1. Only original target GET; old lease denied; no old issued observations or new cancel.',
    fences='Original healthy protection/entry/close/plan/action/native identity and full canonical graph, all account claims, exact issuer/metadata/account windows and final provider guard. Actual independent connection appends before and after cleanup claim block effects. UPDATE/DELETE/same-primary-key REPLACE deny with recursive_triggers OFF. Alternative-primary-key test currently has missing-FK mask and earns no independent native-unique guard credit.',
    freshness_correction='Initial static0C/1I and actual one-test failure show source4.9s to5.1s during actual POST final guard still sent one fake cancel. Final post-scan issuer/window/proof fence preserves existing5s limits, leaves durable unresolved claim and sends zero cancels. Metadata scheduled changes/age are checked by existing capability owner. Controlled source clocks establish no native hard deadline.',
    corrections=['Original missing cleanup method RED1error, then core1PASS and development9PASS. Original joined fixture assertions compare exact Decimal quantities rather than string formatting.',
        'Initial static review finding and actual expiry RED retained; no gate/TTL weakening or new permit. Successor process and accepted release generation are explicitly distinct.'],
    H16_complete='NOT_CLAIMED_TRADE_RESULT_AND_JOINED_FINALIZATION_PENDING',genuine_closed_dispatch='PENDING',
    K05_acceptance='NOT_CLAIMED',actual_production_cleanup='UNSUPPORTED_NOT_CALLED',
    actual_production_ledger='UNSUPPORTED_NOT_CALLED',native_full='NOT_RUN_FOR_THIS_SOURCE',real_cloud='NOT_RUN',
    remaining='First strengthen alternate-primary-key native-unique REPLACE fixture with valid original claimedENTRY key and focused actual denial/oracle proof; preserve current158 results and original static review. Then canonical allocated funding before terminal stop reconciliation; fresh complete terminal target/inventory/native-zero evidence then real E5 TradeResult/CLOSED/binding with immutable replay. Join genuine closed dispatch K05 positive. H01 static Important: formal E2-driven TradingService runner absent in enumerated scope; normal Paper and readonly Shadow remain separate. Bind valid clauses first, complete missing F04/I04/J03/portable upgrade/audits, then final inventory/examples/full/native qualification.',
    frozen_inventory='STALE_PENDING_FINAL_CANDIDATE',preserved_qualified_windows='7d821f29837e95e46bcd5fe32f14d536a28c9aa8',
    master='IN_PROGRESS',public_requests_cumulative=8,public_responses_cumulative=8,additional_public_requests=0,
    private_requests=0,credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',artifacts=items)
write_private_new(out/'disposition.json',(json.dumps(document,ensure_ascii=False,indent=2)+'\n').encode())
for item in items:
    if digest((out/item['retained_ref']).read_bytes())!=item['retained_hash']:raise ValueError('Retained mismatch')
evidence=(out/'disposition.json').relative_to(ROOT).as_posix()
progress=ROOT/'coordination/CODEX/PROGRESS.json';value=json.loads(progress.read_bytes())
value.update(executable_revision=REV,candidate_executable_revision=REV,active_step='H16_SOURCE158_PASS_STRENGTHEN_NATIVE_UNIQUE_FIXTURE_THEN_FINALIZATION',
    next_step='Partition slow cleanup11 across existing perfile900s qualification mechanism without dropping cases or raising limits. Strengthen masked alternative-native-unique test with valid claimedENTRY key and actual denial/oracle; fresh review. Then genuine funded closed ProductDispatch/E5 finalization/replay/K05positive, H01formalrunner and otherlocalclauses. Preserve qualified Windows7d; final inventory/examples/full/native pending.')
value['h16_owned_stop_cleanup_checkpoint']=dict(executable_revision=REV,status='SOURCE_TESTS_PASS_WITH_KNOWN_COVERAGE_FIXTURE_GAP',source_modules=16,source_cases=158,
    cleanup_cases=11,genuine_protected_close_cases=1,H16_acceptance='NOT_CLAIMED',evidence_ref=evidence)
value['h01_formal_trading_runner_gap']=dict(status='IMPORTANT_UNFINISHED_LOCAL_INTEGRATION',reviewed_revision=REV,
    review_ref=evidence+'#artifacts',normal_paper='SEPARATE_EXISTING_FORMAL_PATH',live='NOT_STARTED')
progress.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
prefix_text=f'''# H16 exact-owned stop cleanup source checkpoint — 2026-10-20

Source `{REV}` exact-clean16modules/158cases PASS, unchanged/reaped.
Evidence: `{evidence}`.
Same actual FakeProductProvider performs full entry, genuine E5 protection and
active native inventory, single close/partial/zero, then one exact owned-stop
cancel after immutable local claim. ACK/lost ACK never proves terminality or
permits resend. Targeted CANCELED is actual original reconcile; no result/CLOSED.
Actual successor process/new issuer owners and handles advance E6 lease2 while
accepted E7 release generation remains1; original GET only, old lease denied.
Initial static0C/1I and actual expiry RED expose a post-scan freshness gap.
Final cache/issuer/metadata/proof/window fence preserves5s, keeps unresolved
claim and zero cancel calls; repair static0C/I execution NONE. Later independent
coverage review0C/1I finds alternate-native-unique REPLACE fixture has a missing
FK mask. Production SQL guard has no observed defect; strengthen to real claimed
ENTRY key and prove focused oracle next. Original158 results/reviews preserved;
no independent native-unique regression credit yet. Actual independent connection
append at both boundaries and same-primary-key immutable SQL guards pass.
Observed development9takes1864.525s exceeds fixed900s per source-member limit;
this source regression does not earn PQR credit. Next split all11existingcases
across bounded files/shared non-TestCase helper, preserving every scenario and
unchanged900s deadline; actual partition timings/final inventory still pending.
All failures and original draft/plan artifacts retained with no plan credit.
H16/K05 unfinished: canonical funding before terminal stop, fresh terminal
inventory/native zero, E5 TradeResult/CLOSED/binding and durable crash replay.
Bounded static H01 review0C/1I finds no formal E2-driven TradingService runner
in enumerated265 src/tools files. Normal Paper and readonly Shadow retain
separate supported paths; H01 integration remains local work, not authority wait.
Production cleanup/ledger unsupported/not called. Final inventory/examples/full/
native pending for later source; Windows qualified ZIP7d remains preserved.
Master IN_PROGRESS, original task/branch; public8/responses8/additional0/private0,
credentialsNONE/capitalNONE/LIVENOT_STARTED/GitHubNOT_USED. Old target/Ubuntu/
cloud/policies/forward external or unselected, no wait for independent local work.

'''
for relative in ('coordination/CODEX/HANDOFF.md','status/codex/R7_PRODUCTIZATION_MASTER_COMPLETION_20261002.md'):
    path=ROOT/relative;path.write_text(prefix_text+path.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print(json.dumps(dict(retained=len(items),evidence_ref=evidence)))
