"""Bounded owned source regression only; not native/full qualification."""
import json,os,re,sys
from pathlib import Path
from s09_normal_fixture_source_qualify import BASE,REPO,inputs
from s09_owner_worker_native_regression import OwnedProof,sha,stamp
from s09_local_paper_control_native_regression import read_input
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from local_windows_qualification_awake import awake_request
label,*modules=sys.argv[1:]
assert re.fullmatch('[A-Z0-9_]+',label) and modules
assert all(re.fullmatch(r'tests\.(application|product)\.[A-Za-z0-9_]+',m) for m in modules)
folder=BASE/('S16-validity-research-'+label);assert not os.path.lexists(folder);folder.mkdir()
before=inputs();helper=sha(read_input(Path(__file__),65536));exe=sha(read_input(Path(sys.executable),128*1024**2))
environment={k:os.environ[k] for k in ('SystemRoot','WINDIR','SystemDrive','TEMP','TMP') if k in os.environ}
environment.update(PATH='',PYTHONPATH=str(REPO/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1')
owned=None;started=stamp()
with OwnedProof(folder/'tests.log') as log:
    with awake_request() as awake:
        try:
            owned=spawn_owned([sys.executable,'-X','utf8','-m','unittest','-v',*modules],cwd=REPO,env=environment,
                limits=ResourceLimits(600),stdout=log.stream,stderr=log.stream)
            code=owned.wait()
        finally:
            assert owned is not None and terminate_owned(owned,deadline_seconds=5).reaped
    log.stream.flush();log.require_owned()
assert awake['restored'] and inputs()==before
assert sha(read_input(Path(__file__),65536))==helper and sha(read_input(Path(sys.executable),128*1024**2))==exe
raw=read_input(folder/'tests.log',8*1024**2);text=raw.decode('utf-8');count=re.search(r'Ran (\d+) tests? in',text)
assert count is not None
def number(name):
    found=re.search(name+r'=(\d+)',text)
    return int(found[1]) if found else 0
with OwnedProof(folder/'result.json') as proof:
    proof.persist(dict(scope='FOCUSED_OWNED_SOURCE_ONLY;NO_NATIVE_OR_FULL_MASTER_CREDIT',label=label,modules=modules,
        exit_code=code,tests=int(count[1]),failures=number('failures'),errors=number('errors'),skipped=number('skipped'),
        tree_reaped=True,awake_request=awake,source_input_hashes=before,inputs_unchanged=True,helper_sha256=helper,
        interpreter_sha256=exe,log_sha256=sha(raw),started_at_utc=started,finished_at_utc=stamp(),provider_requests=0,credentials='NONE',capital='NONE'))
print(json.dumps(dict(label=label,exit_code=code,tests=int(count[1]),failures=number('failures'),errors=number('errors'),skipped=number('skipped'))))
raise SystemExit(code)
