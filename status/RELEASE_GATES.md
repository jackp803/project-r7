# Release Gates

> Owner: E7 Integration / Architecture / System QA / Release Engineer  
> Baseline: 2026-08-20  
> Current reconciliation: 2026-08-24 / `E7-20260824-045`  
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
- close/TradeResult contract PR `#46`;
- E5 close producer PR `#47`, merge `e4caa0e1398f2a3cdf1209fa7bc74516f6a94d15`;
- E4 close consumer/residual-flat truth PR `#48`, merge `3f7bba953ece100d23c88b86b47df52696adb3a0`;
- E5 TradeResult builder PR `#49`, merge `a9edc5db9f31efb0c4a8a0c33d54766093c70392`;
- E7 close-to-TradeResult blocker review PR `#50`;
- funding-allocation-v0.1 contract PR `#51`, merge `6950824f6e2e7842718fc29f5e0808f9d8e7b04e`;
- E4 canonical Paper ZERO_CONFIRMED producer PR `#52`, merge `844395fce0504573b5ee4932e3aca09101998080`;
- E5 canonical funding consumer PR `#53`, merge `84d12e4b7ef3638af6690d38f07ce27d10c54fcd`;
- E4 PROTECTION_STOP same-position full-fill flat truth PR `#54`, merge `62605e7abc86f13a1f3102d057aece3d72d465f1`;
- E7 current integration review: `status/e7/GATE_B_PAPER_TRADE_RESULT_INTEGRATION_REVIEW_20260824.md`.

All new Gate B executable evidence remains `NOT_RUN`.

### Canonical Gate B criteria

| Criterion | Current status | Required evidence / blocker |
|---|---|---|
| Gate A | PASS | accepted PR #32/#33 evidence |
| TradeIntent -> E5 RiskDecision boundary implemented | NOT_RUN | approved-local E2/E5 verification still required |
| E5 can reject valid strategy intents | NOT_RUN | approved-local risk/safety verification required |
| ApprovedTradePlan is the only E4 strategy-originated execution input | NOT_RUN | approved-local execution/safety verification required |
| PaperBroker conforms to broker contract | NOT_RUN | approved-local broker verification required |
| Partial fill semantics preserve actual quantity | NOT_RUN | implementation/definitions exist; local evidence required |
| Required protection follows actual filled quantity | NOT_RUN | protection-v0.1 implementation/definitions exist; local evidence required |
| Protection failure triggers emergency path | NOT_RUN | real terminal truth + E5 bridge + E7 definitions exist; local evidence required |
| Stale/unknown market state blocks exposure | NOT_RUN | approved-local safety evidence required |
| Unknown order/position state blocks new exposure | NOT_RUN | approved-local safety/reconciliation evidence required |
| Drawdown/daily/position/kill-switch rules enforced | NOT_RUN | criterion-level definitions exist; local evidence required |
| Ordinary EXIT in-memory close -> canonical TradeResult | NOT_RUN | E5 authority -> E4 MARKET reduce-only -> real Paper Fill -> authoritative same-position flat -> E4 funding-allocation-v0.1 -> E5 TradeResult is statically materialized; approved-local evidence required |
| EMERGENCY_EXIT in-memory close -> canonical TradeResult | NOT_RUN | distinct emergency authority/reasons/order role survive the same real in-memory chain; approved-local evidence required |
| Full verified PROTECTION_STOP trigger -> canonical TradeResult | NOT_RUN | real protection verification -> real full protective Fill -> PR #54 same-position flat truth -> E4 funding evidence -> E5 TradeResult is statically materialized; approved-local evidence required |
| Funding producer -> consumer compatibility | NOT_RUN | PR #52 canonical E4 funding object is directly consumed by PR #53 E5 builder with exact identity/audit binding; approved-local evidence required |
| Restart/persistence preserves required state | BLOCKED | E6 remains early Slice 2 Registry persistence only; no durable Paper Position/Action/Order/Fill/Funding/TradeResult state graph or restart recovery |
| Paper E2E closes to TradeResult and persists audit | BLOCKED | in-memory close-to-TradeResult is statically materialized, but E6 durable runtime persistence/restart/audit and approved-local E2E evidence are absent |
| GitHub CI/Actions not used for verification | PASS | hard policy remains satisfied by E7-045 |

### E7-045 in-memory Paper integration disposition

```text
ordinary EXIT in-memory close -> TradeResult
= IMPLEMENTED_NEEDS_LOCAL_EVIDENCE / NOT_RUN

EMERGENCY_EXIT in-memory close -> TradeResult
= IMPLEMENTED_NEEDS_LOCAL_EVIDENCE / NOT_RUN

full verified PROTECTION_STOP trigger -> TradeResult
= IMPLEMENTED_NEEDS_LOCAL_EVIDENCE / NOT_RUN

funding producer -> consumer
= IMPLEMENTED_NEEDS_LOCAL_EVIDENCE / NOT_RUN

CONTRACT_OR_SEMANTIC_GAP = NO
E4/E5 IMPLEMENTATION_GAP IN THESE THREE IN-MEMORY PATHS = NO
```

The current positive chains use actual E4/E5 production surfaces and do not substitute synthetic `OrderResult`, `Fill`, flat Position or funding evidence.

### Key safety rules retained

```text
OrderStatus.FILLED != flat Position proof
same-position actual_quantity=0 + CONSISTENT truth is required
PROTECTION_STOP must be verified before protected closure semantics are claimed
partial / zero / failed / ambiguous protection cannot finalize normally
missing/corrupt funding evidence cannot silently become zero
funding source must prove complete exact-interval coverage
calculated_at does not change funding financial identity
quantity conservation and explicit fee evidence remain required
```

### Remaining Gate B structural blocker

Current E6 production is still research Registry persistence only. The next bounded persistence/restart/audit boundary must durably preserve, without recomputation or authority invention, exact identities/payloads for at least:

```text
strategy/version
RiskDecision / ApprovedTradePlan
Position + lifecycle/reconciliation projection
PositionAction
OrderRequest / OrderResult / reconciliation state
Fill
FundingAllocationEvidence
TradeResult
```

Funding replay/conflict behavior must preserve:

```text
same funding_evidence_id + identical identity material -> idempotent replay
same funding_evidence_id + changed identity material -> corruption/conflict
same funding lineage key + different valid evidence IDs -> reconciliation conflict, never last-write-wins
existing TradeResult funding binding + later conflict -> no silent historical rewrite
```

### Current Gate B state

```text
Gate B = BLOCKED / NOT YET PASS
PAPER = UNAUTHORIZED
project executable verification = NOT_RUN
```

No executable `NOT_RUN` is converted to PASS by E7-045.

---

## Gate C — SHADOW_READY

```text
BLOCKED / UNCHANGED
```

Gate B is not PASS. No provider/private scope is opened by E7-045.

---

## Gate D — LIVE_READY

```text
BLOCKED / UNCHANGED
```

Gate C is not PASS and Product Owner LIVE approval is absent. No LIVE authority changes in E7-045.

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
