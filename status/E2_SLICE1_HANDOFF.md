# Handoff

**From:** E2 / Strategy Engine Engineer  
**To:** E7 / Integration Engineer  
**Branch:** `agent/e2-strategy-engine`  
**Commit(s):** initial Slice 1 `90262a0dacc7a8f3aa798de1b6f1d1b28fd88f6c`; Issue #5 correction = branch HEAD containing this handoff  
**Date:** 2026-08-20

### 1. Objective

Implement the minimum Slice 1 E2 vertical path against `contracts-v0.1`:

```text
StrategyDefinition -> parser / validation -> Strategy Runtime -> Signal
```

and correct Issue #5 / `E2-SCHEMA-001` so the executable E2 boundary uses the shared contract schema version `contracts-v0.1` consistently without changing shared contracts.

This correction is bounded to schema compatibility only. DSL semantics and runtime semantics remain unchanged.

### 2. What changed

Original Slice 1 behavior remains:

- StrategyDefinition JSON/mapping parser and deterministic validation;
- immutable content-hash verification;
- exact runtime-family/version compatibility check;
- structured unsupported primitive rejection;
- minimal Slice 1 DSL with `SMA`, `GT`, `LT`, and `AND` only;
- deterministic Strategy Runtime producing Signal;
- closed-candle/no-future-data boundary filtering;
- deterministic `market_boundary_ref` and `signal_id` derivation;
- one shared E2 runtime entrypoint for E3/backtest, paper, and live-compatible callers.

Issue #5 correction adds only:

- supported shared schema constant = `contracts-v0.1`;
- StrategyDefinition parser rejects any other `schema_version` with structured `UNSUPPORTED_SCHEMA_VERSION`;
- visible/consumed Candle rejects any other `schema_version` with structured `UNSUPPORTED_CANDLE_SCHEMA_VERSION` before E2 reads Candle financial fields;
- produced `Signal.schema_version` is explicitly `contracts-v0.1`;
- E2 StrategyDefinition and Candle test fixtures now use `contracts-v0.1` instead of `0.1`;
- explicit unsupported StrategyDefinition schema test;
- explicit unsupported consumed Candle schema test;
- deterministic Signal test now asserts produced schema `contracts-v0.1`;
- documentation explicitly distinguishes shared schema `contracts-v0.1`, DSL `0.1`, and runtime `0.1.0`.

No Candle class/model was introduced. No Backtest-only strategy implementation was introduced. No Risk or Execution behavior was added.

### 3. Files changed

Issue #5 writable scope only:

- `src/strategy/runtime.py`
- `tests/strategy/test_slice1_runtime.py`
- `docs/strategy/SLICE1_RUNTIME.md`
- `status/E2_SLICE1_HANDOFF.md`

No other repository path was modified by this correction.

### 4. Contracts consumed

- shared contract/schema version: `contracts-v0.1`
- `Candle` — consumed only; not redefined
- `StrategyDefinition`
- `Signal`
- ADR-0001 one-runtime / closed-candle / UTC / Decimal semantics

Compatibility namespaces are intentionally separate:

- shared contract/schema version = `contracts-v0.1`;
- E2 DSL version = `0.1`;
- E2 runtime version = `0.1.0`.

Contract assumptions:

- `StrategyDefinition.schema_version` must equal `contracts-v0.1` before the definition is accepted.
- E2 consumes canonical Candle fields exactly as defined by `contracts-v0.1`.
- a visible/consumed `Candle.schema_version` must equal `contracts-v0.1` before E2 reads `open/high/low/close/volume`.
- future or provisional Candles outside the current closed-candle boundary are not consumed strategy inputs and remain excluded before OHLCV reads.
- executable financial inputs are Decimal or interchange decimal strings; binary float Candle values are rejected.
- Candle intervals and finalized status remain E1/E7 semantics; E2 enforces the consumer boundary `close_time <= evaluated_at && is_closed`.
- produced `Signal.schema_version` is always `contracts-v0.1`.
- `market_boundary_ref` is an opaque deterministic `sha256:` identifier over the exact visible closed-candle material used by E2.

### 5. Contracts produced or changed

`NONE` — no `contracts/` or shared `src/domain/` file changed.

E2 produces `Signal` mappings conforming to the existing `contracts-v0.1` required fields. Slice 1 does not emit `TradeIntent`.

### 6. Local verification

Result: `NOT_RUN`

Reason: this GPT session has GitHub repository access but no Product-Owner-approved local project execution environment. Project policy forbids using GitHub infrastructure or an unapproved cloud runtime to execute tests.

Required local command from repository root, Windows PowerShell:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests -p "test_*.py" -v
```

Test definitions now cover:

- valid StrategyDefinition using shared schema `contracts-v0.1`;
- unsupported StrategyDefinition shared schema -> structured `UNSUPPORTED_SCHEMA_VERSION`;
- content hash mismatch;
- structured `UNSUPPORTED_PRIMITIVE`;
- runtime incompatibility;
- canonical Candle fixture using shared schema `contracts-v0.1`;
- unsupported visible/consumed Candle shared schema -> structured `UNSUPPORTED_CANDLE_SCHEMA_VERSION`;
- same StrategyDefinition + same exact visible Candle boundary + same runtime version -> identical Signal;
- produced `Signal.schema_version == "contracts-v0.1"`;
- LONG / SHORT / NO_TRADE;
- insufficient history;
- future Candle cannot change earlier Signal;
- `is_closed=false` Candle cannot change Signal.

No PASS is claimed until the command is executed locally and E7 reviews the correction.

### 7. Known limitations

- one required timeframe per strategy only;
- one indicator primitive: `SMA(Candle.close, window_parameter)`;
- operators limited to `GT`, `LT`, `AND`;
- no stateful primitives;
- no entry/exit price model beyond optional Signal `reference_price`;
- no TradeIntent in this slice;
- no indicator cache/performance optimization;
- no executable shared schema types exist yet, so runtime consumes canonical Candle mappings or objects structurally;
- shared schema support is intentionally exact-match `contracts-v0.1` for Slice 1; additive/future contract compatibility requires explicit E7-approved work rather than implicit acceptance.

These limitations are deliberate to avoid expanding Issue #5 beyond its bounded correction scope.

### 8. Dependencies / blockers

- local test execution remains `NOT_RUN` and is required before E7 can accept executable evidence;
- E7 must re-review the corrected E2 revision and replace the rejected E2 pin `90262a0...` only after accepting this correction;
- E1 must provide canonical historical Candle output at shared schema `contracts-v0.1`;
- E3 must consume the corrected E2 runtime and must not reimplement strategy semantics;
- any future shared schema/version change requires E7 contract review rather than E2 implicit compatibility.

### 9. Required next action

**E7:** review Issue #5 correction against `contracts-v0.1`. The corrected commit SHA is reported alongside this handoff by E2. Do not infer Slice 1 PASS from the commit; local executable verification remains `NOT_RUN`.

**E3:** import and call the same corrected E2 runtime:

```python
from strategy import StrategyRuntime, parse_strategy_definition

strategy = parse_strategy_definition(strategy_payload)
runtime = StrategyRuntime()
signal = runtime.evaluate(strategy, canonical_candle_sequence, replay_boundary_utc)
```

E3 must provide StrategyDefinition and consumed Candle data at shared schema `contracts-v0.1`, record `runtime.version` in `BacktestResult.runtime_version`, and record `strategy.content_hash` in `BacktestResult.strategy_content_hash`. E3 may not reimplement SMA or DSL rules in `src/backtest/`.

**E1:** provide ordered canonical Candle sequences using the existing shared `contracts-v0.1` Candle contract. No E1 change is part of Issue #5.

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

None. This correction only tightens shared schema compatibility at the E2 StrategyDefinition/Candle/Signal boundary. It does not approve risk, size positions, create orders, call Pionex, promote strategies, or enable LIVE.

### 13. Codex bug ticket, if applicable

NONE. Issue #5 is an E2 bounded implementation correction under the existing architecture, not a Codex architecture task.
