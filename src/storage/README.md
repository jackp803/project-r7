# Storage — E6 Early Slice 2

Status: **SQLite persistence/migration skeleton present / local verification NOT_RUN**.

The first E6 persistence implementation deliberately uses Python stdlib `sqlite3` with plain SQL migrations. This keeps the early Registry path local, deterministic, dependency-light, and replaceable; it does not make SQLite a cross-module contract.

## Supported public API

Production/downstream project code is supported through exactly this storage composition surface:

```python
from storage import open_sqlite_platform

platform = open_sqlite_platform("registry.sqlite3", compatibility_boundary=e2_boundary)
```

`open_sqlite_platform(...)` returns the safe `StrategyPlatformService` surface. The supported `storage` package does **not** export:

- `SQLiteRegistryStore`;
- raw `sqlite3.Connection` creation;
- migration primitives;
- raw compatibility/validation evidence writers;
- raw lifecycle append/projection writers.

SQLite mechanics now live under `storage._sqlite_registry` and are internal implementation details. Internal storage tests may import its underscore helpers explicitly to verify migration/storage mechanics; those imports are test-only and are not production authority APIs.

## Trusted-process authority model

This early modular monolith assumes trusted in-process project code and controlled access to the SQLite file.

Promotion authority is established only through the supported E6 service/factory path:

- E2 compatibility becomes durable promotion authority when the configured E2 boundary is invoked by `StrategyPlatformService.intake(...)` and its result is persisted by the internal writer;
- E3 BacktestResult / ValidationDecision becomes durable promotion authority when ingested through the supported service methods and passes the accepted canonical validators, exact strategy/backtest bindings, and local-execution metadata checks;
- caller-constructed `CompatibilityEvidence`, `ValidationEvidenceRecord`, or lifecycle DTOs are data structures, not public write capabilities;
- the internal SQLite writer requires a module-private construction capability owned by the E6 composition path.

This is **not** a hostile-process security sandbox. Arbitrary malicious in-process Python code, monkey-patching/introspection, or an attacker with direct filesystem/SQLite write access is outside this trust boundary and is not claimed as prevented. The underscore/export/capability design defines the supported project API and prevents normal downstream code from being handed authoritative raw writers.

## Implemented persistence guarantees

- migration tracking through `schema_migrations`;
- unique `(strategy_id, strategy_version)` identity;
- every new strategy projection must begin `DRAFT / revision 0` in Python persistence and by database trigger;
- immutable strategy content protected by a database trigger;
- separate compatibility evidence and validation evidence records;
- exact strategy-version/content-hash binding for E3 evidence;
- intake receipts without credential data;
- append-only lifecycle transition history protected by update/delete triggers;
- current lifecycle projection plus monotonic `registry_revision`;
- projection UPDATE requires a matching lifecycle-transition row and `revision + 1` database-side;
- atomic lifecycle event + current-state projection update;
- optimistic/stale-write rejection;
- persistence-authoritative early lifecycle allowlist;
- database-level INSERT guard that rejects service-forbidden lifecycle edges;
- persistence-authoritative durable evidence checks before any lifecycle row/projection mutation;
- canonical persisted ValidationDecision/BacktestResult payload revalidation for CANDIDATE promotion;
- restart-readable durable state.

## Current migration / lifecycle scope

`migrations/0001_strategy_registry.sql` intentionally supports only the early Slice 2 lifecycle subset:

```text
DRAFT
BACKTESTING
REJECTED
CANDIDATE
```

The persistence boundary permits exactly these edges:

```text
DRAFT       -> BACKTESTING
BACKTESTING -> REJECTED
BACKTESTING -> CANDIDATE
```

Every other pair among the four states fails closed at the Python persistence boundary and at direct SQL lifecycle INSERT.

For the two promotion edges, edge shape is not sufficient authority:

- `DRAFT -> BACKTESTING` requires durable exact-strategy E2 compatibility evidence with `PASS / LOCAL_EXECUTION` and complete local evidence metadata;
- `BACKTESTING -> CANDIDATE` requires the transition's `primary_evidence_id` to resolve to a durable E3 `ValidationDecision.decision=PASS`, exact strategy/content binding, complete local PASS metadata, and a durable parent E3 BacktestResult with matching canonical payload/binding and complete local PASS metadata.

The same E6 lifecycle-authority policy is called by the public `StrategyPlatformService` and by the internal SQLite append path. The SQLite writer rechecks durable authority inside its transaction before lifecycle history or projection mutation. Failure rolls back without changing state, revision, or transition history.

`BACKTESTING -> REJECTED` remains bounded rejection behavior: at least one reason code is required; supplied evidence must exist and bind to the exact strategy/content.

Later lifecycle states from the E7 canonical contract are not available through this migration/service yet. Enabling `PAPER`, approval, `LIVE`, degradation/recovery, or operational modes requires a later reviewed migration and service gate.

## Security / scope

- no real credential field belongs in these tables;
- Strategy Inbox rejects common secret-like keys before persisting accepted definitions;
- invalid raw secret-bearing payloads must not be logged or stored merely for debugging;
- presence of credentials can never satisfy compatibility, validation, approval, or LIVE gates;
- no external auth/signing service, secret-based capability, provider API, or separate process is introduced by this Slice 2 correction.

## Verification

All migration/persistence/restart tests are defined under `tests/storage/` and must be executed locally only. Current result is `NOT_RUN`; GitHub Actions/CI/hosted runners are forbidden.
