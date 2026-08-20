# Common Construction Map — E1–E7

> Repository: `jackp803/project-r7`  
> Owner: E7 Integration / Architecture / System QA / Release Engineer  
> Status: **AUTHORITATIVE CONSTRUCTION BLUEPRINT — v0.1**  
> Applies to: E1–E7, Project Manager integration review, and bounded Codex bug-fix work  
> Source of authority: `agents/README.md`, `agents/E1_MARKET_DATA.md` … `agents/E7_INTEGRATION.md`

---

## 1. Purpose

This document is the shared construction blueprint for all seven engineering agents.

It defines:

- module ownership;
- dependency direction;
- canonical cross-module contracts;
- producer/consumer boundaries;
- handoff points;
- vertical-slice construction order;
- integration and release gates;
- local-only verification policy;
- GitHub usage limits;
- security boundaries;
- Codex escalation rules.

This document does **not** transfer domain implementation ownership to E7. E7 owns the shared architecture and integration boundary; E1–E6 remain responsible for implementation inside their own domains.

---

## 2. Authority Order

When requirements conflict, use this order:

1. Product Owner explicit instruction.
2. `agents/README.md` hard team rules.
3. `agents/E7_INTEGRATION.md` for shared architecture/contracts/release gates.
4. E1–E6 role contracts for domain implementation scope.
5. Approved ADRs.
6. Approved shared contracts.
7. Committed integration/status artifacts.
8. Domain handoffs/tests.
9. Chat history only when it does not conflict with Git.

No agent may use local implementation convenience to override a higher-level rule.

---

## 3. Non-Negotiable System Shape

### 3.1 Research path

```text
Historical / Normalized Market Data        E1
                |
                v
       Strategy Runtime                    E2
                |
                v
       Backtest / Validation               E3
                |
                v
       Validation Evidence
                |
                v
       Strategy Registry                   E6
```

### 3.2 Trading path

```text
Market Data / Market Health                E1
                |
                v
       Strategy Runtime                    E2
                |
                v
        Signal / TradeIntent
                |
                v
      Risk Decision / Sizing               E5
                |
                v
       ApprovedTradePlan
                |
                v
       Broker / Execution                  E4
                |
                v
      Fill / Order / Position Truth
                |
                +-------------------+
                |                   |
                v                   v
      Position Lifecycle E5      Storage / Monitoring E6
                |                   |
                +---------+---------+
                          |
                          v
                    TradeResult
```

### 3.3 Control plane

```text
E7 Contracts / ADR / Integration / Release Gates
                     |
        +------------+------------+
        |                         |
        v                         v
    E1–E6 boundaries        System QA / Release
```

E7 may stop integration when shared semantics are inconsistent, evidence is missing, a safety boundary is bypassed, or GitHub compute policy is violated.

---

## 4. Forbidden Dependency Paths

The following are architectural violations and must not be merged:

```text
Strategy --------------------X----> Pionex / Broker submit
UI --------------------------X----> Exchange
Signal ----------------------X----> Live Order
Execution -------------------X----> invent Risk limits
Execution -------------------X----> choose trade direction
Backtester ------------------X----> private Strategy implementation
Live Runtime ----------------X----> private Strategy implementation
E1/E2/E3/E4/E5/E6 ----------X----> silently redefine shared contracts
Dashboard -------------------X----> bypass backend approval/risk gate
Credentials present ---------X----> imply LIVE authorization
Backtest PASS ---------------X----> LIVE
Unknown order/position state -X----> new exposure
```

Allowed live submission path is only:

```text
Strategy
  -> TradeIntent
  -> E5 RiskDecision = APPROVE
  -> ApprovedTradePlan
  -> E4 Execution
```

---

## 5. Domain Ownership Map

| Agent | Domain ownership | Primary write areas | Must not own |
|---|---|---|---|
| E1 | Market data ingestion, normalization, integrity, freshness | `src/market_data/`, `tests/market_data/` | Strategy, risk, private execution |
| E2 | Strategy DSL/schema, indicators, deterministic runtime | `src/strategy/`, `src/indicators/`, related tests | Statistical approval, broker execution, account risk |
| E3 | Backtest, replay, costs, validation, OOS/WF/MC | `src/backtest/`, `src/validation/`, related tests | Strategy rewriting, live execution, lifecycle promotion |
| E4 | Broker abstraction, PaperBroker, Pionex execution/reconciliation | `src/execution/`, `src/brokers/`, related tests | Trade decision, risk policy, strategy logic |
| E5 | Risk veto, sizing, limits, position lifecycle/protection | `src/risk/`, `src/position/`, related tests | Strategy discovery, broker auth, statistical validation |
| E6 | Persistence, registry, lifecycle, dashboard, monitoring, approvals | `src/platform/`, `src/storage/`, `src/registry/`, `src/dashboard/`, `src/monitoring/` | Strategy semantics, risk decision, order semantics |
| E7 | Architecture, contracts, ADR, integration, E2E/safety, release gates | `contracts/`, shared `src/domain/`, `docs/adr/`, `docs/architecture/`, integration/E2E/safety tests, release status | Replacing domain engineers |

Broad read access does not grant broad write access.

---

## 6. Canonical Shared Contract Ledger

The following are the canonical cross-module concepts. Domain agents may propose changes; E7 has final approval/versioning authority.

Initial status for all rows is **TO_BE_MATERIALIZED** until the corresponding contract is committed under `contracts/` or approved shared `src/domain/`.

| Contract | Primary producer | Primary consumers | Required invariant | Initial owner |
|---|---|---|---|---|
| `Candle` | E1 | E2, E3 | UTC, explicit timeframe, closed-candle semantics, precise numerics | E7 contract / E1 producer |
| `MarketSnapshot` | E1 | E2, E5, E6 | timestamp + freshness/health; no strategy opinion | E7 / E1 |
| `StrategyDefinition` | E2 | E2, E3, E6 | immutable version identity, deterministic semantics | E7 envelope / E2 semantics |
| `Signal` | E2 | E3, E5, E6 | strategy/version/time/direction/reason; not order authority | E7 / E2 |
| `TradeIntent` | E2 | E5 | proposal only; cannot be directly executed | E7 / E2 |
| `RiskDecision` | E5 | E4, E6, E7 | APPROVE/REJECT + reason + policy version | E7 / E5 |
| `ApprovedTradePlan` | E5 | E4, E6 | only executable trade-plan input | E7 / E5 |
| `OrderRequest` | E4 adapter boundary | E4 broker implementations | idempotent identity; derived from approved plan | E7 / E4 |
| `OrderResult` | E4 | E5, E6 | explicit order state / ambiguity | E7 / E4 |
| `Fill` | E4 | E5, E6, E3 replay parity | actual quantity/price/time; distinct from request | E7 / E4 |
| `Position` | E4 exchange truth + E5 lifecycle semantics | E5, E6, E7 | actual exposure explicit; reconciliation state explicit | E7 shared |
| `PositionAction` | E5 | E4, E6 | HOLD/PROTECT/MODIFY/EXIT/EMERGENCY etc.; reason-coded | E7 / E5 |
| `TradeResult` | E5/E4 integrated close path | E3 analytics, E6 storage | traceable to strategy, plan, orders, fills | E7 shared |
| `RiskState` | E5 | E4 gate, E6 UI/storage, E7 | locks, drawdown, stale/unknown safety state | E7 / E5 |
| `BacktestResult` | E3 | E6, E7 | machine-readable evidence, reproducibility metadata | E7 / E3 |
| `ValidationDecision` | E3 | E6, E7 | PASS/FAIL with gate reasons; never direct LIVE authority | E7 / E3 |
| `StrategyLifecycleState` | E6 persists | E2/E3/E5/E7 | legal transitions only; evidence-backed | E7 contract / E6 storage |
| `OperationalMode` | E6 authoritative persisted mode | E4, E5, E7 | RESEARCH/PAPER/SHADOW/LIVE/PAUSED/LOCKED; LIVE gated | E7 contract / E6 state |
| `HealthStatus` | E1/E4/E5 producers | E6/E7 | no false-green; degraded/unknown explicit | E7 shared |
| `ApprovalRecord` | Product Owner via E6 workflow | E6/E7/E4 gate | actor/time/scope/version/audit immutable | E7 contract / E6 persistence |

### 6.1 Contract rules

Every shared contract must eventually specify:

- schema/version;
- field names and types;
- required vs optional fields;
- time semantics;
- unit semantics;
- numeric precision;
- enum values;
- serialization format;
- producer obligations;
- consumer obligations;
- compatibility rules;
- invalid-state behavior;
- migration/deprecation policy.

No domain agent may create a permanent parallel `Candle`, `Order`, `Position`, `StrategyDefinition`, or similar cross-module model with incompatible semantics.

---

## 7. Shared Domain Semantics That Must Be Fixed Before Deep Integration

These are E7-owned architecture decisions that must be materialized before dependent code relies on them:

1. `Candle.open_time` / `close_time` meaning.
2. Exact closed-candle rule per timeframe.
3. Canonical internal timezone = UTC.
4. Canonical price/quantity/money numeric representation.
5. `StrategyDefinition` immutable identity/version rule.
6. Signal timing boundary and future-data prohibition.
7. TradeIntent vs ApprovedTradePlan separation.
8. Order state machine and ambiguous acknowledgement semantics.
9. Fill quantity vs requested quantity semantics.
10. Position truth vs lifecycle state ownership.
11. RiskDecision reason and policy-version semantics.
12. Strategy lifecycle legal transition graph.
13. Operational mode state machine.
14. Release-gate evidence object/status semantics.
15. PASS / FAIL / BLOCKED / NOT_RUN semantics.

Until materialized, agents must raise a contract request instead of guessing.

---

## 8. Strategy Lifecycle Construction Target

Target state model:

```text
DRAFT
  |
  v
BACKTESTING
  |\
  | \----> REJECTED
  v
CANDIDATE
  |
  v
PAPER
  |
  v
READY_FOR_APPROVAL
  |
  v
APPROVED
  |
  v
LIVE
  |\
  | \----> DEGRADED
  |
  +------> RETIRED
```

This diagram is the construction target, not permission for E6 to invent transitions. E7 must publish the exact transition contract and evidence rules before the lifecycle becomes authoritative.

Hard rules:

- `BACKTESTING -> LIVE` is forbidden.
- `REJECTED` remains auditable; it is not deleted to hide poor results.
- strategy versions are immutable once evidence is attached.
- a new strategy logic/parameter set gets a new version.
- UI cannot skip backend gates.
- first LIVE promotion requires explicit Product Owner approval.

---

## 9. Construction Order — Vertical Slices

Integration begins before all domain agents finish.

### Slice 0 — Shared Foundation

**Owner:** E7  
**Supporting:** all agents

Build first:

- common contracts skeleton;
- architecture ADR baseline;
- shared status/release-gate format;
- contract-change procedure;
- integration test directory structure;
- GitHub-compute prohibition check definition;
- security baseline.

Exit condition:

- downstream agents have stable minimum contracts to build against.

### Slice 1 — Research Skeleton

```text
E1 Historical Data
    -> E2 Strategy Runtime
    -> E3 Backtest Result
```

Minimum interfaces:

- `Candle`
- `StrategyDefinition`
- `Signal`
- `BacktestResult`

Primary integration tests:

- closed-candle semantics;
- no-look-ahead trap;
- same input -> same E2 decision;
- E3 calls E2 runtime rather than reimplements strategy;
- reproducibility metadata present.

Gate target: **Gate A — Research Ready**.

### Slice 2 — Research Platform

```text
E6 Strategy Inbox
    -> E2 schema/runtime compatibility
    -> E3 validation
    -> E6 evidence storage
    -> E6 Registry state
```

Minimum interfaces:

- `StrategyDefinition`
- `BacktestResult`
- `ValidationDecision`
- `StrategyLifecycleState`
- `Approval/Evidence reference`

Primary integration tests:

- valid strategy enters DRAFT/BACKTESTING;
- invalid/unsupported strategy rejected structurally;
- failed validation -> REJECTED retained;
- passed validation -> CANDIDATE only;
- strategy versions cannot overwrite each other.

### Slice 3 — Paper Trading

```text
E2 Strategy
    -> TradeIntent
    -> E5 Risk
    -> ApprovedTradePlan
    -> E4 PaperBroker
    -> Fill
    -> E5 Position Lifecycle
    -> Exit
    -> TradeResult
    -> E6 Storage / Monitoring
```

Minimum interfaces:

- `TradeIntent`
- `RiskDecision`
- `ApprovedTradePlan`
- `OrderRequest`
- `OrderResult`
- `Fill`
- `Position`
- `PositionAction`
- `TradeResult`
- `RiskState`

Primary integration tests:

- risk approve path;
- risk reject path;
- stale data reject;
- daily-limit reject;
- drawdown/kill-switch reject;
- partial fill protection quantity;
- protection failure emergency path;
- restart/recovery behavior;
- audit trail.

Gate target: **Gate B — Paper Ready**.

### Slice 4 — Shadow Live

```text
Live E1 market state
+ E4 private account/order query state
    -> E5 risk
    -> would-be ApprovedTradePlan
    -> E4 shadow execution adapter
    -> NO REAL ORDER
    -> reconciliation / monitoring / audit
```

Hard requirement:

- live submission remains structurally disabled.

Primary integration tests:

- private API read/query mapping;
- timeout/unknown state fail-closed;
- reconciliation;
- credentials are not sufficient to enable live;
- no real order method reachable in SHADOW.

Gate target: **Gate C — Private API / Shadow Ready**.

### Slice 5 — Tiny Live Pilot

This slice is not entered until all required release evidence exists.

Required before activation:

- Gate A PASS;
- Gate B PASS;
- Gate C PASS;
- Gate D technical requirements satisfied;
- no critical blocker;
- E5 live safety evidence;
- E4 recovery/idempotency evidence;
- E6 approval/audit evidence;
- E7 technical sign-off;
- **Product Owner explicit LIVE approval**.

Without Product Owner approval, state remains non-live even if technical gates pass.

---

## 10. Agent-to-Agent Handoff Points

| Producer | Consumer | Handoff | Consumer must reject when |
|---|---|---|---|
| E1 | E2 | normalized market data | stale, malformed, unsupported boundary |
| E1 | E3 | historical dataset / `Candle` stream | gaps/provenance unresolved beyond policy |
| E2 | E3 | deterministic Strategy Runtime | runtime/version undefined or divergent |
| E2 | E5 | `TradeIntent` | contract/version invalid |
| E3 | E6 | validation evidence | strategy/version mismatch or incomplete evidence |
| E5 | E4 | `ApprovedTradePlan` | missing approval/risk policy/version |
| E4 | E5 | order/fill/position truth | state ambiguous/unreconciled |
| E5 | E4 | `PositionAction` | action invalid for actual position/order state |
| E4/E5 | E6 | execution/risk state | incompatible contract version |
| E6 | E4/E5 | `OperationalMode` / approval state | LIVE not explicitly authorized |
| E1–E6 | E7 | contract change / handoff | undocumented assumptions or missing local evidence |

---

## 11. Contract Change Procedure

No shared contract changes by stealth.

Required sequence:

```text
Domain request
  -> identify problem
  -> identify producers
  -> identify consumers
  -> assess whether adapter is enough
  -> impact analysis
  -> compatibility analysis
  -> ADR if material
  -> contract version update
  -> affected test definitions
  -> local verification
  -> integration
```

A contract request must include:

- current contract/version;
- required change;
- reason current contract is insufficient;
- producer impact;
- consumer impact;
- migration/compatibility risk;
- proposed tests;
- owning agent.

---

## 12. Verification Status Vocabulary

Integration/release evidence uses only these meanings:

### PASS

Required evidence exists and the required local verification has passed.

### FAIL

Evidence exists and demonstrates the requirement is not satisfied.

### BLOCKED

Verification or implementation cannot proceed because a prerequisite, contract, environment, approval, or owner action is missing.

### NOT_RUN

The test is required but has not been executed in an allowed environment.

`NOT_RUN` must always include the exact local command/configuration needed when known.

### NOT_APPLICABLE

The gate/test does not apply to the evaluated scope, with a recorded reason.

Hard rule:

```text
NOT_RUN != PASS
BLOCKED != PASS
Component PASS != Release PASS
```

---

## 13. Local-Only Verification Matrix

Git stores test definitions and sanitized evidence summaries. GitHub does not execute them.

| Verification type | Allowed execution | GitHub Actions / runner |
|---|---|---|
| Unit tests | local / Product Owner approved environment | FORBIDDEN |
| Integration tests | local / approved environment | FORBIDDEN |
| E2E | local / approved environment | FORBIDDEN |
| Safety / failure injection | local / approved environment | FORBIDDEN |
| Backtest | local / approved environment | FORBIDDEN |
| Walk-forward | local / approved environment | FORBIDDEN |
| Monte Carlo | local / approved environment | FORBIDDEN |
| Bug reproduction | local / approved environment | FORBIDDEN |
| Regression | local / approved environment | FORBIDDEN |
| Performance/load | local / approved environment | FORBIDDEN |
| Paper runtime test | local / approved environment | FORBIDDEN |
| Shadow/private API validation | local / explicitly approved environment | FORBIDDEN |

If E7 cannot execute a required command, record `NOT_RUN`; do not create CI.

---

## 14. GitHub Usage Boundary

GitHub is allowed for:

- source control;
- branches;
- pull requests;
- issues;
- documentation;
- contracts/ADRs;
- test source code;
- sanitized fixtures;
- status/handoff/shared memory.

GitHub is forbidden as compute infrastructure for:

- GitHub Actions;
- GitHub Hosted Runner;
- GitHub-triggered self-hosted runner;
- scheduled backtests;
- scheduled market-data processing;
- Monte Carlo;
- E2E;
- failure injection;
- bug reproduction;
- performance/load tests;
- PR/push-triggered project test execution.

Any PR/branch introducing `.github/workflows/` execution for this project is an integration blocker by default.

---

## 15. Security Construction Rules

Public repository rules:

Never commit:

- real Pionex API key;
- API secret;
- GitHub token;
- passwords;
- private keys;
- live `.env` values;
- account credentials;
- withdrawal/transfer credentials;
- secret-bearing logs/screenshots/fixtures.

Allowed example:

```text
PIONEX_API_KEY=
PIONEX_API_SECRET=
```

Security incident rule:

If a real secret is found in tracked/public history, stop normal integration and report it immediately. Credential rotation and history remediation become mandatory security work.

Live enablement must never depend solely on secret presence.

---

## 16. Release Gates

### Gate A — Research Ready

Required evidence includes:

- E1 historical/normalized data contract implemented;
- E1 gap/duplicate/closed-candle behavior tested locally;
- E2 deterministic runtime implemented;
- E2 no-future-data boundary tested locally;
- E3 replay uses E2 runtime semantics;
- E3 anti-look-ahead and cost/replay tests locally verified;
- E6 can store/version strategy/result evidence required for the research slice;
- Slice 1 integration test locally PASS;
- no GitHub CI policy violation.

### Gate B — Paper Ready

Required evidence includes:

- E4 PaperBroker conforms to shared contracts;
- E5 risk veto/sizing/position lifecycle implemented;
- stale/unknown state fails closed;
- partial fill/protection behavior verified locally;
- risk locks/persistence behavior verified locally;
- E6 paper mode/audit/storage integration working;
- Slice 3 E2E locally PASS;
- system safety tests locally PASS;
- no critical blocker.

### Gate C — Private API / Shadow Ready

Required evidence includes:

- E4 private auth/account/order-query behavior verified safely;
- no real secrets in Git;
- idempotency/reconciliation implemented;
- live order submission structurally disabled in shadow mode;
- ambiguous/unknown state blocks new exposure;
- E6 monitoring/audit shows degraded/reconciliation state correctly;
- local shadow tests PASS.

### Gate D — Live Ready

Required evidence includes:

- approved strategy/version lifecycle evidence complete;
- E3 validation evidence accepted under current policy;
- required forward/paper evidence complete;
- E4 execution/idempotency/recovery tests locally PASS;
- E5 risk/kill-switch/emergency protection tests locally PASS;
- E6 approval/audit/operational mode controls locally PASS;
- E7 integration/E2E/safety suite locally PASS;
- no critical blocker;
- no unresolved shared-contract mismatch;
- no security incident;
- GitHub compute policy PASS;
- Product Owner explicit approval.

E7 technical readiness never replaces Product Owner live authorization.

---

## 17. Codex Boundary

Codex may receive only bounded implementation bugs under approved architecture.

Every Codex ticket must contain:

```text
Expected
Actual
Reproduction
Failing local test
Writable scope
Architecture constraint
Verification command
```

Additionally include when known:

- owning agent;
- contract/version;
- suspected files;
- regression scope;
- prohibited changes.

Do not send an unresolved architecture disagreement to Codex as a bug.

If the failure demonstrates that the contract/architecture itself is wrong, E7 resolves the design first.

Bug reproduction and regression verification remain local-only.

---

## 18. Planned Repository Construction Layout

The target shared structure is:

```text
agents/
    README.md
    E1_...md ... E7_...md

contracts/
    README.md
    market_data.*
    strategy.*
    risk.*
    execution.*
    position.*
    validation.*
    lifecycle.*
    operational_mode.*

src/
    domain/             # E7-approved shared semantic types/interfaces only
    market_data/        # E1
    strategy/           # E2
    indicators/         # E2
    backtest/           # E3
    validation/         # E3
    execution/          # E4
    brokers/            # E4
    risk/               # E5
    position/           # E5
    platform/           # E6
    storage/            # E6
    registry/           # E6
    dashboard/          # E6
    monitoring/         # E6

docs/
    adr/                # E7-approved material architecture decisions
    architecture/       # E7 construction/integration documentation
    market_data/        # E1
    strategy/           # E2
    backtest/           # E3
    validation/         # E3
    execution/          # E4
    pionex/             # E4
    risk/               # E5
    position/           # E5
    platform/           # E6
    operations/         # E6

tests/
    market_data/        # E1
    strategy/           # E2
    indicators/         # E2
    backtest/           # E3
    validation/         # E3
    execution/          # E4
    brokers/            # E4
    risk/               # E5
    position/           # E5
    platform/           # E6
    storage/            # E6
    registry/           # E6
    dashboard/          # E6
    integration/        # E7
    e2e/                # E7
    safety/             # E7 cross-module + coordinated E5 cases

status/
    INTEGRATION_STATUS.md
    RELEASE_GATES.md
    agent-specific status/handoffs

strategies/
    versioned strategy packages and lifecycle-safe artifacts
```

Exact file formats under `contracts/` are still an E7 implementation decision and must be captured through the first shared-contract ADR rather than guessed by individual agents.

---

## 19. Integration Handoff Checklist

Every agent handoff to E7 must state:

- branch / revision;
- files changed;
- bounded scope;
- contracts consumed;
- contracts produced/requested;
- tests defined;
- exact local tests run + environment + result, or `NOT_RUN` + command;
- known limitations;
- blockers;
- another owner action required;
- security implications;
- live-trading implications;
- confirmation that GitHub Actions/CI was not used.

E7 will not mark integration PASS when these items are materially incomplete.

---

## 20. E7 Integration Report Format

Every material integration checkpoint should report:

```text
Integrated revisions
Contracts
ADR
Agent statuses
Local tests
NOT_RUN
Integration failures
Responsible owner
Release gate
Blockers
Codex bug tickets
Security findings
GitHub compute policy status
```

No release gate may PASS without evidence.

---

## 21. Initial Construction Status

At creation of this map:

| Area | Status | Owner / next action |
|---|---|---|
| Agent role contracts | PRESENT | E1–E7 follow their authoritative files |
| Common construction map | PRESENT | E7 |
| `contracts/` canonical artifacts | NOT_YET_CREATED | E7 Slice 0 |
| `src/domain/` shared semantics | NOT_YET_CREATED | E7 after contract-format ADR |
| `docs/adr/` | NOT_YET_CREATED | E7 Slice 0 |
| `status/INTEGRATION_STATUS.md` | NOT_YET_CREATED | E7 Slice 0 |
| `status/RELEASE_GATES.md` | NOT_YET_CREATED | E7 Slice 0 |
| Domain implementations | NOT_EVALUATED | each E1–E6 branch |
| Local integration tests | NOT_RUN / not yet materialized | E7 |
| Gate A | BLOCKED | shared foundation + Slice 1 evidence required |
| Gate B | BLOCKED | Gate A + Slice 3 required |
| Gate C | BLOCKED | Paper + private API/shadow evidence required |
| Gate D | BLOCKED | all technical evidence + Product Owner approval required |
| LIVE authorization | NOT_GRANTED_BY_THIS_DOCUMENT | Product Owner only |

This table records construction state only. It does not claim domain agents have failed; their implementation branches have not yet been integrated/evaluated by this document.

---

## 22. Immediate Build Sequence After This Map

E7 should proceed in this order:

1. create the shared-contract format/versioning ADR;
2. materialize minimum Slice 1 contracts (`Candle`, `StrategyDefinition`, `Signal`, `BacktestResult`);
3. publish `status/INTEGRATION_STATUS.md`;
4. publish `status/RELEASE_GATES.md`;
5. inspect E1/E2/E3 branch outputs and handoffs against Slice 1 contracts;
6. build local-only Research Skeleton integration tests;
7. record all unavailable executions as `NOT_RUN` with exact commands;
8. open contract requests to domain owners for mismatches rather than silently patching their modules;
9. integrate Slice 1 before waiting for E4/E5/E6 completeness.

---

## 23. Definition of Done for the Shared Construction Map

This map is complete enough to govern construction when:

- each agent can identify its owned module;
- each cross-module transfer has an intended canonical contract;
- dependency direction is explicit;
- forbidden bypasses are explicit;
- vertical-slice order is explicit;
- GitHub compute prohibition is explicit;
- local test status vocabulary is explicit;
- release gates are explicit;
- Product Owner live authority is explicit;
- E7 can use the map to reject incompatible implementations without taking over domain ownership.

Changes to this map that materially alter module boundaries, live safety, shared contract ownership, or release policy should be accompanied by an ADR and impact review.
