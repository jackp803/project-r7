# E6 Platform Status

> Owner: E6 Platform / Storage / Strategy Registry / Dashboard Engineer  
> Branch: `agent/e6-platform`  
> Baseline: `contracts-v0.1` / E7 Slice 0 merge `ba2affa62c89d58bb9ffac054963579e434896e1`

## Current phase

```text
Registry design/skeleton       READY
Persistence design/skeleton    READY
Lifecycle design/skeleton      READY
Executable Registry            BLOCKED
Database/migrations            BLOCKED
Strategy Inbox                 BLOCKED
E2/E3 orchestration            BLOCKED
Dashboard/UI                   NOT_STARTED
```

## Why implementation is intentionally blocked

E6 is waiting for the real executable E2 `StrategyDefinition` and E3 `BacktestResult` / `ValidationDecision` representations before materializing adapters, persistence schema/migrations, or Slice 2 orchestration.

The shared semantic baseline itself is available from E7 and is used by the current design skeleton.

## Prepared artifacts

- `docs/platform/E6_REGISTRY_PERSISTENCE_LIFECYCLE_SKELETON.md`
- `src/registry/README.md`
- `src/storage/README.md`
- `tests/registry/README.md`
- `tests/storage/README.md`

## Key design decisions

- strategy identity is exact `(strategy_id, strategy_version)`;
- same identity with conflicting `content_hash` fails closed;
- validation evidence is exact-version-bound;
- lifecycle history is append-only and auditable;
- current lifecycle state is a projection, not a replacement for transition history;
- rejected/retired strategies remain retained;
- backend lifecycle transition validation is authoritative;
- no DB engine, ORM, migration framework, or language-specific DTO has been selected yet.

## Local verification

```text
Executable verification: NOT_RUN
Reason: this phase contains documentation/skeleton only; no project code, DB, migration, or executable test exists yet.
Future exact commands: TBD only after E6 runtime/test framework is selected.
```

No test was executed on GitHub infrastructure.

## Security

- no real API credentials or secrets added;
- no secret-bearing seed/config/log/UI artifact added;
- credential presence is not treated as approval or LIVE authorization.

## Next entry condition

Proceed into Slice 2 implementation after E7 confirms executable E2/E3 contract compatibility for:

```text
Strategy Inbox
-> E2
-> E3
-> Validation Evidence
-> Registry
```

Until then, E6 should not deepen implementation beyond bounded design refinements.
