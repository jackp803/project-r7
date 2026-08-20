# E7 Slice 1 — Issue #5 Re-review / Candidate Freeze

> Date: 2026-08-20
> Review type: GitHub static Contract / Architecture re-review
> Issue: #5 `E2-SCHEMA-001`
> Contract baseline: `contracts-v0.1`
> Executable evidence: `NOT_RUN` — LOCAL ONLY

## Corrected E2 revision

- rejected prior E2 pin: `90262a0dacc7a8f3aa798de1b6f1d1b28fd88f6c`
- corrected E2 pin: `b1e6920ebb29a84916f99a06fe758529d8fbf3ec`
- correction relation: exactly one commit ahead of rejected pin

## Issue #5 static acceptance

| Acceptance | Result | Static evidence |
|---|---|---|
| StrategyDefinition accepts only `contracts-v0.1` | PASS | `SUPPORTED_SHARED_SCHEMA_VERSION` and exact parser equality check |
| Unsupported StrategyDefinition schema structured reject | PASS | `UNSUPPORTED_SCHEMA_VERSION` with object/supported/actual details |
| Visible/consumed Candle schema validated before financial reads | PASS | `_candle_view` checks schema before `open/high/low/close/volume` reads |
| Unsupported Candle schema structured reject | PASS | `UNSUPPORTED_CANDLE_SCHEMA_VERSION` |
| Produced Signal schema guaranteed `contracts-v0.1` | PASS | Signal output explicitly uses `SUPPORTED_SHARED_SCHEMA_VERSION` |
| Fixtures use `contracts-v0.1` | PASS | StrategyDefinition and Candle fixtures aligned |
| Unsupported StrategyDefinition schema test exists | PASS | `test_unsupported_strategy_schema_is_structured` |
| Unsupported Candle schema test exists | PASS | `test_unsupported_consumed_candle_schema_is_structured` |
| Shared schema / DSL / Runtime namespaces remain separate | PASS | `contracts-v0.1` / `0.1` / `0.1.0` constants and documentation |
| Correction stayed inside Issue #5 writable scope | PASS | diff changes only four authorized paths |

Issue #5 disposition: **RESOLVED / CLOSED**.

This acceptance resolves only the static implementation-alignment finding. It does not constitute executable evidence and does not promote Gate A.

## Frozen Slice 1 executable integration candidate

Composition:

```text
main ba2affa62c89d58bb9ffac054963579e434896e1
+ E1 f962d475b88881c5ae8ceee05e4d952c830b545a
+ E2 b1e6920ebb29a84916f99a06fe758529d8fbf3ec
+ E3 bead77acde5bfb30f4e6a8065d897a938cef840c
```

Frozen assembled branch:

- branch: `integration/slice1-executable-candidate`
- candidate HEAD: `5547fdb4f2ab7f837e09b89368d274fa1cadce8e`

Assembly integrity:

- candidate is based on the Slice 0 `main` baseline through E3 HEAD;
- main -> candidate diff contains exactly 27 Slice 1 files = E1 8 + E2 8 + E3 11;
- no `contracts/`, ADR, release-gate, Risk, Execution, Platform, or GitHub workflow file is changed;
- candidate `src/market_data/candle.py` blob matches E1 reviewed implementation;
- candidate `src/strategy/runtime.py` blob matches corrected E2 revision;
- candidate `src/backtest/e2_runtime.py` blob matches E3 concrete E2 binding revision.

## Local checkout — preferred

The candidate is already assembled. Product Owner-approved local verification should use the frozen candidate SHA directly:

```powershell
git fetch origin --prune
git switch --detach 5547fdb4f2ab7f837e09b89368d274fa1cadce8e
git rev-parse HEAD
```

Expected `git rev-parse HEAD`:

```text
5547fdb4f2ab7f837e09b89368d274fa1cadce8e
```

Optional local named branch:

```powershell
git switch -c local/slice1-verification 5547fdb4f2ab7f837e09b89368d274fa1cadce8e
```

Do not merge or modify the candidate before recording verification evidence. If local fixes are needed after a failure, preserve the failing candidate revision and open a bounded correction path.

## Required local verification commands

Set source path once:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
```

E1:

```powershell
python -m unittest discover -s tests/market_data -v
python -m compileall -q src/market_data tests/market_data
```

E2:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

E3:

```powershell
python -m unittest discover -s tests/backtest -p "test_costs.py" -v
python -m unittest discover -s tests/backtest -p "test_metrics.py" -v
python -m unittest discover -s tests/backtest -p "test_replay.py" -v
```

Integrated Research Skeleton:

```powershell
python tests/backtest/test_real_e2_research_skeleton.py -v
```

E1 public Pionex four-timeframe smoke check:

```powershell
python -c "from datetime import datetime,timedelta,timezone; from market_data import PionexPublicKlineSource,load_pionex_historical_candles; src=PionexPublicKlineSource(); now=int(datetime.now(timezone.utc).timestamp()); specs={'1m':60,'15m':900,'1h':3600,'4h':14400}; [(lambda end,tf,sec: print(tf,len(load_pionex_historical_candles(src,symbol='BTC_USDT_PERP',timeframe=tf,start=end-timedelta(seconds=sec*2),end=end))))(datetime.fromtimestamp((now//sec)*sec,tz=timezone.utc),tf,sec) for tf,sec in specs.items()]"
```

Smoke acceptance: each timeframe returns exactly two ascending closed canonical Candles, or the command fails explicitly with a typed E1 error. API/network failure is not PASS.

## Execution policy

All executable verification is LOCAL ONLY in a Product Owner-approved checkout/environment.

Forbidden:

- GitHub Actions
- GitHub CI
- GitHub-hosted runner
- GitHub-triggered runner
- GitHub-hosted tests/backtests/E2E/bug reproduction

Current executable status remains: **NOT_RUN**.

## Gate disposition

- Issue #5 static acceptance: `PASS / RESOLVED`
- Slice 1 static Contract / Architecture blockers: no remaining blocker identified in the reviewed E1/E2/E3 source pins
- Slice 1 executable candidate: `FROZEN`
- executable tests: `NOT_RUN`
- E1 public Pionex smoke: `NOT_RUN`
- Gate A `RESEARCH_READY`: `BLOCKED`

Gate A may be reconsidered only after real local evidence is recorded against candidate HEAD `5547fdb4f2ab7f837e09b89368d274fa1cadce8e`.

## Codex

No Codex ticket. Issue #5 was E2 domain alignment to an explicit shared contract and is resolved statically.
