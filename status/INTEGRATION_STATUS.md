# Integration Status

> Owner: E7 Integration / Architecture / System QA / Release Engineer  
> Current review: `E7-20260824-047` / 2026-08-24  
> Reviewed main: `0159ddb4afad4db02fa97a29b07ce8d952d68067`  
> Contract baseline: `contracts-v0.1 / BASELINE`  
> Profiles: `protection-v0.1 / close-v0.1 / trade-result-v0.1 / linear-base-asset-pnl-v0.1 / funding-allocation-v0.1 / position-lifecycle-projection-v0.1`

## Current integration target

**Gate B / Slice 3 Paper readiness — Position lifecycle durability ordering contract**

This task is static contract/architecture work only. No project code/tests, migration, Local Runner, provider/private API, GitHub CI, PAPER, SHADOW, or LIVE activity was executed.

## Release-gate state

```text
Gate A — RESEARCH_READY = PASS / RESEARCH-INTEGRATION ONLY
Gate B — PAPER_READY    = BLOCKED / NOT YET PASS
Gate C — SHADOW_READY   = BLOCKED / UNCHANGED
Gate D — LIVE_READY     = BLOCKED / UNCHANGED

PAPER / SHADOW / LIVE   = UNAUTHORIZED
project executable verification = NOT_RUN
```

## Accepted context

```text
PR #55 = complete static in-memory Paper close-to-TradeResult chain / NOT_RUN
PR #56 = E6 Paper durability blocker / CONTRACT_OR_SEMANTIC_GAP
```

PR #56 diagnosis was independently rechecked against current contracts and production surfaces and is confirmed.

## Confirmed semantic gap

Canonical Position authority is split correctly:

```text
E4 -> actual broker facts + broker_state_observed_at
E5 -> lifecycle_state / risk interpretation
E6 -> persistence/recovery only
```

However, baseline `contracts-v0.1` has no serialized lifecycle projection ordering authority.

Accepted lifecycle-only changes can preserve the same exact E4 broker observation:

```text
T / OPEN_UNPROTECTED
T / OPEN_PROTECTED
T / EXIT_REQUESTED
```

The current E5 protection result and close outcomes are internal objects. Their `next_state` is authoritative in memory but does not carry a shared durable lifecycle revision/identity.

Therefore E6 cannot use equal `broker_state_observed_at` as last-write-wins and cannot reconstruct lifecycle from Order/Fill/Action rows.

## Architecture decision

```text
classification = ADDITIVE_PROFILE_REQUIRED
schema_version = contracts-v0.1
profile = position-lifecycle-projection-v0.1
Position lifecycle durability contract/rule = RESOLVED STATIC
```

Materialized:

- `contracts/POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md`;
- `docs/adr/ADR-0007-position-lifecycle-projection-ordering.md`;
- `status/e7/GATE_B_POSITION_LIFECYCLE_ORDERING_CONTRACT_DECISION_20260824.md`.

No existing E4 broker timestamp or E5 lifecycle meaning is changed.

## Two independent authority/order axes

### E4 broker facts

```text
ordering = broker_state_observed_at
```

Same timestamp + identical broker fact payload is an idempotent duplicate. Same timestamp + changed E4-owned broker payload is conflict/fail closed.

### E5 lifecycle projection

```text
ordering = lifecycle_revision
```

E5 owns and emits the revision. E6 may validate but never allocate it.

Multiple lifecycle revisions may share one broker observation time.

## Durable profiled Position

A durability-eligible Position adds:

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

Profile kinds:

```text
GENESIS      -> revision 0
TRANSITION   -> explicit E5 PositionEvent changes lifecycle
REATTESTATION -> same lifecycle explicitly re-bound by E5 to newer/equal E4 broker observation
```

`lifecycle_source_broker_state_observed_at` must equal the Position's exact E4 `broker_state_observed_at`.

Across revisions the broker anchor cannot regress.

## Why REATTESTATION exists

A newer E4 broker observation does not by itself authorize E6 to carry forward an old E5 lifecycle state.

If broker truth advances and lifecycle remains valid, E5 explicitly emits the next revision as `REATTESTATION`.

Without that E5 projection:

```text
newer broker observation + older lifecycle projection
-> preserve both
-> lifecycle interpretation required
-> no synthetic merged current Position
```

E6 may expose a storage/recovery diagnostic, but it does not change the shared lifecycle state.

## Replay / conflict semantics

```text
same revision + same projection ID + identical payload
-> idempotent replay

same revision + changed payload/ID
-> conflict / fail closed

same projection ID + changed payload
-> corrupt/conflict

lower exact known revision
-> historical replay only / never current

lower changed revision
-> stale branch conflict

revision gap
-> cannot advance current

predecessor mismatch
-> branch/conflict

higher lifecycle revision with older broker anchor
-> stale/invalid for current projection
```

Current projection selection is mechanical only after E5 serializes the authority:

```text
highest contiguous conflict-free lifecycle_revision
+ exact predecessor chain
+ nondecreasing broker anchors
```

This is persistence projection, not lifecycle derivation.

## Producer / consumer impact

### E4

```text
adaptation required = NO
```

E4 retains current Position broker-fact semantics unchanged.

### E5

```text
adaptation required = YES
next dependency = E5
```

A bounded E5 producer must emit the new profiled Position for at least:

- GENESIS;
- protection verified/failed/lost lifecycle results;
- ordinary/emergency `EXIT_REQUESTED`;
- supported reconciliation transitions;
- final `POSITION_CLOSED / CLOSED` after TradeResult validation;
- REATTESTATION against newer broker observations with unchanged lifecycle.

### E6

```text
durability implementation = AFTER E5 PRODUCER
```

E6 then persists exact profiled Position history/current projection and the rest of the Paper runtime evidence graph. It must restore exact stored lifecycle projections without recomputation.

### E7

PR #55 remains valid for non-durable in-memory semantics. After the E5 producer exists, durability/E2E definitions should consume the producer rather than manually changing `lifecycle_state` in a test mapping.

## Legacy Position handling

Existing Positions without the profile:

- remain valid historical/research/in-memory evidence;
- are not rewritten or backfilled;
- are not Gate B restart-authoritative current Position projections.

Safe profile entry for a legacy open Position is only:

```text
fresh E4 broker Position observation
-> explicit E5 lifecycle interpretation
-> GENESIS revision 0
```

E6 migration cannot infer lifecycle order from row order or timestamps.

## Remaining Gate B durability boundary

After E5 materializes the lifecycle projection producer, E6 still must durably preserve/recover at least:

```text
strategy_id + strategy_version
RiskDecision / risk_decision_id
ApprovedTradePlan / trade_plan_id
profiled Position / position_id + lifecycle projection chain
PositionAction / position_action_id
OrderRequest / order_request_id + client_order_id
OrderResult / broker_order_id when known + observation/reconciliation state
Fill / fill_id + exact request/action/position/order-role lineage
FundingAllocationEvidence / funding_evidence_id + source/lineage identity
TradeResult / trade_result_id + exact funding evidence binding
```

Funding conflict rules remain unchanged and must survive restart without last-write-wins.

## Gate B reconciliation

```text
Required protection follows actual filled quantity = NOT_RUN
Protection failure triggers emergency path          = NOT_RUN
Drawdown/daily/position/kill-switch                 = NOT_RUN
ordinary EXIT in-memory close -> TradeResult        = NOT_RUN / IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
EMERGENCY_EXIT in-memory close -> TradeResult       = NOT_RUN / IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
PROTECTION_STOP in-memory close -> TradeResult      = NOT_RUN / IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
funding producer -> consumer                        = NOT_RUN / IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
Position lifecycle durability contract/rule         = RESOLVED STATIC
E5 lifecycle projection producer                    = BLOCKED / IMPLEMENTATION GAP
Restart/persistence                                 = BLOCKED / waits for E5 + E6 implementation
Paper E2E -> TradeResult + durable audit            = BLOCKED
Gate B                                               = BLOCKED / NOT YET PASS
PAPER                                                = UNAUTHORIZED
```

No executable criterion changes to PASS.

## Exact next dependency order

E7 does not assign or start follow-up work.

Recommended PM order:

```text
1. E5 — materialize position-lifecycle-projection-v0.1 producer
2. E6 — reissue Paper runtime durability/restart/audit implementation
3. E7 — durable restart/Paper E2E/safety definitions
4. PM-authorized approved-local Gate B verification
```

## Future local verification

Not run here. After dependent implementations exist and PM explicitly authorizes approved-local execution:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/integration -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

These are not PASS evidence until actually executed against an exact approved revision.

## Verification / scope

```text
project executable verification = NOT_RUN
GitHub Actions / CI / hosted runner = NOT_USED
GitHub-triggered compute = NOT_USED
Local Runner = NOT_REQUESTED
Computer Adapter = NOT_USED
provider/private requests = NOT_SENT
exchange credentials = NOT_USED
PAPER / SHADOW / LIVE = UNAUTHORIZED
E1-E6 production changes by E7 = NONE
Codex ticket = NONE
```

## Detailed evidence

`status/e7/GATE_B_POSITION_LIFECYCLE_ORDERING_CONTRACT_DECISION_20260824.md`

## Completion

E7-047 resolves only the shared Position lifecycle durability ordering semantic gap. E7 does not self-start E5 producer adaptation, E6 persistence/restart/audit, full Paper E2E, approved-local verification, Gate C, PAPER, SHADOW or LIVE.
