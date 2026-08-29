# OKX SWAP Close / Residual Sizing — V0.1

> Profile identifier: `okx-swap-close-residual-sizing-v0.1`  
> Owner: E4 Trading Execution / Broker Integration  
> Task: `E4-20260829-028`  
> Baseline `main`: `466b167e32fc84e1906e0e80bae7c55e31a517fc`  
> Status: `DESIGN BASELINE / DOCS ONLY / NOT EXECUTABLE AUTHORITY`

## 1. Purpose

This document defines the E4-owned provider-local sizing and residual-state model for future OKX `BTC-USDT-SWAP` `POSITION_EXIT` and `EMERGENCY_EXIT` translation.

It closes only the FP-05 **design** gap. It does not implement provider translation, provider-native close sizing, a close endpoint, a provider `reduceOnly` mapping, or any runtime/provider action.

The safety objective is:

```text
fresh E5 close authority
+ exact current canonical Position truth
+ exact current provider reducible-exposure truth
+ current FP-04 ownership/reconciliation truth
+ accepted FP-02 action-role capability row
+ current close-applicable provider metadata
-> one deterministic provider-local sizing evaluation
-> at most the authoritative reducible exposure
-> explicit residual state after fresh provider observation

anything missing / stale / conflicting / unproven / unrepresentable
-> fail closed
```

The following are never close-quantity authority:

- original requested ENTRY quantity;
- original ApprovedTradePlan maximum quantity by itself;
- stale local Position quantity;
- requested quantity from a prior close request;
- arithmetic remainder from a prior request;
- an OrderResult status such as `FILLED`;
- a caller-provided `reduce_only=true` flag;
- a caller assertion that an OKX field combination is supported;
- entry-specific sizing compatibility by analogy.

Only fresh authoritative Position/provider truth may establish remaining exposure or flatness.

## 2. Provider target and authority baseline

Current bounded identity:

```text
provider                 = OKX
api_version              = V5
canonical instrument     = BTC_USDT_PERP
provider instrument      = BTC-USDT-SWAP
provider instrument type = SWAP
canonical quantity       = base-asset-v0.1 / BASE_ASSET / BTC
margin baseline          = isolated
FP-02 profile            = okx-swap-action-role-capability-v0.1
```

Shared authority remains unchanged:

- E5 owns `close-v0.1` PositionAction authority, lifecycle/risk interpretation, and the canonical quantity it authorizes.
- E4 owns actual broker/provider order, fill, position/exposure, provider sizing, provider reconciliation, and provider-specific translation truth.
- E6 may persist/audit canonical and provider evidence but does not redefine quantity/lifecycle semantics.
- E7 owns shared contracts/profiles and release interpretation.

This profile is E4/provider-local. No `contracts/**` change is required by this design.

## 3. Existing repository evidence and deliberate non-inference

### 3.1 Repository-evidenced canonical close semantics

The accepted `close-v0.1` profile and current E4 close consumer already require:

```text
PositionAction.action = EXIT | EMERGENCY_EXIT
PositionAction.quantity = exact current Position.actual_quantity
Position.reconciliation_status = CONSISTENT
OrderRequest.quantity = exact PositionAction.quantity
OrderRequest.reduce_only = true
LONG Position -> SELL
SHORT Position -> BUY
order_type = MARKET
```

The current E4 close consumer also rejects stale/mismatched Position observations, incompatible quantity profile/unit/asset, expired close authority, and a close quantity that differs from exact current `Position.actual_quantity`.

This means canonical close quantity authority is already **current Position exposure**, not original entry request size.

### 3.2 Repository-evidenced OKX instrument/entry sizing facts

Current `src/brokers/okx_sizing.py` has a deterministic linear SWAP **ENTRY** conversion path using:

- `instId = BTC-USDT-SWAP`;
- `instType = SWAP`;
- `ctType = linear`;
- `ctVal`;
- `ctMult`;
- `ctValCcy = BTC`;
- `lotSz`;
- `minSz`;
- `maxMktSz` when present;
- instrument `state`;
- metadata reference, observation time and versioned freshness policy;
- scheduled metadata-change guards.

For that entry path:

```text
base_per_contract = ctVal * ctMult
raw_contracts     = canonical_BTC / base_per_contract
provider_sz       = floor(raw_contracts / lotSz) * lotSz
effective_BTC     = provider_sz * base_per_contract
```

and provider exposure may never exceed the E5-approved canonical entry bound.

### 3.3 Facts that are NOT proven for close roles

The current repository does **not** prove that ENTRY-specific provider sizing rules are sufficient or identical for `POSITION_EXIT` / `EMERGENCY_EXIT`.

Therefore V0.1 does not assume that any of these entry facts automatically authorize close translation:

- the ENTRY provider field set;
- ENTRY `posSide` mapping;
- provider-native `reduceOnly` presence/value/omission;
- `minSz` applicability to reduction/close;
- `maxMktSz` applicability to reduction/close;
- whether a distinct provider close/reduce limit exists;
- whether a below-entry-minimum residual is still provider-closeable under a special rule;
- whether a special provider full-close mechanism exists;
- whether a special dust/force-close mechanism exists;
- any alternate close endpoint;
- any automatic position flattening semantics from order status.

Unproven close-specific facts remain fail closed until an accepted E4 capability/metadata row proves them.

## 4. Quantity-authority hierarchy

A future E4 close-sizing evaluator must process quantity authority in this exact precedence order. A lower layer cannot override a contradiction at a higher layer.

### Layer 1 — E5 canonical close authority

Input:

```text
close-v0.1 PositionAction.EXIT | EMERGENCY_EXIT
```

Required canonical facts include:

- `position_action_id`;
- `position_id`;
- exact `position_observed_at`;
- `position_reconciliation_status = CONSISTENT`;
- `quantity_profile_version = base-asset-v0.1`;
- `quantity_unit = BASE_ASSET`;
- `quantity_asset = BTC`;
- positive finite canonical `quantity`;
- action freshness;
- exact parent-plan/risk lineage.

This is E5 action authority, not provider-size authority.

### Layer 2 — exact current normalized canonical Position exposure

E4 must bind the action to the exact current normalized Position observation:

```text
PositionAction.position_id          == Position.position_id
PositionAction.position_observed_at == Position.broker_state_observed_at
PositionAction.quantity             == Position.actual_quantity
Position.reconciliation_status      == CONSISTENT
```

A newer Position observation invalidates the older action for a new residual close. E4 does not reduce the old action quantity opportunistically; E5 must issue fresh close authority from the new Position observation.

### Layer 3 — exact current provider-native reducible exposure

Before provider-native sizing, E4 must have one exact current provider Position/exposure snapshot for the supported provider capability row.

The provider-local representation must bind at minimum:

- provider identity/environment reference;
- provider instrument `BTC-USDT-SWAP`;
- exact provider observation generation;
- provider observation/source time;
- account level;
- position mode;
- margin mode;
- provider position-side identity required by the accepted FP-02 row;
- signed/absolute provider-native exposure quantity as defined by that accepted row;
- exact normalized canonical Position observation derived/reconciled from the same current provider truth;
- FP-04 ownership/reconciliation evidence for the exposure when ownership materially affects whether automation may close it.

If exact provider-native reducible exposure cannot be established, state is `REDUCIBLE_EXPOSURE_UNKNOWN` or `RECONCILIATION_REQUIRED`; no provider quantity is produced.

### Layer 4 — close-applicable instrument metadata

The evaluator must bind one exact current metadata generation suitable for the **close role**, not merely an entry cache.

At minimum the future provider-local evidence must identify:

- metadata profile/policy version;
- metadata reference/generation;
- metadata observed-at time;
- provider/instrument identity;
- instrument type/state;
- conversion facts sufficient to trace provider contracts to canonical BTC;
- role-specific close lot/step/minimum/maximum applicability proof;
- any scheduled metadata change relevant to close sizing;
- the freshness classification at calculation time.

If role-specific applicability of a required constraint is unknown, state is `METADATA_STALE_OR_UNKNOWN` and close sizing fails closed.

### Layer 5 — provider lot/minimum/step/maximum constraints

Only constraints explicitly proven applicable to the accepted close capability row may participate.

The evaluator must never substitute:

```text
ENTRY minSz/maxMktSz evidence
```

for:

```text
POSITION_EXIT / EMERGENCY_EXIT close-limit authority
```

without an accepted role-specific proof.

### Layer 6 — quantized provider-native requested close size

After Layers 1-5 are mutually current and consistent, the evaluator may calculate one provider-native requested close size.

Required invariants:

```text
provider_requested_close_size > 0
provider_requested_close_size <= authoritative provider reducible exposure
provider_effective_canonical_BTC <= E5-authorized current canonical close quantity
provider_effective_canonical_BTC <= exact current Position.actual_quantity
provider_requested_close_size satisfies every accepted close-specific step/lot constraint
provider_requested_close_size satisfies every accepted close-specific min/max constraint
```

Rounding upward beyond authoritative reducible exposure is forbidden.

### Layer 7 — post-action provider observation

A requested or acknowledged close size never establishes actual residual.

After any future close attempt, the next residual evaluation begins from a **new authoritative provider Position observation** and a newly normalized canonical Position observation.

Only that observation may establish:

- still-positive residual exposure;
- changed reducible exposure;
- authoritative flat exposure.

### Layer 8 — residual representability state

Positive residual truth is classified using the new provider Position observation plus a current accepted close capability/metadata generation.

Residual state is evidence/routing only. It does not itself authorize another close request.

## 5. Provider-local sizing evidence envelope

A later executable implementation should produce an immutable E4-local evidence object equivalent to:

```text
OKXCloseResidualSizingEvidence
```

Suggested provider-local fields:

- `close_residual_sizing_profile_version = okx-swap-close-residual-sizing-v0.1`;
- `sizing_evidence_id` — deterministic content-derived identity;
- `action_role = POSITION_EXIT | EMERGENCY_EXIT`;
- `position_action_id`;
- `position_id`;
- `canonical_position_observed_at`;
- `canonical_authorized_close_quantity`;
- `quantity_profile_version`;
- `quantity_unit`;
- `quantity_asset`;
- `fp02_capability_profile_version`;
- `fp02_capability_row_ref`;
- `provider_identity_ref`;
- `provider_instrument_id`;
- `account_level`;
- `position_mode`;
- `margin_mode`;
- `provider_position_snapshot_ref`;
- `provider_position_snapshot_hash`;
- `provider_position_observation_generation_id`;
- `provider_position_observed_at`;
- `provider_reducible_quantity`;
- `provider_reducible_quantity_unit`;
- `fp04_ownership_evidence_ref` when required;
- `fp04_ownership_classification`;
- `fp04_reconciliation_status`;
- `instrument_metadata_ref`;
- `instrument_metadata_generation`;
- `instrument_metadata_observed_at`;
- `instrument_metadata_freshness_policy_version`;
- `conversion_profile`;
- accepted conversion facts (`ctVal`, `ctMult`, `ctValCcy`, `ctType`) when role-applicable;
- accepted close step/lot/min/max facts and their applicability proof reference;
- `raw_provider_close_size` when calculable;
- `quantized_provider_close_size` when calculable;
- `effective_canonical_close_quantity` when calculable;
- `sizing_state`;
- deterministic `reason_codes`;
- `evaluated_at`.

This object is E4 provider evidence, not shared risk/lifecycle authority. A caller-created clone, mapping, boolean or claimed capability must not be accepted as mutation authority.

## 6. Residual-state vocabulary

The stable provider-local state vocabulary is:

| State | Meaning | Mutation implication |
|---|---|---|
| `FULLY_REDUCIBLE` | Exact current positive exposure is fully representable by one accepted close-size request under current capability/metadata evidence. | Sizing is representable only; separate action/provider/runtime authority is still required. |
| `PARTIALLY_REDUCIBLE` | A positive valid close size is representable, but it is strictly smaller than exact current authoritative reducible exposure. | At most that bounded size may be materialized later; no arithmetic assumption about residual flatness. |
| `RESIDUAL_NONZERO_REPRESENTABLE` | A fresh post-action provider Position observation proves positive residual, and current capability/metadata can represent a positive later close size. | Requires a fresh E5 PositionAction from the fresh Position observation before another mutation. |
| `RESIDUAL_NONZERO_UNREPRESENTABLE` | A fresh provider Position observation proves positive residual, but no positive provider close size is valid under current accepted close constraints. | Stable fail-closed residual; no immediate retry. |
| `EXPOSURE_ALREADY_FLAT` | Fresh authoritative provider/normalized Position truth proves zero exposure with reconciliation consistency. | No close request may be created from this state. It does not itself emit E5 `CLOSED`. |
| `REDUCIBLE_EXPOSURE_UNKNOWN` | Exact provider-native reducible exposure or its binding to current Position/ownership is unavailable. | Fail closed; refresh/reconcile first. |
| `METADATA_STALE_OR_UNKNOWN` | Required close-applicable metadata is stale, missing, conflicting, or applicability is unproven. | Fail closed; refresh/prove metadata first. |
| `RECONCILIATION_REQUIRED` | Prior outcome is ambiguous or current canonical/provider/execution/ownership evidence conflicts. | Query/reconcile; blind retry forbidden. |
| `CLOSE_CAPABILITY_UNPROVEN` | FP-02 role/account/position/margin/provider field row is not accepted for the exact close role. | No provider translation/dispatch, regardless of urgency. |

These are E4 provider-local states, not new E5 lifecycle states and not E7 shared-contract enums.

## 7. Deterministic evaluation order

A future evaluator should apply the following precedence so one failure cannot be accidentally hidden by a later arithmetic result.

1. **Action profile/role validation.** Require exact `close-v0.1` EXIT or EMERGENCY_EXIT authority.
2. **Current canonical Position binding.** Require the exact Position observation/action quantity equality and `CONSISTENT` reconciliation.
3. **Prior-outcome ambiguity check.** Any unresolved prior logical close -> `RECONCILIATION_REQUIRED` before new sizing.
4. **FP-04 ownership/currentness check.** Unknown/conflicting/external exposure without accepted disposition -> `REDUCIBLE_EXPOSURE_UNKNOWN` or `RECONCILIATION_REQUIRED`.
5. **Authoritative provider Position check.** If provider position truth is unknown -> `REDUCIBLE_EXPOSURE_UNKNOWN`. If fresh authoritative truth proves zero -> `EXPOSURE_ALREADY_FLAT`.
6. **Canonical/provider exposure binding.** Positive provider exposure must reconcile exactly to the current normalized Position under the accepted conversion. Contradiction -> `RECONCILIATION_REQUIRED`.
7. **FP-02 role capability resolution.** Unaccepted role/mode/margin/provider field combination -> `CLOSE_CAPABILITY_UNPROVEN`.
8. **Metadata/currentness validation.** Missing/stale/unproven close-applicable metadata -> `METADATA_STALE_OR_UNKNOWN`.
9. **Representability calculation.** Compute only from exact current authority and accepted close constraints.
10. **Classify pre-action representability.** Exact full size -> `FULLY_REDUCIBLE`; positive strict subset -> `PARTIALLY_REDUCIBLE`; no positive valid size -> `RESIDUAL_NONZERO_UNREPRESENTABLE` for a positive current residual/exposure.
11. **After any future mutation, discard arithmetic residual as authority.** Wait for fresh provider Position truth.
12. **Re-evaluate fresh residual.** Positive fresh residual -> `RESIDUAL_NONZERO_REPRESENTABLE` or `RESIDUAL_NONZERO_UNREPRESENTABLE`; zero fresh residual -> `EXPOSURE_ALREADY_FLAT`.

## 8. Conversion and quantization rule

### 8.1 Conversion authority

The current repository proves a direct linear BTC conversion for the bounded instrument in the existing sizing implementation:

```text
base_per_contract = ctVal * ctMult
```

For FP-05, those conversion facts may be reused only after the future close capability/metadata boundary proves that the same instrument-unit conversion is valid for the exact close role and current provider Position representation.

The provider-position quantity unit and sign semantics must be explicit for the exact position mode. They may not be guessed from ENTRY `side`/`posSide` rules.

### 8.2 Generic safe bound

Once close-role conversion and constraints are proven, the target native amount must be bounded by both current canonical authority and current provider reducible exposure.

Conceptually:

```text
canonical_target_BTC = exact current Position.actual_quantity
native_bound_from_canonical = canonical_target_BTC / base_per_contract
native_reducible_bound = exact current provider reducible exposure in accepted native units
native_upper_bound = min(native_bound_from_canonical, native_reducible_bound)
```

The provider request must be the largest **accepted close-representable** positive size not exceeding `native_upper_bound`.

If the accepted close step is `close_step`:

```text
candidate = floor(native_upper_bound / close_step) * close_step
```

This formula is design vocabulary only. `close_step`, close minimum and close maximum must come from role-applicable accepted provider evidence; V0.1 does not equate them automatically with ENTRY `lotSz`, `minSz`, or `maxMktSz`.

### 8.3 Hard invariants

Reject when:

- candidate is zero or negative;
- candidate exceeds exact native reducible exposure;
- candidate converts to canonical BTC above current Position/E5 close authority;
- candidate violates an accepted close step/min/max rule;
- conversion facts are stale/unknown/conflicting;
- provider Position quantity unit/sign cannot be proven;
- close capability row is unresolved.

No rounding-up exception exists for EMERGENCY_EXIT.

## 9. Residual behavior and retry discipline

### 9.1 Residual is provider truth, not subtraction authority

The system may calculate an **expected/projected** remainder for diagnostics, but it must never use:

```text
old_position_quantity - requested_close_quantity
```

as authoritative current residual after provider interaction.

Actual residual must come from a later current provider Position observation normalized by E4.

### 9.2 Representable positive residual

If fresh provider/Position truth proves a positive residual and current close metadata can represent a positive valid size:

```text
RESIDUAL_NONZERO_REPRESENTABLE
```

A later close requires:

- materially newer/current provider Position evidence;
- corresponding current normalized Position;
- a new/fresh applicable E5 close PositionAction bound to that Position observation;
- current FP-04 reconciliation truth;
- current FP-02 capability proof;
- current close metadata evidence;
- no unresolved prior-order ambiguity.

The old PositionAction cannot simply be replayed for the residual because `close-v0.1` identity/quantity binds to the old Position observation.

### 9.3 Unrepresentable positive residual

If fresh authoritative exposure is positive but no positive close size is valid under current accepted close constraints:

```text
RESIDUAL_NONZERO_UNREPRESENTABLE
```

This is a stable fail-closed state.

The following are forbidden:

- tight polling that repeatedly creates the same close request;
- repeatedly reusing the same PositionAction;
- rounding the residual down to zero in canonical state;
- declaring Position flat;
- inventing a dust writeoff;
- inventing a force-close endpoint;
- inventing transfer/margin adjustments;
- increasing size above actual reducible exposure;
- switching to Spot/cash semantics.

A new sizing evaluation is meaningful only after material evidence changes, for example:

- new provider Position observation/generation;
- new provider metadata generation;
- new accepted capability evidence;
- resolved FP-04 ownership/reconciliation evidence;
- fresh E5 close authority bound to the new Position.

Unchanged evidence must produce the same stable state and no new mutation.

### 9.4 Ambiguous provider outcome

Timeout, malformed acknowledgement, unknown acceptance, or any outcome that may have changed exposure but is not proven maps to:

```text
RECONCILIATION_REQUIRED
```

E4 must query/reconcile the same logical close before any new request. A second blind close is forbidden.

## 10. `EXPOSURE_ALREADY_FLAT` boundary

`EXPOSURE_ALREADY_FLAT` requires authoritative provider/normalized Position truth equivalent to:

```text
same intended position/instrument scope
actual exposure = 0
reconciliation/currentness = accepted/consistent
observation is current and later than any execution evidence that must be covered
```

The following are insufficient:

- provider ACK;
- terminal order status;
- `OrderResult.FILLED`;
- sum of requested quantities;
- sum of locally expected fills without current Position truth;
- old Position minus requested close size = zero;
- local lifecycle already saying `CLOSED`;
- absence of a local Position row;
- caller statement that provider is flat.

FP-05 does not emit E5 lifecycle `CLOSED` and does not build TradeResult.

## 11. Metadata and currentness requirements

### 11.1 Minimum identity/currentness evidence

Before provider-native close quantity can be calculated, future E4 implementation must bind:

```text
provider identity
action role
FP-02 capability profile + exact accepted row
account level
position mode
margin mode
provider instrument
provider Position snapshot + observation generation
canonical Position snapshot + broker_state_observed_at
FP-04 ownership/reconciliation evidence where applicable
close-applicable instrument metadata reference/generation/observed_at
metadata freshness policy version
calculation/evaluation time
```

A newer provider Position snapshot, newer canonical Position, newer metadata generation, or newer conflicting ownership evidence invalidates older sizing evidence.

### 11.2 Repository-evidenced metadata vocabulary

The following names are already present in the E4 OKX sizing implementation and may be reused as provider metadata vocabulary:

- `ctVal`;
- `ctMult`;
- `ctValCcy`;
- `ctType`;
- `lotSz`;
- `minSz`;
- `maxMktSz`;
- `tickSz`;
- `state`;
- metadata ref;
- metadata observed-at;
- versioned freshness policy;
- scheduled `upcChg` change evidence.

Their **existence and entry use** are repository-evidenced. Their role-specific close applicability is not automatically proven.

### 11.3 Close-applicability proof required

Before a field controls close sizing, the accepted E4 capability/metadata boundary must explicitly classify it as one of:

- `REQUIRED_FOR_CLOSE`;
- `APPLICABLE_CONSTRAINT`;
- `NOT_APPLICABLE_TO_CLOSE`;
- `UNRESOLVED_FAIL_CLOSED`.

Unknown is never treated as omitted/default.

At design time, these close-specific facts remain unresolved:

- exact native provider Position quantity/sign semantics per `net_mode` / `long_short_mode` for close sizing;
- exact provider close field set for both close roles;
- exact provider reduce-only field semantics;
- whether ENTRY `lotSz` is the complete close step rule;
- whether ENTRY `minSz` applies identically to reductions;
- whether ENTRY `maxMktSz` applies identically to reductions;
- whether there are distinct provider reduce/close maximums or exceptions;
- whether a provider-supported below-minimum full residual close rule exists;
- any special full-close/dust endpoint or flag.

All remain non-executable until separately proven.

## 12. Position-mode and FP-02 capability dependency

This profile consumes `okx-swap-action-role-capability-v0.1` exactly.

For both:

- `POSITION_EXIT`;
- `EMERGENCY_EXIT`;

current FP-02 provider mutation rows remain `UNRESOLVED_FAIL_CLOSED` for `net_mode` and `long_short_mode`.

Therefore this FP-05 design does not make either role executable.

A future sizing implementation must receive capability evidence from an accepted E4-owned resolver. It must not accept:

- `capability=True`;
- an arbitrary caller mapping;
- a copied ENTRY materialization;
- a configured position mode without observed/provider-bound proof;
- `reduce_only=true` as provider compatibility proof.

Spot `tdMode=cash` is forbidden.

Emergency urgency does not create capability authority and does not relax quantity/currentness rules.

## 13. FP-04 ownership/reconciliation dependency

FP-04 determines whether current provider exposure can safely participate in automation.

Sizing that depends on exact reducible exposure must fail closed when the relevant provider position/exposure evidence is:

- `EXTERNAL_UNTRACKED`;
- prior-generation without fresh accepted reconciliation;
- `MANUAL_REVIEW_REQUIRED`;
- `CONFLICTING_OWNERSHIP_EVIDENCE`;
- `UNKNOWN`;
- stale/superseded;
- paired with a reconciliation disposition blocking close mutation.

A matching symbol/side/quantity is not ownership proof.

FP-05 does not silently adopt manual/external exposure. If a future explicit policy permits an emergency-safety close of non-owned exposure, that requires separate exact authority; V0.1 does not invent it.

## 14. FP-11 and FP-10 relationship

### 14.1 FP-11 protection convergence remains separate

Flat or reduced provider Position truth does not silently erase or cancel provider protection objects.

After a close/reduction, active protection may be:

- still present;
- partially relevant to residual exposure;
- orphaned;
- duplicated;
- external;
- unknown.

FP-11 owns exactly-one-intended protection registry/multiplicity evidence and routes uncertain cleanup fail closed. FP-05 neither selects nor cancels protection objects.

### 14.2 FP-10 lifecycle convergence remains downstream

FP-10 later consumes, as applicable:

- authoritative reduced/flat Position truth from E4;
- aggregate Fill/execution truth;
- current FP-04 ownership/reconciliation evidence;
- FP-11 protection registry/cleanup convergence;
- E5 lifecycle interpretation.

FP-05 does not:

- emit `RECONCILED_FLAT`;
- emit `POSITION_CLOSED`;
- change lifecycle state;
- create TradeResult;
- decide external/manual adoption;
- clean up protections.

## 15. Provider-local fail-closed reason vocabulary

A future E4 implementation should use stable provider-local reasons equivalent to:

| Reason | Meaning |
|---|---|
| `OKX_CLOSE_SIZING_PROFILE_UNSUPPORTED` | Missing/unknown FP-05 profile. |
| `OKX_CLOSE_ROLE_UNSUPPORTED` | Role is not POSITION_EXIT/EMERGENCY_EXIT or exact FP-02 row is unavailable. |
| `OKX_CLOSE_ACTION_STALE_OR_MISMATCHED` | Close action does not bind exact current Position truth. |
| `OKX_CLOSE_REDUCIBLE_EXPOSURE_UNKNOWN` | Exact provider-native reducible exposure is unavailable. |
| `OKX_CLOSE_OWNERSHIP_RECONCILIATION_REQUIRED` | FP-04 ownership/currentness blocks safe sizing. |
| `OKX_CLOSE_CAPABILITY_UNPROVEN` | FP-02 provider field/mode/margin row is not accepted. |
| `OKX_CLOSE_METADATA_UNKNOWN_OR_STALE` | Required close metadata/currentness is unavailable. |
| `OKX_CLOSE_METADATA_APPLICABILITY_UNPROVEN` | A required limit/step/conversion field is only ENTRY-evidenced or otherwise unproven for close. |
| `OKX_CLOSE_PROVIDER_POSITION_UNIT_UNPROVEN` | Provider Position native quantity/sign semantics are not proven for the exact mode. |
| `OKX_CLOSE_CANONICAL_PROVIDER_QUANTITY_MISMATCH` | Provider exposure cannot reconcile to current canonical Position. |
| `OKX_CLOSE_SIZE_ZERO_OR_NEGATIVE` | Calculated provider request is not positive. |
| `OKX_CLOSE_SIZE_EXCEEDS_REDUCIBLE_EXPOSURE` | Requested native size exceeds provider reducible truth. |
| `OKX_CLOSE_SIZE_EXCEEDS_CANONICAL_AUTHORITY` | Effective canonical size exceeds current E5/Position authority. |
| `OKX_CLOSE_SIZE_NOT_REPRESENTABLE` | No valid positive native size exists under current constraints. |
| `OKX_CLOSE_RESIDUAL_NONZERO_UNREPRESENTABLE` | Fresh positive residual cannot be represented. |
| `OKX_CLOSE_PRIOR_OUTCOME_AMBIGUOUS` | Same logical close requires reconciliation before any new action. |
| `OKX_CLOSE_NEWER_EVIDENCE_REQUIRED` | Unchanged residual/metadata evidence cannot authorize immediate retry/replan. |
| `OKX_CLOSE_PROVIDER_FLAT_NOT_PROVEN` | Caller/order arithmetic tries to claim flatness without authoritative Position truth. |

Reason codes are E4 provider-local vocabulary, not shared E5/E7 enums.

## 16. Idempotency and material-evidence generations

A future provider close materialization must remain tied to the existing stable logical close identity `(position_action_id, order_role)` or the accepted equivalent.

Sizing evidence for that logical request must additionally bind exact provider Position and metadata generations. If those facts change before dispatch, the old materialization/sizing evidence is stale and must not be silently refreshed under the same authority without revalidation.

After a definitive partial/inactive close leaves residual exposure, a new close requires a new Position observation and new E5 PositionAction identity under `close-v0.1`.

After an ambiguous result, the same logical order is reconciled; a new identity is not created merely to bypass ambiguity.

## 17. Future deterministic implementation boundary

The smallest later executable E4 boundary is provider-local and can remain credential-free:

1. add an E4 `okx_close_sizing` module or equivalent provider-local component;
2. accept only exact `POSITION_EXIT | EMERGENCY_EXIT` canonical OrderRequest/PositionAction + current Position;
3. accept exact current normalized provider Position facts and FP-04 ownership evidence;
4. accept one adapter-issued/validated FP-02 capability row;
5. accept one validated close-applicable metadata snapshot/generation;
6. emit immutable `OKXCloseResidualSizingEvidence` plus, only when representable, a provider-native close-size materialization input;
7. do not perform network I/O in the sizing component;
8. keep provider dispatch separate and still default-deny/unimplemented until separately authorized;
9. after any future provider action, require a fresh provider Position observation before residual classification or new close authority.

This future code will be an executable P0 change and requires fresh approved-local credential-free requalification on the exact integrated candidate.

## 18. Required future credential-free tests

At minimum:

1. **Current exposure below original entry request** — original requested/plan size is larger; close size is derived only from exact current Position/provider reducible exposure.
2. **Changed/external/manual exposure** — current provider truth differs; unknown/conflicting FP-04 ownership blocks unsafe sizing until accepted reconciliation/policy permits use.
3. **No over-reduction** — provider-native request never exceeds exact reducible exposure or canonical current authority.
4. **Exact step/lot boundary** — accepted close step quantization is deterministic and never rounds upward.
5. **Full representability** — exact current exposure maps to `FULLY_REDUCIBLE` only when all role-specific constraints pass.
6. **Partial representability** — valid strict-subset size maps to `PARTIALLY_REDUCIBLE` without claiming expected arithmetic residual as truth.
7. **Positive representable post-action residual** — fresh Position observation remains positive and representable -> `RESIDUAL_NONZERO_REPRESENTABLE`.
8. **Positive non-representable residual** — fresh positive residual below/otherwise outside accepted close constraints -> stable `RESIDUAL_NONZERO_UNREPRESENTABLE`.
9. **No unchanged-residual retry** — identical residual Position snapshot + identical metadata/capability generation cannot create another mutation/retry path.
10. **New evidence permits re-evaluation** — materially newer Position or metadata generation can produce a new sizing evaluation, but mutation still requires fresh applicable E5 authority.
11. **Zero/negative native size rejected**.
12. **Stale/unknown metadata rejected**.
13. **Close-applicability unknown rejected** — entry-only `minSz`/`maxMktSz` evidence cannot be silently reused.
14. **Unknown account/position/margin capability rejected**.
15. **ENTRY sizing evidence is not close authority** — `OKXEntrySizingAudit` or equivalent cannot satisfy FP-05/FP-02 close capability.
16. **Provider Position unit/sign unresolved rejected**.
17. **Ambiguous prior close requires reconciliation** — no blind second request.
18. **ACK/terminal status does not establish flatness**.
19. **Authoritative flat Position only** — fresh zero exposure can yield `EXPOSURE_ALREADY_FLAT`; arithmetic/order status cannot.
20. **EMERGENCY_EXIT parity** — emergency uses the same currentness, ownership, capability, metadata and no-over-reduction proofs; urgency adds no bypass.
21. **Spot/cash rejected**.
22. **Caller capability assertion rejected**.
23. **Determinism** — same immutable inputs/generations yield byte-stable sizing state/evidence identity.
24. **No network/credentials** — all fixtures are local deterministic values; provider requests remain zero.

Suggested later approved-local command after implementation:

```powershell
$env:PYTHONPATH="src"
python -m unittest tests.brokers.test_okx_close_sizing -v
python -m unittest tests.execution.test_close -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
```

This docs-only task does not create those tests or execute any command.

## 19. Shared-contract assessment

No new shared field/profile is proven necessary for this design.

Existing shared semantics already provide:

- E5 close authority and exact Position quantity binding;
- E4 broker Position truth authority;
- OrderRequest/OrderResult/Fill identity and reconciliation semantics;
- `close-v0.1` residual/new-authority rule;
- FP-04 ownership/reconciliation evidence;
- FP-11 protection convergence evidence;
- downstream FP-10 lifecycle/flat convergence boundary.

The new quantities/metadata/capability/residual states described here are E4 provider-local implementation evidence. They need not be promoted into a cross-module authority object merely to implement safe OKX sizing.

If a later E6/E7 integration requires persisted cross-module consumption of the exact provider-local sizing evidence rather than only canonical Position/Order/Fill truth, E4 should request an E7 companion profile at that time rather than silently adding shared fields.

## 20. Security and release boundary

This design performs or authorizes none of:

```text
project executable verification = NOT_RUN / NOT REQUIRED
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order submit/cancel/amend/close = 0
SHADOW/PAPER = NOT_STARTED
10U live-fire = NOT_AUTHORIZED
capital exposure = NONE
LF-0 = BLOCKED / UNCHANGED
FP-03 combined qualification = NOT_RUN / NOT_PASS
Gate D / LIVE = BLOCKED / UNAUTHORIZED
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

`DONE` for this document means only that the FP-05 provider-local design is complete. It is not executable/provider/release PASS.