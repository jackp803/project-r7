# E6 Paper journal capacity: approved amendment detailed design

Authority: the human explicitly approved E6_JOURNAL_CAPACITY_DESIGN_REVIEW.md
and directed completion of detailed design and implementation. Same Master,
branch and inline execution. This document refines that scope; it does not
change financial authority, original selected policies or evidence completeness.
No further per-stage confirmation is required within the approved scope.

## Product objective and boundaries

Support the declared1s protection/5s acquisition cadence and actual4h strategy
cache for long Paper operation without copying the whole state at every tick or
replaying the whole history before protecting an existing position. Retain every
logical operation and exact broker/runtime state, fill/effect/publication identity
and original policy. Never grant entry from a recovered broker snapshot alone.
The measured full-state journal projection is about241GB before other data;
the16GiB backup bound and all source/risk limits remain unchanged.

Alternatives considered: full-state compression alone preserves simple reads but
duplicates unchanged history and leaves unbounded recovery; deleting/checkpoint
compaction violates immutable evidence; versioned lossless deltas plus complete
audit is the accepted direction. No second active database or historical rewrite.

## A. Pure lossless versioned physical codec

Use a new explicit storage profile for new runs only. No profile row means legacy
full JSON. Existing rows and old migrations remain unchanged. A new immutable
run/profile selection and the revision0 checkpoint commit in one E6 transaction.
Only the trusted product composition selects the profile; no HTTP/cloud policy
callback, caller PASS or restored permission can select/authorize a run.

Keep the existing checkpoint state_hash as the hash of the exact canonical full
logical JSON. For the new profile only, state_json stores a versioned canonical
physical envelope: codec, run_id, revision, kind KEYFRAME/DELTA, previous revision
and semantic hash for DELTA, uncompressed payload byte count and SHA256, and
canonical base64 of zlib-compressed UTF8 payload. Maximum logical or patch payload
16MiB; maximum encoded input24MiB; strict types, closed fields, duplicate-key and
nonfinite/float refusal. Oversize/unsupported inputs explicitly refuse this profile.

Revision0 and every128th revision are keyframes. Other revisions choose a delta
only when its compressed physical envelope is smaller than a keyframe. An earlier
keyframe is allowed; no chain may cross more than127 predecessor links. A delta
binds exactly revision-1 and its expected full-state hash, within the same run.
The reader obtains original stored rows through an E6-owned callback, reconstructs
in ascending order and verifies every payload and full-state hash. Missing,
wrong-run/revision/hash, cyclic/overlong chains, malformed base64, trailing zlib
data, decompression bombs or noncanonical JSON refuse. No executable pickle.

Patch representation is a closed recursive JSON tree: replacement values;
object removes plus per-key child patches; array common-prefix/common-suffix
splice. Counts are integers, never booleans; paths cannot escape a typed object.
The decoder builds a fresh state and does not mutate any base object. Canonical
serialization must reproduce the original complete raw JSON exactly. Logical
broker/provider-field validation remains in existing E6 _state/_read_json; the
codec itself is pure and creates no financial evidence or entry permission.

## B. Storage integration and legacy compatibility

Add a new migration, never edit0011. The new profile table has UPDATE/DELETE
refusal triggers. Store its immutable physical envelope in existing checkpoint
rows; the public PaperOperation/PaperProcessRecovery APIs still return full
logical state_json and unchanged effect hashes. Existing completed retries,
process generations, deferred foreign keys and atomic effect/checkpoint rollback
remain authoritative. Existing runs cannot change storage profile on retry.

Initially retain the existing full recovery validation. This independently
testable stage saves storage without claiming bounded protection recovery or
long-observation eligibility. Full audit may use a bounded ephemeral decoded
window within its own consistent read transaction; no persisted/global PASS.

## C. Explicit bounded management and historical-audit boundary

Add E6-owned immutable ordered prefix/sequence records binding the run, operation
request, previous prefix, semantic checkpoint hash, exact outcome/effect hash and
publication receipt. Indexed pending work and a current bounded codec chain must
be verified without enumerating all historical published operations. Preserve
legacy recover as the independent complete audit and provide an explicit current
management recovery result whose proof status is REQUIRED unless E6 owns a valid
complete-prefix audit and verified subsequent append extension.

Audit validity is process-instance owned and tied to the exact run/binding,
prefix revision/hash, SQLite schema/data-version and tracked writes. No caller
can deserialize/import a proof. Unexpected external writes or schema changes,
history tampering or a missing prefix invalidate it. Current state/protection
can recover first, but entry and healthy-forward eligibility stay inhibited.
An unaudited/corrupt past must never inherit a cached full-history PASS.

Normal process and canonical publication should use one trusted E6 connection
in the owning thread, preserving each existing transaction boundary and close
ownership. Trusted same-connection append/publication can extend an owned proof;
outside connection changes invalidate it conservatively. If connection sharing
cannot preserve existing canonical transaction semantics, retain invalidation
and deny new entry until an independent audit rather than silently trusting it.

Independent history audit must progress in bounded batches outside protection
work, compare exact fixed-prefix records and reject changing/corrupt inputs.
Each audit batch is resource limited; current protection work runs first. Audit
progress is diagnostic only until the complete fixed prefix is proved and the
tail is verified. No unbounded old-history scan occurs in a protection callback.
Full backup/restore performs its own complete verification; restore remains
inhibited and does not import an in-memory audit lease.

## D. Acceptance and rollout

Tests first at each boundary: pure codec exact equivalence/hostile shapes and
limits; actual SQLite legacy/new runs, trigger immutability and atomic crashes;
exact operation/outcome/publication retries and stale generations; current-read
corruption, audit invalidation, external writes and successor entry inhibition;
funding-pending/original-selection/protection lifecycle and multiframe regression.

Measure actual whole-product30day-equivalent retained disk/CPU/RSS and management
latency, including full cache, source failure, pending funding, publication delay,
restart and contention. Retain failures and distinguish real measurements from
projections. Public archive3.62GB PASS is only one component; include requests,
outcomes, prefixes, WAL/indexes and backup overhead in whole-product budgets.

The new storage profile must not be selected in an ordinary installed product
until its entire codec/storage/proof/audit path, whole-product capacity and new
exact Windows build/PQR are qualified. Old bffc qualification never transfers.
No real-time observation credit is earned from controlled/accelerated testing;
48h/30d/trade counts and original target/Ubuntu/cloud remain independent gates.

Self-review: authority and immutable-history constraints preserved; codec versus
logical validation and management versus full-audit claims explicitly separated;
no placeholder migration changes, account access, retention deletion or limit rise.
