# FP-10 External / Manual Close Lifecycle Convergence Contract Handoff — 2026-08-29

## Task / result boundary

- task_id: `E7-20260829-109`
- profile: `external-manual-close-lifecycle-convergence-v0.1`
- artifact: `contracts/EXTERNAL_MANUAL_CLOSE_LIFECYCLE_CONVERGENCE_PROFILE_V0_1.md`
- task class: `CONTRACT / DOCS / STATUS ONLY`
- executable implementation: `NOT_STARTED`
- executable verification: `NOT_RUN / NOT REQUIRED`
- provider/private verification: `NOT_RUN / NOT AUTHORIZED`

This handoff records only the shared FP-10 design boundary. It grants no provider, runtime, mutation, capital, Gate D, or LIVE authority.

## Core convergence rule

Lifecycle close eligibility is not inferred from an order or local ledger. It requires the exact current conjunction:

```text
fresh authoritative provider/normalized Position zero-exposure truth
+ current compatible FP-04 ownership/reconciliation evidence
+ no unresolved execution/fill ambiguity capable of contradicting Position truth
+ current terminal protection convergence using FP-11/FP-04 principles
+ current E5 lifecycle projection/execution-binding references
+ no newer superseding provider/local/runtime truth
= LIFECYCLE_CLOSE_ELIGIBLE evidence for E5 interpretation
```

`LIFECYCLE_CLOSE_ELIGIBLE` is evidence only. E5 remains authoritative for `POSITION_CLOSED`, `RECONCILED_FLAT`, `CLOSED`, `STATE_UNKNOWN`, `EXIT_FAILED`, `EMERGENCY`, re-attestation, or another accepted lifecycle outcome.

## Evidence distinctions

The profile binds independently:

1. current provider Position/exposure snapshot;
2. exact normalized canonical Position truth and broker observation generation;
3. current relevant OrderResult/Fill/reconciliation evidence;
4. terminal order state as execution evidence only, never flatness authority;
5. current FP-04 ownership/reconciliation evidence for relevant Position/order/fill/protection objects;
6. current FP-05 close/residual sizing evidence when a project close participated;
7. current/open-lineage FP-11 evidence plus a fresh post-flat terminal protection observation set;
8. current E5 lifecycle projection and lifecycle execution binding;
9. current project/runtime/process/config generation when runtime participates;
10. immutable evaluation identity/currentness/supersession material.

## Convergence vocabulary

`convergence_state`:

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

Only the last state is positive close-eligibility evidence, and even it does not perform a transition.

`required_dispositions`:

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

No disposition directly authorizes provider mutation.

## FP-04 dependency

`external-provider-object-ownership-reconciliation-v0.1` remains the ownership/provenance authority for provider Position/order/fill/protection objects.

Key rules preserved:

- external/manual objects are never silently adopted;
- prior-generation provenance does not transfer current mutation authority;
- unknown/conflicting/stale ownership fails closed;
- provider flat Position truth may still be authoritative exposure truth while the responsible external/manual execution lineage remains external, provided current non-conflicting reconciliation evidence is explicit;
- external/manual truth newer than E5 lifecycle authority routes through fresh E5 reinterpretation before close eligibility.

## FP-05 dependency

Accepted E4 `okx-swap-close-residual-sizing-v0.1` remains provider-local design evidence only.

FP-10 consumes, but does not redefine, FP-05 meanings:

- `EXPOSURE_ALREADY_FLAT` is provider-local zero-exposure evidence only;
- `RESIDUAL_NONZERO_REPRESENTABLE` means not flat;
- `RESIDUAL_NONZERO_UNREPRESENTABLE` means explicit positive residual, never rounded/written off;
- `RECONCILIATION_REQUIRED`/unknown states fail closed;
- requested/ACKed close size and arithmetic remainder never establish flatness.

## FP-11 dependency / terminal protection bridge

FP-11 applies to the open Position registry and explicitly routes unresolved protection after flatness to FP-10.

A newer flat Position observation supersedes prior open-position FP-11 currentness. FP-10 therefore records the prior FP-11 evidence as lineage/history and requires a fresh post-flat terminal protection observation set using the same E4 completeness/currentness and FP-04 per-object ownership principles.

`TERMINAL_PROTECTION_CLEAR` requires a complete/current post-flat protection observation with zero relevant active protection and no unresolved ownership conflict.

Any orphan/external/prior-generation/multiple/unknown/conflicting active protection remains explicit and prevents terminal convergence. No blind cancel-all or silent ignore is authorized.

## External/manual close semantics

External/manual/prior-generation reduction may change authoritative provider Position truth without creating project-owned execution lineage.

For a new external/manual exposure change:

```text
EXTERNAL_OR_MANUAL_REINTERPRETATION_REQUIRED
+ E5_LIFECYCLE_REINTERPRETATION_REQUIRED
```

is the first shared routing outcome until E5 has freshly interpreted the exact current evidence generation.

After that interpretation, a subsequent FP-10 evaluation may become `LIFECYCLE_CLOSE_ELIGIBLE` if every flatness/currentness/protection/reconciliation condition passes.

## Order / Fill ambiguity semantics

- terminal/FILLED close order + positive Position -> not flat;
- flat Position + unresolved nonterminal/ambiguous execution -> reconciliation remains explicit when late-effect/duplicate/lineage risk can contradict safe interpretation;
- Fill aggregate contradicting Position truth -> fail closed;
- missing external/manual canonical Fill lineage is never fabricated;
- lifecycle flatness and final TradeResult evidence completeness are separate.

## TradeResult boundary

FP-10 may permit E5 to reflect authoritative provider flatness before a canonical `trade-result-v0.1` object is possible for an external/manual close.

If required exit Fill/OrderRequest lineage is incomplete:

```text
TRADE_RESULT_EVIDENCE_INCOMPLETE
```

remains explicit. E6 must not manufacture missing execution evidence. Existing TradeResult quantity-conservation and closure-evidence rules remain unchanged.

## Evidence identity / currentness

Canonical evidence:

`ExternalManualCloseLifecycleConvergenceEvidence`

Identity:

```text
extcloseconv_<SHA256 canonical complete evidence payload excluding ID>
```

Any materially newer provider Position, normalized Position, order/fill/reconciliation, FP-04, FP-05, protection-set, lifecycle projection/binding, or runtime/process/config generation invalidates old convergence evidence.

A later evaluation timestamp with unchanged stale inputs does not restore currentness.

## Cross-module ownership split

### E4

Provider Position/order/fill observations, provider object identity, reconciliation facts, normalized broker Position truth, and provider-local FP-05 residual evidence.

### E5

Lifecycle/risk reinterpretation and transition/reattestation authority. E5 decides whether accepted FP-10 evidence results in `RECONCILED_FLAT`, `POSITION_CLOSED`, `CLOSED`, emergency/reconciliation handling, or another allowed lifecycle outcome.

### E6

Immutable persistence, exact reference/hash/currentness/conflict validation, and restart/current projection mechanics only. No flatness/lifecycle inference from storage absence/order.

### E7

Shared FP-10 profile/version/state/reason/currentness semantics and cross-module integration/release interpretation.

### PM / Product Owner

PM sequences later implementation/evidence. Product Owner authority remains separately required for provider/private/runtime/capital stages.

## Future deterministic implementation / tests

Minimum credential-free cases:

- terminal close order but Position positive -> not eligible;
- manual partial reduction -> open/reinterpretation, not closed;
- FP-05 representable residual -> not eligible;
- FP-05 unrepresentable residual -> explicit fail-closed not-flat;
- authoritative flat Position + compatible current execution + terminal protection clear -> close-eligible evidence;
- flat Position + orphan/multiple protection -> terminal protection convergence required;
- external/manual flat -> fresh E5 reinterpretation, no silent order adoption;
- ambiguous prior close -> reconciliation required;
- Position/fill/order contradiction -> fail closed;
- newer provider/FP-04/FP-05/protection/lifecycle/runtime evidence invalidates old FP-10 evidence;
- missing local Position row != flat;
- no pending order != flat;
- lifecycle close eligibility != TradeResult eligibility;
- deterministic fixtures use zero provider/network/credentials.

Future executable owner changes require fresh approved-local credential-free qualification on the exact integrated revision.

## LF gate relationship

- `LF-2`: FP-10 contract/design becomes defined only; executable P0 closure remains incomplete.
- `LF-3`: future failure-injection/recovery must exercise manual partial/flat, ambiguous close, residual, stale evidence, and orphan protection after flat.
- `LF-4`: future exact-revision provider read-only verification remains separately Product-Owner-authorized and must validate provider observation semantics without mutation.
- `LF-5`: future SHADOW/PAPER recovery must consume current FP-10 evidence and cannot trust stale local `CLOSED` state.
- `LF-6`: no bounded live-fire authority is created.

## Unresolved provider-specific facts

Still unresolved and intentionally not invented:

- OKX close endpoint/field set;
- `posSide` and native reduce-only close semantics;
- close-specific lot/min/max/dust/full-close behavior;
- exact provider zero-position omission/row representation;
- completeness/timing relationships between Position, order, Fill, and protection readbacks;
- provider behavior for external/manual execution and protection objects after flatness.

These remain E4/provider capability facts.

## ADR decision

`NEW ADR = NO / NOT REQUIRED`

Reason: FP-10 composes already accepted E4 provider-truth, E5 lifecycle, E6 persistence, FP-04 ownership, FP-05 residual, and FP-11 registry boundaries. No dependency direction, authority plane, or lifecycle transition table is changed.

## Recommended next Worker tasks — not issued

After PM review, recommended bounded work is:

1. E5/E4/E6 deterministic FP-04 + FP-10 executable evidence/consumer implementation;
2. E4 FP-05 provider-local implementation when accepted provider capability facts are sufficient;
3. E4/E6/E5 FP-11 executable registry implementation;
4. E7 integrated deterministic safety/E2E definitions after owner implementations;
5. one fresh exact-revision approved-local qualification for the integrated P0 candidate.

This handoff does not assign or start those tasks.

## Current authority / blocker state

```text
LF-0 exact-revision infrastructure = BLOCKED / UNCHANGED
candidate = 9462b2594675b2e28388f55a2af189100b7cbdfc
exact clean candidate = NOT_ESTABLISHED
FP-03 combined qualification = NOT_RUN / NOT_PASS
FP-10 executable implementation = NOT_STARTED
provider-facing verification = NOT_RUN / NOT_INFERRED
SHADOW/PAPER = NOT_STARTED / NOT_AUTHORIZED
10U live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
```

## Verification boundary

```text
project executable verification = NOT_RUN / NOT REQUIRED
Local Job Request = NONE
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order submit/cancel/amend/close = 0
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

`NOT_RUN` is not executable PASS.
