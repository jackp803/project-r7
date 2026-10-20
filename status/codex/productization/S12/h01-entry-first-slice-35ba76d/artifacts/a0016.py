"""Retain first genuine E2 entry slice; no whole H01/native credit."""
from pathlib import Path
import hashlib,json,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import _sanitize,revision_fact
from strategy.v02.capabilities import _revision
REV='35ba76d5773b1382222b0743ea7db672f834ca3e'
revision_fact(ROOT,REV,True)
run='h16-finalization-h01-entry-'+REV[:7]
report=json.loads((BASE/run/'checkpoint.json').read_bytes())
assert report['passed'] and len(report['modules'])==13 and report['source_and_tests_unchanged']
assert report['executable_revision']==REV and report['implementation_hash']==_revision()
assert all(r['passed'] and r['tree_reaped'] and r['within_original_wall_limit'] for r in report['results'])
assert sum(r['tests_run'] for r in report['results'][:10])==11
review_ref='h01-entry-implementation-review-final-20261020.json'
review=json.loads((BASE/review_ref).read_bytes())
assert review['counts']['critical']==review['counts']['important']==0
# Review records are source-pinned; no claim that the reviewer ran tests.
hashes=review.get('subject_hashes',review.get('production_hashes'))
assert isinstance(hashes,dict) and len(hashes)==7
for ref,wanted in hashes.items():assert hashlib.sha256((ROOT/ref).read_bytes()).hexdigest()==wanted
awake_ref='h01-entry-temporary-awake-'+REV[:7]+'.json'
awake=json.loads((BASE/awake_ref).read_bytes());assert awake['explicitly_released'] and not awake['permanent_settings_changed']
refs=[run+'/checkpoint.json','run_finalization_exact_source.py','run_owner_development_v03.py',
    'keep_awake_for_validation.py',awake_ref,review_ref,
    'h01-entry-implementation-review-initial-20261020.json','h01-entry-design-independent-review-20261020.json',
    'h01-entry-root-design-20261020.json','h01-entry-root-design-20261020.initial.json',
    'h01-entry-first-slice-apply-recipe-20261020.json',
    'h01-entry-negative-tests-recipe-20261020.json','h01-entry-recovery-schema-drafts-20261020.json',
    'apply_h01_entry_tests.py','h01-entry-tests-root-application-20261020.json','retain_h01_entry.py']
for folder in ('h01-e2-entry-red','h01-e2-entry-green01','h01-review-faults-red','h01-review-faults-red01','h01-review-faults-green01','h01-entry-negative-recovery-development01'):
    refs.extend((folder+'/checkpoint.json',folder+'/source.log'))
for row in report['results']:
    ref=run+'/'+row['log_ref'];assert 'sha256:'+hashlib.sha256((BASE/ref).read_bytes()).hexdigest()==row['log_hash'];refs.append(ref)
for manifest,key in ((json.loads((BASE/'h01-entry-negative-tests-recipe-20261020.json').read_bytes()),'drafts'),(json.loads((BASE/'h01-entry-recovery-schema-drafts-20261020.json').read_bytes()),'artifacts')):
    refs.extend(d.get('path',d.get('ref')) for d in manifest[key])
refs=list(dict.fromkeys(refs));prepared=[]
for ref in refs:
    raw=(BASE/ref).read_bytes();safe=_sanitize(raw.decode('utf-8'),ROOT)
    for path,label in ((ROOT,'<SOURCE_ROOT>'),(PROJECT,'<PROJECT_ROOT>'),(Path.home(),'<HOME>')):
        for spelling in (str(path),path.as_posix(),str(path).replace('\\','\\\\')):safe=safe.replace(spelling,label)
    safe=('\n'.join(line.rstrip() for line in safe.splitlines()).rstrip()+'\n').encode();prepared.append((ref,raw,safe))
out=ROOT/'status/codex/productization/S12'/('h01-entry-first-slice-'+REV[:7]);create_private_directory(out);create_private_directory(out/'artifacts');items=[]
for index,(ref,raw,safe) in enumerate(prepared,1):
    path=out/'artifacts'/(f'a{index:04d}'+Path(ref).suffix);write_private_new(path,safe)
    items.append(dict(original_ref=ref,original_hash='sha256:'+hashlib.sha256(raw).hexdigest(),retained_ref=path.relative_to(out).as_posix(),retained_hash='sha256:'+hashlib.sha256(safe).hexdigest()))
doc=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',executable_revision=REV,implementation_hash=_revision(),
    status='GENUINE_E2_ENTRY_FIRST_SOURCE_SLICE_PASS',modules=13,source_cases=report['tests_run'],new_join_cases=11,
    source_and_tests_unchanged=True,children_reaped=True,independent_review='STATIC0C0I_EXECUTION_NONE',
    flows=['Actual immutable E6/E7 selected strategy and recorded-received E1 bundle invoke real E2 signal/ExitRequest/TradeIntent and actual E5, before durable decision outbox, canonical risk/plan, original E4 claim and single guarded fake POST.',
      'Actual flat bars NO_TRADE zero financial effects; actual balance1 REJECT one original canonical risk; future/cutoff/historical-asof and forged typed policy denied; same-boundary conflict preserves original.',
      'Actual risk writer commits then throws; new issuer/capability/translator/provider/journal handles/process2 preserve E7release1 and drain exact original effects with zero HTTP; stale process denied.',
      'Lost ACK and expired original entry proof/plan reconcile same claimed request with fresh MANAGE_EXISTING and GET only. Lost local unclaimed preparation blocks without retranslation or renewal.',
      'Actual owner outbox/receipt immutable UPDATE/DELETE/REPLACE denied with recursive triggersOFF; validFK alternative boundary/same unique decisionID refused.'],
    actual_defects='Initial0C2I reproduced: geometry1 and six intrinsic lineage corruptions accepted; actual RED2 own cases/7 failures, then minimal correspondence/existing E2 builder checks. Earlier h01-review-faults-red import2errors is harness setup failure, no product-defect credit. Root corrected PYTHONPATH; all originals retained.',
    source_hygiene='Executable4da292 had trailing blank test EOF; separate35ba76d correction, no amended history or changed behavior. Exact clean qualification follows35ba76d.',
    retainer_preflight='Initial review count lookup KeyError before output creation; corrected to actual nested counts, no product-defect or acceptance credit.',
    scope='FIXTURE/FAKE_PROVIDER_VERIFICATION only. No original E2 exit management yet; no claim wholeH01/LIVE-code-complete/normalPaper native/fullPQR acceptance.',
    awake='Authorized validation-process-only system request explicitly released; no permanent/display/away-mode change.',
    native='NOT_RUN_FOR_THIS_SOURCE',master='IN_PROGRESS',preserved_qualified_windows='7d821f29837e95e46bcd5fe32f14d536a28c9aa8',
    public_requests_cumulative=8,public_responses_cumulative=8,additional_public_requests=0,private_requests=0,
    credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',artifacts=items)
write_private_new(out/'disposition.json',(json.dumps(doc,ensure_ascii=False,indent=2)+'\n').encode())
for item in items:assert 'sha256:'+hashlib.sha256((out/item['retained_ref']).read_bytes()).hexdigest()==item['retained_hash']
evidence=(out/'disposition.json').relative_to(ROOT).as_posix();p=ROOT/'coordination/CODEX/PROGRESS.json';value=json.loads(p.read_bytes())
value.update(executable_revision=REV,candidate_executable_revision=REV,active_step='H01_GENUINE_ENTRY_FIRST_SLICE_PASS_ORIGINAL_E2_MANAGEMENT_PENDING',next_step='Join original E2 exit management to existing E5/close owners preserving clocks/retry; portable crossversion/audits/S16/final settled source/native remain. External oldPC/Ubuntu/cloud/policies/real-forward remain.')
value['h01_genuine_entry_first_slice']=dict(executable_revision=REV,source_cases=report['tests_run'],new_join_cases=11,evidence_ref=evidence,scope=doc['scope'])
p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
note=f'''# Genuine H01 entry first-slice source checkpoint — 2026-10-20

Source {REV}, implementation {_revision()}: exact13modules/{report['tests_run']}cases PASS,
including11 new genuine joined entry/fault/recovery cases; unchanged/reaped,
each<=original900s. Evidence: {evidence}. Independent static0C0I, executionNONE.
Actual E2/E5 outputs, immutable outbox before canonical risk/plan and E4 guarded
single fake POST. Actual NO_TRADE/REJECT, forged policy/future-input denials,
same-boundary conflict, lostACK/expired-proof management, postcommit recovery
with genuinely reconstructed owners, unclaimed preparation loss and immutable
schema attacks preserve original IDs/clocks; no result/authority substitution.
Two concrete review defects reproduced and fixed; all red/harness failures kept.
Temporary system-awake request released after validation; no permanent settings.

This controlled FIXTURE source slice is not whole H01 or LIVE-code-complete.
Original E2 exit management remains pending. Qualified Windows7d package kept
independently; no acceptance transfer. Portable crossversion/audits/S16/final
settled full/native remain. Master active; original task/branch, no main merge.
Public8/responses8/additional0/private0; credentialsNONE/capitalNONE/LIVE notstarted/
GitHubNOT_USED. OldPC/Ubuntu/cloud/formal policies/real-forward remain unaccepted.

'''
for ref in ('coordination/CODEX/HANDOFF.md','status/codex/R7_PRODUCTIZATION_MASTER_COMPLETION_20261002.md'):
    p=ROOT/ref;p.write_text(note+p.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print(json.dumps(dict(status=doc['status'],source_cases=report['tests_run'],retained=len(items),evidence_ref=evidence)))
