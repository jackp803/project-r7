# E5 Status

- task_id: `E5-20260824-016`
- agent: `E5`
- state: `DONE`
- branch: `agent/e5-gate-b-trade-result-builder-20260824`
- base_main_sha: `9c46cdbf415b4c6c580044929ef55ad8a5780a84`
- implementation_evidence_head_before_terminal_status: `a43f9afb993f0a4bdc299121f128d255dfef35e3`
- summary: `Materialized the E5 authoritative-flat lifecycle closure and canonical trade-result-v0.1 builder. Finalization consumes exact parent/risk lineage, E5 EXIT/EMERGENCY_EXIT/PROTECT authority, exact E4 entry/exit OrderRequest+Fill evidence, exact final same-position CONSISTENT flat Position truth, and explicit versioned funding evidence. POSITION_CLOSED is applied only after flatness/lineage/quantity/cost validation succeeds.`
- files_changed: `src/position/trade_result.py; src/position/__init__.py; tests/position/test_trade_result.py; status/E5_GATE_B_TRADE_RESULT_BUILDER_20260824.md; coordination/E5/STATUS.md`
- contracts_changed: `NONE`
- lifecycle_enum_or_transition_table_changed: `NO`
- e4_or_broker_changed: `NO`
- e6_persistence_changed: `NO`
- provider_native_behavior_added: `NO`
- paper_shadow_live_authority_changed: `NO`
- local_verification: `NOT_RUN`
- evidence_path: `status/E5_GATE_B_TRADE_RESULT_BUILDER_20260824.md`
- next_owner: `PM/E7`

## Implemented boundary

```text
exact parent ApprovedTradePlan / risk lineage
+ exact E5 close/protection authority
+ exact E4 entry OrderRequest + Fill evidence
+ exact E4 exit OrderRequest + Fill evidence
+ exact final same-position normalized Position truth
+ explicit funding evidence
-> fail-closed closure validation
-> existing PositionEvent.POSITION_CLOSED
-> canonical trade-result-v0.1
```

## Authoritative flatness

A final result requires exact final Position truth:

```text
same position_id
same symbol/direction
actual_quantity = 0
reconciliation_status = CONSISTENT
base-asset-v0.1 / BASE_ASSET / BTC
broker_state_observed_at >= latest included exit Fill.filled_at
```

The builder never treats `OrderStatus.FILLED` alone as flat proof.

Existing shared state-machine definitions are reused unchanged:

```text
EXIT_REQUESTED + POSITION_CLOSED -> CLOSED
OPEN_PROTECTED / PROFIT_PROTECTED + POSITION_CLOSED -> CLOSED
```

`POSITION_CLOSED` is reached only after all evidence validation passes.

## Supported closure paths

### Ordinary EXIT

- exact `close-v0.1` action `EXIT`;
- exact `POSITION_EXIT` OrderRequest/Fill lineage;
- current E5 lifecycle must be `EXIT_REQUESTED`;
- final reasons are the exact E5 EXIT action reason sequence.

### EMERGENCY_EXIT

- exact `close-v0.1` action `EMERGENCY_EXIT`;
- exact `EMERGENCY_EXIT` OrderRequest/Fill lineage;
- current E5 lifecycle must be `EXIT_REQUESTED`;
- emergency action/reasons remain distinct and auditable.

### Full PROTECTION_STOP

- exact `protection-v0.1` `PROTECT` authority;
- exact `PROTECTION_STOP` OrderRequest/Fill lineage;
- current lifecycle must be `OPEN_PROTECTED` or `PROFIT_PROTECTED`;
- authoritative flat truth is still mandatory;
- canonical closure reason includes `PROTECTION_STOP_FILLED`;
- partial stop execution/residual exposure cannot finalize.

## Evidence integrity

- entry/exit Fill sets must be non-empty;
- Fill quantity/price must be positive finite Decimal facts;
- duplicate `fill_id` inside a set fails closed;
- a Fill counted in both entry/exit sets fails closed;
- entry Fill must bind to an exact declared entry OrderRequest through client-order identity, not `trade_plan_id` alone;
- exit Fill must bind to the exact exit request, exact `position_action_id`, exact `position_id`, exact role, plan, symbol and opposite side;
- mixed/cross-plan, cross-position, wrong-side, wrong-role, wrong-action or unexplained evidence fails closed;
- canonical Fill ordering is `(filled_at, fill_id)`.

## Quantity conservation

```text
entry_qty = sum(entry Fill.quantity)
exit_qty  = sum(exit Fill.quantity)
entry_qty > 0
entry_qty == exit_qty
```

For the current bounded single immediate-exit-authority path, final exit quantity also equals the exact E5-authorized / E4-requested close quantity. Partial/under-close/over-close evidence cannot finalize.

## Financial semantics

Uses only accepted `linear-base-asset-pnl-v0.1` Decimal semantics:

```text
entry_notional = Σ(entry quantity * entry price)
exit_notional  = Σ(exit quantity * exit price)
average_entry_price = entry_notional / entry_qty
average_exit_price  = exit_notional / exit_qty
LONG gross  = exit_notional - entry_notional
SHORT gross = entry_notional - exit_notional
net = gross - total_fees - funding_cost_effective
```

Every included Fill fee must be explicitly known. Non-zero fees must be USDT; signed negative fees remain rebates/credits. Missing/unsupported fee evidence blocks finalization.

Funding uses the E5-internal non-serialized `FundingEvidence` validation input allowed by the TASK:

```text
ZERO_CONFIRMED | INCLUDED
```

It requires a non-empty source version, exact position ID, and exact `[opened_at, closed_at]` interval. `INCLUDED` requires an explicit signed cost; `ZERO_CONFIRMED` permits only omitted/exact-zero cost. No provider Funding DTO was invented.

Actual Fill prices already contain realized execution price. No `slippage_cost` double deduction is performed or emitted.

## Time semantics

```text
opened_at = earliest included entry Fill.filled_at
closed_at = final flat Position.broker_state_observed_at
flat_position_observed_at = closed_at
```

Conflicting final Position opened/closed times or stale flat observation fail closed.

## Deterministic TradeResult

The builder emits the accepted baseline/profile fields, including exact plan/risk/strategy/position lineage, canonical quantity/PnL profiles, Fill IDs, OrderRequest IDs, exit authority refs, exit reasons, funding status, and financial values.

`trade_result_id` is deterministic over closure-authority and financial evidence, including ordered fills/requests, flat observation, reasons, fee facts and funding evidence material.

```text
same exact evidence -> same object / same trade_result_id
material evidence change -> different candidate trade_result_id
```

Durable conflict enforcement remains E6 scope.

## Deterministic tests materialized

`tests/position/test_trade_result.py` defines sanitized coverage for:

- valid ordinary EXIT full close;
- valid EMERGENCY_EXIT full close;
- valid full PROTECTION_STOP close;
- no flat proof / nonzero / unknown / mismatched / reconciliation-required / stale final Position rejection;
- partial explicit/protection close rejection;
- duplicate/cross-set Fill rejection;
- plan/position/symbol/side/role/action lineage rejection;
- exact entry OrderRequest binding;
- quantity conservation;
- missing fee / unsupported fee currency;
- ZERO_CONFIRMED / INCLUDED funding and signed-cost calculations;
- missing/contradictory funding rejection;
- LONG/SHORT gross/net PnL;
- no slippage double subtraction;
- opened/closed time semantics;
- deterministic ID and identity changes for changed fill/reason/funding/flat evidence;
- lifecycle compatibility with protection-result bridge, close producer and existing state machine;
- provider-native/credential/persistence/release fields absent.

## Executable verification

Result:

```text
NOT_RUN
```

Reason: no explicitly PM/Product-Owner-approved AgentBridge Local Runner action pinned to this exact new target revision is exposed in this session. Static review is not executable PASS evidence.

Exact future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

No project tests/code were executed via GitHub Actions/CI/hosted runners, GitHub-triggered self-hosted compute, arbitrary cloud compute, Computer Adapter, provider/private APIs, or credentials.

## Release impact

```text
E5 close-v0.1 producer                   MATERIALIZED / accepted prior PR #47
E4 close-v0.1 consumer + flat truth      MATERIALIZED / accepted prior PR #48
E5 trade-result-v0.1 builder             MATERIALIZED STATICALLY / this task
E6 durable Paper persistence/restart     BLOCKED / later dependency
E7 full Paper E2E/safety                 BLOCKED / later dependency
approved-local Gate B verification       NOT_RUN / later dependency

Paper E2E / durable audit = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

E5 stops on `DONE` for `E5-20260824-016`. Do not self-start E6 persistence, E7 Paper E2E, approved-local verification, provider/private work, Gate C, PAPER, SHADOW, or LIVE.
