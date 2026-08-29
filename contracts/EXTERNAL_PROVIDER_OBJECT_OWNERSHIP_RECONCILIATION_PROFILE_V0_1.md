# External Provider Object Ownership / Reconciliation Profile — V0.1

> Parent contract set: `contracts-v0.1`  
> Companion governance: `bounded-live-fire-readiness-v0.1`, `runtime-preflight-v0.1`  
> Profile identifier: `external-provider-object-ownership-reconciliation-v0.1`  
> Status: `BASELINE`  
> Technical authority: E7 Integration / Architecture / System QA / Release Engineer  
> Decision task: `E7-20260829-106`

## 1. Purpose

This profile defines the provider-neutral, fail-closed ownership and reconciliation evidence required when current provider truth contains a position, order, fill, protection object, or other provider-side object whose relationship to the current project-r7 automation generation must be proven rather than assumed.

It closes the FP-04 contract/design gap only:

```text
provider object exists
!= current project-r7 generation owns it
!= current project-r7 generation may mutate it
```

The profile prevents project-r7 from silently treating an object as trusted merely because its symbol, side, size, client-ID fragment, position, or apparent purpose resembles a locally expected object.

It composes existing authority rather than replacing it:

- E4 remains authoritative for provider observations, broker order/fill/exposure facts, provider object identity/snapshots, and execution lineage it created;
- E5 remains authoritative for Position/risk/lifecycle interpretation and whether new exposure, protection, or exit is safe under current reconciliation state;
- E6 remains authoritative for durable persistence/registry/audit projection and mechanical reference/currentness validation;
- E7 owns this shared profile, deterministic ownership/disposition vocabulary, cross-module compatibility, and integration/release interpretation;
- `runtime-preflight-v0.1` supplies current process/revision/config generation identity where relevant;
- PM reviews evidence sequencing; Product Owner authority remains separately required for provider/private/runtime/capital stages.

This profile grants no provider/private access, credential use, mutation, order action, SHADOW/PAPER runtime, bounded live-fire authority, Gate D, or LIVE authority.

## 2. Compatibility decision

Classification:

```text
ADDITIVE_SHARED_EVIDENCE_PROFILE
schema_version = contracts-v0.1 / unchanged
position/protection/close/lifecycle profiles = referenced / unchanged
runtime-preflight-v0.1 = referenced / unchanged
```

No existing OrderRequest, OrderResult, Fill, Position, PositionAction, lifecycle projection, execution binding, OperationalMode record, or provider adapter object is amended by V0.1.

No new ADR is required because V0.1 does not change authority direction or lifecycle semantics. It makes an already-required reconciliation question explicit and immutable:

> Which exact current provider object snapshot can be proven to belong to which exact local lineage/generation, and what fail-closed reconciliation work is required before automation may continue?

A future executable adoption policy, unique-protection registry, external/manual close convergence, or provider-specific object translator may require separate profiles/tasks; none is made executable here.

## 3. Scope and provider object classes

`provider_object_class` is exactly one of:

- `POSITION_EXPOSURE` — current provider-side position/exposure observation;
- `OPEN_ORDER` — pending/open provider order relevant to current reconciliation;
- `TERMINAL_ORDER` — historical/terminal provider order still relevant to current reconciliation or lineage proof;
- `FILL_EXECUTION` — provider trade/fill execution observation;
- `ACTIVE_PROTECTION` — active conditional/protective order or provider-side protection object;
- `UNCLASSIFIED_PROVIDER_OBJECT` — provider-side object whose purpose/lineage cannot yet be determined safely.

The classes are independent. V0.1 does not assume that provider-native identifiers, endpoints, field sets, timestamps, or lifecycle semantics are identical across classes.

E4 must supply class-specific stable sanitized references/hashes from its own normalized provider observations. E7/E5/E6 must not invent missing provider fields or infer one class from another merely by similar values.

## 4. Ownership classification vocabulary

`ownership_classification` is exactly one of:

- `KNOWN_OWNED_CURRENT_GENERATION`
- `KNOWN_OWNED_PRIOR_GENERATION`
- `EXTERNAL_UNTRACKED`
- `ADOPTABLE_BY_EXPLICIT_POLICY`
- `MANUAL_REVIEW_REQUIRED`
- `CONFLICTING_OWNERSHIP_EVIDENCE`
- `UNKNOWN`

### 4.1 `KNOWN_OWNED_CURRENT_GENERATION`

Allowed only when the exact current provider object snapshot is bound without contradiction to one exact current-generation local lineage and, where runtime generation matters, the exact current runtime/preflight/config generation.

This classification is provenance evidence only. It does not itself authorize provider mutation; the applicable E5/E4 action authority, provider capability, operational mode, reconciliation state, runtime preflight, release gate and Product Owner authority must still independently pass.

### 4.2 `KNOWN_OWNED_PRIOR_GENERATION`

The object is proven to originate from project-r7, but the proven lineage belongs to a previous process/start/config/runtime generation.

Prior-generation provenance does not inherit current-generation mutation authority. Fresh current reconciliation is mandatory before any current process may act on the object. If current policy later permits explicit re-association/adoption, that decision must be separately evidenced under section 12.

### 4.3 `EXTERNAL_UNTRACKED`

Current provider truth contains an object for which no accepted project-r7 lineage exists and no accepted explicit adoption decision applies.

It may have been created manually, by another process/system, or outside the current project generation. It is never silently ignored or treated as trusted protection/position/order ownership.

### 4.4 `ADOPTABLE_BY_EXPLICIT_POLICY`

The exact object snapshot satisfies the eligibility conditions of a separately accepted adoption policy, but adoption has **not** occurred merely because this classification is emitted.

The only meaning is:

```text
classification says explicit adoption evaluation is permitted
!= adoption approved
!= mutation authorized
```

If no separately accepted adoption policy/version exists, this classification cannot be emitted.

### 4.5 `MANUAL_REVIEW_REQUIRED`

Evidence is sufficiently understood to determine that automated adoption/detach/reconciliation cannot proceed under accepted policy without an explicit human review decision.

No provider mutation authority is implied.

### 4.6 `CONFLICTING_OWNERSHIP_EVIDENCE`

Two or more authoritative facts contradict the ownership mapping. Examples include two local lineages claiming the same provider object, one local lineage mapping to multiple provider objects where multiplicity is not permitted, or provider identity/snapshot facts contradicting the claimed local lineage.

This state always fails closed.

### 4.7 `UNKNOWN`

Required ownership evidence is missing, unsupported, stale, malformed, unverifiable, or otherwise insufficient to classify safely.

`UNKNOWN` always fails closed.

## 5. Non-inference rules

The following are never sufficient ownership proof by themselves:

- local record absence;
- matching symbol;
- matching side;
- similar quantity;
- a familiar provider order type;
- a provider client-ID prefix or fragment;
- a provider object existing near the time project-r7 expected one;
- matching stop/trigger value;
- current Position shape alone;
- a prior-generation project-r7 lineage;
- a successful historical provider/qualification session;
- a caller assertion that an object is project-owned;
- a provider object being the only visible object of its class.

Absence of local state is not proof that a provider object is safe to ignore. Presence of local state is not proof that provider truth still matches it.

## 6. Canonical ownership/reconciliation evidence

Canonical shared evidence object:

```text
ExternalProviderObjectOwnershipEvidence
```

Required fields:

- `schema_version` — exactly `contracts-v0.1`;
- `external_provider_ownership_profile_version` — exactly `external-provider-object-ownership-reconciliation-v0.1`;
- `ownership_evidence_id` — deterministic identity from section 15;
- `provider_object_class` — one class from section 3;
- `provider_identity_ref` — E4-supplied sanitized provider/environment identity reference;
- `provider_identity_hash` — canonical `sha256:<lowercase hex>` for that sanitized identity envelope;
- `canonical_symbol` — exact canonical instrument/symbol bound by the provider observation;
- `provider_instrument_ref` — E4-supplied sanitized exact provider instrument reference;
- `provider_object_ref` — E4-supplied stable sanitized reference for the exact provider object identity within its class;
- `provider_snapshot_ref` — E4-supplied immutable reference to the exact normalized provider object snapshot;
- `provider_snapshot_hash` — canonical hash of that exact normalized snapshot;
- `provider_observation_generation_id` — exact E4 provider-observation generation;
- `provider_observed_at` — RFC 3339 UTC source observation time;
- `provider_received_at` — RFC 3339 UTC local receipt/acceptance time;
- `current_project_revision` — exact project revision used for this evaluation;
- `runtime_preflight_ref` — exact current `runtime-preflight-v0.1` reference when a runtime/process generation materially participates, otherwise `null` only for an explicitly non-runtime deterministic evaluation;
- `runtime_process_instance_id` — exact current process identity when applicable, otherwise `null`;
- `runtime_process_start_generation_id` — exact current process-start generation when applicable, otherwise `null`;
- `runtime_config_generation_id` — exact current behavior-affecting runtime config generation when applicable, otherwise `null`;
- `local_lineage_evidence` — deterministic sequence defined in section 7;
- `local_registry_evidence` — deterministic sequence defined in section 8;
- `ownership_classification` — value from section 4;
- `reconciliation_status` — value from section 9;
- `required_dispositions` — deterministic sequence from section 10;
- `reason_codes` — deterministic ordered sequence from section 11;
- `adoption_decision_ref` — exact accepted future adoption-decision reference when one has already been applied to the same exact provider snapshot, otherwise `null`;
- `supersedes_ownership_evidence_id` — immediately prior evidence ID for the same logical provider-object lineage when known, otherwise `null`;
- `evaluated_at` — RFC 3339 UTC evaluation time after all bound inputs are accepted.

No API key, secret, passphrase, account credential, raw private response, raw provider signature/token, exact account balance, local filesystem path, shell command, or unnecessary provider-native payload belongs in this evidence.

## 7. Local lineage evidence

`local_lineage_evidence` is sorted lexicographically by `(owner, evidence_class, evidence_ref)`.

Each item contains:

- `owner` — `E4 | E5 | E6`;
- `evidence_class` — one stable class name identifying the claimed lineage fact;
- `evidence_ref`;
- `evidence_hash`;
- `evidence_generation_id`;
- `observed_or_created_at`;
- `lineage_role` — one of `APPROVED_TRADE_PLAN | POSITION_ACTION | ORDER_REQUEST | CLIENT_ORDER_IDENTITY | ORDER_RESULT | FILL | POSITION | LIFECYCLE_PROJECTION | LIFECYCLE_EXECUTION_BINDING | OTHER_ACCEPTED_LINEAGE`;
- `claim_status` — `CLAIMS_OWNERSHIP | SUPPORTS_LINEAGE | CONTRADICTS_LINEAGE | UNKNOWN`.

Where applicable, exact existing identifiers remain inside their owner-authoritative objects and are referenced rather than duplicated. Examples include `trade_plan_id`, `position_action_id`, `order_request_id`, deterministic client-order identity, lifecycle projection identity, and lifecycle execution-binding identity.

A consumer must not upgrade `SUPPORTS_LINEAGE` into ownership unless all required exact bindings for the object class are present and conflict-free.

## 8. Local persistence/registry evidence

`local_registry_evidence` is sorted lexicographically by `(owner, evidence_class, evidence_ref)` and contains:

- `owner` — normally `E6`, or another authoritative owner only when a future accepted profile explicitly defines it;
- `evidence_class`;
- `evidence_ref`;
- `evidence_hash`;
- `evidence_generation_id`;
- `observed_at`;
- `currentness_status` — `CURRENT | STALE | CONFLICT | UNKNOWN`.

E6 may mechanically prove that an exact accepted record/reference is durable/current/conflict-free. It may not manufacture provider ownership, infer lifecycle meaning, or convert a stale local row into current provider truth.

FP-11 may later add a dedicated protection-registry evidence class. Until then, this profile does not pretend such a registry already exists.

## 9. Reconciliation status vocabulary

`reconciliation_status` is exactly one of:

- `CURRENT_KNOWN_OWNED` — exact current-generation ownership is proven and no FP-04 reconciliation work remains for this exact snapshot;
- `RECONCILIATION_REQUIRED` — fresh provider/local reconciliation is required before dependent automation may proceed;
- `ADOPTION_EVALUATION_REQUIRED` — explicit separate adoption-policy evaluation is required;
- `MANUAL_REVIEW_REQUIRED` — automated policy cannot safely decide the next ownership step;
- `CONVERGENCE_REQUIRED` — one or more downstream lifecycle/registry/terminal-flat convergence operations are required;
- `UNKNOWN` — reconciliation state itself is incomplete or unverifiable.

Only `KNOWN_OWNED_CURRENT_GENERATION` may pair with `CURRENT_KNOWN_OWNED`.

`CURRENT_KNOWN_OWNED` is still not provider-mutation authority. All independent action/risk/provider/runtime gates remain required.

## 10. Required reconciliation dispositions

`required_dispositions` is a deterministic sorted sequence containing one or more of:

- `NO_ACTION_CURRENT_KNOWN_OWNED`
- `FRESH_RECONCILIATION_REQUIRED`
- `BLOCK_NEW_EXPOSURE`
- `BLOCK_PROTECTION_MUTATION`
- `BLOCK_CLOSE_EXIT_MUTATION`
- `ADOPTION_POLICY_EVALUATION_REQUIRED`
- `DETACH_IGNORE_POLICY_EVALUATION_REQUIRED`
- `MANUAL_REVIEW_REQUIRED`
- `LIFECYCLE_REINTERPRETATION_REQUIRED`
- `PROTECTION_REGISTRY_CONVERGENCE_REQUIRED`
- `TERMINAL_FLAT_CONVERGENCE_PENDING`

Rules:

1. `NO_ACTION_CURRENT_KNOWN_OWNED` is exclusive; it cannot coexist with a blocking/convergence disposition.
2. A disposition is reconciliation evidence only and never directly authorizes provider mutation.
3. `BLOCK_CLOSE_EXIT_MUTATION` applies when correctness of a close/exit depends on ownership/quantity that is not authoritative. It does not prohibit a future separately defined emergency-safety path that has its own exact current exposure authority; V0.1 does not invent such a path.
4. `DETACH_IGNORE_POLICY_EVALUATION_REQUIRED` means a later explicit policy may evaluate whether automation should intentionally leave an external object unmanaged. It is not permission to ignore the object now.
5. `PROTECTION_REGISTRY_CONVERGENCE_REQUIRED` routes active-protection multiplicity/identity uncertainty to FP-11; V0.1 never silently selects one object as the intended protection.
6. `LIFECYCLE_REINTERPRETATION_REQUIRED` and `TERMINAL_FLAT_CONVERGENCE_PENDING` route manual/external reduction/flat truth to FP-10/E5 lifecycle handling; provider order status alone never closes lifecycle.

## 11. Stable fail-closed reason vocabulary

Reason codes are emitted in this deterministic order when applicable:

1. `EXTERNAL_OWNERSHIP_PROFILE_UNSUPPORTED`
2. `PROVIDER_OBJECT_CLASS_UNKNOWN`
3. `PROVIDER_IDENTITY_UNBOUND`
4. `PROVIDER_SNAPSHOT_UNBOUND`
5. `PROVIDER_OBJECT_LINEAGE_NOT_PROVEN`
6. `PROVIDER_OBJECT_PRIOR_RUNTIME_GENERATION`
7. `EXTERNAL_PROVIDER_OBJECT_UNTRACKED`
8. `EXPLICIT_ADOPTION_POLICY_REQUIRED`
9. `OWNERSHIP_MANUAL_REVIEW_REQUIRED`
10. `LOCAL_LINEAGE_OWNERSHIP_CONFLICT`
11. `PROVIDER_OBJECT_MULTIPLICITY_CONFLICT`
12. `LINEAGE_PROVIDER_IDENTIFIER_MISMATCH`
13. `LINEAGE_PROVIDER_SNAPSHOT_MISMATCH`
14. `PROVIDER_OBJECT_INSTRUMENT_MISMATCH`
15. `PROVIDER_OBJECT_SIDE_MISMATCH`
16. `PROVIDER_OBJECT_QUANTITY_MISMATCH`
17. `PROVIDER_OBSERVATION_NEWER_THAN_OWNERSHIP_EVIDENCE`
18. `LOCAL_EVIDENCE_NEWER_OR_CONTRADICTORY`
19. `OWNERSHIP_EVIDENCE_STALE`
20. `ADOPTION_EVIDENCE_MISSING_OR_INVALID`
21. `ADOPTION_EVIDENCE_STALE_OR_MISMATCHED`
22. `ADOPTION_EVIDENCE_ALREADY_CONSUMED`
23. `PROTECTION_REGISTRY_CONVERGENCE_REQUIRED`
24. `LIFECYCLE_REINTERPRETATION_REQUIRED`
25. `TERMINAL_FLAT_CONVERGENCE_PENDING`
26. `OWNERSHIP_RECONCILIATION_INCOMPLETE`
27. `CURRENT_GENERATION_OWNERSHIP_PROVEN`

`CURRENT_GENERATION_OWNERSHIP_PROVEN` is the only success reason and appears alone when `ownership_classification=KNOWN_OWNED_CURRENT_GENERATION`, `reconciliation_status=CURRENT_KNOWN_OWNED`, and `required_dispositions=[NO_ACTION_CURRENT_KNOWN_OWNED]`.

Unknown required reason codes under a consumer-required V0.1 profile fail closed rather than being ignored as healthy.

## 12. Adoption boundary

Adoption is a separate explicit policy/authority step. Classification never performs adoption.

V0.1 defines the minimum envelope that a **future separately implemented and accepted** adoption decision must bind. No executable producer is created by this task.

Reserved future evidence object:

```text
ExternalProviderObjectAdoptionDecisionEvidence
```

Minimum required material:

- exact `ownership_evidence_id` and ownership-evidence hash;
- exact `provider_object_class`;
- exact `provider_object_ref`;
- exact `provider_snapshot_ref` and provider snapshot hash;
- exact provider observation generation/time;
- exact current canonical Position/exposure reference when exposure/protection/close semantics depend on it;
- exact current lifecycle projection/execution-binding references when applicable;
- exact current protection/other registry reference when applicable;
- exact current runtime preflight/process/start/config generation when runtime participates;
- `adoption_policy_version` and deterministic policy hash;
- `adoption_decision_id` deterministic over the complete decision payload;
- decision vocabulary limited to `ADOPTION_APPROVED | ADOPTION_REJECTED | MANUAL_REVIEW_REQUIRED`;
- `decision_scope = ONE_EXACT_PROVIDER_OBJECT_SNAPSHOT`;
- `decision_status = VALID | STALE | MISMATCH | CONSUMED`;
- explicit decision time after all bound inputs;
- stable reasons/audit provenance.

Rules:

- no current V0.1 policy says which external object classes are production-adoptable;
- arbitrary manual/external objects cannot be converted to project-owned objects merely by constructing this shape;
- an approved adoption decision applies only to the exact bound provider snapshot and policy/runtime generation;
- a newer provider snapshot, changed local Position/lifecycle/registry truth, changed runtime/config generation, or changed policy version invalidates prior adoption authority;
- a consumed single-object adoption decision cannot be replayed to adopt a later/different object or snapshot;
- stale, mismatched, unknown or consumed adoption evidence is rejected;
- actual mutation after adoption still requires all independent E5/E4/provider/runtime/release authorization.

## 13. Fail-closed classification and disposition rules

### 13.1 Missing trustworthy current lineage

If a provider object exists and exact current lineage cannot be proven:

```text
ownership = EXTERNAL_UNTRACKED | UNKNOWN | MANUAL_REVIEW_REQUIRED
reconciliation != CURRENT_KNOWN_OWNED
BLOCK_NEW_EXPOSURE is required when the object can affect exposure/order/protection certainty
```

Protection objects also require `BLOCK_PROTECTION_MUTATION` until convergence.

### 13.2 Provider/local identity mismatch

If local lineage claims ownership but provider identifier/reference or exact snapshot does not bind to it:

```text
ownership = CONFLICTING_OWNERSHIP_EVIDENCE
reconciliation = RECONCILIATION_REQUIRED
```

Unsafe dependent mutations are blocked.

### 13.3 Two local lineages claim one provider object

This is `CONFLICTING_OWNERSHIP_EVIDENCE`. No arrival-order, latest-row, or arbitrary-selection rule may choose a winner.

### 13.4 One local lineage maps to multiple active provider objects

If the applicable object-class policy does not explicitly permit multiplicity, the result is `CONFLICTING_OWNERSHIP_EVIDENCE`.

For `ACTIVE_PROTECTION`, multiple active candidates additionally require `PROTECTION_REGISTRY_CONVERGENCE_REQUIRED`; V0.1 never collapses them into one intended protection.

### 13.5 Prior-generation project object

An exact prior-generation lineage may classify `KNOWN_OWNED_PRIOR_GENERATION`, but current-generation mutation authority is absent. Fresh reconciliation and, if required by future policy, explicit adoption/re-association evaluation are mandatory.

### 13.6 External/manual object

A manually/external created object is never silently adopted. Without a valid explicit adoption policy/evidence, it remains `EXTERNAL_UNTRACKED`, `MANUAL_REVIEW_REQUIRED`, or `UNKNOWN` and dependent automation fails closed.

### 13.7 Quantity/side/instrument contradiction

When provider class semantics expose canonicalized instrument/side/quantity facts and those facts contradict claimed lineage, classification is `CONFLICTING_OWNERSHIP_EVIDENCE`.

V0.1 does not invent provider-native sizing or side rules. E4 supplies the normalized facts and the accepted role/provider capability profiles define what may be compared.

### 13.8 Reconciliation incomplete

Unknown, incomplete, missing, stale, conflicting, or structurally invalid reconciliation evidence must not be interpreted as current/safe.

## 14. Temporal ordering, currentness and supersession

Ownership evidence is immutable and snapshot-bound.

Deterministic evaluation ordering:

```text
1. accept exact E4 provider object snapshot
2. accept exact local lineage references
3. accept exact E6 registry/persistence references where applicable
4. accept current runtime-preflight/process/config generation where applicable
5. validate any already-existing explicit adoption evidence
6. capture evaluated_at
7. classify ownership and reconciliation dispositions
8. before dependent mutation, reject this evidence if newer relevant provider/local/runtime truth is already known
```

Minimum ordering rules:

```text
provider_received_at >= provider_observed_at, subject to accepted provider clock/receipt policy
evaluated_at >= provider_received_at
evaluated_at >= every bound local evidence observation/creation time
evaluated_at >= every bound registry evidence observed_at
```

When runtime-preflight evidence participates, it must be current for the same exact process/start/config generation; prior-process preflight does not qualify a new process.

### 14.1 Newer provider truth

Any accepted provider observation for the same logical provider object that is newer than the bound provider snapshot invalidates the older ownership evidence for mutation/current-state claims.

Same provider object reference and same observation boundary with different canonical snapshot hash is a conflict, not an arrival-order tie-break.

Changed provider snapshot requires fresh ownership interpretation even when the provider object identifier remains unchanged.

### 14.2 Newer local truth

A newer E4 execution observation, E5 lifecycle projection/reattestation, E6 registry generation, or other required owner-authoritative local evidence that contradicts or supersedes the bound material invalidates the older ownership evidence.

E6 may mark older evidence historical/stale; it may not rewrite the old object to claim later truth.

### 14.3 Runtime/config generation change

A process/start/config generation change invalidates any claim that an object is `KNOWN_OWNED_CURRENT_GENERATION` for the new generation until fresh classification/reconciliation occurs. Historical prior-generation provenance may remain auditable.

### 14.4 Supersession

A fresh evidence object may set `supersedes_ownership_evidence_id` to the immediately preceding evidence for the same logical provider-object lineage. Supersession preserves the old immutable evidence; it does not mutate it.

No timestamp alone makes a prior external/conflicting object current-owned. Material owner evidence must change.

## 15. Deterministic evidence identity

`ownership_evidence_id` is deterministic over the complete canonical evidence payload except the ID field itself.

Algorithm:

1. remove `ownership_evidence_id`;
2. serialize the remaining payload as canonical UTF-8 JSON with lexicographically sorted keys and compact separators;
3. arrays whose order is defined by this profile must already be deterministically sorted;
4. timestamps use canonical RFC 3339 UTC `Z` form;
5. hashes use `sha256:<lowercase hex>` form;
6. compute SHA-256;
7. prefix the lowercase hex digest with:

```text
extownrec_
```

Therefore:

```text
same exact inputs/classification/dispositions/time -> same ID
changed provider snapshot/local lineage/runtime generation/result -> different ID
same ID + changed payload -> conflict/corrupt evidence
```

## 16. FP-11 active-protection dependency

FP-11 must consume this profile before deciding unique active-protection registry convergence.

At minimum every observed active protective provider object must first be individually classified as one of:

```text
KNOWN_OWNED_CURRENT_GENERATION
KNOWN_OWNED_PRIOR_GENERATION
EXTERNAL_UNTRACKED
ADOPTABLE_BY_EXPLICIT_POLICY
MANUAL_REVIEW_REQUIRED
CONFLICTING_OWNERSHIP_EVIDENCE
UNKNOWN
```

FP-11 may later require exactly one intended active protection lineage under its own accepted registry/multiplicity contract. This profile does not define or implement that registry.

Rules preserved for FP-11:

- multiple active protection objects are not silently collapsed;
- an external object that happens to protect the same side/quantity is not trusted protection by similarity;
- a prior-generation project stop is not current-generation mutation authority;
- missing/unknown/external/conflicting protection routes to convergence/reconciliation and blocks false-green protection claims;
- provider readback identity must remain cross-referenceable to the exact local lineage/evidence generation.

## 17. FP-10 external/manual close dependency

FP-10 must consume current provider Position/fill truth plus this ownership/reconciliation evidence before external/manual reduction or flatness can converge lifecycle.

This profile never maps an external/manual terminal order directly to `CLOSED`.

Required rule:

```text
provider terminal order status alone
!= authoritative flat Position
!= E5 lifecycle CLOSED
```

Later FP-10 must bind at minimum:

- authoritative provider Position/exposure truth;
- aggregate relevant fill/execution truth where available/required;
- current ownership/reconciliation evidence for external/manual objects;
- current E5 lifecycle projection and execution-evidence binding;
- E5-owned reconciliation event/interpretation such as the existing `RECONCILED_FLAT` path when its preconditions are actually satisfied.

External/manual reduced-but-not-flat exposure requires current Position quantity truth and fresh E5 interpretation; it cannot reuse original requested/entry quantity or infer closure from one execution row.

## 18. Cross-module ownership split

### E4 — provider/execution truth

E4 owns:

- normalized provider object observations;
- class-specific provider object stable references;
- exact immutable snapshot references/hashes;
- provider observation generation/time;
- broker order/fill/Position facts;
- local execution lineage E4 actually created;
- ambiguity/reconciliation observations and later provider readback.

E4 does not decide E5 lifecycle policy and does not turn an external object into current project authority by convenience.

### E5 — risk/lifecycle safety

E5 owns:

- interpretation of current Position/exposure safety;
- lifecycle response to unknown/external/conflicting provider truth;
- whether new exposure/protection/exit is permissible given current reconciliation state;
- fresh lifecycle transition/reattestation after external/manual truth;
- any future adoption policy's risk/lifecycle constraints when such a policy is separately approved.

E5 does not manufacture provider ownership evidence.

### E6 — durability/registry/audit

E6 owns:

- persistence of accepted immutable ownership/reconciliation evidence;
- durable reference/hash/currentness/conflict validation;
- current-vs-historical audit projection;
- later persistence of dedicated protection/adoption registries only under their own accepted tasks/profiles.

E6 does not infer provider ownership, choose among conflicting lineages, or map provider order state directly to lifecycle state.

### E7 — shared contract/integration

E7 owns:

- this profile and version;
- object/ownership/reconciliation/disposition/reason vocabulary;
- deterministic validation/currentness rules;
- cross-module integration interpretation;
- LF-2/LF-3 acceptance requirements.

A future E7 integration validator may mechanically compose owner-authoritative references and apply this deterministic profile, but E7 does not acquire provider truth or E5 risk authority.

### PM / Product Owner

PM reviews exact evidence generations and sequences future tasks. PM does not grant provider/runtime/mutation/capital authority.

Product Owner authority remains separately required where current governance requires provider/private/runtime/capital authorization. Contract completion alone grants none.

## 19. Future deterministic implementation/test handoff

No executable implementation is created by E7-106. The smallest safe future boundaries are:

### 19.1 E4 provider-object observation/lineage boundary

Provider-free fixtures must prove:

- each object class emits a stable class-specific reference/snapshot hash;
- exact locally-created object maps to exact provider object only when identifiers/snapshots bind;
- provider object with no trustworthy lineage is not guessed owned;
- changed provider snapshot requires fresh interpretation;
- two local lineages claiming one provider object surface conflict;
- one lineage mapping to multiple provider objects surfaces multiplicity conflict;
- no provider/network/credential access is required for deterministic tests.

### 19.2 E5 safety/lifecycle consumer boundary

Provider-free tests must prove:

- unknown provider position blocks new exposure;
- unknown/external protection blocks false-green protection and unsafe protection/new-exposure mutation until convergence;
- prior-generation ownership does not inherit current mutation authority;
- external/manual reduced or flat truth routes to fresh lifecycle interpretation, not direct closure from order status;
- conflicting ownership never becomes APPROVE by default.

### 19.3 E6 persistence/currentness boundary

Provider-free tests must prove:

- immutable evidence persists by deterministic ID/hash;
- changed provider snapshot/local lineage/runtime generation produces new evidence rather than mutating history;
- stale evidence cannot become current by persistence arrival order;
- currentness/reference conflict fails closed;
- no registry row can manufacture ownership classification.

### 19.4 E7 integration/safety boundary

Provider-free integration/safety tests must prove:

- known-owned current-generation exact object classification;
- prior-generation object remains non-authoritative for current mutation;
- unknown/external provider position blocks new exposure;
- unknown/external protection blocks unsafe protection mutation/new exposure;
- manual/external object is never silently adopted;
- conflicting two-local-lineage ownership fails closed;
- stale ownership evidence is invalidated by newer provider snapshot;
- changed provider object snapshot requires fresh interpretation;
- adoption decision binds the exact object snapshot and exact policy generation;
- consumed/stale/mismatched adoption evidence is rejected;
- duplicate/multiple protection routes to FP-11 convergence rather than silent selection;
- external/manual flat/reduced exposure routes to FP-10 lifecycle reinterpretation rather than order-status closure;
- tests use fixtures/fakes only, with zero provider/network/credential access.

Any project executable implementation change requires fresh approved-local credential-free qualification on the exact integrated revision before LF-2 can treat FP-04 executable closure as PASS.

## 20. LF-gate relationship

### LF-2 — P0 failure-prevention closure

FP-04 is a required LF-2 item. This docs-only baseline closes the contract/design gap only; executable implementation and fresh credential-free evidence remain required.

### LF-3 — failure injection/recovery

LF-3 must exercise at minimum:

- external/manual provider position;
- external/open order;
- external fill;
- duplicate/orphan/unknown protection;
- prior-generation project object;
- conflicting lineage;
- stale ownership/adoption evidence;
- changed provider snapshot;
- external/manual reduced/flat exposure;
- restart/current-generation ownership re-evaluation.

All deterministic LF-3 scenarios can initially use fixtures/fakes with no provider credentials or capital.

### LF-4 — provider read-only verification

Future separately authorized LF-4 must establish the provider-specific read-only observation facts needed to populate the exact E4 provider-object references/snapshots for the exact candidate revision.

V0.1 does not assume that historical OKX provider evidence already exposes every needed object class/field, especially provider-native active protection/conditional-order or terminal-order identity surfaces. Missing provider-specific read-only capability remains a future E4/provider-verification dependency.

### LF-5 — SHADOW/PAPER readiness

Before SHADOW/PAPER can claim mature reconciliation readiness:

- runtime preflight/current-generation identity must be current where applicable;
- provider/manual objects must never be silently adopted;
- SHADOW must fail closed on unknown/external/conflicting provider truth;
- PAPER/failure simulation must cover equivalent ownership/reconciliation states;
- FP-11 and FP-10 downstream convergence semantics must be accepted and exercised.

Historical consumed SHADOW authorizations remain non-reusable.

### LF-6 — bounded live-fire authorization

A future bounded live-fire preflight must prove all relevant current provider objects are reconciled under accepted ownership evidence before new exposure.

Any unknown/external/conflicting provider position/order/fill/protection state that affects safe authority blocks new exposure. Explicit adoption, if ever permitted, must be separately authorized/evidenced for the exact snapshot and cannot be inferred from the live-fire authorization itself.

A successful bounded session never grants recurring LIVE authority.

## 21. Current state as of E7-20260829-106

```text
FP-04 prior audit classification = PARTIAL
FP-04 shared contract/design = DEFINED BY THIS PROFILE / EXECUTABLE IMPLEMENTATION NOT STARTED
FP-11 unique protection registry = NOT IMPLEMENTED BY THIS TASK / DOWNSTREAM DEPENDENCY
FP-10 external/manual close convergence = NOT IMPLEMENTED BY THIS TASK / DOWNSTREAM DEPENDENCY
LF-0 exact-revision infrastructure = BLOCKED / UNCHANGED
FP-03 combined candidate revision = 9462b2594675b2e28388f55a2af189100b7cbdfc
exact clean FP-03 candidate = NOT_ESTABLISHED
FP-03 combined qualification = NOT_RUN / NOT_PASS
provider-facing verification on current candidate = NOT_RUN / NOT_INFERRED
SHADOW/PAPER = NOT_AUTHORIZED
10U bounded live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
```

Historical exact-revision, qualification and provider evidence remains bound only to the revisions/generations that produced it.

## 22. Security / execution boundary

E7-106 is contract/docs/status only:

```text
project executable verification = NOT_RUN / NOT REQUIRED
Local Job Request = NONE
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order submit/cancel/amend/close = 0
SHADOW/PAPER runtime = NOT_STARTED / NOT_AUTHORIZED
10U live-fire = NOT_AUTHORIZED
capital exposure = NONE
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
```

`NOT_RUN` is not executable PASS.