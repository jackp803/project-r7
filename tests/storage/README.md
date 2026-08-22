# E6 Persistence / Migration Tests

These test definitions are executable in an approved local checkout. They have **not** been run by this GPT session.

Raw SQLite mechanics used by storage-mechanics tests are imported explicitly from `storage._sqlite_registry`; those helpers are internal/test-only and are not the supported production authority surface.

## Coverage

`test_public_persistence_boundary.py` defines the supported-boundary proofs for:

- public `storage.__all__` exposes only `open_sqlite_platform`;
- public `storage` does not expose `SQLiteRegistryStore`, `connect`, `apply_migrations`, or the old raw module surface;
- `open_sqlite_platform(...)` returns `StrategyPlatformService`, with no public raw connection/writer methods;
- internal SQLite writer construction fails without the module-private writer capability;
- caller-constructed E2/E3-looking DTOs are data, not public write capabilities;
- Python registration rejects `CANDIDATE`, `BACKTESTING`, `REJECTED`, or nonzero initial revision and leaves persistence unchanged;
- database initial-projection guard rejects non-`DRAFT / 0` INSERT;
- database projection guard rejects naked lifecycle/revision UPDATE without matching transition history;
- public service intake creates `DRAFT / revision 0`;
- public-factory service-authorized `DRAFT -> BACKTESTING -> CANDIDATE` remains representable with durable accepted synthetic fixtures.

`test_registry_persistence.py` preserves checks for:

- migration idempotence;
- immutable StrategyVersion content at the database layer;
- append-only lifecycle transition history;
- internal direct-store acceptance of exactly the three early Slice 2 edges when required durable authority exists;
- internal direct-store rejection of service-forbidden edges and self-transitions without transition-row or projection mutation;
- direct SQL forbidden-edge rejection by the migration trigger without authoritative projection/revision mutation;
- restart persistence of current lifecycle state and revision;
- migration-backed Registry reconstruction.

`test_lifecycle_evidence_authority.py` preserves persistence-authority bypass regressions for:

- `DRAFT -> BACKTESTING` with no compatibility evidence;
- non-E2 compatibility evidence;
- non-PASS or non-LOCAL_EXECUTION compatibility evidence;
- incomplete local compatibility metadata;
- `BACKTESTING -> CANDIDATE` without `primary_evidence_id`;
- wrong primary evidence type;
- FAIL/BLOCKED/NOT_RUN ValidationDecision;
- wrong strategy identity or content-hash binding;
- missing or wrong BacktestResult parent;
- malformed/mismatched canonical ValidationDecision-to-BacktestResult binding;
- missing or non-local PASS metadata on either ValidationDecision or BacktestResult;
- row-count/state/revision preservation after every rejected authorization attempt;
- positive service-authorized `DRAFT -> BACKTESTING` and `BACKTESTING -> CANDIDATE` flows using durable E2/E3 synthetic fixtures.

Additional Registry tests cover identity conflicts, canonical evidence binding, lifecycle service gates, rejection retention, and the accepted `E6-EVIDENCE-CONTRACT-001` evidence-shape protection.

Synthetic fixtures in these tests are test doubles only; they are **not** project executable PASS evidence.

## Local-only command

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/storage -p "test_*.py" -v
```

Combined E6 local command:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/registry -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
```

Current result:

```text
NOT_RUN
```

Reason: this ChatGPT GitHub environment is not the Product-Owner-approved local execution environment.

Never use GitHub Actions/CI/hosted runners for migration, persistence, restart, Registry, or lifecycle verification.
