# Release Gates

> Owner: E7 Integration / Architecture / System QA / Release Engineer  
> Baseline: 2026-08-20  
> Current reconciliation: 2026-08-24 / `E7-20260824-041`  
> Policy: no gate may PASS without evidence from an allowed environment.

## Evidence status vocabulary

Canonical criterion states:

- `PASS` — required evidence exists and satisfies the criterion.
- `FAIL` — evidence shows the criterion is not satisfied.
- `BLOCKED` — prerequisite/contract/implementation/environment prevents evaluation.
- `NOT_RUN` — executable verification is required but has not run in an allowed environment.
- `NOT_APPLICABLE` — explicitly outside the evaluated slice/gate.

Hard rules:

- `BLOCKED != PASS`.
- `NOT_RUN != PASS`.
- component success never implies a later gate PASS.
- GitHub Actions/CI/runners cannot be used as project verification evidence.
- executable evidence must record local command/environment/result/revision.
- LIVE activation still requires explicit Product Owner approval even after technical readiness.

---

## Foundation — Slice 0

The accepted structural foundation remains PASS. This does not authorize research, PAPER, SHADOW, or LIVE.

---

## Gate A — RESEARCH_READY

```text
GATE_A = PASS / RESEARCH-INTEGRATION ONLY
```

Accepted evidence remains PR #32 execution evidence plus PR #33 E7 evidence review. Gate A does not authorize Gate B/C/D, PAPER, SHADOW, LIVE, provider/private APIs, credentials, or capital exposure.

---

## Gate B — PAPER_READY

Purpose: authorize controlled paper-trading integration only. No real order submission.

### Current accepted static chain

Relevant accepted prerequisites include:

- Gate B static preflight PR `#34`;
- E5 risk-limit definitions PR `#35`;
- protection chain PR `#37` through `#45`;
- close/TradeResult contract PR `#46`, merge `d070ffc752d5c37c05aa4101ebc2f6add0c1ff48`;
- E5 close producer PR `#47`, merge `e4caa0e1398f2a3cdf1209fa7bc74516f6a94d15`;
- E4 close consumer/residual-flat truth PR `#48`, merge `3f7bba953ece100d23c88b86b47df52696adb3a0`;
- E5 TradeResult builder PR `#49`, merge `a9edc5db9f31efb0c4a8a0c33d54766093c70392`;
- E7 blocker review PR `#50` / `status/e7/GATE_B_TRADE_RESULT_INTEGRATION_REVIEW_20260824.md`;
- E7 funding contract decision `E7-20260824-041`:
  - `contracts/FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md`;
  - `docs/adr/ADR-0006-funding-allocation-evidence-boundary.md`;
  - `status/e7/GATE_B_FUNDING_EVIDENCE_CONTRACT_DECISION_20260824.md`.

All close/funding executable evidence remains `NOT_RUN`.

### Canonical Gate B criteria

| Criterion | Current status | Required evidence / blocker |
|---|---|---|
| Gate A | PASS | accepted PR #32/#33 evidence |
| TradeIntent -> E5 RiskDecision boundary implemented | NOT_RUN | local E2/E5 verification still required |
| E5 can reject valid strategy intents | NOT_RUN | local risk/safety verification required |
| ApprovedTradePlan is the only E4 strategy-originated execution input | NOT_RUN | local execution/safety verification required |
| PaperBroker conforms to broker contract | NOT_RUN | approved-local broker verification required |
| Partial fill semantics preserve actual quantity | NOT_RUN | implementation/definitions exist; local evidence required |
| Required protection follows actual filled quantity | NOT_RUN | protection-v0.1 implementation/definitions exist; local evidence required |
| Protection failure triggers emergency path | NOT_RUN | real terminal truth + E5 bridge + E7 definitions exist; local evidence required |
| Stale/unknown market state blocks exposure | NOT_RUN | local safety evidence required |
| Unknown order/position state blocks new exposure | NOT_RUN | local safety/reconciliation evidence required |
| Drawdown/daily/position/kill-switch rules enforced | NOT_RUN | criterion-level definitions exist; local evidence required |
| Restart/persistence preserves required state | BLOCKED | E6 remains early Slice 2 Registry/CANDIDATE persistence only; no durable Paper Position/Action/Order/Fill/Funding/TradeResult runtime state/restart |
| Paper E2E closes to TradeResult and persists audit | BLOCKED | funding shared semantics are now defined, but E4 canonical Paper funding producer is not implemented, E5 has not yet adapted its builder to consume the shared evidence, PROTECTION_STOP lacks real same-position flat observation, E6 durable Paper persistence/audit is absent, and full E7 E2E/local evidence remains incomplete |
| GitHub CI/Actions not used for verification | PASS | hard policy remains satisfied by E7-041 |

### E7-041 funding evidence decision

```text
funding evidence shared boundary
= RESOLVED BY CONTRACT

versioning
= ADDITIVE_PROFILE_REQUIRED
schema_version = contracts-v0.1
profile = funding-allocation-v0.1

funding canonical producer
= IMPLEMENTATION_GAP / next_owner=E4

E5 shared-evidence consumer adaptation
= IMPLEMENTATION_GAP / later E5 task
```

The profile defines exact provider-neutral source/completeness/position/plan/interval/status/cost/currency/identity/conflict semantics. It forbids empty/unavailable source results from becoming zero evidence.

Canonical interval is:

```text
[TradeResult.opened_at, TradeResult.closed_at)
```

with `ZERO_CONFIRMED` requiring explicit complete zero authority, not missing rows.

The first Gate B producer is expected to be an E4-owned local versioned Paper funding model requiring no provider credentials/private API.

### Close-to-TradeResult decomposition

```text
ordinary EXIT close-to-authoritative-flat
= IMPLEMENTED_NEEDS_LOCAL_EVIDENCE / NOT_RUN

EMERGENCY_EXIT close-to-authoritative-flat
= IMPLEMENTED_NEEDS_LOCAL_EVIDENCE / NOT_RUN

ordinary/EMERGENCY final TradeResult system chain
= BLOCKED / E4 FUNDING PRODUCER + E5 CONSUMER ADAPTATION + E6 PERSISTENCE

PROTECTION_STOP -> authoritative same-position flat -> TradeResult
= BLOCKED / E4 IMPLEMENTATION_GAP
```

Key safety rules remain:

```text
OrderStatus.FILLED != flat Position proof
same-position actual_quantity=0 + CONSISTENT truth is required
flat observation >= latest exit Fill
missing fee/funding evidence cannot silently become zero
funding source must prove complete exact-interval coverage
conflicting funding evidence is not last-write-wins
```

### Current Gate B state

```text
Gate B = BLOCKED / NOT YET PASS
PAPER = UNAUTHORIZED
project executable verification = NOT_RUN / NOT REQUIRED FOR E7-041 STATIC CONTRACT DECISION
```

No executable `NOT_RUN` is converted to PASS.

---

## Gate C — SHADOW_READY

```text
BLOCKED / UNCHANGED
```

Gate B is not PASS. No provider/private scope is opened by E7-041.

---

## Gate D — LIVE_READY

```text
BLOCKED / UNCHANGED
```

Gate C is not PASS and Product Owner LIVE approval is absent. No LIVE authority changes in E7-041.

---

## Evidence record format

Executable evidence must record at minimum:

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

Never invent local test counts or results.
