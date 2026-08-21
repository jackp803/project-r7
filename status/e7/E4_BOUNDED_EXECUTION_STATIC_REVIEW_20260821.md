# E7 Static Review — E4 Bounded Execution / PaperBroker Skeleton

> Task: `E7-20260821-002`
> Reviewer: E7 Integration / Architecture / System QA / Release
> E4 source/handoff revision: `53487a93f6f10d89723403b1a2e2426ba1c7e82a`
> E4 branch: `agent/e4-execution-v2`
> E5 boundary revision: `cb65c951d59f6fd036bd61691d7e96d025e371c8`
> Contract baseline: `contracts-v0.1`
> Review type: static only
> Executable verification: `NOT_RUN`

## 1. Disposition summary

| Item | Disposition | Notes |
|---|---|---|
| E4 bounded Broker/PaperBroker skeleton | `PASS` | Static/source acceptance only. No executable PASS is claimed. |
| E4 test definitions | `PASS` | Sufficient bounded static coverage for this skeleton; local execution remains `NOT_RUN`. |
| E4 <-> E5 concrete entry translation | `BLOCKED` | `CONTRACT MISMATCH`, not merely missing glue. |
| Shared-contract collision | `PASS` | E4 changed no `contracts/**`; provisional E5 nesting remains unstabilized. |
| Scope compliance | `PASS` | E4 implementation revision adds only E4-owned source/tests/handoff files. |
| GitHub-compute policy | `PASS` | No workflow/CI/runner/project execution introduced or used. |
| Private Pionex / SHADOW / LIVE | `NOT_APPLICABLE` | Not implemented in this bounded skeleton. |
| Executable evidence | `NOT_RUN` | No Product-Owner-approved local environment evidence supplied. |
| Gate A/B/C/D | `BLOCKED` | Unchanged by this static review. |

Static PASS means the bounded design/source is acceptable for integration planning. It does not authorize PAPER, SHADOW, LIVE, or any release gate.

## 2. Reviewed repository evidence

E4 implementation/handoff revision `53487a93f6f10d89723403b1a2e2426ba1c7e82a` adds:

- `src/execution/models.py`
- `src/execution/gateway.py`
- `src/brokers/base.py`
- `src/brokers/paper.py`
- `tests/execution/test_gateway.py`
- `tests/brokers/test_paper_broker.py`
- `docs/execution/E4_TO_E7_HANDOFF.md`

The E4 branch completion status is updated separately under `coordination/E4/STATUS.md`.

No shared-contract file, E5/E6 implementation file, Pionex private adapter, or `.github/workflows` path is part of the bounded implementation revision.

## 3. Static acceptance matrix

### 3.1 ApprovedTradePlan-only execution authority — `PASS`

`ExecutionGateway.validate_approved_trade_plan(...)` requires the canonical outer ApprovedTradePlan envelope before preparing an order. A raw TradeIntent cannot satisfy the required plan fields.

The gateway consumes:

- exact plan identity;
- strategy/version/symbol;
- direction;
- approved quantity;
- leverage/margin metadata;
- entry/protection instruction containers;
- creation/expiry time;
- risk policy version.

It does not expose a raw strategy-signal/trade-intent submit shortcut.

### 3.2 No E4 risk invention or exposure expansion — `PASS`

E4 does not calculate position size, leverage, margin policy, risk approval, stop policy, or target policy.

For entry OrderRequest construction:

- quantity is parsed from the ApprovedTradePlan and preserved;
- side is deterministically derived from approved `LONG | SHORT` direction;
- the gateway does not raise quantity;
- leverage and margin mode are not changed by E4;
- protection instructions are not loosened or rewritten in this bounded skeleton.

The absence of leverage/margin/protection execution calls is a scope limitation, not hidden policy.

### 3.3 Stable idempotency identity — `PASS`

E4 derives stable identity from:

```text
trade_plan_id + logical_order_key -> client_order_id
client_order_id -> order_request_id
```

Repeated preparation for the same logical order produces the same IDs. `PaperBroker` also fingerprints safety-relevant payload fields and rejects the same client ID with a changed logical payload.

### 3.4 Requested vs filled quantity separation — `PASS`

`OrderResult` holds distinct `requested_quantity` and `filled_quantity` fields.

`PaperBroker.record_fill(...)` updates cumulative actual filled quantity while preserving the original requested quantity.

### 3.5 Partial-fill representation — `PASS`

A cumulative fill below requested quantity becomes `PARTIALLY_FILLED`; exact completion becomes `FILLED`.

No requested quantity is silently treated as filled quantity.

### 3.6 Explicit fill facts — `PASS`

Paper fills require explicit caller-provided:

- quantity;
- price;
- fill time;
- optional fee/currency/liquidity role.

Fill quantity and price are not copied from requested order values.

### 3.7 Overfill / exposure cap fail closed — `PASS`

Before recording a fill, E4 computes remaining approved order quantity. A fill larger than the remaining quantity raises `ExposureLimitError`.

This prevents PaperBroker from recording exposure beyond the approved OrderRequest quantity.

### 3.8 Ambiguous acknowledgement state — `PASS`

Ambiguous submission returns `RECONCILIATION_REQUIRED` with degraded execution health. E4 does not relabel ambiguity as accepted/open/filled truth for the caller.

### 3.9 No blind duplicate submit — `PASS`

Repeated ordinary `submit_order(...)` for an ambiguous client ID returns the same ambiguous result. It does not create a second logical order.

A changed payload under the same idempotency ID is rejected as an idempotency conflict.

### 3.10 Query / reconcile before retry — `PASS`

Retry requires broker-issued reconciliation evidence.

The reconciliation path compares supplied query evidence to current broker-owned order and position truth. Retry is denied when:

- the broker order exists;
- exposure exists;
- submitted query evidence is fabricated/stale/mismatched;
- no matching broker-issued retry token exists;
- order/exposure truth changes before retry.

A retry token is produced only after broker truth confirms both:

```text
order not found
AND
no exposure
```

### 3.11 Broker/order/fill/exposure truth remains E4-owned — `PASS`

`Broker` exposes explicit E4 methods for order, fill, position, reconcile, and guarded retry state. The PaperBroker itself verifies supplied reconciliation snapshots against its authoritative internal queries before issuing retry permission.

Neither E5 nor an external caller can manufacture retry permission by passing a boolean alone.

### 3.12 No private Pionex / SHADOW / LIVE behavior — `PASS` for scope boundary

No private API/signature/credential/order-submission implementation exists in this revision. No SHADOW or LIVE mode is introduced.

## 4. E4 test-definition review

Static test definitions cover:

- raw TradeIntent cannot cross the ApprovedTradePlan boundary;
- stable `client_order_id` / `order_request_id`;
- current provisional E5 nested entry shape fails closed;
- expired plan rejection;
- partial fill with requested/filled quantity separation;
- overfill rejection;
- idempotency conflict on changed payload;
- ambiguous acknowledgement with an accepted broker order -> no blind retry;
- ambiguous acknowledgement with no order -> query/reconcile/token required before retry;
- fabricated reconciliation evidence rejection.

Disposition: `PASS` for the bounded static skeleton.

Non-blocking test-strengthening recommendations for the future E4 follow-up:

1. add a direct assertion that the returned `Fill` preserves the explicit quantity/price/timestamp/trade-plan identity supplied as broker facts;
2. add a direct reconciliation case where no order is found but existing symbol exposure is non-zero, proving retry denial through the exposure branch;
3. after the entry-instruction contract is approved, add conditional-field mapping tests for every approved order type.

These recommendations do not overturn the current static skeleton PASS because the relevant source paths already fail closed and the concrete E5 entry integration remains blocked until contract resolution.

Executable result remains `NOT_RUN`.

Required local E4 commands remain:

```powershell
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

## 5. E4 <-> E5 boundary decision

### Classification — `CONTRACT MISMATCH`

This is **not** currently an `INTEGRATION GLUE GAP`.

Canonical `contracts-v0.1` says:

- E5 produces `ApprovedTradePlan.entry_instruction`;
- E4 produces `OrderRequest.order_type` plus conditional `limit_price`, `stop_price`, `reduce_only`, and `time_in_force`.

But v0.1 does not define the executable inner profile of `entry_instruction`.

Current E5 emits provisional:

```text
entry_instruction.style
entry_instruction.reference_price? 
```

There is no approved rule proving:

```text
style == MARKET -> order_type == MARKET
style == LIMIT  -> order_type == LIMIT
reference_price -> limit_price
which TIF applies
which price fields are required/forbidden
```

E4 would therefore be inventing shared semantics if it implemented this mapping unilaterally.

The current `CurrentE5ProvisionalEntryTranslator` is correct to fail closed.

### Resolution path

A shared semantic/version clarification is required before concrete E5 plan translation may be enabled.

Proposal:

`docs/architecture/E4_E5_ENTRY_INSTRUCTION_CONTRACT_CHANGE_PROPOSAL.md`

The proposal is deliberately not an edit to `contracts/**` and is not yet an approved contract version.

## 6. Producer / consumer impact inventory

### E5 — producer

Current role:

- emits ApprovedTradePlan;
- owns approved risk bounds;
- currently emits provisional nested entry serialization.

Required future correction after contract approval:

- emit the canonical entry instruction profile;
- validate supported entry semantics;
- never use an advisory/reference price as an executable limit price without explicit contract authority;
- reject unsupported entry styles fail closed.

### E4 — primary consumer

Current role:

- translates an approved plan into an OrderRequest;
- owns broker/order/fill/reconciliation truth.

Required future correction after contract approval:

- implement only the approved canonical translator;
- preserve plan quantity/direction and conditional fields exactly;
- reject incompatible version/order-type combinations;
- retain current idempotency/reconciliation safety behavior.

### E6 — secondary consumer/audit

Current early Slice 2 implementation does not yet persist ApprovedTradePlan, so no immediate E6 code correction is required for this finding.

When execution audit persistence is introduced, E6 must persist/trace the exact contract version and instruction without inventing semantics.

### E7 — integration authority

E7 must:

- complete the contract-change procedure;
- approve versioning/compatibility treatment;
- define integration/safety tests;
- keep Gate B blocked until local E4/E5 evidence exists.

## 7. Contract-change proposal disposition

Proposal classification:

```text
shared semantic clarification required = YES
in-place contracts-v0.1 change          = NO
compatibility                           = BREAKING if executable inner fields become required
proposed treatment                      = versioned contract change via normal E7 procedure
```

The proposal recommends a minimal canonical entry profile and explains why the current provisional `style`-only object cannot be treated as executable authority.

## 8. Branch / scope synchronization review

E4 implementation revision was produced on the fresh PM-created `agent/e4-execution-v2` branch.

At E7 review time the E4 branch is behind current `main` by later coordination/project-history commits. This does not invalidate the reviewed source revision, but the branch must be re-synchronized with then-current `main` before any future integration/merge action.

No history rewrite or force operation is required by this review.

## 9. Findings / blockers

### Blocking finding

`E7-E4E5-ENTRY-001`

- Classification: `CONTRACT MISMATCH`
- Owners: E7 contract authority first; then bounded E5 producer + E4 consumer follow-ups
- Effect: concrete current E5 ApprovedTradePlan -> E4 OrderRequest entry translation remains blocked
- Safety disposition: fail closed
- Codex: `NOT_APPLICABLE` — no locally reproduced implementation bug; this is a shared design/contract gap

### Non-blocking test recommendations

Owner: E4 future follow-up after contract resolution.

- direct explicit Fill-fact assertion;
- no-order + non-zero-exposure reconciliation denial test.

## 10. Release / evidence status

```text
E4 bounded skeleton static review          PASS
E4 test-definition static review           PASS
E4 <-> E5 entry translation                BLOCKED / CONTRACT MISMATCH
E4 executable tests                        NOT_RUN
E4/E5 integration executable test          NOT_RUN
Gate A                                     BLOCKED
Gate B                                     BLOCKED
Gate C                                     BLOCKED
Gate D                                     BLOCKED
PAPER / SHADOW / LIVE                      NOT ENABLED
```

No release gate is advanced by this review.

## 11. Stop condition

E7 completed only task `E7-20260821-002`.

No E4/E5/E6 production code was modified. No shared contract was modified. No follow-up correction is started automatically.
