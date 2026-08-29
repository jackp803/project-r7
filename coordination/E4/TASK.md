# E4 Current Task

- task_id: `E4-20260829-027`
- issued_at: `2026-08-29T15:25:00+08:00`
- state: `HOLD`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, accepted `bounded-live-fire-readiness-v0.1`, accepted `okx-swap-action-role-capability-v0.1`, `status/PM_E4_026_REVIEW_20260829.md`

## Objective

Hold after PM accepted and merged E4-20260829-026 as a docs-only FP-02 capability design baseline.

Authoritative state:

```text
FP-02 capability design = ACCEPTED / DOCS ONLY
FP-02 executable implementation = NOT_STARTED / NOT_PASS
FP-03 combined candidate = IMPLEMENTED / UNQUALIFIED
LF-0 exact-revision infrastructure = BLOCKED
LF-1 credential-free qualification = NOT_RUN / NOT_PASS
LF-2 P0 closure = PARTIAL
FP-05 residual/close sizing = DEPENDS ON FP-02 capability vocabulary
FP-11 protection registry/readback = SEPARATE DOWNSTREAM DEPENDENCY
provider/private verification = NOT_RUN / NOT_INFERRED
SHADOW/PAPER = NOT_AUTHORIZED
10U bounded live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
```

## Required actions while HOLD

- Preserve the accepted FP-02 design baseline.
- Do not implement executable FP-02 translation under this HOLD.
- Do not start FP-05 or FP-11.
- Do not create Local Job Requests.
- Do not call provider/public/private endpoints.
- Do not read/request/use credentials.
- Do not mutate provider/account state or submit/cancel/amend/close orders.
- Do not start SHADOW/PAPER, 10U live-fire, Gate D, or LIVE.
- Do not move/expose capital.
- Do not use GitHub Actions/CI/hosted/GitHub-triggered compute.

## Unblock condition

PM may issue a fresh bounded E4 task after the relevant shared/dependency semantics are accepted and the selected sequencing permits executable FP-02/FP-05/FP-11 work, or if a later qualification exposes a reproducible E4 defect.

## Writable scope

Only `coordination/E4/STATUS.md` for HOLD acknowledgement if needed.

## Completion

Acknowledge HOLD if needed and stop. Do not self-start executable FP-02, FP-05, FP-11, provider verification, exact-revision preparation, qualification, SHADOW/PAPER, 10U live-fire, Gate D, LIVE, mutation, order action or capital movement/exposure.
