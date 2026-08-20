# Handoff

**From:** E2 / Strategy Engine Engineer  
**To:** E7 / Integration Engineer  
**Branch:** `agent/e2-strategy-engine`  
**Commit(s):** branch HEAD containing this handoff  
**Date:** 2026-08-20

### 1. Objective

Implement the minimum Slice 1 E2 vertical path against `contracts-v0.1`:

```text
StrategyDefinition -> parser / validation -> Strategy Runtime -> Signal
```

and define one shared E2 runtime entrypoint that E3 must call rather than reimplement strategy semantics.

### 2. What changed

- added StrategyDefinition JSON/mapping parser and deterministic validation;
- added immutable content-hash verification;
- added exact runtime-family/version compatibility check;
- added structured unsupported primitive rejection;
- added minimal Slice 1 DSL with `SMA`, `GT`, `LT`, and `AND` only;
- added Decimal-only SMA implementation with explicit insufficient-history result;
- added deterministic Strategy Runtime producing canonical Signal fields;
- added closed-candle/no-future-data boundary filtering;
- added deterministic `market_boundary_ref` and `signal_id` derivation;
- added local-only unittest definitions for parser, SMA, LONG, SHORT, NO_TRADE, insufficient history, determinism, future-candle isolation, and provisional-candle isolation;
- documented the required E3 integration call path.

No Candle class/model was introduced. No Backtest-only strategy implementation was introduced. No Risk or Execution behavior was added.

### 3. Files changed

- `src/indicators/__init__.py`
- `src/indicators/sma.py`
- `src/strategy/__init__.py`
- `src/strategy/runtime.py`
- `tests/indicators/test_sma.py`
- `tests/strategy/test_slice1_runtime.py`
- `docs/strategy/SLICE1_RUNTIME.md`
- `status/E2_SLICE1_HANDOFF.md`

### 4. Contracts consumed

- `contracts-v0.1`
- `Candle` — consumed only; not redefined
- `StrategyDefinition`
- `Signal`
- ADR-0001 one-runtime / closed-candle / UTC / Decimal semantics

Contract assumptions:

- E2 consumes canonical Candle fields exactly as defined by `contracts-v0.1`.
- executable financial inputs are Decimal or interchange decimal strings; binary float Candle values are rejected.
- Candle intervals and finalized status remain E1/E7 semantics; E2 only enforces the consumer boundary `close_time <= evaluated_at && is_closed`.
- `StrategyDefinition.schema_version` is preserved into produced `Signal.schema_version`; E2 does not redefine the shared schema-version namespace.
- `market_boundary_ref` is an opaque deterministic `sha256:` identifier over the exact visible closed-candle material used by E2.

### 5. Contracts produced or changed

`NONE` — no `contracts/` or shared `src/domain/` file changed.

E2 produces `Signal` mappings conforming to the existing baseline required fields. Slice 1 does not emit `TradeIntent`.

### 6. Local verification

Result: `NOT_RUN`

Reason: this GPT session has GitHub repository access but no Product-Owner-approved local project execution environment. Project policy forbids using GitHub infrastructure or an unapproved cloud runtime to execute tests.

Required local command from repository root, Windows PowerShell:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests -p "test_*.py" -v
```

Expected test definitions cover:

- exact Decimal SMA reference value;
- insufficient indicator history;
- float input rejection;
- valid StrategyDefinition;
- content hash mismatch;
- structured `UNSUPPORTED_PRIMITIVE`;
- runtime incompatibility;
- same StrategyDefinition + same exact visible Candle boundary + same runtime version -> identical Signal;
- LONG / SHORT / NO_TRADE;
- future Candle cannot change earlier Signal;
- `is_closed=false` Candle cannot change Signal.

No PASS is claimed until the command is executed locally.

### 7. Known limitations

- one required timeframe per strategy only;
- one indicator primitive: `SMA(Candle.close, window_parameter)`;
- operators limited to `GT`, `LT`, `AND`;
- no stateful primitives;
- no entry/exit price model beyond optional Signal `reference_price`;
- no TradeIntent in this slice;
- no indicator cache/performance optimization;
- no executable shared schema types exist yet, so runtime consumes canonical Candle mappings or objects structurally.

These limitations are deliberate to avoid building a large Indicator Library before Slice 1 integration proves the architecture.

### 8. Dependencies / blockers

- local test execution remains `NOT_RUN` and is required before E7 can accept executable evidence;
- E1 must hand off canonical historical Candle output for cross-module Slice 1 integration;
- E3 must use the exact E2 runtime entrypoint below;
- any need for new Candle/shared Signal fields requires E7 contract review rather than E2 modification.

### 9. Required next action

**E7:** review the E2 implementation against `contracts-v0.1`, then integrate with E1/E3 Slice 1 boundaries and run/require local parity tests.

**E3:** import and call the same E2 runtime:

```python
from strategy import StrategyRuntime, parse_strategy_definition

strategy = parse_strategy_definition(strategy_payload)
runtime = StrategyRuntime()
signal = runtime.evaluate(strategy, canonical_candle_sequence, replay_boundary_utc)
```

E3 must record `runtime.version` in `BacktestResult.runtime_version` and `strategy.content_hash` in `BacktestResult.strategy_content_hash`. E3 may not reimplement SMA or DSL rules in `src/backtest/`.

**E1:** provide ordered canonical Candle sequences using the shared Candle contract. E2 does not accept provider-specific payload semantics.

### 10. Security / secrets

- no real API key, API secret, token, credential, password, private key, or live `.env` value was added;
- fixtures contain only synthetic BTC price data;
- runtime exposes no Python/shell/file/network/secret execution primitive.

### 11. GitHub compute policy

Confirmed:

- no GitHub Actions workflow was created or used;
- no GitHub-hosted or GitHub-triggered runner was used;
- no unit/integration/backtest/bug-reproduction workload was executed on GitHub infrastructure;
- verification is explicitly `NOT_RUN` pending the exact local command above.

### 12. Live-trading impact

None. This slice produces only `Signal`. It does not approve risk, size positions, create orders, call Pionex, promote strategies, or enable LIVE.

### 13. Codex bug ticket, if applicable

NONE. No bounded implementation defect has been reproduced locally yet.
