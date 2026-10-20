"""Run only the reviewed supplement; validation-lifetime system awake only."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,runpy,sys

BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(BASE),str(BASE.parent),str(ROOT/'src'),str(ROOT)]
from local_windows_qualification_awake import awake_request
from application.platform.private_files import create_private_directory,write_private_new
from application.qualification import revision_fact

REV='3ae6460c69a8a8f90588c396b819af7079e7546d'
helper=BASE/'verify_b03_m04_f11_supplement.py'
expected='ef460fbf36d9aa9cdd16cffb69682b49a19b4489bb1ad7e167920f1206213995'
if hashlib.sha256(helper.read_bytes()).hexdigest()!=expected:raise ValueError('Reviewed helper changed')
revision_fact(ROOT,REV,True)
record_root=BASE/'b03-m04-f11-awake-records-3ae6460'
if record_root.exists():raise ValueError('Fresh wrapper evidence required')
create_private_directory(record_root)
record=record_root/'temporary-awake.json'
report=dict(revision=REV,started_at_utc=datetime.now(timezone.utc).isoformat(),helper_sha256=expected,
    scope='AUTHORIZED_VALIDATION_LIFETIME_SYSTEM_AWAKE_ONLY',permanent_settings_changed=False,
    provider_requests=0,credentials='NONE',capital='NONE')
code=2
try:
    with awake_request() as awake:
        report['awake']=awake
        try:runpy.run_path(str(helper),run_name='__main__')
        except SystemExit as error:code=error.code if type(error.code) is int else 2
except BaseException as error:report['error_type']=type(error).__name__
finally:
    report.update(exit_code=code,finished_at_utc=datetime.now(timezone.utc).isoformat(),
        helper_unchanged=hashlib.sha256(helper.read_bytes()).hexdigest()==expected)
    try:revision_fact(ROOT,REV,True);report['source_unchanged']=True
    except BaseException as error:report['source_unchanged']=False;report['guard_error_type']=type(error).__name__
    report['passed']=code==0 and report.get('source_unchanged') is True and report['helper_unchanged'] and report.get('awake',{}).get('restored') is True and 'error_type' not in report
    write_private_new(record,(json.dumps(report,indent=2)+'\n').encode())
print(json.dumps(dict(passed=report['passed'],exit_code=code,awake_restored=report.get('awake',{}).get('restored'))),flush=True)
raise SystemExit(0 if report['passed'] else 2)
