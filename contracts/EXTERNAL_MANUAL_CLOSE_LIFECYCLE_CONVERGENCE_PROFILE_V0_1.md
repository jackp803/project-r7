# External / Manual Close Lifecycle Convergence Profile — V0.1

> Parent contract set: `contracts-v0.1`  
> Required companions: `external-provider-object-ownership-reconciliation-v0.1`, `protection-registry-multiplicity-v0.1`, `position-lifecycle-projection-v0.1`, `position-lifecycle-execution-binding-v0.1`  
> Provider-local dependency when project close participated: `okx-swap-close-residual-sizing-v0.1`  
> Profile identifier: `external-manual-close-lifecycle-convergence-v0.1`  
> Status: `BASELINE`  
> Technical authority: E7 Integration / Architecture / System QA / Release Engineer  
> Decision task: `E7-20260829-109`

## 1. Purpose

This profile defines the provider-neutral, fail-closed evidence required to converge current provider exposure, order/fill, ownership, protection, and lifecycle truth after a Position is reduced or flattened.

It closes only the FP-10 contract/design gap.

The profile prevents these unsafe equivalences:

```text
close OrderResult ACK/terminal/FILLED != provider Position is flat
requested close quantity            != actual reduced quantity
local arithmetic remainder = 0       != authoritative flatness
missing local Position row           != flatness
no pending order                      != flatness
provider Position flat               != all execution/protection truth converged
external/manual close                != current-generation execution ownership
flat exposure                         != TradeResult evidence complete
```

The shared safety question is:

> Does current owner-authoritative provider/local evidence prove that exposure is still open, reduced, flat-but-not-converged, or fully eligible for E5 lifecycle-close interpretation without discarding unresolved external/manual execution or protection truth?

This profile produces convergence evidence only. It never emits a Position lifecycle transition and never authorizes provider mutation.

## 2. Compatibility decision

Classification:

```text
ADDITIVE_SHARED_EVIDENCE_PROFILE
schema_version = contracts-v0.1 / unchanged
close-v0.1 = referenced / unchanged
trade-result-v0.1 = referenced / unchanged
position-lifecycle-projection-v0.1 = referenced / unchanged
position-lifecycle-execution-binding-v0.1 = referenced / unchanged
external-provider-object-ownership-reconciliation-v0.1 = required / unchanged
protection-registry-multiplicity-v0.1 = required / unchanged
okx-swap-close-residual-sizing-v0.1 = provider-local reference only / unchanged
```

No existing Position, PositionAction, OrderRequest, OrderResult, Fill, TradeResult, lifecycle projection, lifecycle execution binding, FP-04 ownership object, FP-11 registry object, or E4 provider-local FP-05 object changes identity or meaning.

No new ADR is required for V0.1 because the accepted architecture already assigns:

```text
E4 = provider Position/order/fill/reconciliation/provider-local residual truth
E5 = lifecycle/risk interpretation and transitions
E6 = persistence/currentness/reference validation
E7 = shared evidence/version/integration semantics
```

This profile composes those boundaries. It does not alter dependency direction, lifecycle state-machine transitions, or provider architecture.

## 3. Scope

V0.1 applies to one exact canonical Position lineage after any event that may have reduced or flattened provider exposure, including:

- project-r7 `POSITION_EXIT` or `EMERGENCY_EXIT` activity;
- protection-triggered reduction/close;
- manual provider close/reduction;
- external system close/reduction;
- prior runtime/process-generation close/reduction;
- ambiguous close outcome later reconciled;
- provider Position change whose responsible execution lineage is not current-generation-owned.

V0.1 is provider-neutral. It defines no OKX endpoint, `posSide`, `reduceOnly`, `sz`, close order type, minimum quantity, provider trigger field, or provider-native cancellation behavior.

Those remain E4/provider capability facts.

## 4. Authority model

### 4.1 E4

E4 owns:

- current provider Position/exposure observations;
- normalized canonical Position broker facts;
- provider order/fill observations and exact object/snapshot identity;
- provider reconciliation and ambiguous-outcome facts;
- current provider observation generation/currentness facts;
- FP-05 provider-local close/residual sizing evidence when a project close path participated.

E4 does not emit lifecycle `CLOSED` or reinterpret E5 state.

### 4.2 E5

E5 owns:

- lifecycle/risk interpretation;
- whether convergence evidence leads to `STATE_UNKNOWN`, `RECONCILED_FLAT`, `POSITION_CLOSED`, `EXIT_FAILED`, `EMERGENCY`, hold/lock, re-attestation, or another accepted lifecycle outcome;
- whether a fresh close/protection/emergency action is allowed after current truth is interpreted.

`LIFECYCLE_CLOSE_ELIGIBLE` is input evidence for E5. It is not a transition.

### 4.3 E6

E6 owns:

- immutable persistence of accepted evidence;
- reference/hash/currentness/conflict validation;
- current-vs-historical projection mechanics;
- mechanical comparison of persisted lifecycle execution evidence.

E6 must not infer flatness from missing rows, storage order, latest arrival, or absence of a pending order. It must not map execution status into lifecycle state.

### 4.4 E7

E7 owns:

- this profile and version;
- convergence-state/disposition/reason vocabulary;
- evidence identity/currentness rules;
- cross-module compatibility and release interpretation.

### 4.5 PM / Product Owner

PM sequences bounded implementation/evidence review and cannot manufacture provider/runtime authority.

Product Owner authority remains separately required for provider/private/runtime/capital stages under existing governance. This profile grants none.

## 5. Required evidence distinctions

The evaluator must bind these evidence families independently. One family may not substitute for another.

### 5.1 Current provider Position / exposure truth

Required owner-authoritative facts or references include:

- provider identity/environment reference;
- canonical symbol/instrument reference;
- exact provider Position/exposure snapshot reference/hash;
- provider observation generation;
- provider observed/received time;
- observation coverage/currentness classification;
- exact provider-native zero/nonzero exposure fact as normalized by E4.

Provider Position truth is the ultimate exposure-flatness authority. Order status is not.

### 5.2 Normalized canonical Position truth

The evidence binds exact E4-normalized canonical Position material, including:

- `position_id`;
- canonical symbol;
- side/direction lineage;
- exact `actual_quantity`;
- exact `broker_state_observed_at`;
- `reconciliation_status`;
- quantity profile/unit/asset;
- exact normalized Position snapshot reference/hash.

For lifecycle close eligibility:

```text
actual_quantity = 0
reconciliation_status = CONSISTENT
```

must be established from the current provider/normalized Position boundary.

A missing local Position object is never equivalent to `actual_quantity=0`.

### 5.3 Aggregate relevant execution / Fill evidence

Current execution evidence may include:

- project-owned `POSITION_EXIT` / `EMERGENCY_EXIT` / `PROTECTION_STOP` OrderRequest lineage;
- every current relevant OrderResult observation;
- every current relevant Fill;
- external/manual/provider order/fill objects relevant to the exposure change;
- prior ambiguous-outcome reconciliation evidence.

The profile distinguishes:

```text
execution evidence explains or is compatible with Position truth
```

from:

```text
execution evidence is itself flatness authority
```

Only the first is permitted.

A close order may be ACKed, terminal, or `FILLED` while Position truth remains positive. That is not close eligible.

### 5.4 FP-04 ownership/reconciliation evidence

Every provider Position/order/fill object materially participating in convergence must have current accepted FP-04 evidence or be explicitly represented as missing/unknown.

The profile consumes:

- exact `ownership_evidence_id` / hash;
- provider object class;
- exact provider snapshot identity;
- ownership classification;
- reconciliation status;
- required dispositions/currentness.

External/manual objects do not need to be silently adopted into current-generation execution lineage for provider flat Position truth to be observed. They do need current classification/reconciliation evidence.

### 5.5 FP-05 close/residual sizing evidence

When a project-r7 close path participated, bind exact current E4 provider-local FP-05 evidence or its authoritative equivalent, including:

- sizing evidence reference/hash;
- exact Position/action/provider observation generation;
- sizing/residual state;
- current provider reducible exposure reference;
- metadata/capability generation where applicable.

FP-05 states are provider-local facts, not lifecycle states.

Relevant meanings include:

- `EXPOSURE_ALREADY_FLAT` — current zero exposure is proven, but E5 lifecycle closure is not emitted by FP-05;
- `RESIDUAL_NONZERO_REPRESENTABLE` — positive exposure remains;
- `RESIDUAL_NONZERO_UNREPRESENTABLE` — positive exposure remains but no safe provider close size is currently representable;
- `RECONCILIATION_REQUIRED` / unknown states — close convergence fails closed.

### 5.6 FP-11 protection evidence and terminal protection bridge

FP-11 is mandatory because flat exposure does not erase provider protection objects.

For an open/reduced Position, bind the current FP-11 registry evidence ref/hash directly.

When a newer provider Position observation establishes flat exposure, that Position change necessarily supersedes FP-11 evidence that was bound to the prior open Position snapshot. Therefore V0.1 requires both:

1. `fp11_prior_registry_evidence_ref/hash` — latest FP-11 evidence that was current for the immediately preceding open/reduced Position lineage, when available; and
2. a fresh **terminal protection observation set** evaluated by FP-10 using the same E4 provider-set completeness/currentness and per-object FP-04 ownership principles established by FP-11.

This is a terminal bridge requested by FP-11 section 21; it does not rewrite FP-11 into a flat-Position registry profile.

`terminal_protection_status` is exactly one of:

- `TERMINAL_PROTECTION_CLEAR`
- `TERMINAL_PROTECTION_PRESENT_CONVERGENCE_REQUIRED`
- `TERMINAL_PROTECTION_OBSERVATION_STALE`
- `TERMINAL_PROTECTION_OBSERVATION_UNKNOWN`

`TERMINAL_PROTECTION_CLEAR` requires all of:

- fresh authoritative flat Position observation already established;
- provider protection observation occurs at or after that flat-observation acceptance boundary;
- observation coverage is complete/current;
- zero current `ACTIVE_PROTECTION` objects relevant to the exact Position/instrument lineage;
- no unresolved FP-04 ownership/conflict evidence for a protection object that could still affect the Position/instrument;
- exact terminal protection set hash/currentness validation succeeds.

Any active orphan/external/prior-generation/multiple/unknown/conflicting protection object after flatness yields `TERMINAL_PROTECTION_PRESENT_CONVERGENCE_REQUIRED` or `UNKNOWN`, never silent cleanup.

FP-10 does not authorize cancel-all, detach, ignore, replace, or provider cleanup.

### 5.7 E5 lifecycle projection / execution binding

Bind exact current:

- lifecycle projection ref/hash/id/revision;
- lifecycle state;
- lifecycle broker-observation anchor;
- lifecycle execution-binding ref/hash;
- execution snapshot hash;
- interpretation time/currentness.

A newer provider Position or newer in-scope execution evidence not covered by the current E5 projection/binding requires fresh E5 interpretation before a prior lifecycle claim remains authoritative.

### 5.8 Runtime/process/config generation

Where runtime participates, bind exact current:

- project revision;
- runtime-preflight ref;
- process instance ID;
- process-start generation;
- runtime-config generation.

A process/config generation change invalidates older convergence authority when those generations materially participate.

Non-runtime deterministic fixtures may set these fields to `null` only when explicitly classified as non-runtime evaluation.

## 6. Convergence state vocabulary

`convergence_state` is exactly one of:

- `EXPOSURE_STILL_OPEN`
- `EXPOSURE_REDUCED_NOT_FLAT`
- `FLAT_PROVIDER_TRUTH_PROVEN`
- `FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED`
- `FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED`
- `EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED`
- `OWNERSHIP_CONFLICT_RECONCILIATION_REQUIRED`
- `RESIDUAL_UNREPRESENTABLE_NOT_FLAT`
- `CONVERGENCE_EVIDENCE_STALE`
- `CONVERGENCE_UNKNOWN`
- `LIFECYCLE_CLOSE_ELIGIBLE`

### 6.1 `EXPOSURE_STILL_OPEN`

Current authoritative Position truth is positive and there is no accepted evidence that the current observation is a reduced residual relative to the exact prior authoritative exposure boundary.

The Position is not flat.

### 6.2 `EXPOSURE_REDUCED_NOT_FLAT`

Current authoritative Position truth is positive and a valid exact prior/current comparison proves exposure was reduced but remains nonzero.

This includes a current representable residual. It is not close eligible.

### 6.3 `FLAT_PROVIDER_TRUTH_PROVEN`

Fresh provider/normalized Position truth proves zero exposure, but one or more downstream convergence checks have not yet established lifecycle-close eligibility.

This is an intermediate state, not a lifecycle transition.

### 6.4 `FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED`

Fresh zero exposure is proven but terminal protection is not clear under section 5.6.

### 6.5 `FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED`

Fresh zero exposure is proven but order/fill/ambiguous-outcome evidence is missing, stale, contradictory, or otherwise capable of invalidating a safe lifecycle interpretation.

### 6.6 `EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED`

Current provider truth changed through external/manual/prior-generation activity and the current E5 lifecycle projection has not yet authoritatively interpreted that exact current evidence generation.

This state does not require silent adoption of external execution lineage.

### 6.7 `OWNERSHIP_CONFLICT_RECONCILIATION_REQUIRED`

FP-04 evidence is conflicting, unknown, stale, or otherwise insufficient for one or more materially relevant provider objects.

### 6.8 `RESIDUAL_UNREPRESENTABLE_NOT_FLAT`

Fresh authoritative Position truth is positive and FP-05 establishes `RESIDUAL_NONZERO_UNREPRESENTABLE` or an equivalent accepted provider-local state.

The residual remains real. It is never rounded/written off to zero.

### 6.9 `CONVERGENCE_EVIDENCE_STALE`

At least one previously valid evidence generation has been superseded by materially newer provider Position, execution/fill, FP-04, FP-05, terminal protection, lifecycle, or runtime/config truth.

### 6.10 `CONVERGENCE_UNKNOWN`

Required convergence evidence or currentness cannot be established safely.

### 6.11 `LIFECYCLE_CLOSE_ELIGIBLE`

Allowed only when the exact flat/converged invariant in section 8 passes.

It is evidence for E5 interpretation only. It does not emit `POSITION_CLOSED`, `RECONCILED_FLAT`, or `CLOSED` and does not create TradeResult authority.

## 7. Required disposition vocabulary

`required_dispositions` is a deterministic sorted sequence containing one or more of:

- `NO_ACTION_LIFECYCLE_CLOSE_ELIGIBLE`
- `FRESH_PROVIDER_POSITION_RECONCILIATION_REQUIRED`
- `EXECUTION_FILL_RECONCILIATION_REQUIRED`
- `OWNERSHIP_RECONCILIATION_REQUIRED`
- `FP05_RESIDUAL_REEVALUATION_REQUIRED`
- `TERMINAL_PROTECTION_CONVERGENCE_REQUIRED`
- `E5_LIFECYCLE_REINTERPRETATION_REQUIRED`
- `E6_CURRENTNESS_REVALIDATION_REQUIRED`
- `MANUAL_REVIEW_REQUIRED`
- `BLOCK_NEW_EXPOSURE`
- `BLOCK_CLOSE_RETRY_MUTATION`
- `BLOCK_UNCERTAIN_PROTECTION_CLEANUP`
- `TRADE_RESULT_EVIDENCE_INCOMPLETE`

Rules:

1. `NO_ACTION_LIFECYCLE_CLOSE_ELIGIBLE` is exclusive.
2. No disposition authorizes provider submit/cancel/amend/close/cleanup.
3. `BLOCK_CLOSE_RETRY_MUTATION` means current convergence evidence cannot authorize another logical close attempt. A future fresh E5 action may be possible only after the required new evidence/policy is established.
4. `TRADE_RESULT_EVIDENCE_INCOMPLETE` may coexist with lifecycle convergence states because lifecycle flatness and final TradeResult fill-set completeness are distinct questions.
5. External/manual execution lineage may remain external while E5 interprets authoritative flat Position truth; the profile never rewrites that lineage into current-generation ownership.

## 8. Exact lifecycle-close eligibility invariant

`LIFECYCLE_CLOSE_ELIGIBLE` requires all of the following simultaneously:

1. exact supported profile/schema versions;
2. fresh authoritative provider Position/exposure observation exists;
3. exact E4-normalized canonical Position is bound to that same current provider truth;
4. canonical current Position proves `actual_quantity=0` and `reconciliation_status=CONSISTENT`;
5. provider/normalized Position identity, instrument, side lineage and observation generation are exact and conflict-free;
6. every materially relevant provider Position/order/fill object has current compatible FP-04 evidence, with no unresolved ownership conflict that can affect the flatness interpretation;
7. any project close path has current compatible FP-05 evidence, and no positive residual state remains;
8. prior ambiguous close outcomes are freshly reconciled;
9. current execution/fill evidence does not contradict the zero-exposure Position truth;
10. terminal protection status is exactly `TERMINAL_PROTECTION_CLEAR`;
11. current lifecycle projection and lifecycle execution binding are exact/current for the evidence generation E5 is about to interpret, or the evidence explicitly routes through a current E5 reconciliation interpretation boundary as defined in section 11;
12. no newer in-scope provider Position, order/fill, FP-04, FP-05, terminal protection, lifecycle, or runtime/config generation is known before evaluation completes;
13. evidence identity/hash/time validation passes.

Canonical rule:

```text
fresh authoritative provider/normalized Position zero-exposure truth
+ current compatible FP-04 ownership/reconciliation evidence
+ no unresolved execution/fill ambiguity that can contradict Position truth
+ current terminal protection convergence derived from FP-11/FP-04 principles
+ current lifecycle/execution-binding references
+ no newer superseding provider/local/runtime truth
= LIFECYCLE_CLOSE_ELIGIBLE evidence for E5
```

This invariant does **not** require the current automation generation to have created the closing provider order. It requires current truth and reconciliation evidence to be explicit and non-contradictory.

## 9. Explicit non-flat rules

Any positive authoritative current Position quantity means not flat.

### 9.1 Representable residual

If current exposure is positive and FP-05 says `RESIDUAL_NONZERO_REPRESENTABLE`, the state is:

```text
EXPOSURE_REDUCED_NOT_FLAT
```

or `EXPOSURE_STILL_OPEN` when no exact reduction comparison exists.

A new close attempt requires fresh E5 authority from the fresh Position observation plus all independent provider/runtime gates. FP-10 does not grant it.

### 9.2 Non-representable residual

If current exposure is positive and FP-05 says `RESIDUAL_NONZERO_UNREPRESENTABLE`:

```text
convergence_state = RESIDUAL_UNREPRESENTABLE_NOT_FLAT
```

Required dispositions include:

- `FP05_RESIDUAL_REEVALUATION_REQUIRED` or `MANUAL_REVIEW_REQUIRED` as current policy supports;
- `BLOCK_NEW_EXPOSURE`;
- `BLOCK_CLOSE_RETRY_MUTATION` on unchanged evidence.

The residual may not be rounded, omitted, deleted, or treated as flat merely because no provider-sized close request can currently represent it.

## 10. External/manual close boundary

External/manual/prior-generation activity is handled in two independent dimensions:

```text
provider Position truth = exposure authority
provider object ownership = FP-04 provenance/reconciliation authority
```

Rules:

1. The current automation does not need to have created the external/manual close order before E4 may observe authoritative provider Position truth.
2. External/manual order/fill objects must still be classified under current FP-04 evidence.
3. External/manual execution is never silently adopted into current-generation OrderRequest/client-order lineage.
4. A familiar symbol/side/quantity/order ID is not adoption proof.
5. Provider flat Position truth may be authoritative exposure truth even while the responsible execution lineage remains `EXTERNAL_UNTRACKED`, `KNOWN_OWNED_PRIOR_GENERATION`, or another current non-conflicting FP-04 classification.
6. If that external/manual truth is newer than the current E5 lifecycle projection/binding, initial convergence state is `EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED`.
7. E5 must freshly interpret the exact current evidence before lifecycle closure may become eligible.
8. Unknown/conflicting/stale FP-04 evidence yields `OWNERSHIP_CONFLICT_RECONCILIATION_REQUIRED`, not close eligibility.
9. External/manual order terminal status alone never closes lifecycle.

V0.1 deliberately does not define a production adoption policy for external/manual execution objects.

## 11. E5 lifecycle reinterpretation boundary

Existing E5 state-machine authority remains unchanged.

This profile does not decide whether a given accepted convergence fact produces:

- `STATE_UNKNOWN` into `RECONCILIATION_REQUIRED`;
- `RECONCILED_FLAT` from `RECONCILIATION_REQUIRED`;
- `POSITION_CLOSED` from an allowed current lifecycle state;
- `EXIT_FAILED` / `EMERGENCY`;
- a re-attestation with unchanged lifecycle state;
- another accepted E5 policy outcome.

### 11.1 Project-owned explicit close path

Where exact current E5 close authority, execution evidence, and flat Position truth are already current and conflict-free, E5 may consume `LIFECYCLE_CLOSE_ELIGIBLE` under existing close/lifecycle rules without inventing an external/manual ownership transition.

### 11.2 External/manual/prior-generation path

When the exposure change is external/manual/prior-generation and newer than current E5 lifecycle interpretation, the first shared outcome is:

```text
EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED
+ E5_LIFECYCLE_REINTERPRETATION_REQUIRED
```

E5 must produce the next authoritative lifecycle interpretation bound to the exact current Position/execution/ownership evidence. The exact transition/re-attestation event remains E5 policy.

After that interpretation is current, the convergence evaluator may produce `LIFECYCLE_CLOSE_ELIGIBLE` if every section 8 condition passes.

This two-step boundary prevents FP-10 from manufacturing `CLOSED` while still allowing external/manual provider flatness to become authoritative lifecycle input.

## 12. Protection convergence after flatness

Flat exposure does not erase conditional/protective provider objects.

Rules:

- prior open-position FP-11 evidence is retained as immutable lineage/history;
- a newer flat Position observation supersedes that prior open-position registry evidence for currentness;
- FP-10 therefore requires the fresh terminal protection observation set from section 5.6;
- any active protection object after flatness remains individually bound to current FP-04 ownership evidence;
- multiple, external, orphan, prior-generation, unknown, or conflicting protection objects remain explicit;
- no blind cancel-all;
- no blind ignore/delete;
- no automatic newest/closest-price selection;
- provider cleanup requires a later exact E4/E5-authorized action tied to current provider object identity/ownership evidence;
- lifecycle close eligibility requires `TERMINAL_PROTECTION_CLEAR`.

This is terminal convergence evidence only. It does not create a provider cleanup action.

## 13. Order / Fill ambiguity boundary

### 13.1 Terminal order but positive Position

```text
close order terminal/FILLED
+ current Position.actual_quantity > 0
-> not flat
-> no lifecycle close eligibility
```

If execution evidence claims full closure while Position remains positive, use `FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED` only if a separate fresh Position observation proves flat; otherwise use `EXPOSURE_STILL_OPEN` / `EXPOSURE_REDUCED_NOT_FLAT` with contradiction reasons.

### 13.2 Flat Position but nonterminal local order

Fresh flat provider Position may be authoritative exposure truth even if a local close order has not yet reached a terminal status.

However the nonterminal/ambiguous execution object must remain explicit. If its unresolved state could imply duplicate mutation, late fill, or inconsistent lineage, convergence state is:

```text
FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED
```

until fresh reconciliation proves the execution evidence is compatible with the flat Position truth.

### 13.3 Fill aggregate contradiction

If current canonical Fill aggregate is greater than, less than, or otherwise incompatible with the exact current Position/execution lineage in a way that cannot be explained by current external/manual FP-04 evidence, fail closed.

### 13.4 Missing external Fill lineage

Provider Position flatness does not require silently inventing canonical project-owned Fill objects for an external/manual close.

But missing/incomplete external execution evidence may prevent `trade-result-v0.1` finalization and may require reconciliation if it can contradict Position truth.

Lifecycle close eligibility and TradeResult eligibility are therefore separate.

## 14. TradeResult boundary

`LIFECYCLE_CLOSE_ELIGIBLE` is **not** `trade-result-v0.1` eligibility.

Existing TradeResult closure rules remain authoritative, including coherent entry/exit Fill sets and quantity conservation when TradeResult is produced.

For external/manual close where canonical project-owned exit Fill lineage is absent or incomplete:

- E5 may still interpret current provider flatness under FP-10 once all lifecycle convergence requirements are satisfied;
- E6 must not fabricate missing Fill/OrderRequest lineage;
- `TRADE_RESULT_EVIDENCE_INCOMPLETE` remains explicit;
- no canonical final TradeResult may be produced until its own existing evidence requirements are satisfied or a later E7 profile explicitly defines external execution accounting semantics.

This preserves financial/audit integrity while allowing the lifecycle to reflect authoritative provider exposure truth.

## 15. Canonical convergence evidence object

Canonical shared object:

```text
ExternalManualCloseLifecycleConvergenceEvidence
```

Required fields:

- `schema_version` — exactly `contracts-v0.1`;
- `external_manual_close_convergence_profile_version` — exactly `external-manual-close-lifecycle-convergence-v0.1`;
- `close_convergence_evidence_id` — deterministic identity from section 20;
- `position_id`;
- `canonical_symbol`;
- `provider_identity_ref`;
- `provider_identity_hash`;
- `provider_instrument_ref`;
- `provider_position_snapshot_ref`;
- `provider_position_snapshot_hash`;
- `provider_position_observation_generation_id`;
- `provider_position_observed_at`;
- `provider_position_received_at`;
- `provider_position_currentness_status` — `CURRENT | STALE | UNKNOWN`;
- `normalized_position_ref`;
- `normalized_position_hash`;
- `normalized_position_broker_state_observed_at`;
- `normalized_position_reconciliation_status`;
- `normalized_actual_quantity` — canonical base-10 decimal string, including `0` when authoritatively flat;
- `normalized_quantity_profile_version`;
- `normalized_quantity_unit`;
- `normalized_quantity_asset`;
- `execution_evidence` — deterministic sequence from section 16;
- `execution_evidence_set_hash`;
- `fp04_ownership_evidence` — deterministic sequence from section 17;
- `fp04_evidence_set_hash`;
- `fp05_close_residual_sizing_ref` — exact current ref when project close path participated, otherwise `null`;
- `fp05_close_residual_sizing_hash` — matching hash or `null`;
- `fp05_residual_state` — exact current provider-local state when applicable, otherwise `NOT_APPLICABLE`;
- `fp11_prior_registry_evidence_ref` — latest prior open/reduced Position FP-11 evidence when available, otherwise `null` with reason;
- `fp11_prior_registry_evidence_hash` — matching hash or `null`;
- `terminal_protection_observation_ref`;
- `terminal_protection_observation_hash`;
- `terminal_protection_observed_at`;
- `terminal_protection_received_at`;
- `terminal_protection_status` — section 5.6 vocabulary;
- `lifecycle_projection_ref`;
- `lifecycle_projection_hash`;
- `lifecycle_projection_id`;
- `lifecycle_revision`;
- `lifecycle_state`;
- `lifecycle_execution_binding_ref`;
- `lifecycle_execution_binding_hash`;
- `lifecycle_execution_snapshot_hash`;
- `current_project_revision`;
- `runtime_preflight_ref` — nullable only for non-runtime deterministic evaluation;
- `runtime_process_instance_id` — nullable under the same rule;
- `runtime_process_start_generation_id` — nullable under the same rule;
- `runtime_config_generation_id` — nullable under the same rule;
- `exposure_change_origin_classification` — `CURRENT_GENERATION_PROJECT | PRIOR_GENERATION_PROJECT | EXTERNAL_MANUAL | MIXED_OR_UNKNOWN`;
- `convergence_state`;
- `required_dispositions`;
- `reason_codes`;
- `supersedes_close_convergence_evidence_id` — prior evidence for same Position lineage when known, otherwise `null`;
- `evaluated_at` — RFC 3339 UTC after all bound currentness decisions.

No API key, secret, provider credential, raw private payload, account balance, local filesystem path, shell command, or provider auth material belongs in this evidence.

## 16. Canonical execution evidence sequence

`execution_evidence` contains one item per materially relevant order/fill/reconciliation evidence unit and is sorted lexicographically by:

```text
(evidence_class, owner, evidence_ref, evidence_hash)
```

Each item contains:

- `owner` — normally `E4`, or `E5` only for exact interpreted binding references;
- `evidence_class` — `ORDER_REQUEST | ORDER_RESULT_SET | FILL_SET | AMBIGUOUS_OUTCOME_RECONCILIATION | EXTERNAL_EXECUTION_OBSERVATION | OTHER_ACCEPTED_CLOSE_EVIDENCE`;
- `evidence_ref`;
- `evidence_hash`;
- `evidence_generation_id`;
- `latest_observed_at`;
- `currentness_status` — `CURRENT | STALE | CONFLICT | UNKNOWN`;
- `position_compatibility_status` — `COMPATIBLE | CONTRADICTS | UNKNOWN`;
- `lineage_origin` — `CURRENT_GENERATION_PROJECT | PRIOR_GENERATION_PROJECT | EXTERNAL_MANUAL | UNKNOWN`.

The full sequence is hashed into `execution_evidence_set_hash`.

A later/new/different relevant OrderResult, Fill, reconciliation result, or external execution observation changes the set and invalidates prior convergence evidence.

## 17. Canonical FP-04 evidence sequence

`fp04_ownership_evidence` is sorted lexicographically by:

```text
(provider_object_class, provider_object_ref, ownership_evidence_ref)
```

Each item contains:

- `provider_object_class`;
- `provider_object_ref`;
- `provider_snapshot_hash`;
- `ownership_evidence_ref`;
- `ownership_evidence_hash`;
- `ownership_classification`;
- `ownership_reconciliation_status`;
- `ownership_currentness_status` — `CURRENT | STALE | CONFLICT | UNKNOWN`.

Relevant classes may include `POSITION_EXPOSURE`, `OPEN_ORDER`, `TERMINAL_ORDER`, `FILL_EXECUTION`, and `ACTIVE_PROTECTION`.

External/manual classification is permitted as provenance. Unknown/conflicting/stale classification is not lifecycle-close eligible.

The full sequence is hashed into `fp04_evidence_set_hash`.

## 18. Stable fail-closed reason vocabulary

Reason codes are emitted in this deterministic order when applicable:

1. `CLOSE_CONVERGENCE_PROFILE_UNSUPPORTED`
2. `PROVIDER_POSITION_EVIDENCE_MISSING`
3. `PROVIDER_POSITION_EVIDENCE_STALE`
4. `PROVIDER_NORMALIZED_POSITION_MISMATCH`
5. `POSITION_RECONCILIATION_NOT_CONSISTENT`
6. `POSITIVE_EXPOSURE_REMAINS`
7. `RESIDUAL_NONZERO_REPRESENTABLE`
8. `RESIDUAL_NONZERO_UNREPRESENTABLE`
9. `TERMINAL_ORDER_WITHOUT_FLAT_POSITION_PROOF`
10. `PRIOR_CLOSE_OUTCOME_RECONCILIATION_REQUIRED`
11. `EXECUTION_EVIDENCE_MISSING_OR_UNKNOWN`
12. `EXECUTION_FILL_POSITION_CONTRADICTION`
13. `EXTERNAL_MANUAL_EXECUTION_OBSERVED`
14. `FP04_OWNERSHIP_EVIDENCE_MISSING`
15. `FP04_OWNERSHIP_EVIDENCE_STALE`
16. `FP04_OWNERSHIP_CONFLICT`
17. `FP04_EXTERNAL_MANUAL_REINTERPRETATION_REQUIRED`
18. `FP05_RESIDUAL_EVIDENCE_MISSING_OR_STALE`
19. `FP05_RESIDUAL_STATE_CONTRADICTS_POSITION`
20. `FP11_PRIOR_REGISTRY_EVIDENCE_MISSING_OR_STALE`
21. `TERMINAL_PROTECTION_OBSERVATION_MISSING_OR_STALE`
22. `TERMINAL_PROTECTION_OBJECT_PRESENT`
23. `TERMINAL_PROTECTION_OWNERSHIP_CONFLICT`
24. `LIFECYCLE_PROJECTION_STALE_OR_MISMATCHED`
25. `LIFECYCLE_EXECUTION_BINDING_STALE_OR_MISMATCHED`
26. `EXTERNAL_MANUAL_LIFECYCLE_REINTERPRETATION_REQUIRED`
27. `RUNTIME_GENERATION_STALE_OR_MISMATCHED`
28. `CONVERGENCE_EVIDENCE_SUPERSEDED`
29. `CONVERGENCE_EVIDENCE_IDENTITY_INVALID`
30. `CONVERGENCE_TEMPORAL_ORDER_INVALID`
31. `TRADE_RESULT_EVIDENCE_INCOMPLETE`
32. `TERMINAL_PROTECTION_CLEAR`
33. `LIFECYCLE_CLOSE_ELIGIBLE_PROVEN`

Rules:

- `LIFECYCLE_CLOSE_ELIGIBLE_PROVEN` is the only success reason for `convergence_state=LIFECYCLE_CLOSE_ELIGIBLE` and appears alone.
- `TERMINAL_PROTECTION_CLEAR` is an intermediate positive fact and does not by itself make the overall evidence successful.
- `TRADE_RESULT_EVIDENCE_INCOMPLETE` may remain after lifecycle convergence and must not be hidden merely because exposure is flat.
- unknown required reason values fail closed.

## 19. Deterministic evaluation order

Evaluate in this order:

1. validate profile/schema and canonical identity shapes;
2. validate exact provider Position observation/currentness;
3. bind exact normalized canonical Position to the same provider truth;
4. if Position evidence is stale/unknown -> `CONVERGENCE_EVIDENCE_STALE | CONVERGENCE_UNKNOWN`;
5. if `actual_quantity > 0`, classify open/reduced/residual state before considering flatness;
6. validate prior ambiguous close reconciliation;
7. validate current execution/fill evidence set against current Position truth;
8. validate all materially relevant FP-04 evidence;
9. validate FP-05 when a project close path participated;
10. for flat exposure, validate fresh post-flat terminal protection observation and FP-04 ownership of every active protection object;
11. validate current E5 lifecycle projection and lifecycle execution binding;
12. validate runtime/process/config generation when applicable;
13. reject any known newer superseding evidence;
14. emit the most specific fail-closed convergence state;
15. emit `LIFECYCLE_CLOSE_ELIGIBLE` only if section 8 passes completely.

Precedence when multiple failures apply:

```text
OWNERSHIP_CONFLICT_RECONCILIATION_REQUIRED
> CONVERGENCE_EVIDENCE_STALE
> CONVERGENCE_UNKNOWN
> RESIDUAL_UNREPRESENTABLE_NOT_FLAT
> EXPOSURE_STILL_OPEN / EXPOSURE_REDUCED_NOT_FLAT
> FLAT_BUT_EXECUTION_OR_FILL_RECONCILIATION_REQUIRED
> FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED
> EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED
> FLAT_PROVIDER_TRUTH_PROVEN
> LIFECYCLE_CLOSE_ELIGIBLE
```

This precedence is deterministic evidence routing only. It is not lifecycle policy.

## 20. Evidence identity / immutability

`close_convergence_evidence_id` is deterministic over the complete canonical evidence payload except the ID field itself.

Algorithm:

1. remove `close_convergence_evidence_id`;
2. serialize all remaining fields as canonical UTF-8 JSON with lexicographically sorted keys and compact separators;
3. financial decimals remain base-10 decimal strings;
4. timestamps remain RFC 3339 UTC `Z`;
5. deterministic sequences are pre-sorted as specified;
6. compute SHA-256;
7. prefix the lowercase hex digest with:

```text
extcloseconv_
```

Rules:

```text
same exact evidence -> same ID
any provider/local/currentness/result change -> different ID
same ID + different payload -> conflict/corrupt evidence
```

Evidence is immutable. It is never rewritten to claim later provider truth.

## 21. Temporal ordering and currentness

`evaluated_at` is captured after every evidence family required for that evaluation has been accepted/currentness-classified.

At minimum:

```text
evaluated_at >= provider_position_received_at
evaluated_at >= terminal_protection_received_at when terminal protection is evaluated
evaluated_at >= latest accepted local reconciliation/currentness decision time
```

Provider source timestamps remain E4/provider facts; V0.1 does not invent a second provider clock-skew threshold.

Any materially newer evidence known before the consuming E5 decision invalidates old convergence evidence, including:

- provider Position/exposure snapshot;
- normalized Position observation;
- OrderResult/Fill/reconciliation evidence;
- FP-04 ownership evidence;
- FP-05 residual-sizing evidence;
- provider protection set / terminal protection observation;
- lifecycle projection;
- lifecycle execution binding;
- runtime/process/config generation.

A later `evaluated_at` with identical stale inputs does not refresh authority.

## 22. Explicit rejected shortcuts

The following can never produce `LIFECYCLE_CLOSE_ELIGIBLE` by themselves:

- close request submitted;
- close ACK received;
- close OrderResult terminal;
- close OrderResult `FILLED`;
- requested close quantity equals prior Position quantity;
- local arithmetic remainder equals zero;
- current local Position row missing;
- pending-order query returns zero;
- no recent fill found;
- FP-05 requested/effective close size equals prior exposure;
- prior lifecycle state already says `CLOSED` without current provider truth;
- prior FP-11 registry says converged before the Position became flat;
- external/manual order resembles project-r7 lineage;
- provider Position row omitted without an accepted provider-flat representation rule;
- TradeResult arithmetic happens to balance.

## 23. Deterministic future implementation/test handoff

Future executable implementation remains separate. Minimum credential-free fixtures must prove:

1. terminal close order + positive Position -> not eligible;
2. positive Position after partial reduction -> `EXPOSURE_REDUCED_NOT_FLAT`;
3. FP-05 `RESIDUAL_NONZERO_REPRESENTABLE` -> not eligible;
4. FP-05 `RESIDUAL_NONZERO_UNREPRESENTABLE` -> `RESIDUAL_UNREPRESENTABLE_NOT_FLAT`, no write-off/retry authority;
5. exact fresh flat Position + compatible current execution evidence + terminal protection clear -> eligible only after all other currentness requirements pass;
6. flat Position + orphan/external/multiple active protection -> `FLAT_BUT_PROTECTION_CONVERGENCE_REQUIRED`;
7. external/manual flat Position -> `EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED` until fresh E5 interpretation;
8. external/manual flat does not create current-generation execution ownership;
9. manual partial reduction remains open/reinterpreted, never closed;
10. ambiguous prior close result -> execution reconciliation required;
11. order/fill/Position contradiction -> fail closed;
12. flat Position + nonterminal/ambiguous local order -> reconciliation required when contradiction/late-effect risk remains;
13. newer provider Position invalidates old evidence;
14. newer FP-04 evidence invalidates old evidence;
15. newer FP-05 residual evidence invalidates old evidence;
16. changed terminal protection set invalidates old evidence;
17. newer lifecycle projection/binding invalidates old evidence;
18. stale runtime/process/config generation invalidates old evidence when applicable;
19. missing local Position row never means flat;
20. no pending order never means flat;
21. lifecycle close eligibility remains separate from TradeResult eligibility;
22. all deterministic fixtures use zero provider/network/credential access.

Suggested smallest future ownership boundaries:

### E4

Implement a provider-neutral normalized convergence input producer plus provider-specific adapters later, using exact current provider Position/order/fill/FP-05 facts. Provider-specific mutation remains out of scope until separately authorized.

### E5

Implement the bounded convergence consumer that interprets exact FP-10 evidence into existing lifecycle transitions/reattestations without changing state-machine ownership.

### E6

Persist FP-10 immutable evidence, validate identity/currentness/references, and prevent stale lifecycle/current-state claims from becoming restart-authoritative.

### E7

Add cross-module integration/E2E/safety definitions for project-owned close, manual partial reduction, manual flat, ambiguous close, residual-unrepresentable, orphan protection after flat, restart/currentness, and TradeResult separation.

Executable changes require fresh approved-local credential-free qualification on the exact integrated candidate.

## 24. Relationship to LF gates

### LF-2 — P0 failure-prevention closure

This profile closes FP-10 **design semantics only**.

```text
FP-10 contract/design = DEFINED
FP-10 executable implementation = NOT_STARTED
LF-2 = not PASS from this profile
```

### LF-3 — failure injection / recovery

Future local-only failure-injection must include:

- terminal-order/positive-Position contradiction;
- manual partial reduction;
- manual flat;
- ambiguous close result;
- representable/unrepresentable residual;
- orphan/multiple protection after flat;
- stale ownership/lifecycle/runtime evidence.

This task executes none of it.

### LF-4 — provider read-only verification

Later provider read-only verification must prove current Position/order/fill/protection observation semantics for the exact candidate under separate Product Owner authority. Historical provider evidence does not transfer.

### LF-5 — SHADOW/PAPER readiness

Future runtime readiness must consume current FP-10 convergence evidence during restart/reconciliation and must not restart from stale `CLOSED`/protected assumptions.

### LF-6 — bounded live-fire authorization

No bounded live-fire authority is created. Technical completion of FP-10 later remains only one prerequisite before a separate Product Owner authorization could be considered.

## 25. Unresolved provider-specific facts

The following remain E4/provider capability dependencies and are not guessed by this shared profile:

- exact OKX close endpoint/field set for `POSITION_EXIT` / `EMERGENCY_EXIT`;
- role/mode-specific `posSide` semantics;
- provider-native reduce-only behavior;
- close-specific lot/minimum/maximum/special dust/full-close behavior;
- exact provider Position zero-row/omission representation semantics;
- provider behavior for external/manual fills and terminal order history completeness;
- provider behavior for conditional/protective objects after Position reaches zero;
- provider timing/order guarantees between Position, fill, order, and protection readback endpoints.

Unknown provider-specific facts remain fail closed until E4 proves them under accepted capability/provider evidence.

## 26. Recommended next Worker tasks — not issued here

Recommended bounded follow-ups after PM review:

1. E5/E4/E6 implementation tasks for accepted FP-04 ownership evidence and FP-10 convergence composition using deterministic fixtures only;
2. E4 provider-local FP-05 implementation after accepted capability semantics are executable-ready;
3. E4/E6/E5 FP-11 executable registry implementation;
4. E7 integrated FP-04/05/10/11/16 deterministic safety definitions after owner implementations exist;
5. one fresh approved-local full credential-free qualification on the exact integrated P0 candidate after executable work is intentionally assembled.

No Worker task is issued by this document.

## 27. Verification / authority boundary

For decision task `E7-20260829-109`:

```text
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
FP-03 combined qualification = NOT_RUN / NOT_PASS
Gate D / LIVE = BLOCKED / UNAUTHORIZED
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

`NOT_RUN` is not executable PASS.

The active LF-0 exact-revision preparation blocker for `9462b2594675b2e28388f55a2af189100b7cbdfc` remains unchanged. Historical qualification/provider evidence is not rebound.
