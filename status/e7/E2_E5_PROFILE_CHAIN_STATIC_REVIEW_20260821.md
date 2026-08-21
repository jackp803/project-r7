# E7 Static Review — E2 -> E5 Execution Profile Producer Chain

- task: `E7-20260821-006`
- date: `2026-08-21`
- review branch: `agent/e7-e2-e5-profile-review-20260821`
- parent schema: `contracts-v0.1`
- entry profile: `entry-v0.1`
- quantity profile: `base-asset-v0.1`
- E2 reviewed implementation: `f99a8d00cd1fe40e1d73964d8b1cf37bc1886bd4`
- E5 reviewed implementation: `e5f7088301a92deadfd9f6c416ae03b466c38a47`
- E5 reviewed handoff successor: `3c8f9fa558cc90ad69fd5e58dcd4f6aa457e8de4`
- executable verification: `NOT_RUN`

## Final dispositions

```text
E2 TradeIntent producer                         PASS / STATIC ONLY
E5 RiskDecision -> ApprovedTradePlan producer  PASS / STATIC ONLY
Combined E2 -> E5 profile boundary             PASS / STATIC ONLY
Executable evidence                            NOT_RUN
E4 bounded follow-up recommendation            YES, with pinned accepted producer revisions
Gate A / B / C / D                              BLOCKED / UNCHANGED
```

Static PASS is not executable PASS and does not authorize PAPER, OKX Demo, SHADOW, or LIVE execution.

## 1. E2 review

### Accepted behavior

E2 now has a provider-neutral TradeIntent production boundary at `src/strategy/trade_intent.py`.

Execution-profile eligibility requires explicit opt-in:

```text
entry_profile_version = entry-v0.1
entry_order_type      = MARKET
```

Observed fail-closed behavior:

- `entry_order_type` without a profile is rejected;
- unknown profile versions are rejected;
- `entry-v0.1` without an order type is rejected;
- any executable order type other than exact `MARKET` is rejected;
- LIMIT/stop/trigger/TIF/post-only/IOC/FOK/trailing fields are rejected;
- provider/exchange fields such as OKX/Pionex identifiers, `sz`, `ordType`, `tdMode`, and provider instrument IDs are rejected;
- quantity, approved quantity, leverage, margin mode, risk approval, broker credentials, and direct order identity are rejected from TradeIntent.

Legacy fields remain non-executable:

- `entry_style` may exist as legacy/advisory data but does not create profile fields;
- `entry_reference_price` remains a positive finite advisory decimal string and does not create executable price fields.

The produced profile field names and values exactly match the canonical profile:

```text
entry_profile_version = entry-v0.1
entry_order_type      = MARKET
```

### Slice 1 semantic preservation

The E2 implementation commit changes only:

- `docs/strategy/TRADE_INTENT_ENTRY_PROFILE.md`
- `src/strategy/__init__.py`
- `src/strategy/trade_intent.py`
- `status/E2_TRADE_INTENT_ENTRY_PROFILE_HANDOFF.md`
- `tests/strategy/test_trade_intent.py`

`src/strategy/runtime.py` was not changed by the profile implementation commit.

The existing runtime still produces canonical Signal fields including `strategy_content_hash` and `reason_codes`, and the new deterministic test definitions retain a same-input/same-Signal regression case. No StrategyDefinition, DSL, SMA, Candle, or Signal semantic rewrite was introduced by this task.

### E2 deterministic test definitions

Static test definitions cover:

- deterministic canonical `entry-v0.1 / MARKET` serialization;
- unknown profile rejection;
- missing order type rejection;
- unsupported LIMIT rejection;
- legacy style-only intent remains non-executable;
- reference price remains advisory;
- provider-specific field rejection;
- sizing/risk authority rejection;
- unchanged existing Strategy Runtime determinism.

Executable disposition remains `NOT_RUN`.

### E2 non-blocking hardening note — `E2-SIGNAL-SHAPE-HARDEN-001`

`build_trade_intent()` is publicly exported and validates a Signal mapping, but its local required-field set does not independently require two parent `contracts-v0.1` Signal fields:

- `strategy_content_hash`
- `reason_codes`

The currently accepted `StrategyRuntime.evaluate()` always emits those fields, so the reviewed runtime -> TradeIntent chain is canonical and this does not create a producer-chain ambiguity or authority bypass in the current construction path.

Disposition:

```text
NON_BLOCKING / HARDENING
```

Future owner: E2, if `build_trade_intent()` becomes a broader ingestion boundary rather than an internal producer step. At that time the complete canonical Signal envelope should be validated rather than accepting a structurally incomplete Signal-shaped mapping.

This note does not block the current profile task and is not a Codex bug because no executable defect was locally reproduced.

## 2. E5 review

### Exact E2 profile consumption

E5 accepts the same exact fields and values produced by E2:

```text
entry_profile_version = entry-v0.1
entry_order_type      = MARKET
```

E5 does not infer executable semantics from legacy `entry_style`.

Missing profile, unknown profile, missing order type, unsupported order type, or unsupported canonical symbol for the bounded quantity profile adds rejection reasons and prevents APPROVE.

### ApprovedTradePlan entry profile

A safe approved profiled intent produces:

```text
entry_instruction.profile_version = entry-v0.1
entry_instruction.order_type      = MARKET
```

If `entry_reference_price` exists, E5 may retain it only as:

```text
entry_instruction.reference_price
```

It remains advisory. The E5 plan does not create:

- `limit_price`
- `stop_price`
- `trigger_price`
- `time_in_force`

and does not copy legacy `style` into the executable instruction.

### Canonical quantity profile

For the bounded canonical symbol:

```text
BTC_USDT_PERP
```

E5 emits:

```text
quantity_profile_version = base-asset-v0.1
quantity_unit            = BASE_ASSET
quantity_asset           = BTC
quantity                 = <approved positive finite BTC exposure bound>
```

The returned plan quantity is the E5-approved canonical BTC quantity, not an OKX contract count.

No provider-native sizing metadata is emitted into the plan. The E5 implementation does not add OKX `sz`, `ctVal`, `ctMult`, `ctValCcy`, `lotSz`, `minSz`, `tickSz`, provider instrument IDs, account-mode calls, provider API calls, or credential concerns.

### Existing E5 fail-closed safety remains intact

The previously accepted `E5-RISK-UNKNOWN-001` behavior remains present:

- explicit safe-state allowlists;
- unknown/stale/degraded/unsafe market state rejects;
- contradictory market/account/position/order status and companion boolean rejects;
- unknown/reconciliation-required/mismatch order or position state rejects;
- kill switch blocks new exposure;
- existing same-symbol exposure blocks position-add/averaging-down behavior;
- drawdown, consecutive-loss, trade-count, position-count, balance, leverage, notional, margin, cost, stop, and reward/risk gates remain active;
- a forged APPROVE with unsafe serialized market/account/position state cannot produce an ApprovedTradePlan.

The profile implementation does not weaken these controls.

### E5 changed-file scope

The implementation revision changes only:

- `src/risk/engine.py`
- `tests/risk/test_risk_engine.py`
- `tests/safety/test_e5_fail_closed.py`

The later successor revision changes only `status/E5_RISK_POSITION_HANDOFF.md`.

No `contracts/**`, provider adapter, exchange API, credential, workflow, lifecycle, or E4 production path is modified by this task.

### E5 deterministic test definitions

Static definitions cover:

- valid profiled MARKET intent -> profiled plan;
- missing/unknown profile rejection;
- unsupported order-type rejection;
- legacy style-only intent rejection for execution;
- reference price remains advisory/non-executable;
- exact BTC base-asset quantity metadata;
- no provider-native sizing fields in the plan;
- retained unknown-state and forged-approval fail-closed behavior.

Executable disposition remains `NOT_RUN`.

## 3. Combined E2 -> E5 boundary

### Field alignment

No translation ambiguity remains between the reviewed producer revisions.

E2 emits:

```text
TradeIntent.entry_profile_version = entry-v0.1
TradeIntent.entry_order_type      = MARKET
```

E5 consumes exactly those names and values without aliasing, lowercasing, provider translation, legacy-style inference, or reference-price promotion.

E5 then emits:

```text
ApprovedTradePlan.entry_instruction.profile_version = entry-v0.1
ApprovedTradePlan.entry_instruction.order_type      = MARKET
```

and the canonical quantity profile:

```text
ApprovedTradePlan.quantity_profile_version = base-asset-v0.1
ApprovedTradePlan.quantity_unit            = BASE_ASSET
ApprovedTradePlan.quantity_asset           = BTC
ApprovedTradePlan.quantity                 = approved BTC upper bound
```

This is coherent with `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0002, and ADR-0003.

### Authority boundary

The reviewed chain remains:

```text
E2 Signal
  -> E2 TradeIntent (candidate intent; no sizing/risk/provider authority)
  -> E5 RiskDecision (risk veto + sizing authority)
  -> E5 ApprovedTradePlan (profiled MARKET instruction + canonical BTC exposure bound)
  -> future E4 mechanical translation/provider sizing
```

There is no direct E2 -> E4 order path, no provider-native quantity in E5, and no profile field that implies PAPER/Demo/LIVE permission.

## 4. Branch/integration note

At review time both producer work branches are diverged from current `main` and are each behind current `main` by repository coordination/integration commits.

The static acceptance therefore binds to exact reviewed revisions, not to an assumption that current `main` already contains the producer implementation.

Accepted producer pins:

```text
E2 implementation: f99a8d00cd1fe40e1d73964d8b1cf37bc1886bd4
E5 implementation: e5f7088301a92deadfd9f6c416ae03b466c38a47
E5 handoff head:   3c8f9fa558cc90ad69fd5e58dcd4f6aa457e8de4
```

Before a later merge/integration candidate, branches must be synchronized through the normal repository procedure and material production/test changes after these pins require E7 re-review.

This synchronization note does not change the source-level producer-chain PASS.

## 5. E4 follow-up recommendation

Recommendation:

```text
YES — PM may issue the next bounded E4 task.
```

The task must pin or consume the E7-accepted E2/E5 producer revisions and remain limited to:

1. mechanical `entry-v0.1` translation:
   - `LONG -> BUY`
   - `SHORT -> SELL`
   - `MARKET -> OrderRequest.order_type=MARKET`
   - no executable price/TIF invention;
2. canonical quantity preservation:
   - shared `OrderRequest.quantity` remains the canonical BTC base-asset amount/profile;
3. deterministic OKX instrument metadata conversion:
   - validate current supported metadata;
   - convert canonical BTC exposure to provider contracts only inside E4/provider adapter;
   - round down to a valid lot or reject;
   - never round up above E5-approved exposure;
   - stale/missing/incompatible metadata fails closed;
4. preserve provider-native requested/filled contract quantities separately from canonical quantities for later audit/reconciliation.

Still forbidden in that recommendation unless a separate PM task explicitly authorizes it:

- OKX private API implementation;
- OKX Demo order submission;
- credentials;
- PAPER/SHADOW/LIVE enablement;
- withdrawal/funding-transfer/sub-account-capital-movement capability.

## 6. Scope / security / compute audit

Static review found no blocking:

- shared-contract collision;
- provider leakage into E2 TradeIntent;
- provider-native sizing leakage into E5 ApprovedTradePlan;
- direct execution authority bypass;
- unsafe default enabling unsupported entry types;
- real secret/credential addition;
- GitHub Actions/CI/hosted-runner/project-compute addition.

No E1-E6 production file is modified by this E7 review.

## 7. Executable and release disposition

```text
E2 executable tests             NOT_RUN
E5 executable tests             NOT_RUN
Combined integration execution  NOT_RUN
GitHub project compute          NOT_USED
Gate A RESEARCH_READY           BLOCKED / UNCHANGED
Gate B PAPER_READY              BLOCKED / UNCHANGED
Gate C SHADOW_READY             BLOCKED / UNCHANGED
Gate D LIVE_READY               BLOCKED / UNCHANGED
```

No static finding is treated as executable evidence.

## 8. Next owner

`PM`.

PM may issue a bounded E4 profile/OKX sizing task based on the accepted producer pins above. E7 does not start E4 implementation automatically and stops after this review.