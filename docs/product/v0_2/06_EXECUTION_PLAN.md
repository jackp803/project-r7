# R7 v0.2 continuous implementation plan

> For agentic workers: use the installed superpowers executing-plans workflow, or subagent-driven-development when available, task-by-task. Keep TDD and verification-before-completion. The Product Owner explicitly selected continuous Codex execution; do not ask again after ordinary passing milestones.

**Goal:** deliver the full existing R7 product program with Windows/Ubuntu parity, specified strategy capabilities, reliable cloud exchange, real application/UI, and separately gated live activation.
**Architecture:** compose existing E1-E6 through typed application services. Add versioned E2/E5 profiles, not alternative domain engines. Persist commands/jobs/effects and isolate research from trading processes.
**Tech stack:** Python/Decimal/SQLite/FastAPI; React/TypeScript/Vite; native PyInstaller packaging; Ubuntu systemd; optional bounded rclone bridge.
**Spec:** all `docs/product/v0_2/00_EXECUTION_BASELINE.md` through `05_PRODUCT_OPERATIONS_UI.md` and `07_ACCEPTANCE_MATRIX.json`.
**Authoritative task:** `CODEX-R7-PRODUCTIZATION-MASTER-20261002` (unchanged).

## Global constraints

- Use existing canonical packages (`strategy.*`, `position.*`, etc.), not duplicate `src.*` class identities.
- Legacy DSL0.1/Runtime0.1.0 behavior remains intact; new DSL0.2/Runtime0.2.0 is explicit.
- Windows11 x86-64 and Ubuntu24.04/26.04 x86-64 are required targets; evidence is per target.
- No runtime LLM/GPU requirement, GitHub compute, real provider credentials/private calls or real capital.
- No destructive worktree changes; preserve and reconcile any existing productization implementation.
- Cloud readiness is validated locally; at-least-once delivery uses idempotent effects, not exactly-once claims.
- Missing real hardware/cloud/financial inputs are explicit commissioning gaps, not invented values.
- All project execution occurs on the user's approved local Windows/Ubuntu environment; this Chat's hosted analysis container is not a project test runner.

## Review focus

1. Crash between E6 registration and intake-ledger commit: retry must reuse canonical state (S02).
2. 15m evaluation consuming unfinished4h candle: future prices must not influence signal (S05).
3. Reusing final OOS after Chat feedback: observed holdout cannot count as fresh evidence (S07).
4. Research OOM/process-tree timeout during protective management: runtime stays isolated (S01/S09).
5. Ubuntu service restart or stale UI approval: process liveness cannot re-authorize money (S10/S13).

## Branch, authority and progress

Read current main, TASK, authorizations, progress and existing branches before work. Reuse `codex/r7-productization-master-20261002` when it exists; otherwise create it from reviewed latest main. Preserve any prior P1/master work. Merge/reconcile updated specs non-destructively. Freeze the code/config tested at each milestone; reading newer main never transplants PASS evidence.

Keep original M1-M11 program identities for continuity. The S01-S16 items below are internal work packages within that same task, not new mailbox task IDs. They refine dependencies and may run in parallel only with separate file ownership and fixed interfaces.

Persist `coordination/CODEX/PROGRESS.json` and `coordination/CODEX/HANDOFF.md` on the implementation branch. Progress includes task_id, spec_baseline, base/branch/executable revisions, each M/S status, active_step, next_step, test evidence refs, platform states, blocker class and restart instructions. Never put auth tokens, local credential paths or private payloads in these files.

Allowed work statuses: NOT_STARTED, IN_PROGRESS, PASS, FAIL, BLOCKED, WAITING_EXTERNAL, PAUSED_USAGE_LIMIT. Actual test evidence uses canonical PASS/FAIL/BLOCKED/NOT_RUN/NOT_APPLICABLE. Wait states are not completion.

For every work package: write specific failing tests; run to confirm the intended failure; implement; run focused and affected regression tests; commit an exact executable checkpoint; run qualification from a clean worktree; record evidence in a later commit. Test counts must come from actual output, not expected counts. Run a fresh independent review when available; otherwise label SELF_REVIEW and retain final PM review as required. Never call a self-review independent.

## S01 / M1 foundation: portable installation and resource isolation

Files: add `pyproject.toml` if absent; `src/application/config.py`, `src/application/platform/{paths,processes,resources}.py`, `tools/run_credential_free_tests.py`; tests under `tests/application/test_platform.py` and `test_process_tree.py`.

Interfaces: `load_config(path: Path) -> ProductConfig`; `inspect_hardware() -> HardwareReport`; `spawn_owned(argv: Sequence[str], cwd: Path, limits: ResourceLimits) -> OwnedProcess`; `terminate_owned(handle, deadline_seconds: int) -> TerminationReport`.

- [ ] Write tests rejecting nested cloud/data roots, Windows-path assumptions, invalid resource settings; verify Chinese/spaced paths and UTF-8.
- [ ] Add parent/child/grandchild timeout test and one unrelated process that must survive; run and confirm intended failures.
- [ ] Implement platform adapters and one-worker conservative profile; do not add GPU initialization.
- [ ] Implement portable test runner using actual test inventory and the existing full credential-free manifest. Detect omitted test directories and zero-test suites. Use the canonical import search root, not class aliases.
- [ ] Run `python tools/run_credential_free_tests.py --suite application` plus existing import-identity/strategy/storage suites; record actual platform and commit.

## S02 / M1: manifest, snapshots, intake and outbox

Files: `src/application/cloud/{protocol,synced_folder,manifest,publisher}.py`; `src/application/intake/{service,ledger}.py`; E6 bounded atomic/idempotent intake additions if needed; application-owned migrations; tests `test_cloud_intake.py`, `test_claim_recovery.py`, `test_outbox.py`.

Interfaces: the cloud/intake/publisher ports in APP-01; `validate_package(snapshot: PackageSnapshot) -> VerifiedPackage`; `claim(submission_id, manifest_hash, owner, now) -> ClaimResult`; `commit_effect(claim, effect_ref, outbox_item) -> CommitResult`.

- [ ] Write malformed/path/secret/partial-sync tests and same-ID changed-content conflict tests.
- [ ] Write fault injection after E6 registration, lease expiry, outbox commit and upload-before-ack; run failing tests.
- [ ] Implement sealed local snapshots, transactional claims, E2 parsing, actual E6 DRAFT intake and idempotent effect reconciliation.
- [ ] Implement immutable receipts and LOCAL_STAGED versus CLOUD_ACKNOWLEDGED; no cloud deletion.
- [ ] Run application, strategy, registry, storage regressions; commit and record M1 evidence.

## S03 / M2 capability prerequisite: profile routing and schemas

Files: existing `src/strategy/runtime.py` router preserved; add `src/strategy/v02/{models,parser,ast,capabilities}.py`; `contracts/strategy_dsl_v0_2.schema.json`; `contracts/strategy_package_v0_2.schema.json`; versioned profile documentation; tests `tests/strategy/test_v02_parser.py` and `test_legacy_compatibility.py`.

Interfaces: `parse_v02(payload: Mapping[str, object]) -> ParsedStrategyV02`; `build_capability_snapshot() -> CapabilitySnapshot`; `check_compatibility(definition, snapshot) -> CompatibilityReport`. Preserve public legacy APIs.

- [ ] Pin existing DSL0.1 golden results and write v0.2 invalid grammar/units/cycle/limit tests.
- [ ] Run before implementation and verify unsupported-version failure, not an unrelated setup failure.
- [ ] Implement explicit profile dispatch and strict bounded AST; materialize the exact STR-02 grammar.
- [ ] Generate registry entries only from implemented/versioned primitives with verification metadata; expose missing features.
- [ ] Run both legacy and new strategy/parser suites, canonical import tests and existing backtest tests; commit.

## S04 / M2: indicators and incremental parity

Files: `src/indicators/v02/` focused modules for common arithmetic, trend, Wilder, bands and rolling features; tests `tests/indicators/test_v02_golden.py` and `test_v02_incremental.py`.

Interfaces: `evaluate_feature(spec: FeatureSpec, prefix: CandlePrefix) -> FeatureValue`; `update_feature(state: FeatureState, bar: Candle) -> FeatureUpdate`. Value carries readiness, units, source boundary and semantic profile.

- [ ] Write exact small hand-calculable vectors for all eight indicator families, flat markets, n=1, insufficient history, tie-direction ADX and zero denominators.
- [ ] Write full-prefix versus incremental/snapshot-recovery parity and run failing tests.
- [ ] Implement STR-03/04 Decimal arithmetic, seeds and output-readiness semantics; never hide float conversions.
- [ ] Verify arithmetic operators/crossover/current-bar exclusion and feature limits.
- [ ] Run indicators+strategy+backtest regressions on available local platforms; commit. Unavailable platform remains NOT_RUN.

## S05 / M2: as-of bundles,4h/15m, tactical validity and exits

Files: `src/strategy/v02/{evaluation,temporal}.py`; E1 bounded bundle/aggregation adapter; E5 versioned exit-request consumer in `src/position/`; tests `test_v02_multitimeframe.py`, `test_v02_validity.py`, `tests/position/test_v02_exit_requests.py`.

Interfaces: `build_asof_bundle(candles_by_timeframe, boundary, information_cutoff) -> AsOfBundle`; `evaluate_v02(strategy, bundle) -> Signal`; `assess_submission_validity(manifest, now) -> ValidityDecision`; `interpret_exit_request(request, current_e5_authority) -> PositionAction` using existing authority types.

- [ ] Write11:45/12:00 UTC4h-finality tests; change all future bars and assert earlier signals identical.
- [ ] Write evergreen4h and four-hour-validity expiry tests; expiry blocks entry, not required management of open exposure.
- [ ] Implement cross-timeframe feature alignment, gap rejection and independent entry/holding clocks.
- [ ] Implement fixed/ATR/target/trailing/time-exit proposals under E5; test wrong direction/equality, no widening, actual partial fills and max-hold from first fill.
- [ ] Run E2/E3/E5 integration, protection and old FP-03 regressions; commit.

## S06 / M2: dataset catalog and actual research service

Files: `src/application/datasets/{catalog,resolver,split_plan}.py`; `src/application/research/{service,orchestrator,evidence}.py`; actual E2 compatibility execution adapter; tests `test_dataset_binding.py`, `test_research_pipeline.py`.

Interfaces: APP-01 DatasetResolver/ResearchService; `resolve_split(dataset, policy) -> FrozenSplitPlan`; `execute_compatibility(package, execution_context) -> CompatibilityEvidence` through accepted E2/E6 boundary.

- [ ] Write logical/byte hash, missing funding, gap/finality, wrong units and immutable-policy tests.
- [ ] Write a true E1 -> E2 -> E3 -> E6 integration test, without test-only compatibility PASS injection; run failing tests.
- [ ] Implement pinned dataset resolution, diagnostics, warmup and split plan with real owner services.
- [ ] Persist stage attempts/results with private trusted local execution provenance; reject external PASS injection.
- [ ] Run data/strategy/backtest/validation/registry/application suites; commit.

## S07 / M3: robustness and sealed OOS

Files: E3-owned `src/validation/robustness/` and application orchestration adapters; tests `tests/validation/test_robustness_v02.py`, `test_holdout_ledger.py`, `test_walk_forward.py`, `test_monte_carlo.py`.

Interfaces: `evaluate_robustness(subject, development_binding, policy, seed) -> RobustnessAssessment`; `freeze_finalist(run, strategy_hash, policies) -> FrozenFinalist`; `evaluate_sealed_oos(finalist, holdout_binding) -> ProductAssessment`.

- [ ] Write finite neighborhood/invalid-variant, purging/overlap, trial-ledger and Chat-observed-holdout tests.
- [ ] Write seed reproduction and sample-inadequacy tests; distinguish permutation drawdown from expectancy inference; run failures.
- [ ] Implement documented algorithms and versioned thresholds using actual E3/E2 replay; no final OOS in adaptive choices.
- [ ] Produce E3 assessment and all raw/summary refs, preserving unfavorable results and cost/availability assumptions.
- [ ] Run validation/backtest/application/integration suites; commit.

## S08 / M4: canonical lifecycle and approval authority

Files: existing `src/registry/{service,lifecycle_authority}.py`, E6 store/migrations; new approval/product-assessment adapters; tests `tests/registry/test_product_lifecycle_v02.py`.

Interfaces: named guarded E6 methods for each legal edge; `record_product_assessment(...)`, `start_paper(...)`, `mark_ready_for_approval(...)`, `record_approval(...)`, `activate_deployment(...)`, `degrade(...)`, `resume_authorized(...)`, `retire(...)` using canonical identity/revision/evidence.

- [ ] Write every canonical legal edge and relevant illegal skip; verify product robustness gate cannot be bypassed through a legacy API.
- [ ] Write wrong-version/stale/caller-forged approval and direct store bypass tests; run failures.
- [ ] Materialize canonical lifecycle with additive migrations and product assessment binding; no duplicate lifecycle database.
- [ ] Separate quantitative FAIL from insufficient evidence and preserve rejected histories.
- [ ] Run registry/storage/validation/safety regressions; commit.

## S09 / M5: continuous PAPER and bounded scheduler

Files: `src/application/paper/{service,scheduler,orchestrator,assessment}.py`; runtime IPC/persistence adapters; tests `tests/product/test_paper_runtime_v02.py`, `test_research_isolation.py`.

Interfaces: APP-01 PaperService; `on_market_event(event) -> RuntimeOutcome`; `on_deadline(deadline) -> RuntimeOutcome`; `assess_forward(run, policy) -> ForwardAssessment`.

- [ ] Write full entry/ACK/fill/protection/exit/flat cycle tests with actual E2/E5/PaperBroker/E6 calls.
- [ ] Write repeated-boundary, partial fill, stale market, expiry, missing protection, sleep/restart and OOM-isolation tests; run failures.
- [ ] Implement continuous scheduler with separately scheduled protection/time-exit management and durable operation IDs.
- [ ] Implement distinct accelerated fixture and real-time forward modes; synthetic time cannot satisfy real-forward evidence.
- [ ] Run product/e2e/risk/position/execution/storage/safety suites; commit.

## S10 / M6: authenticated API and command ledger

Files: `src/application/control_api/{app,dto,auth,commands}.py`; tests `tests/product/test_api_authority.py`, `test_api_csrf.py`.

Interfaces: actual routes/DTOs specified in API-01; immutable command receipts and actor binding.

- [ ] Write localhost/Origin/Host, session, CSRF, stale-tab/revision and command-id conflict tests.
- [ ] Write untrusted evidence/approval injection and no-secret-response tests; run failures.
- [ ] Implement route handlers solely through application services; approval actor comes from authentication.
- [ ] Implement truthful health/progress and explicit nulls/NOT_RUN; no raw database endpoints.
- [ ] Run API/application/safety suites, generate OpenAPI snapshot and commit.

## S11 / M7: functional Traditional-Chinese Control Center

Files: `ui/` React/TypeScript/Vite app, typed API client, pages/components and browser tests; no runtime remote-CDN requirement.

Interfaces: generated/validated API DTOs from S10; no direct SQLite/file-system calls.

- [ ] Write browser acceptance for empty states, observed progress,4h versus validity, unavailable metrics and persistent fixture labeling.
- [ ] Write scan/enqueue/cancel/PAPER pause, stale approval conflict, keyboard/error interaction tests; verify failures.
- [ ] Implement Overview, Research, Strategies, Trading, Health, Settings/commissioning and capability-gap details.
- [ ] Build production assets and serve through local backend; prove backend denials are visible and no mock profit data remains.
- [ ] Run `npm --prefix ui ci`, UI typecheck/unit/build and local browser acceptance using pinned scripts; commit. Missing browser evidence is NOT_RUN, not PASS.

## S12 / M9: real implementation surfaces, simulated provider verification

Files: `src/application/trading/{service,orchestrator,admission}.py`; necessary existing E4 adapter additions under accepted/versioned action profiles; secure-credential provider interface; tests `tests/product/test_live_admission_v02.py` and fake-provider E2E.

Interfaces: existing E4 approved-plan/action and provider-observation contracts; APP-01 RuntimeAdmission/ApprovalService.

- [ ] Inspect existing actual E4 implementation and current official provider documentation; write a capability gap/mapping inventory before adding missing code.
- [ ] Write missing/wrong/stale authority, process generation, ambiguous submit, partial fill, duplicate/orphan protection, residual, exit and restart tests; run failures.
- [ ] Implement production request/readback/translation code where scoped, with fake HTTP transport; a NotImplemented stub is not completion.
- [ ] Preserve every existing LF/FP fail-closed behavior and zero real private/provider calls. Unsupported actual capability remains explicitly non-executable and a listed delivery gap.
- [ ] Run original complete credential-free matrix plus new trading/E2E suites; commit. Real activation remains NOT_AUTHORIZED.

## S13 / M8: native packaging, Ubuntu services and recovery

Files: `packaging/windows/`, `packaging/linux/`, `packaging/linux/systemd/`, `tools/build_product.py`; tests `tests/acceptance/test_native_install.py`, `test_service_recovery.py`.

Interfaces: portable CLI `r7 doctor`, `r7 serve`, `r7 research-worker`, `r7 runtime`, first-run non-secret settings and managed shutdown.

- [ ] Write fresh-profile/start/Chinese-path/native migration and no-Python/no-Node end-user tests.
- [ ] Write service process-group cleanup, restart backoff, pending-position shutdown and restored-generation tests; run failures.
- [ ] Build Windows and Ubuntu packages natively; implement unprivileged systemd units with resource limits and explicit writable roots.
- [ ] Verify SSH-tunnel access guide; direct LAN mode fails closed until TLS/auth requirements are configured.
- [ ] Execute package/start/stop/restart/backup restore tests on each available target; commit evidence per target. Continue remaining code if a native target is not attached, but do not claim cross-platform release PASS.

## S14 / M10: cloud bridge, feedback and authoring kit

Files: `src/application/cloud/rclone_bridge.py`, bounded setup/diagnostic CLI; `docs/strategy/authoring-v0.2/`; report schema/rendering and sample generator; tests `test_cloud_bridge.py`, `test_authoring_roundtrip.py`, `test_feedback_redaction.py`.

Interfaces: existing transport/publisher and CapabilityService; `build_package(definition, request_metadata, snapshot) -> PackageBundle`; `render_feedback(result_refs, publication_policy) -> ArtifactBundle`.

- [ ] Write bounded copy-only argv, duplicate-name, remote-ack/outage and malicious-manifest tests; run failures.
- [ ] Implement Ubuntu rclone local-stage bridge without reading operator credentials during development; no delete/sync/bisync.
- [ ] Generate actual JSON schemas/capability snapshots/examples with computed hashes and a compact Chat-facing summary.
- [ ] Test round-trip valid legacy,4h, multi-timeframe, tactical expiry and missing-feature packages; scan reports for secret/provider leakage.
- [ ] Run offline transport tests; provide and separately label bounded real-cloud commissioning test; commit.

## S15 / M11: whole-product acceptance and capacity evidence

Files: `tests/acceptance/test_strategy_to_feedback.py`, `test_cross_platform_parity.py`, `test_operational_faults.py`, portable acceptance runner and requirement-to-evidence report.

- [ ] Map every old applicable acceptance item plus every v0.2 requirement ID to named tests/evidence. Reject missing/unmapped rows.
- [ ] Run valid fixture -> CANDIDATE -> PAPER mechanics -> fixture-only READY; weak -> REJECTED; malformed -> BLOCKED; partial sync -> one durable logical effect; tactical expiry -> no entry.
- [ ] Run native per-platform golden parity and service/install/recovery; execute resource pressure/24GB-oriented benchmark on actual available hardware and identify it.
- [ ] Run complete tests and browser flows; verify artifacts/cloud publication stages and LIVE-denial/approval-forgery scenarios.
- [ ] Freeze exact final executable/builds, run clean qualification, collect counts/log hashes/source/config/OS provenance and report all unexecuted external/real-forward/real-provider checks separately.

## S16 final review and return

- [ ] Perform whole-branch architecture/security/contract review; address all material findings with regression and repeat affected/full qualification.
- [ ] Push the bounded implementation branch and persist `status/codex/R7_PRODUCTIZATION_MASTER_COMPLETION_20261002.md` plus machine-readable acceptance results.
- [ ] Update PROGRESS/HANDOFF with exact code versus evidence/build revisions, platform statuses, package hashes, limitations and commissioning tasks.
- [ ] Open/update one implementation PR if appropriate. Do not merge the implementation branch into main or activate real trading.
- [ ] Return `MASTER_RESULT`, all M/S results, native platform states, real-cloud/forward/provider states, counts and exact evidence refs for final PM/user acceptance.

## Self-advance and real stop conditions

Automatically advance after the affected package's gate passes; do not seek a new PM wake for routine engineering choices. Fix ordinary reproducible code/test/UI/packaging defects. A failure is never permission to delete/skip/weaken its test.

If a platform/cloud/real dataset is absent, label its tests NOT_RUN/WAITING_EXTERNAL and continue independent work. If that evidence is mandatory for final release, final result is PARTIAL/BLOCKED with the gap, not PASS. If repeated attempted fixes make no progress, record reproducible cause and a bounded no-progress checkpoint rather than looping forever.

Stop for an unspecified material architecture/financial-authority decision, a genuine security incident, missing local capability essential to the current dependency, unresolved external dependency, user interruption or exhausted tool/subscription capacity. For quota/session exhaustion use PAUSED_USAGE_LIMIT with exact branch/step/handoff; never switch to a paid API, buy credits, bypass sandbox policy or launch an uncontrolled restart loop.

Continuous execution means automatic progression while an actual Codex session/runner is alive. It cannot guarantee unlimited subscription time or persistence. Resume the SAME task/branch from progress; a manually started continuation or authenticated local runner may be needed after the host/session stops. No GitHub-hosted/GitHub-triggered compute or scheduled cloud Codex task is allowed as a workaround.

## Initial specification self-review

Checked: all earlier product goals retained; Windows-only constraints superseded explicitly; deployment claims separated from test evidence; legacy strategy semantics preserved; every new capability has deterministic semantics; every common failure above has an owning work package; platform and external activation gaps cannot be silently omitted. No production code, tests, packaging, cloud sync or real deployment is claimed complete by this plan.
