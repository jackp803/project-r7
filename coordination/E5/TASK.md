# E5 Current Task

- task_id: `E5-20260829-029`
- issued_at: `2026-08-29T13:41:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e5-fp03-protection-trigger-validity-20260829`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`, accepted `contracts/PROTECTION_TRIGGER_VALIDITY_PROFILE_V0_1.md`, `status/e7/FP03_PROTECTION_TRIGGER_CONTRACT_HANDOFF_20260829.md`, `status/PM_E7_099_REVIEW_20260829.md`

## Objective

Implement the **E5 producer/policy side of FP-03 protection-trigger validity** for `protection-trigger-validity-v0.1`, without provider calls and without modifying E4 execution/provider translation.

The purpose is to make current-market trigger geometry a deterministic fail-closed E5 safety input before protection mutation. This task does not authorize an order, provider request, protection mutation, SHADOW/PAPER runtime, Gate D or LIVE.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E5_RISK_POSITION.md`;
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`;
- `contracts/PROTECTION_TRIGGER_VALIDITY_PROFILE_V0_1.md`;
- current Position lifecycle projection/execution-evidence binding profiles;
- `docs/adr/ADR-0010-shadow-strategy-risk-temporal-ordering.md`;
- E1 canonical `MarketSnapshot` semantics needed for health/freshness consumption;
- current E5 `src/risk/**`, `src/position/**` protection/lifecycle implementation and owned tests;
- `status/e7/FP03_PROTECTION_TRIGGER_CONTRACT_HANDOFF_20260829.md`.

Do not read or execute another Worker's TASK mailbox.

## Required implementation

Within E5-owned source, implement a deterministic producer/evaluator for canonical `ProtectionTriggerValidityEvidence` that:

1. consumes the exact current Position authority and the exact E5 protection action/stop authority;
2. consumes an E1-attested canonical current `MarketSnapshot` and its health/freshness facts without inventing a second freshness threshold;
3. supports exactly `trigger_reference_semantic=LAST_PRICE` in V0.1;
4. enforces strict geometry:
   - LONG actionable only when `stop_level < last_price`;
   - SHORT actionable only when `stop_level > last_price`;
   - equality is fail closed as `TRIGGER_ALREADY_BREACHED`;
5. emits the contract's stable deterministic reason vocabulary and handoff category;
6. captures/evaluates time only after required Position/action/market evidence boundaries; reject temporal precomputation;
7. marks stale/unknown market evidence non-actionable;
8. marks stale/mismatched Position/action authority non-actionable;
9. treats `TRIGGER_ALREADY_BREACHED` or invalid geometry as a fail-closed E5 policy input, never as successful protection;
10. invalidates prior validity evidence when newer accepted market truth, newer Position/lifecycle truth, or changed E5 action/stop authority is known;
11. forbids unchanged breached evidence from becoming retryable merely because time advanced;
12. requires a new E5 action identity when E5 materially changes protection authority/stop policy;
13. preserves existing no-stop-widening semantics;
14. does not choose or encode OKX/provider-native trigger parameters or `triggerPxType`;
15. does not reinterpret the routing-only handoff category as an automatic single lifecycle transition. Any E5 lifecycle/risk response must remain within existing E5 authority and fail closed when policy/current truth is insufficient.

Use the contract's deterministic evidence identity rules. Do not create a parallel schema or rename the profile/reason vocabulary.

## Required E5 test definitions

Add deterministic E5-owned tests covering at minimum:

- `LONG_VALID`;
- `SHORT_VALID`;
- `LONG_EQUALITY_BREACHED`;
- `SHORT_EQUALITY_BREACHED`;
- `LONG_CROSSED`;
- `SHORT_CROSSED`;
- `STALE_MARKET`;
- `UNKNOWN_MARKET`;
- `STALE_POSITION_EVIDENCE`;
- `MISMATCHED_SIDE`;
- `UNSUPPORTED_TRIGGER_REFERENCE`;
- `TEMPORAL_PRECOMPUTE`;
- `UNCHANGED_EVIDENCE_RETRY`;
- `NEW_MARKET_REEVALUATION`;
- `NEW_POSITION_REQUIRES_NEW_AUTHORITY`;
- deterministic evidence identity for identical payload and identity change for materially changed evidence;
- no-stop-widening remains enforced;
- FAIL_CLOSED validity is never represented as successful protection.

Do not add E4 provider mapping tests in this task. `E4_BINDING_MISMATCH` and `PROVIDER_TRIGGER_BASIS_NOT_INFERRED` execution-consumer coverage belongs to the later E4 task.

## Verification boundary

Executable verification is local-only on the Product Owner-approved Windows/non-GitHub environment.

Run the smallest relevant E5 owned tests plus any required risk/position/safety regression set. Record exact local command, environment, revision and results.

If approved-local execution is unavailable, record `NOT_RUN` with exact intended command and finish `PARTIAL`; `NOT_RUN != PASS`.

Forbidden in verification and implementation:

- OKX/provider requests;
- credential read/request/use;
- Local Job action that performs provider/private work;
- provider/account mutation;
- submit/cancel/amend/close order action;
- SHADOW/PAPER runtime;
- capital movement/exposure;
- Gate D or LIVE;
- GitHub Actions/CI/hosted/GitHub-triggered compute.

Provider/private access, credentials and Product Owner trading/runtime authority are **not required** for this deterministic implementation/test task.

## Writable scope

Only E5-owned implementation/tests/docs/status needed for this task, expected under:

- `src/risk/**`;
- `src/position/**`;
- `tests/risk/**`;
- `tests/position/**`;
- `tests/safety/**` only for E5-owned safety scenarios;
- `docs/risk/**` or `docs/position/**` if needed;
- E5-owned status evidence;
- `coordination/E5/STATUS.md`.

Do not modify:

- `contracts/**` or ADR semantics;
- E1/E2/E3/E4/E6/E7 source/tests;
- provider adapter/config/auth code;
- AgentBridge or local action catalog;
- Product Owner authorization artifacts;
- risk limits/leverage/capital thresholds;
- release criteria.

If the accepted profile cannot be implemented without changing a shared contract, stop `BLOCKED` and identify the exact E7 dependency instead of inventing semantics.

## Required durable evidence

Create an E5-owned handoff/status artifact documenting:

- task and exact source revision;
- implementation paths/functions;
- exact contract/profile consumed;
- reason-code/handoff behavior implemented;
- test definitions added;
- local verification command/environment/result, or `NOT_RUN` with exact command;
- provider requests = 0;
- credentials = NONE;
- mutation/submit/order actions = 0;
- SHADOW/PAPER runtime = NOT_STARTED;
- capital exposure = NONE;
- any residual E4 dependency.

Update `coordination/E5/STATUS.md` and commit/push the task branch.

## Result classification

### DONE

Use `DONE` only if the E5 producer/policy implementation matches `protection-trigger-validity-v0.1` and the required local E5 verification passes on the approved environment with durable evidence.

Report downstream state as:

```text
E5 FP-03 producer/policy = IMPLEMENTED + LOCALLY VERIFIED / PM REVIEW REQUIRED
E4 FP-03 consumer/provider mapping = STILL REQUIRED / NOT STARTED BY E5
FP-03 overall = NOT YET COMPLETE
provider/private verification = NOT RUN / NOT AUTHORIZED BY THIS TASK
```

### PARTIAL

Use `PARTIAL` if implementation is complete but approved-local executable verification is `NOT_RUN`, or if tests run and expose a bounded unresolved defect. Do not call FP-03 verified.

### BLOCKED

Use `BLOCKED` for a genuine shared-contract/authority contradiction or unavailable prerequisite that prevents safe implementation. Do not weaken the contract or risk semantics.

## Completion

Read latest `main`, verify wake task ID `E5-20260829-029`, execute only this task, persist evidence, update `coordination/E5/STATUS.md`, commit/push to the target branch, and stop on `DONE`, `PARTIAL`, or `BLOCKED`.

Do not self-start the E4 follow-up, requalification, provider validation, SHADOW/PAPER, Gate D, LIVE, mutation, order action or capital movement/exposure.
