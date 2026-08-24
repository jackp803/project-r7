# E5 Gate B Risk-Limit Criterion Evidence — 2026-08-24

## Authority / scope

- Task: `E5-20260824-007`
- Owner: E5 Risk Management & Position Lifecycle Engineer
- Target branch: `agent/e5-gate-b-risk-evidence-20260824`
- Branch base / latest main at task start: `75862902462eee106d0b9d6ff7a4593c7b9ce0ab`
- Test-definition implementation commit: `eb57637e7c91262f2bbffa140b39db2d24c8c6fc`
- Parent contract set: `contracts-v0.1`
- Gate B criterion: `Drawdown / daily / position / kill-switch rules enforced`
- Gate B disposition: `BLOCKED / NOT YET PASS`
- Executable verification: `NOT_RUN`

This task materializes criterion-level E5 test definitions only. It does not redesign or weaken production risk policy, does not change shared contracts, and does not authorize PAPER/SHADOW/LIVE execution.

## Static production evidence inspected

Existing `src/risk/policy.py` already defines versioned configurable controls:

- `max_trades_per_day`
- `max_open_positions`
- `max_drawdown`
- kill-switch input through `RiskContext.kill_switch_active`

Existing `src/risk/engine.py` already enforces them with the canonical current reason behavior:

- `DAILY_TRADE_LIMIT_REACHED`
- `SIMULTANEOUS_POSITION_LIMIT_REACHED`
- `DRAWDOWN_LOCK_ACTIVE`
- `KILL_SWITCH_ACTIVE`

No production file was modified by this task.

## Criterion-level test mapping

### 1. Daily trade cap

`tests/risk/test_risk_engine.py`

- `RiskEngineTests.test_gate_b_daily_trade_cap_uses_configured_policy_boundary`
  - derives the boundary from `RiskPolicy.max_trades_per_day`;
  - below-limit context continues through the normal risk path and is not rejected for the daily cap;
  - at-limit and above-limit contexts reject with `DAILY_TRADE_LIMIT_REACHED`.

### 2. Open / simultaneous-position cap

`tests/risk/test_risk_engine.py`

- `RiskEngineTests.test_gate_b_open_position_cap_uses_configured_policy_boundary`
  - derives the boundary from `RiskPolicy.max_open_positions`;
  - below-limit context is not rejected for the simultaneous-position cap;
  - at-limit and above-limit contexts reject with `SIMULTANEOUS_POSITION_LIMIT_REACHED` even when `same_symbol_position_open=False`, proving the configured aggregate cap independently blocks a second-position approval.

Existing fail-closed safety coverage remains the companion evidence and was not duplicated:

`tests/safety/test_e5_fail_closed.py`

- `FailClosedBoundaryTests.test_existing_same_symbol_position_blocks_position_add`
- `FailClosedBoundaryTests.test_unknown_position_status_cannot_be_overridden_by_known_flag`
- `FailClosedBoundaryTests.test_reconciliation_required_and_mismatch_states_fail_closed`

### 3. Drawdown lock

`tests/risk/test_risk_engine.py`

- `RiskEngineTests.test_gate_b_drawdown_lock_uses_configured_policy_threshold`
  - derives the threshold from `RiskPolicy.max_drawdown`;
  - below-threshold drawdown does not itself trigger `DRAWDOWN_LOCK_ACTIVE`;
  - threshold and exceeded states reject with `DRAWDOWN_LOCK_ACTIVE`;
  - no drawdown calculation semantics are redefined.

### 4. Kill switch

Existing explicit coverage is sufficient and intentionally not duplicated:

`tests/safety/test_e5_fail_closed.py`

- `FailClosedBoundaryTests.test_kill_switch_always_rejects_new_exposure`
  - active kill switch rejects new exposure with `KILL_SWITCH_ACTIVE`.

### 5. Fail-closed / no policy weakening

`tests/risk/test_risk_engine.py`

- `RiskEngineTests.test_gate_b_new_intent_identity_does_not_bypass_active_limit_locks`
  - a new TradeIntent/signal identity does not reset or bypass active daily-trade, open-position, or drawdown locks.

Existing safety coverage additionally remains intact:

- `FailClosedBoundaryTests.test_loss_lock_does_not_auto_reset_on_new_signal`
- `FailClosedBoundaryTests.test_existing_same_symbol_position_blocks_position_add`
- accepted unknown/reconciliation fail-closed tests.

No martingale, averaging-down, stop-widening, risk escalation, or second-position approval behavior was added.

## Files changed

- `tests/risk/test_risk_engine.py`
- `status/E5_GATE_B_RISK_LIMIT_EVIDENCE_20260824.md`
- `coordination/E5/STATUS.md` is updated separately as the shared mailbox status.

No `src/**`, `contracts/**`, ADR, execution, broker, persistence, strategy, provider, workflow, or lifecycle authority file was changed.

## Verification

Result: `NOT_RUN`

Reason: this ChatGPT/GitHub collaboration session does not expose an explicitly approved AgentBridge Local Runner action pinned to this exact new branch revision. The TASK requires `NOT_RUN` rather than ad-hoc remote/GitHub execution in that case.

Exact future local commands from repository root on Windows PowerShell:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

No executable PASS is claimed from static inspection.

## GitHub compute / security

- GitHub Actions / CI / hosted runner used: `NO`
- GitHub-triggered project compute used: `NO`
- project code executed on GitHub infrastructure: `NO`
- secrets / provider credentials used or added: `NO`

## Handoff / next owner

The requested criterion-level test definitions are materialized statically. E5 does **not** declare the Gate B risk-limit criterion PASS and does **not** declare Gate B/PAPER_READY PASS.

Next owner: `PM/E7` for review and later explicitly authorized approved-local execution/evidence handling.

E5 stops after updating `coordination/E5/STATUS.md`; it does not begin actual-fill protection, protection-failure orchestration, persistence, TradeResult closure, or Paper E2E work.