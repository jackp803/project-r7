# Canonical Position Lifecycle Projection Profile — V0.1

> Parent contract set: `contracts-v0.1`  
> Profile identifier: `position-lifecycle-projection-v0.1`  
> Profile status: `BASELINE`  
> Technical authority: E7 Integration / Architecture / System QA / Release Engineer  
> Decision task: `E7-20260824-047`

## 1. Purpose

The baseline `Position` intentionally splits authority:

```text
E4 -> actual broker exposure/order/fill facts + broker_state_observed_at
E5 -> lifecycle/risk interpretation + lifecycle_state
E6 -> persistence/recovery only
```

That split is correct, but the baseline does not serialize ordering authority for lifecycle-only Position projections. Accepted E5 behavior can change:

```text
OPEN_UNPROTECTED -> OPEN_PROTECTED
OPEN_*           -> EXIT_REQUESTED
EXIT_REQUESTED   -> CLOSED
```

without changing E4-owned `broker_state_observed_at`.

A durable store therefore cannot use `broker_state_observed_at`, insertion order, `persisted_at`, SQLite row order, or an E6-local revision to decide which lifecycle projection is authoritative.

This profile adds the minimum E5-owned ordering/identity material required to persist and replay the exact lifecycle interpretation while leaving E4 broker truth unchanged.

It does not authorize PAPER, SHADOW, LIVE, provider/private API activity, credentials, capital exposure, or release-gate advancement.

---

## 2. Compatibility and versioning decision

Classification:

```text
ADDITIVE_PROFILE_REQUIRED
```

The parent remains:

```text
schema_version = contracts-v0.1
```

No set-wide major version bump is required because:

1. `contracts-v0.1` already assigns broker facts to E4 and lifecycle interpretation to E5;
2. the baseline never defined lifecycle projection ordering/revision semantics;
3. this profile adds fields only when `position_lifecycle_projection_profile_version=position-lifecycle-projection-v0.1` is declared;
4. `broker_state_observed_at` retains exactly its existing E4 broker-observation meaning;
5. `lifecycle_state` retains exactly its existing E5 interpretation meaning;
6. legacy Position objects retain their historical/in-memory meaning and are not rewritten;
7. a consumer requiring restart-authoritative Gate B Position state fails closed when the profile is missing or unsupported.

The profile is therefore an additive refinement of an underspecified persistence/replay boundary, not a changed authority boundary.

---

## 3. Profile scope

This profile applies to a serialized/durable canonical `Position` projection after E5 has interpreted an exact E4 broker Position observation.

A profiled Position remains one Position object. It is not a new broker snapshot type and it does not grant E5 authority over E4-owned fields.

Conceptually:

```text
exact E4 Position broker facts
+ prior E5 profiled lifecycle projection, when one exists
+ E5 lifecycle interpretation
-> position-lifecycle-projection-v0.1 Position
-> E6 append-only persistence/current projection/restart
```

E4 may continue to produce the existing baseline Position broker facts without this profile. E5 is the producer of the profiled canonical lifecycle projection.

---

## 4. Additional required fields

A Position that declares:

```text
position_lifecycle_projection_profile_version = position-lifecycle-projection-v0.1
```

must additionally carry:

- `position_lifecycle_projection_profile_version` — exactly `position-lifecycle-projection-v0.1`
- `lifecycle_projection_id` — deterministic content-derived identity defined in section 10
- `lifecycle_revision` — non-negative integer, E5-owned and monotonic per exact `position_id`
- `previous_lifecycle_projection_id` — `null` for revision `0`; otherwise exact immediately preceding projection ID
- `lifecycle_projection_kind` — `GENESIS | TRANSITION | REATTESTATION`
- `lifecycle_event` — exact canonical E5 `PositionEvent` for `TRANSITION`; `null` for `GENESIS` and `REATTESTATION`
- `lifecycle_interpreted_at` — RFC 3339 UTC time at which E5 materialized this authoritative interpretation
- `lifecycle_source_broker_state_observed_at` — exact E4 `broker_state_observed_at` used by E5 for this projection

All baseline Position fields remain required exactly as defined by `contracts-v0.1`.

For this profile:

```text
lifecycle_source_broker_state_observed_at
== Position.broker_state_observed_at
```

The duplicate field is deliberate authority binding: it identifies the exact E4 observation against which E5 interpreted lifecycle state and makes the lifecycle ordering axis explicit without changing E4 timestamp meaning.

---

## 5. Two independent ordering axes

### 5.1 Broker fact ordering — E4 authority

For one `position_id`, E4 broker observations are ordered by:

```text
broker_state_observed_at
```

Rules:

- later timestamp -> later broker observation;
- same timestamp + identical E4-owned broker fact payload -> idempotent duplicate observation;
- same timestamp + different E4-owned broker fact payload -> broker-truth conflict; fail closed;
- an earlier broker observation may remain in audit history but may not replace a later current broker observation.

E6 may enforce these rules but may not create a new broker observation timestamp or choose one conflicting payload by arrival order.

### 5.2 Lifecycle interpretation ordering — E5 authority

For one `position_id`, authoritative lifecycle projections are ordered only by:

```text
lifecycle_revision
```

Rules:

- first durability-eligible E5 projection is revision `0`;
- every subsequent projection is exactly previous revision `+ 1`;
- E6 never allocates or increments this revision;
- `lifecycle_interpreted_at` is audit time, not the primary ordering key;
- SQLite sequence, row ID, insertion order, `persisted_at`, process arrival order or E6-local revision are never lifecycle authority.

Multiple legitimate lifecycle projections may share the same exact `broker_state_observed_at` while having different lifecycle revisions.

Example:

```text
broker_state_observed_at = T
revision 0 -> OPEN_UNPROTECTED
revision 1 -> OPEN_PROTECTED
revision 2 -> EXIT_REQUESTED
```

is valid when each E5 transition is otherwise canonical and the revision/predecessor chain is exact.

---

## 6. Projection kinds

### 6.1 `GENESIS`

`GENESIS` establishes the first durability-eligible lifecycle projection for one `position_id`.

Required:

```text
lifecycle_revision = 0
previous_lifecycle_projection_id = null
lifecycle_event = null
```

The lifecycle state must be an exact E5-authoritative state for the supplied E4 broker observation. E6 cannot manufacture GENESIS from a legacy Position merely because it is the first row stored.

### 6.2 `TRANSITION`

`TRANSITION` records a real E5 state-machine change.

Required:

```text
lifecycle_revision = previous.lifecycle_revision + 1
previous_lifecycle_projection_id = previous.lifecycle_projection_id
lifecycle_event = exact canonical PositionEvent
```

The transition must be valid under the current E5 canonical state machine:

```text
transition(previous.lifecycle_state, lifecycle_event)
== current.lifecycle_state
```

That validation belongs to E5 when producing the projection. E6 may validate declared shape/reference consistency, but E6 does not reconstruct lifecycle by replaying unrelated Orders/Fills/Actions.

### 6.3 `REATTESTATION`

`REATTESTATION` binds the same E5 lifecycle state to a newer or equal exact E4 broker observation without claiming a state change.

Required:

```text
lifecycle_revision = previous.lifecycle_revision + 1
previous_lifecycle_projection_id = previous.lifecycle_projection_id
lifecycle_event = null
current.lifecycle_state = previous.lifecycle_state
current.broker_state_observed_at >= previous.broker_state_observed_at
```

This is required so broker-fact ordering and lifecycle ordering remain independent but composable. A newer E4 exposure observation does not let E6 copy forward a lifecycle state by inference; E5 explicitly re-attests the state.

---

## 7. Relation to broker observations

Across increasing lifecycle revisions for one Position:

```text
current.lifecycle_source_broker_state_observed_at
>= previous.lifecycle_source_broker_state_observed_at
```

A higher lifecycle revision based on an older E4 broker observation is invalid/stale and cannot advance the current authoritative projection.

A lifecycle projection may legitimately reuse the same broker observation as its predecessor for lifecycle-only changes.

If E6 has persisted a newer E4 broker observation than the newest E5 lifecycle projection references, E6 must not merge that newer broker payload with the older lifecycle state and call the result canonical.

Instead:

- preserve both histories;
- retain the latest exact E5 profiled Position as the last authoritative lifecycle projection;
- mark the durable/current operational view as requiring fresh E5 interpretation/reattestation;
- do not invent `OPEN_PROTECTED`, `EXIT_REQUESTED`, `CLOSED`, `RECONCILIATION_REQUIRED`, or any other lifecycle state from storage facts.

The exact storage diagnostic/API representation is E6 implementation scope; it is not lifecycle authority and must not alter the stored canonical Position payload.

---

## 8. Stale, duplicate, gap and conflict semantics

For one `position_id`:

### 8.1 Exact idempotent replay

Same:

```text
lifecycle_revision
lifecycle_projection_id
full canonical Position projection payload
```

is an idempotent replay.

E6 may acknowledge the duplicate without creating a second logical lifecycle update.

### 8.2 Lower revision after a newer revision

A lower revision arriving later is historical/stale.

- if it exactly matches an already stored revision/ID/payload, it is idempotent historical replay;
- otherwise it is a conflicting stale branch and must fail closed;
- it never replaces the higher current projection.

### 8.3 Revision gap

A revision greater than current `+ 1` cannot advance the current projection because one or more authoritative lifecycle updates are missing.

E6 preserves the evidence for reconciliation/audit if its implementation supports that, but it does not skip the gap or infer intermediate states.

### 8.4 Same revision / changed payload

Same `(position_id, lifecycle_revision)` with any different canonical payload or different projection ID is an authority conflict.

It is never last-write-wins.

### 8.5 Same projection ID / changed payload

The same `lifecycle_projection_id` with changed identity-bearing material is corrupt/conflicting evidence and fails closed.

### 8.6 Predecessor mismatch

For revision > 0:

```text
previous_lifecycle_projection_id
```

must equal the exact stored authoritative projection ID at revision `n-1`.

A different predecessor means branch/conflict; E6 must not choose a branch by arrival order.

---

## 9. Unknown/missing lifecycle authority

The following are not restart-authoritative Gate B Position projections:

- legacy Position lacking `position-lifecycle-projection-v0.1`;
- missing/unknown profile version;
- missing lifecycle revision or projection ID;
- unsupported lifecycle state/event/kind;
- revision gap;
- predecessor mismatch;
- lifecycle revision regression;
- broker observation regression;
- same-order conflicting payload;
- newer broker truth with no matching/newer E5 interpretation.

Missing ordering authority never implies a later, healthier, protected, exiting or closed lifecycle state.

E6 must fail closed rather than backfill lifecycle ordering from Orders, Fills, PositionActions, TradeResult, timestamps, row order or storage metadata.

---

## 10. Stable projection identity

`lifecycle_projection_id` is deterministic over the complete immutable serialized profiled Position payload except the ID field itself.

Normative identity algorithm:

1. take every serialized key/value of the profiled Position except `lifecycle_projection_id`;
2. values must already follow canonical contract serialization (UTC `Z`, base-10 decimal strings, explicit enums, deterministic arrays/maps);
3. serialize as UTF-8 JSON with lexicographically sorted field names and compact separators;
4. compute SHA-256;
5. prefix the lowercase hexadecimal digest with:

```text
posproj_
```

Therefore:

```text
same exact canonical projection -> same lifecycle_projection_id
any broker fact / lifecycle / lineage / revision / time change -> different ID
```

Random UUIDs and E6 database row IDs are not canonical projection identity.

---

## 11. Construction of the durable current Position

E5 is the canonical producer of the profiled Position projection.

E5 must:

1. consume the exact E4 Position broker observation;
2. preserve all E4-owned Position facts unchanged;
3. apply/retain only E5-owned lifecycle interpretation;
4. bind the exact broker observation timestamp;
5. allocate the next lifecycle revision from the exact previous profiled Position, not from storage arrival order;
6. bind the exact previous projection ID;
7. emit a deterministic projection ID.

E6 persists the full object and may maintain a current index/projection only when the revision chain is contiguous, conflict-free and broker-anchor rules are satisfied.

E6 current projection selection is therefore mechanical:

```text
highest contiguous valid E5 lifecycle_revision
with exact predecessor chain
and nondecreasing broker observation anchors
and no same-order/broker conflict
```

This is not E6 lifecycle derivation; the ordered authority material is serialized by E5.

---

## 12. Required producer impacts

### 12.1 E4

No E4 production adaptation is required by this profile.

E4 continues to own and emit actual broker Position facts and `broker_state_observed_at`. E4 must not allocate lifecycle revisions or projection IDs.

### 12.2 E5

A bounded E5 follow-up is required before E6 Gate B durability can be implemented safely.

E5 must provide a canonical producer/composition surface for:

```text
exact E4 Position
+ prior position-lifecycle-projection-v0.1 Position when applicable
+ E5 lifecycle interpretation
-> next position-lifecycle-projection-v0.1 Position
```

It must cover at least:

- initial durability-eligible lifecycle projection;
- `PROTECTION_VERIFIED / PROTECTION_FAILED / PROTECTION_LOST` results;
- `EXIT_REQUESTED` from ordinary/emergency close authority;
- reconciliation transitions where supported;
- `POSITION_CLOSED` after TradeResult/flat-position validation;
- re-attestation against a newer E4 broker observation when lifecycle state remains unchanged.

Existing E5 internal outcome objects remain internal; the profiled Position is the serialized durability boundary.

### 12.3 E6

After the E5 producer exists, E6 may implement append-only persistence/current indexing/restart around this profile.

E6 owns storage mechanics only. It enforces the shared revision/identity/conflict rules and restores exact persisted payloads without recomputing lifecycle.

---

## 13. Existing PR #55 in-memory behavior

Accepted PR #55 directly projects an E5 lifecycle outcome onto an in-memory Position mapping for integration definitions while preserving E4 broker facts.

That behavior remains semantically valid for the current non-durable in-memory integration definition.

It is **not** sufficient as Gate B restart-authoritative durable Position evidence because it lacks this profile's lifecycle ordering/identity fields.

After the E5 profile producer materializes, E7 should update durability/E2E definitions to consume that producer instead of manually projecting `lifecycle_state`.

No E4 production change is implied.

---

## 14. Legacy/migration handling

Existing Position objects without this profile:

- remain valid for their original historical, research or current in-memory audit meaning;
- must not be rewritten/backfilled with invented revisions or IDs;
- may be stored as legacy/raw evidence;
- are not Gate B restart-authoritative current Position projections.

For an open legacy position that must enter the new durable profile, the safe migration is:

```text
fresh exact E4 broker Position observation
-> explicit E5 lifecycle interpretation
-> new GENESIS revision 0 profiled Position
```

A database migration must not infer GENESIS from whichever legacy row happens to be latest.

Because PAPER/SHADOW/LIVE are currently unauthorized and no accepted durable Paper runtime exists, no historical live-state migration is authorized by this profile.

---

## 15. Deterministic examples

### 15.1 Same broker observation, protection verified

```text
T = 2026-08-24T07:00:20Z

revision 0
kind = GENESIS
broker_state_observed_at = T
lifecycle_state = OPEN_UNPROTECTED

revision 1
kind = TRANSITION
previous = revision0.id
broker_state_observed_at = T
lifecycle_event = PROTECTION_VERIFIED
lifecycle_state = OPEN_PROTECTED
```

Valid. Broker fact time did not change; lifecycle authority did.

### 15.2 Same broker observation, exit requested

```text
revision 2
kind = TRANSITION
previous = revision1.id
broker_state_observed_at = T
lifecycle_event = EXIT_REQUESTED
lifecycle_state = EXIT_REQUESTED
```

Valid.

### 15.3 New broker observation, same lifecycle

```text
revision 3
kind = REATTESTATION
previous = revision2.id
broker_state_observed_at = T2 > T
lifecycle_event = null
lifecycle_state = EXIT_REQUESTED
```

Valid only because E5 explicitly re-attested the lifecycle against T2.

### 15.4 Stale lifecycle branch arrives late

A new payload claiming revision `1` after revision `3` exists:

- exact stored revision-1 replay -> idempotent historical replay;
- any changed revision-1 payload -> conflict;
- never becomes current.

### 15.5 Same revision changed lifecycle

Two revision-2 payloads, one `EXIT_REQUESTED`, one `OPEN_PROTECTED`:

```text
CONFLICT / FAIL CLOSED
```

Arrival order cannot decide.

### 15.6 Restart

If revisions `0..3` are persisted contiguously and conflict-free, E6 restores the exact serialized revision-3 Position projection.

It does not replay PositionActions/OrderResults/Fills to rediscover `EXIT_REQUESTED`.

If a newer raw E4 broker observation exists beyond revision-3's broker anchor, E6 reports that lifecycle re-interpretation/reattestation is required and does not synthesize a new Position projection.

---

## 16. Release impact

This profile resolves the shared semantic blocker only:

```text
Position lifecycle durability contract/rule = RESOLVED STATIC
E5 position-lifecycle-projection-v0.1 producer = IMPLEMENTATION GAP / NEXT OWNER E5
E6 durable Paper persistence/restart/audit = BLOCKED / waits for E5 producer
Restart/persistence preserves required state = BLOCKED
Paper E2E closes to TradeResult and persists audit = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

Executable verification is not claimed by this contract decision.
