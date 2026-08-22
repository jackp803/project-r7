# Handoff — E6 Supported Persistence Authority Boundary Correction

**From:** E6 / Platform / Storage / Strategy Registry / Dashboard Engineer  
**To:** E7 / PM  
**Task:** `E6-20260822-007`  
**Branch / PR:** `agent/e6-platform` / PR #16  
**Finding:** `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`  
**Claimed disposition:** `CORRECTED IN SOURCE / READY_FOR_E7_RE_REVIEW`  
**Executable verification:** `NOT_RUN`

## Synchronization

- pre-task E6 head: `e7d1f3d9a99043107824a3c64d1d37663db8ff53`
- latest main merged once before correction: `36d1b5f3baee298dc33da444e0a31782a8cc6d7e`
- non-destructive synchronization merge: `610cdc4edbcd3fdf3f74c1eed9691253b4453cc9`
- force push: `NO`
- destructive rebase/history rewrite: `NO`
- post-correction static compare: current main is merge-base; `behind_by=0`

## Exact correction revision

Source/tests/docs revision before this handoff-only commit:

```text
ca41cb92cfaf23c7c0d00a7802727fa28f5cca86
```

## Public API before / after

Before this task, supported `storage` exports included raw authority-bearing persistence mechanics:

```text
SQLiteRegistryStore
connect
apply_migrations
```

After correction, supported `storage.__all__` contains only:

```text
open_sqlite_platform
```

`open_sqlite_platform(...)` returns `StrategyPlatformService`; it does not return a mutable SQLite connection, `RegistryStore`, or raw writer.

The previous `src/storage/sqlite_registry.py` public-looking module was removed. Raw mechanics now live under:

```text
src/storage/_sqlite_registry.py
```

with underscore-named connection/migration/store helpers. Production authoritative store construction requires a module-private writer capability. Explicit underscore helpers remain available only for internal storage-mechanics test definitions.

## Authority model

This correction establishes a trusted-process supported API boundary, not a hostile-process sandbox.

E2 compatibility becomes promotion authority only when the supported E6 service invokes the configured E2 boundary during intake and the internal authorized writer persists that result. `DRAFT -> BACKTESTING` still revalidates durable exact-identity E2 `PASS / LOCAL_EXECUTION` evidence plus non-empty `source_revision`, `environment`, `command`, and `result_ref`.

E3 BacktestResult / ValidationDecision becomes CANDIDATE authority only when ingested through the supported E6 service methods and the already accepted canonical validators/bindings/local-execution metadata checks pass. The internal SQLite lifecycle path still revalidates durable evidence before mutation.

Caller-created `CompatibilityEvidence`, `ValidationEvidenceRecord`, `LifecycleTransitionRecord`, or `StrategyVersionRecord` values are data structures; they are not supported production write capabilities by themselves.

Out of scope and not claimed as prevented:

- arbitrary malicious in-process Python code;
- monkey-patching or introspection into underscore/private objects;
- an attacker with direct filesystem/SQLite-file write access.

No cryptographic signing, secret capability, external authorization service, additional process, or provider infrastructure was added.

## Initial projection guard

New strategy versions may begin only as:

```text
current_lifecycle_state = DRAFT
registry_revision = 0
```

Enforcement:

1. internal Python registration rejects supplied `BACKTESTING`, `REJECTED`, `CANDIDATE`, or nonzero revision before insert;
2. migration trigger `strategy_versions_initial_projection_guard` independently rejects incoherent direct INSERT.

Same-identity/same-content intake idempotency remains coherent because new proposals are always `DRAFT / 0`; an existing immutable version may already have advanced state and can still be returned as the existing record.

## Projection mutation defense in depth

Existing exact lifecycle edges remain unchanged:

```text
DRAFT       -> BACKTESTING
BACKTESTING -> REJECTED
BACKTESTING -> CANDIDATE
```

The prior Python allowlist and SQL forbidden-edge trigger are preserved.

Migration trigger `strategy_versions_lifecycle_projection_guard` now rejects naked state/revision UPDATE unless:

- revision advances exactly by one; and
- a matching lifecycle transition row already exists for the same identity, previous/new state, expected revision, and resulting revision.

The normal internal append path inserts lifecycle history and updates projection in one transaction, so this guard preserves existing atomicity/rollback semantics.

## Preserved accepted behavior

- `E6-EVIDENCE-CONTRACT-001` canonical validator behavior remains unchanged; `src/registry/contract_validation.py` blob remains `954d21c021c0885554ee650acced17610d958a0e`;
- lifecycle vocabulary remains exactly `DRAFT | BACKTESTING | REJECTED | CANDIDATE`;
- no PAPER / READY_FOR_APPROVAL / APPROVED / SHADOW / LIVE / DEGRADED / RETIRED behavior;
- durable E2/E3 persistence-authority revalidation remains in place;
- append-only lifecycle history remains in place;
- state/revision concurrency checks and transaction rollback remain in place;
- no Slice 3 execution/provider persistence;
- no shared-contract edit.

## Test definitions

New/updated local-only definitions cover:

- public `storage` exports do not expose raw store/connection/migration handles;
- public factory returns the safe service surface;
- direct internal store construction without writer capability fails;
- caller-created authority-looking DTOs are not public write handles;
- non-DRAFT or nonzero initial registration fails with no persistence mutation;
- DB initial projection guard rejects incoherent INSERT;
- DB projection guard rejects naked lifecycle/revision UPDATE;
- normal public service intake creates `DRAFT / 0`;
- public-factory valid service-authorized BACKTESTING/CANDIDATE flows remain representable;
- prior invalid-evidence, canonical-binding, forbidden-edge, SQL-trigger, rollback, append-only, immutability, and restart definitions remain present.

Synthetic PASS fixtures remain test doubles only and are not project executable evidence.

## Executable verification

```text
NOT_RUN
```

No Product Owner-approved local execution environment was available in this session. No unit test, migration, restart test, backtest, provider request, GitHub Action, CI job, hosted runner, or GitHub-triggered project compute was executed.

Exact local-only commands:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/registry -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
```

## E7 review target

E7 should re-review PR #16 at the final E6 branch head after the STATUS commits for:

- supported public API narrowing;
- internal writer capability/construction path;
- initial projection guard;
- lifecycle projection coherence guard;
- preservation of accepted E2/E3 evidence authority and canonical validators;
- explicit trusted-process threat model.

E6 stops after STATUS update and does not start another feature automatically.
