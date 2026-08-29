# E7 Current Task

- task_id: `E7-20260829-106`
- issued_at: `2026-08-29T15:38:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-fp04-external-ownership-reconciliation-contract-20260829`
- authority: `agents/E7_INTEGRATION.md`, `agents/PROJECT_MANAGER.md`, `agents/README.md`, accepted `bounded-live-fire-readiness-v0.1`, accepted `runtime-preflight-v0.1`, `status/PM_E7_105_REVIEW_20260829.md`, mature-OKX failure-prevention baseline/audit, active LF-0 exact-revision infrastructure blocker

## Objective

Define the shared **FP-04 external/manual provider object ownership and reconciliation profile** that prevents project-r7 from silently assuming that every provider position, order, fill, or protection object was created and is owned by the current automation generation.

This is a contract/docs/status-only E7 task. It must not implement E4/E5/E6 executable code, modify provider adapters, call provider endpoints, read credentials, create Local Job Requests, authorize SHADOW/PAPER/10U live-fire, mutate provider/account state, or change Gate D/LIVE status.

The profile closes only the FP-04 contract/design gap. Executable implementation and local qualification remain future bounded domain/integration tasks.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E7_INTEGRATION.md`;
- `agents/PROJECT_MANAGER.md`;
- accepted `contracts/BOUNDED_LIVE_FIRE_READINESS_PROFILE_V0_1.md`;
- accepted Position lifecycle / execution-evidence / protection profiles;
- accepted `contracts/RUNTIME_PREFLIGHT_PROFILE_V0_1.md` only where current runtime generation/reconciliation identity affects ownership evidence;
- accepted E4 `docs/execution/OKX_SWAP_ACTION_ROLE_CAPABILITY_MATRIX_V0_1.md` only as provider-role design evidence;
- current E4 reconciliation/order/fill/position object semantics;
- current E5 Position/lifecycle authority semantics;
- current E6 persistence/reconciliation/operational-mode semantics;
- `status/e7/MATURE_OKX_FAILURE_PREVENTION_GAP_AUDIT_20260829.md` FP-04, FP-10 and FP-11 rows;
- `status/PM_E7_105_REVIEW_20260829.md`;
- active `status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`.

Do not read or execute another Worker's TASK mailbox.

## Required shared profile

Create:

`contracts/EXTERNAL_PROVIDER_OBJECT_OWNERSHIP_RECONCILIATION_PROFILE_V0_1.md`

Profile identifier:

`external-provider-object-ownership-reconciliation-v0.1`

The profile must be provider-neutral at the shared boundary and fail closed. It must define how current provider truth is classified and reconciled when an observed provider object may have been created manually, by another process/generation, by a previous runtime, by an external system, or by project-r7 with incomplete/missing local evidence.

## Required provider object classes

At minimum cover independently:

- provider position/exposure;
- pending/open order;
- historical/terminal order relevant to current reconciliation;
- fill/trade execution;
- active protective order / conditional protection object;
- provider-side object whose purpose/lineage cannot be determined.

Do not assume identical provider-native identifiers or field sets across object classes. Shared ownership semantics must consume exact owner-supplied evidence references rather than invent provider fields.

## Required ownership classification vocabulary

Define a stable fail-closed classification vocabulary equivalent in intent to:

- `KNOWN_OWNED_CURRENT_GENERATION`
- `KNOWN_OWNED_PRIOR_GENERATION`
- `EXTERNAL_UNTRACKED`
- `ADOPTABLE_BY_EXPLICIT_POLICY`
- `MANUAL_REVIEW_REQUIRED`
- `CONFLICTING_OWNERSHIP_EVIDENCE`
- `UNKNOWN`

You may refine names if repository contracts require it, but preserve these semantic distinctions.

Rules:

- absence of local state is never proof that a provider object is safe to ignore;
- presence of a familiar symbol/side/size/client ID fragment is never sufficient ownership proof;
- prior-generation project ownership does not automatically grant current-generation mutation authority;
- external/manual objects are never silently adopted;
- `ADOPTABLE_BY_EXPLICIT_POLICY` is only a classification enabling a separately defined explicit adoption decision; classification itself must not perform adoption;
- `UNKNOWN` and conflicting evidence fail closed.

## Required canonical ownership evidence

Define immutable canonical ownership/reconciliation evidence binding at minimum:

1. profile/schema version;
2. exact provider object class;
3. exact provider/instrument identity reference;
4. provider object stable identifier/reference and observed snapshot hash/reference as supplied by E4;
5. provider observation time/generation;
6. exact current runtime/process/start/config generation where relevant;
7. exact current project revision/preflight reference where relevant;
8. locally claimed lineage references, if any, such as ApprovedTradePlan / PositionAction / OrderRequest / client-order identity / execution binding / lifecycle projection;
9. local persistence/registry references where applicable;
10. ownership classification;
11. reconciliation disposition/state;
12. stable reason codes;
13. evaluation time/order constraints;
14. deterministic evidence ID/hash;
15. supersession/currentness rules when newer provider or local truth arrives.

Do not duplicate E4 provider truth, E5 lifecycle policy or E6 persistence semantics; bind authoritative references from those owners.

## Required reconciliation disposition vocabulary

Define stable dispositions that make automation behavior explicit. At minimum distinguish:

- no action / current known-owned evidence accepted;
- fresh reconciliation required;
- block new exposure;
- block protection mutation;
- block close/exit mutation where ownership/quantity is ambiguous;
- explicit adoption-policy evaluation required;
- explicit detach/ignore decision only if later policy authorizes it;
- manual review required;
- lifecycle reinterpretation required;
- protection-registry convergence required;
- terminal/flat convergence pending.

A disposition may never directly authorize a provider mutation. It is shared reconciliation state/evidence only.

## Required fail-closed semantics

The profile must fail closed when any of these occur:

- provider object exists with no trustworthy current lineage;
- local lineage claims ownership but provider identifier/snapshot does not bind exactly;
- two local lineages claim the same provider object;
- one local lineage maps to multiple active provider objects where multiplicity is not explicitly permitted;
- object belongs to a prior runtime/process/config generation without accepted current reconciliation/adoption evidence;
- provider observation is newer than ownership evidence;
- local execution/lifecycle/persistence evidence is newer and contradicts provider ownership evidence;
- object quantity/side/instrument conflicts with claimed lineage;
- provider object is manually/external created and no explicit adoption policy applies;
- adoption evidence is stale, consumed, mismatched or refers to a different object snapshot;
- ownership evidence identity/hash/currentness validation fails;
- reconciliation state is unknown/incomplete.

Unknown/external/conflicting ownership must block any unsafe new exposure and any mutation whose correctness depends on ownership certainty.

## Adoption boundary

V0.1 must define **adoption as a separate explicit policy/authority step**, not an automatic consequence of classification.

Define the minimum evidence an eventual adoption decision would need, including exact provider snapshot, object class/identity, current Position/exposure truth, current lifecycle/registry state, current runtime/config generation, explicit adoption policy/version, and deterministic adoption decision identity.

Do not decide in this task which external objects should be adopted in production. Do not invent a live policy that converts arbitrary manual objects into project-owned objects.

## Cross-module ownership split

Document at minimum:

### E4

Owns provider observation, provider object identifiers/snapshots, execution lineage it created, ambiguity/reconciliation facts, and later provider readback.

### E5

Owns interpretation of exposure/Position/lifecycle safety, whether new exposure/protection/exit is permissible given reconciliation state, and any lifecycle reinterpretation after external/manual truth.

### E6

Owns durable persistence/registry/audit projection of accepted ownership/reconciliation evidence and currentness/reference validation, without inventing ownership or risk policy.

### E7

Owns the shared profile, cross-module contract consistency, deterministic reason/state vocabulary and release/integration interpretation.

### PM / Product Owner

PM sequences evidence/review and cannot invent provider/runtime authority. Product Owner authority remains separately required for provider/private/runtime/capital stages under current governance.

## FP-11 dependency

The profile must explicitly prepare FP-11 protection-registry work by defining how active protective objects are classified as current-owned, prior-generation, external, conflicting, orphan/unknown or adoptable-by-explicit-policy.

Do not implement the unique protection registry here.

FP-11 may later require exactly-one intended active protection lineage after ownership classification/convergence. Multiple/unknown/external protective objects must never be silently collapsed into one intended protection.

## FP-10 dependency

The profile must explicitly prepare FP-10 external/manual close lifecycle convergence.

A manually/external closed or reduced provider position cannot be translated directly into `CLOSED` merely from an order status. Later FP-10 must consume authoritative provider Position/fill truth plus this ownership/reconciliation evidence and E5 lifecycle semantics.

Do not implement FP-10 here.

## Deterministic implementation/test handoff

Define the smallest future executable implementation boundaries and credential-free tests for E4/E5/E6/E7, including at minimum:

- exact known-owned current-generation object classification;
- prior-generation object does not inherit current mutation authority;
- unknown provider position blocks new exposure;
- unknown/external protection blocks unsafe protection mutation/new exposure until convergence;
- manual/external object is never silently adopted;
- conflicting two-local-lineage ownership fails closed;
- stale ownership evidence invalidated by newer provider snapshot;
- changed provider object snapshot requires fresh interpretation;
- adoption decision must bind exact object snapshot and policy generation;
- consumed/stale/mismatched adoption authority rejected;
- duplicate/multiple protection objects route to FP-11 convergence rather than silent selection;
- external/manual flat/reduced exposure routes to FP-10 lifecycle reinterpretation rather than direct close from order status;
- no provider/network/credential access required for deterministic fixtures.

Do not implement executable changes in this task.

## Required artifacts

- `contracts/EXTERNAL_PROVIDER_OBJECT_OWNERSHIP_RECONCILIATION_PROFILE_V0_1.md`;
- update `contracts/README.md`;
- `status/e7/FP04_EXTERNAL_PROVIDER_OWNERSHIP_RECONCILIATION_CONTRACT_HANDOFF_20260829.md` documenting:
  - profile/version;
  - object/ownership/disposition vocabularies;
  - canonical evidence schema/currentness rules;
  - adoption boundary;
  - E4/E5/E6/E7 ownership split;
  - exact downstream dependencies for FP-11 and FP-10;
  - future deterministic implementation/test boundaries;
  - relationship to LF-2/LF-3/LF-4/LF-5/LF-6;
  - current unresolved provider-specific facts, if any;
  - whether a new ADR is actually required;
  - recommended next Worker task(s), but do not issue them yourself.
- update `coordination/E7/STATUS.md`.

An ADR is optional only if a genuinely new architecture decision cannot be represented by existing ownership/reconciliation/lifecycle governance. Do not create one for documentation volume alone.

## Verification / authority boundary

This task is contract/docs/status only:

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

## Writable scope

Only:

- `contracts/EXTERNAL_PROVIDER_OBJECT_OWNERSHIP_RECONCILIATION_PROFILE_V0_1.md`;
- `contracts/README.md`;
- at most one E7 ADR if genuinely necessary;
- `status/e7/FP04_EXTERNAL_PROVIDER_OWNERSHIP_RECONCILIATION_CONTRACT_HANDOFF_20260829.md`;
- `coordination/E7/STATUS.md`.

Do not modify executable source/tests, E1-E6 code/tests, E4 provider capability docs, AgentBridge/local action catalog, provider config/credentials/private allowlists, Product Owner authorization artifacts, risk limits/leverage/capital thresholds, or release criteria.

## Result classification

### DONE

Use DONE only if the shared FP-04 ownership/reconciliation profile and handoff are complete, internally consistent with accepted governance, define explicit fail-closed external/manual handling, preserve cross-role authority separation and grant no executable/provider/runtime/capital authority.

### PARTIAL

Use PARTIAL if a bounded shared-contract ambiguity prevents deterministic object/ownership/disposition or adoption-boundary definition. Record the exact ambiguity and do not invent semantics.

### BLOCKED

Use BLOCKED only if current authoritative repository evidence is contradictory or insufficient to define the profile safely.

## Completion

Read latest `main`, verify wake task ID `E7-20260829-106`, execute only this docs-only task, persist evidence, update STATUS, commit/push the target branch, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start FP-04 executable implementation, FP-11, FP-10, FP-05, FP-16 executable implementation, AgentBridge changes, exact-revision preparation, qualification, provider verification, SHADOW/PAPER, 10U live-fire, Gate D, LIVE, mutation, order action or capital movement/exposure.
