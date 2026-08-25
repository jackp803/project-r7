# E7 Current Task

- task_id: `E7-20260825-073`
- issued_at: `2026-08-25T21:44:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-c-production-readonly-verification-20260825`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate C baseline PR #75, accepted Phase-1/2/3 work through PR #81, preserved failed credential-free qualification PR #82, diagnostic PR #83, accepted E6 remediation PR #84, accepted credential-free requalification PR #85 merge `e8d0c956b4e504acb91f6aa9323526d2fea4d2e9`, Product Owner Gate C / SHADOW-only authorization including separately governed production-provider read-only verification after safe local operator configuration

## Objective

Execute only the operator-gated **Gate C credential-dependent production read-only verification** for the accepted OKX Shadow provider boundary.

The credential-free Gate C blocker is already closed by accepted E7-072 evidence:

```text
credential-free source revision = 83be94fbc4ee666156c2aaf7a7141b3eda9a4b4c
credential-free result          = PASS / 579 tests / 14 of 14 suites
Gate C                          = BLOCKED / credential-dependent read-only evidence still required
SHADOW runtime                  = NOT STARTED
Gate D / LIVE                   = BLOCKED / NOT AUTHORIZED
```

This task must not start a SHADOW runtime. It verifies only the accepted production read-only provider boundary and sanitized evidence needed for Gate C review.

## Exact executable source revision

All project-code/provider verification must use exactly the credential-free-qualified source revision:

```text
83be94fbc4ee666156c2aaf7a7141b3eda9a4b4c
```

Before any provider request, local evidence must prove:

- repository revision exactly equals that SHA;
- working tree is clean;
- approved local Windows / non-GitHub environment;
- Python executable/version and `PYTHONPATH=src`;
- no GitHub Actions/CI/hosted/GitHub-triggered compute.

If any source/environment precondition cannot be established, stop `BLOCKED` without provider traffic.

## Operator prerequisites — fail before provider traffic if absent

The local operator must have configured all of the following outside Git and outside chat:

1. a dedicated R7 OKX **sub-account** for Gate C observation;
2. an OKX API key for that sub-account with provider permission intended as **Read only** — no Trade and no Withdraw permission;
3. key/secret/passphrase stored only in an ignored local secret/config surface or OS/local secret store consumed by the approved local execution mechanism;
4. the official OKX REST hostname for the account-registration region explicitly confirmed in local configuration;
5. no expectation that this task will place/cancel/amend orders, change leverage/modes, transfer assets, or clean account state by mutation.

Never ask the Product Owner to paste key, secret, passphrase, token, cookie, browser auth, raw UID, exact balance, or provider order/fill IDs into chat, Git, task files, callbacks, screenshots, or logs.

If the dedicated sub-account, regional hostname, or locally stored credentials are unavailable, stop `BLOCKED` and state only the exact operator action required. Do not invent credentials or guess a regional hostname.

## Verification implementation boundary

Reuse the accepted E4 production read-only Gate C surface unchanged:

- `OKXShadowProviderReader` / `OKXShadowReadResult`;
- exact read-only allowlist and signing semantics already accepted;
- no `OKXDemoAdapter` injection;
- no broker submitter;
- no `ExecutionGateway.submit_approved_plan`;
- no generic authenticated transport exposing non-GET methods.

Do not modify provider/auth implementation, tests, contracts, risk policy, storage, strategy logic, or execution semantics in this task. A reproducible implementation defect must be persisted and returned to PM for bounded owner remediation.

## Allowed provider requests

### Required public clock request

```text
GET /api/v5/public/time
```

This must precede the private batch. Absolute local/provider clock skew must be `<= 5000 ms`; otherwise abort before private evidence is accepted.

### Exact private authenticated allowlist

Only these six GET requests are authorized:

```text
GET /api/v5/account/config
GET /api/v5/account/balance?ccy=USDT
GET /api/v5/account/positions?instId=BTC-USDT-SWAP
GET /api/v5/account/leverage-info?instId=BTC-USDT-SWAP&mgnMode=isolated
GET /api/v5/trade/orders-pending?instType=SWAP&instId=BTC-USDT-SWAP
GET /api/v5/trade/fills?instType=SWAP&instId=BTC-USDT-SWAP
```

`GET /api/v5/account/config` must be the first private read. Its normalized permission category must be exactly `read_only`; if provider evidence indicates Trade, Withdraw, unknown, malformed, or contradictory permission, hard-abort the remainder as required by the accepted fail-closed implementation.

No other private endpoint is authorized. `GET /api/v5/trade/order` is not authorized. Private WebSocket is not authorized.

### Optional public non-authenticated verification

Only if the existing bounded verification harness already requires it, the following public GETs are additionally allowed without changing production code:

```text
GET /api/v5/public/instruments?instType=SWAP&instId=BTC-USDT-SWAP
GET /api/v5/market/ticker?instId=BTC-USDT-SWAP
GET /api/v5/market/candles?instId=BTC-USDT-SWAP&bar=<required 1m|15m|1H|4H>
```

Do not widen this list.

## Absolute no-mutation boundary

The verification must prove:

```text
allowed authenticated HTTP method = GET only
mutation_request_count             = 0
submit_request_count               = 0
```

Forbidden before, during, and after verification:

- order place/batch-place;
- cancel/batch-cancel;
- amend/batch-amend;
- close position;
- algo/trigger/conditional order mutation;
- leverage mutation;
- account mode / position mode mutation;
- isolated-margin add/reduce;
- transfer/sub-account transfer;
- deposit/withdrawal/funding movement;
- Demo balance adjustment;
- POST/PUT/PATCH/DELETE provider request;
- PAPER or SHADOW runtime start;
- Gate D/LIVE/capital exposure.

Unexpected provider position, pending order, fill activity, unknown account truth, or other contradictory state is evidence of a fail-closed Gate C observation. Do not mutate the account to make verification pass.

## Required sanitized evidence

Persist E7-owned evidence such as:

```text
status/e7/GATE_C_PRODUCTION_READONLY_VERIFICATION_20260825.md
```

It may contain only sanitized release evidence, including:

- task/request/action/job IDs;
- exact source revision and clean-tree proof;
- OS/Python/PYTHONPATH;
- provider = OKX and environment = production-read-only Shadow verification;
- configured regional hostname;
- canonical/provider instrument identities;
- provider permission category = `read_only` when verified;
- account-level / position-mode / dedicated-subaccount classification without raw UID values;
- clock skew milliseconds;
- `balance_known` but never exact balance;
- position-known / unexpected-exposure boolean;
- leverage-known/acceptable boolean;
- pending-order count only;
- recent/unreconciled fill bounded counts/checkpoint status without provider IDs;
- exact outbound endpoint names/methods and call counts;
- `mutation_request_count=0` and `submit_request_count=0`;
- normalized health/fail-closed reason codes;
- overall verification PASS/FAIL/BLOCKED.

Durable/public evidence must not contain raw key/secret/passphrase/signature, UID/main UID, API label, bound IP list, exact balance, provider order/fill IDs, full provider responses, cookies/tokens/browser auth, or unnecessary user-specific filesystem paths.

## Result interpretation

### PASS

Credential-dependent read-only verification may be marked PASS only if:

- exact source/clean approved-local environment is proven;
- operator-confirmed regional hostname is used;
- `account/config` verifies permission exactly `read_only`;
- the accepted read-only observation batch completes without provider/auth/clock/domain/account-state safety violation;
- authenticated outbound calls are only the exact GET allowlist;
- `mutation_request_count=0` and `submit_request_count=0`;
- no secret/sensitive material appears in durable evidence.

A PASS in this task is **evidence for PM Gate C review only**. Worker must not independently set Gate C PASS or start SHADOW runtime.

### FAIL / BLOCKED

Fail closed and stop if any of the following occurs:

- operator prerequisites absent;
- regional hostname unknown/unconfirmed;
- credential source unavailable;
- provider permission not exactly `read_only`;
- provider/auth/signature/clock failure;
- unexpected position/pending-order/new-unreconciled-fill state;
- malformed/unknown required account truth;
- any non-GET or non-allowlisted request attempt;
- redaction cannot be guaranteed;
- any authority/safety boundary cannot be satisfied.

Do not repair source, widen allowlists, mutate provider state, rerun repeatedly to hide a failure, or start another task.

## Local-job boundary

Use only the approved local non-GitHub AgentBridge/local-job mechanism. Use a task-specific action such as:

```text
GATE_C_PRODUCTION_READONLY_VERIFICATION
```

The task may execute at most the bounded read-only verification needed to produce one reviewable result. No GitHub compute is allowed.

## Writable scope

Only E7-owned provider-verification control/evidence paths:

- `coordination/E7/LOCAL_JOB_REQUEST.json` if required;
- `coordination/E7/STATUS.md`;
- `status/e7/**` for sanitized verification evidence;
- `status/INTEGRATION_STATUS.md` / `status/RELEASE_GATES.md` only to preserve an accurate non-promotional Gate C state.

Forbidden:

- production source/test changes;
- E1-E6 TASK/STATUS or owned code/tests;
- contracts/ADRs/migrations;
- provider implementation/auth changes;
- real secret values in Git/chat/evidence;
- provider mutation/order submission;
- PAPER/SHADOW runtime start;
- Gate D/LIVE/capital exposure;
- GitHub Actions/CI/hosted/GitHub-triggered compute.

## Completion

Read latest `main`, verify wake task ID `E7-20260825-073`, execute only this TASK, update `coordination/E7/STATUS.md`, commit/push required sanitized evidence to the target branch, and stop on `DONE`, `PARTIAL`, or `BLOCKED`. Do not self-start SHADOW runtime, Gate D, LIVE, remediation, or another task.