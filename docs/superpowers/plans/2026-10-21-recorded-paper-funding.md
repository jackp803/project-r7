# Public Recorded Paper Funding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ordinary native Paper uses selected public settled funding rates with the approved entry-fill notional model, safe pending finalization and exact-source evidence.

**Architecture:** E4 registers a new PAPER_MODEL source using existing funding-allocation-v0.1. Independent bounded acquisition supplies source-owned observations; the application persists true flat/fills before deferred financial finalization. Existing E5/E6 financial and lifecycle contracts remain authoritative.

**Tech Stack:** CPython3.12, Decimal, existing urllib public transport, SQLite E6 journals, existing private filesystem/owned-child/supervisor infrastructure, native Windows packaging and existing UI/report stack; no new dependencies.

**Spec:** `status/codex/productization/S16/ordinary-paper-recorded-funding-20261021/FUNDING_MODEL_DESIGN.md` (human adopted on2026-10-21; exact accepted file hash in operator-decision.json).

## Global Constraints

- Same task `CODEX-R7-PRODUCTIZATION-MASTER-20261002` and branch `codex/r7-productization-master-20261002`; root is sole tracked-file writer.
- LOCAL_RESEARCH/REAL_TIME, BTC_USDT_PERP only; actual public settled realizedRate, never private account truth or predicted rate.
- PAPER_MODEL with `paper-public-recorded-entry-notional-v0.1`; new ordinary simulation profile `r7-paper-simulation-policy-v0.5`, funding model `OKX_PUBLIC_RECORDED_ENTRY_NOTIONAL_V1`; preserve legacy and FIXTURE profiles.
- No new canonical lifecycle, PnL meaning, financial defaults, credentials, real account/capital, LIVE/10U, paid API/LLM, GitHub compute, OS startup/power/security changes or main merge.
- Preserve selected numerical policies, original source/build/evidence mapping, family/holdout history and exact software qualification ownership. Original bffc receipt does not qualify changed code or another store.
- Preserve raw public capture and failure accounting. Current public cumulative17requests/17responses; future actual calls add to this count.
- E4 fixed-point inputs<=64chars, integer/fraction<=18digits each, significant<=34; fills/events<=1000; isolated prec128/Emin-256/Emax256 with required traps; canonical zero; exact downstream decimal34 representation or refusal.
- Source freshness60s, refresh5s; one owned child per source kind,165requests/120s transport deadline/125s outer deadline/2MiB response/89day history; combined market+funding+preflight retention86400attempts or1GiB per runtime generation plus actual disk admission across generations.
- New entry/healthy forward require actual current funding HEALTHY. Flat financial PENDING permits protective management and honest operating-health time but blocks new entry/final sample/forward PASS until final evidence exists.
- Preserve current workstation evidence; original target/Ubuntu24/26/cloud/SSH and actual forward samples remain required.

## Review Focus

- Zero or offsetting settled events must remain INCLUDED; source absence must never become ZERO_CONFIRMED (Task1).
- Preflight freshness or config/runtime-generation changes after API read must invalidate admission without stopping protection (Tasks2/4).
- Crash after broker flat but before funding publication must not duplicate exit fills or lose pending financial state (Task3).
- Retention refusal, child timeout and clock reversal must stop entry/healthy time while keeping close/protection available (Tasks2/3).
- A real rate is still a modeled cost basis; old reports/receipts and unobserved-OOS claims cannot be upgraded by relabeling (Tasks4/5/6).

## Conditional approval amendments — binding 2026-10-21

The human conditionally approved all six Tasks, preserved the selected model/numeric policies and expressly authorized continuous implementation after these additions. This section supersedes the previous plan-review-pending state. No per-Task continuation confirmation is required. Financial completeness, risk authority and major architecture changes still require separate review; ordinary defects must be fixed and execution continued.

### P0-1 — pending funding and actual BTC4H opportunities (Tasks1/3/5/6)

- Verify whether the published next-event upper bracket is truly required by the existing completeness contract. Investigate earlier positive source-owned completeness (including actual settled-history/current-state/schedule evidence), distinguish equivalent proof from relaxation. Keep the conservative bracket unless an equivalent path is demonstrated; any lower financial evidence standard remains disabled and separately reviewed.
- Record per-allocation actual wall wait, observed running wait, start/end/maximum/quantiles and reason changes. Account for restart/downtime without inventing observed healthy time. Pending accounting survives successor ownership and finalization.
- Evaluate actual fresh closed-bar E2 intent/exit constraints while entry is blocked, without orders or new authority. Count a **valid blocked opportunity** only when the existing E5 evaluator and every other current entry gate permit it and funding alone prevents entry; record actual signal boundary/hash and reason, once per strategy/run/boundary across retries/restarts. Separately count directional-but-invalid/stale signals; do not call all ticks/trend signals missed trades or calculate invented profit.
- Control Center must show Funding Pending, reason, since/wait, finalized-vs-pending financial samples, latest public source state/observation/coverage/unsupported interval. No pending position disappears behind an aggregate PASS.
- Test actual4h cadence, entry TTL, max4h hold, daily6-entry and single-position limits; quantify source-lag/opportunity impact under a complete simulated clock protocol and later real observed samples, labeling them separately. If material opportunity loss occurs, provide a verifiable improvement recommendation while retaining current restrictions until any necessary financial review.

### P0-2 — durable30day data capacity, not restart evasion (Tasks2/5/6)

- Before long observation, supply explicit48h/30day **request and physical-byte budgets**, measured retained payload/receipt sizes and projected ranges, plus the permitted-protocol worst case. The 5s base cadence is34,560 ticks/48h and518,400 ticks/30days; at two independent5s streams up to69,120/1,036,800 attempts respectively. Count actual requests/pages separately from ticks and account for all preflight/retry/catch-up attempts.
- Inspect and retain existing changed-candle/last-durable-boundary behavior; do not repeatedly download unchanged history. Fetch only required new finalized candle ranges. Deduplicate unchanged funding payloads by immutable content identity while preserving each actual request/response attempt and observation time; funding refresh/history cadence must still satisfy source-health/completeness.
- Implement versioned immutable payload retention and verified sealed archive/segment indexes with uninterrupted cumulative counters across owners/restarts. Preserve all necessary bytes/hashes/lineage; any archived representation must be verified before releasing redundant loose copies. No evidence deletion, counter reset or restart can satisfy a capacity gate.
- Preserve86,400attempt/1GiB active limits and actual host disk/resource admission. Capacity beyond an active segment requires a correctly sealed, indexed and restorable archive with verified total-growth admission; it is not a new empty runtime directory. Define and test combined market/funding/preflight worst-case contention, retained total bytes, index corruption/torn writes, stale writers and crash during sealing/restart.
- Disk pressure, full active volume, unavailable/invalid archive, unknown accounting or unreaped child must produce explicit refusal/blocked-new-entry/unhealthy source. Existing exposure protection/close remains independent. Stop/recovery must retain pending work and evidence.
- Run accelerated **actual local filesystem/CPU/RSS/request-budget** capacity and resource-isolation tests for the declared30day workload and worst-case profile. Report physical measurements separately from projections and real elapsed observation. 48h initial observation requires these capacity/resource gates; it is not formal30day acceptance.

### P1 — actual settlement schedule and publication delay (Tasks1/2/3/5/6)

- First version may retain verified8h capability, but must validate actual published settlement timestamps and coverage; retain raw realizedRate proof and publication observation clocks.
- Settled-but-not-yet-published is PENDING, never zero. Unknown/missing/off-grid/additional interval facts must report explicit UNSUPPORTED/INCOMPLETE reasons, not infer events or apply the wrong period.
- Add reproducible tests with late publication, boundary timing, variable unsupported intervals and no-settlement intervals; include actual public-source readback. No private account or provider mutation.

Final delivery must separately report six-Task status, waiting/opportunity impact,30day capacity/resource tests, real public funding completeness, exact new native package/test evidence and remaining work, and whether ordinary Paper is actually eligible to begin observation. Old target/Ubuntu/cloud/SSH and true time/trade samples remain independent.

### Task 1: E4 registered source and allocation

**Files:** Create `src/execution/public_recorded_funding.py`; test `tests/execution/test_public_recorded_funding.py`. Reuse `execution.funding` identity/flat-lineage conventions, actual `OrderRequest`/`Fill` and existing E5 TradeResult validator. Do not repurpose `ledger_funding.py` or the zero producer.

**Interfaces:** `PublicRecordedFundingModel.observe(pages, *, coverage_start, observed_at) -> ObservedPublicFunding`; pages are immutable raw public request/response facts, with exact shape defined in this E4 module and no caller completeness/PASS/cost. `health(observed, *, now) -> bool` implements the spec's published-grid/freshness predicate. `allocate(parent_plan, final_position, entry_request, entry_fills, *, observed, calculated_at) -> dict` derives signed canonical FundingAllocationEvidence. The model instance must recognize its own validated observations; restart re-verifies retained source.

- [x] Write tests proving actual event allocation: quantity0.001 × fill100000 × rate0.0001 = LONG cost0.01 / SHORT credit-0.01; negative rate reverses; zero-rate event and offsetting events use INCLUDED.
- [x] Add exact opened/closed half-open boundaries, missing upper bracket, zero-with-positive-coverage, caller forged observation, changed source/version, wrong lineage/order/fills, duplicate/partial pages/grid and ambient Decimal precision/rounding tests; input/overflow/underflow/downstream output boundaries refuse rather than round.
- [x] Execute P0-1/P1 completeness analysis and tests; register earlier confirmation only if equivalent authoritative coverage is proved, otherwise keep the existing conservative rule and explicit pending reason.
- [x] Run `python -m unittest discover -s tests/execution -p test_public_recorded_funding.py -v`; record genuine intended missing-feature failure, not a broken fixture/import-only result.
- [x] Implement the exact registered source and isolated arithmetic; no network or store mutation in E4 allocation.
- [x] Re-run new tests plus all `tests/execution` funding/TradeResult regressions; retain RED/GREEN logs and source hashes. Commit only after required whitespace checks.

### Task 2: Independent capture, owner-bound preflight and bounded storage

**Files:** Create `src/application/paper/funding_capture.py` (actual public capture/validation), `funding_feed.py` (owned-child feed and current source health). Modify `src/application/cli.py`, `public_feed.py` (shared aggregate retention), `ordinary_setup.py` (native wiring), `src/application/platform/product_backup.py` and existing backup inventory seams only as needed. Test `tests/application/test_public_paper_funding.py`, `test_public_paper_feed.py`, relevant actual private-files/process/backup tests.

**Interfaces:** `capture_public_funding(root, request, ...) -> dict` only fixed BTC public GET; `observe_funding_capture(root, *, subject, now) -> ObservedPublicFunding` validates raw facts via Task1. `PublicFundingFeed.update(request)`, `.take()`, `.summary()` mirror existing independent feed ownership/cancellation; payload binds config/selection/model/namespace/runtime generation. `current_funding_health(config, selection, runtime_identity, *, now)` is a read-only actual-observation reader for native API admission. No public caller PASS/import or extra database.

- [ ] Write controlled-transport tests for settled vs predicted/blank rates, exact raw/normalized hashes and real request accounting, incomplete pages/timeouts, fresh/stale/future clocks, generation/config selection changes, no requests before explicit selection, idle preflight and combined retention refusal.
- [ ] Run focused new suite; preserve RED. Implement capture using existing transport/private files/scope/owned-child primitives, one bounded immutable source-health observation; cache verified immutable facts so protection does not decode raw history each tick.
- [ ] Prove failure never blocks independent ticker/protection and child cancellation is actually reaped; unknown accounting stays INCOMPLETE instead of zero. Include all captured source/health facts in consistent backup/restore scope without copying operation permission.
- [ ] Implement and measure P0-2 changed-only capture, immutable dedup/archive/segment indexing and cumulative accounting; test limit/disk/crash/restart without evidence deletion or reset. Record48h/30day request/byte budgets before long observation.
- [ ] Re-run public data/feed/backup affected suites, retain sanitized results and commit after reviewable green scope.

### Task 3: Durable flat/funding-pending finalization

**Files:** Modify `src/application/paper/engine.py`, `service.py`, `worker.py`, `scheduler.py` and `orchestrator.py` only where their existing roles require it; create `tests/product/test_paper_recorded_funding.py` and targeted recovery cases alongside existing `test_paper_protection_recovery.py` / `tests/application/test_paper_effect_recovery.py`.

**Interfaces:** service gains a trusted owner-source observation port (not HTTP caller data); engine applies only validated Task1 observations. New internal runtime fields contain captured source commitment and exact flat/fill/exit pending work. Additive `funding_status()` projection exposes pending count/model/coverage; it grants no lifecycle or financial authority. Zero-model states stay compatible without invented defaults for v0.5.

- [ ] Write actual E4/E5/E6 tests: close/fill/flat with missing funding remains durable PENDING, no final TradeResult/sample/new entry; protection/close proceeds despite unavailable source; valid upper bracket publishes one exact funding evidence and TradeResult.
- [ ] Cover crash at each seam and successor recovery from real persisted state, duplicate source/finalization, conflicting capture and stale fences, one original close/fill/TradeResult, partial/unsupported exposure, pending healthy-clock distinction and original policy binding after amendment.
- [ ] Add actual4h source-publication/holding/entry-TTL scenarios and P0-1 durable wait/valid-blocked-opportunity accounting through original E2/E5; no extra order or authority and no invented missed PnL.
- [ ] Run focused tests, observe RED, implement minimum persistence/engine changes through existing journal/effect ports; never hand-write DB rows or bypass E5.
- [ ] Run affected runtime/worker/protection/recovery/retirement/restore tests and E4 regressions; preserve failure attempts and commit green scope.

### Task 4: Versioned ordinary selection and normal PaperStart

**Files:** Modify `src/application/paper/policy.py`, `owners.py`, `release.py`, `ordinary_setup.py`, `release_observation.py` and `src/application/control_api/paper_ports.py` only as required by their existing responsibilities. Test new profile alongside `tests/application/test_ordinary_paper_setup.py`, `test_ordinary_paper_composition.py`, `test_native_paper_release_adapter.py`, `test_native_paper_release_observation.py`, `tests/product/test_api_paper_services.py`.

**Interfaces:** existing parsers recognize exact new schema/model pairing; simulator profile binds registered semantics/implementation. Normal PaperStart retains exact command/revision/candidate/risk/current-native-owner gates and additionally requires current owner-bound source health. Normal configuration alone never starts a run.

- [ ] Write negative tests for missing model, zero-model substitution, stale preflight, wrong config/generation/receipt/store/selection, unsupported schema/model pairing and no local workflow. Preserve v0.2/v0.3/v0.4 behavior.
- [ ] Observe RED, wire Task2 real health read into API start and Task3 entry/first-fill/healthy timing without running qualification/network inside protection.
- [ ] Prove actual authenticated normal command accepts a run only with all owner gates; changed policy invalidates new starts while original exposure keeps original protection.
- [ ] Run existing ordinary/native release security and configuration regressions; commit green scope.

### Task 5: Honest reports, forward assessment and Control Center

**Files:** Modify `src/application/paper/assessment.py`, `src/application/cloud/paper_feedback.py`, add an explicitly versioned new feedback schema alongside `contracts/paper_feedback_v0_2.schema.json`; adjust existing `storage.paper_feedback` and Control Center projection/UI only where they currently validate/display these facts. Discover precise frontend files via `rg --files` before editing; record chosen paths in the ledger. Tests include `tests/product/test_paper_feedback_*.py`, relevant API/browser tests and new recorded-funding tests.

**Interfaces:** new report profile retains existing identity/metrics/authority disclosures and adds explicit model/cost-basis/pending/coverage commitments. Existing v0.2 report bytes and zero-only validator remain supported as their original profile. `assess_forward` refuses pending financial allocation; only published E5/E6 results contribute performance.

- [ ] Write tests proving no pending TradeResult/PnL or forward PASS, new model/cost basis visible, old report accepted unchanged, forged mixed profiles rejected, report failure does not stop protection; browser shows pending versus finalized honestly.
- [ ] Observe RED then implement owner-generated new profile and projections; keep PAPER_ONLY/LIVE NOT_RUN/financial authority NONE and opt-in/redaction behavior.
- [ ] Verify Control Center shows P0-1 Funding Pending/reason/wait/latest source and P1 unsupported schedule state; render closed financial sample distinction and capacity refusal truthfully.
- [ ] Run feedback schema/outbox/bridge/API tests and appropriate frontend/browser regression; commit green scope.

### Task 6: Exact-clean qualification, actual research and bounded observation readiness

**Files:** Register tests through existing `tools/freeze_paper_inventory.py` / `src/application/paper/inventory.py` and fixed artifact; extend existing native verification drivers only with needed real observations. Keep retained evidence under original S09/S12/S16 work packages. Update PROGRESS/HANDOFF and delivery instructions with actual identities.

- [ ] Validate new test membership before execution; all existing mandatory PQR observations remain required. Source tests use controlled public transports separately from real public API calls.
- [ ] Run independent whole-change review and address concrete Critical/Important findings with regression coverage. Commit exact-clean candidate; build native Windows, verify distribution/new install and owning fixed qualification. Do not claim bffc receipt covers it.
- [ ] On fresh owning profile, retain actual public dataset/engineering package lineage, reconcile canonical prior family/trial/holdout history; install selected research policies through official entry, run actual development/robustness/frozen finalist/sealed OOS when independence permits. Preserve REJECTED/BLOCKED; never tune to force CANDIDATE or fabricate unseen OOS.
- [ ] Complete normal enrollment/configuration, model preflight, authenticated PaperStart and actual owner attachment only if real candidate/current exact software/risk/retention gates pass. Validate stop/restart/crash/resource/backup and capacity before observation. Public API calls increment actual counts.
- [ ] Complete actual local accelerated30day capacity/resource-isolation workload, real published funding timestamp/completeness readback and pending-opportunity impact report before long observation; never label accelerated duration as real-time samples.
- [ ] If all conditions pass, begin bounded initial48h real-time observation; final30day/30closed-sample gate remains incomplete until genuinely accumulated. If strategy fails or independence/capacity/target commissioning remains unresolved, report precise result and continue other authorized local Master work.
- [ ] Push bounded original branch, never merge main; retain exact executable/evidence mapping and all external incomplete items. Master remains IN_PROGRESS until original acceptance is actually satisfied.

## Plan self-review and execution record

- Spec sections1–2 map Task1/4; section3 maps Task2/4; section4 maps Task3; section5 maps Tasks4–6; all nine acceptance categories map Tasks1–6 and Review Focus.
- Task2 produces Task1-validated observations consumed by Tasks3/4; Task3 funding-status projection feeds Task5; Task6 requalifies all changed code, not just Task1. Preserve this direction; no E4 dependency on application modules.
- Existing Master execution method is inline local execution on this same branch. Human reviewed the plan and conditionally approved continuous implementation after P0-1/P0-2/P1 additions; these additions are recorded above before product work. No new per-Task approval is needed.
- Plan ledger belongs to this plan under the skill's own workspace; durable summarized status stays in coordination/CODEX and evidence Git history. Do not repeat completed tasks after compaction.
