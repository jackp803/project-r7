# Gate B Close-to-TradeResult Integration Review — E7-20260824-040

## Authority / scope

- task_id: `E7-20260824-040`
- terminal disposition: `BLOCKED / SHARED FUNDING EVIDENCE SEMANTIC BOUNDARY REQUIRED`
- target branch: `agent/e7-gate-b-trade-result-integration-20260824`
- reviewed main: `21dac36db5086a7b13746a71f56e2cc1108d9a9b`
- authoritative TASK blob: `e1f4347864dd5cb79c40439c00414fc144a60da2`
- parent contract: `contracts-v0.1`
- close profile: `close-v0.1`
- TradeResult profile: `trade-result-v0.1`
- PnL profile: `linear-base-asset-pnl-v0.1`
- accepted contract PR #46: merge `d070ffc752d5c37c05aa4101ebc2f6add0c1ff48`
- accepted E5 close producer PR #47: merge `e4caa0e1398f2a3cdf1209fa7bc74516f6a94d15`
- accepted E4 close consumer PR #48: merge `3f7bba953ece100d23c88b86b47df52696adb3a0`
- accepted E5 TradeResult builder PR #49: merge `a9edc5db9f31efb0c4a8a0c33d54766093c70392`
- project executable verification: `NOT_RUN / NOT REQUIRED FOR STATIC REVIEW`

This task performed source/test-definition review only. No project code/tests, Paper runtime verification, Local Runner action, provider/private API, credentials, GitHub Actions/CI, hosted runner, Computer Adapter, PAPER, SHADOW, or LIVE activity was executed.

## Executive disposition

```text
ordinary EXIT close-to-authoritative-flat
= IMPLEMENTED_NEEDS_LOCAL_EVIDENCE / NOT_RUN

EMERGENCY_EXIT close-to-authoritative-flat
= IMPLEMENTED_NEEDS_LOCAL_EVIDENCE / NOT_RUN

ordinary EXIT -> final canonical TradeResult system chain
= BLOCKED / FUNDING_EVIDENCE_SHARED_BOUNDARY_MISSING

EMERGENCY_EXIT -> final canonical TradeResult system chain
= BLOCKED / FUNDING_EVIDENCE_SHARED_BOUNDARY_MISSING

PROTECTION_STOP -> same-position authoritative flat -> TradeResult
= BLOCKED / E4 IMPLEMENTATION_GAP

funding evidence producer/source
= CONTRACT_OR_SEMANTIC_GAP / next_owner=E7

Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

The blocker is not a contradiction in the accepted PnL formula or lifecycle authority. The missing item is a governed cross-module evidence boundary that a real Paper/runtime producer can emit and E5 can consume without importing an E5-private validation type.

## 1. Explicit ordinary EXIT chain

A real provider-neutral production chain is statically callable through authoritative flatness:

```text
E4-normalized CONSISTENT open Position
-> E5 authorize_close_position_action(... action=EXIT ...)
-> PositionEvent.EXIT_REQUESTED / lifecycle EXIT_REQUESTED
-> E4 prepare_close_order(...)
-> POSITION_EXIT / MARKET / reduce_only=true
-> PaperBroker.submit_order(...)
-> PaperBroker.record_fill(...)
-> exact Fill lineage: trade_plan_id + position_action_id + position_id + POSITION_EXIT
-> PaperBroker.observe_position_after_close(...)
-> same-position actual_quantity=0 + CONSISTENT truth
```

Static evidence:

- E5 `src/position/close.py` binds close quantity to exact current `Position.actual_quantity`, validates `CONSISTENT` truth, parent/risk/strategy lineage, lifecycle source, independent action expiry and deterministic action identity.
- E4 `src/execution/close.py` mechanically maps LONG->SELL / SHORT->BUY, `MARKET`, `reduce_only=true`, exact action quantity, and immediate authority lineage.
- PaperBroker close observer derives residual exposure only from the exact source Position and exact logical close Fill set. It does not use symbol-level net exposure or `OrderStatus.FILLED` as flat proof.

Classification:

```text
ordinary EXIT close-to-flat = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE / NOT_RUN
```

The chain cannot yet be classified as complete `TradeResult` system support because `build_trade_result()` requires funding evidence that no current shared producer can lawfully provide.

## 2. EMERGENCY_EXIT chain

The same real production subchain is statically callable for emergency closure:

```text
EMERGENCY Position
-> E5 EMERGENCY_EXIT authority
-> EXIT_REQUESTED
-> E4 EMERGENCY_EXIT / MARKET / reduce_only=true request
-> PaperBroker Fill(s)
-> exact emergency position-action/order-role lineage
-> same-position authoritative flat Position truth
```

The emergency distinction remains auditable in:

- `PositionAction.action = EMERGENCY_EXIT`;
- E5 deterministic emergency reason sequence;
- E4 `order_role = EMERGENCY_EXIT`;
- stable immediate-action-based order identity;
- exit Fill lineage.

Classification:

```text
EMERGENCY_EXIT close-to-flat = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE / NOT_RUN
```

Final canonical TradeResult remains blocked by the same missing funding evidence cross-module boundary/source.

## 3. PROTECTION_STOP full-close review

PR #45 materializes protection Fill lineage correctly:

```text
trade_plan_id
position_action_id
position_id
order_role = PROTECTION_STOP
```

E5 `build_trade_result()` is capable of validating a protection-authorized closure **if** a real same-position final flat Position is supplied.

However current E4/PaperBroker production support does not produce that fact for a protection stop. `PaperBroker.observe_position_after_close()` defines:

```text
_CLOSE_ROLES = {POSITION_EXIT, EMERGENCY_EXIT}
```

and rejects `PROTECTION_STOP` before deriving residual/flat Position truth.

Therefore an E5 unit test that manually supplies a flat Position is not system-level proof.

Classification:

```text
PROTECTION_STOP full-close -> authoritative flat -> TradeResult
= BLOCKED / IMPLEMENTATION_GAP
next_owner = E4
```

Required future E4 behavior is a provider-neutral same-position residual/flat observation path for `PROTECTION_STOP` that:

- consumes exact protection request/fill lineage;
- derives residual quantity from the exact source Position and exact protection Fill set;
- never substitutes symbol-level net exposure;
- never treats `FILLED` alone as flatness;
- preserves E5 lifecycle ownership.

## 4. Funding evidence producer boundary

### Current consumer

E5 PR #49 defines:

```python
FundingEvidence(
    status,
    source_version,
    position_id,
    interval_start,
    interval_end,
    funding_cost=None,
)
```

but explicitly documents this as:

```text
E5-internal validation input
not a shared/persisted funding contract
```

`build_trade_result()` requires this evidence and fails closed if it is absent, malformed, position-mismatched, interval-mismatched, or contradictory.

### Current producer inventory

No current real provider-neutral producer/source was found:

- `Broker` exposes submit/query-order/query-position/query-fills/reconcile/retry only;
- `PaperBroker` has no funding allocation/query/evidence surface;
- E6 currently persists only early Slice 2 Registry/CANDIDATE state and has no Paper funding/runtime evidence store;
- E5 unit tests construct the internal FundingEvidence directly, which is valid unit coverage but not a cross-module producer.

### Classification

```text
funding evidence producer/source
= CONTRACT_OR_SEMANTIC_GAP
next_owner = E7
```

Reason: directing E4 or E6 to construct/import an E5-private dataclass or an undocumented shape would create an ungoverned cross-module contract. `trade-result-v0.1` already requires authoritative/versioned funding evidence but does not materialize the serialized provider-neutral evidence object/profile needed to implement a producer safely.

This task's writable/acceptance rules require E7 to stop on this genuine shared-boundary gap rather than opportunistically edit contracts/ADR.

### Precise follow-up proposal

A bounded E7 contract task should materialize an additive provider-neutral funding allocation evidence profile under the existing contract set if compatibility remains additive. The minimum governed shape should bind at least:

```text
schema/profile version
stable funding_evidence_id
source/source_version
position_id
symbol
interval_start
interval_end
status = ZERO_CONFIRMED | INCLUDED
funding_cost when INCLUDED
cost currency / current PnL currency compatibility
observed/calculated timestamp
stable identity/idempotency material
```

Rules must explicitly define source completeness, exact interval coverage, signed cost semantics, zero-confirmation authority, unknown/partial fail-closed behavior, serialization, producer/consumer ownership, and persistence/audit expectations. No provider credentials or provider-native execution authority belong in the shared object.

Only after E7 materializes that boundary should a domain producer be implemented.

## 5. Entry evidence / identity binding

Static review result:

```text
PASS STATIC / COHERENT
```

E5 `build_trade_result()` does not use `trade_plan_id` alone to accept entry Fill evidence.

It requires:

- explicitly declared entry OrderRequest(s);
- unique exact `order_request_id` / `client_order_id` identities;
- each entry Fill `client_order_id` resolves to one declared request;
- entry request/fill plan/symbol/side/quantity semantics match;
- entry requests are plan-authorized and cannot carry PositionAction/exit/protection authority;
- every declared entry request has included Fill evidence.

The current one-position baseline is therefore contract-valid. As the accepted profile already states, multiple reopen/position instances under one plan would require stronger future binding before reuse of the same profile.

## 6. Fail-closed finance / lifecycle review

Static review found the following accepted invariants implemented:

- `OrderStatus.FILLED != flat Position proof`;
- final Position must be exact same `position_id`, `actual_quantity=0`, `CONSISTENT`;
- flat observation must be at/after latest exit Fill;
- partial/under-close cannot finalize;
- over-close is blocked by E4/PaperBroker and quantity-conservation checks;
- duplicate Fill IDs fail closed;
- the same Fill cannot appear in entry and exit sets;
- missing Fill fee evidence raises an error rather than silently becoming zero;
- non-zero unsupported fee currency fails closed;
- missing funding evidence cannot silently become zero;
- `ZERO_CONFIRMED` funding requires explicit authoritative evidence and zero/no cost;
- LONG/SHORT gross PnL follows Decimal `linear-base-asset-pnl-v0.1` formula;
- actual Fill prices determine realized PnL and no second slippage subtraction occurs;
- `trade_result_id` is deterministic over canonical authority/financial evidence;
- E5 aggregates/validates E4 facts but does not submit/query/rewrite broker truth;
- E4 close requests are reduce-only and exact-current-exposure bounded;
- no provider/private/PAPER/SHADOW/LIVE authority is introduced.

These are static findings only; executable evidence remains NOT_RUN.

## E7-owned test definitions materialized

### `tests/integration/test_gate_b_close_trade_result_chain.py`

Commit:

```text
29e900cb56b887b08634b8bef8062e68a3ad0bcf
```

Definitions intentionally use actual accepted production APIs and prove the current boundary rather than manufacturing a full pass:

- real ordinary EXIT reaches same-position authoritative flat truth;
- real EMERGENCY_EXIT reaches same-position authoritative flat truth;
- both then fail closed at final `build_trade_result(... funding_evidence=None)` because no real funding evidence source exists;
- real `PROTECTION_STOP` request + Fill is rejected by the current explicit-close-only PaperBroker flat observer.

No E5-private FundingEvidence object is injected into these E7 system definitions.

### `tests/safety/test_gate_b_close_trade_result_safety.py`

Commit:

```text
753dfa7534c57a477b4a47a9875b904b19ab65a3
```

Definitions use real entry/close requests, PaperBroker Fill truth and same-position observation for:

- residual partial close cannot finalize;
- `FILLED` evidence plus non-flat Position cannot finalize;
- missing fee cannot become zero;
- unsupported fee currency fails closed;
- duplicate real Fill evidence fails closed.

All definitions remain `NOT_RUN`.

## Release impact

No executable criterion is promoted to PASS.

Preserved:

```text
Required protection follows actual filled quantity = NOT_RUN
Protection failure triggers emergency path = NOT_RUN
Drawdown/daily/position/kill-switch = NOT_RUN
Restart/persistence = BLOCKED
Paper E2E / TradeResult durable audit = BLOCKED
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
```

The explicit close implementation portion of the Paper E2E blocker is now narrower: ordinary/emergency close-to-flat is source-materialized. The remaining full-chain blockers are the funding shared boundary/producer, PROTECTION_STOP same-position flat truth, E6 durable runtime persistence/restart/audit, full E7 E2E definitions, and approved-local evidence.

## Safe next dependency order

E7 does not start or assign these tasks automatically. Recommended PM sequence:

```text
1. E7 — materialize governed funding allocation evidence contract/profile
2. domain implementation — materialize provider-neutral Paper funding producer against that accepted boundary
3. E4 — materialize PROTECTION_STOP same-position residual/flat truth
4. E6 — durable Paper Position/Action/Order/Fill/Funding/TradeResult persistence + restart/audit
5. E7 — complete full Paper E2E/safety definitions
6. PM-authorized approved-local Gate B verification
```

The exact domain ownership of the funding producer should be fixed by the E7 funding contract task after producer/source semantics are explicit; E6 must not invent provider/execution truth merely because it persists evidence.

## Verification / security

```text
project_executable_verification = NOT_RUN / NOT REQUIRED FOR STATIC REVIEW
Local Runner = NOT_REQUESTED
GitHub Actions / CI / hosted runner = NOT_USED
GitHub-triggered project compute = NOT_USED
Computer Adapter = NOT_USED
provider/private requests = NOT_SENT
exchange credentials = NOT_USED
PAPER / SHADOW / LIVE = UNAUTHORIZED
E1-E6 production changes by E7 = NONE
shared contract/ADR changes in E7-040 = NONE / stopped for follow-up
Codex ticket = NONE
```

## Completion

E7-20260824-040 terminates `BLOCKED` because a genuine cross-module funding evidence boundary remains undefined. E7 does not self-start the funding contract follow-up, E4 protection-flat remediation, E6 persistence, approved-local verification, provider/private work, Gate C, PAPER, SHADOW, or LIVE.
