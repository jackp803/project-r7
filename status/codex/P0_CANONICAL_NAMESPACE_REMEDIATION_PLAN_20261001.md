# P0 Canonical Namespace Remediation Plan

> Execute inline with the existing Product Owner delegation; use systematic debugging, TDD, and verification before completion.

**Goal:** Remove the remaining duplicate source-root module identities and complete credential-free qualification.

**Architecture:** Implement the accepted top-level package namespace under `PYTHONPATH=src`. Normalize static imports mechanically across the source/test dependency graph; preserve all executable logic and strict authority validation.

**Tech Stack:** Local Windows, Python unittest and AST, Git.

**Spec:** `status/PM_CODEX_LOCAL_COMPLETION_DELEGATION_20261001.md` and `docs/architecture/CANONICAL_PYTHON_IMPORT_NAMESPACE.md`.

## Constraints

- Preserve the failed detached candidate `bab879dcda2d90bb9facb82f49377529e6b8d35f`.
- No shared-contract or architecture change, type-validation weakening, dual-type acceptance, or module aliasing.
- No provider/private API, exchange credentials, mutation, trading runtime, capital exposure, or GitHub compute.
- Preserve the FP-02 reason aggregation and FP-11 temporal fixture corrections.
- Persist sanitized evidence without local filesystem paths; push a Codex branch; do not merge main.

## Review Focus

- Genuine wrong authority types must still fail closed in the existing canonical identity regression.
- Importing real consumers must not load any parallel `src.*` application module.
- Copied owner rows cannot prove unsupported modes; both rejection reasons must remain present.
- An evaluation before provider receipt must still be rejected without persistence.
- Source edits must be import-prefix changes only, with normalized AST equivalence checked mechanically.

## Task 1: Normalize the existing source/test import graph

Files: remaining static `src.*` imports under `src/` and `tests/`; `tests/integration/test_canonical_import_identity.py`; sanitized evidence under `status/codex/`.

- [ ] Extend the existing import guard to inspect both source and tests for any static `src.*` application import.
- [ ] Run that regression before normalization; require an assertion failure naming non-canonical imports. Preserve the already reproduced real FP-11 integration type errors.
- [ ] Remove only the `src.` prefix from imports referencing existing source-root packages. Verify every transformed AST is equivalent after that import-name normalization.
- [ ] Run canonical identity, FP-11 integrated failure prevention, safety composition, and affected broker/execution tests. Keep wrong-authority and temporal negative cases intact.
- [ ] Commit source/import regressions and sanitized defect evidence together; push the bounded branch.

## Task 2: Establish and qualify the new exact candidate

- [ ] Create a detached worktree at the committed full SHA and verify HEAD, empty porcelain, and both diff exit codes zero.
- [ ] Run all 16 Phase 1 commands in manifest order. Measure actual counts; if a deterministic failure occurs, diagnose and continue the authorized bounded loop.
- [ ] After Phase 1 passes, run all 14 Phase 2 suites in manifest order on the same SHA.
- [ ] Independently review the final changes and measured evidence, then persist and push the final evidence branch for PM acceptance.

## Ruling

The correction covers all remaining static source-root import prefixes, rather than only Position call sites, because the accepted namespace decision explicitly forbids parallel namespaces for every package and their connected producer/consumer graph must share identities. This is an implementation of accepted architecture, not a packaging redesign.
