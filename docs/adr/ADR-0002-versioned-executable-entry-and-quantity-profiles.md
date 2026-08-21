# ADR-0002 — Versioned Executable Entry and Base-Asset Quantity Profiles

- Status: `ACCEPTED`
- Date: `2026-08-21`
- Decision task: `E7-20260821-004`
- Authority: E7 under Product Owner / `contracts/README.md`
- Parent baseline: `contracts-v0.1`

## Context

The V1 baseline established:

```text
TradeIntent -> RiskDecision -> ApprovedTradePlan -> OrderRequest
```

but left two execution-critical meanings underspecified:

1. `TradeIntent.entry_style` and `ApprovedTradePlan.entry_instruction` did not define a canonical executable order type or conditional-field rules.
2. shared `quantity` fields did not state a provider-neutral derivatives unit, while the selected V1 exchange target, OKX, expresses `FUTURES/SWAP` order `sz` in contract units.

A previous E7 review correctly classified the E4/E5 entry translation gap as a shared semantic gap rather than ordinary integration glue. Before that follow-up contract task was accepted, the Product Owner changed the V1 broker target from Pionex to OKX. Task `E7-20260821-004` therefore supersedes the unaccepted prior task and resolves entry and quantity semantics together.

## Decision

Keep the parent contract set at:

```text
schema_version = contracts-v0.1
```

and introduce two compatible object profiles:

```text
entry-v0.1
base-asset-v0.1
```

The canonical profile definitions are in:

```text
contracts/EXECUTION_OBJECT_PROFILES_V0_1.md
```

### Entry profile

`entry-v0.1` supports only:

```text
MARKET
```

E2 may produce an executable `TradeIntent` only when it explicitly declares:

```text
entry_profile_version = entry-v0.1
entry_order_type      = MARKET
```

E5 copies approved executable intent into:

```text
entry_instruction.profile_version = entry-v0.1
entry_instruction.order_type      = MARKET
```

`entry_reference_price` / `reference_price` remain advisory context. They are not executable prices.

Legacy `entry_style` is not mechanically translated.

LIMIT, trigger, stop-entry, post-only, trailing, IOC/FOK profiles are not approved by this ADR.

### Quantity profile

`base-asset-v0.1` defines the E5-approved quantity as the maximum new-position exposure in the canonical instrument base asset.

For `BTC_USDT_PERP`:

```text
quantity_unit  = BASE_ASSET
quantity_asset = BTC
```

Provider-native contract counts are not substituted into shared canonical quantity fields.

## Why no set-wide major bump

A major contract-set version is not required because:

- the baseline did not promise a different executable `entry_instruction` meaning;
- the new profile fields are additive;
- legacy objects remain valid for historical/research/audit use;
- missing/unsupported profile data fails closed for the new execution capability;
- no frozen Slice 1 object changes meaning or schema version;
- no existing object is rewritten in place.

This is therefore compatible object-profile refinement under `contracts/README.md`.

If a future change alters existing quantity units, authority, or previously guaranteed profile behavior incompatibly, normal major-version rules apply.

## Producer / consumer impact

### E2 — producer

Follow-up scope:

- add profile-aware TradeIntent serialization;
- emit `entry_profile_version=entry-v0.1` and `entry_order_type=MARKET` only for supported executable intent;
- preserve `entry_reference_price` as advisory only;
- reject unsupported/unknown entry types;
- do not add broker/provider fields.

No StrategyDefinition/Signal/Slice-1 runtime semantic rewrite is authorized by this ADR.

### E5 — producer / risk authority

Follow-up scope:

- consume the E2 entry profile without inventing unsupported entry semantics;
- emit profiled `ApprovedTradePlan.entry_instruction`;
- emit `quantity_profile_version=base-asset-v0.1`, `quantity_unit=BASE_ASSET`, and canonical `quantity_asset`;
- keep quantity/leverage/margin/protection authority in E5;
- keep provider contract sizing out of E5.

### E4 — primary consumer

Follow-up scope:

- require supported entry + quantity profiles before provider-backed new exposure;
- translate `MARKET` mechanically into provider-neutral `OrderRequest.order_type=MARKET`;
- preserve canonical quantity unchanged in the shared `OrderRequest`;
- perform provider-native conversion/quantization only inside the provider adapter;
- reject unsupported profile values or invalid combinations.

### E6 — secondary consumer / audit

Follow-up scope:

- persist parent schema version plus profile identifiers;
- retain legacy objects without rewriting them;
- represent execution-profile eligibility separately from validation/lifecycle approval;
- later persist provider translation/audit facts without conflating provider contract units and canonical base quantity.

### E1 / E3

No shared-contract migration is required for frozen Slice 1 Candle/backtest evidence. E1 separately migrates provider acquisition to OKX under the Product Owner broker-target decision while preserving canonical Candle semantics. E3 requires no strategy/backtest semantic rewrite from this ADR.

## Behavioral impact

- execution eligibility becomes explicit and fail-closed;
- E4 no longer needs to guess how a legacy `style` maps to an order type;
- successful profile translation does not imply PAPER/Demo/LIVE authorization;
- provider conversion cannot change the E5-approved exposure bound.

## Persistence / replay impact

Legacy objects remain stored as originally produced. A stored legacy plan missing the profile is not retroactively execution-eligible.

Replay/research consumers that do not need execution semantics may continue using the baseline fields they already support.

## Migration

No in-place migration.

New producer revisions emit new profiled objects. Consumers validate the profile they support. Legacy plans can be displayed/audited but must fail closed at the new execution boundary.

## Rejected alternatives

### A. Infer executable semantics from `entry_style`

Rejected because it would silently turn a provisional field into shared execution authority.

### B. Make `reference_price` an executable price

Rejected because it was advisory and may represent strategy context rather than a limit/trigger instruction.

### C. Put OKX order-type names into TradeIntent/ApprovedTradePlan

Rejected because shared strategy/risk contracts must remain broker-neutral.

### D. Set-wide major version bump

Rejected as disproportionate. No unrelated object requires incompatible migration.

## Verification

Executable verification is `NOT_RUN` in this E7 repository session.

Future local integration commands will be owned by the implementation revisions and E7 integration checkout. Minimum scenarios are defined in:

- `tests/integration/EXECUTABLE_ENTRY_PROFILE_TEST_PLAN.md`
- `tests/safety/OKX_QUANTITY_BOUNDARY_TEST_PLAN.md`

No GitHub Actions/CI/hosted runner may be used.

## Release impact

No release gate advances.

```text
Gate A RESEARCH_READY  BLOCKED
Gate B PAPER_READY     BLOCKED
Gate C SHADOW_READY    BLOCKED
Gate D LIVE_READY      BLOCKED
```
