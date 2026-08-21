# ADR-0003 — OKX Derivative Sizing, Quantization, and Operational Boundary

- Status: `ACCEPTED`
- Date: `2026-08-21`
- Decision task: `E7-20260821-004`
- Product target authority: `docs/architecture/BROKER_TARGET_OKX_DECISION_20260821.md`
- Shared execution profile: `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`

## Context

The Product Owner changed the V1 broker target to OKX with this staged path:

```text
internal PaperBroker -> OKX Demo Trading -> dedicated R7 OKX sub-account
```

Real-money execution remains unauthorized.

OKX official API documentation states that for `FUTURES/SWAP/OPTION`, order `sz` is the number of contracts, while instrument metadata exposes contract/value and trading-step facts such as `ctVal`, `ctMult`, `ctValCcy`, `ctType`, `lotSz`, `minSz`, `tickSz`, and instrument `state`.

The shared risk layer must therefore not assume that an E5-approved canonical quantity is numerically identical to OKX `sz`.

Official provider references rechecked for this ADR:

- https://www.okx.com/docs-v5/en/
- https://www.okx.com/zh-hant/help/subaccounts-account-mode-and-api-connections-faq

Provider behavior must be rechecked again at implementation time.

## Decision

### 1. Canonical identity vs provider identity

Shared/canonical identity remains:

```text
BTC_USDT_PERP
```

The OKX adapter target is:

```text
BTC-USDT-SWAP
```

The mapping is adapter configuration. E2/E3/E5/E6 do not replace canonical symbols with OKX instrument IDs.

### 2. Canonical risk quantity

E5 approves the maximum new-position exposure in canonical base-asset units under:

```text
base-asset-v0.1
```

For `BTC_USDT_PERP`, that quantity is BTC.

E5 does not calculate OKX contract `sz` and does not become an OKX instrument-metadata consumer merely to place orders.

### 3. Provider-native sizing ownership

E4 / the OKX adapter owns:

- retrieving current OKX instrument metadata;
- validating provider instrument identity/type/state;
- converting canonical base-asset exposure into provider contracts;
- lot/minimum quantization;
- provider request formatting;
- preserving raw provider order/fill contract quantities;
- reconciliation of provider order/fill/exposure truth.

The provider-native `sz` is an E4 adapter fact. It is not copied into shared `ApprovedTradePlan.quantity` or shared canonical fill/position quantity fields.

### 4. Mandatory metadata inputs

Before new OKX swap exposure, the adapter must obtain and validate current instrument facts sufficient to prove the conversion, including at minimum:

- `instId`
- `instType`
- `ctVal`
- `ctMult`
- `ctValCcy`
- `ctType`
- `lotSz`
- `minSz`
- `tickSz`
- `state`
- adapter observation time / metadata reference

Missing, malformed, stale, mismatched, or unsupported metadata blocks new exposure.

### 5. V1 supported conversion class

For V1, support only a conversion that can be proven directly from current provider metadata without inventing a price-dependent unit transformation.

For a directly base-denominated supported linear swap where `ctValCcy` matches the canonical base asset:

```text
base_per_contract = ctVal * ctMult
raw_contracts     = approved_base_quantity / base_per_contract
```

The requested provider contracts are the largest allowed `lotSz` multiple not exceeding `raw_contracts`.

```text
provider_sz = floor_to_lot(raw_contracts, lotSz)
```

Then:

```text
realized_base_quantity = provider_sz * base_per_contract
```

Required invariants:

```text
provider_sz >= minSz
provider_sz is a valid lotSz multiple
provider_sz > 0
realized_base_quantity > 0
realized_base_quantity <= approved_base_quantity
```

If those conditions cannot be satisfied, reject.

### 6. Rounding policy

Mandatory invariant:

> Provider quantization may round down or reject; it must never round up into exposure greater than the E5-approved bound.

V1 policy:

- round provider contract size **down** to a valid `lotSz` multiple;
- if the result is below `minSz`, reject;
- do not round up to meet `minSz`;
- do not automatically place an additional order to consume residual approved quantity;
- residual quantity remains unexecuted and auditable.

### 7. Unsupported conversion

If current metadata implies a conversion that requires an unreviewed price-dependent formula, unsupported contract type/currency relationship, or ambiguous multiplier meaning, fail closed.

E4 must not infer a conversion from a blog/example/previous observation when current official metadata is insufficient.

### 8. Instrument state

New exposure requires a state compatible with the requested order type.

For the approved `entry-v0.1` MARKET profile:

- normal tradable state is required;
- suspended/rebase/non-tradable state blocks;
- a provider state that only accepts post-only orders is incompatible with MARKET and blocks.

### 9. Metadata freshness

E4 owns a versioned metadata freshness policy.

The shared contract intentionally does not hard-code a provider TTL because exchange behavior can change independently of strategy/risk semantics.

At minimum the adapter records:

- metadata observation time;
- provider/instrument identity;
- adapter metadata-policy version;
- the metadata snapshot/reference used for the conversion.

If the snapshot exceeds the configured allowed age or freshness cannot be established, new exposure blocks.

### 10. Price/tick boundary

`entry-v0.1` is MARKET-only.

Therefore:

- `tickSz` is validated/retained as provider instrument metadata;
- E4 does not use `tickSz` to turn `reference_price` into an executable price;
- no LIMIT price rounding rule is approved yet.

A future LIMIT profile requires separate versioned price/tick semantics.

## Reconciliation and audit

E4 must preserve provider-native truth and canonical normalized truth separately.

Minimum future audit facts:

- canonical `trade_plan_id`;
- canonical approved base quantity/profile;
- provider = OKX;
- provider instrument ID;
- provider requested `sz` contracts;
- actual filled contracts (`fillSz`/cumulative equivalent as applicable);
- provider order/fill IDs;
- instrument metadata reference and values used for translation;
- effective canonical filled base quantity;
- reconciliation status and observation timestamps.

For provider fills, E4 converts raw contract fill facts to canonical base-asset quantity using the relevant validated instrument semantics and emits shared Fill/Position quantities in canonical units. Raw contract counts are retained for audit; they are not conflated with canonical quantity.

Requested quantity and actual fill remain distinct in both provider-native and canonical views.

## Account-mode and isolated-operation boundary

The Product Owner's desired operational intent is isolated exposure.

OKX account mode is an **externally configured prerequisite**. Future runtime must verify that current account/instrument configuration supports the required operation and fail closed otherwise.

Rules:

- R7 does not automatically change the Product Owner's OKX account mode to make an order succeed;
- a configured `isolated` trade intent is provider-adapter configuration, not an E5 risk approval;
- if current account mode does not support the required isolated swap operation, block new exposure;
- account/configuration verification must use current official provider semantics at implementation time.

## Dedicated R7 sub-account security boundary

Future real execution, if separately authorized, uses a dedicated R7 sub-account.

This provides operational isolation but does not replace risk/release approval.

Future API policy:

- credentials outside Git;
- minimum required permissions;
- Read when required;
- Trade only at an authorized provider-execution stage;
- Withdraw forbidden;
- trusted-IP restriction where operationally feasible;
- no withdrawal, funding-transfer, or sub-account-capital-movement operation in the R7 Broker interface.

The Broker abstraction must remain trading/execution oriented and must not expand into asset-custody movement merely because OKX exposes such APIs.

## Demo-first provider stage

The first OKX private-provider target is Demo Trading, not real money.

OKX official API documentation currently describes Demo Trading as requiring a Demo API key and simulated-trading request context/header. That fact belongs in the OKX adapter, not the shared contracts.

Implementation must reverify current provider requirements before code is accepted.

Successful Demo translation/execution does not imply PAPER, SHADOW, LIVE, lifecycle, or release-gate approval.

## Provider-specific facts must not leak upward

Forbidden shared-domain coupling includes:

- E2 emitting `BTC-USDT-SWAP`;
- E5 approving OKX `sz` contracts instead of canonical exposure;
- E6 interpreting OKX account mode as strategy approval;
- StrategyDefinition depending on OKX order-type strings;
- shared `ApprovedTradePlan` carrying OKX credential or API endpoint data.

## Failure behavior

Any of the following blocks new exposure:

- missing/stale instrument metadata;
- provider instrument mismatch;
- unsupported `ctType` / `ctValCcy` conversion;
- malformed or non-positive sizing metadata;
- non-tradable instrument state;
- below-minimum representable size;
- any quantization result exceeding approved canonical quantity;
- unknown/incompatible account mode;
- reconciliation uncertainty affecting order/position truth.

## Follow-up ownership

### E1

Build OKX public market-data adapter for the canonical `BTC_USDT_PERP` identity while preserving existing Candle semantics. No private account/execution code.

### E2

Remain broker-neutral; implement the approved `entry-v0.1` TradeIntent profile only.

### E5

Emit canonical `base-asset-v0.1` risk quantity and approved entry profile. Do not fetch OKX metadata or compute contracts.

### E4

Implement provider-neutral profile translation plus OKX Demo adapter preflight/conversion only after a new TASK authorizes it. Reverify official OKX docs first. Preserve round-down/reject invariant and provider/canonical audit separation.

### E6

Persist profile identifiers and later provider translation/audit facts; never infer approval from sub-account, credentials, Demo success, or provider state.

## Verification

Executable verification for this ADR is `NOT_RUN`.

Static future scenarios are defined under:

- `tests/integration/EXECUTABLE_ENTRY_PROFILE_TEST_PLAN.md`
- `tests/safety/OKX_QUANTITY_BOUNDARY_TEST_PLAN.md`

No GitHub Actions/CI/runner is permitted.

## Release impact

No Gate A/B/C/D advancement.
