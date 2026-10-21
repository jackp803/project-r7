# Intermediate read-only review, not final whole-branch acceptance

Existing reviewer qualification_review inspected the scoped archive decoder,
same-operation backup proof and funding diagnostics. Reviewer execution NONE;
0 Critical/1 Important. Reviewed working-file SHA256 values:

- archive44efa133fdb86909f076095433acc19116523b80d446e55b5cc11b4d63c8a8d3
- engine7fbac9095dae12b2263dcf5d5bf3b2f101da176fc2b3dce31fe36981a241bf14
- backup2af5b997b65173e2dab8aa0b324d6f837bd639d5a5ad0e766a51568f96d3ed5a

Important: Python dictionary equality accepts boolean offset false as equal to
integer0 in a COMMIT index. Full verification lacked the strict pointer check
already used during individual readback. A real FILE after a verified pack seal
has offset0, so this is a reproducible input, not an unreachable type concern.

Two added tests constructed genuine hash-chained frames/head/seals with that
invalid index. Restart and full product backup both failed to refuse (RED2/2).
Fix: validate every stored COMMIT pointer with _pointer_shape before comparing
the actual linear-scan FILE index. Final scoped archive/recovery/backup suite49
PASS,0failures/errors/skips. It preserves all original frames/schema/counters.

The reviewer considered the prior backup proof-to-final-rows and file-closure
repair resolved. No additional concrete Critical/Important finding was reported
for the scoped diagnostic/reason methods. Final whole-change/native acceptance
remains required; this intermediate opinion cannot substitute for it.
