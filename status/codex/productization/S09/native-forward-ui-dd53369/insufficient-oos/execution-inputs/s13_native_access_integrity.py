"""Bind public endpoint qualification to its actual Windows owned generation."""
from contextlib import closing
import ctypes,json,sqlite3
from pathlib import Path
from urllib.request import ProxyHandler,build_opener
from application.platform._loopback_probe import NoRedirect
from application.config import load_config
from application.platform.supervision import config_hash,process_health

def build_loopback_opener():
    return build_opener(ProxyHandler({}),NoRedirect())

def _in_owned_windows_job(owner,pid):
    from ctypes import wintypes as w
    job=owner._job
    if job is None or not job.handle:return False
    count=64
    while True:
        class ProcessIds(ctypes.Structure):
            _fields_=[('assigned',w.DWORD),('listed',w.DWORD),('pids',ctypes.c_size_t*count)]
        ids=ProcessIds()
        if job.kernel.QueryInformationJobObject(job.handle,3,ctypes.byref(ids),ctypes.sizeof(ids),None):
            return pid in list(ids.pids)[:ids.listed]
        error=ctypes.get_last_error()
        if error!=234 or count>=4096:raise ValueError('Actual owned control membership unavailable')
        count*=2

def require_owned_generation(owner,config_path,identity,previous=None):
    if owner.process.poll() is not None:raise ValueError('Actual native control owner exited')
    config=load_config(Path(config_path));health=process_health(config,'control')
    if health.get('status')!='RECENT_HEARTBEAT':raise ValueError('Actual native control generation is not recently running')
    with closing(sqlite3.connect((config.local_data_root/'process-supervision.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
        row=db.execute("SELECT identity_json,state FROM process_sessions WHERE role='control'").fetchone()
    if row is None:raise ValueError('Actual native control generation missing')
    generation=json.loads(row[0])
    if (row[1]!='RUNNING' or generation['pid']!=health['pid'] or generation['product_instance_id']!=config.product_instance_id
            or generation['executable_revision']!=identity['executable_revision'] or generation['build_hash']!=identity['build_hash']
            or generation['config_hash']!=config_hash(config) or generation['financial_authority']!='NONE'
            or generation['process_generation_id']!=health['process_generation_id'] or not _in_owned_windows_job(owner,generation['pid'])
            or (previous is not None and previous!=generation) or owner.process.poll() is not None):
        raise ValueError('Actual native owned control generation mismatch')
    return generation
