# Gate B Protection Lifecycle Integration / Safety Review — E7-20260824-032

## Authority / scope

- task_id: `E7-20260824-032`
- target branch: `agent/e7-gate-b-protection-lifecycle-integration-20260824`
- reviewed latest main: `cbf285e40f9c33bc4b8aafe7dbb6a04c75b70293`
- authoritative TASK blob: `568df8caaece19c1c8f05f06101feccecbae5e68`
- contract baseline: `contracts-v0.1 / BASELINE`
- protection profile: `protection-v0.1`
- protection contract PR: `#37 / merge e6769b5b78f1b5f699ae4000204b803b2f8b69d5`
- E5 producer PR: `#38 / merge 268ac8708f84d0c856ac2d1d7436dcb100347a46`
- E4 consumer PR: `#39 / merge 44ec171817f6c13fa632f2e7658dccc6b518f777`
- E7 producer-consumer review PR: `#40 / merge 0c2202742c6fa601ac79b32603620a0553b95e2e`
- E5 protection-result bridge PR: `#41 / merge 4c3d0f47d26cb23d9baeb17d227a3a1a9185667f / head 4aeffaca987f4348912ed8691fc9b338b20f471a`
- project executable verification: `NOT_RUN / DEFERRED TO LATER APPROVED-LOCAL TASK`

This task is static/test-definition only. E7 did not execute project code, unit/integration/safety tests, PaperBroker runtime, provider/private APIs, Local Runner actions, GitHub Actions/CI, hosted runners, Computer Adapter, or arbitrary cloud compute.

## Terminal static disposition

```text
E5 protection-result bridge vs E4/PaperBroker normalized truth = PASS STATIC / COHERENT
CONTRACT_OR_SEMANTIC_GAP = NO
positive protection verification chain = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
ambiguous accepted/not-accepted reconciliation behavior = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
identity/quantity/health fail-closed interpretation = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
triggered PARTIALLY_FILLED/FILLED handling = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE
REJECTED source through real PaperBroker callable path = IMPLEMENTATION_GAP
CANCELED source through real PaperBroker callable path = IMPLEMENTATION_GAP
EXPIRED source through real PaperBroker callable path = IMPLEMENTATION_GAP
previously verified protection -> definitive loss source = IMPLEMENTATION_GAP
Protection failure triggers emergency path = BLOCKED / IMPLEMENTATION_GAP
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

`PASS STATIC` is an integration-review label only. It is not executable release evidence.

## E5 bridge static review

Accepted PR #41 adds `src/position/protection_result.py` and the callable:

```text
interpret_protection_result(request, evidence, current_state)
```

The bridge consumes only an exact canonical protection `OrderRequest` plus already-normalized E4 order/query/reconciliation truth. It does not submit, query, retry, cancel, or call providers.

Static behavior is coherent with `protection-v0.1` and ADR-0004:

- submit acknowledgement alone cannot verify protection;
- authoritative query is required;
- exact request/client identity and requested quantity must match;
- filled quantity must be within `[0, requested_quantity]`;
- `OPEN / HEALTHY` with known broker order identity may verify protection;
- an ambiguous original submit requires matching reconciliation to exact `OPEN` with `retry_allowed=false` before verification;
- unknown/reconciliation-required status, degraded/unknown health, identity mismatch, quantity mismatch, contradictory reconciliation, or inconsistent Position truth fails closed into existing reconciliation-required lifecycle semantics;
- exact definitive `REJECTED / CANCELED / EXPIRED` normalized truth maps initial protection to `PROTECTION_FAILED -> EMERGENCY` and previously protected state to `PROTECTION_LOST -> EMERGENCY`;
- `PARTIALLY_FILLED / FILLED` protective-stop truth is not mislabeled as failure/loss and remains reconciliation-required until later authoritative position-close/TradeResult behavior exists.

No shared contract contradiction was found.

## Real PaperBroker capability review

Current `src/brokers/paper.py` callable behavior was inspected directly.

### Implemented callable truth

`PaperBroker` can currently produce/observe:

- normal submit -> queryable `OPEN / HEALTHY`;
- ambiguous submit accepted -> submit `RECONCILIATION_REQUIRED / DEGRADED`, query exact `OPEN`, reconcile exact order to `OPEN / retry_allowed=false`;
- ambiguous submit not accepted -> no exact queried order, reconcile to `UNKNOWN / retry_allowed=true` when no exposure is present;
- `record_fill()` -> queryable `PARTIALLY_FILLED` or `FILLED`.

These are sufficient to define real positive verification, ambiguity, fail-closed, and triggered-stop scenarios using actual production APIs.

### Definitive inactive-state capability

Current PaperBroker exposes no public callable behavior that can make or later observe an exact protection request as:

```text
REJECTED
CANCELED
EXPIRED
```

It also exposes no callable state transition by which a previously query-verified `OPEN` protection order later becomes a definitive inactive state representing protection loss.

`OrderStatus` already contains these enum values and E5 PR #41 unit definitions already prove interpreter semantics using normalized fixture values. That is not system-level evidence that PaperBroker can produce those states.

Per TASK, E7 does not substitute direct synthetic `OrderResult(REJECTED/CANCELED/EXPIRED)` construction for the missing broker/PaperBroker capability.

Therefore:

| Required behavior | Classification | Reason |
|---|---|---|
| normal submit + authoritative OPEN query -> `PROTECTION_VERIFIED` | `IMPLEMENTED_NEEDS_LOCAL_EVIDENCE` | real PaperBroker query path + E5 bridge exist |
| ambiguous accepted -> explicit query/reconcile OPEN -> verified | `IMPLEMENTED_NEEDS_LOCAL_EVIDENCE` | real ambiguity/reconcile path exists |
| ambiguous not accepted -> no blind healthy inference | `IMPLEMENTED_NEEDS_LOCAL_EVIDENCE` | real `UNKNOWN / retry_allowed=true` reconciliation path exists; E5 remains fail closed |
| identity/quantity/health/reconciliation mismatch cannot verify | `IMPLEMENTED_NEEDS_LOCAL_EVIDENCE` | E5 bridge + normalized result model support deterministic fail closed definitions |
| protective `PARTIALLY_FILLED/FILLED` not failure/loss | `IMPLEMENTED_NEEDS_LOCAL_EVIDENCE` | real PaperBroker `record_fill()` produces these states |
| definitive `REJECTED` source | `IMPLEMENTATION_GAP` | no real PaperBroker callable source/observation path |
| definitive `CANCELED` source | `IMPLEMENTATION_GAP` | no real PaperBroker callable source/observation path |
| definitive `EXPIRED` source | `IMPLEMENTATION_GAP` | no real PaperBroker callable source/observation path |
| previously verified protection later definitively lost | `IMPLEMENTATION_GAP` | no real PaperBroker active->inactive transition/observation path |
| shared contract/vocabulary | `IMPLEMENTED_NEEDS_LOCAL_EVIDENCE` | existing OrderStatus/reconciliation/lifecycle semantics are sufficient; no new contract is required |

## E7 integration definitions materialized

### Integration

`tests/integration/test_gate_b_protection_lifecycle.py`

Commit:

```text
1e3528496daa61b5a81652c3723e999f4726fd4a
```

Uses actual production APIs:

- `position.build_protect_position_action(...)`
- `src.execution.protection.prepare_protection_order(...)`
- `src.brokers.paper.PaperBroker`
- `position.ProtectionResultEvidence`
- `position.interpret_protection_result(...)`

Definitions cover:

1. `OPEN` submit alone never verifies; exact authoritative `query_order()` does;
2. ambiguous submit actually accepted requires explicit query + `reconcile()` to `OPEN` before verification;
3. ambiguous submit not accepted returns no exact order and `retry_allowed=true`, but E5 remains reconciliation-required and receives no retry authority;
4. real PaperBroker `PARTIALLY_FILLED / FILLED` protective-stop truth is not mislabeled as `PROTECTION_FAILED` or `PROTECTION_LOST`.

### Safety

`tests/safety/test_gate_b_protection_result_safety.py`

Commit:

```text
8af7c3c82425442e021ce18085551af4e3aafb0e
```

Uses a real PaperBroker `OPEN` query result as the normalized baseline and exercises E5 fail-closed interpretation for:

- order-request/client identity mismatch;
- requested/fill quantity inconsistency;
- `DEGRADED / UNKNOWN` execution health;
- `UNKNOWN / RECONCILIATION_REQUIRED` order status;
- inconsistent current Position reconciliation status.

No helper reimplements E4/E5 domain semantics.

## Triggered protective Fill limitation

`PaperBroker.record_fill()` can produce the correct protection-order status transition to `PARTIALLY_FILLED / FILLED`, allowing the E5 interpreter boundary to be tested without calling this a protection failure.

However, current `record_fill()` still creates `Fill` without propagating the additive protection lineage already available on the originating request:

```text
position_action_id
position_id
order_role
```

This remains an E4 implementation gap before full close-to-TradeResult/durable-audit parity. It does not change the present failure/loss classification.

## Gate B evidence reconciliation

Canonical criteria after this review:

```text
Required protection follows actual filled quantity = NOT_RUN / unchanged
Drawdown/daily/position/kill-switch rules enforced = NOT_RUN / unchanged
Protection failure triggers emergency path = BLOCKED / IMPLEMENTATION_GAP
Restart/persistence preserves required state = BLOCKED / IMPLEMENTATION_GAP
Paper E2E closes to TradeResult and persists audit = BLOCKED / IMPLEMENTATION_GAP
Gate B = BLOCKED / NOT YET PASS
PAPER = UNAUTHORIZED
```

PR #41 closes the prior E5 interpreter implementation gap, but the emergency criterion cannot move to `NOT_RUN` because the complete provider-neutral PaperBroker callable source for definitive failure/loss truth is still absent.

No static label is promoted to executable `PASS`.

## Exact next bounded owner / PM recommendation

E7 does not assign work. The next dependency recommended to PM is a bounded **E4 PaperBroker protection terminal-state behavior** task.

Required behavior, without changing E5 risk authority:

1. expose provider-neutral deterministic PaperBroker behavior that can produce and later query exact-request normalized truth for `REJECTED`, `CANCELED`, and `EXPIRED` protection orders;
2. support an already query-verified `OPEN` protection order later becoming/querying a definitive inactive protection state so `PROTECTION_LOST` can be exercised through the real broker boundary;
3. preserve exact `order_request_id`, `client_order_id`, requested quantity, health and existing reconciliation/idempotency semantics;
4. never turn E4 retry permission into E5 retry authority;
5. keep provider/private semantics out of the PaperBroker contract and do not call E5 lifecycle logic from E4.

Safe dependency order:

```text
E4 real PaperBroker terminal/inactive protection truth
-> E7 real failure/loss integration definitions
-> approved-local E4/E5/integration/safety verification
```

Protection Fill lineage propagation remains a later E4 dependency before full TradeResult/audit closure. E6 restart/persistence and the full Paper E2E remain separately blocked.

## Future approved-local verification commands

Not run in this task. After the required E4 capability exists and PM explicitly authorizes local execution:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/integration -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

These commands are not PASS evidence until actually executed in an approved local environment and recorded against an exact revision.

## Verification / security / scope

```text
project executable verification = NOT_RUN / DEFERRED TO LATER APPROVED-LOCAL TASK
GitHub Actions / CI / hosted runner = NOT_USED
GitHub-triggered project compute = NOT_USED
Local Runner = NOT_REQUESTED
Computer Adapter = NOT_USED
provider/private requests = NOT_SENT
exchange credentials = NOT_USED
Paper/Shadow/Live runtime = NOT_USED / UNAUTHORIZED
E4/E5 production changes by E7 = NONE
contracts/ADR changes by E7 = NONE
Codex ticket = NONE
```

## Completion

E7 completes only `E7-20260824-032` after persisting bounded E7-owned tests/evidence/status. Gate B remains blocked. E7 does not self-start E4 terminal-state implementation, approved-local verification, restart/persistence, Fill lineage, full Paper E2E, provider/private work, Gate C, PAPER, SHADOW, or LIVE.
