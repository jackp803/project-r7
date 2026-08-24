# E4 Current Task

- task_id: `E4-20260824-007`
- issued_at: `2026-08-24T12:35:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-gate-b-protection-fill-lineage-20260824`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0004, accepted Gate A PASS, protection contract PR #37, E5 producer PR #38, E4 consumer PR #39, E7 reviews PR #40/#42/#44, E5 result bridge PR #41, E4 PaperBroker terminal truth PR #43

## Objective

Implement only the E4-owned **PaperBroker protection Fill lineage propagation** required by `protection-v0.1` and identified by E7-20260824-034:

```text
canonical protection OrderRequest
-> PaperBroker.record_fill(...)
-> canonical Fill retaining exact protection authority lineage
```

For a Fill produced from a `protection-v0.1` protection-authorized request, the existing shared `Fill` fields must retain the originating request's exact:

```text
trade_plan_id
position_action_id
position_id
order_role = PROTECTION_STOP
```

Stop at E4 Fill truth. Do **not** implement E5 close lifecycle semantics, TradeResult construction, E6 persistence/audit, full Paper E2E, provider/private APIs, Demo/live behavior, or PAPER/SHADOW/LIVE authorization.

## Accepted prerequisite / blocker evidence

E7 protection-failure integration review accepted in PR #44:

```text
PR #44
merge = c431125c03b53b6aff4e5b2cd7715c445f5a33f9
head = 9fbf9ff74e61cd169a767f912e9572a1560d29a9
Protection failure triggers emergency path = NOT_RUN / implementation + real definitions materialized
Paper E2E -> TradeResult + durable audit = BLOCKED / IMPLEMENTATION_GAP
next_owner = E4
bounded_dependency = PaperBroker protection Fill lineage propagation
```

The shared model already supports the required additive fields; this task must not change shared contracts merely to populate them.

Current Gate B remains `BLOCKED`. All prior executable evidence remains `NOT_RUN`.

## Required inspection before editing

Read latest `main` and at minimum:

- `agents/E4_EXECUTION.md` and `agents/README.md`;
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md` section 10 and execution object profiles;
- `src/execution/models.py` `OrderRequest` and `Fill`;
- current `src/brokers/paper.py` including `record_fill()` and terminal-state behavior;
- accepted E4 protection translator `src/execution/protection.py`;
- PR #44 artifact `status/e7/GATE_B_PROTECTION_FAILURE_INTEGRATION_REVIEW_20260824.md`;
- existing broker/execution tests involving entry and protection fills.

If a genuine shared-contract contradiction is found, stop `BLOCKED / CONTRACT_OR_SEMANTIC_GAP` and return ownership to E7. Do not invent a parallel Fill DTO or broaden the shared contract.

## Required behavior

### 1. Exact lineage propagation for protection Fill

When the originating stored `OrderRequest` is the accepted protection path, `record_fill()` must construct each `Fill` with exact lineage copied from that request:

```text
Fill.trade_plan_id       = OrderRequest.trade_plan_id
Fill.position_action_id  = OrderRequest.position_action_id
Fill.position_id         = OrderRequest.position_id
Fill.order_role          = OrderRequest.order_role
```

For the canonical protection path, `order_role` must therefore remain `PROTECTION_STOP`.

Do not derive these values from provider fields, broker order IDs, symbol, side, or heuristics. The source is the exact stored originating canonical request.

### 2. Partial and full fills retain the same authority

For one exact protection request:

```text
OPEN -> PARTIALLY_FILLED -> FILLED
```

all emitted Fill objects must carry the same exact parent/action/position/order-role lineage while preserving each Fill's own actual quantity, price, timestamp, fee and liquidity facts.

No Fill may claim a quantity larger than the actual recorded fill or the existing remaining approved request quantity.

### 3. Legacy/entry compatibility

Existing entry-path behavior must remain additive-compatible.

For an entry `OrderRequest` that has no protection PositionAction lineage:

```text
Fill.position_action_id = None
Fill.position_id = None
Fill.order_role = None
```

Do not manufacture protection lineage for entry fills and do not require legacy entry requests to contain protection-only fields.

### 4. Query/audit preservation

`query_fills(client_order_id)` must return Fill objects with the same lineage originally emitted by `record_fill()`.

Repeated reads must not mutate or erase lineage. Existing deterministic fill identity/idempotency behavior must remain unchanged unless a demonstrated defect requires a terminal blocker rather than scope expansion.

### 5. Terminal/reconciliation behavior unchanged

Do not weaken PR #43 terminal truth semantics:

- REJECTED/CANCELED/EXPIRED/FILLED cannot receive invalid later fills;
- PARTIALLY_FILLED terminalization remains outside this task;
- ambiguous submit/reconciliation/no-blind-retry behavior remains unchanged;
- no Fill lineage field grants retry, lifecycle, risk, or release authority.

### 6. Provider-neutral scope

Do not add OKX/Pionex/private-provider fields, contract counts, network calls, credentials, signatures, or provider-native fill semantics to the canonical Fill.

Provider-native audit facts remain outside this bounded task.

## Required deterministic tests

Add or update E4-owned test definitions covering at minimum:

- protection partial Fill contains exact `trade_plan_id`, `position_action_id`, `position_id`, `order_role=PROTECTION_STOP` from the originating request;
- subsequent full Fill for the same protection request carries the same lineage;
- emitted Fill quantity remains the exact actual per-fill quantity and total cannot exceed request quantity;
- `query_fills()` preserves exact lineage and ordering;
- LONG/SELL and SHORT/BUY protection requests do not alter lineage semantics;
- entry/legacy Fill retains existing `trade_plan_id` but protection-only lineage remains `None`;
- rejected/canceled/expired orders still cannot receive fills;
- existing normal/ambiguous/reconciliation/terminal behavior remains compatible;
- no provider-native or credential fields are introduced.

Tests must use canonical E4 production request/model surfaces or sanitized fixtures. Do not encode E5 lifecycle or TradeResult behavior into E4 tests.

## Writable scope

E4-owned paths only:

- `src/brokers/paper.py`;
- `tests/brokers/**`;
- `tests/execution/**` only if strictly required for E4 compatibility coverage;
- E4-specific `status/**` handoff/evidence;
- `coordination/E4/STATUS.md` on the target branch.

Forbidden:

- `contracts/**` or ADR edits;
- `src/risk/**` / `src/position/**`;
- E6 persistence/registry;
- E2/E3 production;
- shared `Fill` model expansion unless terminating on a genuine E7 blocker rather than editing it;
- TradeResult construction/closure;
- provider/private networking or credentials;
- OKX/Pionex Demo/live behavior;
- PAPER/SHADOW/LIVE authority;
- GitHub Actions/CI/workflows.

## Executable verification

This is implementation/test-definition work. Project execution remains local-only.

If no explicitly PM/Product-Owner-approved Local Runner action exists for the exact clean target revision, record:

```text
local_verification = NOT_RUN
```

with exact future Windows PowerShell commands at minimum:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
```

Do not use GitHub Actions/CI/hosted runners, GitHub-triggered self-hosted compute, arbitrary cloud execution, Computer Adapter, provider/private APIs, or credentials. `NOT_RUN` is not PASS.

## Acceptance

### DONE

- protection-origin PaperBroker Fill objects carry exact existing shared protection lineage from the originating request;
- partial and full protection fills preserve the same authority lineage while retaining actual per-fill quantity;
- entry/legacy Fill compatibility remains intact with no invented protection lineage;
- query_fills preserves the lineage;
- PR #43 terminal/idempotency/reconciliation safety is not weakened;
- no shared contract, E5 lifecycle, TradeResult, persistence, provider/private, or release-authority scope is crossed;
- deterministic tests are materialized;
- executable verification is genuine approved-local evidence or explicitly `NOT_RUN` with exact commands.

### BLOCKED

- existing shared Fill/request semantics are insufficient or contradictory for safe lineage propagation;
- record exact expected-vs-actual evidence and `next_owner = E7`;
- do not invent a workaround.

Do not declare `Paper E2E closes to TradeResult and persists audit` PASS and do not declare Gate B/PAPER_READY PASS.

## Completion / mailbox rule

Commit/push bounded code/tests/evidence to `agent/e4-gate-b-protection-fill-lineage-20260824`.

**Worker-owned terminal STATUS must be written and pushed to `coordination/E4/STATUS.md` on this target branch, not main**, so AgentBridge can observe terminal state and callback PM.

Then stop. Do not self-start E7 integration, close-to-TradeResult semantics, restart/persistence, full Paper E2E, approved-local verification, provider/private work, Gate C, PAPER, SHADOW, or LIVE.