"""Sanitized, allowlisted evidence after all exact-clean executions finish."""
from dataclasses import asdict
import hashlib,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from application.config import load_config
from application.qualification import _sanitize
from application.paper.inventory import current_target,fixed_profile
from application.paper.producer import _guard,native_artifacts
from application.paper.producer import native_assertions
from application.paper.qualification import validate_qualified_receipt,artifact_bytes
from application.platform.distribution import verify_distribution
from application.platform.supervision import config_hash
from strategy.v02.capabilities import build_capability_snapshot
from storage.qualification import open_qualification_receipts
from verify_portable_checkpoint import archive_subject,validate_authoring
from application.cloud.feedback import validate_feedback_publication
def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()

LOG_LABELS={
    'build':('native-build',),
    'portable':('export-capabilities','author-engineering-example'),
    'unattended':('software-before','author-actual-engineering-input','normal-configure-research','actual-running-status','normal-stop-coordinator','software-after'),
    'qualified-backup':('original-software-before','backup-owning-store','verify-owning-backup','restore-owning-store','restored-software-denied','backup-restored-store','verify-restored-rebackup','original-software-after'),
    'headless':('init-headless','select-headless-diagnostic','second-coordinator-denied','stop-first-coordinator','stop-first-coordinator-repeat','stop-recovered-coordinator','stop-recovered-coordinator-repeat'),
    'sessions':('coordinator-first','coordinator-crash','coordinator-recovered')}

def canonical_log(root,label,ref,labels):
    if label not in labels or ref!=label+'.log':raise ValueError('Canonical public stage log required')
    return root/(label+'.log')

def exact_public_logs(root,names):
    observed={p.name for p in root.glob('*.log')}
    if observed!=set(names):raise ValueError('Unexpected or missing stage log')
    return {root/name for name in names}

class CapturedEvidence:
    def __init__(self,root):self.root=Path(root);self.bytes={}
    def capture(self,path,expected=None):
        path=Path(path);ref=path.relative_to(self.root).as_posix()
        raw=artifact_bytes(self.root,ref)
        if expected is not None and sha(raw)!=expected:raise ValueError('Evidence commitment differs')
        if path in self.bytes and self.bytes[path]!=raw:raise ValueError('Captured evidence changed')
        self.bytes[path]=raw
        return raw
    def document(self,path):return json.loads(self.capture(path))

def require_stage_bindings(checkpoints,revision,facts,owning,receipt_ref):
    if any(row.get('passed') is not True or row.get('revision')!=revision for row in checkpoints.values()):
        raise ValueError('Complete exact-subject stages required')
    for name in ('portable','unattended','qualified-backup'):
        if checkpoints[name].get('identity')!=facts:raise ValueError('Ancillary identity differs')
    for name in ('unattended','qualified-backup'):
        row=checkpoints[name]
        if (row.get('owning_profile')!=owning or row.get('all_owned_tree_reaped') is not True
                or row.get('source_and_package_unchanged') is not True):
            raise ValueError('Stopped same owning profile required')
    backup=checkpoints['qualified-backup'];portable=checkpoints['portable'];automatic=checkpoints['unattended']
    if (backup.get('receipt_ref')!=receipt_ref or backup.get('actual_receipt_equal_across_four_stores') is not True
            or backup.get('source_diagnostic_histories_unchanged') is not True
            or backup.get('restored_native_software_admission')!='DENIED'
            or portable.get('source_unchanged') is not True or portable.get('complete_bytes_identical') is not True
            or portable.get('first_run',{}).get('passed') is not True or automatic.get('public_source_unchanged') is not True):
        raise ValueError('Actual ancillary closure incomplete')
    for name in ('build','qualify','headless','native04'):
        if checkpoints[name].get('source_unchanged') is not True:raise ValueError('Source guard missing')

def run(revision,qualification_attempt='first'):
    from run_current_checkpoint import qualification_output
    stages={name:BASE/(name+'-'+revision[:7]+'-first') for name in ('build','qualify','headless','native04','portable','unattended','qualified-backup')}
    stages['qualify']=qualification_output(revision,qualification_attempt)
    captured=CapturedEvidence(PROJECT)
    checkpoints={name:captured.document(path/'checkpoint.json') for name,path in stages.items()}
    if any(not row['passed'] or row['revision']!=revision for row in checkpoints.values()):raise ValueError('Complete actual scoped stages required')
    package=BASE/('build-'+revision[:7])/'dist/R7';facts=verify_distribution(package);profile=fixed_profile(current_target())
    _guard(ROOT,revision,package,facts,profile)
    config=load_config(stages['qualify']/'product.json');q=checkpoints['qualify']['result']
    with open_qualification_receipts(config.database_path,namespace='LOCAL_RESEARCH') as reader:receipt=reader.get(q['receipt_ref'])
    source=config.local_data_root/'qualification'/receipt.execution_id
    validate_qualified_receipt(receipt,profile,artifact_root=source,measured={**facts,'platform_id':current_target(),'capability_hash':build_capability_snapshot().snapshot_hash})
    owning=dict(config_ref=(stages['qualify']/'product.json').relative_to(PROJECT).as_posix(),
        data_root_ref=config.local_data_root.relative_to(PROJECT).as_posix(),canonical_ref=config.database_path.relative_to(PROJECT).as_posix(),
        product_instance_id=config.product_instance_id,config_hash=config_hash(config))
    require_stage_bindings(checkpoints,revision,facts,owning,receipt.receipt_id)
    if (q.get('receipt_ref')!=receipt.receipt_id or q.get('execution_id')!=receipt.execution_id
            or q.get('executable_revision')!=revision or q.get('build_hash')!=facts['build_hash'] or q.get('groups_completed')!=7):
        raise ValueError('Owning result differs from actual typed receipt')
    archive,metadata,packed=archive_subject(BASE/('build-'+revision[:7]),revision,facts)
    captured.capture(BASE/('build-'+revision[:7])/'build-result.json',sha(metadata))
    portable=checkpoints['portable']
    if (portable.get('archive_ref')!=archive.relative_to(PROJECT).as_posix() or portable.get('archive_hash')!=sha(packed)
            or verify_distribution(PROJECT/portable['installation_ref'])!=facts
            or checkpoints['build'].get('result',{}).get('identity')!=facts):
        raise ValueError('Actual portable and build identity differ')
    index=captured.document(BASE/('execution-index-'+revision[:7]+'.json'))
    if (index.get('revision')!=revision or index.get('identity')!=facts or index.get('receipt_ref')!=receipt.receipt_id
            or index.get('execution_id')!=receipt.execution_id or index.get('profile_hash')!=receipt.profile_hash):
        raise ValueError('Actual execution index subject differs')
    target=ROOT/'status/codex/productization/S12'/('current-windows-'+revision[:7])
    if target.exists():raise ValueError('Fresh evidence archive required')
    paths={source/'preflight.json',source/'result.json',BASE/('build-'+revision[:7])/'build-result.json',BASE/('execution-index-'+revision[:7]+'.json')}
    for member in receipt.execution_evidence['members']:
        for row in member['artifacts']:
            path=source/row['ref'];captured.capture(path,row['hash']);paths.add(path)
    for name,path in stages.items():
        paths.add(path/'checkpoint.json')
        if name in ('unattended','qualified-backup','build'):
            names=[label+'.log' for label in LOG_LABELS[name]]
            if name=='unattended':names.append('actual-coordinator.log')
            paths.update(exact_public_logs(path,names))
            if name=='build':paths.add(path/'native-build-execution.json')
        elif name=='headless':
            paths.update(exact_public_logs(path/'execution',[label+'.log' for key in ('headless','sessions') for label in LOG_LABELS[key]]))
            paths.add(path/'execution/observations.json')
        elif name=='portable':
            paths.update(exact_public_logs(path,[label+'.log' for label in LOG_LABELS[name]]))
            paths.update(path/(label+'-execution.json') for label in LOG_LABELS[name])
            smoke=path/'first-run-smoke';smoke_report=captured.document(smoke/'pqr-result.json')
            paths.add(smoke/'pqr-result.json');paths.add(smoke/'native-smoke.json')
            for ref,commitment in native_artifacts(smoke_report,smoke).items():
                raw=captured.capture(smoke/ref,commitment);paths.add(smoke/ref)
            kit=path/'chat-authoring-kit';expected={'README.md','authoring-reference.md','engineering-example-not-gpt.json','capabilities.json','version.json','engineering-package/manifest.json','engineering-package/strategy.json'}
            if {p.relative_to(kit).as_posix() for p in kit.rglob('*') if p.is_file()}!=expected:
                raise ValueError('Canonical public authoring kit required')
            authoring=checkpoints[name]['authoring']
            for ref,commitment in validate_authoring(kit,authoring['capability_export'],authoring['actual_package']).items():
                captured.capture(kit/ref,commitment);paths.add(kit/ref)
        elif name=='native04':
            workspace=path/'execution';report_path=workspace/'pqr-result.json'
            report=captured.document(report_path);paths.add(report_path)
            member=next(g['members'][0] for g in profile['groups'] if g['check_id']=='PQR-04')
            native_assertions(report,member,workspace)
            declared_bindings=native_artifacts(report,workspace)
            if 'native-observations.json' not in declared_bindings:raise ValueError('Native04 primary observation required')
            primary=captured.document(workspace/'native-observations.json')
            if primary.get('passed') is not True or primary.get('identity')!=facts or primary.get('group')!='PQR-04':
                raise ValueError('Scoped native04 preflight subject differs')
            for ref,commitment in declared_bindings.items():
                declared=workspace/ref;raw=captured.capture(declared,commitment);paths.add(declared)
                if ref=='native-observations.json':
                    observed=json.loads(raw)
                    if observed.get('passed') is not True or observed.get('identity')!=facts or observed.get('group')!='PQR-04':
                        raise ValueError('Scoped native04 preflight subject differs')
    headless=stages['headless']/'execution';observed=captured.document(headless/'observations.json')
    if observed.get('passed') is not True or observed.get('identity')!=facts or observed.get('namespace')!='LOCAL_RESEARCH':
        raise ValueError('Actual diagnostic headless subject differs')
    for row in observed['commands']+observed['sessions']:
        if row.get('tree_reaped') is not True:raise ValueError('Actual headless tree not reaped')
        key='command' if 'command' in row else 'label';labels=LOG_LABELS['headless' if key=='command' else 'sessions']
        captured.capture(canonical_log(headless,row[key],row['log'],labels),row['log_hash'])
    for name in ('unattended','qualified-backup'):
        for row in checkpoints[name]['commands']:
            if row['exit_code']!=row['expected_exit_code'] or row.get('tree_reaped') is not True:raise ValueError('Actual ancillary command incomplete')
            captured.capture(canonical_log(stages[name],row['command'],row['log_ref'],LOG_LABELS[name]),row['log_hash'])
    captured.capture(stages['unattended']/'actual-coordinator.log',checkpoints['unattended']['coordinator_log_hash'])
    owner_report=stages['unattended']/'observed-owner-report'
    if {p.name for p in owner_report.iterdir()}!={'feedback.json','report.html'}:raise ValueError('Canonical public owner report required')
    payloads={name:captured.capture(owner_report/name) for name in ('feedback.json','report.html')}
    expected_report=checkpoints['unattended']['actual_owner_report']
    if (json.loads(payloads['feedback.json'])!=expected_report['feedback']
            or sha(payloads['feedback.json'])!=expected_report['publication']['feedback_hash']):
        raise ValueError('Actual owner feedback differs')
    validate_feedback_publication(expected_report['publication']['logical_path'],payloads)
    paths.update(owner_report/name for name in ('feedback.json','report.html'))
    extra=['run_current_checkpoint.py','run_current_checkpoint_v1.py','run_current_checkpoint_v2.py',
        'verify_portable_checkpoint.py','verify_unattended_checkpoint.py','verify_qualified_backup_checkpoint.py','index_current_qualification.py',
        'portable-helper-review.json','portable-helper-repair-review.json','portable-helper-final-review.json',
        'unattended-helper-review.json','unattended-helper-final-review.json','qualified-backup-helper-review.json','qualified-backup-helper-final-review.json',
        'current-index-helper-review.json','portable-helper-source-regressions.log','qualified-backup-helper-source-regressions.log','current-index-helper-source-regressions.log',
        'acceptance-v02-draft.json','legacy-150-draft.json','acceptance-disposition-advisory.json','acceptance-str-expanded-map.json',
        'acceptance-research-expanded-map.json','acceptance-cloud-trade-expanded-map.json','strategy-coverage-completion-design.json',
        'research-coverage-completion-design.json','local-alert-completion-design.json','legacy-local-gap-design.json',
        'write_current_launch_guide.py','current-launch-guide-review.json','current-launch-guide-final-review.json','current-launch-guide-source-regressions.log',
        'retain_current_checkpoint.py','retain-current-checkpoint-review.json','retain-current-checkpoint-final-review.json',
        'retain-current-checkpoint-final2-review.json','retain-current-checkpoint-source-regressions.log']
    paths.update(BASE/name for name in extra)
    missing=[p.relative_to(PROJECT).as_posix() for p in paths if not p.is_file()]
    if missing:raise ValueError('Declared evidence missing: '+','.join(missing))
    for path in paths:captured.capture(path)
    # All subject guards finish BEFORE tracked evidence changes the worktree.
    _guard(ROOT,revision,package,facts,profile)
    target.mkdir();(target/'artifacts').mkdir();bindings=[]
    for number,path in enumerate(sorted(paths,key=lambda p:p.relative_to(PROJECT).as_posix()),1):
        raw=captured.bytes[path];ref=f'artifacts/a{number:04d}'+path.suffix
        if path.suffix=='.png':safe=raw
        else:safe=_sanitize(raw.decode('utf-8-sig'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').replace('\r','').encode()
        (target/ref).write_bytes(safe)
        if artifact_bytes(target,ref)!=safe:raise ValueError('Retained evidence readback differs')
        bindings.append(dict(original_ref=path.relative_to(PROJECT).as_posix(),original_hash=sha(raw),retained_ref=ref,retained_hash=sha(safe)))
    counts={key:sum(getattr(c,key) for c in receipt.checks) for key in ('tests_run','failures','errors','skipped','expected_failures','unexpected_successes')}
    disposition=dict(task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',spec_baseline='r7-product-v0.2',branch='codex/r7-productization-master-20261002',
        executable_revision=revision,identity=facts,master='IN_PROGRESS',source_worktree_at_execution='CLEAN',
        ordinary_windows_paper_software=dict(status='PASS',receipt_ref=receipt.receipt_id,execution_id=receipt.execution_id,
            groups_required=7,groups_completed=q['groups_completed'],commands=len(receipt.checks),**counts,
            ordinary_financial_selection='NOT_SELECTED',ordinary_paper='NOT_STARTED',forward='NOT_STARTED'),
        real_public_data_research=dict(status='ACTUAL_NATIVE_ENGINEERING_DEVELOPMENT_DIAGNOSTIC_BLOCKED',
            origin='ENGINEERING_BASELINE_NOT_GPT',reason='MISSING_PROMOTION_POLICY',independent_oos='NOT_RUN',new_public_requests=0,prior_public_requests=8,prior_public_responses=8),
        headless=dict(status='ACTUAL_NATIVE_START_STOP_DUPLICATE_CRASH_RECOVERY_PASS',normal_automatic_diagnostic='INTAKE_RESEARCH_DURABLE_REPORT_PASS',
            report_publication='NOT_RUN;PENDING_OUTBOX',host_startup='UNCHANGED',sleep='UNCHANGED',security='UNCHANGED'),
        portable=dict(status='ACTUAL_FRESH_ZIP_INSTALL_PASS',archive=checkpoints['portable']['archive_ref'],archive_hash=checkpoints['portable']['archive_hash'],
            installation_ref=checkpoints['portable']['installation_ref'],copied_auth=False,copied_configuration=False),
        backup=dict(status='ACTUAL_NATIVE_SAME_QUALIFIED_DIAGNOSTIC_STORE_BACKUP_RESTORE_REBACKUP_PASS',restoration='RESTORED_INHIBITED',financial_authority='NONE'),
        external=['OLD24GB_TARGET_NATIVE_NOT_RUN','UBUNTU24_04_NATIVE_NOT_RUN','UBUNTU26_04_NATIVE_NOT_RUN','REAL_CLOUD_NOT_COMMISSIONED',
            'FORMAL_RESEARCH_PAPER_RISK_WORKFLOW_POLICIES_UNSELECTED','REAL_FORWARD_SAMPLES_NOT_STARTED'],
        remaining_local='SEMANTIC66_AND150_BINDING_REVIEW;NAMED_COVERAGE_GAPS;J06_ALERTS_AND_OTHER_MASTER_LOCAL_WORK',
        additional_public_requests=0,cumulative_actual_public_requests=8,cumulative_actual_public_responses=8,
        credentials='NONE',private_requests=0,provider_mutation=0,capital='NONE',github_compute='NOT_USED',retained_files=bindings)
    serialized=(json.dumps(disposition,indent=2)+'\n').encode()
    (target/'disposition.json').write_bytes(serialized)
    if artifact_bytes(target,'disposition.json')!=serialized:raise ValueError('Disposition readback differs')
    print(json.dumps(dict(target=target.relative_to(ROOT).as_posix(),retained_files=len(bindings),commands=len(receipt.checks),counts=counts,master='IN_PROGRESS')))
if __name__=='__main__':run(*sys.argv[1:])
