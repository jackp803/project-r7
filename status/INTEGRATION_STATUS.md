# Integration Status

> Owner: E7 Integration / Architecture / System QA / Release Engineer  
> Current review: `E7-20260824-036` / 2026-08-24  
> Reviewed main: `03f06827e9f4659f54afb20b43b0bfc806525b96`  
> Contract baseline: `contracts-v0.1 / BASELINE`

## Current integration target

**Gate B / Slice 3 Paper readiness — close authority, authoritative flatness, canonical TradeResult, durable audit**

This review is static contract/architecture work only. No project code/tests, Paper runtime, provider/private API, migration, Local Runner action, GitHub CI, SHADOW, or LIVE activity was executed.

## Release-gate state

```text
Gate A — RESEARCH_READY = PASS / RESEARCH-INTEGRATION ONLY
Gate B — PAPER_READY    = BLOCKED / NOT YET PASS
Gate C — SHADOW_READY   = BLOCKED / UNCHANGED
Gate D — LIVE_READY     = BLOCKED / UNCHANGED

PAPER / SHADOW / LIVE   = UNAUTHORIZED
provider/private API    = NOT AUTHORIZED
project executable verification = NOT_RUN / NOT REQUIRED FOR STATIC CONTRACT DECISION
```

## Accepted prerequisite state

The protection chain through PR #44 is accepted statically, with executable evidence still NOT_RUN.

PR #45 is merged:

```text
merge = e18fc08d110b0addb77229b1bf47cd7632548427
head  = f8f85923a7dea0c47d7e5f1da46bc0c92a462368
```

PaperBroker protection Fill now retains exact:

```text
trade_plan_id
position_action_id
position_id
order_role = PROTECTION_STOP
```

This removes the prior protection Fill-lineage implementation gap.

## Close-to-TradeResult contract classification

```text
ADDITIVE_PROFILE_REQUIRED
```

The current baseline is directionally correct but does not define executable EXIT/EMERGENCY_EXIT payloads or final TradeResult closure/finance/idempotency semantics.

E7 materialized:

- `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`
  - `close-v0.1`
  - `trade-result-v0.1`
  - `linear-base-asset-pnl-v0.1`
- `docs/adr/ADR-0005-close-authority-and-trade-result-boundary.md`

Compatibility remains additive under:

```text
schema_version = contracts-v0.1
```

No existing entry/protection/quantity meaning is weakened.

## Authority / truth boundary

### E5 close authority

E5 alone produces executable:

```text
EXIT
EMERGENCY_EXIT
```

from exact current `CONSISTENT` Position truth.

Close quantity is exactly current positive `Position.actual_quantity`; it is not original requested quantity or provider-native size.

Ordinary EXIT is restricted to normal open states. EMERGENCY_EXIT requires E5 lifecycle state `EMERGENCY` first. Unknown/mismatch/reconciliation-required Position truth cannot produce guessed close authority.

### E4 mechanical close

V0.1 mapping:

```text
EXIT           -> POSITION_EXIT
EMERGENCY_EXIT -> EMERGENCY_EXIT
LONG            -> SELL
SHORT           -> BUY
order_type       = MARKET
reduce_only      = true
quantity         = exact E5-authorized actual open quantity
```

E4 validates/rejects but cannot choose a larger/different close quantity or invent exit reasons.

The logical order is idempotent on `(position_action_id, order_role)`.

### Flatness / lifecycle closure

A close action corresponds to E5 lifecycle intent `EXIT_REQUESTED`.

A request, submit acknowledgement, or `OrderStatus.FILLED` alone is not closure.

`POSITION_CLOSED` requires authoritative normalized Position truth:

```text
same position_id
actual_quantity = 0
reconciliation_status = CONSISTENT
broker_state_observed_at >= latest included exit Fill.filled_at
```

If order truth says FILLED while Position truth is nonzero/unknown/inconsistent, the system remains reconciliation-required.

Explicit partial close retains `EXIT_REQUESTED` while a consistent residual exists and the same close order remains active. A later new residual action requires fresh Position truth and a new PositionAction identity.

Protection-triggered full close also requires exact flat Position confirmation. Partial protection execution with residual exposure remains fail-closed/reconciliation-required under V0.1.

## Canonical TradeResult boundary

Final production boundary:

```text
E4 authoritative entry/exit Fill + Position truth
+ E5 lifecycle/risk/exit-reason authority
-> E5 trade-result-v0.1
-> E6 durable persistence/audit
```

Final closure evidence binds exact:

- strategy/version;
- plan/risk decision/risk policy;
- position ID;
- entry Fill IDs + entry OrderRequest IDs;
- exit Fill IDs + exit OrderRequest IDs;
- exit authority refs;
- deterministic E5 exit reason codes;
- final flat Position observation;
- fee/funding evidence.

Duplicate, incomplete, cross-plan, cross-position, wrong-side, under-close, over-close, or unreconciled evidence cannot produce final TradeResult.

Final full closure requires canonical quantity conservation:

```text
sum(entry Fill.quantity) = sum(exit Fill.quantity) = TradeResult.entry_quantity
```

## Financial semantics

`linear-base-asset-pnl-v0.1` aligns current Paper/live-compatible TradeResult math with accepted E3 replay semantics:

```text
LONG  gross_pnl = exit_notional - entry_notional
SHORT gross_pnl = entry_notional - exit_notional
net_pnl = gross_pnl - total_fees - funding_cost_effective
```

Actual Fill prices determine realized PnL. Optional analytical slippage is not subtracted again.

Missing fee evidence cannot be silently zero. Funding must be explicitly `ZERO_CONFIRMED` or `INCLUDED` with signed cost evidence.

`opened_at` = earliest authoritative entry Fill timestamp.

`closed_at` = authoritative flat Position observation timestamp.

TradeResult identity is deterministic over exact authority, Fill/order sets, flat observation, reasons and financial evidence.

## E6 persistence state

Current E6 remains early Slice 2 Registry persistence only:

```text
DRAFT -> BACKTESTING -> REJECTED | CANDIDATE
```

There is no Paper Position/PositionAction/OrderRequest/OrderResult/Fill/TradeResult durable runtime persistence or restart recovery yet.

Therefore:

```text
Restart/persistence preserves required state = BLOCKED / E6 IMPLEMENTATION_GAP
Paper E2E closes to TradeResult and persists audit = BLOCKED / IMPLEMENTATION_GAP
```

## Gate B evidence reconciliation

Unchanged executable states:

```text
Required protection follows actual filled quantity = NOT_RUN
Protection failure triggers emergency path          = NOT_RUN
Drawdown/daily/position/kill-switch                 = NOT_RUN
```

Still blocked:

```text
Restart/persistence                                 = BLOCKED
Paper E2E -> TradeResult + durable audit            = BLOCKED
```

Gate B remains BLOCKED and PAPER remains unauthorized.

## Safe sequential dependency order

E7 does not assign work. Recommended PM dependency order:

```text
1. E5 close-v0.1 producer + lifecycle/reason semantics
2. E4 close-v0.1 OrderRequest consumer + close Fill/residual Position truth
3. E5 authoritative-flat POSITION_CLOSED + trade-result-v0.1 builder
4. E6 Paper runtime persistence/restart/audit
5. E7 full Paper E2E/safety definitions
6. PM-authorized approved-local Gate B verification
```

Do not run downstream implementation concurrently when its consumed serialized shape depends on an unfinished upstream interface.

## Verification / compute / safety

```text
project executable verification = NOT_RUN / NOT REQUIRED FOR STATIC CONTRACT DECISION
provider/private requests        = NOT_SENT
exchange credentials             = NOT_USED
GitHub Actions / CI              = NOT_USED
hosted/GitHub-triggered compute  = NOT_USED
Local Runner                     = NOT_REQUESTED
Computer Adapter                 = NOT_USED
PAPER / SHADOW / LIVE            = UNAUTHORIZED
Registry real/live promotion     = NONE
E1-E6 production edits by E7     = NONE
Codex bug ticket                 = NONE
```

## Detailed evidence

`status/e7/GATE_B_CLOSE_TRADE_RESULT_CONTRACT_DECISION_20260824.md`

## Completion

E7-036 stops after persisting the bounded contract/profile, ADR, integration/release evidence, and terminal status. E7 does not self-start E5/E4 implementation, E6 persistence, full Paper E2E, approved-local verification, provider/private work, Gate C, PAPER, SHADOW, LIVE, or another task.
