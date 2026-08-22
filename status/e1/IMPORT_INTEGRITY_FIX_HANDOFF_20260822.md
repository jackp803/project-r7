# Handoff

**From:** E1 / Market Data Engineer  
**To:** E7 / PM  
**Task:** `E1-20260822-001`  
**Branch:** `agent/e1-market-data-import-integrity-fix-20260822`  
**State:** `IN_PROGRESS` until module-role restoration commit is recorded below

## Objective

Restore the already-reviewed E1 market-data module/file identities on current `main` without changing accepted market-data behavior.

The defect is a three-file content permutation:

| Path | Current-main blob before fix | Intended accepted blob | Intended role |
|---|---|---|---|
| `src/market_data/candle.py` | `fb9cd216b83cd595304d23a5cec46fd9a2091894` | `5605830b4da4fbe10e94cff72794a495db9ebf6e` | canonical `Candle` + `CONTRACT_SCHEMA_VERSION` |
| `src/market_data/errors.py` | `ac08d88dd327719b01babba098d78da0f34ab5bf` | `fb9cd216b83cd595304d23a5cec46fd9a2091894` | typed E1 errors |
| `src/market_data/timeframes.py` | `5605830b4da4fbe10e94cff72794a495db9ebf6e` | `ac08d88dd327719b01babba098d78da0f34ab5bf` | timeframe duration/alignment + OKX bar mapping |

Accepted semantic reference: E1 revision `c782438ae7e895f2304498946970f2ee5dd5b18f`.

## Preserved scope

No new market-data behavior is authorized or introduced. The following current-main E1 files are intentionally unchanged:

- `src/market_data/__init__.py` blob `5b426610b49f72068cb4cb8466655f0ddc3224d1`
- `src/market_data/historical.py` blob `b8ecd0ce2fc1a218e2bfcf2c7939c6d029e4b53b`
- `src/market_data/okx.py` blob `65ce66e428e53e69130d682f4a6f4aeb304bc0cf`

Therefore the accepted OKX pagination/finality/documentation semantics remain intact.

## Regression test definition

Added:

- `tests/market_data/test_import_integrity.py`

The deterministic test definition covers:

- `import market_data`;
- public `Candle`, `CONTRACT_SCHEMA_VERSION`, `SUPPORTED_TIMEFRAMES`, and `okx_bar` module identity;
- expected typed error classes under `market_data.errors`;
- explicit non-permutation of `candle`, `errors`, and `timeframes` roles;
- existing `contracts-v0.1` Candle Decimal/RFC3339 serialization and `1m/15m/1h/4h` OKX timeframe mapping.

## Executable verification

Result: `NOT_RUN`.

Reason: current GPT/GitHub context is not a Product Owner-approved local execution environment.

Exact required local commands from repository root:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/market_data -p "test_*.py" -v
python -c "import market_data; print(market_data.Candle, market_data.CONTRACT_SCHEMA_VERSION)"
```

No executable PASS is claimed.

## E3 blocker disposition

At static/source level, this task restores the module/file identity defect that prevented the E1 public import surface from being structurally coherent. This is sufficient for PM/E7/E3 to perform a bounded source/SHA recheck.

It does **not** establish executable E1->E3 integration PASS because imports/tests were not run in an approved local environment. Executable integration remains `NOT_RUN`.

## Security / compute

- shared contract changes: `NONE`
- provider behavior changes: `NONE`
- private/account/Demo/order API work: `NONE`
- E2/E3 production changes: `NONE`
- credentials/secrets: `NONE`
- GitHub Actions/CI/hosted runner/project compute: `NOT_USED`

## Correction revision

The exact module-restoration revision and final evidence state are recorded in `coordination/E1/STATUS.md` after the correction commit is created.
