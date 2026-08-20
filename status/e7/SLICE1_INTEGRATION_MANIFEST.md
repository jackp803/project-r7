# Slice 1 Integration Manifest

> Owner: E7 Integration / Architecture / System QA / Release Engineer
> Branch: `integration/slice1-research-skeleton`
> Status: `BLOCKED_STATIC`
> Executable status: `NOT_RUN`

## Baseline

- `main`: `ba2affa62c89d58bb9ffac054963579e434896e1`
- Contract: `contracts-v0.1`
- ADR: `ADR-0001`
- Common construction map: main baseline
- Release gates: main baseline

## Reviewed source pins

- E1 accepted static source: `f962d475b88881c5ae8ceee05e4d952c830b545a`
- E2 reviewed source: `90262a0dacc7a8f3aa798de1b6f1d1b28fd88f6c` — **NOT ACCEPTED for integration due E2-SCHEMA-001**
- E3 accepted static HEAD: `bead77acde5bfb30f4e6a8065d897a938cef840c`
- E3 concrete E2 binding: `da9fa922f7c6292d4dd801033e70cfe6943249c2`

## Integration rule

E7 will not materialize the combined executable source tree until E2 supplies a bounded correction for `E2-SCHEMA-001`.

The replacement E2 revision must preserve:

- E2 runtime family/version unless E2 intentionally versions it;
- existing StrategyDefinition DSL semantics;
- deterministic runtime behavior;
- actual E2 public binding expected by E3;
- `contracts-v0.1` shared contract unchanged.

It must add exact shared schema compatibility enforcement for StrategyDefinition, consumed visible Candle, and produced Signal, and align E2 fixtures to `contracts-v0.1`.

## Candidate composition after correction

```text
main ba2affa62c89d58bb9ffac054963579e434896e1
+ E1 f962d475b88881c5ae8ceee05e4d952c830b545a
+ E2 <corrected revision for E2-SCHEMA-001>
+ E3 bead77acde5bfb30f4e6a8065d897a938cef840c
= Slice 1 executable integration candidate
```

## Required local verification after source assembly

E1:

```powershell
python -m unittest discover -s tests/market_data -v
python -m compileall -q src/market_data tests/market_data
```

E2:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
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
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python tests/backtest/test_real_e2_research_skeleton.py -v
```

Also required: E1 public Pionex four-timeframe smoke check for `BTC_USDT_PERP` on `1m`, `15m`, `1h`, and `4h`.

## Policy

All commands above are LOCAL ONLY in a Product Owner-approved checkout/environment.

Forbidden:

- GitHub Actions
- GitHub CI
- GitHub-hosted runner
- GitHub-triggered runner
- GitHub-hosted backtest/E2E/bug reproduction

Until those commands are executed locally and recorded, executable evidence remains `NOT_RUN`.

## Gate disposition

- Slice 1 static integration: `BLOCKED`
- Slice 1 executable integration: `NOT_RUN`
- Gate A `RESEARCH_READY`: `BLOCKED`

No Codex ticket exists for this manifest.
