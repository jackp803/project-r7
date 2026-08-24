# E5 Current Task

- task_id: `E5-20260824-012`
- issued_at: `2026-08-24T11:49:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e5-gate-b-protection-result-bridge-20260824`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`, ADR-0004, accepted Gate A PASS, accepted protection contract PR #37, accepted E5 producer PR #38, accepted E4 consumer PR #39, accepted E7 integration review PR #40

## Objective

Implement only the E5-owned **protection-result lifecycle interpretation bridge** required by Gate B:

```text
exact canonical protection OrderRequest
+ authoritative normalized E4/PaperBroker order/query/reconciliation truth
+ current E5 position lifecycle context
-> existing E5 PositionEvent / fail-closed lifecycle outcome
```

The bridge must distinguish verified active protection from definitive failure/loss and ambiguous/reconciliation-required truth. It must stop at E5 lifecycle interpretation/transition. Do not submit/retry/cancel/query broker orders from E5, modify PaperBroker/E4 code, add E6 persistence, close TradeResult, build full Paper E2E, call provider/private APIs, or authorize PAPER/SHADOW/LIVE.

## Accepted prerequisite / blocker classification

E7 static integration review accepted in PR #40:

```text
PR #40
merge = 0c2202742c6fa601ac79b32603620a0553b95e2e
E5 PositionAction producer = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
E4 protection OrderRequest translator = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
PaperBroker generic submit/query/reconcile = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
E5 broker-truth -> lifecycle-event bridge = IMPLEMENTATION_GAP
Protection failure -> EMERGENCY integrated behavior = IMPLEMENTATION_GAP
Protection lost -> EMERGENCY integrated behavior = IMPLEMENTATION_GAP
CONTRACT_OR_SEMANTIC_GAP = NO for the reviewed protection request/result boundary
```

Current Gate B remains BLOCKED. `NOT_RUN` remains `NOT_RUN`.

## Required inspection before editing

Read latest `main` and at minimum:

- `agents/E5_RISK_POSITION.md` and `agents/README.md`;
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md` and ADR-0004;
- accepted E5 producer `src/position/protection.py`;
- accepted E4 `src/execution/models.py` and `src/execution/protection.py` as read-only shared truth semantics;
- `src/brokers/paper.py` as read-only evidence for normalized `OrderResult`, query and reconciliation behavior;
- `src/position/state_machine.py`;
- PR #40 artifact `status/e7/GATE_B_PROTECTION_INTEGRATION_REVIEW_20260824.md` and relevant Gate B integration/safety definitions.

Do not reinterpret shared contracts. If implementation requires a new shared serialized object or exposes a genuine cross-module semantic ambiguity, stop `BLOCKED / CONTRACT_OR_SEMANTIC_GAP` and return ownership to E7 rather than inventing a private cross-module contract.

## Core authority boundary

E4 remains authoritative for broker/order/query/reconciliation truth. E5 must not call a broker or infer provider state.

E5 owns only the risk/lifecycle interpretation of normalized evidence already supplied to it.

A submit acknowledgement alone is never sufficient to claim protection verification. The bridge must require explicit authoritative order/query truth for the exact protection request before emitting `PROTECTION_VERIFIED`.

## Required behavior

### 1. Bind to one exact protection authority

Only interpret evidence for a canonical request that is clearly the accepted protection path:

```text
schema_version = contracts-v0.1
authorization_type = POSITION_ACTION
order_role = PROTECTION_STOP
position_action_id = non-empty
position_id = non-empty
risk_decision_id = non-empty
order_type = STOP_MARKET
reduce_only = true
```

The request's exact `order_request_id`, `client_order_id`, `trade_plan_id`, `position_action_id`, `position_id`, `risk_decision_id`, symbol, side and quantity remain immutable lineage for this bridge.

Malformed/non-protection requests must fail closed and must never create a verified-protection event.

### 2. Distinguish submit result from authoritative verification

Do not equate these with verification by themselves:

- PositionAction creation;
- OrderRequest creation;
- `submit_order()` return;
- local intent that the order should exist.

For initial protection, `PROTECTION_VERIFIED` may be emitted only when an explicit authoritative queried/observed order truth for the exact request proves the protective order is active/effective without reconciliation ambiguity.

For current V1 normalized semantics, the minimum positive case must require all of:

```text
queried OrderResult identifies exact order_request_id/client_order_id
order_status = OPEN
execution_health_status = HEALTHY
broker_order_id = known/non-empty
requested_quantity = exact protection OrderRequest.quantity
0 <= filled_quantity <= requested_quantity
current lifecycle = OPEN_UNPROTECTED
no contradictory reconciliation evidence
```

Do not use the expired parent entry-plan TTL as protection-result freshness or authority.

### 3. Definitive initial protection failure

For a position still `OPEN_UNPROTECTED`, definitive broker truth for the exact protective order that establishes it cannot become/remain active must map to the existing:

```text
PositionEvent.PROTECTION_FAILED
```

and applying the existing state machine must yield:

```text
OPEN_UNPROTECTED + PROTECTION_FAILED -> EMERGENCY
```

At minimum cover definitive exact-request statuses such as:

```text
REJECTED
CANCELED
EXPIRED
```

provided the evidence is healthy/unambiguous and identity-consistent.

Do not classify an ambiguous/mismatched/degraded observation as definitive failure merely to avoid reconciliation.

### 4. Previously verified protection loss

When current lifecycle is `OPEN_PROTECTED` or `PROFIT_PROTECTED`, definitive healthy/unambiguous broker truth showing the exact required protective order is no longer active must map to:

```text
PositionEvent.PROTECTION_LOST
```

and the existing state machine must yield `EMERGENCY` for those protected states.

The bridge must not silently recreate or retry protection; E5 does not own broker retry/submission.

### 5. Unknown / reconciliation-required truth is never verified

Any of the following must fail closed to the existing reconciliation/unknown lifecycle path, never `PROTECTION_VERIFIED`:

- `OrderStatus.UNKNOWN`;
- `OrderStatus.RECONCILIATION_REQUIRED`;
- `ExecutionHealthStatus.UNKNOWN` or `DEGRADED` where authoritative health is insufficient;
- mismatched request/client/order lineage;
- contradictory query/reconciliation inputs;
- required explicit query not performed / no authoritative queried order truth supplied;
- current normalized position/order truth is itself unreconciled or incompatible.

Use existing `PositionEvent.STATE_UNKNOWN` / `RECONCILIATION_REQUIRED` semantics where applicable rather than inventing a healthy-looking fallback.

### 6. Query-not-found must be distinguishable from not-queried

The implementation must not collapse these two states:

```text
A) authoritative query was not performed / result unavailable
B) authoritative query completed and the exact protection order was not found
```

A is unknown/reconciliation-required.

B may be definitive protection failure/loss only when the accompanying normalized evidence is mutually consistent and sufficient to establish absence for the exact protection authority; otherwise remain fail-closed/reconciliation-required.

You may use a small **E5-internal, non-serialized helper/value object** to keep this distinction explicit. Do not create a new cross-module/shared contract or persisted DTO.

### 7. Ambiguous submit/reconciliation handling

If submit truth was `UNKNOWN` / `RECONCILIATION_REQUIRED`, E5 must not authorize retry and must not treat the original submit as verified.

If E4 later supplies consistent reconciliation plus an exact authoritative queried `OPEN / HEALTHY` order, the bridge may verify protection.

If reconciliation remains `UNKNOWN` / `RECONCILIATION_REQUIRED`, emit only fail-closed unknown/reconciliation behavior.

Any `retry_allowed` flag is E4 execution information only; this task must not call or authorize `retry_order()`.

### 8. Triggered/filled protection is not the same as active protection loss

Do **not** map `PARTIALLY_FILLED` or `FILLED` protective-stop order status to `PROTECTION_FAILED` or `PROTECTION_LOST` by assumption.

Those states may represent the protective exit actually triggering. Without the later authoritative position-close / TradeResult closure chain, they must not be mislabeled as failed protection. Keep them fail-closed / reconciliation-required for this bounded bridge unless an already-existing exact contract/state-machine rule unambiguously resolves them without expanding scope.

Do not implement TradeResult closure in this task.

### 9. Apply only existing lifecycle events/transitions

Use the existing E5 state machine. This task may produce/apply only existing semantics such as:

```text
PROTECTION_VERIFIED
PROTECTION_FAILED
PROTECTION_LOST
STATE_UNKNOWN
```

Do not add a direct request/submission -> `OPEN_PROTECTED` shortcut.

Do not add new lifecycle enum values unless a genuine missing shared semantic forces a terminal E7 blocker instead.

## Required deterministic tests

Add E5-owned tests covering at minimum:

- exact protection request + submit `OPEN` only, without authoritative query -> never `PROTECTION_VERIFIED`;
- exact authoritative queried `OPEN / HEALTHY` order -> `PROTECTION_VERIFIED` and `OPEN_UNPROTECTED -> OPEN_PROTECTED`;
- missing/blank broker order identity cannot verify protection;
- request/order ID or client ID mismatch -> `STATE_UNKNOWN` / reconciliation-required, never verified;
- `UNKNOWN` / `RECONCILIATION_REQUIRED` order status -> fail-closed unknown path;
- degraded/unknown execution health -> fail-closed unknown path;
- initial `REJECTED`, `CANCELED`, `EXPIRED` exact healthy truth -> `PROTECTION_FAILED -> EMERGENCY`;
- already `OPEN_PROTECTED` / `PROFIT_PROTECTED` with definitive protection disappearance/failure -> `PROTECTION_LOST -> EMERGENCY`;
- query-not-performed differs from authoritative query-not-found;
- ambiguous submit later reconciled to exact `OPEN / HEALTHY` may verify only after authoritative evidence arrives;
- contradictory reconciliation/query truth never verifies protection;
- `PARTIALLY_FILLED` / `FILLED` are not mislabeled as failure/loss and do not directly produce protected state;
- repeated identical authoritative evidence is deterministic;
- bridge never calls broker retry/submission and contains no provider-native semantics;
- existing state-machine behavior remains unchanged outside the bridge.

Tests must use existing shared E4 model semantics or sanitized mappings/fixtures. Do not fake a new shared protocol in test-only code.

## Writable scope

E5-owned paths only:

- `src/position/**`;
- `src/risk/**` only if strictly required for E5 lifecycle/risk interpretation;
- `tests/position/**`;
- `tests/risk/**` or `tests/safety/**` only for E5-owned fail-closed coverage;
- E5-specific `status/**` handoff/evidence;
- `coordination/E5/STATUS.md` on the target branch.

Forbidden:

- `contracts/**` / ADR edits;
- `src/execution/**` or `src/brokers/**`;
- E6 persistence/registry;
- E2/E3 code;
- provider/private API or credentials;
- PaperBroker modifications;
- TradeResult persistence/closure;
- PAPER/SHADOW/LIVE mode authority;
- GitHub Actions/CI/workflows.

## Executable verification

This task is implementation/test-definition work before the later approved-local integration run.

Do not request GitHub compute. If there is no explicitly PM/Product-Owner-approved exact-revision Local Runner action for this new branch, record:

```text
local_verification = NOT_RUN
```

with exact future Windows PowerShell commands at minimum:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

Do not use GitHub Actions/CI/hosted runners, GitHub-triggered self-hosted compute, arbitrary cloud execution, Computer Adapter, provider/private APIs, or credentials. `NOT_RUN` is not PASS.

## Acceptance

### DONE

- callable E5 protection-result lifecycle bridge exists;
- submit intent alone cannot verify protection;
- exact healthy authoritative queried active-order truth can produce `PROTECTION_VERIFIED`;
- definitive initial failure maps to `PROTECTION_FAILED -> EMERGENCY`;
- definitive loss after verified protection maps to `PROTECTION_LOST -> EMERGENCY`;
- unknown/ambiguous/mismatched/reconciliation-required truth fails closed;
- filled/partially-filled protective exits are not mislabeled as protection failure/loss;
- no E4/broker/provider/persistence/TradeResult/release scope is crossed;
- deterministic tests are materialized;
- executable verification is genuine approved-local evidence or explicitly `NOT_RUN` with commands.

### BLOCKED

- existing shared normalized evidence is insufficient to distinguish required lifecycle outcomes safely, or a new shared serialized contract is genuinely required;
- record exact expected-vs-actual semantic evidence and `next_owner = E7`;
- do not invent a cross-module workaround.

Do not declare `Protection failure triggers emergency path` PASS and do not declare Gate B/PAPER_READY PASS.

## Completion / mailbox rule

Commit/push bounded implementation/tests/evidence to `agent/e5-gate-b-protection-result-bridge-20260824`.

**Worker-owned terminal STATUS must be written and pushed to `coordination/E5/STATUS.md` on this target branch, not main**, so AgentBridge can observe terminal state and callback PM.

Then stop. Do not self-start E7 integration, restart/persistence, E4 Fill lineage, Paper E2E, provider/private work, Gate C, PAPER, SHADOW, or LIVE.