# E4 Gate B Close Consumer / Residual Position Truth — 2026-08-24

## Handoff

**From:** E4 / Trading Execution & Broker Integration Engineer  
**To:** E7 / Project Manager  
**Branch:** `agent/e4-gate-b-close-consumer-20260824`  
**Task:** `E4-20260824-009`  
**Baseline main:** `7014e5ee7a74c65c052ad5674f48f161d41d0434`  
**Date:** 2026-08-24

### 1. Objective

Implement only the E4-owned `close-v0.1` mechanical close-order consumer plus provider-neutral PaperBroker close Fill and same-position residual/flat broker truth required by the accepted dependency order:

```text
E5 close-v0.1 PositionAction.EXIT | EMERGENCY_EXIT
+ exact parent ApprovedTradePlan
+ exact current normalized Position
-> canonical close OrderRequest
-> PaperBroker close Fill truth
-> later/current same-position residual/flat broker observation
```

The implementation stops at E4 execution/broker truth. It does not implement E5 `POSITION_CLOSED`, TradeResult construction, E6 persistence/restart/audit, E7 Paper E2E, provider/private APIs, or any release authority.

### 2. What changed

#### close-v0.1 mechanical consumer

Added `src/execution/close.py`.

The consumer validates exact agreement between:

- accepted `close-v0.1` PositionAction;
- exact parent ApprovedTradePlan;
- exact current normalized Position observation.

Accepted actions:

```text
EXIT
EMERGENCY_EXIT
```

Mechanical mapping:

```text
EXIT           -> order_role=POSITION_EXIT
EMERGENCY_EXIT -> order_role=EMERGENCY_EXIT
LONG           -> SELL
SHORT          -> BUY
order_type     = MARKET
reduce_only    = true
quantity       = exact PositionAction.quantity = exact current Position.actual_quantity
limit_price    = null
stop_price     = null
time_in_force  = null
```

The request preserves exact:

- `trade_plan_id`;
- `position_action_id`;
- `position_id`;
- `risk_decision_id`;
- canonical quantity profile/unit/asset.

Logical order identity uses the already accepted immediate-authority rule:

```text
stable(position_action_id, order_role)
```

and deterministic `order_request_id` from that client identity.

The consumer fails closed for unsupported/missing profile/action/order type, expired action, parent/risk/strategy/risk-policy mismatch, position/source lifecycle/observation/reconciliation mismatch, quantity/profile/unit/asset mismatch, or actual quantity above the parent approved maximum.

The parent entry-plan expiry is structurally validated but is not reused as post-fill close-action lifetime. The close PositionAction's own `expires_at` is authoritative for close-action freshness.

#### PaperBroker close Fill truth

Existing `record_fill()` behavior already copies the originating request's additive lineage into each Fill. Therefore close fills automatically retain exact:

```text
trade_plan_id
position_action_id
position_id
order_role = POSITION_EXIT | EMERGENCY_EXIT
```

Partial/full fills retain their own actual quantity, price, time, fee and liquidity facts. Existing overfill prevention remains intact.

#### Same-position residual / flat broker truth

Added Paper-only callable:

```text
PaperBroker.observe_position_after_close(
    request,
    source_position,
    observed_at=...
)
```

This does not add a new shared DTO and does not modify the shared Broker interface. It returns the existing shared Position shape by copying the exact source Position and refreshing only E4-owned broker facts:

- `actual_quantity`;
- `broker_state_observed_at`;
- `reconciliation_status`.

The E5-owned `lifecycle_state` is preserved exactly and no `closed_at`, `POSITION_CLOSED`, exit reason, or TradeResult semantic is created.

Residual quantity is calculated only from:

```text
exact source Position.actual_quantity
- exact actual Fill set for this exact close request
```

It does **not** use symbol-level `query_position().net_quantity` as a same-position flatness proof and does not treat `OrderStatus.FILLED` alone as flat Position proof.

The observation fails closed when any of these make same-position truth uncertain:

- source Position is not exact/compatible/CONSISTENT;
- close request does not exactly reduce the source Position;
- original submit acknowledgement is `UNKNOWN` or `RECONCILIATION_REQUIRED`;
- stored order identity or execution health is inconsistent;
- OrderResult requested/filled quantity is inconsistent;
- Fill lineage, side, symbol, quantity or timestamps are inconsistent;
- Fill set quantity does not equal authoritative OrderResult filled quantity;
- total close Fill exceeds source Position quantity;
- observed time precedes source/order/latest Fill truth;
- another same-symbol Fill occurred after the source Position observation and could alter the exact position quantity.

State consistency is also required:

```text
0 fills                    -> not PARTIALLY_FILLED/FILLED
0 < fills < request qty    -> PARTIALLY_FILLED
fills == request qty       -> FILLED
```

Only when the exact source quantity is fully consumed by the exact close Fill set can the returned broker observation contain `actual_quantity = 0`.

### 3. Files changed

- `src/execution/close.py`
- `src/brokers/paper.py`
- `tests/execution/test_close.py`
- `tests/brokers/test_paper_broker_close_truth.py`
- `status/e4/E4_GATE_B_CLOSE_CONSUMER_20260824.md`
- `coordination/E4/STATUS.md` (terminal mailbox update follows this handoff commit)

### 4. Contracts consumed

Consumed without modification:

- `contracts-v0.1`
- `contracts/SHARED_CONTRACTS_V1.md`
- `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`
- `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`
- `docs/adr/ADR-0005-close-authority-and-trade-result-boundary.md`
- accepted E5 close producer `src/position/close.py` as read-only evidence
- existing E4 OrderRequest/Fill/idempotency/reconciliation semantics

Contract-first inspection result:

```text
CONTRACT_OR_SEMANTIC_GAP = NO
```

The existing shared Position fields are sufficient to represent a later/current same-position residual/flat broker observation without adding a parallel DTO or changing shared contracts.

### 5. Contracts produced or changed

```text
NONE
```

No contract, ADR, shared schema, E5 risk/lifecycle semantic, or shared Broker abstract interface was modified.

### 6. Local verification

```text
Result: NOT_RUN
```

Reason: no explicitly PM/Product-Owner-approved Local Runner action is available in this session for the exact clean target revision. Project execution was not substituted with GitHub or arbitrary cloud compute.

Required future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

`NOT_RUN` is not PASS.

### 7. Deterministic test definitions materialized

`tests/execution/test_close.py` covers at minimum:

- LONG EXIT -> SELL MARKET reduce-only POSITION_EXIT;
- SHORT EXIT -> BUY;
- EMERGENCY_EXIT -> distinct EMERGENCY_EXIT role/identity;
- exact quantity/parent/action/position/risk lineage;
- no limit/stop/TIF;
- deterministic same-action IDs and changed-authority non-collision;
- parent entry TTL independence;
- unsupported/expired authority fail closed;
- plan/risk/strategy/risk-policy mismatch;
- position ID/symbol/side/lifecycle/observation/reconciliation mismatch;
- quantity/profile/unit/asset mismatch and parent maximum bound;
- no provider-native or credential fields.

`tests/brokers/test_paper_broker_close_truth.py` covers at minimum:

- partial close Fill exact close lineage + truthful positive residual;
- full close Fill set exact lineage + broker-derived zero residual;
- `FILLED` order cannot override conflicting source Position truth;
- overfill/over-close rejection;
- SHORT/BUY and EMERGENCY close lineage;
- query_fills ordering/lineage preservation;
- ambiguous submit cannot be presented as definitive flat truth;
- other same-symbol Fill after the source observation blocks definitive same-position truth;
- terminal/reconciliation/no-retry compatibility;
- entry Fill legacy compatibility;
- protection Fill `PROTECTION_STOP` compatibility;
- no provider-native or credential fields.

These are definitions only and were not executed here.

### 8. Known limitations

- No E5 `POSITION_CLOSED` interpretation is implemented.
- No `trade-result-v0.1` builder is implemented.
- No E6 durable runtime persistence/restart/audit is implemented.
- No full Paper E2E is implemented.
- An ambiguous close submit deliberately cannot yield a definitive residual/flat observation through this bounded callable, even if an underlying Paper order later exists; later integration may reconcile first and provide a fresh authoritative Position path without weakening this fail-closed rule.
- The Paper-only observation relies on the exact source Position as the authoritative pre-close baseline. If other same-symbol Fill activity occurs after that baseline observation, it refuses to infer one-position truth.

### 9. Dependencies / blockers

No blocker for this bounded static/source completion.

Remaining downstream work is outside this task and remains governed by the accepted sequential dependency order. Executable evidence remains outstanding.

### 10. Required next action

E7/PM may perform bounded static integration review and later plan explicitly approved-local verification. E4 does not self-start the E5 TradeResult builder, E6 persistence, E7 Paper E2E, or local execution.

### 11. Security / secrets

Confirmed:

- no real API key, API secret, token, password, private key, credential, passphrase, signature secret, or live `.env` value was committed;
- fixtures use sanitized synthetic identifiers/values;
- no provider/private request was sent.

### 12. GitHub compute policy

Confirmed:

- no GitHub Actions workflow was created or used;
- no GitHub-hosted or GitHub-triggered runner was used;
- no unit/integration/E2E/broker simulation/project command was executed on GitHub infrastructure.

### 13. Live-trading impact

```text
provider/private API = NOT_CALLED
credentials = NOT_USED
PAPER = UNAUTHORIZED
SHADOW = UNAUTHORIZED
LIVE = UNAUTHORIZED
Gate B = BLOCKED / NOT YET PASS
```

This change materializes provider-neutral execution/broker source semantics only. It grants no strategy promotion, risk, capital, PAPER, SHADOW, LIVE, or release authority.

### 14. Completion boundary

This handoff does not claim:

```text
Paper E2E closes to TradeResult and persists audit = PASS
Gate B = PASS
PAPER_READY = PASS
PAPER / SHADOW / LIVE = AUTHORIZED
```

E4 stops after writing terminal STATUS for `E4-20260824-009`.