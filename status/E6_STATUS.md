# E6 Platform Status

> Owner: E6 Platform / Storage / Strategy Registry / Dashboard Engineer  
> Branch: `agent/e6-platform`  
> Task: `E6-20260822-007`  
> State: `DONE / AWAITING E7 RE-REVIEW`

## Summary

Closed the supported-public/raw-persistence authority portion of `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001` for static E7 re-review.

The supported storage surface is now narrowed to:

```python
from storage import open_sqlite_platform
```

`open_sqlite_platform(...)` returns `StrategyPlatformService`; supported downstream code is no longer offered raw SQLite connections, migrations, authoritative Registry writers, or raw evidence/lifecycle write methods.

Raw SQLite mechanics moved to `storage._sqlite_registry` and are internal implementation details. Authoritative store construction requires a module-private writer capability. This defines the supported trusted-process project boundary; it does not claim protection against arbitrary malicious in-process Python, monkey-patching/introspection, or direct filesystem/SQLite compromise.

## Synchronization

- pre-task E6 head: `e7d1f3d9a99043107824a3c64d1d37663db8ff53`
- latest main merged: `36d1b5f3baee298dc33da444e0a31782a8cc6d7e`
- non-destructive synchronization merge: `610cdc4edbcd3fdf3f74c1eed9691253b4453cc9`
- force push: `NO`
- rebase/history rewrite: `NO`

## Correction revisions

- source/tests/docs correction revision: `ca41cb92cfaf23c7c0d00a7802727fa28f5cca86`
- handoff refresh commit: `a81bb0b43c96dc1ddf9152077ea5ca37d47032df`

## Public API / writer authority

Before:

```text
storage.SQLiteRegistryStore
storage.connect
storage.apply_migrations
```

After:

```text
storage.open_sqlite_platform
```

The former `src/storage/sqlite_registry.py` public-looking module was removed. The implementation now lives under `src/storage/_sqlite_registry.py`; production store construction requires the E6-owned internal writer capability. Explicit underscore helpers exist only for internal/test storage-mechanics definitions.

Caller-created `CompatibilityEvidence`, `ValidationEvidenceRecord`, `LifecycleTransitionRecord`, and `StrategyVersionRecord` values remain DTO/data structures and do not themselves provide a supported production persistence writer.

## Initial / lifecycle projection defense in depth

New registrations must be exactly:

```text
DRAFT / registry_revision 0
```

This is enforced by both the Python persistence path and `strategy_versions_initial_projection_guard` in migration `0001_strategy_registry.sql`.

`strategy_versions_lifecycle_projection_guard` rejects naked lifecycle projection updates unless revision advances by one and a coherent matching lifecycle transition row already exists. The normal append path still inserts transition history and updates the projection atomically in the same transaction.

## Preserved accepted boundaries

- `src/registry/contract_validation.py` semantics unchanged; accepted blob remains `954d21c021c0885554ee650acced17610d958a0e`;
- lifecycle vocabulary remains exactly `DRAFT | BACKTESTING | REJECTED | CANDIDATE`;
- exact allowed edges remain `DRAFT -> BACKTESTING`, `BACKTESTING -> REJECTED`, `BACKTESTING -> CANDIDATE`;
- Python and SQL forbidden-edge guards remain;
- durable E2 authority revalidation for BACKTESTING remains;
- durable E3 ValidationDecision + BacktestResult canonical/binding/local-execution revalidation for CANDIDATE remains;
- append-only history, current-state/revision concurrency checks, rollback, and transaction atomicity remain;
- no shared contract change;
- no later lifecycle state or Slice 3 execution/provider persistence added.

## Changed scope

Task changes are limited to E6 writable paths:

- `src/storage/__init__.py`
- `src/storage/platform.py`
- `src/storage/_sqlite_registry.py`
- removal of `src/storage/sqlite_registry.py`
- `src/storage/migrations/0001_strategy_registry.sql`
- `src/storage/README.md`
- `tests/registry/test_strategy_inbox.py`
- `tests/registry/test_validation_lifecycle.py`
- `tests/registry/test_evidence_contract_validation.py`
- `tests/storage/test_registry_persistence.py`
- `tests/storage/test_lifecycle_evidence_authority.py`
- `tests/storage/test_public_persistence_boundary.py`
- `tests/storage/README.md`
- `docs/platform/E6_STORAGE_AUTHORITY_BOUNDARY.md`
- E6 handoff/status files.

Contracts changed: `NONE`.

## Verification

Executable verification remains:

```text
NOT_RUN
```

No Product Owner-approved local execution environment was available. No tests, migrations, backtests, provider requests, GitHub Actions, CI, hosted runners, or GitHub-triggered project compute were executed.

Exact local-only commands:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/registry -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
```

Synthetic PASS fixtures in test definitions are test doubles only; they are not executable project PASS evidence.

## Handoff / stop condition

- handoff: `status/E6_EARLY_SLICE2_HANDOFF.md`
- next owner: `E7 / PM`
- PR #16 must remain open/unmerged for E7 review.
- E6 stops after coordination STATUS update and does not start another task automatically.
