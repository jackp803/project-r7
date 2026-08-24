# E7 Status

- task_id: `E7-20260824-047`
- agent: `E7`
- state: `DONE`
- branch: `agent/e7-gate-b-position-lifecycle-ordering-contract-20260824`
- wake_task_id_verified: `YES — latest main coordination/E7/TASK.md exactly matched E7-20260824-047 before work and remained ACTIVE immediately before terminal write`
- reviewed_main: `0159ddb4afad4db02fa97a29b07ce8d952d68067`
- reviewed_task_blob: `4496317ef1dddfcab450d21af154b9b68a51183f`
- contracts_baseline: `contracts-v0.1 / BASELINE`
- architecture_classification: `ADDITIVE_PROFILE_REQUIRED`
- lifecycle_projection_profile: `position-lifecycle-projection-v0.1 / MATERIALIZED`
- set_wide_schema_bump: `NO / schema_version remains contracts-v0.1`
- pr56_blocker_diagnosis: `CONFIRMED`
- position_lifecycle_durability_contract_rule: `RESOLVED STATIC`
- e4_position_broker_truth_adaptation: `NONE REQUIRED`
- e5_lifecycle_projection_producer: `IMPLEMENTATION GAP / NEXT DEPENDENCY`
- e6_paper_runtime_durability: `BLOCKED / AFTER E5 PRODUCER`
- restart_persistence: `BLOCKED`
- paper_e2e_trade_result_durable_audit: `BLOCKED`
- gate_a: `PASS / RESEARCH-INTEGRATION ONLY`
- gate_b: `BLOCKED / NOT YET PASS`
- gate_c: `BLOCKED / UNCHANGED`
- gate_d: `BLOCKED / UNCHANGED`
- paper_shadow_live: `UNAUTHORIZED`
- provider_private_api: `NOT AUTHORIZED / NOT_SENT`
- exchange_credentials: `NOT_USED`
- project_executable_verification: `NOT_RUN`
- local_job: `NOT_REQUESTED / TASK FORBIDS EXECUTION`
- github_compute: `NOT_USED`
- github_actions_ci_hosted_runner: `NOT_USED`
- computer_adapter: `NOT_USED`
- e1_e6_production_changes_by_e7: `NONE`
- codex_ticket: `NONE`

## Independent blocker decision

PR #56 correctly identified a real shared semantic gap.

Baseline Position contains E4-owned `broker_state_observed_at` and E5-owned `lifecycle_state`, but no serialized E5 lifecycle projection ordering authority.

Accepted PR #55 proves that legitimate lifecycle-only changes may share the same exact broker observation:

```text
T / OPEN_UNPROTECTED
T / OPEN_PROTECTED
T / EXIT_REQUESTED
```

Therefore E6 cannot safely use equal broker timestamp, row order, insertion time, persisted_at, auto-increment, last-write-wins, PositionAction.created_at, OrderResult.observed_at, or lifecycle reconstruction from other rows to choose restart-authoritative lifecycle state.

## Materialized profile

`contracts/POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md`

- commit: `722c504592caae6ed8d55f358931513d1154422b`
- profile: `position-lifecycle-projection-v0.1`
- additive under unchanged `contracts-v0.1`;
- preserves E4 broker authority and E5 lifecycle authority;
- defines E5-owned lifecycle revision/predecessor/identity/event/interpreted-time ordering;
- allows multiple lifecycle revisions for one broker observation;
- defines GENESIS / TRANSITION / REATTESTATION;
- defines stale/gap/duplicate/conflict/restart/legacy behavior;
- forbids E6 arrival-order authority or lifecycle reconstruction.

Additional required profile fields:

```text
position_lifecycle_projection_profile_version
lifecycle_projection_id
lifecycle_revision
previous_lifecycle_projection_id
lifecycle_projection_kind
lifecycle_event
lifecycle_interpreted_at
lifecycle_source_broker_state_observed_at
```

## Architecture ADR

`docs/adr/ADR-0007-position-lifecycle-projection-ordering.md`

- commit: `774f470e943ad81b2d6f4c751a6abc97f76b62de`
- records the two independent authority/order axes:

```text
E4 broker ordering = broker_state_observed_at
E5 lifecycle ordering = lifecycle_revision
```

- E6 may validate/persist but never allocate lifecycle order;
- newer E4 broker truth without a corresponding E5 lifecycle projection/reattestation cannot be merged into a synthetic canonical Position.

## Contract registry

`contracts/README.md`

- commit: `3f3a428b64f978bf7ed80f3bda3370e6768a01c0`
- registers `position-lifecycle-projection-v0.1` and explicit E4/E5/E6/E7 ownership.

## Detailed evidence

`status/e7/GATE_B_POSITION_LIFECYCLE_ORDERING_CONTRACT_DECISION_20260824.md`

- commit: `e646facb80f4f4d867bce28f342195a46d68d195`
- records independent PR #56 diagnosis, deterministic examples, replay/conflict rules, legacy handling and producer/consumer impact inventory.

## Release reconciliation

`status/RELEASE_GATES.md`

- commit: `99b52b62f4115b2b94c3338d483e9fc3424c0d34`
- Position lifecycle durability contract/rule is `RESOLVED STATIC`;
- E5 lifecycle projection producer is still an implementation gap;
- restart/persistence remains BLOCKED;
- durable Paper E2E remains BLOCKED;
- no executable NOT_RUN criterion becomes PASS;
- Gate B remains BLOCKED and PAPER unauthorized.

`status/INTEGRATION_STATUS.md`

- commit: `0bb45e080fa6c7553125ad6970fcef172f3e08df`
- records exact producer/consumer sequence and durable replay semantics.

## Canonical ordering / replay rules

### Broker axis

```text
later broker_state_observed_at -> later E4 broker observation
same time + identical E4 broker facts -> duplicate
same time + changed E4 broker facts -> conflict / fail closed
```

### Lifecycle axis

```text
revision 0 -> GENESIS
revision n+1 -> exact predecessor + 1
```

E5 owns revision allocation.

Multiple revisions may share one broker observation timestamp.

### Re-attestation

When E4 broker facts advance but lifecycle state remains unchanged, E5 must explicitly emit a `REATTESTATION` projection. E6 may not copy the old lifecycle state onto newer broker facts by itself.

### Replay/conflict

```text
same revision + same ID + identical payload -> idempotent replay
same revision + changed payload/ID -> conflict
same ID + changed payload -> corrupt/conflict
lower exact stored revision -> historical replay only
lower changed revision -> stale branch conflict
revision gap -> cannot advance
predecessor mismatch -> branch/conflict
higher lifecycle revision with older broker anchor -> stale/invalid
```

Current projection may advance only through the highest contiguous conflict-free E5 revision with exact predecessor chain and nondecreasing broker anchors.

## Producer / consumer impact

### E4

No production adaptation required. E4 keeps current Position broker facts and `broker_state_observed_at` semantics unchanged.

### E5 — exact next dependency

A bounded E5 task is required to materialize a canonical profile producer for:

```text
exact E4 Position
+ prior profiled Position when applicable
+ E5 lifecycle interpretation
-> next position-lifecycle-projection-v0.1 Position
```

It must cover at minimum:

- GENESIS;
- protection verified/failed/lost outcomes;
- ordinary/emergency EXIT_REQUESTED;
- supported reconciliation transitions;
- final POSITION_CLOSED / CLOSED after TradeResult validation;
- REATTESTATION on newer broker observations with unchanged lifecycle.

### E6

E6 durability implementation must wait for the E5 producer. After that it may persist exact profiled Position history/current projection and the rest of the canonical Paper runtime evidence graph without lifecycle recomputation.

### E7

PR #55 remains valid for non-durable in-memory semantics. Later durability/E2E definitions should consume the E5 profile producer instead of manually assigning `lifecycle_state` in a test mapping.

## Legacy handling

Legacy Positions without the profile remain historical/in-memory evidence only. They are not restart-authoritative Gate B current Position projections and must not be backfilled from storage row order.

Safe profile entry requires:

```text
fresh E4 broker observation
-> explicit E5 interpretation
-> GENESIS revision 0
```

## Gate state

```text
Position lifecycle durability contract/rule = RESOLVED STATIC
E5 profiled lifecycle producer = IMPLEMENTATION GAP / NEXT DEPENDENCY
E6 durability implementation = BLOCKED pending E5 producer
Restart/persistence preserves required state = BLOCKED
Paper E2E closes to TradeResult and persists audit = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

## Verification / completion

No project code/tests were executed. No Local Runner, GitHub Actions/CI/hosted runner, GitHub-triggered compute, Computer Adapter, provider/private request or credential was used.

```text
project_executable_verification = NOT_RUN
```

E7 completed only `E7-20260824-047` and stops on `DONE`. E7 does not self-start the E5 projection producer, E6 persistence/restart/audit, full Paper E2E, approved-local verification, Gate C, PAPER, SHADOW, LIVE or another task.
