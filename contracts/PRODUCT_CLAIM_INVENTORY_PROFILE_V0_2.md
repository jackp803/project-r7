# Product historical claim inventory — v0.2

Additive E6 read/audit profile for the authorized v0.2 product implementation.
Canonical financial/lifecycle authority, original claims and source observations
remain unchanged. A scan is data, never provider mutation or financial permission.

Existing immutable provider/account claims are read in keyset pages of100 rows,
ordered by `(prepared_at, run_id, operation_id)`. Ties across runs are retained.
The exact provider/account and ENTRY/PROTECTION_STOP role delimit each scan.
Unknown initial-stop position binding still blocks the account; an unclaimed
intent is not a dispatched claim. Every request/observation hash is validated.
No total1000-row cutoff, archival deletion, unresolved-claim omission or inferred
settlement is permitted. An additive index supports the scoped keyset order.

Effect guards consume streams. Existing tuple methods remain compatibility
materializations; they are not memory-capacity promises. The protection consumer
retains only historical identity intersections with the bounded current native
inventory. Its complete ordered audit hashes canonical UTF8 claim material with
an8-byte big-endian length prefix per row; a canonical envelope binds profile
`product-account-claim-stream-v0.2`, count and ordered material SHA256. This does
not change historical receipts or rewrite their original audit hashes.

The issuing connection's SQLite `data_version` and `total_changes` fence other
connection commits and same-connection writes. Mutation during/after the scan
invalidates interpretation. No transaction is held over caller/owner iteration
or HTTP. The protection outbox checks the original generation again inside its
actual E6 BEGIN IMMEDIATE transaction, preventing a new claim between the last
check and commit. This conservative fence also rejects unrelated DB writes;
it is not distributed or multi-host fencing.

ENTRY admission still checks actual canonical rejection or restart-authoritative
CLOSED/TradeResult/terminal-order facts for every prior claim. Initial-stop
submission still rejects any earlier ambiguous claim. Native missing inventory
does not erase local history or adopt an unknown stop. Actual E6/E7/E5/E4
freshness, lease, policy, account, source and financial limits remain required.
Long scans that outlive current authority fail closed; this change establishes
mechanics, not a production latency/capacity PASS. Native/supervisor/provider
commissioning and whole-product performance evidence remain separate.
