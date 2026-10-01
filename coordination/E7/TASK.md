# E7 Current Task

- task_id: `E7-20261001-121`
- issued_at: `2026-10-01T16:56:00+08:00`
- state: `HOLD`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts/BOUNDED_LIVE_FIRE_READINESS_PROFILE_V0_1.md`, `status/PM_CODEX_LF3_COMPLETION_REVIEW_20261001.md`, `status/P0_LF_READINESS_20261001.md`

## Objective

Hold E7 chat execution after PM acceptance of LF-3 while the Product Owner
decides whether to grant fresh authority for LF-4 Provider Read-Only
Verification.

Do not duplicate the accepted LF-3 work and do not self-start LF-4.

## Current accepted state

```text
qualified executable revision = 1cd9a408d0c4f22b8e8f22f567005e1af45a0035
LF-0 = PASS
LF-1 = PASS
LF-2 = PASS
LF-3 = PASS
LF-4 = NOT_STARTED / FRESH PRODUCT OWNER AUTHORITY REQUIRED
LF-5 = NOT_STARTED / NOT_AUTHORIZED
LF-6 = NOT_STARTED / NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital = NONE
```

## Required actions while HOLD

- Preserve the exact-revision LF-3 evidence semantics.
- Do not rerun LF-0/LF-1/LF-2/LF-3 unless PM issues a new task because later
  executable changes invalidate accepted qualification.
- Do not request, read or use provider credentials.
- Do not call private provider APIs or mutate provider/account state.
- Do not start SHADOW, PAPER, bounded live fire, Gate D or LIVE.
- Do not move or expose capital.
- Wait for PM to issue a new authoritative TASK only after fresh Product Owner
  authority exists for the next gate.

## Writable scope

Only `coordination/E7/STATUS.md` for HOLD acknowledgement if needed.

## Completion

Acknowledge HOLD if necessary and stop.
