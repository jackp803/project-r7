# Trading feedback implementation

## Historical read foundation

`storage.trading_feedback.open_trading_feedback_reader(canonical_path,
dispatch_path, namespace=...)` opens existing local stores using live-WAL
`mode=ro` and `query_only`. Missing files, schema/namespace drift, malformed
retained bytes, mismatched immutable strategy/plan/claimed request or a changed
capture are typed unavailable. It never initializes a replacement, applies a
migration on disk, attaches a process, refreshes permission or calls a provider.
Recognized DDL is modeled in memory only.

Each `snapshot(run_id, trade_plan_id)` validates both schemas and namespaces in
the actual read transactions. Same-file stores share one transaction. Separate
stores capture and recheck SQLite data versions; a concurrent owner append
refuses the mixed capture. Existing E6 recovery/reference validation runs on
the real read-only connection, followed by retained canonical byte/hash checks.
There is no second PnL, funding or lifecycle engine.

The canonical ApprovedTradePlan has strategy ID/version but no content-hash
field. The reader binds the actual immutable E6 strategy version and original
dispatch binding. It uses the durable preparation's `source_plan_hash` for the
plan; the composite E4 `authority_hash` is a different commitment. No current
financial permission is required to read authentic historical data.

Read limits are 2 MiB per SQLite value/row, 10,000 transferred rows, 16 MiB
transferred values and five seconds per capture, with finite SQL busy/progress
budgets. Exceeding a budget refuses the capture rather than truncating its
financial graph. These are reporting budgets, not a runtime capacity result or
a hard OS resource cap.

The frozen snapshot contains private retained owner binding data for an internal
allowlisted formatter. It must not be serialized directly to an HTTP/cloud
response. Its observed process generation is a private coherence fence, not an
original financial-result producer or renewed runtime authority. ACK, pending
orders and open/partial positions do not become closed performance.

## Remaining work and evidence scope

The additive sanitized public summary schema/constructor and publication
dispatch are still pending. Existing research/Paper v0.2 LIVE placeholders stay
unchanged. The genuine full fake-provider close/funding/TradeResult fixture
remains dependent on the unfinished H16 owner integration. An actual Paper
closure may test a clearly labeled consumer formatter; it cannot substitute for
that dispatch-owner lifecycle or real LIVE history.

Source checks cover real owner-created dispatch ACK history, actual successor
generation and approval revocation, query-only/no-writer reads, missing/unknown
stores, exact-schema corruption, and an actual append during a split-store
capture. Isolated corruption fixtures restore each original row and exact DDL;
they do not manufacture CLOSED or TradeResult rows. This foundation alone is
not K05 acceptance, native qualification, real cloud commissioning or LIVE
authorization.
