"""Retain actual intake delivery source/browser evidence, no real cloud claim."""
from pathlib import Path
import hashlib,json,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import _sanitize,revision_fact
REV='32d846d968c45c41471f1ca23cb9f2a87d33d36a';revision_fact(ROOT,REV,True)
refs=['cloud08-source-32d846d/checkpoint.json','cloud08-source-32d846d/source.log','run_cloud08_source.py',
 'cloud08-api-delivery-development.log','cloud08-api-delivery-development-retry01.log','cloud08-api-bridge-development-green.log',
 'cloud08-ui-typecheck.log','cloud08-ui-build.log','cloud08-visible-delivery-final-review.json',
 'run_cloud08_browser_red.py','cloud08-browser-red/checkpoint.json','cloud08-browser-red/browser.log',
 'cloud08-browser-red/browser/results.json','run_cloud08_browser_green.py',
 'cloud08-browser-green/checkpoint.json','cloud08-browser-green/browser.log',
 'cloud08-browser-green/browser/results.json','cloud08-browser-green/browser/cloud-delivery-states.png','retain_cloud08_source.py']
prepared=[]
for ref in refs:
    raw=(BASE/ref).read_bytes()
    if Path(ref).suffix=='.png':safe=raw
    else:
        text=_sanitize(raw.decode('utf-8'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>')
        safe=('\n'.join(line.rstrip() for line in text.splitlines()).rstrip()+'\n').encode()
    prepared.append((ref,raw,safe))
run=json.loads(prepared[0][1]);browser=json.loads((BASE/'cloud08-browser-green/checkpoint.json').read_bytes())
if not (run['revision']==REV and run['passed'] and run['tests_run']==35 and browser['passed'] and browser['source_unchanged'] and browser['tree_reaped']):
    raise ValueError('Actual source35 and bounded browser PASS required')
out=ROOT/'status/codex/productization/S14/cloud08-source-32d846d';create_private_directory(out)
art=out/'artifacts';create_private_directory(art)
def digest(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
items=[]
for index,(ref,raw,safe) in enumerate(prepared,1):
    target=art/(f'a{index:04d}'+Path(ref).suffix);write_private_new(target,safe)
    items.append(dict(original_ref=ref,original_hash=digest(raw),retained_ref=target.relative_to(out).as_posix(),retained_hash=digest(safe),
        normalization='NONE_BINARY' if Path(ref).suffix=='.png' else 'SANITIZED_ROOTS_LF_TRAILING_WHITESPACE_SINGLE_FINAL_NEWLINE'))
document=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',executable_revision=REV,
    scope='INTAKE_DELIVERY_VISIBILITY_SOURCE_AND_LOCAL_COPY_BROWSER_ONLY',source_cases=35,failures=0,errors=0,skips=0,
    clean_source_unchanged=True,owned_tree_reaped=True,browser_cases=4,browser_scope='DEVELOPMENT_EXACT_RECORDED_FILE_HASHES',
    browser_red=dict(cases=1,failures=1,trigger='LOCAL_STAGED lacked visible explanation/hash'),
    api_first_error='Fixture treated actual dict row as dataclass; corrected, original failure retained',
    actual_flow='Actual authenticated intake; Publisher stages3receipts; RcloneCloudTransport/RcloneBridge local fake byte-readback ACK1; corrupt readback yields actual CONFLICT1; LOCAL_STAGED1 remains',
    UI='Raw persisted state and available bundle hash plus Traditional Chinese meaning; explicit FIXTURE local-copy disclosure; no invented ACK clock',
    independent_review='0_CRITICAL_0_IMPORTANT_EXECUTION_NONE',visual_inspection='ACTUAL_SCREENSHOT_INSPECTED',
    real_cloud='NOT_RUN',report_outbox_delivery_visibility='NOT_IMPLEMENTED_BY_THIS_SLICE',native_full='NOT_RUN_FOR_THIS_SOURCE',
    frozen_inventory='STALE_PENDING_NEXT_FINAL_CANDIDATE',shipped_example_manifests='REGENERATE_FOR_FINAL_CAPABILITY_SNAPSHOT',
    preserved_qualified_windows='7d821f29837e95e46bcd5fe32f14d536a28c9aa8',master='IN_PROGRESS',
    public_requests_cumulative=8,public_responses_cumulative=8,additional_public_requests=0,private_requests=0,
    credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',artifacts=items)
write_private_new(out/'disposition.json',(json.dumps(document,ensure_ascii=False,indent=2)+'\n').encode())
for item in items:
    if digest((out/item['retained_ref']).read_bytes())!=item['retained_hash']:raise ValueError('Retained mismatch')
progress=ROOT/'coordination/CODEX/PROGRESS.json';v=json.loads(progress.read_bytes())
v.update(executable_revision=REV,candidate_executable_revision=REV)
v['cloud08_visible_intake_checkpoint']=dict(executable_revision=REV,source_cases=35,browser_cases=4,
    status='LOCAL_INTAKE_DELIVERY_SOURCE_BROWSER_PASS_ONLY',real_cloud='NOT_RUN',report_delivery='UNFINISHED',
    evidence_ref=(out/'disposition.json').relative_to(ROOT).as_posix())
progress.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
prefix=f'''# Actual intake delivery visibility source checkpoint — 2026-10-20

Source `{REV}` exact-clean35cases PASS, unchanged/reaped. Actual local-copy
browser4/4 PASS after retained missing-label RED1; typecheck/build PASS and
static review0C/I. Actual Publisher/bridge produced stage, byte-verified ACK,
and wrong-readback CONFLICT; UI preserves states/hash and FIXTURE disclosure.
Evidence: `{(out/'disposition.json').relative_to(ROOT).as_posix()}`.
This proves intake-delivery source/UI only. Realcloud NOT_RUN; report-outbox
visibility remains unfinished. Source candidate needs regenerated inventory,
current-capability example manifests and later full/native qualification.
Qualified Windows ZIP remains7d821f2. Same task/branch; Master IN_PROGRESS.
Next: H16 native close owner, cross-role duplicate-claim final guard,
native flat/funding/TradeResult/stop cleanup, K05 readonly reporting and final
clause review. Public cumulative8/responses8; additional0/private0/credentialsNONE/
capitalNONE/LIVENOT_STARTED/GitHubNOT_USED. No active guarded run.

'''
handoff=ROOT/'coordination/CODEX/HANDOFF.md';handoff.write_text(prefix+handoff.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
master=ROOT/'status/codex/R7_PRODUCTIZATION_MASTER_COMPLETION_20261002.md'
master.write_text(prefix+master.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print(json.dumps(dict(retained=len(items),evidence_ref=(out/'disposition.json').relative_to(ROOT).as_posix())))
