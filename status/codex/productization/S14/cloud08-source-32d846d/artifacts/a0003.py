"""Exact-clean first E5 close slice only, not full H16/native qualification."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.qualification import revision_fact,_sanitize
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.platform.private_files import create_private_directory,write_private_new
revision='32d846d968c45c41471f1ca23cb9f2a87d33d36a'
revision_fact(ROOT,revision,True)
output=BASE/'cloud08-source-32d846d';create_private_directory(output)
modules=('tests.product.test_api_owner_services','tests.application.test_cloud_bridge')
owned=None;cleanup=None;started=datetime.now(timezone.utc).isoformat()
try:
    with (output/'source.raw').open('xb') as stream:
        owned=spawn_owned([sys.executable,'-X','utf8','-m','unittest','-v',*modules],cwd=ROOT,
            limits=ResourceLimits(300),stdout=stream,stderr=subprocess.STDOUT)
        code=owned.wait()
finally:
    if owned is not None:cleanup=terminate_owned(owned,deadline_seconds=5)
raw=(output/'source.raw').read_bytes()
safe=(_sanitize(raw.decode('utf-8'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n')).encode()
write_private_new(output/'source.log',safe);(output/'source.raw').unlink()
revision_fact(ROOT,revision,True)
if b'Ran 35 tests' not in safe:raise ValueError('Actual 35-case result required')
report=dict(revision=revision,scope='CLOUD08_INTAKE_DELIVERY_SOURCE_ONLY',modules=list(modules),
    tests_run=35,exit_code=code,source_unchanged=True,tree_reaped=bool(cleanup and cleanup.reaped),
    native='NOT_RUN',real_cloud='NOT_RUN',report_delivery='NOT_IMPLEMENTED_BY_THIS_SLICE',
    frozen_inventory='STALE_UNTIL_NEXT_FINAL_CANDIDATE_GENERATION',
    additional_public_requests=0,private_requests=0,credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',
    helper_hash='sha256:'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    log_hash='sha256:'+hashlib.sha256(safe).hexdigest(),started_at=started,finished_at=datetime.now(timezone.utc).isoformat())
report['passed']=code==0 and report['tree_reaped']
write_private_new(output/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
print(json.dumps(report))
raise SystemExit(0 if report['passed'] else 1)
