# E5 Status

- task_id: `E5-20260821-004`
- agent: `E5`
- state: `COMPLETE_PENDING_E7_REREVIEW`
- branch: `agent/e5-risk-position`
- head_sha: `3c8f9fa558cc90ad69fd5e58dcd4f6aa457e8de4`
- implementation_sha: `e5f7088301a92deadfd9f6c416ae03b466c38a47`
- branch_sync: `SYNCHRONIZED non-destructively before implementation; main=4f969979ad1f2244b14b0a5e12c85177e8fca5c9, merge=d2551999db8bf22f0f93820dd9b7f05cc1301ce9, no force rewrite.`
- summary: `E5 now consumes only explicit entry-v0.1 / MARKET executable TradeIntent profiles and emits provider-neutral profiled ApprovedTradePlan entry instructions plus base-asset-v0.1 BTC canonical quantity metadata for BTC_USDT_PERP. Legacy entry_style is non-executable; advisory reference_price is not promoted to an executable price.`
- files_changed: `src/risk/engine.py; tests/risk/test_risk_engine.py; tests/safety/test_e5_fail_closed.py; status/E5_RISK_POSITION_HANDOFF.md; coordination/E5/STATUS.md`
- contracts_changed: `NONE`
- accepted_fail_closed_correction_preserved: `YES — E5-RISK-UNKNOWN-001 guards remain in source/test definitions.`
- position_lifecycle_changed: `NO`
- provider_native_sizing_added: `NO`
- paper_shadow_live_authority_changed: `NO`
- local_verification: `NOT_RUN`
- not_run: `No Product Owner-approved local execution environment was available; no project code/tests were executed.`
- blockers: `Executable evidence remains NOT_RUN; E7 producer/consumer re-review is required.`
- handoff_path: `status/E5_RISK_POSITION_HANDOFF.md`
- next_owner: `E7`

## Profile semantics implemented

- TradeIntent execution eligibility requires exactly `entry_profile_version=entry-v0.1` and `entry_order_type=MARKET`.
- Missing/unknown profile or unsupported order type fails closed.
- Legacy `entry_style` cannot substitute for the executable profile.
- ApprovedTradePlan emits `entry_instruction.profile_version=entry-v0.1` and `entry_instruction.order_type=MARKET`.
- Optional `entry_reference_price` is serialized only as advisory `entry_instruction.reference_price`; no `limit_price`, `stop_price`, `trigger_price`, or `time_in_force` is manufactured.
- For `BTC_USDT_PERP`, ApprovedTradePlan emits `quantity_profile_version=base-asset-v0.1`, `quantity_unit=BASE_ASSET`, `quantity_asset=BTC`.
- `quantity` is the maximum E5-approved new-position BTC exposure bound. Downstream provider quantization may realize less but must never exceed this bound.
- No OKX `sz`, `ctVal`, `ctMult`, `ctValCcy`, `lotSz`, `minSz`, `tickSz`, instrument metadata retrieval, account-mode handling, provider API calls, or credentials were added to E5.
- `TradeIntent -> RiskDecision -> ApprovedTradePlan` authority remains unchanged.

## Deterministic test definitions

Static definitions cover:

- valid profiled MARKET intent -> profiled ApprovedTradePlan;
- missing/unknown entry profile -> reject;
- unsupported order type -> reject;
- legacy style-only intent -> not execution eligible;
- advisory reference price remains non-executable;
- exact BTC base-asset quantity profile propagation;
- provider-native sizing fields are absent from the E5 plan;
- forged/unsafe approval cannot bypass existing fail-closed state checks.

## Required local verification

Run only in a Product Owner-approved local environment from repository root on Windows PowerShell:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/risk -p "test_*.py"
python -m unittest discover -s tests/position -p "test_*.py"
python -m unittest discover -s tests/safety -p "test_*.py"
```

Result: `NOT_RUN`

## GitHub compute policy

- No GitHub Actions workflow was created or used.
- No GitHub-hosted or GitHub-triggered runner was used.
- No project code/test was executed on GitHub infrastructure.

E5 stops here and waits for E7 re-review / replacement TASK. No next task or provider-adapter work is started automatically.
