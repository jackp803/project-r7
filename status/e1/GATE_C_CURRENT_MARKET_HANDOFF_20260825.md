# E1 Gate C Current Market Handoff — 2026-08-25

- task_id: `E1-20260825-003`
- branch: `agent/e1-gate-c-current-market-20260825`
- provider: `OKX API V5 public REST`
- canonical symbol: `BTC_USDT_PERP`
- provider symbol: `BTC-USDT-SWAP`
- contract: `contracts-v0.1`

## Delivered boundary

E1 now defines a bounded credential-free current-market polling surface for Gate C:

- `GET /api/v5/market/ticker?instId=BTC-USDT-SWAP`
- `GET /api/v5/market/candles?instId=BTC-USDT-SWAP&bar=<1m|15m|1H|4H>`

No private/account/authentication/order/mutation endpoint is exposed.

Current ticker normalization produces the existing canonical `MarketSnapshot` fields with UTC timestamps, Decimal prices, source identity, `health_status=HEALTHY`, and `freshness_ms` only when the observation passes Gate C freshness checks. Stale, materially future, malformed, provider-error, and non-monotonic observations fail through typed E1 errors rather than becoming fake healthy data.

Gate C freshness constants:

```text
healthy maximum age = 5,000 ms
clock future tolerance = 5,000 ms
```

A later-received ticker with an older provider timestamp cannot replace newer accepted truth in `CurrentMarketState`.

Current candles preserve the existing canonical Candle contract. Rows are parsed with OKX provider `confirm` finality; only `confirm=1` rows whose canonical close boundary is at or before `received_at` are exposed as final. Provisional/unclosed rows are validated and withheld. Duplicate, mixed-order, malformed, provider-error, and gaps between exposed finalized candles remain explicit failures.

Supported mappings remain:

| Canonical | OKX |
|---|---|
| `BTC_USDT_PERP` | `BTC-USDT-SWAP` |
| `1m` | `1m` |
| `15m` | `15m` |
| `1h` | `1H` |
| `4h` | `4H` |

## Changed files

- `src/market_data/current.py`
- `src/market_data/errors.py`
- `src/market_data/__init__.py`
- `tests/market_data/test_gate_c_current_market.py`
- `status/e1/GATE_C_CURRENT_MARKET_HANDOFF_20260825.md`
- `coordination/E1/STATUS.md` in the terminal status commit

## Test definitions

Credential-free injected/sanitized tests define:

- ticker -> canonical MarketSnapshot;
- exactly 5,000 ms healthy boundary and >5,000 ms stale failure;
- missing/malformed/future timestamps;
- non-monotonic ticker rejection without state overwrite;
- finalized/closed current candle acceptance;
- provisional/not-yet-closed candle withholding;
- current-candle gap/malformed/provider-error behavior;
- exact `1m/15m/1h/4h` endpoint mapping;
- public ticker endpoint allowlist shape;
- zero/malformed price cannot become valid observation.

## Executable verification

`NOT_RUN` in this ChatGPT/GitHub context because no approved local runner is attached here. No provider network request was performed.

Exact approved-local command:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/market_data -p "test_*.py" -v
```

`NOT_RUN != PASS`.

## Security / scope

- credentials/secrets: `NONE`
- private/account API: `NONE`
- provider mutation/order submission: `NONE`
- WebSocket: `NONE`
- shared contract changes: `NONE`
- E2-E7 production/test changes: `NONE`
- persistence/OperationalMode ownership: `NONE`
- GitHub Actions/CI/hosted/GitHub-triggered compute: `NOT_USED`
- SHADOW/PAPER/LIVE runtime start: `NONE`

E1 stops after this bounded Gate C current-market task and does not self-start another task.
