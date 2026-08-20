# Handoff

**From:** E1 / Market Data Engineer  
**To:** E7 / Integration Engineer  
**Branch:** `agent/e1-market-data`  
**Commit(s):** implementation `f962d475b88881c5ae8ceee05e4d952c830b545a`; this handoff is committed separately on the same branch  
**Date:** 2026-08-20

### 1. Objective

Deliver the bounded Slice 1 E1 vertical path required by the Research Skeleton:

```text
Pionex public historical klines
  -> provider validation / normalization
  -> contracts-v0.1 canonical Candle
  -> exact deterministic closed historical sequence
  -> E2 / E3 consumption boundary
```

Scope is intentionally limited to `BTC_USDT_PERP` historical Candles for canonical `1m`, `15m`, `1h`, and `4h`. No live polling, MarketSnapshot, storage platform, strategy, backtest scoring, risk, or private trading behavior is included.

### 2. What changed

Implemented a stdlib-only Python E1 Slice 1 package under `src/market_data/`:

- canonical executable `Candle` producer model matching `contracts-v0.1`;
- UTC normalization and half-open `[open_time, close_time)` duration enforcement;
- `Decimal`-only financial fields and decimal-string interchange serialization;
- explicit canonical -> Pionex timeframe mapping:
  - `1m -> 1M`
  - `15m -> 15M`
  - `1h -> 60M`
  - `4h -> 4H`;
- unauthenticated Pionex public `/api/v1/market/klines` source for `BTC_USDT_PERP`;
- provider response validation without API credentials;
- malformed OHLC / non-finite decimal / negative volume rejection;
- duplicate detection;
- mixed out-of-order provider page rejection;
- deterministic provider-page normalization to ascending canonical Candles after order validity is established;
- safe closed-candle marking: Pionex kline payload has no explicit finalization flag, so the E1 normalizer marks `is_closed=true` only when the provider response timestamp is at or after the candle's exclusive `close_time`;
- backward `endTime` pagination for exact historical ranges;
- exact-range validator that rejects missing, duplicate, out-of-order, overlapping, wrong-boundary, or provisional candles instead of filling/repairing them;
- local test definitions for contract serialization, timeframe mapping, closed/provisional behavior, duplicate/out-of-order/malformed OHLC, pagination, and missing-range detection.

No shared contract was modified.

### 3. Files changed

Implementation commit `f962d475b88881c5ae8ceee05e4d952c830b545a`:

- `src/market_data/__init__.py`
- `src/market_data/candle.py`
- `src/market_data/errors.py`
- `src/market_data/historical.py`
- `src/market_data/pionex.py`
- `src/market_data/timeframes.py`
- `tests/market_data/test_candle_and_pionex.py`
- `tests/market_data/test_historical_sequence.py`

Handoff commit adds:

- `status/e1/SLICE1_HANDOFF.md`

### 4. Contracts consumed

- `contracts-v0.1`
- `contracts/README.md`
- `contracts/SHARED_CONTRACTS_V1.md` — `Candle` producer/consumer contract
- `docs/adr/ADR-0001-canonical-contract-first-architecture.md`
- `docs/architecture/COMMON_CONSTRUCTION_MAP.md` — Slice 1 Research Skeleton

Consumed/frozen semantics:

- UTC internal time;
- RFC 3339 `Z` interchange timestamps;
- Candle interval `[open_time, close_time)`;
- baseline timeframes `1m | 15m | 1h | 4h`;
- Decimal arithmetic / decimal-string interchange;
- duplicate identity = `symbol + timeframe + open_time`;
- `is_closed=false` cannot be treated as final;
- missing/out-of-order/malformed data must be surfaced rather than manufactured.

### 5. Contracts produced or changed

`NONE` for shared contracts.

E1 now produces executable canonical `Candle` instances that declare `schema_version="contracts-v0.1"`. This is an E1 producer implementation, not a redefinition of the shared contract.

E7 review is specifically requested for the normalization choice used when Pionex provides no explicit candle-finalization flag: `provider_response_timestamp >= close_time` is required before E1 sets `is_closed=true`.

### 6. Local verification

**GitHub Actions / CI were not used. All executable verification remains local-only.**

#### Unit / deterministic fixture suite

Result: `NOT_RUN`  
Reason: current GPT/GitHub execution context is not the Product Owner's local execution environment.

Required local command from repository root:

```powershell
python -m unittest discover -s tests/market_data -v
```

#### Python syntax/compile check

Result: `NOT_RUN`

Required local command:

```powershell
python -m compileall -q src/market_data tests/market_data
```

#### Bounded live public Pionex smoke check for all four Slice 1 timeframes

Result: `NOT_RUN`

This command uses only the public market-data endpoint and no credential:

```powershell
$env:PYTHONPATH="src"; python -c "from datetime import datetime,timedelta,timezone; from market_data import PionexPublicKlineSource,load_pionex_historical_candles; src=PionexPublicKlineSource(); now=int(datetime.now(timezone.utc).timestamp()); specs={'1m':60,'15m':900,'1h':3600,'4h':14400}; [(lambda end,tf,sec: print(tf,len(load_pionex_historical_candles(src,symbol='BTC_USDT_PERP',timeframe=tf,start=end-timedelta(seconds=sec*2),end=end))))(datetime.fromtimestamp((now//sec)*sec,tz=timezone.utc),tf,sec) for tf,sec in specs.items()]"
```

Expected acceptance for the smoke check: each timeframe returns exactly two ascending closed canonical Candles or fails explicitly with a typed E1 error. Do not convert an API failure/gap into PASS.

No PASS claim is made in this handoff.

### 7. Data ranges / timeframes

Supported Slice 1 symbol:

- `BTC_USDT_PERP`

Supported canonical timeframes:

- `1m`
- `15m`
- `1h`
- `4h`

Synthetic local test definitions use fixed UTC data beginning at `2026-01-01T00:00:00Z` and small bounded ranges (minutes to one hour) for deterministic fixtures.

Real Pionex historical data range tested: `NOT_RUN`.

### 8. Known limitations

- Slice 1 supports only `BTC_USDT_PERP`; broader symbols are intentionally rejected rather than silently claimed supported.
- Historical range boundaries must align exactly to the canonical timeframe.
- This slice has no persistent cache/storage and no cross-process resume checkpoint.
- No retry/backoff policy is implemented yet; provider/network failure surfaces explicitly. This is intentionally deferred rather than expanding Slice 1 into the full E1 platform.
- No live/incremental polling or WebSocket path.
- No `MarketSnapshot`, mark/index/funding/bid/ask path.
- No interpolation, synthetic candles, or silent gap repair.
- Pionex kline records do not provide a stable per-record ID in the inspected public response, so `source_record_id` remains unset.
- `received_at` is not populated from the provider response timestamp because that timestamp is a source/server observation, not a local receipt timestamp.
- Pionex API/network behavior has not been locally verified yet; provider assumptions are based on the current official Futures API documentation reviewed on 2026-08-20.
- Python was selected only for this bounded E1 package and uses the standard library; no project-wide language/toolchain contract was changed.

### 9. Dependencies / blockers

Current implementation blocker: none at source-definition level.

Evidence blockers:

- local unit test execution: `NOT_RUN`;
- local live Pionex public API smoke verification: `NOT_RUN`;
- E1 -> E2 closed-candle integration: pending E2 implementation/handoff;
- E1 -> E3 historical-consumer integration: pending E3 implementation/handoff;
- E7 contract/integration review: required before Slice 1 can contribute to Gate A evidence.

### 10. Required next action

**E7:** review `agent/e1-market-data` against `contracts-v0.1`, especially:

1. canonical Candle field/time/Decimal compatibility;
2. `provider_response_timestamp >= close_time` as the conservative Pionex closed-candle finalization rule;
3. provider pagination boundary (`endTime = requested_end - 1 ms` for half-open range);
4. rejection semantics for duplicate/missing/mixed-order/malformed data;
5. E2/E3 consumption boundary (`tuple[Candle, ...]`, ascending, exact, closed, gap-free);
6. whether any Slice 1 integration adapter is required without changing the shared contract.

After E7 review, coordinate the E1 -> E2 -> E3 local integration test definitions. Any executable integration remains local-only.

### 11. Security / secrets

Confirmed for this E1 change:

- no real API key, API secret, token, credential, password, private key, or live `.env` value was added;
- Pionex historical source is public and unauthenticated;
- test data is synthetic;
- no private trading endpoint is used.

Repository-wide secret scan: `NOT_RUN` (requires approved local environment).

### 12. GitHub compute policy

Confirmed:

- no GitHub Actions workflow was created or used;
- no `.github/workflows` file was added;
- no GitHub-hosted or GitHub-triggered runner was used;
- no unit/integration/API/backtest/performance job was executed on GitHub infrastructure;
- GitHub was used only for repository read/write collaboration.

### 13. Live-trading impact

`NONE`.

This change cannot place orders, decide direction, size positions, alter leverage, promote strategies, or enable LIVE. It only produces historical canonical market data for E2/E3 research consumption.

### 14. Codex bug ticket, if applicable

`NONE`.

No reproducible bounded implementation bug has been established because local execution is `NOT_RUN`. Missing local evidence must not be converted into a Codex task or GitHub CI run.
