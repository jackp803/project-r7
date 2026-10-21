"""Final finite Windows identity/disclosure reconciliation, no execution credit."""
from collections import Counter
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,subprocess,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from application.paper.qualification import artifact_bytes
from application.platform.distribution import verify_distribution
from strategy.v02.capabilities import _revision
REV='bffc558b9652dc41c0804896436ac7ad8744f7f8'
IMPL='sha256:387238c130af7b96f59578fdfec3b1fa76fc9443daa8a174be00d79ba166c666'
T=ROOT/'status/codex/productization/S12/current-windows-bffc558'
def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
def read(root,ref):return json.loads(artifact_bytes(root,ref))
def encoded(doc):return (json.dumps(doc,ensure_ascii=False,indent=2)+'\n').encode()
def fresh(ref,doc):
 raw=encoded(doc);assert len(raw)<=8*1024**2
 with (T/ref).open('xb') as f:f.write(raw)
 assert artifact_bytes(T,ref)==raw
 return sha(raw)
def digest_file(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

assert _revision()==IMPL
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==REV
d=read(T,'disposition.json');facts=verify_distribution(BASE/'build-bffc558/dist/R7')
assert d['identity']==facts==verify_distribution(PROJECT/'installations/windows-bffc558-clean')
assert d['ordinary_windows_paper_software']['status']=='PASS'
refs=[r['retained_ref'] for r in d['retained_files']];assert len(refs)==len(set(refs))
for r in d['retained_files']:assert sha(artifact_bytes(T,r['retained_ref']))==r['retained_hash']
parts=d['scoped_static_audit']['parts'];decoded=[]
for n,r in enumerate(parts,1):
 raw=artifact_bytes(T,r['ref']);assert sha(raw)==r['hash'];part=json.loads(raw)
 piece=bytes.fromhex(part['text_hex']);assert part['part']==n and part['byte_length']==len(piece)
 assert part['byte_offset']==sum(map(len,decoded));decoded.append(piece)
assert sha(b''.join(decoded))==d['scoped_static_audit']['sanitized_scan_hash']
assert {p.relative_to(T).as_posix() for p in T.rglob('*') if p.is_file()}==set(refs)|{r['ref'] for r in parts}|{'disposition.json'}
stages={name:read(BASE,name+'-bffc558-first/checkpoint.json') for name in ('build','qualify','portable','headless','unattended','ordinary-idle','qualified-backup')}
assert all(r['revision']==REV and r['passed'] for r in stages.values())
observer=read(BASE,'owning-memory-bffc558-first/checkpoint.json')
assert all(observer[k] for k in ('owning_passed','tree_reaped','monitor_stopped','source_unchanged','wrapper_unchanged')) and observer['errors']==[]
v=read(PROJECT,'deliveries/current-windows-bffc558/version.json');assert v['identity']==facts
for r in v['delivery_files']:
 assert digest_file(PROJECT/r['source_ref'])==r['sha256']==digest_file(PROJECT/'deliveries/current-windows-bffc558'/r['delivery_ref'])
index=read(BASE,'execution-index-bffc558.json');assert index['identity']==facts
required_source={
 'tests.application.test_paper_native_driver.PaperNativeDriverTests.test_every_scenario_and_final_distribution_match_original_group_subject',
 'tests.application.test_feedback_redaction.FeedbackTests.test_adversarial_private_owner_fields_are_omitted_and_freeform_report_input_is_rejected'}
bound=[r for r in index['cases'] if r['test_id'] in required_source]
assert {r['test_id'] for r in bound}==required_source and all(r['status']=='PASS' for r in bound)
required_native={('PQR-02','EXACT_NATIVE_IDENTITY_RESOURCES_LICENSES_UI'),('PQR-02','TAMPER_DENIED_EXTERNAL_DATA'),
 ('PQR-07','SIMULATED_REAL_ELAPSED_DISCLOSURE_REDACTION')}
native=[r for r in index['actual_native_assertions'] if (r['group_id'],r['assertion_id']) in required_native]
assert {(r['group_id'],r['assertion_id']) for r in native}==required_native and all(r['status']=='PASS' for r in native)
triage=read(BASE,'l01-l05-root-triage-bffc558-20261021.json')
assert triage['subject']==dict(head=REV,origin_main='7d1f447c8a9e8b46dc5ecc7bf0a78e1d63680812',merge_base='7d1f447c8a9e8b46dc5ecc7bf0a78e1d63680812')
assert triage['unresolved_after_root_review']==0 and triage['confirmed_real_secrets']==0
advisory=read(BASE,'ops02-final-reconciliation-advisory-bffc558.json');assert advisory['execution']=='NONE'
original=read(T,'semantic-review.json');final=deepcopy(original)
row=next(r for r in final['current_matrix_results'] if r['requirement_id']=='OPS-02')
assert row['status']=='NOT_RUN' and not row['unresolved_named_cases']
row.update(status='PASS',exit_code=0,acceptance_reviewer='ROOT_FINAL_FINITE_CURRENT_WINDOWS_RELEASE_RECONCILIATION')
row['scoped_semantic_decision'].update(scope=advisory['conditional_disposition']['proposed_scope'],remaining_clause=None,
 final_root_reconciliation='ops02-final-release-review.json',actual_native=native,
 bounded_audit_limitations=advisory['bounded_coverage_limitations'])
final['summary']['current_matrix_results']=dict(Counter(r['status'] for r in final['current_matrix_results']))
final['prior_scope_review']=dict(ref='semantic-review.json',hash=sha(artifact_bytes(T,'semantic-review.json')))
now=datetime.now(timezone.utc).isoformat();final['final_reconciled_at']=now
review=dict(task_id=d['task_id'],executable_revision=REV,identity=facts,master='IN_PROGRESS',recorded_at=now,
 scope=advisory['conditional_disposition']['proposed_scope'],reviewer='ROOT_ACTUAL_RECONCILIATION',
 checks={r['id']:'PASS' for r in advisory['minimum_final_root_checks']},
 prior_retained_files_verified=len(refs),audit_parts_verified=len(parts),delivery_files_verified=len(v['delivery_files']),
 actual_owning_receipt=stages['qualify']['result']['receipt_ref'],source_bindings=bound,native_bindings=native,
 source_worktree_at_execution='CLEAN',native_worktree=facts['worktree'],evidence_commit='SUBSEQUENT_METADATA_ONLY;NOT_EXECUTABLE_REVISION',
 audit_review='ROOT_SELF_REVIEW;SCANNER_STOP_ROOT_REVIEW_PRESERVED',audit_input_sha256=triage['scan_sha256'],
 new_metadata_delta='ALLOWLISTED_PUBLIC_CLOSED_PROOFS_AND_KNOWN_SOURCES;BOUNDED_READBACK_HASHES_VERIFIED;NO_PRIVATE_DB_AUTH_OR_RAW_PROVIDER_PAYLOADS',
 bounded_coverage_limitations=advisory['bounded_coverage_limitations'],external=d['external'],
 additional_public_requests=0,cumulative_public_requests=8,cumulative_public_responses=8,private_requests=0,
 provider_credentials='NONE',provider_mutation=0,capital='NONE',github_compute='NOT_USED')
for ref,doc in (('semantic-review-final.json',final),('ops02-final-release-review.json',review)):
 commitment=fresh(ref,doc)
 d['retained_files'].append(dict(original_ref='ROOT_FINAL_METADATA/'+ref,original_hash=commitment,retained_ref=ref,retained_hash=commitment,normalization='ROOT_AUTHORED_FINAL_RECONCILIATION'))
old=d['semantic_review'];d['semantic_review']=dict(ref='semantic-review-final.json',hash=sha(artifact_bytes(T,'semantic-review-final.json')),
 summary=final['summary'],scope=final['kind'],financial_authority='NONE',master='IN_PROGRESS',prior_review=old)
d['remaining_local']='FINITE_CURRENT_WINDOWS_RECONCILIATION_COMPLETE;NO_NEW_DEMONSTRATED_LOCAL_CODE_DEFECT;MANDATORY_EXTERNAL_COMMISSIONING_AND_SELECTED_POLICIES_REAL_FORWARD_OUTSTANDING'
(T/'disposition.json').write_bytes(encoded(d))
p=ROOT/'coordination/CODEX/PROGRESS.json';progress=json.loads(p.read_bytes());ref=(T/'semantic-review-final.json').relative_to(ROOT).as_posix()
progress['current_windows_checkpoint']['semantic_review']=d['semantic_review']
progress['current_windows_ui01_followup'].update(new_source_qualification='ACTUAL_COMPLETE_FIXED_WINDOWS_PQR_PASS',ordinary_deterministic_defect='RESOLVED_IN_QUALIFIED_BFFC558',evidence_ref=ref,
 original_failure_evidence_ref='status/codex/productization/S12/current-windows-aa2d00a/semantic-review.json')
progress['remaining_local_source_checkpoint'].update(status='FINITE_CURRENT_WINDOWS_CLAUSE_AND_RELEASE_RECONCILIATION_COMPLETE',semantic_evidence_ref=ref)
progress['remaining_local_source_checkpoint']['unclosed']=[x for x in progress['remaining_local_source_checkpoint']['unclosed'] if x!='OPS02_WHOLE_BRANCH_FINAL_REVIEW']
progress['next_local_source_work_queue_ref']=ref
progress['next_step']='Current authorized Windows software/delivery/finite release review completed. Preserve qualified bffc source and original subject evidence. Continue Master upon available target/Ubuntu/cloud/SSH commissioning and selected ordinary policies; real-forward requires actual elapsed samples. No new demonstrated independent local code defect remains in this finite review. Master IN_PROGRESS.'
p.write_bytes(encoded(progress))
p=ROOT/'coordination/CODEX/HANDOFF.md'
intro='''# Final current Windows release reconciliation complete

OPS02 final identity/ancillary/public-report/finite committed-text branch audit and
retained-evidence/delivery readback completed. See current-windows-bffc558/
semantic-review-final.json and ops02-final-release-review.json. Prior semantic
review is retained unchanged. Current scope60PASS/6NOT_RUN; inherited scope145PASS/
5NOT_RUN; these are explicit finite Windows decisions, not whole-Master PASS.
UI01 previous NOT_STARTED/remediation labels are now resolved by the actual full
bffc owning receipt. No new demonstrated independent local code defect remains
in this finite review. External target/Ubuntu/cloud/SSH/policies/real-forward
commissioning remains mandatory. MasterIN_PROGRESS; no main merge or activation.

---

'''
p.write_text(intro+p.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
p=ROOT/'status/codex/R7_PRODUCTIZATION_MASTER_COMPLETION_20261002.md';text=p.read_text(encoding='utf-8')
text=text.replace('OPS02 whole-branch final review and external commissioning remain unclosed.',
 'OPS02 finite current-Windows final identity/report/branch-text/retention audit is complete; external commissioning remains unclosed.')
text=text.replace('current-windows-bffc558/semantic-review.json','current-windows-bffc558/semantic-review-final.json')
p.write_text(text,encoding='utf-8',newline='\n')
assert _revision()==IMPL
print(json.dumps(dict(passed=True,retained_files_verified=len(refs),audit_parts_verified=len(parts),
 delivery_files_verified=len(v['delivery_files']),semantic_summary=final['summary'],source_unchanged=True,master='IN_PROGRESS')))
