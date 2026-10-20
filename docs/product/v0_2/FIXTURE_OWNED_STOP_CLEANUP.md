# Exact unused-stop cleanup after original flat

This internal FIXTURE owner profile implements the existing Master cleanup
obligation. It adds no shared CANCEL OrderRequest and no new financial formula,
provider permission or production funding adapter. It never cancels all orders.

The owner first proves the original complete E6 entry/close/position graph and
actual original native-position zero, still EXIT_REQUESTED. The original
PROTECTION_STOP claim must have an actual healthy protection publication and
one exact original native algo ID. No unknown/competing account entry, close or
protection claim may be hidden. All canonical entry and explicit-close fills
remain bound to that original position and action.

Immediately before cleanup, require separately issued current native zero,
targeted ACTIVE stop read and complete converged algo inventory. They must come
from the same actual FakeProductProvider/process, exact current metadata/account
proof, original native position and original stop. The inventory contains exactly
that one active object and agrees with the targeted read's immutable native row.
Copied/stale/foreign reads, triggered children, unknown objects, a non-flat
position or changed canonical source forbid the cancel.

An issuer-local preparation binds those exact reads and the canonical graph.
E6 commits one immutable cleanup claim on the original stop, original flat close
publication and native algo ID before the provider effect. This is a separate
local phase, not reuse of the original stop submission claim. A final actual
provider guard repeats current source/owner checks after that commit. The only
effect is the already-supported single-target cancel-algos body. A returned ACK,
lost ACK, crash or duplicate invocation never proves terminality and never permits
a second cancel POST. A committed claim without a proven terminal target stays
unresolved, with evidence retained; there is no automatic claim reset.

Recovery reads the exact original stop with its existing canonical reconcile
adapter. CANCELED with no child/fills must be positively observed; empty pending
inventory is not a terminal target read. Active/unknown/triggered states do not
finalize. Complete fresh postcancel inventory and current native zero are
separate finalization prerequisites. Reading a current zero does not rewrite the
first authoritative flat clock or previously allocated funding interval.

Claim and source audit rows reject update/delete/INSERT OR REPLACE, including
SQLite recursive_triggers OFF. New claim insertion fences the captured complete
claim-inventory generation inside BEGIN IMMEDIATE. After its own claim commits,
the final effect guard repeats the semantic owner/graph/native inventory scan
and fences that fresh generation. It does not mistake its own insert for a new
external claim or relax the rejection of unknown/competing claims.

After the semantic/SQLite scans, a separate final fence rechecks the original
issuer caches, hashes, provider/lease, exact metadata/account proof and unchanged
five-second windows. Native position freshness uses received_at; targeted stop
and inventory freshness use request_started_at. Metadata age and scheduled
changes are checked by the existing capability owner, not inferred from proof
expiry. These source fixtures use a controlled clock and do not establish a
native hard deadline.

Successor recovery uses a new admission/capability owner, provider, process
instance and journal handles. The E6 dispatch lease advances to generation two
while preserving the accepted E7 release generation; these are distinct counters.
Only the original targeted stop is read, with no old issuer objects or second
cancel. A terminal result may require E5 reinterpretation and does not by itself
restore restart-authoritative closure.

This slice does not infer CLOSED/TradeResult from cancel ACK or flatness. Actual
E5 finalization and its durable publication are a subsequent joined owner step.
Production composition is unsupported by this FIXTURE profile and fails before
credential or network access.
