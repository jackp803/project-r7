# Integration Status

> Owner: E7 Integration / Architecture / System QA / Release Engineer  
> Current review: `E7-20260824-040` / 2026-08-24  
> Reviewed main: `21dac36db5086a7b13746a71f56e2cc1108d9a9b`  
> Contract baseline: `contracts-v0.1 / BASELINE`  
> Profiles: `close-v0.1 / trade-result-v0.1 / linear-base-asset-pnl-v0.1`

## Current integration target

**Gate B / Slice 3 Paper readiness — real close-to-TradeResult chain**

This task is static source/test-definition review only. No project code/tests, Local Runner, Paper runtime verification, provider/private API, GitHub CI, SHADOW, or LIVE activity was executed.

## Release-gate state

```text
Gate A — RESEARCH_READY = PASS / RESEARCH-INTEGRATION ONLY
Gate B — PAPER_READY    = BLOCKED / NOT YET PASS
Gate C — SHADOW_READY   = BLOCKED / UNCHANGED
Gate D — LIVE_READY     = BLOCKED / UNCHANGED

PAPER / SHADOW / LIVE   = UNAUTHORIZED
project executable verification = NOT_RUN / NOT REQUIRED FOR STATIC REVIEW
```

## Accepted implementation state

```text
PR #46 close/TradeResult profiles       = ACCEPTED
PR #47 E5 close producer                = MATERIALIZED / NOT_RUN
PR #48 E4 close consumer + flat truth   = MATERIALIZED / NOT_RUN
PR #49 E5 TradeResult builder           = MATERIALIZED / NOT_RUN
```

## Explicit ordinary EXIT

A real production API chain is materialized through authoritative flatness:

```text
CONSISTENT open Position
-> E5 authorize_close_position_action(EXIT)
-> EXIT_REQUESTED
-> E4 prepare_close_order
-> POSITION_EXIT / MARKET / reduce_only
-> PaperBroker submit + actual Fill(s)
-> PaperBroker.observe_position_after_close
-> same position / actual_quantity=0 / CONSISTENT
```

Classification:

```text
ordinary EXIT close-to-flat = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE / NOT_RUN
```

Final TradeResult system completion remains blocked because no governed funding evidence producer/source exists.

## EMERGENCY_EXIT

A separate real production API chain is materialized:

```text
EMERGENCY Position
-> E5 authorize_close_position_action(EMERGENCY_EXIT)
-> EXIT_REQUESTED
-> E4 EMERGENCY_EXIT / MARKET / reduce_only
-> PaperBroker Fill(s)
-> same-position authoritative flat truth
```

Emergency reason/action/order-role identity is preserved.

Classification:

```text
EMERGENCY_EXIT close-to-flat = IMPLEMENTED_NEEDS_LOCAL_EVIDENCE / NOT_RUN
```

Final TradeResult system completion remains blocked by the funding evidence boundary/source gap.

## PROTECTION_STOP final close gap

Protection request/Fill lineage is available, and E5's builder can validate `PROTECT / PROTECTION_STOP` closure if authoritative flat Position truth is supplied.

Current E4 `PaperBroker.observe_position_after_close()` accepts only:

```text
POSITION_EXIT
EMERGENCY_EXIT
```

It therefore cannot derive/query same-position residual/flat truth after a real `PROTECTION_STOP` Fill.

```text
PROTECTION_STOP -> same-position flat -> TradeResult
= BLOCKED / E4 IMPLEMENTATION_GAP
```

A hand-constructed flat Position or symbol-level net exposure is not accepted as substitute system evidence.

## Funding evidence cross-module gap

E5 `src/position/trade_result.py` defines `FundingEvidence` explicitly as an internal validation input, not a shared/persisted contract.

Current producer inventory:

- E4 `Broker`: no funding query/allocation/evidence method;
- `PaperBroker`: no funding evidence producer;
- E6: no Paper runtime/funding persistence;
- tests: E5 constructs FundingEvidence directly for unit coverage only.

Because `build_trade_result()` requires exact `ZERO_CONFIRMED | INCLUDED` funding evidence over the exact position interval, E4/E6 cannot safely be told to construct an E5-private DTO or undocumented mapping.

Classification:

```text
funding evidence producer/source
= CONTRACT_OR_SEMANTIC_GAP
next_owner = E7
```

A bounded follow-up must first materialize a governed provider-neutral funding allocation evidence profile/object, including exact position/interval/status/cost/source/version/identity semantics. The producer owner should then be fixed from that authoritative boundary; E6 may persist truth but must not invent provider/execution truth.

## Entry identity binding

Static result: `PASS STATIC / COHERENT`.

E5 builder requires every entry Fill to bind through exact `client_order_id` to a declared entry OrderRequest. It validates unique request IDs, plan/symbol/side/quantity semantics, and rejects unused declared requests. `trade_plan_id` alone is not sufficient.

The current one-position baseline remains valid. Multiple position instances/reopens under one plan would require stronger future entry-to-position binding as already documented by the profile.

## Fail-closed financial/lifecycle semantics

Static source implements:

```text
FILLED != flat proof
final same-position actual_quantity=0 + CONSISTENT required
flat observation >= latest exit Fill
partial/under/over-close cannot finalize
duplicate Fill IDs cannot finalize
missing Fill fee cannot silently become zero
unsupported non-zero fee currency fails closed
missing funding evidence cannot silently become zero
LONG/SHORT Decimal PnL follows accepted profile
actual Fill prices are not charged again as slippage
TradeResult identity is deterministic
E5 does not rewrite E4 broker truth
E4 close request is exact-current-exposure + reduce_only
```

## E7 definitions added

`tests/integration/test_gate_b_close_trade_result_chain.py`

- commit `29e900cb56b887b08634b8bef8062e68a3ad0bcf`;
- real ordinary and emergency close-to-flat production paths;
- proves finalization fails closed without funding evidence instead of injecting an E5-private FundingEvidence object;
- proves current real PROTECTION_STOP Fill cannot use the explicit-close-only flat observer.

`tests/safety/test_gate_b_close_trade_result_safety.py`

- commit `753dfa7534c57a477b4a47a9875b904b19ab65a3`;
- real partial close residual, non-flat proof, missing fee, unsupported fee currency and duplicate Fill fail-closed definitions.

No test was executed.

## Gate B evidence reconciliation

```text
Required protection follows actual filled quantity = NOT_RUN
Protection failure triggers emergency path          = NOT_RUN
Drawdown/daily/position/kill-switch                 = NOT_RUN
Restart/persistence                                 = BLOCKED / E6 IMPLEMENTATION_GAP
Paper E2E -> TradeResult + durable audit            = BLOCKED
Gate B                                               = BLOCKED / NOT YET PASS
PAPER                                                = UNAUTHORIZED
```

The Paper E2E blocker is now decomposed as:

1. shared funding evidence boundary/source missing;
2. PROTECTION_STOP same-position flat observer missing in E4;
3. E6 durable Paper runtime persistence/restart/audit missing;
4. complete E7 E2E definitions and approved-local evidence still pending.

## Safe next dependency order

E7 does not start/assign follow-up work automatically.

Recommended PM order:

```text
1. E7 funding allocation evidence contract/profile
2. provider-neutral Paper funding producer under the accepted boundary
3. E4 PROTECTION_STOP same-position residual/flat truth
4. E6 durable Paper runtime persistence/restart/audit
5. E7 complete Paper E2E/safety definitions
6. PM-authorized approved-local Gate B verification
```

## Verification / scope

```text
project executable verification = NOT_RUN / NOT REQUIRED FOR STATIC REVIEW
GitHub Actions / CI / hosted runner = NOT_USED
GitHub-triggered compute = NOT_USED
Local Runner = NOT_REQUESTED
Computer Adapter = NOT_USED
provider/private requests = NOT_SENT
exchange credentials = NOT_USED
PAPER / SHADOW / LIVE = UNAUTHORIZED
E1-E6 production changes by E7 = NONE
contracts/ADR changes by E7 = NONE
Codex ticket = NONE
```

## Detailed evidence

`status/e7/GATE_B_TRADE_RESULT_INTEGRATION_REVIEW_20260824.md`

## Completion

E7-040 terminates `BLOCKED` on the shared funding evidence boundary. E7 does not self-start that contract task, E4 remediation, E6 persistence, local verification, Gate C, PAPER, SHADOW, or LIVE.
