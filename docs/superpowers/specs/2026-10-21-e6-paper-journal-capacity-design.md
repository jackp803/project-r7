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
Delta payloads are at most64KiB; larger changes use an early keyframe. Together
with the16MiB keyframe and127-link limit, generated chains fit the32MiB aggregate
uncompressed-payload budget. The decoder also enforces that aggregate independently
and retains only decoded patches, not every base64 envelope. These are physical
resource limits, not financial or evidence-threshold changes.
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

The prefix protocol has a separate immutable new-run marker, inserted before
checkpoint0 in the same transaction. This distinguishes older codec-only0025
runs from newly prefix-enabled runs; no old run gains this marker automatically.
The root prefix binds the original run binding, physical profile and semantic
checkpoint0 hash. Each next prefix is appended atomically with the exact
publication receipt, after effects are committed. It hashes the previous prefix,
run/revision/operation, existing request/state/outcome/effect hashes and publication
clock, without duplicating those full payloads. Prepared/APPLIED-but-unpublished
operations never advance the published prefix. Idempotent publication validates
its original prefix rather than replacing it. SQL guards forbid UPDATE/DELETE/
REPLACE, missing predecessors and prefix records without actual source facts.

Add a covering (run_id,base_revision,operation_id) index for unfinished-tail
lookup. Before the private audited-prefix mechanism exists, retain the full
operation scan and compare this indexed tail with the complete pending set;
an old unfinished intent cannot be hidden behind a claimed prefix boundary.
Independent full audit checks every prefix/fact and exact prefix inventory;
a missing root on a marked run refuses instead of falling back to codec-only.

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

### D implementation refinement

The first current-reader component is intentionally unintegrated and returns an
immutable CURRENT_FACTS_ONLY result. It can validate management facts even when
an older prefix is corrupt; only the separate full audit may grant historical
eligibility. Older codec-only runs refuse the bounded-reader API rather than
being silently described as bounded.

Historical progress/proof must be owned by the exact journal instance, with an
unserializable issuer identity. Bind SQLite schema_version/data_version and the
connection's total_changes; another connection's write, schema change or unknown
same-connection mutation invalidates readiness. A reopened/restored owner starts
without proof. Progress/results are diagnostic and cannot be imported as proof.

Audit a fixed actual published-prefix cutoff. Use bounded keyset batches across
operations, effects, checkpoints, publications, prefix inventory and generations;
verify exact original facts, counts and contiguous lineage. Do not finish with an
unbounded COUNT/anti-join scan in a protective deadline. Publication operation IDs
are not time ordered: a separate bounded publication inventory is necessary to
find orphan rows that a join from valid operations would omit. Add only indexes
needed for bounded effect/revision scans. Compare relevant actual schema objects
with the packaged E6 model before trusting immutable-history assumptions.

Initially invalidate on every change while developing the private auditor; keep
this conservative component unintegrated. Then add tracked qualified own-write
extension. A SQLite authorizer observation may record touched tables/schema and
actual change deltas in fixed internal mutation scopes, not accept a caller PASS.
Unknown mutation footprints or concurrent external changes must invalidate proof.
Preserve all exact domain/publication validation and immutable SQL guards.

The borrowed canonical connection seam must preserve Python SQLite transaction
semantics. Actual source inspection refines the earlier context-manager concern:
the process journal uses isolation_level=None; principal canonical writers already
use explicit BEGIN IMMEDIATE/commit, while conflict recording relies on ordinary
implicit single-fact transactions. Keep these original individual boundaries.
A trusted borrowed facade may keep ordinary implicit transactions enabled while
the process journal retains its explicit idle BEGIN IMMEDIATE/commit protocol;
test rollback, close ownership, original per-writer commit boundaries and all
distinct-journal financial guards before integration. Otherwise retain separate
connections and conservative invalidation; do not silently alter transactions.

Implemented own-write refinement: only fixed E6 intent/effect/publication/
generation/pause/canonical/feedback scopes observe actual compiled SQLite writes,
including triggers, and bounded total_changes. The observer never denies a
protective write; unknown tables/UPDATE/DELETE/DDL/failed/nested work revokes the
private proof. Compare main AND temp schema versions, data_version and actual
changes before/after each scope. Prior unknown SQL cannot be laundered by a later
valid append. Main-history table/view shadows in temp prevent a new audit.

Freeze each original inventory's key upper bound and physical rowid cutoff in the
initial actual read snapshot. Later valid publication IDs may sort before an old
cursor, so rowid cutoff is required as well as logical ordering. Preserve the one
original PREPARED/APPLIED snapshot for audit of its immutable original facts;
tracked completion/publication extends the live tip separately. Complete original
inventory validation is still required before any live extension is eligible.
This bounds returned rows, not yet CPU/latency: resource scheduling and capacity
measurement remain mandatory before normal entry/healthy gates activate.

### D independent producer refinement

Use the same E6 batch verifier in a separately owned read-only process. It pins
one actual SQLite WAL read snapshot of the original active canonical file, not a
second active database or copied evidence. Source appends can continue while its
fixed snapshot completes. No migration, write or persistent permission is allowed
in that reader. Release the snapshot on completion, failure or cancellation; E4
broker validation of captured state runs after releasing the read transaction.

The diagnostic snapshot report alone is never an accepted proof input. E6 owns
the actual child through the existing platform Job/process-group, private bounded
stdout and a fresh launch nonce. The registered internal E6 receiver ties that
actual process to its exact journal-instance state/issuer, launch source file
identity, implementation hash, original prefix and process generation. The child
may observe a later valid prefix; require exact source hashes and a revision/
generation within the parent's independently tracked own-write extension. Any
unknown/external/schema mutation invalidates the parent state even if the child
completed an older valid snapshot. There is no file/result/PASS import endpoint.

Reuse the original bounded process lifecycle (300s deadline, below-normal
priority,16KiB maximum report), with all blocking IO/reaping in its owning helper
thread. Poll reads only actual completed private session data and bounded source
facts; it does not wait or hash source/history. A failed reap retains its handle,
denies a successor and requires confirmed bounded cleanup before lender close.
Pre-dispatch thread-start failure unwinds only its own state without leaking a
process or making the source connection unclosable.

This component has not yet established whole-product CPU/RSS/protection-latency
qualification. Existing memory enforcement is SOFT_LIMIT_ONLY; do not describe a
deadline/process boundary as a hard memory ceiling. Actual runtime scheduling,
current-reader switch, entry/healthy gates, truthful UI and whole-product capacity
remain required before ordinary encoded-profile rollout or real observation.

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
