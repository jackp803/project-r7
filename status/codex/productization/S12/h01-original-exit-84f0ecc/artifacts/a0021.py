"""Retain original E2 EXIT/source checks for their exact separate subjects."""
from pathlib import Path
import hashlib,json,subprocess,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
QUAL=PROJECT/'workspaces/project-r7-qualification-84f0ecc'
sys.path[:0]=[str(QUAL/'src'),str(QUAL)]
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import _sanitize,revision_fact
from strategy.v02.capabilities import _revision
REV='84f0eccf76167af11b9b4e67fc69af880ebe44ae'
SUPP='8e81fa2d2996f8c18d06534408c9c3170c62bfee'
revision_fact(QUAL,REV,True)
run='h16-finalization-h01exit-affected-'+REV[:7]
tail='h16-finalization-h01exit-corruption-'+SUPP[:7]
report=json.loads((BASE/run/'checkpoint.json').read_bytes())
supplement=json.loads((BASE/tail/'checkpoint.json').read_bytes())
for r,revision,count in ((report,REV,112),(supplement,SUPP,1)):
    assert r['passed'] and r['executable_revision']==revision and r['tests_run']==count
    assert r['implementation_hash']==_revision() and r['source_and_tests_unchanged']
    assert all(row['passed'] and row['tree_reaped'] and row['within_original_wall_limit'] for row in r['results'])
assert len(report['modules'])==29 and len(supplement['modules'])==1
changed=subprocess.run(['git','diff','--name-only',REV,SUPP],cwd=ROOT,check=True,capture_output=True,text=True).stdout.splitlines()
assert changed==['tests/product/test_trading_exit_decision_corruption_v02.py']
for ref,wanted in report['test_file_hashes'].items():assert hashlib.sha256((QUAL/ref).read_bytes()).hexdigest()==wanted
case_ids=[case for r in (report,supplement) for row in r['results'] for case in row['expected_case_ids']]
assert len(case_ids)==len(set(case_ids))==113
review_refs=['h01-original-exit-implementation-review-initial-20261020.json','plat08-writer-guard-review-20261020.json']
review_bindings=[]
for ref in review_refs:
    review=json.loads((BASE/ref).read_bytes());counts=review.get('counts',review)
    assert counts['critical']==counts['important']==0
    for path,wanted in review['subject_hashes'].items():
        blob=subprocess.run(['git','show',REV+':'+path],cwd=ROOT,check=True,capture_output=True).stdout
        raw=(QUAL/path).read_bytes();canonical=raw.replace(b'\r\n',b'\n')
        assert canonical==blob.replace(b'\r\n',b'\n')
        assert wanted in (hashlib.sha256(blob).hexdigest(),hashlib.sha256(canonical).hexdigest())
        review_bindings.append(dict(review_ref=ref,path=path,review_sha256=wanted,
            qualified_raw_sha256=hashlib.sha256(raw).hexdigest(),lf_canonical_sha256=hashlib.sha256(canonical).hexdigest()))
awake_ref='h01-exit-exact-temporary-awake-'+REV[:7]+'.json'
awake=json.loads((BASE/awake_ref).read_bytes());assert awake['explicitly_released'] and not awake['permanent_settings_changed']
refs=[run+'/checkpoint.json',tail+'/checkpoint.json','run_h01_exit_exact_isolated.py',
    'run_finalization_exact_source.py','run_owner_development_v03.py','keep_awake_for_validation.py',awake_ref,
    'h01-exit-development-temporary-awake01.json','h01-exit-recovery-development-awake01.json',
    'h01-original-exit-management-join-design-20261020.json','h01-original-exit-management-join-design-review-20261020.json',
    'h01-original-exit-positive-draft-recipe-20261020.json','h01-original-exit-storage-draft-assumptions-20261020.json',
    'h01-original-exit-schema-test-draft-20261020.json','h01-exit-negative-recovery-drafts-recipe-20261020.json',
    'h01-exit-decision-corruption-draft-recipe-20261020.json','plat08-schema-preflight-minimal-gap-plan-20261020.json',
    'plat08-migration-writer-draft-assumptions-20261020.json','apply_h01_exit_positive.py','apply_h01_exit_storage.py',
    'retain_h01_original_exit.py',*review_refs]
for folder in ('h01-original-exit-red','h01-original-exit-green01','h01-original-exit-schema-development01',
    'h01-exit-negative-recovery-development01','h01-exit-decision-corruption-development01',
    'plat08-migration-writer-red','plat08-migration-writer-green01'):
    refs.extend((folder+'/checkpoint.json',folder+'/source.log'))
for folder,r in ((run,report),(tail,supplement)):
    for row in r['results']:
        ref=folder+'/'+row['log_ref'];assert 'sha256:'+hashlib.sha256((BASE/ref).read_bytes()).hexdigest()==row['log_hash'];refs.append(ref)
refs=list(dict.fromkeys(refs));prepared=[]
for ref in refs:
    raw=(BASE/ref).read_bytes();safe=_sanitize(raw.decode('utf-8'),QUAL)
    for path,label in ((QUAL,'<QUALIFIED_SOURCE_ROOT>'),(ROOT,'<SOURCE_ROOT>'),(PROJECT,'<PROJECT_ROOT>'),(Path.home(),'<HOME>')):
        for spelling in (str(path),path.as_posix(),str(path).replace('\\','\\\\')):safe=safe.replace(spelling,label)
    safe=('\n'.join(line.rstrip() for line in safe.splitlines()).rstrip()+'\n').encode()
    prepared.append((ref,raw,safe))
out=ROOT/'status/codex/productization/S12'/('h01-original-exit-'+REV[:7])
create_private_directory(out);create_private_directory(out/'artifacts');items=[]
for index,(ref,raw,safe) in enumerate(prepared,1):
    path=out/'artifacts'/(f'a{index:04d}'+Path(ref).suffix);write_private_new(path,safe)
    items.append(dict(original_ref=ref,original_hash='sha256:'+hashlib.sha256(raw).hexdigest(),retained_ref=path.relative_to(out).as_posix(),retained_hash='sha256:'+hashlib.sha256(safe).hexdigest()))
doc=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',status='ORIGINAL_E2_EXIT_AND_MIGRATION_WRITER_SCOPED_SOURCE_PASS',
    executable_revision=REV,supplemental_test_revision=SUPP,implementation_hash=_revision(),
    exact_main_cases=112,exact_main_modules=29,exact_supplemental_cases=1,unique_supporting_cases=113,
    count_limit='113 distinct supporting cases across two separate exact-clean revisions; supplement is test-only append, same implementation. Not113 at oneSHA or wholePQR/native acceptance.',
    source_and_tests_unchanged=True,children_reaped=True,per_module_limit_seconds=900,
    independent_reviews='TWO_STATIC0C0I_EXECUTION_NONE',review_bindings=review_bindings,
    flows=['Genuine E2 entry/full native fill/active original stop -> OPEN_PROTECTED; original earliest-fill E5 anchor HOLD -> original max-hold E5 EXIT with exact reason/action -> one guarded close -> partial -> sameposId zero EXIT_REQUESTED. Expired original proof/action and duplicate retries only GET, no renewed clocks or secondPOST.',
      'Current/copied/expired/mismatched native-read denials, actual PREPARED-before-claim interruption and cold-cache refusal, actual canonical EXIT action commits then exception, genuinely new owners/handles/provider[]/process2 drain unchanged original action and receipt without HTTP, originalE7release1 and stale owner fenced.',
      'Nine exact immutable anchor/decision/receipt UPDATE/DELETE/REPLACE attacks denied with recursiveOFF/FKON and full table snapshots unchanged; separate UNIQUE-only collision coverage unclaimed. Actual altered reason/time/genuine earlier binding denied before new decision/action/provider effect.',
      'Actual canonical writer refuses unknown future/gapped/unversioned databases before writes; exact source bytes/directory unchanged. Bounded read-only prefix/schema facts; malformed/view/null/extra/generated/duplicate/empty-populated cases and existing real SQLite migration-fault/rollback paths pass. No historical migration checksum or whole-profile compatibility claim.'],
    actual_red='Original exit missing-entrypoint1ERROR only after genuine protected actual entry graph; migration writer1owncase/3real failures. All originals retained; new source joins/guard then scoped regressions pass.',
    scope='FIXTURE/FAKE_PROVIDER_VERIFICATION EXIT-only source components, not wholeH01/LIVE-code-complete, fullPQR, native or ordinary software qualification transfer.',
    current_continuation='Main source has subsequent unqualified prefix-model/preflight CLI/restore work in progress; excluded from84f0ecc/8e81fa2 proof. Verified backup must pass whole8role target-schema check before restore target creation; implementation underway.',
    awake='Validation-process-only system request explicitly released; no permanent power/display/awaymode settings changed.',
    preserved_qualified_windows='7d821f29837e95e46bcd5fe32f14d536a28c9aa8',native='NOT_RUN_FOR_THIS_SOURCE',master='IN_PROGRESS',
    public_requests_cumulative=8,public_responses_cumulative=8,additional_public_requests=0,private_requests=0,
    credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',artifacts=items)
write_private_new(out/'disposition.json',(json.dumps(doc,ensure_ascii=False,indent=2)+'\n').encode())
for item in items:assert 'sha256:'+hashlib.sha256((out/item['retained_ref']).read_bytes()).hexdigest()==item['retained_hash']
evidence=(out/'disposition.json').relative_to(ROOT).as_posix();p=ROOT/'coordination/CODEX/PROGRESS.json';value=json.loads(p.read_bytes())
value.update(executable_revision=SUPP,candidate_executable_revision=SUPP,active_step='H01_ORIGINAL_EXIT_SCOPED_SOURCE_PASS_PLAT08_WHOLEPROFILE_PREFLIGHT_IN_PROGRESS',next_step='Complete normal target8role preflight/restore gates and role/native crossversion tests; audits/S16/final settled inventory/examples/fullsource/native remain. External oldPC/Ubuntu/cloud/policies/real-forward remain unaccepted.')
value['h01_original_exit_scoped_source']=dict(executable_revision=REV,supplemental_test_revision=SUPP,main_cases=112,supplemental_cases=1,evidence_ref=evidence,native='NOT_RUN_FOR_THIS_SOURCE')
p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
note=f'''# Original E2 EXIT and migration-writer source checkpoint — 2026-10-20

Exact frozen source {REV}:29modules/112cases PASS; separate test-only append
{SUPP}:1corruption case PASS, same implementation {_revision()}.
Evidence: {evidence}. All unchanged/reaped, original per-module900s.
Two independent static0C0I reviews; executionNONE. Separate113 supporting cases
are not113 at oneSHA or full PQR/native qualification. LF-canonical source and
actual checked-out raw hashes retained. Temporary system-awake request released.

Actual original E2 entry/fill/stop/protection -> first-fill HOLD/max-hold E5 EXIT
retains exact action/reason/time, one close -> partial -> sameposId flat, still
EXIT_REQUESTED. Claimed stale/duplicate retries GET only. Copied/expired/mismatched
native inputs and lost unclaimed preparation deny; actual committed-action error
recovers with genuinely new owner/handles/process2 and zero HTTP. OriginalE7release1,
stale owner fencing and immutable3table attacks preserved. Existing close/intent/
projection/protected-close/funded-finalization/E5/dispatch/admission regressions pass.

Migration writer rejects future/gapped/malformed/unversioned schemas before writes;
no whole-profile/downgrade/native claim. New main prefix-model/preflight CLI/restore
work is still unqualified and excluded from this evidence. Whole8role normal
preflight/restore/crossversion, audits/S16 and final settled full/native remain.
Controlled source EXIT-only is not wholeH01 or LIVE-code-complete. Qualified
Windows7d package remains separate; Master active, same task/branch, no main merge.
Public8/responses8/additional0/private0; credentialsNONE/capitalNONE/LIVE notstarted/
GitHubNOT_USED. OldPC/Ubuntu/cloud/formal policies/real-forward remain unaccepted.

'''
for ref in ('coordination/CODEX/HANDOFF.md','status/codex/R7_PRODUCTIZATION_MASTER_COMPLETION_20261002.md'):
    p=ROOT/ref;p.write_text(note+p.read_text(encoding='utf-8'),encoding='utf-8',newline='\n')
print(json.dumps(dict(status=doc['status'],main_cases=112,supplemental_cases=1,retained=len(items),evidence_ref=evidence)))
