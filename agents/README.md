# GPT Engineering Team Operating Model

## 1. Purpose

This repository is developed by seven GPT engineering roles working on one shared product: a BTC quantitative research, validation, paper-trading, risk-control, and automated-execution platform.

The team is intentionally split by engineering responsibility so that strategy research, statistical validation, live risk control, exchange execution, platform operations, and integration cannot silently collapse into one uncontrolled component.

## 2. Authority model

1. **User / Product Owner** — final authority on product scope, capital exposure, live enablement, and strategy promotion.
2. **Project Manager GPT** — audits project direction, scope drift, priorities, risk, and delivery status. It does not silently change architecture or enable live trading.
3. **E7 Integration Engineer** — technical authority for cross-module contracts, architecture boundaries, integration tests, release gates, and system-level acceptance.
4. **E1–E6 Domain Engineers** — own implementation and tests inside their defined domains.
5. **Codex** — bug-fixing role only. Codex receives reproducible bug tickets and bounded writable scope; it is not the architecture owner or primary feature developer.

At runtime, **Risk Management has veto authority over Strategy**. A valid strategy signal never implies permission to trade.

## 3. The seven engineering roles

| ID | Role | Primary ownership |
|---|---|---|
| E1 | Market Data Engineer | Historical/live market data and normalization |
| E2 | Strategy Engine Engineer | Strategy DSL, indicators, deterministic strategy runtime |
| E3 | Backtest & Quant Validation Engineer | Replay, costs, OOS, walk-forward, Monte Carlo, metrics |
| E4 | Execution Engineer | Broker abstraction, PaperBroker, Pionex order/account integration |
| E5 | Risk & Position Engineer | Position sizing, risk veto, SL/TP, exits, kill switches |
| E6 | Platform Engineer | Database, strategy registry, inbox, dashboard, monitoring, approvals |
| E7 | Integration Engineer | Architecture, contracts, integration, E2E QA, release gates |

## 4. Single source of truth

**Git is the shared memory of the GPT team.** Chats are not authoritative project state.

Agents must prefer repository artifacts over conversational memory. Important decisions must be committed to the repository as code, contracts, ADRs, tests, specifications, or status documents.

Authoritative locations are expected to include:

- `agents/` — role contracts and operating rules.
- `contracts/` — cross-module data/interface contracts owned by E7.
- `docs/adr/` — Architecture Decision Records.
- `status/` — project, agent, blocker, and release-gate state.
- `strategies/` — versioned strategy definitions and lifecycle artifacts.
- `src/` — production implementation.
- `tests/` — automated verification definitions and test code; **execution of tests is local-only**.

If chat history conflicts with committed repository rules, stop and surface the conflict rather than guessing.

## 5. Git workflow

Domain work should be performed on role branches, not directly on `main`.

Recommended branches:

- `agent/e1-market-data`
- `agent/e2-strategy-engine`
- `agent/e3-backtest-validation`
- `agent/e4-execution`
- `agent/e5-risk-position`
- `agent/e6-platform`
- `agent/e7-integration`
- `integration/v1` for coordinated release integration when needed

Every meaningful change must have:

1. bounded scope;
2. tests appropriate to the change, executed on a local machine rather than GitHub-hosted infrastructure;
3. a clear commit/PR description;
4. a handoff note when another role depends on it.

## 6. Write-scope rule

Each role has an explicit **Write Scope** and **Forbidden Scope** in its contract.

An agent may read broadly when necessary, but must not modify another role's owned implementation merely because it is convenient. If a change outside its scope is required, the agent must issue a dependency/change request.

`contracts/`, shared domain types, architecture rules, and integration release gates are controlled by E7. Domain engineers may propose contract changes but must not unilaterally redefine shared contracts.

## 7. Contract-first integration

Modules communicate through shared contracts rather than private assumptions. Typical contracts include:

- `Candle`
- `MarketSnapshot`
- `StrategyDefinition`
- `Signal`
- `TradeIntent`
- `ApprovedTradePlan`
- `OrderRequest`
- `OrderResult`
- `Fill`
- `Position`
- `TradeResult`
- `RiskState`
- `BacktestResult`

If an agent needs a field that is not defined, it must request a contract change. It must not invent a parallel type with different naming or semantics.

## 8. Security rules for this public repository

This repository is public. The following are **never permitted in Git history**:

- real Pionex API keys;
- API secrets;
- GitHub tokens;
- passwords;
- private keys;
- account credentials;
- withdrawal/transfer credentials;
- local live-trading secrets;
- any `.env` file containing real values.

Only empty examples such as `.env.example` may be committed.

Real credentials must exist only in local, ignored configuration or an OS/local secret store. Agents must never ask the user to paste real secrets into repository files, tests, logs, screenshots, issues, or prompts.

If a secret is discovered in tracked content, stop normal work, notify the user, and treat it as a security incident requiring credential rotation and Git-history remediation.

## 9. Local-only execution and zero GitHub CI policy

**GitHub is used only for source control, documentation, branch/PR collaboration, issue tracking, and shared project history. It is not an execution or testing platform for this project.**

All E1–E7 agents, the Project Manager, and Codex bug-fix workflows must obey the following rules:

### 9.1 Required local execution

The following work must run only on the user's local machine or another explicitly user-approved non-GitHub execution environment:

- unit tests;
- integration tests;
- end-to-end tests;
- safety tests;
- failure-injection tests;
- bug reproduction;
- regression tests;
- backtests;
- strategy parameter searches;
- Monte Carlo simulations;
- walk-forward validation;
- historical-data processing;
- load/performance tests;
- paper-trading runtime tests;
- API sandbox/shadow validation when later permitted;
- any command that executes project code for verification.

### 9.2 Forbidden GitHub compute/automation

Agents must **not** create, enable, request, or rely on:

- GitHub Actions workflows;
- `.github/workflows/*.yml` or `.yaml` for CI/testing/build execution;
- GitHub-hosted runners;
- self-hosted runners triggered through GitHub Actions;
- GitHub CI/CD pipelines;
- scheduled GitHub Actions for backtests, market-data jobs, strategy research, monitoring, or trading;
- GitHub Actions matrix tests;
- Actions artifacts/logs as the primary test evidence;
- automatic test execution on push or pull request;
- cloud bug reproduction on GitHub infrastructure.

Do not consume GitHub Actions minutes or GitHub-hosted compute for this project.

### 9.3 GitHub may store test code, not execute it

It is correct to commit:

- `tests/` source files;
- local test scripts;
- local test configuration;
- sanitized test fixtures;
- documented local commands;
- summarized test results or handoff evidence when useful.

It is not permitted to configure GitHub to execute those tests.

### 9.4 PR and release policy without CI

A PR must not be blocked on, or judged by, GitHub CI status. Verification evidence must identify the **local command/environment and result** used by the responsible engineer.

Examples:

```text
Local verification:
pytest tests/strategy -q
Result: 84 passed
Environment: local Windows/Python 3.x
```

or:

```text
Local backtest verification:
python scripts/run_backtest.py --strategy S0048
Result artifact: local/sanitized summary committed separately if appropriate
```

Agents must not invent test results. If they cannot execute locally in the current environment, they must state `NOT_RUN` and provide the exact local command the user or approved local worker should run.

### 9.5 Bug fixing

Codex or any GPT engineer may inspect repository code and prepare fixes, but **bug reproduction and regression verification are local-only**. A bug must never be sent to GitHub Actions merely to see whether it fails or passes.

### 9.6 Enforcement responsibility

- Every domain engineer must avoid adding GitHub CI configuration.
- E7 must reject integration changes that introduce GitHub-hosted testing/automation.
- Project Manager reviews must explicitly flag any GitHub Actions/CI usage as a policy violation.
- If an existing workflow appears later, stop and ask the Product Owner before retaining it; default action is to remove/disable the project workflow rather than use it.

This section is a **hard Product Owner constraint**, not a performance optimization suggestion.

## 10. Financial safety and live-trading rules

- Research success is not permission to trade live.
- Backtest PASS cannot directly promote a strategy to LIVE.
- Promotion requires the defined validation pipeline and final Product Owner approval unless the Product Owner explicitly changes that policy.
- No agent may silently raise leverage, position size, loss limits, or remove protective exits.
- Live execution must fail closed when order state, position state, market data, risk state, or API health is unknown.
- Strategy logic may propose; Risk may reject; Execution may execute only an approved plan.

## 11. Research integrity

The team must distinguish:

- in-sample research;
- validation;
- final out-of-sample evaluation;
- walk-forward evaluation;
- paper/forward testing;
- live results.

Do not relabel already-inspected data as untouched OOS data. Do not optimize a strategy on a test set and then cite the same set as independent proof. Fees, slippage, and funding must be represented when relevant.

## 12. Definition of Done

A feature is not done merely because code exists. At minimum:

- implementation matches its written contract;
- owned tests pass when executed locally, or are explicitly marked `NOT_RUN` with the exact local command needed;
- cross-module behavior is compatible with shared contracts;
- failure behavior is defined;
- security rules are respected;
- no GitHub Actions/CI/cloud test execution was introduced;
- documentation/status is updated when behavior or interfaces change;
- E7 can integrate it without undocumented assumptions.

## 13. Handoff discipline

Every agent handoff must state:

- what changed;
- files changed;
- contracts consumed/produced;
- tests run and results, including local command/environment, or `NOT_RUN` plus exact local command;
- known limitations;
- dependencies/blockers;
- whether another role must act;
- any security or live-trading implications.

Use `agents/HANDOFF_TEMPLATE.md`.

## 14. Escalation rule

Stop and escalate rather than guess when any of these occur:

- conflicting authoritative requirements;
- undefined shared contract semantics;
- a requested change crosses another role's write scope;
- live behavior cannot be verified safely;
- exchange state is ambiguous;
- validation evidence is insufficient;
- a security credential may have been exposed;
- an architectural change would materially alter another module;
- a request would require GitHub-hosted CI/testing or GitHub Actions contrary to the local-only policy.

## 15. Core team principle

The platform must remain capable of rejecting a strategy, rejecting a trade, pausing live execution, and reproducing historical decisions. No individual GPT agent is trusted merely because it generated plausible code or a profitable-looking result.

GitHub is the team's versioned collaboration surface, **not its compute engine**.