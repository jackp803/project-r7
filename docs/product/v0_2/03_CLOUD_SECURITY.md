# R7 v0.2 cloud artifact and durability protocol

Authority: `00_EXECUTION_BASELINE.md`. Cloud files are data, not code or approval.

## CLOUD-01 Namespaces and one writer per role

Logical drive root:
```
inbox/strategies/<submission_id>/
datasets/<dataset_id>/<revision>/
capabilities/<instance_id>/<snapshot_hash>/
research/runs/<run_id>/<artifact_generation>/
candidates/<strategy_id>/<version>/<assessment_id>/
paper/<strategy_id>/<version>/<paper_run_id>/<generation>/
live/<deployment_id>/<report_generation>/
reports/feedback/<strategy_id>/<version>/<generation>/
receipts/<instance_id>/<submission_id>/<receipt_generation>/
```

Chat/author writes submissions. R7 writes receipts/results/capabilities. Neither rewrites the other's immutable objects. Archiving is an optional explicit housekeeping action after durable receipt acknowledgment; default intake never deletes or moves the author's source files. A shared drive mount is not a distributed job lock.

The local database, checkpoints containing sensitive execution data, OAuth configuration, provider secrets and raw private-provider responses are outside this root. A missing mount must not cause R7 to initialize a new empty directory at the old mountpoint and mistake it for the correct cloud. Bind a locally configured root marker/identity and detect loss or mismatch.

## CLOUD-02 Submission package v0.2

Required UTF-8 files: `strategy.json`, `manifest.json`; optional author prose in `research_notes.md` is non-executable. Write payload first, manifest last. Consumer readiness still requires all verified bytes.

Manifest schema `r7-strategy-package-v0.2` has strict required fields:
- package_schema_version, submission_id, created_at (UTC), created_by (display metadata only).
- strategy_id, strategy_version, strategy_content_hash; exact match to parsed E2 definition.
- required_runtime_profile and capability_snapshot_hash; exact compatible implementation required.
- payloads: ordered array of role, relative_path, media_type, byte_length, sha256. Required one strategy_definition role; declared notes are optional. No duplicate roles or paths.
- requested_dataset_profile, requested_validation_profile, requested_robustness_profile: references to local configured policies, not embedded authority.
- intent_class: EVERGREEN_STRATEGY or TACTICAL_STRATEGY.
- validity: explicit `from`/`until` UTC strings or null; TACTICAL requires a finite valid interval.
- research_hypothesis: bounded plain text, never instructions for a subprocess.

Submission IDs and artifact path components must match `[A-Za-z0-9][A-Za-z0-9._-]{0,95}` and cannot be `.` or `..`. Treat display names separately. Reject Windows reserved device names, drive prefixes, colons, backslashes, Unicode normalization aliases, path case-fold collisions and NUL/control characters. Additional properties are rejected unless a versioned extension namespace is explicitly supported.

Keep the v0.1 manifest parser as a separate strict adapter. Its missing capability/validity fields cannot infer a new runtime, financial policy or tactical approval. Preserve old hashes/receipts and expose PROFILE_UPGRADE_REQUIRED when required semantics cannot be represented.

## CLOUD-03 Identity and integrity

Two independent hashes:
1. payload byte SHA-256 verifies transport bytes, including exact UTF-8/newline encoding.
2. E2 strategy_content_hash verifies canonical strategy semantics under its profile.

Manifest identity is SHA-256 of validated canonical manifest JSON. A hash is not a signature or evidence of trusted authorship. Locally configured root/account access and author policy are the trust boundary; manifests cannot add trusted authors. External files cannot weaken resource/policy limits or change the deployment configuration.

Stage each complete candidate package into a private local directory. Open paths without following symlinks/reparse escapes, bound read length, hash the bytes actually read, and parse precisely those bytes. Check all payload lengths/hashes and envelope/E2 identity before registering. Do not validate a file and later reopen a changed cloud file for execution. Seal the local staged snapshot with its manifest/payload hashes.

Missing/truncated payload or differing hash prior to successful intake -> INCOMPLETE_SYNC. Retry with bounded backoff (initial 5s, max300s, no busy loop). After24 hours of unchanged incompleteness, surface SYNC_STALLED requiring user attention; never classify this as a statistical strategy failure. A previously accepted immutable submission changing its manifest/bytes -> CONFLICT, quarantined, with no rerun or overwrite. Incomplete observed manifests may evolve before successful claim, with observation history retained.

Malformed JSON, forbidden paths/fields or invalid package shape -> BLOCKED immediately. No raw rejected payload containing suspected secrets goes into logs, receipt or the public repository.

## CLOUD-04 Discovery is at least once

Use periodic scans (default30s, configurable bounded interval) plus optional filesystem notifications as hints. Correctness cannot depend on receiving every notification. A mount outage may be retried; absence of a file is never permission to delete local evidence.

Local durable submission key: `(instance_id, submission_id)`; bind accepted_manifest_hash on successful validation. Claim under a SQLite transaction. Record owner_id, lease_generation, lease_deadline, current_stage, stage_input_hash and optimistic revision. A stale worker cannot commit after its lease generation changes. Do not use cloud rename as an exclusive claim.

Crash recovery reconciles claim/stage/output identities before retry. Pure deterministic computations may be replayed; externally visible registrations and receipts are idempotent. The requirement is no duplicate logical effect, not a false promise that a CPU instruction can never run twice.

## CLOUD-05 Intake and E6 partial failure

Call actual E2 parser and the real E6 service. Intake can be retried after a crash between local ledger and E6 writes. Reconcile using exact strategy identity/content hash and the intake operation key; reuse the existing E6 record rather than creating an alternate registry. Add bounded E6 atomic intake/idempotent receipt support if needed. Do not mark job COMPLETE before the canonical effect is durably verified.

P1 registration stays DRAFT. Later real compatibility execution generates trusted evidence inside the application process; package or API caller cannot submit `verification_kind=LOCAL_EXECUTION` to self-certify. Existing E6 public methods must be behind the trusted local execution service; expose no HTTP endpoint that accepts arbitrary promotion-evidence status.

## CLOUD-06 Durable outbox

Commit stage-result reference and publication outbox item atomically in the owning local store. Publisher retries independently of research/trading. Destination artifact identity is deterministic from run/generation/content hash. Same ID+same bytes -> idempotent success; different bytes -> conflict, never overwrite.

Upload staged result payloads then manifest. Remote completion means actual transport acknowledged all required artifacts and readback/listing or byte verification met the transport profile. A local write into a sync directory means LOCAL_STAGED, not necessarily CLOUD_ACKNOWLEDGED. UI shows these separately. Report references use safe logical paths, not arbitrary URLs or local secret paths.

Cloud outage does not interrupt existing protective management. Stop admitting research if the bounded outbox/disk budget would be exceeded; never discard canonical trading events. Drive availability cannot grant/withdraw E5 trading authority, but local storage inability can fail closed under runtime policy.

## CLOUD-07 Dataset format and identity

Large tables: Parquet with pinned schema/serialization version; manifests/summaries: JSON; human report: self-contained sanitized HTML. No remote JavaScript in reports. Export financial values as exact decimal strings or declared Decimal columns, not silently downgraded float.

Define both artifact-byte hashes and a logical dataset hash over the ordered canonical E1 interchange records. A Parquet library re-encoding must not silently become the same byte artifact; an equivalent logical dataset may have a different container-byte hash. Record both. Dataset identity also binds normalization/timezone/finality/availability/cost-source versions. Bound row groups and reads; never load the entire cloud tree as a single object.

## CLOUD-08 Feedback and privacy

Default Chat-facing report includes strategy/version/hash, source/runtime versions, dataset and split IDs, sample counts, train/OOS/robustness decisions, reason codes, PAPER observation duration, available LIVE performance summary, confidence/uncertainty, artifact links and timestamps. Missing stages remain NOT_RUN and missing metrics null.

Exclude: credentials, OAuth tokens, signatures, raw exchange responses, provider account/order/fill identifiers, machine usernames/full local paths, private IP inventories and exact account balances. Use sanitized local reference IDs. Actual strategy performance/monetary result publication is a local opt-in report policy because it is personal financial data; secret exclusion remains unconditional. The local audit store may retain necessary provider identifiers under protected access; never destroy reconciliation evidence merely to sanitize the cloud.

Chat feedback that exposes an OOS result marks that holdout as observed for subsequent strategy-family experimentation; do not call it untouched OOS again after author iteration.

## CLOUD-09 End-to-end commissioning

Deliver an offline authoring helper that computes all hashes and emits the files/manifest in the correct sequence. Chat should create actual JSON file artifacts, not native cloud word-processing documents with JSON-looking text. Documentation must distinguish connector permissions/upload support from R7's local sync capability; do not claim a connected Chat can upload a file until the relevant tool succeeds.

A real cloud smoke test is explicit and bounded to the selected R7 root: submit one non-sensitive fixture, receive it locally, publish receipt, read it back through cloud. No whole-drive search, sharing changes, credential scraping or automatic OAuth enrollment. Folder-fixture tests remain OFFLINE_TRANSPORT_SIMULATION until that round-trip runs.

## CLOUD-10 Required fault probes

Test manifest-before-payload, byte reordering, truncated JSON, disappearing mount, symlink/reparse escape, Chinese/spaced root, case-collision package paths, conflicting same ID, repeated scans, crash after E6 registration, expired lease, stale worker commit, crash after outbox write, crash after upload-before-ack, destination content conflict, stalled sync, disk full, corrupt local snapshot, readonly directory and redaction of adversarial payloads.

No test receives real provider credentials or triggers GitHub compute. Local/cloud fixtures must never provide real strategy or deployment authority.
