"""Prepare only selected public evidence; leaves the qualified source tree clean."""
from pathlib import Path
import hashlib,json,re,sys

BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
REV='3ae6460c69a8a8f90588c396b819af7079e7546d'
sys.path[:0]=[str(BASE),str(ROOT),str(ROOT/'src')]
from application.paper.producer import _guard
from application.paper.inventory import current_target,fixed_profile
from application.platform.distribution import verify_distribution
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import _sanitize
from retain_current_checkpoint import CapturedEvidence,sha

def require(value,message):
    if not value:raise ValueError(message)

def run():
    facts=verify_distribution(BASE/'build-3ae6460/dist/R7');profile=fixed_profile(current_target())
    guard=lambda:_guard(ROOT,REV,BASE/'build-3ae6460/dist/R7',facts,profile)
    guard();captured=CapturedEvidence(PROJECT);refs=set()
    def document(ref):
        path=BASE/ref;refs.add(path);return captured.document(path)
    def add(ref,expected=None):
        path=BASE/ref;captured.capture(path,expected);refs.add(path)
    q=document('qualify-3ae6460-first/checkpoint.json')
    require(q['passed'] is True and q['revision']==REV,'Actual full owning run must finish first')
    def public_flow(ref,identity):
        row=document(ref+'/observations.json')
        require(row['identity']==identity,'Supplemental child native identity differs')
        require(len(row['commands'])<=32,'Finite public command inventory required')
        for command in row['commands']:
            label=command['command']
            require(re.fullmatch('[a-z][a-z0-9-]{0,100}',label) and command['log']==label+'.log','Exact public stage log required')
            require(command.get('tree_reaped') is True,'Actual child cleanup missing')
            if 'exit_code' in command:require(command['exit_code']==command['expected_exit_code'],'Unexpected actual command result')
            else:require(command.get('managed_stop') is True and command.get('forced_cleanup') is False,'Actual normal managed stop required')
            add(ref+'/'+command['log'],command['log_hash'])
        return row
    cross=document('plat08-native-3ae6460-retry01/plat08-native-result.json')
    require(cross['passed'] is True and cross['new_identity']==facts and cross['errors']==[] and cross['cleanup_errors']==[],
        'Actual native crossversion completion required')
    require(cross['original_source_unchanged'] and cross['original_backup_unchanged'] and len(cross['old_migrations'])==19
        and len(cross['new_migrations'])==24 and len(cross['removed'])==2 and all(row['reaped'] for row in cross['owned_cleanup']),
        'Actual clone-only upgrade/removal/source preservation required')
    public_flow('plat08-native-3ae6460-retry01/old-control',cross['old_identity'])
    public_flow('plat08-native-3ae6460-retry01/new-control',facts)
    failed=document('plat08-native-3ae6460-first/plat08-native-result.json')
    require(failed['passed'] is False and failed['cleanup_errors']==[] and all(row['reaped'] for row in failed['owned_cleanup']),
        'Preserved actual first failure/reaping required')
    public_flow('plat08-native-3ae6460-first/old-control',cross['old_identity'])
    future=document('plat08-future-3ae6460-first/native-future-refusal-result.json')
    require(future['passed'] is True and future['identity']==facts and future['errors']==[] and future['cleanup_errors']==[]
        and future['preflight_restore_all_source_unchanged'] and future['startup_canonical_unchanged']
        and future['source_files_changed_during_startup']==['process-supervision.sqlite'],
        'Actual current native future-schema refusal and truthful mutation scope required')
    public_flow('plat08-future-3ae6460-first/native-control',facts)
    supplement=document('b03-m04-f11-3ae6460-first/supplemental-assertions.json')
    require(supplement['passed'] is True and supplement['identity']==facts and supplement['errors']==[] and supplement['cleanup_errors']==[]
        and {row['requirement_id'] for row in supplement['records']}=={'B03','M04','F11'}
        and all(row['status']=='PASS' for row in supplement['records']),'Actual missing user-flow assertions required')
    allowed=BASE/'b03-m04-f11-3ae6460-first'
    proof_root=PROJECT/'artifacts/q-3ae6460-first/qualification'
    for row in supplement['records']:
        for ref,expected in row['artifact_hashes'].items():
            path=PROJECT/ref
            require((path.is_relative_to(allowed) and path.name!='product.json' and path.suffix in ('.json','.log'))
                or (path.is_relative_to(proof_root) and path.name=='native-observations.json')
                or path==BASE/'b03-m04-f11-supplement-source-pins.unapplied.json','Only declared public supplement evidence may be read')
            captured.capture(path,expected);refs.add(path)
    scan=document('l01-l05-audit-3ae6460-first.json');outer=document('committed-tree-owned-first/checkpoint.json')
    triage=document('l01-l05-root-triage-3ae6460-20261021.json')
    require(scan['requested_head']==REV and outer['source_revision']==REV and outer['outer_tree_reaped'] is True
        and outer['source_unchanged'] is True and triage['unresolved_after_root_review']==0 and triage['confirmed_real_secrets']==0
        and triage['hosted_runner_or_trigger_findings']==0
        and triage['scan_sha256']==hashlib.sha256(captured.bytes[BASE/'l01-l05-audit-3ae6460-first.json']).hexdigest(),
        'Actual scoped scan, owner cleanup and completed root triage required')
    audit=document('j10-l03-l06-final-candidate-delta-binding-20261021.json')
    require(audit['final_candidate_subject']==REV and audit['native_deadlines_and_assertions_unchanged'] is True,
        'Current static audit delta binding required')
    fixed=[
        'prepare_current_supplement_archive.py','verify_plat08_crossversion_native.py','verify_plat08_current_future_refusal.py',
        'plat08-native-crossversion-draft-plan-20261021.json','plat08-crossversion-native-helper-review-20261021.json',
        'plat08-crossversion-native-helper-final-review-20261021.json','plat08-acl-future-refusal-static-review-20261021.json',
        'plat08-native-live-source-acl-diagnostic-20261021.json','plat08-current-native-future-refusal-plan-20261021.json',
        'test_plat08_helper_lifecycle.py','plat08-helper-lifecycle-green.log','plat08-helper-lifecycle-green-retry01.log',
        'verify_b03_m04_f11_supplement.py','verify_b03_m04_f11_supplement.py.unapplied',
        'b03-m04-f11-supplement-apply-recipe-20261021.json','b03-m04-f11-supplement-source-pins.unapplied.json',
        'b03-m04-f11-supplement-static-review-20261021.json','b03-m04-f11-supplement-final-review-20261021.json',
        'b03-m04-f11-supplement-final-review-retry01-20261021.json','test_b03_supplement_reference_guards.py',
        'b03-supplement-reference-guards-green.log','b03-supplement-reference-guards-final-green.log',
        'audit_l01_l05_committed_tree_owned_v4_20261021.py','l01-l05-local-audit-rules-v4-20261021.json',
        'run_committed_tree_audit_owned.py','triage_committed_scan_root.py','j10-l03-l06-static-audit-fc0d01a-20261021.json',
        'settled-inventory-refresh-audit-20261021.json','s16-final11-semantic-closure-and-current-binding-recipe-20261021.json',
        'direct-resource-retention-final-review-20261021.json','record-current-resource-projection-final-review-20261021.json',
        'record_current_windows_checkpoint_before_direct_resource.py',
        'k03-candidate-evidence-index-owner-plan-20261021.json','k03-owner-outbox-implementation-draft-assumptions-20261021.json',
        'k03-owner-outbox-independent-static-review-20261021.json','test_candidate_index_roundtrip_v02.py.unapplied',
        'test_candidate_index_roundtrip_v02_v2.py.unapplied','candidate_index.py.unapplied',
        '0010_candidate_index_outbox.sql.unapplied','research_candidate_index_methods.py.unapplied',
        'registry_candidate_reference_getter.py.unapplied','run_k03_missing_seam_red.py',
        'k03-missing-owner-red-3ae6460-first/checkpoint.json','k03-missing-owner-red-3ae6460-first/execution.log']
    fixed += ['current-supplement-archive-final-review-20261021.json', 'prepare_current_supplement_archive_before_history_refs.py', 'preparer-history-literal-binding-20261021.json', 'l01-l05-audit-3ae6460-refusal.json', 'l01-l05-audit-3ae6460-refusal-retry01.json', 'committed-tree-owned-refusal/stdout.log', 'committed-tree-owned-refusal-retry01/checkpoint.json', 'committed-tree-owned-refusal-retry01/stdout.log', 'committed-tree-owned-first/stdout.log', 'plat08-native-temporary-awake-3ae6460.json', 'settled-inventory-temporary-awake.json', 'plat08-failed-helper-byte-recovery-20261021.json', 'plat08-failed-helper-byte-recovery-retry01-20261021.json', 'run_b03_m04_f11_awake.py', 'b03-m04-f11-temporary-awake-3ae6460.json', 'run_k03_missing_seam_red_v2.py', 'k03-missing-owner-red-v2-3ae6460-first/checkpoint.json', 'k03-missing-owner-red-v2-3ae6460-first/execution.log', 'b03-m04-f11-arguments-3ae6460.json']
    for ref in fixed:add(ref)
    prepared=[]
    for path in sorted(refs):
        raw=captured.capture(path);text=_sanitize(raw.decode('utf-8-sig'),ROOT)
        for root,label in ((ROOT,'<SOURCE_ROOT>'),(PROJECT,'<PROJECT_ROOT>'),(Path.home(),'<HOME>')):
            for spelling in (str(root),root.as_posix(),str(root).replace('\\','\\\\')):text=text.replace(spelling,label)
        safe=('\n'.join(line.rstrip() for line in text.splitlines()).rstrip()+'\n').encode()
        prepared.append((path,raw,safe))
    guard()
    output=BASE/'supplements-3ae6460-prepared';require(not output.exists(),'Fresh public prepared archive required')
    create_private_directory(output);bindings=[];artifacts=[]
    for number,(path,raw,safe) in enumerate(prepared,1):
        ref=f'a{number:04d}'+path.suffix;write_private_new(output/ref,safe)
        bindings.append(dict(original_ref=path.relative_to(PROJECT).as_posix(),original_hash=sha(raw),retained_ref=ref,retained_hash=sha(safe)))
        artifacts.append(dict(ref=ref,hash=sha(safe)))
    disposition=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',executable_revision=REV,identity=facts,
        scope='SUPPLEMENTAL_ACTUAL_NATIVE_AND_STATIC_EVIDENCE_OUTSIDE_FIXED_RECEIPT',master='IN_PROGRESS',
        crossversion='ACTUAL_CLONE_ONLY_19_TO24_AND_TWO_PORTABLE_REMOVALS_PASS',future_schema='ACTUAL_CURRENT_NATIVE_REFUSAL_PASS',
        future_wrapper_started_at_utc='UNKNOWN_NOT_RECORDED',future_wrapper_finished_at_utc='UNKNOWN_NOT_RECORDED',
        future_wrapper_os_toolchain='UNKNOWN_NOT_RECORDED;NOT_BORROWED_FROM_OTHER_RUNS',
        user_flow_assertions=['B03_MANIFEST_LAST','M04_SAME_PARTIAL_TO_ONE_TERMINAL_REPORT','F11_ACTUAL_STOPPED_CANONICAL_COSTS'],
        audits='CURRENT_COMMITTED_UTF8_PATTERN_SCAN_ROOT_TRIAGE_AND_REVIEWED_CORE_DELTA_ONLY',
        k03='ACTUAL_MISSING_OWNER_RED;UNAPPLIED_DESIGN_ONLY;NOT_ACCEPTED',
        limitations=['No whole Master, Ubuntu/old target, real cloud, formal policy, real-forward, LIVE or capital acceptance.',
            'Future-schema startup may update supervision only; no overall zero-DB-mutation or old7d downgrade-guard claim.',
            'Static scan excludes ancestry/binary/ignored/untracked/encoded-secret absence; root triage is self-review.',
            'Supplemental IDs are outside actual fixed owning receipt; no invented receipt check or per-case native timestamp.'],
        cumulative_public_requests=8,cumulative_public_responses=8,additional_public_requests=0,private_requests=0,
        credentials='NONE',capital='NONE',github_compute='NOT_USED',retained_files=bindings)
    raw=(json.dumps(disposition,indent=2)+'\n').encode();write_private_new(output/'disposition.json',raw)
    artifacts.append(dict(ref='disposition.json',hash=sha(raw)))
    manifest=dict(revision=REV,identity=facts,scope=disposition['scope'],artifacts=artifacts)
    write_private_new(output/'prepared-manifest.json',(json.dumps(manifest,indent=2)+'\n').encode())
    guard();print(json.dumps(dict(prepared=output.name,files=len(artifacts),manifest_hash=sha((output/'prepared-manifest.json').read_bytes()))))

if __name__=='__main__':run()
