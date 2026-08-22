# E3 Validation OOS v0.1 Handoff

## Handoff

**From:** E3 Backtest & Quantitative Validation Engineer  
**To:** PM / E7 exact-revision review  
**Task:** `E3-20260822-005`  
**Branch:** `agent/e3-validation-oos-v0-1-20260822`

## Objective completed

Implemented only the bounded E3 OOS ValidationDecision stage requested by the current TASK:

```text
canonical BacktestResult
+ explicit subject binding
+ explicit OOS split/dataset binding
+ explicit versioned thresholds
+ explicit execution state
-> deterministic E3 OOS decision
-> canonical contracts-v0.1 ValidationDecision
```

No later validation engine or lifecycle/execution behavior was added.

## Exact baseline and revisions

- post-TASK latest `main` consumed: `e6cab8a194c8f05ad38b4e4b9294cdbfd0870d89`
- target branch was confirmed identical to that `main` before implementation
- initial source/test revision: `d27b5f9b5e58535bb085304bcf657946132b3a5b`
- final source/test hardening revision: `bb0868fadaf52d3789c36a56cd8f5caba5d4c2a1`

The final source/test revision contains the complete production/test state for this OOS stage.

## Changed-file scope before documentation/status recording

Only:

- `src/validation/__init__.py`
- `src/validation/oos.py`
- `tests/validation/test_oos_validation.py`

No `contracts/**`, replay engine, E1/E2/E4/E5/E6/E7 production, Registry/storage implementation, broker/provider code, workflow/CI file, credential, or secret was changed.

## Policy / context schema

### Decision subject

`ValidationSubject` binds:

- strategy ID;
- strategy version;
- BacktestResult ID.

A consumed BacktestResult mismatch is `BLOCKED`.

### OOS context

`OOSValidationContext` explicitly binds:

- split ID;
- OOS dataset ID/hash/start/end;
- training/reference dataset ID/hash;
- validation policy version.

Training and OOS dataset ID/hash collisions are blocked. BacktestResult dataset ID/hash/start/end must match the declared OOS side exactly.

### Policy

`ValidationPolicy` requires caller-supplied values for:

- version;
- minimum total trades;
- minimum net PnL;
- maximum drawdown;
- maximum consecutive losses;
- optional minimum profit factor (`Decimal`/decimal string or explicit `None`).

There are no hidden product threshold defaults. The complete normalized policy config is hashed into `validation_policy_id`.

## Decision semantics

Precedence is deterministic:

1. malformed BacktestResult / identity mismatch / invalid OOS bindings / invalid execution state -> `BLOCKED`;
2. structurally valid evidence with explicit `execution_state=NOT_RUN` -> `NOT_RUN`;
3. structurally valid executed evidence failing one or more thresholds -> `FAIL`;
4. structurally valid executed evidence passing every configured threshold -> `PASS`.

A configured minimum profit factor with BacktestResult `profit_factor=null` yields FAIL reason `PROFIT_FACTOR_REQUIRED_BUT_NULL`.

Synthetic PASS objects exist only in test definitions. No real strategy PASS is claimed by this task.

## Deterministic identity

`validation_decision_id` binds:

- exact strategy ID/version;
- exact BacktestResult ID;
- policy version and policy identity;
- OOS context identity;
- explicit execution state;
- final decision and ordered reason codes.

`decided_at` is observational and excluded from deterministic identity, so changing only that timestamp does not change the decision ID.

## Reason codes

The full machine-readable vocabulary and deterministic order are documented in:

- `docs/validation/OOS_VALIDATION_V0_1.md`

Categories cover structural Backtest/OOS/identity/execution blocking, quantitative threshold failures, explicit NOT_RUN, and synthetic PASS.

No free-form prose is substituted for reason codes in the canonical decision.

## BacktestResult fail-closed intake

E3 accepts a canonical mapping or an object exposing `to_contract()`.

It rejects/block-closes unsupported/missing schema or required fields, invalid identity/timestamps/counts/decimals, binary floats, inconsistent trade counts, negative max drawdown, negative non-null profit factor, and subject or OOS dataset mismatches.

This validation is E3-owned; production code does not import E6 validation implementation.

## E6 compatibility

Production dependency: **NONE**.

Test-only coverage imports merged E6:

```python
from registry.contract_validation import validate_validation_decision_contract
```

The synthetic emitted ValidationDecision is fed into that validator as a cross-role compatibility assertion. This test definition does not mutate Registry state or lifecycle.

## Test definitions added

`tests/validation/test_oos_validation.py` covers:

- canonical synthetic PASS from explicit OOS bindings/thresholds;
- deterministic quantitative FAIL reason ordering;
- BLOCKED missing OOS context;
- BLOCKED training/OOS identity collision;
- BLOCKED BacktestResult/OOS dataset mismatch;
- explicit NOT_RUN;
- unsupported BacktestResult schema/type;
- binary-float financial rejection;
- strategy/Backtest identity mismatch;
- configured profit-factor threshold with null BacktestResult profit factor;
- stable decision identity across differing `decided_at`;
- E6 ValidationDecision validator compatibility in tests only;
- no Registry/lifecycle authority fields from decision construction;
- threshold change changes deterministic policy/decision identity.

These are test definitions only, not observed executable results.

## Executable verification

Status: `NOT_RUN`.

No Product Owner-approved local execution environment was used. No unit test, validation run, backtest, import probe, or metric execution was performed.

Exact local-only command:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/validation -p "test_*.py" -v
```

No GitHub Actions, CI, hosted runner, GitHub-triggered self-hosted runner, scheduled GitHub job, or GitHub project compute was used.

## Gates / lifecycle

- Gate A: `BLOCKED`
- Gate B: `BLOCKED`
- Gate C: `BLOCKED`
- Gate D: `BLOCKED`
- real strategy validation PASS: `NOT CLAIMED`
- Registry lifecycle transition: `NONE`
- PAPER / SHADOW / LIVE: `NO IMPACT`

## Explicit non-goals preserved

Not implemented:

- Walk Forward;
- Monte Carlo;
- optimization;
- parameter robustness engine;
- regime classification;
- strategy search/tuning;
- lifecycle/promotion logic;
- Registry mutation;
- broker/provider/API execution;
- PAPER/SHADOW/LIVE.

## Next owner

PM / E7 should review the exact revisions and static source/test/docs evidence. E3 stops after STATUS update and does not merge or begin the next task automatically.
