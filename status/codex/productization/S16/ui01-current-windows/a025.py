"""Retain bounded actual UI01 development observations before clean candidate."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from application.qualification import _sanitize
from strategy.v02.capabilities import _revision
def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
def load(path):return json.loads(path.read_bytes())
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
target=ROOT/'status/codex/productization/S16/ui01-current-windows'
target.mkdir(exist_ok=False);bindings=[]
folders=('ui01-projection-apply-first','ui01-backend-first','ui01-original-contract-green',
    'ui01-impacted-backend-first','ui01-frontend-first','ui01-browser-retry01','ui01-browser-retry02',
    'ui01-inventory-freeze-first')
reports={name:load(BASE/name/'checkpoint.json') for name in folders}
assert reports['ui01-backend-first']['exit_code']==1
backend=(BASE/'ui01-backend-first/source.log').read_text(encoding='utf-8')
assert len(re.findall(r'^test_.+\) \.\.\. ok$',backend,re.M))==10
assert 'FAILED (errors=1)' in backend and 'ModuleNotFoundError' in backend
for name,count in (('ui01-original-contract-green',4),('ui01-impacted-backend-first',77)):
    row=reports[name];text=(BASE/name/'source.log').read_text(encoding='utf-8')
    assert row['exit_code']==0 and row['tree_reaped'] and row['source_and_tests_unchanged']
    assert re.search(r'Ran '+str(count)+r' tests in',text) and text.rstrip().endswith('OK')
front=reports['ui01-frontend-first'];assert front['passed'] is False
assert [r['exit_code'] for r in front['commands']]==[0,0,0,0,1]
assert reports['ui01-browser-retry01']['passed'] is False
browser=reports['ui01-browser-retry02'];assert browser['passed'] and browser['awake']['restored']
actual=load(BASE/'ui01-browser-retry02/browser/results.json')['stats']
assert actual['expected']==17 and actual['unexpected']==actual['skipped']==actual['flaky']==0
freeze=reports['ui01-inventory-freeze-first'];assert freeze['passed'] and freeze['added_cases']==10
assert freeze['implementation_hash']==_revision()
refs=[]
for folder in folders:
    parent=BASE/folder
    for name in ('checkpoint.json','source.log','types.log','typecheck.log','unit.log','build.log','browser.log',
                 'before.json','helper.py.unapplied','browser-test-before-selector-repair.ts.unapplied'):
        path=parent/name
        if path.is_file():refs.append(path)
refs += [BASE/'ui01-browser-retry02/browser/results.json',BASE/'run_ui01_frontend_validation.py',
    BASE/'freeze_ui01_inventory_awake.py',Path(__file__),BASE/'test_ui01_observation_contract_aa2d00a_red.py']
for index,path in enumerate(refs,1):
    raw=path.read_bytes();suffix=path.suffix
    safe=raw if suffix=='.png' else ('\n'.join(line.rstrip(' \t') for line in
        _sanitize(raw.decode('utf-8-sig'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').splitlines()).rstrip()+'\n').encode()
    ref='a'+str(index).zfill(3)+suffix;(target/ref).write_bytes(safe)
    assert sha((target/ref).read_bytes())==sha(safe)
    bindings.append(dict(original_ref=path.relative_to(PROJECT).as_posix(),original_hash=sha(raw),
        retained_ref=ref,retained_hash=sha(safe),normalization='PUBLIC_SANITIZATION_LF_TRAILING_WHITESPACE_ONLY' if suffix!='.png' else 'NONE'))
result=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',master='IN_PROGRESS',
    recorded_at=datetime.now(timezone.utc).isoformat(),implementation_hash=_revision(),
    subject='NEW_UI01_SOURCE;FIXED_INVENTORY_DISCOVERY_COMPLETE;NATIVE_QUALIFICATION_NOT_RUN',
    preserved_qualified_executable='aa2d00a4de1147fbc5ff5c4ed14db2f5032b65dd',
    actual_owner_cases_passed=10,original_contract_cases_passed=4,impacted_source_cases_passed=77,
    frontend_unit_cases_passed=18,browser_cases_passed=actual['expected'],
    source_test_invocation_error='Combined first command passed 10 owner cases then failed importing an absolute supplemental path; reran supplemental module by actual PYTHONPATH, 4 passed. Original failure preserved.',
    browser_initial_failure='Long nested local harness scratch failed preparing actual report byte-copy ACK; original log preserved; fresh shorter project-contained scratch prepared all servers.',
    browser_selector_failure='Short scratch run16/17: nested-label exact selector did not resolve real combobox; actual accessibility snapshot showed correct role/name. Replaced only locator with exact combobox role/name; fresh full17/17 passed.',
    independent_review=dict(reviewer='qualification_review',critical=0,important=0,execution='STATIC_ONLY'),
    visual_review='Actual final Settings screenshot inspected; explicit unknowns, source/read times, configured worker count and fixture label visible.',
    local_visual_hash=sha((BASE/'ui01-browser-retry02/browser/ui01-settings-observations.png').read_bytes()),
    fixed_profile=dict(groups=7,commands=freeze['commands'],source_cases=freeze['source_cases'],
        source_files=freeze['source_files'],added_cases=10,removed_cases=0,native_assertions_and_deadlines='UNCHANGED'),
    financial_authority='NONE',ordinary_operator_paper='NOT_STARTED',real_forward='NOT_STARTED',
    public_requests_additional=0,public_requests_cumulative=8,private_requests=0,credentials='NONE',
    next='Commit/push clean candidate; build actual native package; full owning PQR and exact native user-flow/install/recovery/backup verification.',retained_files=bindings)
save(target/'disposition.json',result)
progress=ROOT/'coordination/CODEX/PROGRESS.json';p=load(progress)
p['ui01_current_windows']=dict(status='SOURCE_BACKEND_AND_BROWSER_PASS;NEW_NATIVE_QUALIFICATION_NEXT',
    implementation_hash=_revision(),evidence_ref=(target/'disposition.json').relative_to(ROOT).as_posix(),
    owner_cases=10,contract_cases=4,impacted_cases=77,browser_cases=17,ordinary_operator_paper='NOT_STARTED')
p['next_step']='Commit/push exact clean UI01 candidate; actual native build/full fixed qualification, clean install/headless/ordinary idle/automatic diagnostic/backup. Preserve aa2d PASS separately. Continue remaining semantic Master bindings; external commissioning remains distinct.'
save(progress,p)
handoff=ROOT/'coordination/CODEX/HANDOFF.md';old=handoff.read_text(encoding='utf-8')
handoff.write_text('# UI01 actual source repair complete; new native candidate next\n\n'
    'Applied reviewed closed diagnostic projections and canceled-job filter. Actual10 owner cases, original4 contract cases, impacted77 source cases,18 frontend unit cases and17 full browser cases passed within their recorded scope. Preserved initial invocation/path/selector failures. No native qualification transferred from aa2d. Next clean commit/build/full owning qualification and current user flows; ordinary operator policies remain unselected. Master IN_PROGRESS.\n\n---\n\n'+old,encoding='utf-8',newline='\n')
completion=ROOT/'status/codex/R7_PRODUCTIZATION_MASTER_COMPLETION_20261002.md'
completion.write_text('# Latest UI01 source checkpoint; native qualification next\n\n'
    'The demonstrated diagnostic/canceled-filter omissions are repaired. Actual owner, original RED-to-green, impacted API/process and full browser observations are retained in `productization/S16/ui01-current-windows/disposition.json`. New fixed discovery preserves all prior case order/multiplicity, native assertions/deadlines and toolchains, adding only10 UI01 cases (212commands/2654source cases). Discovery is not execution. New native candidate is still unqualified; aa2d remains the preserved qualified subject. Master IN_PROGRESS.\n\n---\n\n'+completion.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print(json.dumps(dict(retained_files=len(bindings),implementation_hash=_revision(),status=result['subject'])))
