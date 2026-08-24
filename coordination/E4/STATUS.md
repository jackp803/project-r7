# E4 Status

- task_id: `E4-20260824-009`
- agent: `E4`
- state: `DONE`
- branch: `agent/e4-gate-b-close-consumer-20260824`
- baseline_main_sha: `7014e5ee7a74c65c052ad5674f48f161d41d0434`
- head_sha: `db555c0773842630cb1b9aed100d71a4db1a4651` (source/tests/handoff HEAD immediately before this terminal STATUS-only commit)
- summary: `Implemented only E4-owned close-v0.1 mechanical close-order consumption and provider-neutral PaperBroker close Fill/residual Position truth. Exact E5 EXIT/EMERGENCY_EXIT authority plus exact parent plan/current CONSISTENT Position maps to deterministic MARKET reduce-only POSITION_EXIT/EMERGENCY_EXIT OrderRequest. PaperBroker exposes same-position residual/flat observation derived from exact source Position quantity minus exact close Fill set; OrderStatus.FILLED and symbol net exposure are never treated as flat proof. E5 lifecycle/TradeResult/persistence/provider/release authority were not implemented.`
- files_changed: `src/execution/close.py; src/brokers/paper.py; tests/execution/test_close.py; tests/brokers/test_paper_broker_close_truth.py; status/e4/E4_GATE_B_CLOSE_CONSUMER_20260824.md; coordination/E4/STATUS.md`
- contracts_changed: `NO`
- local_verification: `NOT_RUN`
- not_run: `No explicitly PM/Product-Owner-approved Local Runner action is available in this session for the exact clean target revision. Required Windows PowerShell commands from repository root: $env:PYTHONPATH="src" ; python -m unittest discover -s tests/execution -p "test_*.py" -v ; python -m unittest discover -s tests/brokers -p "test_*.py" -v`
- blockers: `NONE for bounded static/source completion. Executable evidence remains outstanding; NOT_RUN is not PASS.`
- handoff_path: `status/e4/E4_GATE_B_CLOSE_CONSUMER_20260824.md`
- next_owner: `E7/PM for bounded static integration review and explicitly approved-local verification planning`

## Wake / authority verification

Wake message task ID:

```text
E4-20260824-009
```

Latest `main:coordination/E4/TASK.md` matched exactly before implementation.

Authoritative files read first:

- `README.md`
- `agents/README.md`
- `agents/E4_EXECUTION.md`
- `coordination/E4/TASK.md`

Only E4's TASK was read; no other Agent TASK was read or executed.

## Branch baseline

At task start:

```text
main = 7014e5ee7a74c65c052ad5674f48f161d41d0434
agent/e4-gate-b-close-consumer-20260824 = identical
```

No merge, rebase, force update, or history rewrite was required.

## Contract-first inspection

Read-only dependencies included:

- `contracts/SHARED_CONTRACTS_V1.md`
- `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`
- `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`
- `docs/adr/ADR-0005-close-authority-and-trade-result-boundary.md`
- accepted E5 `src/position/close.py`
- current E4 models/gateway/protection/PaperBroker/Broker surfaces
- current Gate B integration/release evidence and existing E4 tests

Disposition:

```text
CONTRACT_OR_SEMANTIC_GAP = NO
```

The existing shared Position shape can safely carry later/current same-position broker truth by preserving identity/lifecycle fields and refreshing only E4-owned exposure observation fields. No parallel DTO or shared contract/interface expansion was introduced.

## Implemented close-v0.1 mapping

Accepted actions:

```text
EXIT
EMERGENCY_EXIT
```

Mechanical request mapping:

```text
EXIT           -> POSITION_EXIT
EMERGENCY_EXIT -> EMERGENCY_EXIT
LONG           -> SELL
SHORT          -> BUY
order_type     = MARKET
reduce_only    = true
quantity       = exact PositionAction.quantity = current Position.actual_quantity
limit_price    = null
stop_price     = null
time_in_force  = null
```

Exact lineage retained:

- `trade_plan_id`
- `position_action_id`
- `position_id`
- `risk_decision_id`
- quantity profile/unit/asset

Client identity remains deterministic from `(position_action_id, order_role)` and the order request ID remains deterministic from that client identity.

Validation fails closed on unsupported/missing profile/action/order type, action expiry, parent/risk/strategy/risk-policy lineage mismatch, source Position identity/side/lifecycle/observation/reconciliation mismatch, quantity semantics mismatch, or exposure above the parent maximum.

Parent entry-plan TTL is not reused as close-action lifetime.

## Close Fill / residual Position truth

Existing PaperBroker Fill construction already propagates originating request lineage, so close fills retain:

```text
trade_plan_id
position_action_id
position_id
order_role = POSITION_EXIT | EMERGENCY_EXIT
```

Added Paper-only:

```text
observe_position_after_close(request, source_position, observed_at=...)
```

It returns the existing shared Position shape with only broker-owned facts refreshed:

```text
actual_quantity
broker_state_observed_at
reconciliation_status
```

`lifecycle_state` is preserved unchanged and no `closed_at`, `POSITION_CLOSED`, exit reason, or TradeResult is created.

Residual is derived only from exact source Position quantity minus the exact actual close Fill set. It never uses symbol-level net exposure or `OrderStatus.FILLED` alone as proof of flatness.

Fail-closed conditions include ambiguous submit, inconsistent order health/state/quantity, Fill lineage/time/quantity mismatch, over-close, stale observation, or any other same-symbol Fill after the source Position observation that could invalidate same-position attribution.

Only exact full consumption of source quantity by actual close fills may yield `actual_quantity = 0`.

## Deterministic tests materialized

`tests/execution/test_close.py` covers valid LONG/SHORT/EMERGENCY mapping, exact lineage/idempotency, parent TTL independence, fail-closed authority mismatches and provider-neutrality.

`tests/brokers/test_paper_broker_close_truth.py` covers partial/full close Fill lineage, positive residual, broker-derived flat zero, FILLED-not-flat safety, over-close rejection, short/emergency paths, query_fills preservation, ambiguous truth fail-closed, same-symbol interference fail-closed, terminal/reconciliation compatibility, entry/protection compatibility and provider-neutrality.

Definitions only; none were executed.

## Verification / execution state

```text
local_verification = NOT_RUN
GitHub Actions / CI = NOT_USED
GitHub-hosted / GitHub-triggered runner = NOT_USED
Computer Adapter = NOT_USED
provider/private API = NOT_CALLED
credentials = NOT_USED
Paper runtime/test execution = NOT_RUN
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

Required future approved-local Windows PowerShell commands:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

## Completion boundary

This task does **not** claim Paper E2E, TradeResult durable audit, Gate B/PAPER_READY, PAPER, SHADOW, or LIVE PASS/authority.

E4 stops here and does not self-start E5 TradeResult construction, E6 persistence/restart, E7 Paper E2E, approved-local verification, provider/private work, Gate C, PAPER, SHADOW, or LIVE.