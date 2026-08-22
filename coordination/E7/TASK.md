# E7 Current Task

- task_id: `E7-20260822-014`
- issued_at: `2026-08-22T21:35:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-e3-oos-validation-review-20260822`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, current `main`, merged E3 replay PR #22, merged E6 Registry/evidence persistence

## Objective

Perform a fresh exact-revision static/integration review of PR #24, the bounded E3 OOS ValidationDecision v0.1 producer, and decide whether PM may merge it into current `main`.

This is static/source review only. It does **not** authorize executing validation, generating a real strategy PASS, Registry promotion, Gate A PASS, PAPER/SHADOW/LIVE, provider calls, or GitHub compute.

## Review inputs

- PR: `#24 validation: add bounded OOS ValidationDecision v0.1`;
- E3 branch: `agent/e3-validation-oos-v0-1-20260822`;
- observed PR head at PM audit: `878dfa0384776089e02c14150d29d81620a5dd53`;
- final source/test revision: `bb0868fadaf52d3789c36a56cd8f5caba5d4c2a1`;
- docs/handoff revision: `f88955a068e5a50e29d7e116d3f678b508266018`;
- fresh implementation baseline: `e6cab8a194c8f05ad38b4e4b9294cdbfd0870d89`;
- merged E3 replay PR #22: `7f70d737ffb1276e251bc552ca9e6d39bb44393d`;
- merged E6 ValidationDecision validator: `src/registry/contract_validation.py` blob `954d21c021c0885554ee650acced17610d958a0e`;
- E6 durable evidence/promotion authority remains the merged trusted-process Registry/storage path;
- executable verification: `NOT_RUN`.

## Required review

1. Work only on fresh branch `agent/e7-e3-oos-validation-review-20260822` created by PM from latest `main` after this TASK issuance.
2. Review actual PR #24 source/tests/docs at the exact observed head, or a freshly observed successor only if its post-pin changes are E3 status/handoff evidence with no validation source/test semantic drift. Do not rely only on E3 STATUS claims.
3. Recheck PR scope. It must remain limited to E3-owned `src/validation/**`, `tests/validation/**`, E3 validation docs/handoff/status. No `contracts/**`, E1/E2/E4/E5/E6 production, Registry/storage, replay rewrite, workflow/CI, provider/credential/secret, or later validation engine implementation.
4. Verify canonical BacktestResult intake is fail closed:
   - required contracts-v0.1 identity/reproducibility/core metric fields are required;
   - malformed/unsupported schema/type/timestamp/count/decimal inputs cannot become PASS or FAIL;
   - binary float coercion for financial values is rejected;
   - count coherence and invalid metric ranges are blocked;
   - object `to_contract()` failure/type mismatch is blocked rather than trusted.
5. Verify exact authority binding:
   - `ValidationSubject.strategy_id`, `strategy_version`, and `backtest_result_id` must exactly match parsed BacktestResult before PASS/FAIL/NOT_RUN;
   - emitted ValidationDecision binds those exact identities;
   - malformed BacktestResult may only yield BLOCKED from explicit subject authority and cannot create a promotable PASS.
6. Verify explicit OOS semantics:
   - OOS status is not inferred from filenames/dataset labels/free-form text;
   - context requires non-empty split ID, OOS dataset ID/hash/start/end, training/reference dataset ID/hash, and validation policy version;
   - training/reference and OOS dataset identity/hash must be distinct;
   - BacktestResult dataset ID/hash/start/end must exactly bind to declared OOS dataset;
   - invalid/missing/contradictory context resolves to BLOCKED;
   - policy-version mismatch resolves to BLOCKED.
7. Verify policy semantics:
   - thresholds are explicitly caller supplied with no hidden product defaults;
   - version/configuration material deterministically defines policy identity;
   - minimum total trades, minimum net PnL, maximum drawdown, maximum consecutive losses, and optional minimum profit factor are implemented exactly;
   - configured minimum profit factor with `profit_factor=null` cannot PASS;
   - threshold semantics remain research-only and introduce no E5 sizing/leverage/execution authority.
8. Verify deterministic outcome precedence and reason vocabulary:
   - structural/identity/contract/OOS contradictions => BLOCKED before quantitative evaluation;
   - explicit no-run state => NOT_RUN only after structural bindings are valid;
   - structurally valid quantitative threshold failure => FAIL;
   - PASS only after every structural and configured quantitative condition passes;
   - stable machine-readable reason codes have deterministic ordering and documented vocabulary.
9. Verify deterministic decision identity:
   - binds contracts schema, strategy ID/version, BacktestResult ID, policy version/configuration identity, OOS context identity, execution state, resulting decision, and reason codes;
   - observational `decided_at` does not alter decision identity;
   - policy/context changes that alter authority inputs change identity deterministically.
10. Recheck canonical `ValidationDecision` serialization against current E6 `validate_validation_decision_contract` expectations: required fields, decision enum, reason-code sequence, and RFC3339 UTC `decided_at` must align. E3 production must not depend on E6 production; E6 validator use is allowed only in test definitions.
11. Perform an explicit **execution-evidence authority challenge**:
   - E3's `execution_state=EXECUTED` is a research input flag only and must not be represented as durable `LOCAL_EXECUTION` evidence;
   - construction of a synthetic PASS ValidationDecision must not itself satisfy E6 durable evidence/promotion authority;
   - no Registry/lifecycle mutation or evidence-record insertion occurs in E3 production;
   - real `BACKTESTING -> CANDIDATE` remains impossible without E6's separately stored, bound E3 ValidationDecision + BacktestResult and required durable `LOCAL_EXECUTION` metadata;
   - if supported production code can promote solely from the E3 object/payload or trust the E3 execution flag as evidence, BLOCK the PR and identify the exact owner/source path.
12. Verify test definitions statically cover the task acceptance surface, including synthetic PASS, quantitative FAIL reason ordering, missing OOS context, train/OOS collisions, dataset mismatch, explicit NOT_RUN, malformed schema/type, binary float rejection, subject/Backtest binding mismatch, profit-factor-null threshold, deterministic ID across timestamps, E6 test-only validator compatibility, threshold identity change, and absence of Registry/lifecycle authority. Do not execute tests in GitHub.
13. Recheck docs/handoff clearly distinguish synthetic fixture PASS from real executable validation evidence, record `NOT_RUN`, and include the exact local-only command.
14. Confirm no Walk Forward, Monte Carlo, optimization, parameter robustness, regime classification, strategy search/tuning, lifecycle promotion implementation, PAPER/SHADOW/LIVE, broker/provider/API execution, or shared-contract changes were added.
15. Persist an E7 review artifact under `status/e7/` and update `coordination/E7/STATUS.md` with:
   - exact reviewed PR #24 head and source/test pin;
   - BacktestResult fail-closed disposition;
   - subject/OOS binding disposition;
   - policy/threshold disposition;
   - outcome/reason/identity determinism disposition;
   - canonical ValidationDecision/E6-validator disposition;
   - execution-evidence authority challenge disposition;
   - scope/synchronization disposition;
   - PR #24 merge recommendation;
   - executable verification `NOT_RUN`;
   - real strategy PASS `NOT_CREATED`;
   - Gate A/B/C/D unchanged.
16. If all static/source conditions pass, state exactly `PM MAY MERGE PR #24`. This is static acceptance only and does not authorize Gate A PASS or lifecycle promotion.
17. If blocked, identify the exact source/contract/integration defect and owner. Do not modify E1-E6 production, E3 implementation, Registry/storage, or contracts in this review task.
18. Do not run validation tests, backtests, imports, migrations, provider calls, GitHub Actions/CI/hosted runners, or GitHub-triggered compute. Do not create a Codex ticket without a locally reproduced executable defect.

## Acceptance

Task completes when Git contains an exact-revision E7 static/integration review that either recommends PM merge PR #24 or blocks it with a precise source condition. Executable verification remains `NOT_RUN`; no real strategy PASS exists; Gate A/B/C/D remain blocked.

## Writable scope

- E7-owned review/status/integration documentation
- `coordination/E7/STATUS.md`

## Forbidden scope

- E1-E6 production implementation edits;
- shared-contract changes;
- E3 implementation edits;
- Registry/storage implementation edits;
- Walk Forward/Monte Carlo/optimization/parameter-robustness/regime implementation;
- lifecycle promotion implementation;
- broker/provider/API execution;
- PAPER/SHADOW/LIVE advancement;
- GitHub compute/CI.

## Completion / status

Persist the exact-revision review and STATUS, then stop and wait for PM. Do not merge PR #24 or start another task automatically.
