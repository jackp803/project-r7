# E6 Current Task

- task_id: `E6-20260822-003`
- issued_at: `2026-08-22T10:12:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e6-platform`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003, E7 review `status/e7/E6_REGISTRY_STATIC_REVIEW_20260822.md`

## Objective

Close the single blocking E7 finding in PR #16: `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`.

The StrategyPlatformService already exposes only the intended early Slice 2 lifecycle edges, but the public SQLite persistence boundary currently accepts any transition between the four known states when state/revision values match. A direct store caller can therefore bypass service evidence gates, including an unauthorized `DRAFT -> CANDIDATE` transition.

This task is a bounded persistence-authority correction only. Do not redesign the Registry, evidence contracts, lifecycle model, or add Slice 3 execution persistence.

## Accepted behavior to preserve

The following prior E7 dispositions remain accepted and must not regress:

- `E6-EVIDENCE-CONTRACT-001` — `CLOSED / PASS STATIC`;
- canonical BacktestResult validation before persistence;
- canonical ValidationDecision validation and exact BacktestResult/strategy binding;
- caller `PASS / LOCAL_EXECUTION` metadata cannot bypass canonical validation;
- a BacktestResult alone cannot authorize CANDIDATE;
- default/unwired E2 compatibility remains fail-closed `NOT_RUN`;
- strategy identity/version/content immutability;
- inbox idempotency vs identity conflict behavior;
- append-only lifecycle history;
- lifecycle vocabulary remains exactly `DRAFT | BACKTESTING | REJECTED | CANDIDATE`;
- no Slice 3 execution/provider persistence;
- executable verification remains `NOT_RUN`.

## Exact allowed lifecycle edges

For this early Slice 2 only, the persistence authority must permit exactly:

```text
DRAFT       -> BACKTESTING
BACKTESTING -> REJECTED
BACKTESTING -> CANDIDATE
```

Every other pair among the four lifecycle states must fail closed at the persistence boundary even when the caller supplies the correct current state and registry revision.

## Required actions

1. Before correcting source, fetch current `main` and non-destructively synchronize it into `agent/e6-platform` once. Preserve branch history; no force push, destructive rebase, or history rewrite. This sync may include E7 review/coordination evidence only; do not use it to broaden scope.
2. Fix `SQLiteRegistryStore.append_transition(...)` so it independently rejects any lifecycle edge outside the exact early-Slice-2 allowlist **before authoritative projection mutation**. Do not rely on callers always going through `StrategyPlatformService`.
3. Prefer one clearly named E6-owned authoritative allowlist/helper if practical so service and persistence semantics cannot silently drift. If implementation simplicity requires duplicated checks, they must be exact and covered by tests; do not change shared contracts.
4. Add database-level defense in depth in the still-unmerged early Slice 2 SQLite migration so INSERT into `lifecycle_transitions` cannot represent a service-forbidden edge. The database constraint/trigger must allow only the three edges above; merely constraining the four state names is insufficient.
5. A rejected direct-store transition must leave all authoritative state unchanged:
   - no lifecycle transition row committed;
   - `strategy_versions.current_lifecycle_state` unchanged;
   - `registry_revision` unchanged.
6. Preserve concurrency checks for current state, expected revision, and resulting revision. Do not weaken or bypass those checks while adding edge validation.
7. Add deterministic local-only tests proving direct persistence calls reject at least:
   - `DRAFT -> CANDIDATE`;
   - `DRAFT -> REJECTED`;
   - `CANDIDATE -> DRAFT`;
   - `CANDIDATE -> BACKTESTING`;
   - `REJECTED -> CANDIDATE`;
   - `REJECTED -> BACKTESTING`;
   - self-transitions where applicable.
8. Add positive direct-store coverage for all three legal edges, with the required prerequisite state progression, so the persistence allowlist is not accidentally over-restrictive.
9. Add deterministic proof for the migration/database guard itself where practical: a direct SQL insertion of a forbidden lifecycle edge must fail without changing the authoritative projection. Do not interpret a synthetic test PASS fixture as project executable evidence.
10. Recheck `E6-EVIDENCE-CONTRACT-001` critical behavior and existing Registry/Inbox/SQLite tests for static regression. Do not alter evidence semantics merely to satisfy lifecycle tests.
11. Keep lifecycle scope capped to `DRAFT -> BACKTESTING -> REJECTED | CANDIDATE`. Do not add PAPER, READY_FOR_APPROVAL, APPROVED, SHADOW, LIVE, DEGRADED, RETIRED, or generic lifecycle transition authority.
12. Do not add persistence for ApprovedTradePlan, OrderRequest, OrderResult, Fill, Position, OKX `sz`, provider identities, reconciliation, Demo execution, or other Slice 3 execution-audit facts.
13. Do not reinterpret provider-native quantities as canonical BTC quantities.
14. Do not edit `contracts/**` or E1/E2/E3/E4/E5/E7 production code. No dashboard expansion, broker/API access, credentials, provider execution, or asset movement.
15. Update `status/E6_EARLY_SLICE2_HANDOFF.md`, `status/E6_STATUS.md`, and `coordination/E6/STATUS.md` with the correction design, exact synchronization merge, exact source/tests/docs revision, changed-file scope, and the finding disposition claimed for E7 re-review.
16. Executable verification remains local-only. Without a Product Owner-approved local environment, record `NOT_RUN` and the exact commands:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/registry -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
```

17. Do not run GitHub Actions/CI/hosted runners/project compute, migrations, backtests, or provider requests in GitHub.
18. Push only this bounded correction to the existing PR #16 branch, then stop. Do not merge PR #16 and do not start the next E6 feature automatically.

## Acceptance

Static/source completion requires the public persistence boundary and SQLite migration to enforce exactly the three early Slice 2 lifecycle edges, with direct-store/direct-database forbidden-edge tests defined and no regression to the accepted evidence contract or scope boundaries. Executable verification remains `NOT_RUN`; Gate A/B/C/D remain blocked.

## Writable scope

- `src/registry/**`
- `src/storage/**`
- `tests/registry/**`
- `tests/storage/**`
- `docs/platform/**`
- `status/E6_EARLY_SLICE2_HANDOFF.md`
- `status/E6_STATUS.md`
- `coordination/E6/STATUS.md`

## Forbidden scope

- `contracts/**` edits;
- E1/E2/E3/E4/E5/E7 production rewrites;
- lifecycle expansion beyond the four early states;
- Slice 3 execution/provider persistence;
- private provider/API work;
- real credentials/secrets;
- PAPER/READY_FOR_APPROVAL/APPROVED/SHADOW/LIVE authority;
- GitHub Actions/CI/hosted runner/project compute;
- executable PASS claims.

## Completion / status

Close only `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`, update handoff/STATUS, push to PR #16 branch, then stop and wait for PM/E7 targeted re-review.