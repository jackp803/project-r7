# E7 Current Task

- task_id: `E7-20260829-110`
- issued_at: `2026-08-29T16:31:00+08:00`
- state: `HOLD`
- authority: `agents/E7_INTEGRATION.md`, `agents/PROJECT_MANAGER.md`, `agents/README.md`, accepted `external-manual-close-lifecycle-convergence-v0.1`, `status/PM_E7_109_REVIEW_20260829.md`, active LF-0 exact-revision infrastructure blocker

## Objective

Hold after PM accepted and merged E7-20260829-109 as the FP-10 contract/docs-only baseline.

Authoritative state:

```text
FP-10 contract design = ACCEPTED / DOCS ONLY
FP-10 executable implementation = NOT_STARTED / NOT PASS
FP-04 contract design = ACCEPTED / DOCS ONLY
FP-05 E4 provider-local design = ACCEPTED / DOCS ONLY
FP-11 contract design = ACCEPTED / DOCS ONLY
FP-16 contract design = ACCEPTED / DOCS ONLY
next bounded implementation = E5 provider-neutral FP-04 + FP-10 lifecycle consumer
LF-0 exact-revision infrastructure = BLOCKED / UNCHANGED
FP-03 combined qualification = NOT_RUN / NOT_PASS
provider-facing verification = NOT_RUN / NOT_INFERRED
SHADOW/PAPER = NOT_AUTHORIZED
10U bounded live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
```

## Required actions while HOLD

- Preserve accepted FP-04/FP-10/FP-11/FP-16 shared contracts and their exact currentness/authority boundaries.
- Do not implement E5/E4/E6 executable work under this HOLD.
- Do not create/retry Local Job Requests.
- Do not infer executable PASS from docs, merge status, or historical qualification evidence.
- Do not call provider/public/private endpoints or read/request/use credentials.
- Do not modify AgentBridge/local action infrastructure.
- Do not start SHADOW/PAPER, provider mutation, 10U live-fire, Gate D, or LIVE.
- Do not move/expose capital.
- Do not use GitHub Actions/CI/hosted/GitHub-triggered compute.

## Unblock condition

PM may issue a fresh E7 task after bounded owner implementations require integration/safety composition, a shared-contract ambiguity is surfaced, authoritative approved-local exact-revision infrastructure is restored, or another cross-module/release issue requires E7 action.

## Writable scope

Only `coordination/E7/STATUS.md` for HOLD acknowledgement if needed.

## Completion

Acknowledge HOLD if needed and stop. Do not self-start FP-04/05/10/11/16 executable work, AgentBridge changes, exact-revision preparation, qualification, provider verification, SHADOW/PAPER, 10U live-fire, Gate D, LIVE, mutation, order action or capital movement/exposure.
