# ADR-0007 — Position Lifecycle Projection Ordering and Durability Boundary

- Status: `ACCEPTED`
- Date: `2026-08-24`
- Decision task: `E7-20260824-047`
- Authority: E7 Integration / Architecture / System QA / Release Engineer
- Parent contract: `contracts-v0.1`
- Profile: `position-lifecycle-projection-v0.1`
- Canonical profile: `contracts/POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md`

## Context

PR #55 completed the current in-memory Gate B close-to-TradeResult chain. It also makes the split Position authority visible:

```text
E4 owns broker Position facts and broker_state_observed_at
E5 owns lifecycle interpretation and lifecycle_state
```

For protection verification, the accepted integration path legitimately keeps the exact same E4 broker Position observation while changing only:

```text
OPEN_UNPROTECTED -> OPEN_PROTECTED
```

Likewise, E5 close authorization may change lifecycle to `EXIT_REQUESTED` while preserving the source Position `broker_state_observed_at`.

PR #56 correctly identified that a durable store cannot distinguish these valid lifecycle-only updates from an equal-time conflicting Position payload when the baseline contains no serialized lifecycle ordering authority.

Using SQLite row order, insertion sequence, `persisted_at`, last-write-wins or recomputation from Order/Fill/Action rows would make E6 a lifecycle authority and violate the existing architecture.

## Decision

Classify the missing semantic as:

```text
ADDITIVE_PROFILE_REQUIRED
```

under unchanged:

```text
schema_version = contracts-v0.1
```

Introduce:

```text
position-lifecycle-projection-v0.1
```

as an additive profile on canonical serialized Position projections.

The normative field, ordering, identity, stale/conflict, replay and migration rules live in `contracts/POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md`.

## 1. Preserve split authority

- E4 remains authoritative for actual broker exposure/order/fill facts and `broker_state_observed_at`.
- E5 remains authoritative for lifecycle/risk interpretation.
- E6 persists/replays/projects only according to serialized shared authority; it does not derive lifecycle.
- E7 owns contract/version/integration/release semantics.

No database fact becomes domain authority.

## 2. Lifecycle order is a separate E5 axis

Broker fact order remains:

```text
broker_state_observed_at
```

Lifecycle order becomes:

```text
lifecycle_revision
```

where `lifecycle_revision` is produced by E5 per exact `position_id`.

Multiple lifecycle revisions may share one E4 broker observation timestamp. This is required for valid lifecycle-only changes.

## 3. E5 produces the durable canonical projection

A durability-eligible profiled Position is the exact E4 broker Position facts plus E5 lifecycle interpretation and the additive lifecycle projection metadata.

E5 must preserve all E4-owned facts exactly and add only E5-owned lifecycle authority/order material.

E6 never allocates the lifecycle revision, projection identity, transition event or predecessor link.

## 4. Revision chain

First durability-eligible projection:

```text
lifecycle_revision = 0
kind = GENESIS
previous_lifecycle_projection_id = null
```

Each later projection:

```text
revision = previous + 1
previous_lifecycle_projection_id = exact previous ID
```

The chain is contiguous. Gaps, forks and predecessor mismatches fail closed.

## 5. Transition vs re-attestation

`TRANSITION` means E5 applied an explicit canonical PositionEvent and changed lifecycle state.

`REATTESTATION` means E5 explicitly binds the same lifecycle state to a newer/equal broker observation without claiming a state change.

Re-attestation is necessary because E6 is forbidden from copying a lifecycle state forward merely because broker facts changed.

## 6. Broker anchor cannot regress

Across lifecycle revisions:

```text
current.lifecycle_source_broker_state_observed_at
>= previous.lifecycle_source_broker_state_observed_at
```

A higher lifecycle revision based on older broker truth is not allowed to become current.

A lifecycle-only transition may reuse the same broker timestamp.

## 7. Current projection is mechanical, not inferred

E6 may index as current only the highest contiguous, conflict-free E5 lifecycle revision whose predecessor chain and broker anchors are valid.

If E6 has a newer E4 broker observation than the current E5 projection references, E6 must preserve both but cannot merge them into a fabricated new Position. Fresh E5 interpretation/reattestation is required.

This permits E6 to report recovery as stale/unresolved without inventing a lifecycle state.

## 8. Identity and conflicts

`lifecycle_projection_id` is content-derived SHA-256 over the entire immutable profiled Position payload except the ID field itself.

Rules:

```text
same revision + same ID + identical payload -> idempotent replay
same revision + changed payload -> conflict
same ID + changed payload -> corrupt/conflict
lower exact stored revision -> historical replay only
revision gap -> cannot advance current
predecessor mismatch -> branch/conflict
same broker timestamp + changed E4 broker facts -> broker-truth conflict
```

No last-write-wins rule is permitted.

## 9. Legacy Positions

Positions lacking `position-lifecycle-projection-v0.1` remain valid for original historical/in-memory purposes.

They are not current Gate B restart-authoritative projections.

A legacy open Position may enter the profile only through:

```text
fresh E4 broker observation
-> explicit E5 interpretation
-> GENESIS revision 0
```

Storage migration cannot invent revisions from old row order.

## 10. Impact on accepted PR #55

PR #55 remains semantically valid for non-durable in-memory integration. Its manual mapping of the real E5 lifecycle outcome onto unchanged E4 Position facts expresses the correct authority split.

It is not sufficient for durable restart evidence because no lifecycle ordering/profile fields exist.

A later E5 task must materialize the profile producer. E7 can then update durability/E2E definitions to use that producer rather than manual lifecycle projection.

No E4 adaptation is required.

## 11. Producer/consumer sequence

Next bounded dependency:

```text
E5 — implement position-lifecycle-projection-v0.1 producer/composition surface
```

Then:

```text
E6 — durable Paper journal/current projection/restart/audit using the shared profile
E7 — durability/E2E/safety definitions
approved-local Gate B verification
```

E7 does not start those tasks automatically.

## 12. Rejected alternatives

### Use `broker_state_observed_at` as lifecycle order

Rejected: valid lifecycle-only transitions may share the same E4 broker observation.

### Use PositionAction.created_at as universal lifecycle order

Rejected: protection verification and other lifecycle events are not universally represented by one PositionAction, and Action time is not a complete serialized lifecycle projection authority.

### Use OrderResult.observed_at

Rejected: E6 would have to infer E5 lifecycle from E4 order evidence, violating ownership.

### Use SQLite row ID / insertion time / `persisted_at`

Rejected: storage arrival order is not E5 authority.

### Last-write-wins for equal broker time

Rejected: cannot distinguish a valid lifecycle-only transition from a conflicting payload.

### Recompute lifecycle after restart

Rejected: E6 is persistence authority, not lifecycle authority.

### Make `broker_state_observed_at` E5-owned or redefine its meaning

Rejected: would break the accepted E4 broker-truth authority boundary.

## Verification

Static contract/architecture only:

```text
project_executable_verification = NOT_RUN
```

No Local Runner, project-code execution, GitHub Actions/CI/hosted runner, provider/private API, credential, PAPER, SHADOW or LIVE activity was used.

## Release impact

```text
PR #56 blocker diagnosis = CONFIRMED
Position lifecycle durability contract/rule = RESOLVED STATIC
E5 profiled lifecycle projection producer = NEXT DEPENDENCY / NOT YET MATERIALIZED
E6 durability implementation = BLOCKED pending E5 producer
Restart/persistence preserves required state = BLOCKED
Paper E2E closes to TradeResult and persists audit = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```
