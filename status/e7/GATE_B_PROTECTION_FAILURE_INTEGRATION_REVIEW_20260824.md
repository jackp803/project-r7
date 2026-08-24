# Gate B Protection Failure / Loss Integration Review — E7-20260824-034

## Authority / scope

- task_id: `E7-20260824-034`
- target branch: `agent/e7-gate-b-protection-failure-integration-20260824`
- reviewed latest main: `afd8198e2a0723ead53b366b389c7879a302e923`
- authoritative TASK blob: `f6dcd553aa0cb61ddf0049a0f52589d378a6f3b3`
- contract baseline: `contracts-v0.1 / BASELINE`
- protection profile: `protection-v0.1`
- E5 result bridge PR: `#41 / merge 4c3d0f47d26cb23d9baeb17d227a3a1a9185667f`
- E7 lifecycle review PR: `#42 / merge 05181bf06e9d1f2ad71990b94c446b6bf66d3582`
- E4 PaperBroker terminal truth PR: `#43 / merge d9394c18ca35406831e8966700c3a5210966fbb6 / head 1cded31e141912f2bfe86d04621973182d7bfc05`
- project executable verification: `NOT_RUN / DEFERRED TO LATER APPROVED-LOCAL TASK`

This task is static/test-definition only. E7 did not execute project code/tests, request Local Runner work, call provider/private APIs, use credentials, or authorize PAPER/SHADOW/LIVE.

## Terminal static disposition

```text
PaperBroker terminal truth -> E5 protection-result bridge = PASS STATIC / COHERENT
CONTRACT_OR_SEMANTIC_GAP = NO
real REJECTED -> PROTECTION_FAILED -> EMERGENCY = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
real verified OPEN -> CANCELED -> PROTECTION_LOST -> EMERGENCY = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
real verified OPEN -> EXPIRED -> PROTECTION_LOST -> EMERGENCY = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
terminal reconciliation/no-retry = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
terminal safety/idempotency = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
Protection failure triggers emergency path = NOT_RUN
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

`PASS STATIC` and `IMPLEMENTED_NEEDS_LOCAL_EVIDENCE` are review classifications, not executable PASS evidence.

## PR #43 static review

Current `PaperBroker` now provides real provider-neutral callable terminal truth:

### First-submit rejection

`rejected_outcomes` can deterministically make the exact request return/query:

```text
order_status = REJECTED
execution_health_status = HEALTHY
requested_quantity = exact request.quantity
filled_quantity = 0
broker_order_id = None
```

The same exact request/client identities are retained. Repeated identical submit stays rejected/idempotent; changed safety material under the same client ID remains an idempotency conflict.

### OPEN -> CANCELED

`cancel_order(client_order_id, observed_at=...)` transitions only exact `OPEN` truth to `CANCELED / HEALTHY` while retaining request/client/broker-order identity and quantity.

### OPEN -> EXPIRED

`expire_order(client_order_id, observed_at=...)` transitions only exact `OPEN` truth to `EXPIRED / HEALTHY` with the same identity/quantity guarantees.

Expiry is an explicit Paper observation. It does not reinterpret ApprovedTradePlan or PositionAction TTL.

### Reconciliation

For definitive current truth including `REJECTED`, `CANCELED`, and `EXPIRED`:

```text
retry_allowed = false
retry_token = None
```

The resolved status is the current authoritative queried status.

### Terminal safety

Current PaperBroker fail-closes on:

- unknown order terminalization;
- `PARTIALLY_FILLED -> CANCELED/EXPIRED` under this bounded surface;
- `FILLED -> CANCELED/EXPIRED`;
- cross-terminal rewrites;
- terminal orders receiving later fills;
- terminal orders reopening through repeated identical submit.

No E5 lifecycle logic was added to E4.

## E5 bridge coherence

PR #41 already requires exact canonical protection request identity, quantity consistency, healthy execution truth, and authoritative query evidence.

It maps definitive normalized statuses exactly as required:

```text
OPEN_UNPROTECTED + REJECTED/CANCELED/EXPIRED
-> PROTECTION_FAILED
-> EMERGENCY

OPEN_PROTECTED / PROFIT_PROTECTED + REJECTED/CANCELED/EXPIRED
-> PROTECTION_LOST
-> EMERGENCY
```

For the real PR #43 paths used here:

- initial configured rejection reaches the first mapping;
- query-verified OPEN then explicit cancel/expiry reaches the second mapping;
- no synthetic terminal `OrderResult` construction is used as system evidence.

The accepted state machine already contains the required emergency transitions. No contract/ADR change is required.

## E7 integration definitions materialized

### Real failure/loss lifecycle integration

`tests/integration/test_gate_b_protection_failure_lifecycle.py`

Commit:

```text
c741067d0be3afb0b882e54d0b1ed7bdae1ea535
```

Uses real accepted APIs:

- `build_protect_position_action(...)`
- `prepare_protection_order(...)`
- `PaperBroker(... rejected_outcomes ...)`
- `submit_order(...)`
- `query_order(...)`
- `cancel_order(...)`
- `expire_order(...)`
- `reconcile(...)`
- `ProtectionResultEvidence`
- `interpret_protection_result(...)`

Definitions cover:

1. real exact rejection -> query `REJECTED / HEALTHY` -> `PROTECTION_FAILED -> EMERGENCY`;
2. exact OPEN verification -> real cancel -> query `CANCELED / HEALTHY` -> `PROTECTION_LOST -> EMERGENCY`;
3. exact OPEN verification -> explicit real expiry -> query `EXPIRED / HEALTHY` -> `PROTECTION_LOST -> EMERGENCY`;
4. exact request/client/quantity lineage and broker-order lineage where one exists;
5. reconcile all three terminal statuses with `retry_allowed=false` and no retry token;
6. E5 outcome carries no broker retry authority.

### Terminal safety definitions

`tests/safety/test_gate_b_protection_terminal_safety.py`

Commit:

```text
cb7423bb58283aed103f3c66ccbb46b9237218ce
```

Uses canonical protection requests created through real E5/E4 APIs plus real PaperBroker calls. Definitions cover:

- unknown order cannot be canceled/expired;
- FILLED cannot become canceled/expired or reopen;
- PARTIALLY_FILLED is not reclassified into terminal protection failure/loss;
- REJECTED/CANCELED/EXPIRED orders do not reopen on repeated submit;
- terminal orders cannot receive later fills/create new Paper exposure.

No E7 helper reimplements E4/E5 business semantics.

## Gate B evidence reconciliation

The prior PR #42 blocker was specifically absence of real PaperBroker definitive inactive truth. PR #43 plus these definitions removes that implementation blocker.

Therefore:

```text
Protection failure triggers emergency path
BLOCKED / IMPLEMENTATION_GAP
-> NOT_RUN / IMPLEMENTED + DEFINITIONS MATERIALIZED; APPROVED-LOCAL EVIDENCE REQUIRED
```

It does not become PASS because no approved-local executable verification has occurred.

Other affected criteria remain unchanged:

```text
Required protection follows actual filled quantity = NOT_RUN
Drawdown/daily/position/kill-switch rules enforced = NOT_RUN
Restart/persistence preserves required state = BLOCKED / IMPLEMENTATION_GAP
Paper E2E closes to TradeResult and persists audit = BLOCKED / IMPLEMENTATION_GAP
Gate B = BLOCKED / NOT YET PASS
PAPER = UNAUTHORIZED
```

## Remaining dependency map

```text
Gate A                                               PASS
TradeIntent -> E5 RiskDecision                      NOT_RUN
E5 reject                                            NOT_RUN
ApprovedTradePlan-only strategy execution boundary  NOT_RUN
PaperBroker contract                                 NOT_RUN
Partial fill actual quantity                         NOT_RUN
Required protection follows actual filled quantity  NOT_RUN
Protection failure -> emergency                      NOT_RUN
Stale/unknown market blocks exposure                 NOT_RUN
Unknown order/position blocks exposure               NOT_RUN
Drawdown/daily/position/kill-switch                  NOT_RUN
Restart/persistence                                  BLOCKED / IMPLEMENTATION_GAP
Paper E2E -> TradeResult + audit                     BLOCKED / IMPLEMENTATION_GAP
GitHub CI/Actions not used                           PASS

Gate B                                               BLOCKED / NOT YET PASS
PAPER                                                UNAUTHORIZED
```

## Next bounded PM dependency

E7 does not assign the next task. The recommended next bounded implementation dependency is:

```text
next_owner = E4
bounded_dependency = PaperBroker protection Fill lineage propagation
```

Reason: the shared `Fill` model already has additive protection lineage, but current `PaperBroker.record_fill()` still does not populate:

```text
position_action_id
position_id
order_role
```

from the originating protection request. That lineage is required before the protective close path can be trusted through canonical TradeResult/durable audit integration.

After Fill lineage is materialized, remaining larger blockers are E4/E5 close-to-TradeResult semantics and E6 durable Paper runtime persistence/restart. Full Paper E2E definitions and approved-local Gate B execution follow only after those interfaces exist.

## Future approved-local verification

Not run in this task. A later PM-authorized local task should include at least:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/integration -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

These commands are not PASS evidence until actually executed in an approved environment against an exact revision.

## Verification / security / scope

```text
project executable verification = NOT_RUN / DEFERRED TO LATER APPROVED-LOCAL TASK
Local Runner = NOT_REQUESTED
GitHub Actions / CI / hosted runner = NOT_USED
GitHub-triggered project compute = NOT_USED
Computer Adapter = NOT_USED
provider/private requests = NOT_SENT
exchange credentials = NOT_USED
PAPER / SHADOW / LIVE = UNAUTHORIZED
E4/E5 production changes by E7 = NONE
contracts/ADR changes by E7 = NONE
Codex ticket = NONE
```

## Completion

E7 completes only `E7-20260824-034` after persisting E7-owned definitions/evidence/status. E7 does not self-start local verification, protection Fill lineage, restart/persistence, full Paper E2E, provider/private work, Gate C, PAPER, SHADOW, or LIVE.
