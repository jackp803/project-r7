# Protection Registry / Multiplicity Profile — V0.1

> Parent contract set: `contracts-v0.1`  
> Required ownership companion: `external-provider-object-ownership-reconciliation-v0.1`  
> Related profiles: `protection-v0.1`, `protection-trigger-validity-v0.1`, `position-lifecycle-projection-v0.1`, `position-lifecycle-execution-binding-v0.1`  
> Profile identifier: `protection-registry-multiplicity-v0.1`  
> Status: `BASELINE`  
> Technical authority: E7 Integration / Architecture / System QA / Release Engineer  
> Decision task: `E7-20260829-107`

## 1. Purpose

`protection-registry-multiplicity-v0.1` defines the provider-neutral, fail-closed evidence required to answer one narrow safety question:

> For one exact open canonical Position and one exact currently intended E5 protection lineage, does current complete provider truth contain exactly one active protection object that is both current-generation-owned and exactly bound to that intended lineage, with no extra active protection object whose ownership or purpose is unresolved?

The profile closes the FP-11 contract/design gap only.

It prevents these unsafe equivalences:

```text
local OPEN_PROTECTED record != provider protection currently exists
one visible protection object != intended protection
one familiar client identity != ownership proof
current-generation ownership != intended-lineage match
intended-lineage match != uniqueness
latest/newest/closest-price object != selected intended object
multiple protection objects != harmless redundancy
zero protection objects != permission to create another
```

The profile composes existing authority rather than replacing it:

- E4 owns provider protection observation, normalized provider object identity/snapshot facts, observation generation/completeness/currentness facts, provider readback, and later provider-specific create/cancel/query translation under accepted capability authority;
- E5 owns the intended protection policy/`PositionAction.PROTECT` lineage, lifecycle/risk interpretation, and whether missing/conflicting protection requires create/replace/emergency exit/lock or another policy response;
- E6 owns immutable persistence, registry/audit projection, and mechanical reference/hash/currentness validation;
- E7 owns this profile, deterministic multiplicity/currentness/status/disposition/reason vocabulary, and cross-module/release interpretation;
- FP-04 owns per-provider-object ownership classification evidence;
- PM sequences implementation/evidence review;
- Product Owner remains final authority for provider/private/runtime/capital stages under current governance.

This profile grants no provider/private API access, credential use, provider/account mutation, cancel/create/replace action, SHADOW/PAPER runtime, bounded live-fire authority, Gate D, or LIVE authority.

## 2. Compatibility decision

Classification:

```text
ADDITIVE_SHARED_EVIDENCE_PROFILE
schema_version = contracts-v0.1 / unchanged
protection-v0.1 = referenced / unchanged
protection-trigger-validity-v0.1 = referenced / unchanged
external-provider-object-ownership-reconciliation-v0.1 = required / unchanged
position-lifecycle profiles = referenced / unchanged
```

No existing Position, PositionAction, ApprovedTradePlan, OrderRequest, OrderResult, Fill, lifecycle projection, lifecycle execution binding, provider object, or FP-04 ownership object changes identity or meaning.

No new ADR is required for V0.1 because the accepted architecture already separates:

```text
E4 provider truth
-> FP-04 provider-object ownership evidence
-> FP-11 multiplicity/currentness evidence
-> E5 lifecycle/protection-policy interpretation
-> E6 durable projection/recovery
```

The profile makes that already-required convergence boundary explicit; it does not change authority direction, lifecycle transitions, or provider architecture.

## 3. Scope

V0.1 applies to one canonical open Position and the provider-side set of active protection objects relevant to that Position.

The only provider object class directly admitted into the observed protection set is the FP-04 class:

```text
ACTIVE_PROTECTION
```

Other provider object classes may be referenced as supporting owner-authoritative evidence, but they are not silently reclassified as active protection by FP-11.

The profile is provider-neutral. It defines no:

- OKX endpoint;
- provider order-algo type;
- trigger field name;
- `posSide` rule;
- provider reduce-only spelling;
- provider contract-count semantics;
- provider cancellation field set;
- provider readback identifier format.

Those remain E4/provider-capability facts.

## 4. Canonical concepts

### 4.1 Intended protection lineage

Canonical concept:

```text
IntendedProtectionLineageReference
```

It identifies one exact logical protection intent for one exact Position. It is a reference envelope, not a duplicate of E4/E5 domain objects.

Required fields:

- `position_ref` — exact canonical Position or lifecycle-projection reference;
- `position_hash` — hash of that exact authoritative Position material;
- `position_id`;
- `position_observed_at` — exact E4 broker-state observation anchor consumed by the intended protection authority;
- `position_side` — exact canonical side;
- `position_quantity_ref` — exact owner-authoritative quantity evidence reference;
- `position_action_ref` — exact E5 `protection-v0.1` `PositionAction.PROTECT` reference;
- `position_action_hash`;
- `position_action_id`;
- `approved_trade_plan_ref` — exact parent ApprovedTradePlan reference;
- `approved_trade_plan_hash`;
- `risk_decision_ref` — exact parent RiskDecision reference when required by the accepted protection lineage;
- `protection_order_request_ref` — exact E4 `PROTECTION_STOP` OrderRequest reference if provider materialization has occurred, otherwise `null` only before materialization;
- `protection_order_request_hash` — matching hash or `null` under the same rule;
- `client_order_identity_ref` — exact E4-issued logical/provider identity binding if one exists, otherwise `null` before provider materialization;
- `lifecycle_projection_ref` — exact current E5 lifecycle projection reference when lifecycle authority is in scope, otherwise `null` only for an explicitly pre-lifecycle deterministic fixture;
- `lifecycle_execution_binding_ref` — exact current execution-binding reference when restart-authoritative lifecycle freshness is required, otherwise `null` only when not applicable;
- `trigger_validity_ref` — exact current `protection-trigger-validity-v0.1` evidence reference only when a create/replace action is currently being evaluated, otherwise `null`;
- `runtime_preflight_ref` — exact current runtime-preflight reference when a runtime materially participates, otherwise `null` only for non-runtime deterministic evaluation;
- `runtime_process_instance_id` — exact current process identity when applicable;
- `runtime_process_start_generation_id` — exact process-start generation when applicable;
- `runtime_config_generation_id` — exact behavior-affecting runtime config generation when applicable;
- `ownership_reconciliation_generation_ref` — exact FP-04 generation/reference used to classify the observed set.

Rules:

1. The intended lineage comes from E5/E4 owner-authoritative objects; FP-11 does not invent a new protection intent.
2. A changed Position observation, quantity authority, PositionAction, parent plan, OrderRequest, lifecycle projection/binding, runtime generation, or applicable trigger-validity evidence invalidates an older intended-lineage reference.
3. `trigger_validity_ref` proves only pre-mutation geometry when create/replace is being considered. It does not prove provider protection existence, uniqueness, ownership, or active status.
4. A missing provider materialization reference before the first provider create is valid only as a pre-create lineage state; it cannot by itself satisfy registry convergence.

### 4.2 Observed provider protection set

Canonical concept:

```text
ObservedActiveProtectionSet
```

It represents the complete current E4-normalized set of provider objects classified as `ACTIVE_PROTECTION` for the exact Position/instrument observation boundary.

Required fields:

- `provider_identity_ref`;
- `provider_identity_hash`;
- `canonical_symbol`;
- `provider_instrument_ref`;
- `provider_observation_generation_id`;
- `provider_observed_at`;
- `provider_received_at`;
- `observation_coverage_status` — `COMPLETE | INCOMPLETE | UNKNOWN`;
- `set_currentness_status` — `CURRENT | STALE | UNKNOWN`;
- `objects` — deterministic sequence of `ObservedActiveProtectionEntry`;
- `observed_set_hash` — hash from section 12.

No numeric provider-set freshness threshold is invented by V0.1. E4 or an accepted behavior-affecting observation policy owns the threshold/classification. Missing policy/currentness evidence fails closed.

### 4.3 Per-object observed entry

Each `ObservedActiveProtectionEntry` contains:

- `provider_object_ref` — exact E4 stable sanitized object reference;
- `provider_snapshot_ref` — exact immutable E4 normalized snapshot reference;
- `provider_snapshot_hash`;
- `provider_object_observed_at`;
- `ownership_evidence_ref` — exact current FP-04 `ExternalProviderObjectOwnershipEvidence` reference;
- `ownership_evidence_hash`;
- `ownership_classification` — copied exact FP-04 classification;
- `ownership_reconciliation_status` — copied exact FP-04 reconciliation status;
- `intended_lineage_binding_status` — `EXACT_MATCH | NOT_MATCH | UNKNOWN`;
- `intended_lineage_binding_ref` — exact E4/E5 lineage-comparison evidence reference when `EXACT_MATCH` or `NOT_MATCH`; `null` only when `UNKNOWN`;
- `intended_lineage_binding_hash` — matching hash or `null` under the same rule.

`intended_lineage_binding_status` is a mechanical exact-binding result. It may prove whether the provider object identity/snapshot is tied to the one intended E4/E5 protection lineage. It does not choose lifecycle policy and does not grant mutation authority.

Entries are sorted lexicographically by:

```text
(provider_object_ref, provider_snapshot_hash, ownership_evidence_ref)
```

before set hashing and evidence serialization.

## 5. Multiplicity/currentness vocabulary

`multiplicity_state` is exactly one of:

- `NO_ACTIVE_PROTECTION_OBSERVED`
- `EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION`
- `MULTIPLE_ACTIVE_PROTECTIONS`
- `ORPHAN_OR_EXTERNAL_PROTECTION_PRESENT`
- `OWNERSHIP_CONFLICT_PRESENT`
- `PROTECTION_SET_STALE`
- `PROTECTION_SET_UNKNOWN`

### 5.1 `NO_ACTIVE_PROTECTION_OBSERVED`

Allowed only when provider observation coverage is complete/current and `objects=[]`.

This is not a healthy protected state for an open Position. It requires E5 protection/lifecycle reinterpretation.

### 5.2 `EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION`

Allowed only when all section 8 convergence requirements pass.

This is the only multiplicity state that may pair with a converged registry status.

### 5.3 `MULTIPLE_ACTIVE_PROTECTIONS`

Used when two or more active protection objects exist in a complete/current provider set, including two objects that both appear tied to the same intended lineage.

Multiplicity is fail closed. No automatic winner selection is permitted.

### 5.4 `ORPHAN_OR_EXTERNAL_PROTECTION_PRESENT`

Used when one or more observed active protection objects are not exact current-generation intended-lineage objects and the evidence is otherwise non-conflicting enough to identify them as external, prior-generation, orphan/untracked, manual-review, or not-matching objects.

This state remains fail closed even if exactly one intended current-owned object also exists.

### 5.5 `OWNERSHIP_CONFLICT_PRESENT`

Used when any observed object carries FP-04 `CONFLICTING_OWNERSHIP_EVIDENCE`, two local lineages claim one object, one intended lineage maps to multiple objects where multiplicity is not permitted, or exact lineage/object identity cannot be made conflict-free.

### 5.6 `PROTECTION_SET_STALE`

Used when the provider protection observation set or any required per-object ownership/lineage evidence is known stale/superseded.

### 5.7 `PROTECTION_SET_UNKNOWN`

Used when observation coverage, currentness, object purpose, required ownership evidence, or exact intended-lineage binding cannot be established safely.

Unknown is never converted into an empty or exactly-one set.

## 6. Registry status vocabulary

`registry_status` is exactly one of:

- `CONVERGED_EXACTLY_ONE_INTENDED`
- `MISSING_PROTECTION_REINTERPRETATION_REQUIRED`
- `MULTIPLICITY_CONVERGENCE_REQUIRED`
- `ORPHAN_EXTERNAL_RECONCILIATION_REQUIRED`
- `OWNERSHIP_CONFLICT_MANUAL_REVIEW_REQUIRED`
- `PROVIDER_SET_REFRESH_REQUIRED`
- `LIFECYCLE_PROTECTION_REINTERPRETATION_REQUIRED`
- `UNKNOWN`

Only:

```text
multiplicity_state = EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION
registry_status = CONVERGED_EXACTLY_ONE_INTENDED
```

may represent converged registry truth.

Every other status is non-converged and fail closed for any operation that assumes one safe unique protection.

## 7. Required disposition vocabulary

`required_dispositions` is a deterministic sorted sequence containing one or more of:

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

Rules:

1. `NO_ACTION_REGISTRY_CONVERGED` is exclusive.
2. A disposition is evidence/routing state only; it never authorizes provider create/cancel/replace/cleanup.
3. Unsafe registry states include `BLOCK_NEW_EXPOSURE` and `BLOCK_PROTECTION_CREATE_REPLACE` unless a future accepted profile explicitly defines a narrower emergency path with independent exact authority.
4. Uncertain provider-object authority requires `BLOCK_UNCERTAIN_PROTECTION_CLEANUP_CANCEL`; blind cancel-all is forbidden.
5. After provider Position becomes terminal/flat, unresolved active protection objects route to FP-10 via `FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED`; flat Position truth does not silently erase orphan protection.

## 8. Exact one-intended-protection invariant

For one canonical open Position and one currently intended E5 protection lineage, registry convergence requires all of the following simultaneously:

1. the exact Position/intended-lineage references are current and conflict-free;
2. provider observation coverage is `COMPLETE`;
3. provider set currentness is `CURRENT`;
4. the observed active protection set contains exactly one entry;
5. that entry's FP-04 ownership evidence is current, exact, hash-valid, and bound to the same provider snapshot;
6. that entry's `ownership_classification` is exactly `KNOWN_OWNED_CURRENT_GENERATION`;
7. its FP-04 `ownership_reconciliation_status` is exactly `CURRENT_KNOWN_OWNED`;
8. its `intended_lineage_binding_status` is exactly `EXACT_MATCH`;
9. the provider object/snapshot identity exactly binds to the one intended protection lineage;
10. no additional active protection object exists in the complete observation set;
11. no newer provider snapshot, FP-04 ownership evidence, Position observation, lifecycle projection/binding, or runtime/config generation has superseded the evidence before evaluation completes;
12. evidence identity/hash validation succeeds.

Canonical invariant:

```text
For one canonical open Position and one currently intended E5 protection lineage,
registry convergence requires exactly one observed ACTIVE_PROTECTION provider object
whose current FP-04 evidence proves KNOWN_OWNED_CURRENT_GENERATION and whose exact
lineage/object identity binds to the intended protection lineage.
```

If any item fails, `CONVERGED_EXACTLY_ONE_INTENDED` is forbidden.

### 8.1 Explicit rejected cases

The profile rejects all of the following:

- zero provider protection objects while local lifecycle claims `OPEN_PROTECTED` or `PROFIT_PROTECTED`;
- two or more provider protection objects matching the same intended lineage;
- one intended current-owned object plus any additional active object, including external, prior-generation, unknown, conflicting, or apparently unrelated protection;
- exactly one external object treated as intended by symbol/side/price/client-ID similarity;
- exactly one prior-generation object treated as current mutation authority;
- stale provider object snapshot or stale FP-04 evidence;
- incomplete provider observation coverage treated as an empty/single set;
- an object that is current-generation-owned but does not exactly match the intended protection lineage;
- an object that exactly matches a lineage reference but lacks current FP-04 ownership proof.

## 9. Missing-protection boundary

For an open Position, a complete/current provider set with zero active protection objects yields:

```text
multiplicity_state = NO_ACTIVE_PROTECTION_OBSERVED
registry_status = MISSING_PROTECTION_REINTERPRETATION_REQUIRED
```

Required dispositions include:

- `E5_PROTECTION_POLICY_REINTERPRETATION_REQUIRED`;
- `BLOCK_NEW_EXPOSURE`;
- `BLOCK_PROTECTION_CREATE_REPLACE` until E5 produces fresh exact policy/action authority and all independent pre-mutation gates are satisfied;
- `LIFECYCLE_PROTECTION_STATE_REINTERPRETATION_REQUIRED` when local lifecycle claims `OPEN_PROTECTED` or `PROFIT_PROTECTED`.

The profile does not decide whether E5 should:

- issue a fresh `PROTECT` action;
- issue `EMERGENCY_EXIT`;
- enter reconciliation/lock;
- hold;
- take another future approved protection action.

Local protected lifecycle state must not remain false-green solely because durable local records still say protection was previously verified.

## 10. Multiple/orphan/external/prior-generation boundary

When multiple, external, orphaned, prior-generation, unknown, or conflicting active protection objects are observed:

- every provider object remains independently represented in the complete set;
- every object retains its exact current FP-04 ownership evidence;
- no newest/oldest/closest-price/client-ID heuristic selects an intended object;
- no blind cancel-all is permitted;
- no blind create-another is permitted;
- no extra protection is assumed harmless;
- new exposure is blocked;
- protection create/replace is blocked until convergence and fresh E5 policy authority exist;
- cleanup/cancel remains blocked when the target object's ownership/lineage authority is uncertain;
- a later cleanup action must bind the exact current provider object snapshot, exact current FP-04 ownership evidence, current Position/lifecycle truth, and separate E5/E4 action/capability authority.

An FP-04 `ADOPTABLE_BY_EXPLICIT_POLICY` object is still not current intended protection until the separate adoption decision exists and the resulting current lineage is re-evaluated under this profile.

## 11. Canonical evidence object

Canonical shared object:

```text
ProtectionRegistryMultiplicityEvidence
```

Required fields:

- `schema_version` — exactly `contracts-v0.1`;
- `protection_registry_multiplicity_profile_version` — exactly `protection-registry-multiplicity-v0.1`;
- `protection_registry_evidence_id` — deterministic identity from section 13;
- `position_id`;
- `position_ref`;
- `position_hash`;
- `position_observed_at`;
- `intended_protection_lineage` — exact structure from section 4.1;
- `intended_protection_lineage_hash` — hash of the canonical intended-lineage envelope;
- `provider_identity_ref`;
- `provider_instrument_ref`;
- `provider_observation_generation_id`;
- `provider_observed_at`;
- `provider_received_at`;
- `observation_coverage_status` — `COMPLETE | INCOMPLETE | UNKNOWN`;
- `provider_set_currentness_status` — `CURRENT | STALE | UNKNOWN`;
- `observed_active_protection_objects` — sorted sequence from section 4.3;
- `observed_active_protection_set_hash` — deterministic hash from section 12;
- `active_protection_count` — exact sequence length;
- `runtime_preflight_ref` — exact current runtime-preflight reference when runtime participates, otherwise `null` only for non-runtime deterministic evaluation;
- `runtime_process_instance_id` — exact current runtime identity when applicable;
- `runtime_process_start_generation_id` — exact current start generation when applicable;
- `runtime_config_generation_id` — exact current config generation when applicable;
- `lifecycle_projection_ref` — exact current E5 lifecycle projection when lifecycle state is in scope;
- `lifecycle_execution_binding_ref` — exact current lifecycle execution binding when restart-authoritative freshness is required;
- `multiplicity_state` — section 5 value;
- `registry_status` — section 6 value;
- `required_dispositions` — section 7 deterministic sequence;
- `reason_codes` — section 14 deterministic sequence;
- `supersedes_registry_evidence_id` — immediately prior evidence ID for the same Position/intended-lineage generation when known, otherwise `null`;
- `evaluated_at` — RFC 3339 UTC time captured after all bound provider/ownership/Position/lifecycle evidence has been accepted.

No credentials, account secret, raw provider payload, provider signature/token, local filesystem path, shell command, exact account balance, or unnecessary provider-native field belongs in this object.

## 12. Complete provider-set hash

`observed_active_protection_set_hash` is computed over the complete normalized current set:

```json
{
  "provider_identity_ref": "<ref>",
  "provider_instrument_ref": "<ref>",
  "provider_observation_generation_id": "<generation>",
  "provider_observed_at": "<UTC Z>",
  "observation_coverage_status": "COMPLETE",
  "provider_set_currentness_status": "CURRENT",
  "objects": [
    {
      "provider_object_ref": "...",
      "provider_snapshot_ref": "...",
      "provider_snapshot_hash": "sha256:...",
      "ownership_evidence_ref": "...",
      "ownership_evidence_hash": "sha256:...",
      "ownership_classification": "...",
      "ownership_reconciliation_status": "...",
      "intended_lineage_binding_status": "...",
      "intended_lineage_binding_ref": "...",
      "intended_lineage_binding_hash": "sha256:..."
    }
  ]
}
```

Algorithm:

1. normalize every entry using the exact shared field set;
2. sort entries lexicographically by `(provider_object_ref, provider_snapshot_hash, ownership_evidence_ref)`;
3. serialize UTF-8 canonical JSON with sorted object keys and compact separators;
4. compute SHA-256;
5. prefix with `sha256:`.

Adding, removing, replacing, or changing any active protection object, provider snapshot, ownership evidence, lineage-binding result, coverage/currentness classification, or observation generation changes the set hash.

A later timestamp alone does not make an unchanged stale set current.

## 13. Evidence identity and immutability

`protection_registry_evidence_id` is deterministic over the complete canonical evidence payload except the ID field itself.

Algorithm:

1. remove `protection_registry_evidence_id`;
2. serialize the complete remaining evidence as canonical UTF-8 JSON with lexicographically sorted keys and compact separators;
3. preserve financial decimals inside referenced owner-authoritative objects rather than reserializing them here;
4. compute SHA-256;
5. prefix the lowercase hex digest with:

```text
protregmul_
```

Rules:

```text
same exact evidence payload -> same ID
same ID + changed payload -> conflict/corrupt
changed provider set -> new ID
changed FP-04 ownership evidence -> new ID
changed Position/lifecycle/intended lineage -> new ID
changed runtime/process/config generation -> new ID when runtime participates
```

The evidence is immutable and must never be rewritten to claim a later provider observation or ownership decision.

## 14. Stable fail-closed reason vocabulary

Reason codes are emitted in this deterministic order when applicable:

1. `PROTECTION_REGISTRY_PROFILE_UNSUPPORTED`
2. `POSITION_REFERENCE_MISSING_OR_MISMATCHED`
3. `POSITION_EVIDENCE_STALE`
4. `INTENDED_PROTECTION_LINEAGE_MISSING`
5. `INTENDED_PROTECTION_LINEAGE_MISMATCH`
6. `INTENDED_PROTECTION_LINEAGE_STALE`
7. `PROVIDER_PROTECTION_OBSERVATION_INCOMPLETE`
8. `PROVIDER_PROTECTION_SET_STALE`
9. `PROVIDER_PROTECTION_SET_UNKNOWN`
10. `PROTECTION_OWNERSHIP_EVIDENCE_MISSING`
11. `PROTECTION_OWNERSHIP_EVIDENCE_STALE`
12. `PROTECTION_OWNERSHIP_EVIDENCE_MISMATCH`
13. `NO_ACTIVE_PROTECTION_OBSERVED`
14. `MULTIPLE_ACTIVE_PROTECTIONS_OBSERVED`
15. `EXTERNAL_OR_ORPHAN_PROTECTION_PRESENT`
16. `PRIOR_GENERATION_PROTECTION_PRESENT`
17. `PROTECTION_OWNERSHIP_CONFLICT_PRESENT`
18. `INTENDED_PROTECTION_OBJECT_IDENTITY_MISMATCH`
19. `LIFECYCLE_PROTECTION_STATE_CONTRADICTION`
20. `PROVIDER_PROTECTION_SET_CHANGED_SINCE_EVALUATION`
21. `PROTECTION_REGISTRY_EVIDENCE_IDENTITY_INVALID`
22. `FRESH_PROTECTION_RECONCILIATION_REQUIRED`
23. `E5_PROTECTION_REINTERPRETATION_REQUIRED`
24. `PROTECTION_MULTIPLICITY_CONVERGENCE_REQUIRED`
25. `PROTECTION_OWNERSHIP_MANUAL_REVIEW_REQUIRED`
26. `EXACT_SINGLE_INTENDED_PROTECTION_CONVERGED`

`EXACT_SINGLE_INTENDED_PROTECTION_CONVERGED` is the only success reason and appears alone only when:

```text
multiplicity_state = EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION
registry_status = CONVERGED_EXACTLY_ONE_INTENDED
required_dispositions = [NO_ACTION_REGISTRY_CONVERGED]
```

Unknown required reason codes under a V0.1-required consumer fail closed.

## 15. Deterministic state derivation

Evaluation precedence is fail closed and deterministic.

### 15.1 Input/currentness failures first

If schema/profile, Position, intended-lineage, provider observation coverage/currentness, runtime generation, lifecycle references, or evidence hashes are missing/invalid/stale, emit the applicable stale/unknown/conflict state before counting a set as healthy.

`INCOMPLETE` or `UNKNOWN` observation coverage never becomes `NO_ACTIVE_PROTECTION_OBSERVED` merely because zero entries were returned.

### 15.2 Ownership/conflict evaluation

For a complete/current set, validate every entry's FP-04 evidence and lineage binding.

Any ownership conflict produces:

```text
multiplicity_state = OWNERSHIP_CONFLICT_PRESENT
registry_status = OWNERSHIP_CONFLICT_MANUAL_REVIEW_REQUIRED
```

### 15.3 Count and object-class evaluation

For a complete/current, conflict-free set:

- zero entries -> `NO_ACTIVE_PROTECTION_OBSERVED`;
- two or more entries -> `MULTIPLE_ACTIVE_PROTECTIONS` unless a stronger ownership-conflict state already applies;
- one entry that is external/prior-generation/not-matching/manual-review/adoptable/unknown -> `ORPHAN_OR_EXTERNAL_PROTECTION_PRESENT` or `PROTECTION_SET_UNKNOWN`, whichever is more conservative and accurate;
- one entry that is exact current-owned but not `EXACT_MATCH` -> not converged;
- exactly one entry satisfying all section 8 requirements -> `EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION`.

A set with one intended object plus one external object is `MULTIPLE_ACTIVE_PROTECTIONS`, with orphan/external reasons/dispositions also emitted. It is never partially green.

## 16. Temporal ordering and currentness

The deterministic evidence sequence is:

```text
1. obtain exact current Position/lifecycle authority
2. obtain exact current intended E5 protection lineage
3. obtain complete/current E4 provider ACTIVE_PROTECTION set
4. obtain current FP-04 ownership evidence for every observed object
5. mechanically bind each observed object to the intended lineage
6. capture evaluated_at
7. derive multiplicity/registry status and immutable evidence
8. immediately before any dependent action, reject if newer relevant truth is known
```

Required ordering:

```text
evaluated_at >= provider_received_at
evaluated_at >= position_observed_at
evaluated_at >= each bound ownership-evidence evaluated_at
```

When lifecycle projection/runtime evidence participates, `evaluated_at` must also be at or after those accepted evidence boundaries.

The old registry evidence becomes non-current if any of the following is known before a dependent action:

- newer provider protection observation generation;
- changed active protection set;
- changed provider object snapshot;
- newer/different FP-04 ownership evidence for any object;
- newer Position broker observation;
- newer E5 lifecycle projection or lifecycle execution binding;
- new/changed intended `PositionAction.PROTECT` lineage;
- changed runtime process/start/config generation where runtime participates;
- newly discovered provider object that makes prior observation coverage incomplete.

A later clock time by itself does not refresh evidence.

## 17. Lifecycle/protection-state boundary

FP-11 never emits an E5 `PositionEvent` or lifecycle state.

If local lifecycle says:

```text
OPEN_PROTECTED
or
PROFIT_PROTECTED
```

but current registry evidence is not converged, the evidence must include:

```text
LIFECYCLE_PROTECTION_STATE_REINTERPRETATION_REQUIRED
```

E5 decides whether the authoritative next policy/lifecycle response is `PROTECTION_LOST`, `STATE_UNKNOWN`, `EMERGENCY`, a re-attestation, or another accepted outcome.

Conversely, registry convergence does not itself move `OPEN_UNPROTECTED -> OPEN_PROTECTED`; E5 must still consume the exact verified provider/execution evidence under its existing lifecycle authority.

## 18. Dependency on FP-04

Every observed active protection object must carry current accepted `external-provider-object-ownership-reconciliation-v0.1` evidence.

FP-11 cannot bypass FP-04 classification.

Rules:

```text
KNOWN_OWNED_CURRENT_GENERATION = necessary for the one intended object
KNOWN_OWNED_CURRENT_GENERATION != sufficient without exact intended-lineage match
KNOWN_OWNED_PRIOR_GENERATION != current mutation authority
EXTERNAL_UNTRACKED != intended protection
ADOPTABLE_BY_EXPLICIT_POLICY != adopted
CONFLICTING_OWNERSHIP_EVIDENCE / UNKNOWN = fail closed
```

A future explicit adoption decision may cause FP-04 to emit new current ownership evidence. FP-11 must then evaluate the new exact provider snapshot/current lineage; it never rewrites historical evidence.

## 19. Dependency on FP-03

`protection-trigger-validity-v0.1` remains a create/replace pre-mutation geometry profile.

It does not prove:

- a provider protection object exists;
- the object is active;
- the object is unique;
- the object is project-owned;
- the object is current-generation-owned;
- the object matches the intended provider lineage.

Therefore:

```text
FP-03 ACTIONABLE != FP-11 CONVERGED
FP-11 CONVERGED != create/replace authority
```

A future create/replace path must satisfy both profiles plus E5/E4 provider capability/authorization requirements.

## 20. Dependency on FP-02

The accepted E4 `okx-swap-action-role-capability-v0.1` design leaves provider-native `PROTECTION_STOP` endpoint/trigger/readback/cancel semantics unresolved and fail closed.

FP-11 therefore consumes only E4-supplied abstract provider protection object references/snapshots and observation completeness/currentness evidence.

It does not infer or approve:

- OKX trigger/order fields;
- provider trigger price type;
- protection endpoint;
- cancellation endpoint/fields;
- `posSide`;
- provider reduce-only behavior;
- provider contract quantity conversion;
- provider object identity extraction rules.

Those require accepted E4 implementation/provider evidence.

## 21. Downstream dependency for FP-10

FP-10 external/manual close lifecycle convergence should consume current FP-11 evidence.

When provider Position becomes reduced or flat, FP-10 must not treat the lifecycle as fully converged merely because exposure is zero if active provider protection objects remain unresolved.

At minimum:

- flat/reduced Position truth remains E4 provider truth;
- E5 owns lifecycle close/reconciliation interpretation;
- FP-11 identifies whether intended protection is absent/converged/orphaned/multiple/conflicting;
- unresolved active protection after flatness requires explicit terminal protection convergence evidence rather than silent deletion/ignore;
- provider order status alone remains insufficient to close lifecycle.

FP-11 does not implement FP-10.

## 22. Cross-module ownership split

### E4

E4 owns:

- provider protection observation;
- exact provider object identifiers/references;
- immutable normalized provider snapshots;
- provider observation generation/time;
- observation completeness/currentness classification under accepted provider policy;
- exact provider-object-to-E4 execution-lineage comparison facts;
- future provider create/cancel/query/readback translation only under accepted FP-02 capability authority.

E4 does not choose E5 intended protection policy or lifecycle outcome.

### E5

E5 owns:

- intended protection policy;
- exact `PositionAction.PROTECT` lineage;
- interpretation of Position/protection safety;
- whether missing/conflicting protection requires create, replace, emergency exit, lock, reconciliation, or other accepted response;
- lifecycle transition/reattestation authority;
- permission/veto for any cleanup or provider mutation.

E5 does not manufacture provider ownership or provider object identity.

### E6

E6 owns:

- immutable persistence of accepted FP-11 evidence;
- mechanical reference/hash/currentness/conflict validation;
- current-vs-historical registry/audit projection;
- recovery-time refusal to call stale/non-converged registry evidence current.

E6 must not choose the intended object by arrival order, row ID, newest timestamp, closest trigger, symbol similarity, or client-ID resemblance.

### E7

E7 owns:

- profile/version;
- multiplicity/currentness/status/disposition/reason vocabulary;
- deterministic evidence identity rules;
- cross-module compatibility;
- LF-2/LF-3/LF-5/LF-6 release interpretation.

### PM / Product Owner

PM sequences bounded implementation and evidence review but cannot grant provider/runtime/capital authority.

Product Owner remains separately authoritative for provider/private sessions, runtime/capital exposure, Gate D and LIVE under current governance.

## 23. Smallest future executable implementation boundaries

This task defines no executable code. Future implementation should remain split by existing ownership.

### 23.1 E4 bounded producer/normalizer

Future E4 work may:

- normalize current provider active-protection objects into stable sanitized references/snapshots;
- prove observation completeness/currentness under provider-specific readback semantics;
- bind exact E4-created protection lineage where possible;
- emit fixture-driven provider facts without network access for deterministic tests.

It must not invent E5 intended protection or lifecycle policy.

### 23.2 E5 bounded intended-lineage/policy consumer

Future E5 work may:

- provide the exact current intended `PositionAction.PROTECT` lineage;
- consume FP-11 non-converged evidence;
- produce explicit lifecycle/protection policy outcomes under existing/future accepted E5 semantics.

It must not infer provider ownership or select provider objects by similarity.

### 23.3 E6 bounded durable registry projection

Future E6 work may:

- persist immutable FP-11 evidence;
- validate set/evidence hashes and predecessor/currentness references;
- expose current/non-current audit state;
- fail recovery closed when evidence is stale, conflicting, missing, or superseded.

It must not allocate ownership or lifecycle semantics.

### 23.4 E7 integration/safety composition

Future E7 work may define/verify cross-module fixture composition once E4/E5/E6 implementations exist.

Any executable project changes require fresh approved-local credential-free qualification on the exact integrated candidate under current LF governance.

## 24. Required deterministic credential-free tests for future implementation

Future deterministic tests must require no provider network or credentials and at minimum cover:

1. zero observed protection while local lifecycle claims protected -> fail closed + E5 reinterpretation route;
2. exactly one current-generation-owned exact intended-lineage protection -> converged;
3. exactly one external protection -> not converged / no silent adoption;
4. one intended current-owned object plus one external object -> multiplicity conflict/non-converged;
5. two current-owned objects for one intended lineage -> multiplicity conflict;
6. prior-generation protection -> no current mutation authority;
7. incomplete provider observation coverage -> reject, never infer zero/one;
8. stale provider protection set -> reject;
9. changed provider object set -> old registry evidence invalid;
10. changed provider object snapshot -> old registry evidence invalid;
11. changed FP-04 ownership evidence -> old registry evidence invalid;
12. changed Position observation -> old registry evidence invalid;
13. changed lifecycle projection/execution binding -> old registry evidence invalid;
14. changed intended PositionAction lineage -> old registry evidence invalid;
15. wrong/missing runtime generation when runtime participates -> reject;
16. current-owned but lineage `NOT_MATCH` -> not converged;
17. exact lineage match but FP-04 ownership unknown/external -> not converged;
18. blind newest/closest-price/client-ID selection is impossible by contract;
19. blind cancel-all path receives no authority from FP-11 evidence;
20. blind create-another path receives no authority from FP-11 evidence;
21. new exposure remains blocked while registry is unsafe;
22. local `OPEN_PROTECTED`/`PROFIT_PROTECTED` contradiction routes to E5 reinterpretation;
23. flat Position plus orphan/multiple protection routes to FP-10 terminal protection convergence;
24. deterministic set hash/evidence ID changes on any object/ownership/currentness change;
25. no provider/network/credential access is required for these fixtures.

## 25. Relation to LF gates

### LF-2 — P0 failure-prevention closure

This profile closes only the FP-11 contract/design gap. LF-2 remains `PARTIAL` until executable E4/E5/E6 behavior exists and the exact integrated candidate has accepted local credential-free evidence.

### LF-3 — failure injection/recovery

Future LF-3 must exercise missing, duplicate, orphan, external, prior-generation, stale, incomplete, ownership-conflict, lifecycle-contradiction, and restart-currentness scenarios against the exact integrated candidate.

### LF-4 — provider read-only verification

Future separately authorized provider read-only work must prove the real provider's protection readback/coverage/object-identity semantics used by E4. Historical provider evidence cannot be rebound.

### LF-5 — SHADOW/PAPER readiness

Any provider-observing SHADOW runtime and any recovery path that asserts an open Position is protected must consume current FP-11 evidence where provider protection truth is relevant. Runtime authorization remains separate.

### LF-6 — bounded live-fire authorization

No bounded live-fire authorization may rely on stale, partial, external, or ambiguous protection registry truth. LF-6 remains future Product Owner authority only after preceding gates are accepted.

## 26. Current unresolved provider-specific facts

The following remain intentionally unresolved by this shared profile:

- provider endpoint(s) that enumerate all active protection objects for the relevant Position/instrument;
- provider proof that the observation is complete for all applicable protection mechanisms;
- provider-native stable protection object identity semantics;
- exact OKX protection create/readback/cancel field sets;
- exact trigger/order-algo mapping and trigger basis;
- exact position-mode-specific protection semantics;
- provider-native reduce-only/close behavior for protection;
- provider contract quantity conversion/rounding for protection;
- provider behavior for externally/manual-created conditional orders;
- provider behavior when a Position becomes flat while protection objects remain.

These are E4/provider-capability implementation/verification dependencies, not gaps to guess inside E7 shared semantics.

## 27. Current project state / authority boundary

At E7-107 design time:

```text
FP-11 contract/design = DEFINED BY THIS TASK ONLY
FP-11 executable implementation = NOT_STARTED
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
LF-0 exact-revision infrastructure = BLOCKED / UNCHANGED
FP-03 combined candidate = 9462b2594675b2e28388f55a2af189100b7cbdfc
FP-03 combined qualification = NOT_RUN / NOT_PASS
Gate D / LIVE = BLOCKED / UNAUTHORIZED
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

`NOT_RUN` is not executable PASS.

The active LF-0 `PREPARE_EXACT_REVISION` allowlist/infrastructure blocker remains unchanged and is not resolved by this docs-only task.
