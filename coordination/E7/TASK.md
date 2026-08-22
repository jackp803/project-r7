# E7 Current Task

- task_id: `E7-20260822-004`
- issued_at: `2026-08-22T10:12:00+08:00`
- state: `HOLD`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003

## Objective

Hold after completing `E7-20260822-003`. PR #16 remains blocked by the single E6-owned finding `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`; E6 now owns a bounded persistence-authority correction.

## Accepted review evidence

- completed review task: `E7-20260822-003`;
- review artifact persisted on `main`: `status/e7/E6_REGISTRY_STATIC_REVIEW_20260822.md`;
- E7 review evidence merged via PR #17;
- reviewed E6 revision: `207f6f87dd984c9dea5e4360e2f605e2c94b2bcf`;
- observed PR #16 head at review: `df15109dcb8594b1182bf6fc09cb5ad6681d74b5`;
- `E6-EVIDENCE-CONTRACT-001`: `CLOSED / PASS STATIC`;
- `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`: `BLOCKING / E6 OWNER`;
- PR #16: `DO NOT MERGE` pending correction;
- executable verification: `NOT_RUN`;
- Gate A/B/C/D: `BLOCKED / UNCHANGED`.

## Required actions

1. Do not modify E1-E6 production code or shared contracts.
2. Do not re-review PR #16 until PM replaces this HOLD after E6 completes `E6-20260822-003` with a fresh exact source/test revision.
3. Preserve the accepted `E6-EVIDENCE-CONTRACT-001` disposition and existing E7 review artifact.
4. On the future targeted re-review, focus on whether the persistence boundary and database migration enforce exactly:

```text
DRAFT       -> BACKTESTING
BACKTESTING -> REJECTED
BACKTESTING -> CANDIDATE
```

and whether forbidden direct-store/direct-database edges leave authoritative state/revision unchanged.
5. Do not advance lifecycle scope, Gate A/B/C/D, PAPER/SHADOW/LIVE, or any provider execution stage.
6. Do not run project tests, migrations, provider calls, GitHub Actions/CI/hosted runners, or GitHub-triggered project compute.
7. If acknowledging HOLD, update only `coordination/E7/STATUS.md`.

## Acceptance

E7 remains idle while E6 closes the one persistence-authority blocker. Executable evidence remains `NOT_RUN`; PR #16 remains unmerged; release gates remain blocked.

## Writable scope

Only `coordination/E7/STATUS.md` for HOLD acknowledgement unless PM replaces this task.

## Completion / status

Wait for E6 correction evidence. Do not start re-review, merge PR #16, or start another integration task automatically.