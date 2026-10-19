"""One explicit headless product launcher; no OS installation or financial grant.

Owns only children it launched. Scheduling uses existing local owner commands;
Paper startup and every entry still require existing native/risk/workflow gates.
"""
import json,os,subprocess,sys,time
from pathlib import Path

from application.cloud.manifest import safe_component
from application.cloud.safe_files import _windows_read,_posix_read
from application.config import load_config,product_namespace
from application.datasets.catalog import canonical,decode,digest
from application.entrypoints import _outside_installation
from application.platform.processes import spawn_owned_service,terminate_owned,owned_contains_pid
from application.platform.shutdown import ManagedStop
from application.platform.supervision import ProcessSupervisor,process_health,_local_path,config_hash
from application.platform.service_stop import observe_service_stop,request_service_stop

_unreaped=[]

def validate_operations(value):
    required={'schema_version','workflow_authorized','actor','roles','scan_inbox','research_policy_ids',
              'queue_reports','interval_seconds','restart_budget','restart_backoff_seconds'}
    if not isinstance(value,dict) or set(value)!=required or value['schema_version']!='r7-local-operations-v0.2':
        raise ValueError('Explicit closed local operations profile required')
    if value['workflow_authorized'] is not True:raise ValueError('Explicit unattended local workflow selection required')
    try:safe_component(value['actor'])
    except Exception:raise ValueError('Explicit local scheduling actor required') from None
    roles=value['roles'];policies=value['research_policy_ids']
    if not isinstance(roles,list) or not 1<=len(roles)<=3 or any(role not in ('control','research','runtime') for role in roles) or len(set(roles))!=len(roles):
        raise ValueError('Unique named local services required')
    if not isinstance(policies,list) or len(policies)>32 or any(not isinstance(policy,str) for policy in policies) or len(set(policies))!=len(policies):
        raise ValueError('Bounded explicit research policy IDs required')
    try:
        for policy in policies:safe_component(policy)
    except Exception:raise ValueError('Explicit local research policy IDs required') from None
    if policies and 'research' not in roles:raise ValueError('Selected research service required for automatic enqueue')
    for key in ('scan_inbox','queue_reports'):
        if type(value[key]) is not bool:raise ValueError('Explicit local schedule switches required')
    for key,lower,upper in (('interval_seconds',5,3600),('restart_budget',0,5),('restart_backoff_seconds',1,60)):
        if type(value[key]) is not int or not lower<=value[key]<=upper:raise ValueError('Bounded local scheduling limits required')
    return json.loads(canonical(value))

def _read_operations(config,path):
    path=Path(path)
    if not path.is_absolute() or '..' in path.parts:raise ValueError('Absolute local operations profile required')
    _local_path(path);_outside_installation(path)
    actual=path.resolve(strict=True)
    if actual.is_relative_to(config.local_data_root):
        raise ValueError('Machine-local workflow selection must be outside portable product data')
    if config.cloud_root is not None and actual.is_relative_to(config.cloud_root):
        raise ValueError('Cloud inputs cannot authorize local unattended workflow')
    raw=(_windows_read if os.name=='nt' else _posix_read)(path,16384,require_single_link=True)
    value=validate_operations(decode(raw))
    return value,digest(canonical(value).encode())

def _command_id(profile_hash,operation,subject,revision):
    return 'schedule-'+digest(canonical([profile_hash,operation,subject,revision]).encode())[7:]

def schedule_once(owners,services,operations,*,submission_offset=0,report_offset=0):
    """Only scan/enqueue/report; never approval, candidate promotion or PaperStart."""
    selected=validate_operations(operations);commitment=digest(canonical(selected).encode())
    result=dict(scan='NOT_SELECTED',enqueued=0,reports_queued=0,refusals=[],paper='NOT_COMMANDED',provider_requests=0,
                next_submission_offset=0,next_report_offset=0)
    if selected['scan_inbox']:
        revision=services.revision('INBOX_SCAN','inbox',{})
        receipt=services.execute('INBOX_SCAN','inbox',{},actor=selected['actor'],human=None,
            command_id=_command_id(commitment,'SCAN','inbox',revision),expected_revision=revision)
        result['scan']=receipt['status']
    if selected['research_policy_ids']:
        # Bound each scheduler pass. Existing queue identity deduplicates retries.
        submissions=services.view('submissions',limit=32,offset=submission_offset)['items']
        result['next_submission_offset']=submission_offset+32 if len(submissions)==32 else 0
        for submission in submissions:
            for policy in selected['research_policy_ids']:
                args=dict(submission_id=submission['submission_id'],policy_id=policy)
                try:
                    revision=services.revision('RESEARCH_ENQUEUE','research',args)
                    services.execute('RESEARCH_ENQUEUE','research',args,actor=selected['actor'],human=None,
                        command_id=_command_id(commitment,'ENQUEUE',args,revision),expected_revision=revision)
                    result['enqueued']+=1
                except Exception as error:
                    if len(result['refusals'])<32:result['refusals'].append(dict(submission_id=submission['submission_id'],policy_id=policy,reason_code=type(error).__name__))
    if selected['queue_reports'] and owners.queue is not None:
        from application.cloud.feedback import queue_feedback
        jobs=owners.queue.list(limit=32,offset=report_offset)
        result['next_report_offset']=report_offset+32 if len(jobs)==32 else 0
        for job in jobs:
            if job['state']!='COMPLETE' or job['owner_run_id'] is None:continue
            with owners.queue.service_factory() as research:
                queue_feedback(research,job['owner_run_id'],performance_opt_in=False)
            result['reports_queued']+=1
    result['publication']='LOCAL_DURABLE_OUTBOX_ONLY;REMOTE_NOT_CONFIGURED'
    return result

def _argv(config_path,role,expected_config_hash):
    prefix=[sys.executable] if getattr(sys,'frozen',False) else [sys.executable,'-m','application']
    return [*prefix,'_product-service','--role',role,'--config',str(config_path),
            '--expected-config-hash',expected_config_hash]

def run_selected_service(config_path,role,expected_config_hash):
    """Pin parent-selected configuration before any child owner/store writes."""
    import re
    if role not in ('control','research','runtime') or not isinstance(expected_config_hash,str) or not re.fullmatch('sha256:[0-9a-f]{64}',expected_config_hash):
        raise ValueError('Exact configured local child service required')
    config=load_config(config_path)
    if config_hash(config)!=expected_config_hash:raise ValueError('COORDINATOR_CHILD_CONFIG_CHANGED')
    if role=='control':
        from application.entrypoints import serve
        return serve(config,config_path=config_path)
    if role=='research':
        from application.research.worker import research_worker
        return research_worker(config_path,expected_config_hash=expected_config_hash)
    from application.paper.entrypoint import paper_worker
    return paper_worker(config_path,expected_config_hash=expected_config_hash)

def _compose(config,operations):
    from application.local_owners import LocalOwners
    owners=LocalOwners(config,namespace=product_namespace(config));services=None
    if operations['scan_inbox'] and owners.inbox_factory is None:raise ValueError('Existing explicit inbox selection required')
    if (operations['research_policy_ids'] or operations['queue_reports'] or 'research' in operations['roles']) and owners.queue is None:
        raise ValueError('Existing explicit research selection required')
    if operations['research_policy_ids'] and any(policy not in owners.resolver.policies for policy in operations['research_policy_ids']):
        raise ValueError('Unknown selected research policy')
    if operations['scan_inbox'] or operations['research_policy_ids']:services=owners.control_services()
    return owners,services

def run_product(config_path,operations_path,*,maximum_cycles=None):
    if maximum_cycles is not None and (type(maximum_cycles) is not int or not 1<=maximum_cycles<=100000):
        raise ValueError('Bounded optional verification cycle limit required')
    config_path=Path(config_path).absolute();operations_path=Path(operations_path).absolute()
    config=load_config(config_path);_outside_installation(config.local_data_root)
    operations,commitment=_read_operations(config,operations_path)
    from application.platform.restoration import require_valid_restoration
    if require_valid_restoration(config)['status']!='NOT_RESTORED':raise ValueError('Restored data requires separate workflow reauthorization')
    if 'runtime' in operations['roles'] and (product_namespace(config)!='LOCAL_RESEARCH' or config.diagnostic_only or not config.paper_runtime_enabled):
        raise ValueError('Explicit ordinary Paper capability and existing native qualification required')
    result=dict(status='STOPPED',roles={role:dict(status='NOT_STARTED',launches=0) for role in operations['roles']},
        operation_profile_hash=commitment,financial_authority='NONE',host_settings='UNCHANGED',
        exposure_status='NOT_ASSERTED',browser='NOT_REQUIRED',all_owned_trees_reaped=True,schedule=None)
    children={};retry_at={};next_schedule=0;cycles=0;submission_offset=0;report_offset=0
    with ManagedStop() as stop,ProcessSupervisor(config,'coordinator',config_path=config_path) as supervisor:
        result['coordinator_process_generation_id']=supervisor.identity['process_generation_id']
        try:
            owners,services=_compose(config,operations)
            while not stop.requested:
                supervisor.require_current()
                if observe_service_stop(supervisor,stop):break
                if _read_operations(config,operations_path)[1]!=commitment:
                    result.update(status='INHIBITED',reason_code='OPERATIONS_PROFILE_CHANGED');break
                now=time.monotonic()
                for role,state in result['roles'].items():
                    owned=children.get(role)
                    if owned is not None:
                        handle,stream=owned
                        health=process_health(config,role)
                        if health.get('pid') and owned_contains_pid(handle,health['pid']):
                            state.update(status='RUNNING',actual_process_generation_id=health['process_generation_id'])
                        if handle.process.poll() is None:continue
                        code=handle.wait(timeout=0)
                        if not handle.termination_report.reaped:
                            raise RuntimeError('COORDINATOR_OWNED_TREE_NOT_REAPED')
                        stream.close();children.pop(role)
                        state.update(status='EXITED',exit_code=code,tree_reaped=True)
                        retry_at[role]=now+operations['restart_backoff_seconds']
                    if now<retry_at.get(role,0):continue
                    if state['launches']>=operations['restart_budget']+1:
                        state['status']='RESTART_BUDGET_EXHAUSTED';continue
                    health=process_health(config,role)
                    if health['status']=='RECENT_HEARTBEAT':
                        state['status']='EXTERNALLY_OWNED';continue
                    logs=config.local_data_root/'worker-logs';logs.mkdir(parents=True,exist_ok=True,mode=0o700)
                    name='coordinator-'+supervisor.identity['process_generation_id']+'-'+role+'-'+str(state['launches']+1)+'.log'
                    stream=(logs/name).open('xb')
                    try:handle=spawn_owned_service(_argv(config_path,role,config_hash(config)),cwd=Path.cwd(),stdout=stream,stderr=subprocess.STDOUT)
                    except BaseException:stream.close();raise
                    children[role]=(handle,stream);state.update(status='STARTING',launches=state['launches']+1)
                if now>=next_schedule and (operations['scan_inbox'] or operations['research_policy_ids'] or operations['queue_reports']):
                    try:
                        result['schedule']=schedule_once(owners,services,operations,submission_offset=submission_offset,report_offset=report_offset)
                        submission_offset=result['schedule']['next_submission_offset'];report_offset=result['schedule']['next_report_offset']
                    except Exception as error:
                        # Existing owner CAS/admission/expiry conflicts remain refusals.
                        result['schedule']=dict(status='REFUSED',reason_code=type(error).__name__)
                    next_schedule=now+operations['interval_seconds']
                cycles+=1
                if maximum_cycles is not None and cycles>=maximum_cycles:break
                stop.wait(.2)
        finally:
            for role,(handle,stream) in children.items():
                state=result['roles'][role];state['forced_stop']=False
                try:
                    health=process_health(config,role)
                    token=health.get('process_generation_id')
                    if token and owned_contains_pid(handle,health['pid']):
                        state['actual_process_generation_id']=token
                        state['stop']=request_service_stop(config,role,expected_process_generation_id=token)['status']
                    try:state['exit_code']=handle.wait(timeout=5)
                    except subprocess.TimeoutExpired:state['forced_stop']=True
                except Exception as error:
                    state['stop_error']=type(error).__name__;state['forced_stop']=handle.process.poll() is None
                finally:
                    try:state['tree_reaped']=terminate_owned(handle,deadline_seconds=5,reason='COORDINATOR_STOP').reaped
                    except Exception as error:state['tree_reaped']=False;state['reap_error']=type(error).__name__
                    try:stream.close()
                    except OSError:state['log_close_error']='LOCAL_LOG_CLOSE_FAILED'
                    if not state['tree_reaped']:_unreaped.append(handle)
                    result['all_owned_trees_reaped'] &= state['tree_reaped']
                    state['status']='FORCED_STOP' if state['forced_stop'] else 'STOPPED' if state.get('exit_code')==0 else 'FAILED'
        if not result['all_owned_trees_reaped']:raise RuntimeError('COORDINATOR_OWNED_TREE_NOT_REAPED')
    return result
