# Storage — E6 Skeleton

Status: **design-only / no database implementation yet**.

This directory is reserved for E6-owned persistence, repositories, and migrations.

Authoritative design: `docs/platform/E6_REGISTRY_PERSISTENCE_LIFECYCLE_SKELETON.md`.

## Intended guarantees

- durable strategy-version registry state;
- unique `(strategy_id, strategy_version)` identity;
- immutable content-hash conflict detection;
- append-only lifecycle history;
- transactional lifecycle transition + current-state projection;
- exact strategy-version evidence binding;
- restart-safe reconstruction;
- rollback on partial failure;
- migration/version tracking once a database stack is selected.

## Deferred intentionally

No database engine, ORM, migration framework, schema migration, or executable repository interface is selected here. Those decisions wait for the actual E2/E3 executable representations and the local E6 runtime choice.

Secrets and live credentials are never valid storage content for this public-repository platform path.
