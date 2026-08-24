# Release Gates

> Owner: E7 Integration / Architecture / System QA / Release Engineer  
> Baseline: 2026-08-20  
> Current reconciliation: 2026-08-24 / `E7-20260824-053`  
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

### Accepted static chain now on main / current E7 branch

Relevant accepted chain includes:

- Gate B static/risk/protection work PR `#34` through `#45`;
- close/TradeResult chain PR `#46` through `#55`;
- `position-lifecycle-projection-v0.1` contract PR `#57` / ADR-0007;
- E5 lifecycle projection producer PR `#58`;
- lifecycle vocabulary clarification PR `#60` / ADR-0008;
- E6 durable Paper runtime implementation PR `#61 / merge 42f6d015ea5c9387983a822820dde211608a249e`;
- E7 durable review PR `#62 / merge 383cc6bf622c10f441d082a36b03612a1a8f2a32`;
- E7-053 companion freshness contract:
  - `contracts/POSITION_LIFECYCLE_EXECUTION_EVIDENCE_BINDING_V0_1.md`;
  - `docs/adr/ADR-0009-position-lifecycle-execution-evidence-freshness.md`;
  - `status/e7/GATE_B_EXECUTION_LIFECYCLE_FRESHNESS_CONTRACT_DECISION_20260824.md`.

All executable verification for the current Gate B chain remains unperformed.

### Canonical Gate B criteria after E7-053

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
| Position lifecycle vocabulary | PASS STATIC / RESOLVED | PR #60/ADR-0008; not executable PASS |
| E5 lifecycle projection producer | NOT_RUN / MATERIALIZED | PR #58 accepted; executable evidence absent |
| E6 durable Paper runtime implementation | NOT_RUN / MATERIALIZED | PR #61 accepted for source integration; executable evidence absent |
| Durable E4 execution truth -> E5 lifecycle freshness contract | PASS STATIC / RESOLVED | `position-lifecycle-execution-binding-v0.1` + ADR-0009 define the shared mechanical freshness rule; not executable PASS |
| E5 execution-binding producer | BLOCKED | bounded producer adaptation required to emit one immutable companion binding for each Gate B restart-authoritative lifecycle projection |
| E6 execution-binding persistence/recovery consumer | BLOCKED | bounded mechanical persistence/recompute/compare adaptation required; E6 must not infer lifecycle |
| Durable TradeResult reference completeness | BLOCKED | separate E6 settled-contract defect from E7-052 remains; referenced OrderRequest/Fill/PositionAction graph must exist/match before READY |
| Restart/persistence preserves required state | BLOCKED | E5/E6 companion adaptation + E6 TradeResult completeness repair required; executable evidence also absent |
| Paper E2E closes to TradeResult and persists audit | BLOCKED | durable implementation chain is not complete and executable evidence is absent |
| GitHub CI/Actions not used for verification | PASS | E7-053 uses no GitHub project compute |

### E7-053 shared freshness decision

Classification:

```text
ADDITIVE_COMPANION_PROFILE
schema_version = contracts-v0.1 / unchanged
position-lifecycle-projection-v0.1 = unchanged
position-lifecycle-execution-binding-v0.1 = new companion
```

The companion binds one exact lifecycle projection to all durable E4 Position-linked reduction-order evidence currently interpreted by E5 for:

```text
PROTECTION_STOP
POSITION_EXIT
EMERGENCY_EXIT
```

For every in-scope request it covers exact OrderRequest payload identity plus the complete canonical OrderResult observation set and Fill set.

Recovery rule:

```text
current durable execution snapshot == latest E5 binding snapshot
-> execution-freshness axis current

current durable execution snapshot != latest E5 binding snapshot
-> fresh E5 interpretation required
-> old lifecycle projection cannot be restart READY
```

E6 does not infer the next lifecycle state. New evidence requires E5 to emit a new TRANSITION or REATTESTATION plus a new companion binding.

Existing raw Position re-attestation rules remain a separate required freshness axis.

### Entry path boundary

Pre-position `entry-v0.1` execution is not uniformly `position_id`-linked and is not silently joined by `trade_plan_id`. A future restart-authoritative `PENDING_ENTRY` design requires explicit E7 refinement. Until then that case is not Gate B restart READY.

### Current Gate B state

```text
Gate A = PASS / RESEARCH-INTEGRATION ONLY
execution-truth/lifecycle freshness shared contract = RESOLVED STATIC
E5 companion binding producer = BLOCKED / NOT YET MATERIALIZED
E6 companion binding consumer/recovery = BLOCKED / NOT YET MATERIALIZED
E6 TradeResult graph completeness repair = BLOCKED / NOT YET REMEDIATED
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

Gate B is not PASS. No provider/private scope is opened by E7-053.

---

## Gate D — LIVE_READY

```text
BLOCKED / UNCHANGED
```

Gate C is not PASS and Product Owner LIVE approval is absent.

---

## Future approved-local evidence format

When E5/E6 remediation is accepted and PM authorizes an exact local revision, evidence must record:

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

Minimum later commands include:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/integration -p "test_*.py" -v
python -m unittest discover -s tests/e2e -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

Never invent local results. Missing `tests/e2e` at an accepted revision is not PASS and must be materialized before the complete Gate B run.
