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
