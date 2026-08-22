# E3 Current Task

- task_id: `E3-20260822-005`
- issued_at: `2026-08-22T21:04:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e3-validation-oos-v0-1-20260822`
- authority: `agents/E3_BACKTEST_VALIDATION.md`, `agents/README.md`, `contracts-v0.1`, merged E3 PR #22, merged E6 Registry/evidence persistence

## Objective

Implement the next bounded E3 research-validation stage: a deterministic E3-owned OOS validation policy/input model that consumes canonical `BacktestResult` and emits canonical `ValidationDecision` without adding later validation engines.

This task exists because the historical replay / canonical BacktestResult skeleton is now merged. It must stop at a minimal OOS `ValidationDecision` producer. Do **not** add Walk Forward, Monte Carlo, optimization, parameter-robustness engines, regime classification, Registry promotion, PAPER/SHADOW/LIVE, or provider execution.

## Accepted merged baseline

- E1 import-integrity correction PR #21 merge: `1158a777a2830afc37066ef62ebefe624a9ca28e`;
- E3 replay PR #22 reviewed head: `dbce39cec5d5104e0fe79aca4e3be0e8aef459ec`;
- E3 preserved production pin: `54d40ae96e241f40367016e26b7bd5d03890e629`;
- E7 PR #22 static review artifact: `status/e7/E3_SLICE1_CURRENT_MAIN_STATIC_REVIEW_20260822.md`;
- E7 review evidence PR #23 merge: `d8ab1ac540e954d818bbdc271577e945dbc42b72`;
- E3 PR #22 merge: `7f70d737ffb1276e251bc552ca9e6d39bb44393d`;
- executable verification remains `NOT_RUN`;
- Gate A/B/C/D remain `BLOCKED`.

## Canonical output contract

`ValidationDecision` must remain `contracts-v0.1` and contain at minimum:

- `schema_version`
- `validation_decision_id`
- `strategy_id`
- `strategy_version`
- `backtest_result_id`
- `validation_policy_version`
- `decision`
- `reason_codes`
- `decided_at`

Allowed `decision` values are exactly:

```text
PASS | FAIL | BLOCKED | NOT_RUN
```

E3 production must not depend on E6 production implementation. E3 may use E6's merged validator in **tests only** as a cross-role compatibility assertion.

## Required actions

1. Read this TASK from latest `main`, fetch latest `main` again, and work only on fresh branch `agent/e3-validation-oos-v0-1-20260822` created by PM from post-TASK latest `main`.
2. Add a bounded E3-owned validation package under `src/validation/**`. Do not modify the merged replay engine unless an exact E3-owned import/export correction is demonstrably required.
3. Consume a canonical BacktestResult payload/object and fail closed on missing/malformed required identity, timestamp, count, or decimal fields. Do not silently coerce binary floats into financial values.
4. Define an explicit E3-owned OOS validation context. OOS status must be represented by explicit structured metadata, not inferred from `dataset_id`, filenames, branch names, or free-form strings. At minimum the context must bind:
   - a non-empty `split_id`;
   - the candidate OOS dataset identity/hash and time range;
   - a distinct training/reference dataset hash or identity;
   - the BacktestResult dataset identity/hash/time range exactly to the declared OOS side;
   - a validation-policy version.
   Missing, contradictory, same-train/OOS identity, or mismatched bindings must fail closed as `BLOCKED` rather than become PASS.
5. Define an explicit versioned validation policy configuration. Threshold values must be caller-supplied/configured and serialized into deterministic policy identity; do not hide product thresholds in code defaults. The minimal policy surface must support deterministic checks for:
   - minimum total trades;
   - minimum net PnL;
   - maximum drawdown;
   - maximum consecutive losses;
   - optional minimum profit factor. If a minimum profit factor is configured and BacktestResult `profit_factor` is `null`, the result cannot PASS that criterion.
6. Keep policy semantics research-only. `fixed_quantity`, BacktestResult metrics, and policy thresholds confer no E5 risk sizing, broker, leverage, or execution authority.
7. Produce deterministic `PASS | FAIL | BLOCKED | NOT_RUN` outcomes:
   - `PASS` only when the OOS bindings are structurally valid and every configured criterion passes;
   - `FAIL` when structurally valid OOS evidence fails one or more configured quantitative criteria;
   - `BLOCKED` for missing/contradictory/unverifiable required OOS or contract inputs;
   - `NOT_RUN` only for an explicitly represented no-executable-run state, never as an alias for PASS.
8. Define stable, machine-readable `reason_codes` with deterministic ordering. Document the reason-code vocabulary. Do not put free-form prose in place of reason codes.
9. Make `validation_decision_id` deterministic from decision-authority inputs (strategy identity, bound BacktestResult ID, policy version/configuration identity, OOS context/bindings, resulting decision/reasons). `decided_at` may be observational metadata and must not make identical inputs produce a different decision identity.
10. Ensure the emitted ValidationDecision binds exactly to the consumed BacktestResult's `strategy_id`, `strategy_version`, and `backtest_result_id`. Any mismatch must fail closed.
11. Add deterministic local-only test definitions under `tests/validation/**` covering at minimum:
   - canonical PASS construction from structurally valid OOS inputs and explicitly supplied passing thresholds;
   - quantitative FAIL with deterministic reason codes;
   - BLOCKED for missing OOS context/bindings;
   - BLOCKED for training/OOS identity collision;
   - BLOCKED for BacktestResult/OOS dataset mismatch;
   - NOT_RUN explicit state;
   - malformed/unsupported BacktestResult schema/type fail-closed behavior;
   - strategy/backtest identity binding;
   - optional profit-factor threshold with `profit_factor=null` cannot PASS;
   - deterministic identical decision identity for identical inputs despite differing observational `decided_at`;
   - emitted payload accepted by merged E6 `validate_validation_decision_contract` in test-only compatibility coverage;
   - no lifecycle mutation or Registry promotion from BacktestResult/ValidationDecision construction alone.
12. Do not claim a real strategy `PASS`. Any PASS objects in tests are synthetic fixtures/definitions only. Real durable promotion still requires Product Owner-approved local execution evidence and the E6 evidence-authority path.
13. Do not modify `contracts/**`, E1/E2/E4/E5/E6/E7 production, Registry/storage implementation, broker/provider code, workflow/CI files, credentials, or secrets.
14. Do not add Walk Forward, Monte Carlo, optimization, parameter robustness, regime classification, strategy search/tuning, lifecycle transitions, PAPER/SHADOW/LIVE, or provider execution.
15. Update E3 validation docs/handoff/status with exact source/tests/docs revision, changed-file scope, policy/context schema, reason-code vocabulary, deterministic identity behavior, E6 test-only contract compatibility, and executable verification `NOT_RUN`.
16. Executable verification is local-only. If no Product Owner-approved local environment exists, do not execute. Record exact commands, at minimum:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/validation -p "test_*.py" -v
```

17. Do not use GitHub Actions/CI/hosted runners, GitHub-triggered self-hosted runners, scheduled GitHub jobs, or GitHub project compute.
18. Push only this bounded E3 validation/OOS stage to the target branch, update `coordination/E3/STATUS.md`, then stop for PM/E7 exact-revision review. Do not merge or start the next task automatically.

## Acceptance

Static/source completion requires a deterministic, explicit-policy OOS ValidationDecision producer whose contract/bindings are compatible with `contracts-v0.1`, whose PASS path cannot bypass structural OOS checks, and whose construction alone has no Registry/lifecycle authority.

Executable verification remains `NOT_RUN`; no real strategy validation PASS is created; Gate A/B/C/D remain blocked.

## Writable scope

- `src/validation/**`
- `tests/validation/**`
- `docs/validation/**`
- `status/E3_VALIDATION_OOS_HANDOFF.md`
- E3-owned validation/status documentation
- `coordination/E3/STATUS.md`

## Forbidden scope

- `contracts/**`;
- E1/E2/E4/E5/E6/E7 production edits;
- E6 Registry/storage edits;
- replay-strategy semantic rewrites;
- Walk Forward / Monte Carlo / optimization / parameter-robustness / regime implementation;
- lifecycle promotion implementation;
- broker/provider/API execution;
- credentials/secrets;
- PAPER/SHADOW/LIVE;
- GitHub Actions/CI/hosted/project compute;
- real PASS claims without approved local execution evidence.

## Completion / status

Implement only the bounded OOS ValidationDecision stage, push exact evidence, update STATUS, and stop for PM/E7 review.