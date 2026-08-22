# E7 Current Task

- task_id: `E7-20260822-009`
- issued_at: `2026-08-22T16:08:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-e6-public-boundary-final-review-20260822`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003, prior E7 reviews under `status/e7/`

## Objective

Perform the final exact-revision static/security review of corrected PR #16 after E6 task `E6-20260822-007`, and decide whether the supported-public/raw-persistence portion of `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001` is closed under the explicitly documented trusted-process modular-monolith authority model.

This task is static/source review only. It does **not** authorize project execution, migrations, PAPER/SHADOW/LIVE, provider calls, or GitHub compute.

## Review inputs

- PR: `#16 platform: integrate early Slice 2 registry and evidence persistence`
- E6 branch: `agent/e6-platform`
- corrected source/tests/docs revision: `ca41cb92cfaf23c7c0d00a7802727fa28f5cca86`
- handoff refresh: `a81bb0b43c96dc1ddf9152077ea5ca37d47032df`
- platform-status refresh: `68c9d8e63cc9920975a06a62a080a3ca08a2872f`
- observed PR head at PM audit: `607feaf1663966cd0fac82a244d368822ea28214`
- correction-pin -> PR-head delta: `coordination/E6/STATUS.md + status/E6_EARLY_SLICE2_HANDOFF.md + status/E6_STATUS.md only`
- E6 synchronization merge: `610cdc4edbcd3fdf3f74c1eed9691253b4453cc9`
- main synchronized by E6 before correction: `36d1b5f3baee298dc33da444e0a31782a8cc6d7e`
- accepted prior finding: `E6-EVIDENCE-CONTRACT-001 / CLOSED / PASS STATIC`
- finding under final review: `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`
- executable verification: `NOT_RUN`

## Authority model for this review

Evaluate the repository as a trusted-process Python modular monolith with controlled DB-file access.

The supported production API must prevent ordinary downstream/project code from obtaining raw authoritative persistence writers/connections or manufacturing promotion authority through supported interfaces. Do **not** require impossible protection against arbitrary malicious in-process Python code, deliberate underscore-module imports, introspection/monkey-patching, or an attacker with direct filesystem/SQLite write access; those are outside the declared boundary and must only be checked for accurate documentation, not treated automatically as blockers.

## Required review

1. Work only on fresh branch `agent/e7-e6-public-boundary-final-review-20260822` created from latest `main` after this TASK issuance.
2. Review actual source/tests at exact revision `ca41cb92...`; do not rely only on E6 STATUS/handoff claims.
3. Verify the supported `storage` package surface:
   - `storage.__all__` exposes only the safe SQLite platform factory (currently claimed `open_sqlite_platform`);
   - ordinary supported imports do not expose `SQLiteRegistryStore`, raw `connect`, migration/write primitives, or an equivalent mutable writer/connection handle;
   - the supported factory returns `StrategyPlatformService` or an equivalently narrow safe facade, not a tuple/object exposing raw store/connection;
   - the factory-returned service does not publish a raw writer/connection through supported public attributes/methods.
4. Inspect `storage._sqlite_registry` and related implementation boundaries. Confirm raw mechanics are clearly internal/test-only, and authoritative store construction requires the intended E6-owned internal writer capability. A deliberate import of an underscore implementation module by hostile in-process code is out of scope; however, any raw writer leaked through the supported factory/package API is BLOCKING.
5. Verify caller-constructed `CompatibilityEvidence`, `ValidationEvidenceRecord`, `LifecycleTransitionRecord`, or other DTOs are data only and cannot be written to the production persistence instance through a supported public API without the accepted E6 service path.
6. Verify initial registration authority:
   - Python persistence rejects new strategies unless `current_lifecycle_state=DRAFT` and `registry_revision=0`;
   - database defense in depth independently enforces the same initial projection;
   - idempotent same-identity/content behavior remains coherent;
   - no supported path can register an already-BACKTESTING/REJECTED/CANDIDATE strategy.
7. Verify lifecycle projection defense in depth:
   - naked supported-path updates of `strategy_versions.current_lifecycle_state` / `registry_revision` are unavailable;
   - SQL projection guard requires coherent matching lifecycle transition history/revision movement;
   - the guard does not break the intended atomic append-transition transaction by source design;
   - exact three-edge allowlist, forbidden-edge trigger, append-only history, current-state/revision checks, atomicity, and rollback remain intact.
8. Reconfirm durable promotion authority has not regressed:
   - `DRAFT -> BACKTESTING` still requires accepted durable E2 `PASS / LOCAL_EXECUTION` authority and complete metadata;
   - `BACKTESTING -> CANDIDATE` still requires accepted bound E3 ValidationDecision(PASS) + parent BacktestResult, canonical validation/binding, and complete local PASS metadata;
   - promotion authority is checked before authoritative lifecycle mutation.
9. Recheck `E6-EVIDENCE-CONTRACT-001`: canonical BacktestResult/ValidationDecision validators, exact bindings, invalid enum/type fail-closed behavior, caller metadata bypass protection, and BacktestResult-alone inability to authorize CANDIDATE remain accepted.
10. Review `tests/storage/test_public_persistence_boundary.py` and related test definitions. Confirm static definitions cover:
   - supported package exports only safe factory;
   - factory returns safe facade without raw writer/connection;
   - direct raw-store construction without internal capability fails;
   - authority-looking DTOs are not supported write capabilities;
   - non-DRAFT/nonzero initial registration rejection with no mutation;
   - SQL initial-projection rejection;
   - naked projection update rejection;
   - normal service intake starts `DRAFT / 0`;
   - valid service-authorized BACKTESTING/CANDIDATE flows remain representable;
   - prior evidence/edge/rollback tests remain present.
   Do not execute tests in GitHub.
11. Check documentation accurately states the trust boundary and does not claim protection from arbitrary malicious Python execution, introspection/monkey-patching, or direct DB-file compromise.
12. Recheck PR #16 current branch against latest `main`. Coordination-only TASK commits after the correction pin are not by themselves a resynchronization blocker. Require E6 resynchronization only for meaningful production/shared-contract drift or a real merge conflict affecting reviewed source.
13. Recheck scope: no `contracts/**`, E1/E2/E3/E4/E5 production, workflow/CI, provider/credential/secret, Slice 3 execution-audit, later lifecycle, or unrelated changes.
14. Persist an E7 final review artifact under `status/e7/` and update `coordination/E7/STATUS.md` with:
   - exact reviewed E6 revision and observed PR head;
   - supported-public API disposition;
   - internal writer/capability disposition;
   - initial projection guard disposition;
   - lifecycle projection guard disposition;
   - evidence provenance/authority disposition;
   - `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001` final disposition;
   - `E6-EVIDENCE-CONTRACT-001` regression disposition;
   - PR #16 merge recommendation;
   - executable verification `NOT_RUN`;
   - Gate A/B/C/D unchanged.
15. If the supported production API no longer exposes raw authority-bearing persistence surfaces, initial/projection guards are coherent, accepted E2/E3 evidence gates remain intact, and no other blocker exists, state `PM MAY MERGE PR #16` and close `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001` as `PASS STATIC` under the documented trust model.
16. If blocked, identify the exact reachable **supported production API** bypass or source defect and owner. Do not reject solely because underscore/internal Python implementation remains technically importable by arbitrary in-process code.
17. Do not modify E1-E6 production code or shared contracts. Do not run project tests, migrations, backtests, provider calls, GitHub Actions/CI/hosted runners, or GitHub-triggered compute. Do not create a Codex ticket without a locally reproduced executable defect.

## Acceptance

Task completes when Git contains an exact-revision final E7 review that either closes `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001` and recommends PM merge PR #16 under the declared trusted-process authority model, or keeps it blocked with a precise supported-API/source condition. Executable evidence remains `NOT_RUN`; Gate A/B/C/D remain blocked.

## Writable scope

- E7-owned review/status/integration documentation
- `coordination/E7/STATUS.md`

## Forbidden scope

- E1-E6 production implementation edits;
- shared-contract changes;
- lifecycle expansion;
- Slice 3 execution/provider persistence;
- provider execution;
- PAPER/SHADOW/LIVE advancement;
- GitHub compute/CI.

## Completion / status

Persist the final review and STATUS, then stop and wait for PM. Do not merge PR #16 or start another task automatically.