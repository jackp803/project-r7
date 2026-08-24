# E7 Current Task

- task_id: `E7-20260824-030`
- issued_at: `2026-08-24T11:28:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-b-protection-integration-20260824`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`, ADR-0004, accepted Gate A evidence PR #33, Gate B static preflight PR #34, accepted protection contract PR #37, accepted E5 producer PR #38, accepted E4 consumer PR #39

## Objective

Perform the bounded E7 cross-module **static integration and safety test-definition review** now that both sides of `protection-v0.1` are materialized:

```text
normalized Position actual exposure
-> E5 protection-v0.1 PositionAction.PROTECT
-> E4 canonical protection OrderRequest
```

Materialize only the E7-owned integration/safety definitions that can be grounded in the accepted interfaces, reconcile the affected Gate B evidence statuses, and identify the exact next implementation dependency for any still-blocked protection-failure / verification behavior.

This task does **not** execute project code, submit broker orders, call provider/private APIs, implement E4/E5 domain behavior, add E6 persistence, build a complete Paper E2E runtime, or authorize PAPER/SHADOW/LIVE.

## Accepted prerequisites

### Shared contract

```text
PR #37
merge = e6769b5b78f1b5f699ae4000204b803b2f8b69d5
profile = protection-v0.1
ADR = docs/adr/ADR-0004-actual-fill-protection-action-boundary.md
```

### E5 producer

```text
PR #38
merge = 268ac8708f84d0c856ac2d1d7436dcb100347a46
head = b98188691f7b9468204bf4f8f3164c07367741db
producer = src/position/protection.py
local executable verification = NOT_RUN
```

### E4 consumer

```text
PR #39
merge = 44ec171817f6c13fa632f2e7658dccc6b518f777
head = 5dd502f53b3eeb564ee917a8c5fa2090074908bc
consumer = src/execution/protection.py + additive OrderRequest/Fill lineage
local executable verification = NOT_RUN
```

All prior `NOT_RUN` remains `NOT_RUN`. Do not infer executable PASS from static implementation acceptance.

## Required inspection

Read latest `main` and at minimum:

- `README.md`, `agents/README.md`, `agents/E7_INTEGRATION.md`;
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`, ADR-0004, execution object profiles;
- `status/RELEASE_GATES.md` and `status/e7/GATE_B_STATIC_PREFLIGHT_20260824.md`;
- accepted E5 producer implementation/tests/handoff;
- accepted E4 consumer implementation/tests/handoff;
- current E5 position lifecycle state machine;
- relevant PaperBroker / E4 order-result and reconciliation primitives as read-only evidence;
- existing `tests/integration/**` and `tests/safety/**`.

Do not modify E4/E5 production code. If integration review reveals a genuine shared-contract contradiction, stop `BLOCKED / CONTRACT_OR_SEMANTIC_GAP` and record the exact inconsistency instead of patching domain code.

## Required static integration definitions

Materialize deterministic E7-owned integration/safety test definitions for the **implemented producer -> consumer boundary**. At minimum prove by test definition that:

1. **Partial fill uses exact actual exposure end to end**
   - parent ApprovedTradePlan maximum/requested quantity may be larger;
   - normalized Position actual quantity is smaller;
   - E5 action quantity equals exact Position actual quantity;
   - E4 protection OrderRequest quantity equals that same action/actual quantity;
   - requested/approved maximum cannot substitute for actual exposure.

2. **Full fill preserves exact canonical quantity**
   - full actual quantity propagates E5 -> E4 without provider-native unit leakage.

3. **No protection-bound loosening**
   - E5 action binds exact parent stop/target/max-hold values;
   - tampered/loosened action material cannot be consumed by E4;
   - E4 request stop price is exact approved stop and E4 does not invent target/OCO/timer behavior.

4. **Authority and idempotency lineage is exact**
   - `trade_plan_id`, `risk_decision_id`, `position_id`, `position_action_id`, quantity profile/unit/asset and `order_role=PROTECTION_STOP` remain coherent;
   - identical action -> deterministic request identity;
   - materially different immediate PositionAction -> different logical request identity/fingerprint.

5. **Fail closed on ambiguous execution truth**
   - unknown, `MISMATCH`, or `RECONCILIATION_REQUIRED` current Position cannot produce/consume safe executable protection;
   - over-approved actual exposure cannot silently expand ordinary E5/E4 authority;
   - legacy/missing/unsupported protection profile and `MODIFY_PROTECTION` remain non-executable.

6. **Fresh post-fill authority is independent of entry TTL**
   - an expired parent entry TTL alone must not invalidate a still-valid post-fill PositionAction;
   - expired PositionAction itself fails closed.

7. **Request/submission intent is not verification**
   - producing PositionAction or preparing OrderRequest does not mutate/claim `OPEN_PROTECTED` or `PROTECTION_VERIFIED`;
   - the position remains `OPEN_UNPROTECTED` until later verified broker truth is explicitly consumed by E5.

Use the real accepted E5/E4 production APIs. Do not copy/reimplement their semantics inside the E7 test helper layer.

## Protection verification/failure gap review

Separately inspect whether the repository currently has a complete callable chain for:

```text
protection OrderRequest
-> broker/PaperBroker result / active protective state truth
-> E5 consumes verified/failed/lost protection evidence
-> PROTECTION_VERIFIED or PROTECTION_FAILED / PROTECTION_LOST lifecycle event
```

Do **not** invent this chain in E7 if it belongs to E4/E5.

Classify each required behavior as one of:

```text
IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
IMPLEMENTATION_GAP
CONTRACT_OR_SEMANTIC_GAP
```

For every `IMPLEMENTATION_GAP`, identify the bounded next owner and dependency order. In particular determine the safe owner sequence for the existing Gate B criterion:

```text
Protection failure triggers emergency path
```

If current E5 state-machine transitions exist but the E4 result/verification -> E5 event bridge does not, state that precisely; do not mark the criterion PASS.

## Gate B evidence reconciliation

Update E7-owned Gate B status/evidence only where justified by merged source and test definitions.

Expected interpretation rules:

- `Required protection follows actual filled quantity` may move from `BLOCKED` to `NOT_RUN` **only if** static review confirms the full provider-neutral E5 -> E4 path is now materialized and the remaining requirement is approved-local executable/integration evidence.
- `Drawdown/daily/position/kill-switch rules enforced` may move from `BLOCKED` to `NOT_RUN` only if merged criterion-level test definitions are now sufficient and only executable evidence remains.
- `Protection failure triggers emergency path` remains `BLOCKED` unless its integrated implementation is actually materialized; a state-machine transition alone is insufficient.
- `Restart/persistence preserves required state` and `Paper E2E closes to TradeResult and persists audit` remain `BLOCKED` unless new authoritative implementation evidence genuinely exists.
- No `NOT_RUN`, `BLOCKED`, or static PASS may be promoted to executable `PASS` in this task.

Record the exact post-review Gate B dependency map and next bounded PM task recommendation.

## Writable scope

E7-owned paths only:

- `tests/integration/**`;
- cross-module `tests/safety/**` where appropriate;
- `status/e7/**`;
- `status/INTEGRATION_STATUS.md` and `status/RELEASE_GATES.md` only for evidence reconciliation;
- `coordination/E7/STATUS.md` on the target branch.

Do not modify:

- `src/execution/**`, `src/brokers/**`;
- `src/risk/**`, `src/position/**`;
- E1/E2/E3/E6 production code;
- `contracts/**` or ADRs unless a genuine shared contradiction forces a terminal `BLOCKED` report instead of editing;
- provider/private networking or credentials;
- PAPER/SHADOW/LIVE mode authority;
- GitHub Actions/CI/workflows.

## Executable verification

This task is **STATIC / TEST-DEFINITION ONLY**. Do not run project code or request Local Runner actions.

Record exactly:

```text
project executable verification = NOT_RUN / DEFERRED TO LATER APPROVED-LOCAL TASK
```

Do not use GitHub Actions/CI/hosted runner/GitHub-triggered compute, arbitrary cloud execution, Computer Adapter, provider API, or credentials.

## Acceptance

Allowed terminal outcomes:

### DONE

- accepted E5 producer and E4 consumer are statically coherent under `protection-v0.1`;
- E7 integration/safety test definitions for the materialized boundary exist and use the actual production APIs;
- affected Gate B criteria are reconciled without treating `NOT_RUN` as PASS;
- protection verification/failure chain is precisely classified;
- exact next bounded owner/task dependency is identified;
- Gate B remains BLOCKED unless every required criterion genuinely has PASS evidence, which is not expected in this task;
- no provider/private/PAPER/SHADOW/LIVE activity occurs.

### BLOCKED

- a genuine contract/architecture contradiction prevents coherent integration/test definition;
- record exact expected vs actual semantics and affected producers/consumers;
- do not patch E4/E5 production code to hide the contradiction.

## Completion / mailbox rule

Commit/push bounded E7 tests/evidence/status changes to `agent/e7-gate-b-protection-integration-20260824`.

**Worker-owned terminal STATUS must be written and pushed to `coordination/E7/STATUS.md` on this target branch, not main**, so AgentBridge can observe terminal state and callback PM.

Then stop. Do not self-start the next domain implementation, approved-local verification, full Paper E2E, provider/private work, Gate C, PAPER, SHADOW, or LIVE.