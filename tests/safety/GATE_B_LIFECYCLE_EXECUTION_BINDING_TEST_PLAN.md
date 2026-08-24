# Gate B Lifecycle Execution Binding — Safety Test Plan

> Task: `E7-20260824-053`  
> Contract: `position-lifecycle-execution-binding-v0.1`  
> Execution status: `NOT_RUN`

This file defines downstream executable coverage only. It does not execute project code and does not supply PASS evidence.

## Required real-surface coverage

Later E7 integration/safety tests must use accepted E4/E5/E6 production surfaces and must not implement a parallel strategy/risk/execution/lifecycle model.

### 1. Protected OPEN snapshot remains fresh

- create exact E4 Position and E5 OPEN_PROTECTED lifecycle projection;
- persist PROTECTION_STOP request plus the exact OPEN OrderResult observation E5 interpreted;
- persist the matching E5 companion binding;
- close/reopen E6 store;
- recomputed durable execution snapshot equals binding;
- execution-freshness check does not itself block restart authority.

Other reconciliation/lifecycle criteria still apply independently.

### 2. New partial protection execution invalidates old binding

- start from case 1;
- persist later PARTIALLY_FILLED OrderResult plus exact Fill;
- do not emit a newer E5 lifecycle projection/binding;
- close/reopen;
- E6 must not return old OPEN_PROTECTED projection as restart-authoritative READY;
- E6 must not infer the next lifecycle state.

### 3. New full protection execution invalidates old binding

- same as case 2 with FILLED/full Fill;
- without newer E5 interpretation + authoritative flat Position truth, old binding is stale;
- E6 must require fresh E5 interpretation and must not infer CLOSED.

### 4. New protection inactive terminal truth invalidates old binding

For each:

```text
CANCELED
EXPIRED
REJECTED
```

persist the newer OrderResult after an OPEN_PROTECTED binding and prove the old binding no longer equals the durable snapshot.

E6 must not infer PROTECTION_LOST or EMERGENCY.

### 5. New explicit POSITION_EXIT evidence invalidates old binding

- E5 emits EXIT_REQUESTED + companion binding covering initial POSITION_EXIT request/order evidence;
- later partial Fill, FILLED result, or terminal failure changes the durable snapshot;
- without a newer E5 projection/binding, old lifecycle projection cannot remain restart-ready.

### 6. New EMERGENCY_EXIT evidence invalidates old binding

Same invariant as case 5 for `order_role=EMERGENCY_EXIT`.

### 7. Equal broker Position anchor with unchanged lifecycle can re-attest execution freshness

- hold `broker_state_observed_at` constant;
- add new execution evidence;
- E5 interprets the new evidence and determines lifecycle state is unchanged;
- E5 emits next REATTESTATION revision plus new companion binding;
- E6 accepts the new revision/binding only if both projection chain and execution snapshot are exact.

### 8. Newer raw Position truth remains an independent freshness axis

- binding matches execution snapshot;
- persist newer raw E4 Position observation beyond lifecycle projection broker anchor;
- restart remains non-READY until E5 re-attests/reinterprets Position truth.

### 9. Missing companion fails closed

A valid `position-lifecycle-projection-v0.1` projection without one valid companion binding is not Gate B restart-authoritative.

### 10. Binding/projection mismatch fails closed

Reject at minimum:

- wrong position_id;
- wrong lifecycle_projection_id;
- wrong lifecycle_revision;
- execution_interpreted_at != projection.lifecycle_interpreted_at;
- unsupported companion profile/scope.

### 11. Missing referenced E4 evidence fails closed

Persist binding material that references an OrderRequest/OrderResult/Fill snapshot not fully present in durable storage. Recovery must not become READY.

### 12. New in-scope request invalidates old binding

After binding, persist a new Position-linked request with role PROTECTION_STOP, POSITION_EXIT, or EMERGENCY_EXIT. Snapshot changes even before an OrderResult exists; old binding is stale.

### 13. Historical later-arriving observation changes full-set snapshot

Persist an OrderResult observation after the binding whose `observed_at` is older than the previously latest observation but was not present in the bound observation set. Full-set digest must change and require E5 re-interpretation rather than E6 deciding semantic irrelevance.

### 14. Identical replay is idempotent

Exact duplicate OrderRequest, OrderResult observation, Fill, lifecycle projection, and companion binding must not create a new logical freshness state or false conflict.

### 15. Identity conflict fails closed

At minimum:

- same OrderRequest ID changed payload;
- same OrderResult request/time changed payload;
- same Fill ID changed payload;
- same companion binding ID changed payload;
- same lifecycle_projection_id with a different companion snapshot.

No last-write-wins behavior is permitted.

### 16. Ambiguous/degraded execution remains independently fail closed

UNKNOWN / RECONCILIATION_REQUIRED / DEGRADED OrderResult truth cannot become healthy merely because the companion binding matches it.

### 17. Entry path is not silently inferred

Pre-position `entry-v0.1` objects without exact `position_id` linkage must not be pulled into this V0.1 snapshot by `trade_plan_id` heuristics. A future durable PENDING_ENTRY path must fail closed until separately versioned.

### 18. No provider/private/CI/release authority

The implementation/tests must prove or statically retain that:

- no provider/private API call is needed for this Paper freshness binding;
- no credential is stored in the binding;
- no GitHub Actions/CI dependency exists;
- companion presence does not authorize PAPER/SHADOW/LIVE or strategy promotion.

## Future approved-local commands

After E5 producer and E6 consumer/remediation are accepted and PM authorizes an exact local revision:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/integration -p "test_*.py" -v
python -m unittest discover -s tests/e2e -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

If `tests/e2e` is still absent on the accepted remediation revision, E7 must materialize the required durable Paper E2E definitions before verification. Missing suite is not PASS.

```text
project_executable_verification = NOT_RUN
NOT_RUN != PASS
```
