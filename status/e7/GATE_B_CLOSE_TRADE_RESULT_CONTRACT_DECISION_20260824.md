# Gate B Close-to-TradeResult Contract / Architecture Decision — E7-20260824-036

## Authority / scope

- task_id: `E7-20260824-036`
- target branch: `agent/e7-gate-b-close-trade-result-contract-20260824`
- reviewed main: `03f06827e9f4659f54afb20b43b0bfc806525b96`
- authoritative TASK blob: `17f791baea3ee95c8bc601ff9aa71d50a749607d`
- parent contract: `contracts-v0.1 / BASELINE`
- existing execution profiles: `entry-v0.1`, `base-asset-v0.1`, `protection-v0.1`
- accepted protection Fill-lineage PR: `#45 / merge e18fc08d110b0addb77229b1bf47cd7632548427 / head f8f85923a7dea0c47d7e5f1da46bc0c92a462368`
- project executable verification: `NOT_RUN / NOT REQUIRED FOR STATIC CONTRACT DECISION`

This task is static contract/architecture review only. E7 did not execute project code/tests, request Local Runner work, modify E1-E6 production code, call provider/private APIs, use credentials, or authorize PAPER/SHADOW/LIVE.

## Terminal contract classification

```text
CURRENT BASELINE CLASSIFICATION = ADDITIVE_PROFILE_REQUIRED
profile materialized = YES
set-wide schema bump = NO
schema_version = contracts-v0.1
shared contradiction = NONE FOUND
```

New canonical profile:

```text
contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md
close-v0.1
trade-result-v0.1
linear-base-asset-pnl-v0.1
```

Architecture decision:

```text
docs/adr/ADR-0005-close-authority-and-trade-result-boundary.md
```

## Why baseline alone is insufficient

The baseline already names:

- `PositionAction.EXIT`;
- `PositionAction.EMERGENCY_EXIT`;
- `POSITION_CLOSED`;
- canonical `TradeResult` fields;
- E4 broker-truth authority and E5 lifecycle authority.

But those names do not specify an executable close contract. Missing semantics included:

1. actual close quantity and exact Position observation binding;
2. parent plan/risk/strategy lineage on close actions;
3. action-specific freshness/expiry;
4. ordinary vs emergency close source lifecycle;
5. E4 close OrderRequest role/side/type/reduce-only/idempotency mapping;
6. when close/protection fills prove partial vs full closure;
7. requirement for authoritative flat Position truth before `POSITION_CLOSED`;
8. exact entry/exit fill-set and authority refs for one TradeResult;
9. fee/funding/slippage treatment and PnL currency/profile;
10. stable TradeResult identity/idempotency.

Those gaps are additive underspecification, not contradiction. Existing historical objects keep their original meaning and are not executable-finalization eligible unless the new profiles are declared.

## Accepted prerequisite review

### PR #45 protection Fill lineage

Current PaperBroker `record_fill()` now copies exact originating request lineage into every Fill:

```text
trade_plan_id
position_action_id
position_id
order_role
```

For protection Fill:

```text
order_role = PROTECTION_STOP
```

Entry/legacy fills retain their previous shape with protection-only optional fields unset.

This closes the prior smallest E4 lineage gap, but does not itself define position closure or TradeResult production.

### Existing E5 surface

Current E5 `src/position/` contains:

- protection action producer;
- protection-result interpreter;
- position state machine.

There is no accepted `EXIT` / `EMERGENCY_EXIT` producer or TradeResult builder yet. Therefore the new contract is a downstream implementation target, not a description of already implemented behavior.

### Existing E4 surface

Current E4 execution includes:

- entry gateway;
- protection translator;
- shared OrderRequest/OrderResult/Fill models;
- PaperBroker order/fill/reconciliation/terminal-state truth.

There is no accepted close-v0.1 PositionAction consumer yet.

### Existing E6 persistence

Current E6 storage remains early Slice 2 only:

```text
DRAFT -> BACKTESTING -> REJECTED | CANDIDATE
```

No Paper PositionAction/Order/Fill/TradeResult runtime persistence/restart/audit exists. This remains a Gate B implementation blocker.

## 1. Exit authority decision

E5 is the sole close authority.

### Ordinary exit

`close-v0.1 PositionAction.EXIT` may be produced only from exact current:

```text
OPEN_UNPROTECTED | OPEN_PROTECTED | PROFIT_PROTECTED
```

### Emergency exit

`close-v0.1 PositionAction.EMERGENCY_EXIT` may be produced only from:

```text
EMERGENCY
```

The emergency cause must already exist under E5 lifecycle semantics. E4 cannot create emergency authority.

### Required authority facts

The action binds:

- exact parent `trade_plan_id` / `risk_decision_id`;
- strategy ID/version;
- risk policy version;
- exact `position_id`, side, lifecycle state and Position observation timestamp;
- `reconciliation_status=CONSISTENT`;
- exact current positive `actual_quantity`;
- `base-asset-v0.1 / BASE_ASSET / BTC` quantity semantics;
- non-empty deterministic E5 reason codes;
- `close_order_type=MARKET`;
- action-specific expiry.

Close quantity is exactly current known open exposure, never original requested entry quantity or provider-native size.

Unknown/mismatch/reconciliation-required Position truth cannot produce an executable close under this profile.

## 2. E4 mechanical close decision

Provider-neutral V0.1 mapping:

```text
EXIT           -> order_role POSITION_EXIT
EMERGENCY_EXIT -> order_role EMERGENCY_EXIT
LONG            -> SELL
SHORT           -> BUY
order_type       = MARKET
reduce_only      = true
quantity         = exact E5-authorized current actual quantity
limit_price      = null
stop_price       = null
time_in_force     = null
```

Immediate authority lineage:

```text
authorization_type = POSITION_ACTION
position_action_id
position_id
risk_decision_id
trade_plan_id
```

Idempotency is bound to `(position_action_id, order_role)`.

E4 may validate/reject stale or inconsistent authority but cannot choose a different/larger quantity or invent exit reasons.

## 3. Lifecycle and flatness decision

Issuing a close action corresponds to E5's existing `EXIT_REQUESTED` lifecycle intent. A request or submit is not closure.

Definitive close-order failure while exposure remains uses:

```text
EXIT_REQUESTED + EXIT_FAILED -> EMERGENCY
```

### Flatness proof

`POSITION_CLOSED` requires authoritative E4 normalized Position truth:

```text
same position_id
actual_quantity = 0
reconciliation_status = CONSISTENT
broker_state_observed_at >= latest included exit Fill.filled_at
```

`OrderStatus.FILLED` alone is insufficient.

If a close order reports FILLED but position truth is nonzero/unknown/inconsistent, the state is reconciliation-required.

### Partial explicit close

A partial explicit close with known residual exposure does not create TradeResult. While the exact same logical order is active, lifecycle remains `EXIT_REQUESTED`.

If the close order terminates with residual exposure, E5 must re-observe the Position and apply failure/emergency policy before any new action. A new residual action uses fresh Position evidence and new action identity.

### Protection-triggered close

`PROTECTION_STOP` Fill can reduce/close the position under the existing PROTECT authority.

- partial protection Fill + residual exposure is not `POSITION_CLOSED`;
- current V0.1 remains fail-closed/reconciliation-required for residual protection after partial stop execution;
- full protection Fill still requires exact flat Position confirmation;
- once flat truth is proven, E5 may apply `POSITION_CLOSED` from protected states and finalize protection-stop exit reasons.

## 4. Double-count / evidence integrity decision

Final closure evidence must use stable Fill identities.

Every Fill may appear exactly once in the final entry/exit evidence sets. Duplicate `fill_id`, mixed plan/position/symbol, wrong side, unexplained quantity, or inconsistent order lineage blocks finalization.

Entry Fill binding is explicit through exact declared entry OrderRequest identity/identities and parent plan. Current entry-v0.1 fills may lack position_id, so trade_plan_id alone must never become a future heuristic for multiple position instances/reopens.

Exit fills must bind to the exact same `position_id` and one of:

```text
POSITION_EXIT
EMERGENCY_EXIT
PROTECTION_STOP
```

Final full closure requires:

```text
sum(entry quantity) = sum(exit quantity) = TradeResult.entry_quantity
```

plus authoritative zero broker exposure.

## 5. Canonical TradeResult decision

Final producer boundary:

```text
E4 authoritative Fill/Position truth
+ E5 lifecycle/risk authority
-> E5 canonical trade-result-v0.1
-> E6 durable persistence
```

E5 is the final object producer because it owns `POSITION_CLOSED` and exit reason semantics, but it may only aggregate/validate E4-authoritative execution facts. E6 does not construct/reinterpret the result.

Additional result bindings include:

- `risk_decision_id` and `risk_policy_version`;
- symbol/direction and canonical quantity profile;
- `pnl_currency=USDT`;
- exact entry/exit Fill ID lists;
- exact entry/exit OrderRequest ID lists;
- exact exit authority refs (`EXIT`, `EMERGENCY_EXIT`, or `PROTECT`);
- exact flat-position observation time;
- funding evidence status.

`closed_at` equals the authoritative flat Position observation timestamp. `opened_at` comes from the earliest authoritative entry Fill.

## 6. Financial profile decision

Profile:

```text
linear-base-asset-pnl-v0.1
```

It intentionally aligns with existing E3 replay semantics for current BTC/USDT linear base-asset quantity.

For all included entry/exit Fill facts:

```text
entry_notional = Σ(entry_qty * entry_price)
exit_notional  = Σ(exit_qty * exit_price)
```

Final quantity conservation is required.

Then:

```text
LONG  gross_pnl = exit_notional - entry_notional
SHORT gross_pnl = entry_notional - exit_notional
net_pnl = gross_pnl - total_fees - funding_cost_effective
```

Weighted average entry/exit prices derive from actual Fill facts.

### Fee semantics

Finalization requires explicit fee evidence for every included Fill. Missing fee evidence is not silently zero. Nonzero fees must be in USDT or normalized under a separately accepted conversion profile. Positive fees are costs; negative fees are rebates/credits.

### Funding semantics

`funding_evidence_status` is required:

```text
ZERO_CONFIRMED | INCLUDED
```

`INCLUDED` requires signed `funding_cost` evidence for the exact position interval. Positive means cost, negative means credit. `ZERO_CONFIRMED` permits zero/omitted funding only because zero/not-applicable is explicitly established.

### Slippage semantics

Actual Fill prices already contain realized execution price impact. Optional `slippage_cost` is analytical context only and is not subtracted again from net PnL. Populating it requires an explicit versioned reference-price method.

### R multiple

Optional only when exact E5 initial-risk denominator evidence exists. It must not be guessed.

## 7. TradeResult idempotency decision

`trade_result_id` is deterministic over exact strategy/plan/risk/position authority, ordered Fill IDs, order IDs, exit authority refs, flat observation, reason codes and financial evidence.

Same evidence -> same ID.

Changed/conflicting evidence -> different candidate identity and must not silently overwrite the durable result.

E6 must later enforce one non-conflicting canonical final result for an exact closed position/trade lineage.

## 8. Safe sequential dependency order

E7 does not assign work. The safe PM dependency order is:

```text
1. E5 close-action producer + EXIT_REQUESTED/EXIT_FAILED/reason semantics
2. E4 close-v0.1 OrderRequest consumer + close Fill/residual Position truth
3. E5 POSITION_CLOSED + trade-result-v0.1 builder
4. E6 Paper runtime persistence/restart/audit
5. E7 full Paper E2E/safety definitions
6. PM-authorized approved-local Gate B verification
```

Do not run E4 and E5 producer-interface work concurrently when E4's consumer shape depends on E5's accepted serialized action.

## 9. Gate B reconciliation

No executable status is upgraded by this architecture decision.

```text
Required protection follows actual filled quantity = NOT_RUN
Protection failure triggers emergency path = NOT_RUN
Drawdown/daily/position/kill-switch = NOT_RUN
Restart/persistence preserves required state = BLOCKED / E6 IMPLEMENTATION_GAP
Paper E2E closes to TradeResult and persists audit = BLOCKED / IMPLEMENTATION_GAP
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

The prior protection Fill-lineage implementation gap is resolved by merged PR #45. The remaining Paper E2E/TradeResult blocker is now decomposed into the sequential E5 close authority -> E4 close consumer -> E5 final result -> E6 persistence chain above.

## 10. Verification / security

```text
project executable verification = NOT_RUN / NOT REQUIRED FOR STATIC CONTRACT DECISION
Local Runner = NOT_REQUESTED
GitHub Actions / CI / hosted runner = NOT_USED
GitHub-triggered project compute = NOT_USED
Computer Adapter = NOT_USED
provider/private requests = NOT_SENT
exchange credentials = NOT_USED
PAPER / SHADOW / LIVE = UNAUTHORIZED
E1-E6 production edits by E7 = NONE
Codex ticket = NONE
```

## Completion

E7 completes only `E7-20260824-036` after persisting the contract/profile, ADR, release/integration evidence and terminal STATUS. E7 does not self-start E5/E4 implementation, E6 persistence, full Paper E2E, approved-local verification, provider/private work, Gate C, PAPER, SHADOW, or LIVE.
