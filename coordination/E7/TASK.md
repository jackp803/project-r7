# E7 Current Task

- task_id: `E7-20260829-112`
- issued_at: `2026-08-29T19:56:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-fp16-runtime-preflight-implementation-20260829`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, accepted `runtime-preflight-v0.1`, merged E7-20260829-111 static integration baseline PR #122, `status/PM_E7_111_REVIEW_20260829.md`, active LF-0 exact-revision infrastructure blocker

## Objective

Implement the smallest deterministic **provider-neutral FP-16 RuntimePreflightEvidence validator/evaluator** under E7 cross-module ownership.

This task closes only the current project implementation gap between the accepted `runtime-preflight-v0.1` contract and executable project code. It must consume already-supplied sanitized authority/evidence facts and deterministically produce only `ELIGIBLE | FAIL_CLOSED` plus accepted deterministic reason codes.

It must not launch or restart a process, create a Local Job Request, prepare an exact revision, call provider endpoints, inspect/request credentials, mutate provider/account state, submit/cancel/amend/close orders, enable SHADOW/PAPER/LIVE, move/expose capital, or modify AgentBridge/operator infrastructure.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E7_INTEGRATION.md`;
- `contracts/RUNTIME_PREFLIGHT_PROFILE_V0_1.md` in full, especially role matrix, OperationalMode binding, heartbeat, supervisor, capability, reconciliation, dependency, external-consumer, authorization, reason ordering and deterministic identity sections;
- `contracts/BOUNDED_LIVE_FIRE_READINESS_PROFILE_V0_1.md`;
- current E6 OperationalMode record/storage public surface and accepted restart/reconciliation facts only as input shapes, without modifying E6 semantics;
- merged E7-111 integration files and `status/e7/P0_INTEGRATED_DETERMINISTIC_SAFETY_MATRIX_20260829.md`;
- `status/PM_E7_111_REVIEW_20260829.md`;
- active `status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`.

E7 may read broadly for integration. Do not execute another Worker's TASK mailbox.

## Implementation boundary

Add an E7-owned pure/provider-neutral runtime-preflight module, preferably:

- `src/integration/runtime_preflight.py`;
- minimal export changes in `src/integration/__init__.py` only if needed.

The implementation may define typed/provider-neutral input helpers and pure deterministic functions that:

1. validate the exact `RuntimePreflightEvidence` field set and accepted profile/schema vocabulary;
2. validate canonical timestamps, hashes, sequences and deterministic identity;
3. validate exact revision/worktree binding;
4. validate role-specific OperationalMode requirements without creating/changing OperationalMode;
5. validate process identity, single-instance and heartbeat generation/freshness bindings;
6. validate supervisor/watchdog compatibility and restart-permission evidence;
7. validate required action IDs against both registered and allowlisted exact capability generation;
8. validate reconciliation readiness where the role requires it;
9. validate required owner dependency references/readiness/current generation supplied by the caller;
10. validate external-consumer compatibility according to the accepted role rules;
11. validate exact role/revision/capability authorization evidence;
12. deterministically derive only `ELIGIBLE` or `FAIL_CLOSED` and accepted ordered reason codes;
13. provide deterministic identity/currentness comparison helpers only if required by the accepted profile.

The evaluator is an admission-evidence interpreter only. `ELIGIBLE` must never be exposed as provider authority, order authority, process-launch authority, restart execution, SHADOW/PAPER authority, bounded-live-fire authority, Gate D, LIVE, or capital authorization.

## Required fail-closed semantics

### Exact revision/worktree

- revision-qualified roles require exact matching full revision authority and `EXACT_CLEAN` where the profile requires it;
- historical exact-clean evidence for another revision is non-transferable;
- `CLEAN_UNQUALIFIED`, `DIRTY`, `UNKNOWN`, mismatched authority hash/ref or revision mismatch fail closed;
- the current LF-0 blocker remains unchanged and must not be bypassed by constructing a preflight object.

### Role isolation

A preflight result is bound to exactly one runtime role:

- `CREDENTIAL_FREE_LOCAL_VERIFICATION`
- `PROVIDER_READ_ONLY_OBSERVATION`
- `SHADOW_RUNTIME`
- `PAPER_RUNTIME`
- `BOUNDED_LIVE_FIRE_RUNTIME`

Evidence/results for one role are never transferable to another role.

### OperationalMode

- consume exact current E6 transition ID/revision/mode/payload hash supplied as authority;
- requested mode must equal current durable truth and satisfy the accepted role-specific mode rule;
- environment variables/UI/defaults/prior process memory are not substitutes;
- do not invent a bounded-live-fire OperationalMode mapping where the contract says it remains future authority.

### Process / heartbeat

- exact process instance/start generation must match heartbeat evidence;
- heartbeat policy generation/hash must be present and current as supplied;
- stale/unknown heartbeat, prior-boot heartbeat, invalid temporal ordering or non-single instance fails closed;
- do not invent a numeric heartbeat TTL.

### Supervisor / restart

- supervisor compatibility/restart-permission fields are interpreted exactly as the profile defines;
- dead process alone never authorizes restart;
- `launch_intent=RESTART` must recompute current preflight and may not inherit prior process heartbeat/mode/authorization;
- this module must never itself restart or launch anything.

### Capability / allowlist

- every required canonical action ID must exist in both accepted registered and allowlisted sets for the exact capability generation;
- catalog registration alone is not allowlisting;
- allowlisting alone is not Product Owner/runtime authority;
- refused/terminal request evidence cannot become READY by retry inference;
- no filesystem path, shell command or secret belongs in the shared evidence.

### Reconciliation / dependencies

- roles that can observe/plan/mutate provider/exposure state require accepted current reconciliation readiness exactly as the profile defines;
- required dependency evidence missing, stale, conflicting, `NOT_READY` or `UNKNOWN` fails closed;
- do not duplicate E1/E4/E5/E6 owner semantics: consume their supplied readiness classifications/references only.

### External consumer

- enforce fixed role requirements from the accepted profile;
- when external consumer evidence is present, require exact compatible generation/hash/status/current timestamp material;
- SHADOW must retain the ADR-0010 external-consumer compatibility prerequisite;
- do not modify or call AgentBridge/operator infrastructure.

### Authorization

- exact authorization class/role/revision/capability generation must match the requested preflight role;
- only `VALID` exact current authority may contribute to `ELIGIBLE`;
- `MISSING`, `MISMATCH`, `EXPIRED`, `CONSUMED`, `UNKNOWN` fail closed;
- credentials being present locally never create authorization;
- synthetic test fixtures are not real Product Owner/runtime authority.

## E7-111 test migration requirement

`tests/safety/test_p0_integrated_fail_closed.py` currently asserts that `src/integration/runtime_preflight.py` does not exist. That assertion was valid only for the E7-111 contract-only baseline.

In this task, replace that stale absence assertion with real provider-neutral fail-closed evaluator tests. Do not delete FP-16 safety coverage; migrate it from `CONTRACT_ONLY file absence` to `IMPLEMENTED_UNQUALIFIED behavior`.

Update E7-owned P0 matrix/qualification manifest only as needed so FP-16 classification becomes `IMPLEMENTED_UNQUALIFIED / NOT_RUN / NOT_PASS`, not PASS, after this candidate is materialized.

## Required deterministic tests to define

Add E7-owned tests, preferably `tests/integration/test_runtime_preflight.py` plus bounded safety updates, covering at minimum:

- one internally coherent synthetic `CREDENTIAL_FREE_LOCAL_VERIFICATION` evidence object deterministically evaluates `ELIGIBLE` while granting no provider/runtime/capital authority;
- same exact evidence is deterministic and identity-stable;
- role substitution/transfer invalidates the evidence;
- revision mismatch and non-`EXACT_CLEAN` qualified worktree fail closed;
- OperationalMode transition/revision/hash/mode mismatch fails closed;
- duplicate/unknown single-instance state fails closed;
- stale/unknown heartbeat, wrong process instance, wrong start generation and invalid temporal ordering fail closed;
- supervisor incompatible/unknown and RESTART without current restart permission fail closed where applicable;
- required action registered but not allowlisted fails closed;
- required action allowlisted but not registered fails closed;
- capability status unknown/not-ready fails closed;
- reconciliation required but not ready/current fails closed;
- required dependency missing/not-ready/unknown fails closed;
- required external consumer missing/incompatible for a role that requires it fails closed;
- authorization missing/mismatched/expired/consumed/unknown fails closed;
- provider-role fixtures without real authority remain synthetic test data and do not alter repository authorization state;
- no provider/network/credential/mutation/process-launch dependency;
- E7-111 integrated P0 safety test no longer relies on implementation-file absence.

Do not execute tests through GitHub.

## Verification boundary

All executable verification remains local-only. LF-0 approved-local exact-revision preparation is still blocked.

Unless separately authoritative approved-local execution evidence already exists for the exact resulting revision, record:

```text
project executable verification = NOT_RUN / NOT_PASS
FP-16 runtime-preflight tests = NOT_RUN / NOT_PASS
LF-0 = BLOCKED / UNCHANGED
LF-1 = NOT_RUN / NOT_PASS
LF-2 = PARTIAL / NOT PASS
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
process launch/restart = 0
order/protection actions = 0
SHADOW/PAPER = NOT_AUTHORIZED
10U bounded live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

`NOT_RUN` is not PASS. Do not create a Local Job Request or exact-revision preparation request in this task.

## Required durable evidence

Create:

`status/e7/FP16_RUNTIME_PREFLIGHT_IMPLEMENTATION_20260829.md`

Document task ID, exact files changed, accepted contract consumed, pure evaluator boundary, deterministic identity/reason/currentness behavior, role/OperationalMode/heartbeat/supervisor/capability/reconciliation/dependency/external-consumer/authorization handling, migrated E7-111 tests, exact future approved-local commands, limitations, and confirmation of zero provider/credential/process-launch/runtime/capital authority.

Update `status/e7/P0_INTEGRATED_DETERMINISTIC_SAFETY_MATRIX_20260829.md` and `status/e7/P0_CREDENTIAL_FREE_QUALIFICATION_MANIFEST_20260829.md` only as needed to register the new FP-16 test module and `IMPLEMENTED_UNQUALIFIED / NOT_RUN / NOT_PASS` classification.

Update `coordination/E7/STATUS.md`, commit, and push the target branch.

## Writable scope

Only E7-owned paths:

- `src/integration/runtime_preflight.py`;
- `src/integration/__init__.py` only minimal exports if needed;
- `tests/integration/`;
- `tests/e2e/` only if directly required by the pure preflight boundary;
- cross-module `tests/safety/` only for FP-16/E7-111 migrated safety coverage;
- `status/e7/FP16_RUNTIME_PREFLIGHT_IMPLEMENTATION_20260829.md`;
- E7-owned P0 matrix/qualification manifest;
- `coordination/E7/STATUS.md`.

Do not modify shared contracts/ADRs unless a true contradiction is discovered; if one is discovered, document a precise E7 dependency/change request and stop at PARTIAL rather than silently changing the accepted profile in the same implementation task.

Do not modify E1-E6 production code, E6 OperationalMode semantics/storage, provider adapters/auth/config/credentials, AgentBridge/local-action infrastructure, Product Owner authorization artifacts, risk/leverage/capital thresholds, LIVE/release policy, or GitHub Actions/CI files.

## Result classification

### DONE

Use DONE only if implementation/test definitions are complete and required executable verification actually ran on an approved local exact revision with PASS evidence.

### PARTIAL

Use PARTIAL when implementation/test definitions are complete but executable verification remains `NOT_RUN / NOT_PASS`, or a precise accepted-contract contradiction is surfaced.

### BLOCKED

Use BLOCKED only for contradictory authoritative requirements that prevent bounded implementation within E7 scope.

## Completion

Read latest `main`, verify wake task ID `E7-20260829-112`, execute only this task, persist evidence, update STATUS, commit/push the target branch, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start E6 persistence work, exact-revision preparation, Local Job Requests, qualification execution, provider verification, AgentBridge migration, SHADOW/PAPER, 10U bounded live-fire, Gate D, LIVE, mutation, process launch/restart, order action or capital movement/exposure.
