# Handoff — E6 Lifecycle Persistence Authority Correction

**From:** E6 / Platform / Storage / Strategy Registry / Dashboard Engineer  
**To:** E7 / PM  
**Task:** `E6-20260822-003`  
**Branch:** `agent/e6-platform`  
**Finding:** `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`  
**Claimed disposition:** `CORRECTED IN SOURCE / READY_FOR_E7_TARGETED_RE_REVIEW`  
**Executable verification:** `NOT_RUN`

## Objective

Close only the persistence-authority gap identified by E7: direct callers of `SQLiteRegistryStore.append_transition(...)` and direct SQL writers must not be able to represent a lifecycle edge that the early Slice 2 service forbids.

No Registry redesign, evidence-contract change, lifecycle expansion, or Slice 3 execution persistence was added.

## Synchronization

Before correction, E6 non-destructively synchronized current `main` into the existing branch exactly once:

- pre-task E6 HEAD: `df15109dcb8594b1182bf6fc09cb5ad6681d74b5`
- latest `main` merged: `06752b83c18f6579b06c1f3b7e1d5837a2d6949a`
- synchronization merge: `c3d756b46af547b4ea0bb36aa653cc8b9081163f`
- force push: `NO`
- destructive rebase/history rewrite: `NO`

## Correction design

### E6 authoritative early-edge allowlist

`src/registry/models.py` now defines the bounded internal persistence allowlist:

```text
DRAFT       -> BACKTESTING
BACKTESTING -> REJECTED
BACKTESTING -> CANDIDATE
```

`is_early_lifecycle_transition_allowed(...)` is consumed by the SQLite persistence boundary. The existing service already exposes the same exact three-edge subset and remains independently covered by Registry lifecycle tests.

### Public SQLite store boundary

`SQLiteRegistryStore.append_transition(...)` now rejects every edge outside that allowlist **before** opening the write transaction or inserting lifecycle history/updating the authoritative projection.

Existing concurrency protections remain intact:

- current authoritative state must equal `previous_state`;
- current `registry_revision` must equal `expected_registry_revision`;
- `resulting_registry_revision` must equal current revision + 1;
- lifecycle history insert and projection update remain atomic;
- any exception rolls back the transaction.

A forbidden edge therefore cannot create a transition row, change `current_lifecycle_state`, or increment `registry_revision`.

### SQLite database defense in depth

`src/storage/migrations/0001_strategy_registry.sql` now adds a `BEFORE INSERT` trigger on `lifecycle_transitions` that accepts only the same three edges. The existing four-state vocabulary checks remain, but state-name validity alone is no longer sufficient.

Direct SQL insertion of a forbidden edge fails before the lifecycle row can be recorded. The projection is not automatically mutated by lifecycle-row INSERTs, and the test definition verifies that state/revision remain unchanged after the rejected SQL statement.

## Test definitions added/expanded

`tests/storage/test_registry_persistence.py` now defines deterministic local-only coverage for:

- positive direct-store `DRAFT -> BACKTESTING`;
- positive direct-store `BACKTESTING -> REJECTED`;
- positive direct-store `BACKTESTING -> CANDIDATE`;
- forbidden direct-store `DRAFT -> CANDIDATE`;
- forbidden direct-store `DRAFT -> REJECTED`;
- forbidden direct-store `CANDIDATE -> DRAFT`;
- forbidden direct-store `CANDIDATE -> BACKTESTING`;
- forbidden direct-store `REJECTED -> CANDIDATE`;
- forbidden direct-store `REJECTED -> BACKTESTING`;
- self-transitions for all four early states;
- no transition-row/state/revision mutation after a rejected direct-store edge;
- direct SQL forbidden-edge rejection by the migration trigger with unchanged projection/revision;
- positive legal edges passing through the same database trigger;
- prior migration idempotence, immutability, append-only history, and restart persistence definitions retained.

Synthetic fixtures are test doubles only and are not project executable evidence.

## Prior accepted behavior preserved

Static source review in this task confirmed the previously accepted evidence-contract gate files were not changed:

- `src/registry/contract_validation.py` blob remains `954d21c021c0885554ee650acced17610d958a0e`;
- public `src/registry/service.py` blob remains `3184452956e1540be44d5ea779be87ed573fbcae`.

Therefore this correction does not alter:

- canonical BacktestResult shape/type/reproducibility validation;
- canonical ValidationDecision shape/type/enum/backtest/strategy binding;
- caller PASS/LOCAL_EXECUTION bypass protection;
- the rule that BacktestResult alone cannot authorize CANDIDATE;
- fail-closed default E2 compatibility `NOT_RUN` behavior;
- strategy identity/version/content immutability;
- Inbox idempotency vs identity conflict behavior.

## Lifecycle / scope boundary

Lifecycle vocabulary remains exactly:

```text
DRAFT | BACKTESTING | REJECTED | CANDIDATE
```

No PAPER, READY_FOR_APPROVAL, APPROVED, SHADOW, LIVE, DEGRADED, RETIRED, operational-mode promotion, or generic transition authority was added.

No ApprovedTradePlan, OrderRequest, OrderResult, Fill, Position, provider identity, OKX `sz`, reconciliation, Demo execution, or other Slice 3 persistence was added. Provider-native quantity was not reinterpreted as canonical BTC quantity.

No `contracts/**` or E1/E2/E3/E4/E5/E7 production file was modified by this correction.

## Exact correction revision

Source/tests/docs correction revision before handoff/status-only commits:

```text
aab1639d6db1f94e915d1c4af3041be28e9a4b94
```

Files directly changed for this finding before handoff/status refresh:

- `src/registry/models.py`
- `src/storage/sqlite_registry.py`
- `src/storage/migrations/0001_strategy_registry.sql`
- `tests/storage/test_registry_persistence.py`
- `src/storage/README.md`
- `tests/storage/README.md`

## Verification

Executable verification remains:

```text
NOT_RUN
```

No Product Owner-approved local environment was available in this session. No project unit test, migration, backtest, provider request, GitHub Action, CI job, hosted runner, or GitHub-triggered project compute was executed.

Exact approved-local commands from repository root:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/registry -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
```

`NOT_RUN` is not PASS.

## Next owner / stop condition

E7 should perform a targeted static/source re-review of `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001` on the exact synchronized branch revision. E6 stops after status publication and does not merge PR #16 or begin another feature automatically.
