# Release Gates

> Owner: E7 Integration / Architecture / System QA / Release Engineer  
> Baseline: 2026-08-20  
> Policy: no gate may PASS without evidence from an allowed environment.

## Evidence status vocabulary

Every criterion uses exactly one of:

- `PASS` — required evidence exists and satisfies the criterion.
- `FAIL` — evidence shows the criterion is not satisfied.
- `BLOCKED` — prerequisite/contract/environment prevents evaluation.
- `NOT_RUN` — executable verification is required but has not run in an allowed environment.
- `NOT_APPLICABLE` — criterion is explicitly outside the evaluated slice/gate.

Hard rules:

- `BLOCKED != PASS`.
- `NOT_RUN != PASS`.
- component-level PASS never implies a later release gate PASS.
- GitHub Actions/CI/runners cannot be used as evidence.
- local command, environment, result, and relevant revision must be recorded for executable evidence.
- first LIVE activation requires explicit Product Owner approval even if all technical criteria pass.

---

## Foundation — Slice 0

This is a construction foundation, not a live/research release authorization.

| Criterion | Status | Evidence / blocker |
|---|---|---|
| Common construction map exists | PASS | `docs/architecture/COMMON_CONSTRUCTION_MAP.md` |
| Shared contract governance exists | PASS | `contracts/README.md` |
| Canonical baseline contracts materialized | PASS | `contracts/SHARED_CONTRACTS_V1.md` (`contracts-v0.1`) |
| Architecture baseline ADR exists | PASS | `docs/adr/ADR-0001-canonical-contract-first-architecture.md` |
| Release evidence vocabulary defined | PASS | this file + canonical contracts |
| Integration test structure exists | BLOCKED | to be materialized in Slice 0 |
| Safety/policy test structure exists | BLOCKED | to be materialized in Slice 0 |
| Local executable contract verification | NOT_RUN | no executable shared schemas/types yet |
| GitHub compute policy local scan | NOT_RUN | must be run locally once checkout/runtime is available |
| Secret hygiene local scan | NOT_RUN | must be run locally once checkout/runtime is available |

Slice 0 exits only when the remaining structural items are materialized. Executable items may remain `NOT_RUN` if no executable implementation exists yet, but downstream release gates remain blocked until their required evidence exists.

---

## Gate A — RESEARCH_READY

Purpose: allow reliable integrated research/backtesting. This does **not** authorize paper or live trading.

### Required domains

- E1 historical market-data path
- E2 deterministic Strategy Runtime
- E3 backtest/validation path
- E6 minimal strategy/result persistence or registry integration required by the evaluated slice
- E7 canonical contracts/integration tests

### Criteria

| Criterion | Initial status | Required evidence |
|---|---|---|
| E1 normalized Candle contract implemented | BLOCKED | contract-compatible code + local tests |
| Historical data integrity/gap/duplicate behavior verified | NOT_RUN | local E1 test command/result |
| Closed-candle semantics match canonical contract | NOT_RUN | local E1/E2 integration test |
| E2 StrategyDefinition parser/runtime implemented | BLOCKED | E2 implementation + local tests |
| Same strategy/input boundary -> deterministic Signal | NOT_RUN | local E2 test |
| No future-data/look-ahead trap passes | NOT_RUN | local E2/E3 integration test |
| E3 uses E2 runtime rather than private strategy rewrite | BLOCKED | code review + local integration evidence |
| Backtest fees/slippage/funding assumptions are explicit | BLOCKED | E3 implementation/config/evidence |
| BacktestResult reproducibility metadata present | BLOCKED | E3 result contract implementation |
| Research vertical slice E1 -> E2 -> E3 passes | NOT_RUN | local integration command/result |
| No critical contract mismatch | BLOCKED | E7 integration review after implementations exist |
| No real secrets in tracked research artifacts | NOT_RUN | local repository scan + review |
| GitHub CI/Actions not used for verification | PASS | policy baseline; must remain true during integration |

**Gate A current state: `BLOCKED`.**

---

## Gate B — PAPER_READY

Purpose: authorize controlled paper-trading integration only. No real order submission.

Prerequisite: Gate A PASS unless E7 records an explicit narrower dependency exception that does not weaken safety.

### Criteria

| Criterion | Initial status | Required evidence |
|---|---|---|
| Gate A | BLOCKED | Gate A PASS evidence |
| TradeIntent -> E5 RiskDecision boundary implemented | BLOCKED | E2/E5 integration code + local tests |
| E5 can reject valid strategy intents | NOT_RUN | local risk-rejection tests |
| ApprovedTradePlan is the only E4 strategy-originated execution input | BLOCKED | contract/code review + local safety test |
| PaperBroker conforms to broker contract | BLOCKED | E4 implementation + local broker tests |
| Partial fill semantics preserve actual quantity | NOT_RUN | local E4/E5 integration test |
| Required protection follows actual filled quantity | NOT_RUN | local E4/E5 safety test |
| Protection failure triggers emergency path | NOT_RUN | local failure-injection test |
| Stale/unknown market state blocks exposure | NOT_RUN | local E1/E5 safety test |
| Unknown order/position state blocks new exposure | NOT_RUN | local E4/E5 safety test |
| Drawdown/daily/position/kill-switch rules enforced | NOT_RUN | local E5 safety suite |
| Restart/persistence preserves required state | BLOCKED | E5/E6 implementation + local restart test |
| Paper E2E closes to TradeResult and persists audit | NOT_RUN | local E2E command/result |
| GitHub CI/Actions not used for verification | PASS | must remain true |

**Gate B current state: `BLOCKED`.**

---

## Gate C — SHADOW_READY

Purpose: permit live market/account observation and full execution planning/reconciliation without real order submission.

Prerequisite: Gate B PASS.

### Criteria

| Criterion | Initial status | Required evidence |
|---|---|---|
| Gate B | BLOCKED | Gate B PASS evidence |
| Pionex private adapter auth/signature behavior verified safely | NOT_RUN | local tests using fake/test vectors and approved local credentials only when needed |
| Account/balance/position query mapping verified | NOT_RUN | approved local integration evidence |
| Idempotent client order identity implemented | BLOCKED | E4 implementation + local tests |
| Timeout/ambiguous acknowledgement reconciles before retry | NOT_RUN | local failure-injection test |
| Local/exchange mismatch blocks new exposure | NOT_RUN | local reconciliation test |
| Restart with open order/position recovers safely | NOT_RUN | local restart/reconciliation test |
| Live order submission remains disabled | BLOCKED | mode gate implementation + local safety test |
| Shadow monitoring/audit surfaces degraded state accurately | BLOCKED | E6 implementation + local test |
| Real secrets absent from Git/logs/fixtures/UI | NOT_RUN | local secret scan + runtime redaction tests |
| GitHub CI/Actions not used for verification | PASS | must remain true |

**Gate C current state: `BLOCKED`.**

---

## Gate D — LIVE_READY

Purpose: establish technical readiness for a tiny controlled live pilot. Technical readiness alone does not activate LIVE.

Prerequisite: Gate C PASS and all current strategy lifecycle evidence satisfied.

### Criteria

| Criterion | Initial status | Required evidence |
|---|---|---|
| Gate C | BLOCKED | Gate C PASS evidence |
| Exact strategy version is lifecycle-eligible | BLOCKED | E6 registry/evidence record |
| E3 validation policy satisfied for exact version | BLOCKED | accepted ValidationDecision/evidence |
| Required paper/forward evidence satisfied | BLOCKED | E6/E7 evidence record |
| E4 live execution/recovery safety tests pass | NOT_RUN | local execution regression evidence |
| E5 risk/kill-switch/protection safety tests pass | NOT_RUN | local safety regression evidence |
| E6 audit/approval/operational controls ready | BLOCKED | local platform tests + integration review |
| Critical E2E/failure-injection suite passes | NOT_RUN | local E7 test command/result |
| Semantic parity backtest/paper/live-compatible path passes | NOT_RUN | local parity suite |
| No unresolved critical/high security finding | BLOCKED | security review evidence |
| No unresolved critical integration blocker | BLOCKED | E7 integration status |
| Product Owner explicit LIVE approval captured | BLOCKED | immutable ApprovalRecord / explicit authorization |
| GitHub CI/Actions not used for verification | PASS | must remain true |

**Gate D current state: `BLOCKED`.**

`LIVE_READY` must not be reported as PASS until every required criterion is PASS. Even then, actual LIVE activation must bind to the exact approved strategy/release/mode and Product Owner authorization.

---

## Evidence record format

When executable evidence begins, record at minimum:

```text
Criterion:
Status: PASS | FAIL | BLOCKED | NOT_RUN | NOT_APPLICABLE
Revision:
Environment:
Command:
Result:
Artifact/reference:
Owner:
Timestamp UTC:
Notes:
```

Never write invented local test counts or results.