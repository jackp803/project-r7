"""Explicit native root-only owned service files; no enable/start or data changes."""
from dataclasses import asdict
import hashlib,json,re
from application.platform.service_guard import verify_service_subject
from application.platform.service_plan import render_service_plan
from application.platform.service_admin_files import LinuxServiceBackend,ServiceAdminPrerequisiteError

TARGETS=('/etc/systemd/system/r7-control.service','/etc/systemd/system/r7-research.service','/etc/tmpfiles.d/r7-scopes.conf')
RECEIPT='/var/lib/r7-service-admin/installed-services.json'
UNITS=('r7-control.service','r7-research.service')
def _bytes(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode('utf-8')
def _hash(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()

def _manager_state(backend,name):
    state=backend.manager_state(name)
    keys={'LoadState','ActiveState','SubState','UnitFileState','FragmentPath','DropInPaths','Job'}
    if (type(state) is not dict or set(state)!=keys or not all(type(v) is str for v in state.values())
            or state['LoadState'] not in ('not-found','loaded') or state['ActiveState']!='inactive'
            or state['SubState']!='dead' or state['UnitFileState'] not in ('','disabled','static','not-found')
            or state['Job'] not in ('','0') or state['DropInPaths'] or backend.has_dropin(name)):
        raise ValueError('Inactive disabled exact manager state without jobs or drop-ins required')
    if state['LoadState']=='loaded':
        if state['FragmentPath']!='/etc/systemd/system/'+name:raise ValueError('Foreign service fragment cannot be managed')
    elif state['FragmentPath'] or state['UnitFileState'] not in ('','not-found'):
        raise ValueError('Unambiguous absent manager state required')
    return state

def _prepare(backend,config_path,action,expected):
    subject=verify_service_subject(config_path,**expected)
    plan=render_service_plan(subject)
    content={TARGETS[0]:plan['units'][UNITS[0]].encode('utf-8'),TARGETS[1]:plan['units'][UNITS[1]].encode('utf-8'),
        TARGETS[2]:(plan['scope_lock_provisioning']['rule']+'\n').encode('utf-8')}
    hashes={path:_hash(raw) for path,raw in content.items()}
    receipt=_bytes(dict(schema_version='r7-owned-service-files-v0.2',plan_hash=plan['plan_hash'],subject_hash=_hash(_bytes(asdict(subject))),
        managed_files=hashes,financial_authority='NONE',runtime='NOT_DELIVERED_CONTINUOUS_COMPOSITION_REQUIRED'))
    states={};current={}
    for path in (*TARGETS,RECEIPT):
        states[path],current[path]=backend.snapshot(path)
    if current[RECEIPT] is None:
        if action=='uninstall' or any(current[path] is not None for path in TARGETS):
            raise ValueError('Exact owned receipt required; preserve foreign or partial files')
        installed=False
    else:
        if current[RECEIPT]!=receipt or any(current[path]!=content[path] for path in TARGETS):
            raise ValueError('Exact complete owned subject and file bytes required')
        installed=True
    manager={name:_manager_state(backend,name) for name in UNITS}
    if not installed and any(value['LoadState']!='not-found' for value in manager.values()):
        raise ValueError('Fresh installation cannot replace an existing manager unit')
    commitment=dict(action=action,plan_hash=plan['plan_hash'],subject_hash=_hash(_bytes(asdict(subject))),
        file_hashes=hashes,receipt_sha256=_hash(receipt),existing_targets=states,manager=manager,parents=backend.parent_facts())
    operation_hash=_hash(_bytes(commitment))
    display=dict(schema_version='r7-service-admin-plan-v0.2',status='DRY_RUN',action=action,operation_hash=operation_hash,
        file_hashes=hashes,rendered_files={path:raw.decode('utf-8') for path,raw in content.items()},
        ownership_receipt=RECEIPT,intended_changes=[] if action=='install' and installed else list(TARGETS)+[RECEIPT],
        service_start='NOT_PERFORMED',service_enable='NOT_PERFORMED',scope_inodes='PRESERVED',
        binary_config_data_staging='PRESERVED',native_service_acceptance='NOT_RUN',financial_authority='NONE',
        runtime='NOT_DELIVERED_CONTINUOUS_COMPOSITION_REQUIRED')
    return display,content,receipt,states,installed

def manage_services(config_path,*,action,apply=False,operation_hash=None,_backend=None,**expected):
    if action not in ('install','uninstall') or type(apply) is not bool:
        raise ValueError('Explicit bounded service administration required')
    # The CLI never accepts backend injection or arbitrary unit/system-root inputs.
    unknown=set(expected)-{'expected_revision','expected_build_hash','expected_config_hash','service_user','expected_memory_bytes'}
    if unknown:raise TypeError('Only exact typed service subject arguments are supported')
    if apply and (not isinstance(operation_hash,str) or not re.fullmatch('sha256:[0-9a-f]{64}',operation_hash)):
        raise ValueError('Apply requires the displayed exact operation commitment')
    if not apply and operation_hash is not None:raise ValueError('Operation commitment is an explicit apply argument')
    try:selected_backend=LinuxServiceBackend() if _backend is None else _backend
    except ServiceAdminPrerequisiteError as error:
        return dict(schema_version='r7-service-admin-plan-v0.2',status='PREREQUISITE_REQUIRED',action=action,
            required_directory=error.required_directory,required_owner='root:root',required_mode='0700',
            existing_directory_policy='PRESERVE_AND_INSPECT;NO_OWNER_OR_MODE_REPAIR',applied=False,
            service_start='NOT_PERFORMED',service_enable='NOT_PERFORMED',native_service_acceptance='NOT_RUN',financial_authority='NONE')
    with selected_backend as backend:
        display,content,receipt,states,installed=_prepare(backend,config_path,action,expected)
        if not apply:return display
        if operation_hash!=display['operation_hash']:raise ValueError('Displayed operation changed; inspect a new dry run')
        # Revalidate actual native account, files, config, hardware, restoration,
        # targets, parents and manager immediately before any mutation.
        fresh,new_content,new_receipt,new_states,new_installed=_prepare(backend,config_path,action,expected)
        if fresh!=display or new_content!=content or new_receipt!=receipt or new_states!=states or new_installed!=installed:
            raise ValueError('Exact service administration subject changed')
        result={key:value for key,value in display.items() if key not in ('rendered_files','intended_changes')}
        result.update(applied=True,completed_files=[],manager_reload='NOT_ATTEMPTED')
        if action=='install' and installed:return dict(result,status='ALREADY_INSTALLED')
        try:
            if action=='install':
                for path,raw in content.items():
                    backend.write_new(path,raw,0o644);result['completed_files'].append(path)
                backend.write_new(RECEIPT,receipt,0o600);result['completed_files'].append(RECEIPT)
            else:
                for path in TARGETS:
                    backend.remove_exact(path,states[path]);result['completed_files'].append(path)
                audit='/var/lib/r7-service-admin/uninstalled-'+operation_hash[7:]+'.json'
                backend.write_new(audit,_bytes(dict(schema_version='r7-service-uninstall-disposition-v0.2',operation_hash=operation_hash,
                    removed_files=display['file_hashes'],preserved='BINARY_CONFIG_DATA_STAGING_SHARED_SCOPE_INODES',financial_authority='NONE')),0o600)
                backend.remove_exact(RECEIPT,states[RECEIPT]);result['completed_files'].append(RECEIPT)
                result['audit_disposition']=audit
        except (OSError,ValueError):
            return dict(result,status='INCOMPLETE',reason_code='FILE_OPERATION_FAILED;PRESERVE_AND_INSPECT_PARTIAL_STATE',
                preserved_removals=list(getattr(backend,'preserved_removals',[])))
        try:reloaded=backend.reload()
        except (OSError,ValueError):reloaded=False
        result['manager_reload']='PASS' if reloaded else 'FAILED'
        result['status']=('FILES_INSTALLED' if action=='install' else 'FILES_REMOVED')+('' if reloaded else '_RELOAD_FAILED')
        return result
