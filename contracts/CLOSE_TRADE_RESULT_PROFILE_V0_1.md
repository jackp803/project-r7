# Canonical Close and TradeResult Object Profile — V0.1

> Parent contract set: `contracts-v0.1`  
> Profile identifiers: `close-v0.1`, `trade-result-v0.1`, `linear-base-asset-pnl-v0.1`  
> Profile status: `BASELINE`  
> Technical authority: E7 Integration / Architecture / System QA / Release Engineer  
> Decision task: `E7-20260824-036`

## 1. Purpose

The parent baseline already defines:

- E5 `PositionAction` actions `EXIT` and `EMERGENCY_EXIT`;
- E4 authority over broker order/fill/exposure truth;
- E5 authority over position lifecycle/risk interpretation;
- `POSITION_CLOSED` lifecycle vocabulary;
- canonical `TradeResult` output fields;
- `base-asset-v0.1` quantity semantics;
- `protection-v0.1` PositionAction/OrderRequest/Fill immediate-authority lineage.

It does not define enough executable semantics to safely implement:

```text
known open Position
-> E5 EXIT / EMERGENCY_EXIT authority
-> E4 reduce-only close OrderRequest
-> authoritative close Fill(s) + flat Position truth
-> E5 POSITION_CLOSED lifecycle interpretation
-> canonical TradeResult
```

This profile resolves that bounded underspecification. It does not authorize PAPER, SHADOW, LIVE, provider/private APIs, credentials, capital exposure, or release-gate advancement.

## 2. Compatibility and versioning decision

Classification:

```text
ADDITIVE_PROFILE_REQUIRED
```

The parent remains:

```text
schema_version = contracts-v0.1
```

No set-wide major version bump is required because:

1. the parent already permits E5-authorized PositionActions to reach E4 but never defined executable payloads for `EXIT` / `EMERGENCY_EXIT`;
2. the parent already defines `TradeResult` but does not define fill-set closure proofs, PnL/cost formulas, immediate close-authority references, or idempotency material;
3. all new profile identifiers/fields are additive;
4. existing historical/research/audit objects retain their original meaning;
5. legacy objects without the declared profiles are not executable-close/final-TradeResult eligible and fail closed rather than being guessed or rewritten;
6. existing entry/protection/quantity semantics are not weakened or reinterpreted.

## 3. Supported close actions

`close-v0.1` supports exactly:

```text
PositionAction.action = EXIT | EMERGENCY_EXIT
```

The two actions remain distinct and auditable.

### 3.1 Ordinary EXIT

An executable ordinary `EXIT` may be produced only from a known current Position whose lifecycle state is one of:

```text
OPEN_UNPROTECTED
OPEN_PROTECTED
PROFIT_PROTECTED
```

### 3.2 EMERGENCY_EXIT

An executable `EMERGENCY_EXIT` may be produced only from:

```text
EMERGENCY
```

A risk/lifecycle cause must first place the position in `EMERGENCY` under E5-owned semantics; `EMERGENCY_EXIT` is not a shortcut for inventing emergency state inside E4.

### 3.3 Unsupported states

`CLOSED`, `PENDING_ENTRY`, `EXIT_REQUESTED`, `RECONCILIATION_REQUIRED`, unknown states, or an unrecognized lifecycle value cannot produce a fresh `close-v0.1` action.

Repeated delivery of the same already-issued action is handled idempotently by identity. A new close action requires a new authoritative Position observation.

## 4. Source of close quantity and position truth

E4 remains authoritative for actual broker exposure truth. E5 may produce a close action only from an exact normalized Position observation satisfying all of:

- `schema_version = contracts-v0.1`;
- exact `position_id` and canonical `symbol`;
- side `LONG | SHORT`;
- `reconciliation_status = CONSISTENT`;
- positive finite `actual_quantity`;
- `quantity_profile_version = base-asset-v0.1`;
- `quantity_unit = BASE_ASSET`;
- canonical base asset; for `BTC_USDT_PERP`, `BTC`;
- exact `broker_state_observed_at` in RFC 3339 UTC;
- lifecycle state allowed by section 3;
- position/plan symbol, direction and quantity profile are mutually compatible;
- current actual quantity does not exceed the parent ApprovedTradePlan maximum approved quantity.

For `close-v0.1`:

```text
PositionAction.quantity = exact Position.actual_quantity
```

It is not the original entry requested quantity, plan maximum, or a provider-native contract count.

Unknown, mismatched, stale/unverifiable, `UNKNOWN`, `MISMATCH`, or `RECONCILIATION_REQUIRED` position truth cannot produce ordinary or emergency executable close authority under this profile. Such states remain in reconciliation/emergency policy handling; E4 must not guess exposure and E5 must not fabricate a quantity.

## 5. `PositionAction` close profile

### 5.1 Parent fields retained

Parent required fields remain required:

- `schema_version`
- `position_action_id`
- `position_id`
- `action`
- `reason_codes`
- `risk_policy_version`
- `created_at`

### 5.2 Additional required fields for `close-v0.1`

An executable `EXIT` or `EMERGENCY_EXIT` additionally requires:

- `close_profile_version` — exactly `close-v0.1`
- `trade_plan_id` — exact parent ApprovedTradePlan
- `risk_decision_id` — exact parent RiskDecision lineage
- `strategy_id`
- `strategy_version`
- `symbol`
- `position_side` — `LONG | SHORT`
- `source_lifecycle_state`
- `position_observed_at` — exact source Position `broker_state_observed_at`
- `position_reconciliation_status` — exactly `CONSISTENT`
- `quantity` — exact canonical current open exposure to close
- `quantity_profile_version` — V0.1 `base-asset-v0.1`
- `quantity_unit` — V0.1 `BASE_ASSET`
- `quantity_asset` — for `BTC_USDT_PERP`, `BTC`
- `close_order_type` — exactly `MARKET`
- `expires_at` — close-action-specific RFC 3339 UTC expiry later than `created_at`

`reason_codes` must be a non-empty deterministic E5-owned sequence. E4 may validate presence/shape but may not invent, replace, or broaden the reasons.

### 5.3 Lineage invariants

The close action must bind exactly to the parent plan:

```text
PositionAction.trade_plan_id       == ApprovedTradePlan.trade_plan_id
PositionAction.risk_decision_id    == ApprovedTradePlan.risk_decision_id
PositionAction.strategy_id         == ApprovedTradePlan.strategy_id
PositionAction.strategy_version    == ApprovedTradePlan.strategy_version
PositionAction.risk_policy_version == ApprovedTradePlan.risk_policy_version
PositionAction.symbol              == ApprovedTradePlan.symbol
```

and to the exact source Position observation:

```text
position_id
position_side
source_lifecycle_state
position_observed_at
position_reconciliation_status
quantity
quantity profile/unit/asset
```

The parent entry-plan TTL is immutable lineage only after exposure exists. It must not be reused as the lifetime of a close action. `expires_at` on the PositionAction is the close authority freshness boundary.

### 5.4 Action identity

`position_action_id` must be deterministic for one logical close authorization and must change when any authority-bearing material changes, including at minimum:

- action `EXIT` vs `EMERGENCY_EXIT`;
- parent plan/risk decision;
- position ID/side/source lifecycle state;
- Position observation timestamp;
- close quantity/profile/unit/asset;
- reason codes;
- risk policy version.

A newer Position observation, residual quantity, changed emergency reason, or other authority change therefore requires a new PositionAction identity.

## 6. E5 lifecycle semantics for explicit close

Issuing an executable close action is E5-owned lifecycle intent. The future E5 producer must atomically/durably associate the action with the lifecycle event:

```text
EXIT_REQUESTED
```

under the existing state machine:

```text
OPEN_UNPROTECTED / OPEN_PROTECTED / PROFIT_PROTECTED + EXIT_REQUESTED -> EXIT_REQUESTED
EMERGENCY + EXIT_REQUESTED -> EXIT_REQUESTED
```

A prepared or submitted order does not mean the position is closed.

Definitive close-order failure while exposure remains must follow the existing fail-closed lifecycle:

```text
EXIT_REQUESTED + EXIT_FAILED -> EMERGENCY
```

A fresh subsequent emergency close requires a new authoritative Position observation and new E5 `EMERGENCY_EXIT` action.

## 7. E4 mechanical close translation

E4 consumes:

```text
close-v0.1 PositionAction
+ exact parent ApprovedTradePlan
+ exact current normalized Position observation
```

E4 must reject unless all lineage, action freshness, source lifecycle, position observation, quantity/profile/unit/asset and current reconciliation truth match exactly.

E4 validates; it does not choose a larger/different close quantity or invent an exit reason.

### 7.1 Order-role vocabulary

V0.1 adds provider-neutral order roles:

```text
POSITION_EXIT
EMERGENCY_EXIT
```

Existing:

```text
PROTECTION_STOP
```

remains the protection-triggered close role.

### 7.2 Deterministic mapping

For ordinary `EXIT`:

```text
authorization_type = POSITION_ACTION
order_role          = POSITION_EXIT
order_type          = MARKET
reduce_only         = true
```

For `EMERGENCY_EXIT`:

```text
authorization_type = POSITION_ACTION
order_role          = EMERGENCY_EXIT
order_type          = MARKET
reduce_only         = true
```

Side mapping:

```text
LONG position  -> SELL
SHORT position -> BUY
```

Quantity mapping:

```text
OrderRequest.quantity = exact PositionAction.quantity = exact current Position.actual_quantity
```

The request carries exact immediate and parent lineage:

- `trade_plan_id`
- `position_action_id`
- `position_id`
- `risk_decision_id`
- canonical quantity profile/unit/asset.

V0.1 close requests require:

```text
limit_price   = null
stop_price    = null
time_in_force = null
```

Provider-native IDs, contract counts, trigger fields and credentials remain adapter facts and are forbidden from the shared close authority.

### 7.3 Idempotency

The close `client_order_id` must be stable for:

```text
(position_action_id, order_role)
```

or an equivalently collision-resistant deterministic identity. Replaying the same action cannot create a second logical close order. A materially changed action must yield a new logical order identity.

### 7.4 No exposure increase

E4/broker implementations must preserve all of:

- opposite side to the current position;
- `reduce_only = true`;
- requested canonical quantity no greater than the exact E5-authorized current exposure;
- no provider translation that can increase absolute exposure.

If an adapter cannot represent the full canonical close quantity exactly, it may not report full closure. Any residual must return through normalized broker/Position truth for E5 reconciliation/new authority.

## 8. Close Fill lineage

A Fill produced from a `close-v0.1` OrderRequest must retain:

- parent `trade_plan_id`;
- exact `position_action_id`;
- exact `position_id`;
- exact `order_role = POSITION_EXIT | EMERGENCY_EXIT`;
- actual `side`, `quantity`, `price`, `filled_at`;
- fee/liquidity facts when known;
- canonical quantity profile semantics from the originating request.

Existing `protection-v0.1` Fill lineage remains:

```text
position_action_id
position_id
order_role = PROTECTION_STOP
```

A stable `fill_id` must make duplicate Fill evidence detectable. A final closure evidence set may include each `fill_id` exactly once.

## 9. Position closure truth

### 9.1 Order status is insufficient by itself

`OrderResult.order_status = FILLED` is not proof that a position is flat.

`POSITION_CLOSED` is allowed only when E4 supplies a later/current normalized Position observation satisfying:

```text
same position_id
same symbol
actual_quantity = 0
reconciliation_status = CONSISTENT
broker_state_observed_at >= latest included exit Fill.filled_at
```

If current broker position truth is unknown, mismatched, unreconciled, or nonzero, E5 must not apply `POSITION_CLOSED`.

### 9.2 Explicit EXIT / EMERGENCY_EXIT partial close

If a close order is only partially filled and exact current Position truth remains positive and `CONSISTENT`:

- the position is not closed;
- lifecycle remains `EXIT_REQUESTED` while the same logical close order remains active;
- E5 does not create a TradeResult;
- the same Fill is not counted twice on later observations.

If the close order becomes definitively inactive while residual exposure remains, E5 must re-observe the Position and apply the appropriate failure/emergency policy before issuing any new action. A residual close action uses a new Position observation and new PositionAction identity.

If a close OrderResult says `FILLED` but authoritative Position truth remains nonzero or inconsistent, the state is reconciliation-required, not closed.

### 9.3 Protection-triggered close

A `PROTECTION_STOP` Fill may reduce or fully close the position without a separate `EXIT` PositionAction.

- partial protection Fill + residual exposure does not imply `POSITION_CLOSED`;
- until residual-protection semantics are explicitly proven, partial protection execution with residual exposure is fail-closed/reconciliation-required;
- full protection Fill still requires authoritative flat Position truth before `POSITION_CLOSED`;
- once exact flat truth is established, E5 may apply existing `POSITION_CLOSED` from `OPEN_PROTECTED` / `PROFIT_PROTECTED` and produce deterministic protection-stop exit reasons.

## 10. Canonical closure evidence set

A final TradeResult may be constructed only from one coherent immutable closure evidence set containing at minimum:

1. exact parent ApprovedTradePlan;
2. exact `position_id` and direction;
3. authoritative entry Fill set;
4. authoritative exit Fill set;
5. exact entry OrderRequest identity/identities used by those entry fills;
6. exact exit OrderRequest identity/identities used by those exit fills;
7. E5 close authority/lifecycle reason evidence;
8. authoritative final flat Position observation;
9. risk policy/version lineage;
10. any included funding/cost evidence required by section 12.

The assembler must reject incomplete, ambiguous, duplicated, cross-position, cross-plan, mixed-symbol, wrong-side, unreconciled, or internally inconsistent evidence.

### 10.1 Entry Fill binding

Current entry-v0.1 Fill objects may not carry `position_id`. They are eligible only when the closure evidence explicitly binds them to the exact declared entry OrderRequest(s) and parent `trade_plan_id` for this one position instance.

A `trade_plan_id` match alone must not become a future heuristic for multiple reopens/positions. If the system later supports multiple position instances under one plan, the entry Fill/position binding must be strengthened before this profile can be used unchanged.

### 10.2 Exit Fill eligibility

Every exit Fill must bind to the same `position_id` and exact parent `trade_plan_id` and come from one of:

```text
order_role = POSITION_EXIT
order_role = EMERGENCY_EXIT
order_role = PROTECTION_STOP
```

with side opposite the parent position direction.

### 10.3 Quantity conservation

For final full closure:

```text
sum(entry Fill.quantity) = sum(exit Fill.quantity) = TradeResult.entry_quantity
```

under the same canonical `base-asset-v0.1 / BASE_ASSET / BTC` semantics.

Any over-close, under-close, duplicate fill, unexplained quantity, or residual broker exposure blocks final TradeResult production.

## 11. `TradeResult` profile

### 11.1 Parent required fields retained

The baseline required fields remain required:

- `schema_version`
- `trade_result_id`
- `strategy_id`
- `strategy_version`
- `trade_plan_id`
- `position_id`
- `opened_at`
- `closed_at`
- `entry_quantity`
- `average_entry_price`
- `average_exit_price`
- `gross_pnl`
- `net_pnl`
- `total_fees`
- `exit_reason_codes`

### 11.2 Additional required fields for `trade-result-v0.1`

- `trade_result_profile_version` — exactly `trade-result-v0.1`
- `pnl_profile_version` — exactly `linear-base-asset-pnl-v0.1`
- `risk_decision_id`
- `risk_policy_version`
- `symbol`
- `direction` — `LONG | SHORT`
- `quantity_profile_version` — `base-asset-v0.1`
- `quantity_unit` — `BASE_ASSET`
- `quantity_asset` — for current BTC perpetual, `BTC`
- `pnl_currency` — current profile `USDT`
- `entry_fill_ids` — non-empty deterministic ordered list
- `exit_fill_ids` — non-empty deterministic ordered list
- `entry_order_request_ids` — non-empty deterministic ordered list
- `exit_order_request_ids` — non-empty deterministic ordered list
- `exit_authority_refs` — non-empty deterministic list of immediate E5 authority references used by the exit path
- `flat_position_observed_at` — exact authoritative E4 normalized flat Position observation timestamp; must equal `closed_at`
- `funding_evidence_status` — `ZERO_CONFIRMED | INCLUDED`

Each `exit_authority_refs` element contains:

```text
position_action_id
position_id
action          = EXIT | EMERGENCY_EXIT | PROTECT
order_role      = POSITION_EXIT | EMERGENCY_EXIT | PROTECTION_STOP
```

For protection-triggered closure, `action=PROTECT` references the exact protection PositionAction that authorized the stop order.

`exit_reason_codes` are E5-owned deterministic closure reasons. The TradeResult assembler copies/normalizes the exact E5-authoritative reason set; E4 and E6 must not invent reasons.

## 12. Financial semantics — `linear-base-asset-pnl-v0.1`

This profile is intentionally limited to the current canonical linear BTC/USDT perpetual quantity semantics and aligns with the existing E3 replay financial semantics.

Let all quantities/prices be Decimal values in canonical base quantity / USDT price units.

Define:

```text
entry_qty      = sum(entry_fill.quantity)
exit_qty       = sum(exit_fill.quantity)
entry_notional = sum(entry_fill.quantity * entry_fill.price)
exit_notional  = sum(exit_fill.quantity * exit_fill.price)
```

Final closure requires:

```text
entry_qty > 0
entry_qty == exit_qty
```

Then:

```text
average_entry_price = entry_notional / entry_qty
average_exit_price  = exit_notional / exit_qty
entry_quantity      = entry_qty
```

Gross realized PnL:

```text
LONG:  gross_pnl = exit_notional - entry_notional
SHORT: gross_pnl = entry_notional - exit_notional
```

### 12.1 Fees

`total_fees` is the Decimal sum of all entry and exit Fill fees included in the result.

For V0.1 finalization:

- every included Fill fee must be known explicitly;
- all non-zero fees must be denominated in `pnl_currency=USDT` or already normalized by a separately accepted cost-conversion profile;
- positive fee = cost; negative fee = rebate/credit;
- missing/ambiguous fee evidence blocks final TradeResult rather than being silently treated as zero.

### 12.2 Funding

`funding_cost` remains an optional baseline field but has explicit signed-cost semantics when included:

```text
positive funding_cost = cost
negative funding_cost = funding credit
```

If `funding_evidence_status = INCLUDED`, `funding_cost` is required and must come from authoritative/versioned Paper/provider funding allocation evidence for this exact position interval.

If `funding_evidence_status = ZERO_CONFIRMED`, `funding_cost` may be omitted or exactly zero only because the integrated Paper/provider evidence explicitly confirms zero/not-applicable funding for the interval. Absence without that status is not zero evidence.

### 12.3 Net PnL

```text
net_pnl = gross_pnl - total_fees - funding_cost_effective
```

where `funding_cost_effective = funding_cost` for `INCLUDED`, otherwise zero for `ZERO_CONFIRMED`.

This matches existing E3 replay cost-sign convention.

### 12.4 Slippage

Actual Fill prices already determine realized gross PnL, so slippage must not be subtracted a second time from `net_pnl`.

The optional baseline `slippage_cost` is analytical/audit context relative to an explicit reference-price profile. It may be populated only when a versioned slippage-reference method and source observations exist. It is not an additional net-PnL deduction under `linear-base-asset-pnl-v0.1`.

### 12.5 R multiple

`r_multiple` remains optional and cannot be guessed. It may be produced only when the exact initial E5 risk denominator/maximum-loss evidence and its versioned semantics are available.

## 13. Time semantics

For `trade-result-v0.1`:

```text
opened_at = earliest authoritative entry Fill.filled_at included in the position evidence
closed_at = flat_position_observed_at
```

`closed_at` must be at or after the latest included exit Fill timestamp. It records authoritative flat-position confirmation rather than assuming the last Fill timestamp alone proves flatness.

If any persisted Position `opened_at`/`closed_at` conflicts with the authoritative Fill/flat-observation evidence, finalization fails closed.

## 14. Exit reason semantics

The final E5 implementation must create deterministic reason codes from exact lifecycle authority:

- explicit ordinary exit: exact E5 `EXIT` action reason codes;
- explicit emergency exit: exact E5 `EMERGENCY_EXIT` action reason codes, preserving emergency distinction;
- protection-triggered closure: must include canonical `PROTECTION_STOP_FILLED` plus any stable E5 policy reason codes required for the exact protection/lifecycle cause.

E4 supplies Fill/order facts but does not choose these reason codes. E6 persists them but does not reinterpret them.

## 15. TradeResult identity / idempotency

`trade_result_id` must be deterministic over all closure-authority and financial material, including at minimum:

- `trade_result_profile_version` / `pnl_profile_version`;
- strategy ID/version;
- trade plan / risk decision / risk policy;
- position ID, symbol, direction;
- canonical ordered `entry_fill_ids`;
- canonical ordered `exit_fill_ids`;
- canonical ordered entry/exit OrderRequest IDs;
- canonical `exit_authority_refs`;
- `flat_position_observed_at`;
- exit reason codes;
- fee/funding evidence material affecting financial values.

Canonical Fill ordering is by `(filled_at, fill_id)` unless a later profile defines a stronger broker sequence.

Reprocessing the exact same evidence produces the same TradeResult identity. Changed evidence produces a different candidate identity and must not overwrite an already durable result silently.

E6 durable storage must ultimately enforce one non-conflicting final result for the exact closed position/trade lineage; replaying the same object is idempotent, while a conflicting second result requires reconciliation/audit handling.

## 16. Producer / consumer authority

### E4

E4 owns:

- mechanical close OrderRequest translation;
- broker submit/query/reconciliation;
- actual Fill facts;
- normalized actual Position exposure/flat truth.

E4 does not own exit reasons, risk policy, or lifecycle closure interpretation.

### E5

E5 owns:

- `EXIT` / `EMERGENCY_EXIT` PositionAction production;
- lifecycle events `EXIT_REQUESTED`, `EXIT_FAILED`, `POSITION_CLOSED` interpretation;
- deterministic exit reason codes;
- final TradeResult production from the exact E4-authoritative evidence under this profile.

E5 may aggregate/validate E4 facts but may not invent Fill price/quantity/time/fee/order/position truth.

This satisfies the baseline statement that TradeResult is produced by the integrated E4/E5 close path: E4 supplies broker truth; E5 finalizes lifecycle authority and constructs the canonical result.

### E6

E6 owns durable persistence/restart/audit of:

- Position and lifecycle state;
- PositionActions;
- OrderRequests/OrderResults/Fills;
- closure evidence references;
- one idempotent canonical TradeResult.

E6 does not invent broker truth, exit reasons, or PnL inputs.

## 17. Required implementation dependency order

The safe bounded dependency order is sequential:

1. **E5 close-action producer/lifecycle semantics** — materialize `close-v0.1` EXIT/EMERGENCY_EXIT action production, EXIT_REQUESTED/EXIT_FAILED handling, and closure-reason generation against exact Position truth.
2. **E4 close-order consumer / Fill truth** — consume the accepted E5 shape and mechanically create `POSITION_EXIT` / `EMERGENCY_EXIT` MARKET reduce-only requests; propagate existing lineage into fills; expose authoritative residual/flat Position truth.
3. **E5 closure + TradeResult builder** — consume E4 entry/exit Fill sets and exact flat Position truth, apply POSITION_CLOSED, validate quantity/cost evidence, and emit deterministic `trade-result-v0.1`.
4. **E6 durable Paper runtime persistence/restart/audit** — persist the full position/action/order/fill/result chain and recover it without authority bypass.
5. **E7 Paper E2E / safety definitions** — ordinary exit, emergency exit, protection-triggered full close, partial close, duplicate evidence, mismatch/restart and TradeResult financial/idempotency scenarios.
6. **Approved-local Gate B verification** — only after all required implementation/test-definition prerequisites are materialized.

Do not start E4 close consumer before E5 materializes the exact producer payload it must consume. Do not start E6 final TradeResult persistence before the canonical result production boundary is materialized.

## 18. Release impact

This profile resolves the shared architecture/semantic boundary only.

```text
contract classification = ADDITIVE_PROFILE_REQUIRED / MATERIALIZED
Required protection follows actual filled quantity = NOT_RUN
Protection failure triggers emergency path = NOT_RUN
Drawdown/daily/position/kill-switch = NOT_RUN
Restart/persistence = BLOCKED
Paper E2E / TradeResult durable audit = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

No executable verification is claimed by this profile.
