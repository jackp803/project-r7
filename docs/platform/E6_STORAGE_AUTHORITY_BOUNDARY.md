# E6 Supported SQLite Authority Boundary — Early Slice 2

> Task: `E6-20260822-007`  
> Scope: trusted-process modular monolith; local executable verification remains `NOT_RUN`

## Supported production surface

The supported SQLite-backed E6 composition API is:

```python
from storage import open_sqlite_platform

platform = open_sqlite_platform(
    "registry.sqlite3",
    compatibility_boundary=e2_boundary,
)
```

The factory returns `StrategyPlatformService`. It does not return a raw SQLite connection, migration primitive, `RegistryStore`, or authoritative writer.

`storage.__all__` intentionally contains only:

```text
open_sqlite_platform
```

The previous supported exports are removed:

```text
SQLiteRegistryStore
connect
apply_migrations
```

The raw implementation now lives in the underscore module `storage._sqlite_registry`. Its connection, migration, store, writer capability, and storage-mechanics helpers are internal implementation details. Storage tests may import explicit underscore helpers to test mechanics; that is not a supported production API.

## Internal construction/write authority

The internal `_SQLiteRegistryStore` constructor requires a module-private writer capability. The production capability is supplied only by the E6 factory-owned composition path.

This design means that merely constructing DTOs such as:

```text
CompatibilityEvidence
ValidationEvidenceRecord
LifecycleTransitionRecord
StrategyVersionRecord
```

does not give supported project code an authoritative persistence writer.

The service uses the internal store through the internal `RegistryStore` implementation port. `RegistryStore` is not exported as a user-facing authority API.

## Evidence provenance

### E2 compatibility

E2 compatibility becomes durable promotion authority only when:

1. the supported E6 service invokes the configured E2 compatibility boundary during intake;
2. the resulting evidence is persisted by the internal authorized writer;
3. `DRAFT -> BACKTESTING` revalidates durable exact-identity E2 evidence with `PASS / LOCAL_EXECUTION` and complete local metadata.

A caller-created `CompatibilityEvidence` object is data, not production write authority.

### E3 BacktestResult / ValidationDecision

E3 evidence becomes durable CANDIDATE authority only when:

1. it is ingested through the supported `StrategyPlatformService` evidence methods;
2. the accepted canonical BacktestResult / ValidationDecision validators pass;
3. exact strategy/content/backtest-parent binding passes;
4. required local-execution metadata is preserved;
5. the internal SQLite persistence path revalidates durable evidence inside the lifecycle transaction before mutation.

A caller-created `ValidationEvidenceRecord`, synthetic transition record, or PASS-looking payload does not itself provide a supported raw write path.

## Initial projection authority

A new strategy version must begin exactly as:

```text
current_lifecycle_state = DRAFT
registry_revision = 0
```

This is enforced twice:

- Python internal persistence rejects any supplied non-DRAFT state or nonzero revision before insertion;
- migration `0001_strategy_registry.sql` has `strategy_versions_initial_projection_guard`, which rejects incoherent direct INSERTs.

Normal `StrategyPlatformService.intake(...)` therefore creates only `DRAFT / 0` strategy versions. Same-identity/same-content idempotency remains coherent because the proposed intake record is still `DRAFT / 0`; an already-transitioned persisted version may be returned as the existing immutable version.

## Lifecycle projection mutation authority

The exact early Slice 2 edges remain:

```text
DRAFT       -> BACKTESTING
BACKTESTING -> REJECTED
BACKTESTING -> CANDIDATE
```

The existing Python edge allowlist and SQLite forbidden-edge INSERT trigger remain unchanged.

The migration additionally defines `strategy_versions_lifecycle_projection_guard`. A lifecycle projection UPDATE is accepted only when:

- `registry_revision` advances by exactly one; and
- a matching lifecycle transition row already exists for the same identity, previous state, new state, expected revision, and resulting revision.

The internal append path inserts the lifecycle row and updates the projection in the same transaction, so this defense-in-depth guard preserves the existing atomic path. A naked projection UPDATE without coherent transition history fails.

This database guard is defense in depth, not authentication. An actor with arbitrary direct DB-file write authority is outside the supported trust boundary.

## Threat model

This project is currently a Python modular monolith. The security/authority claim is intentionally limited to the **supported project API** and trusted-process composition model.

In scope:

- normal downstream project code should receive the safe service/factory surface rather than raw writers;
- raw authoritative persistence mechanics are internal and underscore-named;
- production writer construction requires an internal capability;
- initial projection and lifecycle projection coherence have database defense-in-depth guards;
- durable E2/E3 promotion evidence is revalidated before lifecycle mutation.

Out of scope and **not claimed as prevented**:

- arbitrary malicious Python code already executing in-process;
- monkey-patching, introspection, or deliberate access to underscore/private implementation objects;
- an attacker with direct filesystem or SQLite-file write access;
- separate-process authentication, cryptographic signing, HSM/secrets, external authorization services, or provider infrastructure.

Those stronger boundaries require a different deployment/security architecture and are not introduced in early Slice 2.

## Verification policy

Definitions exist under `tests/registry/` and `tests/storage/`, including public-surface, internal writer-capability, initial-projection, naked-projection, evidence-authority, forbidden-edge, append-only, rollback, and canonical-binding checks.

Executable verification remains:

```text
NOT_RUN
```

Exact local-only commands:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/registry -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
```

No GitHub Actions, CI, hosted runner, migration execution, backtest, or provider request is authorized in this task.
