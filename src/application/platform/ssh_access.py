"""Operator-only SSH argv plan and public local health; no SSH/key access."""
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from application.platform.processes import ResourceLimits,spawn_owned
from application.platform._loopback_probe import decode_status,_pairs

def _port(value,*,api):
    if type(value) is not int or not (1024 if api else 1)<=value<=65535:
        raise ValueError('Explicit bounded port required')
    return value

def _host(value):
    if not isinstance(value,str) or not value or len(value)>253:
        raise ValueError('Canonical operator SSH host required')
    try:
        address=ipaddress.ip_address(value)
    except ValueError:
        if (re.fullmatch(r'[0-9.]+',value) or
                any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',label) for label in value.split('.'))):
            raise ValueError('Canonical operator SSH host required') from None
    else:
        if str(address)!=value:raise ValueError('Canonical operator SSH address required')
    return value

def plan_ssh_tunnel(host,username,*,api_port=8765,ssh_port=22):
    host=_host(host);_port(api_port,api=True);_port(ssh_port,api=False)
    if (not isinstance(username,str) or username=='root'
            or not re.fullmatch(r'[a-z_][a-z0-9_-]{0,31}',username)):
        raise ValueError('Explicit unprivileged operator SSH username required')
    argv=['ssh','-N','-T','-a','-F','none','-o','ExitOnForwardFailure=yes','-o','GatewayPorts=no',
        '-o','StrictHostKeyChecking=yes','-p',str(ssh_port),'-l',username,
        '-L',f'127.0.0.1:{api_port}:127.0.0.1:{api_port}',host]
    result=dict(schema_version='r7-ssh-tunnel-plan-v0.2',status='PLANNED_ONLY',argv=argv,
        browser_url=f'http://127.0.0.1:{api_port}/',ssh_connection='NOT_STARTED',credentials='NOT_READ',
        tunnel_commissioning='NOT_RUN',host_origin_boundary='SAME_LOCAL_AND_REMOTE_API_PORT_REQUIRED',
        financial_authority='NONE')
    raw=json.dumps(result,sort_keys=True,separators=(',',':')).encode('utf-8')
    result['plan_hash']='sha256:'+hashlib.sha256(raw).hexdigest()
    return result

def _probe_argv(port,namespace):
    suffix=['--port',str(port),'--expected-namespace',namespace]
    if getattr(sys,'frozen',False):return [sys.executable,'_auth-status-probe',*suffix]
    return [sys.executable,str(Path(__file__).with_name('_loopback_probe.py')),*suffix]

def probe_loopback_auth_status(port,*,expected_namespace='LOCAL_RESEARCH',deadline_seconds=4):
    _port(port,api=True)
    if expected_namespace not in ('LOCAL_RESEARCH','FIXTURE'):
        raise ValueError('Explicit public namespace required')
    if type(deadline_seconds) is not int or not 1<=deadline_seconds<=10:
        raise ValueError('Bounded owned probe deadline required')
    env={key:os.environ[key] for key in ('SystemRoot','WINDIR','SystemDrive','TEMP','TMP') if key in os.environ}
    env.update(PATH='',PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
    owned=spawn_owned(_probe_argv(port,expected_namespace),cwd=Path(sys.executable).absolute().parent,
        limits=ResourceLimits(deadline_seconds),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=env)
    code=owned.wait()
    facts=dict(tree_reaped=owned.termination_report.reaped,child_exit_code=code,ssh_connection='NOT_STARTED',
        tunnel_provenance='UNVERIFIED_LOCAL_ENDPOINT_ONLY',credentials='NONE',financial_authority='NONE',
        actual_provider_requests=0)
    if not facts['tree_reaped']:
        owned.process.stdout.close()
        return dict(facts,status='UNAVAILABLE',reason_code='PROBE_CLEANUP_FAILED')
    if owned.termination_report.reason=='TIMEOUT':
        owned.process.stdout.close()
        return dict(facts,status='UNAVAILABLE',reason_code='PROBE_DEADLINE')
    try:raw=owned.process.stdout.read(4097)
    finally:owned.process.stdout.close()
    try:
        if len(raw)>4096:raise ValueError('Bounded probe reply required')
        result=json.loads(raw.decode('utf-8'),object_pairs_hook=_pairs)
        if code==0 and type(result) is dict and set(result)=={'status','public_auth_status'} and result['status']=='PUBLIC_AUTH_STATUS_AVAILABLE':
            status=decode_status(json.dumps(result['public_auth_status']).encode('utf-8'),expected_namespace)
            return dict(facts,status='PUBLIC_AUTH_STATUS_AVAILABLE',public_auth_status=status)
        if (code==2 and type(result) is dict and set(result)=={'status','reason_code'} and result['status']=='UNAVAILABLE'
                and result['reason_code'] in ('REDIRECT_FORBIDDEN','PUBLIC_STATUS_UNAVAILABLE','PUBLIC_STATUS_INVALID')):
            return dict(facts,**result)
    except Exception:pass
    return dict(facts,status='UNAVAILABLE',reason_code='PROBE_PROTOCOL_INVALID')
