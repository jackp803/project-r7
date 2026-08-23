# E3 Current Task

- task_id: `E3-20260823-001`
- issued_at: `2026-08-23T22:50:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e3-gate-a-validation-fixture-fix-20260823`
- authority: `agents/E3_BACKTEST_VALIDATION.md`, `agents/README.md`, `contracts-v0.1`, approved local Gate A evidence from revision `6ed214276038b1ad517e8875c10946b8fcccf4a3`

## Objective

Fix the single locally reproduced E3 validation-test defect that blocked the Gate A matrix. This is a bounded test-fixture correction. Do not change production OOS validation semantics unless direct source analysis proves the current production behavior is incorrect.

## Reproduced local evidence

Approved local Windows worktree:

```text
C:\Users\彭宏宣\Documents\ChatGPT\project-r7-gate-a-6ed2142
```

Executed source revision:

```text
6ed214276038b1ad517e8875c10946b8fcccf4a3
```

Working tree: `CLEAN`.

AgentBridge durable local job evidence:

```text
GATE_A_MARKET_DATA   JOB-349F7EAF260E  PASS  21 tests
GATE_A_INDICATORS    JOB-E0A467C4A882  PASS   3 tests
GATE_A_STRATEGY      JOB-EDC9C34DCCC8  PASS  21 tests
GATE_A_BACKTEST      JOB-9B6CB89CF105  PASS  21 tests
GATE_A_VALIDATION    JOB-B94CDD33E399  FAIL  14 tests / exit 1
```

First failing test:

```text
tests/validation/test_oos_validation.py::OOSValidationTests.test_quantitative_fail_reason_codes_have_stable_order
```

Observed assertion:

```text
Expected decision = FAIL
Actual decision   = BLOCKED
```

The Gate A run correctly stopped immediately after this failure. Registry/storage/integration remain `NOT_RUN`.

## PM source classification

At approved revision, the failing fixture sets:

```text
total_trades = 5
wins = 2
losses = 3
breakeven = 0
max_consecutive_losses = 4
```

Production `src/validation/oos.py` intentionally enforces the structural invariant:

```text
max_consecutive_losses <= losses
```

Violation produces `BACKTEST_TRADE_COUNTS_INCONSISTENT`, which has BLOCKED precedence before quantitative FAIL criteria. Therefore the current test payload is structurally invalid and cannot legitimately exercise the intended quantitative FAIL ordering path.

Current PM disposition:

```text
probable defect class = TEST_FIXTURE_INCONSISTENCY
probable owner        = E3
target production semantics = PRESERVE
```

E3 must independently re-check this conclusion against current `main` and the contract before editing.

## Required actions

1. Read this TASK from latest `main` and fetch latest `main`.
2. Work only on fresh branch `agent/e3-gate-a-validation-fixture-fix-20260823` from latest post-TASK `main`.
3. Inspect the reproduced failing test and `src/validation/oos.py` structural-vs-quantitative precedence.
4. Preserve the fail-closed production rule that structurally inconsistent BacktestResult metrics resolve to `BLOCKED` unless the authoritative contract explicitly proves otherwise.
5. Correct the test fixture so `test_quantitative_fail_reason_codes_have_stable_order` uses a structurally valid BacktestResult while still violating every intended quantitative threshold in the expected stable order. For example, any chosen counts must satisfy:

```text
wins + losses + breakeven == total_trades
max_consecutive_losses <= losses
max_consecutive_losses > policy.max_consecutive_losses
```

6. Prefer changing only `tests/validation/test_oos_validation.py`. Do not modify `src/validation/oos.py` merely to make the existing invalid fixture pass.
7. Add or preserve an explicit test proving a structurally impossible `max_consecutive_losses > losses` input yields `BLOCKED / BACKTEST_TRADE_COUNTS_INCONSISTENT` if such coverage is absent and the addition remains bounded.
8. Do not change policy thresholds, outcome precedence, reason-code vocabulary/order, contracts, BacktestResult semantics, E6 authority, or Registry lifecycle.
9. Do not run tests in GitHub/CI/hosted runners. Executable verification in the Agent chat remains `NOT_RUN` unless the approved local AgentBridge path is explicitly invoked separately by PM/Product Owner after the source correction is reviewed/merged.
10. Update `coordination/E3/STATUS.md` with exact changed files, rationale, corrected revision, and exact local verification command to rerun later.
11. Commit/push to the target branch and stop. Do not start the remaining Gate A suites automatically.

## Acceptance

Static acceptance requires:

```text
- production fail-closed semantics unchanged;
- quantitative FAIL test payload structurally valid;
- intended five quantitative reason codes still expected in stable order;
- structurally impossible consecutive-loss metrics remain BLOCKED;
- no unrelated source/contract changes.
```

Executable acceptance will occur later through the approved AgentBridge local-only Gate A path.

## Writable scope

- `tests/validation/test_oos_validation.py`
- `docs/validation/**` only if a tiny clarification is strictly necessary
- `status/E3*` / `status/e3/**` handoff evidence if used
- `coordination/E3/STATUS.md`

## Forbidden scope

- `src/validation/**` production semantic changes unless the current contract clearly disproves the PM classification and E3 reports BLOCKED instead;
- E1/E2/E4/E5/E6 production;
- `contracts/**`;
- Registry promotion;
- Walk Forward / Monte Carlo / optimization / regime;
- PAPER / SHADOW / LIVE;
- GitHub Actions/CI/hosted compute.

## Completion

Push the bounded correction and STATUS, then stop for PM/E7 review.