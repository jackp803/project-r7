# E6 Current Task

- task_id: `E6-20260821-003`
- issued_at: `2026-08-21T10:58:00+08:00`
- state: `HOLD`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0002/0003

## Objective

Preserve the statically accepted Registry/evidence-ingest correction while E2 and E5 implement the new execution object profiles and E4 remains frozen pending those producers.

E6 is a future audit/persistence consumer of `entry-v0.1` and `base-asset-v0.1`, but the current early Slice 2 implementation does not yet persist ApprovedTradePlan/provider execution facts. Do not invent that execution-audit surface prematurely.

## Required actions

1. Do not modify the accepted `E6-EVIDENCE-CONTRACT-001` correction during this HOLD.
2. Preserve complete BacktestResult / ValidationDecision validation and caller-metadata bypass protection.
3. Keep lifecycle capped at `DRAFT -> BACKTESTING -> REJECTED | CANDIDATE`.
4. Do not add ApprovedTradePlan/Order/Fill/provider execution persistence until PM/E7 issues an explicit bounded Slice 3 audit task with accepted producer/consumer revisions.
5. Do not reinterpret provider contract quantities as canonical base-asset quantities.
6. Do not add PAPER / READY_FOR_APPROVAL / APPROVED / SHADOW / LIVE behavior.
7. Keep executable evidence `NOT_RUN` until approved local execution.
8. If acknowledging HOLD, update only `coordination/E6/STATUS.md`.

## Acceptance

- accepted E6 correction remains intact;
- no premature execution-audit schema or lifecycle expansion;
- no shared-contract changes;
- no GitHub compute/CI;
- no executable PASS claim.

## Writable scope

Only `coordination/E6/STATUS.md` for HOLD acknowledgement unless PM/E7 replaces this task.

## Completion / status

Acknowledge HOLD if needed and wait for the later bounded execution-audit persistence task.
