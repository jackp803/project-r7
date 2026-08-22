# E1 Current Task

- task_id: `E1-20260822-001`
- issued_at: `2026-08-22T19:55:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e1-market-data-import-integrity-fix-20260822`
- authority: `agents/E1_MARKET_DATA.md`, `agents/README.md`, `contracts-v0.1`, accepted E1 OKX historical implementation revision `c782438ae7e895f2304498946970f2ee5dd5b18f`

## Objective

Repair the current-main E1 public-import/file-integrity defect that blocks E3 integration. This is a bounded restoration of the already reviewed E1 Candle/errors/timeframe module identities, not new market-data behavior.

PM independently confirmed current `main` is internally inconsistent:

- `src/market_data/__init__.py` imports `CONTRACT_SCHEMA_VERSION` and `Candle` from `.candle`, but current `candle.py` contains the E1 error classes instead;
- current `errors.py` contains timeframe functions and imports `.errors.UnsupportedTimeframeError` from itself;
- current `timeframes.py` contains the canonical `Candle` implementation and imports `.timeframes.timeframe_duration` from itself.

The three contents are effectively permuted relative to the accepted E1 implementation.

## Accepted semantic reference

At accepted reviewed E1 revision `c782438ae7e895f2304498946970f2ee5dd5b18f`:

- `src/market_data/candle.py` blob = `5605830b4da4fbe10e94cff72794a495db9ebf6e` — canonical Candle + `CONTRACT_SCHEMA_VERSION`;
- `src/market_data/errors.py` blob = `fb9cd216b83cd595304d23a5cec46fd9a2091894` — typed E1 market-data errors;
- `src/market_data/timeframes.py` blob = `ac08d88dd327719b01babba098d78da0f34ab5bf` — timeframe duration/alignment + OKX bar mapping.

Restore the correct module responsibilities/semantics against latest `main`. Do not blindly overwrite unrelated later accepted OKX pagination/documentation changes in `historical.py` or `okx.py`.

## Required actions

1. Read this TASK from latest `main`, fetch latest `main` again, and work only on fresh branch `agent/e1-market-data-import-integrity-fix-20260822` created by PM from post-TASK latest main.
2. Inspect the three current files and the accepted `c782438...` references directly. Restore the correct code to the correct filenames so `import market_data` and the documented public surface are structurally coherent.
3. Preserve canonical `contracts-v0.1` Candle semantics, Decimal/RFC3339 behavior, E1 typed errors, supported `1m/15m/1h/4h` timeframe behavior, and accepted OKX adapter semantics. No new provider behavior.
4. Do not modify `src/market_data/historical.py` or `src/market_data/okx.py` unless an exact import-path correction is demonstrably required; if changed, explain why and preserve semantics.
5. Add/update deterministic local-only test definitions under `tests/market_data/**` proving at minimum:
   - `import market_data` resolves;
   - public `Candle`, `CONTRACT_SCHEMA_VERSION`, `SUPPORTED_TIMEFRAMES`, `okx_bar` resolve from the intended modules;
   - `errors.py` exposes the expected typed error classes;
   - no self-import cycle/module-role permutation remains;
   - existing Candle/timeframe semantics remain represented.
6. No WebSocket, MarketSnapshot, cache/retry platform, private/account API, Demo/order API, E2/E3 changes, shared-contract edits, or provider calls.
7. Update E1 handoff/status with exact correction revision, file/blob dispositions, changed-file scope, and the E3 blocker disposition.
8. Executable verification is local-only. Without a Product Owner-approved local environment, keep `NOT_RUN` and record exact commands, including:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/market_data -p "test_*.py" -v
python -c "import market_data; print(market_data.Candle, market_data.CONTRACT_SCHEMA_VERSION)"
```

9. Do not use GitHub Actions/CI/hosted runners or GitHub-triggered project compute.
10. Push only this bounded correction and status/handoff evidence, then stop for PM/E7 review. Do not merge yourself or start another task.

## Acceptance

Static/source completion requires the supported E1 package/file identities to be coherent again, with `market_data` public imports structurally resolvable and no semantic expansion beyond the previously reviewed E1 baseline plus already accepted OKX documentation changes. Executable verification remains `NOT_RUN`; Gate A/B/C/D remain blocked.

## Writable scope

- `src/market_data/candle.py`
- `src/market_data/errors.py`
- `src/market_data/timeframes.py`
- `tests/market_data/**`
- E1-owned docs/handoff/status
- `coordination/E1/STATUS.md`

## Forbidden scope

- `contracts/**`;
- E2/E3/E4/E5/E6/E7 production code;
- provider/private API or execution behavior;
- credentials/secrets;
- WebSocket/live market state;
- GitHub compute/CI;
- executable PASS claims.

## Completion / status

Repair only the E1 module/file-integrity defect, push exact evidence, update STATUS, and stop.