# E7 Static Review — E1 OKX Public Historical Migration / PR #8

> Task: `E7-20260821-005`  
> Reviewer: E7 Integration / Architecture / System QA / Release  
> Review branch: `agent/e7-e1-okx-review-20260821`  
> PR: `#8 market-data: migrate V1 public history to OKX`  
> E1 branch: `agent/e1-market-data-okx`  
> Reviewed implementation/tests/handoff revision: `c782438ae7e895f2304498946970f2ee5dd5b18f`  
> PR head observed during review: `d64bb15f93f9383f662848f1a7534152820f4cba`  
> Review date: 2026-08-21

## 1. Disposition

```text
E1 implementation static review        PASS
E1 test-definition static review       PASS
Canonical Candle compatibility         PASS
Provider-fact recheck                  PASS
Role/scope/security audit              PASS
Executable verification                NOT_RUN
PR #8 current-head merge readiness     BLOCKED
Gate A/B/C/D                            BLOCKED / UNCHANGED
```

The E1 OKX public historical implementation is statically acceptable at the reviewed implementation revision.

PR #8 is **not safe to merge at its current head** because its branch is currently diverged from the latest `main` and GitHub reports `mergeable=false`. This is a repository synchronization blocker, not an implementation defect.

## 2. Reviewed repository evidence

E1 reports implementation/tests/handoff HEAD:

```text
c782438ae7e895f2304498946970f2ee5dd5b18f
```

The current PR head is one successor commit later:

```text
d64bb15f93f9383f662848f1a7534152820f4cba
```

Static compare from `c782438...` to `d64bb15...` shows the successor changes only:

```text
coordination/E1/STATUS.md
```

Therefore the production/test/handoff blobs reviewed here are the exact E1-reported implementation revision.

At review time, current `main` is:

```text
4f969979ad1f2244b14b0a5e12c85177e8fca5c9
```

Current E1 branch relation to latest main:

```text
ahead_by  = 2
behind_by = 15
merge_base = 205bec0209f5256329a3c043b24f55f5c58d15f6
```

GitHub PR metadata also reports:

```text
mergeable = false
```

## 3. Official OKX provider facts rechecked

Official OKX API V5 documentation was rechecked during this task. Provider authority remains the official OKX documentation, not community sources.

Relevant current official documentation:

- `https://www.okx.com/docs-v5/en/`
- endpoint: `GET /api/v5/market/history-candles`

Confirmed provider semantics:

1. Market Data endpoints do not require authentication.
2. Historical candles use:
   - `GET /api/v5/market/history-candles`
   - `after` for records **earlier than** the requested `ts`;
   - maximum history page `limit=100`;
   - `ts` as candle opening time in Unix milliseconds.
3. Relevant official bar labels include:
   - `1m`
   - `15m`
   - `1H`
   - `4H`
4. `confirm` is provider finality:
   - `0` = uncompleted;
   - `1` = completed.
5. Current official documentation is internally inconsistent about the historical row tail:
   - the response example contains 9 fields including `volCcyQuote` before `confirm`;
   - the history array declaration also shows an 8-field form ending in `confirm`.

Because E1 accepts only 8- or 9-field rows, keeps OHLCV at documented leading indices, and requires the final field to be exactly `confirm in {"0","1"}`, that compatibility handling is statically reasonable and fail-closed for other shapes.

## 4. Canonical symbol boundary

Required mapping:

```text
canonical BTC_USDT_PERP
        -> E1 OKX adapter only
OKX BTC-USDT-SWAP
```

Observed implementation:

```python
_CANONICAL_TO_OKX_INSTRUMENT = {"BTC_USDT_PERP": "BTC-USDT-SWAP"}
```

Provider identity does not leak into canonical Candle `symbol`.

Disposition: **PASS**.

## 5. Timeframe mapping

Observed provider mapping:

```text
1m  -> 1m
15m -> 15m
1h  -> 1H
4h  -> 4H
```

These labels match the current official OKX historical-candle documentation.

Canonical Candle still uses only canonical `1m / 15m / 1h / 4h` labels.

Disposition: **PASS**.

## 6. Provider finality / no wall-clock promotion

`normalize_okx_history_page(...)` derives:

```text
is_closed = (confirm == "1")
```

It does not use local wall-clock time to promote `confirm=0`.

The exact closed-range loader additionally rejects any `is_closed=false` candle that falls inside the requested range with `UnclosedCandleError`.

Therefore:

```text
confirm=1 -> eligible closed Candle
confirm=0 -> provisional; cannot enter exact closed historical result
```

Disposition: **PASS**.

## 7. UTC and half-open interval semantics

Observed implementation:

- OKX `ts` is parsed as UTC epoch milliseconds;
- canonical `open_time = ts`;
- canonical `close_time = open_time + canonical timeframe duration`;
- exact loader operates on `[start, end)`;
- requested boundaries must be timeframe-aligned;
- interchange serialization remains RFC 3339 UTC `Z`;
- financial fields remain `Decimal` internally and decimal strings at interchange.

This preserves `contracts-v0.1` Candle semantics.

Disposition: **PASS**.

## 8. Pagination and exact-range behavior

Observed loader cursors:

```text
first cursor = end - 1 ms
next cursor  = earliest_open - 1 ms
```

Current official OKX wording says `after` returns records **earlier than** the requested timestamp.

Because canonical requested boundaries and returned candle opens are timeframe aligned, the `-1 ms` cursor is conservative for both the initial exclusive end boundary and subsequent backwards pages. A valid target candle open cannot equal those `boundary - 1 ms` cursor values for the supported whole-minute/hour timeframes.

The loader:

- filters to the requested `[start, end)` range;
- rejects unconfirmed candles inside the range;
- rejects cross-page duplicate identities;
- sorts collected canonical candles ascending only after per-page ordering validity is checked;
- validates the final sequence as exact and gap-free;
- raises when provider history is missing rather than synthesizing a candle.

Disposition: **PASS**.

### Documentation precision finding — `E1-OKX-DOC-AFTER-001`

Severity:

```text
NON_BLOCKING / DOCUMENTATION_ONLY
```

Owner:

```text
E1
```

Current source comments/handoff describe OKX `after` as an inclusive or `at/before` boundary. Current official documentation says records are returned **earlier than** the requested `ts`.

The current implementation remains safe because it explicitly subtracts 1 ms and candle opens are timeframe aligned. The wording should nevertheless be corrected when E1 synchronizes the PR branch so future maintainers do not rely on incorrect provider-boundary prose.

This finding does not require a contract change and does not invalidate the reviewed pagination algorithm.

## 9. Ordering / duplicate / gap / malformed-data behavior

Observed fail-closed behavior:

- duplicate open time within a provider page -> `DuplicateCandleError`;
- duplicate canonical identity across pages -> `DuplicateCandleError`;
- mixed/non-monotonic provider page -> `OutOfOrderCandleError`;
- invalid provider response envelope -> typed provider error;
- malformed/non-finite decimal OHLCV -> reject;
- invalid OHLC invariant -> reject;
- negative volume -> reject;
- invalid `confirm` -> reject;
- missing exact-range candle -> `MissingCandleError`;
- unclosed requested candle -> `UnclosedCandleError`;
- provider/rate-limit/network errors are surfaced, not converted to empty success.

No manufactured candle repair exists.

Disposition: **PASS**.

## 10. Volume boundary

E1 maps OKX provider `vol` into canonical Candle `volume` and explicitly does not reinterpret it as E5 risk quantity, E4 order size, base-asset exposure, or notional.

`contracts-v0.1` currently requires canonical `volume` to be non-negative but does not define a cross-provider execution-sizing unit. Provider provenance remains explicit via Candle `source`.

No execution/risk semantic leakage was identified in this bounded E1 migration.

Disposition: **PASS** for the current Candle baseline.

## 11. Test-definition static review

Reviewed files:

- `tests/market_data/test_candle_and_okx.py`
- `tests/market_data/test_historical_sequence_okx.py`

Static coverage includes:

- exact canonical symbol -> OKX instrument mapping;
- exact canonical -> provider timeframe labels;
- public URL contains SWAP instrument, bar, `after`, and limit;
- descending provider page -> ascending canonical output;
- provider `confirm` controls finality;
- duplicates rejected;
- mixed provider order rejected;
- malformed OHLC rejected;
- negative volume rejected;
- invalid `confirm` rejected;
- provider rate-limit code typed;
- exact backwards pagination cursors;
- exact ascending output;
- gap/missing historical data rejected;
- unconfirmed candle rejected from closed range.

The fake paged source models the provider boundary as `<= cursor`, while current official wording says `earlier than cursor`. Because the implementation/test cursors are always `aligned boundary - 1 ms`, equality cannot occur for valid supported candle opens; this fixture simplification does not change the expected selected candle set. It should not be generalized into provider semantics.

Executable test disposition remains:

```text
NOT_RUN
```

No static review statement is executable PASS.

## 12. Changed-file / role-scope audit

PR #8 changed files are limited to:

```text
coordination/E1/STATUS.md
src/market_data/__init__.py
src/market_data/candle.py
src/market_data/errors.py
src/market_data/historical.py
src/market_data/okx.py
src/market_data/timeframes.py
status/e1/OKX_MIGRATION_HANDOFF.md
tests/market_data/test_candle_and_okx.py
tests/market_data/test_historical_sequence_okx.py
```

Observed scope results:

```text
shared contracts modified             NO
E2/E3/E4/E5/E6 production modified   NO
.github/workflows modified            NO
GitHub CI/Actions added               NO
private/account API logic added       NO
Demo/private execution added          NO
credentials/secrets added             NO
new Pionex-specific development       NO
historical evidence deleted           NO
```

Disposition: **PASS**.

## 13. Merge blocker — `E1-INTEGRATION-SYNC-001`

Classification:

```text
REPOSITORY SYNCHRONIZATION BLOCKER
NOT AN E1 MARKET-DATA SOURCE DEFECT
```

Owner:

```text
E1 / PM branch synchronization
```

Observed state:

```text
PR branch ahead latest main by   2
PR branch behind latest main by 15
GitHub PR mergeable             false
```

Required resolution before merge:

1. synchronize `agent/e1-market-data-okx` with the then-current `main` without discarding reviewed E1 history;
2. resolve coordination/status conflicts without overwriting newer PM-owned TASK material;
3. preserve the reviewed production/test/handoff blobs unless an intentional E1 correction is made;
4. re-check PR changed-file scope and mergeability after synchronization;
5. if any production/test/handoff blob changes, E7 must review the changed content before merge;
6. if only main synchronization / mailbox resolution / documentation wording changes and reviewed code/test blobs remain identical, a bounded SHA/scope recheck is sufficient.

## 14. PR #8 merge recommendation

```text
SOURCE STATIC ACCEPTANCE: PASS
MERGE CURRENT PR HEAD NOW: NO / BLOCKED
```

Reason:

The implementation is statically acceptable, but the current PR head is not mergeable with current main. E7 does **not** recommend bypassing or force-resolving that divergence.

After E1/PM synchronization restores a clean merge relationship and preserves or re-reviews any changed E1 blobs, PR #8 may proceed to merge from the static-contract perspective.

This recommendation does not claim local executable evidence.

## 15. Local verification still required

Current evidence:

```text
unit tests             NOT_RUN
compile/syntax check   NOT_RUN
public OKX smoke       NOT_RUN
```

Exact E1 local commands already recorded in the handoff:

```powershell
python -m unittest discover -s tests/market_data -v
python -m compileall -q src/market_data tests/market_data
```

The public-network smoke command is documented in `status/e1/OKX_MIGRATION_HANDOFF.md`.

No GitHub Actions, CI, hosted runner, GitHub-triggered runner, or project execution may substitute for this evidence.

## 16. Release gates

No release gate changes in this task:

```text
Gate A RESEARCH_READY   BLOCKED
Gate B PAPER_READY      BLOCKED
Gate C SHADOW_READY     BLOCKED
Gate D LIVE_READY       BLOCKED
```

## 17. Final E7 disposition

```text
E1 OKX migration source/tests     PASS / STATIC ONLY
PR #8 current merge readiness     BLOCKED / E1-INTEGRATION-SYNC-001
Provider documentation precision NON_BLOCKING / E1-OKX-DOC-AFTER-001
Executable evidence               NOT_RUN
Shared-contract changes           NONE
Gate A/B/C/D                      BLOCKED / UNCHANGED
Codex ticket                      NONE / NOT_APPLICABLE
```

E7 stops after this review. It does not merge PR #8 and does not start another E1/E2/E5 review automatically.
