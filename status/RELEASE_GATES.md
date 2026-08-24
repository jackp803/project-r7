# Release Gates

> Owner: E7 Integration / Architecture / System QA / Release Engineer  
> Baseline: 2026-08-20  
> Current reconciliation: 2026-08-24 / `E7-20260824-047`  
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

### Accepted static prerequisites

Relevant accepted prerequisites include:

- Gate B static preflight PR `#34`;
- E5 risk-limit definitions PR `#35`;
- protection chain PR `#37` through `#45`;
- close/TradeResult contract PR `#46`;
- E5 close producer PR `#47`;
- E4 close consumer/residual-flat truth PR `#48`;
- E5 TradeResult builder PR `#49`;
- funding-allocation-v0.1 contract PR `#51`;
- E4 canonical Paper funding producer PR `#52`;
- E5 canonical funding consumer PR `#53`;
- E4 PROTECTION_STOP same-position full-fill flat truth PR `#54`;
- E7 complete in-memory Paper integration PR `#55 / merge d6302eb89b9319bfd00d5c26e315bd2fe1923b65`;
- E6 durability blocker PR `#56 / merge 649ae522b71f3992e48b81882662b6d7d0222324`;
- E7 lifecycle durability contract decision `E7-20260824-047`:
  - `contracts/POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md`;
  - `docs/adr/ADR-0007-position-lifecycle-projection-ordering.md`;
  - `status/e7/GATE_B_POSITION_LIFECYCLE_ORDERING_CONTRACT_DECISION_20260824.md`.

All relevant executable verification remains `NOT_RUN`.

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
| Ordinary EXIT in-memory close -> canonical TradeResult | NOT_RUN | statically materialized through real E4/E5/Paper/funding path; approved-local evidence required |
| EMERGENCY_EXIT in-memory close -> canonical TradeResult | NOT_RUN | statically materialized through real E4/E5/Paper/funding path; approved-local evidence required |
| Full verified PROTECTION_STOP trigger -> canonical TradeResult | NOT_RUN | statically materialized through real verification/fill/flat/funding/result path; approved-local evidence required |
| Funding producer -> consumer compatibility | NOT_RUN | E4 canonical funding evidence is directly consumed by E5 with exact identity/audit binding; approved-local evidence required |
| Position lifecycle durability ordering contract/rule | PASS STATIC / RESOLVED | `position-lifecycle-projection-v0.1` + ADR-0007 resolve the shared ordering/authority semantic gap; this is not executable PASS evidence |
| E5 durability-eligible Position lifecycle projection producer | BLOCKED | bounded E5 implementation is required to emit GENESIS/TRANSITION/REATTESTATION profiled Position projections; no E4 change required |
| Restart/persistence preserves required state | BLOCKED | E6 cannot implement safe Paper current Position/restart until the E5 profiled lifecycle projection producer exists; E6 Paper runtime durability remains unimplemented |
| Paper E2E closes to TradeResult and persists audit | BLOCKED | in-memory close-to-TradeResult is statically materialized, but E5 durability projection producer, E6 durable runtime persistence/restart/audit, and approved-local E2E evidence remain absent |
| GitHub CI/Actions not used for verification | PASS | hard policy remains satisfied by E7-047 |

### E7-047 lifecycle durability decision

PR #56 blocker diagnosis is confirmed.

The baseline allows legitimate lifecycle-only changes with the same E4 `broker_state_observed_at`, so storage arrival order cannot decide authoritative Position lifecycle.

Classification:

```text
ADDITIVE_PROFILE_REQUIRED
schema_version = contracts-v0.1
profile = position-lifecycle-projection-v0.1
```

Authority remains:

```text
E4 broker facts/order              -> broker_state_observed_at
E5 lifecycle interpretation/order  -> lifecycle_revision
E6 persistence/replay              -> no domain inference
```

Multiple E5 lifecycle revisions may share one broker observation.

Profile ordering rules include:

```text
revision 0 = GENESIS
revision n+1 = exact predecessor + 1
TRANSITION = explicit PositionEvent changes lifecycle
REATTESTATION = same lifecycle explicitly bound by E5 to newer/equal broker observation
same revision + identical ID/payload = idempotent replay
same revision + changed payload = conflict
revision gap / predecessor mismatch = cannot advance
higher lifecycle revision with older broker anchor = stale/invalid
```

A newer E4 broker observation without a corresponding E5 projection/reattestation must not be merged by E6 with an older lifecycle state to manufacture a current canonical Position.

### Producer impact

```text
E4 adaptation = NONE
E5 adaptation = REQUIRED / next dependency
E6 durability = AFTER E5 producer
```

Accepted PR #55 remains valid for its non-durable in-memory scope but is not restart-authoritative durable Position evidence until an E5 producer emits the new profile.

### Current Gate B state

```text
Position lifecycle durability contract/rule = RESOLVED STATIC
E5 lifecycle projection producer = BLOCKED / NOT YET MATERIALIZED
Restart/persistence = BLOCKED
Paper E2E durable audit = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER = UNAUTHORIZED
project executable verification = NOT_RUN
```

No executable `NOT_RUN` is converted to PASS by E7-047.

---

## Gate C — SHADOW_READY

```text
BLOCKED / UNCHANGED
```

Gate B is not PASS. No provider/private scope is opened by E7-047.

---

## Gate D — LIVE_READY

```text
BLOCKED / UNCHANGED
```

Gate C is not PASS and Product Owner LIVE approval is absent. No LIVE authority changes in E7-047.

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
