# ADR-0005 — Close Authority, Flatness, and TradeResult Boundary

- Status: `ACCEPTED`
- Date: `2026-08-24`
- Decision task: `E7-20260824-036`
- Authority: E7 Integration / Architecture / System QA / Release Engineer
- Parent contract: `contracts-v0.1`
- Profiles: `close-v0.1`, `trade-result-v0.1`, `linear-base-asset-pnl-v0.1`
- Canonical profile: `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`

## Context

Gate B now has accepted provider-neutral entry, protection, protection-failure, and protection Fill-lineage primitives. PR #45 materializes exact protection PositionAction/Position/order-role lineage into PaperBroker Fill truth.

The next Slice 3 boundary is not safe to implement from baseline enum names alone. The parent contract names `PositionAction.EXIT`, `PositionAction.EMERGENCY_EXIT`, `POSITION_CLOSED`, and `TradeResult`, but does not define:

- executable close quantity/lineage/freshness payload;
- E4 close-order mapping and order-role vocabulary;
- how partial vs full close is proven from broker Position truth;
- how protection-triggered fills close a position;
- exact entry/exit Fill sets required for one TradeResult;
- PnL/cost semantics and currency;
- stable final-result identity/idempotency.

Allowing domain implementations to fill these gaps independently would let E4 invent exit authority, let E5/E6 infer broker flatness, or create incompatible PnL/audit semantics.

## Decision

Classify the baseline as:

```text
ADDITIVE_PROFILE_REQUIRED
```

and introduce compatible profile refinements under unchanged:

```text
schema_version = contracts-v0.1
```

The normative field/formula definitions live in `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`.

## 1. Authority separation remains strict

- E4 owns actual order/fill/exposure truth.
- E5 owns exit/emergency authority, lifecycle interpretation, exit reasons, and final TradeResult production from E4 truth.
- E6 owns persistence/restart/audit only.
- E7 owns the shared semantics and integration/release definitions.

No module may infer another module's authority from convenient local state.

## 2. Close authority is an E5 PositionAction

`close-v0.1` makes only:

```text
EXIT
EMERGENCY_EXIT
```

executable.

The action must bind exact parent plan/risk/strategy lineage, exact current `CONSISTENT` Position observation, actual open quantity in canonical base-asset units, deterministic E5 reason codes, source lifecycle state, and its own expiry.

Ordinary `EXIT` is allowed only from normal open states. `EMERGENCY_EXIT` is allowed only after E5 lifecycle authority has entered `EMERGENCY`.

Unknown/unreconciled Position truth cannot produce a guessed close quantity.

## 3. Close quantity is exact current exposure

For both ordinary and emergency close:

```text
close quantity = exact current Position.actual_quantity
```

It is never copied from original requested entry size or provider-native contract counts.

This prevents E4 from increasing exposure or closing more than E5 authorized.

## 4. E4 close translation is mechanical

For `close-v0.1`:

```text
LONG  -> SELL
SHORT -> BUY
order_type = MARKET
reduce_only = true
```

Provider-neutral roles are:

```text
POSITION_EXIT
EMERGENCY_EXIT
```

Immediate authority remains the exact `position_action_id`; parent lineage remains `trade_plan_id` / `risk_decision_id` / `position_id`.

The logical order identity is deterministic from `(position_action_id, order_role)`.

E4 may reject stale/mismatched authority but may not alter quantity or reasons.

## 5. EXIT_REQUESTED is not CLOSED

Issuing an E5 close action creates/associates the existing lifecycle intent `EXIT_REQUESTED`.

A prepared request, submit acknowledgement, or `OrderStatus.FILLED` does not alone prove a flat position.

Definitive close-order failure with remaining exposure uses existing:

```text
EXIT_REQUESTED + EXIT_FAILED -> EMERGENCY
```

Any later emergency close requires fresh Position truth and fresh E5 authority.

## 6. Flatness requires authoritative Position truth

`POSITION_CLOSED` requires an E4-normalized Position observation with:

```text
same position_id
actual_quantity = 0
reconciliation_status = CONSISTENT
observation time >= latest close Fill
```

A FILLED order plus nonzero/unknown/mismatched Position truth is reconciliation-required, not closed.

For explicit close partial fills, lifecycle remains `EXIT_REQUESTED` while exact residual exposure exists and the close order is active.

For a protection stop, full Fill may close the position only after the same authoritative flat-position proof. Partial protection execution with residual exposure remains fail closed/reconciliation-required until residual-protection semantics are separately proven.

## 7. TradeResult requires a closed evidence set

`trade-result-v0.1` requires exact:

- strategy/version, plan, risk decision and risk policy;
- one position ID;
- entry Fill set and entry request identities;
- exit Fill set and exit request identities;
- E5 immediate exit/protection authority refs;
- deterministic E5 exit reasons;
- final flat Position observation;
- quantity/cost evidence.

Duplicate, ambiguous, mixed-plan, cross-position, unreconciled, incomplete, under-close or over-close evidence cannot produce a final result.

For final closure, canonical entry quantity must equal total canonical exit quantity.

## 8. Financial semantics are explicitly versioned

Use:

```text
linear-base-asset-pnl-v0.1
```

for the current `BTC_USDT_PERP / base-asset-v0.1` path.

The profile aligns with existing E3 replay semantics:

```text
LONG gross  = exit_notional - entry_notional
SHORT gross = entry_notional - exit_notional
net         = gross - total_fees - funding_cost
```

where actual Fill prices are used.

Because Fill prices already reflect realized execution, optional analytical `slippage_cost` is not subtracted again from net PnL.

Missing fee evidence is not silently zero. Funding must be either explicitly included from versioned evidence or explicitly confirmed zero/not applicable.

## 9. TradeResult time and identity

`opened_at` comes from the earliest authoritative entry Fill.

`closed_at` equals the authoritative flat Position observation time, not merely the last Fill timestamp.

`trade_result_id` is deterministic over exact closure authority, Fill IDs, order IDs, risk lineage, close observation, exit reasons and financial evidence. Reprocessing identical evidence is idempotent; conflicting evidence must not overwrite a durable result.

## 10. Production boundary

E5 is the final canonical TradeResult producer, but only as the lifecycle authority consuming E4-authoritative facts under the shared profile. This preserves the baseline description "integrated E4/E5 close path":

```text
E4 broker truth
+ E5 lifecycle/risk authority
-> E5 final canonical TradeResult
-> E6 durable persistence
```

E5 may aggregate/validate E4 Fill/Position facts but may not manufacture them.

## 11. Sequential implementation order

The interfaces are dependency-ordered and should not be implemented concurrently when downstream shape depends on upstream shape:

1. E5 close-action producer + lifecycle/reason semantics.
2. E4 close-order consumer + close Fill/residual Position truth.
3. E5 final closure + TradeResult builder.
4. E6 durable Paper runtime persistence/restart/audit.
5. E7 Paper E2E/safety definitions.
6. approved-local Gate B verification.

## Compatibility decision

No set-wide schema bump is required. The parent already names all relevant object families and authority direction; the missing semantics were executable-profile gaps. New fields/profile IDs are additive, legacy objects retain historical/audit meaning, and consumers requiring executable close/final TradeResult semantics fail closed without the profiles.

If a later implementation proves that multiple reopens under one `trade_plan_id`, non-linear/inverse contracts, non-USDT fees, or additional cost accounting cannot preserve these meanings additively, it must return to E7 for a new profile/version rather than silently extending V0.1.

## Rejected alternatives

### Let E4 issue a close from Position truth without E5 action

Rejected: broker truth is not risk/exit authority.

### Use original ApprovedTradePlan quantity as close size

Rejected: actual exposure may differ because of partial entry/exit fills.

### Treat FILLED close order as flat position

Rejected: order completion and account/position truth can disagree.

### Let E6 construct TradeResult from persisted rows

Rejected: persistence is not lifecycle authority and must not invent exit reasons or broker truth.

### Infer missing fees as zero

Rejected: a required financial metric cannot be finalized from missing cost evidence.

### Subtract slippage cost from fill-based realized PnL again

Rejected: actual Fill prices already incorporate realized execution price; double subtraction would distort net PnL.

## Verification

This is a static contract/architecture decision.

```text
project executable verification = NOT_RUN / NOT REQUIRED FOR STATIC CONTRACT DECISION
```

No Local Runner, project-code execution, GitHub Actions/CI, hosted runner, provider/private API, credential, PAPER, SHADOW, or LIVE activity was used.

## Release impact

```text
close-to-TradeResult shared semantic blocker = RESOLVED BY CONTRACT PROFILE
Required protection follows actual filled quantity = NOT_RUN
Protection failure triggers emergency path = NOT_RUN
Drawdown/daily/position/kill-switch = NOT_RUN
Restart/persistence = BLOCKED
Paper E2E / TradeResult durable audit = BLOCKED pending E5/E4/E5/E6 implementation + E7 definitions + local evidence
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```
