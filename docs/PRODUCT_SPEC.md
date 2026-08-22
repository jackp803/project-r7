# Project R7 — Product Specification

> Product: **BTC Quantitative Research & Trading Platform**  
> Repository: `jackp803/project-r7`  
> Product owner: repository owner / user  
> Document owner: Project Manager / Product-Architecture Auditor  
> Version: `product-spec-v0.1`  
> Status: **PROPOSED_BASELINE** — becomes the product baseline when reviewed/merged by the Product Owner  
> Contract baseline at authoring: `contracts-v0.1`  
> Architecture baseline: `ADR-0001` + `docs/architecture/COMMON_CONSTRUCTION_MAP.md`

---

## 1. Purpose

This document defines **what Project R7 is intended to become**.

It is the product-level specification for scope, capabilities, user-visible outcomes, safety properties, release stages, and V1 completion criteria. It complements, but does not replace:

- `agents/` — engineering role ownership and team rules;
- `contracts/` — canonical cross-module semantics;
- `docs/adr/` — architecture decisions;
- `docs/architecture/` — construction blueprint;
- `status/RELEASE_GATES.md` — evidence required to advance release stages.

This Product Specification must not be used to silently redefine a shared contract. If product requirements require a contract change, the normal E7 contract-change process applies.

### 1.1 Authority

When requirements conflict, the authority order defined by the repository remains in force. In particular:

1. explicit Product Owner instruction;
2. hard team/security/infrastructure rules;
3. approved architecture/contracts/ADRs;
4. this product specification for product scope and intended behavior;
5. lower-level implementation details.

The Product Owner retains final authority over major scope changes, live-capital exposure, live enablement, and policy changes that materially increase financial risk.

---

## 2. Product Vision

Project R7 is **not merely a single hard-coded BTC trading bot**.

It is a platform that can repeatedly turn a trading hypothesis into a versioned, testable strategy; subject that strategy to independent quantitative validation; retain both successful and failed research history; promote only eligible versions through paper/shadow/live stages; and execute approved trades through an independent risk and execution boundary.

The intended long-term product loop is:

```text
Strategy Hypothesis
    -> Versioned Strategy Package
    -> Deterministic Strategy Runtime
    -> Automated Backtest / Validation
    -> REJECTED or CANDIDATE
    -> Paper / Forward Evidence
    -> Approval / Promotion
    -> Risk-Controlled Execution
    -> Position Lifecycle
    -> Live / Operational Evidence
    -> Research Feedback
    -> Next Hypothesis
```

The platform remains useful even when a strategy fails. **Zero passing strategies is a valid research result.**

Profitability is not guaranteed by the existence of the platform, by an AI-generated strategy, or by a backtest PASS.

---

## 3. Primary Product Goals

V1 shall provide a coherent path for all of the following:

1. **Acquire trustworthy BTC market history** in one canonical format.
2. **Represent strategies declaratively and immutably** rather than as arbitrary generated execution code.
3. **Evaluate the same strategy semantics** in backtest, paper, and live-compatible paths.
4. **Backtest and independently validate strategies** with realistic costs and anti-bias controls.
5. **Retain strategy lineage, versions, failed experiments, and validation evidence.**
6. **Promote strategies through explicit lifecycle states** rather than directly from backtest to live.
7. **Require an independent Risk boundary** before any executable trade plan is produced.
8. **Execute approved plans safely through a broker abstraction** with idempotency, reconciliation, and recovery.
9. **Manage every open position through an explicit lifecycle** including protective exits and emergency behavior.
10. **Expose operating state, performance, health, locks, and evidence clearly** through platform/monitoring surfaces.
11. **Fail closed** when important market, account, position, order, risk, approval, or operational state is unknown.
12. **Remain reproducible and auditable** so past decisions and research results can be reconstructed.

---

## 4. V1 Target Market and Environment

### 4.1 Primary instrument

V1 primary instrument:

```text
BTC_USDT_PERP
```

The exact exchange/provider symbol mapping may be adapter-specific, but internal canonical identity must follow approved contracts.

### 4.2 Exchange

V1 exchange integration target:

```text
Pionex
```

V1 does not require a generalized multi-exchange product. The architecture should avoid unnecessary lock-in where a Broker abstraction already exists, but multi-exchange support must not delay the Pionex vertical path.

### 4.3 Timeframes

V1 market-data baseline supports:

```text
1m
15m
1h
4h
```

Primary strategy research is expected to emphasize 15m / 1h / 4h semantics, while 1m may be used for replay detail, ambiguity reduction, and supporting strategies where required.

### 4.4 Time and numeric semantics

The product must preserve the canonical contract baseline:

- internal time = UTC;
- Candle intervals = `[open_time, close_time)`;
- closed-candle strategies may not treat provisional candles as final;
- financial price/quantity/margin/fee/PnL semantics use Decimal arithmetic;
- interchange financial decimals use base-10 decimal strings.

---

## 5. Product Users and Control Roles

### 5.1 Product Owner

The Product Owner is the final authority for:

- major product-scope changes;
- activation of real-money trading;
- live-capital exposure;
- policy changes that materially raise financial risk;
- final approval when a release gate explicitly requires Product Owner authorization.

### 5.2 GPT Strategy Researcher

A GPT may act as Strategy Researcher and may:

- propose trading hypotheses;
- create versioned Strategy Packages / DSL definitions;
- propose parameter regions and variants;
- analyze validation evidence;
- identify weak regimes and new research directions.

A Strategy Researcher may **not** self-certify its own strategy for live deployment.

### 5.3 Engineering Agents E1–E7

Engineering ownership is defined by `agents/`. The product relies on their separation of responsibility:

- E1 — Market Data;
- E2 — Strategy DSL / Runtime / Indicators;
- E3 — Backtest / Quantitative Validation;
- E4 — Broker / Trading Execution;
- E5 — Risk / Position Lifecycle;
- E6 — Platform / Storage / Registry / Dashboard;
- E7 — Architecture / Contracts / Integration / QA / Release.

### 5.4 Codex

Codex is a bounded bug-fixing tool in the current project workflow, not the product architect or primary feature owner. Codex work does not override E1–E7 contracts or release gates.

---

## 6. Product Architecture Invariants

The following product boundaries are mandatory:

### 6.1 Research path

```text
Market Data
    -> Strategy Runtime
    -> Backtest / Validation
    -> Validation Evidence
    -> Strategy Registry
```

### 6.2 Trading path

```text
Market Data
    -> Strategy Runtime
    -> Signal / TradeIntent
    -> E5 Risk Decision
    -> ApprovedTradePlan
    -> E4 Execution
    -> Fill / Order / Position Truth
    -> E5 Position Lifecycle
    -> Storage / Monitoring
```

### 6.3 Forbidden shortcuts

The product must structurally prevent or reject:

- Strategy -> direct Pionex order;
- Signal -> direct live order;
- UI -> direct exchange order;
- Execution choosing direction or risk policy;
- Backtest using a private strategy implementation different from E2;
- Live using a private strategy implementation different from E2;
- a domain agent silently redefining shared `Candle`, `Order`, `Position`, etc.;
- Backtest PASS -> direct LIVE promotion;
- credentials existing -> implied LIVE authorization;
- unknown order/position/account/data state -> new exposure.

---

## 7. Functional Requirements — Market Data

V1 shall provide a normalized market-data layer sufficient for deterministic research and later live-compatible evaluation.

Required capabilities include:

- historical BTC perpetual Candle acquisition;
- `1m`, `15m`, `1h`, and `4h` support;
- UTC normalization;
- deterministic ordering;
- pagination/restart-safe historical retrieval where source requires it;
- canonical Candle normalization;
- closed/provisional candle distinction;
- duplicate detection;
- missing interval detection;
- out-of-order detection;
- malformed OHLC rejection;
- non-negative volume semantics unless contract/source policy explicitly says otherwise;
- data provenance/source metadata;
- stale/freshness health for live/near-live data;
- mark/index/bid/ask/funding fields when the current slice requires and the source provides them.

Market-data failures must not be converted to plausible-looking zero/fabricated data.

Large historical datasets should remain local or in an explicitly approved data store. Git is not the historical-data warehouse.

---

## 8. Functional Requirements — Strategy Definition and Runtime

### 8.1 Strategy representation

Strategies shall be versioned, declarative Strategy Definitions / Packages, not arbitrary AI-generated Python that receives unrestricted system access.

The V1 strategy format must support:

- immutable `(strategy_id, strategy_version)` identity;
- content hash / reproducible serialized representation;
- required symbols/timeframes;
- parameters;
- rules / supported primitives;
- runtime compatibility metadata;
- explicit rejection of unsupported primitives/operators.

Material strategy logic, parameter, timeframe, indicator-semantic, entry, or exit changes require a new strategy version once evidence has been attached.

### 8.2 Deterministic runtime

The same Strategy Definition + same exact market/state boundary + same runtime version must produce the same decision.

The same E2 Strategy Runtime semantics must be consumable by:

- historical backtest;
- paper/forward execution path;
- live-compatible evaluation path.

The product must not maintain separate strategy implementations merely because the runtime environment is different.

### 8.3 Strategy output

Strategy output may include structured `Signal` / `TradeIntent` information, but it does not have broker authority and does not approve position size/leverage.

`NO_TRADE` is a valid deterministic result. The system must not force a daily trade merely to satisfy strategy activity targets.

---

## 9. Functional Requirements — Strategy Research

The platform shall support an AI-assisted research workflow while preserving independent validation.

A research cycle may be:

```text
Hypothesis
-> StrategyDefinition
-> Development backtest
-> Failure analysis
-> New strategy version / new experiment
-> Validation
-> REJECTED or CANDIDATE
```

Research should eventually support multiple deterministic strategy families such as trend, breakout, pullback, momentum, mean-reversion, volume, volatility, or regime-aware approaches when the required primitives are available.

The product must prefer testable, auditable hypotheses over subjective chart-reading logic that cannot be reproduced.

Unsupported strategy primitives shall fail explicitly. A future primitive may be added as an engineering capability, but an unsupported primitive must not be silently approximated.

---

## 10. Functional Requirements — Backtest and Quantitative Validation

V1 shall provide an independent validation path capable of rejecting weak or overfit strategies.

### 10.1 Historical replay

The backtest system must:

- consume canonical E1 market data;
- invoke E2 Strategy Runtime rather than reimplement strategy logic;
- respect closed-candle timing;
- prohibit future-data access;
- simulate entries/exits according to approved semantics;
- represent transaction costs explicitly;
- expose replay assumptions/configuration;
- produce deterministic/reproducible results where deterministic inputs are used.

### 10.2 Cost and execution assumptions

The validation engine shall support configurable:

- maker/taker fees where relevant;
- entry/exit fees;
- slippage;
- funding;
- fill/execution assumptions;
- conservative handling of same-candle SL/TP ambiguity or finer-timeframe replay when available.

Published exchange fee/rule values must be treated as versioned/configurable assumptions, not permanent constants embedded inside strategy logic.

### 10.3 Metrics

V1 shall be capable of reporting at least:

- trade count;
- win/loss count and win rate;
- average win/loss;
- gross and net PnL;
- fees/slippage/funding costs;
- Profit Factor;
- Expectancy;
- maximum drawdown;
- maximum consecutive losses;
- holding-time information;
- long/short separated results where applicable;
- reproducibility metadata.

The validation platform should support or evolve toward:

- development/validation/final OOS separation;
- walk-forward analysis;
- Monte Carlo analysis;
- parameter robustness;
- market-regime analysis;
- Sharpe / Sortino where meaningful.

### 10.4 Research integrity

The product must not:

- optimize on a final test segment and continue calling it untouched OOS;
- hide failed strategies;
- silently alter a strategy after a failed validation while retaining the same immutable version;
- always choose the favorable intrabar sequence;
- treat high win rate alone as evidence of profitability;
- claim guaranteed future profitability from backtest evidence.

Validation thresholds are versioned policy. This document does not freeze one universal Profit Factor, trade-count, or drawdown threshold for every strategy family.

---

## 11. Functional Requirements — Strategy Registry and Lifecycle

The platform shall maintain a Strategy Registry containing immutable version identity and evidence references.

Target lifecycle:

```text
DRAFT
  -> BACKTESTING
  -> REJECTED
       or
     CANDIDATE
  -> PAPER
  -> READY_FOR_APPROVAL
  -> APPROVED
  -> LIVE
  -> DEGRADED / RETIRED
```

Exact transition rules are governed by canonical contracts and release policy.

Required lifecycle properties:

- rejected strategies remain auditable;
- failed research history is not deleted merely to make results look better;
- strategy versions cannot overwrite one another;
- validation evidence binds to the exact strategy version/content;
- lifecycle transitions are timestamped/audited;
- invalid skipped transitions are rejected;
- UI actions cannot bypass backend gate checks;
- Backtest PASS alone is insufficient for LIVE.

The Registry should support lineage such as parent strategy / experiment relationships as the research system matures.

---

## 12. Functional Requirements — Risk Management

E5 is the financial safety boundary.

The product must preserve:

```text
Strategy / TradeIntent
    -> E5 RiskDecision
    -> ApprovedTradePlan
    -> E4 Execution
```

Required V1 risk capabilities include:

- position sizing;
- maximum margin/exposure per trade;
- leverage cap;
- margin mode validation;
- minimum risk/reward or equivalent strategy/risk constraints where configured;
- cost-aware risk estimate;
- daily trade limit;
- simultaneous-position limit;
- consecutive-loss lock;
- account drawdown lock;
- stale/unknown market-state rejection;
- unknown account/order/position-state rejection;
- kill switch / paused state;
- structured reject reason codes;
- persisted/auditable policy version.

The product must structurally prevent normal paths for:

- Martingale;
- averaging down / loss averaging;
- revenge-size increase after losses;
- automatic leverage increase after losses;
- stop widening that increases accepted loss beyond approved risk;
- strategy or UI bypass of E5.

Unknown required state fails closed for new exposure.

### 12.1 Initial pilot-policy support target

V1 should be capable of expressing a conservative small-account pilot policy including concepts such as:

- isolated margin;
- one simultaneous position;
- maximum one new trade per day;
- small fixed/bounded margin per trade;
- capped leverage;
- consecutive-loss pause;
- drawdown lock;
- mandatory protective stop.

Values such as `10 USDT` margin, `20x` maximum leverage, `5` consecutive losses, or a drawdown threshold are **configuration/policy candidates, not universal product constants**. Exact live values require explicit Product Owner approval before real-capital activation.

---

## 13. Functional Requirements — Position Lifecycle

After an actual fill, the platform shall manage the position through explicit state and protection logic.

V1 position-management capability shall support:

- actual filled quantity and entry price;
- hard stop loss;
- take profit;
- break-even / profit protection when strategy/policy enables it;
- trailing protection when supported and approved;
- structured strategy-invalidating exit where supported;
- maximum-hold / time stop;
- manual/emergency exit path;
- reconciliation-required state;
- protection based on actual filled quantity rather than requested quantity.

An entry that is filled but cannot be protected must not be reported as safely open. It must enter an explicit unsafe/unprotected/emergency path according to risk policy.

---

## 14. Functional Requirements — Execution / Broker Integration

E4 shall provide exchange-independent broker semantics where practical and a Pionex implementation for V1.

Required capabilities include:

- PaperBroker;
- Pionex private adapter when the project reaches the appropriate slice;
- authentication/signature behavior;
- account/balance/position queries;
- order create/cancel/query;
- open orders / history / fills;
- stable client order identity / idempotency;
- partial-fill handling;
- rate-limit and timeout behavior;
- ambiguous acknowledgement handling;
- exchange/local state reconciliation;
- process restart recovery;
- execution-health state.

A timeout or ambiguous response must not authorize a blind duplicate order. The system must reconcile before retry when exposure might already exist.

The exchange/broker is authoritative for actual orders, fills, and exposure. E5 remains authoritative for risk/lifecycle interpretation.

---

## 15. Operational Modes

The product shall represent mode explicitly rather than by UI convention.

Target modes include:

```text
RESEARCH / BACKTEST
PAPER
SHADOW
LIVE
PAUSED / LOCKED
```

### 15.1 Research / Backtest

No real broker order submission.

### 15.2 Paper

Strategy, risk, execution, position lifecycle, storage, and monitoring may operate using a PaperBroker without real exchange exposure.

### 15.3 Shadow

Live market/account/exchange observations may be consumed and the system may produce would-be decisions/plans, but **real order submission remains structurally disabled**.

### 15.4 Live

Real order submission is permitted only when all required technical gates pass and the Product Owner has explicitly approved live activation for the relevant release/strategy/policy context.

Credentials existing is not equivalent to authorization.

---

## 16. Functional Requirements — Platform, Storage, Dashboard, Monitoring

V1 shall provide an operable platform layer rather than requiring the Product Owner to reconstruct system state from raw logs.

### 16.1 Persistence / audit

The platform should persist or reference, as required by current architecture:

- Strategy Definitions and versions;
- lifecycle state;
- validation/backtest run metadata and evidence;
- signals/intents/plans where required for audit;
- orders/fills/positions/trade results;
- risk state and locks;
- operational mode;
- approvals/rejections;
- system/health events.

State that must survive restart for safety or audit must be persisted.

### 16.2 Dashboard / operator view

The operator should eventually be able to see at least:

- market/data health;
- current strategy ID/version/state;
- validation summary;
- current operational mode;
- risk locks/block reasons;
- equity/drawdown where available;
- trades today / losing streak where available;
- current position and protection state;
- order/reconciliation health;
- system degraded/unknown conditions;
- strategy approval/promotion state;
- audit events.

### 16.3 Performance separation

Performance views must keep these distinct:

- Backtest;
- Paper / Forward;
- Shadow;
- Live.

They must not be merged into one unlabeled performance number.

---

## 17. Security and Secret Handling

The GitHub repository is public.

The following must never be committed to Git history, issues, PR text, tracked fixtures, logs, screenshots, or documentation:

- real Pionex API keys;
- API secrets;
- GitHub tokens;
- passwords;
- private keys;
- session credentials;
- real live `.env` values;
- other account credentials.

Allowed repository pattern:

```text
.env.example
PIONEX_API_KEY=
PIONEX_API_SECRET=
```

Real secrets are local-only and must be ignored by Git or stored in a separately approved local secret mechanism.

If a real credential is found in tracked/public content, normal work stops and the event becomes a security incident requiring Product Owner notification, credential rotation, and appropriate Git-history remediation.

---

## 18. Infrastructure / GitHub Execution Constraint

GitHub is the project's:

- source-control surface;
- PR/review surface;
- issue/task surface;
- documentation/shared-memory surface.

GitHub is **not** the project compute platform.

Unless the Product Owner explicitly changes this rule, the project must not use:

- GitHub Actions;
- `.github/workflows` for project code execution;
- GitHub-hosted runners;
- GitHub-triggered self-hosted runners;
- GitHub CI/CD test pipelines;
- scheduled GitHub backtests;
- GitHub-hosted Monte Carlo / walk-forward runs;
- GitHub-hosted integration/E2E/failure-injection/load/performance tests;
- GitHub-hosted bug reproduction.

All executable verification must run locally or in another environment explicitly approved by the Product Owner.

When an allowed local execution environment is unavailable:

```text
NOT_RUN
+ exact local command
```

is correct.

`NOT_RUN` must never be promoted to PASS by assumption.

---

## 19. Non-Functional Requirements

### 19.1 Determinism

Given the same immutable strategy/version, exact input boundary, runtime version, and deterministic configuration, strategy decisions and deterministic replay outputs must be reproducible.

### 19.2 Auditability

Important research, promotion, risk, order, position, and approval decisions must be attributable to exact versions and reason/evidence records.

### 19.3 Reproducibility

Validation evidence should identify enough information to reproduce the run, including strategy version/content, data/dataset identity, configuration/cost assumptions, runtime/code revision, and random seed where relevant.

### 19.4 Fail-closed safety

Unknown or inconsistent state must never become implicit permission for new live exposure.

### 19.5 Recovery

The trading/runtime path must eventually recover safely from process restart, network interruption, missed acknowledgements, and local/exchange divergence.

### 19.6 Modular boundaries

The intended V1 implementation remains a modular system with strict module boundaries. The project should not prematurely split into operationally expensive microservices merely for architectural fashion.

### 19.7 Explainability

Strategy decisions, validation rejections, risk rejections, lifecycle transitions, and execution failures should expose structured reason information rather than only free-form prose.

---

## 20. V1 Non-Goals / Explicitly Deferred Scope

The following are not required for V1 unless the Product Owner explicitly reprioritizes them:

- multi-exchange live support;
- broad altcoin/multi-asset coverage;
- high-frequency / sub-minute trading architecture;
- automatic leverage escalation;
- portfolio optimization across many simultaneous strategies/accounts;
- ML/RL as a prerequisite for strategy research;
- arbitrary AI-generated executable Python strategy code;
- cloud/GitHub compute platform;
- sophisticated distributed microservice deployment;
- institutional OMS/EMS scope;
- social/community/copy-trading features;
- mobile-native application as a V1 requirement;
- procurement/payment/billing product features;
- guaranteed-profit claims.

These may become future roadmap items only when they do not compromise the current critical path.

---

## 21. Vertical-Slice Product Roadmap

The product is delivered through integrated vertical slices.

### Slice 0 — Shared Foundation

```text
Architecture + Canonical Contracts + ADR + Release Gates
```

Current baseline: `contracts-v0.1`.

### Slice 1 — Research Skeleton

```text
E1 Historical Candle
    -> E2 Strategy Runtime
    -> E3 BacktestResult
```

Product outcome: one strategy can be evaluated reproducibly against canonical historical data through the real shared runtime.

### Slice 2 — Research Platform

```text
Strategy Inbox
    -> compatibility validation
    -> E3 validation
    -> evidence storage
    -> Strategy Registry
```

Product outcome: strategies can be added, versioned, rejected/candidated, and retained with evidence.

### Slice 3 — Paper Trading

```text
Strategy
    -> TradeIntent
    -> Risk
    -> ApprovedTradePlan
    -> PaperBroker
    -> Fill
    -> Position Lifecycle
    -> Exit
    -> TradeResult
    -> Storage / Monitoring
```

Product outcome: the live architecture can be exercised without real capital.

### Slice 4 — Shadow Live

```text
Live market/account observations
    -> full decision/risk/reconciliation path
    -> no real order submission
```

Product outcome: live-world state and failure handling can be validated while exposure remains disabled.

### Slice 5 — Tiny Live Pilot

Product outcome: a tightly bounded real-capital pilot becomes technically possible only after all required gates/evidence and explicit Product Owner approval.

---

## 22. Release and Evidence Requirements

Release decisions use the repository status vocabulary:

```text
PASS
FAIL
BLOCKED
NOT_RUN
NOT_APPLICABLE
```

Rules:

- PASS requires evidence;
- NOT_RUN is not PASS;
- BLOCKED is not PASS;
- component PASS does not imply the next product gate is PASS;
- GitHub CI/Actions evidence is not permitted under current infrastructure policy;
- executable evidence must record allowed environment, command, result, and relevant revision;
- first live activation requires explicit Product Owner approval even after technical readiness.

The authoritative criterion list remains `status/RELEASE_GATES.md`.

---

## 23. Product Acceptance Criteria

### 23.1 Research Platform acceptance

The research portion is product-usable when the system can demonstrably:

- obtain/normalize canonical BTC history;
- evaluate immutable strategy definitions deterministically;
- replay strategies without look-ahead;
- account for configured trading costs;
- produce reproducible Backtest/Validation evidence;
- retain rejected strategies and immutable versions;
- move eligible strategies only through legal lifecycle transitions.

### 23.2 Paper acceptance

Paper capability is product-usable when:

- a real Strategy Runtime output reaches E5 Risk;
- E5 can approve and reject intents;
- only an ApprovedTradePlan reaches broker execution;
- PaperBroker fills flow into actual position-lifecycle logic;
- protection/exit behavior uses actual fill semantics;
- risk locks and failure conditions work;
- results and audit state persist correctly across required restarts.

### 23.3 Shadow acceptance

Shadow capability is product-usable when:

- live market/account/order state can be observed safely;
- execution planning/reconciliation is exercised;
- ambiguous/unknown state fails closed;
- real order submission remains structurally unreachable in SHADOW;
- monitoring exposes degraded state accurately.

### 23.4 V1 technical completion

V1 may be considered **technically complete** when:

- Gate A `RESEARCH_READY` passes;
- Gate B `PAPER_READY` passes;
- Gate C `SHADOW_READY` passes;
- Gate D technical `LIVE_READY` criteria pass for the intended tiny-live configuration;
- no unresolved critical architecture/security/safety blocker remains;
- required user-facing operational controls/audit exist.

Technical completion does **not** automatically activate real-money trading.

### 23.5 Live activation

Real-money LIVE activation additionally requires:

- an exact eligible strategy version;
- required validation/paper evidence;
- exact risk-policy/config context;
- E7 technical sign-off;
- explicit Product Owner approval.

The Product Owner may choose to keep the platform non-live even when technically ready.

---

## 24. Product Success Criteria

Project success is not defined as "the first strategy makes money."

A successful V1 proves that the platform can:

1. turn a strategy hypothesis into a machine-readable immutable definition;
2. reproduce its decisions and historical evaluation;
3. reject poor strategies without hiding them;
4. preserve independent validation evidence;
5. prevent strategy/risk/execution authority collapse;
6. operate through Paper and Shadow modes safely;
7. reconcile and recover execution state;
8. enforce risk locks and protective lifecycle behavior;
9. expose its current state/evidence to the Product Owner;
10. reach technical live readiness without automatically using real capital.

A strategy that fails validation is evidence that the research system is doing its job, not evidence that the platform failed.

---

## 25. Change Control

### Product-level change

Examples:

- add ETH or another asset;
- add another exchange;
- introduce ML/RL as a major research path;
- change live-approval policy;
- permit GitHub/cloud execution;
- materially increase live risk envelope.

These require Product Owner decision and corresponding project/spec/roadmap update.

### Architecture/contract change

If a product decision changes shared data semantics, authority boundaries, state machines, or cross-module behavior, E7 must run the normal ADR/contract-change process before domain implementations depend on it.

### Domain implementation change

Domain engineers may evolve internal implementation inside their owned scope without changing product or canonical contract semantics.

---

## 26. Current Product State at `product-spec-v0.1`

At creation of this specification:

```text
Slice 0 — Shared Foundation     PASS
contracts-v0.1                  BASELINE
ADR-0001                        ACCEPTED

Slice 1 — Research Skeleton     IN PROGRESS by E1 / E2 / E3

Gate A — RESEARCH_READY         BLOCKED until executable evidence
Gate B — PAPER_READY            BLOCKED
Gate C — SHADOW_READY           BLOCKED
Gate D — LIVE_READY             BLOCKED
```

This status statement is descriptive at authoring time. The authoritative live status remains under `status/` and must be updated independently as engineering progresses.

---

## 27. Traceability to Engineering Ownership

| Product capability | Primary owner(s) | Integration authority |
|---|---|---|
| Canonical/historical market data | E1 | E7 |
| Strategy DSL/runtime/indicators | E2 | E7 |
| Backtest/validation/evidence | E3 | E7 |
| Broker/Pionex execution | E4 | E7 |
| Risk/position lifecycle | E5 | E7 |
| Registry/storage/dashboard/monitoring | E6 | E7 |
| Shared contracts/ADR/release integration | E7 | E7 |
| Product direction/scope/live approval | Product Owner + Project Manager audit | Product Owner final |
| Strategy hypothesis generation | GPT Strategy Research mode | independent E3 validation required |
| Bounded implementation bug fix | Codex | owning engineer/E7 acceptance |

---

## 28. Product Principle Summary

Project R7 shall remain a system where:

```text
AI may propose.
Strategy may signal.
Validation may reject.
Risk may veto.
Execution may only execute approved plans.
The platform must remember evidence.
E7 may block integration/release.
The Product Owner alone may authorize first real-money activation.
```

That separation is a product feature, not merely an implementation detail.
