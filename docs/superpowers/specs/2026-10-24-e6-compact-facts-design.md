# E6 compact facts — conditional scope detailed design / finite prototype gate

Authority: e6-compact-fact-layout-operator-decision.json, original Master/branch.
This is additional physical storage, not a second financial database/lifecycle.
Status: DESIGN_AND_FINITE_PROTOTYPE; NO_PRODUCTION_INTEGRATION_AUTHORIZED_BY_RESULTS_YET.

## Contract mapping

E6 public objects retain their exact canonical UTF8 bytes, original canonical ID,
SHA256, clock strings and null/integer types. Physical integer references never
become canonical IDs. A stored byte object is data only; canonical membership is
created only by the existing E4/E5-validated E6 writer transaction. A byte object
may exist after E6 completion and before canonical publication without becoming
an authoritative Projection, Binding, Fill or TradeResult.

Read contracts: agents/E6_PLATFORM.md, agents/E7_INTEGRATION.md,
docs/platform/E6_STORAGE_AUTHORITY_BOUNDARY.md and
docs/platform/E6_GATE_B_PAPER_RUNTIME_DURABILITY.md. The prohibition on E6 domain
reconstruction is preserved: decoding exact stored bytes is permitted; deriving
a new Position/lifecycle or replacing missing financial facts is not. Existing
canonical_payload, projection/binding/funding/TradeResult validators and conflict
rules remain authoritative. No domain implementation or contracts/ edit planned.

## Candidate formats to measure before selection

B: typed interned metadata, independent binary compression per JSON payload.
C: same metadata plus shared typed immutable byte objects, exact outcome byte
templates, bounded raw-byte deltas for Projection/Binding lineages, and binary
representation of the existing checkpoint envelope (same inner codec).
D: C with injective encoded atom keys instead of retaining duplicate full UTF8
lexical bytes for every hash/ID/time atom. Supplementary original TEXT lexical
columns/indices are retained for process operation/effect/publication tie/range
ordering. Only these three candidate formats are explored in this finite gate.
Original complete SQLite snapshot is baseline A. No layout is selected by a
JSON compression ratio alone. Both prototypes include all65source tables, every
column/row and all source index column sets/cardinalities. Only the seven measured
growing process/Projection/Binding tables are compacted; other tables retain
original values/types, including the actual partial unique ORDER_REQUEST index
and fixed dispatch json_extract(role) index. Other unmodeled expressions/predicates
refuse the finite prototype. Original schema SQL is retained as
non-executed diagnostic data. No original schema/triggers are executed in a clone.

Metadata atoms have an integer physical ID and typed binary representation.
B/C additionally keep original UTF8 lexical bytes with a UNIQUE index; D uses
an injective encoded key and the sparse logical lexical indices above. Numeric
interning does not authorize changing public sort/pagination semantics. Source
selectors use run/revision and lifecycle_revision for current facts; private
audit operation/publication cursors additionally need exact lexical tie order.
Other canonical tables stay literal, preserving their existing textual order.
Hashes/content IDs can pack hex to32bytes with an immutable prefix reference;
canonical UTC clocks pack signed microseconds plus exact precision/suffix.
Decode must reproduce the original TEXT exactly or refuse. Other strings stay
literal. Null, signed integers and BLOB remain their original SQLite types.

Physical JSON objects bind type, canonical subject identity, original byte hash,
original length, codec/profile and payload. C may refer to another already
written immutable object's exact bytes only within a closed allowed type and
identity. Exact same bytes across E6 effects/canonical membership may share one
object; different Unicode escaping or canonicalization stays a separate variant.
No semantic equivalence substitution or caller object/progress permission.

Outcome templates retain original literal bytes and typed references to exact
embedded payload byte spans. They never compute a missing financial object.
References include expected kind/identity/hash; wrong type, identity, bytes,
missing record, cycle or aggregate bounds refuse. Only canonical payload objects
may be embedded; no recursively nested outcome templates.

For Projection/Binding byte deltas: same type/position lineage only, original
prefix/suffix splice with full byte hash/length, at most127links, early keyframe
when smaller/required. Full original bytes are reconstructed before existing
canonical financial validation. This does not infer lifecycle from predecessors.
The existing checkpoint codec's inner keyframe/delta bytes and128/32MiB bounds
stay exact; binary metadata removes repeated envelope TEXT only. Unsupported
outer bytes use lossless literal storage in prototypes, never normalization.

## Atomicity and compatibility

| Original transaction | New physical data | Authority retained |
| --- | --- | --- |
| prepare intent | interned request/metadata and intent membership | original expected revision/generation |
| complete | exact effect bytes/template, any referenced byte data, checkpoint and hashes atomically | original E6 effect identity; no canonical publication yet |
| each canonical publication | exact typed byte data/link and canonical membership/current pointer atomically | original per-fact E4/E5 validators/conflicts; no batch transaction |
| publish receipt | original receipt plus prefix binding atomically | original contiguous E6 prefix |

New immutable profile only for explicitly selected new runs/fact lineages.
No rewrite of legacy tables, rows or prior checkpoint profiles. Public readers
dispatch by immutable profile and return original logical rows/objects; unknown
profiles refuse. Existing raw SQL consumers must use the common logical read
port where necessary; no physical BLOB can masquerade as canonical JSON.
SQL immutability/no-REPLACE/FK/uniqueness/contiguity guards remain mandatory in
production; experimental clone tables cannot qualify these semantics.

## History segments / recovery / resources

Each <=300s owned job pins a readonly original source snapshot and binds actual
private parent issuer, nonce, implementation, file/schema/profile, run/binding,
generation and contiguous [first,last] prefix/hash range. A completed segment
can advance only the same owning parent's private accumulator. No public method
accepts serialized progress/PASS. Duplicate/out-of-order/missing/failed/expired
segments or unknown/external/schema writes revoke eligibility. Known original
append scopes may extend only already checked immutable history. New process,
restart/restore or copied reports starts without this private accumulator.

Current management/protection/exit/funding allocation recover before history
completion. Entry/first fill/healthy-forward stay denied until full original
history plus actual tail pass. Current Control Center diagnostics remain
LAST_KNOWN only and show private owner revalidation/blocked reason.
Background jobs remain below-normal priority, bounded memory/pipe/deadline and
one per owner after all protection; polling/reaping never blocks a hot callback.
No persistent audit permission or separate active financial store.

Backup/verify/restore retain all physical data/indices/profile/reference closure
and original16GiB/4096file/300s operation limits. Restore fences current source
generation with bounded current verification, remains RESTORED_INHIBITED and
requires new complete financial history/reconciliation/reauthorization before
entry. Physical bundle verification is not financial-history PASS; independent
full historical audit remains required and available after restore. Existing
full-scan restore fencing must be adapted only if this contract trace is accepted.

## Finite prototype protocol and go/no-go

Use the actual4321revision snapshot SHA35e75388...23b9, source readonly; emit
fresh isolated NON_AUTHORITATIVE_FORMAT_EXPERIMENT files inside project artifacts.
Bound input to30000rows/128MiB, payload16MiB, references64, delta127links,
128entry/64MiB decoded cache and a <=270s internal deadline/300s owned process.
Prototype algorithms never become a product read/write entry or authorization.

Compare actual SQLite allocated bytes incl atoms/blobs/indexes, build/read CPU,
independent process peak RSS, exact all-column roundtrip, decoded-cache-empty
current checkpoint decode and canonical last-payload read. Label SQLite/OS cache
conditions explicitly; a warmed connection is not cold owner recovery. Preserve all failure results.
Bulk clone timing is not normal product write latency; original actual owner
timing remains separate. Projections are feasibility diagnostics ONLY, never
30day capacity PASS. Account for measured public archive3,622,328,474bytes and
other/static data with margin, not just growing JSON columns.

Only if finite measurement demonstrates a plausible fit, bounded recovery and
unchanged bytes, complete E6/E7 contract review and a concrete production plan.
If not, report exact evidence/blocker/alternatives; do not expand speculation.
Then RED-first bounded implementation, actual3,110,400operation whole-product
generation/verification with actual E2/E4/E5/E6 and all user-required adversarial/
funding/4h/multiframe/resource/restart/backup cases. Final fresh whole-branch
review, exact-clean new Windows build/fixed qualification; old bffc never carries.
No real elapsed/trade/native/target/Ubuntu/cloud credit from these prototypes.

## Finite measurements — pre-integration disposition still pending

All three formats roundtripped every value/type of all28,872rows/65tables and
121original indices (plus prototype/supplemental indices), original SHA unchanged.
Source:47,874,048bytes. B:28,901,376bytes/build3.392s/read0.869s/82.9MBpeak/
warm-SQLite checkpoint0.127s. C:22,900,736bytes/build4.003s/read1.322s/82.8MB/
warm-SQLite0.139s. D:18,685,952bytes/build3.861s/read1.652s/83.1MB/warm-SQLite0.141s.
Original B/C/D results used a misleading `cold_current_checkpoint_decode_seconds`
key: Python decoded cache was empty, but SQLite/OS had just read all rows. Those
immutable original results remain retained with this correction. Guard-corrected
D-v2 uses the explicit warm-SQLite label and measures0.140s.
All are independently bounded owned local processes; bulk storage/codec timings,
NOT actual owner write/protection/full financial recovery or native acceptance.

Even D's whole-sample linear estimate plus the actually measured3,622,328,474byte
public archive is17,076,213,914bytes(15.903GiB), leaving103,655,270bytes before
the16GiB bound. This is not actual30day generation, and does not yet include
growing closed trades/broker history, additional timeframe cache or failure tails.
The archive permits up to8GiB retained total (7GiBnormal+1GiBprotective). That is a
stress bound, not a guaranteed simultaneous entitlement with every other maximum.
Do not infer architectural impossibility by summing independently permitted caps.
A coupled whole-backup-budget admission rule might preserve the existing caps,
but would require concrete contract review, retained protection/emergency growth
and evidence that required cadence/retention remain available; it is not selected.

RAM-only attribution (source and measured prototype files unchanged) removes65
experiment-only ordinal UNIQUE indices:18,685,952 ->17,784,832usedbytes. With a
deliberately generous extra ordinal-column credit, linear journal+measured archive
is15,668,982,298bytes(~14.59GiB). This supports only a storage hypothesis: the
whole-product fit, mature history and real backup overhead remain unproven.

An actual original E2/E4/E5/E6 sparse corpus completed90closed trades plus one
protected head, then128controlled seconds/154operations with256cached4h bars.
Correctly drained owned job exited0 in225s; a prior controller deadlocked on its
stdout pipe and exited124, retained as a failed job. This corpus uses controlled
source/clock/native policy, not the selected human policy or real elapsed credit.
Paired D files grew24,084,480 ->24,809,472bytes after those154operations. That
mature-state increment is materially less favorable than the short corpus; it
still contains experiment ordinal overhead and is not actual30day generation.
Fresh original E6 readonly current-facts recovery measured1.661s (fresh instance/
connection; OS cache uncontrolled), not complete owner/E5/history recovery.

Independent E6/E7 technical review finds byte-data versus existing canonical
membership separation consistent in principle, but roundtrip cannot qualify
production guards, selectors, pagination, transactions or restored permissions.
Its recommendation is INSUFFICIENT_EVIDENCE / NO_PRODUCTION_INTEGRATION, not
impossibility and not an E7 authority signature. Its concrete prototype aggregate
allocation finding was fixed RED->GREEN before D-v2. Full actual volume, mature
multiframe/funding/failure/backup/resource/native gates remain NOT_RUN.

Final paired RAM attribution removes the same65experiment-only ordinal UNIQUE
indices from each clone. Used pages grow23,678,976 ->24,379,392bytes, or700,416
bytes/154operations. Even granting9,234bytes extra ordinal-column savings, a
fixed90closed-state linear increment alone plus measured archive is
17,582,409,596bytes, above17,179,869,184(16GiB). Initial/static state, additional
timeframes, later closed-trade growth and backup overhead are omitted favorably.
This is concrete failure of the current candidate's finite feasibility gate,
not actual30day PASS or proof all lossless layouts are impossible. Do not start
P1/P2, enlarge limits or remove necessary history. A possible alternative is
sharing immutable broker/runtime historical subtrees across checkpoints and
effects through exact byte recipes. That requires a separate bounded format
comparison and original contract mapping before integration; it is unmeasured,
not an asserted solution or an implicit change to E4 state/Canonical Contract.

Independent approved-checkpoint cache remediation retains at most two opaque
predecessors from the same successful decode in the existing4row/64MiB cache.
Each carries its own hash/revision/chain bounds, passes journal JSON validation
and uses actual SQL metadata under the same unchanged epoch; optional invalid
history is skipped without becoming a new current-facts gate. Standalone readers
still fully traverse original chains.335storage regressions PASS. A fresh E6
readonly instance/connection over the same90closed snapshot measures0.993s after
the fix versus the retained1.661s diagnostic; OS cache uncontrolled, no full-owner/
history/financial/native/protection-latency qualification is inferred.
