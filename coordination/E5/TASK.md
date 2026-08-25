# E5 Current Task

- task_id: `E5-20260825-025`
- issued_at: `2026-08-25T09:10:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e5-gate-b-test-remediation-20260825`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate B chain through PR #69 merge `a044ff6e382b4fd93308f73169f0952705f922f4`, E7 diagnostic evidence `status/e7/GATE_B_BOUNDED_DIAGNOSTIC_RERUN_20260825.md`

## Objective

Remediate only the E5-owned stale test assertion proven by E7-20260825-061.

Affected test:

`tests/position/test_lifecycle_projection.py` — `test_position_closed_requires_real_trade_result_outcome_and_exact_flat_position`.

The authoritative E4 flat Position may serialize numerically zero `actual_quantity` with preserved Decimal scale such as `"0.0000"`. `contracts-v0.1` requires base-10 Decimal strings and E5 TradeResult validation requires numerical zero; it does not require every zero quantity to be lexically exactly `"0"`.

Required remediation:

- replace only the stale exact-string zero assertion with a Decimal-valid numerical-zero assertion;
- continue to prove the lifecycle projection preserves exact E4 broker facts rather than rewriting them;
- preserve all lifecycle revision/predecessor/event/state/TradeResult and broker-fact preservation assertions;
- do not change E5 production lifecycle or TradeResult logic.

## Writable scope

Only:

- `tests/position/test_lifecycle_projection.py`;
- E5-owned test helper in `tests/position/**` only if strictly necessary;
- `coordination/E5/STATUS.md`.

Forbidden:

- `src/**` production changes;
- contracts/ADR changes;
- other agents' tests/production;
- provider/private APIs/network/credentials;
- GitHub Actions/CI/hosted runners/GitHub-triggered compute;
- PAPER/SHADOW/LIVE/Gate C;
- unrelated cleanup.

## Executable verification

This task does not grant new project execution authority.

Record `local_verification = NOT_RUN` and provide:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_*.py" -v
```

E7-061 diagnostic evidence is pre-remediation FAIL evidence, not post-fix PASS.

## Acceptance

### DONE

- stale lexical-zero assertion corrected to contract-valid numerical-zero validation;
- E4 broker-fact preservation remains exact;
- no production semantic change;
- no scope expansion;
- executable verification remains `NOT_RUN` unless separately authorized;
- commit/push to target branch and terminal E5 STATUS.

### BLOCKED

If this cannot be fixed test-only without changing settled production/contract semantics, stop with exact evidence.

## Completion

Execute only this TASK, update `coordination/E5/STATUS.md`, commit/push to target branch, and stop.