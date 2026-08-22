# Gate A Local Verification Plan

> Owner: E7 Integration / Architecture / System QA  
> Contract baseline: `contracts-v0.1`  
> Execution policy: Product Owner-approved **local-only** environment  
> GitHub Actions / CI / hosted runners / GitHub-triggered self-hosted compute: **FORBIDDEN**

## Purpose

This runbook defines the exact executable evidence required to move the current Gate A research/integration platform from static readiness toward an E7/PM Gate A PASS decision.

The Gate A research path is:

```text
E1 canonical closed Candle / historical market data
    -> E2 parse_strategy_definition + StrategyRuntime
    -> E3 deterministic historical replay
    -> canonical BacktestResult
    -> E3 explicit OOS ValidationDecision policy/context
    -> canonical ValidationDecision
    -> E6 canonical evidence validation / Registry persistence authority
```

Gate A does **not** include E4 provider execution, OKX private APIs, E5 live risk/position lifecycle, PAPER, SHADOW, LIVE, credentials, or Slice 3 execution flow.

## Evidence classes

Keep these meanings separate:

- `PASS STATIC`: source/test definitions are structurally coherent. No project code was executed.
- executable `PASS`: an approved local command actually ran and passed at an exact revision/environment.
- synthetic fixture: test-only data or metadata used to exercise an interface. It is never project execution evidence.
- real E3 evidence: a BacktestResult / ValidationDecision produced by an approved local research run and, when persisted for authority, recorded with the required provenance.
- Gate A PASS: an E7/PM release-gate decision after reviewing the approved local evidence. Test output does not self-authorize the gate.

## Required checkout state

Run only from the repository root of the exact candidate `main` revision approved for Gate A execution.

Before any test command, capture:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
New-Item -ItemType Directory -Force -Path ".gate-a-evidence" | Out-Null
Start-Transcript -Path ".gate-a-evidence\gate-a-local-verification.log" -Force

git rev-parse HEAD
git status --short
python --version
python -c "import platform,sys; print(sys.executable); print(platform.platform()); print(sys.version)"
```

Required precondition:

- `git rev-parse HEAD` equals the exact revision authorized by the Product Owner for the run;
- the working tree state is captured and any local modification is reviewed before evidence is accepted;
- `PYTHONPATH` points to this checkout's `src` directory;
- the run is local/non-GitHub and the environment identity is preserved in the transcript.

## Ordered Gate A execution matrix

Run in this order. Stop and preserve the transcript if a required suite fails; do not reinterpret a failure as PASS.

### 1. E1 market-data boundary

Command:

```powershell
python -m unittest discover -s tests/market_data -p "test_*.py" -v
```

Purpose:

- supported `market_data` package/import integrity;
- canonical Candle module/type ownership;
- UTC/RFC3339 and Decimal interchange semantics;
- supported timeframe mapping;
- historical sequence ordering/pagination;
- missing/gap/unclosed data fail closed.

Expected evidence: suite PASS with no failures/errors.

### 2. E2 indicator semantics

Command:

```powershell
python -m unittest discover -s tests/indicators -p "test_*.py" -v
```

Purpose:

- exact Decimal SMA behavior;
- insufficient-history behavior;
- binary-float rejection.

Expected evidence: suite PASS with no failures/errors.

### 3. E2 StrategyDefinition / StrategyRuntime

Command:

```powershell
python -m unittest discover -s tests/strategy -p "test_*.py" -v
```

Purpose:

- `contracts-v0.1` StrategyDefinition parsing;
- immutable content-hash/runtime compatibility;
- supported primitive/operator semantics;
- deterministic LONG/SHORT/NO_TRADE behavior;
- future/unclosed Candle isolation;
- TradeIntent boundary tests present in the suite do not grant Gate A execution authority.

Expected evidence: suite PASS with no failures/errors.

### 4. E3 historical replay / BacktestResult

Command:

```powershell
python -m unittest discover -s tests/backtest -p "test_*.py" -v
```

Purpose:

- actual E2 runtime consumption;
- closed-prefix no-look-ahead;
- next-open entry/opposite-exit timing;
- conservative stop/target ambiguity;
- fees, adverse slippage, deterministic funding;
- metrics and reproducibility identity;
- canonical BacktestResult serialization and E6 validator compatibility.

Expected evidence: suite PASS with no failures/errors.

### 5. E3 OOS ValidationDecision

Command:

```powershell
python -m unittest discover -s tests/validation -p "test_*.py" -v
```

Purpose:

- fail-closed BacktestResult intake;
- exact strategy/backtest/OOS dataset binding;
- explicit caller-supplied OOS policy thresholds;
- deterministic BLOCKED / NOT_RUN / FAIL / PASS precedence;
- deterministic reason codes and decision identity;
- canonical ValidationDecision compatibility;
- synthetic `EXECUTED`/PASS values remain research/test data, not E6 verification metadata.

Expected evidence: suite PASS with no failures/errors.

### 6. E6 Registry / canonical evidence service gates

Command:

```powershell
python -m unittest discover -s tests/registry -p "test_*.py" -v
```

Purpose:

- Strategy inbox/immutability/idempotency;
- canonical BacktestResult and ValidationDecision validation;
- E2 compatibility gating;
- BacktestResult-alone and NOT_RUN decision non-promotion;
- local-PASS metadata requirements and exact evidence bindings;
- early lifecycle cap.

Expected evidence: suite PASS with no failures/errors.

### 7. E6 persistence / authority / storage guards

Command:

```powershell
python -m unittest discover -s tests/storage -p "test_*.py" -v
```

Purpose:

- supported safe storage factory boundary;
- migration/idempotence/restart definitions;
- initial DRAFT/revision-0 guard;
- immutable strategy content;
- append-only lifecycle history;
- exact legal-edge and forbidden-edge enforcement;
- durable E2/E3 authority revalidation;
- rollback/state/revision preservation;
- synthetic positive authority fixtures remain test-only.

Expected evidence: suite PASS with no failures/errors.

### 8. E7 cross-role Gate A pipeline

Command:

```powershell
python -m unittest discover -s tests/integration -p "test_*.py" -v
```

Current Gate A definition:

```text
tests/integration/test_gate_a_research_pipeline.py
```

Purpose:

- real supported E1 Candle -> real E2 parser/runtime -> E3 replay;
- canonical BacktestResult -> E3 OOS ValidationDecision;
- E6 canonical validator compatibility;
- E6 safe `open_sqlite_platform` composition;
- E6 durable evidence ingest;
- explicit proof that a synthetic E3 `PASS` payload with `execution_state=EXECUTED` still cannot authorize CANDIDATE while durable E3 evidence remains `NOT_RUN`.

The test-only E2 compatibility fixture contains synthetic `PASS / LOCAL_EXECUTION` metadata solely to exercise the E6 `DRAFT -> BACKTESTING` path in an in-memory database. It is labelled `TEST_ONLY` and is not Gate A execution evidence.

Expected evidence: suite PASS with no failures/errors.

## End-of-run capture

After all required commands:

```powershell
Stop-Transcript
```

Preserve at minimum:

```text
main/source revision:
environment / OS:
Python executable:
Python version:
PYTHONPATH:
exact command list:
E1 market_data result:
E2 indicators result:
E2 strategy result:
E3 backtest result:
E3 validation result:
E6 registry result:
E6 storage result:
E7 integration result:
transcript/log reference:
run timestamp/timezone:
Product Owner approval reference:
GitHub compute used: NO
```

## Gate A PASS evidence rule

A future local run does not automatically change Gate A to PASS. E7/PM must review the evidence and confirm:

1. the run used the exact approved `main` revision;
2. every required suite above passed locally with no failure/error;
3. environment/runtime identity and exact commands are recorded;
4. result/log references are retained;
5. no GitHub Actions, hosted runner, GitHub-triggered self-hosted compute, provider/private API, credential, PAPER/SHADOW/LIVE action, or live execution occurred;
6. no test-only synthetic fixture is cited as real E2/E3 project evidence;
7. any real durable E3 BacktestResult / ValidationDecision later persisted for lifecycle authority is bound to the exact strategy/content/backtest identities and carries E6-required:

```text
verification_status = PASS
verification_kind   = LOCAL_EXECUTION
source_revision     = non-empty exact source revision
environment         = non-empty approved local environment identity
command             = non-empty exact executed command
result_ref          = non-empty retained result/log reference
```

8. `BACKTESTING -> CANDIDATE` is considered only through the E6 authority path; a BacktestResult, E3 `execution_state=EXECUTED`, or synthetic ValidationDecision `PASS` is never sufficient by itself.

Until E7/PM accepts that local evidence, Gate A remains `BLOCKED`. Gate B/C/D and PAPER/SHADOW/LIVE remain blocked/unauthorized independently.
