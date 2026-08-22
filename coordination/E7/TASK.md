# E7 Current Task

- task_id: `E7-20260822-008`
- issued_at: `2026-08-22T15:33:00+08:00`
- state: `HOLD`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0001/0002/0003

## Objective

Hold after completing `E7-20260822-007`. PR #16 remains blocked by the supported-public/raw-persistence authority portion of `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`; E6 now owns a bounded correction under `E6-20260822-007`.

## Accepted review evidence

- completed review task: `E7-20260822-007`;
- review artifact: `status/e7/E6_EVIDENCE_AUTHORITY_FINAL_REREVIEW_20260822.md`;
- E7 review evidence merged to `main` via PR #19, merge commit `a829ecc5b30c674d7ba66ff5234b67ab45a22971`;
- reviewed E6 source/tests revision: `df39836adabd04c77cc4f0d0b531ea10408866ab`;
- observed PR #16 head at review: `e7d1f3d9a99043107824a3c64d1d37663db8ff53`;
- exact lifecycle edge enforcement: `PASS / STATIC ONLY`;
- SQL forbidden-edge/append-only guards: `PASS / STATIC ONLY`;
- in-transaction durable content/binding revalidation: `PASS / STATIC ONLY`;
- `E6-EVIDENCE-CONTRACT-001`: `CLOSED / PASS STATIC / NO REGRESSION`;
- `E6-LIFECYCLE-PERSISTENCE-AUTHORITY-001`: `BLOCKING / NOT CLOSED / E6 OWNER`;
- blocking surfaces identified by E7: exported raw persistence writers/connections can manufacture authority-looking rows, initial non-DRAFT projection can be registered, and raw projection can be mutated directly;
- PR #16: `DO NOT MERGE`;
- executable verification: `NOT_RUN`;
- Gate A/B/C/D: `BLOCKED / UNCHANGED`.

## Future targeted re-review focus

Do not start until PM replaces this HOLD after E6 completes `E6-20260822-007`.

The future review should verify the documented **trusted-process modular-monolith authority model**, not demand impossible protection against arbitrary malicious in-process Python execution. Within that stated model, confirm:

1. supported public E6/storage APIs no longer expose raw authoritative `SQLiteRegistryStore`, raw SQLite connection, migration/write handles, or equivalent authority-bearing writer surfaces;
2. the supported SQLite composition/factory returns only the safe E6 platform/service facade;
3. raw storage implementation and writer capability are internal/test-only and not part of the supported production API;
4. caller-constructed CompatibilityEvidence / ValidationEvidenceRecord / lifecycle DTOs cannot by themselves write to the production persistence instance through a supported public API;
5. production initial strategy registration is independently constrained to `DRAFT / revision 0` in Python and database defense in depth;
6. naked lifecycle projection mutation is blocked by supported API design and database defense in depth without breaking atomic append-transition behavior;
7. valid service-authorized E2/E3 promotion flows remain coherent and the accepted canonical validators/bindings are not weakened;
8. exact early lifecycle vocabulary and three-edge cap remain unchanged;
9. no Slice 3/later lifecycle/provider/shared-contract scope appears;
10. documentation explicitly states the trust boundary: trusted in-process project code + controlled DB-file access. Arbitrary Python introspection/monkey-patching or an attacker with direct SQLite file write access is out of scope and must not be falsely represented as prevented.

If a supported production API still gives ordinary callers a raw writer/connection or allows evidence/projection authority manufacture, keep PR #16 blocked. Internal implementation imports used only by E6 tests are not automatically blockers if they are clearly outside the supported production API and cannot be obtained through the supported factory/facade.

## Required actions while HOLD

1. Do not modify E1-E6 production code or shared contracts.
2. Do not re-review PR #16 until PM replaces this HOLD after E6 completion evidence exists.
3. Preserve all prior E7 review artifacts/findings.
4. Do not advance Gate A/B/C/D, PAPER/SHADOW/LIVE, provider execution, or later lifecycle states.
5. Do not run project tests, migrations, backtests, provider calls, GitHub Actions/CI/hosted runners, or GitHub-triggered project compute.
6. If acknowledging HOLD, update only `coordination/E7/STATUS.md`.

## Acceptance

E7 remains idle while E6 corrects the supported-public/raw persistence authority boundary. Executable evidence remains `NOT_RUN`; PR #16 remains unmerged; release gates remain blocked.

## Writable scope

Only `coordination/E7/STATUS.md` for HOLD acknowledgement unless PM replaces this task.

## Completion / status

Wait for E6 correction evidence. Do not start re-review, merge PR #16, or start another integration task automatically.