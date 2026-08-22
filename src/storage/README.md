# Storage — E6 Early Slice 2

Status: **SQLite persistence/migration skeleton present / local verification NOT_RUN**.

The first E6 persistence implementation deliberately uses Python stdlib `sqlite3` with plain SQL migrations. This keeps the early Registry path local, deterministic, dependency-light, and replaceable; it does not make SQLite a cross-module contract.

## Implemented persistence guarantees

- migration tracking through `schema_migrations`;
- unique `(strategy_id, strategy_version)` identity;
- immutable strategy content protected by a database trigger;
- separate compatibility evidence and validation evidence records;
- exact strategy-version/content-hash binding for E3 evidence;
- intake receipts without credential data;
- append-only lifecycle transition history protected by update/delete triggers;
- current lifecycle projection plus monotonic `registry_revision`;
- atomic lifecycle event + current-state projection update;
- optimistic/stale-write rejection;
- persistence-authoritative early lifecycle allowlist at `SQLiteRegistryStore.append_transition(...)`;
- database-level INSERT guard that independently rejects service-forbidden lifecycle edges;
- restart-readable durable state.

## Current migration scope

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

Every other pair among the four states fails closed at the Python persistence boundary and at direct SQL INSERT. The service remains responsible for evidence gates such as E2 compatibility and E3 validation; the store/database independently prevent callers from inventing a service-forbidden lifecycle edge.

Later lifecycle states from the E7 canonical contract are not available through this migration/service yet. Enabling `PAPER`, approval, `LIVE`, degradation/recovery, or operational modes requires a later reviewed migration and service gate.

## Security

- no real credential field belongs in these tables;
- Strategy Inbox rejects common secret-like keys before persisting accepted definitions;
- invalid raw secret-bearing payloads must not be logged or stored merely for debugging;
- presence of credentials can never satisfy compatibility, validation, approval, or LIVE gates.

## Verification

All migration/persistence/restart tests are defined under `tests/storage/` and must be executed locally only. Current result is `NOT_RUN`; GitHub Actions/CI/hosted runners are forbidden.
