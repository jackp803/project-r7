# E3 Slice 1 — Current-Main Research Skeleton

> Owner: E3 Backtest & Quantitative Validation Engineer  
> Contract baseline: `contracts-v0.1`  
> Task: `E3-20260822-001`  
> Branch: `agent/e3-backtest-validation`

## Refresh revisions

- latest `main` consumed: `42339aa9b33c13554acf99bf6d7b272f22eb5673`
- non-destructive main-sync merge: `13b8ff937426d2c982ee41fc6ed08950f0761677`
- merge parents:
  - prior E3 HEAD: `2c7810e9e9c34e103b085b5c40949870723f1941`
  - current-main HEAD: `42339aa9b33c13554acf99bf6d7b272f22eb5673`
- bounded source/test correction: `54d40ae96e241f40367016e26b7bd5d03890e629`

No rebase, force push, branch recreation, shared-contract edit, or cross-agent production edit was used.

## Scope

The preserved research path is:

```text
canonical closed historical Candle
  -> actual current-main E2 StrategyDefinition parser
  -> actual current-main E2 StrategyRuntime
  -> E3 deterministic historical replay
  -> versioned fee/slippage/funding assumptions
  -> basic replay metrics
  -> canonical contracts-v0.1 BacktestResult
```

This refresh does not add OOS, Walk Forward, Monte Carlo, optimization, regime classification, ValidationDecision policy, Registry lifecycle transition, PAPER, SHADOW, LIVE, or provider execution behavior.

## Current E2 integration point

E3 still delegates all strategy semantics to E2. The adapter `project_e2_runtime_binding()` uses the current-main public path:

```python
from strategy import StrategyRuntime, parse_strategy_definition

parsed = parse_strategy_definition(strategy_definition)
runtime = StrategyRuntime()
signal = runtime.evaluate(parsed, closed_candle_history, evaluated_at)
```

`parse_strategy_definition` is E2's authoritative StrategyDefinition validation/compiled representation boundary. E3 does not evaluate SMA, DSL operators, parameters, entry profiles, TradeIntent semantics, or provider-specific execution rules.

Current-main E2 explicitly enforces `schema_version="contracts-v0.1"`, runtime family/version compatibility, immutable strategy content hash, closed-candle visibility, and deterministic Signal production. E3 records the actual `runtime.version` in BacktestResult.

E2 TradeIntent was reviewed only as a downstream E2/E5 boundary. E3 Slice 1 does not produce or consume TradeIntent for historical replay.

## Candle boundary and current E1 blocker

E3 replay consumes canonical Candle objects/mappings structurally and requires the shared fields, closed status, chronological ordering, matching symbol/timeframe, and exact dataset boundaries.

During this refresh, latest main was found to have an external E1 public-import defect: `src/market_data/__init__.py` imports `Candle` and `CONTRACT_SCHEMA_VERSION` from `src/market_data/candle.py`, while the current-main `candle.py` content contains E1 error classes instead of those exports. E3 does not own or modify E1 production code.

Therefore the current-main E2/E3 integration test definition now uses canonical `contracts-v0.1` Candle mappings rather than importing E1's broken public package. This keeps E3 structurally testable without copying E1 implementation logic. Full E1-package -> E2 -> E3 local integration remains blocked until E1/PM/E7 repairs or reconciles that main issue.

## No-look-ahead disposition

The accepted replay boundary is unchanged:

- only finalized closed Candles are accepted;
- at Candle close T, E3 passes E2 only the finalized prefix through T;
- E2 Signal `evaluated_at` must equal the exact replay boundary;
- LONG/SHORT entry signals fill no earlier than the next Candle open;
- opposite-direction exits fill no earlier than the next Candle open;
- a final-bar entry signal cannot create a trade because there is no later fill bar;
- Signal `reference_price` is not used to manufacture a same-bar fill;
- same-candle stop/target ambiguity remains conservative: STOP wins;
- protective OHLC exits do not invent an unknown intrabar timestamp.

The current-main integration test also defines a future-candle poisoning check: future OHLC payload is changed to unreadable objects while evaluating an earlier E2 boundary, and the earlier E2 signal identity/boundary must remain unchanged. E3 unit replay definitions separately verify prefix-only runtime invocation.

## Cost semantics

No cost-model behavior changed in this refresh.

- `FeeModel`: versioned maker/taker bps with separate entry/exit liquidity roles.
- `SlippageModel`: versioned adverse entry/exit bps embedded in simulated fill prices.
- `FixedFundingModel`: explicit deterministic rate, interval, first-event time, and event window.
- gross PnL uses slippage-adjusted simulated fills.
- net PnL = gross PnL - fees - funding; reported slippage cost is not subtracted twice.

These are explicit research assumptions, not E5 sizing/risk authority and not provider execution facts.

## Canonical BacktestResult compatibility

Static/source audit against current `contracts-v0.1` and current-main E6 `validate_backtest_result_contract` found no required E3 serialization change.

E3 `BacktestResult.to_contract()` already emits the required identity/reproducibility fields:

- schema version;
- backtest result ID;
- strategy ID/version/content hash;
- actual E2 runtime version;
- dataset ID/hash/start/end;
- cost-model version;
- created-at timestamp.

It also emits the required core metrics:

- total trades / wins / losses / breakeven;
- gross PnL / net PnL / total fees;
- profit factor;
- expectancy;
- max drawdown;
- max consecutive losses.

Current-main E6 permits `profit_factor=null`. E3's locked edge behavior remains: when aggregate losing PnL is zero, including the case with at least one winning trade, the field is present and serializes as `null`; it is never omitted or emitted as Infinity.

The current-main integration test definition now passes E3 `to_contract()` output to E6's canonical BacktestResult validator and checks required identity/reproducibility/core fields. This is a test definition only; it has not been executed here.

## Reproducibility

Deterministic identity remains based on strategy identity/hash, E2 runtime version, dataset identity/hash/boundaries, cost assumptions, replay engine version, close-at-dataset-end policy, and deterministic replay trades. `created_at` is metadata and is intentionally excluded from deterministic `backtest_result_id`.

Unknown/unsupported shared schema values, unclosed candles, symbol/timeframe mismatches, invalid ordering/overlap, dataset-boundary mismatches, Signal identity/hash/symbol mismatches, unsupported Signal direction, and Signal boundary mismatch fail closed in the existing replay design.

## Test-definition coverage

E3 scope retains definitions for:

- actual current-main E2 runtime consumption;
- deterministic identical replay for identical inputs;
- future-candle isolation / no-look-ahead;
- next-open entry/exit skeleton;
- fee application;
- slippage application;
- funding configuration/application;
- zero/edge metrics, including `profit_factor=null` all-win/no-loss behavior;
- same-candle conservative stop/target handling;
- canonical BacktestResult identity/reproducibility and E6 validator compatibility;
- unsupported schema, unclosed candle, bad dataset boundary, incompatible Signal schema, and Signal-time fail-closed behavior.

## Local-only verification

Executable verification was not performed in this ChatGPT/GitHub environment.

Status: `NOT_RUN`

Exact Product Owner-approved local command from repository root:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/backtest -p "test_*.py" -v
```

Targeted current-main E2 -> E3 definition:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python tests/backtest/test_real_e2_research_skeleton.py -v
```

No GitHub Actions, GitHub CI, hosted runner, GitHub-triggered self-hosted runner, scheduled action, or GitHub project compute was used.

## Validation/release disposition

- executable verification: `NOT_RUN`
- strategy validation decision: `NO DECISION`
- Gate A: `BLOCKED`
- Gate B: `BLOCKED`
- Gate C: `BLOCKED`
- Gate D: `BLOCKED`
- OOS / Walk Forward / Monte Carlo / optimization / regime: `NOT_RUN` / not implemented by this task
- lifecycle promotion: none
- PAPER/SHADOW/LIVE impact: none

The bounded E3 refresh stops here for PM/E7 exact-revision review.
