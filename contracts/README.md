# Shared Contract Registry

> Authority: E7 Integration / Architecture / System QA / Release Engineer  
> Baseline: `contracts-v0.1`  
> Repository: `jackp803/project-r7`

## Purpose

`contracts/` is the canonical cross-module interface surface for E1–E7.

Domain agents may propose changes, but no E1–E6 implementation may silently redefine a shared concept such as Candle, StrategyDefinition, TradeIntent, ApprovedTradePlan, Order, Fill, Position, BacktestResult, lifecycle state, operational mode, release evidence, or funding allocation evidence.

The first materialized baseline is:

- [`SHARED_CONTRACTS_V1.md`](./SHARED_CONTRACTS_V1.md)

Compatible executable/evidence object-profile refinements currently registered under that baseline:

- [`EXECUTION_OBJECT_PROFILES_V0_1.md`](./EXECUTION_OBJECT_PROFILES_V0_1.md) — `entry-v0.1` + `base-asset-v0.1`
- [`PROTECTION_OBJECT_PROFILE_V0_1.md`](./PROTECTION_OBJECT_PROFILE_V0_1.md) — `protection-v0.1` actual-fill PositionAction -> protective OrderRequest semantics
- [`CLOSE_TRADE_RESULT_PROFILE_V0_1.md`](./CLOSE_TRADE_RESULT_PROFILE_V0_1.md) — `close-v0.1` + `trade-result-v0.1` + `linear-base-asset-pnl-v0.1` close authority, authoritative flatness, fill-set closure, and canonical TradeResult semantics
- [`FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md`](./FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md) — `funding-allocation-v0.1` provider-neutral exact-interval funding evidence, completeness, identity, ownership, TradeResult binding, and persistence semantics
- [`POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md`](./POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md) — `position-lifecycle-projection-v0.1` E5-owned lifecycle ordering/identity over unchanged E4 broker Position facts for deterministic persistence/restart

## Authority and ownership

- Product Owner has final authority over product scope, capital exposure, live enablement, and infrastructure policy.
- E7 has final technical approval/versioning authority over shared contracts.
- Domain producers own production of valid contract instances inside their domain.
- Domain consumers must reject incompatible/invalid contract instances rather than guessing missing semantics.
- A domain agent may not create a permanent parallel shared model merely to avoid requesting a contract change.

For `funding-allocation-v0.1` specifically:

- E4 owns Paper/provider funding-source acquisition, completeness, normalization, interval allocation and canonical evidence emission;
- E5 validates/consumes canonical funding evidence for TradeResult but does not manufacture source truth;
- E6 persists/replays/audits evidence but does not invent or rewrite funding truth;
- E7 owns profile/version/release semantics.

For `position-lifecycle-projection-v0.1` specifically:

- E4 continues to own the broker Position fact payload and `broker_state_observed_at`; it does not allocate lifecycle order;
- E5 owns `lifecycle_state` plus the lifecycle projection revision/predecessor/event/identity metadata and emits the durability-eligible profiled Position;
- E6 persists/replays/indexes the serialized projection and enforces the shared ordering/conflict rules without deriving lifecycle or assigning revisions;
- E7 owns profile/version/integration/release semantics.

## Contract status

Every shared contract uses one of these states:

- `DRAFT` — not safe for downstream implementation dependency.
- `BASELINE` — approved minimum contract for current construction; additive compatible refinement is allowed through E7 review.
- `STABLE` — compatibility guarantees are release-significant.
- `DEPRECATED` — supported only during an explicit migration window.
- `RETIRED` — no longer valid for new production use.

`SHARED_CONTRACTS_V1.md` begins as `BASELINE` so E1–E6 have one common interface target while implementation is still early.

## Versioning rules

Contract set versions use `major.minor` semantics.

- **Major**: breaking field meaning, removed required field, incompatible enum/state change, changed time/unit/numeric semantics, or changed authority boundary.
- **Minor**: backward-compatible optional fields, additional reason codes, additive enum values only when consumers are required to reject/handle unknown values safely, or documentation clarification that does not change behavior.

Every serialized shared object must carry `schema_version` once executable implementations are introduced.

### Compatible object-profile versioning

A previously underspecified nested/optional semantic or previously undefined evidence family may be refined through an E7-approved **object profile** without forcing an unrelated set-wide schema bump only when all of the following hold:

1. the parent contract did not already guarantee a conflicting meaning;
2. profile fields/identifiers are additive;
3. legacy objects remain interpretable for their original historical/research/audit purpose;
4. a consumer requiring the new behavior fails closed when the profile is absent or unsupported;
5. no historical object is rewritten to claim a profile it did not originally carry;
6. unrelated implemented objects keep their existing `schema_version` and semantics.

Object-profile identifiers are explicit and independently versioned, for example:

```text
entry-v0.1
base-asset-v0.1
protection-v0.1
close-v0.1
trade-result-v0.1
linear-base-asset-pnl-v0.1
funding-allocation-v0.1
position-lifecycle-projection-v0.1
```

An object profile cannot be used to disguise a real breaking change. If existing field meaning, units, authority, or required-state behavior is changed incompatibly, normal major-version rules apply.

## Canonical interchange conventions

Unless an approved ADR says otherwise:

- field names use `snake_case`;
- timestamps are RFC 3339 UTC strings ending in `Z` at interchange boundaries;
- internal timezone is UTC;
- price, quantity, notional, margin, fee, PnL, funding and other financial decimals serialize as base-10 decimal strings, not binary floating-point JSON numbers;
- identifiers are opaque strings and must not encode business meaning that consumers depend on;
- enums are explicit uppercase strings;
- unknown required enum/state values fail closed;
- optional values are omitted or explicitly `null` only where the contract permits it;
- no contract contains API keys, API secrets, passwords, private keys, session tokens, or other live credentials.

## Contract change procedure

Any cross-module change must follow this sequence:

1. **Request** — domain owner documents why the current contract is insufficient.
2. **Producer inventory** — E7 identifies every producer.
3. **Consumer inventory** — E7 identifies every consumer.
4. **Impact** — identify behavioral, persistence, replay, migration, and release impact.
5. **Compatibility** — classify the change as compatible or breaking.
6. **ADR** — create/update an ADR when semantics, authority, state machines, or dependency direction materially change.
7. **Contract revision** — update the canonical contract and version.
8. **Tests** — add/adjust relevant local test definitions.
9. **Local verification** — execute only on a local or Product-Owner-approved non-GitHub environment; otherwise record `NOT_RUN` and the exact command.
10. **Integration** — E7 accepts dependent revisions only after contract evidence is coherent.

A temporary adapter may bridge versions when approved. A temporary duplicate model may not silently become permanent.

## Compatibility obligations

### Producers

A producer must:

- emit only fields/values valid for the declared schema/profile version;
- preserve required units/time semantics;
- not manufacture valid-looking values when source state is unknown;
- expose degraded/unknown state explicitly or withhold a final evidence object where the profile requires completeness;
- keep immutable identities immutable.

### Consumers

A consumer must:

- validate the schema version and any required object profile it supports;
- reject or safely degrade on incompatible required semantics;
- never infer LIVE authority from credentials, strategy success, or UI state;
- never treat `UNKNOWN` as healthy;
- never infer funding zero from missing/unavailable evidence;
- never infer lifecycle ordering from persistence arrival order, storage timestamps, row IDs or unrelated execution rows;
- never bypass the Strategy -> Risk -> ApprovedTradePlan -> Execution chain.

## GitHub execution policy

GitHub stores these contracts, source code, tests, PRs, issues, documentation, and shared project history only.

Do **not** add or rely on GitHub Actions, GitHub CI, GitHub-hosted runners, GitHub-triggered self-hosted runners, scheduled Actions, or GitHub-based project-code execution for contract verification. Local evidence or `NOT_RUN` is required.

## Security

This is a public repository. Real secrets are forbidden in contract examples, fixtures, logs, screenshots, issues, PR text, and tracked configuration. Use fake or empty values only.
