# E4 -> E7 Handoff — Bounded Execution / PaperBroker Skeleton

## Handoff

**From:** E4 / Trading Execution & Broker Integration Engineer  
**To:** E7 / Integration Engineer  
**Branch:** `agent/e4-execution-v2`  
**Source/test commits:** `643493a52c7eae5f27233b212ddcdcec1938f5a3`, `ea32eb2c1e9c4a05a42cee3e60ad38ad49c34332`, `75f4264c5b3140ef76200cc36224a7d2b9604a22`, `1d7f9010b2387418f8076054057fdad821bcec86`, `878cfa31b81db451492cd7995a1bfcdc92ef7b7d`, `f74d674a705a536f68d15cf5a5c0f49862249343`  
**Date:** 2026-08-21

### 1. Objective

Construct only the minimum E4-owned static execution skeleton for later PAPER integration: ApprovedTradePlan authority gating, Broker abstraction, deterministic PaperBroker, OrderRequest/OrderResult/Fill state, idempotency, partial fills, and fail-closed reconciliation-before-retry behavior.

### 2. What changed

- Added E4-owned execution models consistent with `contracts-v0.1`.
- Added deterministic `client_order_id` and `order_request_id` identity for one logical order under one approved trade plan.
- Added an `ExecutionGateway` that rejects non-ApprovedTradePlan strategy-originated execution input.
- Added a minimum `Broker` abstraction for submit/query/fills/position/reconcile/retry.
- Added deterministic in-memory `PaperBroker` behavior for:
  - idempotent repeated submission;
  - idempotency conflict detection when payload changes under the same client ID;
  - requested quantity distinct from cumulative filled quantity;
  - explicit partial-fill and full-fill states;
  - explicit overfill rejection so paper exposure cannot exceed the approved OrderRequest quantity;
  - ambiguous acknowledgement simulation where the broker may or may not actually have accepted the order;
  - no blind duplicate submit after ambiguity;
  - explicit order query + position query + reconcile path;
  - broker-issued reconciliation token required before a retry can occur;
  - retry refusal if an order or exposure exists.
- Added local-only deterministic unittest definitions. They were not executed in GitHub or any unapproved environment.

### 3. Files changed

- `src/execution/models.py`
- `src/execution/gateway.py`
- `src/brokers/base.py`
- `src/brokers/paper.py`
- `tests/execution/test_gateway.py`
- `tests/brokers/test_paper_broker.py`
- `docs/execution/E4_TO_E7_HANDOFF.md`
- `coordination/E4/STATUS.md` (updated separately at completion)

### 4. Contracts consumed

`contracts-v0.1` / `contracts/SHARED_CONTRACTS_V1.md`:

- `ApprovedTradePlan`
- `OrderRequest`
- `OrderResult`
- `Fill`
- broker exposure / reconciliation ownership semantics from `Position`

Key enforced invariants:

- only `ApprovedTradePlan` may cross from strategy-originated flow into E4;
- E4 may not increase approved quantity or invent risk approval;
- requested and filled quantity remain distinct;
- ambiguous acknowledgement becomes `RECONCILIATION_REQUIRED` rather than permission to retry;
- actual fills are supplied as explicit paper broker facts, not copied from requested quantity/price.

### 5. Contracts produced or changed

`NONE` shared contracts changed.

E4 introduces internal implementation models/interfaces only. These do not redefine `contracts/**`.

#### CONTRACT MISMATCH — E5 nested entry instruction

Current E5 implementation emits a provisional nested shape equivalent to:

```text
entry_instruction:
  style: <E5/TradeIntent value>
  reference_price: <optional>
```

E5 explicitly marks this serialization provisional. `contracts-v0.1` does not define how `entry_instruction.style` maps to E4 `OrderRequest.order_type`, nor which styles require `limit_price`, `stop_price`, or `time_in_force`.

E4 therefore does **not** silently define `style=MARKET/LIMIT/...` semantics. `CurrentE5ProvisionalEntryTranslator` fails closed with `CONTRACT MISMATCH`. E7 must approve a mapping/sub-contract before the current E5 plan can be translated into a concrete entry `OrderRequest`.

The generic `ExecutionGateway` supports an injected `EntryInstructionTranslator` so E7 can approve this mapping later without changing the authority/idempotency/PaperBroker safety boundary.

### 6. Local verification

Result: `NOT_RUN`

Reason: no Product Owner-approved local execution environment was available to this chat. No project code/test was executed on GitHub infrastructure.

Required local commands from repository root:

```text
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

Expected coverage definitions include:

- ApprovedTradePlan-only authority;
- stable idempotency identity;
- current E5 nested-entry contract mismatch;
- expired plan rejection;
- partial fill representation;
- overfill/exposure-cap rejection;
- duplicate client ID payload conflict;
- ambiguous acknowledgement with accepted order -> no retry;
- ambiguous acknowledgement without order/exposure -> reconciliation token before retry;
- fabricated reconciliation evidence rejection.

No PASS is claimed until those commands run locally in an approved environment.

### 7. Known limitations

- No E7-approved mapping yet exists for E5 `entry_instruction.style` -> `OrderRequest.order_type`; concrete E5 plan entry submission is therefore intentionally fail-closed at translation.
- PaperBroker is in-memory only. Restart persistence/recovery is outside this bounded task.
- No cancel-order path, protective-order path, leverage/margin configuration call, account query, rate-limit model, or exchange adapter is included in this minimum skeleton.
- PaperBroker ambiguity outcomes are deterministic constructor fixtures for local failure-path tests; they are not a live retry mechanism.
- No SHADOW or LIVE operational mode exists in this implementation.

### 8. Dependencies / blockers

- **E7 contract decision required:** approve/version the E5 `entry_instruction` -> E4 `OrderRequest` mapping before concrete plan translation is enabled.
- Approved local Python environment required for executable verification.
- Private Pionex access is intentionally not needed and not authorized for this task.

### 9. Required next action

E7 should review:

1. authority and ownership boundaries;
2. internal Order/Fill/reconciliation state behavior;
3. the reported nested-entry CONTRACT MISMATCH;
4. whether to version/approve an entry-instruction mapping;
5. local test evidence after Product Owner-approved local execution.

Do not promote Gate B/PAPER_READY from this handoff alone.

### 10. Security / secrets

Confirmed:

- no real API key, API secret, token, credential, password, private key, or live `.env` value was committed;
- no Pionex credential handling was implemented;
- no private endpoint/request/signature code was added;
- test definitions contain only synthetic values.

### 11. GitHub compute policy

Confirmed:

- no GitHub Actions workflow was created or used;
- no GitHub-hosted or GitHub-triggered runner was used;
- no unit/integration/E2E test or broker simulation was executed on GitHub infrastructure;
- executable verification remains `NOT_RUN`.

### 12. Live-trading impact

This change cannot submit a real order and does not enable SHADOW or LIVE. It contains no Pionex private API integration, credentials, exchange calls, leverage changes, position sizing decisions, stop-policy decisions, or strategy promotion logic.

### 13. Codex bug ticket

`NONE` — no bounded implementation defect was established because executable verification was not run.
