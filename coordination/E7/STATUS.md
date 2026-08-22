# E7 Status

- task_id: `E7-20260822-007`
- agent: `E7`
- state: `DONE / BLOCKED_WAITING_E6_CORRECTION`
- branch: `agent/e7-e6-evidence-authority-rereview-20260822`
- review_target: `PR #16 platform: integrate early Slice 2 registry and evidence persistence`
- reviewed_e6_revision: `df39836adabd04c77cc4f0d0b531ea10408866ab`
- observed_pr_head: `e7d1f3d9a99043107824a3c64d1d37663db8ff53`
- implementation_pin_to_pr_head_delta: `coordination/E6/STATUS.md + status/E6_EARLY_SLICE2_HANDOFF.md + status/E6_STATUS.md only`
- review_time_main: `29b5fa3a011554e472a11b35f216a21eb816d4d1`
- review_artifact: `status/e7/E6_EVIDENCE_AUTHORITY_FINAL_REREVIEW_20260822.md`
- summary: `The corrected E6 persistence path now checks exact early lifecycle edges and revalidates durable E2/E3-looking evidence inside SQLiteRegistryStore.append_transition before history/projection mutation. Canonical binding, transaction/concurrency, SQL edge guards, rollback, and prior E6 evidence-contract semantics remain coherent. However E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001 remains BLOCKING because the exported persistence surface itself can manufacture the durable authority being trusted: save_compatibility/save_validation_evidence accept caller-constructed PASS/LOCAL_EXECUTION records with E2/E3 strings and no non-forgeable producer provenance; register_strategy accepts caller-supplied lifecycle state/revision; and exported raw connect permits direct projection mutation. PR #16 remains DO NOT MERGE.`

## Finding dispositions

- `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`: `BLOCKING / NOT CLOSED / E6 OWNER`
- raw_store_evidence_provenance: `BLOCKING / FAIL`
- `E6-EVIDENCE-CONTRACT-001`: `CLOSED / PASS STATIC / NO REGRESSION`

## Persistence authority dispositions

- early_lifecycle_vocabulary: `PASS / DRAFT|BACKTESTING|REJECTED|CANDIDATE ONLY`
- early_lifecycle_edge_allowlist: `PASS / EXACT THREE EDGES`
- python_forbidden_edge_rejection: `PASS / STATIC ONLY`
- sql_forbidden_edge_insert_trigger: `PASS / STATIC ONLY`
- append_only_lifecycle_history: `PASS / STATIC ONLY`
- current_state_check: `PASS / STATIC ONLY`
- expected_revision_check: `PASS / STATIC ONLY`
- resulting_revision_check: `PASS / STATIC ONLY`
- authority_check_inside_transaction_before_mutation: `PASS / STATIC ONLY`
- atomic_history_projection_update: `PASS / STATIC ONLY`
- rollback_behavior: `PASS / STATIC ONLY`
- durable_row_content_binding: `PASS / STATIC ONLY`
- durable_row_producer_provenance: `FAIL / BLOCKING`
- initial_strategy_lifecycle_registration_guard: `FAIL / BLOCKING`
- raw_projection_write_guard: `FAIL / BLOCKING`

## Exact accepted in-transaction checks

At the reviewed correction, `SQLiteRegistryStore.append_transition(...)`:

1. rejects an edge outside the early Slice 2 allowlist;
2. begins `BEGIN IMMEDIATE`;
3. reloads authoritative strategy state;
4. validates current state;
5. validates expected revision;
6. validates resulting revision equals current + 1;
7. calls `require_transition_authority(...)` before lifecycle INSERT/projection UPDATE;
8. inserts history and updates projection atomically;
9. requires exactly one projection row update;
10. commits or rolls back on exception.

For `DRAFT -> BACKTESTING`, durable compatibility must look like exact-strategy E2 `PASS / LOCAL_EXECUTION` with non-empty source revision/environment/command/result ref.

For `BACKTESTING -> CANDIDATE`, the selected durable ValidationDecision and durable BacktestResult parent must look like E3 local-PASS evidence, bind to the exact strategy/content, pass canonical payload validators, and have exact ValidationDecision -> BacktestResult ID binding.

These content/binding checks are accepted statically.

## Blocking raw-store provenance condition

The trusted rows are still writable by the same caller whose authority is being checked.

Reachable exported/public surfaces include:

```text
registry.CompatibilityEvidence
registry.ValidationEvidenceRecord
registry.StrategyVersionRecord
registry.LifecycleTransitionRecord
storage.SQLiteRegistryStore
storage.connect
RegistryStore.save_compatibility(...)
RegistryStore.save_validation_evidence(...)
RegistryStore.append_transition(...)
```

### Synthetic E2 authority

`SQLiteRegistryStore.save_compatibility(...)` directly persists caller-constructed fields. A caller can create a record with:

```text
checker = "E2..."
status = PASS
verification_kind = LOCAL_EXECUTION
source_revision/environment/command/result_ref = caller strings
```

and then call `append_transition(DRAFT -> BACKTESTING)`.

The new test helper `_to_backtesting(...)` demonstrates this model by saving synthetic local-PASS E2-looking evidence through the raw store and then successfully advancing to BACKTESTING. This is evidence of the provenance weakness, not proof of trusted authority.

### Synthetic E3 authority

`SQLiteRegistryStore.save_validation_evidence(...)` directly persists caller-constructed `ValidationEvidenceRecord` objects. A caller can create canonical-looking, internally consistent E3 BacktestResult + ValidationDecision rows with `producer="E3"`, `decision="PASS"`, `PASS / LOCAL_EXECUTION`, exact parent IDs, and matching strategy/content fields, then use the caller-created decision ID for `BACKTESTING -> CANDIDATE`.

Current `require_candidate_authority(...)` can prove canonical consistency but cannot distinguish those caller-created rows from authoritative E3 output.

### Initial lifecycle projection bypass

`SQLiteRegistryStore.register_strategy(...)` inserts caller-supplied `StrategyVersionRecord.current_lifecycle_state` and `registry_revision`. `StrategyVersionRecord` is public. The SQL schema permits all four early lifecycle states and any non-negative revision, so a direct store caller can register a strategy already in `CANDIDATE` without lifecycle/evidence history.

### Raw projection mutation bypass

`storage.connect` is publicly exported and returns the SQLite connection. The immutable-content trigger does not protect `strategy_versions.current_lifecycle_state` or `registry_revision`; direct SQL can therefore mutate the lifecycle projection without the lifecycle transition/evidence path.

These are authoritative persistence bypasses under the TASK's explicit full-surface provenance challenge.

## `E6-EVIDENCE-CONTRACT-001` regression disposition

- canonical BacktestResult validator: `PASS / unchanged blob 954d21c021c0885554ee650acced17610d958a0e`
- service_base: `PASS / unchanged blob 3889ac156358f58c5fc3380865ad73844b874c3c`
- public service evidence ingest: `PASS / validators retained before base persistence`
- invalid enum/type/shape fail closed: `PASS / STATIC ONLY`
- exact strategy/content/backtest binding: `PASS / STATIC ONLY`
- caller verification metadata cannot bypass canonical payload validation: `PASS / STATIC ONLY`
- BacktestResult alone cannot authorize CANDIDATE through service: `PASS / STATIC ONLY`

`src/registry/service.py` intentionally changed to call the new lifecycle-authority helpers and is same-or-stricter at the normal service boundary; no weakening identified.

## Test-definition disposition

Accepted static coverage includes:

- missing/wrong E2 compatibility fields;
- missing/nonlocal E2 metadata;
- missing primary ValidationDecision;
- wrong evidence type;
- FAIL/BLOCKED/NOT_RUN ValidationDecision;
- wrong strategy identity/content hash;
- missing/wrong BacktestResult parent;
- malformed/mismatched canonical payloads;
- missing/nonlocal E3 metadata;
- rejected path leaves lifecycle row/state/revision unchanged;
- valid service-authorized backtesting/candidate paths.

Missing security coverage / contradictory fixture behavior:

- no proof that raw-store synthetic E2 PASS cannot promote; current helper proves it can;
- no proof that raw-store synthetic canonical E3 PASS evidence cannot promote;
- no rejection of `register_strategy(...)` with non-DRAFT initial state/revision;
- no guard/test against direct raw-connection lifecycle projection mutation.

Synthetic PASS fixture strings are not project executable evidence.

## SQL / migration disposition

- forbidden lifecycle event edge INSERT: `PASS / STATIC ONLY`
- lifecycle history UPDATE/DELETE append-only: `PASS / STATIC ONLY`
- evidence tables constrain enum/foreign-key shape: `PASS / STATIC ONLY`
- trusted writer / producer provenance: `ABSENT / BLOCKING`
- initial projection authority constraint: `ABSENT / BLOCKING`
- direct projection mutation guard: `ABSENT / BLOCKING`

SQL edge-shape enforcement is not sufficient producer/promotion authority.

## Scope / synchronization disposition

PR #16 changed-file scope remains E6 registry/storage/tests/docs/status only.

- shared `contracts/**` edits: `NONE`
- E1/E2/E3/E4/E5 production edits: `NONE`
- workflow/CI additions: `NONE`
- provider/credential/secret additions: `NONE FOUND`
- Slice 3 ApprovedTradePlan/OrderRequest/OrderResult/Fill/Position persistence: `ABSENT`
- OKX `sz` / provider execution/reconciliation persistence: `ABSENT`
- later lifecycle states PAPER/READY_FOR_APPROVAL/APPROVED/SHADOW/LIVE/DEGRADED/RETIRED: `ABSENT`

Correction pin -> observed PR head changes only E6 status/handoff documents; no source/test drift after the reviewed correction pin.

At review time:

```text
latest main = 29b5fa3a011554e472a11b35f216a21eb816d4d1
E6 branch vs latest main = ahead 57 / behind 2
latest-main-only delta = coordination/E6/TASK.md + coordination/E7/TASK.md
meaningful production/shared-contract drift = NONE
PR #16 GitHub mergeable = FALSE
```

Coordination-only drift does not invalidate the exact source review. Current `mergeable=false` is secondary; PR #16 is already source-blocked by the authority bypass.

## Merge / verification / release state

- pr_16_source_disposition: `FAIL / BLOCKED`
- pr_16_merge_recommendation: `DO NOT MERGE`
- executable_verification: `NOT_RUN`
- project_tests_executed: `NO`
- migrations_executed: `NO`
- backtests_executed: `NO`
- provider_requests: `NOT_SENT`
- github_compute: `NOT_USED`
- codex_ticket: `NONE / NOT_APPLICABLE WITHOUT LOCAL REPRODUCTION`
- gate_a: `BLOCKED / UNCHANGED`
- gate_b: `BLOCKED / UNCHANGED`
- gate_c: `BLOCKED / UNCHANGED`
- gate_d: `BLOCKED / UNCHANGED`

## Next owner / required outcome

Next owner: `E6`.

A bounded correction must make promotion-relevant evidence/projection authority non-forgeable through the exported authoritative persistence surface while preserving:

- exact early Slice 2 lifecycle vocabulary/edges;
- canonical BacktestResult/ValidationDecision validators;
- normal service behavior;
- concurrency/atomicity/rollback;
- append-only history;
- no Slice 3 or later lifecycle expansion.

E7 stops here and waits for PM/E6. No PR merge, E6 implementation edit, project execution, migration, or next task is started automatically.
