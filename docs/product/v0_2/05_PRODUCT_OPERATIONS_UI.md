# R7 v0.2 application, Control Center and operations

Authority: `00_EXECUTION_BASELINE.md`. No AI Researcher page, runtime LLM or paid API dependency.

## APP-01 Application ports

Implement these concepts behind small typed modules. The following signatures are the product-level interface contract; concrete classes use dataclasses/strict validation and existing domain objects rather than parallel models.

- `CloudArtifactTransport.discover() -> Iterable[ArtifactDescriptor]`; `read_verified(descriptor, limit_bytes) -> bytes`; `publish(bundle, operation_id) -> PublishReceipt`. Logical paths and hashes only; no package-supplied shell arguments.
- `StrategyInboxService.scan_once(now: datetime) -> ScanSummary` with counts/typed per-submission results, not a fabricated global PASS.
- `CapabilityService.snapshot() -> CapabilitySnapshot`; `check(definition, required_snapshot) -> CompatibilityReport`.
- `DatasetResolver.resolve(profile_id, cutoff: datetime) -> DatasetBinding` including exact E1 data and split inputs.
- `ResearchService.enqueue(submission_id, policy_id, command_id) -> ResearchRunRef`; `step(run_id, lease_generation) -> StageOutcome`; `cancel(run_id, expected_revision, command_id) -> CommandReceipt`.
- `PaperService.start(strategy_identity, policy_id, expected_revision, command_id) -> PaperRunRef`; `stop_new_entries(run_id, command_id) -> CommandReceipt`; actual shutdown is separate from this command.
- `ApprovalService.record(subject, envelope, authenticated_actor, decision, command_id) -> ApprovalRecordRef`.
- `RuntimeAdmission.evaluate(current_evidence) -> PreflightDecision`; delegate existing E7/E5/E6/E4 semantics without reinterpreting them.
- `Publisher.flush(limit: int) -> PublishSummary`; `HealthService.snapshot() -> ProductHealthView`.

Implement command_id idempotency and optimistic revision checks transactionally at the command boundary. Duplicate command with identical content returns the same logical receipt; changed content under the same ID conflicts. Async HTTP202 means accepted/queued, not completed.

## APP-02 Process supervision

R7 must operate without a Chat session, Codex process, browser tab or AgentBridge being alive. AgentBridge is an optional development/operator integration, not an assumed prerequisite of ordinary packaged Research/PAPER use. Where an external operator/supervisor participates, it must supply actual accepted FP-16 compatibility evidence; do not fake it or bypass it. The native product supervisor has its own exact process/config generation and verification.

Control/API, durable coordinator, research workers and trading runtime have separate health/failure boundaries. A child cannot hold a SQLite write transaction while performing network I/O or a long statistical calculation. UI failure does not terminate protective management. A supervisor restart does not automatically clear financial/reconciliation locks or authorize LIVE.

## API-01 Common response and command rules

Use FastAPI, versioned `/api/v1`, strict input DTOs, bounded body/page sizes and stable reason codes. GET responses include source, observed_at, as_of, freshness/status, relevant project/config/strategy versions, current versus last-known-good labels and null for unavailable metrics.

Every write command includes command_id and expected resource revision; server binds authenticated actor. Never accept actor='ProductOwner' as authority merely because a JSON body says so. Reject unknown keys and stale revisions. No endpoint accepts raw SQL, filesystem paths outside configured roots, arbitrary code, user-supplied executable evidence PASS, or a cloud-borne approval.

Minimum routes:
| Route | Contract |
|---|---|
| GET /overview | current mode, queued/running jobs, lifecycle counts, runtime/exposure/alerts; no false green |
| GET /capabilities | exact implemented/verified profiles and missing features |
| GET /submissions and /submissions/{id} | observed/verified/claimed/blocked/published states and reasons |
| POST /research/scan | request a bounded inbox scan, no provider mutation |
| GET /research/runs and /research/runs/{id} | stage input/output refs, observed progress, evidence |
| POST /research/runs | enqueue an allowed submission+local policy |
| POST /research/runs/{id}/cancel | cooperative bounded cancellation, retain evidence |
| GET /strategies and /strategies/{id}/{version} | immutable definition, lifecycle, capability and research lineage |
| GET /datasets and /policies | configured allowed profiles and readiness, no secrets |
| POST /paper/runs | guarded start of selected candidate in selected simulation mode |
| GET /paper/runs/{id} | simulated versus real-time forward provenance, positions, metrics |
| POST /paper/runs/{id}/pause | stop new entries while retaining position management |
| GET /trading | real current E4/E5/E6 projection, not locally guessed flatness |
| GET /health and /alerts | timestamped component/process/dependency diagnostics |
| GET /settings and PUT /settings/non-secret | validated local settings, no secret values |
| POST /approvals | authenticated exact-subject decision and immutable envelope |
| POST /deployments/{id}/activate | fail closed unless separately commissioned real authority exists |
| POST /deployments/{id}/pause | revoke admission of new entries, never erase broker state |

Actual response DTOs and OpenAPI snapshot are committed and tested. Error categories separate INVALID_INPUT, INCOMPLETE_SYNC, CONFLICT, INSUFFICIENT_EVIDENCE, POLICY_FAIL, NOT_CONFIGURED, AUTHORIZATION_REQUIRED, UNAVAILABLE and INTERNAL_ERROR. Internal errors use sanitized correlation IDs, not stack traces with secrets.

## UI-01 Required screens

Default language Traditional Chinese with exact English identifiers available in details. Store/display times in UTC with an explicit selectable display timezone (Asia/Taipei is a UI preference, not data alignment). Support ordinary desktop browser widths and keyboard navigation.

Overview: what is running, stage counts, current strategy/version, actual mode, fresh/last-known health, cloud staging/remote acknowledgment, resource limits, alerts and why trading is disabled.

Research: inbox -> compatibility -> dataset -> development backtest -> robustness -> sealed OOS -> decision. Show completed/total counts only when measured; indeterminate stages have no fake percentage. Filters for rejected, blocked, insufficient evidence, canceled, expired and waiting for configuration. Clicking a reason opens source evidence and corrective guidance.

Strategies: identity/version/hash, hypothesis supplied by author, required capabilities, evaluation timeframe, validity interval, max hold, lineage, train/development/OOS separation, trial count, costs/sample counts/uncertainty, actual lifecycle and evidence. Show no invented profitability rank for untested submissions. A 4h timeframe and a four-hour expiry are separate fields.

Trading: PAPER fixture versus real-time PAPER versus LIVE visibly distinct; exact deployment/version; current Signal/TradeIntent/RiskDecision; order ACK versus actual fill; position/reconciliation; protection currentness; realized/unrealized PnL separately; reasons for no trade. Report fee/funding/slippage conventions and avoid double-subtracting slippage already reflected in fill price.

Health: individual process/data/risk/execution/storage/cloud states and timestamps. No global SAFE_TO_TRADE solely because HTTP/server is online or unit tests passed. Expandable exact revision/preflight/FP evidence. Missing GPU is informational, not a failure.

Settings/commissioning: local/cloud roots, resource budgets, configured profiles, public data source, clock health, backup paths, transport test, server-access mode and credentials-presence status without secret values. Full configuration schema validation happens server-side.

No AI-generated explanation of system state is needed: deterministic reason codes map to clear text. Empty database pages show '尚無資料', not illustrative profits. Fixture/demo mode has persistent conspicuous labeling, isolated data directories and no access to real deployment approvals.

## UI-02 Controls and financial authority

First usable release must offer real research scan/enqueue/cancel and PAPER start/pause/stop workflows; a read-only mock dashboard is not completion. A disabled button is not backend security.

Human approval screen displays exact strategy hash/version, source/build/config/risk policy, sample/uncertainty report, proposed capital/risk envelope and consequences. It requires reauthentication for LIVE/financial-limit operations, immutable audit and explicit confirmation. The server verifies all subject identities and prerequisites again on submission; stale tabs conflict. Persistent authority has expiry/revocation semantics. 'Approve' cannot silently change a strategy version or leverage.

Controls distinguish stop research, stop new entries, pause deployment, request E5 emergency action and stop service. Browser close never means close position. A user must see known remaining exposure and who manages protection before a managed shutdown.

## OPS-01 First run and unattended operation

First run: detect platform/hardware -> select local data root and cloud staging/root -> initialize E6/app stores -> create local authentication -> configure or skip cloud bridge -> choose diagnostic or locally commissioned policies -> enter RESEARCH with real trading disabled -> open Overview.

A configured inbox scan/research pipeline proceeds automatically without per-strategy Chat intervention. Candidates may automatically enter PAPER only under the locally configured PAPER workflow authorization. A pending human approval does not block unrelated research; no polling storm. All permissions are enforceable without a browser being open.

No fabricated real forward data to finish an acceptance run quickly. Offline accelerated acceptance proves mechanics; unattended real forward observation accumulates separately.

## OPS-02 Failure behavior

Cloud loss: publisher retries; local execution evidence preserved; state says CLOUD_UNAVAILABLE.
Market loss/stale data: no new exposure; continue available reconciliation/protection management; alert.
Unknown broker outcomes: reconcile before retry, no duplicate orders.
Research worker OOM/hang: terminate only its owned tree, release lease safely, retain incomplete stage, runtime remains independent.
DB corruption/disk full: explicit storage failure, no false success/new exposure; operator recovery from consistent backup.
Power loss/reboot: load durable state, invalidate process-generation evidence, reconcile before trading; never assume no position because no local row exists.
Policy/capability/code update: invalidate affected pending research/deployment evidence and requalify exact revisions; no in-place live edits.

## OPS-03 Acceptance and release content

Required product distribution includes source/build revision, dependency locks/licenses, package hashes, native install/uninstall/upgrade/recovery instructions, cloud connector commissioning guide, authoring kit, test runner and an acceptance results index. The Ubuntu service path is as mandatory as the Windows launcher.

Monitoring does not imply this Chat remains active. Product persistence and Codex development checkpoints are separate. The build must be resumable, but neither a Markdown task nor a GitHub merge proves a local Codex process was started.
