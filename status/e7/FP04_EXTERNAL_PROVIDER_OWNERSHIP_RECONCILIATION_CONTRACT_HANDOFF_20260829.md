# FP-04 External Provider Ownership / Reconciliation Contract Handoff — 2026-08-29

## Task / profile

```text
task_id = E7-20260829-106
profile = external-provider-object-ownership-reconciliation-v0.1
profile_status = BASELINE
parent_schema = contracts-v0.1 / UNCHANGED
task_type = CONTRACT / DOCS / STATUS ONLY
```

Artifact:

`contracts/EXTERNAL_PROVIDER_OBJECT_OWNERSHIP_RECONCILIATION_PROFILE_V0_1.md`

The profile closes only the FP-04 shared contract/design gap. It does not establish executable FP-04 completion.

## What changed conceptually

Project-r7 now has one provider-neutral fail-closed evidence model for answering:

> Does this exact current provider object snapshot belong to one exact accepted current project-r7 lineage/generation, or must automation reconcile/block before acting?

The profile preserves existing ownership boundaries:

```text
E4 = provider/order/fill/Position observation + execution lineage facts
E5 = risk/lifecycle interpretation and permission/veto
E6 = persistence/registry/audit/currentness validation
E7 = shared evidence schema/vocabulary/integration interpretation
PM = evidence sequencing/review
PO = provider/runtime/capital authority where separately required
```

No provider object is silently adopted, ignored, detached, or mutated by this contract.

## Provider object classes

V0.1 independently classifies:

- `POSITION_EXPOSURE`
- `OPEN_ORDER`
- `TERMINAL_ORDER`
- `FILL_EXECUTION`
- `ACTIVE_PROTECTION`
- `UNCLASSIFIED_PROVIDER_OBJECT`

The shared profile does not assume identical provider-native IDs, endpoints or fields across classes. E4 supplies exact class-specific sanitized provider references/snapshot hashes.

## Ownership classification vocabulary

Stable classifications:

```text
KNOWN_OWNED_CURRENT_GENERATION
KNOWN_OWNED_PRIOR_GENERATION
EXTERNAL_UNTRACKED
ADOPTABLE_BY_EXPLICIT_POLICY
MANUAL_REVIEW_REQUIRED
CONFLICTING_OWNERSHIP_EVIDENCE
UNKNOWN
```

Key interpretation:

- `KNOWN_OWNED_CURRENT_GENERATION` is provenance evidence, not mutation authority;
- `KNOWN_OWNED_PRIOR_GENERATION` never inherits current-process mutation authority;
- `EXTERNAL_UNTRACKED` is never silently ignored/trusted;
- `ADOPTABLE_BY_EXPLICIT_POLICY` means only that separate adoption evaluation may occur;
- `MANUAL_REVIEW_REQUIRED`, `CONFLICTING_OWNERSHIP_EVIDENCE`, and `UNKNOWN` fail closed.

Local absence, symbol/side/size similarity, client-ID fragments, timing proximity, or being the only visible object are never sufficient ownership proof.

## Reconciliation status vocabulary

```text
CURRENT_KNOWN_OWNED
RECONCILIATION_REQUIRED
ADOPTION_EVALUATION_REQUIRED
MANUAL_REVIEW_REQUIRED
CONVERGENCE_REQUIRED
UNKNOWN
```

Only `KNOWN_OWNED_CURRENT_GENERATION` may pair with `CURRENT_KNOWN_OWNED`, and even that pair does not authorize a provider action.

## Required disposition vocabulary

```text
NO_ACTION_CURRENT_KNOWN_OWNED
FRESH_RECONCILIATION_REQUIRED
BLOCK_NEW_EXPOSURE
BLOCK_PROTECTION_MUTATION
BLOCK_CLOSE_EXIT_MUTATION
ADOPTION_POLICY_EVALUATION_REQUIRED
DETACH_IGNORE_POLICY_EVALUATION_REQUIRED
MANUAL_REVIEW_REQUIRED
LIFECYCLE_REINTERPRETATION_REQUIRED
PROTECTION_REGISTRY_CONVERGENCE_REQUIRED
TERMINAL_FLAT_CONVERGENCE_PENDING
```

`NO_ACTION_CURRENT_KNOWN_OWNED` is exclusive. Every other disposition is reconciliation state/evidence only and creates no provider mutation authority.

`BLOCK_CLOSE_EXIT_MUTATION` applies when ownership/quantity is ambiguous. It does not preclude a later separately defined emergency-safety path with its own exact exposure authority; E7-106 does not invent such a path.

## Canonical evidence schema

`ExternalProviderObjectOwnershipEvidence` binds at minimum:

- `contracts-v0.1` + exact FP-04 profile version;
- object class;
- provider/environment identity ref/hash;
- canonical symbol + provider instrument ref;
- E4-stable provider object ref;
- exact provider snapshot ref/hash;
- provider observation generation/time;
- exact current project revision;
- current `runtime-preflight-v0.1` / process / start / config generation when runtime participates;
- deterministic owner-authoritative local lineage references;
- deterministic persistence/registry references;
- ownership classification;
- reconciliation status;
- required dispositions;
- stable reason codes;
- exact future adoption-decision ref when one validly applies;
- superseded evidence ref;
- post-input evaluation time;
- deterministic content-derived `extownrec_...` identity.

The evidence object contains sanitized references/hashes only and never persists credentials, raw private responses, exact balances, provider signatures/tokens, shell commands or local paths.

## Local lineage evidence

V0.1 can reference exact accepted lineage roles including:

```text
APPROVED_TRADE_PLAN
POSITION_ACTION
ORDER_REQUEST
CLIENT_ORDER_IDENTITY
ORDER_RESULT
FILL
POSITION
LIFECYCLE_PROJECTION
LIFECYCLE_EXECUTION_BINDING
OTHER_ACCEPTED_LINEAGE
```

Each reference remains owner-authored. E7/E6 do not recreate E4 provider truth or E5 lifecycle semantics.

## Currentness / supersession rules

Ownership evidence is immutable and bound to one exact provider snapshot + exact local/runtime generations.

Invalidation occurs when:

- provider truth advances for the same logical object;
- same provider identity/observation boundary yields a different snapshot hash;
- newer E4 execution truth contradicts/supersedes the bound lineage;
- newer E5 lifecycle interpretation changes the relevant lineage/currentness;
- E6 registry generation changes/conflicts;
- process/start/config generation changes;
- bound adoption evidence becomes stale/mismatched/consumed.

A new evidence object may reference the immediately superseded evidence. Old evidence remains historical and is never rewritten.

A later timestamp alone never upgrades external/conflicting evidence into current ownership.

## Fail-closed reason vocabulary

Stable reasons include profile/object/identity/snapshot failures, unproven lineage, prior-generation provenance, external objects, required adoption/manual review, local-lineage conflicts, multiplicity conflicts, provider/local identifier or snapshot mismatches, instrument/side/quantity mismatches, newer-provider/local-evidence invalidation, stale ownership evidence, invalid/stale/consumed adoption evidence, FP-11/FP-10 convergence requirements and incomplete reconciliation.

The only success reason is:

```text
CURRENT_GENERATION_OWNERSHIP_PROVEN
```

and it appears alone only with exact current-owned/current-known-owned evidence.

## Adoption boundary

Adoption is deliberately separate from classification.

Reserved future decision envelope:

`ExternalProviderObjectAdoptionDecisionEvidence`

A future implementation must bind at minimum:

- exact ownership evidence ID/hash;
- exact provider class/object/snapshot/generation;
- current Position/exposure truth where relevant;
- current lifecycle/execution-binding evidence where relevant;
- current registry evidence where relevant;
- current runtime/process/start/config generation where runtime participates;
- explicit `adoption_policy_version` + hash;
- deterministic decision ID;
- one-snapshot scope;
- decision status and post-input decision time.

Reserved decision vocabulary:

```text
ADOPTION_APPROVED
ADOPTION_REJECTED
MANUAL_REVIEW_REQUIRED
```

Reserved validity state:

```text
VALID
STALE
MISMATCH
CONSUMED
```

No current policy declares arbitrary manual/external objects production-adoptable. Constructing the decision shape does not create authority.

A newer provider snapshot, changed Position/lifecycle/registry truth, changed runtime/config generation, changed policy version, stale/mismatched decision or consumed single-object decision rejects adoption.

## E4 handoff boundary

Future E4 implementation should remain narrow:

1. normalize each supported provider object class into stable sanitized object/snapshot refs;
2. expose exact provider observation generation/time;
3. expose exact E4-created local execution lineage candidates;
4. never guess current ownership from similar fields;
5. surface one-local-to-many-provider and many-local-to-one-provider conflicts;
6. preserve ambiguous outcome reconciliation/no-blind-retry behavior;
7. use fixtures/fake transports for deterministic tests before any later provider verification.

Provider-specific protection/terminal-order observation capability may require later E4 work; E7-106 does not define OKX fields/endpoints.

## E5 handoff boundary

Future E5 consumers must prove:

- unknown provider exposure blocks new exposure;
- external/unknown/conflicting protection cannot become false-green protected state;
- prior-generation ownership does not inherit current mutation authority;
- external/manual reduced or flat provider truth causes fresh lifecycle interpretation rather than direct closure from order status;
- ownership conflict never becomes APPROVE by default;
- any future adoption policy carries explicit risk/lifecycle constraints and exact policy version.

## E6 handoff boundary

Future E6 work should:

- persist immutable ownership/reconciliation evidence by deterministic ID/hash;
- validate exact references/currentness/conflicts mechanically;
- preserve historical evidence rather than rewrite it;
- never allocate ownership by persistence arrival order;
- never manufacture lifecycle/ownership from registry rows;
- later persist dedicated adoption/protection registries only under separate accepted profiles/tasks.

## E7 integration handoff boundary

Future E7 integration/safety acceptance should cover:

- exact known-owned current-generation classification;
- prior-generation non-transferability;
- unknown provider position blocks new exposure;
- unknown/external protection blocks unsafe protection/new-exposure actions;
- manual/external object never silently adopted;
- two-local-lineage conflict fails closed;
- provider snapshot advance invalidates old ownership evidence;
- changed provider snapshot requires fresh interpretation;
- adoption binds exact object snapshot/policy generation;
- stale/mismatched/consumed adoption evidence rejects;
- multiple protection objects route to FP-11 convergence;
- external/manual flat/reduced exposure routes to FP-10 lifecycle reinterpretation;
- all deterministic tests use fixtures/fakes with zero provider/network/credentials.

Any project executable implementation requires fresh approved-local credential-free qualification on the exact integrated revision.

## FP-11 dependency

FP-11 now has a prerequisite ownership classification layer for every active protection object.

FP-11 must not silently collapse multiple/unknown/external protection objects into one intended protection. It may later define exactly-one intended active protection lineage only after each observed provider protection object has current FP-04 ownership evidence.

Current FP-02 provider design still leaves exact provider-native protection observation/mapping unresolved; E7-106 does not invent it.

## FP-10 dependency

FP-10 must consume:

- authoritative provider Position/exposure truth;
- aggregate relevant Fill/execution truth where required;
- current FP-04 ownership/reconciliation evidence;
- current E5 lifecycle projection/execution binding;
- E5-owned reconciliation interpretation.

A terminal/manual order status alone cannot produce `CLOSED`. Existing `RECONCILED_FLAT` remains an E5 lifecycle event requiring authoritative flat evidence, not a provider-order shortcut.

## LF-gate relationship

### LF-2

FP-04 is a required P0 item. E7-106 defines the design baseline only; executable implementation + fresh credential-free qualification remain required before LF-2 PASS.

### LF-3

Failure injection must cover external/manual position/order/fill/protection, prior generation, conflicting lineage, stale evidence, changed provider snapshot, stale/consumed adoption, protection multiplicity, manual reduction/flatness and restart/current-generation reclassification.

### LF-4

Future separately authorized provider read-only verification must prove the exact provider-specific observation fields/endpoints needed to form E4 snapshots on the exact candidate revision. Historical provider evidence is not rebound.

### LF-5

SHADOW/PAPER readiness must demonstrate no silent adoption, current runtime-generation ownership/reconciliation, and accepted FP-11/FP-10 downstream convergence behavior.

### LF-6

A future bounded live-fire preflight must start with all safety-relevant provider objects reconciled. Unknown/external/conflicting ownership blocks new exposure. Any explicit adoption remains separately exact-snapshot/policy governed.

## Current unresolved provider-specific facts

The shared profile intentionally does not decide:

- exact OKX provider fields/endpoints/identifier behavior for every object class;
- provider-native active conditional/protection readback shape;
- provider-native terminal-order history scope needed by future reconciliation;
- protection provider fieldset/trigger basis still unresolved under FP-02;
- provider-native close/reducible sizing still belongs to FP-05;
- current-candidate provider-facing verification, which remains `NOT_RUN / NOT_INFERRED`.

These are future E4/provider-read-only verification dependencies, not reasons to guess shared ownership semantics.

## ADR decision

```text
new ADR = NO / NOT REQUIRED
```

Reason: FP-04 adds an immutable shared evidence/refinement layer while preserving the established E4 provider truth -> E5 lifecycle/risk -> E6 persistence architecture. No authority direction, lifecycle state machine or provider capability is changed.

## Recommended next Worker tasks — not issued by E7-106

While LF-0 remains blocked, safe next work is docs/contract-first only:

1. E7/PM may next define FP-11 protection-registry/multiplicity contract now that FP-04 ownership classes are explicit.
2. FP-05 design/implementation remains dependent on accepted FP-02 provider capability/metadata semantics.
3. FP-10 contract refinement should consume FP-04 + FP-05 and preferably FP-11 identity/cleanup semantics.
4. FP-04 executable E4/E5/E6/E7 implementation should be scheduled only as a bounded future task and will require fresh exact-revision credential-free qualification after executable changes.

This handoff does not issue or execute any of those tasks.

## Current authority / blocker state

```text
LF-0 exact-revision infrastructure = BLOCKED / UNCHANGED
FP-03 candidate revision = 9462b2594675b2e28388f55a2af189100b7cbdfc
exact clean candidate = NOT_ESTABLISHED
FP-03 combined qualification = NOT_RUN / NOT_PASS
FP-04 executable implementation = NOT_STARTED
provider-facing verification on current candidate = NOT_RUN / NOT_INFERRED
SHADOW/PAPER = NOT_AUTHORIZED
10U live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
```

## Verification / execution boundary

E7-106 executes no project code/tests.

```text
project executable verification = NOT_RUN / NOT REQUIRED FOR CONTRACT-DOCS TASK
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
```

`NOT_RUN` is not executable PASS.