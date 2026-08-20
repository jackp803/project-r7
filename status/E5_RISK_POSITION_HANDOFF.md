# E5 Handoff — Risk / Position Pre-Integration Skeleton

## Handoff

**From:** E5 / Risk Management & Position Lifecycle Engineer  
**To:** E7 / Integration Engineer  
**Branch:** `agent/e5-risk-position`  
**Task:** `E5-20260820-002`  
**Finding:** `E5-RISK-UNKNOWN-001`  
**Date:** 2026-08-20

### 1. Objective

Correct the E7 blocking finding where contradictory required-state status strings and companion booleans could be interpreted permissively, while preserving the bounded `TradeIntent -> RiskDecision -> ApprovedTradePlan` authority chain and existing fail-closed position lifecycle.

### 2. Branch synchronization

Before correction, `agent/e5-risk-position` was diverged from `main` (E5 ahead, main advanced with coordination/review work).

The branch was synchronized without force rewriting history:

- latest main synchronized: `4c531adc575ddd43f095ab8eabba3cae62ecc7b2`
- synchronization merge commit: `7afc026e8f3fdce7bd7efca7e955c841a0173da1`
- method: merge commit with existing E5 history preserved; no rebase/force update.

### 3. What changed

- required market/account/order/position summary statuses now have explicit E5-local safe allowlists;
- any unrecognized or non-safe required status fails closed even when its companion boolean says fresh/known;
- canonical/recognized `UNKNOWN`, `STALE`, `DEGRADED`, `UNSAFE`, `MISMATCH`, and `RECONCILIATION_REQUIRED`-type states therefore cannot be interpreted as permission for exposure;
- contradictory status/boolean combinations produce deterministic contradiction reason codes;
- existing boolean-only fail-closed checks remain intact;
- `build_approved_trade_plan` now re-checks RiskDecision market/account/position status fields before emitting a plan, preventing a forged `APPROVE` object with unsafe state from being converted into execution authority;
- no position-lifecycle transitions were changed;
- no production risk-policy values, sizing logic, broker logic, PAPER/SHADOW/LIVE authority, or shared contracts were added.

The safe summary tokens are E5-local validation semantics only, not new shared-contract enums. Provisional `entry_instruction` / `protection_instruction` nesting remains provisional and unstabilized.

### 4. Files changed for finding correction

- `src/risk/engine.py`
- `tests/safety/test_e5_fail_closed.py`
- `status/E5_RISK_POSITION_HANDOFF.md`
- `coordination/E5/STATUS.md` is updated separately as the task mailbox status.

No `src/position/**`, `contracts/**`, E4, or E6 implementation files were changed for this finding.

### 5. Contracts consumed

- `contracts-v0.1` global fail-closed rule;
- `MarketSnapshot`: stale/unknown provider state must map to non-healthy state and consumers may not turn stale into healthy;
- `RiskDecision`: approval impossible while required market/account/order/position state is stale or unknown;
- `OrderResult`: `UNKNOWN` / `RECONCILIATION_REQUIRED` represent unresolved broker truth;
- `Position.reconciliation_status`: `CONSISTENT | UNKNOWN | MISMATCH | RECONCILIATION_REQUIRED`;
- `RiskState`: `DEGRADED`, `LOCKED`, and `UNKNOWN` are not normal exposure-permission states;
- `ApprovedTradePlan`: may exist only from an E5-approved decision.

### 6. Contracts produced or changed

`NONE`.

### 7. Finding disposition

`E5-RISK-UNKNOWN-001`: **STATIC_SOURCE_CORRECTED / EXECUTABLE_NOT_RUN**.

Static/source correction covers at minimum:

- `account_state_status="UNKNOWN"` + `account_state_known=True` -> `REJECT`;
- `order_state_status="UNKNOWN"` + `order_state_known=True` -> `REJECT`;
- `position_state_status="UNKNOWN"` + `position_state_known=True` -> `REJECT`;
- unsafe/stale/degraded market status + `market_data_fresh=True` -> `REJECT`;
- reconciliation-required/mismatch required state -> `REJECT`;
- rejected/unsafe state cannot produce an `ApprovedTradePlan`;
- forged `APPROVE` with unsafe RiskDecision market/account/position state is rejected by plan construction.

### 8. Local verification

Result: `NOT_RUN`

Reason: this GPT session has repository collaboration access but no Product-Owner-approved local project execution environment. GitHub-hosted execution is forbidden.

Required local commands from repository root on Windows PowerShell:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/risk -p "test_*.py"
python -m unittest discover -s tests/position -p "test_*.py"
python -m unittest discover -s tests/safety -p "test_*.py"
```

No executable result is claimed from static review alone.

### 9. Known limitations

- E2/E4 executable integration remains outside this correction task;
- E6 durable risk/kill-switch/restart persistence remains outside this correction task;
- position sizing remains represented by explicit `RiskProposal` input;
- revenge-size comparison, stop-widening modification logic, break-even, trailing, structure exit, and time-stop action generation remain deferred;
- no PAPER/LIVE authorization is added.

### 10. Dependencies / next action

E7 should re-review `E5-RISK-UNKNOWN-001` against this corrected branch revision. Executable release evidence remains `NOT_RUN` until the exact local commands above run in an approved local environment.

E5 must not start another feature automatically after this handoff.

### 11. Security / secrets

- no API key, API secret, token, credential, password, private key, or live `.env` value was added;
- tests use synthetic values only;
- no real secret is required by this correction.

### 12. GitHub compute policy

- no GitHub Actions workflow was created or used;
- no GitHub-hosted or GitHub-triggered runner was used;
- no unit/integration/safety test or other project code was executed on GitHub infrastructure.

### 13. Live-trading impact

This correction only tightens rejection behavior. It does not enable order placement, PAPER, SHADOW, or LIVE operation and does not raise any exposure/risk limit.

### 14. Codex bug ticket

`NOT_APPLICABLE` — this bounded E5 source correction was implemented directly under the assigned TASK; executable verification remains local-only.
