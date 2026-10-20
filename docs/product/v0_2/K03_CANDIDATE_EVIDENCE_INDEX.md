# Candidate evidence index

This additive application artifact implements the original K03 requirement. It
contains historical evidence references and never grants CANDIDATE, PAPER, LIVE,
workflow, account or capital authority. Actual E6 validation remains authoritative.
The existing feedback JSON/schema, empty artifact_links and exact two-file
feedback bundle remain unchanged.

The actual ResearchService can build an index only from its completed candidate
report, frozen inputs, independently evaluated sealed result and original E6
product assessment. The builder verifies strategy/content/runtime, current source,
dataset/split/policies and the original development/sealed/validation/product
evidence chain. Evidence payload hashes are calculated by the readonly E6 getter;
raw payloads, metrics, trades, provider/account fields and local paths are omitted.
An incomplete or noncandidate diagnostic cannot publish a candidate index.

The owner reserves an idempotent CHAT_OBSERVATION for the exact index hash before
returning its bytes or enqueueing publication. This is distinct from the existing
feedback observation. No sealed evaluation is repeated and existing observations
are not rewritten. An enqueue failure conservatively leaves disclosure recorded.

Each result has exactly three files:

- candidate_manifest.json: closed subject/source and index commitment;
- evidence_index.json: r7-candidate-evidence-index-v0.2 with the original run,
  strategy, input, source, dataset, split/policy commitments and four typed E6 refs;
- report.html: the deterministic escaped rendering of that index.

The immutable logical path is
`candidates/<strategy_id>/<strategy_version>/<index_sha256_without_prefix>/`.
The content-addressed child refines the original per-version candidates directory
so separate runs cannot overwrite each other's evidence. Readers must retain the
complete child path. The existing transport adds its own manifest.json separately.

Normal report scheduling queues this separate index for actual completed
candidates alongside unchanged feedback. Explicit local owner operation is:

```powershell
.\R7.exe queue-candidate-index --config 'C:\R7資料\設定.json' --run-id '<actual run ID>'
```

An index-only refusal is recorded per job in the existing bounded scheduler
refusals. It does not acknowledge or publish the refused index, block ordinary
feedback for other jobs or pin report pagination. Publication acknowledgments are
read and updated in one serialized writer transaction.

The command reads existing owner stores; it accepts no caller index, evidence,
decision, financial payload or PASS. FIXTURE is an explicit test namespace option,
separate from the default LOCAL_RESEARCH namespace. Existing research-owner locks
apply. This does not configure cloud access or start Paper.

The new application migration0010 adds a narrow immutable outbox in the same
research.sqlite. A run has one immutable operation and exact bundle commitment.
Content update/delete/replacement guards retain history. Pending publication is
bounded to1000items/16MiB for this outbox, with1..100items per flush. Existing
outbox limits are unchanged; cloud-publish-outbox shares its requested total batch
limit across intake, feedback, candidate indexes and Paper reports.

LOCAL_STAGED means a local copied bundle, never remote completion. A wrong
operation/hash/status receipt cannot acknowledge publication; interruption is
retryable with the same immutable bytes. CLOUD_ACKNOWLEDGED requires the existing
transport's verified receipt. CONFLICT is retained and acknowledgments do not
regress. The copy bridge validates all three files and regenerates exact HTML
before staging/upload; existing JSON privacy inspection remains active.

Upgrade preflight recognizes exact legacy journal/trial compositions and the new
finite research compositions. It still refuses arbitrary extra schema and creates
only inhibited restore candidates. No new database role, financial registry or
untyped backup folder is introduced.

Source/fake-copy tests establish local mechanics only. Real cloud/Chat retrieval,
Ubuntu, old-target commissioning, actual financial-policy selection and elapsed
forward evidence remain separate. Adding this source feature does not transfer
the qualified3ae6460 Windows receipt to a later executable.
