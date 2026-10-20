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
output=BASE/('h16-terminal-owner-source-'+revision[:7]);create_private_directory(output)
modules=('tests.product.test_trading_terminal_stop_v02','tests.brokers.test_okx_terminal_stop_v02','tests.brokers.test_okx_product_readback_v02','tests.brokers.test_okx_product_inventory_v02','tests.storage.test_stop_cleanup_constraints','tests.product.test_trading_cleanup_immutability_v02')
owned=None;cleanup=None;failure_type=None;started=datetime.now(timezone.utc).isoformat();code=None
try:
    with (output/'source.raw').open('xb') as stream:
        owned=spawn_owned([sys.executable,'-X','utf8','-m','unittest','-v',*modules],cwd=ROOT,
            limits=ResourceLimits(900),stdout=stream,stderr=subprocess.STDOUT)
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
report=dict(executable_revision=revision,implementation_hash=implementation,scope='FIXTURE_TERMINAL_OWNER_AND_GENUINE_VALID_FK_CLEANUP_WITH_PURE_BROKER_REGRESSIONS',
    modules=list(modules),tests_run=count,exit_code=code,failure_type=failure_type,source_unchanged=_revision()==implementation,
    tree_reaped=bool(cleanup and cleanup.reaped),source_provenance='ACTUAL_GUARDED_FAKE_TERMINAL_STOP_OWNER_NO_FINANCIAL_FINALIZATION',
    actual_production_ledger='UNSUPPORTED_NOT_CALLED',H16_complete='NOT_CLAIMED_TRADE_RESULT_AND_JOINED_FINALIZATION_PENDING',
    K05_acceptance='NOT_CLAIMED_GENUINE_CLOSED_DISPATCH_PENDING',native_full='NOT_RUN_FOR_THIS_SOURCE',real_cloud='NOT_RUN',
    additional_public_requests=0,private_requests=0,credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',
    log_hash='sha256:'+hashlib.sha256(safe).hexdigest(),helper_hash='sha256:'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    started_at=started,finished_at=datetime.now(timezone.utc).isoformat())
report['passed']=code==0 and count==20 and b'\nOK\n' in safe and b'skipped=' not in safe and report['source_unchanged'] and report['tree_reaped']
write_private_new(output/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
print(json.dumps(report),flush=True)
raise SystemExit(0 if report['passed'] else 1)
