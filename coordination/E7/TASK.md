# E7 Current Task

- task_id: `E7-20260826-091`
- issued_at: `2026-08-26T23:18:00+08:00`
- state: `HOLD`
- authority: `agents/E7_INTEGRATION.md`, `agents/PROJECT_MANAGER.md`, `agents/README.md`, accepted `E7-20260826-090`, `status/e7/ZERO_CAPITAL_SHADOW_REPLACEMENT_SESSION_RESULT_20260826.md`, `status/BLOCKERS.md`

## Objective

Hold after PM accepted E7-20260826-090 only as terminal `PARTIAL / FAIL_CLOSED` evidence for the single replacement zero-capital SHADOW session.

Authoritative state:

```text
Gate C — SHADOW_READY = PASS / UNCHANGED
E7-090 replacement SHADOW session = FAIL_CLOSED / PARTIAL
replacement authorization = PO-ZERO-CAPITAL-SHADOW-REAUTH-20260826-01 / CONSUMED / NO RETRY
terminal_stop_reason = UNSAFE_PROVIDER_OR_RECONCILIATION_STATE
HTTPS GETs = 9
mutation requests = 0
submit requests = 0
available_balance_is_zero = YES
capital exposure = NONE
operational mode = LOCKED
complete safe SHADOW cycles = 0
successful SHADOW runtime evidence = NOT ESTABLISHED
PAPER = NOT AUTHORIZED
Gate D / LIVE = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
```

## Required actions while HOLD

- Preserve the historical E7-088 consumed authorization and the E7-090 consumed replacement authorization.
- Preserve `status/e7/ZERO_CAPITAL_SHADOW_REPLACEMENT_SESSION_RESULT_20260826.md` as fail-closed evidence; do not reinterpret it as successful SHADOW evidence.
- Do not create a Local Job Request.
- Do not retry SHADOW, start a third session, or start recurring/continuous SHADOW.
- Do not start PAPER, Gate D, or LIVE.
- Do not submit/place/cancel/amend/close orders, mutate provider/account state, move capital, or expose capital.
- Do not reset, delete, rename, overwrite, or recreate either consumption marker.
- Do not request/read/use credentials or provider-sensitive payloads.
- Do not use GitHub Actions/CI/hosted/GitHub-triggered compute.

## Unblock condition

Any third or replacement SHADOW session requires a new explicit Product Owner authorization with its own bounded runtime/safety limits, followed by a fresh PM task and unique request ID. No worker or operator may infer authority from Gate C PASS, the registered action, prior authorization artifacts, or the E7-090 fail-closed result.

## Writable scope

Only `coordination/E7/STATUS.md` for HOLD acknowledgement if needed.

## Completion

Acknowledge HOLD if needed and stop.