# E2 Slice 1 — Minimal Strategy Runtime

## Scope

This implementation consumes the E7-owned `contracts-v0.1` baseline without changing it.

Pipeline:

```text
StrategyDefinition
  -> parse / validate
  -> one E2 Strategy Runtime
  -> Signal
```

The runtime does **not** define a new `Candle` type. It consumes canonical Candle objects or mappings exposing the fields defined by `contracts/SHARED_CONTRACTS_V1.md`.

It does not implement Risk, TradeIntent approval, position sizing, broker execution, backtest metrics, or lifecycle promotion.

## Runtime / DSL version

- Runtime family: `project-r7-e2-strategy-runtime`
- Runtime version: `0.1.0`
- E2 DSL version: `0.1`

A Slice 1 StrategyDefinition declares exact runtime compatibility:

```json
{
  "runtime_compatibility": {
    "runtime_family": "project-r7-e2-strategy-runtime",
    "runtime_version": "0.1.0"
  }
}
```

## Minimal supported primitives

Only what is required for the first baseline strategy is implemented:

- indicator primitive: `SMA`
- Candle field: `close`
- comparison operators: `GT`, `LT`
- boolean composition: `AND`

Unknown primitives produce structured `UNSUPPORTED_PRIMITIVE`. Unknown operators are rejected with `UNSUPPORTED_OPERATOR`.

No RSI, EMA, ATR, VWAP, Bollinger, Donchian, ADX, crossover primitive, arithmetic expression engine, multi-timeframe composition, arbitrary Python, shell, file I/O, network access, or secret access is implemented in Slice 1.

## Baseline rule shape

A minimal SMA crossover definition uses two parameters and two deterministic rules:

```json
{
  "parameters": {
    "fast_window": 2,
    "slow_window": 3
  },
  "rules": {
    "dsl_version": "0.1",
    "long": {
      "operator": "GT",
      "left": {"primitive": "SMA", "field": "close", "window": {"parameter": "fast_window"}},
      "right": {"primitive": "SMA", "field": "close", "window": {"parameter": "slow_window"}}
    },
    "short": {
      "operator": "LT",
      "left": {"primitive": "SMA", "field": "close", "window": {"parameter": "fast_window"}},
      "right": {"primitive": "SMA", "field": "close", "window": {"parameter": "slow_window"}}
    }
  }
}
```

`content_hash` is `sha256:` plus SHA-256 of deterministic canonical JSON for the complete StrategyDefinition excluding the `content_hash` field itself. Changing any material serialized strategy content therefore requires a new hash; contract policy still requires a new `strategy_version` for material semantic changes.

## Closed-candle boundary

For a supplied `evaluated_at = T`, E2 may use a Candle only when:

1. `Candle.close_time <= T`; and
2. `Candle.is_closed == true`.

Future and provisional candles are excluded **before their OHLCV values are read**. This is intentional: appending data beyond `T` cannot change the Signal for boundary `T`.

Visible canonical candles are required to remain in strictly increasing `open_time` order with no duplicate `open_time`. Malformed visible canonical Candle fields fail rather than being repaired by E2.

## Deterministic Signal identity

For the same:

- parsed StrategyDefinition / content hash;
- exact visible closed Candle boundary;
- `evaluated_at`;
- runtime family/version;

the runtime deterministically derives the same:

- direction;
- ordered reason codes;
- `market_boundary_ref`;
- `signal_id`;
- optional `reference_price`.

No clock reads, randomness, network state, file state, account state, or broker state participate in evaluation.

## How E3 must call the same runtime

E3 must import E2 runtime code. It must not reproduce SMA/rule logic inside `src/backtest/`.

With local `PYTHONPATH=src`:

```python
from strategy import StrategyRuntime, parse_strategy_definition

strategy = parse_strategy_definition(strategy_payload)
runtime = StrategyRuntime()

signal = runtime.evaluate(
    strategy,
    candles=canonical_candle_sequence,
    evaluated_at=replay_boundary_utc,
)

runtime_version_for_backtest_result = runtime.version
```

At each replay boundary, E3 supplies its canonical E1 Candle sequence/state to this same `evaluate` method. E3 may model fills, costs, slippage, funding, and trade lifecycle separately, but it must not replace E2's strategy decision semantics.

For reproducibility, E3 should persist `strategy.content_hash` and `runtime.version` into the contract-required `BacktestResult` fields.

## Local verification command

Execution is local-only. From repository root in Windows PowerShell:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests -p "test_*.py" -v
```

No GitHub Actions / CI / runner is permitted for this command.
