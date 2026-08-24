# E4 Status

- task_id: `E4-20260824-013`
- agent: `E4`
- state: `DONE`
- branch: `agent/e4-gate-b-protection-stop-flat-truth-20260824`
- baseline_main_sha: `4222a9989d86b9f9ed61b01b30d291768132f2a6`
- head_sha: `1dc4a7375c9780ed0ec146f77e443ef8d972389f` (source/tests/handoff HEAD immediately before this terminal STATUS-only commit)
- summary: `Implemented only the E4-owned PaperBroker PROTECTION_STOP same-position authoritative flat-truth gap. The existing position-reduction observer now accepts exact canonical protection-v0.1 STOP_MARKET/reduce-only requests from already OPEN_PROTECTED/PROFIT_PROTECTED source Position truth. Exact full protection Fill + FILLED + HEALTHY/unambiguous OrderResult + exact lineage/quantity/time consistency may refresh only E4-owned Position facts to actual_quantity="0", new broker_state_observed_at and reconciliation_status=CONSISTENT. Partial/zero/terminal/ambiguous/degraded/mismatched protection execution fails closed and cannot return ordinary CONSISTENT residual truth. Existing POSITION_EXIT/EMERGENCY_EXIT residual/full semantics, Fill lineage, terminal/reconciliation, funding producer and entry behavior were not intentionally changed.`
- files_changed: `src/brokers/paper.py; tests/brokers/test_paper_broker_protection_stop_flat_truth.py; status/e4/E4_GATE_B_PROTECTION_STOP_FLAT_TRUTH_20260824.md; coordination/E4/STATUS.md`
- contracts_changed: `NO`
- local_verification: `NOT_RUN`
- not_run: `No explicitly PM/Product-Owner-approved exact-revision Local Runner action is available in this session. Required Windows PowerShell commands from repository root: $env:PYTHONPATH="src" ; python -m unittest discover -s tests/brokers -p "test_*.py" -v ; python -m unittest discover -s tests/execution -p "test_*.py" -v`
- blockers: `NONE for bounded static/source completion. Executable evidence remains outstanding; NOT_RUN is not PASS.`
- handoff_path: `status/e4/E4_GATE_B_PROTECTION_STOP_FLAT_TRUTH_20260824.md`
- next_owner: `E7/PM for bounded static integration review and explicitly approved-local verification planning`

## Wake / authority verification

Wake message task ID:

```text
E4-20260824-013
```

Latest `main:coordination/E4/TASK.md` matched exactly before implementation work began.

Authoritative files read first:

- `README.md`
- `agents/README.md`
- `agents/E4_EXECUTION.md`
- `coordination/E4/TASK.md`

Only E4's TASK was read; no other Agent TASK was read or executed.

## Branch baseline

At task start:

```text
main = 4222a9989d86b9f9ed61b01b30d291768132f2a6
agent/e4-gate-b-protection-stop-flat-truth-20260824 = identical
```

No merge, rebase, force update, or history rewrite was required.

## Contract-first inspection

Read-only dependencies included:

- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`
- `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`
- `contracts/FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md` only to avoid overlap
- current `src/brokers/base.py`
- current `src/brokers/paper.py`
- current `src/execution/models.py`
- current `src/execution/protection.py`
- existing E4 protection/terminal/Fill-lineage/close tests
- E5 `src/position/trade_result.py` read-only
- accepted E4/E7/E5 evidence around PR #48/#50/#52/#53
- current `status/RELEASE_GATES.md` read-only

Disposition:

```text
CONTRACT_OR_SEMANTIC_GAP = NO
```

The accepted contracts already define `PROTECTION_STOP` request/Fill authority and explicitly require a later same-position flat observation after full protection execution. The existing shared Position shape can carry this truth without a new DTO, state, enum, or Broker abstract method.

## Implemented PaperBroker truth boundary

Supported position-reduction roles at the observer are now:

```text
POSITION_EXIT
EMERGENCY_EXIT
PROTECTION_STOP
```

Existing explicit-close semantics remain:

```text
POSITION_EXIT / EMERGENCY_EXIT
order_type = MARKET
reduce_only = true
```

Canonical protection-stop observation requires:

```text
authorization_type = POSITION_ACTION
order_role = PROTECTION_STOP
order_type = STOP_MARKET
reduce_only = true
stop_price > 0
limit_price = null
time_in_force = null
```

and exact/non-empty request lineage:

```text
trade_plan_id
position_action_id
position_id
risk_decision_id
```

The exact source Position must be:

```text
schema_version = contracts-v0.1
same position_id / symbol
side opposite request side
actual_quantity > 0
request.quantity = source actual_quantity
reconciliation_status = CONSISTENT
quantity_profile_version = base-asset-v0.1
quantity_unit = BASE_ASSET
quantity_asset = BTC
lifecycle_state = OPEN_PROTECTED | PROFIT_PROTECTED
```

`OPEN_UNPROTECTED` cannot be used as proof that a protection stop was established before trigger execution.

## Full protection execution

A protection-stop observation may return authoritative flat broker truth only when:

```text
sum(exact protection Fill.quantity)
= OrderResult.filled_quantity
= OrderRequest.quantity
= source Position.actual_quantity

OrderResult.order_status = FILLED
execution_health_status = HEALTHY
observed_at >= latest included Fill.filled_at
```

Every Fill must match exact:

```text
trade_plan_id
position_action_id
position_id
order_role = PROTECTION_STOP
symbol
side
```

The returned Position preserves identity and E5-owned lifecycle and refreshes only:

```text
actual_quantity = "0"
broker_state_observed_at = exact observation time
reconciliation_status = CONSISTENT
```

No `closed_at`, `POSITION_CLOSED`, exit reason, TradeResult, or risk/lifecycle event is emitted by E4.

## Partial / ambiguous / terminal behavior

Partial protection execution intentionally fails closed:

```text
0 < summed protection Fill < source actual_quantity
-> ReconciliationRequiredError
```

No ordinary `CONSISTENT` residual Position is returned because residual/replacement protection semantics are outside the accepted V0.1 contract.

Also blocked from flat truth:

- zero/no Fill / untriggered OPEN protection order;
- REJECTED/CANCELED/EXPIRED protection order;
- UNKNOWN/RECONCILIATION_REQUIRED submit/order truth;
- non-HEALTHY execution truth;
- stale observation;
- wrong role/type/reduce-only/stop/limit/TIF semantics;
- request/source/Fill lineage mismatch;
- wrong side/symbol/quantity;
- over-fill;
- another same-symbol Fill after the source Position observation.

Symbol-level net exposure and `OrderStatus.FILLED` alone are never used as same-position flat proof.

## Deterministic test definitions materialized

Added:

```text
tests/brokers/test_paper_broker_protection_stop_flat_truth.py
```

Definitions cover full LONG/SHORT stop closure, PROFIT_PROTECTED, exact lineage, FILLED/quantity equality, stale observation, OPEN_UNPROTECTED rejection, partial/zero fail-closed, rejected/canceled/expired/ambiguous/degraded truth, malformed protection request semantics, mismatched/tampered lineage, overfill, same-symbol interference, explicit-close no-regression, funding producer compatibility, and entry compatibility.

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
```

Required future approved-local Windows PowerShell commands:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
```

`NOT_RUN` is not PASS.

## Completion boundary

This task does **not** claim:

```text
PROTECTION_STOP -> TradeResult = PASS
Paper E2E = PASS
Restart/persistence = PASS
Gate B = PASS
PAPER_READY = PASS
PAPER / SHADOW / LIVE = AUTHORIZED
```

Gate/release authority remains unchanged. E4 stops after this terminal STATUS and does not self-start E6 persistence, E7 integration/E2E, approved-local verification, Gate C, PAPER, SHADOW, or LIVE.
