"""Six bounded temporal/capability/parity source selections, no acceptance."""
from pathlib import Path
import json
base=Path(__file__).resolve().parent;rows=[]
def add(number,behavior,selectors,remaining):rows.append(dict(id=f'STR-{number:02d}',supported_behavior=behavior,selectors=selectors,remaining=remaining))
def select(source,*methods):return [[source,method] for method in methods]
validity='tests/strategy/test_v02_validity.py';exits='tests/position/test_v02_exit_requests.py'
paper='tests/product/test_paper_runtime_v02.py';caps='tests/strategy/test_v02_capabilities.py';mtf='tests/strategy/test_v02_multitimeframe.py'
add(9,'Core validity distinguishes evergreen from bounded tactical intervals, reports NOT_YET_VALID before the interval and explicitly denies entry at expiry while preserving required management permission. Entry deadline does not extend approved plan expiry; unfilled Paper entry expires without renewed plan, and first-fill holding deadline survives later partial-fill facts.',
    select(validity,'test_evergreen_and_tactical_are_not_inferred_from_four_hour_timeframe',
      'test_before_interval_is_waiting_and_invalid_tactical_interval_blocks','test_entry_deadline_never_extends_the_approved_plan_expiry')+
    select(exits,'test_partial_fill_never_resets_first_fill_holding_deadline_or_authorizes_new_entry')+
    select(paper,'test_entry_expiry_cancels_unfilled_order_without_renewing_plan','test_max_hold_deadline_management_does_not_wait_for_new_entry_bar'),
    ['Separate core/owner assertions support independent timing; a joined tactical whole-product acceptance result is separate.'])
add(10,'Core tactical expiry returns no new-entry permission with management still allowed. Separately, actual accelerated Paper pause retains open protection and closes through management; retirement preserves RETIRED lifecycle during successful management closure. Expired unfilled plans cancel without fill.',
    select(validity,'test_evergreen_and_tactical_are_not_inferred_from_four_hour_timeframe')+
    select(paper,'test_pause_preserves_open_protection_and_management','test_retirement_blocks_new_entries_and_preserves_existing_management',
      'test_entry_expiry_cancels_unfilled_order_without_renewing_plan'),
    ['These original-index cases are separate assertions, not joined tactical-expiry E2E. Five new actual tactical-owner probes require their own exact proof/review and are not spliced into the1953-case index.',
     'No expiry bypass of real approval or ordinary native runtime is qualified by this selection.'])
add(11,'Actual E2 exit requests resolve fixed/ATR/reward-risk constraints and E5 interprets stop/target/time exits on actual partial exposure. The first-fill hold anchor persists; changed approved stop/target/request cannot reuse it. Shared trailing geometry tightens without widening; unsupported provider modification remains explicitly NON_EXECUTABLE_PROFILE.',
    select(exits,'test_fixed_distance_and_reward_risk_resolve_both_sides_without_sizing','test_atr_uses_exact_bound_e2_observation',
      'test_stop_and_target_close_both_sides_through_existing_e5_authority','test_time_exit_does_not_wait_for_market_or_entry_candle',
      'test_wrong_stop_geometry_and_equal_target_are_rejected','test_initial_protection_uses_actual_partial_exposure_and_real_fp03_evidence',
      'test_partial_fill_never_resets_first_fill_holding_deadline_or_authorizes_new_entry',
      'test_shared_trailing_geometry_tightens_both_sides_and_rejects_widened_loss_bound',
      'test_trailing_proposal_is_monotonic_without_claiming_provider_execution',
      'test_mismatched_plan_stop_and_changed_request_cannot_reuse_anchor','test_changed_approved_target_or_policy_cannot_reuse_first_fill_binding'),
    ['Canonical owner-request interpretation is source verified; non-executable trailing modification is not relabeled actual provider execution.'])
add(12,'E5 time exit works without market/entry candle. Actual accelerated Paper scheduler independently processes due max-hold management; actual protection cancellation produces E5 emergency exit and canonical recovery after close.',
    select(exits,'test_time_exit_does_not_wait_for_market_or_entry_candle')+
    select(paper,'test_max_hold_deadline_management_does_not_wait_for_new_entry_bar','test_scheduler_runs_due_management_without_market_or_entry_candle',
      'test_authoritative_protection_loss_requests_e5_emergency_exit_and_closes_later'),
    ['E5 request fixture uses4h, but selected continuous Paper owner strategy is1h; a complete4h ordinary/native runtime composition is not asserted.'])
add(13,'Capability snapshots distinguish implemented validator from unverified reference/Paper/provider execution. Missing actual handlers are not advertised implemented; unknown semantic version returns typed source/requested/available gap. Snapshot copies/hash are immutable/deterministic and changed owner semantics or required snapshot hash invalidate compatibility.',
    select(caps,'test_recognized_indicator_does_not_claim_verified_execution_or_provider',
      'test_missing_actual_handler_is_never_advertised_as_implemented','test_unknown_version_gap_names_exact_source_and_available_version',
      'test_snapshot_hash_is_deterministic_and_snapshot_cannot_be_mutated','test_changed_snapshot_hash_does_not_transfer_compatibility',
      'test_e1_aggregation_or_e5_exit_semantics_change_requires_fresh_capability_binding'),
    ['This is source-level capability truthfulness; native release qualification/production issuer acceptance remains separate.'])
add(14,'Windows source actual as-of E2 execution checks nested-indicator warmup, LONG signal and conflicting-entry rejection; future bars/receipts cannot change the earlier canonical signal or boundary hash.',
    select(mtf,'test_real_v02_nested_indicator_warmup_conflict_and_bad_data',
      'test_all_future_bars_and_receipts_cannot_change_earlier_signal_or_boundary_hash'),
    ['Mandatory native Windows-versus-Ubuntu24.04/26.04 golden parity has not run. Source prefix invariance cannot establish cross-platform signal parity; both Ubuntu results remain NOT_RUN.'])
policy=dict(document_kind='MANUALLY_CURATED_SCOPED_SOURCE_SUPPORT_DRAFT;NOT_REQUIREMENT_ACCEPTANCE',
    candidate_revision='fec8af0f70d787deea720b1e7f952c4fca9487b5',scope='STR09-14;WINDOWS_SOURCE_SUPPORT_ONLY',requirements=rows,
    common_limits=['Original1953-case exact-clean source qualification only; no new per-result21-field acceptance execution.',
      'Repeated references do not increase distinct case counts and may overlap prior selections.',
      'Mandatory Ubuntu/native4h/normal-runtime/whole-product and real commissioning gaps remain explicit; requirementPASS0.'])
target=base/'S15-temporal-support-selection-fec8af0.json';assert not target.exists()
target.write_text(json.dumps(policy,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
source=(base/'build_s15_strategy_support_draft.py').read_text(encoding='utf-8')
source=source.replace('S15-strategy-support-selection','S15-temporal-support-selection').replace('S15-strategy-support-draft','S15-temporal-support-draft')
source=source.replace("[f'STR-{number:02d}' for number in range(1,9)]","[f'STR-{number:02d}' for number in range(9,15)]")
source=source.replace('selected_requirement_drafts=8','selected_requirement_drafts=6').replace('unselected_v02_requirements=58','unselected_v02_requirements=60')
builder=base/'build_s15_temporal_support_draft.py';assert not builder.exists();builder.write_text(source,encoding='utf-8',newline='\n')
print('Prepared six manually curated STR09-14 source draft rows; requirementPASS0.')
