# E6 Current Task

- task_id: `E6-20260822-006`
- issued_at: `2026-08-22T15:16:00+08:00`
- state: `HOLD`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003, E7 reviews under `status/e7/`

## Objective

Freeze the latest PR #16 correction while E7 performs an exact-revision targeted static/security re-review of the remaining evidence-authority portion of `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`.

## Frozen evidence

- completed correction task: `E6-20260822-005`
- branch: `agent/e6-platform`
- source/tests/docs correction revision: `df39836adabd04c77cc4f0d0b531ea10408866ab`
- handoff refresh: `dfa6f6a34978a2e068c29279f6ce85836fc806f2`
- platform-status refresh: `63fe79ef2c9b377b960be7ceb2d5f7e9634bd99e`
- observed PR #16 head after mailbox completion: `e7d1f3d9a99043107824a3c64d1d37663db8ff53`
- latest main synchronized into E6 before correction: `4474a919f0446881369914523132b4aa9b88007d`
- synchronization merge: `d94a64a1abaf70850167b3e6aec7af120f40ffa6`
- executable verification: `NOT_RUN`
- Gate A/B/C/D: `BLOCKED / UNCHANGED`

## Claimed correction pending E7 review

E6 reports that:

- `DRAFT -> BACKTESTING` requires durable exact-strategy E2 compatibility authority with `PASS / LOCAL_EXECUTION` and complete local-execution metadata;
- `BACKTESTING -> CANDIDATE` requires durable E3 ValidationDecision PASS + bound BacktestResult, canonical payload revalidation, exact identity/content/backtest binding, and complete local-execution metadata on both;
- the public service and SQLite persistence reuse an E6 lifecycle-authority policy;
- SQLite checks promotion authority inside the transaction before lifecycle INSERT/projection UPDATE;
- prior exact three-edge allowlist, forbidden-edge SQL trigger, append-only history, concurrency and rollback behavior remain intact;
- accepted `E6-EVIDENCE-CONTRACT-001` validators remain unchanged.

## Required actions

1. Do not modify PR #16 registry/storage/tests/docs implementation while E7 reviews the exact frozen revision.
2. Preserve all accepted lifecycle edge, SQLite trigger, evidence-contract, Registry/Inbox, immutability, concurrency, and rollback behavior.
3. Do not add lifecycle states, generic lifecycle authority, Slice 3 execution/provider persistence, dashboard expansion, broker/API work, credentials, asset movement, or shared-contract changes.
4. Keep executable verification `NOT_RUN`; do not run tests/migrations/backtests/provider calls or GitHub Actions/CI/hosted/project compute.
5. Do not resynchronize merely because PM issues coordination-only commits while E7 reviews. Resynchronize only if E7 identifies meaningful production/shared-contract drift or an actual conflict affecting reviewed behavior.
6. If acknowledging HOLD, update only `coordination/E6/STATUS.md`.

## Acceptance

PR #16 remains frozen and unmerged pending E7. No executable PASS, Gate advancement, PAPER/APPROVED/SHADOW/LIVE authority, or provider execution is authorized.

## Writable scope

Only `coordination/E6/STATUS.md` for HOLD acknowledgement unless PM replaces this task.

## Completion / status

Wait for E7/PM disposition. Do not merge PR #16 or start another E6 feature automatically.
