# E4 Current Task

- task_id: `E4-20260824-013`
- issued_at: `2026-08-24T15:15:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-gate-b-protection-stop-flat-truth-20260824`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`, `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`, ADR-0005, accepted protection chain PR #37-#45, accepted close/TradeResult chain PR #46-#50, funding contract PR #51, E4 funding producer PR #52, accepted E5 funding consumer PR #53

## Objective

Implement only the previously identified E4-owned **PROTECTION_STOP same-position residual/flat Position truth** gap for PaperBroker.

Bounded chain:

```text
accepted protection-v0.1 PROTECTION_STOP OrderRequest
+ exact source Position truth
+ actual PaperBroker protection Fill set
+ authoritative Paper OrderResult truth
-> exact same-position residual/flat Position observation
-> E5 may later consume flat truth for POSITION_CLOSED / TradeResult
```

Stop at E4 broker/Position truth. Do **not** implement E5 lifecycle/TradeResult changes, E6 persistence/restart/audit, E7 full Paper E2E, provider/private APIs, funding changes, or PAPER/SHADOW/LIVE authorization.

## Accepted prerequisites / current gap

Accepted contracts already state:

```text
OrderStatus.FILLED != flat Position proof

PROTECTION_STOP Fill may reduce or fully close the Position
partial protection Fill + residual exposure != POSITION_CLOSED
full protection Fill still requires authoritative same-position flat Position truth
```

Current `PaperBroker.observe_position_after_close()` can derive same-position residual/flat truth only for:

```text
POSITION_EXIT
EMERGENCY_EXIT
```

because the current close baseline accepts only reduce-only MARKET close-v0.1 requests. `PROTECTION_STOP` remains rejected even though its Fill lineage is already materialized and E5 TradeResult structurally supports protection-stop closure.

This task resolves only that implementation gap without changing shared contracts.

All executable evidence remains `NOT_RUN`; Gate B remains `BLOCKED`; PAPER remains unauthorized.

## Required inspection before editing

Read latest `main` and at minimum:

- `README.md`, `agents/README.md`, `agents/E4_EXECUTION.md`;
- `contracts/PROTECTION_OBJECT_PROFILE_V0_1.md`;
- `contracts/CLOSE_TRADE_RESULT_PROFILE_V0_1.md`;
- `contracts/FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md` read-only only to avoid accidental scope overlap;
- current `src/brokers/paper.py`, `src/brokers/base.py`, `src/execution/models.py`, `src/execution/protection.py`;
- existing E4 broker/execution tests for protection, close, terminal truth and Fill lineage;
- E5 `src/position/trade_result.py` read-only only to understand the final consumer expectation;
- accepted PR #48, #50, #52, #53 evidence and current release-gate status.

### Contract-first blocker rule

If exact same-position protection-stop observation cannot be implemented from the accepted protection/close contracts without inventing a new shared field/state/authority meaning, stop:

```text
BLOCKED / CONTRACT_OR_SEMANTIC_GAP
next_owner = E7
```

Do not modify `contracts/**`, ADRs, E5 code or invent a parallel cross-module Position/Fill contract.

## Required behavior

### 1. Accept canonical PROTECTION_STOP as a position-reduction observation source

Extend or safely refactor the E4 Paper close/position-observation surface so the exact canonical role:

```text
order_role = PROTECTION_STOP
authorization_type = POSITION_ACTION
order_type = STOP_MARKET
reduce_only = true
```

can be used to derive same-position exposure truth after actual protection Fill(s).

Do not weaken existing ordinary close semantics:

```text
POSITION_EXIT   -> MARKET + reduce_only=true
EMERGENCY_EXIT  -> MARKET + reduce_only=true
```

For `PROTECTION_STOP`, require protection-v0.1 request semantics rather than pretending it is close-v0.1 MARKET:

- exact `position_action_id`, `position_id`, `risk_decision_id`, `trade_plan_id` lineage;
- side opposite the source Position side;
- exact canonical quantity profile/unit/asset;
- `STOP_MARKET`;
- positive finite `stop_price`;
- `limit_price = null`;
- `time_in_force = null`;
- `reduce_only = true`.

Do not infer or modify stop level, quantity, side or authority.

### 2. Exact source Position truth

Require exact same-position source truth at the observation boundary:

```text
schema_version = contracts-v0.1
same position_id
same symbol
actual_quantity > 0 before the protection Fill set is applied
reconciliation_status = CONSISTENT
canonical quantity profile/unit/asset
valid opened_at / broker_state_observed_at
```

For protection-triggered closure, the source lifecycle must represent already-established protection:

```text
OPEN_PROTECTED | PROFIT_PROTECTED
```

Do not treat an unverified `OPEN_UNPROTECTED` protection request as proof that protection was active before the trigger.

The exact source quantity must equal the canonical protection request quantity for the V0.1 full-protection path. If current evidence requires a broader residual/replacement-protection semantic, fail closed rather than inventing it.

### 3. Actual Fill / OrderResult truth only

Use the exact stored Paper order and actual `Fill` objects for the exact `client_order_id`.

Every included protection Fill must preserve and match:

```text
trade_plan_id
position_action_id
position_id
order_role = PROTECTION_STOP
symbol
side
```

and must have positive finite quantity and an observation time consistent with source/order truth.

Require authoritative `OrderResult.filled_quantity` to equal the exact summed Fill quantity. Ambiguous/reconciliation-required/degraded or internally contradictory order truth cannot yield authoritative residual/flat Position truth.

Do not use symbol-level net exposure or `OrderStatus.FILLED` alone as a substitute.

### 4. Full protection Fill -> flat Position truth

For the bounded Gate B V0.1 protection closure path, authoritative flat truth may be emitted only when:

```text
sum(PROTECTION_STOP Fill.quantity)
= OrderResult.filled_quantity
= OrderRequest.quantity
= exact source Position.actual_quantity

OrderResult.order_status = FILLED
observed_at >= latest included protection Fill.filled_at
```

Then return/refine the exact same Position observation with E4-owned broker facts only:

```text
actual_quantity = "0"
broker_state_observed_at = exact observation time
reconciliation_status = CONSISTENT
```

Preserve E5-owned lifecycle state unchanged. Do not emit `POSITION_CLOSED`, `CLOSED`, exit reason, `closed_at`, TradeResult or risk semantics.

### 5. Partial protection execution fails closed

The accepted close profile explicitly says residual-protection semantics are not yet proven.

Therefore:

```text
0 < summed protection Fill quantity < source Position.actual_quantity
```

must **not** be returned as a normal `CONSISTENT` residual Position eligible for closure. Surface deterministic reconciliation-required/fail-closed behavior instead.

Do not create a new protection action, resize protection, infer residual safety, or issue an emergency exit in E4.

### 6. Zero-fill / terminal / ambiguous behavior

Do not emit flat truth for:

- zero protection Fill truth;
- OPEN protection order with no trigger fill;
- REJECTED/CANCELED/EXPIRED protection order;
- UNKNOWN/RECONCILIATION_REQUIRED order state;
- non-HEALTHY execution truth;
- stale observation time;
- mismatched source/request/Fill lineage;
- over-fill;
- another same-symbol Fill after the source Position observation that makes exact one-position attribution unsafe.

Existing protection failure/loss evidence behavior remains unchanged; this task does not reinterpret terminal protection state into E5 events.

### 7. Preserve existing E4 behavior

No regression or semantic weakening for:

- ordinary POSITION_EXIT residual/flat observations;
- EMERGENCY_EXIT residual/flat observations;
- protection submit/query/reconcile terminal truth;
- protection Fill lineage;
- order idempotency/conflict handling;
- partial/full Fill accounting;
- Paper funding producer PR #52;
- entry path.

Do not change the shared Broker abstract interface unless a genuine cross-broker contract requirement appears. If such a requirement appears, stop `BLOCKED / CONTRACT_OR_SEMANTIC_GAP / next_owner=E7` rather than broadening it opportunistically.

## Required deterministic test definitions

Add/update E4-owned tests covering at minimum:

- LONG protected Position + full PROTECTION_STOP SELL Fill -> exact same-position flat `actual_quantity="0" + CONSISTENT` truth;
- SHORT protected Position + full PROTECTION_STOP BUY Fill -> same;
- `PROFIT_PROTECTED` full-stop closure path;
- exact request/Fill/Position lineage preserved and checked;
- full Fill requires `FILLED` OrderResult and exact quantity equality;
- stale observation before latest protection Fill fails closed;
- source lifecycle OPEN_UNPROTECTED fails closed for protection-triggered flat proof;
- partial protection Fill fails closed / reconciliation-required and cannot return ordinary consistent residual truth;
- zero/no Fill cannot report flat;
- rejected/canceled/expired/ambiguous/degraded protection state cannot report flat;
- wrong order role/type/reduce_only/stop-price semantics fail closed;
- wrong side, position ID, action ID, plan ID, symbol or quantity fails closed;
- over-fill cannot produce flat truth;
- interfering same-symbol Fill after source observation fails closed;
- existing POSITION_EXIT / EMERGENCY_EXIT partial/full observation semantics remain unchanged;
- existing protection terminal/failure, Fill-lineage, funding producer and entry behavior remain compatible.

Use sanitized/fake deterministic fixtures only.

## Writable scope

E4-owned only:

- `src/brokers/paper.py`;
- other `src/brokers/**` or `src/execution/**` only if strictly necessary for this bounded E4 behavior;
- `tests/brokers/**`;
- `tests/execution/**` compatibility definitions if necessary;
- `docs/execution/**` only if needed;
- E4-specific `status/**` evidence/handoff;
- `coordination/E4/STATUS.md` on the target branch.

Forbidden:

- `contracts/**` / ADR changes;
- `src/position/**` / `src/risk/**`;
- E6 storage/platform;
- E1-E3 production;
- funding contract/consumer changes;
- provider/private network/API/credentials;
- PAPER/SHADOW/LIVE authority;
- GitHub Actions/CI/workflows.

## Executable verification

This is implementation/test-definition work under the hard local-only policy. Unless an exact-revision Local Runner action is separately approved by PM/Product Owner, record:

```text
local_verification = NOT_RUN
```

with exact future Windows PowerShell commands from repository root, at minimum:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
```

Do not use GitHub Actions/CI/hosted runners, GitHub-triggered self-hosted compute, arbitrary cloud execution, Computer Adapter, provider/private APIs or credentials. `NOT_RUN` is not PASS.

## Acceptance

### DONE

- real PaperBroker PROTECTION_STOP Fill truth can produce exact same-position authoritative flat Position broker truth for the supported full-fill path;
- full protection Fill is not equated with flatness without the later same-position observation;
- partial protection execution fails closed and does not pretend residual protection semantics are solved;
- exact request/Fill/Position lineage and quantity safety are enforced;
- ordinary/emergency close behavior and prior protection/funding behavior are preserved;
- no E5/E6/E7/provider/release scope is crossed;
- deterministic E4 tests are materialized;
- executable verification is approved-local evidence or explicit `NOT_RUN` with exact commands.

### BLOCKED

- accepted contracts cannot represent the required same-position protection-stop truth safely;
- record exact expected-vs-actual evidence and `next_owner = E7`;
- do not invent a workaround or parallel shared contract.

Do not declare `PROTECTION_STOP -> TradeResult`, Paper E2E, Gate B/PAPER_READY or any PAPER/SHADOW/LIVE mode PASS.

## Completion / mailbox rule

Commit/push bounded code/tests/evidence/status to `agent/e4-gate-b-protection-stop-flat-truth-20260824`.

Worker-owned terminal STATUS must be written/pushed to `coordination/E4/STATUS.md` on that target branch, not main.

Then stop. Do not self-start E6 persistence, E7 integration/E2E, approved-local verification, Gate C, PAPER, SHADOW or LIVE.