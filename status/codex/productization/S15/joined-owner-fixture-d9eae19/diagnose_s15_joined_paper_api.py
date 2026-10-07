"""Expose the actual ASGI exception in a single owned local fixture probe."""
from pathlib import Path
import sys
base=Path(__file__).resolve().parent;repo=base.parent/'workspaces/project-r7-productization-master-20261002'
sys.path[:0]=[str(repo/'src'),str(repo),str(base)]
if len(sys.argv)==2 and sys.argv[1]=='CHILD':
    import unittest
    from unittest.mock import patch
    from application.control_api.owner_services import OwnerControlServices
    import traceback
    from s15_joined_owner_acceptance_cases import JoinedOwnerAcceptanceTests
    original=OwnerControlServices.execute
    def expose(self,*args,**kwargs):
        try:return original(self,*args,**kwargs)
        except Exception:traceback.print_exc();raise
    with patch.object(OwnerControlServices,'execute',expose):
        result=unittest.TextTestRunner(verbosity=2).run(JoinedOwnerAcceptanceTests('test_joined_cloud_intake_research_paper_ready_api_and_exact_feedback_ack'))
    raise SystemExit(0 if result.wasSuccessful() else 1)
from application.platform.processes import ResourceLimits,spawn_owned
from application.qualification import _sanitize
from datetime import datetime,timezone
import hashlib,json,os
raw=base/'S15-joined-paper-api-owner-diagnostic.raw';log=raw.with_suffix('.log');report=raw.with_suffix('.json')
assert not any(os.path.lexists(path) for path in (raw,log,report))
scratch=base/'S15-joined-paper-api-owner-diagnostic-temp';scratch.mkdir(exist_ok=False)
before=datetime.now(timezone.utc).isoformat()
with raw.open('xb') as stream:
    owned=spawn_owned([sys.executable,str(Path(__file__).resolve()),'CHILD'],cwd=repo,
        env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(scratch),TMP=str(scratch)),limits=ResourceLimits(120),stdout=stream,stderr=stream)
    code=owned.wait(timeout=130)
log.write_text(_sanitize(raw.read_text(encoding='utf-8'),repo),encoding='utf-8',newline='\n');raw.unlink()
empty=not any(scratch.iterdir())
if empty:scratch.rmdir()
facts=dict(kind='DIAGNOSTIC_ONLY_NOT_ACCEPTANCE',exit_code=code,tree_reaped=owned.termination_report.reaped,fixture_scratch_empty=empty,
    started_at_utc=before,finished_at_utc=datetime.now(timezone.utc).isoformat(),real_provider_requests=0,credentials='NONE',capital='NONE',
    log_sha256='sha256:'+hashlib.sha256(log.read_bytes()).hexdigest())
report.write_text(json.dumps(facts,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(facts))
