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

Every other pair among the four states fails closed at the Python persistence boundary and at direct SQL INSERT.

For the two promotion edges, edge shape is not sufficient authority:

- `DRAFT -> BACKTESTING` requires durable exact-strategy E2 compatibility evidence with `PASS / LOCAL_EXECUTION` and complete local evidence metadata;
- `BACKTESTING -> CANDIDATE` requires the transition's `primary_evidence_id` to resolve to a durable E3 `ValidationDecision.decision=PASS`, exact strategy/content binding, complete local PASS metadata, and a durable parent E3 BacktestResult with matching canonical payload/binding and complete local PASS metadata.

The same E6 lifecycle-authority policy is called by the public StrategyPlatformService and by `SQLiteRegistryStore.append_transition(...)`. The SQLite store rechecks durable authority inside its transaction before lifecycle history or projection mutation. Failure rolls back without changing state, revision, or transition history.

`BACKTESTING -> REJECTED` remains bounded rejection behavior: at least one reason code is required; supplied evidence must exist and bind to the exact strategy/content.

Later lifecycle states from the E7 canonical contract are not available through this migration/service yet. Enabling `PAPER`, approval, `LIVE`, degradation/recovery, or operational modes requires a later reviewed migration and service gate.

## Security

- no real credential field belongs in these tables;
- Strategy Inbox rejects common secret-like keys before persisting accepted definitions;
- invalid raw secret-bearing payloads must not be logged or stored merely for debugging;
- presence of credentials can never satisfy compatibility, validation, approval, or LIVE gates.

## Verification

All migration/persistence/restart tests are defined under `tests/storage/` and must be executed locally only. Current result is `NOT_RUN`; GitHub Actions/CI/hosted runners are forbidden.
