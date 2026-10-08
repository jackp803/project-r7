"""Bounded local fixture regression; no full qualification credit."""
from pathlib import Path
import json,os,re,subprocess,sys
BASE=Path(__file__).resolve().parent;REPO=BASE.parent/'workspaces/project-r7-productization-master-20261002'
sys.path.insert(0,str(BASE));sys.path.insert(0,str(REPO/'src'))
from s09_owner_worker_native_regression import OwnedProof,sha,stamp
from application.platform.processes import spawn_owned,terminate_owned,ResourceLimits
from application.qualification import _sanitize
from local_windows_qualification_awake import awake_request
from s09_owner_worker_source_qualify import inputs

def main():
    label=sys.argv[1];assert label in ('RED','GREEN','INTEGRATION')
    prefix=BASE/f'S12-runtime-identity-isolation-{label}'
    names=['tests.product.test_paper_worker_fixture_publish']
    if label=='INTEGRATION':names.append('tests.product.test_research_isolation')
    selected=[REPO/'tests/product/test_paper_worker_fixture_publish.py',REPO/'tests/product/paper_worker_fixture.py',REPO/'tests/product/test_research_isolation.py']
    captured={path.relative_to(REPO).as_posix():sha(path.read_bytes()) for path in selected}
    temp=BASE/f'S12-runtime-identity-isolation-{label}-temp';temp.mkdir()
    environment=os.environ.copy();environment.update(PYTHONPATH=str(REPO/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(temp),TMP=str(temp))
    started=stamp();handle=None
    with OwnedProof(prefix.with_suffix('.log')) as owner:
        try:
            with awake_request() as awake:
                handle=spawn_owned([sys.executable,'-m','unittest',*names,'-v'],cwd=REPO,limits=ResourceLimits(180),stdout=owner.stream,stderr=subprocess.STDOUT,env=environment)
                code=handle.wait()
        finally:
            reaped=terminate_owned(handle,deadline_seconds=5).reaped if handle else False
        owner.require_owned();owner.stream.seek(0);text=_sanitize(owner.stream.read().decode('utf-8',errors='replace'),REPO).replace(str(BASE.parent),'<PROJECT_ROOT>').replace('\r\n','\n')
        owner.stream.seek(0);owner.stream.write(text.encode());owner.stream.truncate();owner.stream.flush();owner.require_owned()
    unchanged=captured=={path.relative_to(REPO).as_posix():sha(path.read_bytes()) for path in selected}
    value=dict(label=label,started_at_utc=started,finished_at_utc=stamp(),source_revision='3c7c04c7fd9ebd06a626756c7313c4c17168a4ec',worktree='DIRTY_REGRESSION_TEST_FIRST',source_inputs=captured,inputs_unchanged=unchanged,exit_code=code,tree_reaped=reaped,awake_request=awake,log_sha256=sha(prefix.with_suffix('.log').read_bytes()),scope='ACTUAL_BOUNDED_FIXTURE_REGRESSION_ONLY;NO_FULL_QUALIFICATION_CREDIT',provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
    with OwnedProof(prefix.with_suffix('.json')) as owner:owner.persist(value)
    print(text,flush=True);return code
if __name__=='__main__':raise SystemExit(main())
