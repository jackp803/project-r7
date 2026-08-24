# E5 Gate B close-v0.1 Producer Handoff

- task_id: `E5-20260824-014`
- agent: `E5`
- state: `DONE`
- target_branch: `agent/e5-gate-b-close-producer-20260824`
- base_main_sha: `70fc437b6f2b13bba094be7cbe6d6b6e4a3f9f15`
- contract_set: `contracts-v0.1`
- close_profile: `close-v0.1`
- authoritative_contract: `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`
- authoritative_adr: `docs/adr/ADR-0005-close-authority-and-trade-result-boundary.md`
- local_verification: `NOT_RUN`

## Implemented boundary

E5 now materializes only this bounded authority path:

```text
exact current normalized CONSISTENT Position truth
+ exact parent ApprovedTradePlan / risk / strategy lineage
+ deterministic E5 exit reason sequence
-> close-v0.1 PositionAction.EXIT | EMERGENCY_EXIT
-> existing PositionEvent.EXIT_REQUESTED lifecycle intent
```

The implementation stops before E4 OrderRequest translation/submission, broker fills, authoritative-flat closure, TradeResult construction, E6 persistence, Paper E2E, provider/private APIs, or release authority.

## Production implementation

### `src/position/close.py`

Exports:

```text
build_close_position_action(...)
validate_close_position_action(...)
authorize_close_position_action(...)
default_close_reason_codes(...)
CloseActionOutcome
CloseActionError
```

### Supported action/lifecycle matrix

Ordinary `EXIT` is accepted only from:

```text
OPEN_UNPROTECTED
OPEN_PROTECTED
PROFIT_PROTECTED
```

`EMERGENCY_EXIT` is accepted only from:

```text
EMERGENCY
```

`PENDING_ENTRY`, `EXIT_REQUESTED`, `CLOSED`, `RECONCILIATION_REQUIRED`, unknown states, unsupported actions, or wrong action/state combinations fail closed.

## Actual exposure authority

The producer requires current Position truth with:

```text
schema_version = contracts-v0.1
reconciliation_status = CONSISTENT
actual_quantity > 0 and finite
quantity_profile_version = base-asset-v0.1
quantity_unit = BASE_ASSET
position/plan symbol, side/direction and quantity semantics compatible
valid UTC broker_state_observed_at
```

For every valid close action:

```text
PositionAction.quantity = exact Position.actual_quantity
```

It never substitutes the parent plan maximum, original requested entry quantity, provider-native contract count, or broker-specific size.

If actual exposure exceeds the parent ApprovedTradePlan maximum, the producer fails closed with `ACTUAL_QUANTITY_EXCEEDS_APPROVED_MAXIMUM`.

## Canonical close-v0.1 payload

The producer emits the accepted shared field names and semantics:

```text
schema_version = contracts-v0.1
close_profile_version = close-v0.1
position_action_id
position_id
action = EXIT | EMERGENCY_EXIT
reason_codes
risk_policy_version
trade_plan_id
risk_decision_id
strategy_id
strategy_version
symbol
position_side
source_lifecycle_state
position_observed_at
position_reconciliation_status = CONSISTENT
quantity
quantity_profile_version = base-asset-v0.1
quantity_unit = BASE_ASSET
quantity_asset
close_order_type = MARKET
created_at
expires_at
```

Exact plan lineage is validated for:

```text
trade_plan_id
risk_decision_id
strategy_id
strategy_version
risk_policy_version
symbol
```

Exact Position lineage is validated for:

```text
position_id
position_side
source_lifecycle_state
position_observed_at
position_reconciliation_status
quantity
quantity_profile_version
quantity_unit
quantity_asset
```

## E5 reason semantics

Minimal deterministic defaults are E5-owned:

```text
EXIT           -> [E5_EXIT_REQUESTED]
EMERGENCY_EXIT -> [E5_EMERGENCY_EXIT_REQUIRED]
```

The producer also accepts an explicit non-empty deterministic E5 reason sequence for more specific E5 lifecycle/risk context. Reason sequence is part of `position_action_id`; changed reasons therefore change immediate close authority identity.

Broker/E4/provider data is not an input to reason selection, and the producer performs no provider/broker calls.

## Identity and freshness

`position_action_id` is deterministic over authority-bearing close material including:

- action type;
- reason sequence;
- plan/risk/strategy lineage;
- position identity/side/source lifecycle;
- exact Position observation timestamp;
- exact actual quantity/profile/unit/asset;
- risk policy;
- close order type;
- action-specific created/expiry timestamps.

Identical inputs produce identical action identity. New observation, residual quantity, changed reason, changed risk lineage, or ordinary-vs-emergency authority produces a different identity.

Parent entry-plan TTL is validated only for structural lineage. It is not reused as post-exposure close authority lifetime.

The close action uses its own:

```text
created_at >= Position.broker_state_observed_at
expires_at > created_at
```

Expired close action material fails closed.

## Lifecycle boundary

`authorize_close_position_action()` associates the serialized action with only the existing:

```text
PositionEvent.EXIT_REQUESTED
```

and existing state-machine transitions:

```text
OPEN_UNPROTECTED + EXIT_REQUESTED -> EXIT_REQUESTED
OPEN_PROTECTED   + EXIT_REQUESTED -> EXIT_REQUESTED
PROFIT_PROTECTED + EXIT_REQUESTED -> EXIT_REQUESTED
EMERGENCY        + EXIT_REQUESTED -> EXIT_REQUESTED
```

No lifecycle enum or transition table was changed.

Action creation never emits/applies `POSITION_CLOSED`. Existing later semantics remain unchanged:

```text
EXIT_REQUESTED + EXIT_FAILED -> EMERGENCY
EXIT_REQUESTED + POSITION_CLOSED -> CLOSED
```

Those later events require later authoritative execution/Position truth and are outside this task.

## Deterministic tests materialized

`tests/position/test_close_action.py` defines coverage for:

- valid OPEN_UNPROTECTED EXIT exact actual quantity + exact parent lineage;
- OPEN_PROTECTED and PROFIT_PROTECTED ordinary EXIT;
- EMERGENCY -> EMERGENCY_EXIT distinct authority;
- wrong action/lifecycle combinations fail closed;
- zero/negative/non-finite quantity fail closed;
- UNKNOWN/MISMATCH/RECONCILIATION_REQUIRED Position truth fail closed;
- actual exposure above parent approved maximum fail closed;
- symbol/side/quantity-profile/unit/asset mismatch fail closed;
- parent plan/risk/strategy lineage tampering fail closed;
- independent close-action expiry despite expired parent entry TTL;
- deterministic reason sequence/action ID;
- changed observation, residual quantity, risk lineage, reason or ordinary/emergency authority changes identity;
- action creation reaches only EXIT_REQUESTED and never CLOSED;
- existing EXIT_FAILED/POSITION_CLOSED state-machine semantics remain separate;
- existing protection-v0.1 producer remains compatible;
- provider-native and credential fields are absent.

No E4 broker submission, TradeResult formula, E6 persistence, or release-gate behavior is encoded into E5 unit tests.

## Files changed

```text
src/position/close.py
src/position/__init__.py
tests/position/test_close_action.py
status/E5_GATE_B_CLOSE_PRODUCER_20260824.md
coordination/E5/STATUS.md  (terminal status written separately on target branch)
```

## Contracts / cross-role code

```text
contracts changed = NONE
ADRs changed = NONE
src/execution changed = NO
src/brokers changed = NO
E6 persistence changed = NO
TradeResult builder added = NO
PAPER/SHADOW/LIVE authority changed = NO
provider/private behavior added = NO
```

## Executable verification

Result:

```text
local_verification = NOT_RUN
```

Reason: no explicitly PM/Product-Owner-approved AgentBridge Local Runner action pinned to this exact new target revision is exposed in this session. Static inspection is not executable PASS evidence.

Exact future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

No GitHub Actions, CI, hosted runner, GitHub-triggered self-hosted compute, arbitrary cloud execution, Computer Adapter, provider/private API, or credential was used.

`NOT_RUN` is not PASS.

## Release impact

```text
E5 close-v0.1 producer = MATERIALIZED STATICALLY
E4 close consumer = NOT IMPLEMENTED BY THIS TASK
E5 final POSITION_CLOSED / TradeResult = NOT IMPLEMENTED BY THIS TASK
Paper E2E closes to TradeResult and persists audit = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

E5 stops on `DONE` for `E5-20260824-014` after writing the terminal target-branch mailbox STATUS. No next phase is self-started.
