# E7 Current Task

- task_id: `E7-20260822-005`
- issued_at: `2026-08-22T10:28:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-e6-lifecycle-rereview-20260822`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003, prior review `status/e7/E6_REGISTRY_STATIC_REVIEW_20260822.md`

## Objective

Perform a targeted exact-revision static/integration re-review of corrected PR #16 and decide whether `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001` is closed without regression to the previously accepted E6 evidence/Registry boundaries.

This task is static/source review only. It does **not** authorize project execution, provider calls, lifecycle expansion, PAPER/SHADOW/LIVE, or GitHub compute.

## Review inputs

- PR: `#16 platform: integrate early Slice 2 registry and evidence persistence`
- E6 branch: `agent/e6-platform`
- correction source/tests/docs revision: `aab1639d6db1f94e915d1c4af3041be28e9a4b94`
- observed PR head at PM audit: `42c5d56996e0c4ff0e96edfc591726d9f9f34963`
- implementation correction task: `E6-20260822-003`
- synchronization merge with main: `c3d756b46af547b4ea0bb36aa653cc8b9081163f`
- main synchronized by E6 before correction: `06752b83c18f6579b06c1f3b7e1d5837a2d6949a`
- previous finding: `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001 / BLOCKING`
- accepted prior finding: `E6-EVIDENCE-CONTRACT-001 / CLOSED / PASS STATIC`
- executable verification: `NOT_RUN`

## Required review

1. Work only on fresh branch `agent/e7-e6-lifecycle-rereview-20260822` created from latest `main` after this TASK issuance.
2. Review the exact corrected E6 source at `aab1639d6db1f94e915d1c4af3041be28e9a4b94`; do not rely only on E6 STATUS claims.
3. Confirm a single bounded early-Slice-2 edge authority is present/coherent and permits exactly:

```text
DRAFT       -> BACKTESTING
BACKTESTING -> REJECTED
BACKTESTING -> CANDIDATE
```

4. Verify `SQLiteRegistryStore.append_transition(...)` independently rejects every other pair before authoritative lifecycle projection mutation. Confirm direct-store callers cannot bypass `StrategyPlatformService` evidence gates.
5. Verify rejected direct-store transitions leave all authoritative state unchanged:
   - no lifecycle transition row committed;
   - `strategy_versions.current_lifecycle_state` unchanged;
   - `registry_revision` unchanged.
6. Confirm existing concurrency checks remain intact: authoritative current state, expected revision, resulting revision, atomic history/projection update, and rollback behavior.
7. Verify migration `0001_strategy_registry.sql` independently rejects forbidden lifecycle-edge INSERTs at the database boundary, not merely unknown state names. Confirm append-only UPDATE/DELETE protection remains intact.
8. Review deterministic local-only tests and confirm definitions cover at minimum:
   - all three legal direct-store edges;
   - `DRAFT -> CANDIDATE` and `DRAFT -> REJECTED` rejection;
   - forbidden transitions out of CANDIDATE and REJECTED;
   - self-transition rejection;
   - no row/state/revision mutation on rejection;
   - forbidden direct-SQL lifecycle INSERT rejection.
   Do not execute tests in GitHub.
9. Recheck `E6-EVIDENCE-CONTRACT-001` for static regression. In particular confirm canonical BacktestResult/ValidationDecision validators, exact binding, PASS/LOCAL_EXECUTION bypass protection, and CANDIDATE evidence gating remain accepted.
10. Recheck lifecycle vocabulary remains only `DRAFT | BACKTESTING | REJECTED | CANDIDATE`; no PAPER, READY_FOR_APPROVAL, APPROVED, SHADOW, LIVE, DEGRADED, RETIRED, or generic transition authority.
11. Recheck no ApprovedTradePlan/OrderRequest/OrderResult/Fill/Position/OKX `sz`/provider execution/reconciliation persistence or other Slice 3 scope has appeared.
12. Recheck PR #16 current branch against latest `main`. Coordination-only TASK commits after the E6 implementation pin are not by themselves a resynchronization blocker. Require another E6 sync only for meaningful production/shared-contract drift or an actual merge conflict affecting reviewed behavior.
13. Recheck repository scope: no `contracts/**`, E1/E2/E3/E4/E5 production, workflow/CI, secret, provider, or unrelated changes.
14. Persist a targeted E7 re-review artifact under `status/e7/` and update `coordination/E7/STATUS.md` with:
   - exact reviewed E6 revision and observed PR head;
   - `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001` disposition;
   - confirmation/regression status of `E6-EVIDENCE-CONTRACT-001`;
   - persistence/migration/test/scope dispositions;
   - PR #16 merge recommendation;
   - executable verification `NOT_RUN`;
   - Gate A/B/C/D unchanged.
15. If the lifecycle persistence finding is statically closed and no regression/blocker exists, state `PM MAY MERGE PR #16`. This is not Gate A PASS and does not authorize PAPER/APPROVED/SHADOW/LIVE.
16. If blocked, identify the exact remaining source condition and owner. Do not modify E6 implementation yourself.
17. Do not run project tests, migrations, GitHub Actions/CI/hosted runners, backtests, or provider requests. Do not create a Codex ticket without a locally reproduced executable defect.

## Acceptance

Task completes when Git contains an exact-revision targeted E7 re-review that either closes `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001` and recommends PM merge PR #16, or keeps PR #16 blocked with a precise remaining condition. Executable evidence remains `NOT_RUN`; Gate A/B/C/D remain blocked.

## Writable scope

- E7-owned review/status/integration documentation
- `coordination/E7/STATUS.md`

## Forbidden scope

- E1-E6 production implementation edits;
- shared-contract changes;
- provider execution;
- lifecycle expansion;
- PAPER/SHADOW/LIVE advancement;
- GitHub compute/CI.

## Completion / status

Persist the targeted re-review and STATUS, then stop and wait for PM. Do not merge PR #16 or start another task automatically.
