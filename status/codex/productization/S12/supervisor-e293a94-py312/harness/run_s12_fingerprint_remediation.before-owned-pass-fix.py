"""Fresh owned source-identity safety regression, never a full-product PASS."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, sys

base=Path(__file__).resolve().parent
repo=base.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.qualification import _sanitize, parse_result, revision_fact
from application.platform.processes import ResourceLimits,spawn_owned
from strategy.v02.capabilities import _revision

mode=sys.argv[1]
assert mode in ('baseline-safety','baseline-inaccessible-RED','remediation-safety','remediation-product-case')
stem='S12-runtime-supervision-fingerprint-'+mode
assert not (base/(stem+'.json')).exists()
inputs=[Path(__file__),repo/'src/strategy/v02/capabilities.py',repo/'tests/strategy/test_v02_capabilities.py',
        repo/'tests/strategy/test_source_resource_commitment.py',repo/'tests/application/test_native_distribution.py',
        repo/'tests/product/test_trading_protection_monitor_v02.py']
bind=lambda:{p.relative_to(base.parent).as_posix():'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
before=bind();source_before=revision_fact(repo,None,False);implementation_before=_revision()
tests=['tests.strategy.test_v02_capabilities','tests.strategy.test_source_resource_commitment',
       'tests.application.test_native_distribution']
if mode=='remediation-product-case':
    tests=['tests.product.test_trading_protection_monitor_v02.TradingProtectionMonitorV02Tests.test_verified_exact_single_owned_stop_projects_actual_e5_protected_and_fp12']
environment=os.environ.copy();environment.update(PYTHONPATH=str(repo/'src'),PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
stamp=lambda:datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
started=stamp();raw=base/(stem+'.owned.raw')
with raw.open('xb') as stream:
    handle=spawn_owned([sys.executable,'-m','unittest',*tests,'-v'],cwd=repo,env=environment,
                       limits=ResourceLimits(120),stdout=stream,stderr=stream)
    code=handle.wait(timeout=130)
log=_sanitize(raw.read_text(encoding='utf-8',errors='replace'),repo);raw.unlink()
logpath=base/(stem+'.log');logpath.write_text(log,encoding='utf-8',newline='\n')
result=parse_result(log,returncode=code)
after=bind();source_after=revision_fact(repo,None,False);implementation_after=_revision()
facts=dict(scope='BOUNDED_SOURCE_IDENTITY_REGRESSION;NOT_FULL_QUALIFICATION',mode=mode,command_tests=tests,
           started_at_utc=started,finished_at_utc=stamp(),**result.__dict__,exit_code=code,
           tree_reaped=handle.termination_report.reaped,harness_binding='BEFORE_AND_AFTER_EXECUTION',
           input_sha256_before=before,input_sha256_after=after,source_before=source_before,source_after=source_after,
           implementation_hash_before=implementation_before,implementation_hash_after=implementation_after,
           log=logpath.name,log_sha256='sha256:'+hashlib.sha256(logpath.read_bytes()).hexdigest(),
           provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
assert before==after and source_before==source_after and implementation_before==implementation_after
(base/(stem+'.json')).write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps({k:v for k,v in facts.items() if k not in ('input_sha256_before','input_sha256_after')}))
raise SystemExit(0 if result.passed and handle.termination_report.reaped else 1)
