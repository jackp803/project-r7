# E3 OOS Validation v0.1

> Owner: E3 Backtest & Quantitative Validation Engineer  
> Task: `E3-20260822-005`  
> Contract baseline: `contracts-v0.1`  
> Branch: `agent/e3-validation-oos-v0-1-20260822`

## Scope

This stage adds only the bounded OOS validation decision boundary:

```text
canonical BacktestResult
+ explicit ValidationSubject
+ explicit OOSValidationContext
+ explicit ValidationPolicy
+ explicit execution state
-> E3 deterministic OOS evaluation
-> canonical ValidationDecision
```

It does **not** add Walk Forward, Monte Carlo, optimization, parameter robustness, regime classification, strategy search/tuning, Registry promotion, lifecycle transitions, PAPER, SHADOW, LIVE, broker/provider execution, or E5 sizing/risk authority.

## Baseline and source revision

- post-TASK `main` consumed: `e6cab8a194c8f05ad38b4e4b9294cdbfd0870d89`
- initial OOS producer/test commit: `d27b5f9b5e58535bb085304bcf657946132b3a5b`
- final source/test hardening revision: `bb0868fadaf52d3789c36a56cd8f5caba5d4c2a1`

No shared contract or cross-agent production file was changed.

## Public E3 validation models

### `ValidationSubject`

Binds the canonical decision identity to:

- `strategy_id`
- `strategy_version`
- `backtest_result_id`

The consumed BacktestResult must match all three. A mismatch is `BLOCKED`; E3 never silently substitutes the BacktestResult identity.

### `OOSValidationContext`

OOS status is explicit structured metadata and is never inferred from a filename, branch name, dataset label convention, or free-form prose.

Required context fields:

- `split_id`
- `oos_dataset_id`
- `oos_dataset_hash`
- `oos_dataset_start`
- `oos_dataset_end`
- `training_dataset_id`
- `training_dataset_hash`
- `validation_policy_version`

Rules:

- all string bindings must be non-empty;
- timestamps must be UTC;
- OOS start must not be after OOS end;
- training and OOS dataset IDs must differ;
- training and OOS dataset hashes must differ;
- context policy version must equal the supplied policy version;
- BacktestResult dataset ID/hash/start/end must exactly equal the declared OOS side.

Missing or contradictory context resolves to `BLOCKED` before any metric threshold is evaluated.

### `ValidationPolicy`

All threshold values are caller-supplied. There are no hidden product defaults.

Required configuration:

- `version`
- `min_total_trades`
- `min_net_pnl`
- `max_drawdown`
- `max_consecutive_losses`
- `min_profit_factor` — explicit decimal threshold or explicit `None`

Financial thresholds accept `Decimal` or base-10 decimal strings; binary floats and implicit integer-to-financial coercion are rejected. `max_drawdown`, `max_consecutive_losses`, `min_total_trades`, and a configured minimum profit factor must be non-negative.

The deterministic `validation_policy_id` hashes the policy version plus the normalized complete threshold configuration. Changing a threshold changes policy identity even when the final PASS/FAIL outcome happens to remain the same.

## BacktestResult intake

E3 production does not import or depend on E6 production validation code. It consumes either:

- a canonical BacktestResult mapping; or
- an object exposing `to_contract()` that returns the canonical mapping.

The E3 intake requires all `contracts-v0.1` BacktestResult identity/reproducibility/core metric fields and fails closed for:

- missing required fields;
- unsupported schema;
- empty required identity strings;
- malformed/non-UTC timestamps;
- reversed dataset time ranges;
- invalid/non-negative count semantics;
- wins + losses + breakeven not equal to total trades;
- max consecutive losses greater than total losses;
- non-decimal or non-finite financial values;
- binary floats;
- negative max drawdown;
- negative non-null profit factor.

These are structural prerequisites. They never become quantitative FAIL or PASS; they produce `BLOCKED`.

## Decision precedence

Evaluation order is fixed:

1. validate canonical BacktestResult structure and subject binding;
2. validate OOS context and exact dataset binding;
3. validate explicit execution state;
4. if any structural reason exists -> `BLOCKED`;
5. else if execution state is explicitly `NOT_RUN` -> `NOT_RUN`;
6. else evaluate all configured quantitative criteria;
7. any criterion failure -> `FAIL`;
8. all criteria pass -> `PASS`.

Therefore `NOT_RUN` is not a PASS alias, and a malformed or contradictory OOS binding cannot reach the PASS path.

## Quantitative criteria

For structurally valid, explicitly executed evidence:

- `total_trades >= min_total_trades`
- `net_pnl >= min_net_pnl`
- `max_drawdown <= max_drawdown threshold`
- `max_consecutive_losses <= configured maximum`
- when `min_profit_factor` is configured: `profit_factor >= threshold`

If a profit-factor threshold is configured and BacktestResult `profit_factor` is `null`, the criterion fails with `PROFIT_FACTOR_REQUIRED_BUT_NULL`.

## Reason-code vocabulary

Reason codes are machine-readable and emitted in a fixed deterministic order.

### PASS

- `OOS_POLICY_CRITERIA_PASSED`

### NOT_RUN

- `EXECUTION_NOT_RUN`

### Quantitative FAIL

- `MIN_TOTAL_TRADES_NOT_MET`
- `MIN_NET_PNL_NOT_MET`
- `MAX_DRAWDOWN_EXCEEDED`
- `MAX_CONSECUTIVE_LOSSES_EXCEEDED`
- `PROFIT_FACTOR_REQUIRED_BUT_NULL`
- `MIN_PROFIT_FACTOR_NOT_MET`

### Structural BLOCKED

- `BACKTEST_RESULT_TYPE_INVALID`
- `BACKTEST_RESULT_SERIALIZATION_FAILED`
- `BACKTEST_REQUIRED_FIELD_MISSING`
- `BACKTEST_SCHEMA_UNSUPPORTED`
- `BACKTEST_IDENTITY_INVALID`
- `BACKTEST_TIMESTAMP_INVALID`
- `BACKTEST_TIME_RANGE_INVALID`
- `BACKTEST_COUNT_INVALID`
- `BACKTEST_TRADE_COUNTS_INCONSISTENT`
- `BACKTEST_DECIMAL_INVALID`
- `BACKTEST_METRIC_RANGE_INVALID`
- `BACKTEST_STRATEGY_ID_MISMATCH`
- `BACKTEST_STRATEGY_VERSION_MISMATCH`
- `BACKTEST_RESULT_ID_MISMATCH`
- `OOS_CONTEXT_MISSING`
- `OOS_CONTEXT_INVALID`
- `OOS_TIME_RANGE_INVALID`
- `TRAIN_OOS_DATASET_ID_COLLISION`
- `TRAIN_OOS_DATASET_HASH_COLLISION`
- `OOS_POLICY_VERSION_MISMATCH`
- `OOS_BACKTEST_DATASET_ID_MISMATCH`
- `OOS_BACKTEST_DATASET_HASH_MISMATCH`
- `OOS_BACKTEST_DATASET_START_MISMATCH`
- `OOS_BACKTEST_DATASET_END_MISMATCH`
- `EXECUTION_STATE_INVALID`

## Deterministic identities

`validation_decision_id` is derived from decision-authority inputs only:

- schema version;
- strategy ID/version;
- BacktestResult ID;
- validation policy version and deterministic policy identity;
- deterministic OOS context identity;
- explicit execution state;
- resulting decision;
- ordered reason codes.

`decided_at` is observational metadata and is intentionally excluded from decision identity. Identical authority inputs therefore produce the same decision ID even if observed/serialized at different UTC timestamps.

The OOS context identity includes split ID, exact OOS dataset identity/hash/range, training dataset identity/hash, and policy version.

## Canonical ValidationDecision

The emitted payload includes every required `contracts-v0.1` field:

- `schema_version`
- `validation_decision_id`
- `strategy_id`
- `strategy_version`
- `backtest_result_id`
- `validation_policy_version`
- `decision`
- `reason_codes`
- `decided_at`

It additionally includes E3 audit metadata (`validation_policy_id`, `oos_context_id`, `execution_state`, policy thresholds, OOS binding). Those fields carry research evidence only and confer no lifecycle or execution authority.

E6 production is not imported by E3 production. `tests/validation/test_oos_validation.py` imports E6 `validate_validation_decision_contract` **only as test-only cross-role compatibility coverage**.

## Synthetic PASS versus real evidence

PASS examples in tests are synthetic fixtures only. This task creates no real strategy PASS, no durable promotion evidence, and no lifecycle transition.

Real Gate A/B/C/D and promotion state remain blocked until Product Owner-approved local execution and the approved E6/E7 evidence-authority path exist.

## Local-only verification

Executable verification status for this task: `NOT_RUN`.

No test or backtest was executed in GitHub or any hosted runner.

Exact local command from repository root:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/validation -p "test_*.py" -v
```

GitHub Actions, CI, hosted runners, GitHub-triggered self-hosted runners, scheduled GitHub jobs, and GitHub project compute are forbidden for this verification.
