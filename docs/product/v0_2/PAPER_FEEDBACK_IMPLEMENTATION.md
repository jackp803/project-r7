# PAPER feedback increment

This additive S14 exporter uses `r7-paper-feedback-v0.2`. The existing research
feedback contract and renderer remain unchanged. Publication dispatch uses the
document's schema version, preserving an existing research strategy named `paper`.

## Actual owner and evidence

`build_paper_feedback` accepts an already attached actual `PaperRuntime` using
its selected promotion policy. It verifies the current process generation,
original owner instance, exact source/configuration/policy binding and unchanged
checkpoint around the actual forward assessment. It reads the existing published
E5 financial graph. It never constructs a runtime, claims a process lease, changes
a registry stage or grants financial authority.

The report separates actual and simulated elapsed time. An accelerated fixture
has zero actual elapsed time and cannot supply real forward qualification. A
report records the assessment decision and reasons; exporting it does not make
that assessment pass. LIVE remains `NOT_RUN` with unavailable performance.

Monetary disclosure defaults to `OPT_OUT`. Explicit local opt-in publishes the
available canonical PAPER metrics as exact decimal strings; absent closed trades
always leave performance null. The report declares the existing isolated account,
fill-price slippage and explicitly registered zero funding conventions. These
labels describe the current PAPER model and do not assert provider realism.

The allowlisted JSON and self-contained Traditional Chinese HTML exclude private
provider IDs, credentials, balances and local paths. The public producer identity
commits the original process generation and a hash of its instance ID. The
versioned schema is structural validation; it supplies no execution authority.

## Durable publication

`PaperFeedbackOutbox` uses the existing `PaperProcessJournal` connection. Normal
additive migration `0017_paper_feedback_outbox.sql` adds its table to that store;
no additional database is introduced. A bounded transaction atomically records
the report, bundle and exact run/checkpoint/producer references after verifying
that the captured current owner and checkpoint remain unchanged.

The bundle is content addressed under
`reports/feedback/paper/<strategy>/<version>/<report-hash>/`. Identical bytes are
idempotent; a conflicting identity is refused. Publication revalidates immutable
report bytes and historical E6 producer lineage. A legitimate new current owner
does not relabel or invalidate an already committed historical report.

Report computation and transport calls occur outside write transactions. Pending
publication is limited to 1,000 items and 16 MiB; batches are at most 100 items.
Capacity failure preserves earlier reports and canonical runtime evidence.
Crash after upload but before acknowledgment remains retryable with the same
content identity. `LOCAL_STAGED` is distinct from `CLOUD_ACKNOWLEDGED`; the latter
requires the existing transport's exact operation and artifact-hash receipt.

The existing `RcloneCloudTransport` validates both JSON and its exact renderer
output before any stage write, then uses the existing copy-only byte-verification
bridge. Controlled local fake transport tests are offline mechanics evidence.
They do not prove real cloud delivery.

## Integration boundary

`cloud-publish-outbox` publishes existing historical PAPER reports after intake
receipts and research feedback. All three share one total requested batch limit
and the existing cloud host scope, including protection from stopped-owner
backup races. The PAPER journal opens only when the configured canonical E6
database already exists and a positive batch budget remains. SQLite opens in
existing-only `mode=rw`, so a database disappearing after the presence check
cannot be recreated as an empty success. Default owner initialization retains
its existing creating behavior. This publication path introduces no
additional database and never attaches a runtime, renews a process generation,
computes a report or changes a checkpoint. `COMPLETE` describes that bounded
batch; it does not assert that every queue is empty. Controlled local fake
transport verification remains distinct from real cloud delivery.

The ordinary continuous runtime/worker composition remains S12 work. That owner
must enqueue from an already attached runtime and schedule bounded independent
publication; API reads must not attach a runtime merely to produce a report.
This increment does not start a runtime or connect a cloud account.

Real cloud commissioning, real forward observation, provider verification and
Ubuntu native qualification remain separately required and `NOT_RUN` until
their actual evidence is retained. A Windows source test result cannot satisfy
those acceptance requirements.
