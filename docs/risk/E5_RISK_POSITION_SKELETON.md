# E5 Risk / Position Skeleton

Status: **PRE-INTEGRATION SKELETON**  
Shared contract baseline: `contracts-v0.1`

## Scope

This slice prepares the E5-owned safety path:

```text
TradeIntent
  -> E5 validation / fail-closed risk gate
  -> RiskDecision
  -> ApprovedTradePlan
```

and the canonical position lifecycle state machine.

It does not claim E2->E5 or E5->E4 executable integration is complete.

## Policy model

`RiskPolicy` is explicit and versioned. Capital-risk values have no production defaults in code. A caller must supply every limit before E5 can approve an intent.

The skeleton gates:

- supported shared schema (`contracts-v0.1`);
- required TradeIntent fields and declared-field boundary;
- LONG/SHORT only;
- stale/future TradeIntent;
- stale/unknown market state;
- unknown account state;
- unknown position state;
- unknown order state;
- active kill switch;
- `new_exposure_allowed=false`;
- same-symbol existing exposure (position-add / averaging-down block);
- daily trade limit;
- simultaneous position limit;
- drawdown lock;
- consecutive-loss lock;
- missing sizing proposal;
- margin/notional/leverage caps;
- insufficient available balance;
- estimated transaction-cost cap;
- cost-adjusted minimum reward/risk;
- mandatory protective stop;
- explicit entry style for plan serialization.

A `RiskDecision=REJECT` cannot produce an `ApprovedTradePlan`.

## ApprovedTradePlan boundary

The top-level output fields match the canonical `contracts-v0.1` baseline.

`entry_instruction` and `protection_instruction` are deliberately minimal provisional E5 serializations of already-approved bounds. Their nested shape is **not declared a new shared contract**. E4/E7 must review the nested instruction mapping before execution integration treats it as stable.

## Fail-closed position lifecycle

Canonical states implemented:

- `PENDING_ENTRY`
- `OPEN_UNPROTECTED`
- `OPEN_PROTECTED`
- `PROFIT_PROTECTED`
- `EXIT_REQUESTED`
- `CLOSED`
- `EMERGENCY`
- `RECONCILIATION_REQUIRED`

Safety invariants:

1. `PENDING_ENTRY -> OPEN_PROTECTED` is not permitted directly.
2. An observed entry fill first becomes `OPEN_UNPROTECTED`.
3. Only explicit `PROTECTION_VERIFIED` may establish `OPEN_PROTECTED`.
4. Protection failure/loss enters `EMERGENCY`.
5. Unknown broker/position truth enters `RECONCILIATION_REQUIRED`.
6. Unknown state names/events fail closed.
7. Only `OPEN_PROTECTED` and `PROFIT_PROTECTED` may be described as safely open.
8. Under the current V1 one-position baseline, any lifecycle state other than `CLOSED` blocks new exposure.

## Deferred intentionally

The following are not claimed complete in this skeleton:

- E2 executable TradeIntent producer;
- position-sizing algorithm derived from account/equity/risk percentage;
- revenge-size comparison against historical/nominal size;
- stop-widening modification logic;
- break-even/trailing/structure-exit algorithms;
- E4 broker/protective-order executable integration;
- E6 risk-state persistence/restart implementation;
- kill-switch durable storage/reset authorization;
- final nested `entry_instruction` / `protection_instruction` shared semantics;
- PAPER/LIVE enablement.

## Local-only verification

Tests are definitions only until run on an approved local environment.

PowerShell from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/risk -p "test_*.py"
python -m unittest discover -s tests/position -p "test_*.py"
python -m unittest discover -s tests/safety -p "test_*.py"
```

GitHub Actions / CI / hosted runners must not be used.
