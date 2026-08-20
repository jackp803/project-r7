# Slice 1 Integration Manifest

> Owner: E7 Integration / Architecture / System QA / Release Engineer
> Branch: `integration/slice1-research-skeleton`
> Static status: `ACCEPTED`
> Candidate status: `FROZEN`
> Executable status: `NOT_RUN`
> Gate A: `BLOCKED`

## Baseline

- `main`: `ba2affa62c89d58bb9ffac054963579e434896e1`
- Contract: `contracts-v0.1`
- ADR: `ADR-0001`
- Common construction map: main baseline
- Release gates: main baseline

## Accepted source pins

- E1: `f962d475b88881c5ae8ceee05e4d952c830b545a`
- E2 corrected for Issue #5: `b1e6920ebb29a84916f99a06fe758529d8fbf3ec`
- E3 HEAD: `bead77acde5bfb30f4e6a8065d897a938cef840c`
- E3 concrete E2 binding: `da9fa922f7c6292d4dd801033e70cfe6943249c2`

Rejected E2 pin `90262a0dacc7a8f3aa798de1b6f1d1b28fd88f6c` is superseded and must not be used for Slice 1 integration.

Issue #5 / `E2-SCHEMA-001` static acceptance is complete and the issue is closed. Detailed acceptance evidence is recorded in `status/e7/SLICE1_ISSUE5_REREVIEW.md`.

## Frozen executable integration candidate

Composition:

```text
main ba2affa62c89d58bb9ffac054963579e434896e1
+ E1 f962d475b88881c5ae8ceee05e4d952c830b545a
+ E2 b1e6920ebb29a84916f99a06fe758529d8fbf3ec
+ E3 bead77acde5bfb30f4e6a8065d897a938cef840c
```

Frozen assembled candidate:

- branch: `integration/slice1-executable-candidate`
- HEAD: `5547fdb4f2ab7f837e09b89368d274fa1cadce8e`

Static assembly integrity:

- exactly 27 Slice 1 files over main = E1 8 + E2 8 + E3 11;
- no shared contract, ADR, release-gate, Risk, Execution, Platform, or GitHub workflow changes;
- E1 Candle blob matches the reviewed E1 revision;
- E2 runtime blob matches the corrected E2 revision;
- E3 real-E2 binding blob matches the reviewed E3 binding revision.

## Preferred local checkout

```powershell
git fetch origin --prune
git switch --detach 5547fdb4f2ab7f837e09b89368d274fa1cadce8e
git rev-parse HEAD
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
```

Expected HEAD:

```text
5547fdb4f2ab7f837e09b89368d274fa1cadce8e
```

## Required local verification

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

Smoke acceptance: each timeframe returns exactly two ascending closed canonical Candles or fails explicitly with a typed E1 error. API/network failure is not PASS.

## Policy

All executable verification above is LOCAL ONLY in a Product Owner-approved checkout/environment.

Forbidden:

- GitHub Actions
- GitHub CI
- GitHub-hosted runner
- GitHub-triggered runner
- GitHub-hosted tests/backtests/E2E/bug reproduction

Until real local commands execute against the frozen candidate and their results are recorded, executable evidence remains `NOT_RUN`.

## Gate disposition

- Issue #5 static acceptance: `PASS / RESOLVED`
- Slice 1 static Contract / Architecture review: `ACCEPTED`
- Slice 1 executable candidate: `FROZEN`
- Local tests: `NOT_RUN`
- E1 Pionex smoke: `NOT_RUN`
- Gate A `RESEARCH_READY`: `BLOCKED`
- Gate B/C/D: unchanged / `BLOCKED`

Static acceptance and candidate freeze do not imply Gate A PASS.

## Codex

No Codex ticket exists for Issue #5 or this candidate freeze.
