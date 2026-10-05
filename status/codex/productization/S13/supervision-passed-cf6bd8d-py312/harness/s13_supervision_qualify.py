from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, sys
project = Path(__file__).resolve().parent.parent
root = project / 'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0, str(root / 'src'))
from application.qualification import run_qualification
revision = sys.argv[1]
assert re.fullmatch('[0-9a-f]{40}', revision)
output = project / ('artifacts/r7-productization-S13-supervision-qualified-' + revision[:7])
configuration = dict(suites=['all'], include_focused=True, require_clean=True, timeout_seconds=900, expected_revision=revision)
def stamp(): return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
started = stamp()
try:
    report = run_qualification(root, output, **configuration)
except BaseException as error:
    output.mkdir(parents=True, exist_ok=True)
    (output/'qualification-launcher-failure.json').write_text(json.dumps(dict(
        started_at_utc=started,finished_at_utc=stamp(),exception_class=type(error).__name__,
        executable_revision=revision,passed=False,configuration=configuration),indent=2)+'\n',encoding='utf-8')
    raise
context = dict(started_at_utc=started, finished_at_utc=stamp(), configuration=configuration,
    config_hash='sha256:' + hashlib.sha256(json.dumps(configuration, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
    launcher_hash='sha256:' + hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    spec_revision='9fd277798b1c51d1bc79b29a61bec81b552efeb1', task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',
    scope='S13 source local owner/research worker and process supervision checkpoint. Actual host process exclusion, durable current process/config generations, heartbeat, control restart/config failure, owned research cancellation/reaping and all existing LF/FP regression. Native builds/smokes are separately retained. S12 continuous runtime and S13 service/SSH/backup/selected native research remain IN_PROGRESS; missing Ubuntu/cloud/real forward/private provider commissioning NOT_RUN.')
(output / 'qualification-context.json').write_text(json.dumps(context, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps(dict(passed=report['passed'], tests_run=report['tests_run'], commands=len(report['commands']))))
raise SystemExit(0 if report['passed'] else 1)
