"""Exact-clean cleanup/funding/close owner regressions, no full H16 credit."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,subprocess,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.qualification import revision_fact,_sanitize
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.platform.private_files import create_private_directory,write_private_new
from strategy.v02.capabilities import _revision
revision=sys.argv[1];revision_fact(ROOT,revision,True);implementation=_revision()
output=BASE/('h16-stop-cleanup-source-'+revision[:7]);create_private_directory(output)
modules=('tests.product.test_trading_stop_cleanup_v02','tests.product.test_trading_protected_close_v02',
    'tests.execution.test_ledger_funding','tests.execution.test_funding','tests.product.test_trading_funding_v02',
    'tests.product.test_trading_close_v02','tests.product.test_trading_close_intent_v02','tests.product.test_trading_close_projection_v02',
    'tests.storage.test_product_dispatch_v02','tests.product.test_trading_dispatch_v02',
    'tests.product.test_trading_position_v02','tests.product.test_trading_protection_monitor_v02',
    'tests.position.test_product_close_observation','tests.brokers.test_okx_product_position_v02',
    'tests.product.test_k05_readonly_history','tests.product.test_k05_feedback_privacy')
owned=None;cleanup=None;failure_type=None;started=datetime.now(timezone.utc).isoformat();code=None
try:
    with (output/'source.raw').open('xb') as stream:
        owned=spawn_owned([sys.executable,'-X','utf8','-m','unittest','-v',*modules],cwd=ROOT,
            limits=ResourceLimits(5400),stdout=stream,stderr=subprocess.STDOUT)
        code=owned.wait()
except Exception as error:
    failure_type=type(error).__name__
    code=-1
finally:
    if owned is not None:cleanup=terminate_owned(owned,deadline_seconds=10)
safe=_sanitize((output/'source.raw').read_text(encoding='utf-8'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').encode()
write_private_new(output/'source.log',safe);(output/'source.raw').unlink()
revision_fact(ROOT,revision,True)
counts=re.findall(rb'Ran (\d+) tests? in ',safe);count=int(counts[-1]) if counts else None
report=dict(executable_revision=revision,implementation_hash=implementation,scope='FIXTURE_OWNED_STOP_CLEANUP_AND_AFFECTED_OWNERS_SOURCE_ONLY',
    modules=list(modules),tests_run=count,exit_code=code,failure_type=failure_type,source_unchanged=_revision()==implementation,
    tree_reaped=bool(cleanup and cleanup.reaped),source_provenance='R7_FIXTURE_ALLOCATED_FUNDING_LEDGER',
    actual_production_ledger='UNSUPPORTED_NOT_CALLED',H16_complete='NOT_CLAIMED_TRADE_RESULT_AND_JOINED_FINALIZATION_PENDING',
    K05_acceptance='NOT_CLAIMED_GENUINE_CLOSED_DISPATCH_PENDING',native_full='NOT_RUN_FOR_THIS_SOURCE',real_cloud='NOT_RUN',
    additional_public_requests=0,private_requests=0,credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',
    log_hash='sha256:'+hashlib.sha256(safe).hexdigest(),helper_hash='sha256:'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    started_at=started,finished_at=datetime.now(timezone.utc).isoformat())
report['passed']=code==0 and count==158 and b'\nOK\n' in safe and b'skipped=' not in safe and report['source_unchanged'] and report['tree_reaped']
write_private_new(output/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
print(json.dumps(report),flush=True)
raise SystemExit(0 if report['passed'] else 1)
