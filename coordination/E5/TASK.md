# E5 Current Task

- task_id: `E5-20260829-030`
- issued_at: `2026-08-29T14:02:00+08:00`
- state: `HOLD`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, accepted `contracts/PROTECTION_TRIGGER_VALIDITY_PROFILE_V0_1.md`, E5-20260829-029 PARTIAL evidence, merged PR #105, `status/PM_E5_029_REVIEW_20260829.md`

## Objective

Hold after PM static review accepted E5-029 only as an **unverified executable candidate** and merged it to main.

Authoritative state:

```text
E5 FP-03 producer/policy implementation = MERGED / STATIC CANDIDATE ACCEPTED
E5 local executable verification = NOT_RUN / NOT PASS
E4 FP-03 consumer/binding implementation = NEXT OWNER / DISPATCHED SEPARATELY
FP-03 overall = NOT EXECUTABLE-QUALIFIED
fresh combined E5+E4 approved-local credential-free requalification = REQUIRED AFTER E4
provider/private verification = NOT AUTHORIZED BY THIS HOLD
SHADOW/PAPER runtime = NOT AUTHORIZED
Gate D / LIVE = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
capital exposure = NONE
```

## Required actions while HOLD

- Preserve the merged E5 FP-03 producer/currentness semantics and accepted shared profile.
- Do not treat E5-029 `NOT_RUN` as PASS or DONE.
- Do not modify E4/provider code or shared contracts/ADRs.
- Do not self-start local requalification; final combined qualification is an E7-owned later task after E4 implementation review.
- Do not call OKX/provider endpoints or read/request/use credentials.
- Do not start SHADOW/PAPER, Gate D or LIVE.
- Do not mutate provider/account state, submit/cancel/amend/close orders, or move/expose capital.
- Do not use GitHub Actions/CI/hosted/GitHub-triggered compute.

## Unblock condition

PM may issue a fresh E5 task only if E4/E7 review identifies a bounded E5 defect or a shared-contract change requires E5 adaptation. Otherwise remain HOLD while E4 implements the consumer boundary and E7 later requalifies the combined exact revision.

## Writable scope

Only `coordination/E5/STATUS.md` for HOLD acknowledgement if needed.

## Completion

Acknowledge HOLD if needed and stop. Do not self-start E4 work, requalification, provider verification, SHADOW/PAPER, Gate D, LIVE, mutation, order action or capital movement/exposure.
