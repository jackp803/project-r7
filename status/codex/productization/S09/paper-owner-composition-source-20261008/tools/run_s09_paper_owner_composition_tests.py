"""Owned local factory-component tests with complete current public input binding."""
from pathlib import Path
import os,re,subprocess,sys,json
BASE=Path(__file__).resolve().parent;REPO=BASE.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(BASE));sys.path.insert(0,str(REPO/'src'))
from s09_owner_worker_native_regression import OwnedProof,sha,stamp
from s09_owner_worker_source_qualify import inputs
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.platform.supervision import _local_path
from application.qualification import _sanitize,parse_result
from strategy.v02.capabilities import _revision
from local_windows_qualification_awake import awake_request

def capture():
    values=inputs()
    for name in ['src/application/paper/owners.py','tests/application/test_paper_owner_composition.py','docs/product/v0_2/PAPER_OWNER_COMPOSITION_PLAN.md']:
        path=REPO/name;_local_path(path);values[name]=sha(path.read_bytes()) if path.exists() else 'MISSING'
    return values

def main():
    label=sys.argv[1];assert re.fullmatch('[A-Z_]{1,32}',label)
    modules=['tests.application.test_paper_owner_composition']
    if label=='REGRESSION':modules+=['tests.application.test_paper_owner_worker','tests.application.test_local_paper_control_composition','tests.application.test_local_owner_composition','tests.application.test_runtime_process_supervision']
    before=capture();implementation=_revision();temporary=BASE/f'S09-paper-owner-composition-{label}-temp';_local_path(temporary);temporary.mkdir()
    environment=os.environ.copy();environment.update(PYTHONPATH=str(REPO/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(temporary),TMP=str(temporary))
    prefix=BASE/f'S09-paper-owner-composition-{label}';handle=None;started=stamp()
    with OwnedProof(prefix.with_suffix('.log')) as owner:
        try:
            with awake_request() as awake:
                handle=spawn_owned([sys.executable,'-m','unittest',*modules,'-v'],cwd=REPO,limits=ResourceLimits(600),stdout=owner.stream,stderr=subprocess.STDOUT,env=environment);code=handle.wait()
        finally:
            reaped=handle is not None and terminate_owned(handle,deadline_seconds=5).reaped
        owner.require_owned();owner.stream.seek(0);raw=owner.stream.read(8*1024**2+1);assert len(raw)<=8*1024**2
        text=_sanitize(raw.decode('utf-8',errors='replace'),REPO).replace(str(BASE.parent),'<PROJECT_ROOT>').replace('\r\n','\n')
        owner.stream.seek(0);owner.stream.write(text.encode());owner.stream.truncate();owner.stream.flush();owner.require_owned()
    result=parse_result(text,returncode=code);unchanged=before==capture() and implementation==_revision()
    value=dict(label=label,started_at_utc=started,finished_at_utc=stamp(),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),worktree='DIRTY_IMPLEMENTATION_TESTING',implementation_hash=implementation,source_input_hashes=before,inputs_unchanged=unchanged,modules=modules,tests_run=result.tests_run,failures=result.failures,errors=result.errors,skipped=result.skipped,exit_code=code,tree_reaped=reaped,awake_request=awake,log_sha256=sha(prefix.with_suffix('.log').read_bytes()),scope='ACTUAL_SOURCE_OWNER_COMPONENT_AND_ISOLATED_FIXTURE_MECHANICS;NO_NATIVE_OR_RELEASE_QUALIFICATION_CREDIT',ordinary_native_paper='NOT_RUN',production_profile='PROPOSED_NOT_ACTIVE',provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
    with OwnedProof(prefix.with_suffix('.json')) as owner:owner.persist(value)
    assert unchanged and reaped and awake['restored'] is True
    print(text,flush=True);return code
if __name__=='__main__':raise SystemExit(main())
