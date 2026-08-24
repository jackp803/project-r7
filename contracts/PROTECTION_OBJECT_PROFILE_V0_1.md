# Canonical Protection Object Profile — V0.1

> Parent contract set: `contracts-v0.1`  
> Profile identifier: `protection-v0.1`  
> Profile status: `BASELINE`  
> Technical authority: E7 Integration / Architecture / System QA / Release Engineer  
> Decision task: `E7-20260824-028`

## 1. Purpose

`contracts-v0.1` already establishes the correct authority chain:

```text
broker/execution truth -> E5 PositionAction -> E4 execution -> broker truth -> E5 lifecycle
```

and already requires protective quantity to follow actual filled/open quantity. The parent baseline did not, however, define an executable provider-neutral payload for `PositionAction.PROTECT`, nor did it define how an `OrderRequest` authorized by a PositionAction carries that authority while retaining parent `trade_plan_id` lineage.

This profile resolves only that underspecified boundary. It does not authorize PAPER, SHADOW, LIVE, provider/private API activity, or capital exposure.

## 2. Compatibility and versioning decision

This is an **additive-compatible object-profile refinement** under the existing parent:

```text
schema_version = contracts-v0.1
```

A set-wide schema-version change is not required because:

1. the parent contract already permits E5-authorized PositionActions to reach E4 but does not define the executable payload;
2. the new profile fields are additive and apply only when `protection_profile_version=protection-v0.1` is declared;
3. existing entry-path objects keep their existing meaning;
4. legacy PositionAction/OrderRequest/Fill objects remain valid historical/research/audit objects;
5. legacy objects without this profile are **not executable-protection eligible** and must fail closed rather than being guessed or rewritten in place;
6. no existing quantity, authority, time, or lifecycle meaning is weakened.

The parent baseline and `entry-v0.1` / `base-asset-v0.1` profiles remain authoritative. This profile normatively reuses `base-asset-v0.1` canonical quantity semantics.

## 3. Supported action scope

`protection-v0.1` supports exactly:

```text
PositionAction.action = PROTECT
```

The existing baseline enum value `MODIFY_PROTECTION` remains valid as a shared lifecycle/action vocabulary value, but it is **not executable under `protection-v0.1`**.

A future profile may make `MODIFY_PROTECTION` executable only after E7 defines side-aware monotonic protection rules proving that ordinary modification cannot widen loss risk. Until then E4 must fail closed on `MODIFY_PROTECTION` for this profile. A new E5 risk decision/profile is required for any change that would otherwise loosen an approved protection bound.

## 4. Source of actual exposure truth

E4 remains authoritative for actual broker order/fill/exposure truth. E5 may issue a profiled `PROTECT` action only from a known normalized `Position` observation satisfying all of the following:

- `reconciliation_status = CONSISTENT`;
- `actual_quantity` is known, finite, and strictly positive;
- `actual_quantity` uses the same supported canonical quantity profile/unit/asset as the parent ApprovedTradePlan;
- the observation is bound by exact `position_id` and `broker_state_observed_at`;
- the observed symbol and side are consistent with the parent ApprovedTradePlan;
- for initial protection, lifecycle state is `OPEN_UNPROTECTED`;
- actual canonical quantity is not greater than the parent ApprovedTradePlan maximum approved quantity.

Unknown, zero, negative, non-finite, mismatched, stale/unverifiable, `UNKNOWN`, `MISMATCH`, or `RECONCILIATION_REQUIRED` exposure cannot produce an ordinary `protection-v0.1` action.

If actual exposure exceeds the E5-approved maximum, E5 must not silently create ordinary protection authority by expanding the parent plan. The state is an exceptional safety/reconciliation condition and must fail closed into the separately authorized emergency/reconciliation path. This profile does not redefine `EMERGENCY_EXIT` semantics.

## 5. `PositionAction` profile

### 5.1 Parent fields retained

The parent `PositionAction` required fields remain required:

- `schema_version`
- `position_action_id`
- `position_id`
- `action`
- `reason_codes`
- `risk_policy_version`
- `created_at`

### 5.2 Additional required fields for `protection-v0.1`

A serialized executable `PROTECT` action additionally requires:

- `protection_profile_version` — exactly `protection-v0.1`
- `trade_plan_id` — exact parent ApprovedTradePlan
- `risk_decision_id` — exact parent RiskDecision lineage
- `symbol` — canonical symbol
- `position_side` — `LONG | SHORT`
- `position_observed_at` — exact source `Position.broker_state_observed_at`, RFC 3339 UTC
- `position_reconciliation_status` — exactly `CONSISTENT`
- `quantity` — exact canonical quantity to protect
- `quantity_profile_version` — exactly the parent supported quantity profile; V1 is `base-asset-v0.1`
- `quantity_unit` — V1 `BASE_ASSET`
- `quantity_asset` — canonical base asset; for `BTC_USDT_PERP`, `BTC`
- `protection_instruction`
- `expires_at` — action-specific expiry, RFC 3339 UTC and later than `created_at`

`quantity` is the exact currently known open exposure being protected. For an initial partial fill it is the partial actual open quantity, not the entry OrderRequest requested quantity and not automatically the full ApprovedTradePlan quantity.

### 5.3 Protection instruction binding

For `protection-v0.1`, `protection_instruction` is:

```text
protection_instruction:
  stop_level: <required positive finite decimal string>
  target_level: <optional positive finite decimal string>
  max_hold_seconds: <required positive integer>
```

For `PROTECT`, these values must equal the corresponding already-approved values in the exact parent `ApprovedTradePlan.protection_instruction`. E5 may not use this action to loosen or invent stop, target, or max-hold bounds.

`target_level` and `max_hold_seconds` remain binding E5 lifecycle/risk facts. `protection-v0.1` authorizes only the protective-stop executable translation defined below; it does not silently invent a target order or timer implementation.

### 5.4 Lineage invariants

The action is valid only when:

```text
PositionAction.trade_plan_id       == ApprovedTradePlan.trade_plan_id
PositionAction.risk_decision_id    == ApprovedTradePlan.risk_decision_id
PositionAction.risk_policy_version == ApprovedTradePlan.risk_policy_version
PositionAction.symbol              == ApprovedTradePlan.symbol
```

and the source Position observation matches the action's:

```text
position_id
position_observed_at
position_side
quantity
position_reconciliation_status
quantity profile/unit/asset
```

E5 creates the action from those authoritative inputs. E4 validates the declared lineage and current execution truth; E4 does not choose the quantity or protection bounds.

## 6. Action identity and freshness

`position_action_id` must be deterministic/stable for one logical authorization material and must change when any authority-bearing material changes, including at minimum:

- parent `trade_plan_id` / `risk_decision_id`;
- `position_id` / `position_observed_at`;
- action quantity/profile/unit/asset;
- protection instruction;
- risk policy version;
- action type.

Repeated delivery of the same action is idempotent. A materially changed action must have a different identity.

`expires_at` is specific to the PositionAction. The parent ApprovedTradePlan entry TTL must not be reinterpreted as the lifetime of protection authority after a legitimate fill has opened exposure. E4 rejects an expired PositionAction.

## 7. E4 mechanical consumption contract

For execution, E4 must validate all three authoritative inputs, directly or through an authoritative equivalent lookup:

```text
PositionAction (protection-v0.1)
+ exact parent ApprovedTradePlan
+ exact current E4-normalized Position observation
```

E4 must fail closed unless the lineage, quantity profile, position observation, current reconciliation status, symbol/side, action freshness, and protection bounds are mutually consistent.

E4 may re-observe broker truth and reject stale/mismatched action evidence. That verification does not grant E4 risk authority: it may only confirm or reject E5's declared action; it may not substitute a different quantity, stop, target, or policy.

## 8. `OrderRequest` profile for protective stop

The parent `OrderRequest.trade_plan_id` remains required for all executable requests and now has an explicit meaning for position-action requests: it is the immutable parent-plan lineage, not the immediate authorization object.

For a `protection-v0.1` request, the following additive fields are required:

- `authorization_type` — exactly `POSITION_ACTION`
- `position_action_id` — exact E5 authorization identity
- `position_id`
- `risk_decision_id`
- `order_role` — exactly `PROTECTION_STOP`

Existing canonical quantity profile fields remain required under `base-asset-v0.1`.

The deterministic provider-neutral mapping is:

```text
PositionAction.position_side LONG  -> OrderRequest.side SELL
PositionAction.position_side SHORT -> OrderRequest.side BUY
PositionAction.quantity            -> OrderRequest.quantity unchanged in canonical units
PositionAction.protection_instruction.stop_level -> OrderRequest.stop_price
OrderRequest.order_type            = STOP_MARKET
OrderRequest.reduce_only           = true
OrderRequest.limit_price           = null
OrderRequest.time_in_force         = null
```

The request retains:

```text
trade_plan_id     = PositionAction.trade_plan_id
position_action_id = PositionAction.position_action_id
risk_decision_id  = PositionAction.risk_decision_id
position_id       = PositionAction.position_id
```

The `client_order_id` must be stable for the tuple `(position_action_id, PROTECTION_STOP)` or an equivalently collision-resistant deterministic identity. Replaying the same logical action must not create a second logical protective order.

E4/provider adapters may translate `STOP_MARKET` into provider-specific trigger/order fields only inside the adapter. Provider spellings, contract counts, trigger parameters, and OKX `sz` are adapter facts and must not leak upward into PositionAction canonical quantity or authority fields.

Provider quantization may safely round only in a way that preserves the protective intent and never creates exposure. For the shared canonical request, quantity remains the exact E5-authorized actual open quantity; any provider representation must remain traceable back to it.

## 9. Target and max-hold behavior in V0.1

`target_level` and `max_hold_seconds` are preserved in the E5 action because they are part of the parent approved bounds.

This profile does **not** authorize E4 to manufacture:

- a take-profit order from `target_level`;
- an exit timer from `max_hold_seconds`;
- provider-specific linked/OCO semantics.

Those behaviors require an explicit later PositionAction/profile or E5 lifecycle implementation. Their absence must not be interpreted as permission to weaken the required stop protection.

## 10. OrderResult / Fill / reconciliation lineage

Existing `OrderResult` semantics remain authoritative. A protective `OrderResult` is traceable through its `order_request_id` to the exact profiled OrderRequest and therefore to both `position_action_id` and `trade_plan_id` lineage.

For independently serialized `Fill` objects produced from a protection-authorized request, `protection-v0.1` requires additive lineage:

- `position_action_id`
- `position_id`
- `order_role = PROTECTION_STOP`

The existing `trade_plan_id` lineage is retained. Shared Fill quantity remains canonical actual fill quantity under `base-asset-v0.1`; provider-native contract counts remain separate adapter/audit facts.

Unknown or ambiguous protective order state must enter the existing reconciliation-required behavior. Blind retry is forbidden.

## 11. Lifecycle meaning

A created PositionAction, prepared OrderRequest, or local submit call is **not** `PROTECTION_VERIFIED`.

The position remains:

```text
OPEN_UNPROTECTED
```

until E4 broker truth establishes that the exact protective request is active/effective for the exact authorized quantity and stop bound with no reconciliation ambiguity, and E5 consumes that verified evidence.

Only then may E5 apply:

```text
OPEN_UNPROTECTED + PROTECTION_VERIFIED -> OPEN_PROTECTED
```

If protection is rejected, expired before becoming effective, cannot be established, or is otherwise definitively failed:

```text
OPEN_UNPROTECTED + PROTECTION_FAILED -> EMERGENCY
```

If protection was previously verified and later disappears/fails:

```text
OPEN_PROTECTED/PROFIT_PROTECTED + PROTECTION_LOST -> EMERGENCY
```

If broker/order/position truth is unknown or unreconciled, `PROTECTION_VERIFIED` is forbidden and the existing reconciliation-required semantics apply.

There is no request-created shortcut from `OPEN_UNPROTECTED` to `OPEN_PROTECTED`.

## 12. Legacy compatibility

Legacy `contracts-v0.1` PositionAction/OrderRequest/Fill objects without `protection_profile_version=protection-v0.1`:

- remain valid for their original historical/research/audit meaning;
- are not rewritten or upgraded in place;
- are not executable under the new actual-fill protection path;
- must fail closed when a consumer requires executable protection semantics.

Existing entry-path `entry-v0.1` objects are unchanged.

## 13. Downstream implementation obligations

### E5 producer

A bounded E5 follow-up may implement:

```text
known CONSISTENT Position observation
+ exact ApprovedTradePlan
-> protection-v0.1 PositionAction.PROTECT
```

It must not fetch provider metadata, produce provider contract counts, or invent E4 order fields.

### E4 consumer

After the E5 producer shape is materialized, a bounded E4 follow-up may implement:

```text
protection-v0.1 PositionAction
+ exact parent ApprovedTradePlan
+ current E4 Position truth
-> deterministic protection-v0.1 OrderRequest
```

E4 may reject incompatible/stale inputs but may not choose risk quantity, loosen protection bounds, or infer missing lineage/unit semantics.

### E7 integration

After both producer and consumer exist, E7 must define/verify local-only integration and safety coverage for partial fills, exact protection quantity, no risk-bound loosening, protection verification vs submission, failure -> emergency, reconciliation, and idempotency.

## 14. Release and execution impact

This contract decision resolves the **shared semantic blocker only**.

```text
Required protection follows actual filled quantity = BLOCKED pending E5/E4 implementation and local evidence
Gate B = BLOCKED / NOT YET PASS
PAPER / SHADOW / LIVE = UNAUTHORIZED
provider/private API = NOT AUTHORIZED
```

No executable verification is claimed by this profile.
