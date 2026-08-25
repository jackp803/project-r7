# E7 Current Task

- task_id: `E7-20260825-062`
- issued_at: `2026-08-25T09:10:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-b-test-remediation-20260825`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate B chain through PR #69 merge `a044ff6e382b4fd93308f73169f0952705f922f4`, E7 diagnostic evidence `status/e7/GATE_B_BOUNDED_DIAGNOSTIC_RERUN_20260825.md`

## Objective

Remediate only the two E7-owned integration/safety test-definition defects proven by E7-20260825-061. Do not change shared contracts or production semantics.

### Cause B — lexical zero over-constraint in integration definitions

Affected tests: the ordinary EXIT and EMERGENCY_EXIT cases in `tests/integration/test_gate_b_paper_trade_result_integration.py` that assert `flat_position.actual_quantity == "0"`.

Required remediation:

- validate that the authoritative E4 flat Position quantity is a valid Decimal string numerically equal to zero;
- preserve exact broker fact, lineage, TradeResult, funding, lifecycle, execution-binding and close/reopen assertions;
- do not normalize or rewrite the E4 Position fact merely for E7 tests;
- no new shared zero-normalization contract is needed.

### Cause F — safety test expects wrong specific diagnostic

Affected test: `tests/safety/test_gate_b_paper_trade_result_safety.py::test_cross_plan_position_fill_and_funding_lineage_fail_closed`.

The fixture changes only `exit_fill.position_id`; accepted E5 validation returns `EXIT_FILL_POSITION_MISMATCH`. `EXIT_FILL_AUTHORITY_MISMATCH` is reserved for `position_action_id` mismatch.

Required remediation:

- update the specific expected diagnostic for the existing position-id mutation to `EXIT_FILL_POSITION_MISMATCH`;
- retain or add clear distinct coverage that position-action authority mismatch still fails closed with `EXIT_FILL_AUTHORITY_MISMATCH` if already within the bounded existing test structure;
- do not weaken exact exit Fill authority/position/role lineage validation.

## Writable scope

Only:

- `tests/integration/test_gate_b_paper_trade_result_integration.py`;
- `tests/safety/test_gate_b_paper_trade_result_safety.py`;
- bounded E7-owned helper under `tests/integration/**` / `tests/safety/**` only if strictly necessary;
- `coordination/E7/STATUS.md`.

Forbidden:

- production code changes;
- contracts/ADR changes;
- E1-E6 tests/production;
- release-gate promotion;
- GitHub Actions/CI/hosted runners/GitHub-triggered compute;
- provider/private API/network/credentials;
- PAPER/SHADOW/LIVE/Gate C;
- unrelated cleanup.

## Executable verification

This remediation task does not authorize a new project execution run.

Record `local_verification = NOT_RUN` and provide exact later approved-local commands:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/integration -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

E7-061 diagnostic execution is pre-remediation FAIL evidence, not post-fix PASS.

## Dependency / release state

E4, E5, E6 and E7 bounded test remediations may proceed independently. Do not self-start cross-domain integration or a new Gate B qualification run after this task.

Formal state remains:

```text
Gate B = BLOCKED / EXECUTABLE_VERIFICATION_FAIL
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

After all bounded remediation branches are PM-reviewed and merged, the next full Gate B qualification execution requires a separate exact-revision PM/Product Owner decision.

## Acceptance

### DONE

- E7 integration lexical-zero assertions are contract-valid numerical-zero checks;
- safety diagnostic expectation matches the exact mutated lineage field and remains fail closed;
- no production/shared-contract change;
- no scope expansion;
- executable verification remains `NOT_RUN` unless separately authorized;
- commit/push to target branch and terminal E7 STATUS.

### BLOCKED

If these test-only changes require a new contract or production behavior change, stop with exact evidence; do not broaden scope.

## Completion

Execute only this TASK, update `coordination/E7/STATUS.md`, commit/push to target branch, and stop. Do not start another task.