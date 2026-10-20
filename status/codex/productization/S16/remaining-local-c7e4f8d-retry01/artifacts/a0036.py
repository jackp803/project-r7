"""Retain named source-only evidence; preserve the separately qualified ZIP."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import revision_fact,_sanitize
from application.cloud.manifest import parse_manifest,byte_hash
from strategy import parse_strategy_definition
from strategy.v02.capabilities import build_capability_snapshot
REV='c7e4f8df3fd5324d9a25071cf61cf76b1e82fafe'
QUALIFIED='7d821f29837e95e46bcd5fe32f14d536a28c9aa8'
revision_fact(ROOT,REV,False)
changes=subprocess.run(['git','status','--porcelain=v1','--untracked-files=all'],cwd=ROOT,
    check=True,stdout=subprocess.PIPE,text=True).stdout.splitlines()
if any(not line.startswith('?? status/codex/productization/S16/remaining-local-c7e4f8d/') for line in changes):
    raise ValueError('Only preserved first-attempt evidence may be dirty before retention')
run=json.loads((BASE/'remaining-local-c7e4f8d-green/checkpoint.json').read_bytes())
if not (run['revision']==REV and run['passed'] and run['tests_run']==146 and run['source_unchanged'] and run['tree_reaped']):
    raise ValueError('Exact-clean affected-source PASS required')
attempt=sys.argv[1]
if attempt!='retry01':raise ValueError('Explicit preserved retainer retry01 required')
out=ROOT/('status/codex/productization/S16/remaining-local-c7e4f8d-'+attempt);create_private_directory(out)
art=out/'artifacts';create_private_directory(art)
refs=['remaining-local-74934d7-red/checkpoint.json','remaining-local-74934d7-red/source.log',
 'remaining-local-c7e4f8d-green/checkpoint.json','remaining-local-c7e4f8d-green/source.log',
 'run_remaining_local_source.py','cross-immediate-predecessor-green.log',
 'j06-reader-api-development.log','j06-reader-api-development-green.log',
 'j06-deep-reason-red.log','j06-deep-reason-portable-red.log','j06-authoring-development-green.log',
 'authoring-required-examples-development.log','authoring-required-examples-development-retry01.log',
 'trade02-joined-development.log','j06-ui-typecheck.log','j06-ui-unit.log','j06-ui-build.log',
 'j06-source-review.json','j06-source-final-review.json','remaining-source-final-review.json',
 'run_j06_browser.py','j06-browser-development/checkpoint.json','j06-browser-development/browser.log',
 'j06-browser-development/browser/results.json','j06-browser-development/browser/research-failure-history.png',
 'j06-browser-development/browser/health.png','j06-browser-development/browser/supervised-health.png',
 'remaining-source-inventory-generation.log','remaining-source-inventory-build-env-diagnostic.log',
 'remaining-source-inventory-generation-retry01.log',
 'refresh_required_authoring_examples_v1.py','refresh_required_authoring_examples.py',
 'required-authoring-examples-01/execution.json','required-authoring-examples-02/execution.json',
 'required-authoring-examples-03/execution.json','retain_remaining_source_checkpoint.py',
 'h16-close-projection-builder-plan.json']
retained=[]
for index,ref in enumerate(refs,1):
    source=BASE/ref;raw=source.read_bytes();binary=source.suffix=='.png'
    safe=raw if binary else (_sanitize(raw.decode('utf-8'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>')
        .replace(str(PROJECT).replace('\\','/'),'<PROJECT_ROOT>').replace('\r\n','\n').rstrip()+'\n').encode()
    target=art/(f'a{index:04d}'+source.suffix)
    write_private_new(target,safe)
    retained.append(dict(original_ref=ref,retained_ref=target.relative_to(out).as_posix(),
        original_hash=byte_hash(raw),retained_hash=byte_hash(safe),
        normalization='NONE_BINARY' if binary else 'SANITIZED_ROOTS_LF_SINGLE_FINAL_NEWLINE'))
examples={}
for name in ('four-hour','multitimeframe'):
    folder=ROOT/'docs/strategy/authoring-v0.2/examples'/name
    raw=(folder/'strategy.json').read_bytes();strategy=parse_strategy_definition(raw)
    manifest=parse_manifest((folder/'manifest.json').read_bytes());payload=manifest.payloads[0]
    if not (payload.sha256==byte_hash(raw) and payload.byte_length==len(raw)
            and manifest.strategy_content_hash==strategy.content_hash
            and manifest.raw['capability_snapshot_hash']==build_capability_snapshot().snapshot_hash):
        raise ValueError('Current shipped example manifest binding required')
    examples[name]=dict(version=strategy.strategy_version,content_hash=strategy.content_hash,
        manifest_byte_hash=byte_hash((folder/'manifest.json').read_bytes()),current_capability_binding='MATCH',
        source_behavior='BOTH_SIDES_ASOF_AND_ATR_BINDING_TESTED',real_data_research='NOT_RUN',paper='NOT_RUN')
document=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',
    scope='EXACT_CLEAN_AFFECTED_SOURCE_REGRESSIONS_ONLY',executable_revision=REV,
    branch='codex/r7-productization-master-20261002',main_revision='7d1f447c8a9e8b46dc5ecc7bf0a78e1d63680812',
    source_cases=146,source_modules=14,source_failures=0,source_errors=0,source_skips=0,
    source_unchanged=True,tree_reaped=True,full_native_qualification='NOT_RUN_FOR_THIS_REVISION',
    frozen_inventory=dict(groups=7,commands=160,case_executions=2458,source_files=297,execution='NOT_FULLY_EXECUTED'),
    actual_browser=dict(cases=3,passed=3,scope='DIRTY_SOURCE_DEVELOPMENT_EXACT_RECORDED_FILE_HASHES'),
    ui=dict(typecheck='PASS',unit_cases=18,build='PASS'),static_reviews='0_CRITICAL_0_IMPORTANT_EXECUTION_NONE',
    failed_history=dict(retainer_first='remaining-local-c7e4f8d/failure.json;wrong helper dataclass attribute;no product change',
        initial_clean_red=dict(cases=142,failures=6,errors=10),
        deep_reason_native_decoder='TYPED_DENIAL_ALREADY_PASS',
        deep_reason_stdlib_python_decoder_red=dict(cases=1,failures=1,errors=1),
        decoder_fix='RecursionError mapped to typed unavailable; included in exact-clean146PASS',
        test_setup_repairs=['TRADE02 canonicalize before digest','gap JSON array/tuple normalization',
            'authoring behavior import actual position.exit_requests','SQLite fixture connection closed explicitly'],
        inventory_environment='First invocation mistakenly used build venv lacking httpx/jsonschema/numpy; development host retry PASS',
        diagnostic_limit='Combined-loader diagnostic hit module-name collision; not a product or test execution failure'),
    shipped_examples=examples,
    preserved_windows_qualified_executable=QUALIFIED,
    preserved_windows_evidence='status/codex/productization/S12/current-windows-7d821f2/disposition.json',
    preserved_zip_hash='sha256:8ef3e058da61d613bc7cd3488b390252190c224750abc90c1356ca1b8bd7b0a9',
    remaining_local=['H16 native close-to-flat/funding/TradeResult owner integration',
        'K05 sanitized canonical historical summary','CLOUD08 populated visible delivery proof',
        'exact clause disposition and final architecture/security review','new executable full/native qualification for changed source'],
    h16_state_correction='Canonical intermediate state EXIT_REQUESTED; earlier draft EXIT_PENDING is not a valid state',
    real_data=dict(cumulative_actual_public_requests=8,cumulative_actual_public_responses=8,additional_requests=0,
        strategy_version='authoring-example-four-hour@0.2.0',new_0_2_1_research='NOT_RUN'),
    private_requests=0,credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',
    master='IN_PROGRESS',recorded_at=datetime.now(timezone.utc).isoformat(),artifacts=retained)
write_private_new(out/'disposition.json',(json.dumps(document,ensure_ascii=False,indent=2)+'\n').encode())
for item in retained:
    if byte_hash((out/item['retained_ref']).read_bytes())!=item['retained_hash']:raise ValueError('Retained hash changed')
revision_fact(ROOT,REV,False)
progress_path=ROOT/'coordination/CODEX/PROGRESS.json';progress=json.loads(progress_path.read_bytes())
prior=progress.get('qualified_executable_revision')
progress['qualified_executable_revision_history_before_windows_completion']=prior
progress.update(executable_revision=REV,candidate_executable_revision=REV,qualified_executable_revision=QUALIFIED,
    qualified_executable_scope='CURRENT_WINDOWS_FULL_SOFTWARE_ONLY;NO_UBUNTU_REAL_FORWARD_OR_LIVE_CREDIT',
    state='IN_PROGRESS',active_step='S16_H16_CLOSE_OWNER_K05_HISTORY_AND_REMAINING_PRODUCT_ACCEPTANCE',
    next_step='Continue H16 actual native close/funding/TradeResult owner adapter, K05 readonly sanitized history and CLOUD08 populated delivery proof. Preserve qualified7d Windows ZIP; changedc7 source has affected146PASS only, requires later full/native qualification. OldPC/Ubuntu/cloud/formal policies/forward remain external or unselected.')
progress['remaining_local_source_checkpoint']=dict(executable_revision=REV,source_cases=146,
    status='AFFECTED_SOURCE_PASS_ONLY',evidence_ref=(out/'disposition.json').relative_to(ROOT).as_posix(),
    full_native='NOT_RUN',j06_browser_cases=3,ui_unit_cases=18,master='IN_PROGRESS')
progress_path.write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
handoff=ROOT/'coordination/CODEX/HANDOFF.md'
prefix=f'''# Remaining local source checkpoint — 2026-10-20

Same task/branch. Source `{REV}`: exact-clean affected14modules/146cases PASS,
no failures/errors/skips, source unchanged, owned tree reaped. Frozen inventory
2458cases/160commands is not a full execution. J06 source browser3/3, UI18/18,
typecheck/build PASS; static reviews0Critical/0Important, executionNONE.
Retained disposition:
`{(out/'disposition.json').relative_to(ROOT).as_posix()}`.

Current fully qualified Windows executable remains `{QUALIFIED}` and its
immutable ZIP/checksum/clean-install/backup/operations guide. Do not transfer
that native qualification to changed source. Engineering examples0.2.1 have
actual source behavior/intake proof only; public research remains0.2.0 diagnostic.
Public requests cumulative8/responses8, additional0; private0/credentialsNONE/
capitalNONE/LIVENOT_STARTED/GitHubcomputeNOT_USED. MasterIN_PROGRESS.

Next: H16 real native close/funding/TradeResult owner integration, K05 readonly
historical export, CLOUD08 populated delivery visibility, per-clause final
review and a new exact-clean native/full run for the changed executable.
Canonical close intermediate state is `EXIT_REQUESTED`; earlier advisory
`EXIT_PENDING` is invalid wording, not an added state. No guard currently active.
Old target/Ubuntu/cloud commissioning/policy selection/real forward remain open.

'''
handoff.write_text(prefix+handoff.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print(json.dumps(dict(retained=len(retained),revision=REV,evidence_ref=(out/'disposition.json').relative_to(ROOT).as_posix())))
