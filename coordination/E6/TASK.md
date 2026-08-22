# E6 Current Task

- task_id: `E6-20260822-007`
- issued_at: `2026-08-22T15:33:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e6-platform`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003, E7 review `status/e7/E6_EVIDENCE_AUTHORITY_FINAL_REREVIEW_20260822.md`

## Objective

Close the remaining public/raw persistence authority bypass in `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001` on PR #16 without pretending that a Python modular monolith is a hostile-process security sandbox.

E7 accepted the edge allowlist, SQL edge trigger, in-transaction durable evidence revalidation, canonical E2/E3-looking content/binding checks, concurrency/rollback, and `E6-EVIDENCE-CONTRACT-001`. The remaining blocker is that the currently **exported/supported raw persistence surface** can itself manufacture the rows/projection that promotion authority trusts:

- `storage.SQLiteRegistryStore`, `storage.connect`, and raw write methods are publicly exported/reachable through the supported package surface;
- `save_compatibility(...)` / `save_validation_evidence(...)` accept caller-constructed authority-looking records;
- `register_strategy(...)` accepts caller-supplied initial lifecycle state/revision;
- exported raw SQLite access permits direct lifecycle projection mutation.

This task must establish a clear **trusted-process supported API boundary**: normal project code may use the E6 platform/service/factory surface; raw SQLite implementation/writer/connection mechanics are internal implementation details and must not be available as supported authority-bearing public APIs. Arbitrary code execution, Python introspection/monkey-patching, or direct external write access to the SQLite file is outside this modular-monolith trust boundary and must be documented explicitly rather than falsely claimed as prevented.

## Accepted behavior to preserve

Do not regress:

- `E6-EVIDENCE-CONTRACT-001` — `CLOSED / PASS STATIC`;
- lifecycle vocabulary exactly `DRAFT | BACKTESTING | REJECTED | CANDIDATE`;
- legal lifecycle edges exactly:

```text
DRAFT       -> BACKTESTING
BACKTESTING -> REJECTED
BACKTESTING -> CANDIDATE
```

- forbidden edge rejection in Python and SQL;
- durable E2 authority revalidation for `DRAFT -> BACKTESTING`;
- durable E3 ValidationDecision + BacktestResult revalidation for `BACKTESTING -> CANDIDATE`;
- canonical payload validation/binding;
- append-only lifecycle history;
- current-state / expected-revision / resulting-revision checks;
- atomic history + projection update and rollback;
- no later lifecycle states;
- no Slice 3 execution/provider persistence;
- executable verification `NOT_RUN`.

## Required correction

### 1. Supported public API boundary

Refactor the E6/storage package surface so production/downstream code is not offered raw authoritative persistence writers or raw SQLite connections as supported public APIs.

At minimum:

- `storage.__init__` must no longer export `SQLiteRegistryStore`, raw `connect`, or raw migration/write primitives;
- provide one narrow E6-owned composition/factory entry point for the SQLite-backed platform that returns the safe `StrategyPlatformService` (or an equivalently narrow E6 platform facade), not the raw store/connection;
- raw SQLite store/connection/migration helpers must become internal implementation details by naming/module/export policy and documentation;
- `RegistryStore` remains an internal implementation port, not a user-facing authority surface;
- do not expose a public method that returns the underlying mutable SQLite connection or authoritative writer.

Do not add cryptographic signing, secrets, API authentication, another service process, or external infrastructure in this task.

### 2. Internal writer capability / construction authority

A caller that only has the supported public E6 platform API must not be able to call raw methods to manufacture promotion authority.

Use a bounded E6-owned internal authority mechanism. A reasonable implementation is an internal writer capability/factory-owned writer that is not part of the supported package export surface. The exact implementation is E6-owned, but the result must satisfy:

- raw write methods cannot be exercised through the supported public package API;
- service/factory-authorized writes remain possible;
- direct construction of authority-looking DTOs does not by itself grant write authority to the production persistence instance;
- test-only internal fixtures may still test storage mechanics, but they must be clearly internal/test-only and must not become public production authority APIs.

Python underscore/privacy conventions are not a hostile-code security boundary by themselves; combine export/factory design with internal construction/write authority so the supported production path is unambiguous.

### 3. Initial lifecycle registration guard

Independently enforce that a newly registered strategy version begins only as:

```text
current_lifecycle_state = DRAFT
registry_revision = 0
```

Requirements:

- Python persistence/registration path rejects caller-supplied non-DRAFT state or nonzero revision before authoritative insertion;
- add database-level defense in depth for initial insert where practical in the still-unmerged baseline migration;
- same identity/content idempotency behavior must remain coherent;
- no direct registration of an already-CANDIDATE strategy.

### 4. Projection mutation guard

Prevent naked supported-path mutation of `strategy_versions.current_lifecycle_state` / `registry_revision` outside the lifecycle append path.

Because raw SQLite connection access is removed from the supported public API, arbitrary direct SQL is outside the supported trust boundary. Still add database-level defense in depth where practical so projection updates must correspond to a coherent lifecycle transition/revision change rather than an arbitrary UPDATE.

Do not create a trigger design that breaks the existing atomic append-transition transaction.

### 5. Evidence provenance model

Document the exact authority model:

- E2 compatibility becomes promotion authority only when produced/ingested through the supported E6 service path using the configured E2 boundary;
- E3 BacktestResult / ValidationDecision becomes promotion authority only when ingested through the supported E6 service path and passes the accepted canonical validators/bindings/local-execution metadata checks;
- raw caller-constructed record objects are data structures, not authority, unless written through the internal authorized persistence path;
- the threat model assumes trusted in-process project code and controlled DB-file access; arbitrary malicious in-process code, monkey-patching/introspection, or an attacker with direct filesystem/SQLite write access is **out of scope** and must not be claimed as prevented.

Do not weaken canonical validation to implement provenance.

## Required tests / static proof definitions

Add deterministic local-only tests proving at minimum:

1. supported public `storage` imports do not expose raw `SQLiteRegistryStore`, raw `connect`, or equivalent writer/connection handles;
2. supported SQLite platform factory returns the safe E6 platform/service surface and does not return/expose a raw mutable connection/writer;
3. raw caller-constructed E2/E3-looking records cannot be persisted/promoted through the supported public API without going through the accepted service gates;
4. direct registration with `CANDIDATE`, `BACKTESTING`, `REJECTED`, or nonzero revision fails closed and leaves persistence unchanged;
5. normal service intake still creates `DRAFT / revision 0`;
6. valid service-authorized `DRAFT -> BACKTESTING` and `BACKTESTING -> CANDIDATE` flows remain representable when durable accepted E2/E3 evidence exists;
7. all previously defined invalid-evidence, forbidden-edge, rollback, append-only, and canonical-binding tests remain present;
8. database defense-in-depth rejects incoherent initial projection and naked lifecycle projection mutation where the implementation supports that guard;
9. synthetic PASS fixtures remain explicitly test-only and are not represented as project executable evidence.

Do not execute these tests in GitHub.

## Required actions

1. Fetch latest `main` and non-destructively synchronize it into `agent/e6-platform` once before correction. Preserve history; no force push/destructive rebase. The expected main-only delta is E7 review/coordination evidence.
2. Implement only the supported-public-boundary / internal-writer / initial-projection / projection-guard correction described above.
3. Preserve `src/registry/contract_validation.py` semantics and all accepted evidence bindings.
4. Keep the existing exact lifecycle edge allowlist and SQL forbidden-edge trigger.
5. Do not add PAPER, READY_FOR_APPROVAL, APPROVED, SHADOW, LIVE, DEGRADED, RETIRED, or generic lifecycle authority.
6. Do not add ApprovedTradePlan, OrderRequest, OrderResult, Fill, Position, OKX `sz`, provider identities, reconciliation, Demo execution, or other Slice 3 execution-audit persistence.
7. Do not edit `contracts/**` or E1/E2/E3/E4/E5/E7 production code.
8. No dashboard expansion, broker/API work, credentials, asset movement, network/provider calls, or workflow/CI changes.
9. Update `docs/platform/**` as needed to document the trusted-process authority model and supported public API.
10. Update `status/E6_EARLY_SLICE2_HANDOFF.md`, `status/E6_STATUS.md`, and `coordination/E6/STATUS.md` with exact sync/correction revisions, changed-file scope, public API before/after, authority model, and claimed finding disposition.
11. Executable verification remains local-only. Without a Product Owner-approved local environment, keep `NOT_RUN` and record exact commands:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/registry -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
```

12. Do not run tests, migrations, backtests, provider requests, GitHub Actions/CI/hosted runners, or GitHub-triggered project compute in this environment.
13. Push only this bounded correction to existing PR #16 branch, update STATUS/handoff, then stop. Do not merge PR #16 or begin another E6 feature automatically.

## Acceptance

Static/source completion requires a documented trusted-process authority boundary where the **supported public E6 API** cannot directly obtain/use authoritative raw persistence writers or SQLite connections, initial strategy projection is always DRAFT/revision 0, promotion writes still pass the accepted E2/E3 evidence gates, and DB-level defense in depth prevents incoherent projection mutation without breaking the normal atomic lifecycle path.

E7 must be able to distinguish supported production authority from intentionally internal/test-only storage mechanics. Do not claim protection against arbitrary malicious in-process Python code or direct external DB-file compromise.

Executable verification remains `NOT_RUN`; Gate A/B/C/D remain blocked.

## Writable scope

- `src/registry/**`
- `src/storage/**`
- `tests/registry/**`
- `tests/storage/**`
- `docs/platform/**`
- `status/E6_EARLY_SLICE2_HANDOFF.md`
- `status/E6_STATUS.md`
- `coordination/E6/STATUS.md`

## Forbidden scope

- `contracts/**` edits;
- E1/E2/E3/E4/E5/E7 production rewrites;
- later lifecycle expansion;
- Slice 3 execution/provider persistence;
- provider/API execution;
- credentials/secrets;
- external auth/signing infrastructure;
- PAPER/READY_FOR_APPROVAL/APPROVED/SHADOW/LIVE authority;
- GitHub Actions/CI/hosted/project compute;
- executable PASS claims.

## Completion / status

Close only the supported-public/raw-persistence authority portion of `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`, push the exact source/test/handoff revision, update STATUS, and stop for E7 re-review.