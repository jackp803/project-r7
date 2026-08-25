# E6 Current Task

- task_id: `E6-20260825-020`
- issued_at: `2026-08-25T09:10:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e6-gate-b-storage-test-remediation-20260825`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate B chain through PR #69 merge `a044ff6e382b4fd93308f73169f0952705f922f4`, E7 diagnostic evidence `status/e7/GATE_B_BOUNDED_DIAGNOSTIC_RERUN_20260825.md`

## Objective

Remediate only the three E6-owned storage test-fixture / expectation defects proven by E7-20260825-061. Preserve accepted production durability, immutability, lifecycle-binding and migration semantics.

### Cause C — corruption-recovery fixtures violate immutable canonical tables

Affected tests: three cases in `tests/storage/test_paper_runtime_reference_remediation.py` that currently use direct SQL `UPDATE` against canonical `paper_runtime_objects` / `paper_trade_results` after immutability triggers are active.

Required remediation:

- represent legacy/corrupt durable material using a bounded test fixture/setup that can exist before or outside the active canonical immutability trigger boundary;
- reach the intended recovery validation without weakening, dropping, bypassing, or modifying production immutability semantics;
- preserve assertions that invalid legacy TradeResult/reference lineage cannot recover READY.

### Cause D — re-attestation fixture prerequisite drift

Affected test: `test_fractional_newer_raw_position_requires_reattestation`.

Required remediation:

- first establish a current restart-authoritative Position graph satisfying accepted durable lineage and `position-lifecycle-execution-binding-v0.1` companion prerequisites;
- then add only the newer raw Position observation so the test isolates the intended independent re-attestation freshness axis;
- do not weaken INCOMPLETE precedence or recovery fail-closed rules.

### Cause E — migration inventory expectation drift

Affected tests include:

- `test_true_additive_migration_from_registry_only_database`;
- `test_migration_is_idempotent`.

Current accepted migration set includes `0001_strategy_registry.sql`, `0002_paper_runtime_durability.sql`, and `0003_lifecycle_execution_binding.sql`.

Required remediation:

- update idempotency/additive migration expectations to the current accepted migration inventory/semantics;
- prefer assertions that remain correct as the accepted migration set evolves rather than hard-coded obsolete subsets where practical;
- do not remove or skip `0002`/`0003` and do not alter migration production behavior in this task.

## Writable scope

Only E6-owned storage tests/helpers necessary for these proven defects, including:

- `tests/storage/test_paper_runtime_reference_remediation.py`;
- `tests/storage/test_paper_runtime_conflict_and_time_ordering.py`;
- `tests/storage/test_registry_persistence.py`;
- bounded test-only helpers under `tests/storage/**` if necessary;
- `coordination/E6/STATUS.md`.

Forbidden:

- `src/storage/**` or any other production code changes;
- migration SQL changes;
- contracts/ADR changes;
- other agents' tests/production;
- GitHub Actions/CI/hosted runners/GitHub-triggered compute;
- provider/private API/network/credentials;
- PAPER/SHADOW/LIVE/Gate C;
- unrelated cleanup.

## Executable verification

This remediation assignment grants no new project execution authority.

Record `local_verification = NOT_RUN` and provide:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/storage -p "test_*.py" -v
```

E7-061 remains pre-remediation diagnostic FAIL evidence only.

## Acceptance

### DONE

- all proven E6 storage test-fixture/expectation defects are remediated test-only;
- production immutable tables/triggers remain unchanged and fail closed;
- re-attestation test establishes complete current prerequisites before introducing only newer raw Position truth;
- migration tests reflect current accepted additive/idempotent behavior including 0001/0002/0003;
- no production/contract semantic change or scope expansion;
- executable verification remains `NOT_RUN` unless separately authorized;
- commit/push to target branch and terminal E6 STATUS.

### BLOCKED

If any proven defect cannot be remediated without changing settled production durability/contract semantics, stop with exact evidence and do not broaden scope.

## Completion

Execute only this TASK, update `coordination/E6/STATUS.md`, commit/push to target branch, and stop.