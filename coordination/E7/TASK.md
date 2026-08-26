# E7 Current Task

- task_id: `E7-20260826-082`
- issued_at: `2026-08-26T11:05:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-c-production-readonly-canonical-reverification-20260826`
- authority: `agents/E7_INTEGRATION.md`, `agents/PROJECT_MANAGER.md`, `coordination/LOCAL_ACTION_CATALOG.md`, `contracts-v0.1`, accepted PR #92 credential-free PASS, Product Owner Gate C / SHADOW-only authorization

## Objective

Replace only the terminal refused E7-081 request with one new production OKX read-only Gate C re-verification using the registered canonical action. E7-081 remains immutable `BLOCKED / LOCAL_ACTION_NOT_REGISTERED`; do not reuse its request ID.

## Exact executable boundary

```text
revision  = ab725965e96cac7a9769fd1ab15a3e626f920b95
action_id = GATE_C_OKX_PRODUCTION_READONLY
```

Before requesting execution, verify latest `main`, this exact task ID, the exact clean active worktree, approved Windows local environment, ignored DPAPI credential surface availability, and operator-confirmed `https://openapi.okx.com` identity without printing secrets.

Create exactly one new request ID in `coordination/E7/LOCAL_JOB_REQUEST.json`. Do not invent another action alias.

## Authorized provider surface

Only the accepted `OKXShadowProviderReader` GET batch is authorized:

```text
GET /api/v5/public/time
GET /api/v5/account/config
GET /api/v5/account/balance?ccy=USDT
GET /api/v5/account/positions?instId=BTC-USDT-SWAP
GET /api/v5/account/leverage-info?instId=BTC-USDT-SWAP&mgnMode=isolated
GET /api/v5/trade/orders-pending?instId=BTC-USDT-SWAP&instType=SWAP
GET /api/v5/trade/fills?instId=BTC-USDT-SWAP&instType=SWAP
```

All mutation, order, cancel/amend/close, transfer, deposit, withdrawal, WebSocket private access, Demo/PAPER/SHADOW runtime start, Gate D and LIVE remain forbidden.

## PASS candidate requirements

- provider/API/environment identity correct;
- clock healthy and skew within 5000 ms;
- permission exactly `read_only`;
- account level `2`, position mode `net_mode`, dedicated sub-account confirmed;
- available USDT truth known and sanitized `available_balance_is_zero=true`;
- no unexpected position, pending order or unreconciled fill activity;
- isolated leverage observation known/valid;
- `private_get_count=6`, mutation/submit count `0`;
- no secret, exact balance, UID, raw response, signature, order/fill ID or auth material in evidence.

Unknown or contradictory truth is FAIL/BLOCKED, never permission. Preserve the Local Job result without reinterpretation.

## Writable scope and completion

- `coordination/E7/LOCAL_JOB_REQUEST.json`
- `coordination/E7/STATUS.md`
- `status/e7/GATE_C_PRODUCTION_READONLY_CANONICAL_REVERIFICATION_20260826.md`

Commit/push the target branch and stop on `DONE`, `PARTIAL`, or `BLOCKED`. Even on a healthy result, report only `GATE_C_REVIEW_CANDIDATE=YES`; PM must perform final Gate C review. Do not start SHADOW, Gate D or LIVE.
