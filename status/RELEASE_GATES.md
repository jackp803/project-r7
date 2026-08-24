# Release Gates

> Owner: E7 Integration / Architecture / System QA / Release Engineer  
> Baseline: 2026-08-20  
> Current reconciliation: 2026-08-24 / `E7-20260824-026`  
> Policy: no gate may PASS without evidence from an allowed environment.

## Evidence status vocabulary

Every canonical criterion uses exactly one of:

- `PASS` — required evidence exists and satisfies the criterion.
- `FAIL` — evidence shows the criterion is not satisfied.
- `BLOCKED` — prerequisite/contract/implementation/environment prevents evaluation.
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
| Integration test structure exists | PASS | `tests/integration/README.md` |
| Safety/policy test structure exists | PASS | `tests/safety/README.md` |
| Local executable contract verification | NOT_RUN | historical Slice 0 item; later executable slices provide their own evidence |
| GitHub compute policy local scan | NOT_RUN | no standalone local scan is recorded for Slice 0 |
| Secret hygiene local scan | NOT_RUN | no standalone local scan is recorded for Slice 0 |

**Slice 0 structural foundation: `PASS`.**

---

## Gate A — RESEARCH_READY

Purpose: allow reliable integrated research/backtesting. This does **not** authorize paper or live trading.

### Current accepted decision

```text
GATE_A = PASS / RESEARCH-INTEGRATION ONLY
```

Authoritative accepted evidence:

- Gate A execution evidence PR `#32`
  - merge: `154b3164ce579672d601a23bbc17a485f3ebcbb1`
  - execution branch head: `633261d58a4c86d7b6d760e23660b48c471bcc31`
  - approved project source revision: `4da559bbbb569ea4f32246a40ef35f4bd8477a71`
  - artifact: `status/e7/GATE_A_LOCAL_RERUN4_20260824.md`
  - result: `127` fresh local tests / zero failure or error
- Gate A evidence review PR `#33`
  - merge: `429e8961dc4c32996e12fa7258c734571ea7d823`
  - review branch head: `e18f35b9513a4912390ed9920e98e9572be88cc7`
  - artifact: `status/e7/GATE_A_EVIDENCE_REVIEW_20260824.md`
  - disposition: `GATE_A = PASS / RESEARCH-INTEGRATION ONLY`

The accepted PASS is bounded to Gate A. It does not authorize Gate B/C/D, PAPER, SHADOW, LIVE, provider/private API activity, exchange credentials, capital exposure, or lifecycle promotion beyond existing authority.

### Historical Gate A construction criteria

The table below preserves the original construction-era baseline for audit history. Its old `Initial status` values are not the current Gate A disposition and are superseded by the accepted evidence above.

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

**Gate A current state: `PASS / RESEARCH-INTEGRATION ONLY`.**

---

## Gate B — PAPER_READY

Purpose: authorize controlled paper-trading integration only. No real order submission.

Prerequisite: Gate A PASS unless E7 records an explicit narrower dependency exception that does not weaken safety.

### Current canonical evidence state after E7-20260824-026 static preflight

| Criterion | Current status | Required evidence / blocker |
|---|---|---|
| Gate A | PASS | PR `#32` execution evidence + PR `#33` accepted evidence review |
| TradeIntent -> E5 RiskDecision boundary implemented | NOT_RUN | static implementation exists; bounded local E2/E5 verification still required |
| E5 can reject valid strategy intents | NOT_RUN | E5 fail-closed implementation/test definitions exist; local risk/safety execution required |
| ApprovedTradePlan is the only E4 strategy-originated execution input | NOT_RUN | E4 gateway statically enforces boundary; local execution/safety evidence required |
| PaperBroker conforms to broker contract | NOT_RUN | E4 `PaperBroker` + broker tests exist; approved local broker verification required |
| Partial fill semantics preserve actual quantity | NOT_RUN | E4 broker primitive exists; cross-module Paper integration definition/evidence still required |
| Required protection follows actual filled quantity | BLOCKED | Slice 3 fill -> E5 protection quantity -> E4 protection execution path is not yet materialized |
| Protection failure triggers emergency path | BLOCKED | E5 lifecycle transition exists, but integrated protection operation/failure path is not yet materialized |
| Stale/unknown market state blocks exposure | NOT_RUN | E5 static fail-closed implementation/test definitions exist; local safety execution required |
| Unknown order/position state blocks new exposure | NOT_RUN | E5 static fail-closed implementation/test definitions exist; local safety execution required |
| Drawdown/daily/position/kill-switch rules enforced | BLOCKED | E5 policy/engine contains the controls, but complete criterion-level test/evidence coverage is not yet established |
| Restart/persistence preserves required state | BLOCKED | E6 persistence is currently research Registry/CANDIDATE only; no Slice 3 risk/position/order/trade runtime persistence |
| Paper E2E closes to TradeResult and persists audit | BLOCKED | no complete Slice 3 Paper E2E implementation/test materialization yet |
| GitHub CI/Actions not used for verification | PASS | static repo inspection found no `.github` directory; policy remains hard requirement |

Preflight detail and owners are recorded in `status/e7/GATE_B_STATIC_PREFLIGHT_20260824.md`.

```text
GATE_B_STATIC_PREFLIGHT = READY_FOR_BOUNDED_NEXT_TASKS
Gate B = BLOCKED / NOT YET PASS
PAPER = UNAUTHORIZED
```

`READY_FOR_BOUNDED_NEXT_TASKS` is a planning/preflight disposition only. It does not convert any `NOT_RUN`/`BLOCKED` criterion to PASS and does not authorize PaperBroker runtime execution.

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

**Gate C current state: `BLOCKED / UNCHANGED`.**

Documentation drift note: this historical Gate C table still names Pionex, while the active Product Owner broker-target decision is OKX (`docs/architecture/BROKER_TARGET_OKX_DECISION_20260821.md`). This naming drift is non-blocking for Paper-only Gate B semantics and is intentionally deferred; `E7-20260824-026` does not broaden into Gate C/private-provider scope.

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

**Gate D current state: `BLOCKED / UNCHANGED`.**

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
