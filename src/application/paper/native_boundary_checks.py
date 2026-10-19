"""Fixed native component diagnostics, never a qualification or financial grant.

Synthetic validator/comparison models live only in memory. Their represented
members are NOT executed PQR checks and are never appended to E6. The separate
storage exercise retains only an actually executed doctor command, explicitly
an incomplete, non-inventory diagnostic attempt against the installed profile.
"""
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import asdict,replace
from datetime import datetime,timezone
import json,os,subprocess,sys,tempfile,time,uuid
from pathlib import Path

from application.config import load_config,product_namespace
from application.datasets.catalog import canonical,digest as byte_digest
from application.platform.private_files import create_private_directory,write_private_new
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.platform.scope_lock import ProcessScopeLock,operational_lock_root
from application.platform.supervision import ProcessSupervisor,PROCESS_ROLES,config_hash
from application.platform.runtime_identity import read_runtime_identity,RuntimeIdentityUnavailable
from application.platform.restoration import require_valid_restoration
from storage import open_sqlite_platform
from storage.paper_selection import OperationalSelection
from storage.qualification import QualificationSubject,QualificationCheck,_payload,_open_qualification_receipt_owner,open_qualification_receipts

_unreaped=[]


def digest(value):
    return byte_digest(value.encode('utf-8') if isinstance(value,str) else value)


def denied(action,exception=ValueError,reason=None):
    try:action()
    except exception as error:
        if reason is not None and reason not in str(error):raise RuntimeError('Native diagnostic refusal differs') from None
        return
    raise RuntimeError('Native diagnostic unexpectedly accepted negative input')


def memory_component_checks(root,config,facts,identity):
    """Explicitly synthetic fixture objects; no receipt/selection storage call."""
    from . import qualification as gate
    from .release_observation import validate_observation,owner_projection
    root=Path(root);results=[];profile=dict(schema_version='r7-qualified-paper-inventory-v0.2',
        profile_id=gate.PROFILE_ID,decision_ref='PM_PAPER_RELEASE_MAPPING_DECISION_20261013',
        decision_hash=digest(b'SYNTHETIC_IN_MEMORY_ONLY'),platform_id=facts['platform_id'],
        capability_hash=facts['capability_hash'],groups=[])
    evidence=dict(schema_version='r7-qualified-paper-execution-evidence-v0.2',provenance='FIXTURE_SOFTWARE_CHECKS_ONLY',members=[])
    checks=[]
    for number in range(1,8):
        group=f'PQR-{number:02d}';member=group+'-synthetic-nonissued-model';ref=f'model-{number:02d}.log'
        raw=f'SYNTHETIC IN-MEMORY VALIDATOR INPUT {number}; NOT AN EXECUTED PQR MEMBER\n'.encode()
        write_private_new(root/ref,raw);commitment=digest(raw)
        profile['groups'].append(dict(check_id=group,members=[dict(member_id=member,kind='UNITTEST',
            command_ref='synthetic-nonissued-model',tool_hash=digest(b'synthetic-model-only'),
            test_cases=['synthetic_model.NotExecuted.case'],assertions=[],target_predicate='SYNTHETIC_COMPONENT_ONLY')]))
        checks.append(QualificationCheck(member,'synthetic-nonissued-model',ref,commitment,0,True,1,0,0,0,0,0,1))
        evidence['members'].append(dict(member_id=member,group_id=group,test_cases=['synthetic_model.NotExecuted.case'],
            artifacts=[dict(ref=ref,hash=commitment)],assertions=[]))
    now=datetime.now(timezone.utc)
    model,_=_payload('synthetic-nonissued-model',QualificationSubject(namespace='LOCAL_RESEARCH',
        **{key:facts[key] for key in ('executable_revision','implementation_hash','build_hash','platform_id')}),
        gate.PROFILE_ID,digest(canonical(profile)),tuple(checks),now,now,profile_manifest=profile,execution_evidence=evidence)
    def validate(receipt=model,measured=facts):gate.validate_qualified_receipt(receipt,profile,artifact_root=root,measured=measured)
    validate();results.append('SYNTHETIC_NONISSUED_VALIDATOR_BASELINE')
    for key in ('executable_revision','implementation_hash','build_hash','platform_id','capability_hash'):
        denied(lambda key=key:validate(measured={**facts,key:'changed-subject'}));results.append('SUBJECT_DENIED_'+key.upper())
    for name,changed in (('MISSING_MEMBER',replace(model,checks=model.checks[:-1])),
            ('REORDERED_MEMBERS',replace(model,checks=tuple(reversed(model.checks)))),
            ('ZERO_TEST',replace(model,checks=(replace(model.checks[0],tests_run=0),*model.checks[1:]))),
            ('UNREAPED',replace(model,checks=(replace(model.checks[0],tree_reaped=False),*model.checks[1:])))):
        denied(lambda changed=changed:validate(changed));results.append('SYNTHETIC_'+name+'_DENIED')
    path=root/checks[0].log_ref;original=path.read_bytes();path.write_bytes(b'CONTROLLED MUTATED COMPONENT ARTIFACT')
    try:denied(validate)
    finally:path.write_bytes(original)
    results.append('ACTUAL_COMPONENT_ARTIFACT_MUTATION_DENIED')
    # A typed comparison fixture, not an allocated or persisted operational
    # selection. It cannot be resolved by any runtime, API or financial owner.
    material=canonical(dict(simulator_profile=dict(implementation_hash=facts['implementation_hash']),synthetic_comparison_only=True))
    comparison=OperationalSelection(1,digest(material),material)
    current=time.monotonic_ns();token=owner_projection(identity)
    observation=dict(schema_version='r7-native-paper-observation-v0.2',state='CURRENT',attempt_token=uuid.uuid4().hex,
        receipt_ref='qualification-'+'a'*64,runtime=token,selection_generation=comparison.generation,
        selection_hash=digest(comparison.canonical_json),facts=facts,started_ns=current-2_000_000,finished_ns=current-1_000_000)
    def observe(value=observation):return validate_observation(value,config=config,receipt_ref=observation['receipt_ref'],
        runtime_identity=identity,selection=comparison,now_ns=current)
    observe();results.append('SYNTHETIC_OBSERVATION_COMPARISON_BASELINE')
    for name,change in (('PENDING',dict(state='PENDING')),('OLD_AGE',dict(started_ns=current-31_000_000_000,finished_ns=current-30_000_000_000)),
            ('WRONG_RECEIPT',dict(receipt_ref='qualification-'+'b'*64)),('WRONG_SELECTION_GENERATION',dict(selection_generation=2)),
            ('WRONG_OWNER',dict(runtime={**token,'process_generation_id':str(uuid.uuid4())})),
            ('CALLER_EXTRA',dict(passed=True))):
        denied(lambda change=change:observe({**observation,**change}));results.append('SYNTHETIC_OBSERVATION_'+name+'_DENIED')
    return results


def _doctor(config,config_path,output):
    owned=None;code=None;failure=None;cleanup=None;cleanup_error=None
    started=datetime.now(timezone.utc);begin=time.monotonic_ns()
    with tempfile.TemporaryFile() as stream:
        try:
            owned=spawn_owned([sys.executable,'doctor','--hardware','--data-root',str(config.local_data_root),'--json'],
                cwd=output,limits=ResourceLimits(30),stdout=stream,stderr=subprocess.STDOUT)
            code=owned.wait(timeout=35);stream.seek(0);raw=stream.read(1024*1024+1)
            if code!=0 or len(raw)>1024*1024 or not owned.termination_report.reaped:raise RuntimeError('Actual native doctor diagnostic failed')
            document=json.loads(raw)
            if not isinstance(document,dict) or type(document.get('physical_memory_bytes')) is not int:raise RuntimeError('Actual doctor output required')
        except BaseException as error:
            failure=type(error).__name__
            raise
        finally:
            try:
                if owned is not None:cleanup=terminate_owned(owned,deadline_seconds=3)
            except BaseException as error:cleanup_error=type(error).__name__
            finally:
                reaped=cleanup is not None and cleanup.reaped
                if owned is not None:
                    if not reaped:_unreaped.append(owned)
                    if code is None:code=owned.process.poll()
                stream.seek(0);captured=stream.read(1024*1024+1)
                from application.qualification import _sanitize
                text=_sanitize(captured[:1024*1024].decode('utf-8',errors='replace'),Path(sys.executable).resolve().parent)
                text=text.replace(str(config.local_data_root),'<DIAGNOSTIC_DATA_ROOT>').replace(str(config_path),'<DIAGNOSTIC_CONFIG>')
                raw=text.encode('utf-8');write_private_new(output/'doctor.log',raw)
                write_private_new(output/'doctor-execution.json',(canonical(dict(command='ACTUAL_NATIVE_DOCTOR',
                    exit_code=code,tree_reaped=reaped,error_type=failure,cleanup_error_type=cleanup_error,
                    started_at=started.isoformat(),finished_at=datetime.now(timezone.utc).isoformat(),
                    log_ref='doctor.log',log_hash=digest(raw),captured_output_truncated=len(captured)>1024*1024,
                    qualification='NOT_ISSUED'))+'\n').encode())
            if cleanup_error is not None or owned is not None and not reaped:raise RuntimeError('Native doctor cleanup unconfirmed')
    return QualificationCheck('native-diagnostic-doctor-not-in-pqr-inventory','actual-native-doctor','doctor.log',digest(raw),
        code,True,0,0,0,0,0,0,max(0,(time.monotonic_ns()-begin)//1_000_000)),started,datetime.now(timezone.utc)


def stale_paper_operation_check(config,run_id,implementation_hash,*,config_path=None):
    """Try only the actual prior E6 generation on an existing FIXTURE run.

    No generation or operation payload can be supplied by a CLI/API caller.
    A refusal must leave no new prepared row or changed checkpoint.
    """
    from storage.paper_process import open_paper_process_journal
    from storage.runtime_models import RuntimeConflictError
    if product_namespace(config)!='FIXTURE' or require_valid_restoration(config)['status']!='NOT_RESTORED':
        raise ValueError('Existing non-restored synthetic run required')
    with ProcessScopeLock('runtime:'+config.product_instance_id,lock_root=operational_lock_root(config)),\
            open_paper_process_journal(config.database_path,require_existing=True) as journal:
        if config_path is not None and load_config(config_path)!=config:raise ValueError('Stale diagnostic configuration changed')
        before=journal.recover(run_id)
        if (before.binding['namespace']!='FIXTURE' or before.binding['implementation_hash']!=implementation_hash
                or before.process_generation<2 or before.pending_operations):raise ValueError('Actual same-subject E6 successor required')
        observed=before.state['runtime']['forward']['observed_at']
        now=datetime.now(timezone.utc)
        if observed is not None:now=max(now,datetime.fromisoformat(observed.replace('Z','+00:00')))
        operation='native-stale-diagnostic-'+uuid.uuid4().hex
        denied(lambda:journal.prepare(run_id,operation,dict(kind='DEADLINE',due_at=now.isoformat()),
            expected_revision=before.revision,now=now,process_generation=before.process_generation-1),
            RuntimeConflictError,reason='stale process generation')
        after=journal.recover(run_id)
        if before!=after or journal.operation(run_id,operation) is not None:raise RuntimeError('Refused stale writer changed actual E6 facts')
    return dict(status='STALE_OPERATION_DENIED',original_checkpoint_unchanged=True,
        actual_generation=before.process_generation,rejected_generation=before.process_generation-1,
        scope='EXISTING_FIXTURE_E6_OWNER_OPERATION',provider_requests=0,credentials='NONE',capital='NONE')


def run_native_stale_paper_check(config_path,run_id):
    if not getattr(sys,'frozen',False):raise ValueError('Installed native stale-owner diagnostic required')
    from application.platform.distribution import verify_distribution
    facts=verify_distribution(Path(sys.executable).resolve().parent)
    return stale_paper_operation_check(load_config(config_path),run_id,facts['implementation_hash'],config_path=config_path)


def diagnostic_receipt_input(facts,profile,check,started,finished):
    """Paired E6 manifests for one observed diagnostic, with no PQR claim."""
    from .qualification import PROFILE_ID
    return dict(execution_id='native-diagnostic-'+uuid.uuid4().hex,
        subject=QualificationSubject(namespace='LOCAL_RESEARCH',
            **{key:facts[key] for key in ('executable_revision','implementation_hash','build_hash','platform_id')}),
        profile_id=PROFILE_ID,profile_hash=digest(canonical(profile)),profile_manifest=profile,
        checks=(check,),started_at=started,finished_at=finished,
        execution_evidence=dict(schema_version='r7-native-diagnostic-evidence-v1',
            provenance='ONE_OBSERVED_DIAGNOSTIC_NOT_PQR_QUALIFICATION',qualification_complete=False,
            executed_pqr_members=[],observed_checks=[asdict(check)]))


def run_native_boundary_checks(config_path):
    if not getattr(sys,'frozen',False):raise ValueError('Installed native boundary diagnostic required')
    from .release import NativePaperReleaseReader
    from .inventory import fixed_profile
    from application.entrypoints import _outside_installation
    config_path=Path(config_path);config=load_config(config_path);_outside_installation(config.local_data_root)
    if (product_namespace(config)!='LOCAL_RESEARCH' or not config.diagnostic_only or config.paper_runtime_enabled
            or config.cloud_root is not None or require_valid_restoration(config)['status']!='NOT_RESTORED'):
        raise ValueError('Fresh diagnostic-only local profile required; no Paper workflow')
    results=[];missing='qualification-'+'0'*64
    with ExitStack() as stack:
        for role in PROCESS_ROLES:
            if role!='runtime':stack.enter_context(ProcessScopeLock(role+':'+config.product_instance_id,lock_root=operational_lock_root(config)))
        with ProcessScopeLock('runtime:'+config.product_instance_id,lock_root=operational_lock_root(config)):
            if load_config(config_path)!=config or config.local_data_root.exists() and any(config.local_data_root.iterdir()):
                raise ValueError('Unchanged fresh empty diagnostic data required')
            facts=NativePaperReleaseReader(config,receipt_ref=missing)._installed_facts()
            denied(lambda:NativePaperReleaseReader(config,receipt_ref=missing).software_eligible(),reason='STORE_MISSING')
            results.append('ACTUAL_SOFTWARE_STORE_MISSING_DENIED')
            if not config.local_data_root.exists():create_private_directory(config.local_data_root)
            output=config.local_data_root/'native-boundary-diagnostic';create_private_directory(output)
            actual_check,started,finished=_doctor(config,config_path,output)
            if load_config(config_path)!=config:raise ValueError('Boundary diagnostic configuration changed')
            with open_sqlite_platform(config.database_path,research_namespace='LOCAL_RESEARCH'):pass
            denied(lambda:NativePaperReleaseReader(config,receipt_ref=missing).software_eligible(),reason='RECEIPT_MISSING')
            results.append('ACTUAL_SOFTWARE_RECEIPT_MISSING_DENIED')
            profile=fixed_profile(facts['platform_id'])
            captured=diagnostic_receipt_input(facts,profile,actual_check,started,finished)
            with _open_qualification_receipt_owner(config.database_path,namespace='LOCAL_RESEARCH') as owner:
                receipt=owner._append(**captured)
                if owner._append(**captured)!=receipt:raise RuntimeError('Actual receipt replay changed')
                results.append('ACTUAL_DIAGNOSTIC_RECEIPT_REPLAY')
                denied(lambda:owner._append(**{**captured,'checks':(replace(actual_check,log_hash=digest(b'controlled conflicting input')),)}),reason='CONFLICT')
                if owner.get(receipt.receipt_id)!=receipt:raise RuntimeError('Refused conflict changed original receipt')
                results.append('ACTUAL_DIAGNOSTIC_RECEIPT_CONFLICT_DENIED')
            denied(lambda:open_qualification_receipts(config.database_path,namespace='FIXTURE'),reason='NAMESPACE')
            with open_qualification_receipts(config.database_path,namespace='LOCAL_RESEARCH') as reader:
                if reader.get(receipt.receipt_id)!=receipt:raise RuntimeError('Namespace refusal changed original receipt')
            results.append('ACTUAL_RECEIPT_NAMESPACE_DENIED')
            denied(lambda:NativePaperReleaseReader(config,receipt_ref=receipt.receipt_id).software_eligible())
            results.append('ACTUAL_PARTIAL_DOCTOR_RECEIPT_NOT_QUALIFIED')
            denied(lambda:read_runtime_identity(config),RuntimeIdentityUnavailable,reason='NOT_STARTED')
            results.append('ACTUAL_RUNTIME_MISSING_DENIED')
        if load_config(config_path)!=config:raise ValueError('Boundary diagnostic configuration changed')
        with ProcessSupervisor(config,'runtime',config_path=config_path) as supervisor:
            actual=read_runtime_identity(config).identity
            if actual['process_generation_id']!=supervisor.identity['process_generation_id']:raise RuntimeError('Actual native runtime identity differs')
            results.append('ACTUAL_NATIVE_SUPERVISOR_CURRENT_READ')
            denied(lambda:read_runtime_identity(replace(config,product_instance_id=config.product_instance_id+'-wrong')),
                RuntimeIdentityUnavailable,reason='CONFIG_CHANGED')
            results.append('ACTUAL_NATIVE_RUNTIME_WRONG_CONFIG_DENIED')
            results.extend(memory_component_checks(output,config,facts,actual))
        denied(lambda:read_runtime_identity(config),RuntimeIdentityUnavailable,reason='NOT_RUNNING')
        results.append('ACTUAL_NATIVE_RUNTIME_STOPPED_DENIED')
    return dict(schema_version='r7-native-boundary-diagnostic-v1',status='COMPONENT_CHECKS_PASS',
        actual_assertions=len(results),assertions=results,subject=facts,diagnostic_receipt_ref=receipt.receipt_id,
        diagnostic_all_recorded_checks_passed=receipt.passed,qualification_complete=False,completed_pqr_groups=0,
        software_eligibility='NOT_QUALIFIED',synthetic_models='IN_MEMORY_ONLY_NEVER_STORED',
        synthetic_represented_members_not_executed=7,financial_selection='NONE',paper='NOT_STARTED',
        provider_requests=0,credentials='NONE',provider_mutation=0,capital='NONE')
