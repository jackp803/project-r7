# E5 Gate B Protection Result Lifecycle Bridge Evidence

- task_id: `E5-20260824-012`
- agent: `E5`
- state: `DONE`
- target_branch: `agent/e5-gate-b-protection-result-bridge-20260824`
- base_main_sha: `1e63f15a7e9db2fce4e0c72786a6c0d25a6277e8`
- contract_set: `contracts-v0.1`
- protection_profile: `protection-v0.1`
- accepted_review: `PR #40 / merge 0c2202742c6fa601ac79b32603620a0553b95e2e`
- local_verification: `NOT_RUN`

## Objective implemented

This task materializes only the E5-owned interpretation boundary:

```text
exact canonical protection OrderRequest
+ already-normalized authoritative E4 order/query/reconciliation truth
+ current E5 lifecycle context
-> existing E5 PositionEvent / lifecycle outcome
```

The bridge does not submit, query, retry, cancel, or otherwise operate a broker. It does not call provider/private APIs and does not persist runtime state.

## Production implementation

Added:

- `src/position/protection_result.py`

Updated export surface:

- `src/position/__init__.py`

Callable API:

```python
interpret_protection_result(request, evidence, current_state)
```

E5-internal, non-serialized helper values:

- `ProtectionResultEvidence`
- `ProtectionLifecycleOutcome`

These helpers do not introduce a shared cross-module contract. They only preserve interpretation distinctions around already-normalized E4 evidence.

## Exact protection-request boundary

Before interpreting broker truth, the bridge fail-closes unless the supplied request is the accepted canonical protection path, including:

```text
schema_version = contracts-v0.1
authorization_type = POSITION_ACTION
order_role = PROTECTION_STOP
order_type = STOP_MARKET
reduce_only = true
non-empty order_request_id
non-empty client_order_id
non-empty trade_plan_id
non-empty position_action_id
non-empty position_id
non-empty risk_decision_id
non-empty symbol
positive finite canonical quantity
canonical quantity profile/unit/asset present
positive finite stop_price
limit_price = null
time_in_force = null
```

Malformed/non-protection input never produces `PROTECTION_VERIFIED`.

## Authoritative verification rule

Submit acknowledgement alone is not protection verification.

Initial `PROTECTION_VERIFIED` requires explicit `query_performed=True` plus exact queried `OrderResult` evidence satisfying:

```text
order_request_id == request.order_request_id
client_order_id == request.client_order_id
requested_quantity == request.quantity
0 <= filled_quantity <= requested_quantity
order_status = OPEN
execution_health_status = HEALTHY
broker_order_id = known/non-empty
current lifecycle = OPEN_UNPROTECTED
current position reconciliation status = CONSISTENT
no contradictory reconciliation evidence
```

The resulting existing transition is:

```text
OPEN_UNPROTECTED + PROTECTION_VERIFIED -> OPEN_PROTECTED
```

If the original submit result was `UNKNOWN` or `RECONCILIATION_REQUIRED`, queried `OPEN / HEALTHY` is not sufficient by itself. A matching reconciliation result resolving the exact client order to `OPEN` with `retry_allowed=false` is required before verification.

The bridge never authorizes or calls retry.

## Definitive failure / loss mapping

For exact healthy/unambiguous queried truth:

```text
REJECTED
CANCELED
EXPIRED
```

map as follows:

```text
OPEN_UNPROTECTED -> PROTECTION_FAILED -> EMERGENCY
OPEN_PROTECTED   -> PROTECTION_LOST   -> EMERGENCY
PROFIT_PROTECTED -> PROTECTION_LOST   -> EMERGENCY
```

An authoritative query that completed but returned no order remains distinct from a query that was not performed. Query-not-found becomes definitive failure/loss only when supplied reconciliation evidence itself resolves the exact protection authority to a definitive inactive status without retry permission; otherwise it remains reconciliation-required.

## Unknown / reconciliation behavior

The bridge maps these to existing fail-closed reconciliation semantics and never to verified protection:

- query not performed;
- query completed but exact order not found without sufficient definitive reconciliation;
- `OrderStatus.UNKNOWN`;
- `OrderStatus.RECONCILIATION_REQUIRED`;
- `ExecutionHealthStatus.DEGRADED`;
- `ExecutionHealthStatus.UNKNOWN`;
- order-request or client-order identity mismatch;
- quantity mismatch or invalid fill quantity;
- contradictory query/reconciliation evidence;
- current normalized position reconciliation not `CONSISTENT`;
- malformed/non-protection request.

For an active lifecycle state this uses the existing `STATE_UNKNOWN -> RECONCILIATION_REQUIRED` transition. If the lifecycle is already `RECONCILIATION_REQUIRED`, repeated ambiguous evidence leaves it there without inventing a new self-transition.

## Triggered protective exit handling

`PARTIALLY_FILLED` and `FILLED` protective-stop statuses are intentionally **not** interpreted as `PROTECTION_FAILED` or `PROTECTION_LOST`.

They may represent the protective exit actually triggering. Because this task does not implement authoritative position close / TradeResult closure, these states remain fail-closed/reconciliation-required until the later bounded close chain exists.

## Deterministic tests materialized

Added:

- `tests/position/test_protection_result_bridge.py`

Definitions cover:

1. submit `OPEN` without authoritative query never verifies;
2. exact queried `OPEN / HEALTHY` verifies initial protection;
3. blank broker-order identity cannot verify;
4. order-request/client identity mismatch fails closed;
5. UNKNOWN / RECONCILIATION_REQUIRED order states fail closed;
6. DEGRADED / UNKNOWN execution health fails closed;
7. initial REJECTED / CANCELED / EXPIRED -> PROTECTION_FAILED -> EMERGENCY;
8. protected/profit-protected definitive loss -> PROTECTION_LOST -> EMERGENCY;
9. query-not-performed differs from query-performed/not-found;
10. sufficiently reconciled query-not-found may become definitive failure;
11. ambiguous submit cannot verify until exact OPEN reconciliation is supplied;
12. contradictory reconciliation/query truth never verifies;
13. PARTIALLY_FILLED / FILLED are not mislabeled as failure/loss;
14. repeated identical authoritative evidence is deterministic;
15. malformed non-protection request fails closed;
16. unreconciled current position truth fails closed;
17. repeated unknown evidence preserves existing reconciliation-required state;
18. callable bridge has no broker submit/query/retry argument or dependency;
19. existing state-machine entry-fill transition remains unchanged.

The tests use the accepted real E5 producer, real E4 `prepare_protection_order()`, and existing E4 `OrderResult` / `ReconciliationResult` model semantics. No test-only shared protocol was introduced.

## Scope confirmation

Changed only E5-owned paths:

- `src/position/protection_result.py`
- `src/position/__init__.py`
- `tests/position/test_protection_result_bridge.py`
- `status/E5_GATE_B_PROTECTION_RESULT_BRIDGE_20260824.md`
- `coordination/E5/STATUS.md` is written separately on the target branch.

Not changed:

- `contracts/**`
- ADRs
- `src/execution/**`
- `src/brokers/**`
- PaperBroker
- E6 persistence/registry
- E2/E3 code
- TradeResult closure/persistence
- provider/private APIs
- PAPER/SHADOW/LIVE authority
- GitHub Actions/CI/workflows

## Executable verification

```text
local_verification = NOT_RUN
```

Reason: no explicitly PM/Product-Owner-approved AgentBridge Local Runner action pinned to this exact new target revision is exposed in this session. This task did not execute project code or tests through GitHub/cloud/Computer Adapter.

Exact future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

No executable PASS is claimed.

## Release impact

This implementation closes only the static E5 implementation gap assigned by `E5-20260824-012`.

```text
Protection failure triggers emergency path = implementation materialized / executable evidence NOT_RUN
Required protection follows actual filled quantity = NOT_RUN
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

Do not interpret this artifact as Gate B criterion PASS.

## Completion

E5 stops on `DONE` after target-branch terminal STATUS is persisted. E5 does not self-start E7 integration, restart/persistence, E4 Fill lineage, Paper E2E, provider/private work, Gate C, PAPER, SHADOW, or LIVE.
