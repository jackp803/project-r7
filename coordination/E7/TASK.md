# E7 Current Task

- task_id: `E7-20260829-113`
- issued_at: `2026-08-29T20:00:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-fp16-runtime-preflight-implementation-20260829`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, accepted `runtime-preflight-v0.1`, `status/PM_E7_112_REVIEW_20260829.md`, active LF-0 exact-revision infrastructure blocker

## Objective

Remediate only the PM-identified FP-16 **external-consumer participation fail-open defect** in the existing unmerged E7-112 branch, add deterministic regression definitions, update E7 evidence/status, and stop.

Do not expand FP-16 semantics, change the accepted shared contract, execute project code, create Local Job Requests, prepare exact revisions, call providers, read/request credentials, launch/restart processes, mutate provider/account state, submit/cancel/amend/close orders, start SHADOW/PAPER/live runtime, expose/move capital, or modify AgentBridge/operator infrastructure.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E7_INTEGRATION.md`;
- `contracts/RUNTIME_PREFLIGHT_PROFILE_V0_1.md`, especially sections 5.1 and 12;
- `status/PM_E7_112_REVIEW_20260829.md`;
- current branch `src/integration/runtime_preflight.py`;
- current branch `tests/integration/test_runtime_preflight.py`;
- current branch `tests/safety/test_p0_integrated_fail_closed.py`;
- current branch FP-16 handoff/matrix/qualification manifest;
- active LF-0 blocker.

E7 may read broadly for integration. Do not execute another Worker's TASK mailbox.

## Precise defect to fix

Accepted `runtime-preflight-v0.1` requires:

- `external_consumer_evidence` may be null only when the declared role proves no external orchestrator materially participates;
- when an external orchestrator/launcher/AgentBridge supervisor/operator-owned runtime materially participates, exact compatible external-consumer evidence is required.

Current branch implementation computes external requirement from only:

```text
fixed role requirement OR supervisor_present
```

and does not treat non-null/current caller-supplied `RuntimePreflightAuthority.external_consumer_authority` as evidence that an external consumer materially participates.

This permits a fail-open case for conditional roles such as `CREDENTIAL_FREE_LOCAL_VERIFICATION` and `PROVIDER_READ_ONLY_OBSERVATION`: external authority can be present/current while input omits `external_consumer_evidence` and supervisor is absent, without necessarily emitting `PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED`.

## Required remediation

Within E7-owned FP-16 code/tests only:

1. preserve the existing fixed unconditional requirement for `SHADOW_RUNTIME` and `BOUNDED_LIVE_FIRE_RUNTIME`;
2. preserve supervisor-triggered conditional participation;
3. additionally treat non-null supplied current `external_consumer_authority` as material external participation that requires exact `external_consumer_evidence`;
4. when external participation is required and input evidence is missing, emit accepted `PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED`;
5. when external evidence is present, require exact ID/generation/config/profile/evidence hash/status/timestamp compatibility against the supplied current authority as already defined;
6. if evidence is present but current external authority is absent/does not match, remain fail closed rather than silently accepting historical/unsupported consumer evidence;
7. do not invent any new reason code or contract field;
8. preserve pure evaluator/no-I/O/no-authority side-effect behavior;
9. preserve deterministic evidence identity/currentness behavior.

Do not change shared `runtime-preflight-v0.1` semantics to accommodate the implementation.

## Required deterministic regression definitions

Add/adjust E7-owned tests covering at minimum:

- credential-free role + `supervisor_present=false` + non-null current `external_consumer_authority` + missing `external_consumer_evidence` -> `FAIL_CLOSED / PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED`;
- provider-read-only role with the same authority/evidence mismatch -> fail closed;
- credential-free no-external case remains eligible only when both input external evidence and current external authority represent no material external consumer;
- exact current external evidence + exact current external authority remains admissible when all other required facts are coherent;
- mismatched/stale/incompatible external consumer evidence remains fail closed;
- SHADOW unconditional requirement remains intact;
- role-transfer/no-authority-side-effect safety remains intact;
- no provider/network/credential/process-launch/restart/mutation/capital dependency.

Do not execute tests through GitHub.

## Verification boundary

All executable verification remains local-only. LF-0 remains blocked.

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

`NOT_RUN` is not PASS.

## Required durable evidence

Update/create E7-owned evidence so the remediation is explicit:

- update `status/e7/FP16_RUNTIME_PREFLIGHT_IMPLEMENTATION_20260829.md` with the corrected external participation rule and regression definitions;
- update E7 P0 matrix/qualification manifest only if needed for exact test registration/classification;
- update `coordination/E7/STATUS.md` with task `E7-20260829-113` and terminal state.

## Writable scope

Only E7-owned paths already used by E7-112:

- `src/integration/runtime_preflight.py`;
- `tests/integration/test_runtime_preflight.py`;
- `tests/safety/test_p0_integrated_fail_closed.py` only if directly required;
- E7-owned FP-16 status/matrix/qualification artifacts;
- `coordination/E7/STATUS.md`.

Do not modify shared contracts/ADRs, E1-E6 production code, E6 OperationalMode semantics/storage, provider adapter/auth/config/credentials, AgentBridge/local-action infrastructure, Product Owner authorization artifacts, risk/leverage/capital thresholds, LIVE/release policy, or GitHub Actions/CI files.

## Result classification

### DONE
Use DONE only if remediation/test definitions are complete and required executable verification actually ran on an approved local exact revision with PASS evidence.

### PARTIAL
Use PARTIAL when remediation/test definitions are complete but executable verification remains `NOT_RUN / NOT_PASS`.

### BLOCKED
Use BLOCKED only if accepted contract semantics make the bounded remediation impossible or contradictory.

## Completion

Read latest `main`, verify wake task ID `E7-20260829-113`, continue only the existing E7 FP-16 branch, apply the bounded remediation, persist evidence, update STATUS, commit/push, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start E6 persistence work, exact-revision preparation, Local Job Requests, qualification execution, provider verification, AgentBridge migration, SHADOW/PAPER, bounded 10U live-fire, Gate D, LIVE, mutation, process launch/restart, order action or capital movement/exposure.
