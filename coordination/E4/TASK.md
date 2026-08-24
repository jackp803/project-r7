# E4 Current Task

- task_id: `E4-20260824-005`
- issued_at: `2026-08-24T12:09:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-gate-b-paperbroker-protection-terminal-20260824`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`, ADR-0004, accepted Gate A PASS, accepted protection contract PR #37, accepted E5 producer PR #38, accepted E4 consumer PR #39, accepted E7 boundary review PR #40, accepted E5 result bridge PR #41, accepted E7 lifecycle integration review PR #42

## Objective

Implement only the E4-owned **provider-neutral PaperBroker protection terminal/inactive-state behavior** identified by E7-20260824-032:

```text
exact canonical protection OrderRequest
-> real callable PaperBroker normalized truth
-> queryable REJECTED | CANCELED | EXPIRED / definitive inactive state
```

The purpose is to materialize the missing E4 source of authoritative normalized truth so the already accepted E5 `interpret_protection_result(...)` bridge can later be exercised through the real PaperBroker boundary for `PROTECTION_FAILED` / `PROTECTION_LOST` semantics.

Stop at E4 PaperBroker/order truth. Do **not** call E5 lifecycle code, modify E5 risk semantics, add E6 persistence, propagate TradeResult closure, build full Paper E2E, call provider/private APIs, enable Demo/live execution, or authorize PAPER/SHADOW/LIVE.

## Accepted blocker evidence

E7 lifecycle integration review accepted in PR #42:

```text
PR #42
merge = 05181bf06e9d1f2ad71990b94c446b6bf66d3582

normal OPEN query -> E5 verification                      = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
ambiguous accepted/not-accepted reconciliation            = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
PARTIALLY_FILLED/FILLED triggered-stop handling            = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
real PaperBroker REJECTED source                           = IMPLEMENTATION_GAP
real PaperBroker CANCELED source                           = IMPLEMENTATION_GAP
real PaperBroker EXPIRED source                            = IMPLEMENTATION_GAP
verified OPEN -> definitive protection loss source         = IMPLEMENTATION_GAP
CONTRACT_OR_SEMANTIC_GAP                                   = NO
```

Current Gate B remains `BLOCKED`. All prior executable evidence remains `NOT_RUN`.

## Required inspection before editing

Read latest `main` and at minimum:

- `agents/E4_EXECUTION.md` and `agents/README.md`;
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`, ADR-0004, execution object profiles;
- `src/brokers/base.py` and `src/brokers/paper.py`;
- `src/execution/models.py` / `OrderStatus`, `ExecutionHealthStatus`, `OrderResult`, reconciliation semantics;
- accepted E4 protection consumer and E5 result bridge as read-only integration evidence;
- PR #42 artifact `status/e7/GATE_B_PROTECTION_LIFECYCLE_INTEGRATION_REVIEW_20260824.md`;
- existing `tests/brokers/**` and `tests/execution/**`.

Existing shared status vocabulary is sufficient according to E7. If implementation reveals a genuine need to change a shared contract, stop `BLOCKED / CONTRACT_OR_SEMANTIC_GAP`, record exact expected-vs-actual evidence, and return ownership to E7. Do not invent a private cross-module DTO.

## Required behavior

### 1. Real callable REJECTED truth

PaperBroker must expose a deterministic provider-neutral way for a sanitized Paper scenario to produce an exact protection request as definitive `REJECTED` truth through its **real callable surface**.

Requirements:

- `submit_order()` or another E4-owned PaperBroker simulation control may deterministically establish rejection for the exact `client_order_id`/request;
- the resulting `OrderResult` must preserve exact `order_request_id`, `client_order_id`, requested quantity and schema;
- `order_status = REJECTED`;
- `execution_health_status = HEALTHY` for definitive unambiguous Paper truth;
- `query_order(client_order_id)` must subsequently return the same definitive rejected truth rather than `None` or a reopened order;
- if rejection occurs before broker acceptance, `broker_order_id` may remain absent; do not invent exchange acceptance merely to populate an ID;
- repeated submission of the identical logical request must remain deterministic/idempotent and must not create exposure;
- a materially different request using the same client identity must retain existing idempotency-conflict behavior.

Do not make E4 decide `PROTECTION_FAILED`; E4 produces broker truth only.

### 2. Real callable OPEN -> CANCELED truth

For an existing exact protection order in queryable `OPEN` state, PaperBroker must provide a deterministic callable Paper transition to `CANCELED` and preserve:

- exact order/request/client lineage;
- existing non-empty broker order identity from the OPEN order;
- requested quantity and current filled quantity;
- `execution_health_status = HEALTHY`;
- explicit UTC `observed_at` for the terminal observation.

After transition, `query_order()` must return `CANCELED`. Repeated identical cancellation must be deterministic or explicitly idempotent; it must never reopen or duplicate the order.

### 3. Real callable OPEN -> EXPIRED truth

Materialize the equivalent deterministic Paper transition from an eligible `OPEN` protection order to `EXPIRED`, with the same identity/quantity/health/time requirements and queryability.

Expiry must be an explicit Paper simulation event/observation. Do not silently use parent entry-plan TTL as a protection-order expiry rule.

### 4. Previously verified protection can become definitively inactive

The same exact request must support this observable sequence without synthetic direct `OrderResult` construction outside the broker:

```text
submit -> query OPEN / HEALTHY
-> later PaperBroker terminal transition
-> query CANCELED or EXPIRED / HEALTHY
```

This is the E4 source required for the later E7 `PROTECTION_LOST` integration definition.

E4 must not itself invoke `PROTECTION_LOST`, `PROTECTION_FAILED`, `EMERGENCY`, or any E5 transition.

### 5. Strict transition safety

Fail closed for invalid Paper terminal-state operations.

At minimum:

- unknown client/order identity cannot be terminalized as if known;
- mismatched logical request identity remains an idempotency conflict;
- `FILLED` must not be rewritten to `CANCELED`, `EXPIRED`, or `REJECTED`;
- a triggered protection `PARTIALLY_FILLED` state must not be casually rewritten into failure/loss for this bounded task; if safe partial-fill cancellation semantics require broader close/exposure rules, leave them unsupported and fail explicitly;
- terminal `REJECTED/CANCELED/EXPIRED` must not later be reopened by repeat submit;
- no terminal operation may increase exposure or alter approved quantity/side/price fields.

### 6. Reconciliation / retry semantics remain safe

A definitive healthy terminal result is not ambiguous.

- `reconcile()` for an already definitive terminal order must resolve to that terminal status with `retry_allowed=false`;
- no terminal result may issue a retry token that could duplicate exposure;
- existing ambiguous submit accepted/not-accepted behavior from prior tasks must remain unchanged;
- E4 retry permission remains E4 execution information only; this task adds no E5 retry authority.

### 7. Paper-only and provider-neutral

This task must not add OKX/Pionex/private-provider fields, network calls, credentials, signatures, real exchange behavior, or live/Demo enablement.

Do not modify the shared `Broker` abstract interface merely to expose Paper test controls unless implementation proves a genuine cross-broker contract requirement; if so, stop and return to E7 rather than broadening this task.

## Required deterministic tests

Add E4-owned definitions covering at minimum:

- configured/controlled exact protection rejection -> `submit/query = REJECTED / HEALTHY`, zero exposure;
- repeated identical rejected submission remains rejected/idempotent;
- different request with same client identity remains conflict;
- `OPEN -> CANCELED` preserves exact IDs, broker ID, requested/filled quantity, health and UTC observation;
- `OPEN -> EXPIRED` preserves the same material;
- query after terminal transition returns the definitive terminal state;
- repeat terminal operation is deterministic/idempotent or explicitly safely rejected;
- repeat `submit_order()` after terminal state does not reopen the order;
- reconcile definitive terminal truth returns the terminal status with `retry_allowed=false` and no retry token;
- unknown-order terminal operation fails explicitly;
- `FILLED` cannot be terminalized as canceled/expired/rejected;
- `PARTIALLY_FILLED` is not reclassified as protection failure/loss by this task;
- existing normal OPEN, ambiguity/reconciliation, fill and entry behavior remain compatible;
- no provider-native fields or credentials are introduced.

Use sanitized/fake fixtures only. Do not encode E5 lifecycle semantics into E4 tests.

## Writable scope

E4-owned paths only:

- `src/brokers/paper.py`;
- `src/brokers/**` only if strictly necessary for PaperBroker-owned behavior and without shared-contract expansion;
- `tests/brokers/**`;
- `tests/execution/**` only for E4 no-regression/compatibility where required;
- E4-specific `status/**` evidence/handoff;
- `coordination/E4/STATUS.md` on the target branch.

Do not modify:

- `contracts/**` or ADRs;
- `src/risk/**` or `src/position/**`;
- E6 persistence/registry;
- E2/E3 code;
- provider/private networking or credentials;
- OKX/Pionex Demo/live execution;
- TradeResult closure/audit;
- PAPER/SHADOW/LIVE authority;
- GitHub Actions/CI/workflows.

## Executable verification

This is implementation/test-definition work. Project execution remains local-only.

If no explicitly PM/Product-Owner-approved Local Runner action exists for the exact clean target revision, record:

```text
local_verification = NOT_RUN
```

and provide exact future Windows PowerShell commands from repository root, at minimum:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
```

Do not use GitHub Actions/CI/hosted runners, GitHub-triggered self-hosted compute, arbitrary cloud execution, Computer Adapter, provider/private APIs, or credentials. `NOT_RUN` is not PASS.

## Acceptance

### DONE

- PaperBroker exposes real callable/queryable `REJECTED`, `CANCELED`, and `EXPIRED` protection truth under deterministic provider-neutral semantics;
- an exact previously queryable `OPEN` protection order can later be observed as definitively inactive without direct synthetic `OrderResult` substitution outside PaperBroker;
- identity, quantity, health, idempotency, reconciliation and no-blind-retry properties remain intact;
- filled/partial-fill states are not mislabeled or unsafely rewritten;
- no E5 lifecycle, provider/private, persistence, TradeResult, or release-authority scope is crossed;
- deterministic tests are materialized;
- executable verification is genuine approved-local evidence or explicitly `NOT_RUN` with exact commands.

### BLOCKED

- current shared semantics cannot safely represent the required behavior without a genuine shared-contract change;
- record exact expected-vs-actual evidence and `next_owner = E7`;
- do not invent a cross-module workaround.

Do not declare `Protection failure triggers emergency path` PASS and do not declare Gate B/PAPER_READY PASS.

## Completion / mailbox rule

Commit/push bounded code/tests/evidence to `agent/e4-gate-b-paperbroker-protection-terminal-20260824`.

**Worker-owned terminal STATUS must be written and pushed to `coordination/E4/STATUS.md` on this target branch, not main**, so AgentBridge can observe the terminal state and callback PM.

Then stop. Do not self-start E7 integration, approved-local verification, protection Fill lineage, restart/persistence, full Paper E2E, provider/private work, Gate C, PAPER, SHADOW, or LIVE.