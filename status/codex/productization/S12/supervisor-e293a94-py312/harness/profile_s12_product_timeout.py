"""Owned, exact-source diagnosis of one unchanged product regression."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, io, json, os, pstats, sys

base = Path(__file__).resolve().parent
repo = base.parent / 'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0, str(repo / 'src'))
from application.qualification import _sanitize, parse_result, revision_fact
from application.platform.processes import spawn_owned, ResourceLimits

revision = '4ea0f61c62984eaca1cbfae8b745cffb9cdec901'
stem = 'S12-runtime-supervision-product-timeout-profile'
target = base / (stem + '.json')
assert not target.exists()
before = revision_fact(repo, revision, True)
environment = os.environ.copy()
environment.update(PYTHONPATH=str(repo / 'src'), PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
profile = base / (stem + '.pstats')
raw = base / (stem + '.owned.raw')
case = ('tests.product.test_trading_protection_monitor_v02.TradingProtectionMonitorV02Tests.'
        'test_verified_exact_single_owned_stop_projects_actual_e5_protected_and_fp12')
stamp = lambda: datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
started = stamp()
with raw.open('xb') as stream:
    handle = spawn_owned([sys.executable, '-m', 'cProfile', '-o', str(profile), '-m', 'unittest', case, '-v'],
                         cwd=repo, env=environment, limits=ResourceLimits(120), stdout=stream, stderr=stream)
    code = handle.wait(timeout=130)
log = _sanitize(raw.read_text(encoding='utf-8', errors='replace'), repo)
raw.unlink()
logpath = base / (stem + '.log')
logpath.write_text(log, encoding='utf-8', newline='\n')
facts = dict(source_before=before, source_after=revision_fact(repo, revision, True),
             started_at_utc=started, finished_at_utc=stamp(), exit_code=code,
             tree_reaped=handle.termination_report.reaped,
             result=parse_result(log, returncode=code).__dict__,
             log=logpath.name, log_sha256='sha256:' + hashlib.sha256(logpath.read_bytes()).hexdigest(),
             scope='DIAGNOSTIC_ONE_UNCHANGED_TEST;NOT_FULL_QUALIFICATION', provider_requests=0,
             credentials='NONE', capital='NONE', github_compute='NOT_USED')
if profile.exists():
    output = io.StringIO()
    pstats.Stats(str(profile), stream=output).sort_stats('cumulative').print_stats(35)
    public = _sanitize(output.getvalue(), repo)
    (base / (stem + '-stats.log')).write_text(public, encoding='utf-8', newline='\n')
    facts['profile_sha256'] = 'sha256:' + hashlib.sha256(profile.read_bytes()).hexdigest()
target.write_text(json.dumps(facts, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps(facts))
