# E3 Slice 1 Handoff — Current-Main Refresh

## Handoff

**From:** E3 Backtest & Quantitative Validation Engineer  
**To:** PM / E7 Integration review  
**Task:** `E3-20260822-001`  
**Branch:** `agent/e3-backtest-validation`

## Objective completed

Refreshed the previously reviewed E3 Slice 1 historical replay / canonical BacktestResult research skeleton onto current main without adding later validation or execution scope.

## Exact revisions

- current-main baseline consumed: `42339aa9b33c13554acf99bf6d7b272f22eb5673`
- non-destructive sync merge: `13b8ff937426d2c982ee41fc6ed08950f0761677`
- merge parent 1, prior E3 HEAD: `2c7810e9e9c34e103b085b5c40949870723f1941`
- merge parent 2, current main: `42339aa9b33c13554acf99bf6d7b272f22eb5673`
- bounded source/test correction: `54d40ae96e241f40367016e26b7bd5d03890e629`

The merge preserved history. No force push, destructive rebase, or branch recreation was used.

## Changed-file scope for the correction revision

`54d40ae96e241f40367016e26b7bd5d03890e629` changes only:

- `src/backtest/e2_runtime.py`
- `tests/backtest/test_real_e2_research_skeleton.py`

The final documentation/status recording revision additionally updates only:

- `docs/backtest/SLICE1_RESEARCH_SKELETON.md`
- `status/E3_SLICE1_HANDOFF.md`
- `coordination/E3/STATUS.md`

No `contracts/**`, E1/E2/E4/E5/E6/E7 production code, Registry/storage implementation, broker/provider code, workflow/CI file, credential, or secret was modified.

## Contracts consumed

- `contracts-v0.1` Candle
- `contracts-v0.1` StrategyDefinition
- `contracts-v0.1` Signal
- `contracts-v0.1` BacktestResult

No shared contract was produced, revised, or reinterpreted by E3.

## Current E2 runtime integration point

The E3 adapter still calls the real current-main E2 path:

```python
from strategy import StrategyRuntime, parse_strategy_definition

parsed_strategy = parse_strategy_definition(strategy_definition)
runtime = StrategyRuntime()
signal = runtime.evaluate(parsed_strategy, closed_history, evaluated_at)
```

E3 does not copy or reimplement SMA, DSL operators, parameters, StrategyDefinition semantics, TradeIntent policy, or provider execution behavior.

Current-main E2 exports `RUNTIME_VERSION = "0.1.0"` and enforces shared schema `contracts-v0.1`. E3 records the actual runtime instance version in BacktestResult.

## Canonical BacktestResult disposition

Static/source comparison against current-main E6 `validate_backtest_result_contract` found E3's existing `BacktestResult.to_contract()` field binding structurally aligned with the required identity/reproducibility and core metric fields.

The refreshed integration test definition now explicitly feeds the E3 contract payload into the current E6 validator and checks identity/reproducibility/core required fields.

Current E6 permits `profit_factor=null`; E3 preserves the already locked behavior that no aggregate losing PnL produces a present `profit_factor` field with JSON `null`, not an omitted field or Infinity.

This is static/test-definition evidence only. No executable compatibility PASS is claimed.

## Replay / no-look-ahead disposition

Preserved behavior:

- only closed historical candles accepted;
- deterministic chronological replay;
- E2 sees only the finalized prefix at each Candle close;
- Signal evaluated time must equal the replay boundary;
- entry fills no earlier than next Candle open;
- opposite-signal exit fills no earlier than next Candle open;
- final-bar signal cannot enter without a later fill bar;
- Signal reference price is not used as a same-bar fill shortcut;
- same-candle SL/TP ambiguity resolves conservatively to STOP;
- invalid required contract inputs fail closed through existing replay checks.

The refreshed real-E2 test definition adds a future-candle poisoning case to ensure unreadable future OHLC cannot alter an earlier E2 boundary decision.

## Costs / metrics / reproducibility

No model semantics changed.

Cost assumptions remain explicitly versioned and configurable:

- maker/taker entry/exit fees;
- adverse entry/exit slippage;
- fixed deterministic funding event model.

Gross PnL is calculated from slippage-adjusted fills; net PnL subtracts fees and funding, while reported slippage cost is not double-subtracted.

Core metrics remain total trades, wins/losses/breakeven, gross/net PnL, fees, profit factor, expectancy, max drawdown, max consecutive losses, plus audit-only slippage/funding totals.

Backtest result identity remains deterministic from strategy, runtime, dataset, cost assumptions, replay settings, and replay trade fingerprints. Runtime `created_at` is not included in deterministic result identity.

## Dataset / validation status

No real dataset or OOS dataset was executed in this task.

- dataset execution: `NOT_RUN`
- OOS contamination status: `NOT_APPLICABLE` for this source refresh
- strategy validation decision: `NO DECISION`
- OOS: `NOT_RUN`
- Walk Forward: `NOT_RUN`
- Monte Carlo: `NOT_RUN`
- optimization: not implemented
- regime analysis: not implemented

## External blocker discovered on current main

Latest main currently has an E1 public package inconsistency outside E3 writable scope:

- `src/market_data/__init__.py` imports `Candle` and `CONTRACT_SCHEMA_VERSION` from `.candle`;
- current-main `src/market_data/candle.py` contains E1 error-class definitions and does not provide those exports.

Therefore `from market_data import Candle` is structurally blocked on current main. E3 did not modify E1 code.

To keep the E3 refresh bounded and current-main-compatible, the real-E2 integration test now uses canonical `contracts-v0.1` Candle mappings. Full E1 public-package -> E2 -> E3 integration should remain blocked until E1/PM/E7 reconciles the E1 main defect.

## Executable verification

`NOT_RUN`

No Product Owner-approved local environment was available in this ChatGPT/GitHub context. No test, replay, backtest, metric verification, or bug reproduction was executed.

Exact local-only command:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/backtest -p "test_*.py" -v
```

Targeted current-main E2 -> E3 definition:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python tests/backtest/test_real_e2_research_skeleton.py -v
```

## Gates / lifecycle

- Gate A: `BLOCKED`
- Gate B: `BLOCKED`
- Gate C: `BLOCKED`
- Gate D: `BLOCKED`
- validation PASS: not claimed
- Registry lifecycle transition: none
- PAPER/SHADOW/LIVE: no impact
- Product Owner approval: not inferred

## GitHub compute / security

- GitHub Actions: not used
- GitHub CI: not used
- GitHub-hosted runner: not used
- GitHub-triggered self-hosted runner: not used
- GitHub project compute/backtest: not used
- credentials/secrets: none added or requested

## Recommended next owner

PM / E7 should review exact revisions above and separately route the current-main E1 public-import defect to the E1 owner. E3 must not begin the next validation/OOS task until a new `coordination/E3/TASK.md` is issued.
