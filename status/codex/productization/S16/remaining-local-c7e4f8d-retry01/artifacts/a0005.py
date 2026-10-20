"""Exact-clean affected source regressions; no native qualification credit."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,subprocess,sys
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from application.qualification import revision_fact,_sanitize
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.platform.private_files import create_private_directory,write_private_new

revision,label=sys.argv[1:]
if not re.fullmatch('[0-9a-f]{40}',revision) or label not in ('red','green'):
    raise ValueError('Explicit source revision and result attempt required')
revision_fact(ROOT,revision,True)
output=BASE/('remaining-local-'+revision[:7]+'-'+label);create_private_directory(output)
modules=('tests.indicators.test_v02_golden','tests.position.test_v02_exit_requests',
    'tests.strategy.test_v02_capabilities','tests.strategy.test_v02_multitimeframe',
    'tests.application.test_dataset_binding','tests.validation.test_walk_forward',
    'tests.application.test_research_e6_recovery','tests.application.test_research_robustness',
    'tests.application.test_product_assessment_binding','tests.product.test_research_queue',
    'tests.product.test_api_owner_services','tests.application.test_authoring_roundtrip',
    'tests.application.test_claim_recovery','tests.product.test_trading_dispatch_v02')
report=dict(revision=revision,scope='AFFECTED_SOURCE_REGRESSIONS_ONLY',qualification_credit='NONE',
    started_at=datetime.now(timezone.utc).isoformat(),modules=list(modules),
    helper_hash='sha256:'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    additional_public_requests=0,private_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
owned=None;cleanup=None;code=None
try:
    with (output/'source.raw').open('xb') as stream:
        owned=spawn_owned([sys.executable,'-X','utf8','-m','unittest','-v',*modules],cwd=ROOT,
            limits=ResourceLimits(1800),stdout=stream,stderr=subprocess.STDOUT)
        code=owned.wait()
finally:
    if owned is not None:cleanup=terminate_owned(owned,deadline_seconds=5)
raw=(output/'source.raw').read_bytes()
safe=_sanitize(raw.decode('utf-8',errors='replace'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n').encode()
write_private_new(output/'source.log',safe);(output/'source.raw').unlink()
revision_fact(ROOT,revision,True)
counts=re.findall(r'^Ran (\d+) tests? in ',safe.decode(),re.M)
report.update(exit_code=code,tree_reaped=bool(cleanup and cleanup.reaped),source_unchanged=True,
    passed=code==0 and bool(cleanup and cleanup.reaped),tests_run=int(counts[-1]) if counts else None,
    log_ref='source.log',log_hash='sha256:'+hashlib.sha256(safe).hexdigest(),finished_at=datetime.now(timezone.utc).isoformat())
write_private_new(output/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
print(json.dumps(report),flush=True)
raise SystemExit(0 if report['passed'] else 1)
