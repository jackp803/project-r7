# E6 Current Task

- task_id: `E6-20260820-001`
- issued_at: `2026-08-20T16:53:00+08:00`
- state: `HOLD`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, `contracts-v0.1`

## Objective

Hold the completed early Slice 2 Strategy Registry / persistence / lifecycle skeleton at its current bounded scope until E7 completes static review.

## Required actions

1. Do not expand beyond `DRAFT -> BACKTESTING -> REJECTED | CANDIDATE`.
2. Do not add PAPER / APPROVED / LIVE lifecycle or promotion behavior.
3. Do not treat contract-shaped E2/E3 artifacts as executable PASS.
4. Preserve fail-closed default compatibility boundary and `NOT_RUN` semantics.
5. Do not wire a real E2 adapter or final E3 ValidationDecision flow until E7 issues a new task.
6. Keep local Registry/storage tests `NOT_RUN` if no approved local environment exists.

## Acceptance

- current E6 branch/handoff remains intact;
- no lifecycle expansion or approval bypass;
- no shared contract redefinition;
- no GitHub Actions/CI/runner.

## Writable scope

Only `coordination/E6/STATUS.md` for this HOLD task.

## Completion / status

Update `coordination/E6/STATUS.md` to acknowledge HOLD and report current branch/HEAD/handoff. Wait for replacement TASK.md after E7 review.
