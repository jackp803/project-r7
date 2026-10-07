"""Manually select bounded DATA/RES source support; never issue acceptance."""
from pathlib import Path
import json

base=Path(__file__).resolve().parent
revision='fec8af0f70d787deea720b1e7f952c4fca9487b5'
rows=[]
def add(identifier,behavior,selections,remaining):
    rows.append(dict(id=identifier,supported_behavior=behavior,
        selectors=[[f'tests/{group}/{source}.py',method] for group,source,method in selections],remaining=remaining))
def a(source,*methods):return [('application',source,method) for method in methods]
def v(source,*methods):return [('validation',source,method) for method in methods]

add('DATA-01',
    'Independent container and logical hashes are checked; changed container encoding preserves logical identity while changing byte identity. Gaps, duplicate/unclosed/missing-arrival rows and late receipts are rejected. Missing funding or incomplete funding coverage is explicit, with no invented zero funding.',
    a('test_dataset_binding','test_container_encoding_changes_byte_identity_but_preserves_logical_identity',
      'test_changed_container_cannot_reuse_prior_manifest_or_mutate_resolved_input',
      'test_logical_hash_is_verified_independently_of_container_hash',
      'test_gap_duplicate_unclosed_and_missing_arrival_fail_before_e2',
      'test_missing_funding_is_explicit_blocker_never_factual_zero',
      'test_late_receipt_and_missing_recorded_funding_coverage_are_not_silently_repaired')+
    a('test_research_pipeline','test_missing_funding_blocks_replay_without_inventing_zero_cost'),
    ['All selected datasets/funding rows are controlled FIXTURE inputs, not real dataset commissioning.'])
add('DATA-02',
    'Frozen chronological DEV/OOS split binds feature-only warmup, bounded entry horizon and declared purge/embargo. Overlap, unbounded horizon or missing embargo are refused. Legacy fractional drawdown is converted with explicit equity into a USDT amount; wrong fee units/nonfinite costs are rejected before replay.',
    a('test_dataset_binding','test_split_is_frozen_sealed_and_has_feature_only_warmup',
      'test_overlap_unbounded_horizon_and_unspecified_embargo_block_protocol')+
    v('test_robustness_v02','test_legacy_validation_policy_receives_drawdown_amount_with_explicit_equity')+
    a('test_research_pipeline','test_wrong_fee_units_and_nonfinite_costs_block_before_replay'),
    ['These selections cover the declared fixture boundaries and units, not every production dataset/split/threshold combination.'])
add('RES-01',
    'The actual ResearchService executes owner-compatible fixture replay, persists canonical E6 backtest evidence and per-stage input/output hashes and times. Reopen reuses durable outputs without repeating replay; a crash between E6 evidence save and job receipt recovers with ABORTED/COMPLETE attempts.',
    a('test_research_pipeline','test_actual_owner_pipeline_persists_execution_and_keeps_diagnostic_out_of_candidate',
      'test_resume_returns_same_durable_outputs_and_does_not_repeat_replay')+
    a('test_research_e6_recovery','test_crash_after_e6_evidence_save_before_job_receipt_recovers_same_upstream_record'),
    ['Source fixture execution and accelerated job-clock recovery are not packaged/native whole-product or real-forward evidence.'])
add('RES-02',
    'Adaptive development binding excludes sealed rows/funding; the actual complete pipeline durably freezes a finalist after robustness and before final OOS. Full normalization observes the durable freeze; an unselected diagnostic does not normalize invalid sealed values. Holdout replay is idempotent and records one observation.',
    v('test_robustness_v02','test_adaptive_binding_has_no_sealed_rows_or_funding_events')+
    a('test_research_robustness','test_real_complete_pipeline_freezes_before_final_replay_and_is_idempotent',
      'test_full_normalization_occurs_only_after_durable_finalist_freeze',
      'test_unselected_diagnostic_never_normalizes_invalid_sealed_values')+
    v('test_holdout_ledger','test_actual_finalist_is_frozen_before_oos_read_and_replay_is_once'),
    ['A FIXTURE OOS PASS does not grant canonical candidate/risk/approval authority; the selected pipeline explicitly retains its blocked candidate gate.'])
add('RES-03',
    'Append-only trial events retain INVALID,FAILED,ABORTED after reopen and reject SQL mutation. Interrupted adaptive STARTED trials remain durable. A Chat observation burns the same symbol/period across family/hash changes and records manual revision; policy amendment cannot reset observed holdout; incomplete consumed OOS cannot be replayed after reopen.',
    v('test_holdout_ledger','test_append_only_trials_keep_invalid_failed_and_aborted_after_restart',
      'test_chat_observation_is_global_for_symbol_period_even_after_family_or_hash_change',
      'test_consumed_incomplete_oos_cannot_be_replayed_after_crash_or_new_version')+
    a('test_research_robustness','test_interrupted_adaptive_trial_is_retained_before_stage_result_exists',
      'test_amended_policy_generation_cannot_reset_observed_holdout'),
    ['Chat observation here is an actual local ledger call with synthetic public inputs, not an external chat/cloud integration execution.'])
add('RES-04',
    'Actual E2/E3 robustness replay retains all four distinct fixture variants, including BLOCKED and INVALID_WINDOW, and computes the declared pass fraction. Selected execution requires explicit immutable profiles/family/seed; invalid or over-budget profiles cannot begin replay.',
    v('test_robustness_v02','test_actual_e2_e3_replays_preserve_every_invalid_and_insufficient_variant',
      'test_unknown_and_over_budget_profiles_do_not_begin_replay',
      'test_declared_budget_is_admitted_before_any_e2_runtime_execution')+
    a('test_research_robustness','test_selected_execution_requires_both_frozen_profiles_explicit_family_and_seed'),
    ['The finite tested parameter neighborhood is fixture-specific; exhaustive search/general strategy robustness is not claimed.'])
add('RES-05',
    'Walk-forward evaluates actual training candidates, uses feature-only warmup with positive purge/embargo and counts each disjoint scored trade once. Overlap/misalignment/sealed access are rejected; changing later evaluation rows preserves the first training selection; stitched loss streak can fail even when individual windows pass.',
    v('test_walk_forward','test_actual_training_selection_and_each_disjoint_scored_interval_once',
      'test_overlap_misalignment_and_sealed_access_rejected',
      'test_later_evaluation_values_cannot_change_earlier_training_choice',
      'test_stitched_loss_streak_is_checked_even_when_each_window_meets_its_limit'),
    ['Only the selected fixture schedules/trades are asserted; real-forward observation and broad capacity remain separate.'])
add('RES-06',
    'Seeded SHA256-counter permutation reproduces pinned ordering and explicitly reports only drawdown/order sensitivity without expectancy inference. Moving blocks preserve local order and report conditional sensitivity with dependence limits. Equity-denominated drawdown/nearest-rank quantiles and ambient-decimal independence are asserted.',
    v('test_monte_carlo','test_seeded_permutation_reproduces_pinned_order_but_never_infers_expectancy',
      'test_moving_blocks_preserve_local_order_and_record_conditional_sensitivity',
      'test_fraction_drawdown_has_explicit_equity_denominator_and_nearest_rank_quantiles',
      'test_fixed_decimal_profile_is_independent_of_ambient_context',
      'test_unknown_float_seed_units_and_computation_budget_rejected'),
    ['These statistical resamples describe selected finite historical fixture trades, not guaranteed returns or independent future evidence.'])
add('RES-07',
    'Empty/too-small Monte Carlo and arithmetic overflow return BLOCKED with absent quantiles; missing research policy or insufficient DEV cannot become quantitative PASS. Insufficient final OOS remains product BLOCKED while preserving the actual canonical numeric FAIL; diagnostic missing robustness/OOS remains outside candidate.',
    v('test_monte_carlo','test_empty_small_and_too_few_blocks_are_insufficient_not_zero_risk_pass',
      'test_decimal_arithmetic_overflow_is_typed_incomplete_evidence')+
    v('test_robustness_v02','test_no_selected_policy_and_too_few_samples_are_blocked_not_quantitative_fail')+
    a('test_research_robustness','test_insufficient_final_oos_is_product_blocked_and_preserves_legacy_numeric_decision')+
    a('test_research_pipeline','test_actual_owner_pipeline_persists_execution_and_keeps_diagnostic_out_of_candidate'),
    ['This source selection does not replace UI missing-stage truthfulness, whole-product admission or production policy acceptance.'])
add('RES-08',
    'Declared fee stress retains negative net PnL and fees and fails the selected tolerance; its explicit adverse-funding assumption always charges absolute event cost. Changed cost bytes after freeze cannot alter replay assumptions. Actual sealed OOS losses remain FAIL on retry without requery or threshold change, and finalist freezing rejects changed policy.',
    v('test_robustness_v02','test_stress_replays_keep_unfavorable_cost_outcomes_and_fail_selected_criterion')+
    a('test_research_pipeline','test_cost_file_change_after_freeze_cannot_change_actual_replay_assumptions')+
    a('test_research_robustness','test_actual_oos_losses_are_retained_as_fail_without_requery_or_threshold_change')+
    v('test_holdout_ledger','test_freeze_requires_actual_completed_robustness_and_exact_immutable_inputs'),
    ['Selected fee/funding stress is bounded fixture evidence; this selection does not separately assert every slippage-stress variant.'])

body=dict(document_kind='MANUALLY_CURATED_SCOPED_SOURCE_SUPPORT_DRAFT;NOT_REQUIREMENT_ACCEPTANCE',
    candidate_revision=revision,scope='DATA-01_DATA-02_RES-01_THROUGH_RES-08;WINDOWS_OFFLINE_SOURCE_CASES_ONLY',
    requirements=rows,common_limits=[
      'All selected cases come from existing exact-clean fec8af0 Windows source qualification; this draft executes no new research or per-requirement acceptance.',
      'Duplicate references do not increase distinct executed-case counts; no per-case timestamps/duration, native Ubuntu or whole-flow acceptance is inferred.',
      'Dataset/candles/funding/accounts and job clocks are controlled FIXTURE evidence, not real provider, real dataset or forward commissioning.',
      'Ten additional scoped draft rows do not close the66 requirement results or150 inherited applicability decisions; requirement PASS0.'])
target=base/'S15-data-research-support-selection-fec8af0.json';assert not target.exists()
target.write_text(json.dumps(body,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
source=(base/'build_s15_strategy_support_draft.py').read_text(encoding='utf-8')
source=source.replace('S15-strategy-support-selection','S15-data-research-support-selection').replace('S15-strategy-support-draft','S15-data-research-support-draft')
source=source.replace("[f'STR-{number:02d}' for number in range(1,9)]","['DATA-01','DATA-02']+[f'RES-{number:02d}' for number in range(1,9)]")
source=source.replace('selected_requirement_drafts=8','selected_requirement_drafts=10').replace('unselected_v02_requirements=58','unselected_v02_requirements=56')
builder=base/'build_s15_data_research_support_draft.py';assert not builder.exists()
builder.write_text(source,encoding='utf-8',newline='\n')
print('Prepared ten manually curated DATA/RES draft rows; no acceptance issued.')
