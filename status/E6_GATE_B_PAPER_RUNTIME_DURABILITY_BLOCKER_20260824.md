# E6 Gate B Paper Runtime Durability — Contract/Semantic Blocker

- task_id: `E6-20260824-010`
- agent: `E6`
- target_branch: `agent/e6-gate-b-paper-runtime-durability-20260824`
- inspected_main_revision: `cccb509483e35a5515c81bde35d5af21cd762879`
- state: `BLOCKED / CONTRACT_OR_SEMANTIC_GAP`
- next_owner: `E7`
- local_verification: `NOT_RUN`
- Gate B: `BLOCKED / NOT YET PASS`
- PAPER / SHADOW / LIVE: `UNAUTHORIZED`

## Bounded objective inspected

E6 was assigned only the first durable Paper runtime persistence / restart / audit slice:

```text
canonical E4/E5 runtime objects / observations
-> E6 durable SQLite runtime journal + exact projections/indexes
-> process close/reopen
-> exact restart-safe recovery/readback
-> immutable/idempotent audit behavior
```

No runtime scheduling, E4/E5 behavior, E7 release logic, provider/private API work, lifecycle promotion, or executable verification was in scope.

## Contract-first blocker disposition

The task requires E6 to stop instead of inventing precedence when shared semantics are insufficient to choose a safe current Position projection.

That condition is present in the accepted Gate B chain.

### Expected semantics required by E6 durability

For Position observations, the task requires all of the following simultaneously:

1. append-only authoritative observation history;
2. current projection advances only from a coherent later authoritative observation;
3. stale historical observation may be retained but may not replace the newer projection;
4. equal observation identity/time with conflicting payload fails closed;
5. restart returns the exact stored current canonical observation;
6. E6 must not recompute Position lifecycle from other rows.

To satisfy those requirements, E6 needs canonical authority material that distinguishes a later E5 lifecycle projection from an equal-time conflicting Position payload.

### Actual accepted canonical/runtime evidence

The canonical Position baseline contains `broker_state_observed_at` as the Position observation time and `lifecycle_state` as E5 lifecycle interpretation. No separate shared lifecycle observation timestamp, sequence, revision, or lifecycle-event identity is defined for a Position projection.

The accepted PR #55 positive protection chain explicitly performs:

```python
protected_position = dict(source_position)
protected_position["lifecycle_state"] = verified.next_state.value
```

while asserting the following E4-owned Position facts are unchanged:

```text
position_id
actual_quantity
broker_state_observed_at
reconciliation_status
```

Therefore a valid supported transition:

```text
OPEN_UNPROTECTED -> OPEN_PROTECTED
```

can produce two different canonical Position payloads for the same `position_id` and the same `broker_state_observed_at`.

The E5 `ProtectionLifecycleOutcome` carrying `next_state=OPEN_PROTECTED` is explicitly an E5-internal object, not a shared serialized DTO, and has no authoritative timestamp/sequence field that E6 may persist as cross-module ordering authority.

The same structural gap exists for explicit close intent. `authorize_close_position_action(...)` returns an E5-internal `CloseActionOutcome.next_state=EXIT_REQUESTED` and explicitly does not mutate Position truth. The serialized PositionAction preserves the source Position's `position_observed_at`, but there is no canonical serialized lifecycle-projection timestamp/revision identifying when `EXIT_REQUESTED` became the authoritative lifecycle state.

## Why E6 cannot implement a safe local workaround

The following would cross the task's contract-first boundary:

### Use SQLite insertion order / auto-increment / `persisted_at`

Rejected. Those are E6 storage facts, not E5 lifecycle authority. Arrival order cannot be promoted into a cross-module precedence rule for canonical Position state.

### Last-write-wins for equal `broker_state_observed_at`

Rejected. The task explicitly requires equal observation identity/time with conflicting payload to fail closed. Last-write-wins could silently replace financial/lifecycle truth.

### Treat the lifecycle-only payload change as idempotent

Rejected. `OPEN_UNPROTECTED` and `OPEN_PROTECTED` are materially different canonical lifecycle states and cannot be treated as the same payload.

### Recompute lifecycle from PositionAction / OrderResult / Fill after restart

Rejected. The task explicitly forbids E6 from deriving Position lifecycle/protection state during persistence/recovery. E5 owns lifecycle interpretation.

### Persist both equal-time Position payloads and arbitrarily choose one on restart

Rejected. Without a shared authoritative ordering semantic, choosing one would invent lifecycle precedence. Returning both without a current projection would fail the required exact restart-safe recovery of current Paper runtime state.

## Minimal semantic gap requiring E7 authority

E7 must define an accepted way for serialized/durable Position lifecycle projection changes to carry ordering/authority distinct from the E4 broker observation timestamp, or otherwise define a canonical persistence rule that resolves lifecycle-only updates without E6 inventing domain precedence.

This may be a compatible shared field/profile/refinement or another E7-approved authority model. E6 does not prescribe the contract design.

Until that exists, E6 cannot safely materialize the required current Position projection/restart behavior while satisfying the task's own equal-time conflict rule.

## What was not changed

Because the contract-first blocker was found before editing production persistence:

- no `src/storage/**` production code was changed;
- no migration was added;
- no Paper runtime durability API was added;
- no test definitions were added that encode an invented precedence rule;
- no Registry lifecycle behavior was changed;
- no `contracts/**`, ADR, E1-E5 production, or E7 files were changed;
- no provider/private API, credentials, dashboard, PAPER/SHADOW/LIVE authority, or GitHub workflow/CI work was performed.

Existing early Registry behavior remains untouched:

```text
DRAFT -> BACKTESTING -> REJECTED | CANDIDATE
```

## Executable verification

Executable verification remains:

```text
NOT_RUN
```

No tests, migrations, backtests, runtime code, provider requests, GitHub Actions, CI, hosted runners, GitHub-triggered compute, Computer Adapter, or approved-local runner were used.

Exact future local-only commands from repository root remain:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/platform -p "test_*.py" -v
python -m unittest discover -s tests/registry -p "test_*.py" -v
```

These commands are not PASS evidence until executed against an exact approved revision in a Product Owner-approved local environment.

## Release impact

```text
Restart/persistence preserves required state
= BLOCKED / CONTRACT_OR_SEMANTIC_GAP

Paper E2E closes to TradeResult and persists audit
= BLOCKED / E6 DURABILITY + APPROVED-LOCAL E2E EVIDENCE

Gate B
= BLOCKED / NOT YET PASS

PAPER / SHADOW / LIVE
= UNAUTHORIZED
```

E6 stops on this blocker and does not start another task.