# E4 Current Task

- task_id: `E4-20260824-009`
- issued_at: `2026-08-24T13:23:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-gate-b-close-consumer-20260824`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`, ADR-0005, accepted Gate A PASS, accepted protection chain PR #37-#45, accepted close/TradeResult contract PR #46, accepted E5 close producer PR #47

## Objective

Implement only the E4-owned **`close-v0.1` mechanical close-order consumer plus provider-neutral PaperBroker close Fill/residual-exposure truth** required by the accepted dependency order:

```text
E5 close-v0.1 PositionAction.EXIT | EMERGENCY_EXIT
+ exact parent ApprovedTradePlan
+ exact current E4-normalized Position observation
-> canonical close OrderRequest
-> PaperBroker order/fill truth
-> provider-neutral residual/flat exposure observation usable by later E5 lifecycle work
```

Stop at E4 execution/broker truth. Do **not** implement E5 `POSITION_CLOSED`, E5 `trade-result-v0.1` construction, E6 persistence/restart/audit, E7 Paper E2E, provider/private APIs, Demo/live execution, or PAPER/SHADOW/LIVE authorization.

## Accepted prerequisites

```text
PR #46
merge = d070ffc752d5c37c05aa4101ebc2f6add0c1ff48
profiles = close-v0.1 / trade-result-v0.1 / linear-base-asset-pnl-v0.1
schema_version = contracts-v0.1

PR #47
merge = e4caa0e1398f2a3cdf1209fa7bc74516f6a94d15
head = 45c26072f37c0caa234385701288789893da80e8
E5 close producer = MATERIALIZED
local executable verification = NOT_RUN
```

All prior executable Gate B evidence remains `NOT_RUN`; Gate B remains `BLOCKED` and PAPER remains unauthorized.

## Required inspection before editing

Read latest `main` and at minimum:

- `README.md`, `agents/README.md`, `agents/E4_EXECUTION.md`;
- `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`, ADR-0005, parent shared/execution/protection profiles;
- accepted E5 `src/position/close.py` from PR #47, read-only;
- current `src/execution/models.py`, `src/execution/gateway.py`, `src/execution/protection.py`;
- current `src/brokers/base.py`, `src/brokers/paper.py` including PR #43/#45 terminal/fill behavior;
- current E4 tests and E7 release-gate evidence.

### Contract-first blocker rule

If the existing E7-owned shared Position/OrderRequest/Fill semantics are insufficient to represent the required same-position residual/flat broker truth safely, stop:

```text
BLOCKED / CONTRACT_OR_SEMANTIC_GAP
next_owner = E7
```

Record the exact missing semantic/field and producer/consumer impact. Do not invent a parallel shared Position DTO or change `contracts/**` / ADRs.

## Required behavior

### 1. Exact close-v0.1 validation

Consume only accepted `close-v0.1` `PositionAction` with action exactly:

```text
EXIT
EMERGENCY_EXIT
```

Validate against the exact parent ApprovedTradePlan and exact current normalized Position observation. Fail closed on at least:

- unsupported/missing schema/profile/action;
- expired close action;
- parent plan/risk/strategy/risk-policy lineage mismatch;
- position ID/symbol/side/source lifecycle/observation mismatch;
- `reconciliation_status != CONSISTENT`;
- quantity/profile/unit/asset mismatch;
- action quantity not equal to exact current `Position.actual_quantity`;
- action quantity greater than parent approved maximum;
- unknown/unsupported position state;
- unsupported order type/profile.

Do not use parent entry-plan TTL as the lifetime of a post-fill close action.

### 2. Mechanical OrderRequest mapping

For accepted ordinary `EXIT`:

```text
authorization_type = POSITION_ACTION
order_role = POSITION_EXIT
order_type = MARKET
reduce_only = true
```

For accepted `EMERGENCY_EXIT`:

```text
authorization_type = POSITION_ACTION
order_role = EMERGENCY_EXIT
order_type = MARKET
reduce_only = true
```

Side mapping:

```text
LONG  -> SELL
SHORT -> BUY
```

Quantity and lineage must be exact:

```text
OrderRequest.quantity = PositionAction.quantity = current Position.actual_quantity
trade_plan_id = PositionAction.trade_plan_id
position_action_id = exact immediate E5 authority
position_id = exact PositionAction.position_id
risk_decision_id = exact parent/E5 lineage
quantity_profile_version/unit/asset = exact accepted canonical semantics
```

V0.1 requires:

```text
limit_price = None
stop_price = None
time_in_force = None
```

E4 may validate or reject but may not change quantity, action type, E5 reason semantics or risk authority.

### 3. Deterministic idempotency

Use the existing immediate-authority identity rule:

```text
client_order_id = stable for (position_action_id, order_role)
```

and deterministic `order_request_id` from that client identity.

Replaying the same exact close action must produce the same logical request. Different action/role authority must not collide. Preserve existing no-blind-retry and reconciliation behavior.

### 4. Close Fill lineage

PaperBroker fills produced from close requests must preserve exact originating request lineage:

```text
trade_plan_id
position_action_id
position_id
order_role = POSITION_EXIT | EMERGENCY_EXIT
```

Partial and full close fills retain the same authority lineage and exact per-fill quantity/price/time/fee facts. Total fills may never exceed the authorized request quantity.

Do not reinterpret `PROTECTION_STOP` fills; accepted PR #45 protection lineage must remain compatible.

### 5. Residual / flat broker truth

Materialize the E4-owned provider-neutral Paper path needed to observe actual residual exposure after close fills without inferring E5 lifecycle state.

Required safety semantics:

- partial close must leave an observable positive residual when exposure remains;
- full close may expose actual zero quantity only from broker/Paper truth, never from `OrderStatus.FILLED` alone;
- no over-close or absolute-exposure increase is allowed;
- ambiguous/unknown/reconciliation-required order/position truth must not be presented as definitively flat;
- the observation required for later `POSITION_CLOSED` must preserve the exact position/symbol identity and current broker observation time under existing shared Position semantics;
- E4 must not emit/apply `POSITION_CLOSED` or exit reason codes.

If current PaperBroker/execution models cannot produce that same-position normalized observation without a shared semantic change, stop on the contract-first blocker rather than guessing from symbol net exposure alone.

### 6. Terminal/failure behavior

Preserve existing provider-neutral E4 terminal/reconciliation semantics. A close order rejection/cancel/expiry is E4 truth only; do not call E5 lifecycle in this task.

`FILLED` is order truth, not proof of a flat Position. `PARTIALLY_FILLED` must remain distinct.

### 7. Provider-neutral / security scope

Do not add OKX/Pionex/private-provider fields, contract counts, networking, credentials, signatures, provider-native IDs beyond existing broker truth, or live execution behavior.

## Required deterministic tests

Materialize E4-owned definitions covering at minimum:

- valid LONG EXIT -> SELL MARKET reduce-only POSITION_EXIT request;
- valid SHORT EXIT -> BUY equivalent;
- valid EMERGENCY_EXIT -> EMERGENCY_EXIT role and distinct idempotency identity;
- exact close quantity/parent/action/position/risk lineage;
- `limit_price`, `stop_price`, `time_in_force` remain `None`;
- same action -> same client/order request IDs; changed action/role -> different identity;
- expired/mismatched/unknown/reconciliation-required authority fails closed;
- parent entry TTL does not invalidate a still-valid close action;
- partial close Fill carries exact close lineage and leaves truthful residual exposure;
- full close Fill carries exact lineage and produces only broker-derived zero exposure when actually flat;
- `OrderStatus.FILLED` without valid flat-position truth is not represented as definitive flat;
- overfill/over-close remains rejected;
- entry/protection request/fill behavior remains compatible;
- terminal/reconciliation/no-blind-retry safety remains compatible;
- no provider-native/credential fields are introduced.

Use real E4 production surfaces or sanitized fixtures. Do not encode E5 `POSITION_CLOSED`, TradeResult formulas or E6 persistence into E4 tests.

## Writable scope

E4-owned paths only:

- `src/execution/**`;
- `src/brokers/**`;
- `tests/execution/**`;
- `tests/brokers/**`;
- E4-specific `status/**` evidence/handoff;
- `coordination/E4/STATUS.md` on the target branch.

Forbidden:

- `contracts/**` / ADR edits;
- `src/risk/**` / `src/position/**`;
- E6 persistence/registry;
- E2/E3 production;
- E5 lifecycle or reason changes;
- TradeResult construction;
- E7 integration/release-gate changes;
- provider/private networking or credentials;
- OKX/Pionex Demo/live behavior;
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
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

Do not use GitHub Actions/CI/hosted runners, GitHub-triggered self-hosted compute, arbitrary cloud execution, Computer Adapter, provider/private APIs, or credentials. `NOT_RUN` is not PASS.

## Acceptance

### DONE

- E4 mechanically consumes accepted E5 `close-v0.1` authority without changing risk semantics;
- exact MARKET/reduce-only side/quantity/lineage/idempotency mapping is materialized;
- close Fill lineage and partial/full actual facts remain exact;
- E4 can expose safe provider-neutral residual/flat broker truth under existing shared semantics, without equating FILLED order with flat Position;
- prior protection/terminal/reconciliation behavior is not weakened;
- no E5/E6/provider/private/TradeResult/release-authority scope is crossed;
- deterministic tests are materialized;
- executable verification is approved-local evidence or explicit `NOT_RUN` with exact commands.

### BLOCKED

- existing shared Position/OrderRequest/Fill semantics cannot safely represent the required close/residual truth;
- record exact expected-vs-actual evidence and `next_owner = E7`;
- do not invent a workaround or broaden shared contracts.

Do not declare Paper E2E, TradeResult durable audit, Gate B/PAPER_READY, or any PAPER/SHADOW/LIVE authority PASS.

## Completion / mailbox rule

Commit/push bounded E4 code/tests/evidence/status to `agent/e4-gate-b-close-consumer-20260824`.

**Worker-owned terminal STATUS must be written and pushed to `coordination/E4/STATUS.md` on this target branch, not main**, so AgentBridge can observe terminal state and callback PM.

Then stop. Do not self-start E5 TradeResult builder, E6 persistence, E7 Paper E2E, approved-local verification, provider/private work, Gate C, PAPER, SHADOW, or LIVE.