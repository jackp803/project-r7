# E3 Current Task

- task_id: `E3-20260822-001`
- issued_at: `2026-08-22T19:36:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e3-backtest-validation`
- authority: `agents/E3_BACKTEST_VALIDATION.md`, `agents/README.md`, `contracts-v0.1`, current `main` E2 runtime/StrategyDefinition/TradeIntent implementation, merged E6 early Slice 2 Registry/evidence persistence

## Objective

Refresh the previously reviewed E3 Slice 1 historical replay / BacktestResult research skeleton onto current `main` without expanding the research scope.

The existing E3 branch is substantially behind current `main`. Preserve the accepted architecture — Historical Candle -> actual E2 Strategy Runtime -> E3 historical replay -> canonical BacktestResult — while reconciling only the source/import/contract drift required by the current repository.

This task is **not** Gate A executable verification and is not a request to add OOS, Walk Forward, Monte Carlo, optimization, regime classification, PAPER, or LIVE behavior.

## Required baseline behavior to preserve

E3 remains the independent quantitative/replay owner and must:

- consume the actual current E2 runtime; never copy/reimplement E2 strategy rules;
- replay only closed historical candles in deterministic chronological order;
- prevent look-ahead / same-bar future-data access;
- preserve deterministic entry/exit replay semantics;
- preserve configurable fees, slippage, and funding assumptions;
- preserve reproducibility metadata / dataset identity / runtime identity;
- produce canonical `contracts-v0.1` BacktestResult with required identity, counts, PnL/cost, drawdown, loss-streak, and reproducibility fields;
- keep requested research assumptions explicit rather than silently provider-specific;
- keep executable evidence `NOT_RUN` unless a Product Owner-approved local environment exists.

## Required actions

1. Read this TASK from latest `main`, then fetch latest `main` again and **non-destructively merge** it into existing branch `agent/e3-backtest-validation` once before implementation review/correction. Preserve history; no force push, destructive rebase, or branch recreation.
2. Audit the old E3 source against current `main` E2/runtime/contracts. Update only what is required to make the E3 Slice 1 source structurally compatible with the current repository.
3. Verify the E3 adapter still calls the real E2 runtime/compiled strategy path. If current E2 public interfaces changed, adapt E3 at its own boundary; do not modify E2 production code and do not duplicate strategy logic.
4. Recheck canonical BacktestResult production against the current `contracts-v0.1` contract and the merged E6 canonical BacktestResult validator expectations. Correct E3 serialization/field binding only where needed.
5. Preserve deterministic cost semantics for fees/slippage/funding and ensure gross PnL, net PnL, total fees, trade counts, max drawdown, expectancy/profit-factor handling, and max consecutive losses remain internally coherent by source design.
6. Preserve no-look-ahead protections. Explicitly review candle-close timing, signal evaluation timing, entry/exit fill timing assumptions, and any use of reference prices so no future candle data can affect an earlier decision.
7. Preserve deterministic/reproducible ordering and metadata. Unknown/invalid required inputs must fail closed rather than silently coerce.
8. Review/update deterministic test definitions under E3 scope for at minimum:
   - real E2 runtime consumption rather than copied strategy logic;
   - deterministic identical replay for identical inputs;
   - no-look-ahead / future-candle isolation;
   - entry/exit replay skeleton;
   - fees;
   - slippage;
   - funding assumption/config application;
   - zero/edge trade metrics where applicable;
   - canonical BacktestResult identity/reproducibility fields;
   - malformed/unsupported input fail-closed behavior.
9. Do **not** add a new ValidationDecision policy engine in this task. This refresh stops at canonical BacktestResult; the next E3 validation/OOS task will be issued separately after this implementation is integrated.
10. Do not modify `contracts/**`, E1/E2/E4/E5/E6/E7 production code, E6 registry/storage code, broker/provider code, workflow/CI files, or credentials/secrets.
11. Do not add OOS/Walk Forward/Monte Carlo/optimization/regime work, strategy promotion logic, Registry lifecycle transitions, PAPER/SHADOW/LIVE, or provider execution.
12. Update E3 docs/handoff/status with:
   - latest-main sync commit and parents;
   - exact source/tests/docs correction revision;
   - changed-file scope;
   - current E2 runtime integration point;
   - canonical BacktestResult compatibility statement;
   - no-look-ahead/cost/reproducibility dispositions;
   - executable verification `NOT_RUN`;
   - exact local-only commands.
13. Executable verification is local-only. If no Product Owner-approved local environment exists, do not execute; record exact commands such as:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/backtest -p "test_*.py" -v
```

14. Do not use GitHub Actions/CI/hosted runners or GitHub-triggered project compute. Do not run backtests in GitHub.
15. Push only this bounded refresh to `agent/e3-backtest-validation`, update `coordination/E3/STATUS.md`, then stop for PM/E7 exact-revision review. Do not merge to `main` yourself and do not start the next E3 task automatically.

## Acceptance

Static/source completion requires a current-main-compatible E3 Slice 1 research skeleton that still consumes the real E2 runtime, emits canonical BacktestResult, preserves deterministic costs/reproducibility/no-look-ahead behavior, and introduces no cross-agent or later-validation scope.

Executable verification remains `NOT_RUN`; Gate A/B/C/D remain blocked.

## Writable scope

- `src/backtest/**`
- `tests/backtest/**`
- `docs/backtest/**`
- `status/E3_SLICE1_HANDOFF.md`
- E3-owned status/handoff documentation
- `coordination/E3/STATUS.md`

## Forbidden scope

- `contracts/**` edits;
- E1/E2/E4/E5/E6/E7 production edits;
- copied/reimplemented E2 strategy semantics;
- OOS/Walk Forward/Monte Carlo/optimization/regime implementation;
- Registry/lifecycle promotion implementation;
- broker/provider/API execution;
- credentials/secrets;
- PAPER/SHADOW/LIVE;
- GitHub Actions/CI/hosted/project compute;
- executable PASS claims without approved local execution.

## Completion / status

Refresh only the E3 Slice 1 replay/BacktestResult implementation, push exact evidence, update STATUS, and stop for PM/E7 review.
