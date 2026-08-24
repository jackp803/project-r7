# Gate B Position Lifecycle Ordering / Durability Contract Decision — E7-20260824-047

## Authority / scope

- task_id: `E7-20260824-047`
- target branch: `agent/e7-gate-b-position-lifecycle-ordering-contract-20260824`
- reviewed latest main: `0159ddb4afad4db02fa97a29b07ce8d952d68067`
- authoritative TASK blob: `4496317ef1dddfcab450d21af154b9b68a51183f`
- parent contract: `contracts-v0.1 / BASELINE`
- accepted in-memory integration prerequisite: PR `#55 / merge d6302eb89b9319bfd00d5c26e315bd2fe1923b65`
- accepted blocker evidence: PR `#56 / merge 649ae522b71f3992e48b81882662b6d7d0222324`
- project executable verification: `NOT_RUN`

This task is static contract/architecture work only. No project code, tests, migrations, Local Runner actions, GitHub Actions/CI, hosted runners, provider/private APIs, credentials, PAPER, SHADOW or LIVE activity was executed.

## Architecture classification

```text
ADDITIVE_PROFILE_REQUIRED
```

Materialized profile:

```text
position-lifecycle-projection-v0.1
```

Parent remains:

```text
schema_version = contracts-v0.1
```

No breaking change is required because the baseline already defines the correct split authority but never defined serialized lifecycle projection ordering.

## Independent review of PR #56 blocker

PR #56 diagnosis is confirmed.

The baseline Position contains:

```text
broker_state_observed_at  # E4-owned broker observation time
lifecycle_state           # E5-owned lifecycle interpretation
```

but no lifecycle revision, lifecycle projection identity, predecessor identity or lifecycle interpretation ordering material.

Accepted PR #55 demonstrates a valid lifecycle-only change by taking the exact same Position broker facts and replacing only:

```text
OPEN_UNPROTECTED -> OPEN_PROTECTED
```

from the actual E5 protection result outcome while preserving:

```text
position_id
actual_quantity
broker_state_observed_at
reconciliation_status
```

The same structural condition exists for E5 `EXIT_REQUESTED`: the serialized close PositionAction binds the source broker observation, while E5 returns the lifecycle change through an internal outcome object.

Therefore two materially different legitimate lifecycle projections may share one E4 `broker_state_observed_at`.

E6 cannot safely distinguish that condition from an equal-time conflicting Position payload using baseline fields alone.

## Why baseline-only persistence rules are insufficient

Rejected as lifecycle authority:

```text
SQLite row order
insertion sequence
persisted_at
E6-local revision
database auto-increment
last-write-wins
OrderResult.observed_at
PositionAction.created_at as universal ordering
recomputation from Orders/Fills/Actions after restart
```

These are either storage facts, incomplete domain facts, or would force E6 to reconstruct E5 lifecycle semantics.

The conflict is therefore cross-module and genuinely requires E7 contract authority.

## Accepted minimal semantic model

The new profile remains a Position profile rather than introducing a parallel replacement Position type.

E4 continues producing the exact broker fact payload. E5 materializes the durability-eligible canonical Position lifecycle projection by preserving those E4 fields and adding E5-owned lifecycle ordering metadata.

Required additive fields:

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

Ordering axes remain independent:

```text
broker facts     -> broker_state_observed_at / E4
lifecycle state  -> lifecycle_revision / E5
```

Multiple E5 lifecycle revisions may share one broker observation time.

## Projection kinds

```text
GENESIS
TRANSITION
REATTESTATION
```

### GENESIS

First durability-eligible lifecycle projection:

```text
revision = 0
previous = null
event = null
```

E6 cannot manufacture GENESIS from the first row it sees.

### TRANSITION

A real E5 state-machine transition:

```text
revision = previous + 1
previous ID = exact prior projection
lifecycle_event = canonical PositionEvent
transition(previous_state, event) = new lifecycle_state
```

### REATTESTATION

A new E4 broker observation may arrive while E5 lifecycle interpretation remains unchanged.

E6 may not simply copy the old lifecycle state onto the new broker facts. E5 must explicitly emit:

```text
revision = previous + 1
kind = REATTESTATION
event = null
same lifecycle_state
new/equal broker observation anchor
```

This keeps broker and lifecycle ordering independent without making E6 an interpretation engine.

## Identity / replay / conflict rules

Projection identity:

```text
lifecycle_projection_id = posproj_<sha256>
```

computed over the complete immutable profiled Position payload except the ID field itself.

Canonical behavior:

```text
same revision + same ID + identical payload
-> IDEMPOTENT REPLAY

same revision + changed payload or ID
-> CONFLICT / FAIL CLOSED

same ID + changed identity-bearing payload
-> CORRUPT / CONFLICT

lower exact already-known revision arriving later
-> HISTORICAL IDEMPOTENT REPLAY / NEVER CURRENT

lower revision with changed payload
-> STALE BRANCH CONFLICT

revision > current + 1
-> GAP / CANNOT ADVANCE CURRENT

previous_lifecycle_projection_id mismatch
-> BRANCH / CONFLICT
```

Lifecycle projection broker anchors must be nondecreasing across revisions.

## Stale broker/lifecycle composition rule

If E6 has a newer E4 broker observation than the newest E5 profiled Position references:

```text
new broker fact exists
+ no E5 lifecycle projection/reattestation for it
```

E6 must not construct a new canonical Position by merging the newer broker payload with the older lifecycle state.

Required behavior:

- preserve the newer broker evidence;
- preserve the exact last E5 canonical lifecycle projection;
- expose storage/recovery state as requiring E5 re-interpretation/reattestation;
- do not invent a shared lifecycle state.

The storage diagnostic representation is E6 scope; the lifecycle state itself remains E5 authority.

## Required deterministic cases

### Case 1 — same broker observation, protection verified

```text
T / rev0 / OPEN_UNPROTECTED
T / rev1 / PROTECTION_VERIFIED -> OPEN_PROTECTED
```

Valid. Rev1 is later lifecycle authority despite the same E4 timestamp.

### Case 2 — same broker observation, EXIT_REQUESTED

```text
T / rev1 / OPEN_PROTECTED
T / rev2 / EXIT_REQUESTED -> EXIT_REQUESTED
```

Valid.

### Case 3 — stale update after newer lifecycle authority

After rev3 exists, a replay of exact rev1 remains historical/idempotent. A changed rev1 payload is a conflict and never replaces rev3.

### Case 4 — exact replay

Same revision/ID/full payload is idempotent and creates no second logical projection.

### Case 5 — same order changed payload

Same `(position_id, lifecycle_revision)` with different lifecycle state or any changed canonical payload is conflict/fail closed.

### Case 6 — restart

Contiguous conflict-free revisions `0..N` recover exactly revision N without replaying Orders, Fills, PositionActions or TradeResult to infer lifecycle.

### Case 7 — broker update independent from lifecycle

A newer E4 broker observation does not advance the lifecycle projection by itself. E5 must TRANSITION or REATTEST against that observation.

### Case 8 — missing/unknown lifecycle ordering

Legacy Position or missing/unsupported profile/revision/identity cannot be restart-authoritative Gate B state and cannot be interpreted as protected/exiting/closed merely because it arrived later.

## Producer / consumer impact inventory

### E4 broker Position truth

```text
production adaptation required = NO
```

E4 continues to own actual broker Position facts and `broker_state_observed_at` exactly as today. It does not allocate lifecycle revisions or projection IDs.

### E5 protection lifecycle result

```text
production adaptation required = YES
next_owner = E5
```

The current internal `ProtectionLifecycleOutcome` remains internal. A bounded E5 producer must convert the accepted outcome plus exact E4 Position and exact prior profiled Position into the next `position-lifecycle-projection-v0.1` Position.

### E5 close lifecycle result

```text
production adaptation required = YES
next_owner = E5
```

`authorize_close_position_action(...)` currently returns internal `CloseActionOutcome.next_state=EXIT_REQUESTED`. E5 must additionally materialize the next profiled Position lifecycle projection; E4 behavior remains unchanged.

### E5 TradeResult closure lifecycle

```text
production adaptation required = YES
next_owner = E5
```

`build_trade_result(...)` currently returns `POSITION_CLOSED / CLOSED` internally after validating flat/funding/financial truth. The durable close path must emit the corresponding next profiled Position projection anchored to the final E4 flat Position observation.

### E6 persistence/current projection/restart

```text
implementation = BLOCKED UNTIL E5 PRODUCER EXISTS
```

After E5 materializes the producer, E6 may implement append-only runtime journal/current indexing/restart under the shared revision/identity/predecessor/broker-anchor rules. E6 may enforce those rules but may not assign lifecycle revisions or derive lifecycle state.

### E7 integration/E2E/release evidence

PR #55 in-memory projection remains valid for its non-durable scope. After E5 materializes the profiled producer, E7 durability/E2E definitions should consume the producer instead of manually assigning `lifecycle_state` in an integration fixture.

## Legacy / migration consequences

Legacy Positions without the profile:

- remain valid historical/research/in-memory evidence;
- are not rewritten/backfilled;
- are not restart-authoritative Gate B current Position projections.

A legacy open Position can enter the profile only through:

```text
fresh E4 broker observation
-> explicit E5 interpretation
-> GENESIS revision 0
```

E6 migration may not infer GENESIS from row order or the apparently latest old Position.

## Release reconciliation

```text
Position lifecycle durability contract/rule
= RESOLVED STATIC

E5 position-lifecycle-projection-v0.1 producer
= NEXT DEPENDENCY / IMPLEMENTATION GAP

E6 durable Paper persistence/restart/audit
= BLOCKED pending E5 producer

Restart/persistence preserves required state
= BLOCKED

Paper E2E closes to TradeResult and persists audit
= BLOCKED

Gate B
= BLOCKED / NOT YET PASS

PAPER / SHADOW / LIVE
= UNAUTHORIZED
```

No current executable `NOT_RUN` criterion is promoted to PASS.

## Exact PM dependency order

E7 does not assign/start follow-up work.

Recommended dependency order:

```text
1. E5
   implement position-lifecycle-projection-v0.1 producer
   cover GENESIS / TRANSITION / REATTESTATION
   cover protection, close, reconciliation and POSITION_CLOSED outcomes

2. E6
   reissue bounded Paper runtime durability task
   persist exact profiled Position history/current projection
   preserve other canonical runtime identities and funding conflict semantics
   recover exact state without recomputation

3. E7
   add/update restart/durable Paper E2E/safety definitions

4. PM-authorized approved-local Gate B verification
```

## Verification / scope

```text
project_executable_verification = NOT_RUN
Local Runner = NOT_REQUESTED
GitHub Actions / CI / hosted runner = NOT_USED
GitHub-triggered compute = NOT_USED
Computer Adapter = NOT_USED
provider/private requests = NOT_SENT
exchange credentials = NOT_USED
PAPER / SHADOW / LIVE = UNAUTHORIZED
E1-E6 production changes by E7 = NONE
Codex ticket = NONE
```

Future executable verification remains local-only after dependent implementations exist. This static decision itself is not executable PASS evidence.
