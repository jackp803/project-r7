# E3 Slice 1 Handoff — Research Skeleton

## Handoff

**From:** E3 Backtest & Quantitative Validation Engineer  
**To:** E7 Integration / Architecture / System QA / Release Engineer  
**Branch:** `agent/e3-backtest-validation`  
**Implementation commits:** `1154692831c43931130760a710651c8ee5efe6f1`, `c454beabb4c5e93b34ed8edd2a1e06fc5f2729be`  
**Date:** 2026-08-20

### 1. Objective

Build the minimum Slice 1 research skeleton against `contracts-v0.1`:

```text
Historical Candle
  -> E2 Strategy Runtime boundary
  -> historical replay
  -> simulated costs/fills
  -> basic metrics
  -> BacktestResult
```

The scope intentionally excludes Monte Carlo, full Walk Forward, optimization, full regime analysis, and lifecycle promotion.

### 2. What changed

E3 added a closed-candle replay skeleton with the following properties:

- requires an `E2RuntimeBinding` containing a runtime object, exact runtime version, and thin invocation adapter;
- does not accept a precomputed Signal stream as a substitute for E2 execution;
- contains no strategy indicator/condition implementation;
- passes E2 only the finalized historical Candle prefix available at each evaluation boundary;
- rejects a Signal whose `evaluated_at` differs from the exact replay boundary;
- schedules new entries and opposite-signal exits no earlier than the next Candle open;
- prevents a final-dataset-bar signal from creating an entry without a future fill bar;
- supports basic LONG/SHORT entry/exit replay with no pyramiding or averaging down;
- supports strategy-provided stop/target/max-hold fields at entry;
- resolves same-candle stop/target ambiguity conservatively in favor of STOP;
- handles stop gaps using the adverse Candle-open reference;
- supports maker/taker fee assumptions with separate entry/exit roles;
- supports adverse fixed-bps entry/exit slippage;
- supports a deterministic fixed-event funding assumption/config;
- produces core `BacktestResult` metrics and reproducibility metadata;
- marks OOS, Walk Forward, Monte Carlo, parameter robustness, and regime analysis as `NOT_RUN`;
- rejects unsupported `StrategyDefinition`, `Candle`, and `Signal` schema versions instead of guessing compatibility.

### 3. Files changed

- `src/backtest/__init__.py`
- `src/backtest/costs.py`
- `src/backtest/metrics.py`
- `src/backtest/replay.py`
- `tests/backtest/test_costs.py`
- `tests/backtest/test_metrics.py`
- `tests/backtest/test_replay.py`
- `docs/backtest/SLICE1_RESEARCH_SKELETON.md`
- `status/E3_SLICE1_HANDOFF.md`

No E7-owned shared contract file was modified.

### 4. Contracts consumed

Contract baseline: `contracts-v0.1`.

Consumed shared semantics:

- `Candle`
- `StrategyDefinition`
- `Signal`
- `BacktestResult`
- UTC / `[open_time, close_time)` Candle semantics
- Decimal financial semantics
- immutable strategy identity/content hash
- exact runtime-version reproducibility
- missing validation stages must be `NOT_RUN`, not PASS

Architecture consumed:

- `docs/adr/ADR-0001-canonical-contract-first-architecture.md`
- one E2 Strategy Runtime semantic implementation across research/paper/live-compatible callers
- E3 may not reimplement strategy semantics
- GitHub execution/CI prohibition

### 5. Contracts produced or changed

`NONE`.

E3 emits a `BacktestResult`-compatible mapping under the existing baseline and does not request a shared contract change in this slice.

Review note for E7: when no losing trade exists, Slice 1 serializes mathematically undefined `profit_factor` as `null`. This is not a baseline contract change, but E7 should confirm the desired edge-case representation before a future STABLE contract.

### 6. Strategy / runtime / dataset evidence

#### Authoritative strategy validation

**Strategy ID/version:** `NONE — no authoritative E2 strategy was executed.`

A synthetic test fixture uses:

- strategy ID: `baseline-test`
- strategy version: `1.0.0`
- content hash: `sha256:baseline-test`
- runtime label: `e2-runtime-test-double-v1`

These identifiers exist only in test definitions and are **not validation evidence**.

#### E2 runtime integration status

At handoff time, no `agent/e2-strategy-engine` branch, E2 Slice 1 PR, or E2 runtime implementation commit was visible in the repository through the GitHub integration.

Therefore:

```text
Concrete E2 Strategy Runtime consumption: BLOCKED
Reason: E2 concrete public runtime/API is not yet available to E3 without guessing.
```

The E3 engine structurally requires the runtime binding, but a real E2 integration test must still prove that the binding invokes E2's actual runtime implementation.

#### Historical dataset

**Real E1 dataset:** `NOT_RUN / not consumed`.

Synthetic test fixture metadata only:

- symbol: `BTC_USDT_PERP`
- timeframe: `15m`
- example 4-Candle fixture boundary: `2026-01-01T00:00:00Z` to `2026-01-01T01:00:00Z`
- fixture dataset ID: `fixture-btc-15m-v1`
- fixture hash label: `sha256:fixture-btc-15m-v1`

The fixture hash is a test label, not an E1 historical dataset provenance hash and must not be presented as such.

### 7. Fee / slippage / funding assumptions

The engine requires explicit versioned cost assumptions for each replay.

Supported configuration:

- maker fee bps;
- taker fee bps;
- separate entry/exit liquidity roles;
- adverse entry slippage bps;
- adverse exit slippage bps;
- funding `rate_per_event`;
- funding event interval;
- explicit first funding-event timestamp;
- fixed research replay quantity.

Semantics:

- fees apply to simulated fill notional;
- slippage is embedded in simulated fill price and separately reported for audit, but is not subtracted from net PnL twice;
- positive fixed funding charges LONG and credits SHORT;
- funding event window is `opened_at <= event < closed_at`;
- Slice 1 funding notional approximation is entry fill price x fixed replay quantity.

Synthetic zero-cost fixture defaults and a 10-bps stress fixture exist only as test definitions. They are not exchange fee/funding truth and are not recommended production assumptions.

### 8. Local verification

**GitHub Actions / CI was not used. No project test or backtest was executed on GitHub infrastructure.**

#### E3 unit/replay test definitions

```text
Result: NOT_RUN
Required local command: python -m unittest discover -s tests/backtest -p "test_*.py" -v
Windows equivalent: py -3 -m unittest discover -s tests/backtest -p "test_*.py" -v
Reason: the current ChatGPT GitHub environment is not the Product Owner's local execution environment; project verification is local-only by policy.
```

Defined coverage includes:

- entry/exit timing skeleton;
- next-open fill timing after a closed-candle signal;
- final-bar no-entry protection;
- unclosed Candle rejection;
- incompatible schema rejection;
- no-future-Candle runtime prefix trap;
- Signal boundary timestamp mismatch rejection;
- same-candle stop/target conservative resolution;
- maker/taker fees;
- adverse slippage;
- funding event accounting;
- dataset boundary mismatch rejection;
- known-sequence basic metrics;
- empty metrics edge case.

#### Concrete E2 integration verification

```text
Result: BLOCKED / NOT_RUN
Reason: concrete E2 runtime implementation/API is not yet available in repository state visible to E3.
Required next local verification: an integration test that passes the real E2 runtime object into E2RuntimeBinding and proves E3 invokes it using only the exact closed-Candle prefix.
```

E7 should require local evidence for:

```text
same StrategyDefinition
+ same exact Candle/input boundary
+ same E2 runtime version
= same deterministic Signal
```

and then prove E3 replay consumes that same runtime rather than a private strategy implementation.

### 9. Metrics

Implemented metric capability:

- total trades;
- wins;
- losses;
- breakeven;
- win rate;
- average win/loss;
- gross PnL;
- net PnL;
- total fees;
- total slippage cost;
- total funding cost;
- profit factor;
- expectancy;
- max absolute drawdown on cumulative net trade PnL;
- max consecutive losses.

**Measured strategy metrics:** `NONE / NOT_RUN`.

No numeric test expectation is reported here as an observed backtest result because no local test/backtest was executed.

### 10. OOS / contamination / validation decision

- OOS status: `NOT_RUN`
- Walk Forward: `NOT_RUN`
- Monte Carlo: `NOT_RUN`
- parameter robustness: `NOT_RUN`
- regime analysis: `NOT_RUN`
- real historical dataset contamination status: `NOT_APPLICABLE — no real validation/OOS dataset was consumed`
- synthetic test fixtures: test-only, never described as untouched OOS evidence

**Strategy PASS/FAIL:** `NO DECISION — no strategy validation was executed.`

**E3 Slice 1 construction status:** `READY_FOR_E7_CODE/CONTRACT REVIEW`, not a validation PASS.

**Research Skeleton integration status:** `BLOCKED` pending concrete E2 runtime availability and local verification.

**Gate A / RESEARCH_READY:** E3 does **not** recommend PASS from this handoff alone.

### 11. Rejection / blocking reasons

No strategy is rejected because no authoritative strategy was evaluated.

Current integration blocker:

1. concrete E2 Strategy Runtime implementation/API is unavailable to E3 in visible repository state, so actual same-runtime consumption cannot yet be proven;
2. all E3 tests are `NOT_RUN` until executed locally;
3. no real E1 historical dataset/hash has been replayed by E3.

### 12. Known limitations

- exactly one strategy-required timeframe per Slice 1 replay;
- fixed replay quantity is a research assumption, not E5 position-sizing semantics;
- funding is a deterministic fixed-event model, not historical exchange funding records;
- strategy stop/target/max-hold values are captured from the entry Signal only; dynamic protective-level changes are not implemented;
- OHLC cannot reveal exact intrabar stop/target event time; Slice 1 records Candle close time for protective exits to avoid fabricating an intrabar timestamp and to remain conservative for funding duration;
- no partial-fill model yet;
- no order-book/liquidity model yet;
- no Sharpe/Sortino yet;
- no R-multiple distribution yet;
- no holding-time distribution yet;
- no long/short breakdown report yet;
- no OOS, Walk Forward, Monte Carlo, robustness, optimization, or regime engine yet;
- max drawdown is currently absolute drawdown of cumulative net closed-trade PnL, not a mark-to-market equity-curve drawdown;
- no real E1 dataset replay has run;
- concrete E2 runtime adapter is intentionally not guessed.

### 13. Dependencies / blockers

- **E2:** publish Slice 1 Strategy Runtime implementation, runtime version, public call shape, baseline StrategyDefinition, and handoff.
- **E1:** publish/merge deterministic historical Candle path plus real dataset reference/hash for integration replay.
- **E7:** review E3 replay assumptions against contracts-v0.1 and arbitrate any cross-module semantic mismatch.

### 14. Required next action

**E7 should:**

1. review `agent/e3-backtest-validation` for Slice 1 contract compliance;
2. keep concrete Research Skeleton integration BLOCKED until E2's actual runtime is available;
3. once E2 is available, require E3/E7 integration to bind the real E2 runtime rather than add strategy code inside E3;
4. use an E1-provided deterministic Candle fixture/dataset reference;
5. execute the relevant E1/E2/E3 unit and integration tests locally only;
6. record actual dataset hash, strategy identity, runtime version, cost assumptions, metrics, and local results before considering Gate A.

### 15. Security / secrets

Confirmed for E3 changes:

- no real API key, API secret, token, credential, password, private key, or live `.env` value was added;
- test fixtures are synthetic and sanitized;
- E3 Slice 1 requires no private exchange credentials.

### 16. GitHub compute policy

Confirmed:

- no GitHub Actions workflow was created or used;
- no GitHub-hosted runner was used;
- no GitHub-triggered self-hosted runner was used;
- no backtest, unit test, integration test, bug reproduction, performance test, or strategy job was executed through GitHub infrastructure;
- GitHub was used only for source/history collaboration.

### 17. Live-trading impact

`NONE`.

E3 Slice 1 does not submit orders, manage credentials, approve risk, alter position sizing, promote lifecycle state, or enable LIVE.

### 18. Codex bug ticket

`NONE`.

No reproducible implementation defect has been established through approved local execution, so Codex was not invoked.
