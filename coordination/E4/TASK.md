# E4 Current Task

- task_id: `E4-20260821-006`
- issued_at: `2026-08-21T12:50:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-execution-v2`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`, ADR-0002/0003, Product Owner OKX decision, E7 review `status/e7/E2_E5_PROFILE_CHAIN_STATIC_REVIEW_20260821.md`

## Objective

Extend the statically accepted E4 Broker/PaperBroker skeleton with the **bounded provider-neutral entry translator and deterministic OKX instrument sizing/quantization layer** required by the E7-accepted E2/E5 producer chain.

This task does **not** authorize OKX Demo/private API calls, authentication, signatures, account calls, leverage-setting calls, or order submission.

## Accepted upstream pins

- E2 implementation: `f99a8d00cd1fe40e1d73964d8b1cf37bc1886bd4`
- E5 implementation: `e5f7088301a92deadfd9f6c416ae03b466c38a47`
- E7 disposition: E2 `PASS (STATIC)`, E5 `PASS (STATIC)`, E2->E5 `PASS (STATIC)`
- parent schema: `contracts-v0.1`
- entry profile: `entry-v0.1 / MARKET`
- quantity profile: `base-asset-v0.1 / BASE_ASSET / BTC`
- executable verification: `NOT_RUN`

## Required actions

1. Non-destructively synchronize `agent/e4-execution-v2` with latest `main` before implementation. Preserve the accepted E4 skeleton/history; no force rewrite. If safe synchronization is not possible, report `BLOCKED`.
2. Preserve existing E4 authority/idempotency/partial-fill/overfill/ambiguous-acknowledgement/reconciliation fail-closed behavior.
3. Replace the provisional entry translator with canonical mechanical translation that accepts only a valid E5 ApprovedTradePlan declaring:
   - `entry_instruction.profile_version = entry-v0.1`
   - `entry_instruction.order_type = MARKET`
   - `quantity_profile_version = base-asset-v0.1`
   - `quantity_unit = BASE_ASSET`
   - `quantity_asset = BTC`
4. Mechanical shared translation only:
   - `LONG -> BUY`
   - `SHORT -> SELL`
   - `MARKET -> MARKET`
   - preserve canonical `ApprovedTradePlan.quantity` unchanged in shared `OrderRequest.quantity`.
5. Treat `reference_price` as advisory only. Do not create `limit_price`, `stop_price`, `trigger_price`, or TIF from it.
6. Fail closed for missing/unknown profile versions, unsupported order types, invalid quantity profile/unit/asset, malformed quantity, expired/incompatible plans, or forbidden executable price/TIF fields.
7. Implement deterministic **local provider metadata and sizing logic** for the configured mapping `BTC_USDT_PERP -> BTC-USDT-SWAP`. No network/API call is authorized in this task.
8. Define/validate the E4-owned OKX instrument metadata model needed for sizing, including at minimum:
   - provider/instrument identity;
   - `instType`;
   - `ctVal`;
   - `ctMult`;
   - `ctValCcy`;
   - `ctType`;
   - `lotSz`;
   - `minSz`;
   - `tickSz`;
   - tradability/state;
   - metadata observation/reference and an explicit E4 freshness policy/version.
9. Support only the E7-approved direct conversion class where current metadata proves an unambiguous canonical BTC base quantity per provider contract. Unsupported/price-dependent conversion fails closed.
10. For supported direct conversion, implement deterministically:

```text
base_per_contract = ctVal * ctMult
raw_contracts     = approved_base_quantity / base_per_contract
provider_sz       = floor_to_valid_lot(raw_contracts, lotSz)
effective_base    = provider_sz * base_per_contract
```

Acceptance requires:

```text
provider_sz >= minSz
0 < effective_base <= approved_base_quantity
```

Below minimum/non-representable quantity -> reject. Provider quantization may round down or reject; **never round up above the E5-approved bound**.
11. Missing/stale/malformed/provider-mismatched/non-tradable/unsupported metadata must block new exposure.
12. Preserve canonical and provider-native facts separately. At minimum the E4 translation/audit object must distinguish:
   - canonical approved quantity/profile;
   - provider requested contract quantity;
   - effective canonical requested quantity after round-down;
   - instrument metadata reference/observation used;
   - provider instrument identity.
   Do not place OKX contract `sz` into shared canonical quantity fields.
13. Do not add withdrawal, funding transfer, sub-account-capital-movement, or other asset-movement Broker capability.
14. Add deterministic local-only tests covering at minimum:
   - valid profiled MARKET plan -> mechanical OrderRequest;
   - LONG/SHORT side mapping;
   - advisory reference price never becomes executable price;
   - unknown/missing profile fails closed;
   - exact representable quantity;
   - round-down quantity;
   - below-minimum reject;
   - lot/min size validation;
   - stale/missing/malformed/non-tradable/mismatched metadata reject;
   - unsupported conversion reject;
   - provider sizing never exceeds canonical approved BTC exposure;
   - canonical quantity and provider contract quantity remain distinct;
   - existing ambiguity/reconciliation/idempotency behavior remains intact.
15. Recheck current official OKX API V5 instrument semantics while implementing and document the references used. Do not implement provider networking in this task.
16. Update E4 handoff and `coordination/E4/STATUS.md` with exact branch HEAD, changed files, metadata policy, conversion assumptions, limitations, and verification state.
17. Executable verification remains local-only. If no Product Owner-approved local environment exists, record `NOT_RUN` plus exact commands.

## Acceptance

Static/source acceptance requires:

- canonical `entry-v0.1` MARKET translation is mechanical and fail closed;
- canonical BTC quantity is never conflated with OKX `sz`;
- deterministic OKX sizing can only round down or reject;
- no generated provider exposure exceeds the E5-approved bound;
- provider metadata incompatibility/staleness blocks new exposure;
- existing Broker/PaperBroker safety behavior remains intact;
- no private/Demo API/auth/account/order submission exists;
- no shared-contract change;
- no Pionex new development;
- no GitHub Actions/CI/hosted runner/project compute;
- executable evidence remains `NOT_RUN` without approved local execution.

## Writable scope

E4-owned paths only:

- `src/execution/**`
- `src/brokers/**`
- `tests/execution/**`
- `tests/brokers/**`
- E4-owned docs/status/handoff
- `coordination/E4/STATUS.md`

## Forbidden scope

- `contracts/**` changes;
- E1/E2/E3/E5/E6 production rewrites;
- OKX private/Demo API networking, auth, credentials, account calls, or order submission;
- withdrawal/funding-transfer/sub-account capital movement;
- PAPER/SHADOW/LIVE enablement;
- GitHub compute/CI.

## Completion / status

Persist the bounded translator + deterministic sizing implementation and handoff, update STATUS, then stop. Do not start OKX Demo/private execution automatically.
