"""Additional exact native SSH/public access subject and evidence checks."""
import hashlib,json
from pathlib import Path
from s13_acceptance_integrity import validate_primary_artifacts as _primary,require_artifact,require_sequence,digest,publish_retention_manifest
COMMANDS=['plan-hostname','plan-ipv6','invalid-host','invalid-root','init-profile','unavailable-before-start',
    'public-probe','wrong-namespace','proxy-ignored','control-owner']
SCENARIOS=['NATIVE_LITERAL_LOOPBACK_SSH_PLAN_WITHOUT_CONNECTION','NATIVE_CANONICAL_IPV6_DESTINATION_PLAN',
    'NATIVE_INVALID_HOST_DENIED','NATIVE_INVALID_ROOT_DENIED','NATIVE_PUBLIC_PROFILE_HAS_NO_TRADING_OR_AUTH_ENROLLMENT',
    'NATIVE_MISSING_PUBLIC_ENDPOINT_DENIED_AND_CHILD_REAPED','ACTUAL_NATIVE_PARENT_AND_FROZEN_CHILD_READ_ACTUAL_PUBLIC_ENDPOINT',
    'NATIVE_PUBLIC_NAMESPACE_MISMATCH_DENIED','NATIVE_PUBLIC_PROBE_IGNORES_ENVIRONMENT_PROXY',
    'ACTUAL_NATIVE_CONTROL_OWNER_TREE_REAPED_WITHOUT_SSH_CONNECTION']

def validate_ssh_report(folder,report,identity,verified,project):
    if (report['identity']!=identity or not report['passed'] or report['command_count']!=10 or report['scenario_count']!=10
            or report['ssh_connection']!='NOT_STARTED' or report['real_tunnel']!='NOT_RUN' or report['credentials']!='NONE'
            or report['actual_provider_requests']!=0 or report['financial_authority']!='NONE'):
        raise ValueError('Exact native public access boundary differs')
    require_sequence(report['commands'],COMMANDS);require_sequence(report['scenarios'],SCENARIOS)
    if not all(s['result']=='PASS' for s in report['scenarios']):raise ValueError('Native access scenario did not pass')
    for row in report['commands']:
        if not row['passed'] or not row['tree_reaped'] or row['log']!=row['name']+'.log':raise ValueError('Actual native access command missing')
        if row['name']!='control-owner' and row['exit_code']!=row['expected_exit_code']:raise ValueError('Native access exit disposition differs')
        log=require_artifact(folder,row['log'],row['log_sha256']);verified[log.relative_to(project).as_posix()]=row['log_sha256']
        if 'result' in row and json.loads(log.read_bytes())!=row['result']:raise ValueError('Native access observed result differs')
    before=report['control_generation_before'];after=report['control_generation_after']
    if (before!=after or before['financial_authority']!='NONE' or before['role']!='control'
            or before['executable_revision']!=identity['executable_revision'] or before['build_hash']!=identity['build_hash']
            or type(before['pid']) is not int or before['pid']<=0 or not before['process_generation_id']):
        raise ValueError('Actual owned native control generation differs')
    results={row['name']:row.get('result') for row in report['commands']}
    for name in ('public-probe','proxy-ignored'):
        value=results[name]
        if (value['status']!='PUBLIC_AUTH_STATUS_AVAILABLE' or not value['tree_reaped'] or value['child_exit_code']!=0
                or value['tunnel_provenance']!='UNVERIFIED_LOCAL_ENDPOINT_ONLY' or value['ssh_connection']!='NOT_STARTED'
                or value['actual_provider_requests']!=0 or value['credentials']!='NONE'
                or value['public_auth_status']!=dict(configured=False,namespace='LOCAL_RESEARCH',enrollment='LOCAL_CLI_ONLY')):
            raise ValueError('Actual native public child facts differ')
    for name,reason in [('unavailable-before-start','PUBLIC_STATUS_UNAVAILABLE'),('wrong-namespace','PUBLIC_STATUS_INVALID')]:
        value=results[name]
        if value['status']!='UNAVAILABLE' or value['reason_code']!=reason or not value['tree_reaped'] or 'public_auth_status' in value:
            raise ValueError('Native public access denial differs')

def validate_primary_artifacts(*args,**kwargs):
    result=_primary(*args,**kwargs);repo,revision,source=args[:3];project=repo.parent.parent
    verified=result['verified_artifact_hashes'];identity=args[9]['identity']
    folder=project/f'artifacts/r7-native-S13-ssh-access-{revision[:7]}'
    path=folder/'native-ssh-access.json';raw=path.read_bytes();report=json.loads(raw)
    require_artifact(folder,path.name,'sha256:'+hashlib.sha256(raw).hexdigest())
    verified[path.relative_to(project).as_posix()]='sha256:'+hashlib.sha256(raw).hexdigest()
    validate_ssh_report(folder,report,identity,verified,project)
    for name in ('qualification-context.json','hardware-observations.json'):
        path=source/name;verified[path.relative_to(project).as_posix()]=digest(path)
        require_artifact(source,name,verified[path.relative_to(project).as_posix()])
    context=json.loads((source/'qualification-context.json').read_bytes())
    if context['launcher_hash']!=digest(project/'artifacts/s13_ssh_qualify.py') or context['configuration']['expected_revision']!=revision:
        raise ValueError('Actual full-source launcher subject differs')
    pipeline=project/f'artifacts/S13-recovery-{revision[:7]}-serial-pipeline.json';raw=pipeline.read_bytes();data=json.loads(raw)
    require_sequence(data['commands'],['native-build','native-service-denial','native-ssh-access','native-smoke',
        'native-research','native-cloud','native-restore','full-source'],key='label')
    if not data['passed'] or data['revision']!=revision or data['worktree']!='CLEAN':raise ValueError('Exact serial pipeline differs')
    verified[pipeline.relative_to(project).as_posix()]='sha256:'+hashlib.sha256(raw).hexdigest()
    for row in data['commands']:
        if not row['passed'] or not row['tree_reaped'] or row['exit_code']!=0:raise ValueError('Pipeline command did not pass')
        file=require_artifact(project/'artifacts',row['log'],row['log_sha256'])
        verified[file.relative_to(project).as_posix()]=row['log_sha256']
    result.update(native_scenarios=result['native_scenarios']+10,native_commands=result['native_commands']+10,
        ssh_access_scenarios=10,ssh_access_commands=10,real_ssh='NOT_RUN;LOCAL_PUBLIC_ENDPOINT_ONLY')
    return result
