"""Local private cooperative stop, fenced to an actual process incarnation.

The request never sends a signal, changes a journal or asserts exposure is flat.
Only the owning loop observes it at a transaction boundary. Old requests are
retained and cannot target a successor generation.
"""
import json
from pathlib import Path
import re

from application.cloud.safe_files import read_bounded
from application.platform.private_files import create_private_directory,require_private,write_private_new
from application.platform.shutdown import ManagedStop
from application.platform.supervision import PROCESS_ROLES,ProcessSupervisor,config_hash,process_health
from registry.product_assessment import canonical


def _request_path(config,token):
    if not isinstance(token,str) or not re.fullmatch('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',token):
        raise ValueError('Actual local process incarnation required')
    return config.local_data_root/'managed-stop-requests'/(token+'.json')


def _payload(config,identity):
    return dict(schema_version='r7-managed-process-stop-v0.2',role=identity['role'],
        product_instance_id=config.product_instance_id,config_hash=config_hash(config),
        generation=identity['generation'],process_generation_id=identity['process_generation_id'],
        action='COOPERATIVE_OWNER_STOP',financial_authority='NONE',exposure_status='NOT_ASSERTED')


def request_service_stop(config,role,*,expected_process_generation_id=None):
    if role not in PROCESS_ROLES:raise ValueError('Named local process role required')
    health=process_health(config,role)
    if expected_process_generation_id is not None and health.get('process_generation_id')!=expected_process_generation_id:
        raise ValueError('Process changed before incarnation-fenced cooperative stop')
    if health['status']!='RECENT_HEARTBEAT':
        return dict(status='NO_CURRENT_PROCESS',role=role,financial_authority='NONE',exposure_status='NOT_ASSERTED')
    path=_request_path(config,health['process_generation_id']);raw=canonical(_payload(config,health)).encode('utf-8')
    if not path.parent.exists():
        try:create_private_directory(path.parent)
        except FileExistsError:pass
    require_private(path.parent,directory=True)
    try:write_private_new(path,raw)
    except FileExistsError:
        require_private(path)
        if read_bounded(path.parent,path.name,4096)!=raw:raise ValueError('Conflicting private stop request')
    current=process_health(config,role)
    if current.get('process_generation_id')!=health['process_generation_id']:
        raise ValueError('Process changed before cooperative request confirmation')
    return dict(status='COOPERATIVE_STOP_REQUESTED',role=role,generation=health['generation'],
        process_generation_id=health['process_generation_id'],financial_authority='NONE',exposure_status='NOT_ASSERTED')


def observe_service_stop(supervisor,stop):
    if not isinstance(supervisor,ProcessSupervisor) or not isinstance(stop,ManagedStop) or supervisor.identity is None:
        raise ValueError('Actual owning process and managed stop required')
    path=_request_path(supervisor.config,supervisor.identity['process_generation_id'])
    if not path.exists():return False
    require_private(path.parent,directory=True);require_private(path)
    raw=read_bounded(path.parent,path.name,4096)
    if raw!=canonical(_payload(supervisor.config,supervisor.identity)).encode('utf-8'):
        raise ValueError('Private cooperative stop binding invalid')
    supervisor.require_current();stop.request()
    return True
