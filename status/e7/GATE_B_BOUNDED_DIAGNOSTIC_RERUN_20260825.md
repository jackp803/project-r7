# Gate B Bounded Diagnostic Rerun — 2026-08-25

- task_id: `E7-20260825-061`
- request_id: `REQ-E7-GATEB-061-01-5F7C3A92`
- action_id: `GATE_B_BOUNDED_DIAGNOSTIC_RERUN`
- job_id: `JOB-23558DF308D825E2`
- source_execution_revision: `62bef3cedda7f7b65116defd9802e2aee37a4fb0`
- source_revision_match: `YES — every delivered diagnostic chunk names the exact authorized revision`
- worktree_state: `CLEAN`
- project_executable_verification: `RAN / DIAGNOSTIC_ONLY`
- remediation_started: `NO`
- Gate B: `BLOCKED / EXECUTABLE_VERIFICATION_FAIL`
- PAPER / SHADOW / LIVE: `UNAUTHORIZED`

## 1. Approved local environment evidence

Sanitized evidence delivered for this single approved bounded diagnostic job:

```text
environment_label = Product-Owner-approved AgentBridge local Windows runner
OS = Windows 10.0.19045
Python = 3.10.6
Python executable = registered local Python310 executable / sanitized
repository path = AgentBridge project-r7 revision worktree / sanitized
checked-out revision = 62bef3cedda7f7b65116defd9802e2aee37a4fb0
working tree before execution = CLEAN
PYTHONPATH = src
job_id = JOB-23558DF308D825E2
request_id = REQ-E7-GATEB-061-01-5F7C3A92
```

The callback chunks did not include trustworthy per-suite wall-clock start/end timestamps. They are recorded as `UNAVAILABLE_IN_DELIVERED_DIAGNOSTIC_CHUNKS`; E7 does not invent timestamps. Exact request/job/revision/count/exit/traceback evidence is sufficient for bounded root-cause triage.

All four durable diagnostic chunks carried the same job ID, exact source revision, clean worktree statement, OS, Python version, `PYTHONPATH`, five suite counts and five suite exit codes. This establishes that the supplied diagnostics belong to the one approved bounded request/job rather than separate ad-hoc runs.

## 2. Exact diagnostic matrix

Commands are exactly the E7-061 authorized commands:

| Suite | Exact command | Tests run | Exit | Result |
|---|---|---:|---:|---|
| brokers | `python -m unittest discover -s tests/brokers -p "test_*.py" -v` | 107 | 1 | FAIL |
| position | `python -m unittest discover -s tests/position -p "test_*.py" -v` | 97 | 1 | FAIL |
| storage | `python -m unittest discover -s tests/storage -p "test_*.py" -v` | 76 | 1 | FAIL |
| integration | `python -m unittest discover -s tests/integration -p "test_*.py" -v` | 21 | 1 | FAIL |
| safety | `python -m unittest discover -s tests/safety -p "test_*.py" -v` | 50 | 1 | FAIL |

Total tests executed in bounded diagnostic matrix: `351`.

Observed non-passing cases: `15` total = `7 ERROR + 8 FAIL`.

This diagnostic run is not a new Gate B qualification run. It cannot promote Gate B even if a subset had passed.

## 3. Complete failure/error inventory

Repository paths below are sanitized to repository-relative form. No private Windows user path is persisted.

### brokers — 107 tests / exit 1

#### ERROR — four tests, one identical first-order signature

Affected tests:

1. `test_okx_demo_adapter.OKXDemoAdapterTests.test_forged_mutated_replayed_or_cross_materialization_evidence_cannot_submit`
2. `test_okx_demo_adapter.OKXDemoAdapterTests.test_reconciliation_queries_truth_but_never_authorizes_retry`
3. `test_okx_demo_adapter.OKXDemoAdapterTests.test_success_ack_is_pending_not_fill_truth`
4. `test_okx_demo_adapter.OKXDemoAdapterTests.test_timeout_is_reconciliation_required_and_ordinary_resubmit_is_not_sent`

Error:

```text
src.brokers.okx_demo.OKXProtocolError:
submit requires the exact OKXOrderMaterialization instance issued by this adapter
```

Traceback locations:

```text
tests/brokers/test_okx_demo_adapter.py:377 -> adapter.submit_entry(...)
tests/brokers/test_okx_demo_adapter.py:354 -> adapter.submit_entry(...)
tests/brokers/test_okx_demo_adapter.py:310 -> adapter.submit_entry(...)
tests/brokers/test_okx_demo_adapter.py:318 -> adapter.submit_entry(...)
src/brokers/okx_demo.py:1111 -> submit_entry -> _authorize_submit
src/brokers/okx_demo.py:1037 -> OKXProtocolError exact-instance provenance guard
```

Static source evidence at the exact diagnosed revision:

- test helper `_materialization()` calls the free `materialize_demo_market_order(...)` function before creating the adapter;
- `_adapter(...)` then constructs a separate `OKXDemoAdapter`;
- `OKXDemoAdapter.prepare_entry(...)` is the production surface that both materializes and calls `_register_issued_preparation(...)`;
- `_authorize_submit(...)` intentionally requires the exact materialization object recorded in that adapter's `_issued_preparations` map.

Therefore the four tests attempt a normal submit/reconcile path with a materialization that the adapter never issued.

#### FAIL — explicit-close zero lexical representation

Test:

`test_paper_broker_protection_stop_flat_truth.PaperBrokerProtectionStopFlatTruthTests.test_existing_position_exit_partial_and_emergency_full_observation_semantics_remain_unchanged`

Traceback:

```text
tests/brokers/test_paper_broker_protection_stop_flat_truth.py:619
self.assertEqual("0", flat["actual_quantity"])
AssertionError: '0' != '0.0000'
```

Production source at the exact revision:

```text
src/brokers/paper.py
residual = source_quantity - total_reduction_filled
refreshed["actual_quantity"] = "0" if is_protection_stop else format(residual, "f")
```

For explicit POSITION_EXIT/EMERGENCY_EXIT, Decimal scale is preserved, so a fully reduced `Decimal("0.0012")` path may serialize zero as `"0.0000"`.

### position — 97 tests / exit 1

#### FAIL — same zero lexical representation cause

Test:

`test_lifecycle_projection.PositionLifecycleProjectionV01Tests.test_position_closed_requires_real_trade_result_outcome_and_exact_flat_position`

Traceback:

```text
tests/position/test_lifecycle_projection.py:320
self.assertEqual("0", closed["actual_quantity"])
AssertionError: '0' != '0.0000'
```

Static source evidence:

- `build_position_lifecycle_closed_transition(...)` preserves E4 broker facts from the authoritative flat Position;
- the test's own `_assert_broker_facts_preserved(...)` requires non-E5 fields to remain unchanged;
- accepted shared financial precision semantics require base-10 Decimal strings but do not require all numeric zero values to be lexically rewritten to exactly `"0"`.

### storage — 76 tests / exit 1

#### ERROR — three corruption-recovery tests blocked by accepted immutability triggers

Affected tests:

1. `test_paper_runtime_reference_remediation.TradeResultReferenceRemediationDefinitions.test_legacy_generic_invalid_trade_result_graph_cannot_recover_ready`
2. `test_paper_runtime_reference_remediation.TradeResultReferenceRemediationDefinitions.test_recovered_position_action_lineage_mismatch_is_conflict`
3. `test_paper_runtime_reference_remediation.TradeResultReferenceRemediationDefinitions.test_recovered_position_action_missing_lineage_is_non_ready_incomplete`

Errors / tracebacks:

```text
tests/storage/test_paper_runtime_reference_remediation.py:181
 -> _direct_replace_trade_result_payload(...)
tests/storage/test_paper_runtime_reference_remediation.py:160
 -> UPDATE paper_trade_results ...
sqlite3.IntegrityError: canonical TradeResult is immutable
```

```text
tests/storage/test_paper_runtime_reference_remediation.py:263
 -> _direct_replace_object_payload(...)
tests/storage/test_paper_runtime_reference_remediation.py:147
 -> UPDATE paper_runtime_objects ...
sqlite3.IntegrityError: paper runtime canonical objects are immutable
```

```text
tests/storage/test_paper_runtime_reference_remediation.py:277
 -> _direct_replace_object_payload(...)
tests/storage/test_paper_runtime_reference_remediation.py:147
 -> UPDATE paper_runtime_objects ...
sqlite3.IntegrityError: paper runtime canonical objects are immutable
```

Static source evidence:

`src/storage/migrations/0002_paper_runtime_durability.sql` deliberately installs:

```text
paper_runtime_objects_immutable_update
paper_runtime_objects_immutable_delete
paper_trade_result_immutable_update
paper_trade_result_immutable_delete
```

The failing tests try to corrupt already-migrated canonical rows using direct SQL UPDATE after those accepted fail-closed triggers are active. The setup fails before the intended recovery assertion is reached.

#### FAIL — stale recovery fixture cannot isolate re-attestation

Test:

`test_paper_runtime_conflict_and_time_ordering.PaperRuntimeConflictAndOrderingDefinitions.test_fractional_newer_raw_position_requires_reattestation`

Traceback:

```text
tests/storage/test_paper_runtime_conflict_and_time_ordering.py:357
self.assertEqual("REATTESTATION_REQUIRED", recovery.status)
AssertionError: 'REATTESTATION_REQUIRED' != 'INCOMPLETE'
```

Static source evidence:

- the test calls `_parents()`, which persists only RiskDecision + ApprovedTradePlan;
- it then persists a lifecycle projection and a newer raw Position observation;
- it does not persist a Position-linked PositionAction/OrderRequest graph or the accepted `position-lifecycle-execution-binding-v0.1` companion;
- `_PaperRuntimeStore.recover(position_id=...)` resolves plan lineage from durable Position-linked runtime objects/funding/TradeResult. With only the supplied `position_id`, the fixture has no Position-linked `trade_plan_id`, so `TRADE_PLAN_LINEAGE_UNRESOLVED` is an INCOMPLETE condition;
- the binding augmentation also requires a companion binding for restart-authoritative lifecycle freshness.

The fixture therefore contains prerequisite incompleteness independent of the newer raw Position observation, so expecting REATTESTATION_REQUIRED as the final status is no longer a valid isolated test setup.

#### FAIL — two stale migration inventories

Test 1:

`test_paper_runtime_conflict_and_time_ordering.PaperRuntimeConflictAndOrderingDefinitions.test_true_additive_migration_from_registry_only_database`

Traceback:

```text
tests/storage/test_paper_runtime_conflict_and_time_ordering.py:284
expected migrations = {
  "0001_strategy_registry.sql",
  "0002_paper_runtime_durability.sql"
}
actual additionally contains:
  "0003_lifecycle_execution_binding.sql"
```

Test 2:

`test_registry_persistence.RegistryPersistenceTests.test_migration_is_idempotent`

Traceback:

```text
tests/storage/test_registry_persistence.py:234
expected = ["0001_strategy_registry.sql"]
actual = [
  "0001_strategy_registry.sql",
  "0002_paper_runtime_durability.sql",
  "0003_lifecycle_execution_binding.sql"
]
```

Static source evidence:

- the exact revision contains all three migration files under `src/storage/migrations/`;
- `_apply_migrations(...)` intentionally applies every sorted `*.sql` file not already recorded in `schema_migrations`;
- `0003_lifecycle_execution_binding.sql` is required by the accepted execution-binding durability implementation.

The assertions encode older migration inventories rather than testing idempotency/additive migration against the current accepted migration set.

### integration — 21 tests / exit 1

#### FAIL — two tests, same zero lexical representation cause

Affected tests:

1. `test_gate_b_paper_trade_result_integration.GateBPaperTradeResultIntegrationDefinitions.test_real_emergency_exit_full_chain_to_canonical_trade_result`
2. `test_gate_b_paper_trade_result_integration.GateBPaperTradeResultIntegrationDefinitions.test_real_ordinary_exit_full_chain_to_canonical_trade_result`

Traceback locations:

```text
tests/integration/test_gate_b_paper_trade_result_integration.py:197 -> _assert_explicit_result(...)
tests/integration/test_gate_b_paper_trade_result_integration.py:193 -> _assert_explicit_result(...)
tests/integration/test_gate_b_paper_trade_result_integration.py:180
 -> self.assertEqual("0", evidence["flat_position"]["actual_quantity"])
AssertionError: '0' != '0.0000'
```

The complete real chain reaches the authoritative flat Position and canonical TradeResult construction; failure occurs only at an E7 lexical string assertion after E4 emits a numerically zero Decimal string preserving scale.

### safety — 50 tests / exit 1

#### FAIL — expected diagnostic code is less specific than actual valid fail-closed code

Test:

`test_gate_b_paper_trade_result_safety.GateBPaperTradeResultSafetyDefinitions.test_cross_plan_position_fill_and_funding_lineage_fail_closed`

Traceback:

```text
tests/safety/test_gate_b_paper_trade_result_safety.py:324
expected code: EXIT_FILL_AUTHORITY_MISMATCH
actual code:   EXIT_FILL_POSITION_MISMATCH
```

Fixture mutation:

```text
wrong_fill = replace(evidence["exit_fill"], position_id="position-other")
```

Static E5 source evidence in `src/position/trade_result.py`:

```text
_validate_exit_fill_binding(...)
1. checks position_action_id -> EXIT_FILL_AUTHORITY_MISMATCH
2. checks position_id        -> EXIT_FILL_POSITION_MISMATCH
3. checks order_role         -> EXIT_FILL_ROLE_MISMATCH
```

The fixture changes only `position_id`; the actual code therefore returns the more specific fail-closed `EXIT_FILL_POSITION_MISMATCH`. Shared close/TradeResult semantics require exact Position lineage but do not require this wrong fixture to be reported as an authority-ID mismatch.

## 4. Evidence-based first-order cause triage

### Cause A — OKX Demo normal-submit tests bypass adapter-issued materialization provenance

```text
classification = SETTLED_CONTRACT_IMPLEMENTATION_DEFECT
bounded defect type = E4-owned test/fixture API-use defect; production provenance guard is behaving as designed
next_owner recommendation = E4
```

Affected: four brokers ERROR cases.

Expected bounded remediation shape: normal submit/reconciliation tests that intend a valid adapter-issued order must obtain materialization through `OKXDemoAdapter.prepare_entry(...)`; forged/clone/cross-adapter evidence rejection should remain separately tested. Do not weaken `_authorize_submit(...)` merely to make the stale fixtures pass.

### Cause B — exact lexical `"0"` assertions over-constrain valid Decimal-string zero

```text
classification = E7_TEST_OR_INTEGRATION_DEFINITION_DEFECT
shared contract gap = NO
next_owner recommendations = E7 for integration definition; E4/E5 for analogous owned domain assertions
```

Affected:

- brokers: one FAIL;
- position: one FAIL;
- integration: two FAIL.

Shared contract `contracts-v0.1` requires Decimal arithmetic and base-10 decimal strings at interchange boundaries; it does not require Decimal-equivalent zero strings to collapse scale to exactly `"0"`. E5 final-position validation itself converts the string to Decimal and requires numerical equality to zero. The integration assertion should therefore validate numeric zero/canonical Decimal validity rather than one lexical scale unless E7 deliberately versions a stricter normalization rule. No such new rule is needed to satisfy current safety semantics.

### Cause C — corruption-recovery tests attempt UPDATE against intentionally immutable canonical tables

```text
classification = SETTLED_CONTRACT_IMPLEMENTATION_DEFECT
bounded defect type = E6-owned test-fixture defect; accepted immutability triggers are functioning
next_owner recommendation = E6
```

Affected: three storage ERROR cases.

The tests need a corruption/legacy fixture that represents invalid persisted material without violating the active production immutability trigger during setup—for example a bounded pre-trigger/legacy database fixture or another test-only setup that does not require weakening production immutability. Production UPDATE protection must remain fail closed.

### Cause D — re-attestation test fixture is incomplete under current durable lineage/binding prerequisites

```text
classification = SETTLED_CONTRACT_IMPLEMENTATION_DEFECT
bounded defect type = E6-owned storage test-fixture drift
next_owner recommendation = E6
```

Affected: one storage FAIL.

The fixture must first establish a restart-authoritative current Position graph under the accepted lifecycle execution-binding profile, then add only the newer raw broker Position observation. Otherwise `INCOMPLETE` correctly outranks the intended re-attestation-only condition.

### Cause E — migration tests assert superseded migration inventories

```text
classification = SETTLED_CONTRACT_IMPLEMENTATION_DEFECT
bounded defect type = E6-owned migration-test expectation drift
next_owner recommendation = E6
```

Affected: two storage FAIL cases.

The current accepted migration directory is `0001 + 0002 + 0003`. Idempotency/additive migration tests must derive or assert the accepted current set rather than historical subsets.

### Cause F — E7 safety test expects the wrong specific fail-closed diagnostic

```text
classification = E7_TEST_OR_INTEGRATION_DEFINITION_DEFECT
next_owner recommendation = E7
```

Affected: one safety FAIL.

The fixture changes `position_id`, and production returns `EXIT_FILL_POSITION_MISMATCH` exactly at the position-lineage check. The test should not require `EXIT_FILL_AUTHORITY_MISMATCH` for a different field mismatch.

## 5. Fan-out summary

The five failing suites do **not** represent five independent production failures.

```text
Cause A -> brokers (4 ERROR)
Cause B -> brokers + position + integration (4 FAIL)
Cause C -> storage (3 ERROR)
Cause D -> storage (1 FAIL)
Cause E -> storage (2 FAIL)
Cause F -> safety (1 FAIL)
```

Total: `15` non-passing tests accounted for exactly.

No observed failure requires a new shared contract or ADR based on the available evidence.

No observed failure is attributable to Windows/Python/PYTHONPATH/revision/worktree configuration.

No production remediation is performed by E7-061.

## 6. Release interpretation

The original complete Gate B matrix remains authoritative executable qualification evidence:

```text
E7-059 overall_matrix_result = FAIL
Gate B = BLOCKED / EXECUTABLE_VERIFICATION_FAIL
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

E7-061 is diagnostic-only. It identifies bounded remediation candidates but cannot promote Gate B and is not a replacement full qualification run.

After PM assigns and accepted owners remediate the bounded defects, any full Gate B qualification rerun requires a separate PM/Product Owner exact-revision authorization.

## 7. Compute / security boundary

```text
GitHub Actions / CI = NOT USED
GitHub-hosted runner = NOT USED
GitHub-triggered compute = NOT USED
provider/private API = NOT USED
exchange credentials = NOT USED
PAPER runtime = NOT STARTED
SHADOW = NOT STARTED
LIVE = NOT STARTED
strategy promotion = NONE
```

Only the five specifically authorized local unittest suites were used for diagnostic execution. No remediation or additional project workload is started by this task.
