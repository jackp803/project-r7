# E7 Current Task

- task_id: `E7-20260824-032`
- issued_at: `2026-08-24T11:56:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-b-protection-lifecycle-integration-20260824`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`, ADR-0004, accepted Gate A evidence PR #33, Gate B static preflight PR #34, accepted protection contract PR #37, accepted E5 producer PR #38, accepted E4 consumer PR #39, accepted E7 protection integration PR #40, accepted E5 protection-result bridge PR #41

## Objective

Perform the bounded E7 cross-module **static protection lifecycle integration and safety test-definition review** now that the E5 protection-result bridge is materialized:

```text
normalized Position actual exposure
-> E5 protection-v0.1 PositionAction.PROTECT
-> E4 canonical protection OrderRequest
-> E4/PaperBroker normalized submit/query/reconciliation truth
-> E5 interpret_protection_result(...)
-> existing E5 PositionEvent / state-machine outcome
```

Materialize only E7-owned integration/safety definitions that can be grounded in the accepted production APIs, reconcile the affected Gate B criterion, and identify the next bounded implementation owner if the real PaperBroker chain cannot yet materialize definitive protection failure/loss truth.

This task does **not** execute project code, modify E4/E5 production, add broker/provider behavior, add E6 persistence, close TradeResult, build full Paper E2E runtime, call provider/private APIs, or authorize PAPER/SHADOW/LIVE.

## Accepted prerequisites

### Shared protection boundary

```text
PR #37 merge = e6769b5b78f1b5f699ae4000204b803b2f8b69d5
profile = protection-v0.1
```

### E5 producer

```text
PR #38 merge = 268ac8708f84d0c856ac2d1d7436dcb100347a46
local executable verification = NOT_RUN
```

### E4 consumer

```text
PR #39 merge = 44ec171817f6c13fa632f2e7658dccc6b518f777
local executable verification = NOT_RUN
```

### E7 producer-consumer integration definitions

```text
PR #40 merge = 0c2202742c6fa601ac79b32603620a0553b95e2e
Required protection follows actual filled quantity = NOT_RUN
Drawdown/daily/position/kill-switch = NOT_RUN
Protection failure triggers emergency path = BLOCKED / IMPLEMENTATION_GAP at that review
```

### E5 protection-result lifecycle bridge

```text
PR #41
merge = 4c3d0f47d26cb23d9baeb17d227a3a1a9185667f
head = 4aeffaca987f4348912ed8691fc9b338b20f471a
bridge = src/position/protection_result.py
local executable verification = NOT_RUN
```

All prior `NOT_RUN` remains `NOT_RUN`. Static acceptance does not imply executable PASS.

## Required inspection

Read latest `main` and at minimum:

- `README.md`, `agents/README.md`, `agents/E7_INTEGRATION.md`;
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`, ADR-0004, execution object profiles;
- `status/RELEASE_GATES.md` and PR #40 review artifact;
- accepted E5 producer and `src/position/protection_result.py` plus tests/handoff;
- accepted E4 protection consumer and `src/execution/models.py`;
- real `src/brokers/paper.py` submit/query/fill/reconcile behavior and E4 broker tests;
- current E5 state machine;
- existing Gate B integration/safety definitions.

Do not patch E4/E5 domain code. If a genuine shared-contract contradiction is found, stop `BLOCKED / CONTRACT_OR_SEMANTIC_GAP` and record it instead of inventing integration glue.

## Required integration/safety definitions

Use the real accepted production APIs. Do not copy/reimplement E4/E5 semantics in E7 helpers.

At minimum define the following cross-module scenarios wherever the current callable APIs genuinely support them.

### 1. Positive protection verification chain

Materialize the real chain:

```text
E5 build_protect_position_action(...)
-> E4 prepare_protection_order(...)
-> PaperBroker.submit_order(...)
-> PaperBroker.query_order(...)
-> E5 ProtectionResultEvidence(query_performed=True, queried_order=...)
-> interpret_protection_result(..., OPEN_UNPROTECTED)
-> PROTECTION_VERIFIED -> OPEN_PROTECTED
```

Assert that submit `OPEN` alone without authoritative query never verifies protection.

### 2. Ambiguous submit / reconciliation behavior

Use real PaperBroker ambiguity/reconciliation primitives where possible.

Cover both safe classes:

- ambiguous submit actually accepted: explicit query + consistent reconciliation resolving the exact order to `OPEN` may verify;
- ambiguous submit not accepted / no exact order: no blind retry or healthy verification may be inferred; unresolved/`retry_allowed` evidence remains fail-closed/reconciliation-required for E5.

Do not let an E4 retry permission become an E5 retry authorization.

### 3. Identity / quantity / health fail-closed chain

Cross-module definitions must show that mismatched order/client identity, quantity inconsistency, degraded/unknown health, unknown/reconciliation-required status, or incompatible position reconciliation cannot yield `PROTECTION_VERIFIED`.

### 4. Triggered protective stop is not failure

Where PaperBroker Fill primitives are available, define that `PARTIALLY_FILLED` / `FILLED` protective-stop truth is not mislabeled by E5 as `PROTECTION_FAILED` or `PROTECTION_LOST`, and cannot directly prove TradeResult closure in this task.

Do not add TradeResult behavior.

## Definitive protection failure / loss capability review

Independently determine whether the **real current E4/PaperBroker callable path** can produce authoritative healthy exact-request truth for definitive inactive protection states required by the Gate B criterion, including at least:

```text
REJECTED
CANCELED
EXPIRED
```

and whether a previously verified protection can subsequently be observed as definitively lost.

Classify each as exactly one of:

```text
IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
IMPLEMENTATION_GAP
CONTRACT_OR_SEMANTIC_GAP
```

Important rules:

- Do not satisfy this system-level capability review merely by directly constructing a synthetic `OrderResult(REJECTED/CANCELED/EXPIRED)` inside an E7 integration test if the real PaperBroker/broker boundary has no callable way to produce/observe that truth.
- Unit-level E5 bridge fixtures may prove E5 interpretation semantics, but they are not evidence that the complete PaperBroker -> E5 failure/loss chain is materialized.
- If PaperBroker lacks the required provider-neutral failure/inactive-state behavior, identify the exact bounded E4 implementation gap and safe dependency order. Do not implement E4 behavior in E7.
- Existing shared models/state-machine vocabulary should remain sufficient unless inspection proves otherwise; if not, return a precise E7 contract blocker rather than guessing.

## Gate B evidence reconciliation

Reconcile only where justified by merged implementation and the new definitions.

- `Required protection follows actual filled quantity` remains `NOT_RUN` unless executable approved-local evidence later exists.
- `Drawdown/daily/position/kill-switch rules enforced` remains `NOT_RUN` unless executable approved-local evidence later exists.
- `Protection failure triggers emergency path` may move from `BLOCKED` to `NOT_RUN` **only if** the complete provider-neutral/PaperBroker callable failure/loss path is now materialized and the only missing evidence is approved-local execution.
- If the real broker/PaperBroker failure/loss source remains absent, keep `Protection failure triggers emergency path = BLOCKED / IMPLEMENTATION_GAP` and identify `next_owner = E4` with exact required behavior.
- `Restart/persistence preserves required state` remains `BLOCKED` unless new authoritative implementation exists.
- `Paper E2E closes to TradeResult and persists audit` remains `BLOCKED`; protection Fill lineage/close/audit gaps must not be hidden.
- No `NOT_RUN`, `BLOCKED`, or static label may become executable `PASS` in this task.

Record the exact post-review Gate B dependency map and next bounded PM recommendation.

## Writable scope

E7-owned paths only:

- `tests/integration/**`;
- cross-module `tests/safety/**`;
- `status/e7/**`;
- `status/INTEGRATION_STATUS.md`;
- `status/RELEASE_GATES.md` only for evidence reconciliation;
- `coordination/E7/STATUS.md` on the target branch.

Do not modify:

- `src/execution/**`, `src/brokers/**`;
- `src/risk/**`, `src/position/**`;
- E1/E2/E3/E6 production code;
- `contracts/**` or ADRs unless the task terminates on a genuine shared contradiction rather than editing them;
- provider/private networking or credentials;
- persistence/TradeResult implementation;
- PAPER/SHADOW/LIVE authority;
- GitHub Actions/CI/workflows.

## Executable verification

This task is **STATIC / TEST-DEFINITION ONLY**.

Do not run project code and do not request Local Runner actions. Record exactly:

```text
project executable verification = NOT_RUN / DEFERRED TO LATER APPROVED-LOCAL TASK
```

Do not use GitHub Actions/CI/hosted runner/GitHub-triggered compute, arbitrary cloud execution, Computer Adapter, provider/private APIs, or credentials.

## Acceptance

Allowed terminal outcomes:

### DONE

- E5 bridge is statically coherent with the real E4/PaperBroker normalized truth boundary;
- positive verification and ambiguity/fail-closed cross-module definitions are materialized using actual production APIs;
- definitive failure/loss capability is classified without synthetic system-level evidence substitution;
- affected Gate B statuses are reconciled without treating `NOT_RUN` as PASS;
- exact next bounded owner/task is identified if a real broker/PaperBroker implementation gap remains;
- Gate B remains BLOCKED unless every required criterion genuinely has PASS evidence, which is not expected;
- no provider/private/PAPER/SHADOW/LIVE activity occurs.

### BLOCKED

- a genuine shared contract/architecture contradiction prevents coherent integration/test definition;
- record exact expected-vs-actual semantics and affected producers/consumers;
- do not patch E4/E5 production code to hide it.

## Completion / mailbox rule

Commit/push bounded E7 tests/evidence/status changes to `agent/e7-gate-b-protection-lifecycle-integration-20260824`.

**Worker-owned terminal STATUS must be written and pushed to `coordination/E7/STATUS.md` on this target branch, not main**, so AgentBridge can observe terminal state and callback PM.

Then stop. Do not self-start E4 failure-state implementation, approved-local verification, restart/persistence, Fill lineage, full Paper E2E, provider/private work, Gate C, PAPER, SHADOW, or LIVE.