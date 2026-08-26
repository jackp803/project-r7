# E7 Current Task

- task_id: `E7-20260826-083`
- issued_at: `2026-08-26T11:08:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-c-complete-sanitized-readonly-evidence-20260826`
- authority: `agents/E7_INTEGRATION.md`, `agents/PROJECT_MANAGER.md`, `coordination/LOCAL_ACTION_CATALOG.md`, `contracts-v0.1`, accepted credential-free PASS, E7-082 healthy provider observation, Product Owner Gate C / SHADOW-only authorization

## Objective

Perform one final production OKX read-only evidence run using the now-updated canonical harness, solely to add the sanitized assertions missing from E7-082. Preserve E7-081 REFUSED and E7-082 PARTIAL; do not reinterpret or overwrite them.

## Exact boundary

```text
revision  = ab725965e96cac7a9769fd1ab15a3e626f920b95
action_id = GATE_C_OKX_PRODUCTION_READONLY
```

Use a new request ID. Verify latest `main`, this task ID, exact clean active worktree, approved Windows local environment, DPAPI credential surface availability without disclosure, and confirmed `https://openapi.okx.com`.

The action must expose only sanitized evidence and must exit nonzero unless the observation is healthy and runtime available USDT balance is exactly zero. Required explicit output includes:

```text
AVAILABLE_BALANCE_IS_ZERO=YES
MUTATION_REQUEST_COUNT=0
SUBMIT_REQUEST_COUNT=0
```

Also require: `read_only`, account level `2`, `net_mode`, dedicated sub-account, healthy clock, known position with no exposure, valid isolated leverage, zero pending orders, zero new unreconciled fills, six private GETs, no reason codes, no credential/exact-balance/UID/raw-response/signature/order/fill/auth disclosure.

Only the fixed accepted seven GET requests are authorized. All POST/PUT/PATCH/DELETE, order/cancel/amend/close, leverage/account mutation, transfer/deposit/withdrawal, Demo, PAPER/SHADOW runtime start, Gate D and LIVE are forbidden.

## Writable scope and completion

- `coordination/E7/LOCAL_JOB_REQUEST.json`
- `coordination/E7/STATUS.md`
- `status/e7/GATE_C_COMPLETE_SANITIZED_READONLY_EVIDENCE_20260826.md`

On complete healthy evidence report `DONE` and `GATE_C_REVIEW_CANDIDATE=YES`; do not declare Gate C PASS. Otherwise preserve the exact result and stop `PARTIAL` or `BLOCKED`.
