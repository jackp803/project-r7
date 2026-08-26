# E7 Current Task

- task_id: `E7-20260826-088`
- issued_at: `2026-08-26T17:12:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-zero-capital-shadow-session-20260826`
- authority: `agents/E7_INTEGRATION.md`, `agents/PROJECT_MANAGER.md`, `agents/README.md`, `contracts-v0.1`, `status/PRODUCT_OWNER_ZERO_CAPITAL_SHADOW_AUTHORIZATION_20260826.md`, accepted `E7-20260826-086`, `status/e7/ZERO_CAPITAL_SHADOW_SESSION_READINESS_20260826.md`, `status/AGENTBRIDGE_ZERO_CAPITAL_SHADOW_ACTION_REGISTRATION_20260826.md`, `coordination/LOCAL_ACTION_CATALOG.md`, `status/BLOCKERS.md`

## Objective

Execute exactly one Product-Owner-authorized **bounded zero-capital SHADOW runtime session** using the registered canonical local action and persist only sanitized durable evidence for PM review.

This task consumes the single authorized session if the local supervisor reaches its consumption-marker point. It does not authorize a retry, second session, recurring operation, PAPER, Gate D, LIVE, provider/account mutation, order submission, or capital exposure.

## Exact execution boundary

```text
qualified executable revision = ab725965e96cac7a9769fd1ab15a3e626f920b95
canonical action_id            = GATE_C_ZERO_CAPITAL_SHADOW_SESSION
request_id                     = REQ-E7-SHADOW-088-01-8C4F2A71
approved computer              = current registered local Windows computer only
provider/environment           = OKX production read-only shadow
REST hostname                  = https://openapi.okx.com
maximum monotonic duration     = 1800 seconds
maximum shared HTTPS GETs      = 300
available capital              = exactly zero
provider/account mutation      = forbidden
order submission               = forbidden
capital exposure               = forbidden
GitHub compute                 = forbidden
```

Use exactly the registered canonical action. Do not add executable paths, shell text, arguments, environment values, credentials, hostnames, branch names, remotes, or local filesystem paths to the Local Job Request.

## Preflight before creating the Local Job Request

Read latest `main` and verify:

1. wake task ID is exactly `E7-20260826-088` and task is ACTIVE;
2. Product Owner authorization remains current and no authoritative evidence says the one-session authorization was already consumed;
3. `GATE_C_ZERO_CAPITAL_SHADOW_SESSION` remains present in `coordination/LOCAL_ACTION_CATALOG.md`;
4. operator registration evidence remains `REGISTERED / ALLOWLISTED / NOT EXECUTED` or otherwise authoritatively confirms the single-session allowance is still available;
5. no new authoritative blocker conflicts with execution.

Do not read or expose credential values during repository preflight.

If any preflight item fails, do not create the Local Job Request; update E7 STATUS to `BLOCKED` with a sanitized reason and stop.

## Local Job Request

Create at most one request using exactly:

```text
request_id = REQ-E7-SHADOW-088-01-8C4F2A71
action_id  = GATE_C_ZERO_CAPITAL_SHADOW_SESSION
```

No second request is authorized in this task.

If AgentBridge refuses the request before the session consumption marker is created, preserve the refusal as terminal `BLOCKED`; do not retry under the same or a new request ID.

If the session starts/consumes the authorization and then terminates for any reason, the authorization is consumed. Do not retry or start another session.

## Authorized runtime behavior

The local operator-owned supervisor is authoritative for enforcing the accepted E7-086 session contract. E7 must not weaken, bypass, reinterpret, or repair around its fail-closed behavior.

Required invariant throughout the session:

```text
elapsed_seconds <= 1800
HTTPS_GET_COUNT <= 300
MUTATION_REQUEST_COUNT = 0
SUBMIT_REQUEST_COUNT = 0
available_balance_is_zero = YES
capital_exposure = NONE
```

The session must remain within the accepted read-only E1/E2/E4/E5/E6/E7 Shadow composition and may persist sanitized SHADOW evidence/checkpoints only.

No POST/PUT/PATCH/DELETE, order place/cancel/amend/close, leverage/account/position-mode change, transfer, deposit, withdrawal, funding action, Demo execution, browser/provider UI automation, PAPER runtime, Gate D or LIVE is permitted.

## Mandatory fail-closed conditions

Do not override the supervisor if it stops because of any accepted safety condition, including:

- zero available balance is not explicitly proven;
- any unexpected position/exposure, pending order, or unreconciled fill appears;
- permission is not exactly `read_only`;
- hostname/account/subaccount/position mode/clock health is invalid or unknown;
- market data is stale/future/malformed/non-final/non-monotonic;
- leverage/risk/mode/checkpoint/reconciliation state is unsafe or unknown;
- submit/mutation reachability appears or counters become nonzero;
- exact revision / clean worktree / approved local environment cannot be proven;
- the 300-GET budget cannot admit the next complete cycle or is exhausted;
- the 1800-second monotonic deadline is reached;
- credentials/provider responses/evidence cannot remain sanitized;
- any unknown runtime/provider/storage exception prevents proving safe state.

No fail-closed condition authorizes account repair, funding, order cancellation, retry escalation, or scope expansion.

## Required durable evidence

Persist one bounded E7 artifact:

`status/e7/ZERO_CAPITAL_SHADOW_SESSION_RESULT_20260826.md`

It may contain only sanitized evidence and must include, where available:

```text
task_id
request_id
canonical action_id
local job_id / state / exit code
exact executable revision
approved-local-Windows / clean-worktree classifications
session authorization consumed = YES/NO/UNKNOWN
start/end UTC timestamps
elapsed_seconds
total_https_get_count
private_get_count
public_market_get_count
public_provider_time_get_count
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
operational mode / checkpoint / reconciliation classifications
cycle_count_completed
terminal_stop_reason
session_result = COMPLETE / FAIL_CLOSED / BLOCKED
```

Explicitly confirm that no API key/secret/passphrase, exact balance, UID/mainUID, signature, token/cookie, browser-auth material, raw private provider response, provider order/fill ID, or unnecessary local path was displayed or persisted.

## Result classification

### DONE

Use `DONE` only when the one authorized local job completed and durable sanitized result says `session_result=COMPLETE`, all required safety invariants remained satisfied, mutation/submit counts are zero, zero-capital classification remained explicit, and no unauthorized runtime/capital action occurred.

Report release interpretation only as:

```text
Gate C — SHADOW_READY = PASS / unchanged
bounded zero-capital SHADOW session = COMPLETE / PM REVIEW REQUIRED
SHADOW runtime = STOPPED / session complete / not recurring
PAPER = NOT AUTHORIZED
Gate D / LIVE = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
```

Do not self-declare a new release gate.

### PARTIAL

Use `PARTIAL` when the session started/consumed authorization but terminated fail-closed or otherwise did not produce a COMPLETE healthy result. Persist the exact sanitized terminal reason. Do not retry.

### BLOCKED

Use `BLOCKED` when preflight fails or the local request is refused before session consumption/start. Persist sanitized evidence sufficient for PM to determine whether the one-session allowance remains unconsumed. Do not retry.

## Writable scope

Only:

- `coordination/E7/LOCAL_JOB_REQUEST.json` while required by the local mechanism; clear it according to normal completed/refused request handling;
- `coordination/E7/STATUS.md`;
- `status/e7/ZERO_CAPITAL_SHADOW_SESSION_RESULT_20260826.md`;
- optionally `status/INTEGRATION_STATUS.md` only if needed to record the terminal non-promotional bounded-session state.

Do not modify production source, tests, contracts, ADRs, migrations, E1-E6 files, local action catalog, Product Owner authorization, credentials, runtime implementation, or release-gate PASS criteria.

## Completion

Read latest `main`, verify wake task ID `E7-20260826-088`, execute only this TASK, persist the bounded sanitized evidence, update `coordination/E7/STATUS.md`, commit/push to the target branch, and stop on `DONE`, `PARTIAL`, or `BLOCKED`.

Do not self-start a second SHADOW session, recurring/continuous runtime, remediation, PAPER, Gate D, LIVE, provider mutation, order submission, or capital movement/exposure.
