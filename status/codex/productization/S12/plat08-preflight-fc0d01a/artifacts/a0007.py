"""Retain one exact source preflight checkpoint; no native/PLAT08 row credit."""
from pathlib import Path
import hashlib,json,subprocess,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import _sanitize,revision_fact
from strategy.v02.capabilities import _revision
REV='fc0d01a3ae54bb777238acacbfc9cad5a4b5317b'
revision_fact(ROOT,REV,True)
run='plat08-affected-'+REV[:7]
report=json.loads((BASE/run/'checkpoint.json').read_bytes())
assert report['passed'] and report['executable_revision']==REV and report['tests_run']==94
assert len(report['modules'])==11 and report['implementation_hash']==_revision()
assert report['source_and_tests_unchanged']
assert all(row['passed'] and row['tree_reaped'] and row['within_original_wall_limit'] for row in report['results'])
ids=[case for row in report['results'] for case in row['expected_case_ids']]
assert len(ids)==len(set(ids))==94
for ref,digest in report['test_file_hashes'].items():assert hashlib.sha256((ROOT/ref).read_bytes()).hexdigest()==digest
reviews=['plat08-preflight-implementation-review-20261021.json','plat08-preflight-final-delta-review-20261021.json']
final=json.loads((BASE/reviews[-1]).read_bytes());bindings=[]
for ref in reviews:
    review=json.loads((BASE/ref).read_bytes());assert review['counts']==dict(critical=0,important=0)
    for path,wanted in review['subject_hashes'].items():
        blob=subprocess.run(['git','show',REV+':'+path],cwd=ROOT,check=True,capture_output=True).stdout
        raw=(ROOT/path).read_bytes();canonical=raw.replace(b'\r\n',b'\n')
        assert canonical==blob.replace(b'\r\n',b'\n')
        actual=hashlib.sha256(raw).hexdigest()
        status='EXACT_REVIEWED_BYTES'
        if wanted not in (actual,hashlib.sha256(canonical).hexdigest(),hashlib.sha256(blob).hexdigest()):
            assert path in final['subject_hashes'] and final['subject_hashes'][path]==actual
            status='SUPERSEDED_BY_EXACT_FINAL_DELTA_REVIEW'
        bindings.append(dict(review_ref=ref,path=path,review_sha256=wanted,qualified_raw_sha256=actual,status=status))
awake_ref='plat08-exact-temporary-awake-'+REV[:7]+'.json'
awake=json.loads((BASE/awake_ref).read_bytes());assert awake['explicitly_released'] and not awake['permanent_settings_changed']
failed=json.loads((BASE/'plat08-complete-product-green04/checkpoint.json').read_bytes())
assert failed['exit_code']==1 and failed['source_and_tests_unchanged'] and failed['tree_reaped']
refs=[run+'/checkpoint.json','run_plat08_exact_source.py','plat08-exact-helper-binding.json',
    'run_owner_development_v03.py','keep_awake_for_validation.py',awake_ref,'retain_plat08_source.py',
    'plat08-preflight-restore-contract-review-20261020.json',*reviews,
    'plat08-schema-preflight-minimal-gap-plan-20261020.json',
    'plat08-wholeprofile-preflight-role-map-20261020.json',
    'plat08-preflight-first-test-draft-20261020.json','plat08-preflight-service-draft-assumptions-20261020.json',
    'plat08-complete-role-test-drafts-20261021.json']
for folder in ('plat08-product-preflight-red','plat08-product-preflight-red01','plat08-preflight-cli-red',
    'plat08-prefix-model-red','plat08-prefix-model-green01','plat08-product-preflight-green01',
    'plat08-product-preflight-green02','plat08-archival-contract-red','plat08-product-preflight-green03',
    'plat08-complete-identity-red','plat08-complete-product-green04','plat08-corrected-regressions-green05'):
    refs.extend((folder+'/checkpoint.json',folder+'/source.log'))
for row in report['results']:
    ref=run+'/'+row['log_ref']
    assert 'sha256:'+hashlib.sha256((BASE/ref).read_bytes()).hexdigest()==row['log_hash'];refs.append(ref)
prepared=[]
for ref in dict.fromkeys(refs):
    raw=(BASE/ref).read_bytes();safe=_sanitize(raw.decode('utf-8'),ROOT)
    for path,label in ((ROOT,'<SOURCE_ROOT>'),(PROJECT,'<PROJECT_ROOT>'),(Path.home(),'<HOME>')):
        for spelling in (str(path),path.as_posix(),str(path).replace('\\','\\\\')):safe=safe.replace(spelling,label)
    prepared.append((ref,raw,('\n'.join(line.rstrip() for line in safe.splitlines()).rstrip()+'\n').encode()))
out=ROOT/'status/codex/productization/S12'/('plat08-preflight-'+REV[:7])
if out.exists():raise ValueError('Fresh retained evidence required')
create_private_directory(out);create_private_directory(out/'artifacts');items=[]
for index,(ref,raw,safe) in enumerate(prepared,1):
    path=out/'artifacts'/(f'a{index:04d}'+Path(ref).suffix);write_private_new(path,safe)
    items.append(dict(original_ref=ref,original_hash='sha256:'+hashlib.sha256(raw).hexdigest(),retained_ref=path.relative_to(out).as_posix(),retained_hash='sha256:'+hashlib.sha256(safe).hexdigest()))
doc=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',status='PLAT08_PREFLIGHT_SCOPED_SOURCE_PASS',
    executable_revision=REV,implementation_hash=_revision(),exact_modules=11,exact_cases=94,
    source_and_tests_unchanged=True,children_reaped=True,per_module_limit_seconds=900,
    independent_review='TWO_COMPLEMENTARY_STATIC0C0I_EXECUTION_NONE',review_bindings=bindings,
    actual_flows=[
        'Normal actual four-present/four-absent and all-eight-present owner schemas -> create/verify complete backup -> target read-only preflight; all source DB/WAL/SHM and bundle bytes unchanged. Exact target provenance, source config hash and raw verified manifest binding retained.',
        'Genuine source queue/research extra indexes, control user_version and supervision receipt changes -> normal valid backup -> typed unsupported preflight and complete restore denied before destination creation. Real held owner role and expired reader budget deny; subsequent successful request proves locks released.',
        'Fresh actual canonical migrator prefix19 -> normal complete backup -> reports known pending suffix without source migration -> public product restore inhibited clone -> normal create_local_app applies packaged suffix to clone only; integrity/FK checks pass and RESTORED_INHIBITED persists.',
        'Generic arbitrary-only DB archival restore preserves bytes and DATABASES_ONLY/PENDING/inhibited state; actual canonical runtime owner still refuses that unversioned archive. E6 generation/lease fencing regressions now start from genuine canonical schema, with all original assertions retained.',
        'Actual migration cap accepts exact packaged prefix only, refuses unknown/backward cap and custom SQL directory; normal migration rollback, auth/session revocation, runtime supervision, API and owner composition regressions pass.'
    ],actual_failures_retained=[
        'Initial private-profile fixture setup errors, then actual missing service and CLI after genuine verified backup.',
        'Namespace model omission and archival overgate: failed green01 retained. Existing owner namespace shape added as finite second model; full gate restricted to product-data restore, dedicated generic archive RED then repaired.',
        'Identity output missing actual RED; minimal measured target/config/manifest bindings added.',
        'green04 remains FAILED with two root-mistyped nonexistent unittest modules; no failed-loader acceptance credit. Corrected actual regressions32PASS development, followed by exact-clean11module94case run.'
    ],scope='SOURCE_ONLY;NOT_NATIVE_CROSSVERSION_OR_WHOLE_PLAT08_OR_FULL_PQR',
    limitations=['Historical migration ledger has filenames/time only; no historical SQL checksum attestation.',
        'Compatibility is schema/layout suitability for an inhibited clone, not financial permission or complete logical data validation.',
        'Old sealed7d lacks new guard: rollback must use untouched old data or verified compatible old backup; no retroactive downgrade refusal claim.',
        'Native crossversion/install removal, final audits/S16 and final settled full/native inventory remain pending.'],
    awake='Validation-process-only system request explicitly released; no permanent power/display/away-mode changes.',
    preserved_qualified_windows='7d821f29837e95e46bcd5fe32f14d536a28c9aa8',native='NOT_RUN_FOR_THIS_SOURCE',master='IN_PROGRESS',
    public_requests_cumulative=8,public_responses_cumulative=8,additional_public_requests=0,private_requests=0,
    credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',artifacts=items)
write_private_new(out/'disposition.json',(json.dumps(doc,ensure_ascii=False,indent=2)+'\n').encode())
for item in items:assert 'sha256:'+hashlib.sha256((out/item['retained_ref']).read_bytes()).hexdigest()==item['retained_hash']
evidence=(out/'disposition.json').relative_to(ROOT).as_posix()
p=ROOT/'coordination/CODEX/PROGRESS.json';value=json.loads(p.read_bytes())
value.update(executable_revision=REV,candidate_executable_revision=REV,
    active_step='PLAT08_PREFLIGHT_SCOPED_SOURCE_PASS_FINAL_INVENTORY_NATIVE_PREPARATION',
    next_step='Refresh settled fixed inventory/offline authoring examples, exact candidate build/full local qualification; actual native crossversion/removal plus audits/S16 remain. Preserve old7d proof; external oldPC/Ubuntu/cloud/policies/real-forward unaccepted.')
value['plat08_preflight_source']=dict(revision=REV,implementation_hash=_revision(),modules=11,cases=94,status='SCOPED_SOURCE_PASS',evidence_ref=evidence,native='NOT_RUN',whole_clause='NOT_RUN')
p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
paragraph=f'''# PLAT08 read-only upgrade preflight source checkpoint — 2026-10-21

Exact source {REV}, implementation {_revision()}:11modules/94cases PASS,
unchanged/reaped, original900s per module. Evidence: {evidence}.
Two complementary independent static0C0I reviews, executionNONE. All initial
fixture/model/archival/identity/import-name failures retained. Temporary system
awake request explicitly released; no permanent power/display/away-mode change.

Actual8role all-present and absent inventory, normal verified backups, read-only
version/config/manifest bindings, genuine changed-schema/receipt/version denials
before product restore target creation. Real prefix19 backup reports suffix;
normal inhibited restore and product composition migrate clone only, source and
backup unchanged. Generic archival remains DATABASES_ONLY/PENDING/inhibited and
cannot open as a canonical product DB. Existing E6 fencing/auth/API/migration/
supervision regressions preserved. No historical SQL checksum/financial claim.

This source checkpoint is not native crossversion/removal/fullPQR/wholePLAT08.
Next settled inventory/authoring refresh, build and full native qualification,
actual portable crossversion/removal, audits and S16. Preserved7d package/proof
remain separate; no old7d downgrade-guard or new native acceptance transfer.
Master active, same task/branch, no merge. Public8/responses8/additional0/private0;
credentialsNONE/capitalNONE/LIVE notstarted/GitHubNOT_USED. OldPC/Ubuntu/cloud/
formal policies/real-forward remain unaccepted.

'''
for ref in ('coordination/CODEX/HANDOFF.md','status/codex/R7_PRODUCTIZATION_MASTER_COMPLETION_20261002.md'):
    p=ROOT/ref;p.write_text(paragraph+p.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print(json.dumps(dict(evidence_ref=evidence,artifacts=len(items),exact_cases=94,native='NOT_RUN',master='IN_PROGRESS')))
