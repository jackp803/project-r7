# R7 Autonomous Strategy-to-Capital Product — V0.1

Status: PRODUCT OWNER DIRECTION / PM ARCHITECTURE BASELINE
Date: 2026-10-02

## 1. Product goal

Project R7 shall become a usable local-first quantitative product that accepts
versioned strategy packages authored outside the runtime (initially by ChatGPT
Chat mode), consumes them through a cloud-drive data plane, automatically runs
the required deterministic research/validation pipeline, promotes only evidence-
qualified strategies through the allowed lifecycle, operates PAPER and later
approved LIVE execution, persists complete audit truth, and publishes sanitized
results back to the cloud-drive data plane for later human/Chat review.

The end-to-end product flow is:

```text
ChatGPT Chat
  -> Cloud Strategy Inbox
  -> R7 local intake
  -> compatibility/schema validation
  -> historical backtest
  -> independent OOS validation
  -> robustness / walk-forward / Monte Carlo
  -> REJECTED or CANDIDATE
  -> PAPER / forward validation
  -> READY_FOR_APPROVAL
  -> explicit Product Owner deployment approval
  -> LIVE within an approved risk/capital envelope
  -> execution / protection / reconciliation
  -> TradeResult / performance monitoring
  -> sanitized Cloud Results
  -> later ChatGPT research feedback
```

The product target is automated evidence generation, validation, execution and
performance measurement. It must never claim guaranteed profitability.

## 2. Fundamental architecture

R7 uses three distinct planes.

### Code plane — GitHub

GitHub is authoritative for:

- source code;
- schemas/contracts;
- migrations;
- tests;
- architecture/ADR;
- release and implementation evidence.

GitHub is NOT the strategy/data transport and is NOT project compute.

### Data plane — Cloud Drive

Cloud Drive is the exchange surface for immutable or append-only product
artifacts:

- strategy submissions;
- dataset artifacts or dataset references;
- research results;
- candidate reports;
- PAPER reports;
- LIVE sanitized performance reports;
- human-readable reports.

Cloud Drive is not authoritative runtime state and must not host the actively
mutated runtime SQLite database.

### Runtime plane — Local R7

The local R7 installation is authoritative for active runtime state:

- intake ledger;
- strategy Registry;
- research run state;
- operational mode;
- RiskDecision / ApprovedTradePlan;
- orders/fills;
- Position lifecycle;
- protection truth;
- reconciliation state;
- kill-switch state;
- PAPER/LIVE runtime state;
- local audit database.

Cloud synchronization failure must never silently change active trading truth.

## 3. AI boundary

V0.1 has NO embedded AI Researcher and requires no paid LLM API.

Initial strategy authoring flow:

```text
ChatGPT Chat -> StrategyPackage -> Cloud Drive
```

R7 itself performs deterministic computation. Backtest, OOS, robustness,
walk-forward, Monte Carlo, PAPER and trading runtime must not call an LLM.

A future local/remote AI Researcher may be added behind a separate interface,
but is explicitly out of scope for V0.1.

## 4. Cloud transport abstraction

R7 must depend on an application-level `CloudArtifactTransport` abstraction,
not directly on a particular cloud vendor.

V0.1 required adapter:

```text
SyncedFolderCloudTransport
```

It consumes a user-configured local folder synchronized by the user's cloud-drive
client. This avoids a new paid service and avoids binding the product to Google
Drive/OneDrive semantics.

A future native Google Drive adapter may be added without changing Strategy,
Backtest, Validation, Risk or Execution domain code.

## 5. Cloud folder contract

Configured cloud root:

```text
<R7_CLOUD_ROOT>/
  inbox/
    strategies/
  datasets/
  research/
    runs/
    rejected/
  candidates/
  paper/
  live/
  reports/
  archive/
```

No secret or credential may be persisted in this tree.

### Submission layout

Each submission is immutable once complete:

```text
inbox/strategies/<submission_id>/
  strategy.json
  manifest.json
```

`manifest.json` is written last by the producer and is the handoff marker.
It includes the exact payload filenames and SHA-256 hashes. R7 must never ingest
a strategy solely because a directory exists.

Missing files or hash mismatches that are plausibly caused by incomplete cloud
synchronization are classified as `INCOMPLETE_SYNC`, not strategy rejection.
R7 retries on a later scan. A complete stable package with invalid semantics is
`BLOCKED` or `REJECTED` according to the owning domain rule.

Local durable intake identity prevents duplicate execution of the same
submission after restart.

## 6. Strategy Package V0.1

A Strategy Package contains at minimum:

```text
package_schema_version
submission_id
strategy_id
strategy_version
strategy_content_hash
created_at
created_by
research_hypothesis
strategy_definition_file
requested_dataset_profile
requested_validation_profile
requested_robustness_profile
```

The strategy definition itself remains owned by the existing E2/shared-contract
semantics. The package envelope must not duplicate or reinterpret E2 strategy
rules.

Material strategy changes require a new strategy version/content hash. A LIVE
strategy version is never silently edited in place.

## 7. Application layer

Add an application/orchestration layer above E1-E6. It may sequence domain
services but must not duplicate their semantics.

Required application capabilities:

1. `StrategyInboxService`
   - scan configured Cloud Drive inbox;
   - validate manifest/hash;
   - claim idempotently into local intake ledger;
   - submit exact package to E6 Registry/intake boundary.

2. `ResearchOrchestrator`
   - resolve exact dataset;
   - establish E2 compatibility;
   - execute E3 historical replay;
   - execute independent OOS;
   - execute robustness stages;
   - persist every stage result;
   - request only allowed lifecycle transitions.

3. `RobustnessOrchestrator`
   - deterministic parameter-neighborhood checks;
   - walk-forward evaluation;
   - Monte Carlo analysis;
   - no final-OOS leakage into tuning.

4. `PaperOrchestrator`
   - run qualified candidate using current market inputs;
   - E5 remains risk authority;
   - E4/PaperBroker remains execution simulator;
   - E6 persists runtime truth;
   - produce forward/PAPER performance evidence.

5. `DeploymentApprovalService`
   - READY_FOR_APPROVAL does not mean LIVE;
   - durable explicit Product Owner approval binds exact strategy version,
     project revision, provider/account target and risk/capital envelope.

6. `TradingOrchestrator`
   - only starts after exact-role runtime preflight;
   - E2 strategy cannot directly submit;
   - every new exposure requires current E5 approval;
   - E4 owns provider translation/execution;
   - reconciliation/protection/restart stay fail closed.

7. `ResultPublisher`
   - publish sanitized immutable research/PAPER/LIVE result artifacts to
     Cloud Drive;
   - never publish credentials, signatures, raw private-provider payloads,
     account secrets, or runtime database files.

## 8. Research pipeline

A real strategy submission follows:

```text
SUBMITTED
-> INTAKE_VALIDATED
-> DRAFT
-> BACKTESTING
-> OOS_VALIDATING
-> ROBUSTNESS_VALIDATING
-> REJECTED | CANDIDATE
```

Research results must include exact identities for:

- strategy/version/content hash;
- project executable revision;
- dataset ID/hash/range;
- E2 runtime version;
- cost/fee/slippage/funding assumptions;
- validation policy identity;
- robustness policy identity;
- timestamps and result artifact hashes.

No strategy reaches CANDIDATE because a Chat message, filename, static review,
or manually edited PASS field says so.

## 9. OOS / research integrity

The final OOS partition is independent.

Rules:

- parameter search/tuning cannot consume final-OOS performance;
- final OOS must be dataset/hash/range bound;
- failed strategies remain durable and visible;
- parameter variants are separate immutable strategy/research identities;
- high win rate alone is never a promotion criterion;
- fees/slippage/funding remain explicit;
- no look-ahead semantics remain enforced.

## 10. Robustness V0.1

The product must support configurable deterministic robustness profiles.

Minimum capabilities before a strategy can become a product-level CANDIDATE:

- parameter-neighborhood perturbation;
- walk-forward validation;
- Monte Carlo resampling/ordering analysis;
- explicit threshold policy;
- complete result persistence;
- deterministic PASS/FAIL/BLOCKED decision.

The exact statistical thresholds are configuration/policy, not hidden defaults
inside the orchestrator.

## 11. Lifecycle extension

Existing Registry support stops at CANDIDATE. Productization shall extend the
guarded lifecycle, with E7-reviewed evidence gates, to:

```text
DRAFT
-> BACKTESTING
-> REJECTED | CANDIDATE
-> PAPER
-> READY_FOR_APPROVAL
-> APPROVED
-> LIVE
-> DEGRADED
-> RETIRED
```

No generic arbitrary transition API is allowed.

Critical rules:

- CANDIDATE -> PAPER requires accepted research evidence;
- PAPER -> READY_FOR_APPROVAL requires configured forward-test evidence;
- READY_FOR_APPROVAL -> APPROVED requires explicit Product Owner approval;
- APPROVED -> LIVE additionally requires exact runtime/provider/risk readiness;
- DEGRADED/RECONCILIATION_REQUIRED blocks new exposure;
- approval of one exact strategy version does not transfer to another version.

## 12. PAPER product behavior

PAPER shall be a continuous product runtime, not only unit tests.

It must:

- consume current market data;
- evaluate the exact selected strategy;
- run E5 Risk;
- execute through PaperBroker;
- persist fills/position/protection/funding/trade result;
- survive restart;
- produce performance metrics;
- compare realized forward behavior to research expectations;
- stop or degrade on fail-closed conditions.

Configurable PAPER promotion policy may use duration, minimum trade count,
drawdown, expectancy/profit factor, execution-health and reconciliation criteria.

## 13. LIVE product behavior

The implementation may build all LIVE-capable code and simulation/test surfaces
credential-free.

Real provider activation remains separately gated.

Before real capital:

- exact project revision and package are known;
- provider read-only verification is current;
- account/position/order/fill/protection truth is reconciled;
- exact risk policy/capital envelope is approved;
- kill switches are current;
- runtime preflight is eligible;
- Product Owner approval is explicit and durable.

Once approved, individual trades may execute automatically inside that exact
envelope. Product Owner approval is deployment authority, not per-trade manual
approval.

No code path may interpret credentials as authorization.

## 14. Control Center

The final product must have a user-facing Control Center.

Minimum screens:

### Overview
- current operational mode;
- currently deployed strategy/version;
- research/PAPER/LIVE status;
- current position summary;
- Risk/Broker/DB/reconciliation health;
- actionable alerts.

### Research
- submissions;
- current stage/progress;
- dataset;
- backtest/OOS/robustness results;
- explicit reject/block reason.

### Strategies
- version history;
- lifecycle;
- train vs OOS metrics;
- drawdown/profit factor/trade count;
- research artifacts.

### Trading
- PAPER/LIVE runtime status;
- current position;
- entry/fill/protection;
- PnL;
- recent trades;
- E5 rejection reasons.

### System Health
- market/data health;
- Strategy Runtime;
- Risk;
- broker/provider;
- persistence;
- reconciliation;
- runtime revision/mode/heartbeat;
- plain-language summary with technical details expandable.

The user should not need Git, PowerShell or raw JSON for normal operation.

## 15. Product packaging

Target end-user behavior:

```text
launch R7
-> Control Center opens
-> local database/config are initialized or recovered
-> cloud inbox is scanned
-> research/runtime services operate under configured mode
```

Windows is the primary V0.1 target.

A final packaged release may use an installer or packaged executable. Exact UI
packaging technology is an implementation choice only if it preserves this
architecture.

## 16. Product usability acceptance

R7 V0.1 is not considered a usable product until an approved-local acceptance
run demonstrates, on one exact revision:

1. clean install/start;
2. configured Cloud Drive root;
3. ingest one valid Strategy Package;
4. reject one malformed/incompatible package safely;
5. run a real deterministic backtest;
6. run independent OOS;
7. run robustness/walk-forward/Monte Carlo;
8. produce REJECTED and CANDIDATE outcomes correctly;
9. run a CANDIDATE through continuous PAPER;
10. persist/recover after restart;
11. publish sanitized results back to Cloud Drive;
12. show the run in Control Center;
13. exercise alerts/fail-closed behavior;
14. prove no GitHub compute and no paid LLM API;
15. prove credentials are not persisted to Git/Cloud artifacts.

Real-money activation is a later acceptance layer requiring separate provider
and capital authority.

## 17. Implementation program

### P0 — Architecture / product contract
This document + scoped Product Owner Codex authorization.

### P1 — Cloud Strategy Intake + application skeleton
Deliver CloudArtifactTransport, synced-folder adapter, Strategy Package manifest
validation, durable intake ledger, application service skeleton and result
artifact conventions.

### P2 — Automated Research Pipeline
Deliver DatasetResolver + ResearchOrchestrator using existing E1/E2/E3/E6
boundaries from StrategyPackage through REJECTED/CANDIDATE.

### P3 — Robustness Pipeline
Deliver parameter-neighborhood, walk-forward and Monte Carlo framework and
evidence gate.

### P4 — Continuous PAPER + lifecycle extension
Deliver CANDIDATE -> PAPER -> READY_FOR_APPROVAL with continuous Paper runtime,
durability, restart and performance reports.

### P5 — Control Center
Deliver local UI/API for Overview, Research, Strategies, Trading, Health plus
safe controls for research/PAPER.

### P6 — Windows product packaging
Deliver reproducible application launch/packaging, config/data directories,
startup/recovery and product-level acceptance harness.

### P7 — LIVE-capable integration
Complete provider/runtime integration code and credential-free tests. Real
provider read-only verification and capital activation require separate Product
Owner authority and cannot be inferred from implementation completion.

### P8 — Cloud result feedback
Publish structured sanitized research/PAPER/LIVE result artifacts suitable for
later ChatGPT review and next-version strategy authoring.

## 18. Codex implementation rule

For this productization program, Codex may be the primary implementation agent
under the separately recorded Product Owner authorization.

Codex must:

- read latest main and this product spec before every phase;
- preserve E1-E7 ownership semantics and shared contracts;
- prefer additive adapters/orchestration over rewriting validated domain logic;
- commit each phase separately;
- execute all project tests locally, never through GitHub compute;
- keep exact revision/evidence for every qualification;
- stop on architecture/contract ambiguity instead of inventing authority;
- never request/store provider secrets in Git or cloud artifacts;
- never start real provider/capital work without separate fresh authority.

PM/E7 remain architecture, contract and acceptance authorities.
