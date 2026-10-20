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

## Additive public v0.3 projection

`application.cloud.trading_feedback.build_trading_feedback` accepts the actual
protected read port, run ID and trade-plan ID. It receives no trading client,
provider, caller result or PASS flag. Default `performance_opt_in=False` hides
monetary values. Opt-in copies only existing canonical gross/net PnL and total
fees, plus the exactly referenced FundingEvidence cost; it does not recalculate
PnL or add drawdown/expectancy/balances. Raw local identities are hashed, private
provider/account/credential/path fields are excluded, and `closed_at` is the
original TradeResult clock rather than an invented report-creation clock.

The strict additive contract is `contracts/trading_feedback_v0_3.schema.json`.
The JSON/HTML bundle uses deterministic self-contained escaped HTML with a CSP.
Public publication validation dispatches this exact version; existing research
and Paper v0.2 schemas and their LIVE placeholders retain their original rules.
The public document is reporting data, not importable financial evidence or a
runtime permission. Its financial authority is always NONE.

`PAPER_OWNER_SOURCE_FIXTURE` can describe an actual Paper closure only as a
consumer fixture with its registered PaperZero provenance. A fake-provider
dispatch summary is separately labeled `FAKE_PROVIDER_VERIFICATION`; an
available dispatch result requires BROKER_LEDGER funding and cannot borrow
PaperZero. Both keep actual LIVE NOT_RUN/null. Only an available protected
LOCAL_RESEARCH/ACTUAL_OWNER historical canonical result can select the
HISTORICAL_CANONICAL_RECORDS branch; this is no claim of a running runtime or
current permission. Observed process generations are not exported as original
financial-result producers.

## Remaining work and evidence scope

The genuine full fake-provider close/funding/TradeResult fixture remains
dependent on unfinished H16 owner integration. An actual Paper closure tests
the explicitly labeled consumer projection, not that dispatch-owner lifecycle
or real LIVE history. The actual protected public constructor is independently
exercised on genuine ACK/pending dispatch history and reports UNAVAILABLE/null.
The complete closed dispatch positive, native qualification and real LIVE
commissioning remain unproven; this increment does not accept K05 or H16.

Source checks cover real owner-created dispatch ACK history, actual successor
generation and approval revocation, query-only/no-writer reads, missing/unknown
stores, exact-schema corruption, and an actual append during a split-store
capture. Isolated corruption fixtures restore each original row and exact DDL;
they do not manufacture CLOSED or TradeResult rows. Privacy/schema cases cover
strict opt-in, exact available amounts, alias/unknown-field exclusion, typed
malformed provenance, immutable capture mutations, deterministic HTML/media
checks and unchanged legacy LIVE placeholders. These are source checks, not
native qualification, real cloud commissioning or LIVE authorization.
