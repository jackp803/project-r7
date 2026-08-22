# E3 Current Task

- task_id: `E3-20260822-003`
- issued_at: `2026-08-22T20:10:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e3-backtest-validation`
- authority: `agents/E3_BACKTEST_VALIDATION.md`, `agents/README.md`, `contracts-v0.1`, current `main`, merged E1 PR #21 import-integrity correction

## Objective

Perform a narrow reconciliation of the completed E3 Slice 1 replay/BacktestResult refresh against corrected current `main` after E1 PR #21 restored the `market_data` public-import/module identities.

This is a sync/recheck task only. Do not expand E3 research scope and do not start ValidationDecision/OOS work.

## Frozen E3 evidence to preserve

- prior completed task: `E3-20260822-001`;
- prior source/test correction revision: `54d40ae96e241f40367016e26b7bd5d03890e629`;
- prior non-destructive sync: `13b8ff937426d2c982ee41fc6ed08950f0761677`;
- architecture: Historical Candle -> actual E2 Strategy Runtime -> E3 replay -> canonical BacktestResult;
- executable verification: `NOT_RUN`.

## Corrected E1 baseline now on main

- PR #21 merge commit: `1158a777a2830afc37066ef62ebefe624a9ca28e`;
- `src/market_data/candle.py` restored to accepted blob `5605830b4da4fbe10e94cff72794a495db9ebf6e`;
- `src/market_data/errors.py` restored to accepted blob `fb9cd216b83cd595304d23a5cec46fd9a2091894`;
- `src/market_data/timeframes.py` restored to accepted blob `ac08d88dd327719b01babba098d78da0f34ab5bf`;
- E1 import-integrity test definitions are merged;
- executable E1 import/test evidence remains `NOT_RUN`.

## Required actions

1. Read this TASK from latest `main`, fetch latest `main` again, and non-destructively merge latest `main` into existing `agent/e3-backtest-validation`. Preserve history; no force push, destructive rebase, or branch recreation.
2. Recheck the merged E1 `market_data` public surface against E3's existing Slice 1 source. Confirm the previous external import/file-role blocker is removed by source structure.
3. Do not work around E1. Consume the supported E1 Candle/public package normally; do not copy E1 Candle/timeframe/error logic into E3.
4. Reconfirm E3 still consumes the actual current E2 `StrategyRuntime` / `parse_strategy_definition` path and does not duplicate E2 strategy semantics.
5. Reconfirm canonical BacktestResult serialization remains compatible with current `contracts-v0.1` and merged E6 canonical validator expectations.
6. Preserve deterministic closed-candle prefix replay, no-look-ahead, next-open entry/exit timing assumptions, fees, slippage, funding assumptions, metrics, reproducibility metadata, and fail-closed input handling.
7. Prefer **no E3 production source change** if the E1 correction alone resolves the blocker. If an E3-owned import/interface adjustment is genuinely required after synchronization, keep it minimal, explain the exact reason, and touch only E3 writable scope.
8. Update E3 handoff/status with:
   - latest main consumed;
   - reconciliation merge commit and parents;
   - whether E3 production changed after the prior `54d40ae...` pin;
   - E1 blocker disposition;
   - exact final branch/source revision;
   - changed-file scope;
   - executable verification `NOT_RUN`;
   - exact local-only command.
9. Do not add ValidationDecision policy, OOS, Walk Forward, Monte Carlo, optimization, regime classification, Registry promotion logic, PAPER/SHADOW/LIVE, broker/provider execution, or shared-contract changes.
10. Do not modify E1/E2/E4/E5/E6/E7 production code or `contracts/**`.
11. Do not execute tests/backtests/import probes in GitHub. Without Product Owner-approved local execution, keep `NOT_RUN` and record:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/backtest -p "test_*.py" -v
python tests/backtest/test_real_e2_research_skeleton.py -v
```

12. Push this bounded reconciliation to `agent/e3-backtest-validation`, update `coordination/E3/STATUS.md`, and stop for PM/E7 exact-revision review. Do not merge yourself or start the next E3 task.

## Acceptance

Static/source completion requires the E3 Slice 1 replay branch to be current-main reconciled, the E1 import blocker to be cleared by source structure, real E2 runtime consumption and canonical BacktestResult behavior preserved, and no scope expansion introduced.

Executable verification remains `NOT_RUN`; Gate A/B/C/D remain blocked.

## Writable scope

- `src/backtest/**`
- `tests/backtest/**`
- `docs/backtest/**`
- `status/E3_SLICE1_HANDOFF.md`
- E3-owned status/handoff docs
- `coordination/E3/STATUS.md`

## Forbidden scope

- `contracts/**`;
- E1/E2/E4/E5/E6/E7 production edits;
- copied E1/E2 semantics;
- OOS/Walk Forward/Monte Carlo/optimization/regime implementation;
- ValidationDecision policy engine;
- Registry lifecycle promotion;
- broker/provider/API execution;
- credentials/secrets;
- PAPER/SHADOW/LIVE;
- GitHub Actions/CI/hosted/project compute;
- executable PASS claims.

## Completion / status

Reconcile only against corrected current `main`, update exact evidence, and stop for PM/E7 review.
