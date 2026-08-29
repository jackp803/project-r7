# E4 Current Task

- task_id: `E4-20260829-025`
- issued_at: `2026-08-29T14:15:00+08:00`
- state: `HOLD`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, accepted E7 FP-03 contract, merged E5 FP-03 candidate PR #105, merged E4 FP-03 candidate PR #106, `status/PM_E4_024_REVIEW_20260829.md`

## Objective

Hold after PM accepted E4-20260829-024 only as an **unverified executable candidate** and merged PR #106.

Authoritative state:

```text
FP-03 shared contract = ACCEPTED / protection-trigger-validity-v0.1
E5 producer/policy candidate = MERGED / LOCAL VERIFICATION NOT_RUN / NOT_PASS
E4 consumer/binding candidate = MERGED / LOCAL VERIFICATION NOT_RUN / NOT_PASS
combined candidate revision = 9462b2594675b2e28388f55a2af189100b7cbdfc
FP-03 executable qualification = NOT_ESTABLISHED
next owner = E7 fresh approved-local credential-free requalification
provider/private verification = NOT_AUTHORIZED BY THIS HOLD
SHADOW/PAPER runtime = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / NOT_AUTHORIZED
LIVE = UNAUTHORIZED
```

## Required actions while HOLD

- Preserve the merged E4 FP-03 candidate exactly.
- Do not modify E4 source/tests under this HOLD.
- Do not run project code or create a Local Job Request.
- Do not start FP-02 or FP-15.
- Do not call OKX/provider endpoints or read/request/use credentials.
- Do not mutate provider/account state or submit/cancel/amend/close orders.
- Do not start SHADOW/PAPER, Gate D or LIVE.
- Do not move/expose capital.
- Do not use GitHub Actions/CI/hosted/GitHub-triggered compute.

## Unblock condition

Wait for PM review of E7's fresh approved-local credential-free requalification of exact combined candidate revision `9462b2594675b2e28388f55a2af189100b7cbdfc`, or a fresh bounded E4 task if that qualification exposes a reproducible E4 defect.

## Writable scope

Only `coordination/E4/STATUS.md` for HOLD acknowledgement if needed.

## Completion

Acknowledge HOLD if needed and stop. Do not self-start requalification, provider verification, FP-02, FP-15, SHADOW/PAPER, Gate D, LIVE, mutation, order action or capital movement/exposure.
