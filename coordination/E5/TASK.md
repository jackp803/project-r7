# E5 Current Task

- task_id: `E5-20260824-016`
- issued_at: `2026-08-24T13:40:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e5-gate-b-trade-result-builder-20260824`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`, ADR-0005, accepted Gate A PASS, accepted protection chain PR #37-#45, accepted close/TradeResult contract PR #46, accepted E5 close producer PR #47, accepted E4 close consumer PR #48

## Objective

Implement only the E5-owned **authoritative-flat lifecycle closure plus canonical `trade-result-v0.1` builder** defined by the accepted close/TradeResult profile.

Bounded truth/authority chain:

```text
exact parent ApprovedTradePlan / risk lineage
+ exact E5 close/protection authority and current lifecycle context
+ exact E4-authoritative entry OrderRequest + entry Fill set
+ exact E4-authoritative exit OrderRequest + exit Fill set
+ exact E4-normalized final same-position Position observation
+ explicit funding evidence status/cost facts required by the profile
-> fail-closed closure validation
-> existing E5 PositionEvent.POSITION_CLOSED only when authoritative flatness is proven
-> canonical trade-result-v0.1 TradeResult
```

Stop at E5 lifecycle/TradeResult production. Do **not** implement E6 durable persistence/restart/audit, E7 full Paper E2E, E4 broker/execution behavior, provider/private APIs, Demo/live execution, or PAPER/SHADOW/LIVE authorization.

## Accepted prerequisites

```text
PR #46
merge = d070ffc752d5c37c05aa4101ebc2f6add0c1ff48
profiles = close-v0.1 / trade-result-v0.1 / linear-base-asset-pnl-v0.1
schema_version = contracts-v0.1

PR #47
merge = e4caa0e1398f2a3cdf1209fa7bc74516f6a94d15
E5 close-v0.1 producer + EXIT_REQUESTED intent = MATERIALIZED
local executable verification = NOT_RUN

PR #48
merge = 3f7bba953ece100d23c88b86b47df52696adb3a0
head = 4d743ee78883905e4fac8f1a05bdeb70b4338811
E4 close-v0.1 consumer + close Fill/residual/flat PaperBroker truth = MATERIALIZED
local executable verification = NOT_RUN
```

All prior executable Gate B evidence remains `NOT_RUN`; Gate B remains `BLOCKED` and PAPER remains unauthorized.

## Required inspection before editing

Read latest `main` and at minimum:

- `README.md`, `agents/README.md`, `agents/E5_RISK_POSITION.md`;
- `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`, ADR-0005, parent shared/execution/protection profiles;
- current `src/position/state_machine.py`, E5 protection producer/result bridge and close producer;
- accepted E4 `src/execution/models.py`, `src/execution/close.py`, `src/execution/protection.py`, and `src/brokers/paper.py` read-only;
- canonical baseline `TradeResult`, `Position`, `PositionAction`, `OrderRequest`, `Fill` semantics;
- current E5 tests and release-gate evidence.

### Contract-first blocker rule

If the accepted E7-owned profiles do not provide enough semantics to validate/finalize a canonical result without inventing a new shared object or financial meaning, stop:

```text
BLOCKED / CONTRACT_OR_SEMANTIC_GAP
next_owner = E7
```

Record the exact missing field/semantic and producer/consumer impact. Do not create a parallel cross-module TradeResult/Funding/Fill contract or modify `contracts/**` / ADRs.

## Required behavior

### 1. Authoritative flatness is mandatory before lifecycle closure

A final closure may apply `PositionEvent.POSITION_CLOSED` only when the supplied E4-normalized final Position proves all of:

```text
same exact position_id
same exact symbol
actual_quantity = 0
reconciliation_status = CONSISTENT
broker_state_observed_at >= latest included exit Fill.filled_at
```

`OrderStatus.FILLED` alone is never flat proof.

Fail closed / produce no final TradeResult when final Position truth is unknown, mismatched, nonzero, stale relative to exit fills, `RECONCILIATION_REQUIRED`, or otherwise inconsistent.

Do not modify the shared state-machine transition table. Use existing transitions only. For explicit E5 close paths, final lifecycle should come from existing:

```text
EXIT_REQUESTED + POSITION_CLOSED -> CLOSED
```

For a fully executed protection stop, existing allowed protected/emergency closure transitions may be used only when exact lifecycle/authority evidence supports them. Do not manufacture a lifecycle shortcut.

### 2. Supported final closure paths

Materialize deterministic validation/finalization for the currently accepted bounded paths:

#### Explicit ordinary EXIT

- exact E5 `close-v0.1` `PositionAction.action = EXIT`;
- exact E4 exit request/fills with `order_role = POSITION_EXIT`;
- E5 lifecycle context must prove the explicit close reached `EXIT_REQUESTED` before final closure;
- final exit reasons derive from the exact E5 EXIT action reason sequence.

#### Explicit EMERGENCY_EXIT

- exact E5 `close-v0.1` `PositionAction.action = EMERGENCY_EXIT`;
- exact E4 exit request/fills with `order_role = EMERGENCY_EXIT`;
- preserve emergency distinction in authority/reason evidence;
- final closure still requires authoritative flat Position truth.

#### Full protection-triggered close

- exact accepted `protection-v0.1` `PositionAction.action = PROTECT` and exact `PROTECTION_STOP` OrderRequest/Fill lineage;
- only a full protection-triggered close with authoritative final flat Position truth may finalize;
- deterministic `exit_reason_codes` must include canonical `PROTECTION_STOP_FILLED` plus any stable E5 policy/lifecycle reasons required by exact accepted evidence;
- partial protection execution with residual exposure must not finalize; preserve fail-closed/reconciliation behavior defined by the profile.

Do not broaden into unprofiled trailing-stop/modify-protection/reopen/multi-position semantics.

### 3. Exact closure evidence validation

Consume one coherent immutable evidence set. Validate at minimum:

- exact parent ApprovedTradePlan and risk decision/policy lineage;
- exact strategy ID/version, symbol, direction and position ID;
- non-empty authoritative entry Fill set and exact entry OrderRequest identities;
- non-empty authoritative exit Fill set and exact exit OrderRequest identities;
- exact E5 immediate exit/protection authority references;
- exact final flat Position observation;
- no duplicate `fill_id` in either set and no Fill counted twice across sets;
- all entry fills bind to the exact declared entry OrderRequest(s) and parent `trade_plan_id`;
- all exit fills bind to the same `position_id`, parent `trade_plan_id`, exact exit request/action lineage and an allowed role `POSITION_EXIT | EMERGENCY_EXIT | PROTECTION_STOP`;
- entry Fill side is consistent with parent direction and exit Fill side is opposite it;
- no mixed plan, mixed symbol, cross-position, unexplained order/fill, ambiguous, unreconciled or duplicated evidence;
- canonical Fill ordering is deterministic by `(filled_at, fill_id)`.

Current entry Fill may lack `position_id`; bind it only through the exact declared entry OrderRequest identity + parent plan as specified by the accepted profile. Do not rely on `trade_plan_id` alone as a future multi-position heuristic.

### 4. Quantity conservation

Under exact `base-asset-v0.1 / BASE_ASSET / BTC` semantics require:

```text
entry_qty = sum(entry Fill.quantity)
exit_qty  = sum(exit Fill.quantity)
entry_qty > 0
entry_qty == exit_qty
```

Any under-close, over-close, duplicate quantity, non-positive/non-finite quantity or residual final exposure blocks finalization.

`TradeResult.entry_quantity = entry_qty`.

### 5. Financial semantics — exact profile only

Use Decimal arithmetic and the accepted `linear-base-asset-pnl-v0.1` rules only:

```text
entry_notional = sum(entry Fill.quantity * entry Fill.price)
exit_notional  = sum(exit Fill.quantity * exit Fill.price)
average_entry_price = entry_notional / entry_qty
average_exit_price  = exit_notional / exit_qty

LONG:  gross_pnl = exit_notional - entry_notional
SHORT: gross_pnl = entry_notional - exit_notional

net_pnl = gross_pnl - total_fees - funding_cost_effective
```

Fee requirements:

- every included Fill fee must be explicitly known;
- non-zero fees must be `USDT` under this profile unless a separately accepted conversion profile exists;
- positive fee = cost, negative fee = rebate/credit;
- missing/ambiguous fee evidence must block finalization rather than silently become zero.

Funding requirements:

```text
funding_evidence_status = ZERO_CONFIRMED | INCLUDED
```

- `INCLUDED` requires explicit authoritative/versioned funding cost for this exact position interval;
- `ZERO_CONFIRMED` permits zero only because the supplied integrated evidence explicitly confirms zero/not-applicable;
- absence of funding evidence is not zero.

Do not invent a provider Funding DTO. A bounded E5-internal validation input is acceptable only if it does not become a parallel shared contract; if cross-module serialized funding evidence is required now and not defined, stop on the contract-first blocker.

Actual Fill prices already include realized execution price. Do not subtract `slippage_cost` again from `net_pnl`. Leave optional slippage/R-multiple absent unless exact versioned evidence already exists and is explicitly within the accepted profile.

### 6. Time semantics

Set exactly:

```text
opened_at = earliest authoritative included entry Fill.filled_at
closed_at = final flat Position.broker_state_observed_at
flat_position_observed_at = closed_at
```

`closed_at` must be at or after the latest included exit Fill time.

Conflicting persisted/local Position times or fill ordering must fail closed rather than be repaired heuristically.

### 7. Canonical TradeResult payload

Produce the baseline required fields plus the accepted profile fields, including at minimum:

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
```

Include `funding_cost` exactly when required by `INCLUDED` or when an explicit zero representation is chosen consistently for `ZERO_CONFIRMED`.

Do not add provider-native fields or E6 persistence metadata into canonical TradeResult.

### 8. Exit authority refs / reason ownership

Every `exit_authority_refs` item must carry the exact accepted immediate authority:

```text
position_action_id
position_id
action = EXIT | EMERGENCY_EXIT | PROTECT
order_role = POSITION_EXIT | EMERGENCY_EXIT | PROTECTION_STOP
```

E5 owns final deterministic `exit_reason_codes`; E4 order/fill facts must never invent them.

Do not silently combine unrelated action reasons. The exact closure path must determine the canonical ordered reason sequence.

### 9. Deterministic TradeResult identity / idempotency

`trade_result_id` must be deterministic over all closure-authority and financial material required by the accepted profile, including ordered fill IDs, order request IDs, authority refs, risk lineage, flat observation, reasons and funding/fee material.

Reprocessing exact identical evidence must yield the same object/ID. Any material evidence change must produce a different candidate identity and must not silently overwrite an earlier result; durable conflict enforcement belongs later to E6.

### 10. No hidden truth manufacture

E5 may aggregate and validate E4 facts but must never invent or overwrite:

- Fill quantity/price/time/fee;
- OrderRequest identity/lineage;
- broker Position quantity/reconciliation/observation time;
- provider funding facts;
- broker order status.

Unknown/incomplete/ambiguous evidence must fail closed.

## Required deterministic tests

Add E5-owned definitions covering at minimum:

- valid ordinary EXIT full close -> authoritative flat proof -> `POSITION_CLOSED` -> deterministic TradeResult;
- valid EMERGENCY_EXIT full close preserves emergency authority/reasons;
- valid full `PROTECTION_STOP` close can finalize only with exact flat Position proof and canonical protection-stop reason;
- `OrderStatus.FILLED` without flat Position proof cannot finalize;
- nonzero final Position cannot close/finalize;
- unknown/reconciliation-required/stale final Position cannot close/finalize;
- partial explicit close cannot finalize;
- partial protection fill cannot finalize;
- duplicate Fill IDs / cross-set duplicate Fill fail closed;
- cross-plan/cross-position/mixed-symbol/wrong-side/wrong-role/wrong-action lineage fail closed;
- entry Fill must bind to exact declared entry OrderRequest, not `trade_plan_id` alone;
- quantity conservation exact pass/fail cases;
- missing fee / unsupported fee currency blocks finalization;
- ZERO_CONFIRMED funding and INCLUDED funding calculations;
- missing funding evidence blocks finalization;
- LONG and SHORT gross/net PnL formulas using exact Fill prices;
- slippage is not double-subtracted;
- opened_at/closed_at semantics;
- same exact evidence -> same `trade_result_id`; changed fill/reason/funding/flat observation -> changed ID;
- close/result construction does not modify E4 broker truth or shared contracts;
- existing protection result bridge, close producer and state-machine behavior remain compatible;
- no provider-native/credential/persistence/release-authority fields are introduced.

Use sanitized/fake fixtures only. Do not encode E6 storage implementation or E7 release-gate transitions into E5 unit tests.

## Writable scope

E5-owned paths only:

- `src/position/**`;
- `src/risk/**` only if strictly required for E5-owned reason/risk-lineage validation without changing policy values;
- `tests/position/**`;
- `tests/risk/**` only if needed for compatibility;
- E5-owned `tests/safety/**` only where appropriate;
- E5-specific `status/**` evidence/handoff;
- `coordination/E5/STATUS.md` on the target branch.

Forbidden:

- `contracts/**` / ADR edits;
- `src/execution/**` / `src/brokers/**`;
- E6 persistence/registry;
- E2/E3 production;
- shared contract expansion outside E5-owned implementation unless terminating on a genuine E7 blocker;
- provider/private networking or credentials;
- PAPER/SHADOW/LIVE authority;
- GitHub Actions/CI/workflows.

## Executable verification

Implementation/test-definition work remains local-only. If no explicitly PM/Product-Owner-approved Local Runner action is available for the exact clean target revision, record:

```text
local_verification = NOT_RUN
```

with exact future Windows PowerShell commands from repository root, at minimum:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

Do not use GitHub Actions/CI/hosted runners, GitHub-triggered self-hosted compute, arbitrary cloud execution, Computer Adapter, provider/private APIs, or credentials. `NOT_RUN` is not PASS.

## Acceptance

### DONE

- authoritative same-position flat proof is required before any `POSITION_CLOSED` interpretation;
- ordinary, emergency and full protection-triggered closures are correctly bounded by exact authority/Fill/Position evidence;
- canonical `trade-result-v0.1` is produced exactly from accepted evidence and financial semantics;
- duplicate/partial/ambiguous/unreconciled/incomplete evidence fails closed;
- TradeResult identity is deterministic/idempotent;
- no E4/E6/provider/private/release-authority scope is crossed;
- deterministic tests are materialized;
- executable verification is approved-local evidence or explicit `NOT_RUN` with exact commands.

### BLOCKED

- accepted TradeResult/financial/funding/closure semantics cannot be safely materialized without a genuine shared-contract change or unresolved cross-role dependency;
- record exact expected-vs-actual evidence and `next_owner = E7`;
- do not invent a workaround or parallel shared DTO.

Do not declare Paper E2E, durable audit, Gate B/PAPER_READY, or any PAPER/SHADOW/LIVE authority PASS.

## Completion / mailbox rule

Commit/push bounded code/tests/evidence/status to `agent/e5-gate-b-trade-result-builder-20260824`.

**Worker-owned terminal STATUS must be written and pushed to `coordination/E5/STATUS.md` on this target branch, not main**, so AgentBridge can observe terminal state and callback PM.

Then stop. Do not self-start E6 persistence, E7 Paper E2E, approved-local verification, provider/private work, Gate C, PAPER, SHADOW, or LIVE.