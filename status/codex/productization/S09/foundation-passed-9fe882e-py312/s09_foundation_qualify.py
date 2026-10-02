from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, sys
root = Path(__file__).resolve().parent.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0, str(root/'src'))
from application.qualification import run_qualification
output = Path(__file__).resolve().parent/'r7-productization-S09-foundation-qualified-9fe882e'
config = dict(suites=['all'], include_focused=True, require_clean=True, timeout_seconds=600,
              expected_revision='9fe882e20eed791891cac0d279ea4cb664aba767')
def stamp(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
start = stamp()
report = run_qualification(root, output, **config)
context = dict(started_at_utc=start, finished_at_utc=stamp(), configuration=config,
    config_hash='sha256:'+hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
    launcher_hash='sha256:'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    scope='S09 durability foundation only; continuous cycle/scheduler/forward assessment remain IN_PROGRESS')
(output/'qualification-context.json').write_text(json.dumps(context,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(passed=report['passed'],tests_run=report['tests_run'],commands=len(report['commands']))))
raise SystemExit(0 if report['passed'] else 1)
