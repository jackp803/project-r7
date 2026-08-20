# Handoff — E6 Evidence Contract Correction

**From:** E6 / Platform / Storage / Strategy Registry / Dashboard Engineer  
**To:** E7 / Integration / Architecture / System QA / Release Engineer  
**Task:** `E6-20260820-002`  
**Branch:** `agent/e6-platform`  
**Contract baseline:** `contracts-v0.1`  
**Finding:** `E6-EVIDENCE-CONTRACT-001`  
**Date:** 2026-08-20

## 1. Objective

Correct the E6 evidence-ingest boundary so incomplete or non-canonical E3-shaped objects cannot become promotable Registry evidence merely because a caller supplies `PASS` / `LOCAL_EXECUTION` metadata.

Scope remains the existing early Slice 2 path:

```text
StrategyDefinition intake
-> E2 compatibility boundary
-> BacktestResult / ValidationDecision evidence persistence
-> Strategy Registry
-> DRAFT -> BACKTESTING -> REJECTED | CANDIDATE
```

No PAPER / READY_FOR_APPROVAL / APPROVED / LIVE behavior is introduced.

## 2. Branch synchronization

Before correction, E6 synchronized `agent/e6-platform` with the then-latest `main` without rewriting history.

- E6 pre-sync HEAD: `13c67d4fa91e1cf4cc3b5a394c7ce88de0902321`
- main synchronized revision: `4c531adc575ddd43f095ab8eabba3cae62ecc7b2`
- merge commit: `6f15f8190a597cdf25284f00eb7b84b3c34f73a0`
- force update: **NO**
- history rewrite/rebase: **NO**
- post-correction static compare: `main` is merge-base; branch `behind_by=0`

The merge tree used current `main` as the base and restored only existing E6-owned branch paths, preserving coordination/review/product material from `main` and all prior E6 history.

## 3. Correction implemented

### Canonical contract-shape validator

Added `src/registry/contract_validation.py`.

For `BacktestResult`, E6 now requires every `contracts-v0.1` identity/reproducibility field before evidence persistence:

- `schema_version`
- `backtest_result_id`
- `strategy_id`
- `strategy_version`
- `strategy_content_hash`
- `runtime_version`
- `dataset_id`
- `dataset_hash`
- `dataset_start`
- `dataset_end`
- `cost_model_version`
- `created_at`

It also requires every core metric:

- `total_trades`
- `wins`
- `losses`
- `breakeven`
- `gross_pnl`
- `net_pnl`
- `total_fees`
- `profit_factor`
- `expectancy`
- `max_drawdown`
- `max_consecutive_losses`

Contract-shape checks include:

- exact shared schema `contracts-v0.1`;
- stable IDs / versions / hashes as non-empty strings;
- RFC 3339 UTC timestamps ending in `Z`;
- dataset start not after dataset end;
- count metrics as non-negative integers, excluding booleans;
- financial metrics as finite base-10 decimal strings at interchange boundaries;
- `profit_factor` may be `null` when mathematically undefined, matching the current E3 Slice 1 representation noted for review.

These checks do not calculate or judge E3 statistics.

### ValidationDecision contract gate

For `ValidationDecision`, E6 now requires:

- `schema_version`
- `validation_decision_id`
- `strategy_id`
- `strategy_version`
- `backtest_result_id`
- `validation_policy_version`
- `decision`
- `reason_codes`
- `decided_at`

Additional contract checks:

- decision is exactly `PASS | FAIL | BLOCKED | NOT_RUN`;
- `reason_codes` is a sequence of non-empty strings;
- `decided_at` is RFC 3339 UTC;
- existing E6 service binding still requires the exact registered strategy version/content hash through the BacktestResult parent;
- existing parent binding still requires `ValidationDecision.backtest_result_id` to equal the persisted BacktestResult object ID.

E6 does **not** reproduce E3 validation policy, thresholds, robustness analysis, Monte Carlo, walk-forward logic, or any statistical PASS methodology.

### Caller metadata cannot bypass shape validation

The public `StrategyPlatformService` now runs canonical contract validation before delegating to the existing persistence/binding implementation.

Caller-provided verification metadata is also enum-checked. A caller may not turn a missing-field or non-canonical shared object into evidence by passing:

```text
verification_status = PASS
verification_kind   = LOCAL_EXECUTION
```

The existing `mark_candidate(...)` gate remains unchanged and still separately requires stored E3 `ValidationDecision.decision=PASS`, exact evidence binding, and complete local PASS metadata for both ValidationDecision and its BacktestResult parent.

## 4. Implementation structure

To avoid a large rewrite of the already-reviewed early Slice 2 lifecycle service:

- the prior implementation is preserved verbatim as `src/registry/service_base.py`;
- `src/registry/service.py` is the public fail-closed wrapper;
- only `record_backtest_result(...)` and `record_validation_decision(...)` are strengthened before delegating to the preserved implementation.

This correction does not alter storage schema, migrations, Registry identity, transition graph, E2 compatibility behavior, or audit semantics.

## 5. Tests defined

Added `tests/registry/test_evidence_contract_validation.py`.

Deterministic local-only definitions cover:

1. every required BacktestResult identity/reproducibility field omitted one-at-a-time -> rejected before persistence even with synthetic local PASS metadata;
2. every required BacktestResult core metric omitted one-at-a-time -> rejected before persistence;
3. binary-float financial metric -> rejected at interchange boundary;
4. non-UTC timestamp -> rejected;
5. every required ValidationDecision field omitted one-at-a-time -> rejected before persistence;
6. non-canonical ValidationDecision enum -> rejected;
7. invalid `reason_codes` shape -> rejected;
8. valid-looking BacktestResult with synthetic local PASS metadata alone -> cannot be supplied as candidate evidence without ValidationDecision;
9. public lifecycle surface still exposes no approval/live/generic-transition path.

Existing E6 tests continue to define:

- wrong strategy content hash rejection;
- BacktestResult / ValidationDecision parent binding;
- `NOT_RUN` evidence cannot promote;
- Candidate requires separate local PASS evidence for BacktestResult and ValidationDecision;
- rejected strategy retention/audit;
- persistence/migration/restart behavior.

Synthetic PASS metadata in test definitions is only a gate test fixture. It is not project executable evidence.

## 6. Files changed for this task

Correction-specific files:

- `src/registry/contract_validation.py` — new canonical evidence shape/type validator
- `src/registry/service_base.py` — preserved prior service implementation for minimal-diff delegation
- `src/registry/service.py` — public evidence validation wrapper
- `tests/registry/test_evidence_contract_validation.py` — deterministic regression definitions
- `status/E6_EARLY_SLICE2_HANDOFF.md` — this handoff
- `status/E6_STATUS.md` — E6 platform status update
- `coordination/E6/STATUS.md` — mailbox completion status

No `contracts/**` file is changed. No storage migration/schema change is required for this finding.

## 7. Static/source audit

Observed before handoff update:

```text
base = main
head = agent/e6-platform
status = ahead
merge_base = 4c531adc575ddd43f095ab8eabba3cae62ecc7b2
behind_by = 0
```

Branch changes relative to main are limited to E6-owned `src/registry`, `src/storage`, `tests/registry`, `tests/storage`, E6 docs/status paths. No `.github/workflows` change is present.

The TASK-referenced path `status/e7/POST_SLICE1_CONSTRUCTION_SYNC_REVIEW.md` was not present at the queried `main` path during this session; the correction therefore follows the complete finding and acceptance requirements explicitly materialized in authoritative `coordination/E6/TASK.md`.

## 8. Local verification

**Result: `NOT_RUN`.**

Reason: this session has no Product Owner-approved local execution environment. No unit test, migration test, restart test, integration test, backtest, or bug reproduction was executed here.

Exact required commands from repository root:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/registry -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
```

Correction-focused registry command:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/registry -p "test_evidence_contract_validation.py" -v
```

`NOT_RUN != PASS`.

## 9. Security / compute policy

- no credentials, API keys, tokens, passwords, private keys, or live `.env` values added;
- existing Strategy Inbox secret-like-key rejection remains intact;
- no GitHub Actions workflow created or used;
- no GitHub-hosted/triggered runner used;
- no GitHub scheduled compute used;
- GitHub was used only for source/status/version-control operations.

## 10. Lifecycle / authority boundary

Unchanged executable lifecycle subset:

```text
DRAFT -> BACKTESTING -> REJECTED | CANDIDATE
```

Still absent:

- `CANDIDATE -> PAPER`
- `READY_FOR_APPROVAL`
- `APPROVED`
- `LIVE`
- generic client-controlled transition API
- real E2 adapter wiring
- E3 validation methodology

A complete BacktestResult is only structurally admissible evidence. It is not a validation PASS and cannot by itself promote a strategy.

## 11. Required next action

**E7:** re-review `agent/e6-platform` for `E6-EVIDENCE-CONTRACT-001` source/test acceptance.

Do not infer executable PASS from this handoff. Local verification remains `NOT_RUN` until the Product Owner-approved environment executes the commands above.

After this handoff E6 must stop and wait for a replacement TASK.md; no next feature is started automatically.
