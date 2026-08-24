# Release Gates

> Owner: E7 Integration / Architecture / System QA / Release Engineer  
> Baseline: 2026-08-20  
> Current reconciliation: 2026-08-24 / `E7-20260824-057`  
> Policy: no gate may PASS without evidence from an allowed environment.

## Evidence status vocabulary

- `PASS` — required evidence exists and satisfies the criterion.
- `FAIL` — evidence shows the criterion is not satisfied.
- `BLOCKED` — prerequisite/contract/implementation/environment prevents evaluation.
- `NOT_RUN` — executable verification is required but has not run in an allowed environment.
- `NOT_APPLICABLE` — explicitly outside the evaluated slice/gate.

Hard rules: `BLOCKED != PASS`, `NOT_RUN != PASS`, static source acceptance never implies executable PASS, and GitHub Actions/CI/runners are forbidden project verification evidence.

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

### Accepted source chain through E7-057

Relevant accepted chain includes Gate B PR `#34` through `#65`, including:

- in-memory close-to-TradeResult PR `#55`;
- lifecycle projection/vocabulary PR `#57/#58/#60`;
- E6 durability PR `#61`;
- E7 blocker review PR `#62`;
- execution-freshness companion PR `#63`;
- E5 companion producer PR `#64 / merge d36d1897ccb4ee06ed9a2dbf981dc4814d7a8541`;
- E6 binding consumer + TradeResult reference remediation PR `#65 / merge 43eeb2bba236a12d641a30a807eb120990b6e595`;
- E7-057 static re-review `status/e7/GATE_B_DURABLE_PAPER_REREVIEW_20260824.md`.

All Gate B executable verification remains unperformed.

### Canonical Gate B criteria after E7-057

| Criterion | Current status | Evidence / remaining requirement |
|---|---|---|
| Gate A | PASS | accepted PR #32/#33 evidence |
| TradeIntent -> E5 RiskDecision boundary | NOT_RUN | implementation/definitions exist; approved-local evidence required |
| E5 risk rejection and stale/unknown exposure gates | NOT_RUN | implementation/definitions exist; approved-local evidence required |
| ApprovedTradePlan-only E4 strategy execution boundary | NOT_RUN | implementation/definitions exist; approved-local evidence required |
| PaperBroker contract / partial-fill semantics | NOT_RUN | implementation/definitions exist; approved-local evidence required |
| Required protection follows actual filled quantity | NOT_RUN | implementation/definitions exist; approved-local evidence required |
| Protection failure triggers emergency path | NOT_RUN | implementation/definitions exist; approved-local evidence required |
| Drawdown/daily/position/kill-switch rules | NOT_RUN | implementation/definitions exist; approved-local evidence required |
| Ordinary EXIT -> TradeResult durable chain | NOT_RUN | real E4/E5/Paper/funding/E6 definition now materialized |
| EMERGENCY_EXIT -> TradeResult durable chain | NOT_RUN | real E4/E5/Paper/funding/E6 definition now materialized |
| Full verified PROTECTION_STOP -> TradeResult durable chain | NOT_RUN | real verify/fill/flat/funding/result/persistence definition now materialized |
| Funding producer -> consumer compatibility | NOT_RUN | source/consumer/persistence semantics statically coherent; local evidence required |
| Position lifecycle ordering/profile | PASS STATIC / RESOLVED | PR #57/ADR-0007; not executable PASS |
| Position lifecycle vocabulary | PASS STATIC / RESOLVED | PR #60/ADR-0008; not executable PASS |
| E5 lifecycle projection producer | NOT_RUN / MATERIALIZED | PR #58 |
| Durable E4 execution truth -> E5 lifecycle freshness contract | PASS STATIC / RESOLVED | PR #63/ADR-0009; not executable PASS |
| E5 execution-binding producer | NOT_RUN / MATERIALIZED | PR #64 |
| E6 durable Paper runtime + binding consumer | NOT_RUN / MATERIALIZED | PR #61/#65 |
| Durable TradeResult referenced-object completeness | NOT_RUN / MATERIALIZED | PR #65 statically closes E7-052 defect; executable evidence absent |
| Restart/persistence preserves required state | NOT_RUN | no remaining known static blocker; approved-local restart matrix required |
| Paper E2E closes to TradeResult and persists audit | NOT_RUN | E7 durable E2E definition materialized; approved-local evidence required |
| GitHub CI/Actions not used for verification | PASS | hard policy remains satisfied by E7-057 |

### Static disposition

The two E7-052 blockers are now statically remediated:

```text
execution-truth/lifecycle freshness false READY = RESOLVED STATIC
TradeResult referenced-object completeness       = RESOLVED STATIC
```

PR #64 produces the exact immutable companion binding. PR #65 persists/recomputes the same fixed shared execution snapshot and refuses stale/missing/conflicting bindings without importing E5 lifecycle semantics.

PR #65 also requires the declared TradeResult request/fill/action reference graph and settled PositionAction lineage to exist/match; invalid/corrupt recovered graphs cannot remain READY.

No new shared contract or domain implementation blocker was found in E7-057 for the reviewed Gate B durable slice.

### Current Gate B state

```text
Gate A = PASS / RESEARCH-INTEGRATION ONLY
E5 lifecycle projection producer = MATERIALIZED / executable NOT_RUN
E5 lifecycle execution-binding producer = MATERIALIZED / executable NOT_RUN
E6 durability + binding consumer + TradeResult completeness = MATERIALIZED / executable NOT_RUN
Restart/persistence executable criterion = NOT_RUN
Paper E2E durable audit executable criterion = NOT_RUN
READY_FOR_APPROVED_LOCAL_GATE_B_VERIFICATION = YES
Gate B = BLOCKED / NOT YET PASS
PAPER = UNAUTHORIZED
project executable verification = NOT_RUN
```

`READY_FOR_APPROVED_LOCAL_GATE_B_VERIFICATION` means source/contracts/test definitions are statically coherent enough for the next separately authorized local verification task. It is **not** Gate B PASS and does not authorize PAPER.

### Required later local matrix

After PM explicitly authorizes an exact accepted revision:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/strategy -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/platform -p "test_*.py" -v
python -m unittest discover -s tests/registry -p "test_*.py" -v
python -m unittest discover -s tests/integration -p "test_*.py" -v
python -m unittest discover -s tests/e2e -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

No result from these commands exists yet.

---

## Gate C — SHADOW_READY

```text
BLOCKED / UNCHANGED
```

Gate B is not PASS. No provider/private scope is opened by E7-057.

---

## Gate D — LIVE_READY

```text
BLOCKED / UNCHANGED
```

Gate C is not PASS and Product Owner LIVE approval is absent.

---

## Future approved-local evidence format

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
