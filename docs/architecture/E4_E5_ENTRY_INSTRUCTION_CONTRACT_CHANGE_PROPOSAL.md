# E4 <-> E5 Entry Instruction Contract Change Proposal

> Status: `DRAFT / NOT_APPROVED`
> Owner: E7 Integration / Architecture / System QA / Release
> Task: `E7-20260821-002`
> Existing baseline: `contracts-v0.1`
> Scope: proposal only; this document does **not** modify `contracts/**` and does not authorize PAPER/SHADOW/LIVE.

## 1. Problem statement

`contracts-v0.1` requires an `ApprovedTradePlan.entry_instruction` and requires E4 `OrderRequest.order_type` plus conditional order fields, but the baseline does not define the executable semantics inside `entry_instruction`.

The current E5 revision `cb65c951d59f6fd036bd61691d7e96d025e371c8` emits a provisional shape:

```text
entry_instruction:
  style: <non-empty TradeIntent entry_style>
  reference_price: <optional decimal string>
```

E5 explicitly marks that nested shape as provisional. The current E4 revision `53487a93f6f10d89723403b1a2e2426ba1c7e82a` correctly refuses to infer how that provisional shape becomes:

```text
OrderRequest.order_type
OrderRequest.limit_price
OrderRequest.stop_price
OrderRequest.time_in_force
```

This is not merely a missing adapter. The producer/consumer shared semantics are underspecified.

## 2. E7 classification

**Classification: `CONTRACT MISMATCH`.**

Reason:

- the shared contract defines the outer `entry_instruction` container but not its executable field profile;
- `style` has no canonical enum or normative mapping to `OrderRequest.order_type`;
- `reference_price` is not defined as an executable limit/stop price;
- conditional requirements for price and time-in-force are absent;
- unknown/unsupported instruction values do not have a canonical producer/consumer rule beyond the global fail-closed requirement.

Therefore E4 cannot safely implement a translation without inventing cross-module semantics.

An `INTEGRATION GLUE GAP` will exist only **after** E7 approves a canonical entry-instruction profile. At that point E4 may implement the mechanical adapter under the approved semantics.

## 3. Minimum canonical semantics proposed

The first approved executable entry profile should remain deliberately small.

### 3.1 `ApprovedTradePlan.entry_instruction`

Proposed required field:

```text
order_type
```

Proposed initial enum:

```text
MARKET | LIMIT
```

Proposed optional/audit-only field:

```text
reference_price
```

`reference_price`, when present, is a base-10 positive decimal string used for audit/decision context only. It **must not** be silently converted into `limit_price` or `stop_price`.

Proposed conditional executable fields:

```text
limit_price

time_in_force
```

Rules:

1. `order_type=MARKET`
   - `limit_price` must be absent;
   - `stop_price` must be absent;
   - `time_in_force` must be absent;
   - E4 emits `OrderRequest.order_type=MARKET`.

2. `order_type=LIMIT`
   - `limit_price` is required and must be a finite positive base-10 decimal string;
   - `time_in_force` is required;
   - proposed baseline `time_in_force` enum: `GTC | IOC | FOK`;
   - `stop_price` must be absent in the initial entry profile;
   - E4 emits the same canonical `order_type`, `limit_price`, and `time_in_force` without loosening or replacing them.

3. Entry orders are opening-exposure instructions:
   - `reduce_only` is omitted or `false` for this entry profile;
   - E4 must not change outer `ApprovedTradePlan.quantity`, leverage, margin mode, or protection bounds while translating the entry request.

4. `STOP`, `STOP_LIMIT`, trigger-order, post-only, maker-only, trailing, exchange-specific, or other entry styles are **not** part of the minimum profile. They require a later approved contract extension.

5. Unsupported or unknown `order_type` / `time_in_force` values fail closed at both producer validation and E4 translation.

### 3.2 Upstream `TradeIntent.entry_style`

Current `contracts-v0.1` allows optional `entry_style` but does not define an enum. A future approved contract revision must align this request-level field with the plan-level executable profile.

Minimum safe rule:

- `entry_style=MARKET` may produce canonical `entry_instruction.order_type=MARKET` after E5 approval;
- `entry_style=LIMIT` may produce canonical `order_type=LIMIT` only when an explicit approved limit price is available under the revised contract;
- current `entry_reference_price` must not be assumed to be a limit price;
- unsupported styles are rejected/fail closed rather than normalized by E4.

If the product does not yet have a distinct approved limit-price source, E5 should support `MARKET` only for the first integrated profile and reject/defer `LIMIT` until the upstream contract supplies a real limit-price semantic.

## 4. Compatibility impact

### Existing `contracts-v0.1`

Existing E5 plans contain `entry_instruction.style` and may omit canonical `order_type`. Existing E4 intentionally rejects these plans at concrete translation.

### Proposed semantics

Making `entry_instruction.order_type` normative/required for executable translation changes the meaning and required content of a shared object. Existing `style`-only plan instances would not satisfy the new executable profile.

**Compatibility classification: `BREAKING`.**

This proposal therefore must **not** silently change `contracts-v0.1` in place.

### Forward compatibility

Future consumers must reject unknown required enum values safely. New optional audit metadata may later be additive-compatible, but new executable order types or changed conditional semantics require E7 compatibility review.

## 5. Proposed versioning treatment

Under the current `contracts/README.md` rules, a breaking field/semantic requirement requires a major contract-set revision.

Recommended treatment:

```text
contracts-v0.1        remains unchanged and supported only under its current semantics
next approved breaking baseline -> contracts-v1.0
```

`contracts-v1.0` is a proposal identifier, not an approved version in this task. E7/PM must complete the normal contract-change procedure before materializing it.

A migration adapter may be temporary, but it must not infer `reference_price -> limit_price` or other semantics not explicitly present in the revised plan.

## 6. Producer / consumer impact inventory

### E5 — producer of `ApprovedTradePlan`

Owner: E5 Risk & Position.

Follow-up scope:

- validate the revised supported entry request enum;
- emit canonical `entry_instruction.order_type`;
- emit required conditional fields only when explicitly approved/available;
- do not treat `entry_reference_price` as executable price unless a revised contract explicitly says so;
- preserve risk veto and `RiskDecision -> ApprovedTradePlan` authority;
- reject unsupported entry styles rather than passing provisional strings downstream;
- update E5-owned tests/docs only.

E5 must not implement broker submission or E4 retry semantics.

### E4 — primary consumer / execution translator

Owner: E4 Execution.

Follow-up scope:

- replace the current fail-closed provisional translator with a translator that consumes only the approved canonical profile/version;
- map canonical `order_type` and conditional fields mechanically into `OrderRequest`;
- continue deriving `side` only from the approved plan direction;
- preserve plan quantity exactly;
- reject unsupported/invalid instruction combinations;
- preserve stable idempotency identity;
- do not infer risk approval, leverage, margin policy, protection loosening, or missing prices;
- update E4-owned gateway tests/docs only.

### E6 — secondary consumer / audit

Owner: E6 Platform.

Current early Slice 2 implementation does not yet persist `ApprovedTradePlan`; therefore an immediate E6 code change is `NOT_APPLICABLE` to the currently reviewed E6 skeleton.

When execution/audit persistence is added, E6 follow-up scope is:

- persist the exact plan schema version and canonical entry instruction without reinterpretation;
- keep plan, OrderRequest, OrderResult, Fill, and lifecycle/audit references traceable;
- reject incompatible required schema when E6 begins validating this object;
- never infer order semantics or risk approval from display/storage state.

### E7 — integration / contract authority

Owner: E7.

Follow-up scope:

- complete producer/consumer inventory at change time;
- approve the final field/enums/conditional rules;
- version and update canonical contract documentation through the normal procedure;
- define migration/compatibility policy;
- add E4<->E5 integration/safety test definitions;
- keep release gates blocked until approved local evidence exists.

## 7. Required local verification after an approved contract revision

All commands must run only in the Product-Owner-approved local environment.

At minimum:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) "src")
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/integration -p "test_*entry*translation*.py" -v
```

Required integration cases:

- canonical MARKET plan -> MARKET OrderRequest;
- canonical LIMIT plan -> exact limit price/TIF if LIMIT is approved in the revision;
- `reference_price` never becomes executable `limit_price` implicitly;
- unsupported order type fails closed;
- invalid conditional field combination fails closed;
- old `contracts-v0.1` provisional `style`-only plan remains rejected by the new translator unless an explicitly approved migration adapter exists;
- exact quantity is preserved E5 -> E4;
- direction -> side mapping is deterministic;
- expired plan is rejected;
- stable client/order request identity remains unchanged for one logical order;
- no PAPER/LIVE authorization is inferred from successful translation.

If E6 execution-audit persistence exists at that time, also add a local round-trip test proving the exact plan/version/instruction remains traceable without semantic reinterpretation.

## 8. Release / execution effect

Current state remains:

```text
E4 bounded Broker/PaperBroker skeleton    STATIC PASS (subject to E7 review artifact)
E4 <-> E5 concrete entry translation      BLOCKED / CONTRACT MISMATCH
Executable verification                   NOT_RUN
Gate A                                    BLOCKED
Gate B                                    BLOCKED
Gate C                                    BLOCKED
Gate D                                    BLOCKED
PAPER / SHADOW / LIVE                     NOT ENABLED
```

This draft is not execution authority and not an approved shared-contract revision.
