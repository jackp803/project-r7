# E7 Current Task

- task_id: `E7-20260821-004`
- issued_at: `2026-08-21T10:07:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-okx-contract-boundary-20260821`
- supersedes: `E7-20260821-003` because the Product Owner changed the V1 broker target before repository evidence for that task was accepted
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts/README.md`, `contracts-v0.1`, ADR-0001, release gates, Product Owner decision `docs/architecture/BROKER_TARGET_OKX_DECISION_20260821.md`

## Product Owner decision

V1 no longer targets Pionex for new development.

The V1 exchange/execution target is now:

```text
OKX
Dedicated R7 sub-account
Canonical BTC_USDT_PERP -> OKX BTC-USDT-SWAP adapter mapping
isolated intent
internal PaperBroker -> OKX Demo -> real sub-account only after later release approval
```

Shared architecture must remain broker-neutral above provider adapters.

## Objective

Resolve the two cross-module boundaries that must be coherent before E2/E5/E4 follow-up implementation can continue:

1. versioned executable `TradeIntent` / `ApprovedTradePlan.entry_instruction` semantics;
2. OKX derivative instrument sizing/quantization and account-configuration boundary between shared risk authority and provider-specific execution.

This is an E7 contract/ADR/integration-test-definition task only. Do not modify E1/E2/E3/E4/E5/E6 production code.

## Required actions

### A. Recover/supersede the prior entry-contract task cleanly

1. Treat prior E7 proposal/review artifacts as input only. Do not claim `E7-20260821-003` complete unless its repository evidence actually exists.
2. Complete the formal `contracts/README.md` change procedure for executable entry semantics:
   - request/problem;
   - producer inventory;
   - consumer inventory;
   - behavioral/persistence/replay/migration/release impact;
   - compatibility classification;
   - versioning model;
   - ADR when material;
   - canonical contract revision only if coherent;
   - local-only integration/safety test definitions.
3. Include at minimum E2 TradeIntent producer, E5 ApprovedTradePlan producer, E4 execution consumer, E6 future audit persistence, and frozen E1/E2/E3 Slice 1 compatibility impact.
4. Do not perform a set-wide major bump merely because the entry sub-profile was underspecified. Prefer the smallest unambiguous safe treatment. If a major set-wide bump is truly required, justify why no narrower compatible/object-profile treatment works and provide migration/support rules for every implemented `contracts-v0.1` object.
5. Preserve exchange-neutral entry semantics. Do not encode OKX-specific names into shared `TradeIntent` or `ApprovedTradePlan` fields merely because OKX is now V1 target.

### B. Canonical executable entry semantics

Regardless of version treatment, resolve these rules:

- explicit executable order type is required before E4 translation;
- initial supported profile should remain deliberately small;
- `MARKET` must not silently carry executable limit/stop/TIF semantics;
- if `LIMIT` is supported, executable `limit_price` must be explicit positive finite decimal-string data and `time_in_force` must be explicit from an approved enum;
- `reference_price` remains advisory/audit context unless separately and explicitly contracted as executable;
- STOP/trigger/post-only/trailing/exchange-specific entry types remain unsupported until versioned;
- unknown/unsupported values and invalid conditional combinations fail closed;
- E4 translation is mechanical and cannot invent quantity, leverage, margin mode, price, protection loosening, or risk approval.

### C. OKX sizing / instrument boundary

Review official OKX semantics and define the provider boundary without leaking exchange-specific units into unrelated shared domains.

At minimum account for:

- OKX `BTC-USDT-SWAP` adapter identity;
- derivative order `sz` being instrument-contract units rather than blindly identical to canonical risk quantity;
- instrument metadata such as `ctVal`, `ctType`, `lotSz`, `minSz`, `tickSz`, and tradability/state where applicable;
- isolated trading intent / provider account mode as an external operational prerequisite;
- dedicated R7 sub-account isolation as a security boundary, not a substitute for E5 risk approval.

Decide explicitly:

1. what quantity/exposure unit the canonical E5-approved plan should represent;
2. which OKX conversion/quantization fields remain E4/provider-adapter implementation details;
3. whether any shared object needs a versioned unit/rounding semantic clarification;
4. how E4 proves the exchange order cannot exceed E5-approved exposure after contract-unit quantization;
5. how stale/unknown/incompatible instrument metadata fails closed;
6. how reconciliation/audit records preserve the canonical approved amount and the actual provider contract quantity without conflating them.

Mandatory safety invariant:

> Provider quantization may round down or reject; it must never round up into exposure greater than the E5-approved bound.

### D. OKX operational/security boundary

Document integration requirements, without implementing private API code:

- dedicated OKX sub-account is the future live account boundary;
- API credentials stay outside Git;
- Withdraw permission is forbidden;
- R7 Broker interface must not expose withdrawal/funding-transfer/sub-account-capital-movement capability;
- account mode/configuration must be treated as an externally configured prerequisite and verified/fail-closed before new exposure;
- OKX Demo Trading is the first provider execution adapter target before real-money use;
- provider API/product behavior must be reverified from official OKX documentation at implementation time.

### E. Artifacts / tests

Produce E7-owned repository artifacts that include:

- explicit versioning/compatibility decision for the entry profile;
- ADR(s) for material shared semantics;
- canonical contract revision only if the procedure reaches a coherent approved result;
- OKX provider-boundary architecture note or ADR;
- producer/consumer impact inventory;
- exact bounded follow-up scopes for E1/E2/E5/E4/E6;
- local-only integration/safety test definitions covering entry translation and OKX quantity quantization/fail-closed cases.

Minimum future local test cases must include:

- canonical MARKET plan -> mechanical provider-neutral OrderRequest;
- LIMIT only if explicitly approved and all required executable fields exist;
- reference_price never implicitly becomes executable price;
- unsupported entry type fails closed;
- exact approved quantity/exposure is traceable E5 -> E4;
- OKX contract quantization never increases approved exposure;
- below-minimum/non-representable quantity rejects or rounds down per approved rule, never up;
- stale/missing instrument metadata blocks new exposure;
- provider requested contract quantity and actual fills remain distinct from canonical approved quantity;
- no Demo/PAPER/LIVE authorization is inferred from successful translation.

## Versioning / contract rule

Do not silently mutate historical `contracts-v0.1` meaning.

If a coherent compatible revision is possible, document exactly how old objects remain interpretable and why no ambiguity is introduced. If a breaking revision is required, document migration and support scope before materializing it.

If no coherent treatment can be established, leave `contracts/**` unchanged and return `BLOCKED` with the exact unresolved alternatives.

## Official OKX references to re-check

Use official OKX documentation as provider authority for current exchange semantics. At task issue time the relevant official references include:

- https://www.okx.com/docs-v5/en/
- https://www.okx.com/zh-hant/help/subaccounts-account-mode-and-api-connections-faq

Do not copy provider behavior from blogs/community posts when official documentation exists.

## Acceptance

Task is complete only when Git contains either a coherent E7 contract/provider-boundary decision or a precise BLOCKED decision, and explicitly records:

- entry-instruction versioning disposition;
- OKX sizing/quantization ownership boundary;
- security/account-mode boundary;
- E1/E2/E5/E4/E6 follow-up owners/scopes;
- no Pionex new-development dependency;
- no domain implementation edits;
- no unapproved LIVE/Demo/private execution implementation;
- executable verification `NOT_RUN` unless approved local evidence exists;
- Gate A/B/C/D unchanged.

## Writable scope

- `contracts/**` only through the formal contract-change procedure
- `docs/adr/**`
- E7-owned architecture/integration/status/review paths
- `tests/integration/**`
- `tests/safety/**` only for E7-owned cross-module scenarios
- `coordination/E7/STATUS.md`

## Forbidden scope

- E1/E2/E3/E4/E5/E6 production implementation edits;
- Pionex-specific new development;
- OKX private/Demo API implementation or credential handling;
- withdrawal/funding-transfer capability;
- PAPER/SHADOW/LIVE enablement;
- GitHub Actions/CI/runner/project compute;
- treating static evidence or `NOT_RUN` as executable PASS.

## Completion / status

Persist the decision/revision or exact blocker, update `coordination/E7/STATUS.md`, and stop. Do not automatically start E2/E5/E4 implementation afterward.
