"""Retain exact frozen H16 owner regression, independently of current worktree."""
from pathlib import Path
import hashlib,json,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
QUAL=PROJECT/'workspaces/project-r7-qualification-cd415a1'
sys.path[:0]=[str(QUAL/'src'),str(QUAL)]
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import _sanitize,revision_fact
from strategy.v02.capabilities import _revision
REV='cd415a11a97b4b04f490112f6d5ef319ad267395'
revision_fact(QUAL,REV,True)
run='h16-finalization-affected-cd415a1'
report=json.loads((BASE/run/'checkpoint.json').read_bytes())
assert report['passed'] and report['tests_run']==177 and len(report['modules'])==26
assert report['executable_revision']==REV and report['implementation_hash']==_revision()
assert report['source_and_tests_unchanged'] and all(r['passed'] and r['tree_reaped'] and r['within_original_wall_limit'] for r in report['results'])
prior_ref='status/codex/productization/S12/h16-finalization-components-cd415a1/disposition.json'
prior=json.loads((ROOT/prior_ref).read_bytes())
assert prior['executable_revision']==REV
refs=[run+'/checkpoint.json','run_finalization_exact_source_isolated.py',
      'keep_awake_for_validation.py','h16-affected-temporary-awake-cd415a1.json',
      'h16-finalization-implementation-review-final-20261020.json','retain_h16_affected.py']
assert 'sha256:'+hashlib.sha256((BASE/refs[1]).read_bytes()).hexdigest()==report['helper_hash']
awake=json.loads((BASE/'h16-affected-temporary-awake-cd415a1.json').read_bytes())
assert awake['explicitly_released'] and not awake['permanent_settings_changed']
case_ids=[]
for row in report['results']:
    ref=run+'/'+row['log_ref']
    assert 'sha256:'+hashlib.sha256((BASE/ref).read_bytes()).hexdigest()==row['log_hash']
    refs.append(ref);case_ids.extend(row['expected_case_ids'])
assert len(case_ids)==len(set(case_ids))==177
prepared=[]
for ref in refs:
    raw=(BASE/ref).read_bytes();safe=_sanitize(raw.decode('utf-8'),QUAL)
    for path,label in ((QUAL,'<QUALIFIED_SOURCE_ROOT>'),(ROOT,'<SOURCE_ROOT>'),(PROJECT,'<PROJECT_ROOT>'),(Path.home(),'<HOME>')):
        for spelling in (str(path),path.as_posix(),str(path).replace('\\','\\\\')):safe=safe.replace(spelling,label)
    safe=('\n'.join(line.rstrip() for line in safe.splitlines()).rstrip()+'\n').encode()
    prepared.append((ref,raw,safe))
out=ROOT/'status/codex/productization/S12/h16-finalization-affected-cd415a1'
create_private_directory(out);create_private_directory(out/'artifacts');items=[]
for index,(ref,raw,safe) in enumerate(prepared,1):
    path=out/'artifacts'/(f'a{index:04d}'+Path(ref).suffix);write_private_new(path,safe)
    items.append(dict(original_ref=ref,original_hash='sha256:'+hashlib.sha256(raw).hexdigest(),retained_ref=path.relative_to(out).as_posix(),retained_hash='sha256:'+hashlib.sha256(safe).hexdigest()))
doc=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',status='H16_AFFECTED_OWNER_SOURCE_PASS',
    executable_revision=REV,implementation_hash=_revision(),source_and_tests_unchanged=True,
    affected_modules=26,affected_cases=177,affected_case_ids=case_ids,children_reaped=True,
    prior_components_ref=prior_ref,combined_disjoint_modules=39,combined_disjoint_cases=192,
    scope='Actual cleanup/terminal/protection/close/funding/dispatch/position/K05 owner source regression; each original per-module900s unchanged. Separate component15 + affected177, no duplicate development credit.',
    prior_failure='Original 7de158 timeout/memory failures remain failed. cd415 new source plus legitimate existing-case partition retains unchanged case identities and limits.',
    awake='Explicitly authorized system-only request bound to validation process; released after exit, no permanent/display/away-mode settings.',
    qualification='AFFECTED_SOURCE_ONLY; NOT_FULL_PQR; NOT_NATIVE; NOT_CURRENT_H01_SOURCE',
    preserved_qualified_windows='7d821f29837e95e46bcd5fe32f14d536a28c9aa8',master='IN_PROGRESS',
    public_requests_cumulative=8,public_responses_cumulative=8,additional_public_requests=0,
    private_requests=0,credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',artifacts=items)
write_private_new(out/'disposition.json',(json.dumps(doc,ensure_ascii=False,indent=2)+'\n').encode())
for item in items:assert 'sha256:'+hashlib.sha256((out/item['retained_ref']).read_bytes()).hexdigest()==item['retained_hash']
evidence=(out/'disposition.json').relative_to(ROOT).as_posix()
p=ROOT/'coordination/CODEX/PROGRESS.json';value=json.loads(p.read_bytes())
value.update(active_step='H16_AFFECTED_SOURCE_PASS_H01_ENTRY_IMPLEMENTATION_IN_PROGRESS',next_step='Complete genuine H01 original entry and E2 exit management; retain distinct revisions; portable upgrade/removal/audits/S16 and final settled full/native remain. External oldPC/Ubuntu/cloud/policies/real-forward unaccepted.')
value['h16_affected_source']=dict(executable_revision=REV,status=doc['status'],affected_cases=177,combined_disjoint_cases=192,evidence_ref=evidence,native='NOT_RUN_FOR_THIS_SOURCE')
p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
note=f'''# H16 exact affected-owner source checkpoint — 2026-10-20

Source {REV}: affected26modules/177cases PASS, unchanged/reaped, each<=original900s.
Together with separately retained disjoint component13modules/15cases, scoped
source union39modules/192cases. Evidence: {evidence}.
Actual cleanup11 cases, original terminal readback, protection/close/funding,
dispatch/position and K05 owners passed; no new thresholds or skipped cases.
Frozen checkout remained under the project while main implementation advanced.
Temporary system-awake request explicitly released after validation exit;
no permanent power/display/away-mode settings changed.

This is affected source mechanics, not full PQR/native or later H01 credit.
H01 first real E2 entry development positive passed; independent review found
caller geometry and intrinsic retained E2 lineage defects. Actual red faults
preserved; minimal fixes and further genuine recovery/negative checks underway.
Original E2 exit management remains pending. Preserved Windows7d qualified
package unchanged. Master active; original task/branch, no main merge.
Public8/responses8/additional0/private0; credentialsNONE/capitalNONE/LIVE notstarted/
GitHubNOT_USED. OldPC/Ubuntu/cloud/policies/real-forward remain unaccepted.

'''
for ref in ('coordination/CODEX/HANDOFF.md','status/codex/R7_PRODUCTIZATION_MASTER_COMPLETION_20261002.md'):
    p=ROOT/ref;p.write_text(note+p.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print(json.dumps(dict(evidence_ref=evidence,retained_artifacts=len(items),affected_cases=177,status=doc['status'])))
