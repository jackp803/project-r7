# E6 Current Task

- task_id: `E6-20260829-027`
- issued_at: `2026-08-29T17:18:00+08:00`
- state: `HOLD`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, merged E6-20260829-026 static candidate PR #116, `status/PM_E6_026_REVIEW_20260829.md`, active LF-0 exact-revision infrastructure blocker

## Objective

Hold after PM accepted E6-20260829-026 only as a **static implementation/test-definition candidate** for provider-neutral FP-04/FP-10 immutable persistence/currentness/restart behavior.

Authoritative state:

```text
E6 FP-04/FP-10 persistence/currentness implementation = MERGED / STATIC CANDIDATE ACCEPTED
E6 executable verification = NOT_RUN / NOT_PASS
FP-04 / FP-10 executable qualification = NOT ESTABLISHED
E5 FP-04/FP-10 lifecycle consumer = MERGED STATIC CANDIDATE / NOT_RUN / NOT_PASS
E4 provider-neutral evidence producer/assembler = NEXT OWNER / DISPATCHED SEPARATELY
LF-0 exact-revision infrastructure = BLOCKED / UNCHANGED
LF-2 P0 closure = PARTIAL
provider-facing verification = NOT_RUN / NOT_INFERRED
SHADOW/PAPER = NOT_AUTHORIZED
10U bounded live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
```

## Required actions while HOLD

- Preserve append-only immutable history, explicit supersession-chain selection, exact reference/hash validation and restart false-green prevention.
- Do not treat merge/static review or `NOT_RUN` as executable PASS.
- Do not modify E4/E5/E7 code/contracts or provider/runtime authority.
- Do not self-start integrated qualification, Local Job Requests or provider verification.
- Do not call provider endpoints, read/request credentials, mutate provider/account state or submit/cancel/amend/close orders.
- Do not start SHADOW/PAPER, bounded live-fire, Gate D or LIVE.
- Do not move/expose capital.
- Do not use GitHub Actions/CI/hosted/GitHub-triggered compute.

## Unblock condition

PM may issue a fresh E6 task if E4/E7 integration exposes a bounded storage defect/change request, or after the approved-local exact-revision path is restored for integrated verification.

## Writable scope

Only `coordination/E6/STATUS.md` for HOLD acknowledgement if needed.

## Completion

Acknowledge HOLD if needed and stop. Do not self-start E4 evidence production, E7 integration/requalification, provider verification, SHADOW/PAPER, bounded live-fire, Gate D, LIVE, mutation, order action or capital movement/exposure.
