# E7 Current Task

- task_id: `E7-20260826-090`
- issued_at: `2026-08-26T23:01:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-zero-capital-shadow-replacement-20260826`
- authority: `agents/E7_INTEGRATION.md`, `agents/PROJECT_MANAGER.md`, `agents/README.md`, `contracts-v0.1`, `status/PRODUCT_OWNER_ZERO_CAPITAL_SHADOW_REAUTHORIZATION_20260826.md`, accepted `E7-20260826-088`, `status/e7/ZERO_CAPITAL_SHADOW_SESSION_RESULT_20260826.md`, `status/AGENTBRIDGE_ZERO_CAPITAL_SHADOW_INCIDENT_REMEDIATION_20260826.md`, `status/AGENTBRIDGE_ZERO_CAPITAL_SHADOW_REAUTHORIZATION_REGISTRATION_20260826.md`, `coordination/LOCAL_ACTION_CATALOG.md`, `status/BLOCKERS.md`

## Objective

Execute exactly one Product-Owner-authorized **replacement bounded zero-capital SHADOW runtime session** using the repaired and registered canonical local action, then persist only sanitized durable evidence for PM review.

The original E7-088 authorization remains consumed and must not be reset, deleted, renamed, overwritten, or reused. This task is authorized only by replacement authorization `PO-ZERO-CAPITAL-SHADOW-REAUTH-20260826-01`.

If the replacement authorization's new append-only consumption marker is reached, the replacement authority is consumed regardless of success or fail-closed termination. No retry, third session, recurring operation, PAPER, Gate D, LIVE, provider/account mutation, order submission, or capital exposure is authorized.

## Exact execution boundary

```text
replacement authorization_id   = PO-ZERO-CAPITAL-SHADOW-REAUTH-20260826-01
qualified executable revision   = ab725965e96cac7a9769fd1ab15a3e626f920b95
canonical action_id              = GATE_C_ZERO_CAPITAL_SHADOW_SESSION
request_id                       = REQ-E7-SHADOW-090-01-6A9D3F12
approved computer                = current registered local Windows computer only
provider/environment             = OKX production read-only shadow
REST hostname                    = https://openapi.okx.com
maximum monotonic duration       = 1800 seconds
maximum shared HTTPS GETs        = 300
available capital                = exactly zero
provider/account mutation        = forbidden
order submission                 = forbidden
capital exposure                 = forbidden
GitHub compute                   = forbidden
```

Use exactly the registered canonical action. Do not add executable paths, shell text, arguments, environment values, credentials, hostnames, branch names, remotes, or local filesystem paths to the Local Job Request.

## Mandatory preflight before Local Job Request

Read latest `main` and verify all of the following before creating any request:

1. wake task ID is exactly `E7-20260826-090` and this TASK remains `ACTIVE`;
2. replacement authorization `PO-ZERO-CAPITAL-SHADOW-REAUTH-20260826-01` remains authoritative and not consumed;
3. the historical E7-088 consumption marker remains preserved and consumed;
4. the new replacement append-only consumption marker remains absent;
5. `GATE_C_ZERO_CAPITAL_SHADOW_SESSION` remains in the canonical catalog;
6. operator reauthorization registration remains `REGISTERED / ALLOWLISTED / NOT EXECUTED` or otherwise authoritatively confirms this replacement allowance remains available;
7. repaired AgentBridge supervisor revision/evidence remains compatible with the accepted E6 safe-token contract and no authoritative blocker conflicts with execution.

Do not read or expose credential values during repository preflight.

If any item fails, do not create the Local Job Request. Persist sanitized `BLOCKED` evidence and stop.

## Local Job Request

Create at most one request using exactly:

```text
request_id = REQ-E7-SHADOW-090-01-6A9D3F12
action_id  = GATE_C_ZERO_CAPITAL_SHADOW_SESSION
```

No second request is authorized in this task.

If AgentBridge refuses before the replacement consumption marker is created, preserve the refusal as terminal `BLOCKED`; do not retry under the same or a new request ID.

If the replacement session starts/consumes authorization and then terminates for any reason, the replacement authorization is consumed. Do not retry or start a third session.

## Authorized runtime invariants

The repaired operator-owned supervisor remains authoritative for enforcing the accepted E7-086 boundary. E7 must not weaken, bypass, reinterpret, or repair around fail-closed behavior.

Required invariant throughout the session:

```text
elapsed_seconds <= 1800
HTTPS_GET_COUNT <= 300
MUTATION_REQUEST_COUNT = 0
SUBMIT_REQUEST_COUNT = 0
available_balance_is_zero = YES
capital_exposure = NONE
```

No POST/PUT/PATCH/DELETE, order place/cancel/amend/close, leverage/account/position-mode change, transfer, deposit, withdrawal, funding action, Demo execution, browser/provider UI automation, PAPER runtime, Gate D or LIVE is permitted.

## Mandatory fail-closed conditions

Do not override the supervisor if it stops because of any accepted safety condition, including:

- zero available balance is not explicitly proven;
- any unexpected position/exposure, pending order, or unreconciled fill appears;
- permission is not exactly `read_only`;
- hostname/account/subaccount/position mode/leverage/clock/market health is invalid or unknown;
- submit/mutation reachability appears or counters become nonzero;
- exact revision / clean worktree / approved local environment cannot be proven;
- operational-mode audit/recovery/checkpoint state is unsafe or unknown;
- the 300-GET budget cannot admit the next complete cycle or is exhausted;
- the 1800-second monotonic deadline is reached;
- credentials/provider responses/evidence cannot remain sanitized;
- any unknown runtime/provider/storage exception prevents proving safe state.

No fail-closed condition authorizes account repair, funding, order cancellation, retry escalation, resetting a consumption marker, or scope expansion.

## Required durable evidence

Persist one bounded E7 artifact:

`status/e7/ZERO_CAPITAL_SHADOW_REPLACEMENT_SESSION_RESULT_20260826.md`

It may contain only sanitized evidence and must include, where available:

```text
task_id
replacement authorization_id
request_id
canonical action_id
local job id/state/exit code
exact executable revision
approved-local-Windows / clean-worktree classifications
historical first-session marker preserved = YES/NO/UNKNOWN
replacement authorization consumed = YES/NO/UNKNOWN
start/end UTC timestamps
elapsed_seconds
total/private/public-market/public-time GET counts
MUTATION_REQUEST_COUNT
SUBMIT_REQUEST_COUNT
available_balance_is_zero = YES/NO/UNKNOWN only
provider/api/environment/hostname classifications
permission/account-level/position-mode/dedicated-subaccount classifications without IDs
market freshness/finality/health classification
position-known / unexpected-exposure classification
isolated-leverage-known/valid classification
pending-order classification/count
unreconciled-fill classification/count without provider IDs
operational mode / mode revision / checkpoint / reconciliation classifications
cycle_count_completed
terminal_stop_reason
session_result = COMPLETE / FAIL_CLOSED / BLOCKED
```

Explicitly confirm that no API key/secret/passphrase, exact balance, UID/mainUID, signature, token/cookie, browser-auth material, raw private provider response, provider order/fill ID, or unnecessary local path was displayed or persisted.

## Result classification

### DONE

Use `DONE` only when the one replacement local job completed and durable sanitized result says `session_result=COMPLETE`, all required safety invariants remained satisfied, mutation/submit counts are zero, zero-capital classification remained explicit, historical first-session marker remained preserved, and no unauthorized runtime/capital action occurred.

Report release interpretation only as:

```text
Gate C — SHADOW_READY = PASS / unchanged
replacement bounded zero-capital SHADOW session = COMPLETE / PM REVIEW REQUIRED
SHADOW runtime = STOPPED / session complete / not recurring
PAPER = NOT AUTHORIZED
Gate D / LIVE = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
```

Do not self-declare a new release gate.

### PARTIAL

Use `PARTIAL` when the replacement session started/consumed authorization but terminated fail closed or otherwise did not produce a COMPLETE healthy result. Persist the exact sanitized terminal reason. Do not retry.

### BLOCKED

Use `BLOCKED` when preflight fails or the local request is refused before replacement session consumption/start. Persist sanitized evidence sufficient for PM to determine whether the replacement allowance remains unconsumed. Do not retry.

## Writable scope

Only:

- `coordination/E7/LOCAL_JOB_REQUEST.json` while required by the local mechanism; clear it according to normal completed/refused handling;
- `coordination/E7/STATUS.md`;
- `status/e7/ZERO_CAPITAL_SHADOW_REPLACEMENT_SESSION_RESULT_20260826.md`;
- optionally `status/INTEGRATION_STATUS.md` only if needed to record the terminal non-promotional bounded-session state.

Do not modify production source, tests, contracts, ADRs, migrations, E1-E6 files, local action catalog, Product Owner authorization artifacts, credentials, runtime implementation, or release-gate PASS criteria.

## Completion

Read latest `main`, verify wake task ID `E7-20260826-090`, execute only this TASK, persist bounded sanitized evidence, update `coordination/E7/STATUS.md`, commit/push to the target branch, and stop on `DONE`, `PARTIAL`, or `BLOCKED`.

Do not self-start a retry, third SHADOW session, recurring/continuous runtime, remediation, PAPER, Gate D, LIVE, provider mutation, order submission, or capital movement/exposure.
