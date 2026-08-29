# Shared Contract Registry

> Authority: E7 Integration / Architecture / System QA / Release Engineer  
> Baseline: `contracts-v0.1`  
> Repository: `jackp803/project-r7`

## Purpose

`contracts/` is the canonical cross-module interface surface for E1–E7.

Domain agents may propose changes, but no E1–E6 implementation may silently redefine a shared concept such as Candle, StrategyDefinition, TradeIntent, ApprovedTradePlan, Order, Fill, Position, BacktestResult, lifecycle state, operational mode, release evidence, funding allocation evidence, lifecycle execution-evidence freshness, protection-trigger validity, external-provider object ownership/reconciliation, bounded live-fire readiness evidence, or runtime-preflight identity/readiness evidence.

The first materialized baseline is:

- [`SHARED_CONTRACTS_V1.md`](./SHARED_CONTRACTS_V1.md)

Compatible executable/evidence object-profile refinements currently registered under that baseline:

- [`EXECUTION_OBJECT_PROFILES_V0_1.md`](./EXECUTION_OBJECT_PROFILES_V0_1.md) — `entry-v0.1` + `base-asset-v0.1`
- [`PROTECTION_OBJECT_PROFILE_V0_1.md`](./PROTECTION_OBJECT_PROFILE_V0_1.md) — `protection-v0.1` actual-fill PositionAction -> protective OrderRequest semantics
- [`PROTECTION_TRIGGER_VALIDITY_PROFILE_V0_1.md`](./PROTECTION_TRIGGER_VALIDITY_PROFILE_V0_1.md) — `protection-trigger-validity-v0.1` current-market/Position-bound protective-trigger geometry evidence, already-breached fail-closed handling, temporal invalidation, and no-blind-retry semantics
- [`CLOSE_TRADE_RESULT_PROFILE_V0_1.md`](./CLOSE_TRADE_RESULT_PROFILE_V0_1.md) — `close-v0.1` + `trade-result-v0.1` + `linear-base-asset-pnl-v0.1` close authority, authoritative flatness, fill-set closure, and canonical TradeResult semantics
- [`FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md`](./FUNDING_ALLOCATION_EVIDENCE_PROFILE_V0_1.md) — `funding-allocation-v0.1` provider-neutral exact-interval funding evidence, completeness, identity, ownership, TradeResult binding, and persistence semantics
- [`POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md`](./POSITION_LIFECYCLE_PROJECTION_PROFILE_V0_1.md) — `position-lifecycle-projection-v0.1` E5-owned lifecycle ordering/identity over unchanged E4 broker Position facts for deterministic persistence/restart
- [`POSITION_LIFECYCLE_PROJECTION_VOCABULARY_V0_1.md`](./POSITION_LIFECYCLE_PROJECTION_VOCABULARY_V0_1.md) — normative exhaustive lifecycle state/event/kind consumer vocabulary for restart-authoritative `position-lifecycle-projection-v0.1`; unknown values fail closed
- [`POSITION_LIFECYCLE_EXECUTION_EVIDENCE_BINDING_V0_1.md`](./POSITION_LIFECYCLE_EXECUTION_EVIDENCE_BINDING_V0_1.md) — `position-lifecycle-execution-binding-v0.1` immutable E5 companion proof binding one lifecycle projection to the exact Position-linked E4 PROTECTION_STOP / POSITION_EXIT / EMERGENCY_EXIT OrderRequest, OrderResult-observation, and Fill snapshot it interpreted; changed durable execution evidence requires fresh E5 interpretation before restart `READY`
- [`EXTERNAL_PROVIDER_OBJECT_OWNERSHIP_RECONCILIATION_PROFILE_V0_1.md`](./EXTERNAL_PROVIDER_OBJECT_OWNERSHIP_RECONCILIATION_PROFILE_V0_1.md) — `external-provider-object-ownership-reconciliation-v0.1` immutable provider-object ownership/reconciliation evidence for positions, orders, fills, protection and unknown provider objects; external/prior-generation/conflicting truth fails closed and adoption is always a separate exact-snapshot policy decision.

Release/readiness evidence profiles registered under E7 authority:

- [`BOUNDED_LIVE_FIRE_READINESS_PROFILE_V0_1.md`](./BOUNDED_LIVE_FIRE_READINESS_PROFILE_V0_1.md) — `bounded-live-fire-readiness-v0.1` fail-closed LF-0..LF-6 exact-revision/evidence gates, P0 failure-prevention closure map, failure-injection/recovery requirements, provider read-only boundary, SHADOW/PAPER prerequisites, and future single-session 10 USDT Product Owner authorization boundary. This profile grants no provider, runtime, mutation, capital, Gate D, or LIVE authority.
- [`RUNTIME_PREFLIGHT_PROFILE_V0_1.md`](./RUNTIME_PREFLIGHT_PROFILE_V0_1.md) — `runtime-preflight-v0.1` provider-neutral exact revision/worktree/mode/config/process/start-generation/heartbeat/supervisor/action-capability/reconciliation/external-consumer/authorization admission evidence for credential-free verification, provider read-only, SHADOW, PAPER, and bounded live-fire runtime roles. `ELIGIBLE` is role-scoped admission evidence only and grants no provider, runtime, mutation, capital, Gate D, or LIVE authority.

## Authority and ownership

- Product Owner has final authority over product scope, capital exposure, live enablement, and infrastructure policy.
- E7 has final technical approval/versioning authority over shared contracts and release/readiness evidence profiles.
- Domain producers own production of valid contract instances inside their domain.
- Domain consumers must reject incompatible/invalid contract instances rather than guessing missing semantics.
- A domain agent may not create a permanent parallel shared model merely to avoid requesting a contract change.

For `external-provider-object-ownership-reconciliation-v0.1` specifically:

- E4 owns normalized provider object observations, provider object identity/snapshot references, provider observation generations, canonical broker order/fill/Position facts, execution lineage it created, ambiguity/reconciliation facts and later provider readback;
- E5 owns Position/risk/lifecycle interpretation and whether new exposure, protection or exit is safe given current reconciliation/ownership state; it does not manufacture provider ownership;
- E6 may persist immutable ownership/reconciliation evidence, validate references/hashes/currentness/conflicts, and project current-vs-historical audit state; it must not infer ownership/lifecycle from persistence order;
- E7 owns the profile, object/ownership/reconciliation/disposition/reason vocabulary, deterministic identity/currentness rules and integration/release interpretation;
- external/manual objects are never silently adopted, detached, ignored or treated as trusted protection by similarity;
- `ADOPTABLE_BY_EXPLICIT_POLICY` is eligibility for a separate exact-snapshot adoption decision, not adoption itself;
- prior-generation project ownership remains provenance only and never automatically transfers current-generation mutation authority;
- unknown/external/conflicting safety-relevant provider truth blocks unsafe new exposure and dependent mutation until reconciliation/convergence;
- FP-11 must classify every observed active protection under this profile before unique-protection registry convergence; FP-10 must consume this evidence plus authoritative Position/fill truth before external/manual flat/reduced lifecycle convergence.

For `runtime-preflight-v0.1` specifically:

- E7 owns the shared evidence schema, runtime-role compatibility, deterministic identity/reason vocabulary, cross-module composition and release interpretation;
- E6 owns durable OperationalMode and recovery/reconciliation-readiness storage facts and may later persist/display sanitized preflight evidence only under a separate task;
- E4/E5 retain ownership of provider/execution and financial-risk/kill-switch semantics; preflight consumes only exact owner-authoritative readiness references and does not reinterpret them;
- external operator/AgentBridge owns approved-local exact-worktree/process/start-generation/single-instance/heartbeat/supervisor/local-action allowlisting and external-consumer compatibility facts where it materially participates;
- PM reviews exact revision/config/evidence generations and cannot transfer historical PASS or grant Product Owner-only authority;
- Product Owner remains final authority for provider/private runtime, bounded live-fire/capital, Gate D and LIVE stages under current governance;
- one runtime role's `ELIGIBLE` result is not transferable to another role;
- catalog registration is not local allowlisting, and local allowlisting is not runtime/Product Owner authority;
- prior-process heartbeat or admission evidence does not survive restart as authority;
- the profile introduces no numeric heartbeat TTL and no new OperationalMode; heartbeat thresholds and any future bounded-live-fire mode representation must be explicitly bound to accepted configuration/governance.

For `bounded-live-fire-readiness-v0.1` specifically:

- E7 owns LF gate definitions, exact revision/evidence compatibility and cross-module release/readiness interpretation;
- PM audits gate evidence and may request a future Product Owner authorization only after prerequisites are accepted; PM cannot grant provider mutation/capital authority;
- Product Owner alone grants any future bounded provider mutation/capital exposure and Gate D/LIVE authority;
- E1/E4/E5/E6 remain authoritative for their existing market, execution, risk/lifecycle and persistence facts respectively;
- AgentBridge/operator remains authoritative for approved-local action allowlisting, exact worktree/process infrastructure, watchdog/process identity and secure local credential injection when later authorized;
- historical evidence from a different revision is not rebound to a newer executable candidate;
- `NOT_RUN`, `PARTIAL`, merge status, docs-only completion and historical PASS are never equivalent to current executable PASS.

For `protection-trigger-validity-v0.1` specifically:

- E1 owns canonical current-market observation, health and freshness facts; it does not judge protection geometry or lifecycle policy;
- E5 owns protection/risk policy, the exact PositionAction authority and the lifecycle/risk response to fail-closed trigger evidence;
- E4 owns provider capability/parameter translation and must reject a provider protection mutation unless exact current shared validity evidence is actionable and still current;
- E6 may persist/display/provenance-check the evidence but must not reinterpret breached/stale evidence into a lifecycle decision;
- E7 owns profile/version/cross-module compatibility;
- V0.1 shared geometry uses canonical `MarketSnapshot.last_price` only as the pre-mutation reference; this does not select an OKX provider trigger-price type;
- unchanged breached evidence never authorizes a blind retry; materially new market/Position/E5 authority is required before reevaluation.

For `funding-allocation-v0.1` specifically:

- E4 owns Paper/provider funding-source acquisition, completeness, normalization, interval allocation and canonical evidence emission;
- E5 validates/consumes canonical funding evidence for TradeResult but does not manufacture source truth;
- E6 persists/replays/audits evidence but does not invent or rewrite funding truth;
- E7 owns profile/version/release semantics.

For `position-lifecycle-projection-v0.1` specifically:

- E4 continues to own the broker Position fact payload and `broker_state_observed_at`; it does not allocate lifecycle order;
- E5 owns `lifecycle_state` plus the lifecycle projection revision/predecessor/event/identity metadata and emits the durability-eligible profiled Position;
- E6 persists/replays/indexes the serialized projection and enforces shared profile/vocabulary/ordering/conflict rules without deriving lifecycle or assigning revisions;
- the exhaustive restart-authoritative lifecycle vocabulary is the E7-owned `POSITION_LIFECYCLE_PROJECTION_VOCABULARY_V0_1.md`; E6 may validate membership but must not copy/import E5 transition semantics;
- E7 owns profile/version/integration/release semantics.

For `position-lifecycle-execution-binding-v0.1` specifically:

- E4 remains authoritative for the canonical Position-linked OrderRequest / OrderResult / Fill facts;
- E5 alone declares which exact execution-evidence snapshot it interpreted for one lifecycle projection and emits the immutable companion binding;
- E6 may persist, recompute the fixed shared evidence snapshot from durable E4 objects, compare exact equality, and fail closed on mismatch; it must not map execution statuses/fills to lifecycle states;
- the companion does not alter `lifecycle_projection_id` and is mandatory only when a consumer requires current Gate B restart-authoritative execution freshness;
- changed/new in-scope durable execution evidence after the binding requires a new E5 TRANSITION or REATTESTATION plus a new companion binding before restart `READY` can be restored.

## Contract status

Every shared contract/profile uses one of these states:

- `DRAFT` — not safe for downstream implementation dependency.
- `BASELINE` — approved minimum contract/profile for current construction; additive compatible refinement is allowed through E7 review.
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
protection-trigger-validity-v0.1
close-v0.1
trade-result-v0.1
linear-base-asset-pnl-v0.1
funding-allocation-v0.1
position-lifecycle-projection-v0.1
position-lifecycle-execution-binding-v0.1
external-provider-object-ownership-reconciliation-v0.1
```

Release/readiness profiles such as `bounded-live-fire-readiness-v0.1` and `runtime-preflight-v0.1` are independently versioned governance/evidence profiles. They do not alter serialized domain-object identities unless a later explicit contract says otherwise.

An object or readiness profile cannot be used to disguise a real breaking change. If existing field meaning, units, authority, required-state behavior, or release authority is changed incompatibly, normal contract/ADR/governance rules apply.

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
4. **Impact** — identify behavioral, persistence, replay, migration, release and authority impact.
5. **Compatibility** — classify the change as compatible or breaking.
6. **ADR** — create/update an ADR when semantics, authority, state machines, runtime architecture or dependency direction materially change.
7. **Contract/profile revision** — update the canonical contract/profile and version.
8. **Tests** — add/adjust relevant local test definitions.
9. **Local verification** — execute only on a local or Product-Owner-approved non-GitHub environment; otherwise record `NOT_RUN` and the exact local command.
10. **Integration** — E7 accepts dependent revisions only after contract/evidence provenance is coherent.

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

- validate the schema version and any required object/profile version it supports;
- reject or safely degrade on incompatible required semantics;
- never infer LIVE authority from credentials, strategy success, UI state, a bounded live-fire session, or prior gate PASS;
- never treat `UNKNOWN` as healthy;
- never infer funding zero from missing/unavailable evidence;
- never infer lifecycle ordering from persistence arrival order, storage timestamps, row IDs or unrelated execution rows;
- never accept unsupported lifecycle state/event/kind as restart-authoritative;
- when Gate B restart execution freshness is required, never claim the latest lifecycle projection is current if its `position-lifecycle-execution-binding-v0.1` companion is missing, conflicting, or differs from the current durable in-scope E4 execution snapshot;
- when a protection mutation requires `protection-trigger-validity-v0.1`, never treat stale/unknown/mismatched/already-breached evidence as actionable and never retry unchanged breached truth merely because time advanced;
- when `external-provider-object-ownership-reconciliation-v0.1` is required, never treat local-state absence, provider-object similarity, prior-generation provenance, stale adoption evidence, or unresolved conflicting ownership as current mutation authority; external/manual objects require explicit reconciliation and any adoption is a separate exact-snapshot policy decision;
- when an LF gate requires exact-revision evidence, never reuse another revision's qualification/provider/runtime result as current PASS;
- when `runtime-preflight-v0.1` is required, never treat another role's result, prior-process heartbeat, catalog-only action registration, stale mode/config/reconciliation evidence, or missing runtime authorization as `ELIGIBLE`;
- never bypass the Strategy -> Risk -> ApprovedTradePlan -> Execution chain.

## GitHub execution policy

GitHub stores these contracts, source code, tests, PRs, issues, documentation, and shared project history only.

Do **not** add or rely on GitHub Actions, GitHub CI, GitHub-hosted runners, GitHub-triggered self-hosted runners, scheduled Actions, or GitHub-based project-code execution for contract or LF-gate verification. Approved local evidence or explicit `NOT_RUN` is required.

## Security

This is a public repository. Real secrets are forbidden in contract examples, fixtures, logs, screenshots, issues, PR text, and tracked configuration. Use fake or empty values only. Future provider-read-only or live-fire credentials must remain local and may not be persisted in LF, runtime-preflight, or external-provider ownership/reconciliation evidence.