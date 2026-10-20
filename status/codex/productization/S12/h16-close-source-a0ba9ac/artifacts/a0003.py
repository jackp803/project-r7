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
revision='a0ba9ac41929fa61535ee917624dd145d24f84e0'
revision_fact(ROOT,revision,True)
output=BASE/'h16-close-source-a0ba9ac';create_private_directory(output)
modules=('tests.position.test_product_close_observation','tests.position.test_entry_observation',
    'tests.position.test_close_action','tests.position.test_trade_result','tests.execution.test_close',
    'tests.brokers.test_okx_product_close_v02','tests.brokers.test_okx_close_sizing','tests.brokers.test_okx_close_sizing_binding')
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
if b'Ran 88 tests' not in safe:raise ValueError('Actual 88-case result required')
report=dict(revision=revision,scope='E5_ONE_EXPLICIT_CLOSE_SOURCE_ONLY',modules=list(modules),
    tests_run=88,exit_code=code,source_unchanged=True,tree_reaped=bool(cleanup and cleanup.reaped),
    native='NOT_RUN',H16_whole='INCOMPLETE_OWNER_ADAPTER_FUNDING_TRADE_RESULT',
    frozen_inventory='STALE_UNTIL_NEXT_FINAL_CANDIDATE_GENERATION',
    additional_public_requests=0,private_requests=0,credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',
    helper_hash='sha256:'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    log_hash='sha256:'+hashlib.sha256(safe).hexdigest(),started_at=started,finished_at=datetime.now(timezone.utc).isoformat())
report['passed']=code==0 and report['tree_reaped']
write_private_new(output/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
print(json.dumps(report))
raise SystemExit(0 if report['passed'] else 1)
