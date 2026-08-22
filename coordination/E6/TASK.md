# E6 Current Task

- task_id: `E6-20260822-008`
- issued_at: `2026-08-22T16:08:00+08:00`
- state: `HOLD`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003, E7 reviews under `status/e7/`

## Objective

Freeze the completed PR #16 supported-public/raw-persistence authority correction while E7 performs the final exact-revision static/security re-review of `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`.

## Frozen evidence

- completed correction task: `E6-20260822-007`
- branch: `agent/e6-platform`
- source/tests/docs correction revision: `ca41cb92cfaf23c7c0d00a7802727fa28f5cca86`
- handoff refresh: `a81bb0b43c96dc1ddf9152077ea5ca37d47032df`
- platform-status refresh: `68c9d8e63cc9920975a06a62a080a3ca08a2872f`
- observed PR #16 head after completion mailbox status: `607feaf1663966cd0fac82a244d368822ea28214`
- latest main synchronized by E6 before correction: `36d1b5f3baee298dc33da444e0a31782a8cc6d7e`
- synchronization merge: `610cdc4edbcd3fdf3f74c1eed9691253b4453cc9`
- correction-pin -> PR-head delta: `coordination/E6/STATUS.md + status/E6_EARLY_SLICE2_HANDOFF.md + status/E6_STATUS.md only`
- executable verification: `NOT_RUN`
- Gate A/B/C/D: `BLOCKED / UNCHANGED`

## Claimed correction pending E7 review

E6 reports that the supported production storage surface now exports only `open_sqlite_platform(...)`, which returns `StrategyPlatformService`; raw SQLite connection, migration, store, and writer mechanics live under internal `storage._sqlite_registry` implementation scope and are not returned by the supported factory.

E6 also reports:

- internal authoritative store construction requires an E6-owned writer capability;
- caller-constructed DTOs do not by themselves provide a supported production write path;
- new registration is independently restricted to `DRAFT / registry_revision=0` in Python and SQL;
- database defense in depth requires coherent lifecycle transition history for lifecycle projection updates;
- accepted E2/E3 promotion evidence revalidation, exact early lifecycle edges, SQL forbidden-edge/append-only guards, canonical validators, concurrency, atomicity, and rollback remain intact;
- the documented threat model is a trusted-process modular monolith with controlled DB-file access, not a hostile arbitrary-Python-code sandbox.

## Required actions

1. Do not modify PR #16 source/tests/docs while E7 reviews the exact frozen revision.
2. Preserve `E6-EVIDENCE-CONTRACT-001`, the exact early lifecycle state/edge cap, canonical E2/E3 evidence bindings, SQL guards, and Registry/Inbox behavior.
3. Do not expand the security claim beyond the documented trusted-process boundary; arbitrary malicious in-process Python, introspection/monkey-patching, or direct external SQLite-file write compromise remains out of scope.
4. Do not add later lifecycle states, Slice 3 execution/provider persistence, dashboard expansion, broker/API work, credentials, asset movement, or shared-contract changes.
5. Keep executable verification `NOT_RUN`; do not run tests, migrations, backtests, provider calls, GitHub Actions/CI/hosted/project compute.
6. Do not resynchronize merely because PM issues coordination-only TASK commits while E7 reviews. Resynchronize only if E7 finds meaningful production/shared-contract drift or an actual merge conflict affecting reviewed behavior.
7. If acknowledging HOLD, update only `coordination/E6/STATUS.md`.

## Acceptance

PR #16 remains frozen and unmerged pending E7 final review. No executable PASS, Gate advancement, PAPER/APPROVED/SHADOW/LIVE authority, or provider execution is authorized.

## Writable scope

Only `coordination/E6/STATUS.md` for HOLD acknowledgement unless PM replaces this task.

## Completion / status

Wait for E7/PM disposition. Do not merge PR #16 or start another E6 feature automatically.