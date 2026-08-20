# E3 Slice 1 — Research Skeleton

> Owner: E3 Backtest & Quantitative Validation Engineer  
> Contract baseline: `contracts-v0.1`  
> Branch: `agent/e3-backtest-validation`

## Scope

Slice 1 is intentionally narrow:

```text
E1 Historical Candle
  -> E2 Strategy Runtime
  -> E3 closed-candle historical replay
  -> simulated fills / costs
  -> basic metrics
  -> BacktestResult
```

This slice does not implement Monte Carlo, full Walk Forward, optimization, full regime analysis, or strategy promotion.

## E2 is the only strategy semantic implementation

E3 does not accept a precomputed Signal stream as a substitute for strategy execution and contains no SMA, indicator, DSL-rule, or strategy-condition implementation.

The concrete E3 binding is `project_e2_runtime_binding()` in `src/backtest/e2_runtime.py`. It uses the exact public API published by E2 Slice 1:

```python
from strategy import StrategyRuntime, parse_strategy_definition

parsed = parse_strategy_definition(strategy_definition)
runtime = StrategyRuntime()
signal = runtime.evaluate(parsed, closed_candle_history, evaluated_at)
```

The E3 adapter only changes call shape. It does not evaluate `rules`, `parameters`, SMA, GT/LT/AND, or any other strategy primitive.

`BacktestResult.runtime_version` is taken from the actual E2 runtime instance. The integration test definition asserts that the object inside the binding is an actual E2 `StrategyRuntime`.

## E1 Candle integration

E1 Slice 1 publishes canonical `market_data.Candle` with:

- `schema_version="contracts-v0.1"`;
- UTC times;
- half-open `[open_time, close_time)`;
- Decimal financial fields;
- canonical `1m`, `15m`, `1h`, `4h` timeframes;
- explicit `is_closed` status.

E3 consumes these Candle objects structurally and does not redefine Candle.

The cross-role test definition `tests/backtest/test_real_e2_research_skeleton.py` constructs actual E1 `Candle` objects, passes them through actual E2 `StrategyRuntime`, then into E3 replay and `BacktestResult` generation.

## No-look-ahead boundary

For every historical boundary E3 passes E2 only the finalized Candle prefix available at that boundary.

A Signal is rejected if `Signal.evaluated_at` differs from the exact replay boundary.

Entry timing is deliberately delayed:

- a LONG/SHORT Signal at Candle close may fill no earlier than the next Candle open;
- an opposite-direction Signal while a position is open schedules exit no earlier than the next Candle open;
- a Signal on the final dataset Candle cannot create a new position because no future fill bar exists.

This prevents a close-known signal from receiving a fill earlier inside the same completed Candle.

## Replay skeleton

Current Slice 1 behavior:

- LONG/SHORT while flat -> entry at next Candle open;
- opposite E2 direction while open -> exit at next Candle open;
- no pyramiding or averaging down;
- strategy stop/target/max-hold values may be captured from the entry Signal;
- if one OHLC Candle touches both stop and target and intrabar order is unknown, STOP wins;
- a stop gap uses the adverse Candle-open reference when the market has already moved through the stop;
- max hold starts from simulated actual entry fill time and exits at the first available Candle open at/after the deadline;
- an open position at dataset end closes at final Candle close by default with `DATASET_END`.

For OHLC-only protective exits the exact intrabar event timestamp is unknowable. Slice 1 records Candle close time rather than inventing an intrabar timestamp. This is conservative for funding-duration accounting.

These are research replay assumptions only; they do not create E5 live risk/sizing authority.

## Costs

Every replay requires explicit versioned cost assumptions.

### Fees

`FeeModel` supports:

- maker bps;
- taker bps;
- separate entry/exit liquidity roles.

Fees are applied to simulated fill notional.

### Slippage

`SlippageModel` supports separate adverse entry/exit bps.

Slippage is embedded in simulated fill price. `slippage_cost` is also reported separately for audit, but is not subtracted from net PnL a second time.

### Funding

Slice 1 provides deterministic `FixedFundingModel` configuration:

- fixed rate per event;
- fixed interval;
- explicit first funding-event timestamp;
- positive rate charges LONG and credits SHORT;
- event window `opened_at <= event < closed_at`;
- notional approximation = entry fill price x fixed replay quantity.

Historical event-by-event funding can replace this assumption later without changing E2 strategy semantics.

## Basic metrics

Current result capability includes:

- total trades;
- wins / losses / breakeven;
- win rate;
- average win/loss;
- gross PnL;
- net PnL;
- total fees;
- total slippage cost;
- total funding cost;
- profit factor;
- expectancy;
- max absolute drawdown on cumulative net closed-trade PnL;
- max consecutive losses.

If there are no losing trades, profit factor is currently serialized as `null`; E7 should confirm this edge representation before a future STABLE contract.

## Reproducibility metadata

Every `BacktestResult` carries/references:

- exact strategy ID/version;
- `strategy_content_hash`;
- actual E2 `runtime_version`;
- E3 replay engine version;
- dataset ID/hash/start/end;
- cost-model version;
- exact fee/slippage/funding assumptions;
- deterministic `backtest_result_id` derived from immutable replay inputs/results.

`created_at` records run time and is intentionally excluded from the deterministic result ID.

## Validation stages deliberately not implemented

Slice 1 marks these as `NOT_RUN`:

- OOS;
- Walk Forward;
- Monte Carlo;
- parameter robustness;
- regime analysis.

No missing stage is converted into PASS.

## Cross-module review finding

E1's executable Candle producer uses `schema_version="contracts-v0.1"`. E2's own local strategy test fixtures currently use `schema_version="0.1"`, while E2 runtime accepts/preserves the StrategyDefinition schema value rather than enforcing one exact value.

The E3 cross-role integration test deliberately uses E1's `CONTRACT_SCHEMA_VERSION` (`contracts-v0.1`) for both StrategyDefinition and Candle, and expects E2 Signal to preserve that value. E7 should review whether E2's internal fixture value should be aligned. E3 does not change E2 tests or shared contract semantics.

## Local-only verification

GitHub Actions/CI/runners are forbidden. No test or replay was executed in the GitHub environment.

### E3-only unit/replay definitions

From repository root:

```powershell
python -m unittest discover -s tests/backtest -p "test_costs.py" -v
python -m unittest discover -s tests/backtest -p "test_metrics.py" -v
python -m unittest discover -s tests/backtest -p "test_replay.py" -v
```

Windows launcher equivalents may replace `python` with `py -3`.

### Full E1 -> E2 -> E3 Research Skeleton

Run only from a local integration checkout containing the reviewed E1, E2, and E3 Slice 1 revisions:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python tests/backtest/test_real_e2_research_skeleton.py -v
```

Expected test definition verifies:

```text
actual E1 Candle objects
-> actual E2 StrategyRuntime object
-> E3 replay
-> deterministic BacktestResult
```

and checks that the same StrategyDefinition + same exact Candle boundary + same E2 runtime version produces the same deterministic replay identity/metrics.

Current verification status: `NOT_RUN` because this ChatGPT GitHub context is not the Product Owner-approved local execution environment.

## E7 Slice 1 integration condition

E7 should combine the reviewed E1/E2/E3 revisions in an integration checkout and execute the above commands locally. E3 does not claim Research Skeleton PASS until that evidence exists.
