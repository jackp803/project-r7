# E3 Slice 1 Handoff — Research Skeleton

## Handoff

**From:** E3 Backtest & Quantitative Validation Engineer  
**To:** E7 Integration / Architecture / System QA / Release Engineer  
**Branch:** `agent/e3-backtest-validation`  
**Date:** 2026-08-20  
**Contract baseline:** `contracts-v0.1`

Implementation history includes:

- `1154692831c43931130760a710651c8ee5efe6f1` — initial historical replay / costs / metrics skeleton
- `c454beabb4c5e93b34ed8edd2a1e06fc5f2729be` — fail-closed contracts-v0.1 consumer boundary
- `da9fa922f7c6292d4dd801033e70cfe6943249c2` — concrete binding to real E2 Strategy Runtime + E1/E2/E3 integration test definition
- later branch commits update this documentation/handoff only

### 1. Objective

Deliver the minimum Slice 1 Research Skeleton:

```text
E1 Historical Candle
  -> E2 Strategy Runtime
  -> E3 historical replay
  -> fees / slippage / funding assumptions
  -> basic metrics
  -> BacktestResult
```

Monte Carlo, full Walk Forward, optimization, full regime analysis, and lifecycle promotion are intentionally deferred.

### 2. What changed

E3 added:

- `HistoricalReplayEngine` using closed-candle historical prefixes;
- `E2RuntimeBinding` dependency boundary;
- concrete `project_e2_runtime_binding()` that imports and calls E2's actual public Slice 1 API:
  - `strategy.parse_strategy_definition`
  - `strategy.StrategyRuntime`
  - `StrategyRuntime.evaluate`;
- no SMA, DSL rule, indicator, GT/LT/AND, or private strategy implementation inside E3;
- E1/E2/E3 cross-role test definition using actual `market_data.Candle` and actual `strategy.StrategyRuntime`;
- next-open entry/exit timing after closed-candle Signals;
- final-bar no-entry protection;
- conservative same-candle TP/SL handling where STOP wins if sequence is unknown;
- stop-gap adverse-open handling;
- entry-Signal stop/target/max-hold replay skeleton;
- maker/taker fee model with separate entry/exit liquidity roles;
- adverse fixed-bps slippage model;
- deterministic fixed-event funding assumption model;
- basic trade/result metrics;
- deterministic reproducibility identity and metadata;
- fail-closed StrategyDefinition/Candle/Signal schema checks at the E3 boundary;
- explicit `NOT_RUN` markers for validation stages not implemented in Slice 1.

E3 did not modify E1, E2, E5, E6, E7-owned shared contracts, strategy semantics, risk semantics, execution code, or lifecycle state.

### 3. Files changed

E3-owned files:

- `src/backtest/__init__.py`
- `src/backtest/costs.py`
- `src/backtest/e2_runtime.py`
- `src/backtest/metrics.py`
- `src/backtest/replay.py`
- `tests/backtest/test_costs.py`
- `tests/backtest/test_metrics.py`
- `tests/backtest/test_replay.py`
- `tests/backtest/test_real_e2_research_skeleton.py`
- `docs/backtest/SLICE1_RESEARCH_SKELETON.md`
- `status/E3_SLICE1_HANDOFF.md`

### 4. Contracts consumed

- `contracts-v0.1`
- `Candle`
- `StrategyDefinition`
- `Signal`
- `BacktestResult`
- ADR-0001 canonical contract-first / one-runtime architecture

Key consumed semantics:

- UTC;
- Candle `[open_time, close_time)`;
- finalized closed Candle only;
- Decimal financial semantics;
- strategy version/content hash immutability;
- same exact input boundary + same strategy + same E2 runtime must produce deterministic Signal;
- E3 must call E2 runtime rather than reimplement strategy;
- missing validation evidence is `NOT_RUN`, never implicit PASS.

### 5. Contracts produced or changed

`NONE`.

E3 produces a `BacktestResult`-compatible mapping under the existing baseline. No shared contract file was changed.

E7 review note: if there are no losing trades, E3 currently serializes mathematically undefined `profit_factor` as `null`. Confirm this edge representation before a future STABLE contract.

### 6. Concrete E2 runtime consumption

E2 Slice 1 handoff publishes the required call path:

```python
from strategy import StrategyRuntime, parse_strategy_definition

strategy = parse_strategy_definition(strategy_payload)
runtime = StrategyRuntime()
signal = runtime.evaluate(strategy, canonical_candle_sequence, replay_boundary_utc)
```

E3 now calls exactly this path through `project_e2_runtime_binding()`.

The adapter contains no strategy semantics. It parses the StrategyDefinition with E2 and invokes the actual E2 runtime object for each replay boundary.

The cross-role test definition asserts:

- binding runtime is an actual E2 `StrategyRuntime` instance;
- `BacktestResult.runtime_version == E2 RUNTIME_VERSION` (`0.1.0` in the current E2 Slice 1 branch);
- E2 Signal strategy content hash matches the StrategyDefinition;
- E3 invokes E2 once per exact closed-Candle boundary;
- repeated identical E1 Candle + StrategyDefinition + E2 runtime inputs produce identical E3 result identity/metrics.

### 7. Strategy ID / version

No production or promotion-candidate strategy was validated.

The concrete cross-role integration test definition uses E2's baseline SMA-cross fixture identity:

- Strategy ID: `baseline-sma-cross`
- Strategy version: `1.0.0`
- runtime family/version: E2 exported `RUNTIME_FAMILY` / `RUNTIME_VERSION` (`0.1.0` currently)
- content hash: computed by E2 `compute_content_hash(...)` from the exact fixture StrategyDefinition

Because the integration test has not been executed locally, the computed content-hash value is not reported as observed evidence here.

This fixture is integration evidence only; it is not a strategy validation PASS.

### 8. Dataset boundaries / hash

No real Pionex historical validation dataset was replayed by E3 in this GPT session.

The concrete E1/E2/E3 synthetic integration fixture is defined as:

- dataset ID: `e1-e2-e3-synthetic-btc-1h-v1`
- symbol: `BTC_USDT_PERP`
- timeframe: `1h`
- boundary: `2026-08-20T00:00:00Z` to `2026-08-20T06:00:00Z`
- source: `e1-e3-integration-fixture`
- dataset hash: deterministic SHA-256 over the exact E1 Candle interchange payload, computed by the local test definition

Observed dataset hash: `NOT_RUN`.

Do not confuse this synthetic fixture with E1 real historical Pionex provenance.

### 9. Fee / slippage / funding assumptions

Supported per-run configuration:

- maker fee bps;
- taker fee bps;
- entry/exit liquidity roles;
- adverse entry slippage bps;
- adverse exit slippage bps;
- funding rate per event;
- funding interval;
- first funding-event timestamp;
- fixed research replay quantity.

Funding semantics in Slice 1:

- positive rate charges LONG and credits SHORT;
- event window `opened_at <= event < closed_at`;
- notional approximation = entry fill price x fixed replay quantity.

The real E1/E2/E3 integration test uses deliberately neutral integration assumptions:

- fixed quantity: `1`
- maker fee: `0 bps`
- taker fee: `0 bps`
- entry slippage: `0 bps`
- exit slippage: `0 bps`
- funding rate: `0`

These values isolate semantic integration and are **not exchange-cost assumptions for strategy validation**.

Separate E3 test definitions cover non-zero fee/slippage/funding behavior.

### 10. Tests / local verification

**No GitHub Actions, GitHub CI, hosted runner, or GitHub-triggered runner was used. No project test/backtest was executed on GitHub infrastructure.**

Current execution result for all commands below: `NOT_RUN`.

Reason: this ChatGPT GitHub environment is not the Product Owner-approved local execution environment.

#### E3-only cost/replay/metric tests

```powershell
python -m unittest discover -s tests/backtest -p "test_costs.py" -v
python -m unittest discover -s tests/backtest -p "test_metrics.py" -v
python -m unittest discover -s tests/backtest -p "test_replay.py" -v
```

#### Full E1 -> E2 -> E3 Research Skeleton

Run from an E7 local integration checkout containing the reviewed E1, E2, and E3 Slice 1 revisions:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python tests/backtest/test_real_e2_research_skeleton.py -v
```

This test definition directly consumes actual E1 `Candle` and actual E2 `StrategyRuntime`; it does not use an E3 strategy test double.

Required acceptance:

```text
same StrategyDefinition
+ same exact closed Candle/input boundary
+ same E2 runtime version
= deterministic Signal / deterministic replay result
```

No PASS is claimed until these commands execute locally.

### 11. Test-definition coverage

Defined tests cover:

- real E1 Candle -> real E2 Runtime -> E3 replay boundary;
- actual E2 runtime object binding;
- deterministic repeatability;
- closed-Candle prefix/no-look-ahead trap;
- next-open entry timing;
- opposite-signal next-open exit timing;
- final-bar signal cannot receive an impossible future fill;
- unclosed Candle rejection;
- unsupported schema rejection;
- Signal evaluated-at mismatch rejection;
- same-candle SL/TP conservative STOP resolution;
- maker/taker fee calculation;
- adverse slippage;
- funding event accounting;
- dataset-boundary mismatch rejection;
- known-sequence metrics;
- empty/no-trade metric edge case.

### 12. Metrics

Implemented capability:

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

Observed strategy metrics: `NONE / NOT_RUN`.

The integration test contains expected fixture assertions, but expectations are not reported as observed results before local execution.

### 13. OOS / contamination status

- OOS: `NOT_RUN`
- Walk Forward: `NOT_RUN`
- Monte Carlo: `NOT_RUN`
- parameter robustness: `NOT_RUN`
- regime analysis: `NOT_RUN`
- real dataset contamination: `NOT_APPLICABLE — no real OOS/validation dataset was consumed by E3`
- synthetic integration fixture: test-only and never labeled untouched OOS

### 14. PASS / FAIL decision

**Strategy validation decision:** `NO DECISION`.

No authoritative strategy validation run occurred, therefore E3 issues neither strategy PASS nor strategy FAIL.

**E3 Slice 1 source construction:** `READY_FOR_E7 INTEGRATION REVIEW`.

**Executable evidence:** `NOT_RUN`.

**Gate A / RESEARCH_READY recommendation:** `DO NOT PASS YET`.

Gate A remains blocked until E7 assembles the E1/E2/E3 revisions and obtains local unit/integration evidence.

### 15. Rejection / blocking reasons

No strategy rejection reason exists because no strategy validation was executed.

Current evidence blockers:

1. E1/E2/E3 branches have not yet been assembled and executed in an approved local integration checkout;
2. E3 unit/replay tests remain `NOT_RUN`;
3. cross-role real E1/E2/E3 test remains `NOT_RUN`;
4. no real Pionex historical dataset/hash/cost assumption set has been validated by E3.

### 16. Cross-module integration finding for E7

E1 executable Candle explicitly uses:

```text
schema_version = "contracts-v0.1"
```

E2's current local strategy test fixtures use:

```text
schema_version = "0.1"
```

while E2 runtime itself accepts and preserves the StrategyDefinition schema string rather than enforcing one exact value.

E3's concrete integration test uses E1's exported `CONTRACT_SCHEMA_VERSION` (`contracts-v0.1`) for both StrategyDefinition and Candle, and expects E2 Signal to preserve it.

E3 does not change E2 tests or shared schema semantics. E7 should decide whether the E2 fixture value is merely a test inconsistency that should be aligned before merge.

### 17. Known limitations

- one strategy-required timeframe per replay;
- fixed replay quantity is research configuration, not E5 sizing;
- fixed-event funding assumption, not historical exchange funding records;
- stop/target/max-hold captured from entry Signal only; dynamic protective-level changes not implemented;
- OHLC intrabar stop/target event time unknown; protective exit records Candle close time rather than fabricating an intrabar timestamp;
- no partial-fill model;
- no order-book/liquidity model;
- no Sharpe/Sortino;
- no R-multiple distribution;
- no holding-time distribution;
- no long/short separated report;
- no mark-to-market equity-curve drawdown; current drawdown is absolute drawdown of cumulative net closed-trade PnL;
- no OOS / Walk Forward / Monte Carlo / robustness / optimization / full regime engine;
- no real Pionex dataset replay has been executed.

### 18. Dependencies / next action

**E7 should:**

1. review E1 `agent/e1-market-data`, E2 `agent/e2-strategy-engine`, and E3 `agent/e3-backtest-validation` against `contracts-v0.1`;
2. resolve/accept the schema-version fixture inconsistency noted above;
3. assemble the reviewed revisions into a local integration checkout without rewriting E2 strategy logic;
4. run E1, E2, E3 unit tests locally;
5. run `tests/backtest/test_real_e2_research_skeleton.py` locally;
6. record actual command/environment/results;
7. only after executable parity succeeds, use a real E1 historical dataset reference/hash and explicit realistic cost assumptions for the first actual strategy validation run;
8. keep Gate A blocked if any required evidence is `FAIL`, `BLOCKED`, or `NOT_RUN`.

### 19. Security / secrets

Confirmed for E3 changes:

- no real API key, API secret, token, credential, password, private key, or live `.env` value was added;
- fixtures are synthetic and sanitized;
- no private exchange credentials are required.

### 20. GitHub compute policy

Confirmed:

- no GitHub Actions workflow was created or used;
- no GitHub-hosted runner was used;
- no GitHub-triggered self-hosted runner was used;
- no unit/integration/backtest/bug-reproduction/performance/strategy workload ran on GitHub infrastructure;
- GitHub was used only for source/history collaboration.

### 21. Live-trading impact

`NONE`.

E3 Slice 1 cannot place orders, approve risk, alter position sizing/leverage, modify live protective behavior, change lifecycle promotion state, or enable LIVE.

### 22. Codex bug ticket

`NONE`.

No reproducible implementation defect has been established by approved local execution, so Codex was not invoked.
