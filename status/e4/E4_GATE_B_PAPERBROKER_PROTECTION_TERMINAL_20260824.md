# E4 Gate B PaperBroker Protection Terminal Truth — Handoff

**From:** E4 / Trading Execution & Broker Integration Engineer  
**To:** E7 / PM  
**Branch:** `agent/e4-gate-b-paperbroker-protection-terminal-20260824`  
**Source/tests revision before this handoff:** `dc2d965b7694efae8981a9ab10845368ef64d21f`  
**Date:** 2026-08-24

## 1. Objective

Implement only E4-owned provider-neutral PaperBroker callable/queryable normalized truth for protection-order terminal/inactive states required by `E4-20260824-005`:

```text
exact canonical protection OrderRequest
-> PaperBroker normalized truth
-> REJECTED | CANCELED | EXPIRED / HEALTHY
```

No E5 lifecycle interpretation, provider/private execution, persistence, TradeResult closure, Paper E2E, or release-gate advancement is included.

## 2. Wake / authority verification

Wake task ID:

```text
E4-20260824-005
```

Latest `main:coordination/E4/TASK.md` matched exactly before implementation.

Required authority read from latest `main` before work:

- `README.md`
- `agents/README.md`
- `agents/E4_EXECUTION.md`
- `coordination/E4/TASK.md`

Only E4's TASK was read; no other Agent TASK was read or executed.

## 3. Branch baseline

The target branch initially lagged latest `main` by one commit and had no unique commits. It was safely fast-forwarded, without force/rebase, to:

```text
main = 387ed83dc6fd807e0907ff132e58e0193e20e5d4
```

Implementation then proceeded only on the target branch.

## 4. What changed

### Deterministic definitive rejection

`PaperBroker` accepts optional Paper-only simulation configuration:

```text
rejected_outcomes: client_order_id -> sanitized rejection reason
```

For a first exact submit configured for rejection:

- `order_status = REJECTED`;
- `execution_health_status = HEALTHY`;
- exact `order_request_id`, `client_order_id`, schema and requested quantity are retained;
- `filled_quantity = 0`;
- `broker_order_id = None` because Paper acceptance is not invented;
- `query_order(client_order_id)` returns the same definitive result;
- identical resubmission is idempotent;
- materially changed safety material under the same client identity remains `IdempotencyConflictError`;
- no fill/exposure can later be recorded against the rejected terminal result.

A client ID cannot simultaneously be configured for both ambiguous and rejected outcomes.

### OPEN -> CANCELED

New Paper-only callable:

```text
PaperBroker.cancel_order(client_order_id, observed_at=<UTC>)
```

Only a known exact `OPEN` order can transition. The terminal result retains:

- exact request/client identity;
- existing broker order ID;
- requested quantity;
- current filled quantity;
- `HEALTHY` execution health;
- explicit UTC terminal observation.

Repeated `cancel_order()` on the already canceled order is idempotent and returns the original terminal truth. It never reopens the order.

### OPEN -> EXPIRED

New Paper-only callable:

```text
PaperBroker.expire_order(client_order_id, observed_at=<UTC>)
```

It has the same identity/quantity/health/time guarantees as cancellation. Expiry is an explicit Paper event only; no parent-plan or protection-action TTL is reused as an automatic order-expiry rule.

### Strict terminal safety

Fail-closed behavior now includes:

- unknown order identity -> `UnknownOrderError`;
- `PARTIALLY_FILLED` cannot be canceled/expired by this bounded behavior;
- `FILLED` cannot be rewritten to canceled/expired;
- `REJECTED/CANCELED/EXPIRED` cannot cross-transition to another terminal status;
- terminal observation cannot precede the current order observation;
- fills are accepted only for `OPEN` or `PARTIALLY_FILLED` orders;
- `REJECTED/CANCELED/EXPIRED/FILLED` cannot receive a later fill through `record_fill()`.

There is deliberately no callable post-acceptance `reject_order()` transition. `REJECTED` is only established as a configured definitive first-submit Paper outcome, so a filled order cannot later be rewritten to rejected truth.

### Submission acknowledgement vs current order truth

`_submissions` continues to preserve the original submit acknowledgement while `_orders` holds evolving authoritative query truth.

This preserves the prior ambiguity semantics:

```text
ambiguous submit acknowledgement
+ accepted Paper order
-> query current order
-> reconcile exact current truth
```

A later fill/cancel/expiry does not silently rewrite the historical submit acknowledgement.

### Reconciliation

For an already definitive non-ambiguous order, `reconcile()` resolves from current queryable order truth and returns:

```text
retry_allowed = false
retry_token = None
```

Thus `REJECTED`, `CANCELED`, `EXPIRED`, as well as later definitive fill states, never create a duplicate-exposure retry token.

Existing ambiguous accepted/not-accepted reconciliation branches remain intact.

## 5. Files changed

- `src/brokers/paper.py`
- `tests/brokers/test_paper_broker_protection_terminal.py`
- `status/e4/E4_GATE_B_PAPERBROKER_PROTECTION_TERMINAL_20260824.md`
- `coordination/E4/STATUS.md` (terminal mailbox update follows this handoff)

No shared `Broker` interface change was required.

## 6. Contracts consumed

Consumed without modification:

- `contracts-v0.1`
- `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`
- `docs/adr/ADR-0004-actual-fill-protection-action-boundary.md`
- E4 canonical protection consumer `src/execution/protection.py`
- E4 normalized execution types in `src/execution/models.py`
- E5 read-only protection result bridge `src/position/protection_result.py`
- E7 review `status/e7/GATE_B_PROTECTION_LIFECYCLE_INTEGRATION_REVIEW_20260824.md`

E7's existing shared vocabulary (`REJECTED/CANCELED/EXPIRED`, health and reconciliation states) was sufficient. `CONTRACT_OR_SEMANTIC_GAP = NO` for this bounded implementation.

## 7. Contracts produced or changed

```text
NONE
```

No `contracts/**`, ADR, shared Broker interface, E5 risk/lifecycle semantics, or E6 persistence contract was changed.

## 8. Deterministic test definitions materialized

Added:

```text
tests/brokers/test_paper_broker_protection_terminal.py
```

Definitions cover:

- configured exact protection rejection -> submit/query `REJECTED / HEALTHY`, zero exposure;
- identical rejected resubmit -> deterministic/idempotent;
- changed request with same client identity -> idempotency conflict;
- `OPEN -> CANCELED` exact lineage/broker ID/quantity/health/time preservation;
- `OPEN -> EXPIRED` same preservation;
- query after terminal returns definitive truth;
- repeated same terminal operation is idempotent;
- repeat submit after canceled/expired does not reopen;
- reconcile `REJECTED/CANCELED/EXPIRED` -> exact terminal status, no retry, no token;
- unknown terminal operation fails;
- `FILLED` cannot become canceled/expired and resubmit remains filled;
- `PARTIALLY_FILLED` cannot be reclassified as terminal failure/loss;
- terminal order cannot later receive a fill or create exposure;
- prior ambiguous accepted query/reconcile behavior remains compatible;
- legacy entry submit/fill behavior remains compatible;
- no provider-native/credential fields are introduced by this Paper surface.

These are test definitions only. They were not executed in this environment.

## 9. Local verification

```text
Result: NOT_RUN
```

Reason: no explicitly PM/Product-Owner-approved Local Runner action is available in this session for the exact clean target revision. Project code was not executed through GitHub, hosted compute, Computer Adapter, provider API, or arbitrary cloud execution.

Required future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
```

`NOT_RUN` is not PASS.

## 10. Known limitations

Intentionally not implemented:

- E5 `PROTECTION_FAILED` / `PROTECTION_LOST` invocation;
- emergency lifecycle orchestration;
- protection Fill lineage propagation gap identified by E7;
- restart/durable persistence;
- TradeResult closure/audit;
- full Paper E2E;
- provider/private networking;
- Demo/live exchange execution;
- automatic protection expiry from any plan/action TTL.

`PARTIALLY_FILLED` protection cancellation semantics remain unsupported because safely terminalizing partial protective execution requires broader position-close/exposure semantics outside this TASK.

## 11. Dependencies / blockers

No shared contract blocker for bounded static/source completion.

Executable evidence remains outstanding. Prior E4/E5/E7 executable evidence remains `NOT_RUN` and is not upgraded by this task.

## 12. Required next action

`E7/PM` should perform the bounded static integration review and, only when explicitly authorized, arrange approved-local verification across broker/execution/position/integration/safety suites.

E4 does not self-start that integration or local execution task.

## 13. Security / secrets

- no real API key, secret, token, password, private key, credential, signature, or live `.env` value was used or committed;
- tests use sanitized Paper-only fixtures;
- no provider-native transport or credential surface was added.

## 14. GitHub compute policy

Confirmed:

- no GitHub Actions workflow was created or used;
- no GitHub-hosted/GitHub-triggered runner was used;
- no project test, Paper runtime, provider request, build, backtest, or executable verification ran on GitHub infrastructure.

## 15. Live-trading / release impact

This change adds only provider-neutral in-memory Paper normalized order truth needed for later integration definitions.

It does **not** authorize or claim:

```text
Protection failure triggers emergency path = PASS
Gate B = PASS
PAPER_READY = PASS
PAPER / SHADOW / LIVE = AUTHORIZED
```

Those states remain outside E4 authority and unchanged by this handoff.
