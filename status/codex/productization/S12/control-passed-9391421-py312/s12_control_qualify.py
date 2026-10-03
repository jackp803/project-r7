from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, sys
project = Path(__file__).resolve().parent.parent
root = project / 'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0, str(root / 'src'))
from application.qualification import run_qualification
revision = sys.argv[1]
assert re.fullmatch('[0-9a-f]{40}', revision)
output = project / ('artifacts/r7-productization-S12-control-qualified-' + revision[:7])
config = dict(suites=['all'], include_focused=True, require_clean=True, timeout_seconds=600, expected_revision=revision)
def stamp():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
started = stamp()
report = run_qualification(root, output, **config)
context = dict(started_at_utc=started, finished_at_utc=stamp(), configuration=config,
    config_hash='sha256:' + hashlib.sha256(json.dumps(config, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
    launcher_hash='sha256:' + hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    scope='S12 control checkpoint: exact E6 financial proposal views, authenticated stop-new-entry/replay and current E6/E7/E5/E4 dispatch expiry fences; continuous orchestration, residual/newer-flat settlement and trading/protection projections remain IN_PROGRESS; real vault/provider/native/cloud/forward commissioning NOT_RUN')
(output / 'qualification-context.json').write_text(json.dumps(context, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps(dict(passed=report['passed'], tests_run=report['tests_run'], commands=len(report['commands']))))
raise SystemExit(0 if report['passed'] else 1)
