# Handoff — E6 Lifecycle Evidence Authority Correction

**From:** E6 / Platform / Storage / Strategy Registry / Dashboard Engineer  
**To:** E7 / PM  
**Task:** `E6-20260822-005`  
**Branch / PR:** `agent/e6-platform` / PR #16  
**Finding:** `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`  
**Claimed disposition:** `CORRECTED IN SOURCE / READY_FOR_E7_TARGETED_RE_REVIEW`  
**Executable verification:** `NOT_RUN`

## Synchronization

- pre-task E6 head: `42c5d56996e0c4ff0e96edfc591726d9f9f34963`
- latest main merged once before correction: `4474a919f0446881369914523132b4aa9b88007d`
- non-destructive synchronization merge: `d94a64a1abaf70850167b3e6aec7af120f40ffa6`
- force push / destructive rebase / history rewrite: `NONE`

## Correction revision

Source/tests/docs correction revision before this handoff/status refresh:

`df39836adabd04c77cc4f0d0b531ea10408866ab`

## Authority design

A new E6-owned `src/registry/lifecycle_authority.py` policy is reused by the public `StrategyPlatformService` and `SQLiteRegistryStore.append_transition(...)`.

The SQLite store revalidates authority inside `BEGIN IMMEDIATE`, after current-state/revision checks and before any `lifecycle_transitions` INSERT or `strategy_versions` projection UPDATE. Any authority failure follows the existing rollback path.

### DRAFT -> BACKTESTING

Persistence now requires durable compatibility evidence for the exact strategy version with:

- E2 checker semantics (`checker.startswith("E2")`);
- `status=PASS`;
- `verification_kind=LOCAL_EXECUTION`;
- non-empty `source_revision`, `environment`, `command`, and `result_ref`.

A transition record by itself cannot supply this authority.

### BACKTESTING -> CANDIDATE

Persistence now requires `primary_evidence_id` to resolve to a durable E3 `VALIDATION_DECISION` with `decision=PASS`, exact strategy/version/content binding, complete local PASS metadata, and a durable E3 parent `BACKTEST_RESULT` with the same exact strategy/content binding and complete local PASS metadata.

Both stored payloads are decoded and revalidated with the already accepted canonical E6 validators:

- `validate_validation_decision_contract(...)`
- `validate_backtest_result_contract(...)`

Stored object IDs/schema versions must match their canonical payloads, and the ValidationDecision canonical `backtest_result_id` must match the canonical parent BacktestResult.

### BACKTESTING -> REJECTED

Existing bounded rejection semantics are preserved: at least one reason code is required; if evidence is supplied it must exist and bind to the exact strategy version/content.

## Preserved accepted boundaries

- exact lifecycle vocabulary remains `DRAFT | BACKTESTING | REJECTED | CANDIDATE`;
- exact edge allowlist remains `DRAFT -> BACKTESTING`, `BACKTESTING -> REJECTED`, `BACKTESTING -> CANDIDATE`;
- SQLite forbidden-edge INSERT trigger remains unchanged;
- append-only history remains unchanged;
- current-state, expected-revision, resulting-revision checks remain unchanged;
- atomic history + projection mutation and rollback remain unchanged;
- `E6-EVIDENCE-CONTRACT-001` canonical validator implementation remains unchanged (`contract_validation.py` blob `954d21c021c0885554ee650acced17610d958a0e`);
- default/unwired E2 compatibility remains fail-closed `NOT_RUN`;
- no PAPER / READY_FOR_APPROVAL / APPROVED / SHADOW / LIVE / DEGRADED / RETIRED behavior;
- no Slice 3 execution/provider persistence;
- no contracts changes or other-agent production changes.

## Test definitions added/updated

`tests/storage/test_lifecycle_evidence_authority.py` defines fail-closed direct-persistence cases for:

- missing/non-E2/non-PASS/non-local/incomplete E2 compatibility authority;
- missing candidate `primary_evidence_id`;
- wrong primary evidence type;
- FAIL/BLOCKED/NOT_RUN ValidationDecision;
- wrong strategy identity/content hash;
- missing/wrong BacktestResult parent;
- malformed/mismatched canonical ValidationDecision ↔ BacktestResult binding;
- missing/non-local PASS metadata on either decision or backtest;
- state/revision/history row-count preservation after every rejection;
- positive public-service BACKTESTING and CANDIDATE flows with durable synthetic E2/E3 evidence.

`tests/storage/test_registry_persistence.py` retains forbidden-edge/self-transition and direct-SQL trigger coverage, with its legal-edge fixtures upgraded to carry the durable authority now required by persistence.

Synthetic fixtures are test definitions only and are not project PASS evidence.

## Changed-file scope for this task

- `src/registry/lifecycle_authority.py`
- `src/registry/service.py`
- `src/storage/sqlite_registry.py`
- `src/storage/README.md`
- `tests/storage/test_registry_persistence.py`
- `tests/storage/test_lifecycle_evidence_authority.py`
- `tests/storage/README.md`
- this handoff/status files

No `contracts/**`, E1/E2/E3/E4/E5/E7 production code, provider/API, dashboard, credentials, CI/workflow, or Slice 3 persistence changes were made.

## Verification

Executable verification remains:

```text
NOT_RUN
```

No Product Owner-approved local environment was available in this session. No tests, migrations, backtests, provider requests, GitHub Actions, CI, hosted runner, or GitHub-triggered project compute were executed.

Exact local-only commands:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/registry -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
```

## Next owner / stop condition

E7 should perform the targeted re-review of PR #16 at the final branch revision and determine whether `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001` can be closed statically.

E6 stops after STATUS update and does not merge PR #16 or begin another feature automatically.
