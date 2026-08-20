# E3 Slice 1 — Research Skeleton

> Owner: E3 Backtest & Quantitative Validation Engineer  
> Contract baseline: `contracts-v0.1`  
> Branch: `agent/e3-backtest-validation`

## Scope

This Slice 1 implementation is intentionally narrow:

```text
Historical Candle
  -> E2 Strategy Runtime binding
  -> closed-candle historical replay
  -> simulated fills/costs
  -> basic metrics
  -> BacktestResult
```

It does not implement Monte Carlo, full Walk Forward, parameter optimization, regime analysis, or strategy promotion.

## Non-negotiable strategy boundary

E3 does **not** accept a precomputed Signal stream as a substitute for strategy execution and does not contain strategy conditions/indicator logic.

`HistoricalReplayEngine` requires an `E2RuntimeBinding`. The binding contains:

- the real E2 runtime object;
- the exact E2 runtime version;
- a thin invocation adapter for E2's public runtime API.

The adapter may translate call shape only. It must not implement strategy semantics.

For each historical candle boundary, E3 passes E2 only the tuple of finalized candles whose `close_time` is at or before that evaluation boundary. A Signal whose `evaluated_at` does not equal that exact boundary is rejected.

At the time this Slice 1 branch was created, no `agent/e2-strategy-engine` branch/PR/commit was available in GitHub, so the concrete E2 invocation adapter cannot be frozen without guessing E2's API. The replay implementation is therefore ready for that binding, but E7 must treat concrete E2-runtime integration evidence as **BLOCKED** until E2 publishes its handoff/API.

## Candle and time semantics

Consumed Candle semantics come from `contracts-v0.1`:

- UTC only;
- `[open_time, close_time)`;
- `is_closed=true` required;
- Decimal/string financial semantics;
- baseline timeframes `1m`, `15m`, `1h`, `4h`;
- duplicate/out-of-order/overlapping candle input is rejected;
- Slice 1 replay supports exactly one strategy-required timeframe.

A signal produced after candle `T` is filled no earlier than the next candle open. A signal on the final dataset candle cannot create a new position because no future fill bar exists.

## Entry / exit replay skeleton

Current research-only rules:

- LONG/SHORT while flat -> schedule entry at next candle open;
- opposite E2 direction while open -> schedule exit at next candle open;
- no pyramiding or averaging down;
- strategy stop/target levels from the entry Signal may be replayed;
- if a candle touches both stop and target and intrabar sequence is unknown, STOP wins;
- stop gaps use the adverse candle-open reference when the open is already beyond the stop;
- max hold begins from simulated actual entry fill time and exits at the first candle open at/after the deadline;
- an open position at dataset end is closed at the final candle close by default and labeled `DATASET_END`.

For OHLC-only stop/target exits, exact intrabar exit time is unknowable. Slice 1 records the candle close time for that exit, which is conservative for funding duration and avoids fabricating an intrabar timestamp.

These are E3 replay assumptions, not E5 live sizing/approval authority.

## Costs

All cost assumptions are explicit and versioned per run.

### Fees

`FeeModel` supports:

- maker bps;
- taker bps;
- separate entry/exit liquidity roles.

Fees are applied to simulated fill notional.

### Slippage

`SlippageModel` supports separate entry/exit adverse bps. Slippage is embedded in simulated fill prices. Therefore:

- `gross_pnl` uses simulated fill prices and already reflects slippage;
- `slippage_cost` is also reported separately for audit;
- slippage is **not** subtracted from net PnL a second time.

### Funding

Slice 1 provides `FixedFundingModel` as an explicit deterministic assumption:

- fixed `rate_per_event`;
- fixed interval;
- explicit first funding-event timestamp;
- positive funding charges LONG and credits SHORT;
- event window is `opened_at <= event < closed_at`;
- notional approximation is entry fill price x fixed replay quantity.

Historical event-by-event funding data can replace this assumption later without changing E2 strategy semantics.

## Basic metrics

`BacktestResult` currently includes the contracts-v0.1 required core metrics:

- total trades;
- wins / losses / breakeven;
- gross PnL;
- net PnL;
- total fees;
- profit factor;
- expectancy;
- max absolute drawdown on cumulative net trade PnL;
- max consecutive losses.

Additional Slice 1 fields include win rate, average win/loss, total slippage cost, and total funding cost.

When profit factor is mathematically undefined because there are no losing trades, the field is present with `null`; E7 should confirm this edge-case serialization before a stable contract version.

## Reproducibility metadata

Every result carries/references:

- exact `(strategy_id, strategy_version)`;
- `strategy_content_hash`;
- E2 `runtime_version`;
- E3 replay engine version;
- E1-provided `dataset_id` and `dataset_hash`;
- exact consumed dataset start/end;
- versioned cost-model identifier;
- exact fee/slippage/funding assumptions;
- deterministic `backtest_result_id` derived from immutable inputs and replay trades.

`created_at` records run time and is intentionally excluded from the deterministic result ID.

## Explicitly not performed

The emitted result marks these stages `NOT_RUN` in Slice 1:

- OOS;
- Walk Forward;
- Monte Carlo;
- parameter robustness;
- regime analysis.

No missing stage is silently treated as PASS.

## Local-only verification

GitHub Actions/CI/runners are forbidden. This branch contains test definitions only.

Required local command from repository root:

```text
python -m unittest discover -s tests/backtest -p "test_*.py" -v
```

Windows Python Launcher equivalent:

```text
py -3 -m unittest discover -s tests/backtest -p "test_*.py" -v
```

The current ChatGPT GitHub environment is not the Product Owner's local execution machine, so these tests are recorded as `NOT_RUN` until executed locally.

## E7 Slice 1 integration condition

E7 should not mark the research skeleton integrated until E2 publishes its concrete runtime and a local integration test proves:

```text
same StrategyDefinition
+ same exact closed Candle boundary
+ same E2 runtime version
= same deterministic Signal
```

and E3's replay is shown to invoke that same runtime object rather than a private strategy implementation.
