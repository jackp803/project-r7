# Integration Status

> Owner: E7 Integration / Architecture / System QA / Release Engineer  
> Current review: `E7-20260824-052` / 2026-08-24  
> Reviewed main: `3c4d8f38aa16bf06cc4e448238f4469d83c6c7b4`  
> Contract baseline: `contracts-v0.1 / BASELINE`  
> Profiles: `protection-v0.1 / close-v0.1 / trade-result-v0.1 / linear-base-asset-pnl-v0.1 / funding-allocation-v0.1 / position-lifecycle-projection-v0.1`

## Current integration target

**Gate B / Slice 3 Paper readiness — durable Paper runtime integration after merged E6 PR #61**

This review is static only. No project code/tests, migration, Local Runner, provider/private API, GitHub CI, PAPER, SHADOW, or LIVE activity was executed.

## Release state

```text
Gate A — RESEARCH_READY = PASS / RESEARCH-INTEGRATION ONLY
Gate B — PAPER_READY    = BLOCKED / NOT YET PASS
Gate C — SHADOW_READY   = BLOCKED / UNCHANGED
Gate D — LIVE_READY     = BLOCKED / UNCHANGED

PAPER / SHADOW / LIVE   = UNAUTHORIZED
project executable verification = NOT_RUN
READY_FOR_APPROVED_LOCAL_GATE_B_VERIFICATION = NO
```

## Accepted current implementation state

```text
PR #55 in-memory Paper close-to-TradeResult chain       = MATERIALIZED / NOT_RUN
PR #57 lifecycle projection contract/ADR                = ACCEPTED
PR #58 E5 lifecycle projection producer                 = MATERIALIZED / NOT_RUN
PR #60 lifecycle vocabulary clarification/ADR           = ACCEPTED
PR #61 E6 Paper runtime durability/restart implementation = MATERIALIZED / NOT_RUN
```

The stale pre-PR #58/#61 statements that E5 projection production and E6 durability are absent are retired by this review.

## Static areas that compose correctly

### Canonical identity / authority preservation

E6 stores exact canonical JSON/IDs and storage hashes; it does not regenerate E4/E5 canonical identities on restart.

Authority remains:

```text
E4 = broker/order/fill/actual Position truth
E5 = risk + Position lifecycle interpretation/revision/event/identity
E6 = persistence/replay/diagnostics only
E7 = shared contracts/integration/release
```

No storage row ID, insertion sequence, persisted timestamp, or database arrival order becomes domain authority.

### Lifecycle profile / vocabulary mechanics

PR #61 mechanically validates:

- `position-lifecycle-projection-v0.1`;
- GENESIS / TRANSITION / REATTESTATION shape;
- E7-published lifecycle state/event/kind vocabulary;
- contiguous revision/predecessor chain;
- content-derived projection ID;
- non-regressing broker anchor;
- equal-anchor broker-fact consistency;
- idempotent replay vs conflict.

E6 does not import/replay the E5 transition table.

### Newer raw Position truth

A newer raw E4 Position observation beyond the latest E5 projection remains separate evidence and causes:

```text
E5_REATTESTATION_REQUIRED
PaperRuntimeRecovery.status = REATTESTATION_REQUIRED
```

No synthetic lifecycle promotion occurs.

### Order / Fill persistence

OrderResult observations are append-only and preserve distinct:

```text
requested_quantity
filled_quantity
order_status
execution_health_status
observed_at
```

Fill identity and request/action/position/order-role lineage are preserved mechanically.

`UNKNOWN / RECONCILIATION_REQUIRED / DEGRADED` current order truth survives restart and prevents a READY recovery claim.

### Funding / immutable result mechanics

Funding evidence preserves exact allocation identity/lineage. Same-lineage conflicting evidence fails closed and cannot last-write-win over prior financial truth. TradeResult is immutable by canonical ID and binds exact durable ApprovedTradePlan + FundingAllocationEvidence.

## Blocking semantic gap — execution evidence freshness vs lifecycle projection

The durable lifecycle profile currently proves which E4 **Position broker observation** E5 interpreted:

```text
lifecycle_source_broker_state_observed_at
```

It does not prove which relevant later E4 `OrderResult` / `Fill` execution observations E5 has already interpreted.

That omission is material for the accepted protection path.

Current E5 `interpret_protection_result(...)` semantics require:

```text
OPEN_PROTECTED + later PARTIALLY_FILLED/FILLED protection truth
-> STATE_UNKNOWN
-> RECONCILIATION_REQUIRED until authoritative close/Position truth exists

OPEN_PROTECTED + later CANCELED/EXPIRED/REJECTED protection truth
-> PROTECTION_LOST
-> EMERGENCY
```

Current E6 `recover()` instead considers an order-level recovery unresolved only for:

```text
order_status = UNKNOWN | RECONCILIATION_REQUIRED
or execution_health_status = UNKNOWN | DEGRADED
```

A healthy later `PARTIALLY_FILLED` or `CANCELED` observation can therefore remain newer than the latest E5 `OPEN_PROTECTED` projection while recovery still reports `READY` if no newer raw Position observation exists.

This is visible in accepted E6 definitions: `test_close_reopen_recovers_exact_open_partial_fill_graph` expects `READY` after persisting a later partial protective Fill without a newer E5 lifecycle projection.

Classification:

```text
BLOCKED / CONTRACT_OR_SEMANTIC_GAP
```

E6 cannot correctly repair this by inventing a private status-to-lifecycle table because that would duplicate E5 semantic authority. An E7-governed shared lifecycle execution-evidence freshness/binding rule is required before the durable graph can be called restart-authoritative across these cases.

E7 blocker definitions:

```text
tests/safety/test_gate_b_durable_lifecycle_freshness.py
commit 47fe8d4adc6939370aba4c7080eee580333c790c
```

They use real E5 lifecycle producer/interpreter, real E4 protection translator/PaperBroker, and real E6 journal. They are `NOT_RUN`.

## Separate E6 settled-contract defect — incomplete TradeResult graph can recover READY

`trade-result-v0.1` carries exact audit references:

```text
entry_fill_ids
exit_fill_ids
entry_order_request_ids
exit_order_request_ids
exit_authority_refs
funding_evidence_id
```

PR #61 verifies plan/funding binding but does not require all referenced OrderRequest/Fill/PositionAction rows to exist/match before recovery may be READY.

The accepted E6 closed recovery fixture references entry Fill/OrderRequest IDs that it does not persist, yet expects READY.

Classification:

```text
IMPLEMENTATION_DEFECT_UNDER_SETTLED_CONTRACT
responsible domain = E6 storage
```

E7 does not modify E6 production/tests here.

## Gate B reconciliation

```text
Required protection follows actual filled quantity = NOT_RUN
Protection failure triggers emergency path          = NOT_RUN
Drawdown/daily/position/kill-switch                 = NOT_RUN
ordinary EXIT in-memory close -> TradeResult        = NOT_RUN
EMERGENCY_EXIT in-memory close -> TradeResult       = NOT_RUN
PROTECTION_STOP in-memory close -> TradeResult      = NOT_RUN
funding producer -> consumer                        = NOT_RUN
Position lifecycle ordering/profile                 = RESOLVED STATIC
Position lifecycle vocabulary                       = RESOLVED STATIC
E5 lifecycle projection producer                    = MATERIALIZED / NOT_RUN
E6 durability implementation                        = MATERIALIZED / NOT_RUN
execution-truth/lifecycle freshness binding          = BLOCKED / CONTRACT_OR_SEMANTIC_GAP
TradeResult durable reference completeness           = BLOCKED / E6 IMPLEMENTATION DEFECT
Restart/persistence                                 = BLOCKED
Paper E2E -> TradeResult + durable audit            = BLOCKED
Gate B                                               = BLOCKED / NOT YET PASS
PAPER                                                = UNAUTHORIZED
```

No executable criterion changes to PASS.

## Bounded next dependency sequence for PM consideration

E7 does not assign or start follow-up tasks.

```text
E7 shared lifecycle execution-evidence freshness/binding decision
-> E5 producer adaptation
-> E6 mechanical consumer/recovery adaptation + TradeResult graph-completeness fix
-> E7 durable integration/E2E/safety completion
-> PM-approved local Gate B verification
```

## Future approved-local matrix

Not run here. After blockers are resolved and PM authorizes an exact revision:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/strategy -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/platform -p "test_*.py" -v
python -m unittest discover -s tests/integration -p "test_*.py" -v
python -m unittest discover -s tests/e2e -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

`tests/e2e` is currently absent on reviewed main; it must be materialized after coherent domain/contract surfaces exist rather than treated as implicit PASS.

## Verification / scope

```text
project executable verification = NOT_RUN
GitHub Actions / CI / hosted runner = NOT_USED
GitHub-triggered compute = NOT_USED
Local Runner = NOT_REQUESTED
Computer Adapter = NOT_USED
provider/private requests = NOT_SENT
exchange credentials = NOT_USED
strategy lifecycle promotion = NONE
PAPER / SHADOW / LIVE = UNAUTHORIZED
E1-E6 production/test changes by E7 = NONE
contracts / ADR changes by E7 = NONE
```

## Detailed evidence

`status/e7/GATE_B_DURABLE_PAPER_INTEGRATION_REVIEW_20260824.md`

## Completion

E7-052 stops on `BLOCKED`. E7 does not self-start contract remediation, E5/E6 fixes, complete Paper E2E definitions, approved-local verification, Gate C, provider/private APIs, PAPER, SHADOW, LIVE, or another task.
