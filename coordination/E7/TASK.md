# E7 Current Task

- task_id: `E7-20260829-114`
- issued_at: `2026-08-29T20:08:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-fp16-runtime-preflight-implementation-20260829`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, accepted `runtime-preflight-v0.1`, `status/PM_E7_113_REVIEW_20260829.md`, active LF-0 exact-revision infrastructure blocker

## Objective

Remediate only the E7-113 writable-scope violation on the existing unmerged FP-16 branch. Preserve the accepted E7-113 external-consumer participation source semantics, consolidate the regression definitions into the previously authorized existing integration test module, remove the unauthorized extra regression file, update E7 evidence/status, and stop.

This is governance/test-layout remediation only. Do not expand FP-16 semantics, execute project code, create Local Job Requests, prepare exact revisions, call providers, read/request credentials, launch/restart processes, mutate provider/account state, submit/cancel/amend/close orders, start SHADOW/PAPER/live runtime, expose/move capital, or modify AgentBridge/operator infrastructure.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E7_INTEGRATION.md`;
- `contracts/RUNTIME_PREFLIGHT_PROFILE_V0_1.md` sections 5.1 and 12;
- `status/PM_E7_113_REVIEW_20260829.md`;
- current branch `src/integration/runtime_preflight.py`;
- current branch `tests/integration/test_runtime_preflight.py`;
- current branch `tests/integration/test_runtime_preflight_external_consumer_regression.py` solely because this task explicitly authorizes removing it;
- current branch E7 FP-16 handoff/qualification manifest;
- active LF-0 blocker.

E7 may read broadly for integration. Do not execute another Worker's TASK mailbox.

## Required remediation

1. Preserve the E7-113 source rule that external participation is required when any of the following is true:
   - fixed unconditional role requirement;
   - `supervisor_present`;
   - non-null current caller-supplied `external_consumer_authority`.
2. Do not otherwise change `src/integration/runtime_preflight.py` unless a minimal no-semantic-change adjustment is mechanically necessary.
3. Move the E7-113 external-consumer regression cases into existing `tests/integration/test_runtime_preflight.py`.
4. Delete `tests/integration/test_runtime_preflight_external_consumer_regression.py`.
5. Preserve at least these deterministic regression definitions in the existing test module:
   - credential-free + no supervisor + current external authority + missing external evidence -> `FAIL_CLOSED / PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED`;
   - provider-read-only same mismatch -> fail closed;
   - credential-free true no-external case remains eligible when all other synthetic facts are coherent;
   - exact current external evidence + exact current external authority remains admissible;
   - external evidence without current authority fails closed;
   - stale/mismatched/incompatible external consumer fails closed;
   - SHADOW unconditional requirement remains fail closed when evidence is missing;
   - no provider/network/credential/process/order/runtime/capital authority side effects.
6. Update `status/e7/FP16_RUNTIME_PREFLIGHT_IMPLEMENTATION_20260829.md` and `status/e7/P0_CREDENTIAL_FREE_QUALIFICATION_MANIFEST_20260829.md` so future local verification references the existing `test_runtime_preflight.py` module only; no stale command/reference to the deleted regression file may remain.
7. Update `coordination/E7/STATUS.md` with task `E7-20260829-114` and terminal state.

No new reason code, shared contract field, runtime authority, provider capability, or release authority may be introduced.

## Verification boundary

All executable verification remains local-only. LF-0 remains blocked. Do not execute tests in this task.

Record:

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

`NOT_RUN` is not PASS.

## Writable scope

Only:

- `src/integration/runtime_preflight.py` only if a minimal no-semantic-change adjustment is mechanically required;
- `tests/integration/test_runtime_preflight.py`;
- `tests/integration/test_runtime_preflight_external_consumer_regression.py` **deletion only**;
- `status/e7/FP16_RUNTIME_PREFLIGHT_IMPLEMENTATION_20260829.md`;
- `status/e7/P0_CREDENTIAL_FREE_QUALIFICATION_MANIFEST_20260829.md`;
- `coordination/E7/STATUS.md`.

Do not modify the P0 matrix unless a stale reference to the deleted file actually exists; if so, only remove/redirect that reference with no classification change. Do not modify shared contracts/ADRs, E1-E6 production code, E6 OperationalMode semantics/storage, provider adapter/auth/config/credentials, AgentBridge/local-action infrastructure, Product Owner authorization artifacts, risk/leverage/capital thresholds, LIVE/release policy, or GitHub Actions/CI files.

## Result classification

### DONE
Use DONE only if the remediation is complete and required executable verification actually ran on an approved local exact revision with PASS evidence. Under current LF-0, DONE is not expected.

### PARTIAL
Use PARTIAL when the scope remediation/test definitions are complete but executable verification remains `NOT_RUN / NOT_PASS`.

### BLOCKED
Use BLOCKED only if a contradictory authoritative requirement prevents this bounded remediation.

## Completion

Read latest `main`, verify wake task ID `E7-20260829-114`, continue only the existing E7 FP-16 branch, perform this exact governance/test-layout remediation, persist evidence, update STATUS, commit/push, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start exact-revision preparation, Local Job Requests, qualification execution, provider verification, AgentBridge migration, SHADOW/PAPER, bounded 10U live-fire, Gate D, LIVE, mutation, process launch/restart, order action or capital movement/exposure.
