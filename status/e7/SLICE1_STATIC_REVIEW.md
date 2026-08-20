# E7 Slice 1 Static Contract / Architecture Review

> Date: 2026-08-20
> Review type: GitHub static review only
> Integration branch: `integration/slice1-research-skeleton`
> Baseline `main`: `ba2affa62c89d58bb9ffac054963579e434896e1`
> Contract baseline: `contracts-v0.1`
> ADR baseline: `ADR-0001`
> Gate baseline: `status/RELEASE_GATES.md`
> Executable evidence: **NOT_RUN — local only**

## Reviewed domain revisions

- E1: `f962d475b88881c5ae8ceee05e4d952c830b545a`
- E2: `90262a0dacc7a8f3aa798de1b6f1d1b28fd88f6c`
- E3 HEAD: `bead77acde5bfb30f4e6a8065d897a938cef840c`
- E3 concrete E2 binding: `da9fa922f7c6292d4dd801033e70cfe6943249c2`

The E3 commits after `da9fa922...` modify only E3 documentation/handoff, not executable E3 source.

---

## Overall static disposition

| Domain | Static disposition | Blocking finding |
|---|---|---|
| E1 | **PASS for static contract/architecture review** | none |
| E2 | **FAIL / BLOCKED for integration** | `E2-SCHEMA-001` |
| E3 | **PASS with BASELINE edge interpretation** | none; `profit_factor=null` interpretation recorded below |
| Slice 1 combined executable integration | **BLOCKED** | E2 correction required before code assembly / local execution |
| Gate A | **BLOCKED** | executable evidence is still NOT_RUN; E2 static blocker exists |

Static PASS means only that the reviewed source is structurally compatible with the Slice 0 architecture and `contracts-v0.1`. It is not executable evidence and is not a Release Gate PASS.

---

# Contract findings

## E2-SCHEMA-001 — CONFIRMED / BLOCKING

**Owner:** E2 Strategy Engine

**Expected**

`contracts/README.md` requires every consumer to validate the schema version it supports. Slice 1 canonical executable boundaries use `schema_version="contracts-v0.1"`.

**Actual**

At E2 revision `90262a0...`:

1. `parse_strategy_definition(...)` validates `schema_version` only as a non-empty string.
2. E2 Candle projection validates Candle `schema_version` only as a non-empty string and does not reject unsupported contract schema versions.
3. E2 unit fixtures use `schema_version="0.1"` for both StrategyDefinition and Candle.
4. produced Signal assigns `schema_version = strategy.schema_version`, allowing an arbitrary accepted StrategyDefinition schema string to propagate into Signal.
5. E1 and E3 explicitly enforce `schema_version="contracts-v0.1"`; therefore E2 can currently produce a Signal that E3 must reject.

**Impact**

This is a cross-module contract incompatibility at the E1 -> E2 -> E3 boundary. It blocks Slice 1 integration even though E2's runtime semantics are otherwise structurally compatible.

**Required bounded E2 correction**

E2 must correct only E2-owned files. Do not modify `contracts-v0.1`.

Minimum required behavior:

- define one E2 supported contract schema value equal to `contracts-v0.1`;
- `StrategyDefinition` parser rejects any other `schema_version` with a structured unsupported/incompatible-schema error;
- visible/consumed Candle input rejects any other `schema_version` before using Candle financial values in strategy evaluation;
- produced Signal always declares the supported canonical schema version; inheritance is acceptable only if parser enforcement guarantees exact equality;
- align all E2 StrategyDefinition/Candle fixtures to `contracts-v0.1`;
- add explicit tests proving unsupported StrategyDefinition schema is rejected;
- add explicit tests proving unsupported consumed Candle schema is rejected;
- preserve DSL version `0.1` and E2 runtime version `0.1.0` as separate namespaces; do not conflate those with shared contract version.

Suggested writable scope:

- `src/strategy/runtime.py`
- `tests/strategy/test_slice1_runtime.py`
- `docs/strategy/SLICE1_RUNTIME.md`
- `status/E2_SLICE1_HANDOFF.md`

No shared Contract modification is authorized. No E1/E3 implementation modification is authorized for this correction.

**Codex:** NOT APPLICABLE. This is E2 implementation alignment to an already explicit shared contract, not a Codex bug-fix ticket.

---

## E3-PROFIT-FACTOR-NULL — BASELINE INTERPRETATION ACCEPTED

`contracts-v0.1` requires the `profit_factor` field but does not yet define the denominator-zero representation. E3 computes `profit_factor=None` when aggregate losing PnL is zero and serializes the field as JSON `null`.

E7 accepts this for the current **BASELINE** integration under the following narrow interpretation:

- the `profit_factor` field remains present;
- `null` means the ratio is mathematically undefined/non-finite because aggregate losing PnL denominator is zero;
- `null` must not mean missing computation, NOT_RUN validation, parser failure, or unknown data;
- a finite ratio must remain a decimal string;
- consumers must not interpret `null` as zero or as favorable validation evidence.

Before the shared contract is promoted to `STABLE`, E7 must materialize the nullability/edge semantics in the canonical contract (or choose another versioned representation). This static interpretation does not authorize a strategy PASS.

E3 should add/retain explicit local test coverage for both empty/no-trade and all-win/no-loss denominator-zero cases before Gate A evidence is accepted.

---

# E1 static review

Revision: `f962d475b88881c5ae8ceee05e4d952c830b545a`

## 1. Canonical Candle compatibility — PASS (static)

E1 defines the canonical producer fields required by `contracts-v0.1`, including `schema_version`, symbol/timeframe, OHLCV, `is_closed`, source, and optional receipt/source-record metadata. Producer schema is fixed to `contracts-v0.1`.

No alternate cross-module Candle contract was introduced outside E1's producer implementation.

## 2. UTC / Decimal / `[open_time, close_time)` — PASS (static)

- internal datetimes normalize to UTC;
- timeframe duration is enforced;
- decimal financial fields require `Decimal` and finite values;
- interchange serializes financial fields as decimal strings;
- close boundary is derived as `open_time + canonical timeframe duration`, consistent with half-open Candle semantics.

## 3. Pionex finalization rule — ACCEPTED FOR STATIC INTEGRATION; PROVIDER EVIDENCE NOT_RUN

Pionex payload has no explicit per-kline finalization flag in the reviewed E1 model. E1 sets `is_closed=true` only when the provider response timestamp is at or after the Candle's exclusive `close_time`.

This is conservative and compatible with `contracts-v0.1`: it cannot mark a Candle final before the exclusive close boundary. If the source timestamp is stale/invalid, the path fails or leaves bars provisional/missing rather than manufacturing a closed bar.

This acceptance is source-level only. Real Pionex behavior must still pass the required local public 4-timeframe smoke check.

## 4. Inclusive `endTime` -> half-open conversion — PASS (static)

For requested `[start, end)`, E1 calls Pionex with inclusive `endTime = epoch_ms(end) - 1`, and backward pagination advances to one millisecond before the earliest returned open time. The test definition explicitly checks these cursor values.

## 5. Duplicate / missing / ordering / malformed fail-fast — PASS (static)

- duplicate provider identities fail;
- mixed/non-monotonic provider page order fails;
- descending provider pages are normalized only after strict-order validity is established;
- duplicates across pages fail;
- canonical exact-range validation rejects missing, duplicate, out-of-order, overlapping, wrong-boundary, and provisional Candle sequences;
- malformed/non-finite OHLCV fails;
- no interpolation/silent gap repair exists.

### Required E1 correction

None from static review.

### E1 executable evidence

`NOT_RUN` until Product Owner-approved local execution:

```powershell
python -m unittest discover -s tests/market_data -v
python -m compileall -q src/market_data tests/market_data
```

Also required: public Pionex `BTC_USDT_PERP` smoke check for canonical `1m`, `15m`, `1h`, `4h`, with exactly two ascending closed Candles per timeframe or explicit typed failure. An API/network failure is not PASS.

---

# E2 static review

Revision: `90262a0dacc7a8f3aa798de1b6f1d1b28fd88f6c`

## 1. StrategyDefinition compatibility — BLOCKED only by E2-SCHEMA-001

Required field shape, content hash, runtime compatibility, supported timeframe, declarative DSL, unsupported primitive/operator rejection, and immutable identity handling are structurally compatible. Shared schema compatibility enforcement is missing and must be corrected.

## 2. Deterministic runtime — PASS (static)

- no randomness;
- explicit runtime family/version;
- deterministic Decimal SMA;
- deterministic market-boundary hash;
- deterministic signal ID from exact identity/material;
- deterministic reason codes for identical inputs.

Executable determinism remains NOT_RUN.

## 3. Closed/provisional/future Candle isolation — PASS (static)

E2 reads only Candle close boundary and closed flag before deciding whether a Candle is visible. OHLCV from future or provisional Candles is not read into the strategy calculation. Visible history must be strictly ordered.

## 4. No Candle redefinition — PASS

E2's private `_CandleView` is an internal consumer projection only. It is not exported as a competing canonical Candle producer/type and does not alter shared semantics.

## 5. Schema-version compatibility — FAIL

See `E2-SCHEMA-001`.

## 6. Signal canonical compatibility — BLOCKED only by E2-SCHEMA-001

All required Slice 1 Signal fields are emitted with deterministic identity/timestamp/reason/boundary references. The only blocking incompatibility is arbitrary schema propagation from StrategyDefinition.

### Required E2 correction

`E2-SCHEMA-001` only. E7 did not identify a need to redesign the runtime or expand indicator primitives.

### E2 executable evidence

`NOT_RUN` until the corrected E2 revision is assembled locally:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests -p "test_*.py" -v
```

---

# E3 static review

Reviewed HEAD: `bead77acde5bfb30f4e6a8065d897a938cef840c`
Concrete E2 binding source introduced by: `da9fa922f7c6292d4dd801033e70cfe6943249c2`

## 1. Concrete E2 runtime consumption — PASS (static)

`project_e2_runtime_binding()` imports E2's public `StrategyRuntime` and `parse_strategy_definition`, instantiates the actual E2 runtime, parses via E2, and invokes `runtime.evaluate(...)` for replay decisions.

## 2. No private strategy logic — PASS

E3 binding/replay contains no SMA, indicator, DSL, GT/LT/AND, or duplicated direction-decision semantics. Test doubles exist only in E3-owned unit tests; the integrated research skeleton test explicitly requires actual E2 runtime.

## 3. No-look-ahead — PASS (static)

Replay passes only the closed historical prefix through the current Candle boundary and validates that prefix boundaries do not exceed `evaluated_at`. Provisional Candle input is rejected before replay.

## 4. Next-open replay semantics — PASS (static)

A Signal generated at Candle close creates a pending entry/exit that executes at the next Candle open. A final-bar entry Signal cannot receive a nonexistent future open fill. Opposite Signal exits are likewise deferred to the next open.

## 5. Fee/slippage/funding separation — PASS (static)

- fee model is independently versioned/configurable with entry/exit liquidity roles;
- slippage model applies adverse entry/exit fill adjustments and reports slippage cost separately;
- funding is an independently versioned deterministic assumption;
- net PnL uses slippage-adjusted fills and subtracts fees/funding without subtracting reported slippage a second time.

## 6. BacktestResult required fields / reproducibility — PASS (static)

E3 materializes all `contracts-v0.1` required identity/reproducibility fields and core metrics. Result identity binds strategy identity/hash, E2 runtime version, dataset identity/hash/boundaries, replay-engine version, cost assumptions, and trade fingerprints. Unimplemented validation stages remain explicitly `NOT_RUN`.

## 7. `profit_factor=null` edge — ACCEPTED FOR BASELINE WITH CONDITION

See `E3-PROFIT-FACTOR-NULL` above. This interpretation must be formalized before Contract STABLE; it is not a Gate A PASS criterion by itself.

### Required E3 correction

No blocking source correction from this static review.

Before Gate A evidence acceptance, add/confirm explicit local test for an all-win/no-loss denominator-zero `profit_factor=null` case in addition to the existing empty/no-trade case.

### E3 executable evidence

`NOT_RUN` until approved local execution:

```powershell
python -m unittest discover -s tests/backtest -p "test_costs.py" -v
python -m unittest discover -s tests/backtest -p "test_metrics.py" -v
python -m unittest discover -s tests/backtest -p "test_replay.py" -v
```

---

# Integrated Research Skeleton

Static source assembly is **BLOCKED pending corrected E2 revision**. E7 must not freeze or locally execute an integration revision that knowingly contains `E2-SCHEMA-001` as if it were a valid candidate.

After E2 supplies the bounded correction, E7 will pin:

```text
main contracts-v0.1 / ADR-0001
+ reviewed E1 f962d475b88881c5ae8ceee05e4d952c830b545a
+ corrected E2 revision replacing 90262a0...
+ reviewed E3 bead77acde5bfb30f4e6a8065d897a938cef840c
= Slice 1 integration candidate revision
```

Required local integration command:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python tests/backtest/test_real_e2_research_skeleton.py -v
```

The integration test must directly consume actual E1 `Candle` and actual E2 `StrategyRuntime` through E3's concrete binding.

---

# Local-only execution policy

No executable command in this review was run on GitHub infrastructure. No GitHub Actions, GitHub CI, hosted runner, GitHub-triggered runner, scheduled workflow, GitHub backtest, or GitHub E2E execution is authorized.

Current executable status for E1, E2, E3, integrated research skeleton, secret scan, and Pionex smoke: **NOT_RUN**.

`NOT_RUN` remains `NOT_RUN` and is not inferred PASS from static code review.

---

# Slice 1 / Gate status

- Slice 1 static Contract / Architecture Review: **BLOCKED — E2-SCHEMA-001**
- E1 static review: **PASS**
- E2 static review: **FAIL / correction required**
- E3 static review: **PASS with BASELINE edge interpretation**
- Slice 1 executable integration: **NOT_RUN / BLOCKED pending E2 correction**
- Gate A `RESEARCH_READY`: **BLOCKED**
- Gate B/C/D: unchanged / BLOCKED

No Codex ticket is created by this review.
