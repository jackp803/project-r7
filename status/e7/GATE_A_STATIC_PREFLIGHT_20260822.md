# E7 Gate A Static Preflight — 2026-08-22

- task_id: `E7-20260822-015`
- owner: `E7 Integration / Architecture / System QA`
- reviewed_current_main: `3504c75cb88e068d209aeb91af3450481ef74191`
- target_branch: `agent/e7-gate-a-preflight-20260822`
- contract_baseline: `contracts-v0.1`
- executable_verification: `NOT_RUN`
- gate_a: `BLOCKED / LOCAL EXECUTION NOT YET PERFORMED`
- static_preflight_disposition: `STATIC_PREFLIGHT_READY_LOCAL_EXECUTION_REQUIRED`
- gate_b: `BLOCKED / UNCHANGED`
- gate_c: `BLOCKED / UNCHANGED`
- gate_d: `BLOCKED / UNCHANGED`
- paper_shadow_live: `UNAUTHORIZED / UNCHANGED`

## Executive disposition

The current merged research platform is structurally ready for a future Product Owner-approved **local-only** Gate A execution run.

No E1-E6 production source or shared-contract defect was found that would prevent a meaningful local Gate A verification run.

The only missing static test-definition surface found at preflight start was the absence of an executable cross-role Gate A test under `tests/integration/**`. E7 added one minimal deterministic definition:

```text
tests/integration/test_gate_a_research_pipeline.py
```

It uses the supported E1/E2/E3/E6 interfaces and does not duplicate their production semantics. It was **not executed** in this task.

Final source disposition:

```text
STATIC_PREFLIGHT_READY_LOCAL_EXECUTION_REQUIRED
```

This is not Gate A PASS.

## Current-main component inventory

Reviewed source revision:

```text
3504c75cb88e068d209aeb91af3450481ef74191
```

Accepted merged/current components:

### E1 market data

- PR #21 merge: `1158a777a2830afc37066ef62ebefe624a9ca28e`
- canonical Candle blob: `5605830b4da4fbe10e94cff72794a495db9ebf6e`
- public package exposes `Candle` / `CONTRACT_SCHEMA_VERSION`
- schema: `contracts-v0.1`

### E2 strategy runtime

- current runtime blob: `3491f1784fb27d17f36f0afc7397bf8f9e48ad8b`
- runtime family: `project-r7-e2-strategy-runtime`
- runtime version: `0.1.0`
- public path remains `parse_strategy_definition` + `StrategyRuntime`

### E3 historical replay

- PR #22 merge: `7f70d737ffb1276e251bc552ca9e6d39bb44393d`
- E7 replay review evidence PR #23 merge: `d8ab1ac540e954d818bbdc271577e945dbc42b72`
- replay blob: `bf2b013a1cacd7af93f71c977320dda7d3382375`
- E2 adapter blob: `c603233b53217118f6979f9372477de65101938a`

### E3 OOS ValidationDecision

- PR #24 merge: `2ff34a894c4ac16bc989ac701d7e8a9b42eb8692`
- E7 OOS review evidence PR #25 merge: `2b0b725446350b04b9950820ce79a2b919587301`
- OOS producer blob: `5f7d20ab0401287b642aa96db0bbf73e51078a25`

### E6 Registry / evidence persistence

- PR #16 merged: `666323f6be0e8428d7307c222ffe91eacd2f8419`
- canonical contract validator blob: `954d21c021c0885554ee650acced17610d958a0e`
- service-base blob: `3889ac156358f58c5fc3380865ad73844b874c3c`
- supported SQLite factory blob: `9dd16aded85bde6533f8bed138ee0ac705f83416`
- internal SQLite persistence blob: `d63cabbb708d9e65916df802fd69eb66473907cd`

## Gate A dependency direction

Current source preserves the required direction:

```text
E1 Candle / historical data
    -> E2 StrategyDefinition parser + StrategyRuntime
    -> E3 replay
    -> BacktestResult
    -> E3 OOS validation
    -> ValidationDecision
    -> E6 canonical evidence validation / persistence authority
```

### E3 replay -> E2

`src/backtest/e2_runtime.py` imports the public E2 runtime package and delegates every replay evaluation through:

```text
parse_strategy_definition(strategy_definition)
StrategyRuntime.evaluate(parsed_strategy, closed_history, evaluated_at)
```

No E3 copy of SMA/indicator/DSL/operator/strategy-decision semantics was found.

Disposition: `PASS STATIC`.

### E3 OOS -> BacktestResult

`src/validation/oos.py` consumes a canonical BacktestResult mapping / `to_contract()` result and implements only E3 research validation policy/context logic.

It does not import Registry/storage/E6 production code.

Disposition: `PASS STATIC`.

### E6 authority

E6 remains authoritative for durable evidence and lifecycle mutation.

Supported storage composition remains:

```text
storage.open_sqlite_platform(...)
    -> StrategyPlatformService
```

Raw SQLite connection/writer mechanics are internal and are not the supported production API.

A canonical BacktestResult or ValidationDecision payload alone cannot promote lifecycle. `BACKTESTING -> CANDIDATE` requires separately stored, bound E3 BacktestResult + ValidationDecision evidence with complete E6-required `PASS / LOCAL_EXECUTION` metadata.

Disposition: `PASS STATIC`.

## Cross-contract compatibility

The full Gate A path remains aligned to `contracts-v0.1`:

### Time

- canonical UTC internal semantics;
- RFC3339 `...Z` interchange;
- E1 closed Candle boundaries;
- E3 BacktestResult dataset range and created timestamp;
- E3 ValidationDecision `decided_at`;
- E6 validators require UTC/RFC3339.

### Financial values

- executable research arithmetic uses Decimal semantics;
- canonical BacktestResult financial interchange uses base-10 decimal strings;
- binary float is rejected on relevant E1/E2/E3 boundaries;
- E6 canonical BacktestResult validator rejects non-string/non-finite decimal interchange;
- `profit_factor = null` remains supported where defined.

### Identity

- immutable `(strategy_id, strategy_version)`;
- strategy content hash preserved through replay evidence;
- BacktestResult binds exact strategy/runtime/dataset/cost identity;
- ValidationDecision binds exact strategy/version/BacktestResult and explicit OOS/policy identity;
- E6 durable evidence revalidates exact strategy/content/backtest parent bindings.

### Enums / fail closed

- unsupported schemas/states do not become PASS;
- E3 OOS precedence remains structural `BLOCKED` before `NOT_RUN`, `FAIL`, `PASS`;
- E6 promotion requires canonical decision `PASS` plus durable local execution provenance.

Disposition: `PASS STATIC`.

## Current deterministic test-definition inventory

### E1 — `tests/market_data/**`

Present:

```text
test_candle_and_okx.py
test_historical_sequence_okx.py
test_import_integrity.py
```

Static coverage includes package/module integrity, Candle Decimal/UTC behavior, timeframe/provider mapping, historical ordering/pagination, missing gaps, and unclosed-data rejection.

Disposition: `SUFFICIENT FOR GATE A LOCAL MATRIX / PASS STATIC`.

### E2 — `tests/indicators/**` + `tests/strategy/**`

Present:

```text
tests/indicators/test_sma.py
tests/strategy/test_slice1_runtime.py
tests/strategy/test_trade_intent.py
```

Static coverage includes Decimal SMA, float rejection, parser/schema/content-hash/runtime compatibility, deterministic Signal semantics, future/unclosed Candle isolation, and current strategy boundary behavior.

Disposition: `SUFFICIENT FOR GATE A LOCAL MATRIX / PASS STATIC`.

### E3 replay — `tests/backtest/**`

Present:

```text
test_costs.py
test_metrics.py
test_real_e2_research_skeleton.py
test_replay.py
```

Static coverage includes real E1 Candle use, actual E2 runtime path, no-look-ahead, next-open timing, final-bar no-fill, conservative stop/target ambiguity, fees/slippage/funding, metrics/reproducibility, deterministic result identity, and E6 BacktestResult validator compatibility.

Disposition: `SUFFICIENT FOR GATE A LOCAL MATRIX / PASS STATIC`.

### E3 OOS — `tests/validation/**`

Present:

```text
test_oos_validation.py
```

Static coverage includes canonical BacktestResult intake, OOS/context/policy binding, deterministic outcomes/reasons/identity, float rejection, profit-factor-null threshold behavior, and E6 ValidationDecision validator compatibility.

Disposition: `SUFFICIENT FOR GATE A LOCAL MATRIX / PASS STATIC`.

### E6 Registry — `tests/registry/**`

Present:

```text
test_evidence_contract_validation.py
test_strategy_inbox.py
test_validation_lifecycle.py
```

Static coverage includes canonical evidence validation, inbox/identity/immutability, E2 compatibility gates, BacktestResult-alone non-promotion, ValidationDecision local-PASS requirements, exact evidence bindings, rejection persistence, and early lifecycle cap.

Disposition: `SUFFICIENT FOR GATE A LOCAL MATRIX / PASS STATIC`.

### E6 storage — `tests/storage/**`

Present:

```text
test_lifecycle_evidence_authority.py
test_public_persistence_boundary.py
test_registry_persistence.py
```

Static coverage includes supported public storage boundary, durable evidence authority, initial projection, exact transition edges, forbidden transitions, append-only history, rollback, restart/migration definitions, and positive/negative synthetic authority fixtures.

Disposition: `SUFFICIENT FOR GATE A LOCAL MATRIX / PASS STATIC`.

### E7 cross-role integration — `tests/integration/**`

Preflight-start finding:

```text
NO EXECUTABLE .py CROSS-ROLE GATE A PIPELINE DEFINITION
```

E7 correction added:

```text
tests/integration/test_gate_a_research_pipeline.py
commit dd2d454bec1d0855bd25d74b672b6a1ed42f7732
```

Definition uses:

- real E1 `Candle`;
- real E2 `compute_content_hash`, `parse_strategy_definition`, `StrategyRuntime` through E3 binding;
- real E3 replay and OOS producer;
- real E6 canonical validators;
- real supported `storage.open_sqlite_platform` service composition;
- in-memory SQLite only when eventually executed locally;
- test-only synthetic E2 compatibility metadata clearly labelled `TEST_ONLY`;
- E3 synthetic OOS PASS payload;
- E6 durable BacktestResult/ValidationDecision deliberately recorded `NOT_RUN`;
- assertion that `mark_candidate` remains rejected despite E3 `PASS` + `EXECUTED` payload fields.

No production semantics are copied.

Disposition: `GAP CLOSED BY E7 TEST DEFINITION / PASS STATIC / NOT_RUN`.

## Gate A exact local-only command matrix

PowerShell setup:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
New-Item -ItemType Directory -Force -Path ".gate-a-evidence" | Out-Null
Start-Transcript -Path ".gate-a-evidence\gate-a-local-verification.log" -Force

git rev-parse HEAD
git status --short
python --version
python -c "import platform,sys; print(sys.executable); print(platform.platform()); print(sys.version)"
```

Required suite order:

```powershell
python -m unittest discover -s tests/market_data -p "test_*.py" -v
python -m unittest discover -s tests/indicators -p "test_*.py" -v
python -m unittest discover -s tests/strategy -p "test_*.py" -v
python -m unittest discover -s tests/backtest -p "test_*.py" -v
python -m unittest discover -s tests/validation -p "test_*.py" -v
python -m unittest discover -s tests/registry -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/integration -p "test_*.py" -v
```

End capture:

```powershell
Stop-Transcript
```

Reusable detailed runbook:

```text
docs/integration/GATE_A_LOCAL_VERIFICATION_PLAN.md
```

Runbook commit:

```text
32021832cebbf2084efa1304e9a03b813801ef1d
```

## Evidence required before Gate A PASS review

A future approved local run must capture at minimum:

- exact approved `main` source revision;
- dirty/clean working-tree state;
- OS/runtime/environment identity;
- Python executable/version;
- exact PYTHONPATH;
- exact commands executed;
- per-suite PASS/FAIL/error results;
- retained result/transcript/log reference;
- run timestamp/timezone;
- Product Owner approval reference;
- explicit `GitHub compute used = NO`.

All required suites must PASS before a Gate A PASS review can begin.

If real E3 BacktestResult / ValidationDecision evidence is persisted or used for lifecycle authority, E6 additionally requires both exact canonical bindings and:

```text
verification_status = PASS
verification_kind   = LOCAL_EXECUTION
source_revision     = non-empty exact revision
environment         = non-empty approved local environment
command             = non-empty exact executed command
result_ref          = non-empty retained result/log reference
```

A BacktestResult, synthetic ValidationDecision PASS, or E3 `execution_state=EXECUTED` does not satisfy that durable authority by itself.

## Synthetic fixture rule

Synthetic PASS/local metadata appears in existing E6 tests and the new E7 integration definition only to exercise code paths.

It is never:

- executable project evidence;
- real E2/E3 verification;
- a real strategy ValidationDecision PASS;
- Gate A PASS evidence;
- CANDIDATE/PAPER/SHADOW/LIVE authorization.

## Provider / execution independence

No Gate A suite requires:

- E4 broker execution;
- OKX private APIs;
- provider credentials;
- E5 live risk/position action;
- PAPER;
- SHADOW;
- LIVE;
- GitHub Actions/CI;
- hosted runner;
- GitHub-triggered self-hosted runner.

E1 historical provider normalization is tested with deterministic local fixtures/fakes; Gate A does not require a live provider request.

Disposition: `PASS STATIC`.

## Source blockers

```text
NONE FOUND
```

No production defect was identified that prevents a meaningful local Gate A run.

No Codex ticket was created because no defect was reproduced in an approved local environment.

## Verification state

```text
project tests executed        = NO
imports/probes executed       = NO
backtests executed            = NO
validation run executed       = NO
migrations executed           = NO
provider requests sent        = NO
GitHub Actions/CI used        = NO
hosted runner used            = NO
GitHub-triggered compute used = NO
real strategy PASS created    = NO
durable real E3 local evidence= NO
Registry project promotion    = NONE
```

## Final disposition

```text
STATIC_PREFLIGHT_READY_LOCAL_EXECUTION_REQUIRED
```

Gate A remains `BLOCKED` until a Product Owner-approved local execution run is performed and E7/PM reviews the required evidence.

Gate B/C/D remain `BLOCKED`.

PAPER/SHADOW/LIVE remain unauthorized.
