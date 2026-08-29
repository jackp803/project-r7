# E4 Current Task

- task_id: `E4-20260829-029`
- issued_at: `2026-08-29T16:15:00+08:00`
- state: `HOLD`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, accepted `okx-swap-close-residual-sizing-v0.1`, `status/PM_E4_028_REVIEW_20260829.md`

## Objective

Hold after PM accepted and merged E4-20260829-028 as a docs-only FP-05 close/residual sizing design baseline.

Authoritative state:

```text
FP-05 design = ACCEPTED / DOCS ONLY
FP-05 executable implementation = NOT_STARTED / NOT_PASS
FP-02 close-role provider mutation capability = UNRESOLVED_FAIL_CLOSED
FP-04 contract design = ACCEPTED / DOCS ONLY
FP-11 contract design = ACCEPTED / DOCS ONLY
FP-10 contract sequencing = DISPATCHED SEPARATELY TO E7
LF-0 exact-revision infrastructure = BLOCKED
FP-03 combined qualification = NOT_RUN / NOT_PASS
provider-facing verification = NOT_RUN / NOT_INFERRED
SHADOW/PAPER = NOT_AUTHORIZED
10U bounded live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
```

## Required actions while HOLD

- Preserve accepted FP-02/FP-05 provider-local design semantics.
- Do not self-start executable FP-05 or provider close translation.
- Do not create Local Job Requests or use GitHub compute.
- Do not call provider endpoints, read credentials, mutate provider/account state, or submit/cancel/amend/close orders.
- Do not start SHADOW/PAPER, 10U live-fire, Gate D, or LIVE.
- Do not move/expose capital.

## Unblock condition

PM may issue a fresh bounded E4 task after relevant shared/provider capability semantics and sequencing are accepted, or if a later exact-revision qualification exposes a reproducible E4 defect.

## Writable scope

Only `coordination/E4/STATUS.md` for HOLD acknowledgement if needed.

## Completion

Acknowledge HOLD if needed and stop. Do not self-start executable FP-02/FP-05/FP-10/FP-11 work, provider verification, exact-revision preparation, qualification, runtime, mutation, order action, or capital movement/exposure.
