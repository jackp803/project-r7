from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
root=Path(__file__).resolve().parent.parent/'workspaces'/'project-r7-productization-master-20261002'
sys.path.insert(0,str(root/'src'))
from application.qualification import run_qualification
output=Path(__file__).resolve().parent/'r7-productization-S08-qualified-aa0e2e9'
config=dict(suites=['all'],include_focused=True,require_clean=True,timeout_seconds=600,
            expected_revision='aa0e2e9431374a6838359d04ef80bc7df5cb0d38')
def stamp(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
start=stamp(); report=run_qualification(root,output,**config)
context=dict(started_at_utc=start,finished_at_utc=stamp(),configuration=config,
    config_hash='sha256:'+hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
    launcher_hash='sha256:'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    scope='Overall qualification invocation; per-command UTC mapping remains S15')
(output/'qualification-context.json').write_text(json.dumps(context,indent=2)+'\n',encoding='utf-8',newline='\n')
raise SystemExit(0 if report['passed'] else 1)
