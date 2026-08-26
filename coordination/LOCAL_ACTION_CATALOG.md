# AgentBridge Canonical Local Action Catalog

This file names stable action identities available to PM/Workers. It grants no capability by
itself: the local AgentBridge configuration and runtime flags remain authoritative and
deny-by-default.

## Credential-free project verification

- `GATE_A_MARKET_DATA`
- `GATE_A_INDICATORS`
- `GATE_A_STRATEGY`
- `GATE_A_BACKTEST`
- `GATE_A_VALIDATION`
- `GATE_A_REGISTRY`
- `GATE_A_STORAGE`
- `GATE_A_INTEGRATION`
- `GATE_B_APPROVED_LOCAL_VERIFICATION`
- `GATE_B_BOUNDED_DIAGNOSTIC_RERUN`
- `GATE_B_POST_REMEDIATION_QUALIFICATION`
- `GATE_C_CREDENTIAL_FREE_QUALIFICATION`
- `GATE_C_CREDENTIAL_FREE_REQUALIFICATION`

## Production read-only observation

- `GATE_C_OKX_PRODUCTION_READONLY`

This action is bounded to the operator-confirmed OKX production REST hostname, Windows
DPAPI-protected local credentials, the fixed GET allowlist, sanitized output and no mutation.
Its presence is not authorization to run it; the PM TASK, operator prerequisites and runtime
flags must also permit the exact verification.

## Bounded zero-capital SHADOW session

- `GATE_C_ZERO_CAPITAL_SHADOW_SESSION`

This is a distinct, single-consumption runtime-session action. It is not an alias for
`GATE_C_OKX_PRODUCTION_READONLY` and must not be used for recurring operation.

The operator-owned supervisor is fixed to the registered local Windows computer and exact
clean revision `ab725965e96cac7a9769fd1ab15a3e626f920b95`. It pins all E1/E4 traffic to
`https://openapi.okx.com`, admits only the fixed public/read-only GET paths, shares one
pre-dispatch 300-GET budget across E1 and E4, uses a monotonic 1800-second deadline, denies
redirects/non-GET/mutation/submission, requires explicitly zero available capital, and stops
fail closed on every E7-086 safety condition. It emits sanitized evidence only.

The action uses a durable local consumption marker created immediately before session network
operation. Once a session starts, a later request cannot consume the same Product Owner
authorization again. Registration does not itself start or consume the authorized session;
execution still requires a fresh matching PM TASK and E7 Local Job Request.

## Worktree preparation

- `PREPARE_EXACT_REVISION`

This is a separate, normally disabled operator capability. It accepts only a full approved
revision reachable from registered `origin/main`, creates a new clean worktree without
overwriting an existing one, and must be disabled again after preparation.

## Request rules

1. Use a unique task-specific `request_id`.
2. Reuse the matching canonical `action_id` exactly as written here.
3. Never add shell text, executable paths, arguments, environment secrets, branch names,
   remotes or filesystem paths to a Local Job Request.
4. If no action matches, stop on `LOCAL_ACTION_NOT_REGISTERED`; do not invent an alias.
5. A refused request is not retried under the same request ID.
