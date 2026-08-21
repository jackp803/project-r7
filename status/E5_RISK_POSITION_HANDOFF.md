# E5 Handoff — Executable Entry / Canonical Quantity Profiles

## Handoff

**From:** E5 / Risk Management & Position Lifecycle Engineer  
**To:** E7 / Integration Engineer  
**Task:** `E5-20260821-004`  
**Branch:** `agent/e5-risk-position`  
**Implementation revision:** `e5f7088301a92deadfd9f6c416ae03b466c38a47`  
**Main synchronization revision:** `d2551999db8bf22f0f93820dd9b7f05cc1301ce9`  
**Main synchronized:** `4f969979ad1f2244b14b0a5e12c85177e8fca5c9`  
**Date:** 2026-08-21

## 1. Objective

Implement the accepted provider-neutral execution profiles at the E5 `RiskDecision -> ApprovedTradePlan` boundary without changing shared contracts, weakening E5 risk authority, or adding provider-native sizing.

## 2. Entry profile semantics

Executable promotion now requires the TradeIntent to declare exactly:

```text
entry_profile_version = entry-v0.1
entry_order_type      = MARKET
```

Missing or unsupported profile/order-type values fail closed.

Legacy `entry_style` remains permitted as legacy/advisory baseline data but has no executable mapping and cannot substitute for the required profile fields.

A valid E5 ApprovedTradePlan emits:

```text
entry_instruction.profile_version = entry-v0.1
entry_instruction.order_type      = MARKET
```

Optional `entry_reference_price` is copied only to advisory `entry_instruction.reference_price`. It is never promoted into `limit_price`, `stop_price`, `trigger_price`, `time_in_force`, or another executable price field.

## 3. Canonical quantity profile

For canonical symbol:

```text
BTC_USDT_PERP
```

E5 emits:

```text
quantity_profile_version = base-asset-v0.1
quantity_unit            = BASE_ASSET
quantity_asset           = BTC
quantity                 = <maximum approved BTC new-position exposure bound>
```

The approved quantity remains a positive finite base-10 decimal string.

Provider conversion may realize less canonical exposure due to downstream lot/minimum constraints, but must never realize more than the E5-approved quantity.

## 4. Provider boundary preserved

E5 does not implement or emit provider-native sizing/metadata such as:

- OKX `sz`;
- `ctVal`;
- `ctMult`;
- `ctValCcy`;
- `lotSz`;
- `minSz`;
- `tickSz`;
- provider instrument metadata retrieval;
- provider account mode;
- provider API calls or credentials.

Those remain E4/provider-adapter responsibilities under ADR-0003.

## 5. Existing risk safety preserved

The accepted `E5-RISK-UNKNOWN-001` correction remains intact:

- unknown/stale/degraded/unsafe required state fails closed;
- contradictory status/boolean inputs fail closed;
- forged `APPROVE` decisions with unsafe market/account/position status cannot produce an ApprovedTradePlan;
- kill switch and other existing E5 risk vetoes remain unchanged.

The authority chain remains:

```text
TradeIntent -> RiskDecision -> ApprovedTradePlan
```

No position-lifecycle transition was changed.

## 6. Files changed for this task

- `src/risk/engine.py`
- `tests/risk/test_risk_engine.py`
- `tests/safety/test_e5_fail_closed.py`
- `status/E5_RISK_POSITION_HANDOFF.md`

No `contracts/**` file was changed.

## 7. Deterministic test definitions added/updated

Static test definitions cover at minimum:

- valid profiled MARKET intent -> profiled ApprovedTradePlan;
- missing profile -> reject;
- unknown profile -> reject;
- unsupported executable order type -> reject;
- legacy style-only intent -> not execution eligible;
- reference price remains advisory/non-executable;
- exact `base-asset-v0.1 / BASE_ASSET / BTC` propagation;
- provider-native sizing fields do not appear in the E5 plan;
- unsafe/forged approval cannot bypass existing fail-closed plan checks.

## 8. Verification

Result: `NOT_RUN`

Reason: no Product Owner-approved local execution environment was available in this session. No project code/test was executed on GitHub or another hosted runner.

Exact local commands from repository root on Windows PowerShell:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/risk -p "test_*.py"
python -m unittest discover -s tests/position -p "test_*.py"
python -m unittest discover -s tests/safety -p "test_*.py"
```

## 9. Security / release impact

- no secrets or credentials added;
- no OKX/Pionex private API implementation added;
- no PAPER/SHADOW/LIVE authorization added;
- no GitHub Actions/CI/hosted runner used;
- no release gate advanced.

## 10. Next action

E7 should re-review the producer/consumer profile alignment against E2/E4/E6 and keep executable evidence `NOT_RUN` until approved local verification exists.

E5 stops after this handoff and waits for a replacement TASK.
