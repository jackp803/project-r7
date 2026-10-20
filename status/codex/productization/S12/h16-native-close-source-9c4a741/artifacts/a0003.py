"""One exact-clean native-close SOURCE slice; no full/native H16 credit."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.qualification import revision_fact,_sanitize
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.platform.private_files import create_private_directory,write_private_new
from strategy.v02.capabilities import _revision

revision=sys.argv[1]
revision_fact(ROOT,revision,True);implementation=_revision()
output=BASE/('h16-native-close-source-'+revision[:7]);create_private_directory(output)
modules=('tests.product.test_trading_close_v02','tests.product.test_trading_close_projection_v02',
    'tests.storage.test_product_dispatch_v02','tests.product.test_trading_dispatch_v02',
    'tests.product.test_trading_position_v02','tests.product.test_trading_protection_monitor_v02',
    'tests.position.test_product_close_observation','tests.brokers.test_okx_product_position_v02')
owned=None;cleanup=None;started=datetime.now(timezone.utc).isoformat();code=None
try:
    with (output/'source.raw').open('xb') as stream:
        owned=spawn_owned([sys.executable,'-X','utf8','-m','unittest','-v',*modules],cwd=ROOT,
            limits=ResourceLimits(1200),stdout=stream,stderr=subprocess.STDOUT)
        code=owned.wait()
finally:
    if owned is not None:cleanup=terminate_owned(owned,deadline_seconds=5)
raw=(output/'source.raw').read_bytes()
safe=(_sanitize(raw.decode('utf-8'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n')).encode()
write_private_new(output/'source.log',safe);(output/'source.raw').unlink()
revision_fact(ROOT,revision,True)
unchanged=_revision()==implementation
passed=(code==0 and b'Ran 76 tests' in safe and b'\nOK\n' in safe and unchanged and bool(cleanup and cleanup.reaped))
report=dict(revision=revision,implementation_hash=implementation,scope='NATIVE_CLOSE_OWNER_SOURCE_ONLY',
    modules=list(modules),tests_run=76 if b'Ran 76 tests' in safe else None,exit_code=code,
    source_unchanged=unchanged,tree_reaped=bool(cleanup and cleanup.reaped),passed=passed,
    native='NOT_RUN',H16_whole='INCOMPLETE_ACK_INTENT_STOP_CLEANUP_FUNDING_TRADE_RESULT',
    frozen_inventory='STALE_UNTIL_NEXT_FINAL_CANDIDATE_GENERATION',
    additional_public_requests=0,private_requests=0,credentials='NONE',capital='NONE',live='NOT_STARTED',github_compute='NOT_USED',
    helper_hash='sha256:'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    log_hash='sha256:'+hashlib.sha256(safe).hexdigest(),started_at=started,finished_at=datetime.now(timezone.utc).isoformat())
write_private_new(output/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
print(json.dumps(report));raise SystemExit(0 if passed else 1)
