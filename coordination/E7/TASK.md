# E7 Current Task

- task_id: `E7-20260829-100`
- issued_at: `2026-08-29T13:41:00+08:00`
- state: `HOLD`
- authority: `agents/E7_INTEGRATION.md`, `agents/PROJECT_MANAGER.md`, `agents/README.md`, accepted `E7-20260829-099`, `contracts/PROTECTION_TRIGGER_VALIDITY_PROFILE_V0_1.md`, `status/e7/FP03_PROTECTION_TRIGGER_CONTRACT_HANDOFF_20260829.md`, `status/PM_E7_099_REVIEW_20260829.md`

## Objective

Hold after PM accepted and merged the FP-03 shared protection-trigger validity profile. E5 now owns the first executable downstream implementation step; E4 follows only after E5 implementation is reviewed.

Authoritative state:

```text
FP-03 shared contract = ACCEPTED / protection-trigger-validity-v0.1
E5 producer/policy implementation = DISPATCHED SEPARATELY
E4 consumer/provider mapping implementation = NOT YET DISPATCHED
FP-03 executable qualification = NOT YET ESTABLISHED
provider/private verification = NOT AUTHORIZED BY THIS HOLD
SHADOW/PAPER runtime = NOT AUTHORIZED
Gate D / LIVE = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
```

## Required actions while HOLD

- Preserve the accepted profile and handoff semantics.
- Do not implement E5/E4 domain code under E7 HOLD.
- Do not create a Local Job Request.
- Do not run provider-facing verification or call OKX.
- Do not read/request/use credentials.
- Do not start SHADOW/PAPER, Gate D or LIVE.
- Do not mutate provider/account state, submit/cancel/amend/close orders, or move/expose capital.
- Do not use GitHub Actions/CI/hosted/GitHub-triggered compute.

## Unblock condition

PM may issue a fresh E7 integration/requalification task only after required E5/E4 executable work is accepted, or if a new authoritative cross-module ambiguity requires E7 action.

## Writable scope

Only `coordination/E7/STATUS.md` for HOLD acknowledgement if needed.

## Completion

Acknowledge HOLD if needed and stop. Do not self-start E5/E4 implementation, provider validation, SHADOW/PAPER, Gate D, LIVE, mutation, order action or capital movement/exposure.
