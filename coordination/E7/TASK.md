# E7 Current Task

- task_id: `E7-20260822-006`
- issued_at: `2026-08-22T14:40:00+08:00`
- state: `HOLD`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003

## Objective

Hold after completing `E7-20260822-005`. PR #16 remains blocked by the remaining E6-owned evidence-authority portion of `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`.

## Accepted review evidence

- completed review task: `E7-20260822-005`;
- review artifact: `status/e7/E6_LIFECYCLE_TARGETED_REREVIEW_20260822.md`;
- review evidence merged to `main` via PR #18, merge commit `ef5837673f7f75085e55ad1b7311767f0625f984`;
- reviewed E6 correction revision: `aab1639d6db1f94e915d1c4af3041be28e9a4b94`;
- observed PR #16 head: `42c5d56996e0c4ff0e96edfc591726d9f9f34963`;
- exact three-edge allowlist: `PASS / STATIC ONLY`;
- forbidden-pair direct-store rejection: `PASS / STATIC ONLY`;
- SQLite forbidden-edge trigger: `PASS / STATIC ONLY`;
- `E6-EVIDENCE-CONTRACT-001`: `CLOSED / PASS STATIC / NO REGRESSION`;
- `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`: `BLOCKING / NOT CLOSED / E6 OWNER`;
- remaining blocker: direct persistence callers can chain legal edge shapes without the E2/E3 evidence authority enforced by `StrategyPlatformService`;
- PR #16: `DO NOT MERGE` pending E6 correction;
- executable verification: `NOT_RUN`;
- Gate A/B/C/D: `BLOCKED / UNCHANGED`.

## Required actions

1. Do not modify E1-E6 production code or shared contracts.
2. Do not re-review PR #16 until PM replaces this HOLD after E6 completes `E6-20260822-005` with a fresh exact source/test revision.
3. Preserve the accepted edge-allowlist/SQLite-trigger dispositions and `E6-EVIDENCE-CONTRACT-001` disposition.
4. On the future targeted re-review, focus on whether the authoritative persistence path independently requires the same durable promotion authority as the service:
   - `DRAFT -> BACKTESTING`: bound E2 compatibility `PASS / LOCAL_EXECUTION` with complete local evidence metadata;
   - `BACKTESTING -> CANDIDATE`: bound E3 `ValidationDecision(PASS)` + parent `BacktestResult`, exact identity/content/backtest binding, canonical payload validity, and complete `PASS / LOCAL_EXECUTION` metadata on both.
5. Verify future bypass tests include direct-store missing/invalid evidence and prove no transition-row/state/revision mutation on rejection, plus valid service-authorized positive flows.
6. Keep lifecycle scope restricted to the early four states and exact three legal edge shapes.
7. Do not advance Gate A/B/C/D, PAPER/SHADOW/LIVE, provider execution, or any later lifecycle state.
8. Do not run project tests, migrations, provider calls, backtests, GitHub Actions/CI/hosted runners, or GitHub-triggered project compute.
9. If acknowledging HOLD, update only `coordination/E7/STATUS.md`.

## Acceptance

E7 remains idle while E6 closes the remaining persistence evidence-authority bypass. Executable evidence remains `NOT_RUN`; PR #16 remains unmerged; release gates remain blocked.

## Writable scope

Only `coordination/E7/STATUS.md` for HOLD acknowledgement unless PM replaces this task.

## Completion / status

Wait for E6 correction evidence. Do not start re-review, merge PR #16, or start another integration task automatically.