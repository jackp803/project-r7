# E4 Gate B PROTECTION_STOP Same-Position Flat Truth — 2026-08-24

## Handoff

**From:** E4 / Trading Execution & Broker Integration Engineer  
**To:** E7 / Project Manager  
**Branch:** `agent/e4-gate-b-protection-stop-flat-truth-20260824`  
**Task:** `E4-20260824-013`  
**Baseline main:** `4222a9989d86b9f9ed61b01b30d291768132f2a6`  
**Implementation/tests HEAD before this handoff:** `353814e5489b31488ed6cdcd1fd8dd0e8c69042e`  
**Date:** 2026-08-24

### 1. Objective

Implement only the previously identified E4-owned PaperBroker gap:

```text
canonical protection-v0.1 PROTECTION_STOP OrderRequest
+ exact already-protected same-position source Position
+ actual Paper Fill set
+ authoritative Paper OrderResult
-> exact same-position authoritative flat Position broker truth
```

The task stops at E4 broker/Position truth. It does not implement E5 lifecycle/TradeResult changes, E6 persistence/restart/audit, E7 full Paper E2E, provider/private APIs, funding changes, or release authority.

### 2. Contract-first disposition

Required inspection found:

```text
CONTRACT_OR_SEMANTIC_GAP = NO
```

The accepted `protection-v0.1` and `close-v0.1 / trade-result-v0.1` profiles already define all required authority/truth semantics:

- `PROTECTION_STOP` is a PositionAction-authorized reduce-only `STOP_MARKET` request;
- protection Fill carries exact `trade_plan_id`, `position_action_id`, `position_id`, and `order_role=PROTECTION_STOP` lineage;
- `OrderStatus.FILLED` alone is not flat Position proof;
- a full protection Fill may close a Position only after authoritative same-position `actual_quantity=0 + CONSISTENT` truth;
- partial protection execution with residual exposure is fail-closed/reconciliation-required until residual-protection semantics are separately defined.

No shared DTO, enum, state, Broker abstract method, contract, ADR, or E5 semantic was added or changed.

### 3. What changed

Modified only the PaperBroker same-position observation implementation in:

```text
src/brokers/paper.py
```

The previous close-only validation surface was refactored into a role-aware position-reduction boundary supporting exactly:

```text
POSITION_EXIT
EMERGENCY_EXIT
PROTECTION_STOP
```

#### Existing explicit close semantics preserved

`POSITION_EXIT` and `EMERGENCY_EXIT` remain:

```text
order_type = MARKET
reduce_only = true
limit_price = null
stop_price = null
time_in_force = null
```

Their existing partial-close behavior is unchanged: a coherent `PARTIALLY_FILLED` explicit close can still return a positive `CONSISTENT` residual Position observation.

#### New PROTECTION_STOP observation semantics

A protection-triggered observation requires the exact canonical request shape:

```text
authorization_type = POSITION_ACTION
order_role = PROTECTION_STOP
order_type = STOP_MARKET
reduce_only = true
stop_price = positive finite canonical value
limit_price = null
time_in_force = null
```

Immediate/parent request lineage must be present:

```text
trade_plan_id
position_action_id
position_id
risk_decision_id
```

The source Position must be exact and coherent:

```text
schema_version = contracts-v0.1
same position_id
same symbol
side LONG | SHORT
request side opposite Position side
actual_quantity > 0
request.quantity = exact source actual_quantity
reconciliation_status = CONSISTENT
quantity_profile_version = base-asset-v0.1
quantity_unit = BASE_ASSET
quantity_asset = BTC
valid opened_at / broker_state_observed_at
lifecycle_state = OPEN_PROTECTED | PROFIT_PROTECTED
```

`OPEN_UNPROTECTED` is intentionally rejected at this flat-proof boundary because an unverified protection request is not evidence that protection was established before trigger execution.

### 4. Actual Fill / OrderResult truth

`observe_position_after_close(...)` uses only the exact stored Paper order and exact Fill set for the supplied `client_order_id`.

Every included Fill must match exact:

```text
trade_plan_id
position_action_id
position_id
order_role
symbol
side
```

and carry a positive finite actual Fill quantity with coherent timestamps.

The observer requires:

```text
sum(exact Fill.quantity) = OrderResult.filled_quantity
OrderResult.requested_quantity = OrderRequest.quantity
execution_health_status = HEALTHY
```

Ambiguous submit acknowledgement, `UNKNOWN`, `RECONCILIATION_REQUIRED`, degraded execution truth, stale observations, contradictory quantities, lineage mismatch, or any other same-symbol Fill after the source Position observation fail closed.

Symbol-level `query_position().net_quantity` is not used as same-position flat proof.

### 5. Full PROTECTION_STOP -> authoritative flat truth

For the bounded V0.1 protection-stop closure path, a normal authoritative Position observation is returned only when:

```text
sum(PROTECTION_STOP Fill.quantity)
= OrderResult.filled_quantity
= OrderRequest.quantity
= exact source Position.actual_quantity

OrderResult.order_status = FILLED
observed_at >= latest included protection Fill.filled_at
```

Then PaperBroker returns the exact same Position shape with only E4-owned broker facts refreshed:

```text
actual_quantity = "0"
broker_state_observed_at = exact observation time
reconciliation_status = CONSISTENT
```

The source `lifecycle_state` is preserved unchanged. E4 does not emit or infer:

```text
POSITION_CLOSED
CLOSED
closed_at
exit_reason_codes
TradeResult
risk/lifecycle event
```

### 6. Partial / zero / terminal protection execution

Protection semantics are intentionally stricter than explicit close semantics.

```text
0 < summed protection Fill < source Position.actual_quantity
```

raises `ReconciliationRequiredError` even when the Paper order is coherently `PARTIALLY_FILLED`. E4 does not return an ordinary `CONSISTENT` residual Position because replacement/residual-protection safety has not been defined by the accepted profile.

Also no flat truth is emitted for:

- zero/no protection Fill;
- OPEN untriggered protection order;
- REJECTED/CANCELED/EXPIRED protection order;
- ambiguous/reconciliation-required submit state;
- non-HEALTHY execution truth;
- invalid request role/type/reduce-only/stop semantics;
- stale observation;
- mismatched request/source/Fill lineage;
- over-fill;
- interfering same-symbol Fill after source observation.

This does not reinterpret terminal protection failure into E5 lifecycle events.

### 7. Files changed

- `src/brokers/paper.py`
- `tests/brokers/test_paper_broker_protection_stop_flat_truth.py`
- `status/e4/E4_GATE_B_PROTECTION_STOP_FLAT_TRUTH_20260824.md`
- `coordination/E4/STATUS.md` (terminal mailbox update follows this handoff commit)

### 8. Contracts consumed

Consumed read-only without modification:

- `contracts-v0.1`
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`
- `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`
- `contracts/FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md` only to avoid scope overlap
- ADR-0005 authority/flatness semantics
- existing E4 `OrderRequest`, `OrderResult`, `Fill`, PaperBroker and Broker semantics
- accepted E5 TradeResult consumer behavior read-only

### 9. Contracts produced or changed

```text
NONE
```

### 10. Deterministic test definitions materialized

Added:

```text
tests/brokers/test_paper_broker_protection_stop_flat_truth.py
```

Definitions cover at minimum:

- LONG protected Position + full STOP SELL Fill -> exact flat `"0" + CONSISTENT` truth;
- SHORT protected Position + full STOP BUY Fill -> same;
- `PROFIT_PROTECTED` full-stop path;
- exact request/Fill/Position lineage;
- full-fill `FILLED` and quantity equality requirements;
- stale observation rejection;
- `OPEN_UNPROTECTED` rejection;
- partial protection Fill -> reconciliation-required, not consistent residual;
- zero/no Fill rejection;
- rejected/canceled/expired/ambiguous/degraded rejection;
- wrong role/type/reduce-only/stop/limit/TIF rejection;
- wrong side/position/symbol/quantity rejection;
- tampered Fill action/plan/symbol/side lineage rejection;
- overfill rejection;
- same-symbol interference rejection;
- existing `POSITION_EXIT` partial residual behavior;
- existing `EMERGENCY_EXIT` full-flat behavior;
- Paper funding producer compatibility;
- legacy entry behavior compatibility.

Definitions only; none were executed in this session.

### 11. Local verification

```text
Result: NOT_RUN
Environment: no explicitly PM/Product-Owner-approved exact-revision Local Runner action available in this session
```

Required future local Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
```

`NOT_RUN` is not PASS and does not upgrade any Gate B criterion.

### 12. Known limitations

- Partial PROTECTION_STOP execution remains deliberately reconciliation-required; residual/replacement protection is not solved here.
- This is in-memory Paper truth only; restart/durable runtime state remains E6 scope.
- No provider/private or Demo/live stop behavior is validated or authorized.
- No E5 lifecycle/TradeResult system-chain execution evidence is claimed.

### 13. Dependencies / blockers

```text
NONE for bounded static/source completion.
Executable local evidence remains outstanding.
```

Separate downstream blockers remain outside this task, including E6 durable Paper persistence/restart/audit and E7 full Paper E2E/local Gate B verification.

### 14. Required next action

E7/Project Manager may perform bounded static integration review and plan exact-revision approved-local verification. E4 does not self-start E5/E6/E7 work.

### 15. Security / secrets

- no API key, API secret, token, credential, password, private key, signature secret or live `.env` value was committed;
- fixtures are deterministic/sanitized;
- no provider/private request or credential was used.

### 16. GitHub compute policy

- no GitHub Actions workflow was created or used;
- no GitHub-hosted or GitHub-triggered runner was used;
- no project code/test was executed on GitHub infrastructure.

### 17. Live-trading / release impact

This change only materializes provider-neutral PaperBroker truth for a previously defined protection closure path. It does not authorize a Paper runtime, real order placement, provider/private calls, SHADOW, LIVE, capital exposure, or release-gate advancement.

```text
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

### 18. Codex bug ticket

```text
NONE
```
