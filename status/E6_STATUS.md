# E6 Platform Status

> Owner: E6 Platform / Storage / Strategy Registry / Dashboard Engineer  
> Branch: `agent/e6-gate-b-paper-runtime-durability-v2-20260824`  
> Task: `E6-20260824-013`  
> State: `DONE / STATIC IMPLEMENTATION MATERIALIZED / EXECUTABLE NOT_RUN`

## Task identity / baseline

- wake task_id: `E6-20260824-013`
- authoritative `main:coordination/E6/TASK.md`: `E6-20260824-013`
- task_id match: `YES`
- task-start/latest inspected main: `beaf2a052f4885e64c6a4a1d66c6ae65bbaf7168`
- target branch initially identical to main: `ahead=0 / behind=0`
- source/tests/docs head before handoff/status: `95679067132d8fa3933b8534983e6d975d0d68ff`
- handoff commit: `fbeee41741f2d060d130217efc3dfe4bb699de28`

## Summary

The PR #56 Position lifecycle durability blocker is no longer present because accepted PR #57 defines `position-lifecycle-projection-v0.1` and accepted PR #58 materializes the E5 producer.

E6 therefore implemented the bounded Gate B Paper durability layer using only serialized shared authority:

```text
canonical E4/E5 runtime payloads
+ E5 profiled Position lifecycle projections
-> additive SQLite journal/current indexes
-> close/reopen recovery surface
-> exact-payload readback + fail-closed diagnostics
```

E6 does not run E4/E5 state machines during persistence/restart and does not derive financial/runtime truth from other rows.

## Materialized storage

Additive migration:

```text
src/storage/migrations/0002_paper_runtime_durability.sql
```

It adds E6-owned storage for:

- immutable RiskDecision;
- immutable ApprovedTradePlan;
- append-only profiled Position lifecycle projections;
- raw/legacy Position broker-observation audit history;
- immutable PositionAction;
- immutable OrderRequest;
- append-only OrderResult observations + current pointer;
- immutable Fill;
- immutable FundingAllocationEvidence + duplicate-observation metadata;
- immutable TradeResult;
- sanitized conflict audit metadata.

Existing `0001_strategy_registry.sql` is unchanged.

## Public surface

Added:

```python
from storage.runtime import open_paper_runtime_journal
```

`PaperRuntimeJournal` exposes persistence/recovery only and does not expose raw SQLite, provider submit, strategy promotion, PAPER, SHADOW or LIVE enablement.

Existing top-level Registry storage boundary remains unchanged:

```text
storage.__all__ = ["open_sqlite_platform"]
```

## Position lifecycle durability

E6 mechanically enforces the accepted E5 profile material:

```text
GENESIS revision 0
subsequent revision = current + 1
exact previous_lifecycle_projection_id
nondecreasing E4 broker anchor
no equal-anchor broker-fact conflict
```

Rules preserved:

- exact duplicate projection = idempotent;
- same revision changed ID/payload = conflict;
- same declared projection ID with changed payload = corruption/conflict;
- revision gap = no advancement;
- predecessor mismatch = no branch selection;
- broker-anchor regression = no advancement;
- exact stale replay = historical/idempotent only;
- legacy Position = never restart-authoritative by row order;
- newer raw E4 Position beyond the current E5 anchor = `REATTESTATION_REQUIRED`, with no synthetic Position projection.

RFC3339 canonical strings are stored unchanged in payload JSON. Separate fixed-width UTC ordering metadata prevents fractional-second formatting from affecting observation order.

## Runtime object idempotency / conflicts

For immutable identity-bearing runtime objects:

```text
same ID + same canonical payload -> idempotent
same ID + changed canonical payload -> conflict / fail closed
```

OrderRequest `client_order_id` remains bound to one durable request. Fill lineage is checked against the durable request without generating broker facts.

OrderResult is append-only by request/observation instant; later observations advance the mechanical current pointer, stale observations do not regress it, and equal-time changed payload conflicts.

## Funding / TradeResult

Funding persistence enforces the accepted `funding-allocation-v0.1` lineage key and identity material.

- same allocation identity -> idempotent;
- later equivalent `calculated_at` observation does not rewrite the first canonical financial object;
- same ID with mismatched identity material -> corruption/conflict;
- different IDs for one lineage key -> conflict, never last-write-wins.

TradeResult:

- is immutable;
- is unique for the bounded `(trade_plan_id, position_id)` closed lineage;
- requires exact durable ApprovedTradePlan and FundingAllocationEvidence binding;
- cannot silently rewrite PnL, fees, quantity, exit reasons or funding reference.

## Recovery

E6-local `PaperRuntimeRecovery` returns exact stored canonical payloads and one storage diagnostic:

```text
READY
REATTESTATION_REQUIRED
RECONCILIATION_REQUIRED
INCOMPLETE
CONFLICT
```

UNKNOWN / RECONCILIATION_REQUIRED / DEGRADED order/position truth is preserved and not converted to healthy/flat/closed state.

A CLOSED current projection without durable funding/result remains `INCOMPLETE`. A newer raw broker observation without E5 re-attestation remains `REATTESTATION_REQUIRED`.

## Deterministic definitions

Added:

```text
tests/storage/test_paper_runtime_durability.py
tests/storage/test_paper_runtime_conflict_and_time_ordering.py
tests/platform/test_paper_runtime_storage_surface.py
```

Coverage includes additive migration, exact round-trip, immutable conflicts, Fill replay, lifecycle GENESIS/TRANSITION/REATTESTATION, gap/fork/stale/anchor behavior, fractional timestamp ordering, raw-broker re-attestation requirement, OrderResult history, funding conflicts, immutable TradeResult binding, close/reopen recovery, ambiguous/reconciliation-required recovery, closed recovery, conflict recovery, rollback, secret rejection and provider-native field rejection.

Existing Registry tests remain defined and `tests/storage/README.md` is updated with the combined inventory.

## Changed scope

Only E6-owned paths:

```text
src/storage/**
tests/storage/**
tests/platform/**
docs/platform/**
status/E6_GATE_B_PAPER_RUNTIME_DURABILITY_20260824.md
status/E6_STATUS.md
coordination/E6/STATUS.md
```

Contracts/ADR changed:

```text
NONE
```

E1-E5 production changed: `NONE`.  
E7 integration/release files changed: `NONE`.  
Provider/private API/network/credential work: `NONE`.  
Strategy lifecycle expansion: `NONE`.

Existing early Registry lifecycle remains exactly:

```text
DRAFT -> BACKTESTING -> REJECTED | CANDIDATE
```

## Verification

```text
local_verification = NOT_RUN
```

No separate exact-revision Local Runner action was approved for this task. No tests, migrations, restart flows, Paper runtime, provider request, GitHub Actions/CI, hosted runner, GitHub-triggered compute or Computer Adapter project execution was run.

Exact future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/platform -p "test_*.py" -v
python -m unittest discover -s tests/registry -p "test_*.py" -v
```

`NOT_RUN` is not PASS.

## Release impact

This task does **not** claim:

```text
Restart/persistence = PASS
Paper E2E = PASS
Gate B / PAPER_READY = PASS
PAPER / SHADOW / LIVE authorization
```

Those require later E7 integration review and approved-local evidence.

## Handoff / stop

Detailed handoff:

```text
status/E6_GATE_B_PAPER_RUNTIME_DURABILITY_20260824.md
```

E6 stops after terminal mailbox STATUS is pushed. It does not self-start E7 integration/E2E, approved-local verification, provider/private work, Gate C, PAPER, SHADOW or LIVE.
