from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,sys
project=Path(__file__).resolve().parent.parent
root=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(root/'src'))
from application.qualification import run_qualification
revision=sys.argv[1];assert re.fullmatch('[0-9a-f]{40}',revision)
output=project/('artifacts/r7-productization-S12-position-qualified-'+revision[:7])
config=dict(suites=['all'],include_focused=True,require_clean=True,timeout_seconds=600,expected_revision=revision)
def stamp():return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
started=stamp();report=run_qualification(root,output,**config)
context=dict(started_at_utc=started,finished_at_utc=stamp(),configuration=config,
    config_hash='sha256:'+hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
    launcher_hash='sha256:'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    scope='S12 native position checkpoint: actual admitted E4 reads, original clocks/identity, actual E5 projection/FP12 reinterpretation, durable E6 position outbox/restart and initial-stop ambiguity fence. Continuous orchestration, protection observations, residual/exit/newer-flat/funding settlement and runtime/control projections remain IN_PROGRESS; real vault/provider/native/cloud/forward commissioning NOT_RUN')
(output/'qualification-context.json').write_text(json.dumps(context,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(passed=report['passed'],tests_run=report['tests_run'],commands=len(report['commands']))))
raise SystemExit(0 if report['passed'] else 1)
