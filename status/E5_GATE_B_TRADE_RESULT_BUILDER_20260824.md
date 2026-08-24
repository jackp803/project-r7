# E5 Gate B TradeResult Builder Evidence — 2026-08-24

## Authority / scope

- task_id: `E5-20260824-016`
- agent: `E5 Risk Management & Position Lifecycle Engineer`
- target branch: `agent/e5-gate-b-trade-result-builder-20260824`
- base main revision: `9c46cdbf415b4c6c580044929ef55ad8a5780a84`
- parent contract: `contracts-v0.1`
- close profile: `close-v0.1`
- TradeResult profile: `trade-result-v0.1`
- PnL profile: `linear-base-asset-pnl-v0.1`
- architecture: `ADR-0005`
- accepted prerequisites: close/TradeResult contract PR #46, E5 close producer PR #47, E4 close consumer PR #48

This task implements only the E5-owned authoritative-flat lifecycle closure and canonical TradeResult production boundary. It does not implement E6 persistence/restart/audit, E7 full Paper E2E, provider/private APIs, Demo/live execution, or PAPER/SHADOW/LIVE authorization.

## Terminal static disposition

```text
E5 authoritative-flat / trade-result-v0.1 builder = MATERIALIZED STATICALLY
project executable verification = NOT_RUN
Paper E2E / durable audit = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

`MATERIALIZED STATICALLY` is implementation/test-definition evidence only. It is not executable PASS evidence.

## Implemented boundary

New callable:

```python
build_trade_result(
    parent_plan,
    *,
    current_lifecycle_state,
    exit_authority,
    entry_order_requests,
    entry_fills,
    exit_order_request,
    exit_fills,
    final_position,
    funding_evidence,
)
```

The bounded authority/truth chain is:

```text
exact parent ApprovedTradePlan / risk lineage
+ exact E5 close/protection PositionAction authority
+ exact E4 entry OrderRequest + Fill evidence
+ exact E4 exit OrderRequest + Fill evidence
+ exact final same-position normalized Position truth
+ explicit versioned funding evidence facts
-> fail-closed closure validation
-> existing PositionEvent.POSITION_CLOSED
-> canonical trade-result-v0.1
```

The builder has no broker argument and performs no submit/query/retry/cancel/provider operation. It does not persist data.

## Authoritative flatness

Finalization requires exact final Position evidence satisfying all of:

```text
schema_version = contracts-v0.1
same exact position_id as E5 immediate authority
same exact symbol / direction as parent plan
actual_quantity = 0
reconciliation_status = CONSISTENT
quantity_profile_version = base-asset-v0.1
quantity_unit = BASE_ASSET
quantity_asset = BTC
broker_state_observed_at >= latest included exit Fill.filled_at
opened_at = earliest authoritative included entry Fill.filled_at
```

If an optional final Position `closed_at` is supplied, it must equal the authoritative flat observation time.

The builder does not consume `OrderStatus.FILLED` as closure authority. A fully filled order without exact flat Position truth cannot produce `POSITION_CLOSED` or TradeResult.

## Supported final closure paths

### Ordinary explicit EXIT

Required immediate authority:

```text
close_profile_version = close-v0.1
action = EXIT
order_role = POSITION_EXIT
current E5 lifecycle = EXIT_REQUESTED
```

Final `exit_reason_codes` are copied from the exact deterministic E5 EXIT PositionAction reason sequence.

### Explicit EMERGENCY_EXIT

Required immediate authority:

```text
close_profile_version = close-v0.1
action = EMERGENCY_EXIT
order_role = EMERGENCY_EXIT
current E5 lifecycle = EXIT_REQUESTED
```

Emergency action/reason distinction remains explicit in `exit_authority_refs` and `exit_reason_codes`.

### Full protection-triggered close

Required immediate authority:

```text
protection_profile_version = protection-v0.1
action = PROTECT
order_role = PROTECTION_STOP
current E5 lifecycle = OPEN_PROTECTED | PROFIT_PROTECTED
```

Only a full protection Fill set plus exact authoritative flat Position truth may finalize. The canonical E5 closure reason is:

```text
PROTECTION_STOP_FILLED
```

Partial protection execution or residual exposure cannot finalize.

## Exact evidence binding

### Parent / risk / strategy

The builder validates exact:

- `trade_plan_id`;
- `risk_decision_id`;
- `risk_policy_version`;
- `strategy_id` / `strategy_version` where the close profile carries them;
- `symbol = BTC_USDT_PERP`;
- `direction = LONG | SHORT`;
- `base-asset-v0.1 / BASE_ASSET / BTC` quantity semantics.

### Entry OrderRequest / Fill binding

Every included entry Fill must bind to an explicitly declared entry OrderRequest through its exact `client_order_id`. `trade_plan_id` alone is insufficient.

Entry requests must remain plan-authorized MARKET entry requests and must not carry PositionAction/exit/protection authority fields. Every declared entry request must have included Fill evidence.

Entry Fill direction must match parent direction:

```text
LONG  -> BUY
SHORT -> SELL
```

### Exit OrderRequest / Fill binding

Exit OrderRequest must retain:

```text
authorization_type = POSITION_ACTION
exact trade_plan_id
exact position_action_id
exact position_id
exact risk_decision_id
exact expected order_role
reduce_only = true
exact canonical authorized quantity
```

Side must be opposite the parent position direction:

```text
LONG  -> SELL
SHORT -> BUY
```

Explicit EXIT / EMERGENCY_EXIT requests are `MARKET` with no executable stop/limit/TIF. Protection exits are `STOP_MARKET` and the stop price must match the E5 protection authority.

Every exit Fill must bind to the exact exit request through `client_order_id` and to the exact immediate E5 authority through `position_action_id`, `position_id`, and `order_role`.

## Duplicate / ambiguity protection

- entry and exit Fill sets must each be non-empty;
- duplicate `fill_id` inside either set fails closed;
- the same `fill_id` appearing in both entry and exit sets fails closed;
- mixed plan, symbol, side, position, request, action or role evidence fails closed;
- malformed/non-finite/non-positive Fill quantity or price fails closed;
- canonical Fill ordering is deterministic by `(filled_at, fill_id)`.

## Quantity conservation

Using Decimal arithmetic:

```text
entry_qty = Σ entry Fill.quantity
exit_qty  = Σ exit Fill.quantity
entry_qty > 0
entry_qty == exit_qty
```

For the current bounded single immediate-exit-authority path, final `exit_qty` must also equal the exact exit OrderRequest quantity and the exact E5 PositionAction quantity.

Thus partial/under-close and over-close evidence cannot produce a final TradeResult.

`TradeResult.entry_quantity = entry_qty`.

## Financial semantics

All calculations use Decimal arithmetic over actual Fill facts:

```text
entry_notional = Σ(entry_qty_i * entry_price_i)
exit_notional  = Σ(exit_qty_i * exit_price_i)
average_entry_price = entry_notional / entry_qty
average_exit_price  = exit_notional / exit_qty

LONG:  gross_pnl = exit_notional - entry_notional
SHORT: gross_pnl = entry_notional - exit_notional

net_pnl = gross_pnl - total_fees - funding_cost_effective
```

Actual Fill prices are authoritative realized execution prices. `slippage_cost` is not subtracted again and is not emitted by this V0.1 builder.

### Fees

Every included Fill must carry explicit fee evidence. Missing fee is a finalization error.

- positive fee = cost;
- negative fee = rebate/credit;
- non-zero fee must be `USDT` under this profile;
- zero fee may have absent or `USDT` currency;
- unsupported fee currency fails closed.

### Funding

The task explicitly permits a bounded E5-internal funding validation input without creating a shared Funding DTO.

Implemented E5-internal helper:

```python
FundingEvidence(
    status,
    source_version,
    position_id,
    interval_start,
    interval_end,
    funding_cost=None,
)
```

This helper is not a persisted/shared cross-module contract. It represents already-authoritative/versioned integrated evidence supplied to E5.

Required semantics:

```text
status = ZERO_CONFIRMED | INCLUDED
same exact position_id
interval_start = TradeResult.opened_at
interval_end = authoritative flat observation / TradeResult.closed_at
```

- `INCLUDED` requires explicit signed `funding_cost`;
- positive funding is cost;
- negative funding is credit;
- `ZERO_CONFIRMED` permits omitted or exactly zero cost only;
- missing, mismatched or contradictory evidence fails closed.

The TradeResult emits `funding_cost` for `INCLUDED`; for `ZERO_CONFIRMED` it is omitted consistently and effective cost is zero.

## Time semantics

```text
opened_at = earliest authoritative included entry Fill.filled_at
closed_at = final flat Position.broker_state_observed_at
flat_position_observed_at = closed_at
```

Final flat observation must be at or after the latest included exit Fill. Conflicting supplied Position opened/closed times fail closed.

## Lifecycle semantics

The builder does not modify the shared transition table.

For explicit close paths:

```text
EXIT_REQUESTED + POSITION_CLOSED -> CLOSED
```

For a full protection-triggered close, the existing accepted state machine supports:

```text
OPEN_PROTECTED / PROFIT_PROTECTED + POSITION_CLOSED -> CLOSED
```

`POSITION_CLOSED` is applied only after all evidence/flatness/quantity/cost validation succeeds.

The builder returns an E5-internal `TradeResultBuildOutcome` containing the canonical TradeResult plus the existing lifecycle event/next state. This helper is not a shared DTO.

## Canonical TradeResult fields

The builder emits baseline plus accepted profile fields including:

```text
schema_version = contracts-v0.1
trade_result_profile_version = trade-result-v0.1
pnl_profile_version = linear-base-asset-pnl-v0.1
trade_result_id
strategy_id
strategy_version
trade_plan_id
risk_decision_id
risk_policy_version
position_id
symbol
direction
quantity_profile_version = base-asset-v0.1
quantity_unit = BASE_ASSET
quantity_asset = BTC
pnl_currency = USDT
opened_at
closed_at
flat_position_observed_at
entry_quantity
average_entry_price
average_exit_price
gross_pnl
net_pnl
total_fees
exit_reason_codes
entry_fill_ids
exit_fill_ids
entry_order_request_ids
exit_order_request_ids
exit_authority_refs
funding_evidence_status
funding_cost  # INCLUDED only
```

No provider-native, credential, E6 persistence, registry, Gate, PAPER, SHADOW, or LIVE fields are added.

## Deterministic identity / idempotency

`trade_result_id` is SHA-256-based and deterministic over canonical closure authority and financial evidence, including:

- profile versions;
- plan/risk/strategy/position lineage;
- ordered Fill IDs;
- ordered entry/exit OrderRequest IDs;
- immediate exit authority refs;
- final flat observation;
- E5 exit reason sequence;
- actual Fill quantity/price/time/fee/currency evidence;
- funding status/source version/interval/signed cost.

Identical evidence produces the same object/ID. Material changes produce a different candidate identity. Durable conflict enforcement remains E6 scope and is not implemented here.

## Deterministic test definitions materialized

`tests/position/test_trade_result.py` defines sanitized test coverage for:

- valid ordinary EXIT full close -> authoritative flat proof -> `POSITION_CLOSED` -> TradeResult;
- valid EMERGENCY_EXIT preserving emergency action/reason/role;
- valid full PROTECTION_STOP closure with canonical protection-stop reason;
- full Fill evidence without flat Position proof cannot finalize;
- non-zero final Position cannot finalize;
- UNKNOWN/MISMATCH/RECONCILIATION_REQUIRED final Position cannot finalize;
- stale final Position observation cannot finalize;
- partial explicit close cannot finalize;
- partial protection execution cannot finalize;
- duplicate Fill IDs and cross-set duplicate Fill rejection;
- mixed plan/position/symbol/side/role/action lineage rejection;
- entry Fill exact OrderRequest binding rather than `trade_plan_id` alone;
- exact quantity conservation pass/fail;
- missing fee and unsupported fee-currency rejection;
- ZERO_CONFIRMED and INCLUDED signed funding calculations;
- missing/contradictory funding evidence rejection;
- LONG and SHORT fill-price PnL formulas;
- no slippage double subtraction;
- opened-at / closed-at semantics;
- deterministic identical result identity;
- changed Fill/reason/funding/flat observation changes identity;
- explicit close requires `EXIT_REQUESTED` lifecycle context;
- protection closure requires a protected lifecycle state;
- existing protection-result bridge, close producer and state-machine compatibility;
- absence of provider-native, credential, persistence and release-authority fields.

Tests use real accepted E5/E4 public APIs and shared model semantics where available rather than reimplementing E4 behavior in test helpers.

## Files changed by E5 task

Expected bounded diff:

- `src/position/trade_result.py` — new E5 authoritative-flat/TradeResult builder;
- `src/position/__init__.py` — E5 exports only;
- `tests/position/test_trade_result.py` — deterministic definitions;
- `status/E5_GATE_B_TRADE_RESULT_BUILDER_20260824.md` — this evidence/handoff;
- `coordination/E5/STATUS.md` — terminal mailbox status on target branch.

No `contracts/**`, ADR, `src/execution/**`, `src/brokers/**`, E6 persistence, E2/E3 production or release-gate files are changed by this task.

## Executable verification

Result:

```text
NOT_RUN
```

Reason: no explicitly PM/Product-Owner-approved AgentBridge Local Runner action pinned to the exact clean target revision is exposed in this session. Static inspection is not executable PASS evidence.

Exact future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

No project code/tests were executed through GitHub Actions, GitHub-hosted or GitHub-triggered runners, arbitrary cloud compute, Computer Adapter, provider/private APIs, or credentials.

`NOT_RUN` is not PASS.

## Security / provider scope

```text
GitHub Actions / CI / hosted runner = NOT_USED
GitHub-triggered self-hosted compute = NOT_USED
Computer Adapter = NOT_USED
provider/private requests = NOT_SENT
provider credentials = NOT_USED
Paper/Shadow/Live authority = NOT_CHANGED / UNAUTHORIZED
contracts/ADR changes = NONE
E4/E6 production changes = NONE
```

## Release impact / handoff

This task resolves only the E5 implementation slot in the accepted dependency chain:

```text
E5 close-v0.1 producer                  MATERIALIZED / prior PR #47
E4 close-v0.1 consumer + flat truth     MATERIALIZED / prior PR #48
E5 trade-result-v0.1 builder            MATERIALIZED STATICALLY / this task
E6 durable Paper persistence/restart    BLOCKED / later dependency
E7 full Paper E2E/safety                BLOCKED / later dependency
approved-local Gate B verification      NOT_RUN / later dependency
```

Therefore:

```text
Paper E2E / durable audit = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER = UNAUTHORIZED
SHADOW = UNAUTHORIZED
LIVE = UNAUTHORIZED
```

Next owner after E5 terminal handoff: `PM/E7` for review/dependency coordination. E5 does not self-start E6 persistence, E7 Paper E2E, approved-local verification, provider/private work, Gate C, PAPER, SHADOW, or LIVE.
