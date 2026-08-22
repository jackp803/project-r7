# E6 Current Task

- task_id: `E6-20260822-005`
- issued_at: `2026-08-22T14:40:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e6-platform`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003, E7 targeted re-review `status/e7/E6_LIFECYCLE_TARGETED_REREVIEW_20260822.md`

## Objective

Close the remaining source condition in `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001` on PR #16.

The exact three-edge early-Slice-2 allowlist and SQLite forbidden-edge trigger are now accepted statically, but the authoritative persistence API still validates only edge shape/state/revision. A direct caller can therefore legally chain `DRAFT -> BACKTESTING -> CANDIDATE` without the E2/E3 evidence authority required by `StrategyPlatformService`.

This task is a bounded lifecycle **evidence-authority-at-persistence** correction only. Do not expand lifecycle scope, redesign shared contracts, or add Slice 3 execution persistence.

## Accepted behavior to preserve

The following E7 dispositions are already accepted and must not regress:

- `E6-EVIDENCE-CONTRACT-001` — `CLOSED / PASS STATIC`;
- early lifecycle vocabulary remains exactly `DRAFT | BACKTESTING | REJECTED | CANDIDATE`;
- legal edge shape remains exactly:

```text
DRAFT       -> BACKTESTING
BACKTESTING -> REJECTED
BACKTESTING -> CANDIDATE
```

- every other edge pair is rejected before authoritative mutation;
- migration `0001_strategy_registry.sql` rejects forbidden edge pairs;
- lifecycle history remains append-only;
- current-state / expected-revision / resulting-revision concurrency checks remain intact;
- atomic history + projection update and rollback behavior remain intact;
- canonical BacktestResult / ValidationDecision validators and bindings remain unchanged;
- no Slice 3 execution/provider persistence;
- executable verification remains `NOT_RUN`.

## Required persistence authority

The authoritative persistence path must independently enforce the same promotion prerequisites as the service. It must not rely on callers always using `StrategyPlatformService`.

### `DRAFT -> BACKTESTING`

Before mutation, persistence must require durable compatibility authority bound to the exact strategy identity:

- compatibility evidence exists for the strategy version;
- checker is the accepted E2 boundary (`E2...` according to existing service semantics);
- `status = PASS`;
- `verification_kind = LOCAL_EXECUTION`;
- `source_revision`, `environment`, `command`, and `result_ref` are present/non-empty;
- no caller-supplied transition record alone can manufacture this authority.

Use the same accepted semantics as `StrategyPlatformService.begin_backtesting()`; do not invent a weaker alternative.

### `BACKTESTING -> CANDIDATE`

Before mutation, persistence must require durable evidence bound to the exact strategy identity/content:

- transition identifies the authoritative ValidationDecision evidence used for promotion;
- referenced record is `VALIDATION_DECISION` produced by E3;
- `decision = PASS`;
- decision identity and strategy content hash match the persisted strategy;
- decision has `PASS / LOCAL_EXECUTION` with non-empty `source_revision`, `environment`, `command`, `result_ref`;
- decision has a stored parent `BACKTEST_RESULT`;
- parent identity/content hash match the persisted strategy;
- parent has `PASS / LOCAL_EXECUTION` with non-empty `source_revision`, `environment`, `command`, `result_ref`;
- ValidationDecision/BacktestResult canonical payloads and exact parent/backtest binding remain valid under the already accepted E6 validators;
- a caller cannot substitute a BACKTEST_RESULT, FAIL/NOT_RUN decision, unbound decision, missing parent, mismatched backtest id, malformed canonical payload, or synthetic transition record and still advance CANDIDATE.

Do not weaken the existing service gate. Prefer one E6-owned policy/helper reused by service and persistence where practical so semantics cannot silently drift.

### `BACKTESTING -> REJECTED`

Preserve the existing rejection semantics and edge cap. Do not turn REJECTED into a promotion path. If persistence currently accepts reason/evidence fields, keep them coherent and fail closed on invalid bound evidence; do not broaden this task into a new rejection policy design.

## Required actions

1. Fetch latest `main` and non-destructively synchronize it into `agent/e6-platform` once before correction. Preserve history; no force push/destructive rebase. The main-only delta is expected to be E7 review/coordination evidence, not a reason for scope expansion.
2. Correct the E6 persistence boundary so the two promotion edges above require durable accepted evidence authority **before any lifecycle row/projection mutation**.
3. The persistence check must read/validate authoritative stored evidence; a transition object's state pair/reason code/`primary_evidence_id` by itself is not sufficient authority.
4. Reuse the already accepted canonical BacktestResult / ValidationDecision validation functions when validating persisted promotion evidence where needed; do not create a second weaker payload grammar.
5. Preserve the exact three-edge allowlist and SQL forbidden-edge trigger from the prior correction.
6. A failed evidence-authority check must leave all authoritative state unchanged:
   - no lifecycle transition row committed;
   - `strategy_versions.current_lifecycle_state` unchanged;
   - `registry_revision` unchanged.
7. Preserve current-state/revision/resulting-revision checks, transaction atomicity, and rollback.
8. Add deterministic local-only tests proving direct persistence cannot advance:
   - `DRAFT -> BACKTESTING` with no compatibility evidence;
   - `DRAFT -> BACKTESTING` with non-E2, non-PASS, non-LOCAL_EXECUTION, or incomplete local-execution metadata;
   - `BACKTESTING -> CANDIDATE` without `primary_evidence_id`;
   - with wrong evidence type;
   - with FAIL/BLOCKED/NOT_RUN ValidationDecision;
   - with wrong strategy identity/content hash;
   - with missing/wrong BacktestResult parent;
   - with invalid/mismatched canonical ValidationDecision ↔ BacktestResult binding;
   - with missing/non-local PASS metadata on either decision or backtest.
9. Tests must also prove each rejected authorization attempt leaves row count/state/revision unchanged.
10. Add positive tests showing the normal service-authorized `DRAFT -> BACKTESTING` and `BACKTESTING -> CANDIDATE` flows still work when the required durable E2/E3 evidence exists. Do not use a bypass-only fake path as proof of authority.
11. Keep the prior direct-store forbidden-edge and SQL-trigger tests intact.
12. Recheck `E6-EVIDENCE-CONTRACT-001` and Registry/Inbox behavior for static regression; accepted critical validators must not be weakened.
13. Do not add PAPER, READY_FOR_APPROVAL, APPROVED, SHADOW, LIVE, DEGRADED, RETIRED, generic lifecycle authority, or any later-state migration.
14. Do not add ApprovedTradePlan, OrderRequest, OrderResult, Fill, Position, OKX `sz`, provider identities, reconciliation, Demo execution, or other Slice 3 execution-audit persistence.
15. Do not edit `contracts/**` or E1/E2/E3/E4/E5/E7 production code. No dashboard expansion, provider/API access, credentials, asset movement, or workflow/CI changes.
16. Update `status/E6_EARLY_SLICE2_HANDOFF.md`, `status/E6_STATUS.md`, and `coordination/E6/STATUS.md` with exact sync/correction revisions, changed-file scope, authority design, and claimed finding disposition for E7.
17. Executable verification is local-only. Without a Product Owner-approved local environment, keep `NOT_RUN` and record exact commands:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/registry -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
```

18. Do not run tests, migrations, backtests, provider requests, GitHub Actions/CI/hosted runners, or GitHub-triggered project compute in this environment.
19. Push only this bounded correction to existing PR #16 branch, update STATUS/handoff, then stop. Do not merge PR #16 or begin another E6 feature automatically.

## Acceptance

Static/source completion requires that a direct caller of the authoritative persistence surface cannot reach BACKTESTING or CANDIDATE without the same durable E2/E3 authority required by the accepted service path, while all prior edge/migration/evidence/immutability/concurrency boundaries remain intact. Test definitions must cover both bypass attempts and valid service-authorized flows. Executable verification remains `NOT_RUN`; Gate A/B/C/D remain blocked.

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
- lifecycle expansion beyond early four states;
- Slice 3 execution/provider persistence;
- private provider/API work;
- credentials/secrets;
- PAPER/READY_FOR_APPROVAL/APPROVED/SHADOW/LIVE authority;
- GitHub Actions/CI/hosted/project compute;
- executable PASS claims.

## Completion / status

Close only the remaining evidence-authority bypass in `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`, push the exact source/test/handoff revision, update STATUS, and stop for E7 targeted re-review.