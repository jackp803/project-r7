# E6 Current Task

- task_id: `E6-20260821-002`
- issued_at: `2026-08-21T08:37:00+08:00`
- state: `HOLD`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, `contracts-v0.1`

## Objective

Freeze the corrected E6 Registry/evidence-ingest source after E7 static acceptance of `E6-EVIDENCE-CONTRACT-001`. Wait for future local verification and later integration resynchronization.

## Accepted static evidence

- corrected revision: `4a845ff79ba48abb6122191a2cf8df7d52544475`
- E7 re-review artifact: `status/e7/E5_E6_CORRECTION_REREVIEW_20260821.md`
- E7 finding disposition: `STATICALLY_RESOLVED / PASS (static)`
- executable verification: `NOT_RUN`

## Required actions

1. Do not modify the accepted evidence-contract correction unless PM/E7 issues another bounded task.
2. Preserve complete `contracts-v0.1` BacktestResult / ValidationDecision shape validation before promotable persistence.
3. Preserve caller-metadata bypass protection.
4. Do not implement E3 statistical methodology or wire the real E2 adapter.
5. Keep lifecycle capped at `DRAFT -> BACKTESTING -> REJECTED | CANDIDATE`.
6. Do not add PAPER / READY_FOR_APPROVAL / APPROVED / SHADOW / LIVE behavior.
7. Keep executable evidence `NOT_RUN` until approved local execution.
8. If acknowledging HOLD, update only `coordination/E6/STATUS.md`.

## Acceptance

- E7-accepted static correction remains intact;
- no lifecycle expansion or shared-contract change;
- no GitHub compute/CI;
- no executable PASS claim.

## Writable scope

Only `coordination/E6/STATUS.md` for HOLD acknowledgement unless PM/E7 replaces this task.

## Completion / status

Acknowledge HOLD if needed and wait for a replacement TASK.md.
