# E6 ordinary Paper journal capacity amendment — review required

Task: CODEX-R7-PRODUCTIZATION-MASTER-20261002. Same implementation branch.
Status: HUMAN_SCOPE_APPROVED_DETAIL_DESIGN_AND_IMPLEMENTATION_AUTHORIZED.
Decision: the human selected "核准草案範圍，完成詳細設計並實作（建議）" in the
existing approval question. See e6-journal-capacity-operator-decision.json. This
authorizes detailed design and implementation within this written scope; it is
not implementation completion or native/financial/observation acceptance.
No change to selected financial policies,
funding completeness, E4/E5/E6 authority, canonical lifecycle or permission.

## Demonstrated problem

The public capture archive is only one part of product capacity. Its controlled
30day workload actually produced and verified1,037,010captures,3,622,328,474bytes
and2,176files. This does not qualify the Paper journal or whole product.

A separate controlled source integration used actual LOCAL E2/E4/E5/E6 owners,
an actual4h strategy and200closed4h bars (below the human-selected256bar ceiling).
Existing source fixtures control the native qualification boundary; this is NOT
native eligibility, live public data or genuine elapsed observation.

After100controlled seconds there were121actual owner operations/122immutable
checkpoints. Retained checkpoint TEXT alone was9,383,612bytes; each current state
was about77,593bytes. The measured last tick rose from0.268s at13operations to
0.866s at61 and1.657s at121. These are actual local durations, not a fitted
long-run benchmark; resource interference can affect individual samples.

At the declared1s management plus5s market cadence,30days is3,110,400operations.
The measured sample-mean checkpoint TEXT projection is241,213,113,758bytes,
excluding indexes, requests, effects, canonical position graphs and future
growth. This projection holds the populated200bar state constant; it is NOT a
claim that30days were run or that the cache is already200bars at initial start.
It demonstrates a permitted steady-state workload well beyond the existing
16GiB whole-product backup bound. Reducing the cache would change the selected
protocol and still would not resolve historical recovery scaling.

Two concrete implementation facts explain this:

- storage.paper_process.complete writes the entire immutable state_json at each
  operation. It repeatedly includes retained candle history and earlier facts.
- storage.paper_process.recover enumerates every historical operation and
  validates its request/base checkpoint/effect/publication on each recovery read.
  The owner and scheduler call this repeatedly, so cost grows with run history.

Migration0011 explicitly forbids UPDATE/DELETE of Paper operations, effects,
checkpoints, publications and generations. Deleting history, resetting a run,
weakening checks, raising limits or adding a second journal is not a remedy.

## Recommended bounded architecture amendment

Approve a versioned E6 physical storage and recovery profile inside the existing
canonical local SQLite store. New-profile runs only; existing rows stay intact
and readable. This must retain every operation and its exact logical state and
publication identity. No rewrite of historical financial evidence.

1. Add immutable, content-addressed keyframes and bounded state deltas. The
   existing E6 transaction commits the operation, physical state records,
   semantic full-state hash, exact effects and checkpoint binding atomically.
   No external active SQLite, sidecar authority or extra database. A bounded
   keyframe interval (initial proposal128) limits decoding work and memory.
   Versioned codec validates base revision/hash, exact reconstructed state and
   physical payload integrity. Corrupt, missing, cyclic, oversized, wrong-run or
   unsupported chains refuse. Existing E6 APIs continue returning the same
   canonical logical broker/runtime state and financial hashes.
2. Define an E6-owned immutable prefix/sequence proof and indexed pending-work
   read so normal management does not repeatedly decode every published
   operation. Specify what is validated at write, each hot read, successor
   recovery and full audit. Do not silently remove the current historical
   integrity promise: preserve independent full verification and explicitly
   fail admission when the required proof cannot be established.
3. Recover actual current exposure, original policy and pending effects before
   background historical auditing can delay protection. New entries/healthy
   eligibility stay inhibited until the required full/current proofs pass.
   This ordering and proof boundary require E6/PM design acceptance before code.
4. Keep public capture accounting and financial allocation unchanged. No missing
   funding becomes zero. Pending data and reporting use original flat/fill
   facts. No order, risk permission or lifecycle change arises from compression.

This is a new physical persistence/recovery design, beyond the approved public
capture-pack implementation. It is submitted because the human's conditional
approval explicitly reserves major architecture changes for additional review.
It is unrelated to the four ordinary Paper mappings already accepted on main.

## Acceptance required after architecture acceptance

- Tests first: exact old/new logical-state equivalence, every crash seam,
  original fill/effect IDs, publication prefix replay, stale writer, partial
  codec record, immutable history, and pending original-policy recovery.
- A malicious/missing/corrupt old or new fact must not inherit a cached proof.
  Independent full audit, backup and restore must validate original logical
  facts; restored operations remain inhibited.
- Measure actual disk/CPU/RSS and management deadline latency as the journal
  grows, including actual4h/multiframe cache, pending funding, source outage,
  publication delay, restart and resource contention. No time/trade credit.
- Actual30day equivalent whole-product workload must fit existing declared
  storage/backup limits, with explicit worst-case refusal and protection budget.
  Public raw archive PASS alone is insufficient.
- Preserve all existing tests and fixed PQR observations. New exact Windows
  package/full qualification and owning admission are required. Old bffc
  receipt, Windows results and accelerated time do not qualify a changed build,
  the original target PC, Ubuntu or real elapsed observation.

## Decisions requested

Either approve this bounded E6 amendment for a detailed codec/proof design and
implementation with these constraints, or return it to PM/E6 for a different
design. Until that decision, preserve current immutable journal semantics and
keep long-running ordinary Paper observation NOT_STARTED. Continue independent
source/archive/backup, report/browser and other authorized local work.

Measurements are retained in journal-growth-result.json beside this document.
