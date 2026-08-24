# Integration Status

> Owner: E7 Integration / Architecture / System QA / Release Engineer  
> Current review: `E7-20260824-053` / 2026-08-24  
> Contract baseline: `contracts-v0.1 / BASELINE`  
> Profiles: `protection-v0.1 / close-v0.1 / trade-result-v0.1 / linear-base-asset-pnl-v0.1 / funding-allocation-v0.1 / position-lifecycle-projection-v0.1 / position-lifecycle-execution-binding-v0.1`

## Current integration target

**Gate B / Slice 3 Paper readiness — E4 execution-truth to E5 lifecycle freshness contract**

This task is static contract/architecture work only. No project code/tests, migration, Local Runner, provider/private API, GitHub CI, PAPER, SHADOW, or LIVE activity was executed.

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

## Accepted implementation / contract context

```text
PR #55 in-memory Paper close-to-TradeResult chain         = MATERIALIZED / NOT_RUN
PR #57 position-lifecycle-projection-v0.1                 = ACCEPTED
PR #58 E5 lifecycle projection producer                   = MATERIALIZED / NOT_RUN
PR #60 lifecycle vocabulary clarification / ADR-0008      = ACCEPTED
PR #61 E6 durable Paper runtime implementation            = MATERIALIZED / NOT_RUN
PR #62 E7 durable review                                  = BLOCKED / accepted blocker diagnosis
E7-053 execution-evidence companion contract / ADR-0009   = RESOLVED STATIC
```

## E7-053 contract resolution

The primary E7-052 shared semantic gap is resolved by:

```text
contracts/POSITION_LIFECYCLE_EXECUTION_EVIDENCE_BINDING_V0_1.md
docs/adr/ADR-0009-position-lifecycle-execution-evidence-freshness.md
profile = position-lifecycle-execution-binding-v0.1
classification = ADDITIVE_COMPANION_PROFILE
```

Existing lifecycle projection semantics and identities remain unchanged:

```text
schema_version = contracts-v0.1
position_lifecycle_projection_profile_version = position-lifecycle-projection-v0.1
lifecycle_projection_id identity material = unchanged
```

## Authority remains split

```text
E4 = broker/order/fill/actual Position truth
E5 = risk + Position lifecycle interpretation/revision/event/identity
     + declaration of the exact E4 execution evidence it interpreted
E6 = persistence/replay/hash/reference/freshness comparison only
E7 = shared contracts/integration/release
```

E6 does not gain authority to map OrderResult/Fill truth to PositionEvent or lifecycle state.

## Two independent restart-freshness axes

### Position broker facts

Existing rule remains:

```text
lifecycle_source_broker_state_observed_at
== exact E4 Position observation interpreted by E5
```

Newer raw Position truth beyond the latest E5 projection requires E5 re-attestation/interpretation.

### Position-linked execution evidence

A Gate B restart-authoritative lifecycle projection now requires one immutable companion binding covering all current durable E4 Position-linked reduction-order evidence for:

```text
PROTECTION_STOP
POSITION_EXIT
EMERGENCY_EXIT
```

The companion snapshot includes each exact OrderRequest plus all canonical OrderResult observations and Fill objects for its request/Position lineage.

Freshness rule:

```text
current durable execution snapshot == latest E5 binding snapshot
-> execution-evidence axis is current

current durable execution snapshot != latest E5 binding snapshot
-> fresh E5 interpretation required
-> old lifecycle projection cannot be restart READY
```

No SQLite arrival order or E6 status-to-lifecycle mapping is used.

## Required downstream adaptation

### E5

```text
position-lifecycle-execution-binding-v0.1 producer = REQUIRED / NOT YET MATERIALIZED
```

For every lifecycle projection intended to be Gate B restart-authoritative, E5 must emit exactly one immutable companion binding.

When new execution evidence changes lifecycle, E5 emits a new TRANSITION + binding. When new execution evidence is interpreted but lifecycle remains unchanged, E5 emits a new REATTESTATION + binding. Equal broker Position anchor remains allowed under the accepted lifecycle profile.

### E6

```text
companion binding persistence/recovery consumer = REQUIRED / NOT YET MATERIALIZED
```

E6 may persist/recompute/compare the fixed shared execution snapshot and fail closed on missing/mismatch/conflict. E6 may not infer lifecycle semantics.

### Separate E6 defect from E7-052

Still unresolved and separate:

```text
TradeResult durable referenced-object completeness
= BLOCKED / E6 IMPLEMENTATION DEFECT UNDER SETTLED CONTRACT
```

E6 must later require the referenced OrderRequest / Fill / PositionAction graph to exist and match before a closed durable graph may recover READY.

## Entry-path boundary

Pre-position `entry-v0.1` execution is not uniformly `position_id`-linked and is intentionally outside `position-lifecycle-execution-binding-v0.1` rather than joined heuristically by `trade_plan_id`.

A future restart-authoritative `PENDING_ENTRY` design requires separate E7 contract refinement. Until then that pre-position restart case is not eligible for READY.

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
execution-truth/lifecycle freshness contract        = RESOLVED STATIC
E5 execution-binding producer                       = BLOCKED / IMPLEMENTATION REQUIRED
E6 execution-binding consumer/recovery              = BLOCKED / IMPLEMENTATION REQUIRED
TradeResult durable reference completeness          = BLOCKED / E6 IMPLEMENTATION DEFECT
Restart/persistence                                 = BLOCKED
Paper E2E -> TradeResult + durable audit            = BLOCKED
Gate B                                               = BLOCKED / NOT YET PASS
PAPER                                                = UNAUTHORIZED
```

No executable criterion changes to PASS.

## Bounded next dependency sequence for PM consideration

E7 does not assign or self-start follow-up work.

```text
E5 — materialize position-lifecycle-execution-binding-v0.1 producer
-> E6 — persist/recompute/compare binding + repair TradeResult graph completeness
-> E7 — durable Paper integration/E2E/safety re-review/definition completion
-> PM-authorized exact approved-local Gate B verification
```

No E4 production contract adaptation is required.

## Future approved-local matrix

Not run here. After E5/E6 remediation is accepted and PM authorizes an exact revision:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/integration -p "test_*.py" -v
python -m unittest discover -s tests/e2e -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

If `tests/e2e` is absent at the accepted remediation revision, it must be materialized before verification. Missing suite is not PASS.

## Verification / scope

```text
project executable verification = NOT_RUN
GitHub Actions / CI / hosted runner = NOT_USED
GitHub-triggered compute = NOT_USED
Local Runner = NOT_REQUESTED
provider/private requests = NOT_SENT
exchange credentials = NOT_USED
strategy lifecycle promotion = NONE
PAPER / SHADOW / LIVE = UNAUTHORIZED
E1-E6 production/test changes by E7 = NONE
```

## Detailed evidence

`status/e7/GATE_B_EXECUTION_LIFECYCLE_FRESHNESS_CONTRACT_DECISION_20260824.md`
