# E6 Current Task

- task_id: `E6-20260821-001`
- issued_at: `2026-08-21T00:04:00+08:00`
- state: `HOLD`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, `contracts-v0.1`

## Objective

Hold corrected E6 evidence-contract revision while E7 performs static re-review.

## Frozen correction evidence

- finding: `E6-EVIDENCE-CONTRACT-001`
- corrected revision reported by E6: `4a845ff79ba48abb6122191a2cf8df7d52544475`
- executable verification: `NOT_RUN`

## Required actions

1. Do not modify the corrected Registry/evidence ingest source unless E7/PM issues another bounded correction.
2. Do not wire the real E2 adapter or implement E3 statistical methodology.
3. Do not expand lifecycle beyond `DRAFT -> BACKTESTING -> REJECTED | CANDIDATE`.
4. Do not add PAPER / READY_FOR_APPROVAL / APPROVED / SHADOW / LIVE.
5. Keep executable evidence `NOT_RUN` until approved local execution.
6. If acknowledging this HOLD, update only `coordination/E6/STATUS.md` and do not claim E7 acceptance.

## Acceptance

- corrected source/handoff preserved;
- no contract changes;
- no lifecycle expansion;
- no GitHub compute/CI;
- E7 re-review remains the next authority action.

## Writable scope

Only `coordination/E6/STATUS.md` for HOLD acknowledgement unless PM/E7 replaces this task.
