# E6 whole-product compact fact layout — concrete additional review

Master: CODEX-R7-PRODUCTIZATION-MASTER-20261002.
Branch: codex/r7-productization-master-20261002.
Status: CONDITIONALLY_APPROVED_ADDITIONAL_BOUNDED_SCOPE; original checkpoint/recovery approval retained.

Human decision2026-10-24: detailed design, finite measured prototypes and E6/E7
contract review FIRST. If feasibility within unchanged limits is demonstrated,
continuous implementation is authorized without per-step confirmation. No scope
expansion if finite prototype does not support feasibility. See
e6-compact-fact-layout-operator-decision.json for all conditions. The proposal
below is retained as the reviewed record, not a new approval request.

## New measured conflict

The approved checkpoint/delta and management/history separation are implemented
as source components. This is not a reopening of that approval or the four PM
Paper mappings. New whole-product measurements show a different remaining limit.

Source99df382b68569b5b79ad2d04fa76a8faecb213e9, actual LOCAL E2/E4/E5/E6
owners with controlled source/clock/native-measurement boundary and existing
test policy;256closed4h bars and one protected position. In3600controlled
seconds, actual4320additional operations grew the SQLite allocation by46,862,336
bytes to47,874,048. All3600management durations were below1s: maximum0.187s,
p950.123s, median0.060s. Wall264.436s, CPU248.578s, peak150.4MB including
snapshot hashing. Zero public/private requests, no real elapsed/native credit.

At the declared1s management/5s acquisition cadence, the measured per-operation
growth projects to33,740,881,920bytes for3,110,400operations/30days. With the
previous actually generated public archive3,622,328,474bytes, the sum is about
37.36GB, before other product data. Existing whole-product backup bound is
17,179,869,184bytes(16GiB). This is a sample projection, not an actual30day run
or a fabricated boundary refusal. It is sufficient to withhold capacity PASS.

Measured growing TEXT across the4320operations:

| Immutable inventory | Measured growing bytes | Projected30day bytes |
| --- | ---: | ---: |
| E6 effects (all TEXT) | 9,618,749 | 6,925,499,280 |
| Lifecycle execution bindings (all TEXT) | 5,944,742 | 4,280,214,240 |
| Lifecycle projections (all TEXT) | 5,246,912 | 3,777,776,640 |
| Encoded checkpoints (all TEXT) | 5,155,113 | 3,711,681,360 |

These figures exclude other rows, indices and page overhead. A read-only byte
experiment compressed individual effect/projection/binding JSON with zlib:
plain16,289,855bytes ->7,900,436binary bytes, or10,550,136base64bytes, before
envelopes/indexes. This is an estimate, not an implemented store or capacity PASS.
It does not establish that adding another per-row JSON compression wrapper will
fit the whole-product budget. Repeating that partial fix would be speculative.

The complete838operation cold readonly audit now takes7.109s with0writes,
47.7MBpeak and unchanged source SHA. That is useful measured improvement, but
does not establish complete30day history verification within an individual
300s owned process deadline. No audit deadline has been raised or bypassed.

Evidence: e6-whole-product-growth/result.json and growth-analysis.json. Original
consistent4321revision snapshot is retained under project artifacts only, SHA
sha256:35e7538884bd6f7f56a990b0f7b6d0f8c0aa29ae578e11853d7f537428ad23b9.

## Recommended additional scope

Approve detailed design, bounded prototypes and implementation of a versioned
compact layout for the *other* immutable E6 process and canonical facts inside
the original SQLite, alongside the already approved checkpoint codec.

1. Use compact typed internal references for repeatedly stored run/position/
   operation identities, with immutable exact string mapping. Versioned bounded
   lossless payload records may share verified source facts/deltas instead of
   duplicating complete projection/binding JSON in every outcome. Evaluate
   binary compression and metadata packing before choosing the final format.
   No claimed size result from an unimplemented layout.
2. Preserve every original logical operation, canonical payload, clock, hash,
   ID and publication/retry identity. All public E6 readers return the exact
   original canonical UTF8 bytes. Existing rows/profiles remain unchanged and
   independently readable; new layout only for explicitly selected new runs/
   fact lineages. No legacy automatic migration or historical rewrite.
3. Preserve intent, effect/checkpoint and publication transaction boundaries;
   canonical publication remains per fact with its original conflict semantics.
   New physical records and their required references commit atomically inside
   their original transaction. Partial/missing/foreign/oversized records refuse.
4. Preserve E4/E5 financial/lifecycle ownership, all risk/source/selection gates,
   funding completeness and original pending handling. No missing evidence
   becomes zero, no skipping reattestations or changing1s/5s/4h/256bar policies.
5. Design owned history work to remain bounded per process/job. If full history
   cannot fit300s, complete it through source-bound private partial segments in
   the same actual E6 owner instance, with exact continuation/source epoch and
   known append checks. No persisted/imported PASS or caller-supplied progress.
   Unknown/external/schema changes revoke all accumulated eligibility. No entry
   or healthy-forward credit until *all* original history plus actual tail pass.
   Measure and report recovery-induced blocked signals/duration; protection and
   exit continue independently. Restored/new instances earn new proof.
6. Retain complete independent old/new auditing and immutable evidence, including
   source quantities, all intermediate semantic hashes, orphan inventories and
   clocks. Backup/restore includes all physical records; restore stays inhibited.
   Preserve16GiB/4096file/300s bounds and current host reserve/isolation limits.

This extends beyond checkpoint storage into canonical fact/index layout and
owned audit continuation. It is a concrete major architecture amendment under
the human's earlier rule, not a deterministic defect to defer without diagnosis.
No such layout or continuation implementation is present or enabled yet.

## Alternatives and decision

Recommended: the compact lossless fact layout above. It addresses demonstrated
duplication and index overhead while keeping original evidence and limits.

Keeping this layout and raising backup/audit limits requires different resource
and target-machine acceptance, and violates current authority. Reducing1s
management, cache/history or canonical evidence changes the selected contract.
Deleting history, resetting counters/runs or a second active DB is excluded.
Thus there is no evidenced small within-current-layout fix to call sufficient.

Requested decision: approve this additional scope for detailed design and
implementation, or return the layout/resource contract to PM/E6. Preserve the
original approved work and all evidence either way. No ordinary long observation
until complete capacity, software, research, policy and source admission qualify.

## Acceptance before rollout

- RED before implementation: old/new exact logical bytes, all fault/transaction
  seams, original IDs and retry/conflict behavior, malicious/foreign/cyclic/
  oversized records, index/root/mapping corruption, missing/orphan records.
- Actual same-owner and successor proof, unknown writes, interrupted child,
  duplicate/out-of-order segment, expiration/cancellation/reaping and resource
  contention. Public/saved reports cannot supply permission.
- Actually generate and verify the declared whole30day-equivalent workload with
  full4h/multiframe cache, pending funding, source outage/publication delay,
  original hold/TTL/entry-limit/amendment behavior, cold recovery and complete
  backup/verify/restore at the unchanged budgets. Report workload assumptions.
- Whole-change independent review, exact-clean new native Windows build and
  complete fixed qualification; original bffc receipt never transfers.
- Real48h/30d/trades, old PC, Ubuntu and cloud commissioning stay separate.

Independent already-authorized backup/recovery, emergency quote reserve path and
remaining original product checks continue while this new decision is pending.
