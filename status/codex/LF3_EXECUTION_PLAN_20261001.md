# LF-3 local execution plan — 2026-10-01

Authority: `status/PM_CODEX_LF3_DELEGATION_20261001.md` at authoritative main
`5a78fcb831d5855ce5823832286e438d86c65261`.
Accepted executable baseline: `cec90965a0cd29fe59bec604987ebeebfb5ad09d`.

1. Audit all 20 rows of readiness profile V0.1 section 7 against actual test
   assertions. All 20 rows apply to deterministic local fixtures.
2. Add bounded restart tests for fresh preflight identity/reconciliation and
   repeated recovery with missing protection. Preserve all shared contracts and
   production semantics. Run focused regressions and remediate ordinary defects
   if revealed.
3. Commit one candidate, push it to the bounded branch, and materialize a clean
   detached worktree at its exact revision. Run the complete LF-3 scenario
   matrix there, recording test IDs, counts, timestamps, log hashes, and clean
   revision proofs.
4. After LF-3 passes, run the manifest's complete Phase 1 and Phase 2 commands
   on the same candidate. Audit output and obtain independent read-only review.
5. Persist sanitized evidence under `status/codex/`, push the branch, verify its
   remote revision, and return to PM. Evidence commits do not rebind the tested
   executable revision.

All execution is credential-free Windows local unittest simulation. No actual
provider access, credentials, mutations, runtime launch, capital, hosted compute,
or merge to main is authorized. Synthetic runtime roles and in-memory broker
objects in tests do not represent started SHADOW/PAPER/LIVE processes.

The guarded Antigravity advisory attempt was refused before dispatch because
this worktree was not already trusted. The audit proceeds locally without
changing trust or selecting a paid fallback.

Independent review of the first candidate identified two coverage gaps despite
passing execution: restart-flat checks needed a composed fresh-reconciliation
test, and repeated missing-protection recovery needed assertions on the durable
E5 interpretation itself. The updated tests reopen the exact flat graph, require
a new simulated provider observation/E5 decision and bound FP16 preflight, then
prove fresh positive exposure overrides stored flat truth. Repeated missing
protection also checks the exact persisted interpretation and lifecycle binding.
The first candidate's evidence remains historical and is not the final LF-3 PASS.
