# R7 product specification baseline v0.2

Date: 2026-10-02
Task: `CODEX-R7-PRODUCTIZATION-MASTER-20261002` (unchanged)
Reviewed main: `696ff055d33da2031f67bd15306e0978d15f5db0`
State: implementation specification, not implemented or qualified software.

## 1. User outcome

Chat authors declarative strategy packages and writes them to the user's cloud drive. A local R7 installation receives them, performs reproducible research and validation, rejects inadequate strategies, forward-tests candidates, captures explicit deployment approval, executes only within approved authority, and publishes performance evidence back to the drive. The same product offers a browser Control Center on Windows and on a headless Ubuntu host. No embedded AI Researcher, local LLM, or paid LLM API is required by R7. Codex is the development agent, not part of the runtime.

The user reports an older computer with 24 GB RAM and an unspecified GPU. CPU, architecture, GPU model, disk, driver support, operating system and actual throughput are unverified. These are deployment inputs, not grounds for claiming performance or GPU acceleration.

Product success is usable, auditable automation, not a promise that any strategy will pass or earn money. A run rejecting every submitted strategy can be a correct product result.

## 2. Authority and precedence

This v0.2 specification refines the existing v0.1 product program. It does not create another task or discard existing branches/evidence.

Read in this order:
1. `coordination/CODEX/TASK.md` and its current authorization references.
2. This file and `01_PLATFORM_DEPLOYMENT.md` through `07_ACCEPTANCE_MATRIX.json` in this directory.
3. Existing v0.1 master architecture, execution plan and acceptance matrix, except the explicitly superseded provisions below.
4. Canonical shared contracts, ADRs and relevant owner source/tests.

Explicitly superseded product provisions:
- Windows-only implementation/testing and Windows-only packaging: Windows and Ubuntu are now both required product targets; platform qualification is separate.
- Stopping on unavailable real provider authority before completing other code: continue independent credential-free work; real activation remains gated.
- A promise of exactly-once file delivery/execution: use at-least-once discovery with idempotent durable effects, transactional claims, replay-safe stages and an outbox.
- Treating a manifest-last write as a distributed atomic commit: it is a readiness hint; validate the complete byte set locally.
- A broad statement that all state truth is local: local E6 state governs application workflow; E4 provider observations govern actual orders/fills/exposure; E5 governs risk/lifecycle interpretation. Disagreement blocks new exposure.
- SMA-only as the final product capability: retain the legacy DSL/runtime unchanged and add the versioned capability profile specified in `02_STRATEGY_SEMANTICS.md`.
- OOS before any further adaptive robustness/tuning: all adaptive selection occurs on development partitions; the frozen finalist's sealed final OOS is evaluated last.
- Treating a short-horizon Chat recommendation as already validated: separate evaluation timeframe, submission validity, entry validity and maximum holding duration.
- One platform's test PASS qualifying another platform; simulated time qualifying real forward observation; simulation qualifying real broker operation: all are forbidden.

No new specification silently overwrites `contracts-v0.1` meanings. The explicitly specified additive strategy and evidence profiles are authorized implementation work; materialize them under their semantic owners, retain compatibility tests, and obtain final independent review before merging the implementation. Unspecified changes to risk authority, exposure policy, provider semantics or canonical lifecycle still require review.

## 3. Bounded v0.2 scope

Required: BTC perpetual instrument support through the existing canonical/provider mapping; 1m/15m/1h/4h inputs; single- and multi-timeframe declarative rules; eight specified indicator families; versioned exits and capability negotiation; cloud-drive artifact exchange; reproducible data catalog and research; validation/robustness; continuous local PAPER; approvals; LIVE-capable implementation and fake-provider tests; truthful Control Center; Windows launcher; Ubuntu service; backups/recovery; deployable documentation and authoring kit.

Excluded: arbitrary user Python, automatic runtime code installation, AI Researcher, GPU requirement, multi-exchange expansion, distributed trading, multiple active trading writers per account/instrument, mobile app, HFT, auto-funding/withdrawal, guaranteed profit. Do not invent extra strategy indicators beyond the declared set to postpone delivery.

A one-off tactical recommendation is supported as a typed package/request, but cannot obtain LIVE approval by bypassing the existing research and runtime gates. Previously qualified strategies can receive bounded activation requests through a separately authorized local workflow; cloud submissions alone cannot activate capital.

## 4. Components and ownership

| Component | Responsibility | Forbidden responsibility |
|---|---|---|
| CloudArtifactTransport / ResultPublisher | bounded artifact reads/writes and receipts | runtime database, deployment approval, shell execution from files |
| Inbox and durable job coordinator | package validation, claims, leases, retry/outbox | interpreting strategy or risk |
| E1 data services | finalized candles, timestamps, market health and source provenance | inventing missing candles |
| E2 strategy and capability services | parsing, deterministic features/rules/exit proposals, compatibility | broker access or risk approval |
| E3 research and validation | actual replay, costs, splits, robustness, statistics, decisions | LIVE promotion or claiming sample adequacy without data |
| E5 risk/position | limits, sizing approval, lifecycle interpretation, exit/protection authority | silently expanding a deployment envelope |
| E4 execution | broker translation, order/fill/exposure truth, reconciliation | strategy selection or weaker risk limits |
| E6 persistence | canonical registry, durable commands/events, recovery projections | replacing provider truth with stale local observations |
| Application/runtime services | sequence the above, enforce product gates | a second strategy, risk, or registry implementation |
| Control API/UI | authenticated commands and observable state | direct database writes or UI-only security |

Research and trading run in separate processes and resource budgets. A slow research job cannot block the trading event loop. The UI can disconnect without stopping the supervisor; stopping the UI is not a request to close a position.

## 5. Data/control separation

GitHub: source, schemas, ADRs, tests, sanitized engineering evidence.
Cloud drive: immutable submissions, datasets or references, capability snapshots, reports.
Local store: jobs, registry, outbox, local approvals, operational state and audit history.
Provider: actual orders, fills and exposure, interpreted through E4/E5.

Drive artifacts and Chat prose are untrusted data. An artifact may request a locally configured validation profile, never redefine its limits, install code, provide commands or change account state. Hashes prove byte integrity, not trusted authorship.

## 6. Product states are separate

Do not conflate: intake state; job state; execution evidence status; quantitative decision; canonical strategy lifecycle; OperationalMode; process health; data freshness; financial risk lock; reconciliation lock; deployment authorization; cloud publication state.

For example, research execution can succeed while the strategy fails. An online API can report trading disabled. A stored LIVE mode is not proof of current permission. A hash mismatch during synchronization is not a quantitative strategy rejection.

## 7. Evidence and completion levels

Track separately:
- CODE_COMPLETE: required implementation exists and code review is recorded.
- SIMULATED_E2E_PASS: deterministic test fixtures pass; no real-strategy authority.
- WINDOWS_QUALIFIED: required tests/install/recovery pass on native Windows.
- UBUNTU_24_04_QUALIFIED and UBUNTU_26_04_QUALIFIED: native or explicitly identified local VM platform evidence, including systemd tests.
- CLOUD_CONNECTED: operator-configured real cloud round-trip verified; folder fixture PASS is not this.
- PAPER_FORWARD_QUALIFIED: actual elapsed observation and sample requirements met for the exact strategy/profile.
- LIVE_PROVIDER_VERIFIED / LIVE_AUTHORIZED: separate fresh provider and human authority.

`PRODUCT_IMPLEMENTATION_COMPLETE` requires all mandatory code and platform acceptance items, with external commissioning exclusions explicitly listed. It must not be reported as a real deployment or real financial validation. Missing platform execution is NOT_RUN, not inferred PASS. A unavailable platform may block final cross-platform qualification but must not block unrelated implementation.

## 8. Decisions fixed here versus remaining configuration

Fixed engineering decisions: Python core; FastAPI local API; React/TypeScript/Vite static UI; local SQLite; CPU-reference strategy calculations; portable processes; Ubuntu systemd integration; PyInstaller native-per-platform packaging; optional rclone one-way copy bridge for Ubuntu cloud synchronization; declarative packages; no runtime LLM.

Runtime selections requiring local commissioning: exact data/cloud paths; validated hardware inventory; authentic cloud account connection; chosen dataset/profile; real financial validation thresholds; risk/capital limits; actual provider hostname/account permissions; deployment approval. Provide complete schemas and safe first-run screens for these inputs. Do not invent their values or turn examples into approval. Development fixtures remain separately labeled.

## 9. Specification index

- `01_PLATFORM_DEPLOYMENT.md`: platforms, resources, cloud bridge, packaging, authentication, operations.
- `02_STRATEGY_SEMANTICS.md`: DSL/capabilities, indicators, timeframes, validity and exits.
- `03_CLOUD_SECURITY.md`: packages, durability, idempotency, artifact integrity and trust.
- `04_RESEARCH_LIFECYCLE.md`: datasets, independent evidence, validation, lifecycle and execution.
- `05_PRODUCT_OPERATIONS_UI.md`: application interfaces, UI, recovery and commissioning.
- `06_EXECUTION_PLAN.md`: implementation sequence, concrete interfaces/tests and resumption.
- `07_ACCEPTANCE_MATRIX.json`: machine-readable requirements and mandatory evidence.

All numbers in configuration proposals are engineering defaults or test limits unless explicitly marked as user-approved financial policy. The developer must publish the exact versioned schemas, capability manifest and examples from executable implementations, not advertise unsupported capabilities.
