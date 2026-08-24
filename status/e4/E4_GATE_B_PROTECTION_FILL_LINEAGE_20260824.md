# E4 Gate B Protection Fill Lineage Handoff — E4-20260824-007

**From:** E4 / Trading Execution / Broker Integration Engineer  
**To:** E7 / Project Manager  
**Branch:** `agent/e4-gate-b-protection-fill-lineage-20260824`  
**Source/tests head before this handoff:** `5686949b6ddd35774579daaf0b4afa4ece8d02c5`  
**Date:** 2026-08-24

## 1. Objective

Implement only the E4-owned PaperBroker `protection-v0.1` Fill-lineage propagation required by task `E4-20260824-007`:

```text
canonical protection OrderRequest
-> PaperBroker.record_fill(...)
-> canonical Fill retaining exact protection authority lineage
```

No E5 lifecycle, TradeResult, E6 persistence, provider/private API, Demo/live behavior, full Paper E2E, or release authority is included.

## 2. What changed

`PaperBroker.record_fill()` now copies the accepted additive protection lineage directly from the exact stored originating canonical `OrderRequest` into every emitted `Fill`:

```text
Fill.trade_plan_id      = OrderRequest.trade_plan_id   # existing behavior retained
Fill.position_action_id = OrderRequest.position_action_id
Fill.position_id        = OrderRequest.position_id
Fill.order_role         = OrderRequest.order_role
```

No lineage is derived from broker IDs, symbol, side, provider fields, or heuristics.

For a canonical protection request this preserves:

```text
position_action_id = exact immediate E5 PositionAction authority
position_id        = exact position lineage
order_role         = PROTECTION_STOP
```

For an entry/legacy request, the existing optional request fields are `None`, so emitted entry fills remain:

```text
position_action_id = None
position_id        = None
order_role         = None
```

The change does not modify fill identity material, per-fill quantity, price, time, fees, liquidity facts, cumulative quantity checks, order-status transitions, terminal-state behavior, reconciliation, or retry semantics.

## 3. Files changed

Production:

- `src/brokers/paper.py`

Tests:

- `tests/brokers/test_paper_broker_protection_fill_lineage.py`

Evidence/status:

- `status/e4/E4_GATE_B_PROTECTION_FILL_LINEAGE_20260824.md`
- `coordination/E4/STATUS.md` will be updated by the terminal status commit.

## 4. Contracts consumed

Read and consumed without modification:

- `contracts-v0.1`
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md` section 10
- `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`
- ADR-0004 actual-fill protection boundary
- accepted E4 canonical protection `OrderRequest` surface
- existing E4 `Fill` model additive lineage fields
- accepted PaperBroker terminal/reconciliation behavior from PR #43
- E7 PR #44 review artifact `status/e7/GATE_B_PROTECTION_FAILURE_INTEGRATION_REVIEW_20260824.md`

## 5. Contracts produced or changed

`NONE`

No shared model, contract, ADR, Broker abstract interface, E5 lifecycle vocabulary, or release gate was changed.

## 6. Deterministic test definitions materialized

`tests/brokers/test_paper_broker_protection_fill_lineage.py` defines coverage for:

1. protection partial Fill copies exact `trade_plan_id`, `position_action_id`, `position_id`, `order_role=PROTECTION_STOP`;
2. partial Fill retains exact actual per-fill quantity, price, timestamp, fee and liquidity facts;
3. subsequent full Fill on the same request retains the same exact authority lineage;
4. total fills cannot exceed originating `OrderRequest.quantity`;
5. `query_fills()` preserves lineage, ordering, Fill identity and repeated-read equality;
6. LONG-position protective SELL and SHORT-position protective BUY requests preserve lineage identically;
7. legacy/entry Fill retains `trade_plan_id` and keeps protection-only fields `None`;
8. REJECTED/CANCELED/EXPIRED orders still reject later fills;
9. existing ambiguous-accepted query/reconciliation behavior remains compatible;
10. canonical Fill surface contains no provider-native fields or credentials.

These are definitions only; no project code or tests were executed in this session.

## 7. Local verification

```text
Result: NOT_RUN
```

Reason: no explicitly PM/Product-Owner-approved Local Runner action is available in this session for the exact clean target revision.

Required future Windows PowerShell commands from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
```

`NOT_RUN` is not PASS. Prior E4/E5/E7 `NOT_RUN` evidence is not upgraded by this task.

## 8. Known limitations

This task stops at E4 canonical PaperBroker Fill truth. It intentionally does not implement:

- E5 protective-close lifecycle semantics;
- TradeResult construction/closure;
- E6 persistence, restart recovery, or durable audit;
- provider-native fill conversion/audit fields;
- full Paper E2E;
- approved-local Gate B execution;
- provider/private, Demo, PAPER, SHADOW, or LIVE execution.

## 9. Dependencies / blockers

No `CONTRACT_OR_SEMANTIC_GAP` was found for this bounded implementation.

Executable verification remains outstanding because no approved local runner was used.

Larger project blockers remain outside E4-20260824-007, including close-to-TradeResult semantics and durable Paper persistence/audit.

## 10. Required next action

Next owner: E7 / PM.

Recommended bounded next step is static integration review of the new PaperBroker Fill lineage and later explicitly approved-local verification. This handoff does not authorize E7 integration execution automatically and does not assign work.

## 11. Security / secrets

- no real API key, API secret, token, credential, password, private key, or live `.env` value was committed;
- fixtures are synthetic/sanitized;
- no provider request, signature, account access, or credential path was used;
- provider-native facts were not added to canonical Fill.

## 12. GitHub compute policy

Confirmed:

- no GitHub Actions workflow was created or used;
- no GitHub-hosted or GitHub-triggered runner was used;
- no unit/integration/E2E test, broker simulation, provider request, or project code was executed on GitHub infrastructure.

## 13. Live-trading impact

No live-trading authority or provider submission behavior is introduced.

This task does not claim:

```text
Paper E2E closes to TradeResult and persists audit = PASS
Gate B = PASS
PAPER_READY = PASS
PAPER / SHADOW / LIVE = AUTHORIZED
```

## 14. Completion boundary

E4 completes only `E4-20260824-007` in static/source form and stops after terminal STATUS. E4 does not self-start E7 integration, close-to-TradeResult behavior, persistence/restart, full Paper E2E, approved-local verification, provider/private work, Gate C, PAPER, SHADOW, or LIVE.
