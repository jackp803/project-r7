"""Owned public research setup integration tests with complete current public input binding."""
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

def execution_inputs(paths=None):
    if paths is None:
        paths=[Path(__file__),BASE/'s09_owner_worker_native_regression.py',BASE/'s09_owner_worker_source_qualify.py',BASE/'local_windows_qualification_awake.py',BASE/'test_s09_public_setup_runner_bindings.py']
    result={}
    for path in paths:
        _local_path(path)
        result['external/'+path.name]=sha(path.read_bytes())
    return result

def capture():
    values=inputs()
    for name in ['src/application/research/setup.py','tests/application/test_research_setup_flow.py']:
        path=REPO/name;_local_path(path);values[name]=sha(path.read_bytes()) if path.exists() else 'MISSING'
    values.update(execution_inputs())
    return values

def main():
    label=sys.argv[1];assert re.fullmatch('[A-Z_]{1,32}',label)
    modules=['tests.application.test_research_setup_flow']
    if label=='REGRESSION':modules+=['tests.application.test_native_entrypoints','tests.application.test_local_owner_composition','tests.application.test_native_research_worker','tests.application.test_control_process_supervision','tests.product.test_api_owner_services']
    if label.startswith('PRECOMMIT'):
        modules=['tests.application.test_research_setup_flow.ResearchSetupFlowTests.'+name for name in ['test_first_run_cloud_root_is_explicit_disjoint_and_never_connected','test_overlapping_cloud_root_never_publishes_profile_or_initializes_database','test_explicit_setup_is_immutable_idempotent_and_creates_no_owner_database','test_cloud_borne_selection_unknown_authority_and_missing_local_inputs_are_rejected','test_each_running_owner_fences_configuration_without_changing_selection','test_config_inside_or_equal_to_cloud_root_is_rejected_before_any_write','test_outside_profile_hardlinked_to_cloud_input_is_rejected_without_publication','test_canonical_cloud_alias_is_rejected_before_opening_profile_bytes']]
        modules+=['tests.application.test_native_entrypoints','tests.application.test_local_owner_composition','tests.application.test_native_research_worker','tests.application.test_control_process_supervision','tests.application.test_product_data_backup','tests.product.test_api_owner_services']
    if label.startswith('CANONICAL'):
        modules=['tests.application.test_research_setup_flow.ResearchSetupFlowTests.test_canonical_cloud_alias_is_rejected_before_opening_profile_bytes']
    before=capture();implementation=_revision();temporary=BASE/f'S09-public-research-setup-{label}-temp';_local_path(temporary);temporary.mkdir()
    environment=os.environ.copy();environment.update(PYTHONPATH=str(REPO/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(temporary),TMP=str(temporary))
    prefix=BASE/f'S09-public-research-setup-{label}';handle=None;started=stamp()
    with OwnedProof(prefix.with_suffix('.log')) as owner:
        try:
            with awake_request() as awake:
                command=[sys.executable,str(BASE/'test_s09_public_setup_runner_bindings.py')] if label.startswith('PROOF') else [sys.executable,'-m','unittest',*modules,'-v']
                handle=spawn_owned(command,cwd=REPO,limits=ResourceLimits(600),stdout=owner.stream,stderr=subprocess.STDOUT,env=environment);code=handle.wait()
        finally:
            reaped=handle is not None and terminate_owned(handle,deadline_seconds=5).reaped
        owner.require_owned();owner.stream.seek(0);raw=owner.stream.read(8*1024**2+1);assert len(raw)<=8*1024**2
        text=_sanitize(raw.decode('utf-8',errors='replace'),REPO).replace(str(BASE.parent),'<PROJECT_ROOT>').replace('\r\n','\n')
        owner.stream.seek(0);owner.stream.write(text.encode());owner.stream.truncate();owner.stream.flush();owner.require_owned()
    result=parse_result(text,returncode=code);unchanged=before==capture() and implementation==_revision()
    value=dict(label=label,started_at_utc=started,finished_at_utc=stamp(),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),worktree='CLEAN' if not subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip() else 'DIRTY_IMPLEMENTATION_TESTING',implementation_hash=implementation,source_input_hashes={key:val for key,val in before.items() if not key.startswith('external/')},execution_input_hashes={key:val for key,val in before.items() if key.startswith('external/')},inputs_unchanged=unchanged,modules=modules,tests_run=result.tests_run,failures=result.failures,errors=result.errors,skipped=result.skipped,exit_code=code,tree_reaped=reaped,awake_request=awake,log_sha256=sha(prefix.with_suffix('.log').read_bytes()),scope='EXTERNAL_EXECUTION_BINDING_GUARDS_ONLY;NO_PRODUCT_TEST_CREDIT' if label.startswith('PROOF') else 'PUBLIC_NORMAL_SOURCE_SETUP_AUTH_INTAKE_RESEARCH_WITH_NEW_SYNTHETIC_INPUTS;NO_NATIVE_REAL_CLOUD_OR_PAPER_ACCEPTANCE',ordinary_native_paper='NOT_RUN',production_profile='PROPOSED_NOT_ACTIVE',provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
    with OwnedProof(prefix.with_suffix('.json')) as owner:owner.persist(value)
    assert unchanged and reaped and awake['restored'] is True
    print(text,flush=True);return code
if __name__=='__main__':raise SystemExit(main())
