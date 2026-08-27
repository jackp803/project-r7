# E7 Current Task

- task_id: `E7-20260827-095`
- issued_at: `2026-08-27T09:24:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-shadow-temporal-requalification-20260827`
- authority: `agents/E7_INTEGRATION.md`, `agents/PROJECT_MANAGER.md`, `agents/README.md`, accepted `E7-20260826-092`, terminal `E7-20260826-093`, `docs/adr/ADR-0010-shadow-strategy-risk-temporal-ordering.md`, `status/e7/SHADOW_TEMPORAL_ORDERING_REMEDIATION_20260826.md`, `status/e7/SHADOW_TEMPORAL_ORDERING_CREDENTIAL_FREE_REQUALIFICATION_20260826.md`, `status/AGENTBRIDGE_EXACT_REVISION_PREPARATION_20260827.md`, `status/BLOCKERS.md`, `coordination/LOCAL_ACTION_CATALOG.md`

## Objective

Perform the approved-local **credential-free Gate C requalification** of the exact E7 temporal-ordering remediation candidate now that AgentBridge has established an `EXACT_CLEAN` local worktree. Do not perform provider verification or any SHADOW runtime.

E7-093 remains historical `BLOCKED / NOT_RUN / NOT_PASS`. Its refused preparation request must not be retried or reinterpreted. This task begins from the new authoritative approved-local preparation fact only.

## Exact candidate and prepared local state

```text
candidate_revision = 8fbf5fcae2eaf44accdf535121d8abf29ef5c93c
prior_qualified_revision = ab725965e96cac7a9769fd1ab15a3e626f920b95
approved_local_worktree = EXACT_CLEAN
preparation_action = PREPARE_EXACT_REVISION
preparation_job = JOB-852ABEE9A8CC
preparation_evidence = status/AGENTBRIDGE_EXACT_REVISION_PREPARATION_20260827.md
canonical_qualification_action = GATE_C_CREDENTIAL_FREE_REQUALIFICATION
qualification_request_id = REQ-E7-GATEC-095-01-3C71A8D4
```

Do **not** issue another `PREPARE_EXACT_REVISION` request in this task. Qualification must execute only against the already-prepared exact clean candidate worktree. Do not silently qualify another revision.

## Runtime / financial boundary

E7-095 authorizes only credential-free local verification on the approved Windows/non-GitHub environment.

Forbidden:

- OKX/provider requests of any kind;
- credential read/request/use;
- `GATE_C_ZERO_CAPITAL_SHADOW_SESSION`;
- `GATE_C_OKX_PRODUCTION_READONLY`;
- SHADOW or PAPER runtime;
- resetting/deleting/reusing either consumed SHADOW marker;
- provider/account mutation;
- order submit/cancel/amend/close;
- capital movement/exposure;
- Gate D or LIVE;
- GitHub Actions/CI/hosted/GitHub-triggered compute.

Both prior SHADOW session authorizations remain consumed. This task grants no third-session authority.

## Mandatory preflight

Read latest `main` and verify all of the following before creating the qualification request:

1. wake task ID is exactly `E7-20260827-095` and this task remains `ACTIVE`;
2. authoritative preparation evidence still identifies exact revision `8fbf5fcae2eaf44accdf535121d8abf29ef5c93c` as `EXACT_CLEAN` with job `JOB-852ABEE9A8CC`;
3. `GATE_C_CREDENTIAL_FREE_REQUALIFICATION` remains in `coordination/LOCAL_ACTION_CATALOG.md`;
4. no authoritative blocker forbids credential-free verification;
5. both prior SHADOW authorizations remain consumed and no provider/runtime authority is inferred;
6. the active approved-local project worktree used by the qualification action resolves to the exact candidate revision and is clean.

If the local worktree no longer matches the prepared exact candidate or clean state cannot be proven, stop `BLOCKED`; do not create a preparation request, qualify another revision, or substitute GitHub/cloud/container execution.

## Qualification execution

Create at most one Local Job Request using exactly:

```text
request_id = REQ-E7-GATEC-095-01-3C71A8D4
action_id  = GATE_C_CREDENTIAL_FREE_REQUALIFICATION
```

Do not add shell text, executable paths, arguments, environment secrets, provider credentials, branch names, remotes or local filesystem paths to the Local Job Request.

The canonical action must run the governed credential-free Gate C verification matrix on the exact prepared candidate. Record the exact execution revision, approved-local Windows/OS/Python/worktree classifications, per-suite results/counts, aggregate result, and explicit confirmation of zero provider/credential/runtime activity.

If any suite fails, preserve exact sanitized failure evidence and report `PARTIAL`; do not weaken/remove tests and do not call the candidate qualified.

If execution cannot occur in the approved local environment, record `NOT_RUN` and stop `BLOCKED`; `NOT_RUN != PASS`.

## Required suite/evidence boundary

The governed requalification must cover the credential-free project matrix required for the E7 temporal-ordering candidate, including at minimum the project suites exercised by the Gate C credential-free requalification action and explicit coverage of:

- market data;
- indicators/strategy;
- backtest/validation where included in the governed matrix;
- broker read-only contracts without provider traffic;
- risk;
- storage/platform as included by the action;
- integration;
- E2E;
- safety/no-submit/fail-closed behavior.

Do not invent counts or PASS results. Use only the local action's actual result.

## Required durable evidence

Update/create only E7-owned evidence/status needed for this qualification, using:

`status/e7/SHADOW_TEMPORAL_ORDERING_CREDENTIAL_FREE_REQUALIFICATION_20260827.md`

Evidence must state at minimum:

```text
task_id
request_id
action_id
local job id/state/exit code
exact candidate revision
approved local Windows classification
clean exact worktree classification
per-suite result + test count
aggregate PASS/FAIL
provider requests = 0
credentials read/requested/used = NONE
mutation requests = 0
submit requests = 0
SHADOW runtime = NOT_STARTED
PAPER runtime = NOT_STARTED
capital exposure = NONE
GitHub compute = NOT_USED
candidate qualification decision
```

Do not expose secrets, exact balances, provider payloads/IDs, signatures, tokens/cookies, browser auth material or unnecessary local paths.

## Result classification

### DONE

Use `DONE` only if the exact candidate revision passes the full governed credential-free Gate C requalification locally with complete durable evidence. Then report only:

```text
candidate 8fbf5fca... = CREDENTIAL_FREE_REQUALIFIED / PM REVIEW REQUIRED
prior qualified revision ab725965... = historical prior baseline
provider verification = NOT_RUN / NOT AUTHORIZED BY THIS TASK
third SHADOW session = NOT AUTHORIZED
PAPER = NOT AUTHORIZED
Gate D / LIVE = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
```

Do not self-promote a release gate, start provider verification, update AgentBridge, or start any runtime.

### PARTIAL

Use `PARTIAL` when the qualification job ran but one or more suites failed or required evidence is incomplete. Preserve exact sanitized failure evidence and stop.

### BLOCKED

Use `BLOCKED` when exact local preflight cannot be proven, the qualification action is refused/unavailable, or approved-local execution cannot occur. Keep unexecuted suites `NOT_RUN`; do not call them PASS.

## Downstream dependencies preserved

Even if E7-095 is `DONE`:

1. AgentBridge remains an external consumer that must migrate/review against ADR-0010 before any future provider SHADOW session;
2. both prior SHADOW authorizations remain consumed;
3. any third/replacement provider SHADOW session requires a new explicit Product Owner authorization with its own bounded safety/runtime limits;
4. no PAPER, Gate D, LIVE, provider mutation, order submission or capital exposure is authorized.

## Writable scope

Only:

- `coordination/E7/LOCAL_JOB_REQUEST.json` while required by the local mechanism, then clear it according to normal completed/refused handling;
- `coordination/E7/STATUS.md`;
- `status/e7/SHADOW_TEMPORAL_ORDERING_CREDENTIAL_FREE_REQUALIFICATION_20260827.md`;
- optionally `status/INTEGRATION_STATUS.md` for the non-promotional qualification state.

Do not modify production source/tests/contracts/ADR in E7-095. If verification exposes a defect, stop with evidence; remediation requires a new bounded task.

## Completion

Read latest `main`, verify wake task ID `E7-20260827-095`, execute only this TASK, persist evidence, update `coordination/E7/STATUS.md`, commit/push to the target branch, and stop on `DONE`, `PARTIAL`, or `BLOCKED`.

Do not self-start preparation, AgentBridge remediation, provider execution, a third SHADOW session, PAPER, Gate D, LIVE, provider mutation, order submission or capital movement/exposure.
