# E5 Handoff — Risk / Position Pre-Integration Skeleton

## Handoff

**From:** E5 / Risk Management & Position Lifecycle Engineer  
**To:** E7 / Integration Engineer  
**Branch:** `agent/e5-risk-position`  
**Commit(s):** branch HEAD containing this handoff  
**Date:** 2026-08-20

### 1. Objective

Prepare the bounded E5 safety skeleton for `TradeIntent -> RiskDecision -> ApprovedTradePlan` plus a fail-closed position lifecycle state machine, without changing shared contracts or claiming executable E2/E4 integration.

### 2. What changed

- added explicit versioned `RiskPolicy` with no production capital-risk defaults;
- added canonical `contracts-v0.1` TradeIntent validation and fail-closed risk gating;
- added auditable `RiskDecision` generation;
- added guarded `ApprovedTradePlan` generation only from `APPROVE` decisions;
- added canonical position lifecycle states/transitions;
- made entry fill explicitly become `OPEN_UNPROTECTED` before verified protection;
- made protection failure/loss enter emergency handling;
- made unknown state enter reconciliation and block safe-open claims/new exposure;
- added local-only unit/safety test definitions.

### 3. Files changed

- `src/risk/__init__.py`
- `src/risk/policy.py`
- `src/risk/engine.py`
- `src/position/__init__.py`
- `src/position/state_machine.py`
- `tests/risk/test_risk_engine.py`
- `tests/position/test_state_machine.py`
- `tests/safety/test_e5_fail_closed.py`
- `docs/risk/E5_RISK_POSITION_SKELETON.md`
- `status/E5_RISK_POSITION_HANDOFF.md`

### 4. Contracts consumed

- `contracts-v0.1` `TradeIntent`
- `contracts-v0.1` `RiskDecision`
- `contracts-v0.1` `ApprovedTradePlan`
- `contracts-v0.1` `Position` lifecycle states
- `contracts-v0.1` `RiskState` fail-closed semantics
- ADR-0001 Risk -> ApprovedTradePlan -> Execution boundary

### 5. Contracts produced or changed

`NONE`.

The nested `entry_instruction` / `protection_instruction` mapping in the skeleton is explicitly provisional E5 serialization and is not asserted as a new shared contract. E7/E4 review is required before treating that nested shape as stable execution semantics.

### 6. Local verification

Result: `NOT_RUN`

Reason: this GPT session has repository collaboration access but no Product-Owner-approved local project execution environment. GitHub-hosted execution is forbidden.

Required local commands from repository root (PowerShell):

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/risk -p "test_*.py"
python -m unittest discover -s tests/position -p "test_*.py"
python -m unittest discover -s tests/safety -p "test_*.py"
```

### 7. Known limitations

- E2 currently exposes executable `Signal` semantics on its branch; executable `TradeIntent` production is not yet integrated here.
- E4 executable broker branch/interface implementation is not yet available to this skeleton.
- E6 persistence observed during preparation is design-only; restart-safe risk/kill-switch persistence is therefore not implemented here.
- position sizing is represented as an explicit `RiskProposal` input; the sizing algorithm itself is deferred.
- revenge-size comparison, stop-widening modification logic, break-even, trailing, structure exit, and time-stop action generation remain deferred.
- no PAPER/LIVE authorization is added.

### 8. Dependencies / blockers

- E2: executable canonical TradeIntent producer/adapter.
- E4: broker/account/order/position interfaces and final ApprovedTradePlan instruction semantics.
- E6: durable risk-state / kill-switch / lifecycle persistence and restart reconstruction.
- E7: review of provisional instruction substructure and future cross-module integration.
- Product Owner: concrete policy values before any non-test risk policy is considered operational.

### 9. Required next action

E7 should statically review this skeleton for `contracts-v0.1` compatibility and keep Gate B criteria `BLOCKED`/`NOT_RUN` until local executable integration evidence exists.

### 10. Security / secrets

- no real API key, API secret, token, credential, password, private key, or live `.env` value was added;
- test data is synthetic;
- no secret is required by this skeleton.

### 11. GitHub compute policy

- no GitHub Actions workflow was created or used;
- no GitHub-hosted or GitHub-triggered runner was used;
- no project code/test was executed on GitHub infrastructure.

### 12. Live-trading impact

This change does **not** enable LIVE or PAPER execution. It adds safety gating structure only. Any future execution remains subject to E4/E7 release gates and Product Owner authorization.

Kill-switch behavior in this skeleton: active kill switch always rejects new exposure; there is no automatic reset path.

Restart assumption: no restart safety claim is made until E6 durable persistence/recovery interfaces exist and local restart tests pass.

### 13. Codex bug ticket, if applicable

`NOT_APPLICABLE` — no locally reproduced bounded implementation bug has been established.
