# E4 FP-05 Close / Residual Sizing Implementation Evidence — 2026-08-29

- task_id: `E4-20260829-031`
- agent: `E4`
- branch: `agent/e4-fp05-close-residual-sizing-implementation-20260829`
- baseline_main_sha: `e9e8aa6674bc5696a194e61e2e0dc1b4b75ef86c`
- result_classification: `PARTIAL / SOURCE AND TEST DEFINITIONS COMPLETE / EXECUTABLE VERIFICATION NOT_RUN`

## Scope

This task implements only the provider-free deterministic E4 FP-05 sizing/evidence boundary described by:

- `docs/execution/OKX_SWAP_ACTION_ROLE_CAPABILITY_MATRIX_V0_1.md`
- `docs/execution/OKX_SWAP_CLOSE_RESIDUAL_SIZING_V0_1.md`
- accepted `external-provider-object-ownership-reconciliation-v0.1`
- current E4 `close-v0.1` consumer and merged FP-04 producer/currentness helper
- current E5 `close-v0.1` PositionAction/current Position semantics

No shared contract, E5 lifecycle/risk policy, E6 persistence semantics, provider transport/authentication, runtime authorization, release gate, risk limit, leverage or capital threshold was changed.

## Files changed

Source:

- `src/brokers/okx_close_sizing.py`
- `src/brokers/okx_close_sizing_binding.py`

Tests:

- `tests/brokers/test_okx_close_sizing.py`
- `tests/brokers/test_okx_close_sizing_binding.py`
- `tests/brokers/test_okx_close_sizing_currentness.py`

Evidence/status:

- `status/e4/FP05_CLOSE_RESIDUAL_SIZING_IMPLEMENTATION_20260829.md`
- `coordination/E4/STATUS.md`

## Provider-free implementation boundary

The implementation consumes supplied in-memory facts only and emits immutable E4-local evidence equivalent to `OKXCloseResidualSizingEvidence` under:

```text
close_residual_sizing_profile_version = okx-swap-close-residual-sizing-v0.1
```

The implementation does not contain or call:

- an OKX HTTP/private client;
- an account endpoint;
- credentials or secret lookup;
- order submit/cancel/amend/close dispatch;
- provider/account mutation;
- retry dispatch;
- SHADOW/PAPER/live runtime startup;
- capital movement/exposure.

The sizing result is evidence/routing only. It is not an `OrderRequest`, provider materialization, E5 lifecycle transition, provider mutation authority or release authorization.

## Input/evidence types

`src/brokers/okx_close_sizing.py` adds frozen provider-local fact types:

- `OKXProviderExposureObservation`
- `OKXCloseRoleCapabilityEvidence`
- `OKXCloseMetadataApplicabilityEvidence`
- `OKXCloseSizingInput`

The strict task-facing metadata binding boundary in `src/brokers/okx_close_sizing_binding.py` adds:

- `OKXCloseMetadataBindingEvidence`

The strict entry point requires the close-applicability proof to bind the exact metadata ref/hash/generation used by sizing before the core evaluator may run.

## E5 close authority / Position binding

The evaluator consumes existing E4 `validate_close_authority(...)`; it does not redefine E5 close semantics.

For `PRE_ACTION` sizing:

```text
PositionAction = exact close-v0.1 EXIT | EMERGENCY_EXIT
source Position = exact current Position
PositionAction.position_id = Position.position_id
PositionAction.position_observed_at = Position.broker_state_observed_at
PositionAction.quantity = Position.actual_quantity
Position reconciliation = CONSISTENT
quantity profile = base-asset-v0.1 / BASE_ASSET / BTC
```

The original ApprovedTradePlan quantity remains only a maximum/lineage constraint. It does not become current close quantity authority.

## Post-action residual boundary

The evaluator explicitly separates:

```text
PRE_ACTION
POST_ACTION_RESIDUAL
```

For `POST_ACTION_RESIDUAL`:

- the original close action is validated against the original source Position lineage;
- the current Position must remain the same logical Position/instrument/side/quantity-profile lineage;
- the current Position observation must be equal to or newer than the source observation;
- actual residual/flatness comes only from the newer current Position + provider exposure observation;
- old Position quantity minus requested/acknowledged close size is never residual authority;
- the old PositionAction is not silently rewritten to the residual quantity.

This preserves the accepted rule that a future additional close requires fresh E5 authority from a fresh Position observation.

## Required evaluation precedence

The implementation preserves the accepted fail-closed precedence:

1. validate exact close-v0.1 action/role;
2. bind exact source/current canonical Position lineage;
3. unresolved prior logical close outcome -> `RECONCILIATION_REQUIRED` before sizing;
4. validate exact FP-04 provider Position snapshot/currentness/ownership;
5. unknown provider reducible exposure -> `REDUCIBLE_EXPOSURE_UNKNOWN`;
6. exact authoritative provider/canonical zero -> `EXPOSURE_ALREADY_FLAT` with no requested provider size;
7. provider/canonical quantity contradiction -> `RECONCILIATION_REQUIRED`;
8. unproven exact close-role FP-02 capability -> `CLOSE_CAPABILITY_UNPROVEN`;
9. stale/missing/unproven close-applicable metadata proof -> `METADATA_STALE_OR_UNKNOWN`;
10. only after all preceding checks calculate provider-native representability;
11. never round upward beyond provider/current canonical/E5 authority;
12. after any future mutation, require fresh provider Position truth before residual/flatness classification.

## FP-04 ownership/currentness behavior

The evaluator converts the supplied provider Position observation into the exact existing FP-04 `ProviderObjectObservation` shape and consumes:

```text
external_provider_ownership_evidence_is_current(...)
```

Sizing can progress beyond ownership only for the exact success tuple:

```text
ownership_classification = KNOWN_OWNED_CURRENT_GENERATION
reconciliation_status = CURRENT_KNOWN_OWNED
required_dispositions = [NO_ACTION_CURRENT_KNOWN_OWNED]
```

Behavior otherwise remains fail closed:

- stale/mismatched FP-04 evidence -> `RECONCILIATION_REQUIRED`;
- external/manual/prior-generation/unknown ownership -> no trusted reducible-size authority;
- external/manual evidence remains external and is never silently adopted;
- matching symbol/side/quantity is not ownership proof.

## FP-02 capability boundary

The evaluator has no built-in production assertion that `POSITION_EXIT` or `EMERGENCY_EXIT` is currently provider-executable.

Current authoritative FP-02 design rows for both close roles remain:

```text
UNRESOLVED_FAIL_CLOSED
```

The evaluator can calculate representability only when supplied typed capability evidence explicitly proves one exact close-role row, including provider/instrument/account/position-mode/margin/native-quantity-unit/fieldset/currentness facts.

The deterministic test fixtures marked `REPO_EVIDENCED` are hypothetical accepted-proof fixtures used only to test the algorithmic boundary. They are not evidence that the current real OKX close role has been provider-verified or release-authorized.

An actual current `UNRESOLVED_FAIL_CLOSED` row deterministically produces:

```text
CLOSE_CAPABILITY_UNPROVEN
```

No Spot/cash rule, ENTRY `posSide`, ENTRY field set or shared `reduce_only=true` is promoted into close-role provider authority.

## Close metadata / applicability boundary

The implementation reuses existing E4 `OKXInstrumentMetadata` only as provider metadata vocabulary/currentness structure.

Close sizing additionally requires explicit close-role applicability evidence:

- conversion = `REQUIRED_FOR_CLOSE`;
- close step = `APPLICABLE_CONSTRAINT`;
- close minimum = `APPLICABLE_CONSTRAINT | NOT_APPLICABLE_TO_CLOSE`;
- close maximum = `APPLICABLE_CONSTRAINT | NOT_APPLICABLE_TO_CLOSE`;
- currentness = `CURRENT`;
- scope = exact `CLOSE_ROLE`;
- exact action role matches `POSITION_EXIT | EMERGENCY_EXIT`.

`src/brokers/okx_close_sizing_binding.py` additionally requires an exact immutable cross-binding of:

```text
instrument_metadata_ref
instrument_metadata_hash
instrument_metadata_generation
metadata_applicability_proof_ref
metadata_applicability_hash
metadata_applicability_generation_id
```

A proof from another metadata snapshot/generation fails before sizing.

ENTRY-only applicability evidence cannot satisfy the close-role boundary.

## Quantization / no-over-reduction

Only after all authority/currentness/applicability checks pass:

```text
base_per_contract = ctVal * ctMult
native_bound_from_canonical = current Position.actual_quantity / base_per_contract
native_upper_bound = min(native_bound_from_canonical, exact provider reducible quantity)
native_upper_bound = min(native_upper_bound, close_max) when an explicit close-role maximum applies
candidate = floor(native_upper_bound / close_step) * close_step
```

Hard invariants:

```text
candidate > 0
candidate <= exact provider reducible exposure
effective canonical close quantity <= current Position.actual_quantity
effective canonical close quantity <= E5-authorized close quantity
candidate is an exact close-step multiple
candidate satisfies explicit close min/max constraints
```

There is no rounding-up exception for `EMERGENCY_EXIT`.

If a positive current residual cannot produce a valid positive close size, it remains positive and becomes:

```text
RESIDUAL_NONZERO_UNREPRESENTABLE
```

It is never rounded/written off to zero.

## Implemented sizing-state vocabulary

Exactly:

- `FULLY_REDUCIBLE`
- `PARTIALLY_REDUCIBLE`
- `RESIDUAL_NONZERO_REPRESENTABLE`
- `RESIDUAL_NONZERO_UNREPRESENTABLE`
- `EXPOSURE_ALREADY_FLAT`
- `REDUCIBLE_EXPOSURE_UNKNOWN`
- `METADATA_STALE_OR_UNKNOWN`
- `RECONCILIATION_REQUIRED`
- `CLOSE_CAPABILITY_UNPROVEN`

These states remain E4 provider-local evidence/routing facts.

## Flatness boundary

`EXPOSURE_ALREADY_FLAT` requires exact current evidence equivalent to:

```text
current canonical Position actual_quantity = 0
provider normalized canonical quantity = 0
provider native reducible quantity = 0
provider Position currentness = CURRENT
exact current FP-04 ownership evidence
Position reconciliation = CONSISTENT
```

The result carries no provider request size and does not emit `CLOSED`, `POSITION_CLOSED`, `RECONCILED_FLAT` or TradeResult authority.

ACK/terminal/FILLED state and local arithmetic are not used as flatness authority.

## Ambiguity / retry behavior

A supplied unresolved prior close outcome is classified before capability/metadata/sizing:

```text
RECONCILIATION_REQUIRED
reason = OKX_CLOSE_PRIOR_OUTCOME_AMBIGUOUS
provider request size = null
```

No second close identity or retry authority is created.

For a post-action positive unrepresentable residual, evidence includes:

```text
OKX_CLOSE_NEWER_EVIDENCE_REQUIRED
```

Unchanged residual evidence is stable and does not itself authorize another mutation.

## Deterministic evidence identity / hash

Provider-local evidence includes deterministic:

```text
sizing_evidence_id = okxclosesz_<sha256>
sizing_evidence_hash = sha256:<same material digest>
```

Canonicalization uses sorted compact JSON, finite base-10 decimal strings and canonical UTC `Z` timestamps.

The identity material binds action/parent/source/current Position/provider/FP-04/FP-02/metadata/applicability/state/reason/supersession facts. `evaluated_at` is intentionally non-authoritative audit time and is excluded from the material authority digest so a later timestamp alone cannot create a new sizing authority.

Materially changed facts produce a different evidence identity. Explicit supersession requires:

- same logical `position_id`;
- same action role;
- exact prior valid sizing evidence ID;
- at least one material fact change.

Attempting explicit supersession using only a later `evaluated_at` is rejected with `SUPERSESSION_REQUIRES_MATERIAL_CHANGE`.

## Currentness behavior

`okx_close_residual_sizing_evidence_is_current(...)` re-evaluates the supplied current facts and compares all material fields while ignoring only:

- evidence ID/hash;
- audit `evaluated_at`;
- supersession pointer.

A material change in any of these invalidates old evidence:

- source/current Position observation/quantity;
- provider snapshot/generation/currentness;
- FP-04 ownership/currentness;
- FP-02 capability generation/currentness/facts;
- metadata snapshot/freshness;
- metadata applicability generation/proof;
- prior close ambiguity;
- representability/state/reasons.

A later wall-clock can still invalidate evidence when it causes previously bound metadata to become stale. The rule is only that timestamp change alone does not manufacture fresh authority.

## Tests defined

Provider-free deterministic test definitions cover:

- exact full representability;
- strict-subset/partial representability;
- fresh post-action positive representable residual;
- positive unrepresentable/dust residual;
- unchanged post-action residual carrying no retry authority;
- fresh exact provider/canonical flat truth with no provider request size;
- unknown provider reducible exposure;
- stale/inconsistent Position/provider/FP-04 facts;
- external/manual FP-04 without silent adoption;
- unproven ordinary/emergency close capability;
- ENTRY-only constraint/applicability evidence rejected for close;
- stale close metadata;
- unresolved prior close outcome before sizing;
- floor quantization and no-over-reduction;
- exact metadata ref/hash/generation vs applicability proof binding;
- changed Position/provider/FP-04/capability/metadata invalidating old evidence;
- later timestamp alone not refreshing authority;
- explicit supersession on material change only;
- deterministic identity independent of mapping insertion order;
- EMERGENCY_EXIT safety parity;
- absence of provider transport/credential/mutation fields from the evaluator boundary.

## Executable verification

Per the Product Owner local-only policy and active LF-0 exact-revision preparation blocker:

```text
project executable verification = NOT_RUN / NOT_PASS
```

No Python project module, unit test, broker simulation or provider verification command was executed in this task session.

Future approved-local Windows PowerShell commands for the exact integrated candidate:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/brokers -p "test_okx_close_sizing*.py" -v
python -m unittest tests.execution.test_close -v
python -m unittest discover -s tests/execution -p "test_external_close*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
```

Result in this task:

```text
ALL ABOVE = NOT_RUN / NOT_PASS
```

No GitHub Action, CI, hosted runner, GitHub-triggered self-hosted runner or cloud project-code verification was used.

## Known limitations / unresolved provider-specific facts

The deterministic evaluator is implemented, but current real provider close capability remains intentionally unproven. The following are still not inferred:

- exact OKX provider mutation field set for `POSITION_EXIT` / `EMERGENCY_EXIT`;
- exact `posSide` semantics for close in `net_mode` or `long_short_mode`;
- provider-native reduce-only field presence/value/omission;
- provider Position native quantity/sign semantics until an exact accepted capability proof exists;
- whether ENTRY `lotSz`, `minSz`, `maxMktSz` apply identically to close;
- distinct reduce/close maxima or minimum exceptions;
- special below-minimum/dust/full-close endpoint/flag;
- actual provider timing/readback behavior after a future close mutation.

Those facts require later E4 provider-capability evidence under separate authority. This task does not claim them.

No shared-contract field or E7 semantic change was proven necessary by this implementation.

## Authority / safety state

```text
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order submit/cancel/amend/close = 0
SHADOW/PAPER runtime = NOT_STARTED / NOT_AUTHORIZED
10U live-fire = NOT_AUTHORIZED
capital exposure = NONE
LF-0 = BLOCKED / UNCHANGED
LF-2 = NOT PASS
Gate D / LIVE = BLOCKED / UNAUTHORIZED
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

`PARTIAL` means only that the source/test-definition candidate exists while executable qualification remains unavailable. It is not provider capability proof, executable PASS, PAPER readiness, bounded-live-fire readiness or LIVE authority.
