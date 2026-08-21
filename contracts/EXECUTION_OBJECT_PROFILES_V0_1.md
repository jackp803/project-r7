# Canonical Execution Object Profiles — V0.1

> Parent contract set: `contracts-v0.1`  
> Profile status: `BASELINE`  
> Technical authority: E7 Integration / Architecture / System QA / Release Engineer  
> Decision task: `E7-20260821-004`  
> Effective for new Slice 3 execution construction after producer/consumer follow-up revisions are accepted

## 1. Purpose

`contracts-v0.1` deliberately established the authority chain and required an `ApprovedTradePlan.entry_instruction`, but it did not define the executable inner mapping from strategy intent to E4 order fields. It also used the field name `quantity` without defining a provider-neutral derivatives unit suitable for an exchange such as OKX, where perpetual-swap order `sz` is expressed in instrument contracts.

This file is the canonical compatible object-profile refinement for those two previously underspecified areas. It does **not** replace `contracts-v0.1`, and it does not change the schema version of unrelated objects.

Two independent profile identifiers are introduced:

```text
entry-v0.1
base-asset-v0.1
```

The parent serialized object still carries:

```text
schema_version = contracts-v0.1
```

## 2. Compatibility and versioning decision

This is an **additive-compatible object-profile refinement**, not a set-wide major contract bump.

Reasons:

1. `contracts-v0.1` never defined executable inner semantics for `entry_instruction`; therefore no previously guaranteed executable mapping is being reinterpreted.
2. New profile fields are additive. Existing `contracts-v0.1` objects remain valid historical/research/audit objects.
3. A legacy object that does not declare the relevant profile is **not execution-eligible under the new provider path**. Consumers fail closed rather than guessing missing semantics.
4. Frozen Slice 1 `Candle`, `StrategyDefinition`, `Signal`, and `BacktestResult` semantics are unchanged.
5. No existing financial/time/authority meaning is removed or weakened.

No stored legacy object is rewritten in place. Migration is by producing a new compatible object instance from an updated producer when execution is desired.

## 3. `entry-v0.1` — executable entry profile

### 3.1 Scope

The initial profile is intentionally small:

```text
Supported executable entry order type: MARKET only
```

Not supported by this profile:

- `LIMIT`
- stop/trigger entry
- post-only
- IOC/FOK as a separate entry type or TIF policy
- trailing entry
- exchange-specific order types
- provider-specific price-band behavior

A future profile version must explicitly define any additional order type and its conditional fields before E4 may translate it.

### 3.2 `TradeIntent` producer fields

**Producer:** E2  
**Consumer:** E5

The following fields are additive to the existing `TradeIntent` baseline:

- `entry_profile_version` — when present for executable intent, exactly `entry-v0.1`
- `entry_order_type` — when `entry_profile_version=entry-v0.1`, exactly `MARKET`

Existing `entry_reference_price` remains optional **advisory/audit context only**.

Existing legacy `entry_style` remains a permitted legacy/advisory field under the parent baseline, but it has no executable mapping in `entry-v0.1`. E4 and E5 must not infer `entry_order_type` from `entry_style`.

Rules:

- `TradeIntent` still contains no approved quantity, leverage, broker credentials, provider endpoint, provider instrument ID, or execution approval.
- `entry_profile_version` without a valid `entry_order_type` fails closed for executable promotion.
- unknown `entry_profile_version` or unknown `entry_order_type` fails closed.
- `entry_reference_price` must never become an executable limit/stop price merely because it exists.

### 3.3 `ApprovedTradePlan.entry_instruction`

**Producer:** E5  
**Primary consumer:** E4  
**Secondary consumer/audit:** E6

For `entry-v0.1`, `entry_instruction` is:

```text
entry_instruction:
  profile_version: entry-v0.1
  order_type: MARKET
  reference_price: <optional advisory decimal string>
```

Required executable fields:

- `profile_version = entry-v0.1`
- `order_type = MARKET`

Optional advisory field:

- `reference_price` — positive finite decimal string if present; advisory/audit only

Forbidden executable combinations in this profile:

- `limit_price`
- `stop_price`
- `trigger_price`
- `time_in_force`
- provider-specific order-type names
- provider-specific instrument IDs

A `MARKET` plan carrying any of those forbidden executable fields fails closed.

### 3.4 E4 mechanical translation

For a valid `entry-v0.1` plan, E4 shared execution translation is mechanical:

```text
ApprovedTradePlan.direction LONG  -> OrderRequest.side BUY
ApprovedTradePlan.direction SHORT -> OrderRequest.side SELL
entry_instruction.order_type MARKET -> OrderRequest.order_type MARKET
ApprovedTradePlan.quantity -> OrderRequest.quantity unchanged in canonical units
```

E4 may reject an incompatible/expired plan. E4 may not invent or modify:

- direction;
- quantity;
- leverage;
- margin mode;
- risk approval;
- executable price;
- time in force;
- protection loosening.

Provider adapters may map the shared enum `MARKET` to a provider spelling such as `market`, but that provider spelling is not a shared-contract value.

## 4. `base-asset-v0.1` — canonical quantity/exposure profile

### 4.1 Canonical meaning

The E5-approved `ApprovedTradePlan.quantity` is the **maximum approved new-position exposure quantity in the canonical instrument base asset**.

For:

```text
symbol = BTC_USDT_PERP
```

the canonical quantity asset is:

```text
BTC
```

The profile fields are:

- `quantity_profile_version = base-asset-v0.1`
- `quantity_unit = BASE_ASSET`
- `quantity_asset = <canonical base asset, e.g. BTC>`

`quantity` remains a positive finite base-10 decimal string.

The value is an **upper exposure bound**, not a provider order-size field. Provider conversion may realize less exposure because of lot/minimum constraints; it may never realize more.

### 4.2 Profile propagation

For execution objects produced from a `base-asset-v0.1` plan, the same canonical quantity meaning applies to shared quantity-like fields:

- `ApprovedTradePlan.quantity`
- `OrderRequest.quantity`
- `OrderResult.requested_quantity`
- `OrderResult.filled_quantity`
- `Fill.quantity`
- `Position.actual_quantity`
- `TradeResult.entry_quantity`

When these profiled objects are serialized independently, they should carry:

- `quantity_profile_version`
- `quantity_unit`
- `quantity_asset`

Provider-native contract counts or other provider units must **not** be placed into those shared canonical quantity fields.

### 4.3 Provider conversion boundary

Provider conversion is owned by E4/provider adapters.

For OKX `BTC-USDT-SWAP`, E4 must retrieve and validate current instrument metadata before converting canonical BTC exposure to OKX contract `sz`. Provider-native `sz` remains an adapter/request fact and is not substituted for shared `OrderRequest.quantity`.

Mandatory invariant:

> Provider quantization may round down or reject; it must never round up into exposure greater than the E5-approved canonical quantity.

If a safe monotonic conversion from provider contracts to the canonical base asset cannot be proven from current instrument metadata, new exposure is rejected.

## 5. OKX V1 conversion profile

This section defines the safety semantics for the current V1 provider target without putting OKX names into `TradeIntent` or `ApprovedTradePlan`.

Canonical identity:

```text
BTC_USDT_PERP
```

Provider adapter identity:

```text
OKX BTC-USDT-SWAP
```

For the V1 direct conversion path, E4 must validate at minimum:

- provider instrument ID is the configured mapping for `BTC_USDT_PERP`;
- instrument type is `SWAP`;
- `ctType` is the adapter-supported contract type;
- `ctVal`, `ctMult`, `lotSz`, `minSz`, and `tickSz` are present as positive finite decimals where applicable;
- `ctValCcy` permits an unambiguous conversion to the canonical base asset for the supported path;
- instrument `state` permits the requested order type;
- metadata is current under an E4-owned, versioned freshness policy.

For a directly base-denominated linear contract where `ctValCcy` equals the canonical base asset:

```text
base_per_contract = ctVal * ctMult
raw_contracts     = approved_base_quantity / base_per_contract
provider_sz       = floor raw_contracts to an allowed lotSz multiple
realized_base_qty = provider_sz * base_per_contract
```

Acceptance conditions:

```text
provider_sz >= minSz
provider_sz is a valid lotSz multiple
0 < realized_base_qty <= approved_base_quantity
```

If the largest representable size is below `minSz`, reject. Residual approved quantity left by round-down remains unexecuted; E4 must not create a compensating order that exceeds the original bound.

If the provider contract requires a price-dependent or otherwise unsupported conversion to canonical base quantity, V1 fails closed until that conversion is separately reviewed and versioned.

## 6. Price/tick semantics

`entry-v0.1` is MARKET-only, so `tickSz` is instrument-health metadata but is not used to manufacture an executable entry price.

`reference_price` remains advisory and must not be tick-quantized into an executable order price.

A future LIMIT profile must explicitly define:

- executable `limit_price`;
- permitted `time_in_force` enum;
- price tick quantization;
- side-aware rounding rules;
- price-band/provider constraints;
- fail-closed behavior.

No such LIMIT semantics are approved by this profile.

## 7. Instrument metadata freshness and incompatibility

E4/provider adapters own retrieval, caching, validation, and freshness policy for provider instrument metadata.

Required behavior:

- missing metadata -> block new exposure;
- stale metadata -> block new exposure;
- unknown or unsupported contract type/unit -> block new exposure;
- non-tradable instrument state -> block new exposure;
- metadata/provider identity mismatch -> block new exposure;
- malformed decimal metadata -> block new exposure.

The shared contract does not hard-code a freshness duration. E4 must use an explicit versioned adapter policy and record the metadata observation time/reference used for translation.

## 8. Provider audit / reconciliation requirements

E4 must preserve both canonical and provider facts without conflation.

At minimum, later E4/E6 audit persistence must be able to trace:

- `trade_plan_id`;
- canonical symbol;
- canonical approved quantity + quantity profile/unit/asset;
- provider name;
- provider instrument ID;
- provider requested contract quantity (`sz` for OKX);
- provider actual filled contract quantity;
- provider fill/order IDs;
- instrument-metadata reference/snapshot identity and observation time;
- `ctVal`, `ctMult`, `ctValCcy`, `ctType`, `lotSz`, `minSz`, `tickSz`, and state used for translation;
- effective canonical filled quantity derived from provider fill facts;
- reconciliation status.

Provider fill quantities are broker truth. E4 normalizes them to canonical base-asset quantity for shared `Fill`/`Position` semantics while retaining raw provider facts for audit/reconciliation.

## 9. Operational/account prerequisites

The profile grants no operational permission.

Before future OKX Demo or real new exposure, E4 must fail closed unless externally configured prerequisites are verified, including:

- the configured provider account/sub-account matches the intended R7 account boundary;
- account mode supports the required derivative operation;
- isolated intent is supported by the current account/instrument configuration;
- required read/trade capability exists for the authorized stage;
- the instrument is currently tradable for the requested order type.

Runtime code must not silently change the Product Owner's account mode merely to make an order succeed.

Dedicated sub-account isolation is a security boundary only. It is never evidence of E5 risk approval, strategy promotion, PAPER/Demo/LIVE permission, or release-gate PASS.

## 10. Security prohibitions

- credentials remain outside Git;
- Withdraw permission is forbidden for R7 keys;
- R7 Broker interfaces must not expose withdrawal, funding transfer, or sub-account capital-movement capability;
- provider credentials never appear in shared `TradeIntent`, `ApprovedTradePlan`, or audit fixtures;
- Demo success does not authorize real-money execution.

## 11. Legacy compatibility / migration

Legacy `contracts-v0.1` objects without these profile fields:

- remain valid historical/research/audit objects;
- must not be mutated in place to pretend they were produced under these profiles;
- are not eligible for the new provider-backed executable entry path;
- may be persisted by E6 with an explicit legacy/non-executable profile status.

E2/E5 follow-up producers create new profiled objects. E4 accepts only declared profiles it explicitly supports. E6 preserves both the parent schema version and profile identifiers.

No migration is required for frozen Slice 1 E1/E2/E3 evidence.

## 12. Future compatible evolution

A future profile may add LIMIT or another executable entry mode only through E7 contract review.

If the future profile can remain additive and old profiled objects keep their meaning, use a new object-profile version without forcing an unrelated set-wide major bump. If field meaning, units, or authority are changed incompatibly, normal major-version rules apply.
