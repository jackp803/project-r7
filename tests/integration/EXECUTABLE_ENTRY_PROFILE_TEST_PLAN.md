# Local Integration Test Plan — Executable Entry Profile

> Owner: E7 integration  
> Contract: `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`  
> Execution policy: local / Product-Owner-approved non-GitHub environment only  
> Current result: `NOT_RUN`

## Purpose

Define the minimum cross-module tests required after E2/E5/E4 implement `entry-v0.1` and `base-asset-v0.1`.

Static definitions in this file are not executable PASS evidence.

## Required assembly

The future local integration checkout must pin exact accepted revisions for:

- E2 TradeIntent producer;
- E5 RiskDecision / ApprovedTradePlan producer;
- E4 ExecutionGateway / Broker translator;
- E7 contract/profile revision.

E6 persistence may be included for audit tests after its follow-up revision exists.

## Test cases

### INT-ENTRY-001 — MARKET intent remains broker-neutral

Input:

- canonical symbol `BTC_USDT_PERP`;
- valid E2 Signal/strategy boundary;
- executable TradeIntent profile `entry-v0.1`;
- `entry_order_type=MARKET`.

Assert:

- no provider instrument ID appears in TradeIntent;
- no quantity/leverage/risk approval appears in TradeIntent;
- no OKX-specific order spelling appears in TradeIntent.

### INT-ENTRY-002 — E5 creates profiled MARKET plan only after APPROVE

Assert:

- `RiskDecision.decision=APPROVE` is required;
- `ApprovedTradePlan.entry_instruction.profile_version=entry-v0.1`;
- `ApprovedTradePlan.entry_instruction.order_type=MARKET`;
- `quantity_profile_version=base-asset-v0.1`;
- `quantity_unit=BASE_ASSET`;
- `quantity_asset=BTC` for `BTC_USDT_PERP`;
- quantity remains an E5-approved decimal-string bound.

### INT-ENTRY-003 — mechanical E4 translation

Given a valid profiled plan:

Assert:

```text
LONG  -> BUY
SHORT -> SELL
MARKET -> MARKET
OrderRequest.quantity == ApprovedTradePlan.quantity
```

Assert E4 does not modify/invent:

- quantity;
- leverage;
- margin mode;
- risk approval;
- executable price;
- protection bounds.

### INT-ENTRY-004 — advisory reference price remains advisory

Provide `entry_reference_price` / `entry_instruction.reference_price`.

Assert:

- it may remain in audit/context metadata;
- E4 does not create `limit_price`, `stop_price`, or another executable price from it;
- resulting MARKET OrderRequest has no executable price field inferred from reference price.

### INT-ENTRY-005 — legacy `entry_style` does not become executable

Provide legacy `entry_style=MARKET` without `entry_profile_version` / `entry_order_type`.

Assert provider-backed preparation fails closed with an unsupported/missing-profile error.

### INT-ENTRY-006 — unsupported entry type fails closed

For values such as:

```text
LIMIT
STOP
POST_ONLY
IOC
FOK
TRAILING
provider-specific value
unknown string
```

under `entry-v0.1`, assert execution preparation rejects.

### INT-ENTRY-007 — invalid MARKET conditional combinations fail closed

For `entry-v0.1/MARKET`, add any executable:

- `limit_price`;
- `stop_price`;
- `trigger_price`;
- `time_in_force`.

Assert E5 producer and/or E4 consumer rejects rather than silently ignoring or translating.

### INT-ENTRY-008 — quantity traceability E5 -> E4

Assert exact canonical approved quantity and profile fields are preserved from ApprovedTradePlan to OrderRequest.

No provider quantization may overwrite shared `OrderRequest.quantity`.

### INT-ENTRY-009 — successful translation grants no operational authority

After successful provider-neutral translation, assert no automatic transition or permission is created for:

- lifecycle `PAPER`;
- OKX Demo execution;
- SHADOW;
- LIVE;
- Product Owner approval;
- Gate B/C/D PASS.

### INT-ENTRY-010 — legacy object remains auditable

Persist/read a legacy `contracts-v0.1` plan without object profiles.

Assert:

- object is still interpretable as legacy audit data;
- object is not mutated in place;
- execution eligibility is false/blocked.

## LIMIT profile reservation

No LIMIT integration test is a PASS criterion for `entry-v0.1` because LIMIT is not approved.

When a later profile approves LIMIT, local tests must additionally require explicit positive finite `limit_price`, an approved `time_in_force` enum, tick-size rules, and invalid-combination rejection.

## Required future command

Exact command depends on the accepted implementation test filenames. E7 must record the final command with exact revision/environment when implementation exists.

Minimum expected form:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/integration -p "test_*entry*.py" -v
```

Until that test implementation and approved local execution exist:

```text
NOT_RUN
```

GitHub Actions/CI/hosted runners are forbidden.
