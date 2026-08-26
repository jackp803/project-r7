# E7 Current Task

- task_id: `E7-20260826-093`
- issued_at: `2026-08-26T23:43:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-shadow-temporal-requalification-20260826`
- authority: `agents/E7_INTEGRATION.md`, `agents/PROJECT_MANAGER.md`, `agents/README.md`, accepted `E7-20260826-092`, `docs/adr/ADR-0010-shadow-strategy-risk-temporal-ordering.md`, `status/e7/SHADOW_TEMPORAL_ORDERING_REMEDIATION_20260826.md`, `status/PM_E7_092_REVIEW_20260826.md`, `status/BLOCKERS.md`, `coordination/LOCAL_ACTION_CATALOG.md`

## Objective

Perform the approved-local **credential-free Gate C requalification** of the merged E7 temporal-ordering remediation candidate. Do not perform provider verification or any SHADOW runtime.

This task exists because E7-092 changed executable integration source/tests but correctly reported `local_verification = NOT_RUN`. `NOT_RUN != PASS`.

## Exact candidate

```text
candidate_revision = 8fbf5fcae2eaf44accdf535121d8abf29ef5c93c
prior_qualified_revision = ab725965e96cac7a9769fd1ab15a3e626f920b95
canonical_qualification_action = GATE_C_CREDENTIAL_FREE_REQUALIFICATION
qualification_request_id = REQ-E7-GATEC-093-01-4F7C2A91
```

The candidate revision is reachable from current `origin/main` and contains the accepted E7-092 source/test/ADR remediation. Do not silently qualify a different revision.

## Runtime / financial boundary

E7-093 authorizes only credential-free local verification on the approved Windows/non-GitHub environment.

Forbidden:

- OKX/provider requests of any kind;
- credential read/request/use;
- `GATE_C_ZERO_CAPITAL_SHADOW_SESSION`;
- production read-only provider action;
- SHADOW or PAPER runtime;
- resetting/deleting/reusing either consumed SHADOW marker;
- provider/account mutation;
- order submit/cancel/amend/close;
- capital movement/exposure;
- Gate D or LIVE;
- GitHub Actions/CI/hosted/GitHub-triggered compute.

Both prior SHADOW session authorizations remain consumed. This task grants no third-session authority.

## Preflight

Read latest `main` and verify:

1. wake task ID is exactly `E7-20260826-093` and task remains ACTIVE;
2. `candidate_revision` is exactly `8fbf5fcae2eaf44accdf535121d8abf29ef5c93c` and reachable from registered `origin/main`;
3. `GATE_C_CREDENTIAL_FREE_REQUALIFICATION` remains in `coordination/LOCAL_ACTION_CATALOG.md`;
4. no authoritative blocker forbids credential-free local verification;
5. no provider/runtime authority is inferred from this task.

If the approved local active worktree is not already the exact candidate revision, E7 may use the governed `PREPARE_EXACT_REVISION` capability only if it is locally enabled and only to prepare this exact revision. Use a fresh preparation request ID if required:

```text
REQ-E7-PREPARE-093-01-8D31B5C4
```

If preparation is required but unavailable/refused, stop `BLOCKED`; do not substitute GitHub/cloud/container execution and do not qualify another revision.

## Qualification execution

After exact clean candidate worktree is established, create at most one qualification Local Job Request using exactly:

```text
request_id = REQ-E7-GATEC-093-01-4F7C2A91
action_id  = GATE_C_CREDENTIAL_FREE_REQUALIFICATION
```

Do not add shell text, executable paths, arguments, environment secrets, provider credentials, branch names, remotes or local filesystem paths to the Local Job Request.

The canonical action is expected to run the governed Gate C credential-free project verification matrix. Record the exact revision, OS/Python/worktree classifications, per-suite results/counts, aggregate result, and explicit confirmation of zero provider/credential/runtime activity.

If any suite fails, report `PARTIAL` or `BLOCKED` according to the actual terminal condition; do not weaken/remove tests and do not call the candidate qualified.

If execution cannot occur in the approved local environment, record `NOT_RUN` and stop `BLOCKED`; do not treat it as PASS.

## Required evidence

Create/update only E7-owned evidence/status needed for this qualification, including:

`status/e7/SHADOW_TEMPORAL_ORDERING_CREDENTIAL_FREE_REQUALIFICATION_20260826.md`

Evidence must state at minimum:

- task/request/action IDs;
- exact candidate revision and clean worktree classification;
- approved local Windows environment classification;
- each suite result and test count;
- aggregate PASS/FAIL;
- provider requests = 0;
- credentials read/requested/used = none;
- mutation/submit = 0;
- SHADOW/PAPER runtime = not started;
- capital exposure = none;
- GitHub compute = not used;
- candidate qualification decision.

## Downstream interpretation

### DONE

Use `DONE` only if the exact candidate revision passes the full governed credential-free Gate C requalification locally. Even then:

- do not start provider verification or SHADOW;
- do not self-authorize a third session;
- AgentBridge consumer migration against ADR-0010 remains required before any future provider session;
- new explicit Product Owner authority remains required for any third/replacement SHADOW session.

### PARTIAL

Use `PARTIAL` when verification ran but one or more suites failed or evidence is incomplete. Preserve exact failure evidence and stop.

### BLOCKED

Use `BLOCKED` when exact local preparation/qualification cannot run or an authoritative dependency prevents verification. `NOT_RUN` remains `NOT_RUN`.

## Writable scope

Only:

- `coordination/E7/LOCAL_JOB_REQUEST.json` while required by the local mechanism, then clear according to normal handling;
- `coordination/E7/STATUS.md`;
- `status/e7/SHADOW_TEMPORAL_ORDERING_CREDENTIAL_FREE_REQUALIFICATION_20260826.md`;
- optionally `status/INTEGRATION_STATUS.md` for non-promotional qualification state.

Do not modify production source/tests/contracts/ADR in E7-093. If verification exposes a defect, stop with evidence; remediation requires a new bounded task.

## Completion

Execute only E7-20260826-093, persist evidence, update STATUS, commit/push to the target branch, and stop on DONE, PARTIAL or BLOCKED. Do not self-start AgentBridge remediation, provider execution, a third SHADOW session, PAPER, Gate D, LIVE, provider mutation, order submission or capital movement.