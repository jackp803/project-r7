# E4 Current Task

- task_id: `E4-20260829-024`
- issued_at: `2026-08-29T14:03:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-fp03-protection-trigger-consumer-20260829`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`, accepted `contracts/PROTECTION_TRIGGER_VALIDITY_PROFILE_V0_1.md`, `status/e7/FP03_PROTECTION_TRIGGER_CONTRACT_HANDOFF_20260829.md`, merged E5 FP-03 candidate PR #105, `status/PM_E5_029_REVIEW_20260829.md`

## Objective

Implement the **E4 execution-consumer/binding side of FP-03 protection-trigger validity** for `protection-trigger-validity-v0.1`, without provider calls and without modifying E5 policy/runtime semantics.

The goal is structural fail-closed enforcement immediately before any protection mutation path: E4 may proceed toward provider translation only when the exact current protection mutation is bound to valid, current, `ACTIONABLE` trigger-validity evidence. This task does not authorize a provider mutation, provider verification, SHADOW/PAPER runtime, Gate D or LIVE.

E5-029 is merged only as an **unverified executable candidate**. Its local verification is `NOT_RUN / NOT PASS`. Do not infer E5 executable PASS from the merge.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E4_EXECUTION.md`;
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`;
- `contracts/PROTECTION_TRIGGER_VALIDITY_PROFILE_V0_1.md`;
- current Position lifecycle/execution-evidence binding profiles;
- `status/e7/FP03_PROTECTION_TRIGGER_CONTRACT_HANDOFF_20260829.md`;
- `status/PM_E5_029_REVIEW_20260829.md`;
- current E4 `src/execution/protection.py`, related execution/order translation surfaces, and E4-owned tests;
- the accepted E5 public trigger-validity surface only as needed to consume/validate canonical evidence.

Do not read or execute another Worker's TASK mailbox.

## Required implementation

Within E4-owned execution source, implement the bounded consumer/gate so that a protection create path:

1. requires canonical `protection-trigger-validity-v0.1` evidence before it can become mutation-ready;
2. validates evidence structure/profile/identity using the accepted shared semantics;
3. requires `validity_status=ACTIONABLE` and `reason_codes=[PROTECTION_TRIGGER_ACTIONABLE]`;
4. requires exact binding to the actual mutation inputs, including at minimum:
   - `position_action_id`;
   - `position_id` and Position authority anchor/reference;
   - Position side;
   - symbol;
   - `order_role=PROTECTION_STOP`;
   - `protection_operation=CREATE` for the current executable baseline;
   - exact stop level;
5. rejects missing, unsupported, malformed or `FAIL_CLOSED` evidence;
6. rejects binding mismatch even when the evidence is otherwise ACTIONABLE;
7. rejects evidence that is no longer current when newer relevant Position/action/market truth is supplied/known at the consumer boundary;
8. never treats a breached/failed evidence result as permission to submit or re-submit;
9. preserves existing `protection-v0.1` authority, quantity, expiry, reconciliation and idempotency checks;
10. does not select an E5 lifecycle response from the evidence handoff category;
11. does not choose, infer or encode an OKX/provider-native trigger-price basis merely because shared evidence uses `LAST_PRICE`;
12. fails closed if provider trigger-basis compatibility is not separately proven by the applicable provider capability boundary;
13. does not make `REPLACE` / `MODIFY_PROTECTION` executable; FP-15 remains separate;
14. does not bundle the separate FP-02 SWAP action-role capability-matrix remediation into this task.

Prefer the smallest safe E4 boundary. Do not duplicate or fork the shared evidence schema/reason vocabulary.

## Required E4 test definitions

Add deterministic credential-free E4-owned tests covering at minimum:

- ACTIONABLE matching CREATE evidence is accepted by the E4 pre-mutation consumer;
- missing evidence fails closed;
- unsupported profile fails closed;
- FAIL_CLOSED evidence fails closed;
- `E4_BINDING_MISMATCH` cases for different action ID, Position ID/authority, side, symbol, stop, role and operation;
- stale/currentness mismatch when newer relevant market/Position/action truth is known;
- unchanged breached/failed evidence cannot authorize retry;
- `REPLACE` remains non-executable under the current baseline;
- existing protection authority/quantity/idempotency checks remain enforced;
- `PROVIDER_TRIGGER_BASIS_NOT_INFERRED`: shared `LAST_PRICE` evidence alone does not select or authorize provider `triggerPxType` or equivalent;
- provider-native mapping incompatibility is fail closed;
- no provider client/request/credential/mutation is needed or invoked by these tests.

Do not modify E5 tests or shared contracts in this task.

## Verification boundary

Executable verification is local-only on the Product Owner-approved Windows/non-GitHub environment.

Run the smallest relevant E4 execution/protection tests plus required execution/broker/safety regressions that exercise the changed consumer boundary. Record exact command, environment, revision and results.

If approved-local execution is unavailable, record `NOT_RUN` with exact intended commands and finish `PARTIAL`; `NOT_RUN != PASS`.

Forbidden:

- OKX/provider network requests;
- credential read/request/use;
- provider/account mutation;
- submit/cancel/amend/close order action;
- SHADOW/PAPER runtime;
- capital movement/exposure;
- Gate D or LIVE;
- GitHub Actions/CI/hosted/GitHub-triggered compute.

Provider/private access, credentials and Product Owner trading/runtime authority are **not required** for this deterministic implementation/test task.

## Writable scope

Only E4-owned implementation/tests/docs/status needed for this task, expected under:

- `src/execution/**`;
- E4-owned non-provider-neutral broker capability guard code only if strictly required to preserve fail-closed provider-basis non-inference, but do **not** implement the broader FP-02 matrix;
- `tests/execution/**`;
- `tests/brokers/**` only for credential-free consumer/capability guard tests that do not call provider endpoints;
- E4-owned docs/status evidence;
- `coordination/E4/STATUS.md`.

Do not modify:

- `contracts/**` or ADR semantics;
- E1/E2/E3/E5/E6/E7 source/tests;
- E5 policy/lifecycle semantics;
- provider credentials/config or private API allowlists;
- AgentBridge/local action catalog;
- Product Owner authorization artifacts;
- risk limits/leverage/capital thresholds;
- release criteria.

If the accepted shared profile or E5 public surface cannot be consumed without a shared-contract change, stop `BLOCKED` and identify the exact E7 dependency instead of inventing semantics.

## Required durable evidence

Create an E4-owned handoff/status artifact documenting:

- task and exact source revision;
- implementation paths/functions;
- exact shared profile consumed;
- exact E5 public evidence surface consumed, if any;
- binding/currentness/fail-closed behavior;
- provider trigger-basis non-inference behavior;
- test definitions added;
- local verification command/environment/result, or `NOT_RUN` with exact command;
- provider requests = 0;
- credentials = NONE;
- mutation/submit/order actions = 0;
- SHADOW/PAPER runtime = NOT_STARTED;
- capital exposure = NONE;
- remaining FP-02/FP-15 dependencies.

Update `coordination/E4/STATUS.md` and commit/push the task branch.

## Result classification

### DONE

Use `DONE` only if the E4 FP-03 consumer/binding implementation matches the accepted profile and required approved-local credential-free E4 verification passes.

Even on DONE, report:

```text
E5 FP-03 producer/policy = MERGED / prior local verification NOT_RUN
E4 FP-03 consumer/binding = IMPLEMENTED + LOCALLY VERIFIED / PM REVIEW REQUIRED
FP-03 overall executable qualification = NOT YET ESTABLISHED
fresh combined E7 approved-local credential-free requalification = REQUIRED
provider/private verification = NOT RUN / NOT AUTHORIZED BY THIS TASK
```

### PARTIAL

Use `PARTIAL` if implementation is complete but approved-local executable verification is `NOT_RUN`, or if tests expose a bounded unresolved E4 defect. Do not call FP-03 verified.

### BLOCKED

Use `BLOCKED` for a genuine shared-contract/authority contradiction or unavailable prerequisite preventing safe implementation. Do not weaken the contract, E5 policy or fail-closed semantics.

## Completion

Read latest `main`, verify wake task ID `E4-20260829-024`, execute only this task, persist evidence, update `coordination/E4/STATUS.md`, commit/push to the target branch, and stop on `DONE`, `PARTIAL`, or `BLOCKED`.

Do not self-start FP-02, FP-15, combined requalification, provider verification, SHADOW/PAPER, Gate D, LIVE, mutation, order action or capital movement/exposure.
