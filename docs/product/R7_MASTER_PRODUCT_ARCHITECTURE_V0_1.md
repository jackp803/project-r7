# R7 Master Product Architecture — V0.1

Status: PRODUCT OWNER DIRECTION / PM ARCHITECTURE BASELINE
Date: 2026-10-02
Repository: jackp803/project-r7

## 0. Purpose

This document is the architecture authority for completing Project R7 as one
usable end-to-end product.

The product goal is:

```text
Chat-authored Strategy Package
-> Cloud Drive
-> local R7 intake
-> deterministic research
-> independent validation
-> robustness
-> CANDIDATE
-> continuous PAPER
-> READY_FOR_APPROVAL
-> Product Owner approval
-> LIVE-capable runtime
-> real execution only when separately authorized
-> performance feedback
-> Cloud Drive results
-> later Chat research
```

R7 must be useful without any embedded LLM. The runtime product performs
deterministic quantitative computation and trading orchestration. ChatGPT Chat is
an external strategy author/research surface, not a runtime dependency.

No component may claim guaranteed profitability.

---

## 1. Architectural principles

### 1.1 Preserve existing domain ownership

R7 already has accepted domain boundaries. Productization composes them; it does
not replace them.

```text
E1  Market Data / market truth
E2  StrategyDefinition / Strategy Runtime / Signal / TradeIntent semantics
E3  Historical replay / BacktestResult / validation / research statistics
E4  Broker / execution / provider translation / actual execution truth
E5  Risk / approval veto / position lifecycle interpretation / protection policy
E6  Registry / persistence / operational state / platform projections
E7  Shared contracts / architecture / integration / release semantics
```

The application layer may sequence calls across domains, but it must not
privately reimplement their meanings.

### 1.2 Three-plane architecture

```text
+--------------------------------------------------------------+
| CODE PLANE — GitHub                                          |
| source / contracts / schemas / migrations / tests / docs     |
+--------------------------------------------------------------+

+--------------------------------------------------------------+
| DATA PLANE — Cloud Drive                                     |
| strategy packages / datasets / reports / immutable results   |
+--------------------------------------------------------------+

+--------------------------------------------------------------+
| RUNTIME PLANE — local R7                                     |
| SQLite / orchestration / runtime / risk / execution / state  |
+--------------------------------------------------------------+
```

GitHub is not the strategy-data bus and is not compute.

Cloud Drive is not authoritative active trading state.

The local R7 runtime database is not stored inside the cloud-synchronized tree.

### 1.3 Fail closed

Unknown, stale, contradictory, incomplete or unreconciled state never becomes
permission for new exposure.

A product-level orchestration convenience must not weaken an existing domain
fail-closed rule.

### 1.4 Immutable strategy versions

A materially changed strategy is a new `strategy_version` and content hash.

A deployed version is never silently edited in place.

### 1.5 Explicit policy generations

Research, validation, robustness, PAPER promotion, risk and deployment limits
must be versioned policy/config objects.

No hidden "reasonable default" may silently decide promotion to capital.

---

## 2. Final product topology

```text
                         ChatGPT Chat
                              |
                              | StrategyPackage
                              v
                    +---------------------+
                    |     Cloud Drive     |
                    | Strategy Inbox      |
                    | Results / Reports   |
                    +----------+----------+
                               |
                               | CloudArtifactTransport
                               v
+-----------------------------------------------------------------------+
|                         R7 LOCAL PRODUCT                               |
|                                                                       |
|  +--------------------- Application Layer --------------------------+ |
|  | StrategyInboxService                                             | |
|  | ResearchOrchestrator                                             | |
|  | RobustnessOrchestrator                                           | |
|  | PaperOrchestrator                                                | |
|  | DeploymentApprovalService                                        | |
|  | TradingOrchestrator                                              | |
|  | ResultPublisher                                                  | |
|  | ProductHealthService                                             | |
|  | Control API                                                      | |
|  +---------------------------+--------------------------------------+ |
|                              |                                        |
|       +----------------------+------+----------------------+           |
|       |             |             |          |           |           |
|       v             v             v          v           v           |
|      E1            E2            E3         E5          E4           |
|  Market Data     Strategy      Research     Risk      Broker/Exec     |
|       |             |             |          |           |           |
|       +-------------+-------------+----------+-----------+           |
|                              |                                        |
|                              v                                        |
|                             E6                                        |
|                Registry / SQLite / Runtime State                      |
|                                                                       |
|  +-------------------- Control Center UI --------------------------+ |
|  | Overview | Research | Strategies | Trading | Health | Settings  | |
|  +-----------------------------------------------------------------+ |
+--------------------------------+--------------------------------------+
                                 |
                                 | only when separately authorized
                                 v
                               OKX
```

---

## 3. Repository product layout

Codex may refine filenames, but product boundaries must remain recognizable.

Target structure:

```text
src/
  application/
    config.py
    models.py
    clock.py
    errors.py

    cloud/
      protocol.py
      synced_folder.py
      package_manifest.py
      publisher.py

    intake/
      service.py
      ledger.py

    datasets/
      resolver.py
      catalog.py

    research/
      orchestrator.py
      policy.py
      result.py

    robustness/
      orchestrator.py
      parameter_neighborhood.py
      walk_forward.py
      monte_carlo.py
      policy.py

    paper/
      orchestrator.py
      policy.py
      scheduler.py

    deployment/
      approvals.py
      policy.py

    trading/
      orchestrator.py

    health/
      service.py

    control_api/
      app.py
      dto.py

  ...existing E1-E6 packages remain domain-owned...

ui/
  package.json
  src/
    pages/
      Overview
      Research
      Strategies
      Trading
      Health
      Settings
    components/
    api/

packaging/
  windows/
  launch/

tests/
  application/
  product/
  acceptance/
```

Application code imports domain code. Domain code must not import the UI.

The UI talks to the Control API, not directly to SQLite or domain modules.

---

## 4. Configuration model

R7 has one product configuration root independent from strategy semantics.

Minimum configuration:

```text
product_instance_id
local_data_root
cloud_root
database_path
operational_mode
scan_interval
research_worker_count
paper_runtime_enabled
control_api_host
control_api_port
log_level
```

Sensitive provider credentials are never stored in the ordinary product config.

Configuration precedence must be deterministic and documented.

A first-run wizard may write non-secret configuration.

### 4.1 Directories

Example only:

```text
<R7_LOCAL_ROOT>/
  db/
    r7.db
  cache/
  datasets/
  work/
  logs/
  reports/
  config/

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

The user may choose actual paths.

---

## 5. Cloud artifact transport

### 5.1 Protocol

Define a provider-neutral application protocol:

```text
CloudArtifactTransport

initialize()
list_strategy_submissions()
read_artifact()
write_artifact_atomic()
artifact_exists()
archive_submission()
```

The protocol deals in logical artifact paths and bytes/streams.

It must not expose provider authentication or trading concerns to research code.

### 5.2 V0.1 adapter

Required:

```text
SyncedFolderCloudTransport
```

This adapter uses a local filesystem directory synchronized by the user's
existing cloud-drive client.

Benefits:

- no new paid cloud service;
- no runtime dependency on a cloud-vendor SDK;
- no vendor credential handling in R7;
- works with Google Drive, OneDrive or another mounted/synced drive.

### 5.3 Native cloud adapter

Optional later:

```text
GoogleDriveCloudTransport
```

It must implement the same application protocol and must not force changes to
E1-E6 or research semantics.

---

## 6. Strategy Package protocol

### 6.1 Submission directory

```text
inbox/strategies/<submission_id>/
  strategy.json
  manifest.json
```

The producer writes `manifest.json` last.

Manifest presence means "producer claims package complete", but R7 still verifies
all declared bytes/hashes.

### 6.2 Manifest V0.1

Minimum fields:

```json
{
  "package_schema_version": "r7-strategy-package-v0.1",
  "submission_id": "...",
  "strategy_id": "...",
  "strategy_version": "...",
  "strategy_content_hash": "sha256:...",
  "created_at": "...Z",
  "created_by": "chat",
  "research_hypothesis": "...",
  "strategy_definition_file": "strategy.json",
  "strategy_definition_sha256": "sha256:...",
  "requested_dataset_profile": "...",
  "requested_validation_profile": "...",
  "requested_robustness_profile": "..."
}
```

### 6.3 Security

Reject:

- absolute paths;
- `..` traversal;
- alternate separators escaping package root;
- unexpected executable files;
- symlink traversal when filesystem adapter is used;
- credential/secret-like fields;
- malformed JSON / duplicate JSON keys;
- conflicting immutable submission identity.

### 6.4 Cloud synchronization semantics

Cloud synchronization is eventually consistent.

Therefore:

```text
manifest exists + referenced file temporarily missing
-> INCOMPLETE_SYNC

manifest exists + referenced file transient hash mismatch
-> INCOMPLETE_SYNC
```

R7 retries later.

A stable complete package with invalid strategy semantics is different:

```text
complete package + invalid StrategyDefinition
-> BLOCKED
```

No cloud transport race should permanently reject an otherwise valid strategy.

---

## 7. Local intake ledger

The intake ledger is local SQLite state.

Suggested table:

```text
application_strategy_submissions
- submission_id PK
- manifest_hash
- strategy_id
- strategy_version
- strategy_content_hash
- discovered_at
- last_observed_at
- state
- attempt_count
- claimed_at
- completed_at
- registry_identity
- reason_codes_json
- published_receipt_hash
```

States:

```text
DISCOVERED
INCOMPLETE_SYNC
CLAIMED
INTAKE_ACCEPTED
BLOCKED
PUBLISHED
ARCHIVED
```

Rules:

- same submission + same immutable bytes is idempotent;
- restart does not duplicate execution;
- same submission ID + changed immutable material = CONFLICT / fail closed;
- database is outside Cloud Drive;
- claim and durable state update are transactional.

---

## 8. Strategy intake

For a complete package:

```text
Package envelope validation
-> E2 parse_strategy_definition
-> exact strategy content/hash check
-> E6 StrategyPlatformService.intake
-> DRAFT
```

The product may create real E2 compatibility evidence only through an executed
accepted E2 compatibility adapter/process.

No application code may fabricate:

```text
status = PASS
verification_kind = LOCAL_EXECUTION
```

just to advance lifecycle.

---

## 9. Dataset architecture

### 9.1 Dataset artifact

Dataset identity must remain reproducible:

```text
dataset_id
dataset_hash
symbol
timeframe
start
end
source
normalization_version
row_count
created_at
```

Tabular market data should use Parquet or another deterministic columnar format
where practical; metadata remains JSON.

### 9.2 Dataset catalog

The application DatasetResolver maps a requested dataset profile to exact E1-
compatible data.

It must resolve one immutable dataset identity before a research run begins.

### 9.3 Split plan

Before optimization/tuning, persist a split plan:

```text
training
validation/tuning
final OOS
```

Final OOS identity/range/hash is locked before parameter tuning.

The orchestrator must not expose final-OOS performance to parameter selection.

---

## 10. Research run model

Suggested local application record:

```text
ResearchRun
- research_run_id
- submission_id
- strategy_id/version/hash
- project_revision
- dataset_id/hash
- split_plan_id
- research_policy_id
- validation_policy_id
- robustness_policy_id
- state
- started_at
- finished_at
- result
- reason_codes
```

Research stages:

```text
QUEUED
DATASET_RESOLVED
COMPATIBILITY_VERIFIED
BACKTESTING
OOS_VALIDATING
ROBUSTNESS_VALIDATING
DECIDING
PASS
FAIL
BLOCKED
```

Every stage is restartable/idempotent from durable evidence.

---

## 11. Automated research orchestration

### 11.1 ResearchOrchestrator

Required sequence:

```text
DRAFT
-> resolve dataset
-> establish E2 LOCAL_EXECUTION compatibility evidence
-> DRAFT -> BACKTESTING
-> run historical replay
-> persist BacktestResult
-> run independent OOS
-> persist ValidationDecision
-> run robustness gate
-> final research decision
-> BACKTESTING -> REJECTED | CANDIDATE
```

The orchestrator only requests lifecycle transitions. E6 validates authority.

### 11.2 Backtest execution

Must use:

- canonical E1 Candle semantics;
- actual E2 StrategyRuntime;
- existing E3 replay semantics;
- explicit fee/slippage/funding assumptions;
- next-boundary fill rules;
- no look-ahead.

### 11.3 Policy result

A BacktestResult payload may contain favorable numbers, but product promotion
depends on accepted evidence metadata and policy, not on UI interpretation.

---

## 12. Robustness architecture

Robustness is a first-class deterministic stage.

### 12.1 RobustnessPolicy

Versioned minimum fields:

```text
policy_version
parameter_neighborhood_spec
walk_forward_spec
monte_carlo_spec
minimum_pass_fraction
maximum_degradation
maximum_drawdown_threshold
minimum_trade_count
minimum_profit_factor_or_none
stress_cost_profiles
```

Financial values use decimal semantics.

### 12.2 Parameter neighborhood

The baseline strategy is not trusted if only one exact parameter vector works.

The framework generates deterministic nearby parameter variants according to an
explicit neighborhood spec.

It records all tested variants, including failures.

### 12.3 Walk forward

Walk-forward definitions include immutable ordered windows:

```text
train_start/end
evaluation_start/end
policy/generation identity
```

Future windows cannot affect earlier tuning.

### 12.4 Monte Carlo

Monte Carlo must use an explicit deterministic seed in evidence.

Supported analyses may include:

- trade-order permutation/resampling;
- return/path resampling where statistically meaningful;
- slippage/cost stress combinations.

The exact algorithm/version is persisted.

### 12.5 RobustnessDecision

Product-level output:

```text
PASS | FAIL | BLOCKED
```

with deterministic reason codes and full artifact references.

A favorable OOS ValidationDecision alone is not sufficient for product-level
CANDIDATE after this stage is introduced.

---

## 13. Strategy lifecycle product materialization

The shared contract already defines:

```text
DRAFT
BACKTESTING
REJECTED
CANDIDATE
PAPER
READY_FOR_APPROVAL
APPROVED
LIVE
DEGRADED
RETIRED
```

and legal transitions.

E6 productization shall materialize those existing transitions behind named,
guarded service methods.

No generic arbitrary `transition(state)` public API.

Required gates:

### DRAFT -> BACKTESTING

- exact E2 compatibility LOCAL_EXECUTION PASS;
- exact strategy version/content binding.

### BACKTESTING -> CANDIDATE

- BacktestResult LOCAL_EXECUTION PASS;
- OOS ValidationDecision PASS;
- RobustnessDecision PASS;
- all exact strategy/dataset/project revisions bound.

### BACKTESTING -> REJECTED

- explicit reason;
- failed/blocking evidence retained.

### CANDIDATE -> PAPER

- accepted research evidence;
- PAPER policy exists;
- current application/runtime compatibility;
- no LIVE authority implied.

### PAPER -> READY_FOR_APPROVAL

- configured PAPER observation duration/trade count satisfied;
- forward-performance criteria pass;
- runtime health/restart/reconciliation evidence pass;
- no unresolved protection/execution safety defect.

### READY_FOR_APPROVAL -> APPROVED

- exact immutable ApprovalRecord;
- actor = authorized Product Owner path;
- binds exact strategy version and deployment envelope.

### APPROVED -> LIVE

- approval still current;
- required release/provider/runtime gates current;
- OperationalMode is authorized for LIVE;
- current E5 risk state allows new exposure;
- exact strategy/project/config revision preflight eligible.

### LIVE -> DEGRADED

May be automatic on fail-closed operational conditions.

### DEGRADED -> LIVE

Never automatic. Requires explicitly authorized resumption evidence.

---

## 14. PAPER runtime architecture

PAPER is a continuously operating runtime.

```text
market scheduler
-> E1 current market/candles
-> E2 StrategyRuntime
-> Signal
-> TradeIntent
-> E5 Risk
-> ApprovedTradePlan
-> E4 PaperBroker
-> OrderResult / Fill
-> E5 Position lifecycle/protection
-> E6 runtime journal
-> TradeResult
```

### 14.1 Scheduler

The scheduler triggers evaluations by strategy-required timeframe boundary.

It must:

- avoid duplicate boundary evaluation after restart;
- use UTC;
- distinguish provisional/current vs closed Candle;
- persist last evaluated boundary;
- support clean stop.

### 14.2 PAPER policy

A versioned PaperPromotionPolicy includes:

```text
minimum_runtime_duration
minimum_closed_trades
maximum_drawdown
minimum_expectancy
minimum_profit_factor_or_none
maximum_execution_error_rate
required_restart_recovery_checks
required_reconciliation_health
```

No hidden default promotes to READY_FOR_APPROVAL.

### 14.3 Performance comparison

PAPER reports compare forward behavior against research evidence:

- signal frequency;
- trade count;
- PnL;
- drawdown;
- win/loss;
- profit factor;
- costs;
- fill assumptions vs simulated realization;
- reason-code distribution.

---

## 15. Approval architecture

Approval is a human governance action captured by the product.

### 15.1 DeploymentApproval

Build on canonical ApprovalRecord.

Additional application deployment envelope references may include:

```text
strategy_id/version/hash
project_revision
risk_policy_version
max_allocated_capital
max_risk_per_trade
max_concurrent_positions
max_daily_loss
instrument
provider/account target reference
authorization generation
expiration/revocation conditions
```

Never store credentials in approval.

### 15.2 UI

The user sees a clear pre-deployment report and explicitly chooses APPROVE or
REJECT.

PAPER PASS does not silently create approval.

---

## 16. LIVE-capable trading architecture

Codex may complete all credential-free code and simulated tests.

Real provider activation is separately authorized.

LIVE sequence:

```text
runtime preflight
-> current provider reconciliation
-> current market
-> E2 evaluate
-> E5 risk decision
-> E4 exact provider request
-> ACK
-> fill truth
-> position truth
-> protection
-> readback/reconciliation
-> exit
-> flat truth
-> TradeResult
```

Invariants:

- Signal is not execution authority;
- credentials are not execution authority;
- ACK is not fill truth;
- order status alone is not position closure;
- stale provider/position/execution truth blocks new exposure;
- ambiguous submit result requires reconciliation before retry;
- missing/duplicate/orphan protection fails closed;
- restart requires fresh reconciliation;
- runtime revision/mode/heartbeat/preflight must remain current.

---

## 17. Credential architecture

Real provider credentials, when later authorized, are local only.

Preferred future storage priority:

1. OS credential manager / secure operator injection;
2. protected local secret file outside repo/cloud, if explicitly configured;
3. environment injection for bounded execution.

Never:

- Git;
- Cloud Drive result tree;
- SQLite ordinary artifact tables;
- logs;
- UI URLs;
- screenshots;
- error payloads.

The product must operate fully in Research/PAPER without any provider credential.

---

## 18. Result publishing

### 18.1 Principle

Cloud output is immutable/sanitized evidence and reports, not the mutable
runtime database.

### 18.2 Research run

```text
research/runs/<research_run_id>/
  manifest.json
  intake_receipt.json
  dataset_manifest.json
  backtest_summary.json
  oos_summary.json
  robustness_summary.json
  decision.json
  equity.parquet
  trades.parquet
  report.html
```

### 18.3 Rejected

A rejected strategy remains visible and can be archived:

```text
research/rejected/<strategy_id>/<strategy_version>/...
```

### 18.4 Candidate

```text
candidates/<strategy_id>/<strategy_version>/
  candidate_manifest.json
  evidence_index.json
  report.html
```

### 18.5 PAPER

```text
paper/<strategy_id>/<strategy_version>/<paper_run_id>/
  manifest.json
  performance.json
  trades.parquet
  health.json
  report.html
```

### 18.6 LIVE

Only sanitized:

```text
live/<strategy_id>/<strategy_version>/<deployment_id>/
  performance_snapshot.json
  trade_results.parquet
  health_summary.json
  report.html
```

No raw private provider payloads/IDs beyond approved sanitized references.

---

## 19. Control API

The backend Control API is local-only by default.

Recommended technology:

```text
Python FastAPI
localhost binding
typed DTOs
read/write application services
```

The API is an application adapter. It cannot bypass domain gates.

Minimum endpoint families:

```text
GET  /api/v1/overview
GET  /api/v1/research/runs
GET  /api/v1/research/runs/{id}
POST /api/v1/research/scan
GET  /api/v1/strategies
GET  /api/v1/strategies/{id}/{version}
GET  /api/v1/paper
POST /api/v1/paper/{strategy}/{version}/start
POST /api/v1/paper/{run}/stop
GET  /api/v1/trading
GET  /api/v1/health
GET  /api/v1/alerts
GET  /api/v1/settings
PUT  /api/v1/settings/non-secret
POST /api/v1/approvals/{subject}/decision
```

LIVE controls remain hidden/disabled unless corresponding backend authority
exists.

---

## 20. Control Center UI

Target:

```text
React + TypeScript + Vite
static build served by local R7 backend
```

Avoid Electron for V0.1 unless packaging proves necessary.

### 20.1 Overview

Display:

- operational mode;
- product/process health;
- active research runs;
- CANDIDATE count;
- active PAPER strategy;
- deployed LIVE strategy when authorized;
- current position summary;
- Risk/Broker/Reconciliation state;
- alerts.

### 20.2 Research

Display each submission/run:

```text
INBOX
DATASET
BACKTEST
OOS
ROBUSTNESS
DECISION
```

with progress and explicit fail/block reason.

### 20.3 Strategies

Display:

- strategy family/version history;
- lifecycle;
- immutable hash;
- train/OOS/robustness metrics;
- candidate/PAPER status;
- evidence links.

### 20.4 Trading

Display:

- PAPER/LIVE;
- exact strategy version;
- current signal;
- current RiskDecision;
- position;
- entry/fill/protection;
- PnL;
- recent TradeResults.

### 20.5 Health

Translate low-level states into plain language while retaining expandable
technical evidence.

Example:

```text
Position Truth       RECONCILIATION REQUIRED
New Trades           DISABLED
Reason               provider/local exposure mismatch
```

### 20.6 Settings

Non-secret product settings only.

Secret/provider credential configuration must use a separate secure local
workflow later.

---

## 21. Product process model

### 21.1 Supervisor

R7 must have an explicit product supervisor/process owner.

It starts:

- Control API;
- inbox scanner;
- research workers;
- PAPER scheduler only when enabled/authorized;
- health monitor;
- result publisher.

It must not silently start LIVE.

### 21.2 Clean stop

On shutdown:

- stop accepting new work;
- finish or checkpoint current atomic step;
- persist durable states;
- stop schedulers;
- close database;
- leave restart-safe evidence.

### 21.3 Restart

On restart:

- recover application jobs;
- reconcile incomplete claims;
- resume safe research stages;
- PAPER runtime re-establishes current data/runtime state;
- provider-capable runtime requires fresh preflight/reconciliation.

---

## 22. Concurrency

V0.1 supports bounded concurrency for research.

Requirements:

- one durable owner/lease per ResearchRun;
- no duplicate processing of one submission;
- deterministic work queue;
- configurable worker count;
- SQLite transaction safety;
- UI queries never become lifecycle authority.

PAPER/LIVE trading for the V0.1 BTC baseline uses at most one exposure under
current risk policy unless later versioned policy changes.

---

## 23. Observability

Structured local logs:

```text
timestamp
level
component
event
correlation_id
strategy_id/version
research_run_id
paper_run_id/deployment_id when applicable
reason_codes
```

Redaction is mandatory.

Metrics may include:

- inbox pending;
- research run duration;
- stage PASS/FAIL;
- candidate count;
- PAPER trade count;
- runtime heartbeat;
- reconciliation status;
- order/fill/protection health.

Cloud reports are summaries, not raw debug logs.

---

## 24. Error taxonomy

Application errors must be typed.

Minimum categories:

```text
INCOMPLETE_SYNC
PACKAGE_INVALID
STRATEGY_INCOMPATIBLE
DATASET_UNAVAILABLE
RESEARCH_BLOCKED
VALIDATION_FAIL
ROBUSTNESS_FAIL
PAPER_FAIL
RUNTIME_DEGRADED
RECONCILIATION_REQUIRED
AUTHORIZATION_REQUIRED
PROVIDER_UNAVAILABLE
INTERNAL_ERROR
```

A transient transport error is not a strategy rejection.

A quantitative strategy failure is not a system error.

---

## 25. Product policy objects

Define versioned schemas/classes for:

```text
ResearchPolicy
DatasetProfile
ValidationPolicy              existing E3 concept reused
RobustnessPolicy
PaperPromotionPolicy
RiskPolicy                    existing E5 concept reused
DeploymentEnvelope
```

Application policies may reference existing domain policy identities; they
must not redefine E3/E5 meanings.

---

## 26. Versioning

Version separately:

```text
product version
shared contract version
Strategy Package schema
E2 runtime version
research policy
validation policy
robustness policy
PAPER promotion policy
risk policy
cloud artifact schema
control API version
database migration version
```

Do not conflate these identifiers.

---

## 27. Database evolution

Continue plain SQLite migrations unless a demonstrated scaling issue requires
change.

Application-owned tables can be added in new migrations, but existing E6 domain
tables remain authoritative for their data.

Do not create duplicate canonical strategy lifecycle tables in the application
layer.

Suggested application tables:

```text
application_strategy_submissions
application_research_runs
application_research_stage_attempts
application_robustness_results
application_paper_runs
application_deployment_envelopes
application_publish_ledger
application_alerts
application_settings
```

Use foreign/logical references to E6 identities.

---

## 28. Security model

### 28.1 Threats

At minimum address:

- malicious Strategy Package paths;
- secret-like material in strategy artifacts;
- cloud partial-sync;
- replayed submission;
- changed content under same ID;
- UI bypass of backend gate;
- stale approval;
- stale runtime revision;
- log credential leakage;
- cloud publication of sensitive provider state;
- accidental LIVE start;
- restart duplicate action.

### 28.2 Required guarantees

- declarative strategies only;
- no arbitrary strategy Python execution;
- cloud files do not define shell commands;
- all path joins stay under configured roots;
- IDs are data, not filenames without sanitization;
- receipt/result publishing is atomic/idempotent;
- credentials never persisted to code/data plane;
- new exposure has E5 + runtime/provider authority;
- operational mode and strategy lifecycle remain distinct.

---

## 29. Testing architecture

### 29.1 Layers

```text
unit
domain regression
application integration
product integration
E2E
failure injection
restart/recovery
packaging smoke
acceptance
```

### 29.2 No GitHub compute

All execution stays in approved local Windows infrastructure.

GitHub stores source/evidence only.

### 29.3 Determinism

Research tests use explicit:

- dataset hashes;
- time boundaries;
- random seeds;
- policy versions;
- project revision;
- strategy hashes.

### 29.4 Product fixtures

Create a bounded set:

```text
valid strategy package
malformed package
unsupported strategy package
known REJECTED research fixture
known CANDIDATE research fixture
PAPER success fixture
PAPER degradation fixture
restart fixture
```

Fixtures are synthetic and never become real promotion evidence.

---

## 30. Windows packaging

Target normal usage:

```text
R7.exe
-> ensure local directories
-> apply database migrations
-> start local backend
-> start product supervisor
-> open default browser to Control Center
```

Recommended packaging approach:

```text
React static build
+ Python backend
+ PyInstaller/Nuitka evaluated by Codex
```

Choose the packaging tool based on reproducible Windows build evidence.

Do not require Python/Node to be manually installed by the end user in the
final packaged acceptance.

---

## 31. First-run flow

```text
Welcome
-> choose Local Data folder
-> choose Cloud Drive R7 root
-> initialize
-> verify folder permissions
-> create logical Cloud folders
-> create/migrate local DB
-> enter RESEARCH mode
-> scan inbox
-> open Overview
```

No provider credentials are required for first-run Research/PAPER product use.

---

## 32. Chat-to-R7 workflow

The external Chat workflow is:

1. Chat reads prior Cloud results when requested.
2. Chat proposes one Strategy Package.
3. Chat writes package files to Cloud Drive.
4. Chat writes manifest last.
5. R7 discovers package.
6. R7 performs all deterministic tests.
7. R7 publishes result.
8. User can later ask Chat to analyze the result and produce a new version.

No paid LLM API call occurs inside R7.

---

## 33. Complete program build order

```text
M0 Architecture baseline
M1 Cloud intake / local application core
M2 Research orchestration
M3 Robustness
M4 Lifecycle extension
M5 Continuous PAPER
M6 Control API
M7 Control Center
M8 Windows packaging
M9 LIVE-capable integration
M10 Cloud result feedback
M11 Full product acceptance
```

Some milestones may be implemented in parallel only when their interface is
already fixed in this document.

---

## 34. Definition of "implementation complete"

Implementation is complete when Codex has delivered one exact branch/revision
that:

- contains every M1-M10 capability;
- passes all credential-free local tests;
- passes product acceptance through PAPER;
- builds and launches the Windows product;
- performs Cloud Drive round-trip;
- shows product state in UI;
- contains LIVE-capable code and tests without consuming credentials/capital;
- contains no unresolved P0/P1 correctness/safety defect.

This is not the same as "real-money activated."

---

## 35. Definition of "real product activated"

Real provider/capital activation additionally requires:

- fresh provider read-only verification;
- account/provider configuration;
- secure credential injection;
- exact deployed strategy approval;
- risk/capital envelope;
- current runtime preflight;
- current reconciliation;
- Product Owner authority.

These are deliberately outside Codex autonomous authority.

---

## 36. Non-goals for V0.1

Do not block V0.1 on:

- embedded AI Researcher;
- local LLM;
- multi-exchange abstraction beyond preserving reasonable ports;
- altcoin portfolio engine;
- HFT;
- mobile native app;
- cloud-hosted backend;
- team multi-tenancy;
- distributed compute cluster;
- arbitrary user Python strategies;
- plugin marketplace.

The first product is a local-first BTC strategy research/validation/PAPER/LIVE-
capable platform with Cloud Drive artifact exchange and a usable Control Center.
