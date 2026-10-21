# E6 published prefix and complete-audit component

Approved capacity subplan C. Migration0026 adds a separate immutable new-run
prefix marker, exact published-prefix chain and covering unfinished-operation
index. New codec-only0025 runs are not silently upgraded; actual0025 compatibility
test preserves their full reader without inventing a prefix. New marked runs
require their original root and contiguous exact published sequence.

Initial root binds original binding/state/profile and original run/selection
clocks. Published steps bind prior prefix, exact request/state/outcome/effect hashes,
original prepare/complete/publication clocks. Publication receipt and prefix commit
or roll back together. PREPARED/APPLIED do not advance the published prefix; retries
validate the original prefix. UPDATE/DELETE/REPLACE and missing predecessor/source
facts refuse. These facts alone are not an audit lease or financial permission.

Explicit audit_full retains complete operation validation in one read snapshot,
streams operation IDs instead of loading the whole inventory, validates all
published-prefix facts and complete per-run checkpoint/effect/publication counts,
and compares the indexed unfinished tail with the complete pending set. An old
unfinished intent cannot hide behind an asserted tip; a missing marked root never
silently falls back. Current validly encoded orphan checkpoint/publication and
rewritten original clocks reproduced genuine failures and now refuse.

Initial clock-test editing error is retained, followed by a stable RED without
fixture errors; it is not counted as the defect reproduction.51focused,270storage
and33encoded-funding/report checks PASS, overlapping scopes,0fail/error/skip in
final runs. All evidence is source/controlled scope, not native/real elapsed credit.

Existing recover still performs the complete audit. Bounded current management,
private process-owned audit eligibility, invalidation, background batches and
entry/healthy gates remain subplan D. Ordinary composition still defaults to
legacy storage; no new native qualification or real observation. Continue D/E,
whole-product capacity, original remaining product gates and external acceptance.
