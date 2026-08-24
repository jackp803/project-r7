# E5 Status

- task_id: `E5-20260824-021`
- agent: `E5`
- state: `DONE`
- branch: `agent/e5-gate-b-position-lifecycle-projection-producer-20260824`
- base_main_sha: `d4ad044566b64f160c29dbfb1cd7b1dd5da90925`
- implementation_evidence_head_before_terminal_status: `a7df5f11b01c9476f4000f1e36e59ab6aaa55160`
- summary: `Materialized the E5 position-lifecycle-projection-v0.1 producer/composition surface. E5 now emits deterministic GENESIS/TRANSITION/REATTESTATION Position projections with E5-owned contiguous lifecycle revisions, exact predecessor links, broker-anchor non-regression/equal-time conflict checks, and posproj_ content identity while preserving E4 broker facts. POSITION_CLOSED projection is structurally restricted to a successful real TradeResultBuildOutcome and exact flat CONSISTENT Position truth.`
- files_changed: `src/position/lifecycle_projection.py; src/position/__init__.py; tests/position/test_lifecycle_projection.py; status/E5_GATE_B_POSITION_LIFECYCLE_PROJECTION_PRODUCER_20260824.md; coordination/E5/STATUS.md`
- contracts_changed: `NONE`
- adr_changed: `NONE`
- lifecycle_enum_or_transition_table_changed: `NO`
- e4_or_broker_changed: `NO`
- e6_storage_or_persistence_changed: `NO`
- provider_private_behavior_added: `NO`
- paper_shadow_live_authority_changed: `NO`
- local_verification: `NOT_RUN`
- evidence_path: `status/E5_GATE_B_POSITION_LIFECYCLE_PROJECTION_PRODUCER_20260824.md`
- next_owner: `PM/E7`

## Implemented boundary

```text
exact E4 Position broker observation
+ exact prior position-lifecycle-projection-v0.1 Position when applicable
+ real E5 lifecycle interpretation/outcome
-> canonical position-lifecycle-projection-v0.1 Position
```

## Canonical producer behavior

### GENESIS

```text
lifecycle_revision = 0
previous_lifecycle_projection_id = null
lifecycle_projection_kind = GENESIS
lifecycle_event = null
```

The source must be an exact unprofiled canonical Position. E5 explicitly supplies the lifecycle interpretation and UTC interpretation time; revision/ID are not caller-controlled.

### TRANSITION

For ordinary lifecycle changes:

```text
lifecycle_revision = previous + 1
previous_lifecycle_projection_id = exact previous ID
lifecycle_projection_kind = TRANSITION
lifecycle_event = exact canonical PositionEvent
lifecycle_state = transition(previous.lifecycle_state, lifecycle_event)
```

The producer directly reuses the existing canonical E5 state machine. It supports the current real E5 protection/close/unknown outcomes and compatible reconciliation/profit-protection events without duplicating transition semantics.

### CLOSED transition guard

Generic `build_position_lifecycle_transition()` rejects caller-supplied `POSITION_CLOSED` with:

```text
TRADE_RESULT_CLOSURE_OUTCOME_REQUIRED
```

`build_position_lifecycle_closed_transition()` requires a real successful E5 `TradeResultBuildOutcome` with `POSITION_CLOSED -> CLOSED`, exact TradeResult/Position identity, exact flat `actual_quantity=0`, `reconciliation_status=CONSISTENT`, and exact flat observation binding before producing the CLOSED projection.

### REATTESTATION

```text
lifecycle_revision = previous + 1
previous_lifecycle_projection_id = exact previous ID
lifecycle_projection_kind = REATTESTATION
lifecycle_event = null
lifecycle_state = previous E5 lifecycle state
broker anchor >= previous broker anchor
```

A newer E4 broker observation may update broker facts, but E5 explicitly re-attests lifecycle; E6/storage arrival order is never lifecycle authority.

## Broker fact / ordering safety

E5 preserves current canonical E4-owned Position facts unchanged.

```text
same broker timestamp + same broker facts
-> lifecycle-only revision allowed

same broker timestamp + changed broker facts
-> fail closed / EQUAL_TIME_BROKER_FACT_CONFLICT

older broker timestamp
-> fail closed / BROKER_OBSERVATION_REGRESSION
```

No SQLite row order, `persisted_at`, last-write-wins, provider field or storage revision is used.

## Identity / validation

`lifecycle_projection_id` is deterministic:

```text
complete serialized profiled Position except lifecycle_projection_id
-> sorted compact UTF-8 JSON
-> SHA-256
-> posproj_<lowercase hex>
```

The producer/validator rejects unsupported profile/state/event/kind, malformed revision/predecessor, invalid ID, broker-anchor mismatch/regression, noncanonical timestamps/decimals, invalid event/state edges and unknown undeclared Position fields.

Public producer APIs do not accept caller-provided `lifecycle_revision` or `lifecycle_projection_id`.

## Tests materialized

`tests/position/test_lifecycle_projection.py` defines deterministic coverage for:

- GENESIS/profile/revision/predecessor/identity/idempotent replay;
- real `interpret_protection_result()` verified/failure/loss/unknown outcomes;
- profit protection transition compatibility;
- real `authorize_close_position_action()` ordinary/emergency EXIT_REQUESTED;
- supported reconciliation transition;
- real successful `build_trade_result()` closure requirement;
- generic manual POSITION_CLOSED rejection;
- exact flat CLOSED projection;
- REATTESTATION on newer broker truth;
- multiple lifecycle revisions on one broker observation;
- broker anchor regression/equal-time broker conflict;
- corrupt previous profile/ID/revision/predecessor;
- invalid event/state edge;
- deterministic identity/timestamp checks;
- no E6/storage/provider/release/caller revision or ID authority.

## Executable verification

```text
local_verification = NOT_RUN
```

Reason: no explicitly PM/Product-Owner-approved AgentBridge Local Runner action pinned to this exact target revision is exposed in this session. No project code/tests were executed.

Exact future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

`NOT_RUN != PASS`.

## GitHub compute / security

- GitHub Actions / CI / hosted runner used: `NO`
- GitHub-triggered self-hosted compute used: `NO`
- arbitrary cloud project execution used: `NO`
- Computer Adapter used: `NO`
- provider/private API used: `NO`
- credentials used: `NO`

## Release impact

```text
position-lifecycle-projection-v0.1 contract = ACCEPTED / prior PR #57
E5 lifecycle projection producer = MATERIALIZED STATICALLY
E6 durable Paper persistence/restart/audit = LATER DEPENDENCY / NOT IMPLEMENTED HERE
Restart/persistence preserves required state = BLOCKED pending E6 + approved-local evidence
Paper E2E durable audit = BLOCKED
approved-local Gate B verification = NOT_RUN
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

E5 stops on `DONE` for `E5-20260824-021`. Do not self-start E6 persistence/migrations/restart/audit, E7 durability/E2E work, approved-local verification, provider/private work, Gate C, PAPER, SHADOW or LIVE.
