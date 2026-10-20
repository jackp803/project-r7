"""One reviewed draft RED case, external to the frozen qualification inventory."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, os, re, subprocess, sys

BASE=Path(__file__).resolve().parent
PROJECT=BASE.parents[1]
ROOT=PROJECT/'workspaces/project-r7-productization-master-20261002'
REVISION='3ae6460c69a8a8f90588c396b819af7079e7546d'
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from application.qualification import revision_fact, _sanitize
from application.platform.processes import spawn_owned, terminate_owned, ResourceLimits
from application.platform.private_files import create_private_directory, write_private_new
from application.platform.resources import _memory, GIB
from strategy.v02.capabilities import _revision

def sha(raw):return 'sha256:'+hashlib.sha256(raw).hexdigest()
def utc():return datetime.now(timezone.utc).isoformat()

revision_fact(ROOT,REVISION,True)
implementation=_revision()
draft=BASE/'test_candidate_index_roundtrip_v02_v2.py.unapplied'
raw=draft.read_bytes()
if sha(raw)!='sha256:ccf5e361d8cc374e0d84bd59af86552f971d81e96f2cdd2f3d1a800e295aeb04':
    raise ValueError('Reviewed RED draft changed')
if _memory()[1]<6*GIB:raise ValueError('Conservative six GiB launch preflight')
output=BASE/'k03-missing-owner-red-v2-3ae6460-first'
create_private_directory(output)
write_private_new(output/'test_candidate_index_roundtrip_v02.py',raw)
report=dict(status='NOT_RUN',scope='DEVELOPMENT_RED_ONLY_NO_QUALIFICATION_CREDIT',
    executable_revision=REVISION,implementation_hash=implementation,started_at=utc(),
    draft_hash=sha(raw),helper_hash=sha(Path(__file__).read_bytes()),provider_requests=0,
    credentials='NONE',capital='NONE',github_compute='NOT_USED')
owned=None;cleanup=None;code=None
try:
    env=os.environ.copy()
    env.update(PYTHONPATH=os.pathsep.join((str(ROOT/'src'),str(ROOT))),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
    with (output/'execution.raw').open('xb') as stream:
        owned=spawn_owned([sys.executable,'-X','utf8','-m','unittest','discover','-v',
            '-s',str(output),'-p','test_candidate_index_roundtrip_v02.py'],cwd=ROOT,env=env,
            limits=ResourceLimits(900),stdout=stream,stderr=subprocess.STDOUT)
        code=owned.wait()
finally:
    if owned is not None:cleanup=terminate_owned(owned,deadline_seconds=10)
    safe=_sanitize((output/'execution.raw').read_text(encoding='utf-8'),ROOT).replace(str(PROJECT),'<PROJECT_ROOT>').replace('\r\n','\n')
    safe='\n'.join(line.rstrip() for line in safe.splitlines()).rstrip()+'\n'
    write_private_new(output/'execution.log',safe.encode())
    (output/'execution.raw').unlink()
    revision_fact(ROOT,REVISION,True)
    report.update(exit_code=code,tree_reaped=bool(cleanup and cleanup.reaped),
        source_unchanged=_revision()==implementation,finished_at=utc(),log_hash=sha(safe.encode()))
    report['expected_missing_seam_observed']=(code==1 and report['tree_reaped'] and report['source_unchanged']
        and "ModuleNotFoundError: No module named 'application.cloud.candidate_index'" in safe
        and 'Ran 1 test in ' in safe and 'FAILED (errors=1)' in safe)
    report['status']='EXPECTED_RED' if report['expected_missing_seam_observed'] else 'UNEXPECTED_RESULT'
    write_private_new(output/'checkpoint.json',(json.dumps(report,indent=2)+'\n').encode())
print(json.dumps(report),flush=True)
raise SystemExit(0 if report['expected_missing_seam_observed'] else 2)
