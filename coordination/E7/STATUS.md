# E7 Status

- task_id: `E7-20260821-006`
- agent: `E7`
- state: `COMPLETED`
- branch: `agent/e7-e2-e5-profile-review-20260821`
- summary: `Static producer-chain review accepted E2 entry-v0.1 TradeIntent production, E5 entry-v0.1/base-asset-v0.1 ApprovedTradePlan production, and the combined E2->E5 boundary. E4 may receive the next bounded profile/OKX sizing task pinned to the accepted producer revisions; private/Demo API remains excluded.`
- e2_static_disposition: `PASS / STATIC ONLY`
- e5_static_disposition: `PASS / STATIC ONLY`
- e2_to_e5_boundary_disposition: `PASS / STATIC ONLY`
- e2_reviewed_revision: `f99a8d00cd1fe40e1d73964d8b1cf37bc1886bd4`
- e5_reviewed_revision: `e5f7088301a92deadfd9f6c416ae03b466c38a47`
- e5_handoff_revision: `3c8f9fa558cc90ad69fd5e58dcd4f6aa457e8de4`
- e4_next_bounded_task_recommendation: `YES`
- e4_allowed_followup: `mechanical entry-v0.1 MARKET translation; canonical BTC quantity preservation; deterministic OKX metadata conversion and round-down-or-reject sizing; no private/Demo API`
- non_blocking_note: `E2-SIGNAL-SHAPE-HARDEN-001 — build_trade_intent does not independently require Signal.strategy_content_hash/reason_codes, but accepted StrategyRuntime always emits both; current runtime->TradeIntent chain remains canonical. Harden before broader external ingestion use.`
- contracts_changed: `NO`
- production_domain_code_changed: `NO`
- executable_verification: `NOT_RUN`
- github_compute: `NOT_USED`
- codex_ticket: `NONE / NOT_APPLICABLE`
- gate_a: `BLOCKED / UNCHANGED`
- gate_b: `BLOCKED / UNCHANGED`
- gate_c: `BLOCKED / UNCHANGED`
- gate_d: `BLOCKED / UNCHANGED`
- handoff_path: `status/e7/E2_E5_PROFILE_CHAIN_STATIC_REVIEW_20260821.md`
- next_owner: `PM`

## E2 static acceptance

Accepted exact producer semantics:

```text
TradeIntent.schema_version        = contracts-v0.1
TradeIntent.entry_profile_version = entry-v0.1
TradeIntent.entry_order_type      = MARKET
```

E2 requires explicit profile opt-in for executable eligibility. Legacy `entry_style` remains non-executable, `entry_reference_price` remains advisory, unsupported entry types fail closed, and provider/risk/quantity authority is rejected from TradeIntent.

The E2 profile implementation commit does not modify `src/strategy/runtime.py`; existing Slice 1 Strategy Runtime/DSL/Signal semantics remain structurally unchanged by this task.

## E5 static acceptance

E5 consumes the exact E2 field names/values above and rejects missing/unknown profile or unsupported order type.

A safe APPROVE path produces:

```text
entry_instruction.profile_version = entry-v0.1
entry_instruction.order_type      = MARKET
quantity_profile_version          = base-asset-v0.1
quantity_unit                     = BASE_ASSET
quantity_asset                    = BTC
quantity                          = E5-approved canonical BTC exposure upper bound
```

Advisory reference price is not promoted into executable limit/stop/trigger/TIF fields. Provider-native OKX sizing/metadata/API fields remain absent from E5.

Previously accepted `E5-RISK-UNKNOWN-001` fail-closed protections remain present, including unsafe/unknown state and contradictory status/boolean rejection.

## Combined E2 -> E5 boundary

Disposition:

```text
PASS / STATIC ONLY
```

There is no profile-field aliasing or translation ambiguity between the reviewed producer revisions. The authority chain remains:

```text
E2 Signal
-> E2 TradeIntent
-> E5 RiskDecision
-> E5 ApprovedTradePlan
-> future E4 mechanical/provider translation
```

No E2 object carries approved sizing/leverage/provider authority. E5 owns the risk-approved canonical exposure bound. OKX contract-unit conversion remains downstream E4/provider-adapter responsibility.

## Non-blocking hardening note

`E2-SIGNAL-SHAPE-HARDEN-001`:

`build_trade_intent()` validates a Signal mapping but does not independently require the parent Signal fields `strategy_content_hash` and `reason_codes`. Current accepted `StrategyRuntime.evaluate()` always emits both fields, so this is not a blocking defect for the reviewed runtime -> TradeIntent chain.

If `build_trade_intent()` is later exposed as a broader ingestion boundary, E2 should validate the complete canonical Signal envelope.

No Codex ticket is created because no executable defect was locally reproduced.

## Branch/integration note

At review time the E2 and E5 work branches are both diverged from current `main` and behind it by repository coordination/integration commits. Static acceptance binds to the exact reviewed revisions above.

A future integration/merge candidate must synchronize normally; any material producer/test changes after the reviewed pins require E7 re-review.

This does not change the source-level producer-chain PASS.

## E4 recommendation

PM may issue the next bounded E4 task, provided it pins/consumes these E7-accepted producer revisions and remains limited to:

- `LONG -> BUY`, `SHORT -> SELL`;
- `entry-v0.1 MARKET -> OrderRequest.order_type=MARKET` mechanically;
- no executable price/TIF invention;
- shared OrderRequest canonical quantity preserved in BTC base units;
- OKX instrument metadata validation and deterministic base-to-contract conversion inside E4/provider adapter only;
- round down to valid lot or reject;
- never round up above the E5-approved bound;
- stale/missing/incompatible metadata blocks new exposure;
- provider-native requested/filled contract counts remain separate audit facts.

Still excluded unless separately authorized:

- OKX private API;
- OKX Demo order submission;
- credentials;
- PAPER/SHADOW/LIVE enablement;
- withdrawal/funding-transfer/sub-account-capital-movement capability.

## Verification / release

All executable verification remains:

```text
NOT_RUN
```

No unit test, integration test, safety test, broker simulation, provider API request, backtest, GitHub Action, CI job, hosted runner, or GitHub project compute was executed for this review.

Release gates remain:

```text
Gate A RESEARCH_READY  BLOCKED
Gate B PAPER_READY     BLOCKED
Gate C SHADOW_READY    BLOCKED
Gate D LIVE_READY      BLOCKED
```

E7 stops after this task and waits for PM. No E4 implementation is started automatically.