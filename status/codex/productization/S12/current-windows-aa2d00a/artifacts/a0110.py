"""Sanitized, allowlisted evidence after all exact-clean executions finish."""
from dataclasses import asdict
from datetime import datetime
import hashlib,json,re,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from application.config import load_config
from application.qualification import _sanitize
from application.paper.inventory import current_target,fixed_profile
from application.paper.producer import _guard,native_artifacts
from application.paper.qualification import validate_qualified_receipt,artifact_bytes
from application.platform.distribution import verify_distribution
from application.platform.supervision import config_hash
from strategy.v02.capabilities import build_capability_snapshot
from storage.qualification import open_qualification_receipts
from verify_portable_checkpoint import archive_subject,validate_authoring
from application.cloud.feedback import validate_feedback_publication
from application.cloud.manifest import safe_component
from application.cloud.protocol import CloudError
from verify_qualified_backup_checkpoint import require_idle_backup_binding,backup_output
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
        path=Path(path);relative=path.relative_to(self.root)
        try:
            for part in relative.parts:safe_component(part)
        except CloudError:raise ValueError('Contained host artifact components required') from None
        # These are allowlisted host artifact paths, not cloud references.
        # The opened-file reader still checks every ancestor and single link.
        raw=artifact_bytes(path.parent,path.name)
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
            or backup.get('actual_runtime_selection_equal_across_four_stores') is not True
            or backup.get('restored_native_software_admission')!='DENIED'
            or portable.get('source_unchanged') is not True or portable.get('complete_bytes_identical') is not True
            or portable.get('first_run',{}).get('passed') is not True or automatic.get('public_source_unchanged') is not True):
        raise ValueError('Actual ancillary closure incomplete')
    for name in ('build','qualify','headless'):
        if checkpoints[name].get('source_unchanged') is not True:raise ValueError('Source guard missing')

def require_owning_native04(captured,source,members,facts):
    # Full owning qualification already executes native04. Bind its retained
    # primary observation; an additional ad hoc preflight is not a release gate.
    rows=[row for row in members if row.get('group_id')=='PQR-04']
    if len(rows)!=1 or rows[0].get('member_id')!='PQR-04-native':
        raise ValueError('Exact full owning native04 member required')
    ref='PQR-04-native-artifacts/native-observations.json'
    declared=[row for row in rows[0]['artifacts'] if row['ref']==ref]
    if len(declared)!=1:raise ValueError('Owning native04 primary must be declared exactly once')
    path=source/ref;primary=json.loads(captured.capture(path,declared[0]['hash']))
    if primary.get('passed') is not True or primary.get('identity')!=facts or primary.get('group')!='PQR-04':
        raise ValueError('Actual owning native04 primary subject differs')
    return path

def require_idle_checkpoint(row,revision,facts,owning,receipt_ref):
    require_idle_backup_binding(row,revision,facts,owning,receipt_ref)
    binding=row.get('owning_profile',{})
    if (row.get('passed') is not True or row.get('revision')!=revision or row.get('identity')!=facts
            or row.get('all_owned_trees_reaped') is not True or row.get('source_and_package_unchanged') is not True
            or row.get('helper_unchanged') is not True or row.get('workflow_authorized') is not False
            or binding.get('original_config_hash')!=owning['config_hash'] or binding.get('same_original_receipt_ref')!=receipt_ref
            or binding.get('same_original_data_root') is not True or binding.get('workflow_authorized') is not False):
        raise ValueError('Actual same-store/receipt unauthorized idle proof required')
    summaries=row.get('actual_idle_runtime_summaries')
    if (not isinstance(summaries,list) or len(summaries)!=2
            or any(value.get('market_source')!='NOT_CONNECTED' or value.get('run_failures')!={}
                or any(type(value.get(key)) is not int or value[key]!=0 for key in ('provider_requests','provider_responses')) for value in summaries)):
        raise ValueError('Actual zero-request idle runtime summaries required')


def host_and_pqr05_observation(captured,stage,source,members,facts,revision,attempt):
    if (stage.get('stage')!='qualify' or stage.get('revision')!=revision or stage.get('attempt')!=attempt
            or stage.get('passed') is not True or stage.get('source_unchanged') is not True):
        raise ValueError('Actual direct owning stage/attempt required')
    def stamp(text):
        value=datetime.fromisoformat(text.replace('Z','+00:00'))
        if value.tzinfo is None:raise ValueError('Actual timezone required')
        return value
    start=stamp(stage['started_at']);end=stamp(stage['finished_at'])
    if end<start:raise ValueError('Actual owning interval required')
    valid=[];errors=[];times=[]
    for row in stage['host_samples']:
        if 'error_type' in row:errors.append(row);continue
        available=row.get('available_memory_bytes');physical=row.get('physical_memory_bytes')
        at=stamp(row['observed_at'])
        if (type(available) is not int or type(physical) is not int or not 0<=available<=physical
                or not start<=at<=end or (times and at<times[-1])):
            raise ValueError('Actual ordered host memory sample required')
        valid.append(row);times.append(at)
    rows=[row for row in members if row.get('group_id')=='PQR-05']
    if len(rows)!=1 or rows[0].get('member_id')!='PQR-05-native':
        raise ValueError('Exact owning native05 member required')
    ref='PQR-05-native-artifacts/native-observations.json'
    declared=[row for row in rows[0]['artifacts'] if row['ref']==ref]
    if len(declared)!=1:raise ValueError('Exact owning native05 artifact required')
    path=source/ref;primary=json.loads(captured.capture(path,declared[0]['hash']))
    if primary.get('passed') is not True or primary.get('identity')!=facts or primary.get('group')!='PQR-05':
        raise ValueError('Actual owning native05 subject differs')
    cases=[row for row in primary['observations'] if row.get('case')=='research-isolation']
    if len(cases)!=1:raise ValueError('Actual unique isolation window required')
    case=cases[0]
    if (any(case.get(key) is not True for key in ('passed','research_fault_protection_isolation','host_bounded_capacity_measured'))
            or case.get('capacity_scope')!='ONE_PAPER_OWNER_ONE_RESEARCH_JOB_AND_CONTROL'
            or case.get('memory_enforcement')!='SOFT_LIMIT_ONLY'
            or any(case.get(key)!='NOT_ESTABLISHED' for key in ('maximum_load_qualification','target_24gb_qualification'))):
        raise ValueError('Actual bounded isolation scope required')
    samples=case['process_samples']
    if not isinstance(samples,list) or not 1<=len(samples)<=2048:raise ValueError('Actual finite process sample window required')
    totals=[]
    for sample in samples:
        processes=sample['processes']
        if set(processes)!={'control','runtime','research'}:raise ValueError('Exact measured owner scopes required')
        measured=[row for rows in processes.values() for row in rows]
        if not 1<=len(measured)<=128:raise ValueError('Finite measured process list required')
        pids=[row['pid'] for row in measured]
        if any(type(pid) is not int or pid<=0 for pid in pids) or len(set(pids))!=len(pids):
            raise ValueError('Unique actual measured PIDs required')
        if any(type(row[key]) is not int or row[key]<0 for row in measured for key in ('rss_bytes','private_bytes')):
            raise ValueError('Actual nonnegative process counters required')
        totals.append({key:sum(row[key] for row in measured) for key in ('rss_bytes','private_bytes')})
    rss=max(row['rss_bytes'] for row in totals);private=max(row['private_bytes'] for row in totals)
    if case['sampled_peak_total_rss_bytes']!=rss or case['sampled_peak_total_private_bytes']!=private:
        raise ValueError('Actual isolation counters and scalar peaks differ')
    minimum=min((row['available_memory_bytes'] for row in valid),default=None)
    return dict(retention_mode='HOST_AND_PQR05_ONLY',valid_samples=len(valid),minimum_host_available_bytes=minimum,
        peak_owned_rss_bytes=None,peak_owned_private_bytes=None,
        complete_owning_run=dict(process_memory_status='UNKNOWN_NOT_OBSERVED_FOR_THIS_ATTEMPT',
            peak_owned_rss_bytes=None,peak_owned_private_bytes=None,reason='NO_ACTUAL_SAME_ATTEMPT_FULL_TREE_RSS_OBSERVER'),
        host_memory=dict(scope='ACTUAL_LAUNCHER_HOST_AVAILABILITY;NOT_OWNED_PROCESS_ATTRIBUTION',
            valid_sample_count=len(valid),error_sample_count=len(errors),error_samples=errors,
            minimum_host_available_bytes=minimum,intended_sampling_interval_seconds=2,
            maximum_observed_gap_seconds=max(((b-a).total_seconds() for a,b in zip(times,times[1:])),default=None),
            first_sample_at=None if not times else times[0].isoformat(),last_sample_at=None if not times else times[-1].isoformat(),
            monitor_stopped='NOT_RECORDED',continuous_coverage='NOT_ESTABLISHED'),
        pqr05_isolation=dict(scope='ONE_PAPER_OWNER_ONE_RESEARCH_JOB_AND_CONTROL_FINITE_WINDOW',sample_count=len(samples),
            sampled_peak_total_rss_bytes=rss,sampled_peak_total_private_bytes=private,memory_enforcement='SOFT_LIMIT_ONLY',
            maximum_load_qualification='NOT_ESTABLISHED',target_24gb_qualification='NOT_ESTABLISHED',
            artifact_ref=ref,artifact_hash=declared[0]['hash'])),{path}


def run(revision,qualification_attempt='first',backup_attempt='first',resource_mode='COMPLETE_OWNING_TREE_OBSERVER'):
    from run_current_checkpoint import qualification_output
    stages={name:BASE/(name+'-'+revision[:7]+'-first') for name in ('build','qualify','headless','portable','unattended','ordinary-idle','qualified-backup')}
    stages['qualify']=qualification_output(revision,qualification_attempt)
    stages['qualified-backup']=backup_output(revision,backup_attempt)
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
    require_idle_checkpoint(checkpoints['ordinary-idle'],revision,facts,owning,receipt.receipt_id)
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
    paths.add(require_owning_native04(captured,source,receipt.execution_evidence['members'],facts))
    acceptance_path=BASE/('acceptance-records-'+revision[:7]+'.json');acceptance=captured.document(acceptance_path)
    if (acceptance.get('revision')!=revision or acceptance.get('identity')!=facts or acceptance.get('receipt_ref')!=receipt.receipt_id
            or len(acceptance.get('current_matrix_results',[]))!=66 or len(acceptance.get('inherited_legacy_results',[]))!=150):
        raise ValueError('Actual current supporting acceptance bindings required')
    paths.add(acceptance_path)
    delivery=PROJECT/'deliveries'/('current-windows-'+revision[:7]);version=captured.document(delivery/'version.json')
    if (version.get('revision')!=revision or version.get('identity')!=facts or version.get('archive_ref')!=portable['archive_ref']
            or version.get('archive_sha256')!=portable['archive_hash'][7:] or version.get('installation_ref')!=portable['installation_ref']):
        raise ValueError('Actual delivery guide version differs')
    paths.update(delivery/name for name in ('README.md','SHA256SUMS.txt','version.json'))
    memory_root=BASE/('owning-memory-'+revision[:7]+'-'+qualification_attempt)
    if resource_mode=='HOST_AND_PQR05_ONLY':
        if memory_root.exists():raise ValueError('Explicit direct launch cannot hide a present tree observer')
        memory,resource_paths=host_and_pqr05_observation(captured,checkpoints['qualify'],source,
            receipt.execution_evidence['members'],facts,revision,qualification_attempt)
        paths.update(resource_paths)
    elif resource_mode=='COMPLETE_OWNING_TREE_OBSERVER':
        memory=captured.document(memory_root/'checkpoint.json')
        if (memory.get('revision')!=revision or memory.get('attempt')!=qualification_attempt or memory.get('owning_passed') is not True
                or memory.get('exit_code')!=0 or memory.get('tree_reaped') is not True or memory.get('monitor_stopped') is not True
                or memory.get('source_unchanged') is not True or memory.get('wrapper_unchanged') is not True or memory.get('errors')!=[]
                or type(memory.get('valid_samples')) is not int or memory['valid_samples']<=0):
            raise ValueError('Actual same-attempt complete owning memory observation required')
        memory={key:memory[key] for key in ('valid_samples','peak_owned_rss_bytes','peak_owned_private_bytes','minimum_host_available_bytes')}
        memory['retention_mode']=resource_mode
        paths.update(memory_root/name for name in ('checkpoint.json','wrapper.log'))
    else:raise ValueError('Explicit known resource retention mode required')
    supplemental=None
    if resource_mode=='HOST_AND_PQR05_ONLY':
        if revision!='3ae6460c69a8a8f90588c396b819af7079e7546d':
            raise ValueError('Current supplemental archive is exact-subject only')
        prepared=BASE/'supplements-3ae6460-prepared'
        manifest=captured.document(prepared/'prepared-manifest.json')
        if (manifest.get('revision')!=revision or manifest.get('identity')!=facts
                or manifest.get('scope')!='SUPPLEMENTAL_ACTUAL_NATIVE_AND_STATIC_EVIDENCE_OUTSIDE_FIXED_RECEIPT'):
            raise ValueError('Exact prepared supplemental subject required')
        entries=manifest.get('artifacts')
        if (not isinstance(entries,list) or not 1<=len(entries)<=256 or any(
                not isinstance(row,dict) or set(row)!={'ref','hash'} or not isinstance(row['ref'],str)
                or (row['ref']!='disposition.json' and not re.fullmatch(r'a[0-9]{4}\.(json|log|py|md|sql|unapplied)',row['ref']))
                for row in entries)):
            raise ValueError('Only flat selected public prepared files allowed')
        bindings=native_artifacts(manifest,prepared)
        if 'disposition.json' not in bindings:raise ValueError('Prepared public disposition required')
        for ref,commitment in bindings.items():
            captured.capture(prepared/ref,commitment);paths.add(prepared/ref)
        supplemental=captured.document(prepared/'disposition.json')
        if supplemental.get('executable_revision')!=revision or supplemental.get('identity')!=facts:
            raise ValueError('Supplemental disposition subject differs')
        paths.add(prepared/'prepared-manifest.json')
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
        elif name=='ordinary-idle':
            idle=checkpoints[name];labels=('new-public-idle-profile','normal-configure-paper-idle','ordinary-duplicate-denied','ordinary-stop-first','ordinary-stop-restarted')
            if [row['command'] for row in idle['commands']]!=list(labels):raise ValueError('Exact ordinary idle public command sequence required')
            declared_logs=set()
            for row in idle['commands']:
                if row['tree_reaped'] is not True or row['exit_code']!=(2 if row['command']=='ordinary-duplicate-denied' else 0):raise ValueError('Actual ordinary idle command incomplete')
                log=canonical_log(path,row['command'],row['log'],labels);captured.capture(log,row['log_hash']);paths.add(log);declared_logs.add(log.name)
            if [row['label'] for row in idle['sessions']]!=['coordinator-ordinary-first','coordinator-ordinary-restarted']:
                raise ValueError('Exact ordinary idle sessions required')
            for row in idle['sessions']:
                if row['tree_reaped'] is not True:raise ValueError('Actual ordinary idle session not reaped')
                log=canonical_log(path,row['label'],row['log'],('coordinator-ordinary-first','coordinator-ordinary-restarted'))
                captured.capture(log,row['log_hash']);paths.add(log);declared_logs.add(log.name)
            for row in idle['service_logs']:
                if not re.fullmatch(r'service-coordinator-ordinary-(first|restarted)-(control|research|runtime)-[1-3]\.log',row['retained_ref']):
                    raise ValueError('Canonical ordinary service log required')
                log=path/row['retained_ref'];captured.capture(log,row['retained_hash']);paths.add(log);declared_logs.add(log.name)
            paths.update(exact_public_logs(path,declared_logs));paths.add(path/'observations.json')
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
        'retain-current-checkpoint-final2-review.json','retain-current-checkpoint-source-regressions.log',
        'verify_ordinary_idle_coordinator.py','test_ordinary_idle_coordinator_helper.py','ordinary-idle-coordinator-helper-review.json',
        'ordinary-idle-coordinator-helper-final-review.json','ordinary-idle-coordinator-helper-final2-review.json',
        'ordinary-idle-helper-final-source-regressions.log','retainer-owning-only-review.json','retainer-owning-only-green.log',
        'retainer-idle-binding-green.log','normal-paper-coordinator-coverage-review.json','normal-paper-idle-native-setup-design.json',
        'run_owning_with_memory.py','owning-memory-observer-final2-review.json','retainer-idle-and-chain-review.json',
        'record_current_windows_checkpoint.py','run-post-owning-checkpoint.ps1',
        'test_qualified_backup_checkpoint_helper.py','test_retain_current_checkpoint.py',
        'idle-backup-integration-review.json','idle-backup-binding-plan.json','idle-backup-binding-red-corrected.log',
        'idle-backup-binding-green.log','idle-backup-binding-final-review.json']
    paths.update(BASE/name for name in extra)
    if resource_mode=='COMPLETE_OWNING_TREE_OBSERVER':paths.add(BASE/'postqualification-power-interval-20261020.json')
    else:paths.update(BASE/name for name in ('retain_current_checkpoint_before_direct_resource.py',
        'test_direct_qualification_resource_retention.py','owning-resource-retention-advisory-3ae6460-20261021.json',
        'direct-resource-retention-red.log','direct-resource-retention-green.log',
        'current-supplement-archive-final-review-20261021.json',
        'retain_current_checkpoint_before_archive_review_refs.py',
        'retainer-final-archive-review-retention-binding-20261021.json'))
    if backup_attempt!='first':
        failed_root=backup_output(revision,'first')
        failed=captured.document(failed_root/'checkpoint.json')
        if (failed.get('revision')!=revision or failed.get('passed') is not False
                or failed.get('all_owned_tree_reaped') is not True or failed.get('source_and_package_unchanged') is not True):
            raise ValueError('Historical first backup failure binding differs')
        captured.capture(BASE/'verify_qualified_backup_checkpoint_failed_v1.py',failed['helper_hash'])
        paths.update((failed_root/'checkpoint.json',BASE/'verify_qualified_backup_checkpoint_failed_v1.py'))
        for row in failed['commands']:
            ref=row['log_ref']
            if row['command'] not in LOG_LABELS['qualified-backup'] or ref!=row['command']+'.log':
                raise ValueError('Historical backup command log differs')
            captured.capture(failed_root/ref,row['log_hash'])
            paths.add(failed_root/ref)
        paths.update(BASE/name for name in ('test_qualified_backup_checkpoint_helper.py','backup-selection-shape-red.log',
            'backup-selection-shape-green.log','backup-selection-shape-combined-green.log','backup-selection-shape-final-review.json'))
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
            ordinary_runtime_idle='ACTUAL_NATIVE_COORDINATOR_CONTROL_RESEARCH_RUNTIME_IDLE_RESTART_STOP_PASS',ordinary_workflow_authorized=False,
            ordinary_trading_lifecycle='NOT_RUN;OPERATOR_POLICIES_UNSELECTED',
            report_publication='NOT_RUN;PENDING_OUTBOX',host_startup='UNCHANGED',sleep='UNCHANGED',security='UNCHANGED'),
        portable=dict(status='ACTUAL_FRESH_ZIP_INSTALL_PASS',archive=checkpoints['portable']['archive_ref'],archive_hash=checkpoints['portable']['archive_hash'],
            installation_ref=checkpoints['portable']['installation_ref'],copied_auth=False,copied_configuration=False),
        backup=dict(status='ACTUAL_NATIVE_SAME_QUALIFIED_DIAGNOSTIC_STORE_BACKUP_RESTORE_REBACKUP_PASS',restoration='RESTORED_INHIBITED',financial_authority='NONE',
            protected_runtime_selection='ACTUAL_TYPED_EQUALITY_ACROSS_ORIGINAL_CAPTURED_RESTORED_RECAPTURED'),
        owning_resource_observation=memory,
        supplemental_actual_evidence=supplemental,
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
