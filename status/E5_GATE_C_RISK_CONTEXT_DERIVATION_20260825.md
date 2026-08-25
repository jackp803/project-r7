# E5 Gate C RiskContext Derivation — 2026-08-25

- task_id: `E5-20260825-027`
- branch: `agent/e5-gate-c-risk-context-20260825`
- base_main_sha: `43b3d5bd1746773c4018c9e30182e3e60024ab88`
- state: `DONE / EXECUTABLE_NOT_RUN`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate C baseline and accepted E1/E4 normalized Gate C surfaces

## Bounded implementation

E5 now has a pure derivation surface that consumes only normalized Gate C facts and E5-owned risk-runtime state:

```text
accepted E1 MarketSnapshot
+ accepted E4 OKXShadowReadResult normalized observation/runtime balance
+ explicit UTC risk evaluation time
+ E5 kill-switch/counters/drawdown
-> existing RiskContext
```

No caller-provided market/account/position/order safety booleans or independently supplied available balance are accepted by the derivation API.

## Market safety

The derivation requires the accepted canonical BTC perpetual current-ticker identity, healthy E1 status, valid UTC observation/receipt times and internally consistent freshness metadata. Freshness is re-evaluated at the E5 decision boundary:

```text
age <= 5000 ms -> eligible
age > 5000 ms -> stale / fail closed
material future/invalid/contradictory timing -> fail closed
```

## E4 Shadow safety

The derivation consumes only the sanitized normalized observation plus the same-batch runtime-only balance. It validates the accepted production read-only OKX V5 identity, read-only permission, clock status/skew, account/sub-account/mode facts, balance-known/runtime Decimal binding, position truth, pending-order truth, fill checkpoint/new-unreconciled-fill truth, and healthy/no-blocking-reason status.

Unsafe/unknown observation axes cannot enable new exposure. The exact runtime balance is not serialized or persisted by this task and is not included in this evidence/status artifact.

## E5 policy preservation

Existing `RiskContext`, `_validate_context`, `RiskPolicy`, `RiskDecision`, sizing/caps, daily/open-position limits, drawdown/consecutive-loss locks, kill-switch semantics, ApprovedTradePlan behavior, position lifecycle and protection logic are unchanged.

`new_exposure_allowed` is derived false whenever market/account/position/order derivation is unsafe or the kill switch is active. Policy thresholds remain enforced downstream by the existing E5 risk engine rather than being redefined in this adapter.

## Test definitions

`tests/risk/test_gate_c_context_derivation.py` statically defines credential-free coverage for:

- healthy E1/E4 normalized inputs -> safe existing RiskContext;
- exact same-batch runtime Decimal handoff with redacted derivation repr;
- exact 5000 ms decision boundary and >5000 ms stale rejection;
- future/malformed/identity/freshness market failures;
- degraded/contradictory E4 health;
- missing/invalid runtime balance;
- unexpected/unknown position truth;
- pending order/new fill/unknown checkpoint activity;
- provider/environment/instrument/permission/clock/account contradictions;
- kill switch and existing daily-limit behavior;
- invalid E5 counter/drawdown state;
- absence of caller-supplied safety booleans in the derivation signature;
- downstream existing risk engine approval/rejection compatibility.

## Executable verification

```text
local_verification = NOT_RUN
```

No exact-revision approved local runner action is exposed in this session. E7/PM Product Owner authorization permits local credential-free execution, but this GitHub-connected session itself is not that local runner. No project code/tests were executed here.

Exact future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

`NOT_RUN != PASS`.

## Scope / security

- E1/E2/E3/E4/E6/E7 production/tests changed: `NO`
- shared contracts/ADR changed: `NO`
- provider parsing/network/auth/signing added to E5: `NO`
- provider/private request executed: `NO`
- credentials/secrets used or persisted: `NO`
- runtime balance persisted/publicly recorded: `NO`
- GitHub Actions/CI/hosted/GitHub-triggered compute used: `NO`
- risk caps/policy loosened: `NO`
- PAPER/SHADOW runtime started: `NO`
- LIVE/capital authority changed: `NO`

## Release impact

This task statically materializes only the E5 Phase-2 Gate C normalized-observation-to-risk-context gap. It does not claim Gate C/SHADOW_READY PASS, does not perform provider verification, and does not authorize SHADOW runtime start or LIVE.
