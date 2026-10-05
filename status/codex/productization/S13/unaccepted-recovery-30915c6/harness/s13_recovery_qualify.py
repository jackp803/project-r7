from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,sys,threading
project=Path(__file__).resolve().parent.parent
repo=project/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(repo/'src'))
from application.qualification import run_qualification
revision=sys.argv[1];assert re.fullmatch('[0-9a-f]{40}',revision)
suffix=sys.argv[2] if len(sys.argv)>2 else ''
assert suffix in ('','-retry-1')
output=project/f'artifacts/r7-productization-S13-recovery-qualified-{revision[:7]}{suffix}'
configuration=dict(suites=['all'],include_focused=True,require_clean=True,timeout_seconds=900,expected_revision=revision)
stamp=lambda:datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
started=stamp()
from application.platform.resources import _memory
measurements=[];stop=threading.Event()
def monitor():
    while not stop.is_set():
        total,available=_memory()
        measurements.append(dict(observed_at_utc=stamp(),physical_memory_bytes=total,available_memory_bytes=available,
                                 existing_admission_minimum_bytes=max(2*1024**3,total*15//100)))
        stop.wait(2)
thread=threading.Thread(target=monitor,daemon=True);thread.start()
try:report=run_qualification(repo,output,**configuration)
finally:
    stop.set();thread.join(5)
    if output.exists():
        (output/'hardware-observations.json').write_text(json.dumps(dict(scope='Actual host memory samples only; no admission threshold/fixture/production changes',samples=measurements),indent=2)+'\n',encoding='utf-8',newline='\n')
context=dict(started_at_utc=started,finished_at_utc=stamp(),configuration=configuration,
    config_hash='sha256:'+hashlib.sha256(json.dumps(configuration,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
    launcher_hash='sha256:'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),spec_revision='9fd277798b1c51d1bc79b29a61bec81b552efeb1',
    task_id='CODEX-R7-PRODUCTIZATION-MASTER-20261002',scope='S13 private full product-data backup/fresh restore and application/auth/E6 process fencing, durable restoration/startup restriction, exact admission-time numeric diagnostics, failure-fixture cleanup, retained S14 offline cloud/authoring/feedback fixes and full LF/FP regression. Native/browser acceptance is separate. Real rclone/cloud/Ubuntu/forward/provider NOT_RUN; S12/S13 service/SSH/S14 forward/S15/S16 pending.')
(output/'qualification-context.json').write_text(json.dumps(context,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(passed=report['passed'],tests_run=report['tests_run'],commands=len(report['commands']))))
raise SystemExit(0 if report['passed'] else 1)
