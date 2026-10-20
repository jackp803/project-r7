"""Retain actual F04/I04/J03 source flows; no native or financial activation credit."""
from pathlib import Path
import hashlib,json,subprocess,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import _sanitize,revision_fact
from strategy.v02.capabilities import _revision
REV='41ade60cea0ebb49a19b256be5a3808fcc07e163';revision_fact(ROOT,REV,True)
api='h16-finalization-f04-i04-api-'+REV[:7];browser='i04-j03-two-version-browser-source-'+REV[:7]
a=json.loads((BASE/api/'checkpoint.json').read_bytes());b=json.loads((BASE/browser/'checkpoint.json').read_bytes())
assert a['passed'] and a['tests_run']==2 and len(a['modules'])==2 and a['source_and_tests_unchanged']
assert b['passed'] and b['browser_cases']==1 and b['source_and_tests_unchanged']
for run in (a,b):assert run['executable_revision']==REV and run['implementation_hash']==_revision()
assert all(r['tree_reaped'] and r['passed'] for r in a['results']) and all(r['tree_reaped'] and r['exit_code']==0 for r in b['commands'])
review_ref='f04-i04-j03-source-review-20261020.json';review=json.loads((BASE/review_ref).read_bytes())
assert review['critical']==review['important']==0 and len(review['subject_hashes'])==6
for ref,wanted in review['subject_hashes'].items():assert hashlib.sha256((ROOT/ref).read_bytes()).hexdigest()==wanted
refs=[api+'/checkpoint.json',browser+'/checkpoint.json',browser+'/build.log',browser+'/browser.log',browser+'/two-version.config.mts',browser+'/browser-artifacts/results.json',review_ref,'run_finalization_exact_source.py','run_finalization_development_v02.py','run_two_version_browser_development.py','run_two_version_browser_exact.py','f04-paper-risk-reject-development/checkpoint.json','f04-paper-risk-reject-development/source.log','i04-two-version-api-development/checkpoint.json','i04-two-version-api-development/source.log','i04-j03-two-version-browser-development/checkpoint.json','i04-j03-two-version-browser-development/browser.log','i04-j03-two-version-browser-development/build.log','h16-finalization-f04-paper-893600b/checkpoint.json','h16-finalization-f04-paper-893600b/001.log','f04-paper-risk-reject-test.py.unapplied','i04-j03-two-version-draft-recipe-20261020.json','i04-j03-two-version-root-plan-20261020.json','h01-entry-root-design-20261020.json','h01-entry-root-design-20261020.initial.json','h01-entry-design-independent-review-20261020.json','retain_f04_i04_j03_flows.py']
for row in a['results']:
    ref=api+'/'+row['log_ref'];assert 'sha256:'+hashlib.sha256((BASE/ref).read_bytes()).hexdigest()==row['log_hash'];refs.append(ref)
images=sorted((BASE/browser/'browser-artifacts').glob('two-versions-selected-*.png'));assert len(images)==3
image_comparison=[]
for path in images:
    refs.append(path.relative_to(BASE).as_posix());dev=BASE/'i04-j03-two-version-browser-development/browser-artifacts'/path.name
    image_comparison.append(dict(file=path.name,identical_to_visually_inspected_development=dev.read_bytes()==path.read_bytes()))
refs=list(dict.fromkeys(refs));prepared=[]
for ref in refs:
    raw=(BASE/ref).read_bytes()
    if Path(ref).suffix=='.png':safe=raw
    else:
        safe=_sanitize(raw.decode('utf-8'),ROOT)
        for path,label in ((ROOT,'<SOURCE_ROOT>'),(PROJECT,'<PROJECT_ROOT>'),(Path.home(),'<HOME>')):
            for spelling in (str(path),path.as_posix(),str(path).replace('\\','\\\\')):safe=safe.replace(spelling,label)
        safe=('\n'.join(line.rstrip() for line in safe.splitlines()).rstrip()+'\n').encode()
    prepared.append((ref,raw,safe))
out=ROOT/'status/codex/productization/S12'/('f04-i04-j03-flows-'+REV[:7]);create_private_directory(out);create_private_directory(out/'artifacts');items=[]
for index,(ref,raw,safe) in enumerate(prepared,1):
    path=out/'artifacts'/(f'a{index:04d}'+Path(ref).suffix);write_private_new(path,safe)
    items.append(dict(original_ref=ref,original_hash='sha256:'+hashlib.sha256(raw).hexdigest(),retained_ref=path.relative_to(out).as_posix(),retained_hash='sha256:'+hashlib.sha256(safe).hexdigest()))
doc=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',executable_revision=REV,implementation_hash=_revision(),status='F04_I04_J03_SCOPED_SOURCE_USER_FLOWS_PASS',source_api_cases=2,browser_cases=1,frontend_build='PASS',source_and_tests_unchanged=True,children_reaped=True,independent_review='STATIC0C0I_EXECUTION_NONE',
 F04='Actual ordinary PaperEngine/E2 proposal/E5 INSUFFICIENT_BALANCE REJECT from explicit simulated balance1 and unchanged selected fixture policy. Actual canonical risk persisted; no plan/request/position, no broker submission, zero exposure. Exact market operation retry preserves original state/revision/risk and creates no second write/effect. Spies forward actual methods, no injected REJECT.',
 I04_J03='Actual normal immutable package intake accepts same strategyID versions0.2.0/0.2.1 with distinct computed hashes/submissions/hypotheses. Only first actually enqueued/researched under existing engineering FIXTURE policy -> CANDIDATE; second DRAFT. Real list/detail/author/revision/pagination0/1/2 and repeated reads/scan replay stable. Real authenticated browser selects candidate/draft/candidate independently, exact hashes/author/state, no other detail heading, no remote page requests, Paper disabled without selected policy; screenshots retained.',
 visual_review='Root inspected actual candidate/draft development screenshots; exact source screenshot byte equality recorded perimage; no claim of inspecting a nonidentical exact screenshot.',image_comparison=image_comparison,
 H16='Original cd415 affected26 run remains isolated and frozen; component15 evidence retained separately; no qualification transfer by test counts.',H01='Design review found fresh retranslation changes original request created_at causing conflict. Root corrected claimed retry to fresh MANAGE_EXISTING/direct original reconciliation before E4/new-entry gates; unclaimed original intent cannot be silently renewed. Draft/test assumptions remain unapplied; entry and E2 management implementation pending.',
 native='NOT_RUN_FOR_THIS_SOURCE',master='IN_PROGRESS',preserved_qualified_windows='7d821f29837e95e46bcd5fe32f14d536a28c9aa8',
 public_requests_cumulative=8,public_responses_cumulative=8,additional_public_requests=0,private_requests=0,credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',artifacts=items)
write_private_new(out/'disposition.json',(json.dumps(doc,ensure_ascii=False,indent=2)+'\n').encode())
for item in items:assert 'sha256:'+hashlib.sha256((out/item['retained_ref']).read_bytes()).hexdigest()==item['retained_hash']
evidence=(out/'disposition.json').relative_to(ROOT).as_posix();p=ROOT/'coordination/CODEX/PROGRESS.json';value=json.loads(p.read_bytes())
value.update(executable_revision=REV,candidate_executable_revision=REV,active_step='F04_I04_J03_SOURCE_USER_FLOWS_PASS_H16_AFFECTED_RUNNING',next_step='Finish isolated cd415 affected source owners, implement corrected genuine E2 entry+original exit management, portable upgrade/removal/audits/S16 binding; final settled full/native remain. External oldPC/Ubuntu/cloud/formal policies/real-forward unaccepted.')
value['f04_i04_j03_source_flows']=dict(executable_revision=REV,status=doc['status'],source_api_cases=2,browser_cases=1,evidence_ref=evidence,native='NOT_RUN_FOR_THIS_SOURCE')
p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
note=f'''# F04/I04/J03 actual owner and browser checkpoint — 2026-10-20

Source {REV}: actual ordinary Paper E5 balance rejection/zero effects and actual
two immutable-version owner/API flows PASS; frontend build and one real browser
candidate/draft/candidate flow PASS. Source frozen and all children reaped.
Evidence: {evidence}. Default/current policies unchanged; no mocked PASS or
canonical financial injection. Source2/API cases and browser1 are separate
workflow proof, not full source/native/Master acceptance. Engineering FIXTURE
research CANDIDATE never grants ordinary Paper/financial/forward authority.

First0.2.0 actually researched, second0.2.1 remainsDRAFT; exact hashes/author/
version/revision/pagination and selection remain independent. Actual E5
INSUFFICIENT_BALANCE writes one canonical risk, no plan/request/broker submit/
position; identical operation retry creates no second effect. Static0C0I reviewer
executionNONE. Root visually inspected actual development candidate/draft
screenshots; exact source screenshot equality is recorded, no invented review.

cd415 affected26 runs in frozen project-contained checkout, prior genuine
funded finalization/recovery/K05 source15 already retained. Current core source
hash unchanged; no native qualification transfer to this source revision.
H01 entry retry design corrected before implementation: claimed original request
requires fresh management/direct reconcile, no E4 retranslation/new-entry gate;
unclaimed persisted preparation cannot silently renew original bytes/clocks.
Actual entry and original E2 management remain pending. Portable/audits/S16 and
final full/native remain. Windows7d qualified package preserved; Master active.
Public8/responses8/additional0/private0; credentialsNONE/capitalNONE/LIVE notstarted/
GitHubNOT_USED. Original task/branch, no main merge; external items unaccepted.

'''
for ref in ('coordination/CODEX/HANDOFF.md','status/codex/R7_PRODUCTIZATION_MASTER_COMPLETION_20261002.md'):
    p=ROOT/ref;p.write_text(note+p.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print(json.dumps(dict(retained=len(items),evidence_ref=evidence,status=doc['status'],image_comparison=image_comparison)))
