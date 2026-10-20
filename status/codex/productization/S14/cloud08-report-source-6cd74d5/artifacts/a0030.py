"""Retain exact source/API/local-copy browser proof, not real cloud/native."""
from pathlib import Path
import hashlib,json,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import _sanitize,revision_fact
REV='6cd74d59952c160bfb1d91fb49c966d3df92b0b7';revision_fact(ROOT,REV,True)
refs=['cloud08-report-source-6cd74d5/checkpoint.json','cloud08-report-source-6cd74d5/source.log','run_report_history_source.py',
    'cloud08-report-history-reader-red.log','cloud08-report-history-reader-green01.log','cloud08-report-history-api-red.log',
    'cloud08-report-history-green02.log','cloud08-report-history-review-red.log','cloud08-report-history-green03.log',
    'cloud08-report-history-readonly-design-20261020.json','cloud08-report-history-source-review.json',
    'cloud08-report-history-source-final-review.json','cloud08-report-history-source-ui-final-review.json',
    'cloud08-report-ui-contract.log','cloud08-report-ui-typecheck.log','cloud08-report-ui-build.log','cloud08-report-ui-tests.log',
    'run_report_history_browser.py','cloud08-report-browser-dev01/checkpoint.json','cloud08-report-browser-dev01/browser.log',
    'cloud08-report-browser-dev01/report.config.mjs','cloud08-report-browser-dev02/checkpoint.json',
    'cloud08-report-browser-dev02/browser.log','cloud08-report-browser-dev02/results.json','cloud08-report-browser-dev02/report.config.mjs',
    *['cloud08-report-browser-dev02/browser/'+name for name in ('paper-report-history.png','research-report-CLOUD_ACKNOWLEDGED.png',
        'research-report-CONFLICT.png','research-report-LOCAL_STAGED.png')],'retain_report_history_source.py']
def digest(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
prepared=[]
for ref in refs:
    raw=(BASE/ref).read_bytes()
    if Path(ref).suffix=='.png':safe=raw
    else:
        value=_sanitize(raw.decode('utf-8'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>')
        safe=('\n'.join(line.rstrip() for line in value.splitlines()).rstrip()+'\n').encode()
    prepared.append((ref,raw,safe))
run=json.loads(prepared[0][1]);browser=json.loads((BASE/'cloud08-report-browser-dev02/checkpoint.json').read_bytes())
review=json.loads((BASE/'cloud08-report-history-source-ui-final-review.json').read_bytes())
if not (run['executable_revision']==REV and run['passed'] and run['tests_run']==53 and browser['passed']
        and browser['source_unchanged'] and browser['tree_reaped'] and review['counts']=={'Critical':0,'Important':0}):
    raise ValueError('Actual clean source53/local browser2/static0C/I required')
for ref,expected in browser['after'].items():
    if digest((ROOT/ref).read_bytes())!=expected:raise ValueError('Browser input drift')
out=ROOT/'status/codex/productization/S14/cloud08-report-source-6cd74d5';create_private_directory(out)
art=out/'artifacts';create_private_directory(art);items=[]
for number,(ref,raw,safe) in enumerate(prepared,1):
    target=art/(f'a{number:04d}'+Path(ref).suffix);write_private_new(target,safe)
    items.append(dict(original_ref=ref,original_hash=digest(raw),retained_ref=target.relative_to(out).as_posix(),retained_hash=digest(safe),
        normalization='NONE_BINARY' if Path(ref).suffix=='.png' else 'SANITIZED_ROOTS_LF_TRAILING_WHITESPACE_SINGLE_FINAL_NEWLINE'))
document=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',executable_revision=REV,
    implementation_hash=run['implementation_hash'],scope='CLOUD08_REPORT_HISTORY_SOURCE_API_AND_LOCAL_COPY_BROWSER_ONLY',
    source_cases=53,failures=0,errors=0,skips=0,clean_source_unchanged=True,owned_tree_reaped=True,
    browser_cases=2,browser_scope='DEVELOPMENT_EXACT_RECORDED_FILE_HASHES_IDENTICAL_TO_EXECUTABLE_COMMIT',
    RED=dict(reader_missing_module='2_ERRORS',api_missing_ports='2_ERRORS',review_counterexamples='4_CASES_2_FAILURES_2_ERRORS'),
    browser_first_failure=dict(stage='FIXTURE_SERVER_STARTUP_BEFORE_BROWSER_CASES',passed=False,tree_reaped=True,
        observed_path_characters=[263,265],actual_failure='ACTUAL_BYTE_READBACK_ACK_REQUIRED',
        root_cause='LONG_SCRATCH_PATH_ATTRIBUTION_INFERRED_NOT_PROVEN;ORIGINAL_INNER_BRIDGE_ERROR_NOT_CAPTURED',
        repair='EXPLICIT_FRESH_SHORT_FIXTURE_SCRATCH_INSIDE_PROJECT;NO_PRODUCT_GUARD_CHANGE'),
    actual_flow='Authenticated real research queue/owner and Paper runtime checkpoints produce reports. Actual SyncedFolder staging and RcloneCloudTransport/RcloneBridge LocalFakeRclone byte-copy produce ACK/CONFLICT/LOCAL_STAGED. Outage source tests produce UNAVAILABLE. No handcrafted ACK or terminal owner rows for positive credit.',
    readonly='Live-WAL mode=ro; exact owned schema/namespace/row and bundle hashes/lineage; no RW factory, migrations on disk, worker, report regeneration, lease attachment or transport in GET. SQL metadata preflight, bounded pages and lazy reports.',
    historical_limits='Queue owner pointer/outcome/available frozen subject-family-seed verified; historical policy path-to-content mapping cannot independently be reconstructed from retained inputs. No current files/resolver read, policy requalification or authority grant.',
    UI='Historical states, operation/report/artifact hashes, original queued time and Paper checkpoint/producer; historical ACK distinct from current cloud connectivity; explicit FIXTURE/local-copy label.',
    ui_tests=18,typecheck='PASS',build='PASS',independent_review='0_CRITICAL_0_IMPORTANT_EXECUTION_NONE',
    visual_inspection='ACTUAL_PAPER_THREE_STATE_AND_RESEARCH_ACK_SCREENSHOTS_INSPECTED',
    real_cloud='NOT_RUN',native_full='NOT_RUN_FOR_THIS_SOURCE',frozen_inventory='STALE_PENDING_FINAL_CANDIDATE',
    preserved_qualified_windows='7d821f29837e95e46bcd5fe32f14d536a28c9aa8',master='IN_PROGRESS',
    public_requests_cumulative=8,public_responses_cumulative=8,additional_public_requests=0,private_requests=0,
    credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',artifacts=items)
write_private_new(out/'disposition.json',(json.dumps(document,ensure_ascii=False,indent=2)+'\n').encode())
for item in items:
    if digest((out/item['retained_ref']).read_bytes())!=item['retained_hash']:raise ValueError('Retained mismatch')
progress=ROOT/'coordination/CODEX/PROGRESS.json';value=json.loads(progress.read_bytes())
value.update(executable_revision=REV,candidate_executable_revision=REV,
    active_step='S14_REPORT_HISTORY_SOURCE_PASS_CONTINUE_K05_AND_H16_ACCOUNTING',
    next_step='Continue K05 readonly canonical history/privacy and H16 owned stop cleanup, source-owned BROKER_LEDGER funding and TradeResult. Keep qualified Windows7d. Final inventory/examples/full/native after source settles; oldPC/Ubuntu/cloud/policies/forward remain external or unselected.')
value['cloud08_report_history_checkpoint']=dict(executable_revision=REV,source_cases=53,browser_cases=2,
    status='SOURCE_API_LOCAL_COPY_BROWSER_PASS_ONLY',real_cloud='NOT_RUN',native_full='NOT_RUN',
    evidence_ref=(out/'disposition.json').relative_to(ROOT).as_posix())
progress.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
prefix=f'''# Research/Paper report delivery history source checkpoint — 2026-10-20

Source `{REV}` exact-clean5modules/53cases PASS, unchanged/reaped.
Actual localhost browser2/2 PASS with identical recorded source hashes;
UI18tests/typecheck/build PASS, final static review0C/I (execution NONE).
Evidence: `{(out/'disposition.json').relative_to(ROOT).as_posix()}`.
Authenticated leaf GETs use protected live-WAL RO stores and original report/
bundle/owner/checkpoint/producer bindings, no owner/writer/worker/transport.
Actual owner reports and local-copy byte-readback bridge produce visible
LOCAL_STAGED/CLOUD_ACKNOWLEDGED/CONFLICT; outage tests preserve UNAVAILABLE.
Queued time is not ACK time, historical ACK is not current cloud health.
Review counterexamples4=2fail/2error fixed; initial reader/API REDs retained.
First browser startup ACK failed with263/265char paths; short PROJECT scratch
retry passed; longpath causality inferred, inner bridge error not captured.
Historical policy-path reconstruction remains unproven; no authority upgrade.
This is source/API/local-copy browser proof, no real cloud/native/full credit.
Qualified Windows ZIP remains7d821f2. Master IN_PROGRESS, original task/branch.
Next: K05 readonly history/privacy; H16 exact stop cleanup, BROKER_LEDGER source
and TradeResult; then regenerate final inventory/examples/full/native checks.
Public cumulative8/responses8; additional0/private0/credentialsNONE/capitalNONE/
LIVENOT_STARTED/GitHubNOT_USED. TargetPC/Ubuntu/cloud/policies/forward still
external or unselected. Preserve every prior result and failed run.

'''
for relative in ('coordination/CODEX/HANDOFF.md','status/codex/R7_PRODUCTIZATION_MASTER_COMPLETION_20261002.md'):
    path=ROOT/relative;path.write_text(prefix+path.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print(json.dumps(dict(retained=len(items),evidence_ref=(out/'disposition.json').relative_to(ROOT).as_posix())))
