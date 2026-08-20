# Shared Contract Registry

> Authority: E7 Integration / Architecture / System QA / Release Engineer  
> Baseline: `contracts-v0.1`  
> Repository: `jackp803/project-r7`

## Purpose

`contracts/` is the canonical cross-module interface surface for E1–E7.

Domain agents may propose changes, but no E1–E6 implementation may silently redefine a shared concept such as Candle, StrategyDefinition, TradeIntent, ApprovedTradePlan, Order, Fill, Position, BacktestResult, lifecycle state, operational mode, or release evidence.

The first materialized baseline is:

- [`SHARED_CONTRACTS_V1.md`](./SHARED_CONTRACTS_V1.md)

## Authority and ownership

- Product Owner has final authority over product scope, capital exposure, live enablement, and infrastructure policy.
- E7 has final technical approval/versioning authority over shared contracts.
- Domain producers own production of valid contract instances inside their domain.
- Domain consumers must reject incompatible/invalid contract instances rather than guessing missing semantics.
- A domain agent may not create a permanent parallel shared model merely to avoid requesting a contract change.

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

## Canonical interchange conventions

Unless an approved ADR says otherwise:

- field names use `snake_case`;
- timestamps are RFC 3339 UTC strings ending in `Z` at interchange boundaries;
- internal timezone is UTC;
- price, quantity, notional, margin, fee, PnL, and other financial decimals serialize as base-10 decimal strings, not binary floating-point JSON numbers;
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

- emit only fields/values valid for the declared schema version;
- preserve required units/time semantics;
- not manufacture valid-looking values when source state is unknown;
- expose degraded/unknown state explicitly;
- keep immutable identities immutable.

### Consumers

A consumer must:

- validate the schema version it supports;
- reject or safely degrade on incompatible required semantics;
- never infer LIVE authority from credentials, strategy success, or UI state;
- never treat `UNKNOWN` as healthy;
- never bypass the Strategy -> Risk -> ApprovedTradePlan -> Execution chain.

## GitHub execution policy

GitHub stores these contracts, source code, tests, PRs, issues, documentation, and shared project history only.

Do **not** add or rely on GitHub Actions, GitHub CI, GitHub-hosted runners, GitHub-triggered self-hosted runners, scheduled Actions, or GitHub-based project-code execution for contract verification. Local evidence or `NOT_RUN` is required.

## Security

This is a public repository. Real secrets are forbidden in contract examples, fixtures, logs, screenshots, issues, PR text, and tracked configuration. Use fake or empty values only.