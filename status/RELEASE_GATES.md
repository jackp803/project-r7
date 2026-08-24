# Release Gates

> Owner: E7 Integration / Architecture / System QA / Release Engineer  
> Baseline: 2026-08-20  
> Current reconciliation: 2026-08-24 / `E7-20260824-052`  
> Policy: no gate may PASS without evidence from an allowed environment.

## Evidence status vocabulary

- `PASS` — required evidence exists and satisfies the criterion.
- `FAIL` — evidence shows the criterion is not satisfied.
- `BLOCKED` — prerequisite/contract/implementation/environment prevents evaluation.
- `NOT_RUN` — executable verification is required but has not run in an allowed environment.
- `NOT_APPLICABLE` — explicitly outside the evaluated slice/gate.

Hard rules: `BLOCKED != PASS`, `NOT_RUN != PASS`, component/static acceptance never implies a later gate PASS, and GitHub Actions/CI/runners are forbidden project verification evidence.

---

## Foundation — Slice 0

Structural foundation remains `PASS`. This is not PAPER/SHADOW/LIVE authority.

---

## Gate A — RESEARCH_READY

```text
GATE_A = PASS / RESEARCH-INTEGRATION ONLY
```

Accepted PR #32 execution evidence plus PR #33 evidence review remain authoritative. Gate A does not authorize Gate B/C/D, PAPER, SHADOW, LIVE, provider/private APIs, credentials, or capital exposure.

---

## Gate B — PAPER_READY

Purpose: controlled Paper integration only; no real order submission.

### Accepted static prerequisites now on main

Relevant accepted chain includes:

- Gate B static/risk/protection work PR `#34` through `#45`;
- close/TradeResult chain PR `#46` through `#55`;
- `position-lifecycle-projection-v0.1` contract PR `#57 / merge 5b203ea2e4a235dfb4575626f15e2409b6674c59`;
- E5 lifecycle projection producer PR `#58 / merge f5bbeaf1daef1fdeda28ea6d12482b3b26018cc8`;
- lifecycle vocabulary clarification PR `#60` + ADR-0008;
- E6 durable Paper runtime implementation PR `#61 / merge 42f6d015ea5c9387983a822820dde211608a249e`;
- E7 current review: `status/e7/GATE_B_DURABLE_PAPER_INTEGRATION_REVIEW_20260824.md`.

All executable verification for the new Gate B chain remains unperformed.

### Canonical criteria after E7-052

| Criterion | Current status | Evidence / blocker |
|---|---|---|
| Gate A | PASS | accepted PR #32/#33 evidence |
| TradeIntent -> E5 RiskDecision boundary | NOT_RUN | implementation/definitions exist; approved-local evidence required |
| E5 risk rejection and stale/unknown exposure gates | NOT_RUN | implementation/definitions exist; approved-local evidence required |
| ApprovedTradePlan-only E4 strategy execution boundary | NOT_RUN | implementation/definitions exist; approved-local evidence required |
| PaperBroker contract / partial-fill semantics | NOT_RUN | implementation/definitions exist; approved-local evidence required |
| Required protection follows actual filled quantity | NOT_RUN | protection chain exists; approved-local evidence required |
| Protection failure triggers emergency path | NOT_RUN | terminal truth + E5 bridge + E7 definitions exist; approved-local evidence required |
| Drawdown/daily/position/kill-switch rules | NOT_RUN | criterion definitions exist; approved-local evidence required |
| Ordinary EXIT in-memory -> TradeResult | NOT_RUN | accepted real E4/E5/Paper/funding path exists |
| EMERGENCY_EXIT in-memory -> TradeResult | NOT_RUN | accepted real E4/E5/Paper/funding path exists |
| Full verified PROTECTION_STOP -> TradeResult | NOT_RUN | accepted real verification/fill/flat/funding/result path exists |
| Funding producer -> consumer compatibility | NOT_RUN | canonical E4 evidence directly consumed by E5; local evidence required |
| Position lifecycle ordering/profile | PASS STATIC / RESOLVED | PR #57/ADR-0007; not executable PASS |
| Position lifecycle vocabulary | PASS STATIC / RESOLVED | PR #60/ADR-0008; unknown values fail closed; not executable PASS |
| E5 lifecycle projection producer | NOT_RUN / MATERIALIZED | PR #58 accepted; executable evidence absent |
| E6 durable Paper runtime implementation | NOT_RUN / MATERIALIZED | PR #61 accepted for source integration; executable evidence absent |
| Durable E4 execution truth -> E5 lifecycle freshness | BLOCKED | current shared projection has no authoritative execution-evidence freshness/binding; later protection `PARTIALLY_FILLED` or `CANCELED` truth can coexist with older `OPEN_PROTECTED` projection while E6 recovery can still report READY |
| Durable TradeResult reference completeness | BLOCKED | E6 does not require TradeResult referenced OrderRequest/Fill/PositionAction rows to exist/match before READY recovery; settled-contract implementation defect |
| Restart/persistence preserves required state | BLOCKED | component durability exists but coherent restart authority is blocked by the above semantic/implementation gaps; executable evidence also absent |
| Paper E2E closes to TradeResult and persists audit | BLOCKED | durable integration is not statically coherent yet and executable evidence is absent |
| GitHub CI/Actions not used for verification | PASS | E7-052 used no GitHub project compute |

### E7-052 blocker disposition

Primary blocker:

```text
classification = CONTRACT_OR_SEMANTIC_GAP
boundary = newer E4 OrderResult/Fill truth vs latest E5 lifecycle projection freshness
```

Current E5 semantics require lifecycle re-interpretation after relevant newer protection execution truth. Current E6 recovery only treats newer raw Position observations as lifecycle-stale and only treats UNKNOWN/RECONCILIATION_REQUIRED or degraded OrderResult truth as reconciliation-required. It therefore lacks shared authority to know whether a later healthy `PARTIALLY_FILLED`, `FILLED`, `CANCELED`, `EXPIRED`, or other execution observation has already been consumed by E5.

E6 must not repair this by importing/copying the E5 transition table or by inventing a private status-to-lifecycle rule.

Secondary blocker:

```text
classification = IMPLEMENTATION_DEFECT_UNDER_SETTLED_CONTRACT
boundary = E6 durable TradeResult referenced-object completeness
```

Detailed evidence and E7 blocker definitions are in:

`status/e7/GATE_B_DURABLE_PAPER_INTEGRATION_REVIEW_20260824.md`

### Current Gate B state

```text
Gate A = PASS / RESEARCH-INTEGRATION ONLY
E5 lifecycle projection producer = MATERIALIZED / executable NOT_RUN
E6 durability implementation = MATERIALIZED / executable NOT_RUN
Restart/persistence executable criterion = BLOCKED
Paper E2E durable audit executable criterion = BLOCKED
READY_FOR_APPROVED_LOCAL_GATE_B_VERIFICATION = NO
Gate B = BLOCKED / NOT YET PASS
PAPER = UNAUTHORIZED
project executable verification = NOT_RUN
```

No static finding converts an executable criterion to PASS.

---

## Gate C — SHADOW_READY

```text
BLOCKED / UNCHANGED
```

Gate B is not PASS. No provider/private scope is opened by E7-052.

---

## Gate D — LIVE_READY

```text
BLOCKED / UNCHANGED
```

Gate C is not PASS and Product Owner LIVE approval is absent.

---

## Future approved-local evidence format

When the semantic/implementation blockers are remediated and PM authorizes exact local verification, evidence must record:

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

Never invent local results.
