# E7 Current Task

- task_id: `E7-20260822-012`
- issued_at: `2026-08-22T20:36:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-e3-slice1-current-main-review-20260822`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, current `main`, merged E1 PR #21, merged E6 Registry/evidence persistence

## Objective

Perform a fresh exact-revision static/integration review of PR #22, the reconciled E3 Slice 1 historical replay / canonical BacktestResult research skeleton, and decide whether PM may merge it into current `main`.

This task is static/source review only. It does **not** authorize project execution, backtests, migrations, provider calls, ValidationDecision promotion, PAPER/SHADOW/LIVE, or GitHub compute.

## Review inputs

- PR: `#22 backtest: reconcile Slice 1 replay with corrected current main`;
- E3 branch: `agent/e3-backtest-validation`;
- observed PR head at PM audit: `dbce39cec5d5104e0fe79aca4e3be0e8aef459ec`;
- preserved E3 production pin: `54d40ae96e241f40367016e26b7bd5d03890e629`;
- post-E1 reconciliation merge: `aee813855759cd63548d452a93de26fc208afa20`;
- reconciliation test revision: `185185fbb403b3622c96a218717d67a2eb41a684`;
- E3 reported production changes after production pin: `NONE`;
- merged E1 import-integrity fix: PR #21 merge `1158a777a2830afc37066ef62ebefe624a9ca28e`;
- corrected E1 blobs:
  - `candle.py` = `5605830b4da4fbe10e94cff72794a495db9ebf6e`;
  - `errors.py` = `fb9cd216b83cd595304d23a5cec46fd9a2091894`;
  - `timeframes.py` = `ac08d88dd327719b01babba098d78da0f34ab5bf`;
- executable verification: `NOT_RUN`.

## Required review

1. Work only on fresh branch `agent/e7-e3-slice1-current-main-review-20260822` created from latest `main` after this TASK issuance.
2. Review actual PR #22 source/tests/docs at the exact observed head (or a freshly observed unchanged successor containing only E3 status/handoff). Do not rely only on E3 STATUS claims.
3. Recheck PR scope. It must remain limited to E3-owned `src/backtest/**`, `tests/backtest/**`, E3 docs/handoff/status. No `contracts/**`, E1/E2/E4/E5/E6 production, workflow/CI, provider/credential/secret, Registry promotion, or later-slice implementation.
4. Verify current-main reconciliation is non-destructive and the branch is not meaningfully behind current production/shared-contract state. Coordination-only TASK drift after the reviewed pin is not by itself a blocker.
5. Verify the previous E1 blocker is actually cleared by merged source structure: supported `market_data` package exports canonical `Candle` / `CONTRACT_SCHEMA_VERSION`; E3 integration definitions use the supported E1 package rather than copied Candle/timeframe/error logic.
6. Verify E3 consumes the actual current E2 public runtime path:
   - `parse_strategy_definition` is the E2 validation/compile boundary;
   - actual `StrategyRuntime.evaluate` is invoked;
   - E3 does not copy/reimplement E2 DSL, indicator, signal, or strategy decision semantics;
   - malformed/unavailable runtime integration fails closed.
7. Verify historical replay no-look-ahead semantics by source design:
   - only finalized closed candles accepted;
   - deterministic chronological ordering;
   - E2 receives only the historical prefix available at each close boundary;
   - signal `evaluated_at` cannot bind to future data;
   - entries and opposite-signal exits use next-open timing rather than same-bar hindsight;
   - final-bar signals cannot obtain a nonexistent future fill;
   - stop/target intrabar ambiguity handling is explicit and conservative rather than hindsight-optimistic.
8. Verify cost/replay arithmetic by source design:
   - explicit/versioned fee model;
   - adverse slippage semantics;
   - funding assumptions/configuration are deterministic and included in cost/reproducibility metadata;
   - gross PnL, net PnL, total fees/costs, trade counts, expectancy, profit factor, max drawdown, and max consecutive losses are internally coherent;
   - no martingale/live sizing authority is introduced by research `fixed_quantity`.
9. Verify deterministic reproducibility:
   - dataset identity/hash/time range;
   - strategy identity/version/content hash;
   - E2 runtime version;
   - replay/cost assumptions;
   - stable trade/result fingerprint inputs;
   - repeated identical inputs are designed to produce identical research result identity except explicitly non-identity observational metadata, if any.
10. Recheck canonical `contracts-v0.1` BacktestResult serialization against merged E6 `validate_backtest_result_contract` expectations. Required identity/reproducibility/core metric fields, UTC/RFC3339 and decimal interchange rules must align. Recheck the `profit_factor` no-losing-PnL edge remains field-present with `null`, not Infinity or a noncanonical string.
11. Confirm BacktestResult is research evidence only: no ValidationDecision engine is added, no BacktestResult-alone lifecycle promotion is performed, and E6 durable E3 ValidationDecision authority remains untouched.
12. Review deterministic test definitions, especially `tests/backtest/test_real_e2_research_skeleton.py`, and confirm they statically cover actual E1 Candle use, actual E2 runtime path, deterministic replay, future-candle isolation, canonical E6 BacktestResult validation, fees/slippage/funding, entry/exit skeleton, edge metrics, and fail-closed unsupported input behavior. Do not execute tests in GitHub.
13. Recheck documentation/handoff accurately distinguishes `PASS STATIC` from executable evidence and records exact local-only commands.
14. Persist an E7 review artifact under `status/e7/` and update `coordination/E7/STATUS.md` with:
   - exact reviewed PR #22 head and E3 production pin;
   - E1 blocker disposition;
   - real E2 runtime-consumption disposition;
   - no-look-ahead/timing disposition;
   - costs/metrics/reproducibility disposition;
   - canonical BacktestResult/E6-validator disposition;
   - scope/synchronization disposition;
   - PR #22 merge recommendation;
   - executable verification `NOT_RUN`;
   - Gate A/B/C/D unchanged.
15. If all static/source conditions pass, state exactly `PM MAY MERGE PR #22`. This is static acceptance only and does not establish Gate A PASS or any ValidationDecision/PAPER/SHADOW/LIVE authority.
16. If blocked, identify the exact source/contract/integration defect and owner. Do not modify E1-E6 production code or shared contracts in this review task.
17. Do not run project tests/backtests/import probes, migrations, provider calls, GitHub Actions/CI/hosted runners, or GitHub-triggered compute. Do not create a Codex ticket without a locally reproduced executable defect.

## Acceptance

Task completes when Git contains an exact-revision E7 static/integration review that either recommends PM merge PR #22 or blocks it with a precise source condition. Executable verification remains `NOT_RUN`; Gate A/B/C/D remain blocked.

## Writable scope

- E7-owned review/status/integration documentation
- `coordination/E7/STATUS.md`

## Forbidden scope

- E1-E6 production implementation edits;
- shared-contract changes;
- E3 implementation edits;
- ValidationDecision/OOS/Walk Forward/Monte Carlo/optimization/regime implementation;
- Registry/lifecycle promotion implementation;
- broker/provider/API execution;
- PAPER/SHADOW/LIVE advancement;
- GitHub compute/CI.

## Completion / status

Persist the exact-revision review and STATUS, then stop and wait for PM. Do not merge PR #22 or start another task automatically.