# Release Gates

> Owner: E7 Integration / Architecture / System QA / Release Engineer  
> Baseline: 2026-08-20  
> Current reconciliation: 2026-08-24 / `E7-20260824-036`  
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

The accepted structural foundation remains PASS. This does not itself authorize research, PAPER, SHADOW, or LIVE.

---

## Gate A — RESEARCH_READY

```text
GATE_A = PASS / RESEARCH-INTEGRATION ONLY
```

Accepted evidence remains PR #32 execution evidence plus PR #33 E7 evidence review. Gate A does not authorize Gate B/C/D, PAPER, SHADOW, LIVE, provider/private API activity, credentials, or capital exposure.

---

## Gate B — PAPER_READY

Purpose: authorize controlled paper-trading integration only. No real order submission.

### Current accepted static chain

Relevant accepted prerequisites now include:

- Gate B static preflight PR `#34`;
- E5 risk-limit definitions PR `#35`;
- protection contract PR `#37`;
- E5 protection producer PR `#38`;
- E4 protection consumer PR `#39`;
- E7 protection integration PR `#40`;
- E5 protection-result bridge PR `#41`;
- E7 protection lifecycle review PR `#42`;
- E4 PaperBroker terminal truth PR `#43`;
- E7 protection failure/loss integration PR `#44`;
- E4 protection Fill-lineage PR `#45`, merge `e18fc08d110b0addb77229b1bf47cd7632548427`;
- E7 close/TradeResult contract decision `E7-20260824-036`:
  - `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`;
  - `docs/adr/ADR-0005-close-authority-and-trade-result-boundary.md`;
  - `status/e7/GATE_B_CLOSE_TRADE_RESULT_CONTRACT_DECISION_20260824.md`.

The close-to-TradeResult contract classification is:

```text
ADDITIVE_PROFILE_REQUIRED / MATERIALIZED
schema_version = contracts-v0.1
```

This resolves the shared semantic boundary only. It does not implement E5/E4/E6 production paths and does not provide executable evidence.

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
| Protection failure triggers emergency path | NOT_RUN | real PaperBroker terminal truth + E5 bridge + E7 definitions exist; local evidence required |
| Stale/unknown market state blocks exposure | NOT_RUN | local safety evidence required |
| Unknown order/position state blocks new exposure | NOT_RUN | local safety/reconciliation evidence required |
| Drawdown/daily/position/kill-switch rules enforced | NOT_RUN | criterion-level definitions exist; local evidence required |
| Restart/persistence preserves required state | BLOCKED | E6 remains early Slice 2 Registry/CANDIDATE persistence only; no Paper risk/position/action/order/fill/result runtime persistence/restart |
| Paper E2E closes to TradeResult and persists audit | BLOCKED | protection Fill lineage is now materialized, but close-v0.1 E5 producer, E4 consumer, E5 trade-result-v0.1 builder, E6 durable runtime/audit and full E7 Paper E2E are not yet implemented |
| GitHub CI/Actions not used for verification | PASS | hard policy remains satisfied by this static task |

### Close-to-TradeResult blocker decomposition

The prior Fill-lineage gap is closed by PR #45.

The remaining sequential implementation chain is now explicit:

```text
E5 close-v0.1 EXIT / EMERGENCY_EXIT producer + lifecycle/reasons
-> E4 close-v0.1 MARKET reduce-only consumer + close Fill/residual Position truth
-> E5 authoritative-flat POSITION_CLOSED + trade-result-v0.1 builder
-> E6 durable Paper runtime persistence/restart/audit
-> E7 full Paper E2E/safety definitions
-> approved-local Gate B verification
```

Key safety rule:

```text
OrderStatus.FILLED != proof of flat Position
```

Final closure requires exact same-position normalized truth with `actual_quantity=0` and `reconciliation_status=CONSISTENT` at/after the latest included exit Fill.

### Current Gate B state

```text
Gate B = BLOCKED / NOT YET PASS
PAPER = UNAUTHORIZED
project executable verification = NOT_RUN / NOT REQUIRED FOR E7-036 STATIC CONTRACT DECISION
```

No existing `NOT_RUN` is converted to PASS by this task.

---

## Gate C — SHADOW_READY

Gate C remains:

```text
BLOCKED / UNCHANGED
```

Prerequisite Gate B is not PASS. The historical Pionex wording remains documentation drift; active V1 provider target is OKX. E7-036 does not broaden into provider/private work.

---

## Gate D — LIVE_READY

Gate D remains:

```text
BLOCKED / UNCHANGED
```

Gate C is not PASS, operational/audit/security evidence remains incomplete, and Product Owner LIVE approval is absent. No LIVE authority changes in E7-036.

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
