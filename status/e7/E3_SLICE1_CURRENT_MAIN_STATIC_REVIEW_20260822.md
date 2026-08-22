# E7 Static / Integration Review — E3 Slice 1 Current-Main Reconciliation

- Task: `E7-20260822-012`
- Date: `2026-08-22`
- Review branch: `agent/e7-e3-slice1-current-main-review-20260822`
- Review target: PR `#22 backtest: reconcile Slice 1 replay with corrected current main`
- Reviewed PR head: `dbce39cec5d5104e0fe79aca4e3be0e8aef459ec`
- Preserved E3 production pin: `54d40ae96e241f40367016e26b7bd5d03890e629`
- Post-E1 reconciliation merge: `aee813855759cd63548d452a93de26fc208afa20`
- Reconciliation test revision: `185185fbb403b3622c96a218717d67a2eb41a684`
- Review-time `main`: `801c81ff80b42cfe2e1424567ea5ef41be7e9270`
- Executable verification: `NOT_RUN`
- Backtests/tests/import probes: `NOT_RUN`
- GitHub compute: `NOT_USED`

## Executive disposition

PR #22 passes the requested exact-revision static/integration review.

```text
E1 import-integrity blocker                 CLEARED / PASS STATIC
Actual current E2 runtime consumption       PASS STATIC
Closed-candle / no-look-ahead boundary      PASS STATIC
Next-open entry/opposite-exit timing        PASS STATIC
Protective intrabar ambiguity policy        PASS STATIC / CONSERVATIVE
Fees / slippage / funding source design     PASS STATIC
Metrics arithmetic / edge behavior          PASS STATIC
Deterministic reproducibility identity      PASS STATIC
Canonical BacktestResult / E6 validator     PASS STATIC
Research-only / no promotion authority      PASS STATIC
Scope / current-main synchronization         PASS STATIC
PR #22 merge recommendation                  PM MAY MERGE PR #22
```

This is static/source acceptance only. It is not executable evidence, does not establish Gate A PASS, does not create a ValidationDecision, and does not authorize Registry promotion, PAPER, SHADOW, LIVE, provider activity, or later E3 validation stages.

## 1. E1 blocker disposition

**Disposition: `CLEARED / PASS STATIC`**

Current `main` exposes the supported E1 package surface:

```python
from market_data import CONTRACT_SCHEMA_VERSION, Candle
```

The exact corrected E1 blobs match the task inputs:

```text
src/market_data/candle.py      5605830b4da4fbe10e94cff72794a495db9ebf6e
src/market_data/errors.py      fb9cd216b83cd595304d23a5cec46fd9a2091894
src/market_data/timeframes.py  ac08d88dd327719b01babba098d78da0f34ab5bf
```

`src/market_data/__init__.py` exports `Candle` and `CONTRACT_SCHEMA_VERSION` from the supported package path.

`tests/backtest/test_real_e2_research_skeleton.py` now imports and constructs actual E1 `Candle` objects and derives the synthetic dataset fingerprint from `Candle.to_interchange_dict()` output. The prior cross-role plain-mapping workaround is no longer used for the real E1/E2/E3 integration definition.

E3 production replay still performs consumer-side fail-closed contract checks on incoming candle fields. No competing E1 Candle class, timeframe module, or E1 error implementation is introduced under `src/backtest/**`.

## 2. Real E2 runtime consumption

**Disposition: `PASS STATIC`**

`src/backtest/e2_runtime.py` is a thin adapter. It imports the current public E2 package:

```python
from strategy import RUNTIME_VERSION, StrategyRuntime, parse_strategy_definition
```

The adapter constructs the actual `StrategyRuntime`, verifies `runtime.version == RUNTIME_VERSION`, and for every replay evaluation performs:

```text
parse_strategy_definition(strategy_definition)
-> StrategyRuntime.evaluate(parsed_strategy, closed_history, evaluated_at)
```

Current `src/strategy/__init__.py` publicly exports the same runtime/parser symbols. Current E2 `runtime.py` keeps `parse_strategy_definition` as the authoritative StrategyDefinition/DSL validation boundary and `StrategyRuntime.evaluate` as the deterministic decision runtime.

No E3 code under `src/backtest/**` implements SMA, E2 DSL operators, strategy rule interpretation, signal decision logic, TradeIntent construction, or another strategy runtime.

Unavailable E2 package import fails as `E2RuntimeUnavailableError`; runtime-version mismatch fails as `RuntimeContractError`; E2 parser/runtime exceptions are not converted into optimistic research output.

## 3. Historical no-look-ahead and timing

**Disposition: `PASS STATIC`**

The replay source enforces the following before/during runtime evaluation:

- supported `contracts-v0.1` Candle schema;
- `is_closed is True` only;
- UTC timestamps and `open_time < close_time`;
- finite decimal-compatible OHLCV and non-negative volume;
- symbol/timeframe match to StrategyDefinition;
- duplicate/out-of-order `open_time` rejection;
- overlapping interval rejection;
- dataset start/end must exactly match the consumed first open / final close.

At each candle-close boundary E3 passes only:

```python
frames[: index + 1]
```

to E2, and explicitly rejects any internal prefix whose close exceeds the current boundary.

E2 itself also excludes future/provisional candles before reading their OHLCV. E3 does not rely on that behavior for correctness because the replay source already passes a closed historical prefix.

The returned Signal must bind exactly to:

- strategy id;
- strategy version;
- strategy content hash;
- symbol;
- supported Signal schema;
- exact `evaluated_at == current candle.close_time`;
- `LONG | SHORT | NO_TRADE` direction.

### Entry / opposite-signal exit timing

A LONG/SHORT signal at close creates only `_PendingEntry`. The position is opened at the next loop iteration's `frame.open` / `frame.open_time`.

An opposite-direction signal creates only `pending_exit_reason`. The position is closed at the next loop iteration's `frame.open` / `frame.open_time`.

Therefore signal decisions are not filled at the same candle close that produced them.

A final-bar entry signal remains pending after the loop and cannot create a nonexistent future fill. If an already-open position is configured for dataset-end closure, that separate explicit replay assumption closes the existing position at the final dataset close; it does not manufacture a next-open fill for the final signal.

### Protective intrabar ambiguity

For same-candle stop/target ambiguity, stop is checked before target for both LONG and SHORT. This is conservative rather than hindsight-optimistic.

For an adverse gap through a stop, the reference is the bar open when the open is already beyond the stop level, avoiding a fictitious better stop fill. A favorable gap through a target is not upgraded to a more favorable open price; the configured target is retained.

OHLC cannot prove the exact intrabar event timestamp. Protective exits therefore record `close_time`, explicitly avoiding invented intrabar sequencing; this is conservative for the deterministic funding-duration assumption.

## 4. Cost and replay arithmetic

**Disposition: `PASS STATIC`**

### Fee model

`FeeModel` is explicitly versioned, keeps Decimal semantics, distinguishes entry/exit maker/taker roles, and applies basis-point fees to fill notional.

### Slippage model

`SlippageModel` is explicitly versioned and adverse by side:

```text
BUY  -> reference * (1 + bps)
SELL -> reference * (1 - bps)
```

Entry and exit slippage are independently configurable. `slippage_cost` is retained as reference-vs-fill decomposition metadata.

### Funding model

`FixedFundingModel` is explicitly versioned and deterministic. Assumptions include:

- `rate_per_event`;
- `interval_seconds`;
- `first_event_at`;
- notional basis;
- event-window convention `opened_at <= event < closed_at`.

Positive rate charges LONG and credits SHORT; negative rate reverses that sign.

### PnL coherence

Replay gross PnL is calculated from actual replay fill prices, so adverse slippage is already embedded in fill-to-fill gross PnL. Net PnL is then:

```text
net_pnl = gross_pnl - total_fees - funding_cost
```

`total_slippage_cost` is reported separately as cost decomposition and is not subtracted a second time.

`fixed_quantity` is an explicit research/replay assumption included in cost/reproducibility metadata. It provides no E5 risk sizing, leverage, martingale, broker, or live execution authority.

## 5. Metrics

**Disposition: `PASS STATIC`**

`calculate_metrics()` deterministically derives:

- total trades;
- wins/losses/breakeven;
- win rate;
- average win/loss;
- gross PnL;
- net PnL;
- total fees;
- total slippage cost;
- total funding cost;
- expectancy;
- profit factor;
- max drawdown;
- max consecutive losses.

All financial arithmetic uses `Decimal` semantics.

Profit factor is based on positive/negative net trade PnL. If aggregate losing PnL is zero, `profit_factor` is `None`; serialization retains the field as JSON `null`, including the winner-with-no-loser edge. No Infinity, NaN, or noncanonical string sentinel is emitted.

Max drawdown is computed over the deterministic cumulative net-PnL equity sequence; consecutive-loss state resets on non-negative trades.

## 6. Reproducibility

**Disposition: `PASS STATIC`**

Backtest identity includes the deterministic research inputs/facts:

- replay engine version;
- strategy id/version/content hash;
- actual E2 runtime version;
- dataset id/hash/start/end;
- full cost assumptions;
- fixed replay quantity;
- dataset-end closure setting;
- deterministic trade fingerprints.

Each trade fingerprint includes signal identity, direction, open/close timestamps, quantity, fill/reference prices, PnL/costs, and exit reason.

`run_created_at` / serialized `created_at` is observational metadata and is intentionally excluded from the result identity. Thus otherwise identical replay inputs/trades are designed to retain the same `backtest_result_id` even when observational creation time differs.

The real E1/E2/E3 integration test definition runs the same bounded inputs twice and asserts identical result identity and metrics.

## 7. Canonical `BacktestResult` / E6 validator

**Disposition: `PASS STATIC`**

Current merged E6 `validate_backtest_result_contract` blob remains:

```text
954d21c021c0885554ee650acced17610d958a0e
```

E3 `BacktestResult.to_contract()` emits every E6-required field.

Identity/reproducibility:

```text
schema_version
backtest_result_id
strategy_id
strategy_version
strategy_content_hash
runtime_version
dataset_id
dataset_hash
dataset_start
dataset_end
cost_model_version
created_at
```

Core metrics:

```text
total_trades
wins
losses
breakeven
gross_pnl
net_pnl
total_fees
profit_factor
expectancy
max_drawdown
max_consecutive_losses
```

Timestamp fields serialize as RFC3339 UTC ending in `Z`. Financial metric interchange fields serialize as base-10 decimal strings. Integer metrics remain non-negative integers.

The E6 validator explicitly permits `profit_factor=None`; E3 produces exactly that shape when losing PnL is zero.

E3 additionally emits replay/reproducibility/validation-stage metadata. Extra fields do not weaken or replace the canonical required fields.

`tests/backtest/test_real_e2_research_skeleton.py` statically feeds E3's serialized contract directly into E6 `validate_backtest_result_contract` and checks the returned identity view.

## 8. Research-only authority boundary

**Disposition: `PASS STATIC`**

PR #22 adds no ValidationDecision policy/engine and performs no Registry lifecycle promotion.

`BacktestResult` remains research evidence only. The backtest package exports replay/cost/metrics/result primitives, not E6 lifecycle or ValidationDecision authority.

No OOS, Walk Forward, Monte Carlo, optimization, parameter robustness engine, regime engine, PAPER, SHADOW, LIVE, broker/provider, risk sizing, or execution implementation is added.

Merged E6 durable promotion requirements remain untouched: BacktestResult alone cannot authorize CANDIDATE; a separately valid bound E3 ValidationDecision with the required durable local-execution evidence is still required by E6.

## 9. Test-definition review

**Disposition: `PASS STATIC / DEFINITIONS ONLY`**

Reviewed deterministic definitions cover:

- actual supported E1 `Candle` construction and interchange serialization;
- actual current E2 `StrategyRuntime` binding;
- actual E2 parser failure propagation;
- future-candle isolation at an earlier E2 boundary;
- deterministic E1/E2/E3 replay identity;
- direct current E6 BacktestResult contract validation;
- closed historical prefix lengths;
- next-open entry and opposite-signal exit;
- final-bar signal no-fill;
- unclosed Candle rejection;
- incompatible strategy/candle/signal schema rejection;
- exact Signal `evaluated_at` boundary;
- same-bar stop/target ambiguity -> STOP;
- fee/slippage/funding impact;
- dataset descriptor boundary checks;
- maker/taker fees;
- adverse BUY/SELL slippage;
- deterministic funding event count/sign;
- known-sequence metrics;
- no-loss profit-factor `null` edge;
- empty-trade metric edge.

Synthetic runtime/PASS fixtures in tests are test data only. They are not represented here as project executable evidence.

No test was executed in GitHub.

## 10. Scope and synchronization

**Disposition: `PASS STATIC`**

PR #22 current changed-file set is limited to:

```text
coordination/E3/STATUS.md
docs/backtest/SLICE1_RESEARCH_SKELETON.md
src/backtest/__init__.py
src/backtest/costs.py
src/backtest/e2_runtime.py
src/backtest/metrics.py
src/backtest/replay.py
status/E3_SLICE1_HANDOFF.md
tests/backtest/test_costs.py
tests/backtest/test_metrics.py
tests/backtest/test_real_e2_research_skeleton.py
tests/backtest/test_replay.py
```

No `contracts/**`, E1/E2/E4/E5/E6 production, Registry/storage implementation, workflow/CI, provider/credential/secret, or later-slice implementation is part of the PR diff against current main.

The production pin remains exact for E3 source. Confirmed unchanged blob identities between `54d40ae...` and the reviewed PR head include:

```text
src/backtest/replay.py       bf2b013a1cacd7af93f71c977320dda7d3382375
src/backtest/e2_runtime.py   c603233b53217118f6979f9372477de65101938a
src/backtest/costs.py        7ba0f38e21340fc64bdaa830a750a237af4e4991
src/backtest/metrics.py      4ad18c1066d3726b1338596a15d373a28f955f69
```

The E1 files seen after the E3 production pin came from the non-destructive current-main reconciliation, not an E3 production rewrite.

At final review:

```text
latest main = 801c81ff80b42cfe2e1424567ea5ef41be7e9270
PR #22 head = dbce39cec5d5104e0fe79aca4e3be0e8aef459ec
E3 branch vs latest main = ahead 14 / behind 2
merge base = 47c7f3c24300b9ea21a8d50eba5be13884c88a7a
latest-main-only delta = coordination/E3/TASK.md + coordination/E7/TASK.md
meaningful production/shared-contract drift = NONE
GitHub PR mergeable = TRUE
```

Coordination-only TASK drift after the reviewed reconciliation is not a resynchronization blocker under this TASK.

## 11. Documentation / verification policy

E3 docs/handoff accurately state:

- static/source readiness only;
- executable verification `NOT_RUN`;
- no import probe, test, replay, backtest, or metric execution occurred;
- GitHub compute/CI remains forbidden;
- exact local-only commands are recorded.

Recorded local-only commands:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/backtest -p "test_*.py" -v
python tests/backtest/test_real_e2_research_skeleton.py -v
```

These commands were not executed in this E7 task.

## Final recommendation

**PM MAY MERGE PR #22**.

This recommendation is limited to static/source integration acceptance of the bounded Slice 1 E3 research skeleton.

```text
Executable verification: NOT_RUN
Backtest execution: NOT_RUN
ValidationDecision: NOT CREATED / NOT AUTHORIZED BY THIS REVIEW
Registry promotion: NONE
Gate A: BLOCKED / UNCHANGED
Gate B: BLOCKED / UNCHANGED
Gate C: BLOCKED / UNCHANGED
Gate D: BLOCKED / UNCHANGED
PAPER / SHADOW / LIVE: NO ADVANCEMENT
Provider requests: NOT_SENT
GitHub compute: NOT_USED
Codex ticket: NONE
```

E7 stops after this review and waits for PM. No PR merge, executable verification, ValidationDecision implementation, Registry promotion, or next E3 stage is started automatically.
