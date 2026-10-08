"""Read-only diagnostic of the unchanged separate-process isolation test."""
from pathlib import Path
import json, os, subprocess, sys, time, unittest
from unittest.mock import patch
BASE=Path(__file__).resolve().parent
REPO=BASE.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(REPO/'src'));sys.path.insert(0,str(REPO));sys.path.insert(0,str(BASE))
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.qualification import revision_fact,_sanitize
from s09_owner_worker_native_regression import OwnedProof,sha,stamp
from local_windows_qualification_awake import awake_request
REV='3c7c04c7fd9ebd06a626756c7313c4c17168a4ec'
OUTPUT=BASE/'S12-runtime-identity-isolation-diagnostic-3c7c04c'

def child():
    import tests.product.test_research_isolation as subject
    temporary=subject.TemporaryDirectory;spawn=subject.spawn_owned;wait=subject.wait_for
    handles=[];start=time.monotonic()
    def info(label,**values):print(json.dumps(dict(label=label,elapsed=round(time.monotonic()-start,3),**values)),flush=True)
    class CapturedTemporary:
        def __init__(self,*args,**kwargs):self.owned=temporary(*args,dir=OUTPUT/'temp',**kwargs)
        def __enter__(self):
            self.root=Path(self.owned.__enter__());info('ROOT_CREATED');return str(self.root)
        def __exit__(self,*args):
            for handle in handles:info('OWNED_FINAL',returncode=handle.process.poll(),report=vars(terminate_owned(handle,deadline_seconds=5)))
            for name in ('workers.log','heartbeat.json','paper-result.json','memory/fault-entered.json','memory/fault-result.json','timeout/fault-entered.json'):
                path=self.root/name
                if path.is_file():
                    raw=path.read_bytes();text=_sanitize(raw.decode('utf-8',errors='replace'),REPO).replace(str(self.root),'<FIXTURE_ROOT>').replace(str(BASE.parent),'<PROJECT_ROOT>').replace('\r\n','\n')
                    (OUTPUT/name.replace('/','-')).write_text(text,encoding='utf-8',newline='\n')
            return self.owned.__exit__(*args)
    def owned(*args,**kwargs):
        handle=spawn(*args,**kwargs);handles.append(handle);info('SPAWN',kind=args[0][-2],timeout=handle.limits.timeout_seconds);return handle
    def observed(*args,**kwargs):
        info('WAIT_BEGIN');value=wait(*args,**kwargs);info('WAIT_END',value=value if isinstance(value,(dict,str,int)) else repr(value));return value
    with patch.object(subject,'TemporaryDirectory',CapturedTemporary),patch.object(subject,'spawn_owned',owned),patch.object(subject,'wait_for',observed):
        suite=unittest.defaultTestLoader.loadTestsFromTestCase(subject.ResearchIsolationTests)
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

def main():
    revision_fact(REPO,REV,True);OUTPUT.mkdir();(OUTPUT/'temp').mkdir()
    environment=os.environ.copy();environment.update(PYTHONPATH=str(REPO/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(OUTPUT/'temp'),TMP=str(OUTPUT/'temp'))
    with OwnedProof(OUTPUT/'outer.log') as owner:
        handle=None
        try:
            with awake_request() as awake:
                handle=spawn_owned([sys.executable,str(Path(__file__)),'child'],cwd=REPO,limits=ResourceLimits(120),stdout=owner.stream,stderr=subprocess.STDOUT,env=environment)
                code=handle.wait()
        finally:
            reaped=terminate_owned(handle,deadline_seconds=5).reaped if handle else False
        owner.require_owned();owner.stream.seek(0);text=_sanitize(owner.stream.read().decode('utf-8',errors='replace'),REPO).replace(str(BASE.parent),'<PROJECT_ROOT>').replace('\r\n','\n')
        owner.stream.seek(0);owner.stream.write(text.encode());owner.stream.truncate();owner.stream.flush();owner.require_owned()
    after=revision_fact(REPO,REV,True)
    (OUTPUT/'disposition.json').write_text(json.dumps(dict(executable_revision=REV,source_after=after,exit_code=code,tree_reaped=reaped,awake_request=awake,scope='UNCHANGED_SINGLE_CASE_DIAGNOSTIC;NO_FULL_QUALIFICATION_CREDIT',provider_requests=0,credentials='NONE'),indent=2)+'\n',encoding='utf-8',newline='\n')
    print(text,flush=True);return code
if __name__=='__main__':raise SystemExit(child() if len(sys.argv)>1 else main())
