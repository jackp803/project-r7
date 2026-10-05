from pathlib import Path
import os, sys, json, time, pstats
project = Path(__file__).resolve().parent.parent
root = project / 'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0, str(root/'src'))
from application.platform.processes import spawn_owned, ResourceLimits
out = project/'artifacts/S13-timeout-profile-f2e9703'
out.mkdir(exist_ok=False)
env = dict(os.environ, PYTHONPATH=str(root/'src'), PYTHONUTF8='1')
name = 'tests.product.test_trading_protection_monitor_v02.TradingProtectionMonitorV02Tests.test_local_stop_after_1000_claims_remains_unknown_without_cleanup'
started = time.monotonic()
with (out/'test.log').open('wb') as stream:
    handle = spawn_owned([sys.executable,'-m','cProfile','-o',str(out/'profile.bin'),'-m','unittest',name,'-v'], cwd=root, env=env, stdout=stream, stderr=stream, limits=ResourceLimits(180))
    code = handle.wait(timeout=190)
facts = dict(returncode=code,duration_seconds=time.monotonic()-started,tree_reaped=handle.termination_report.reaped)
(out/'result.json').write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8')
print(json.dumps(facts))
if (out/'profile.bin').exists():
    with (out/'profile.txt').open('w',encoding='utf-8') as stream:
        pstats.Stats(str(out/'profile.bin'),stream=stream).sort_stats('cumulative').print_stats(45)
print((out/'test.log').read_text(encoding='utf-8',errors='replace'))
