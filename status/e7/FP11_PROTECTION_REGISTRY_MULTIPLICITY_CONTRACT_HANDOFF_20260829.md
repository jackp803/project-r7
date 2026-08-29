# E7 FP-11 Protection Registry / Multiplicity Contract Handoff — 2026-08-29

## Task / scope

```text
task_id = E7-20260829-107
profile = protection-registry-multiplicity-v0.1
task_class = CONTRACT / DOCS / STATUS ONLY
executable implementation = NOT_STARTED
project executable verification = NOT_RUN / NOT REQUIRED
```

E7 defined the shared fail-closed FP-11 evidence boundary for reconciling one exact open canonical Position and one exact intended E5 protection lineage against the complete current provider set of active protection objects.

This handoff grants no provider/private access, credential use, mutation, runtime, capital, Gate D, or LIVE authority.

## Profile/version

Canonical artifact:

`contracts/PROTECTION_REGISTRY_MULTIPLICITY_PROFILE_V0_1.md`

Profile identifier:

`protection-registry-multiplicity-v0.1`

Compatibility:

```text
schema_version = contracts-v0.1 / unchanged
classification = ADDITIVE_SHARED_EVIDENCE_PROFILE
external-provider-object-ownership-reconciliation-v0.1 = REQUIRED
protection-v0.1 = REFERENCED / UNCHANGED
protection-trigger-validity-v0.1 = REFERENCED / UNCHANGED
position lifecycle/execution-binding semantics = REFERENCED / UNCHANGED
```

No existing Position, PositionAction, ApprovedTradePlan, OrderRequest, OrderResult, Fill, lifecycle projection, execution binding, provider object, or FP-04 evidence identity is changed.

## Intended-lineage model

The profile defines one `IntendedProtectionLineageReference` for one exact Position. It binds owner-authoritative references rather than copying provider-native fields.

Minimum binding includes:

- exact Position reference/hash/ID and `broker_state_observed_at`;
- exact current Position quantity authority;
- exact E5 `protection-v0.1` `PositionAction.PROTECT` reference/hash/ID;
- exact parent ApprovedTradePlan and RiskDecision lineage where applicable;
- exact E4 `PROTECTION_STOP` OrderRequest/client-order identity once provider materialization exists;
- exact current lifecycle projection and execution binding when lifecycle/restart authority is in scope;
- exact FP-03 trigger-validity evidence only when create/replace is currently being evaluated;
- exact runtime process/start/config/preflight generation when runtime participates;
- exact current FP-04 ownership/reconciliation generation.

A material change to any authority-bearing lineage invalidates prior FP-11 evidence.

## Observed-set model

The profile defines a complete deterministic `ObservedActiveProtectionSet` produced from E4-owned normalized provider truth.

Each active protection object independently binds:

- exact provider object reference;
- exact immutable provider snapshot reference/hash;
- exact current FP-04 ownership evidence reference/hash;
- exact copied FP-04 ownership classification/reconciliation status;
- exact intended-lineage binding result: `EXACT_MATCH | NOT_MATCH | UNKNOWN`;
- exact lineage-comparison evidence reference/hash when known.

The provider set also binds:

- provider/environment/instrument references;
- observation generation/time;
- `COMPLETE | INCOMPLETE | UNKNOWN` coverage;
- `CURRENT | STALE | UNKNOWN` currentness;
- deterministic complete-set hash.

No object may be selected as intended merely because it is newest, oldest, closest in price, the only locally known object, or has a familiar client-ID fragment.

## Exact convergence invariant

The only converged case is:

```text
one exact open Position
+ one exact current intended E5 protection lineage
+ COMPLETE/CURRENT provider protection observation
+ exactly one ACTIVE_PROTECTION provider object
+ current exact FP-04 evidence = KNOWN_OWNED_CURRENT_GENERATION
+ FP-04 reconciliation status = CURRENT_KNOWN_OWNED
+ exact provider-object lineage binding = EXACT_MATCH
+ no additional active protection object
+ no newer/superseding Position/lifecycle/runtime/provider/ownership truth
= CONVERGED_EXACTLY_ONE_INTENDED
```

`KNOWN_OWNED_CURRENT_GENERATION` is necessary but not sufficient. Exact intended-lineage binding is independently required.

## Multiplicity vocabulary

`multiplicity_state`:

- `NO_ACTIVE_PROTECTION_OBSERVED`
- `EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION`
- `MULTIPLE_ACTIVE_PROTECTIONS`
- `ORPHAN_OR_EXTERNAL_PROTECTION_PRESENT`
- `OWNERSHIP_CONFLICT_PRESENT`
- `PROTECTION_SET_STALE`
- `PROTECTION_SET_UNKNOWN`

Only `EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION` may be registry-converged.

## Registry status vocabulary

`registry_status`:

- `CONVERGED_EXACTLY_ONE_INTENDED`
- `MISSING_PROTECTION_REINTERPRETATION_REQUIRED`
- `MULTIPLICITY_CONVERGENCE_REQUIRED`
- `ORPHAN_EXTERNAL_RECONCILIATION_REQUIRED`
- `OWNERSHIP_CONFLICT_MANUAL_REVIEW_REQUIRED`
- `PROVIDER_SET_REFRESH_REQUIRED`
- `LIFECYCLE_PROTECTION_REINTERPRETATION_REQUIRED`
- `UNKNOWN`

There is no partial-green registry state.

## Disposition vocabulary

`required_dispositions` may contain:

- `NO_ACTION_REGISTRY_CONVERGED`
- `E5_PROTECTION_POLICY_REINTERPRETATION_REQUIRED`
- `MULTIPLICITY_CONVERGENCE_REQUIRED`
- `ORPHAN_EXTERNAL_RECONCILIATION_REQUIRED`
- `OWNERSHIP_MANUAL_REVIEW_REQUIRED`
- `REFRESH_PROVIDER_PROTECTION_SET_REQUIRED`
- `BLOCK_NEW_EXPOSURE`
- `BLOCK_PROTECTION_CREATE_REPLACE`
- `BLOCK_UNCERTAIN_PROTECTION_CLEANUP_CANCEL`
- `LIFECYCLE_PROTECTION_STATE_REINTERPRETATION_REQUIRED`
- `FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED`

`NO_ACTION_REGISTRY_CONVERGED` is exclusive.

No disposition authorizes provider create/cancel/replace/cleanup.

## Stable reason vocabulary

The profile defines deterministic reasons covering:

- unsupported profile/schema;
- missing/mismatched/stale Position;
- missing/mismatched/stale intended protection lineage;
- incomplete/stale/unknown provider observation;
- missing/stale/mismatched FP-04 ownership evidence;
- zero active protection;
- multiple active protection;
- external/orphan protection;
- prior-generation protection;
- ownership conflict;
- intended provider-object identity mismatch;
- lifecycle/protection-state contradiction;
- provider set changed since evaluation;
- invalid evidence identity/hash;
- fresh reconciliation/E5 reinterpretation/manual review/convergence required;
- exact single intended protection converged.

The only success reason is:

`EXACT_SINGLE_INTENDED_PROTECTION_CONVERGED`

and it must appear alone with the exact converged state/status/disposition tuple.

## Missing protection semantics

For one open Position, `COMPLETE + CURRENT + zero ACTIVE_PROTECTION` is authoritative missing-provider-protection evidence, not a healthy state.

The profile requires E5 protection/lifecycle reinterpretation and blocks new exposure/protection create-replace until fresh E5 authority and all independent gates are satisfied.

It does not decide whether E5 should create protection, emergency-exit, lock, reconcile, hold, or choose another accepted policy outcome.

Local `OPEN_PROTECTED` / `PROFIT_PROTECTED` may not remain false-green solely from stale local records.

## Multiple/orphan protection semantics

When multiple, external, orphaned, prior-generation, unknown or conflicting objects exist:

- every object remains independently represented;
- every object retains its own FP-04 evidence;
- no newest/oldest/closest-price/client-ID selection;
- no blind cancel-all;
- no blind create-another;
- no assumption extra protection is harmless;
- new exposure remains blocked;
- protection create/replace remains blocked;
- uncertain cleanup/cancel remains blocked;
- later cleanup must bind the exact current provider object snapshot, current FP-04 evidence, current Position/lifecycle truth and separate E5/E4 authority.

## Evidence identity/currentness

Canonical evidence object:

`ProtectionRegistryMultiplicityEvidence`

The object binds:

- exact Position reference/hash;
- exact intended-lineage reference/hash;
- exact provider observation generation/time/coverage/currentness;
- complete deterministic active-protection object set;
- per-object FP-04 evidence IDs/hashes;
- runtime process/start/config generation when applicable;
- current lifecycle projection/execution-binding references;
- multiplicity state;
- registry status;
- deterministic dispositions/reasons;
- evaluation time;
- predecessor/supersession reference;
- deterministic evidence ID.

Complete-set hash changes when any object, provider snapshot, FP-04 evidence, lineage binding, observation generation, coverage or currentness changes.

Evidence ID prefix:

`protregmul_`

A later timestamp alone does not make stale evidence current.

Old evidence is invalidated by newer/different:

- provider protection observation generation;
- active protection object set;
- provider object snapshot;
- FP-04 ownership evidence;
- Position observation;
- lifecycle projection/execution binding;
- intended PositionAction lineage;
- runtime process/start/config generation where applicable.

## Cross-module ownership split

### E4

Owns provider protection observation, exact normalized object references/snapshots, observation generation/completeness/currentness, exact provider-object-to-E4 lineage comparison facts, and future provider-specific create/cancel/query/readback mappings under accepted provider capability authority.

E4 does not choose the intended E5 protection or lifecycle outcome.

### E5

Owns intended protection policy/PositionAction lineage, Position/protection safety interpretation, lifecycle transition/reattestation, and permission/veto for create/replace/emergency/cleanup actions.

E5 does not manufacture provider ownership or provider identifiers.

### E6

Owns immutable persistence, registry/audit projection, and mechanical reference/hash/currentness/conflict validation.

E6 must not select intended protection by persistence order, row ID, timestamp recency, price similarity or client-ID resemblance.

### E7

Owns profile/version, multiplicity/currentness/status/disposition/reason vocabulary, deterministic identity and cross-module/release interpretation.

### PM / Product Owner

PM sequences bounded implementation/evidence review only. Product Owner authority remains separately required for provider/private/runtime/capital stages.

## Exact dependency on FP-04

Every active protection object must carry current accepted FP-04 ownership evidence.

```text
FP-04 KNOWN_OWNED_CURRENT_GENERATION = necessary but not sufficient
FP-04 KNOWN_OWNED_PRIOR_GENERATION = no current mutation authority
FP-04 EXTERNAL_UNTRACKED = not intended protection
FP-04 ADOPTABLE_BY_EXPLICIT_POLICY = not adopted
FP-04 CONFLICTING_OWNERSHIP_EVIDENCE / UNKNOWN = fail closed
```

FP-11 cannot bypass FP-04.

## Exact dependency on FP-03

FP-03 remains create/replace pre-mutation market-geometry evidence only.

```text
FP-03 ACTIONABLE != provider protection exists
FP-03 ACTIONABLE != provider protection unique
FP-03 ACTIONABLE != provider protection owned
FP-03 ACTIONABLE != FP-11 CONVERGED
FP-11 CONVERGED != create/replace authority
```

Both profiles plus independent E5/E4/provider/runtime authority are required by any future mutation path.

## Exact dependency on FP-02

The accepted E4 FP-02 design still leaves OKX provider-native `PROTECTION_STOP` endpoint/trigger/readback/cancel semantics unresolved.

FP-11 therefore binds only E4-supplied abstract provider protection references/snapshots and completeness/currentness evidence. It does not invent provider endpoint, field, trigger-basis, `posSide`, reduce-only, quantity-conversion or cancellation semantics.

## FP-10 downstream dependency

FP-10 external/manual close convergence should later consume FP-11 evidence.

A flat/reduced Position does not silently erase active protection objects. If provider Position is flat but provider protection remains orphaned/multiple/conflicting, terminal protection convergence remains explicit and E5 lifecycle close/reconciliation semantics must consume it.

Provider order status alone remains insufficient for lifecycle closure.

## Future deterministic implementation boundaries

### E4

Smallest boundary: fixture-driven provider protection set normalization, complete-set observation classification, exact object identity/snapshot evidence and E4-created lineage comparison.

### E5

Smallest boundary: exact intended-lineage producer plus policy/lifecycle consumer for non-converged FP-11 evidence.

### E6

Smallest boundary: immutable evidence persistence, set/evidence hash validation, current/historical projection, recovery fail-closed on stale/non-converged registry evidence.

### E7

Smallest boundary: cross-module composition/integration/safety tests after domain producers/consumers exist.

No executable implementation is authorized by E7-107.

## Future credential-free test matrix

At minimum:

- zero observed protection while local state claims protected -> fail closed + E5 reinterpretation;
- exactly one intended current-owned protection -> converged;
- exactly one external protection -> non-converged / no adoption;
- intended current-owned + external extra -> multiplicity conflict;
- two current-owned objects for one intended lineage -> multiplicity conflict;
- prior-generation object -> no current mutation authority;
- incomplete/stale observation set -> reject;
- changed provider set/snapshot -> old evidence invalid;
- changed FP-04 evidence -> old evidence invalid;
- changed Position/lifecycle/intended lineage -> old evidence invalid;
- current-owned but lineage mismatch -> non-converged;
- exact lineage match without current ownership -> non-converged;
- blind cancel-all/create-another receives no authority;
- unsafe registry blocks new exposure;
- false-green `OPEN_PROTECTED`/`PROFIT_PROTECTED` routes to E5 reinterpretation;
- flat Position plus orphan/multiple protection routes to FP-10 convergence;
- deterministic set/evidence identity changes on material input change;
- no provider/network/credential access required.

Any future executable project changes require fresh approved-local credential-free qualification on the exact integrated candidate.

## LF relationship

### LF-2

FP-11 design is defined by this task, but executable closure remains `NOT_STARTED`. LF-2 remains partial until executable implementation plus accepted exact-revision local evidence exists.

### LF-3

Future failure-injection must cover missing, duplicate, orphan, external, prior-generation, incomplete, stale, ownership-conflict, lifecycle contradiction and restart-currentness cases.

### LF-4

Future separately authorized read-only provider evidence must validate real provider protection enumeration/completeness/identity semantics. Historical provider evidence is not rebound.

### LF-5

Future SHADOW/recovery protected-position claims must consume current FP-11 evidence where provider protection truth is relevant. Runtime authority remains separate.

### LF-6

Future bounded live-fire cannot rely on stale/partial/external/ambiguous registry truth and remains Product Owner-only authority after prior gates are accepted.

## Current unresolved provider-specific facts

Still unresolved and intentionally not invented:

- exact OKX endpoint(s) covering all active protection mechanisms;
- proof of complete provider protection enumeration;
- stable OKX protection object identity semantics;
- exact create/readback/cancel field sets;
- trigger/order-algo mapping and trigger basis;
- position-mode-specific protection semantics;
- reduce-only semantics;
- contract quantity conversion/rounding;
- handling of externally/manual-created conditional objects;
- behavior of protection objects after Position becomes flat.

These remain E4/provider-capability implementation/verification dependencies.

## ADR decision

`NO NEW ADR REQUIRED`.

Reason: FP-11 is an additive shared evidence profile within accepted E4 provider truth -> FP-04 ownership -> E5 lifecycle/risk -> E6 persistence authority. It does not introduce a new architecture direction or change an existing state-machine owner.

## Recommended next Worker tasks — recommendation only

Do not treat these recommendations as issued tasks.

1. E4 bounded executable implementation for provider-neutral active-protection set normalization/lineage evidence using deterministic fixtures only, after PM dispatch.
2. E5 bounded executable intended-lineage and non-converged policy consumer under this profile, after PM dispatch.
3. E6 bounded immutable registry persistence/currentness consumer, after PM dispatch.
4. E7 integration/safety composition after those domain changes are available.
5. FP-10 contract/implementation may then consume accepted FP-04 + FP-11 and later FP-05 semantics as sequenced by PM.

## Preserved blocker / authority state

```text
LF-0 exact-revision infrastructure = BLOCKED / UNCHANGED
candidate revision = 9462b2594675b2e28388f55a2af189100b7cbdfc
exact clean candidate = NOT_ESTABLISHED
FP-03 combined qualification = NOT_RUN / NOT_PASS
provider-facing verification on current candidate = NOT_RUN / NOT_INFERRED
project executable verification = NOT_RUN / NOT REQUIRED
Local Job Request = NONE
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order submit/cancel/amend/close = 0
SHADOW/PAPER = NOT_STARTED / NOT_AUTHORIZED
10U live-fire = NOT_AUTHORIZED
capital exposure = NONE
Gate D / LIVE = BLOCKED / UNAUTHORIZED
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

`NOT_RUN` is not executable PASS. This docs-only task does not resolve the active `PREPARE_EXACT_REVISION` local allowlist/infrastructure blocker.
