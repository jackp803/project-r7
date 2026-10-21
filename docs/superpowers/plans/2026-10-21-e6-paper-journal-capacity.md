# E6 Paper journal capacity implementation subplan

Same original Master and branch. Detailed design:
docs/superpowers/specs/2026-10-21-e6-paper-journal-capacity-design.md.
Human approval explicitly includes detailed design and implementation; preserve
inline continuous execution, no repeated Task approval. This subplan is part of
recorded-funding Tasks2/3/4/6, not a replacement project or acceptance standard.

- [x] A. Pure versioned physical codec (component16PASS; no product activation)
- [x] B. New-run E6 storage profile and legacy readers (component; ordinary default unchanged)
- [ ] C. Immutable prefix, indexed pending work and explicit full audit
- [ ] D. Bounded current management, private audit proof and successor entry gates
- [ ] E. Whole-product capacity, regression and new exact native qualification

## A — codec before persistence

Files: src/storage/paper_state_codec.py;
tests/storage/test_paper_state_codec.py. No database/service modification here.
Interfaces: encode_state(raw, *, run_id, revision, previous_raw=None) -> str;
decode_state(encoded, *, run_id, revision, expected_hash, read_previous) -> str,
where read_previous(revision) returns the same run's (encoded, semantic_hash).
ValueError with stable PAPER_STATE_CODEC_ reasons on malformed/unsupported input.

Write and execute failing tests before implementation: exact mixed-type nested
state changes/deletes/array rolls and unchanged states; Unicode/key ordering;
keyframe0/128 and early-keyframe choice; bounds/hostile duplicate keys/bools;
wrong source hash/run/revision/base, missing/cyclic/too-deep chain, altered compressed
bytes/base64/trailing stream/oversized expansion and noncanonical logical input.
Then implement closed recursive patches and bounded zlib codec with standard
library only. Assert original base is unchanged, logical hash and raw output exact.
Verify: python -m unittest tests.storage.test_paper_state_codec -v => all PASS.

## B — persistence only, retain full recover

Files: next numbered src/storage/migrations SQL, storage/paper_process.py and
tests/storage/test_paper_process_journal.py plus new profile integration tests.
Add immutable run profile; explicit trusted create_run storage_profile selection,
legacy default and retry profile binding. Delegate exact physical encoding to A;
_checkpoint returns decoded logical state. Existing state/effect hashes unchanged.
RED then GREEN: actual SQLite old/new reopen; every effect/checkpoint transaction
fault; profile reselect refusal, malformed/foreign codec row, stale process,
published/applied/prepared retries and complete independent history verification.
Verify new suite plus tests.storage.test_paper_process_journal/existing and
tests.storage.test_migration_compatibility_v02. No ordinary activation yet.

## C — E6 prefix and bounded pending inventory

Add immutable ordered prefix proofs in the same transactions as facts, plus
indexes for actual unpublished/prepared work. Define audit_full(run_id) as the
complete legacy-strength validation of all logical operations, physical chains,
sequence records, request/effect/publication hashes and current binding.
RED then GREEN for missing/reordered/extra/hash-corrupt prefix, mismatched original
effects, pending-work inventory and old/new history. Preserve original immutable
rows/readers. Tests must show bounded current inventory does not imply full PASS.

## D — explicit management/audit separation

Add recover_current(run_id) with bounded current-chain/pending proof and explicit
audit-required state. Add process-owned audit lease with exact SQLite invalidation
and trusted same-connection append tracking; no serializable/importable proof.
Audit work in bounded batches after protection, entry/healthy gates require the
completed prefix plus verified append extension. Share the E6 connection only
through trusted E6 constructors, with unchanged canonical transaction semantics.
RED then GREEN external/schema/history mutations, successor/no-proof and stale
generation, canonical publication crash seams, funding pending and original-policy
recovery, no hot full-history reads/hashes/network, control views and assessment.
Any invalidation must preserve management and deny new entry until proof completes.

## E — whole product and native acceptance

Run impacted E4/E5/E6/legacy4h/multiframe/source/report/UI/browser suites and final
independent whole-change review. Measure actual permitted30day whole-product
disk/CPU/RSS/protection latency and backup/restore at original bounds; include
pending funding, failure/restart and resource contention. Refreeze fixed PQR
inventory, build exact-clean Windows package, run full native qualification and
positive/negative ordinary source/start paths. No old receipt transfer.
Only after actual research/independence/current policy/source admission passes
may real ordinary Paper observation begin. Preserve all external/time sample gaps.

Review focus: semantic raw-byte/effect identity; malicious codec/base/prefix rows;
audit proof invalidation versus genuine external DB writes; connection ownership
and transaction rollback; long-run whole-product growth and bounded protection.
Self-review: each design stage has tests and an explicit claim boundary; B does
not preclaim D, accelerated capacity does not preclaim real observation.
