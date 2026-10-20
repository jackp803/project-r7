"""Close actual aa2d evidence, preserving supplements and known UI01 failure."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from application.qualification import _sanitize
from application.platform.private_files import write_private_new
from strategy.v02.capabilities import _revision
REV='aa2d00a4de1147fbc5ff5c4ed14db2f5032b65dd'
IMPL='sha256:6731c69a4034921a613b61633770101d64708ce3ca12698543601107668aefce'
TARGET=ROOT/'status/codex/productization/S12/current-windows-aa2d00a'
def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
def load(path):return json.loads(path.read_bytes())
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
assert _revision()==IMPL
d=load(TARGET/'disposition.json');assert d['identity']['implementation_hash']==IMPL
assert d['ordinary_windows_paper_software']['status']=='PASS'
assert len(d['retained_files'])==830
for row in d['retained_files']:assert sha((TARGET/row['retained_ref']).read_bytes())==row['retained_hash']
for stage in ('qualify','portable','headless','unattended','ordinary-idle','qualified-backup'):
    q=load(BASE/(stage+'-aa2d00a-first/checkpoint.json'))
    assert q['passed'] is True and q['revision']==REV
q=load(BASE/'qualify-aa2d00a-first/checkpoint.json')
power=BASE/'power-interval-timezone-repair-aa2d00a';actual=load(power/'retry-observation.json')
parse=lambda s:datetime.fromisoformat(s.replace('Z','+00:00'))
assert parse(actual['owning_start_utc'])==parse(q['started_at'])
assert parse(actual['owning_end_utc'])==parse(q['finished_at'])
assert actual['query_status'] in ('COMPLETE','COMPLETE_NO_MATCHING_EVENTS')
assert all(parse(q['started_at'])<=parse(row['recorded_utc'])<=parse(q['finished_at']) for row in actual['events'])
assert load(power/'red.json')['outside_event_count']==3
green=dict(status='ACTUAL_EXACT_UTC_REQUERY_VERIFIED',query_status=actual['query_status'],events=len(actual['events']),
    precise_start_equal=True,precise_end_equal=True,all_returned_events_in_window=True,
    original_observation='INVALID_FOR_OWNING_INTERVAL;THREE_OUTSIDE_EVENTS_RETAINED',
    retry_helper_hash=sha((power/'retry.ps1').read_bytes()),retry_hash=sha((power/'retry-observation.json').read_bytes()),
    independent_static_review=dict(reviewer='pqr_inventory_map',critical=0,important=0,execution='NONE'),
    qualification_credit='NONE',power_continuity='NOT_INFERRED',host_settings='UNCHANGED')
write_private_new(power/'green.json',(json.dumps(green,indent=2)+'\n').encode())
extra=[BASE/'aa2d-final-static-review-records/record.json',BASE/'record_current_windows_checkpoint_aa2d00a.py',
       BASE/'run_aa2d_remaining_checkpoint.ps1',BASE/'apply_ui01_projection_patch.py',
       BASE/'ui01-projection-unapplied-v1/manifest.json',Path(__file__),*sorted(power.iterdir())]
draft=BASE/'ui01-projection-unapplied-v1';manifest=load(draft/'manifest.json')
assert sha((draft/'manifest.json').read_bytes())=='sha256:76f450c9fbb7f02537aafdcdde60fd5eec4d542c30e6aedec3b48aeed829f411'
extra.extend(draft/row['ref'] for row in manifest['records'])
addenda=TARGET/'addenda';addenda.mkdir()
for number,path in enumerate(extra,1):
    raw=path.read_bytes();assert path.is_file() and path.stat().st_nlink==1 and len(raw)<=8*1024**2
    if path.is_relative_to(draft) and path.name!='manifest.json':
        safe=raw;suffix='.unapplied';normalization='NONE;PUBLIC_REVIEWED_SOURCE_TEMPLATE;UNAPPLIED_UNQUALIFIED'
    else:
        text=_sanitize(raw.decode('utf-8-sig'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n')
        safe=('\n'.join(line.rstrip(' \t') for line in text.splitlines()).rstrip()+'\n').encode()
        suffix=path.suffix;normalization='PUBLIC_SANITIZATION_LF_TRAILING_WHITESPACE_ONLY'
    ref='addenda/b'+str(number).zfill(4)+suffix;(TARGET/ref).write_bytes(safe)
    assert (TARGET/ref).read_bytes()==safe
    d['retained_files'].append(dict(original_ref=path.relative_to(PROJECT).as_posix(),original_hash=sha(raw),
        retained_ref=ref,retained_hash=sha(safe),normalization=normalization))
d['power_observation']=green
d['remaining_local']='UI01_DEMONSTRATED_MISSING_DIAGNOSTIC_PROJECTIONS_AND_CANCELED_JOB_FILTER;ACTUAL_REPAIR_AND_NEW_QUALIFICATION;SEMANTIC66_AND150_REVIEW'
d['ui01_current_acceptance']='FAIL_DEMONSTRATED_14_MISSING_FIELDS;REPAIR_PREPARED_UNAPPLIED;FIXED_PQR_PASS_IS_NOT_WHOLE_UI01_PASS'
d['supplemental_acceptance_scope']='NATIVE_K03_PRODUCER_AND_STOPPED_SOURCE_RO_LOCAL_COPY;SOURCE_SAME_LINEAGE_H01_H16_K05_AND_GENUINE_FOUR_HOUR_STR12;NO_NEW_RECEIPT_MEMBERSHIP'
save(TARGET/'disposition.json',d)
review=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',executable_revision=REV,identity=d['identity'],
    recorded_at=datetime.now(timezone.utc).isoformat(),review='ROOT_SEMANTIC_SCOPE_REVIEW',master='IN_PROGRESS',
    fixed_profile=d['ordinary_windows_paper_software'],
    completed_user_flows=['Fresh native ZIP install without developer PATH/PYTHONPATH/Node; fresh unconfigured auth',
        'Native FIXTURE candidate/rejection/insufficient evidence and Paper ACK/fill/protection/pause/restart/exit/final flat',
        'Nine actual native fault windows plus finite research/protection resource isolation',
        'Native coordinator automatic ordinary diagnostic intake/research/BLOCKED/durable report',
        'Same actual qualified ordinary profile idle control/research/runtime duplicate/crash/restart/stop; workflow false',
        'Same qualified store backup/verify/restore/rebackup and four-way file/receipt/runtime-selection equality; restored denied'],
    supplements=[
        dict(id='K03',status='SCOPED_PASS',scope='NATIVE_PRODUCER_PLUS_STOPPED_SOURCE_READONLY_LOCAL_COPY_AUDIT',native_outbox='PENDING',remote_ack='NOT_RUN',qualification_membership='NONE'),
        dict(id='H01_H16',status='SCOPED_PASS',scope='SOURCE_SAME_ORIGINAL_E2_ENTRY_EXIT_FUNDING_STOP_CLEANUP_CLOSED_AND_FINALIZATION',real_http=0,native_credit='NONE'),
        dict(id='K05',status='SCOPED_PASS',scope='SAME_SOURCE_FINANCIAL_LINEAGE_READONLY_PRIVATE_AND_PUBLIC_REPORT_REDACTION_POLICY_BUNDLE',financial_mutation='NONE',native_credit='NONE'),
        dict(id='STR12',status='SCOPED_PASS',scope='GENUINE_FOUR_HOUR_RESEARCH_REOPEN_SAME_REGISTRY_TO_PAPER_NEW_GENERATION_RECOVERY_NO_BAR_MAX_HOLD_EXIT_CLOSED',real_forward_seconds=0,native_credit='NONE'),
        dict(id='UI01',status='FAIL_REMEDIATION_NEXT',actual_red_cases=4,missing_field_failures=14,errors=0,planned_owner_cases=10,source_patch='UNAPPLIED',manifest_hash=sha((draft/'manifest.json').read_bytes())),
        dict(id='L01_L05',status='SCOPED_ROOT_TRIAGE_CLOSED',scope='AA2D_COMMITTED_TEXT_SNAPSHOT_ONLY',original_scanner_status='STOP_ROOT_REVIEW',root_unresolved=0,confirmed_real_credential_patterns=0,history_binary_spend_absence='NOT_INFERRED'),
        dict(id='B03_M04_F11_PLAT08',status='PRESERVED_PRIOR_SUBJECT_PROOFS',executable_revision='3ae6460c69a8a8f90588c396b819af7079e7546d',current_native_credit='NOT_TRANSFERRED')],
    power=green,
    whole_requirement_acceptance='NOT_BLANKET_PASS;216_ACTUAL_BINDINGS_ARE_SUPPORT_NOT_COMPLETE_CLAUSE_ACCEPTANCE',
    external=d['external'],additional_public_requests=0,cumulative_public_requests=8,cumulative_public_responses=8,
    provider_credentials='NONE',private_requests=0,capital='NONE',github_compute='NOT_USED')
save(TARGET/'semantic-review.json',review)
p=ROOT/'coordination/CODEX/PROGRESS.json';v=load(p)
v['current_windows_ui01_followup']=dict(executable_revision=REV,status='ACTUAL_RED_DEMONSTRATED_REPAIR_PREPARED_UNAPPLIED',
    evidence_ref=(TARGET/'semantic-review.json').relative_to(ROOT).as_posix(),required_missing_fields=14,
    patch_manifest_hash=sha((draft/'manifest.json').read_bytes()),new_source_qualification='NOT_STARTED',
    ordinary_deterministic_defect='CONTINUE_MINIMAL_REMEDIATION_AFTER_THIS_EVIDENCE_COMMIT')
v['current_windows_completed_supplements']=dict(revision=REV,scope=review['supplements'][:4],qualification_membership='NONE')
save(p,v)
p=ROOT/'coordination/CODEX/HANDOFF.md';prefix='''# Immediate follow-up after preserved aa2d software checkpoint

Current fixed Windows qualification and same-version delivery/backup PASS. Exact
software subject aa2d00a4de1147fbc5ff5c4ed14db2f5032b65dd remains preserved.
UI01 has a genuine separate RED:4cases/14missing diagnostic fields; canceled-job
filter also missing. Eight-file minimal patch is reviewed and UNAPPLIED; apply
only after this evidence commit, then actual backend/browser tests and new clean
candidate qualification. Do not transfer aa2d qualification to later source.
K03 native producer/stopped-source local-copy and same-lineage H01-H16-K05/STR12
source supplements are complete only within their recorded scope. Native K03
outbox remains PENDING; no real cloud ACK/ordinary operator Paper/real-forward.
Power observer's first query was invalid for this interval (three old events);
exact UTC XML requery is retained separately, with no power-continuity claim.
See current-windows-aa2d00a/semantic-review.json; Master remains IN_PROGRESS.

---

''';p.write_text(prefix+p.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
assert _revision()==IMPL
assert all(sha((TARGET/row['retained_ref']).read_bytes())==row['retained_hash'] for row in d['retained_files'])
print(json.dumps(dict(retained_files=len(d['retained_files']),semantic_review='SCOPED',master='IN_PROGRESS',next='COMMIT_PUSH_THEN_UI01_IMPLEMENTATION',source_unchanged=True)))
