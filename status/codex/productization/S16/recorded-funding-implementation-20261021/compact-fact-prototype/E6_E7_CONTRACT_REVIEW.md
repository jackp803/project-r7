# Readonly technical pre-integration review, 2026-10-24

Reviewer: existing delegated `/root/compact_gate_review`, separate from root
implementer. Readonly source/design/results review; no code changes, commands,
provider calls or external messages. This is an independent technical assessment,
not an E6/E7 human authority signature, accepted executable or financial approval.

Original source base:fd10db6; design/operator decision in this change. Review of
the existing codec, journal, published prefixes, canonical writer and archive
contracts finds the proposed separation consistent in principle: encoded byte
objects are DATA ONLY; existing E5/E6 validation and atomic canonical membership
remain the sole lifecycle/financial authorities. No financial/canonical contract
change is established or implicitly authorized by the prototype.

Findings and dispositions:

1. **Feasibility unproven.** Short-sample D+measured archive has almost no margin;
   closed-trade growth, multiframe cache, failure tails and backup overhead are
   missing. Roundtrip does not establish product selector/order/pagination,
   immutability, FK/no-REPLACE/uniqueness or full restore. Production gate stays
   closed. Subsequent root-produced90closed paired evidence remains a finite
   measurement, with its explicit capacity failure in the disposition.
2. **Timing label corrected.** Empty Python cache after exhaustive clone readback
   is warmed SQLite/OS, not cold restart or full owner recovery. Original immutable
   result keys retained with correction; D-v2 emits the precise label. Separate
   fresh E6 current-facts probe labels OS cache uncontrolled and excludes full
   history/E5/native recovery.
3. **Aggregate template allocation defect fixed.** Prototype mode3 previously
   joined referenced child/literal bytes before enforcing the parent aggregate
   limit. RED test reproduced; fix checks child declared sizes, incremental
   totals and exact final size before joining, and prechecks byte-delta lengths.
   SQL CASE excludes oversized payload fetches. Final7prototype tests PASS and
   corrected D-v2 all-cell readback PASS. No product codec was integrated.
4. **Independent caps clarification.** Reviewer rejected treating permitted8GiB
   archive maximum as a guaranteed simultaneous footprint. The alternative of
   coupling admission to total backup capacity might preserve maxima, but needs
   concrete contract review and demonstrated protection/emergency/cadence/retention
   preservation. It was not selected. Optimistic14.59GiB short-sample arithmetic
   supports a hypothesis, not a whole-product pass or architectural impossibility.

The reviewer also identified repeated tip/base ancestry decoding in the original
approved checkpoint cache: `recover_current` decodes the tip, then published-tip
`operation()` requests its base, with another base for an APPLIED tail. Suggested
bounded remediation retains the last two opaque predecessor records from the
same successful full decode, using individual hashes/revisions/chain bounds,
journal JSON checks, actual row metadata, unchanged epoch invalidation and the
existing4row/64MiB eviction limits. Root additionally ensured invalid OPTIONAL
history does not add a new current-read gate. Standalone readers keep complete
validation. Root implemented/tested/measured separately; this reviewer did not
issue a final whole-branch review or native approval for those later edits.

Review conclusion: **INSUFFICIENT_EVIDENCE / NO_PRODUCTION_INTEGRATION** for the
current compact candidate. Full actual volume and final whole-branch review are
still separate mandatory gates. No external PASS/progress import is acceptable.
