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
        paths=[Path(__file__),BASE/'s09_owner_worker_native_regression.py',BASE/'s09_owner_worker_source_qualify.py',BASE/'local_windows_qualification_awake.py',BASE/'test_s09_public_setup_runner_bindings.py',BASE/'diagnose_s09_fixture_paper_start.py',BASE/'diagnose_s09_fixture_worker.py',BASE/'diagnose_s09_fixture_restore.py']
    result={}
    for path in paths:
        _local_path(path)
        result['external/'+path.name]=sha(path.read_bytes())
    return result

def capture():
    values=inputs()
    for name in ['src/application/research/setup.py','tests/application/test_research_setup_flow.py','tests/application/test_fixture_product_mode.py','tests/application/test_fixture_recipe_flow.py','src/application/fixtures/recipe.py','src/application/fixtures/__init__.py','tests/application/test_normal_fixture_paper.py','src/application/paper/setup.py']:
        path=REPO/name;_local_path(path);values[name]=sha(path.read_bytes()) if path.exists() else 'MISSING'
    values.update(execution_inputs())
    return values

def retain_execution_inputs(commitments):
    from application.datasets.catalog import read_local
    identifier=sha(json.dumps(commitments,sort_keys=True,separators=(',',':')).encode('utf-8'))[7:]
    folder=BASE/'normal-fixture-execution-inputs'/identifier
    _local_path(folder);folder.mkdir(parents=True,exist_ok=True)
    for name,expected in commitments.items():
        filename=name.removeprefix('external/')
        raw=read_local(BASE,filename,1024**2)
        assert sha(raw)==expected
        destination=folder/filename
        if destination.exists():
            assert sha(read_local(folder,filename,1024**2))==expected
        else:
            with OwnedProof(destination) as owner:
                owner.stream.write(raw);owner.stream.flush();owner.require_owned()
    return folder.relative_to(BASE).as_posix()

def main():
    label=sys.argv[1];assert re.fullmatch('[A-Z_]{1,32}',label)
    modules=['tests.application.test_fixture_recipe_flow'] if label.startswith('RECIPE') else ['tests.application.test_fixture_product_mode']
    if label.startswith('REGRESSION'):modules+=['tests.application.test_fixture_recipe_flow','tests.application.test_research_setup_flow']
    if label.startswith('REGRESSION'):modules+=['tests.application.test_native_entrypoints','tests.application.test_local_owner_composition','tests.application.test_native_research_worker','tests.application.test_control_process_supervision','tests.product.test_api_owner_services','tests.application.test_database_backup','tests.application.test_database_restore','tests.application.test_product_data_backup','tests.application.test_process_supervision','tests.application.test_runtime_process_supervision']
    if label.startswith('PRECOMMIT'):
        modules=['tests.application.test_research_setup_flow.ResearchSetupFlowTests.'+name for name in ['test_first_run_cloud_root_is_explicit_disjoint_and_never_connected','test_overlapping_cloud_root_never_publishes_profile_or_initializes_database','test_explicit_setup_is_immutable_idempotent_and_creates_no_owner_database','test_cloud_borne_selection_unknown_authority_and_missing_local_inputs_are_rejected','test_each_running_owner_fences_configuration_without_changing_selection','test_config_inside_or_equal_to_cloud_root_is_rejected_before_any_write','test_outside_profile_hardlinked_to_cloud_input_is_rejected_without_publication','test_canonical_cloud_alias_is_rejected_before_opening_profile_bytes']]
        modules+=['tests.application.test_native_entrypoints','tests.application.test_local_owner_composition','tests.application.test_native_research_worker','tests.application.test_control_process_supervision','tests.application.test_product_data_backup','tests.product.test_api_owner_services','tests.application.test_database_backup','tests.application.test_database_restore','tests.application.test_product_data_backup','tests.application.test_process_supervision','tests.application.test_runtime_process_supervision']
    if label.startswith('CANONICAL'):
        modules=['tests.application.test_research_setup_flow.ResearchSetupFlowTests.test_canonical_cloud_alias_is_rejected_before_opening_profile_bytes']
    if label.startswith('RECIPE_INSTALL'):modules=['tests.application.test_fixture_recipe_flow.FixtureRecipeFlowTests.'+name for name in ('test_frozen_installation_cannot_be_used_as_data','test_frozen_installation_cannot_be_used_as_fake_staging')]
    if label.startswith('LEGACY'):modules=['tests.application.test_fixture_product_mode.DefaultAndUnsupportedModeTests.'+name for name in ('test_default_mode_preserves_legacy_commitment_and_fixture_mode_is_distinct','test_actual_legacy_backup_verifies_and_restores_with_unchanged_inhibition','test_actual_legacy_restoration_marker_still_requires_reconciliation')]
    if label.startswith('PAPER'):modules=['tests.application.test_normal_fixture_paper','tests.application.test_paper_owner_composition.PaperOwnerCompositionTests.test_subject_bound_start_port_rejects_another_actual_same_risk_candidate']
    if label.startswith('PAPER_PRECOMMIT'):modules=['tests.application.test_normal_fixture_paper.NormalFixturePaperTests.'+name for name in ('test_ordinary_mode_has_no_fixture_paper_authority_or_side_effect','test_all_running_owners_fence_paper_selection','test_operator_profile_cannot_supply_qualification_or_workflow_authority')]
    if label.startswith('WORKER'):modules=['tests.application.test_normal_fixture_worker']
    if label.startswith('WORKER_CORE'):modules=['tests.application.test_paper_owner_composition.PaperOwnerCompositionTests.test_subject_bound_service_denies_foreign_start_and_recovery_without_generation_change']
    if label.startswith('WORKER_REPORT'):modules=['tests.application.test_normal_fixture_worker.NormalFixtureWorkerTests.test_normal_completed_trade_stages_actual_reports_and_receipts']
    if label.startswith('WORKER_FEEDBACK'):modules=['tests.application.test_paper_owner_worker.PaperOwnerWorkerTests.test_actual_full_feedback_outbox_cannot_stop_other_protected_management']
    if label.startswith('WORKER_BACKUP'):modules=['tests.application.test_normal_fixture_worker.NormalFixtureWorkerTests.test_complete_normal_fixture_backup_preserves_protected_truth_and_restore_fences']
    if label.startswith('INTEGRATION'):modules=['tests.application.test_fixture_product_mode','tests.application.test_fixture_recipe_flow','tests.application.test_research_setup_flow','tests.application.test_normal_fixture_paper','tests.application.test_normal_fixture_worker','tests.application.test_paper_owner_composition','tests.application.test_paper_owner_worker','tests.application.test_product_data_backup','tests.application.test_cloud_feedback','tests.application.test_cloud_publisher','tests.application.test_paper_feedback_outbox']
    before=capture();implementation=_revision();temporary=BASE/f'S09-normal-fixture-{label}-temp';_local_path(temporary);temporary.mkdir()
    retained=retain_execution_inputs({key:val for key,val in before.items() if key.startswith('external/')})
    environment=os.environ.copy();environment.update(PYTHONPATH=str(REPO/'src'),PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',TEMP=str(temporary),TMP=str(temporary))
    prefix=BASE/f'S09-normal-fixture-{label}';handle=None;started=stamp()
    with OwnedProof(prefix.with_suffix('.log')) as owner:
        try:
            with awake_request() as awake:
                command=[sys.executable,str(BASE/'test_s09_public_setup_runner_bindings.py')] if label.startswith('PROOF') else [sys.executable,'-m','unittest',*modules,'-v']
                if label=='PAPER_DIAGNOSTIC':command=[sys.executable,str(BASE/'diagnose_s09_fixture_paper_start.py')]
                if label=='WORKER_DIAGNOSTIC':command=[sys.executable,str(BASE/'diagnose_s09_fixture_worker.py')]
                if label.startswith('WORKER_RESTORE_DIAG'):command=[sys.executable,str(BASE/'diagnose_s09_fixture_restore.py')]
                handle=spawn_owned(command,cwd=REPO,limits=ResourceLimits(600),stdout=owner.stream,stderr=subprocess.STDOUT,env=environment);code=handle.wait()
        finally:
            reaped=handle is not None and terminate_owned(handle,deadline_seconds=5).reaped
        owner.require_owned();owner.stream.seek(0);raw=owner.stream.read(8*1024**2+1);assert len(raw)<=8*1024**2
        text=_sanitize(raw.decode('utf-8',errors='replace'),REPO).replace(str(BASE.parent),'<PROJECT_ROOT>').replace('\r\n','\n')
        owner.stream.seek(0);owner.stream.write(text.encode());owner.stream.truncate();owner.stream.flush();owner.require_owned()
    result=parse_result(text,returncode=code);unchanged=before==capture() and implementation==_revision()
    value=dict(label=label,started_at_utc=started,finished_at_utc=stamp(),source_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),worktree='CLEAN' if not subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip() else 'DIRTY_IMPLEMENTATION_TESTING',implementation_hash=implementation,source_input_hashes={key:val for key,val in before.items() if not key.startswith('external/')},execution_input_hashes={key:val for key,val in before.items() if key.startswith('external/')},inputs_unchanged=unchanged,modules=modules,tests_run=result.tests_run,failures=result.failures,errors=result.errors,skipped=result.skipped,exit_code=code,tree_reaped=reaped,awake_request=awake,log_sha256=sha(prefix.with_suffix('.log').read_bytes()),scope='EXTERNAL_EXECUTION_BINDING_GUARDS_ONLY;NO_PRODUCT_TEST_CREDIT' if label.startswith('PROOF') else 'PUBLIC_NORMAL_SOURCE_SETUP_AUTH_INTAKE_RESEARCH_WITH_NEW_SYNTHETIC_INPUTS;NO_NATIVE_REAL_CLOUD_OR_PAPER_ACCEPTANCE',ordinary_native_paper='NOT_RUN',production_profile='PROPOSED_NOT_ACTIVE',provider_requests=0,credentials='NONE',capital='NONE',github_compute='NOT_USED')
    value['execution_inputs_retained_at']=retained
    if label in ('PAPER_DIAGNOSTIC','WORKER_DIAGNOSTIC') or label.startswith('WORKER_RESTORE_DIAG'):
        value['scope']='DIAGNOSTIC_ONLY;NO_PRODUCT_QUALIFICATION'
    elif label.startswith(('WORKER_CORE','WORKER_FEEDBACK')):
        value['scope']='ACTUAL_COMPONENT_GUARDS_ONLY;NO_NORMAL_PRODUCT_OR_NATIVE_ACCEPTANCE'
    elif label.startswith(('WORKER','PAPER','INTEGRATION')):
        value['scope']='NORMAL_PUBLIC_SOURCE_FIXTURE_FLOW_AND_NAMED_COMPONENT_REGRESSION;SYNTHETIC_AUTH_TTY_AND_MINIMAL_UI_ASSETS;NO_NATIVE_BROWSER_REAL_CLOUD_OR_REAL_FORWARD_ACCEPTANCE'
    with OwnedProof(prefix.with_suffix('.json')) as owner:owner.persist(value)
    assert unchanged and reaped and awake['restored'] is True
    print(text,flush=True);return code
if __name__=='__main__':raise SystemExit(main())
