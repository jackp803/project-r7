# E6 Current Task

- task_id: `E6-20260829-030`
- issued_at: `2026-08-29T19:39:00+08:00`
- state: `HOLD`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, merged E6-20260829-029 static candidate PR #121, `status/PM_E6_029_REVIEW_20260829.md`, active LF-0 exact-revision infrastructure blocker

## Objective

Hold after PM accepted and merged E6-20260829-029 only as a provider-neutral FP-11 persistence/currentness/restart **static implementation/test-definition candidate** with the projection-vs-Position hash-domain remediation included.

Authoritative state:

```text
E6 FP-11 persistence/currentness/restart candidate = MERGED / STATIC CANDIDATE ACCEPTED
E6 executable verification = NOT_RUN / NOT_PASS
FP-11 executable qualification = NOT ESTABLISHED
FP-04/FP-10 E6 currentness candidate = MERGED / NOT_RUN / NOT_PASS
E4 FP-11 producer candidate = MERGED / NOT_RUN / NOT_PASS
E5 FP-11 policy consumer candidate = MERGED / NOT_RUN / NOT_PASS
LF-0 exact-revision infrastructure = BLOCKED / UNCHANGED
LF-2 P0 closure = NOT PASS
provider-facing verification = NOT_RUN / NOT_INFERRED
SHADOW/PAPER = NOT_AUTHORIZED
10U bounded live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
```

## Required actions while HOLD

- Preserve the accepted separation between canonical Position hash and lifecycle projection payload hash.
- Preserve append-only FP-11 history, explicit supersession/current-head conflict handling, exact E5/FP-04/lifecycle/provider/runtime reference checks, terminal-flat FP-10 dependency, and false-green restart prevention.
- Do not treat merge/static review or `NOT_RUN` as executable PASS.
- Do not modify E4/E5/E7 code/contracts or provider/runtime authority.
- Do not self-start qualification, Local Job Requests, provider verification, SHADOW/PAPER, bounded live-fire, Gate D, or LIVE.
- Do not call provider endpoints, read/request credentials, mutate provider/account state, submit/cancel/amend/close orders, or move/expose capital.
- Do not use GitHub Actions/CI/hosted/GitHub-triggered compute.

## Unblock condition

PM may issue a fresh E6 task if E7 integrated safety composition exposes a bounded E6 defect/change request, or if approved-local exact-revision qualification later becomes available and requires an E6-owned correction/retest.

## Writable scope

Only `coordination/E6/STATUS.md` for HOLD acknowledgement if needed.

## Completion

Acknowledge HOLD if needed and stop. Do not self-start E7 integration/requalification, exact-revision preparation, provider verification, SHADOW/PAPER, bounded live-fire, Gate D, LIVE, mutation, order action, or capital movement/exposure.
