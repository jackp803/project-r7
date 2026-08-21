# E7 Status

- task_id: `E7-20260821-004`
- agent: `E7`
- state: `DONE_PENDING_PM`
- branch: `agent/e7-okx-contract-boundary-20260821`
- head_sha: `BRANCH_HEAD_CONTAINS_THIS_STATUS`
- summary: `Resolved the provider-neutral executable entry profile and OKX derivative sizing/quantization/account-security boundaries through the formal contract-change procedure. Parent schema remains contracts-v0.1; compatible object profiles entry-v0.1 and base-asset-v0.1 are canonical for new execution construction. No E1-E6 production code or private/Demo execution was implemented.`
- entry_versioning_disposition: `PASS / ADDITIVE_COMPATIBLE_OBJECT_PROFILE / NO_SET_WIDE_MAJOR_BUMP`
- canonical_parent_schema: `contracts-v0.1`
- entry_profile: `entry-v0.1 / MARKET_ONLY`
- quantity_profile: `base-asset-v0.1 / BASE_ASSET`
- canonical_btc_perp_quantity_unit: `BTC base-asset exposure bound`
- okx_provider_mapping: `BTC_USDT_PERP -> BTC-USDT-SWAP inside provider adapter only`
- okx_sz_semantics: `provider contract units; E4 adapter-owned; never substituted for shared canonical quantity`
- quantization_rule: `ROUND_DOWN_TO_VALID_LOT_OR_REJECT; NEVER_ROUND_UP_ABOVE_E5_BOUND`
- okx_account_boundary: `future dedicated R7 sub-account; external account-mode/config prerequisite; isolated intent; Demo first; real execution not authorized`
- withdraw_permission: `FORBIDDEN`
- broker_asset_movement_capability: `FORBIDDEN`
- contracts_changed: `YES — contracts/README.md governance registry + new compatible contracts/EXECUTION_OBJECT_PROFILES_V0_1.md; historical contracts/SHARED_CONTRACTS_V1.md intentionally unchanged`
- production_domain_code_changed: `NO`
- executable_verification: `NOT_RUN`
- github_compute: `NOT_USED`
- gate_a: `BLOCKED / UNCHANGED`
- gate_b: `BLOCKED / UNCHANGED`
- gate_c: `BLOCKED / UNCHANGED`
- gate_d: `BLOCKED / UNCHANGED`
- codex_ticket: `NONE / NOT_APPLICABLE`
- handoff_path: `status/e7/OKX_CONTRACT_BOUNDARY_DECISION_20260821.md`
- next_owner: `PM to issue bounded E1/E2/E5/E4/E6 follow-up TASKs`

## Supersession

`E7-20260821-004` supersedes `E7-20260821-003`.

Repository inspection found no accepted `E7-20260821-003` commit evidence; `agent/e7-entry-contract-vnext-20260821` was not ahead of current main. Prior entry-contract material was input only and is not claimed complete.

## Canonical contract decision

Parent shared schema remains:

```text
contracts-v0.1
```

New object-profile identifiers:

```text
entry-v0.1
base-asset-v0.1
```

This is compatible because the old baseline never defined a conflicting executable `entry_instruction` meaning, legacy objects remain auditable, and missing profile semantics fail closed for the new execution path.

No frozen Slice 1 E1/E2/E3 object requires a schema migration.

## Entry profile

`entry-v0.1` supports only:

```text
MARKET
```

Required future E2 executable intent semantics:

```text
entry_profile_version = entry-v0.1
entry_order_type      = MARKET
```

Required future E5 plan semantics:

```text
entry_instruction.profile_version = entry-v0.1
entry_instruction.order_type      = MARKET
```

`entry_reference_price` / `reference_price` remain advisory. Legacy `entry_style` is not executable. LIMIT/STOP/trigger/post-only/trailing/exchange-specific profiles remain unsupported.

## Quantity profile

For canonical `BTC_USDT_PERP`:

```text
quantity_profile_version = base-asset-v0.1
quantity_unit            = BASE_ASSET
quantity_asset           = BTC
```

E5 `ApprovedTradePlan.quantity` is the maximum approved new-position BTC exposure.

Shared `OrderRequest.quantity` remains canonical base quantity. OKX contract `sz` is provider-native E4 adapter data.

## OKX sizing boundary

E4/provider adapter owns current instrument metadata retrieval and validation including at minimum:

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
- metadata observation/reference

For the V1 direct supported conversion class:

```text
base_per_contract = ctVal * ctMult
raw_contracts     = approved_base_quantity / base_per_contract
provider_sz       = floor_to_lot(raw_contracts, lotSz)
effective_base    = provider_sz * base_per_contract
```

Acceptance requires:

```text
provider_sz >= minSz
0 < effective_base <= approved_base_quantity
```

Below minimum -> reject. Unsupported/price-dependent conversion -> reject. Missing/stale/incompatible metadata -> reject.

## Audit / reconciliation boundary

E4 must preserve canonical and provider-native facts separately:

- canonical approved quantity/profile;
- provider requested contract `sz`;
- provider actual filled contracts;
- effective canonical filled base quantity;
- instrument metadata reference used for translation;
- provider order/fill IDs;
- reconciliation state.

E6 later persists these without conflation or authority inference.

## Security / operational boundary

Future real execution requires a dedicated R7 OKX sub-account under separate release authorization.

Rules:

- API key/secret/passphrase outside Git;
- Withdraw forbidden;
- no withdrawal/funding-transfer/sub-account-capital-movement Broker methods;
- trusted IP restriction where operationally feasible;
- account mode/configuration externally configured and runtime-verified/fail-closed;
- isolated intent does not equal E5 approval;
- successful Demo does not equal PAPER/SHADOW/LIVE authorization.

OKX Demo remains the first provider execution target under a future explicit TASK. No private/Demo API implementation occurred here.

## Official OKX references rechecked

- `https://www.okx.com/docs-v5/en/`
- `https://www.okx.com/zh-hant/help/subaccounts-account-mode-and-api-connections-faq`

Current provider semantics must be reverified again at implementation time.

## Files changed

- `contracts/README.md`
- `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`
- `docs/adr/ADR-0002-versioned-executable-entry-and-quantity-profiles.md`
- `docs/adr/ADR-0003-okx-derivative-sizing-and-operational-boundary.md`
- `status/e7/OKX_CONTRACT_BOUNDARY_DECISION_20260821.md`
- `tests/integration/EXECUTABLE_ENTRY_PROFILE_TEST_PLAN.md`
- `tests/safety/OKX_QUANTITY_BOUNDARY_TEST_PLAN.md`
- `coordination/E7/STATUS.md`

No E1/E2/E3/E4/E5/E6 production implementation file was edited.

## Local-only verification

Result:

```text
NOT_RUN
```

No project code, unit test, integration test, safety test, provider API experiment, backtest, Demo request, private request, or broker simulation was executed in this GitHub environment.

Future local test definitions are recorded in the two E7 test-plan files. Exact executable commands must be bound to accepted implementation revisions when those revisions exist.

## Follow-up owners / bounded scopes

### E1

OKX public market adapter only; preserve canonical Candle semantics; no private account/execution; no new Pionex development.

### E2

Implement provider-neutral `entry-v0.1` TradeIntent serialization; MARKET only; advisory reference price remains non-executable.

### E5

Emit profiled ApprovedTradePlan and canonical `base-asset-v0.1` quantity; no OKX metadata/API/contract sizing.

### E4

After producer revisions, implement mechanical profile translation and deterministic local OKX metadata/quantization logic. Private/Demo adapter work requires a separate explicit TASK and official-doc recheck.

### E6

Persist profile identifiers and later canonical/provider audit facts; no automatic lifecycle/release promotion.

## Remaining blockers

- E1 OKX public adapter implementation: `BLOCKED` pending TASK.
- E2 entry profile implementation: `BLOCKED` pending TASK.
- E5 plan/quantity profile implementation: `BLOCKED` pending TASK.
- E4 profile/OKX adapter implementation: `BLOCKED` pending producer revisions + TASK.
- E6 audit persistence compatibility: `BLOCKED` pending TASK.
- executable local evidence: `NOT_RUN`.
- OKX Demo/private execution: `BLOCKED / NOT_AUTHORIZED`.
- real execution: `BLOCKED / NOT_AUTHORIZED`.

The contract/design boundary itself is resolved statically.

E7 stops here and waits for PM. No E1/E2/E5/E4/E6 follow-up implementation is started automatically.
