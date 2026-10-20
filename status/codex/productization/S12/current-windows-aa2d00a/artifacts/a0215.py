"""One exact candidate's selected public supplements; no qualification credit."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,re,sys

BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from application.qualification import _sanitize
from application.paper.producer import _guard
from application.paper.inventory import current_target,fixed_profile
from application.platform.distribution import verify_distribution
from application.platform.private_files import create_private_directory,write_private_new
from application.platform.supervision import _local_path
from application.cloud.candidate_index import validate_candidate_index_publication

REV='aa2d00a4de1147fbc5ff5c4ed14db2f5032b65dd'
IMPL='sha256:6731c69a4034921a613b61633770101d64708ce3ca12698543601107668aefce'
PACKAGE=BASE/'build-aa2d00a/dist/R7'
FACTS=verify_distribution(PACKAGE)
assert FACTS['executable_revision']==REV and FACTS['implementation_hash']==IMPL
def guard():_guard(ROOT,REV,PACKAGE,FACTS,fixed_profile(current_target()))
def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
def load(path):return json.loads(path.read_bytes())
guard()
OUT=BASE/'supplements-aa2d00a-prepared';create_private_directory(OUT)
files=set()
probe_names=(
 'k03-missing-owner-red-3ae6460-first','k03-missing-owner-red-v2-3ae6460-first',
 'k03-source-owner-red-250ed2d-first','k03-source-owner-green01',
 'k03-integration-red01','k03-integration-red02','k03-integration-green01',
 'k03-recovery-green01','k03-related-regression-green01',
 'k03-ack-concurrency-red01','k03-ack-concurrency-red02','k03-ack-concurrency-green01',
 'k03-pagination-refusal-red01','k03-pagination-refusal-green01',
 'k03-related-regression-green02','k03-inventory-authoring-green01',
 'h01-joined-close-aa2d00a-first','h01-joined-k05-aa2d00a-first')
probes=[]
for name in probe_names:
 folder=BASE/name;d=load(folder/'checkpoint.json')
 assert d.get('tree_reaped') is True
 log=folder/'source.log'
 if not log.exists():
  options=list(folder.glob('*.log'));assert len(options)==1;log=options[0]
 files.update((folder/'checkpoint.json',log))
 counts=re.findall(r'Ran (\d+) tests? in ',log.read_text(encoding='utf-8'))
 probes.append(dict(ref=name,implementation_hash=d.get('implementation_hash'),exit_code=d.get('exit_code'),
  status=d.get('status'),source_case_executions=int(counts[-1]) if counts else None,
  acceptance_credit='NONE;HISTORICAL_DEVELOPMENT_OR_EXACT_SOURCE_SUPPLEMENT_ONLY'))
for name in ('h01-joined-close-aa2d00a-first','h01-joined-k05-aa2d00a-first'):
 d=load(BASE/name/'checkpoint.json')
 assert (d['implementation_hash']==IMPL and d['exit_code']==0 and d['source_and_tests_unchanged'] is True)
 assert next(row for row in probes if row['ref']==name)['source_case_executions']==1

native_path=BASE/'k03-native-aa2d00a-first/native-k03-observations.json'
native=load(native_path)
assert (native['passed'] is True and native['identity']==FACTS and native['source_package_unchanged'] is True
 and native['awake']['restored'] is True and native['native_worker_reaped'] is True
 and all(row['reaped'] is True for row in native['owned_cleanup'])
 and native['native_outbox_state']=='PENDING' and native['native_new_owner_command_count']==3
 and native['new_disclosure_observations']==1 and native['repeated_disclosure_observations']==0)
files.add(native_path)
stage=native_path.parent/'local-copy'
payload_paths=[p for p in stage.rglob('*') if p.is_file() and p.name!='.r7-root.json']
assert len(payload_paths)==3 and {p.name for p in payload_paths}==set(native['exact_three_payloads'])
parents={p.parent for p in payload_paths};assert len(parents)==1
logical=next(iter(parents)).relative_to(stage).as_posix()
payloads={p.name:p.read_bytes() for p in payload_paths}
assert validate_candidate_index_publication(logical,payloads)==native['index']
assert {name:sha(raw) for name,raw in payloads.items()}==native['local_copy_payload_hashes']
files.update(payload_paths)

names=(
 'run_owner_development_v03.py','run_k03_missing_seam_red.py','run_k03_missing_seam_red_v2.py',
 'k03-candidate-evidence-index-owner-plan-20261021.json',
 'k03-owner-outbox-implementation-draft-assumptions-20261021.json',
 'k03-owner-outbox-independent-static-review-20261021.json',
 'k03-actual-review-pins-20261021.json','k03-actual-review-pins-retry01-20261021.json',
 'k03-tracked-diff-250ed2d-review.patch','k03-tracked-diff-250ed2d-review-retry01.patch',
 'freeze_k03_inventory_awake.py','finish_k03_whitespace_bindings.py',
 'verify_k03_native_aa2d00a.py','verify_k03_native_aa2d00a_before_health_assertion.py.unapplied',
 'test_h01_joined_close_aa2d00a.py','h01_joined_close_extension.py.unapplied',
 'test_h01_joined_k05_aa2d00a.py','h01_joined_k05_extension.py.unapplied',
 'materialize_current_delivery_aa2d00a.py',
 'audit_l01_l05_committed_tree_aa2d00a.py','l01-l05-local-audit-rules-aa2d00a.json',
 'run_committed_tree_audit_aa2d00a.py','triage_committed_scan_aa2d00a.py',
 'l01-l05-audit-aa2d00a-refusal-retry01.json','l01-l05-root-triage-aa2d00a-20261021.json',
 'aa2d00a-independent-review-records.json',
 'review-record-private-archive-aa2d00a/aa2d00a-independent-review-records.json',
 'review-record-private-archive-aa2d00a/recovery.json')
files.update(BASE/name for name in names)
for folder in ('k03-inventory-freeze-first','k03-whitespace-final-bindings'):
 files.update(p for p in (BASE/folder).iterdir() if p.is_file())
for attempt in ('refusal-retry01','first'):
 files.update(BASE/('committed-tree-owned-aa2d00a-'+attempt)/name for name in ('checkpoint.json','stdout.log'))

scan_path=BASE/'l01-l05-audit-aa2d00a-first.json';raw_scan=scan_path.read_bytes();scan=json.loads(raw_scan)
triage=load(BASE/'l01-l05-root-triage-aa2d00a-20261021.json')
assert (scan['subject']['head']==REV and scan['final_subject_unchanged'] is True
 and scan['all_direct_git_children_reaped'] is True and scan['status']=='STOP_ROOT_REVIEW'
 and triage['scan_sha256']==sha(raw_scan)[7:] and triage['review']=='ROOT_SELF_REVIEW'
 and triage['unresolved_after_root_review']==0)
safe_scan=_sanitize(raw_scan.decode('utf-8'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').encode()
chunks=[]
for offset in range(0,len(safe_scan),384*1024):
 part=safe_scan[offset:offset+384*1024];ref='audit-part-'+str(len(chunks)+1).zfill(3)+'.json'
 document=dict(part=len(chunks)+1,byte_offset=offset,byte_length=len(part),text_hex=part.hex())
 raw=(json.dumps(document,indent=2)+'\n').encode();write_private_new(OUT/ref,raw)
 chunks.append(dict(ref=ref,hash=sha(raw)))

bindings=[]
for number,path in enumerate(sorted(files,key=lambda p:p.relative_to(PROJECT).as_posix()),1):
 _local_path(path)
 assert path.is_file() and path.stat().st_nlink==1 and path.stat().st_size<=8*1024**2
 raw=path.read_bytes();text=_sanitize(raw.decode('utf-8-sig'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').replace('\r','')
 safe=('\n'.join(line.rstrip(' \t') for line in text.splitlines()).rstrip()+'\n').encode()
 suffix=path.suffix if path.suffix in ('.py','.json','.log','.md','.patch','.unapplied','.html') else '.txt'
 ref='a'+str(number).zfill(4)+suffix
 write_private_new(OUT/ref,safe)
 assert (OUT/ref).read_bytes()==safe
 bindings.append(dict(original_ref=path.relative_to(PROJECT).as_posix(),original_hash=sha(raw),
  retained_ref=ref,retained_hash=sha(safe),normalization='PUBLIC_SANITIZATION_LF_TRAILING_WHITESPACE_ONLY'))

guard()
disposition=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',executable_revision=REV,identity=FACTS,
 scope='SUPPLEMENTAL_ACTUAL_NATIVE_SOURCE_AND_STATIC_EVIDENCE_OUTSIDE_FIXED_RECEIPT',master='IN_PROGRESS',
 recorded_at=datetime.now(timezone.utc).isoformat(),qualification_membership='NONE',development_probes=probes,
 native_k03='NATIVE_PRODUCER_QUEUE_RETRY_AND_STOPPED_SOURCE_READONLY_LOCAL_COPY_PASS;NATIVE_OUTBOX_PENDING',
 native_k03_cloud_ack='NOT_RUN;LOCAL_STAGED_SOURCE_TRANSPORT_AUDIT_ONLY',
 h01_h16='SAME_ORIGINAL_E2_ENTRY_EXIT_FUNDING_STOP_CLEANUP_CLOSED_FINALIZATION_SOURCE_SUPPLEMENT_PASS',
 k05='SAME_FINANCIAL_LINEAGE_READONLY_PRIVATE_SNAPSHOT_PUBLIC_OPT_POLICY_REDACTION_BUNDLE_SOURCE_SUPPLEMENT_PASS',
 financial_scope='CONTROLLED_FAKE_PROVIDER_WIRE_ONLY;NO_REAL_HTTP_OR_OPERATOR_PAPER',
 root_static_audit=dict(status=triage['status'],review='ROOT_SELF_REVIEW',
  original_scan_status=scan['status'],original_scan_hash=sha(raw_scan),sanitized_scan_hash=sha(safe_scan),
  encoding='HEX_OF_SANITIZED_UTF8_TEXT_CHUNKS',reconstruction='Decode text_hex in part order; concatenate and check sanitized_scan_hash.',
  parts=chunks,limits=scan['limits']),
 retained_files=bindings,additional_public_requests=0,cumulative_public_requests=8,cumulative_public_responses=8,
 private_requests=0,credentials='NONE',provider_mutation=0,capital='NONE',github_compute='NOT_USED')
write_private_new(OUT/'disposition.json',(json.dumps(disposition,indent=2)+'\n').encode())
entries=[dict(ref=p.name,hash=sha(p.read_bytes())) for p in sorted(OUT.iterdir()) if p.is_file()]
write_private_new(OUT/'prepared-manifest.json',(json.dumps(dict(revision=REV,identity=FACTS,
 scope=disposition['scope'],artifacts=entries),indent=2)+'\n').encode())
guard()
print(json.dumps(dict(prepared_files=len(entries),actual_development_probes=len(probes),audit_parts=len(chunks),
 source_unchanged=True,qualification_credit='NONE',master='IN_PROGRESS')),flush=True)
