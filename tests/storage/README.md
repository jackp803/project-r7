# E6 Persistence Test Intent

These are local-only test requirements for the future E6 persistence implementation. No database or migration is executable yet.

Future local tests must cover:

- create/read of exact strategy-version metadata;
- unique `(strategy_id, strategy_version)` constraint;
- same identity/different hash conflict rejection;
- append-only lifecycle transition persistence;
- transaction rollback when transition audit/current-state projection cannot both persist;
- restart reconstruction of registry/current lifecycle state;
- optimistic-concurrency or equivalent stale-write rejection;
- evidence references survive restart and remain bound to the exact strategy version;
- rejected/retired history is preserved;
- migration forward behavior once a migration framework exists;
- migration failure does not silently corrupt or discard registry/audit state;
- no API-secret-like values are written into public fixtures/audit output.

## Current status

```text
Result: NOT_RUN
Reason: database engine, migration framework, and executable E6 runtime are intentionally deferred
Required future local command: TBD after E6 runtime/database selection
```

GitHub Actions/CI/hosted runners must never be used to execute persistence or migration tests.
