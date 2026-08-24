# E7 Current Task

- task_id: `E7-20260824-034`
- issued_at: `2026-08-24T12:22:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-b-protection-failure-integration-20260824`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`, ADR-0004, accepted Gate A evidence PR #33, Gate B static preflight PR #34, protection contract PR #37, E5 producer PR #38, E4 consumer PR #39, E7 boundary review PR #40, E5 result bridge PR #41, E7 lifecycle review PR #42, accepted E4 PaperBroker terminal truth PR #43

## Objective

Perform the bounded E7 cross-module **static protection failure/loss integration and safety test-definition review** now that E4 has materialized real provider-neutral PaperBroker terminal truth:

```text
E5 PositionAction.PROTECT
-> E4 protection OrderRequest
-> PaperBroker submit/query/reconcile
-> real REJECTED or OPEN -> CANCELED/EXPIRED truth
-> E5 interpret_protection_result(...)
-> existing PROTECTION_FAILED / PROTECTION_LOST lifecycle event
-> existing EMERGENCY state transition
```

Use only accepted production APIs and real PaperBroker callable terminal-state controls. Determine whether `Protection failure triggers emergency path` can now move from `BLOCKED` to `NOT_RUN` because the complete provider-neutral callable path is materialized, while preserving that executable evidence has not run.

This task is static/test-definition only. It does **not** execute project code, modify E4/E5 production, add E6 persistence, propagate TradeResult closure, call provider/private APIs, or authorize PAPER/SHADOW/LIVE.

## Accepted prerequisites

```text
PR #41
merge = 4c3d0f47d26cb23d9baeb17d227a3a1a9185667f
E5 bridge = normalized protection truth -> existing lifecycle event/outcome
local verification = NOT_RUN

PR #42
merge = 05181bf06e9d1f2ad71990b94c446b6bf66d3582
prior disposition = protection failure emergency BLOCKED because real PaperBroker terminal truth was absent

PR #43
merge = d9394c18ca35406831e8966700c3a5210966fbb6
head = 1cded31e141912f2bfe86d04621973182d7bfc05
PaperBroker now materializes real queryable REJECTED / OPEN->CANCELED / OPEN->EXPIRED healthy terminal truth
local verification = NOT_RUN
```

All prior `NOT_RUN` remains `NOT_RUN`. Static acceptance never implies executable PASS.

## Required inspection

Read latest `main` and at minimum:

- `README.md`, `agents/README.md`, `agents/E7_INTEGRATION.md`;
- protection/execution contracts and ADR-0004;
- `status/RELEASE_GATES.md` and PR #42 lifecycle review artifact;
- accepted E5 producer/result bridge and state machine;
- accepted E4 protection translator and current `src/brokers/paper.py` from PR #43;
- E4 PR #43 broker tests/handoff;
- existing Gate B integration/safety definitions.

Do not patch E4/E5 domain code. If a genuine shared-contract contradiction appears, stop `BLOCKED / CONTRACT_OR_SEMANTIC_GAP` with exact evidence rather than inventing E7 glue.

## Required real cross-module definitions

Use actual production APIs. Do not directly construct synthetic terminal `OrderResult` values as a substitute for PaperBroker behavior.

### 1. Initial definitive rejection -> emergency

Materialize the real sequence:

```text
build_protect_position_action(...)
-> prepare_protection_order(...)
-> PaperBroker configured deterministic rejection
-> submit_order(...) = REJECTED / HEALTHY
-> query_order(...) = exact REJECTED truth
-> ProtectionResultEvidence(query_performed=True, queried_order=...)
-> interpret_protection_result(..., OPEN_UNPROTECTED)
-> PROTECTION_FAILED
-> EMERGENCY
```

Assert exact request/client/quantity lineage and that no retry authority is created.

### 2. Verified OPEN -> CANCELED -> protection lost -> emergency

Materialize with one exact request:

```text
submit -> query OPEN / HEALTHY
-> E5 PROTECTION_VERIFIED -> OPEN_PROTECTED
-> PaperBroker.cancel_order(...)
-> query exact CANCELED / HEALTHY
-> E5 PROTECTION_LOST
-> EMERGENCY
```

No direct/synthetic terminal result construction outside PaperBroker.

### 3. Verified OPEN -> EXPIRED -> protection lost -> emergency

Materialize the equivalent real path using `expire_order(...)` and assert exact identity/quantity/broker-order lineage survives into terminal truth.

Expiry must remain an explicit Paper observation; do not reinterpret entry-plan or PositionAction TTL.

### 4. Reconciliation/no-retry safety

For real `REJECTED`, `CANCELED`, and `EXPIRED` PaperBroker truth:

- `reconcile()` resolves the definitive current terminal status;
- `retry_allowed=false`;
- no retry token;
- E5 receives only normalized truth and never gains broker retry authority.

### 5. Invalid terminal behavior remains fail closed

Ground definitions in the real E4 surface showing at least:

- unknown order cannot be terminalized;
- FILLED cannot become CANCELED/EXPIRED;
- PARTIALLY_FILLED is not reclassified into protection failure/loss by this path;
- terminal order cannot reopen on repeated submit;
- terminal order cannot receive later fill/exposure.

Do not broaden into partial-fill close semantics or TradeResult closure.

## Gate B evidence reconciliation

Update E7-owned release/integration evidence only if justified by merged production paths and these definitions.

Expected decision rule:

- `Required protection follows actual filled quantity` stays `NOT_RUN`.
- `Drawdown/daily/position/kill-switch rules enforced` stays `NOT_RUN`.
- `Protection failure triggers emergency path` may move from `BLOCKED` to `NOT_RUN` **only if** the complete real provider-neutral PaperBroker -> E5 failure/loss -> EMERGENCY path is now statically materialized and only approved-local executable evidence remains.
- It must not become `PASS` in this task.
- `Restart/persistence preserves required state` remains `BLOCKED` unless authoritative implementation evidence has appeared.
- `Paper E2E closes to TradeResult and persists audit` remains `BLOCKED`; do not hide the known protection Fill lineage / close / durable-audit gaps.

Record the exact post-review dependency map. If the protection-failure implementation blocker is removed, identify the next bounded PM dependency among remaining Gate B blockers without self-starting it.

## Writable scope

E7-owned paths only:

- `tests/integration/**`;
- cross-module `tests/safety/**`;
- `status/e7/**`;
- `status/INTEGRATION_STATUS.md`;
- `status/RELEASE_GATES.md` for evidence reconciliation;
- `coordination/E7/STATUS.md` on the target branch.

Do not modify:

- `src/execution/**`, `src/brokers/**`;
- `src/risk/**`, `src/position/**`;
- E1/E2/E3/E6 production code;
- `contracts/**` or ADRs unless terminating on a genuine shared contradiction;
- provider/private networking or credentials;
- persistence/TradeResult implementation;
- PAPER/SHADOW/LIVE authority;
- GitHub Actions/CI/workflows.

## Executable verification

This task is **STATIC / TEST-DEFINITION ONLY**. Do not execute project code and do not request Local Runner actions.

Record exactly:

```text
project executable verification = NOT_RUN / DEFERRED TO LATER APPROVED-LOCAL TASK
```

Do not use GitHub Actions/CI/hosted runners/GitHub-triggered compute, arbitrary cloud execution, Computer Adapter, provider/private APIs, or credentials.

## Acceptance

### DONE

- real PaperBroker terminal-state behavior from PR #43 is statically coherent with the accepted E5 result bridge;
- real REJECTED -> PROTECTION_FAILED -> EMERGENCY definition exists;
- real verified OPEN -> CANCELED/EXPIRED -> PROTECTION_LOST -> EMERGENCY definitions exist;
- reconciliation/no-retry and invalid-terminal safety are covered using real production APIs;
- affected Gate B status is reconciled without treating `NOT_RUN` as PASS;
- remaining exact Gate B implementation dependencies are identified;
- no provider/private/PAPER/SHADOW/LIVE activity occurs.

### BLOCKED

- a genuine contract/architecture contradiction prevents coherent real failure/loss integration;
- record exact expected-vs-actual semantics and affected owners;
- do not patch E4/E5 production to hide it.

## Completion / mailbox rule

Commit/push bounded E7 tests/evidence/status changes to `agent/e7-gate-b-protection-failure-integration-20260824`.

**Worker-owned terminal STATUS must be written and pushed to `coordination/E7/STATUS.md` on this target branch, not main**, so AgentBridge can observe terminal state and callback PM.

Then stop. Do not self-start approved-local verification, protection Fill lineage, restart/persistence, full Paper E2E, provider/private work, Gate C, PAPER, SHADOW, or LIVE.