# E5 Status

- task_id: `E5-20260824-014`
- agent: `E5`
- state: `DONE`
- branch: `agent/e5-gate-b-close-producer-20260824`
- base_main_sha: `70fc437b6f2b13bba094be7cbe6d6b6e4a3f9f15`
- implementation_evidence_head_before_terminal_status: `bc11e20d5cfa3b4e3d74db0c3a4a26f5c0d23f81`
- summary: `Materialized the E5 close-v0.1 EXIT / EMERGENCY_EXIT PositionAction producer and immediate EXIT_REQUESTED lifecycle intent. Close quantity equals exact current CONSISTENT Position.actual_quantity; parent plan/risk/strategy lineage, source lifecycle, deterministic E5 reason sequence and independent action freshness are bound into stable authority identity. No closure, E4 execution, TradeResult, persistence or release authority was added.`
- files_changed: `src/position/close.py; src/position/__init__.py; tests/position/test_close_action.py; status/E5_GATE_B_CLOSE_PRODUCER_20260824.md; coordination/E5/STATUS.md`
- contracts_changed: `NONE`
- lifecycle_enum_or_transition_table_changed: `NO`
- e4_or_broker_changed: `NO`
- trade_result_or_flat_closure_added: `NO`
- provider_native_behavior_added: `NO`
- persistence_changed: `NO`
- paper_shadow_live_authority_changed: `NO`
- local_verification: `NOT_RUN`
- evidence_path: `status/E5_GATE_B_CLOSE_PRODUCER_20260824.md`
- next_owner: `PM/E7`

## Implemented boundary

```text
exact current E4-normalized CONSISTENT Position truth
+ exact parent ApprovedTradePlan / risk / strategy lineage
+ deterministic E5-owned exit reason sequence
-> close-v0.1 PositionAction.EXIT | EMERGENCY_EXIT
-> existing PositionEvent.EXIT_REQUESTED
```

### Supported lifecycle/action matrix

```text
OPEN_UNPROTECTED -> EXIT
OPEN_PROTECTED   -> EXIT
PROFIT_PROTECTED -> EXIT
EMERGENCY        -> EMERGENCY_EXIT
```

All wrong action/state combinations, `PENDING_ENTRY`, `EXIT_REQUESTED`, `CLOSED`, `RECONCILIATION_REQUIRED`, unknown lifecycle values and unsupported actions fail closed.

### Exact actual quantity

For valid close authority:

```text
PositionAction.quantity = exact Position.actual_quantity
```

The source Position must be `CONSISTENT`, positive/finite, canonical quantity-compatible with the parent plan, and not exceed the parent ApprovedTradePlan maximum. Original requested/plan-max/provider-native quantity is never substituted for current exposure.

### Canonical close payload / lineage

Producer emits accepted `close-v0.1` fields, including exact:

```text
schema_version = contracts-v0.1
close_profile_version = close-v0.1
action = EXIT | EMERGENCY_EXIT
position_id
trade_plan_id
risk_decision_id
strategy_id
strategy_version
risk_policy_version
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
reason_codes
created_at
expires_at
position_action_id
```

Parent plan/risk/strategy lineage and exact source Position identity/side/lifecycle/observation/quantity semantics are revalidated fail closed.

### E5 reason semantics

Default deterministic E5 reason sequences:

```text
EXIT           -> [E5_EXIT_REQUESTED]
EMERGENCY_EXIT -> [E5_EMERGENCY_EXIT_REQUIRED]
```

An explicit non-empty deterministic E5 reason sequence may carry more specific E5 lifecycle/risk context. The exact sequence is identity-bearing; changed reason material changes `position_action_id`. Broker/E4/provider data does not select reasons.

### Identity / freshness

Identical logical authority material yields the same `position_action_id`. Changes in action type, parent/risk lineage, Position identity/side/lifecycle/observation, exact quantity semantics, reason sequence, policy or freshness material change identity.

Parent entry-plan TTL remains lineage only after exposure exists. The close action has independent `created_at` / `expires_at`; `expires_at > created_at`, creation cannot predate its source Position observation, and expired action material fails closed.

## Lifecycle boundary

`authorize_close_position_action()` applies only existing:

```text
EXIT_REQUESTED
```

and yields `EXIT_REQUESTED` from normal open states or `EMERGENCY`. It never emits `POSITION_CLOSED` and does not mutate shared state-machine definitions.

Existing later semantics remain separate:

```text
EXIT_REQUESTED + EXIT_FAILED -> EMERGENCY
EXIT_REQUESTED + POSITION_CLOSED -> CLOSED
```

No broker result interpretation, authoritative-flat proof or TradeResult production is implemented in this task.

## Deterministic test definitions

`tests/position/test_close_action.py` covers at minimum:

- OPEN_UNPROTECTED EXIT exact actual quantity and parent lineage;
- OPEN_PROTECTED / PROFIT_PROTECTED ordinary EXIT;
- EMERGENCY -> EMERGENCY_EXIT;
- wrong action/lifecycle fail closed;
- zero/negative/non-finite actual quantity fail closed;
- UNKNOWN/MISMATCH/RECONCILIATION_REQUIRED Position truth fail closed;
- over-approved actual exposure fail closed;
- symbol/side/profile/unit/asset mismatch fail closed;
- plan/risk/strategy lineage tamper fail closed;
- independent close expiry despite expired parent entry TTL;
- deterministic reason sequence and action identity;
- identity changes on observation/quantity/reason/risk/action changes;
- close creation reaches only EXIT_REQUESTED, never CLOSED;
- existing EXIT_FAILED/POSITION_CLOSED transitions remain later separate evidence paths;
- protection-v0.1 producer compatibility;
- provider-native/credential fields absent.

## Executable verification

Result:

```text
NOT_RUN
```

Reason: no explicitly PM/Product-Owner-approved AgentBridge Local Runner action pinned to this exact new target revision is exposed in this session. No project code/tests were executed.

Exact future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

`NOT_RUN` is not PASS.

## GitHub compute / security

- GitHub Actions / CI / hosted runner used: `NO`
- GitHub-triggered self-hosted compute used: `NO`
- arbitrary cloud project execution used: `NO`
- Computer Adapter used: `NO`
- provider/private request used: `NO`
- credentials used: `NO`

## Release impact

```text
E5 close-v0.1 producer = MATERIALIZED STATICALLY
E4 close consumer = NOT IMPLEMENTED BY THIS TASK
E5 authoritative-flat / trade-result-v0.1 builder = NOT IMPLEMENTED BY THIS TASK
Paper E2E / durable audit = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

E5 stops on `DONE` for `E5-20260824-014`. Do not self-start E4 close consumer, E5 TradeResult builder, E6 persistence, E7 Paper E2E, approved-local verification, provider/private work, Gate C, PAPER, SHADOW, or LIVE.
