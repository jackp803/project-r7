# E6 Current Task

- task_id: `E6-20260822-001`
- issued_at: `2026-08-22T02:49:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e6-platform`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003, accepted E7 re-review of `E6-EVIDENCE-CONTRACT-001`

## Objective

Non-destructively resynchronize the statically accepted early Slice 2 Strategy Registry / evidence-ingest / persistence skeleton with current `main` so E7 can perform a fresh exact-revision review and PM can decide whether to integrate it.

This task is **synchronization and preservation only**. Do not add the later Slice 3 execution-audit persistence surface yet.

## Accepted baseline to preserve

- E6 branch: `agent/e6-platform`
- accepted correction/status revision: `4a845ff79ba48abb6122191a2cf8df7d52544475`
- finding: `E6-EVIDENCE-CONTRACT-001 / STATICALLY RESOLVED`
- BacktestResult full canonical contract-shape/type/reproducibility validation: preserve
- ValidationDecision full canonical shape/type/enum/binding validation: preserve
- caller PASS/local-execution metadata bypass protection: preserve
- lifecycle cap: `DRAFT -> BACKTESTING -> REJECTED | CANDIDATE`
- no PAPER / READY_FOR_APPROVAL / APPROVED / SHADOW / LIVE lifecycle behavior
- executable verification: `NOT_RUN`

At PM audit before this task, `agent/e6-platform` was substantially behind current `main`; therefore no old branch head may be merged directly without synchronization and fresh E7 review.

## Required actions

1. Fetch latest `main` and non-destructively merge/synchronize it into `agent/e6-platform`. Preserve branch history; no force push, destructive rebase, or history rewrite.
2. Resolve conflicts only within E6-owned paths. Do not modify E1/E2/E3/E4/E5/E7 production code or shared contracts.
3. Preserve the accepted `E6-EVIDENCE-CONTRACT-001` correction exactly in behavior:
   - reject incomplete/incompatible BacktestResult before persistence;
   - reject incomplete/incompatible ValidationDecision before persistence;
   - validate exact strategy/backtest bindings;
   - unknown/invalid required enum/type/state fails closed;
   - caller-supplied PASS / LOCAL_EXECUTION metadata cannot bypass canonical evidence validation.
4. Preserve Strategy Registry / Inbox / SQLite skeleton only at its current bounded lifecycle scope.
5. Do **not** add ApprovedTradePlan, OrderRequest, OrderResult, Fill, OKX/provider-native quantity, reconciliation, Demo execution, or other Slice 3 execution-audit persistence in this task.
6. Do not reinterpret OKX contract `sz` as canonical BTC quantity.
7. Do not add PAPER, READY_FOR_APPROVAL, APPROVED, SHADOW, LIVE, or generic lifecycle transition authority.
8. Do not add dashboard expansion, broker/private API access, credentials, asset movement, or unrelated platform features.
9. Recheck changed-file scope after synchronization and ensure it remains E6-owned registry/storage/tests/docs/status only.
10. Update `status/E6_EARLY_SLICE2_HANDOFF.md`, `status/E6_STATUS.md`, and `coordination/E6/STATUS.md` with:
    - synchronization merge commit;
    - exact latest-main revision merged;
    - final E6 source/tests/docs revision;
    - changed-file scope;
    - preservation of the accepted finding correction;
    - executable verification `NOT_RUN` and exact local commands.
11. Do not execute project tests, migrations, backtests, GitHub Actions/CI/hosted runners, or GitHub-triggered project compute. Without a Product Owner-approved local environment, keep `NOT_RUN`.
12. Push the synchronized branch and stop. Do not open/merge a PR or start a new E6 feature automatically unless the TASK explicitly requires it.

## Acceptance

Task is complete when `agent/e6-platform` is non-destructively synchronized with latest `main`, the statically accepted early Slice 2 registry/evidence correction is preserved without scope expansion, status/handoff evidence is current, and executable evidence remains `NOT_RUN`.

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
- execution/provider audit schema expansion;
- private provider/API work;
- real credentials/secrets;
- PAPER/READY_FOR_APPROVAL/APPROVED/SHADOW/LIVE lifecycle expansion;
- GitHub Actions/CI/hosted runner/project compute;
- executable PASS claims.

## Completion / status

Synchronize, preserve the accepted E6 implementation, update handoff/STATUS, push, then stop and wait for PM/E7 re-review.
