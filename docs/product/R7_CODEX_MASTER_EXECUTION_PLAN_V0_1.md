# R7 Codex Master Execution Plan — V0.1

Status: PM EXECUTION AUTHORITY
Date: 2026-10-02
Architecture: `docs/product/R7_MASTER_PRODUCT_ARCHITECTURE_V0_1.md`

## 1. Execution model

Codex is the primary implementation agent for this program.

Unlike the earlier single-phase P1 task, this master program is continuous.

Codex shall:

```text
read latest main
-> create one bounded productization branch
-> implement M1
-> locally verify M1
-> persist checkpoint evidence
-> implement M2 on same branch
-> locally verify M1+M2
-> ...
-> implement through M10
-> run M11 full product acceptance
-> persist final evidence
-> push final branch
-> stop for PM final review
```

Codex does not wait for PM between milestones when the milestone gate is PASS.

Codex must stop only when one of the explicit stop conditions in this plan is
met.

---

## 2. Branch and history

Recommended branch:

```text
codex/r7-productization-master-20261002
```

Requirements:

- branch from latest authoritative main at task start;
- no force push;
- no destructive rebase after evidence exists;
- one or more commits per milestone;
- milestone completion commit must contain no uncommitted product changes;
- evidence/docs commits after an executable checkpoint must not rebind the
  executable revision;
- final branch may be long-lived until M11 completes.

Each milestone records:

```text
milestone
base revision
executable revision
evidence revision
changed files
local commands
test counts
failures/errors/skips
security scan
exact-clean proof
next milestone decision
```

---

## 3. General implementation rules

### 3.1 Use existing domains

Before writing code for a capability, search existing E1-E6 implementation.

Prefer:

```text
adapter
facade
application service
orchestrator
```

over duplicate domain code.

### 3.2 Fix deterministic defects

If local tests reveal a bounded implementation bug compatible with accepted
architecture:

- reproduce;
- add/strengthen regression;
- fix;
- rerun;
- continue.

Do not stop merely because tests fail.

### 3.3 Architecture changes

Stop if the fix requires:

- changing shared object meaning;
- weakening an E5/E6/E7 safety rule;
- changing legal lifecycle vocabulary;
- granting a new authority;
- inventing provider semantics not present in accepted docs;
- changing final-OOS research-integrity rules.

Persist a blocker with exact evidence.

### 3.4 Local-only compute

All:

- tests;
- backtests;
- robustness;
- walk-forward;
- Monte Carlo;
- packaging builds;
- acceptance runs

are local Windows work.

No GitHub Actions or GitHub-triggered compute.

### 3.5 No LLM runtime dependency

Project tests must prove:

```text
OpenAI API calls = 0
Gemini API calls = 0
Claude API calls = 0
local LLM calls = 0
```

for normal R7 product operation.

---

# M1 — Cloud Intake + Application Core

## Goal

A Chat-authored Strategy Package can arrive through a configured synced Cloud
Drive folder and be safely registered as DRAFT locally.

## Deliver

- `src/application/` base;
- product config;
- `CloudArtifactTransport`;
- `SyncedFolderCloudTransport`;
- Strategy Package V0.1 manifest parser;
- safe path/hash validation;
- durable SQLite intake ledger;
- `StrategyInboxService`;
- E2 StrategyDefinition parse/validation;
- real E6 intake;
- idempotent receipt publishing;
- one-shot product/application command/API callable.

## Required tests

- valid package;
- missing artifact -> INCOMPLETE_SYNC;
- transient hash mismatch -> INCOMPLETE_SYNC;
- invalid hash format;
- duplicate JSON key;
- absolute/traversal path;
- secret-like field;
- duplicate package idempotence;
- conflicting same submission ID;
- restart dedupe;
- invalid E2 strategy -> BLOCKED;
- valid E6 DRAFT intake;
- no fabricated compatibility PASS;
- receipt atomic/idempotent;
- local/cloud roots separated.

## M1 gate

```text
M1 = PASS
```

only when focused application + directly affected E2/E6/storage regressions pass
locally.

---

# M2 — Dataset Resolver + Automated Research Orchestrator

## Goal

A DRAFT strategy automatically reaches a deterministic real
BACKTESTING/OOS result using existing E1/E2/E3 semantics.

## Deliver

- DatasetProfile V0.1;
- dataset catalog/manifest;
- local dataset cache;
- DatasetResolver;
- immutable split-plan model;
- ResearchPolicy V0.1;
- ResearchRun persistence;
- research-stage attempt history;
- real E2 compatibility execution adapter;
- `ResearchOrchestrator`;
- actual E3 replay invocation;
- BacktestResult persistence into E6;
- OOS ValidationDecision persistence into E6;
- durable stage recovery.

## Research rules

- final OOS locked before tuning;
- exact dataset hashes;
- explicit costs;
- actual E2 runtime;
- no look-ahead;
- no manual PASS flags;
- failed runs remain queryable.

## Required product fixture

One synthetic-but-real-execution research fixture must:

```text
Cloud package
-> DRAFT
-> BACKTESTING
-> BacktestResult
-> ValidationDecision
```

without CANDIDATE yet if robustness is not complete.

## M2 gate

All M1 tests remain green plus new dataset/research/E3 integration tests.

---

# M3 — Robustness Engine

## Goal

Product-level CANDIDATE promotion requires robustness evidence, not only one
backtest/OOS outcome.

## Deliver

- RobustnessPolicy V0.1;
- deterministic parameter-neighborhood generator;
- walk-forward window planner/executor;
- Monte Carlo engine with explicit seed;
- cost/slippage stress profiles;
- RobustnessResult / RobustnessDecision application evidence;
- persisted raw/summary artifacts;
- result publishing.

## Required tests

- neighborhood deterministic;
- baseline included/excluded by policy explicitly;
- invalid parameter combinations recorded, not hidden;
- walk-forward no future leakage;
- final OOS never used for tuning;
- same seed -> same Monte Carlo output;
- changed seed changes stochastic sample identity;
- threshold PASS/FAIL ordering deterministic;
- stress failures retained.

## M3 gate

Known PASS fixture and known FAIL fixture both resolve correctly.

---

# M4 — Research Decision + Full Lifecycle Materialization

## Goal

Extend E6 implementation to the full lifecycle already defined in
`contracts-v0.1` without changing that contract.

## Deliver

Named guarded service methods for:

```text
CANDIDATE -> PAPER
PAPER -> READY_FOR_APPROVAL
READY_FOR_APPROVAL -> APPROVED
APPROVED -> LIVE
LIVE -> DEGRADED
LIVE -> RETIRED
DEGRADED -> LIVE
DEGRADED -> RETIRED
CANDIDATE/PAPER/READY_FOR_APPROVAL -> REJECTED/RETIRED where contract allows
```

Do not add arbitrary public transition API.

Integrate RobustnessDecision into product-level BACKTESTING -> CANDIDATE gate.

If existing E6 CANDIDATE method cannot accept robustness evidence without a
bounded additive API, add an application/evidence gate preserving the shared
contract and existing legacy tests.

## Required tests

Every legal edge and every relevant illegal skip.

At minimum:

- BACKTESTING cannot jump LIVE;
- CANDIDATE without robustness cannot PAPER;
- PAPER cannot self-approve;
- READY cannot self-approve;
- APPROVED without current runtime prerequisites cannot LIVE;
- DEGRADED cannot auto-resume;
- exact version binding.

---

# M5 — Continuous PAPER Runtime

## Goal

A CANDIDATE can run continuously in PAPER using the real strategy/risk/execution
composition and produce forward evidence.

## Deliver

- PaperPromotionPolicy;
- PaperRun model/persistence;
- scheduler/timeframe boundary service;
- current-data adapter;
- E2 evaluation;
- TradeIntent;
- E5 risk gate;
- E4 PaperBroker execution;
- position/protection lifecycle;
- E6 paper journal;
- funding/trade result;
- runtime heartbeat;
- clean stop;
- restart/recovery;
- PAPER report/publisher;
- PAPER -> READY_FOR_APPROVAL decision.

## Required scenarios

- no signal;
- risk reject;
- approved entry;
- partial fill;
- protection success;
- protection failure;
- normal exit;
- emergency exit;
- restart flat;
- restart open protected;
- restart open unprotected;
- ambiguous/reconciliation-required;
- duplicate scheduler event;
- stale market;
- PAPER policy fail;
- PAPER policy pass.

## M5 gate

An acceptance fixture must complete at least one full paper lifecycle:

```text
flat -> entry -> protected -> exit -> flat -> TradeResult
```

and restart safely.

---

# M6 — Control API

## Goal

Expose the product through a local typed API without allowing UI bypass.

## Deliver

Recommended:

```text
FastAPI
localhost only by default
/api/v1
```

Families:

- overview;
- research;
- strategies;
- paper;
- trading;
- health;
- alerts;
- settings;
- approvals.

API command endpoints call application services.

No direct raw SQLite mutation endpoints.

## Required tests

- DTO validation;
- lifecycle forbidden action returns fail-closed result;
- PAPER start requires CANDIDATE;
- approval endpoint creates immutable ApprovalRecord;
- LIVE endpoint remains unavailable/blocked without authority;
- secret values never returned.

---

# M7 — Control Center

## Goal

Normal user operation no longer requires Git/PowerShell/raw JSON.

## Technology target

```text
React
TypeScript
Vite
static bundle served locally
```

Codex may use another open-source frontend library only if the architecture and
packaging are simpler and tests remain reproducible.

## Required screens

### Overview
- mode;
- active strategy;
- research status;
- PAPER/LIVE;
- position;
- health;
- alerts.

### Research
- inbox submissions;
- stage progress;
- dataset;
- backtest/OOS/robustness;
- reason codes.

### Strategies
- families/versions;
- lifecycle;
- metrics;
- evidence.

### Trading
- PAPER/LIVE state;
- signal;
- risk decision;
- position;
- fill/protection;
- PnL;
- TradeResult.

### Health
- plain-language health;
- technical details expandable.

### Settings
- local/cloud paths;
- non-secret policies/config.

## UI safety

- disabled control is not backend security;
- backend remains authoritative;
- no UI state can promote lifecycle by itself.

## M7 gate

Browser-level local acceptance demonstrates navigation and live API state.

If browser automation is unavailable locally, persist exact manual smoke steps
and implement backend/API tests; do not use hosted browser CI.

---

# M8 — Windows Packaging + First-Run

## Goal

End user launches the product without setting PYTHONPATH or running development
commands.

## Deliver

- frontend production build;
- packaged Python/backend/runtime;
- Windows launcher;
- first-run config wizard or first-run page;
- directory initialization;
- DB migration;
- backend process management;
- browser launch to Control Center;
- clean shutdown;
- application version display;
- local logs location.

Evaluate PyInstaller and Nuitka locally; choose one based on actual reproducible
build/start evidence.

## Acceptance

On a clean-ish local test directory/profile:

```text
launch product
-> choose local root
-> choose cloud root
-> initialize
-> Control Center opens
-> scan inbox works
-> close
-> relaunch
-> state persists
```

End user must not manually install Node for packaged execution.

---

# M9 — LIVE-Capable Integration (Credential-Free)

## Goal

Complete all code needed for eventual real provider deployment without consuming
provider credentials or capital.

## Deliver

- DeploymentEnvelope;
- ApprovalRecord UI/API flow;
- exact strategy/project/config binding;
- TradingOrchestrator;
- runtime-preflight composition;
- E4 live provider execution port/adapters as already architected;
- provider capability gating;
- reconciliation;
- protection readback;
- degrade/lock behavior;
- sanitized LIVE reporting;
- secure-credential interface abstraction;
- fake/simulated provider for local tests.

Do NOT:

- read real credentials;
- call private provider endpoints;
- submit real orders;
- expose capital.

## Required local simulation matrix

At minimum cover the accepted LF/failure-prevention cases plus:

- approval missing;
- approval wrong version;
- stale approval/config;
- runtime revision mismatch;
- mode mismatch;
- heartbeat stale;
- provider read unhealthy;
- position mismatch;
- ACK pending vs fill;
- ambiguous submit;
- partial fill;
- missing/duplicate/orphan protection;
- exit with residual;
- restart;
- kill switch;
- daily-loss lock;
- successful bounded simulated lifecycle.

---

# M10 — Cloud Results + Chat Feedback Surface

## Goal

Everything Chat needs for later strategy iteration exists as sanitized structured
artifacts in Cloud Drive.

## Deliver

- research artifact manifests;
- rejected archive;
- candidate evidence index;
- PAPER reports;
- LIVE sanitized performance snapshots;
- human-readable HTML report;
- compact Chat-facing summary JSON.

### Chat-facing summary

Minimum:

```text
strategy identity/version/hash
research decision
train metrics
OOS metrics
robustness metrics
PAPER metrics when available
LIVE metrics when available
regime/time breakdown when available
top failure/degradation reason codes
artifact references
generated_at
```

No secrets/provider raw payloads.

---

# M11 — Full Product Acceptance

## Goal

Prove one exact branch/revision behaves as a usable R7 product through PAPER and
is LIVE-capable without real activation.

## Scenario A — valid strategy

```text
create cloud submission
-> R7 discovers
-> DRAFT
-> research
-> OOS
-> robustness
-> CANDIDATE
-> PAPER
-> full paper lifecycle
-> READY_FOR_APPROVAL
-> report published
-> UI shows exact state
```

Use a deterministic fixture whose expected outcome is known.

## Scenario B — rejected strategy

```text
submission
-> research failure
-> REJECTED
-> reason retained
-> report published
```

## Scenario C — malformed strategy

```text
submission
-> BLOCKED
-> no research execution
```

## Scenario D — partial cloud synchronization

```text
manifest/bytes incomplete
-> INCOMPLETE_SYNC
-> later complete
-> one execution only
```

## Scenario E — restart

Restart during:

- intake;
- research stage boundary;
- PAPER flat;
- PAPER open/protected.

No duplicate or false-green state.

## Scenario F — UI/package

Packaged launcher starts, recovers state and displays all prior runs.

## Scenario G — LIVE-capable fail closed

Simulated provider path proves real activation is blocked without:

- current approval;
- runtime/provider authority;
- credential provider;
- reconciliation;
- valid mode/preflight.

## Final test matrix

Run all project credential-free tests plus new application/product/acceptance
suites.

No skipped critical acceptance scenario.

---

## 4. Checkpoint evidence format

For each milestone M1-M10 create:

```text
status/codex/productization/M<NN>_COMPLETION_20261002.md
```

and machine-readable JSON when useful.

Each completion includes:

- result;
- exact executable revision;
- base;
- diff classification;
- commands;
- test totals;
- focused tests;
- full regressions;
- exact-clean before/after;
- provider requests;
- LLM calls;
- credentials;
- capital;
- GitHub compute;
- defects fixed;
- known limitations;
- next milestone.

Final:

```text
status/codex/R7_PRODUCTIZATION_MASTER_COMPLETION_20261002.md
```

---

## 5. Self-advance rules

Codex SHALL automatically advance to the next milestone when:

```text
current milestone required implementation complete
AND focused tests PASS
AND relevant regressions PASS
AND no P0/P1 known correctness/security defect
AND no architecture stop condition
AND no external authority required for next implementation work
```

Do not wait for a chat wake message.

Codex MAY implement later credential-free code even when actual provider
activation is not authorized.

---

## 6. Stop conditions

Codex must stop with `BLOCKED` only for a genuine condition:

### ARCHITECTURE_REVIEW_REQUIRED
A shared semantic/authority change not already decided by architecture docs.

### LOCAL_CAPABILITY_UNAVAILABLE
A required build/test capability cannot run on approved local infrastructure.

### EXTERNAL_DEPENDENCY_REQUIRED
A required non-repository dependency cannot be obtained/configured without user
action.

### PROVIDER_AUTHORITY_REQUIRED
Only when real provider facts are actually required. Credential-free
implementation/tests must continue before this point.

### CREDENTIAL_OR_CAPITAL_REQUIRED
Never infer or request automatically.

### SECURITY_INCIDENT
Potential real secret committed/exposed.

Do not stop for:

- ordinary failing test;
- import error;
- missing internal module;
- deterministic implementation bug;
- packaging bug;
- UI bug;
- migration bug;
- fixture inconsistency.

Fix those and continue.

---

## 7. Scope freedom

Within the architecture, Codex may:

- create new application/product modules;
- add open-source dependencies required by the selected product stack;
- add migrations;
- add UI;
- add packaging scripts;
- refactor internal implementation;
- fix bounded existing defects exposed by the new product tests;
- add docs/tests/evidence.

Codex must not:

- silently redefine shared contracts;
- weaken safety gates;
- replace E1-E6 with parallel semantics;
- introduce a paid runtime service;
- add GitHub CI;
- add embedded LLM dependency;
- hard-code user secrets/paths;
- activate real capital.

---

## 8. Final delivery

At completion, Codex returns:

```text
MASTER_RESULT = PASS | BLOCKED
branch
final branch HEAD
final qualified executable revision
milestone results M1-M11
full local test totals
packaged product path/name (local evidence only)
known limitations
provider/credential/capital status
GitHub compute status
```

If PASS, the branch is ready for PM final static review and Product Owner
hands-on product acceptance.

Real-money provider activation remains a separate final operational gate.
