# E7 Decision Record — Executable Entry + OKX Provider Boundary

- Task: `E7-20260821-004`
- Date: `2026-08-21`
- Target branch: `agent/e7-okx-contract-boundary-20260821`
- Contract parent baseline: `contracts-v0.1`
- Product broker target: OKX
- Static decision state: `PASS`
- Executable verification: `NOT_RUN`

## 1. Supersession / prior-task recovery

`E7-20260821-004` explicitly supersedes `E7-20260821-003` because the Product Owner changed the V1 broker target before repository evidence for the prior task was accepted.

Repository inspection found no commit matching `E7-20260821-003` and the prior `agent/e7-entry-contract-vnext-20260821` branch is not ahead of current `main`. Therefore this record does **not** claim `-003` complete.

Prior E7 entry-gap review/proposal material was treated only as design input.

## 2. Contract-change procedure record

This section records completion of the `contracts/README.md` sequence.

### 2.1 Request / problem

Two cross-module semantics were insufficient for continued implementation:

1. existing `TradeIntent.entry_style` / `ApprovedTradePlan.entry_instruction` did not define a safe executable mapping to E4 `OrderRequest.order_type`;
2. existing shared `quantity` naming did not distinguish provider-neutral approved exposure from OKX swap contract units (`sz`).

Both gaps could otherwise force E4/E5 to invent private semantics.

### 2.2 Producer inventory

- E2 produces `TradeIntent`.
- E5 produces `RiskDecision` and `ApprovedTradePlan`.
- E4 produces shared `OrderRequest`, `OrderResult`, `Fill`, and provider translation facts.
- Integrated E4/E5 path later produces Position/TradeResult quantity facts.

### 2.3 Consumer inventory

- E5 consumes TradeIntent entry semantics.
- E4 consumes ApprovedTradePlan and owns provider translation.
- E6 is secondary consumer/audit persistence for plan/order/fill/provider translation facts.
- E7 consumes all above for integration/release evidence.
- E3 may later consume equivalent fill semantics for parity but does not own provider sizing.

### 2.4 Behavioral impact

- executable entry type is now explicit under an object profile;
- initial approved entry type is MARKET only;
- advisory reference price cannot become executable price;
- canonical quantity is explicitly a base-asset exposure bound;
- provider contract conversion is isolated to E4/provider adapters;
- successful translation has no release/lifecycle authority.

### 2.5 Persistence impact

E6 must preserve:

- parent `schema_version`;
- entry profile identifier;
- quantity profile/unit/asset;
- legacy/non-profiled state;
- later provider-native translation/audit facts separately from canonical quantities.

No legacy record is rewritten in place.

### 2.6 Replay / research impact

Frozen Slice 1 objects remain compatible:

- Candle: unchanged;
- StrategyDefinition: unchanged;
- Signal: unchanged;
- BacktestResult: unchanged.

E3 historical replay is not required to model OKX contract-unit conversion merely to preserve Strategy Runtime semantics.

Provider-derived datasets may later identify OKX as source under existing reproducibility conventions.

### 2.7 Migration impact

No set-wide migration.

New E2/E5/E4 revisions produce/consume profiled Slice 3 objects. Legacy `contracts-v0.1` plans remain valid audit objects but are not provider-execution eligible when profile semantics are absent.

### 2.8 Release impact

No gate advances. The new contracts remove a design ambiguity only.

```text
Gate A RESEARCH_READY  BLOCKED
Gate B PAPER_READY     BLOCKED
Gate C SHADOW_READY    BLOCKED
Gate D LIVE_READY      BLOCKED
```

### 2.9 Compatibility classification

Disposition:

```text
ADDITIVE_COMPATIBLE_OBJECT_PROFILE
```

Parent schema remains:

```text
contracts-v0.1
```

New profile identifiers:

```text
entry-v0.1
base-asset-v0.1
```

A set-wide major bump was rejected because no unrelated object needs incompatible migration and the old entry substructure never had an accepted executable meaning.

### 2.10 ADR

Material decisions are captured in:

- `docs/adr/ADR-0002-versioned-executable-entry-and-quantity-profiles.md`
- `docs/adr/ADR-0003-okx-derivative-sizing-and-operational-boundary.md`

### 2.11 Canonical contract revision

Canonical compatible profile added:

- `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`

Registry/versioning rules updated:

- `contracts/README.md`

Historical `contracts/SHARED_CONTRACTS_V1.md` is intentionally unchanged so its original baseline meaning remains inspectable.

### 2.12 Tests

Local-only definitions added:

- `tests/integration/EXECUTABLE_ENTRY_PROFILE_TEST_PLAN.md`
- `tests/safety/OKX_QUANTITY_BOUNDARY_TEST_PLAN.md`

### 2.13 Local verification

Result:

```text
NOT_RUN
```

Reason: no Product-Owner-approved local project execution environment was used. GitHub project compute is forbidden.

## 3. Entry-instruction decision

### TradeIntent

New executable intent profile:

```text
entry_profile_version = entry-v0.1
entry_order_type      = MARKET
```

Legacy `entry_style` remains non-executable/advisory.

`entry_reference_price` remains advisory.

### ApprovedTradePlan

Executable entry instruction:

```text
entry_instruction.profile_version = entry-v0.1
entry_instruction.order_type      = MARKET
```

Optional `reference_price` is advisory only.

MARKET carrying executable limit/stop/trigger/TIF fields is invalid.

### E4

Shared translation is mechanical only:

```text
LONG  -> BUY
SHORT -> SELL
MARKET -> MARKET
canonical quantity -> canonical OrderRequest.quantity unchanged
```

E4 does not invent execution semantics.

## 4. Quantity / exposure decision

Canonical plan quantity profile:

```text
quantity_profile_version = base-asset-v0.1
quantity_unit            = BASE_ASSET
quantity_asset           = BTC  # for BTC_USDT_PERP
```

`ApprovedTradePlan.quantity` is the E5-approved maximum new-position exposure in base-asset units.

OKX `sz` contracts are provider-adapter data and never replace canonical shared quantity.

## 5. Official OKX semantics rechecked

Official OKX API material reviewed for this task confirms current provider semantics relevant to the boundary:

- FUTURES/SWAP/OPTION order `sz` uses number-of-contract units;
- Get Instruments exposes `ctVal`, `ctMult`, `ctValCcy`, `ctType`, `lotSz`, `minSz`, `tickSz`, and instrument state semantics;
- derivative `lotSz` / `minSz` are in contract units;
- account mode is configured before trading and must be compatible with the intended operation;
- Demo Trading uses Demo API context/key and simulated-trading request handling;
- API permissions include Read / Trade / Withdraw, with Withdraw explicitly forbidden by R7 product policy.

Official references:

- https://www.okx.com/docs-v5/en/
- https://www.okx.com/zh-hant/help/subaccounts-account-mode-and-api-connections-faq

These provider details must be reverified at E4 implementation time.

## 6. OKX sizing / quantization ownership

### E5 owns

- approved canonical exposure;
- quantity/leverage/margin/risk bounds;
- risk approval/rejection.

### E4 / OKX adapter owns

- current instrument metadata retrieval/validation;
- canonical symbol -> `BTC-USDT-SWAP` mapping;
- provider contract conversion;
- `lotSz` quantization;
- `minSz` check;
- tradability/state check;
- provider request/fill truth;
- reconciliation;
- provider/native audit facts.

### V1 quantization rule

For a supported direct base-denominated contract conversion:

```text
base_per_contract = ctVal * ctMult
raw_contracts     = approved_base_quantity / base_per_contract
provider_sz       = floor_to_lot(raw_contracts, lotSz)
effective_base    = provider_sz * base_per_contract
```

Must satisfy:

```text
provider_sz >= minSz
0 < effective_base <= approved_base_quantity
```

If not, reject.

Provider quantization can round down or reject. It can never round up beyond the E5-approved exposure.

## 7. Metadata fail-closed boundary

New exposure is blocked if instrument metadata is:

- missing;
- stale under the versioned E4 adapter freshness policy;
- malformed;
- provider/instrument mismatched;
- non-tradable;
- unsupported contract type/value currency;
- insufficient to prove canonical exposure conversion.

No shared hard-coded TTL is introduced.

## 8. Audit / reconciliation boundary

Provider native and canonical quantities are separate facts.

E4 must preserve at least:

- approved canonical quantity;
- provider requested contracts;
- provider filled contracts;
- effective canonical filled quantity;
- metadata snapshot/reference used for conversion;
- provider order/fill IDs;
- reconciliation state.

E6 later persists these without reinterpreting exchange semantics.

## 9. Account/security decision

Future real execution boundary:

```text
Dedicated OKX R7 sub-account
```

Security rules:

- credentials outside Git;
- Withdraw forbidden;
- no Broker withdrawal/funding-transfer/sub-account-capital-movement methods;
- trusted-IP restriction where operationally feasible;
- account mode/configuration is external prerequisite;
- runtime verifies/fails closed rather than silently changing account mode;
- sub-account identity does not equal E5 approval or release authorization.

Provider progression remains:

```text
internal PaperBroker -> OKX Demo -> real R7 sub-account only after future approval
```

This task implements none of those private provider stages.

## 10. Follow-up scopes

### E1 — next owner for public market provider migration

Bounded scope:

- implement OKX public historical/live market adapter for canonical `BTC_USDT_PERP`;
- map to `BTC-USDT-SWAP` only inside adapter;
- preserve UTC / half-open / closed Candle semantics;
- no private account/order code;
- no Pionex new-development work.

### E2 — next owner for TradeIntent profile

Bounded scope:

- emit `entry-v0.1` MARKET intent;
- preserve reference price as advisory;
- fail closed on unsupported types;
- no broker-specific fields;
- no Strategy Runtime rewrite beyond required TradeIntent serialization boundary.

### E5 — next owner for ApprovedTradePlan / quantity profile

Bounded scope:

- consume profiled intent;
- emit profiled `entry_instruction`;
- emit `base-asset-v0.1` quantity fields;
- preserve E5 risk authority;
- no OKX contract calculation or API calls.

### E4 — next owner after E2/E5 contract producers are revised

Bounded scope:

- mechanically translate `entry-v0.1` to provider-neutral OrderRequest;
- preserve canonical quantity;
- implement local deterministic OKX metadata/quantization adapter logic first;
- reverify official OKX docs;
- Demo/private implementation only under a separate explicit TASK;
- no withdrawal/transfer capability;
- no real execution.

### E6 — next owner for audit/persistence compatibility

Bounded scope:

- persist profile identifiers/quantity unit/asset;
- preserve legacy objects without rewriting;
- later store canonical/provider translation audit facts distinctly;
- no automatic lifecycle promotion from successful translation or Demo state.

## 11. No Pionex new-development dependency

The current construction decision has no new Pionex-specific dependency.

Existing reviewed Pionex code remains historical/migration evidence only until replaced/retired under explicit tasks.

## 12. Open blockers after this decision

The **contract/design boundary itself is resolved**.

Remaining implementation/evidence blockers:

- E2 profile producer implementation: `BLOCKED` pending new TASK;
- E5 profile/quantity producer implementation: `BLOCKED` pending new TASK;
- E4 profile translator/OKX adapter implementation: `BLOCKED` pending producer revisions and new TASK;
- E6 audit support: `BLOCKED` pending new TASK;
- E1 OKX public adapter: `BLOCKED` pending new TASK;
- all executable local evidence: `NOT_RUN`;
- OKX Demo/private execution: `BLOCKED / NOT_AUTHORIZED`;
- real execution: `BLOCKED / NOT_AUTHORIZED`.

## 13. Codex

No Codex ticket.

This task resolves architecture/contract semantics; no locally reproduced bounded implementation defect exists.

## 14. Final disposition

```text
Entry-profile versioning decision        PASS (STATIC)
Canonical contract change procedure      PASS (STATIC)
OKX quantity ownership boundary          PASS (STATIC)
OKX quantization safety rule             PASS (STATIC)
OKX operational/security boundary        PASS (STATIC)
Producer/consumer impact inventory       PASS (STATIC)
Local test definitions                   PASS (STATIC DEFINITION)
Executable verification                  NOT_RUN
Gate A                                   BLOCKED
Gate B                                   BLOCKED
Gate C                                   BLOCKED
Gate D                                   BLOCKED
```
