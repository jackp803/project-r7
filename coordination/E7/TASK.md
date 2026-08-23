# E7 Current Task

- task_id: `E7-20260824-018`
- issued_at: `2026-08-24T00:11:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-a-validation-fixture-review-20260824`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, current `main`, approved local Gate A failure evidence, PR #28

## Objective

Perform an exact-revision static/integration review of the bounded E3 Gate A validation test-fixture correction in PR #28 and decide whether PM may merge it before a new AgentBridge local-only Gate A rerun.

This task is static/source review only. Do not execute project code, do not rerun Gate A, and do not claim executable PASS. The previous approved local matrix remains authoritative evidence: Market Data / Indicators / Strategy / Backtest passed, Validation failed, and Registry / Storage / Integration were NOT_RUN at source revision `6ed214276038b1ad517e8875c10946b8fcccf4a3`.

## Review inputs

- PR: `#28 test(validation): correct Gate A quantitative FAIL fixture`;
- E3 branch: `agent/e3-gate-a-validation-fixture-fix-20260823`;
- observed PR head: `6f5b1c65a079e18464690a3a6e7a0b15e41cc7fd`;
- corrected source revision reported by E3: `f7698f03a9bfb4280190a357b50366b43b260e21`;
- branch baseline: `b8be4c450c9730f62c6c87b0db9da10fbb6af3cb`;
- changed-file scope observed by PM: only `tests/validation/test_oos_validation.py` and `coordination/E3/STATUS.md`;
- production `src/validation/oos.py` unchanged;
- contracts unchanged;
- E3 executable verification after fix: `NOT_RUN`.

## Required review

1. Read this TASK from latest `main`, fetch latest `main`, and work only on fresh branch `agent/e7-gate-a-validation-fixture-review-20260824` created by PM from post-TASK latest `main`.
2. Review actual PR #28 at exact head `6f5b1c65a079e18464690a3a6e7a0b15e41cc7fd`; do not rely only on E3 STATUS.
3. Reconfirm changed-file scope is limited to E3-owned validation test definition plus E3 STATUS. Any production, contracts, cross-agent source, workflow/CI, provider, lifecycle, PAPER/SHADOW/LIVE change is a blocker.
4. Verify the original locally reproduced failure was caused by the old test fixture being structurally impossible: `losses=3` with `max_consecutive_losses=4`, while production intentionally requires `max_consecutive_losses <= losses` and classifies violations as `BLOCKED / BACKTEST_TRADE_COUNTS_INCONSISTENT` before quantitative FAIL evaluation.
5. Verify PR #28 preserves that production fail-closed behavior and does not weaken or change `src/validation/oos.py` semantics.
6. Verify the corrected quantitative FAIL fixture is structurally coherent and still fails all five intended configured quantitative criteria in the existing deterministic reason order:
   - `MIN_TOTAL_TRADES_NOT_MET`;
   - `MIN_NET_PNL_NOT_MET`;
   - `MAX_DRAWDOWN_EXCEEDED`;
   - `MAX_CONSECUTIVE_LOSSES_EXCEEDED`;
   - `MIN_PROFIT_FACTOR_NOT_MET`.
7. Verify the new regression explicitly covers the impossible consecutive-loss shape and expects exactly `BLOCKED / BACKTEST_TRADE_COUNTS_INCONSISTENT`.
8. Reconfirm the correction does not change policy thresholds, outcome precedence, reason-code vocabulary/order, BacktestResult semantics, E6 authority, Registry lifecycle, contracts, or production behavior.
9. Treat E3 `local_verification=NOT_RUN` correctly. Do not convert it to PASS. Static review may accept the fixture correction while executable acceptance remains pending a new Product Owner-approved AgentBridge local-only run at a later exact merged revision.
10. Persist E7-owned review evidence under `status/e7/` and update `coordination/E7/STATUS.md` with:
    - exact reviewed PR head;
    - scope disposition;
    - original failure classification;
    - fixture coherence disposition;
    - production-semantics preservation disposition;
    - regression-coverage disposition;
    - executable verification = `NOT_RUN` for this review;
    - PR #28 merge recommendation;
    - Gate A remains `BLOCKED` until local rerun;
    - Gate B/C/D unchanged;
    - PAPER/SHADOW/LIVE unchanged unauthorized.
11. If all static conditions pass, state exactly `PM MAY MERGE PR #28`.
12. If blocked, identify the exact source/test/scope defect and owner. Do not modify E3 implementation/test in this review task.
13. Do not run tests, backtests, imports, migrations, provider calls, GitHub Actions/CI/hosted runners, or GitHub-triggered compute.

## Acceptance

Task completes when Git contains an exact-revision E7 review that either says `PM MAY MERGE PR #28` or blocks it with a precise defect. Neither outcome is Gate A PASS.

## Writable scope

- E7-owned review/status documentation under `status/e7/**`;
- `coordination/E7/STATUS.md`.

## Forbidden scope

- E1-E6 production changes;
- E3 test/source changes;
- `contracts/**` changes;
- project executable verification;
- Gate A rerun;
- provider/private APIs;
- lifecycle promotion;
- PAPER/SHADOW/LIVE;
- GitHub Actions/CI/hosted compute.

## Completion

Persist review evidence/status, push to the target branch, and stop for PM. Do not merge PR #28 or start the local rerun automatically.
