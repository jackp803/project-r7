# E6 Registry / Lifecycle Test Intent

These are local-only test requirements for the future executable E6 Registry implementation. No test is executable yet.

## Registry identity

Future local tests must verify:

- first registration of `(strategy_id, strategy_version)` succeeds;
- same identity + same `content_hash` is idempotent;
- same identity + different `content_hash` is rejected;
- multiple versions of one strategy do not overwrite each other;
- rejected/retired strategy versions remain queryable.

## Evidence binding

Future local tests must verify:

- evidence binds to the exact strategy version;
- evidence for version A cannot satisfy version B;
- conflicting strategy content hash is rejected when the upstream evidence exposes the hash;
- `FAIL`, `BLOCKED`, and `NOT_RUN` evidence remains retained and is never normalized to PASS;
- attaching validation evidence makes the covered strategy version immutable as required by the shared contract.

## Lifecycle

Future local tests must verify every E7 baseline legal transition and representative illegal transitions, including:

- `DRAFT -> BACKTESTING` accepted;
- `BACKTESTING -> CANDIDATE` accepted only when the later evidence predicate permits it;
- `BACKTESTING -> REJECTED` retained;
- `BACKTESTING -> LIVE` rejected unconditionally;
- skipped transitions are rejected;
- `DEGRADED -> LIVE` cannot occur automatically;
- stale/concurrent transition requests are rejected;
- transition actor, timestamp, previous/new state, and evidence/reason are retained.

## UI/backend gate boundary

When an API/UI exists, future local tests must prove a client cannot overwrite lifecycle state directly and cannot bypass backend transition validation.

## Current status

```text
Result: NOT_RUN
Reason: no executable E6 Registry implementation exists yet
Required future local command: TBD after E6 runtime/test framework selection
```

GitHub Actions/CI/hosted runners must never be used to execute these tests.
