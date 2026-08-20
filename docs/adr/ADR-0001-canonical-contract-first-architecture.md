# ADR-0001 — Canonical Contract-First Modular Architecture

- Status: **ACCEPTED**
- Date: 2026-08-20
- Decision owner: E7 Integration / Architecture / System QA / Release Engineer
- Product owner constraint: GitHub is collaboration/storage only; execution and verification are local-only or explicitly approved non-GitHub.

## Context

`project-r7` is developed in parallel by E1–E7. Without a shared architecture baseline, each domain could independently invent Candle, Strategy, Order, Position, lifecycle, or execution semantics. That would make backtest/paper/live behavior diverge and could create unsafe paths such as Strategy -> Exchange or UI -> Exchange.

The project also has a hard Product Owner constraint forbidding GitHub Actions/CI/runners and all GitHub-hosted project-code execution, including backtests, E2E, bug reproduction, failure injection, regression, Monte Carlo, and performance testing.

## Decision

### 1. Shared contract authority

E7 is the final technical authority for shared cross-module contracts and versioning. E1–E6 may propose changes but may not silently redefine shared semantics.

Canonical baseline contracts are materialized in `contracts/SHARED_CONTRACTS_V1.md`.

### 2. Dependency direction

Research flow:

```text
E1 Market Data
  -> E2 Strategy Runtime
  -> E3 Backtest / Validation
  -> E6 Registry / Evidence
```

Trading flow:

```text
E1 Market Data
  -> E2 Strategy Runtime
  -> TradeIntent
  -> E5 RiskDecision
  -> ApprovedTradePlan
  -> E4 Execution
  -> Fill / Position Truth
  -> E5 Position Lifecycle
  -> E6 Storage / Monitoring
```

Forbidden shortcuts include:

- Strategy -> Broker/Pionex direct execution;
- UI -> Exchange;
- Signal -> Live order;
- E4 inventing or increasing risk;
- E3 reimplementing strategy semantics;
- separate live strategy runtime semantics;
- domain-owned incompatible duplicate shared models;
- credentials implying LIVE permission.

### 3. One strategy semantic implementation

`StrategyDefinition` is evaluated by E2 Strategy Runtime semantics. E3 backtest, Paper, Shadow, and Live-compatible paths must call/use the same semantic runtime rather than rewrite equivalent strategy logic.

Execution/fill environments may differ, but strategy decision semantics must remain common.

### 4. Canonical time semantics

Internal time is UTC.

Canonical Candle intervals are half-open:

```text
[open_time, close_time)
```

Provider-specific timestamp conventions are normalized at E1's boundary.

A closed-candle strategy may use a candle only when the evaluation boundary is at/after `close_time` and the normalized source marks the candle closed/finalized.

### 5. Canonical financial precision

Financial values use decimal arithmetic. JSON/interchange financial values are base-10 decimal strings. Binary floating-point is not the canonical representation for price, quantity, money, fee, margin, PnL, or risk amount.

### 6. Strategy immutability

A strategy version is immutable once evidence is attached. Material changes to logic, parameters, timeframes, indicators, entry, or exit semantics require a new version/content hash.

Failed/rejected versions remain auditable.

### 7. Risk/execution boundary

E4 may execute only an E5 `ApprovedTradePlan` or an E5-authorized `PositionAction` that conforms to the shared contract.

`Signal` and `TradeIntent` are never execution authority.

Unknown/stale account, order, position, market, approval, or risk state fails closed for new exposure.

### 8. Broker truth and lifecycle truth

E4 is authoritative for actual broker order/fill/exposure observations.

E5 is authoritative for risk decisions, protective requirements, and position lifecycle interpretation.

E6 persists and presents these states but does not redefine them.

### 9. Lifecycle and LIVE authorization

Strategy lifecycle is evidence-backed and version-bound. Backtest PASS cannot directly become LIVE.

Current baseline progression is:

```text
DRAFT -> BACKTESTING -> CANDIDATE -> PAPER
      -> READY_FOR_APPROVAL -> APPROVED -> LIVE
```

with REJECTED/DEGRADED/RETIRED paths as defined by the canonical contract.

First LIVE promotion and later authorized recovery where required remain subject to explicit Product Owner approval under current policy.

### 10. Release evidence semantics

Release/integration criteria use:

- PASS
- FAIL
- BLOCKED
- NOT_RUN
- NOT_APPLICABLE

`NOT_RUN` and `BLOCKED` never imply PASS.

### 11. Local-only verification

GitHub may store:

- source code;
- tests;
- fixtures;
- docs;
- PRs/issues;
- handoffs;
- summarized local verification evidence.

GitHub must not execute project code or tests.

Forbidden mechanisms include:

- GitHub Actions;
- `.github/workflows` project execution;
- GitHub-hosted runners;
- GitHub-triggered self-hosted runners;
- PR/push CI;
- scheduled Actions;
- GitHub-hosted backtests, E2E, Monte Carlo, bug reproduction, regression, failure injection, load/performance tests.

If a required test cannot run in the current allowed environment, the correct result is `NOT_RUN` plus the exact local command.

### 12. Public-repository security

Real API keys, API secrets, tokens, passwords, private keys, live `.env` values, and other credentials are forbidden in Git history, examples, fixtures, screenshots, logs, issues, and prompts committed to the repository.

Secret discovery is a security incident and blocks normal release progression until remediated.

## Consequences

### Positive

- E1–E6 can develop in parallel against one interface target.
- Backtest/paper/live semantic drift becomes testable.
- Risk bypass paths are structurally rejected.
- Shared data types cannot silently fork.
- release decisions become evidence-based.
- GitHub compute cost/CI usage is structurally out of scope.

### Costs

- domain changes that affect shared semantics require E7 review.
- some local convenience models need adapters rather than becoming new canonical types.
- contract changes may require migration/version work.
- absence of a local runtime yields `NOT_RUN`, which may temporarily block a gate.

## Rejected alternatives

### Each domain owns its own DTOs and translates later

Rejected because semantic drift would become hard to detect and could create different Candle/Order/Position meanings across research and live paths.

### Let E4 accept raw Signal/BUY/SELL instructions

Rejected because it bypasses E5's financial safety authority.

### Separate backtest strategy implementation

Rejected because a profitable backtest could reflect different semantics from paper/live.

### Use GitHub Actions for convenience

Rejected because it violates the Product Owner's hard infrastructure constraint.

## Verification required

This ADR is architectural documentation. No project-code execution was performed to create it.

Future executable verification must be local-only and must cover:

- dependency boundary enforcement;
- one-runtime strategy parity;
- closed-candle/no-look-ahead semantics;
- Risk -> ApprovedTradePlan -> Execution boundary;
- unknown-state fail-closed behavior;
- lifecycle transition enforcement;
- no GitHub workflow dependency;
- public-repository secret hygiene.

Until those executable tests exist and run locally, the corresponding release criteria remain `BLOCKED` or `NOT_RUN`, not PASS.