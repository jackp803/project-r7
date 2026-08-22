# E7 Static / Integration Review — E3 OOS ValidationDecision v0.1

- task_id: `E7-20260822-014`
- reviewer: `E7 Integration / Architecture / System QA / Release`
- review_target: `PR #24 validation: add bounded OOS ValidationDecision v0.1`
- reviewed_pr_head: `878dfa0384776089e02c14150d29d81620a5dd53`
- reviewed_source_test_pin: `bb0868fadaf52d3789c36a56cd8f5caba5d4c2a1`
- docs_handoff_revision: `f88955a068e5a50e29d7e116d3f678b508266018`
- implementation_baseline: `e6cab8a194c8f05ad38b4e4b9294cdbfd0870d89`
- review_time_main: `7750b4a91039268a0be1cf749037019cb5b6da33`
- executable_verification: `NOT_RUN`
- real_strategy_pass: `NOT_CREATED`

## Final disposition

**PASS / STATIC ONLY**

**PM MAY MERGE PR #24**

This recommendation is bounded to static/source integration acceptance. It does not establish Gate A PASS, does not create real executable validation evidence, does not authorize Registry promotion, and does not authorize PAPER/SHADOW/LIVE or provider execution.

## Exact revision / drift disposition

The reviewed source/test authority is the exact E3 revision:

```text
bb0868fadaf52d3789c36a56cd8f5caba5d4c2a1
```

The observed PR head is:

```text
878dfa0384776089e02c14150d29d81620a5dd53
```

Source/test pin -> PR head changes only:

```text
coordination/E3/STATUS.md
docs/validation/OOS_VALIDATION_V0_1.md
status/E3_VALIDATION_OOS_HANDOFF.md
```

No validation source/test semantic drift exists after the reviewed source/test pin.

At final review:

```text
latest main = 7750b4a91039268a0be1cf749037019cb5b6da33
E3 validation branch = ahead 4 / behind 2
merge base = e6cab8a194c8f05ad38b4e4b9294cdbfd0870d89
latest-main-only delta = coordination/E3/TASK.md + coordination/E7/TASK.md
meaningful production/shared-contract drift = NONE
PR #24 GitHub mergeable = TRUE
```

Coordination-only TASK drift is not a resynchronization blocker for this review.

## PR scope disposition

PR #24 changed-file scope is exactly:

```text
coordination/E3/STATUS.md
docs/validation/OOS_VALIDATION_V0_1.md
src/validation/__init__.py
src/validation/oos.py
status/E3_VALIDATION_OOS_HANDOFF.md
tests/validation/test_oos_validation.py
```

Confirmed absent from the PR diff:

- `contracts/**` changes;
- E1/E2/E4/E5/E6 production changes;
- Registry/storage implementation changes;
- E3 replay rewrite;
- workflow/CI/hosted-runner changes;
- provider/API/credential/secret changes;
- Walk Forward implementation;
- Monte Carlo implementation;
- optimization/strategy search/tuning;
- parameter robustness engine;
- regime classification;
- lifecycle promotion implementation;
- PAPER/SHADOW/LIVE behavior.

Scope is coherent with the bounded E3 validation task.

## BacktestResult fail-closed disposition

`src/validation/oos.py` requires the full `contracts-v0.1` BacktestResult identity/reproducibility/core metric surface before quantitative evaluation.

Required fields include:

```text
schema_version
backtest_result_id
strategy_id
strategy_version
strategy_content_hash
runtime_version
dataset_id
dataset_hash
dataset_start
dataset_end
cost_model_version
created_at
total_trades
wins
losses
breakeven
gross_pnl
net_pnl
total_fees
profit_factor
expectancy
max_drawdown
max_consecutive_losses
```

Static fail-closed behavior:

- non-Mapping object without callable `to_contract()` -> `BLOCKED / BACKTEST_RESULT_TYPE_INVALID`;
- `to_contract()` exception -> `BLOCKED / BACKTEST_RESULT_SERIALIZATION_FAILED`;
- `to_contract()` non-Mapping return -> `BLOCKED / BACKTEST_RESULT_TYPE_INVALID`;
- missing required field -> `BLOCKED / BACKTEST_REQUIRED_FIELD_MISSING`;
- unsupported schema -> `BLOCKED / BACKTEST_SCHEMA_UNSUPPORTED`;
- empty identity/reproducibility strings -> `BLOCKED / BACKTEST_IDENTITY_INVALID`;
- malformed/non-UTC timestamp -> `BLOCKED / BACKTEST_TIMESTAMP_INVALID`;
- reversed dataset range -> `BLOCKED / BACKTEST_TIME_RANGE_INVALID`;
- negative/non-integer counts -> `BLOCKED / BACKTEST_COUNT_INVALID`;
- `wins + losses + breakeven != total_trades` -> `BLOCKED / BACKTEST_TRADE_COUNTS_INCONSISTENT`;
- `max_consecutive_losses > losses` -> `BLOCKED / BACKTEST_TRADE_COUNTS_INCONSISTENT`;
- invalid/non-finite decimal values -> `BLOCKED / BACKTEST_DECIMAL_INVALID`;
- binary float or implicit integer-to-financial coercion -> rejected by the E3 decimal boundary;
- negative max drawdown -> `BLOCKED / BACKTEST_METRIC_RANGE_INVALID`;
- negative non-null profit factor -> `BLOCKED / BACKTEST_METRIC_RANGE_INVALID`.

Structural BacktestResult failures cannot become quantitative FAIL or PASS. They terminate the decision path as `BLOCKED`.

## Subject authority binding disposition

`ValidationSubject` is explicit and requires non-empty:

```text
strategy_id
strategy_version
backtest_result_id
```

For a structurally parsed BacktestResult, all three must match exactly before `NOT_RUN`, `FAIL`, or `PASS` can be reached.

Mismatch mapping:

```text
strategy_id mismatch      -> BACKTEST_STRATEGY_ID_MISMATCH
strategy_version mismatch -> BACKTEST_STRATEGY_VERSION_MISMATCH
backtest_result_id mismatch -> BACKTEST_RESULT_ID_MISMATCH
```

The emitted ValidationDecision uses the exact `ValidationSubject` identity. A malformed BacktestResult can therefore produce only a `BLOCKED` decision under the explicitly supplied subject authority; it cannot create a promotable PASS.

## Explicit OOS binding disposition

OOS status is represented only by structured `OOSValidationContext`. No filename, dataset-label convention, free-form prose, or implicit string heuristic is used to infer OOS authority.

Required context bindings:

```text
split_id
oos_dataset_id
oos_dataset_hash
oos_dataset_start
oos_dataset_end
training_dataset_id
training_dataset_hash
validation_policy_version
```

Static checks require:

- non-empty string identifiers;
- valid UTC OOS timestamps;
- OOS start not after OOS end;
- training dataset ID different from OOS dataset ID;
- training dataset hash different from OOS dataset hash;
- context policy version exactly equal supplied policy version;
- BacktestResult dataset ID exactly equal declared OOS dataset ID;
- BacktestResult dataset hash exactly equal declared OOS dataset hash;
- BacktestResult dataset start exactly equal declared OOS start;
- BacktestResult dataset end exactly equal declared OOS end.

Missing/invalid/contradictory context is `BLOCKED` before quantitative threshold evaluation.

## Policy / threshold disposition

`ValidationPolicy` has no hidden product defaults. Every threshold is caller supplied:

```text
version
min_total_trades
min_net_pnl
max_drawdown
max_consecutive_losses
min_profit_factor
```

Policy construction validates:

- non-empty version;
- non-negative integer minimum trade count;
- non-negative integer maximum consecutive losses;
- decimal/decimal-string financial threshold semantics;
- binary floats and implicit integer financial coercion rejected;
- non-negative maximum drawdown;
- configured minimum profit factor non-negative.

Deterministic `validation_policy_id` hashes the policy version and normalized complete threshold configuration.

Quantitative semantics are exact:

```text
total_trades >= min_total_trades
net_pnl >= min_net_pnl
max_drawdown <= max_drawdown
max_consecutive_losses <= max_consecutive_losses
profit_factor >= min_profit_factor when configured
```

When a minimum profit factor is configured and BacktestResult `profit_factor` is null, the result is FAIL with:

```text
PROFIT_FACTOR_REQUIRED_BUT_NULL
```

The policy contains no quantity, leverage, margin, broker, execution, or E5 risk authority.

## Outcome precedence / reason vocabulary disposition

Decision precedence is deterministic and fail closed:

```text
1. BacktestResult structural validation
2. exact ValidationSubject binding
3. OOS context / dataset / policy binding
4. execution-state validation
5. any structural contradiction -> BLOCKED
6. structurally valid + execution_state=NOT_RUN -> NOT_RUN
7. structurally valid + EXECUTED -> evaluate configured quantitative thresholds
8. one or more threshold failures -> FAIL
9. all configured thresholds pass -> PASS
```

Reason-code ordering is not dependent on incidental append order. Structural reasons are normalized through `BLOCK_REASON_ORDER`; quantitative reasons are normalized through `FAIL_REASON_ORDER`.

Stable outcome vocabulary includes:

```text
PASS:    OOS_POLICY_CRITERIA_PASSED
NOT_RUN: EXECUTION_NOT_RUN
```

and fixed machine-readable BLOCKED/FAIL reason sets documented by E3.

No free-form reason text becomes the canonical decision authority.

## Deterministic decision identity disposition

`validation_decision_id` binds:

- `contracts-v0.1` schema identity;
- exact strategy ID;
- exact strategy version;
- exact BacktestResult ID;
- validation policy version;
- deterministic validation policy ID;
- deterministic OOS context ID;
- explicit E3 execution-state research flag;
- resulting decision;
- ordered reason codes.

`decided_at` is observational metadata and is intentionally excluded from the ID material.

Therefore identical authority inputs are designed to retain the same decision ID across different observation timestamps, while policy/context/execution/outcome/reason changes deterministically change decision identity.

## Canonical ValidationDecision / E6 validator disposition

Current merged E6 validator blob:

```text
src/registry/contract_validation.py
954d21c021c0885554ee650acced17610d958a0e
```

E3 `ValidationDecision.to_contract()` emits all E6-required `contracts-v0.1` fields:

```text
schema_version
validation_decision_id
strategy_id
strategy_version
backtest_result_id
validation_policy_version
decision
reason_codes
decided_at
```

Decision values are bounded to:

```text
PASS | FAIL | BLOCKED | NOT_RUN
```

Reason codes serialize as a sequence of non-empty strings and `decided_at` serializes as RFC3339 UTC `...Z`.

Additional E3 research metadata (`validation_policy_id`, `oos_context_id`, `execution_state`, policy thresholds, OOS binding) does not weaken the canonical required fields.

E3 production does not import E6 production. The E6 validator is imported only in `tests/validation/test_oos_validation.py` as a cross-role compatibility definition.

## Execution-evidence authority challenge

**PASS STATIC**

E3's:

```text
execution_state = EXECUTED | NOT_RUN
```

is an E3 research evaluation input and serialized audit field only. It is not E6 durable verification metadata.

No E3 production path:

- imports Registry/storage;
- inserts a `ValidationEvidenceRecord`;
- records a durable BacktestResult or ValidationDecision into E6 persistence;
- supplies E6 `verification_status`;
- supplies E6 `verification_kind`;
- supplies durable source revision/environment/command/result reference;
- mutates Registry lifecycle;
- calls `mark_candidate`.

Current E6 remains independently authoritative.

`StrategyPlatformService.record_validation_decision(...)` accepts verification metadata separately and defaults it to:

```text
verification_status = NOT_RUN
verification_kind   = NOT_RUN
```

Real `BACKTESTING -> CANDIDATE` still requires a separately persisted E3 ValidationDecision and its stored BacktestResult parent, both bound to the strategy and both carrying durable:

```text
verification_status = PASS
verification_kind   = LOCAL_EXECUTION
source_revision     = non-empty
environment         = non-empty
command             = non-empty
result_ref          = non-empty
```

E6 re-validates the stored canonical ValidationDecision and BacktestResult payloads and exact parent/binding semantics before authoritative lifecycle mutation.

Therefore:

- constructing an E3 synthetic PASS object does not itself create durable promotion evidence;
- `execution_state=EXECUTED` is not treated as `LOCAL_EXECUTION`;
- BacktestResult + ValidationDecision payload construction alone cannot promote Registry lifecycle;
- no real strategy PASS or candidate promotion exists from this task.

## Test-definition disposition

Static test definitions cover the TASK-requested acceptance surface, including:

- canonical synthetic PASS from explicit subject/OOS/policy bindings;
- deterministic multi-threshold FAIL reason ordering;
- missing OOS context -> BLOCKED;
- training/OOS dataset identity/hash collision -> BLOCKED;
- BacktestResult/OOS dataset mismatch -> BLOCKED;
- explicit `NOT_RUN` -> NOT_RUN;
- unsupported BacktestResult schema -> BLOCKED;
- invalid BacktestResult object type -> BLOCKED;
- binary-float financial input -> BLOCKED;
- subject/Backtest identity mismatch -> BLOCKED;
- configured minimum profit factor with null profit factor -> FAIL;
- deterministic decision ID across differing `decided_at`;
- E6 validator compatibility in test definitions only;
- policy-threshold change modifies policy and decision identity;
- decision construction exposes no Registry/lifecycle authority fields.

The source also contains explicit fail-closed branches for serializer failure/non-Mapping serializer output, required-field failures, timestamp/count/coherence/metric-range failures, policy-version mismatch, full OOS dataset range binding, and invalid execution state.

No tests were executed by E7.

## Documentation / handoff disposition

`docs/validation/OOS_VALIDATION_V0_1.md` and `status/E3_VALIDATION_OOS_HANDOFF.md` accurately state:

- synthetic PASS fixtures are not real executable evidence;
- no real strategy PASS is claimed;
- no Registry lifecycle transition occurred;
- Gate A/B/C/D remain blocked;
- executable verification is `NOT_RUN`;
- E6 validator use is test-only;
- no later validation/execution stage is implemented.

Recorded local-only command:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/validation -p "test_*.py" -v
```

This command was not executed in this review.

## Verification / release state

- executable_verification: `NOT_RUN`
- validation_tests_executed: `NO`
- backtests_executed: `NO`
- import_probes_executed: `NO`
- migrations_executed: `NO`
- provider_requests: `NOT_SENT`
- github_compute: `NOT_USED`
- real_strategy_pass: `NOT_CREATED`
- durable_e3_local_execution_evidence_created: `NO`
- registry_promotion: `NONE`
- gate_a: `BLOCKED / UNCHANGED`
- gate_b: `BLOCKED / UNCHANGED`
- gate_c: `BLOCKED / UNCHANGED`
- gate_d: `BLOCKED / UNCHANGED`
- paper_shadow_live_advancement: `NONE`
- codex_ticket: `NONE / NOT_APPLICABLE WITHOUT LOCAL REPRODUCTION`

## Completion

E7 completed only `E7-20260822-014` and stops here.

**PM MAY MERGE PR #24**.

E7 does not merge PR #24, does not execute validation/tests/backtests/import probes, does not create durable evidence or a real strategy PASS, does not promote Registry lifecycle, and does not start another task automatically.

Next owner: `PM`.
