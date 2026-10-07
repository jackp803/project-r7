"""Eight partial platform mappings; Windows source cannot qualify Ubuntu."""
from pathlib import Path
import json
base=Path(__file__).resolve().parent;rows=[]
def select(source,*methods):return [[source,method] for method in methods]
def add(number,behavior,selectors,remaining):rows.append(dict(id=f'PLAT-{number:02d}',supported_behavior=behavior,selectors=selectors,remaining=remaining))
platform='tests/application/test_platform.py';entry='tests/application/test_native_entrypoints.py'
build='tests/application/test_native_build_inputs.py';dist='tests/application/test_native_distribution.py'
service='tests/application/test_service_plan.py';supervision='tests/application/test_process_supervision.py'
backup='tests/application/test_database_backup.py';restore='tests/application/test_database_restore.py'
add(1,'Source CLI first profile is diagnostic/loopback with no trading authority or initial database. Existing profile bytes survive identical retry; actual source entrypoint composes E6 migrations and authenticated ASGI using explicitly local synthetic enrollment.',
    select(entry,'test_first_profile_is_explicit_local_diagnostic_and_not_trading_authority',
        'test_existing_profile_is_preserved_including_identical_retry','test_actual_e6_migrations_and_authenticated_api_are_composed'),
    ['These execute Python source, not end-user native startup/no-Python/no-Node acceptance. Separately retained Windows54scenarios57commands native evidence is not transferred to Ubuntu24.04/26.04; both Ubuntu targets NOT_RUN.'])
add(2,'Actual source config and CLI fixture use Chinese/spaced UTF8 paths, preserve existing selected profile bytes and reject nested/external database roots. Explicit local data versus optional cloud roots are retained.',
    select(platform,'test_chinese_paths_diagnostic_defaults_and_local_database',
        'test_nested_roots_and_external_database_rejected_both_directions')+
    select(entry,'test_existing_profile_is_preserved_including_identical_retry'),
    ['Selected assertions do not establish case-sensitive-import or UTC golden parity. Native per-platform Chinese/UTF8/import/time acceptance remains separate; Ubuntu NOT_RUN.'])
add(3,'Actual owned source process tree explicit termination reaps parent/child/grandchild while an unrelated process survives. Separately, automatic timeout reaps the owned child without caller cancellation; shell strings/invalid limits are rejected before spawn.',
    select('tests/application/test_process_tree.py','test_timeout_reaps_parent_child_grandchild_and_preserves_unrelated_process',
        'test_automatic_timeout_reaps_without_caller_cancellation','test_rejects_shell_strings_and_invalid_limits_before_spawning'),
    ['Named tree test invokes explicit termination; separate timeout test covers one owned child. Windows source execution only, not native Ubuntu descendant cleanup acceptance.'])
add(4,'Source hardware doctor reports positive measured memory and GPU NOT_REQUIRED; separate hardware inspection asserts positive memory/CPU/disk. Conservative24GiB policy-input assertions enforce an8GiB research soft budget/one worker and deny supplied low-memory/low-disk facts.',
    select(platform,'test_hardware_doctor_emits_measured_json_without_initializing_data',
        'test_measured_hardware_has_positive_memory_cpu_disk_and_no_gpu_requirement',
        'test_resource_pressure_blocks_research_with_measured_boundaries'),
    ['Actual inspected Windows hardware has33736265728bytes RAM/20logical cores, not asserted24GB capacity. Policy-input threshold test is not actual memory/CPU workload benchmark. Original535 qualification memory samples remain separate; native capacity benchmark pending.'])
add(5,'Portable source service rendering separates existing control/research roles, explicitly reports missing continuous runtime, applies fixed24GiB-input research budget/one-CPU quota/owned-group shutdown and backoff directives, and restricts writable roots/user privilege. Separately, Windows source supervisor restart advances actual process generation, config drift inhibits it and clock regression cannot auto-resume.',
    select(service,'test_two_existing_roles_are_isolated_and_missing_runtime_is_explicit',
        'test_research_uses_measured_budget_one_cpu_and_owned_group_shutdown',
        'test_config_and_binary_are_read_only_with_only_explicit_writable_roots',
        'test_privileged_or_injected_identity_is_denied')+
    select(supervision,'test_restart_has_a_new_actual_process_generation_and_never_financial_permission',
        'test_config_change_inhibits_the_existing_generation_without_renewing_it',
        'test_actual_clock_regression_stops_heartbeat_and_cannot_resume_automatically'),
    ['Unit text is RENDERED_ONLY and supervisor tests run Windows/Python; Ubuntu systemd install/start/restart/stop/generation execution NOT_RUN. No ordinary native continuous PAPER runtime is delivered by these selected assertions.'])
add(6,'Actual local fake bridge marker loss fails CLOUD_NOT_CONNECTED without creating a replacement remote marker/receipt root. Local intake missing root marker and optional cloud config do not initialize replacement staging/data.',
    select('tests/application/test_cloud_bridge.py','test_marker_loss_never_initializes_a_replacement_stage_root_or_remote')+
    select('tests/application/test_cloud_intake.py','test_missing_root_marker_does_not_initialize_replacement_cloud')+
    select(platform,'test_optional_cloud_is_not_silently_initialized'),
    ['Local Windows fake/filesystem faults, not real cloud/mount commissioning or Ubuntu native mount-loss acceptance.'])
add(7,'Actual SQLite committed WAL/intake snapshots are verified without copying WAL/SHM. Source restore creates disjoint private inhibited configuration, fences stale intake/auth claims, advances E6 dispatch/Paper process generations while retaining uncertainty/state, and preserves selected datasets/snapshots/settings bytes through full product restore.',
    select(backup,'test_committed_wal_and_separate_databases_are_backed_up_without_copying_wal')+
    select(restore,'test_restoration_is_disjoint_private_and_emits_inhibited_new_configuration',
        'test_stale_intake_claim_and_auth_session_cannot_survive_restore',
        'test_actual_e6_dispatch_and_paper_generations_advance_without_replaying_effects')+
    select('tests/application/test_product_data_backup.py','test_actual_selected_data_snapshots_and_settings_survive_fresh_restore'),
    ['Synthetic owner stores only; restoration inhibition/reconciliation/reauthorization remain REQUIRED. Separately retained native Windows restore evidence does not qualify Ubuntu or grant restored runtime/financial authority.'])
add(8,'Source build tests require exact clean full revision and preserve foreign output, whitelist code/SQL while excluding synthetic env/cache, and retain interpreter license material. Synthetic native inventory binds source/binary/resources/dependencies; tampering or manifest escape is rejected. Linux wrapper/guide bytes are retained exactly and changed wrapper invalidates provenance. Controlled removal protocol preserves unverified replacement leaves.',
    select(build,'test_exact_source_requires_clean_full_revision','test_existing_foreign_output_is_preserved',
        'test_staged_resource_whitelist_bounds_windows_command_without_copying_other_data',
        'test_native_package_retains_selected_interpreter_license_material')+
    select(dist,'test_sealed_inventory_binds_binary_source_resources_and_exact_dependencies',
        'test_binary_sql_missing_and_unexpected_file_changes_are_rejected',
        'test_manifest_escape_duplicate_keys_and_wrong_platform_are_rejected')+
    select('tests/application/test_service_admin_packaging.py','test_linux_package_retains_exact_wrappers_and_complete_operator_guide',
        'test_changed_retained_wrapper_invalidates_actual_distribution_provenance')+
    select('tests/application/test_service_admin_removal.py','test_leaf_replacement_between_snapshot_and_transfer_is_restored_and_never_deleted',
        'test_replacement_is_preserved_in_quarantine_when_public_name_is_reoccupied'),
    ['Inventory uses synthetic binary bytes and removal uses controlled in-memory leaf interleavings; no native Linux filesystem/upgrade/uninstall execution claim. Full platform dependency/license/checksum/upgrade/uninstall acceptance remains separate; Ubuntu NOT_RUN.'])
policy=dict(document_kind='MANUALLY_CURATED_SCOPED_SOURCE_SUPPORT_DRAFT;NOT_REQUIREMENT_ACCEPTANCE',
    candidate_revision='fec8af0f70d787deea720b1e7f952c4fca9487b5',scope='PLAT01-08;WINDOWS_SOURCE_SUPPORT_ONLY',requirements=rows,
    common_limits=['Original1953-case exact-clean source qualification only; no new per-result21-field platform acceptance execution.',
      'Source/synthetic inventory/rendered Linux text cannot qualify native package/runtime/Ubuntu.',
      'All platform requirements remainNOT_RUN here; actual native Windows evidence is separately retained; requirementPASS0.'])
target=base/'S15-platform-support-selection-fec8af0.json';assert not target.exists()
target.write_text(json.dumps(policy,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
source=(base/'build_s15_strategy_support_draft.py').read_text(encoding='utf-8')
source=source.replace('S15-strategy-support-selection','S15-platform-support-selection').replace('S15-strategy-support-draft','S15-platform-support-draft')
source=source.replace("[f'STR-{number:02d}' for number in range(1,9)]","[f'PLAT-{number:02d}' for number in range(1,9)]")
builder=base/'build_s15_platform_support_draft.py';assert not builder.exists();builder.write_text(source,encoding='utf-8',newline='\n')
print('Prepared eight platform partial source rows; requirementPASS0.')
