# Handoff

**From:** E1 / Market Data Engineer  
**To:** E7 / Integration Engineer  
**Branch:** `agent/e1-market-data-okx`  
**Task:** `E1-20260821-002`  
**Date:** 2026-08-21

## 1. Objective

Migrate the bounded V1 public historical market-data path from Pionex to OKX while preserving the unchanged `contracts-v0.1` canonical Candle semantics.

```text
OKX public history-candles
  -> provider validation / mapping / finality
  -> contracts-v0.1 Candle
  -> deterministic exact closed historical sequence
  -> E2 / E3 research consumption boundary
```

This handoff does not authorize or implement WebSocket, MarketSnapshot, private account data, Demo/private orders, Risk, Strategy, Backtest, Registry, or Execution changes.

## 2. Provider endpoint and mappings

Official OKX API V5 reference inspected 2026-08-21:

- `GET https://www.okx.com/api/v5/market/history-candles`
- public / unauthenticated;
- `after` paginates toward older records;
- maximum `limit=100`;
- `ts` is candle opening time in Unix milliseconds;
- `confirm=0` means uncompleted;
- `confirm=1` means completed.

Canonical/provider mapping:

| Canonical | OKX |
|---|---|
| `BTC_USDT_PERP` | `BTC-USDT-SWAP` |
| `1m` | `1m` |
| `15m` | `15m` |
| `1h` | `1H` |
| `4h` | `4H` |

Provider details remain inside E1. Canonical consumers do not receive OKX instrument/bar labels.

## 3. What changed

- Added the executable canonical Candle producer surface preserving `contracts-v0.1`.
- Added OKX public historical-candle source and adapter.
- Added explicit canonical symbol/timeframe mappings.
- Added OKX response-envelope validation and typed rate-limit failure (`50011` / HTTP 429).
- Added Decimal-only OHLCV normalization and malformed OHLCV rejection.
- Added provider-finality normalization using OKX `confirm` only; wall-clock time does not promote a candle to closed.
- Added deterministic within-page duplicate and mixed-order rejection.
- Added ascending canonical page output even when OKX returns descending rows.
- Added exact `[start, end)` historical pagination using `after=end-1ms`, then `after=earliest_open-1ms`.
- Added cross-page duplicate rejection, explicit unconfirmed-candle rejection, exact gap/missing detection, and final ascending sequence validation.
- Added local-only unit/fixture test definitions.

No shared contract was changed.

## 4. Files changed

- `src/market_data/__init__.py`
- `src/market_data/candle.py`
- `src/market_data/errors.py`
- `src/market_data/historical.py`
- `src/market_data/okx.py`
- `src/market_data/timeframes.py`
- `tests/market_data/test_candle_and_okx.py`
- `tests/market_data/test_historical_sequence_okx.py`
- `status/e1/OKX_MIGRATION_HANDOFF.md`
- `coordination/E1/STATUS.md` (status-only successor commit)

## 5. Contracts consumed / changed

Consumed:

- `contracts-v0.1`
- canonical `Candle` contract
- Product Owner decision `docs/architecture/BROKER_TARGET_OKX_DECISION_20260821.md`

Preserved semantics:

- UTC internally;
- RFC 3339 `Z` timestamps at interchange;
- `[open_time, close_time)`;
- `1m / 15m / 1h / 4h` canonical labels;
- Decimal arithmetic and decimal-string interchange;
- duplicate identity = `symbol + timeframe + open_time`;
- no manufactured gap repair;
- `is_closed=false` cannot be consumed as a final historical candle.

Shared contracts changed: `NONE`.

## 6. OKX finality and volume semantics

Finality is provider-authoritative:

```text
OKX confirm == "1" -> canonical is_closed = True
OKX confirm == "0" -> canonical is_closed = False
```

An unconfirmed candle that falls inside a requested exact closed historical range raises `UnclosedCandleError`; it is never silently promoted based on local time.

Canonical `volume` uses OKX response field `vol` as the provider market-data fact. For SWAP, E1 does not reinterpret this value as risk quantity, order size, base-asset quantity, or notional. Exchange execution sizing remains outside this task.

## 7. Pagination / deterministic range behavior

OKX `after` is used for older-data pagination. Because the canonical requested end is exclusive and OKX timestamp pagination is inclusive at the provider boundary, E1 requests:

```text
first cursor = end - 1 ms
next cursor  = earliest returned open_time - 1 ms
```

The loader collects only candles fully inside `[start, end)`, requires `confirm=1`, rejects duplicate identities, sorts only after provider page-order validity is established, then validates an exact gap-free ascending sequence. Missing provider history remains an error; no synthetic candle is created.

## 8. Local verification

Current environment is not a Product Owner-approved local execution environment.

### Unit / deterministic fixtures

Result: `NOT_RUN`

Exact local command from repository root:

```powershell
python -m unittest discover -s tests/market_data -v
```

### Python compile/syntax verification

Result: `NOT_RUN`

Exact local command:

```powershell
python -m compileall -q src/market_data tests/market_data
```

### Public OKX network smoke test

Result: `NOT_RUN`

This future smoke test uses public market data only and requires no credential:

```powershell
$env:PYTHONPATH="src"
@'
from datetime import datetime, timedelta, timezone
from market_data import OkxPublicHistoricalCandleSource, load_okx_historical_candles

source = OkxPublicHistoricalCandleSource()
now = int(datetime.now(timezone.utc).timestamp())
for timeframe, seconds in {"1m": 60, "15m": 900, "1h": 3600, "4h": 14400}.items():
    end = datetime.fromtimestamp((now // seconds) * seconds, tz=timezone.utc)
    start = end - timedelta(seconds=2 * seconds)
    candles = load_okx_historical_candles(
        source,
        symbol="BTC_USDT_PERP",
        timeframe=timeframe,
        start=start,
        end=end,
    )
    print(timeframe, len(candles), [c.is_closed for c in candles])
'@ | python -
```

Acceptance for the smoke test: each timeframe returns exactly two ascending canonical candles with provider-confirmed finality, or fails explicitly with a typed E1 error. API/rate-limit/gap failures must not be converted to PASS.

No executable PASS is claimed.

## 9. Data ranges / test fixtures

- Canonical symbol: `BTC_USDT_PERP`
- OKX instrument: `BTC-USDT-SWAP`
- Timeframes: `1m`, `15m`, `1h`, `4h`
- Synthetic deterministic fixtures begin at `2026-01-01T00:00:00Z` and cover bounded minute-scale ranges.
- Real OKX historical range tested: `NOT_RUN`.

## 10. Known limits

- Only `BTC_USDT_PERP` is authorized in this bounded migration.
- Exact requested boundaries must align to the canonical timeframe.
- OKX history-candles page limit is capped at 100 by this adapter.
- No retry/backoff platform was added; network/provider/rate-limit failures surface explicitly.
- No persistent cache/resume checkpoint was added.
- No live/WebSocket/MarketSnapshot path was added.
- No private OKX endpoint, account data, credential, Demo order, or execution logic was added.
- The adapter accepts the documented OKX historical row variants where `confirm` is the final field and OHLCV remain at the documented leading positions; an incompatible response shape fails explicitly.
- Provider `vol` is preserved without converting it into execution sizing semantics.

## 11. Security / GitHub compute

- No API key, secret, passphrase, token, credential, private key, or live `.env` value was added.
- The OKX source is public and unauthenticated.
- No GitHub Actions/workflow/CI/hosted runner/GitHub-triggered runner was created or used.
- No project code, tests, API experiment, or performance job was executed on GitHub infrastructure.

## 12. Required next action

**E7 / PM:** statically review the OKX E1 migration against `contracts-v0.1`, focusing on symbol/bar isolation, provider `confirm` finality, `after` pagination boundaries, duplicate/gap behavior, and the unchanged E2/E3 canonical Candle boundary.

Executable evidence remains `NOT_RUN` until Product Owner-approved local verification occurs.

E1 stops after this task and does not start WebSocket/private/account/execution work automatically.
