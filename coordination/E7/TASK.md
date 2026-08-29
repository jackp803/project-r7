# E7 Current Task

- task_id: `E7-20260829-107`
- issued_at: `2026-08-29T15:55:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-fp11-protection-registry-multiplicity-contract-20260829`
- authority: `agents/E7_INTEGRATION.md`, `agents/PROJECT_MANAGER.md`, `agents/README.md`, accepted `bounded-live-fire-readiness-v0.1`, accepted `external-provider-object-ownership-reconciliation-v0.1`, `status/PM_E7_106_REVIEW_20260829.md`, accepted E4 FP-02 provider-role design, accepted FP-03 protection-trigger-validity profile/candidates, mature-OKX failure-prevention baseline/audit, active LF-0 exact-revision infrastructure blocker

## Objective

Define the shared **FP-11 unique active-protection registry / multiplicity convergence profile** that prevents project-r7 from treating multiple, missing, orphaned, prior-generation, external or ambiguous provider protection objects as one valid intended protection.

This is a contract/docs/status-only E7 task. It must not implement E4/E5/E6 executable code, modify provider adapters, call provider endpoints, read credentials, create Local Job Requests, authorize SHADOW/PAPER/10U live-fire, mutate provider/account state, or change Gate D/LIVE status.

The profile closes only the FP-11 contract/design gap. Executable registry/provider integration and local qualification remain future bounded tasks.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E7_INTEGRATION.md`;
- `agents/PROJECT_MANAGER.md`;
- accepted `contracts/BOUNDED_LIVE_FIRE_READINESS_PROFILE_V0_1.md`;
- accepted `contracts/EXTERNAL_PROVIDER_OBJECT_OWNERSHIP_RECONCILIATION_PROFILE_V0_1.md`;
- accepted Position lifecycle / protection / execution-evidence / protection-trigger-validity profiles;
- accepted E4 `docs/execution/OKX_SWAP_ACTION_ROLE_CAPABILITY_MATRIX_V0_1.md` only as provider-role design evidence;
- current E4/E5/E6 protection identity, execution binding, persistence and reconciliation semantics;
- `status/e7/MATURE_OKX_FAILURE_PREVENTION_GAP_AUDIT_20260829.md` FP-11 row plus FP-04/FP-10 context;
- `status/PM_E7_106_REVIEW_20260829.md`;
- active `status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`.

Do not read or execute another Worker's TASK mailbox.

## Required shared profile

Create:

`contracts/PROTECTION_REGISTRY_MULTIPLICITY_PROFILE_V0_1.md`

Profile identifier:

`protection-registry-multiplicity-v0.1`

The profile must be provider-neutral at the shared boundary and fail closed. It must define how one canonical Position and one intended E5 protection lineage are reconciled against zero, one or multiple observed provider protection objects whose ownership classification is supplied by accepted FP-04 evidence.

## Required canonical concepts

Define at minimum:

### Intended protection lineage

One exact logical protection intent must bind to exact authoritative references such as:

- current Position identity/version/snapshot;
- exact E5 `PositionAction.PROTECT` lineage;
- exact parent `ApprovedTradePlan` where required by existing protection semantics;
- exact protection-trigger-validity evidence for create/replace authority where relevant;
- exact E4 `OrderRequest` / client-order identity / execution evidence lineage if provider materialization has occurred;
- exact runtime/config/process generation where runtime participates;
- exact current ownership/reconciliation evidence generation.

Do not invent provider-native protection fields or IDs in the shared profile.

### Observed provider protection set

Represent a deterministic set of currently observed provider protection objects for the Position, where every object independently carries current FP-04 ownership classification/evidence.

Never select one object as intended merely because it is newest, closest in price, only locally known, or has a similar client ID fragment.

## Required multiplicity vocabulary

Define stable shared multiplicity/currentness states equivalent in intent to:

- `NO_ACTIVE_PROTECTION_OBSERVED`
- `EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION`
- `MULTIPLE_ACTIVE_PROTECTIONS`
- `ORPHAN_OR_EXTERNAL_PROTECTION_PRESENT`
- `OWNERSHIP_CONFLICT_PRESENT`
- `PROTECTION_SET_STALE`
- `PROTECTION_SET_UNKNOWN`

You may refine names to fit existing contract style, but preserve these semantic distinctions.

Only the exact single intended current-owned case may represent converged protection-registry truth. All other states must fail closed for actions that assume safe unique protection.

## Required registry status/disposition vocabulary

Define stable registry outcomes/dispositions, including at minimum:

- current/converged exactly-one intended protection;
- missing protection / E5 protection-policy reinterpretation required;
- multiplicity convergence required;
- orphan/external protection reconciliation required;
- ownership conflict/manual review required;
- stale provider-set refresh required;
- block new exposure;
- block protection create/replace while multiplicity is unresolved;
- block unsafe cleanup/cancel when provider-object authority is uncertain;
- lifecycle/protection-state reinterpretation required where actual provider protection truth contradicts local `OPEN_PROTECTED` / `PROFIT_PROTECTED` assumptions.

A registry disposition must never itself authorize cancel/create/replace provider mutation.

## Exact one-intended-protection invariant

Define the invariant precisely:

```text
For one canonical open Position and one currently intended E5 protection lineage,
registry convergence requires exactly one observed ACTIVE_PROTECTION provider object
whose current FP-04 evidence proves KNOWN_OWNED_CURRENT_GENERATION and whose exact
lineage/object identity binds to the intended protection lineage.
```

The profile must explicitly reject:

- zero provider protection objects while local state claims protected;
- two or more objects matching the same intended lineage;
- a current-owned intended object plus any additional external/prior-generation/unknown/conflicting active protection object;
- one external object being treated as intended by similarity;
- one prior-generation object inheriting current mutation authority;
- stale provider-object snapshots;
- registry state based on incomplete provider observation coverage.

## Missing-protection boundary

When no valid active provider protection exists for an open Position:

- registry state is not converged;
- local `OPEN_PROTECTED`/`PROFIT_PROTECTED` truth must not remain false-green solely from stale local records;
- E5 must receive authoritative evidence requiring protection-policy/lifecycle reinterpretation;
- the shared profile must not itself decide whether to create protection, emergency-exit or otherwise mutate provider state.

Preserve E5 policy authority.

## Multiple/orphan protection boundary

When multiple, external, orphaned, prior-generation, unknown or conflicting provider protection objects are observed:

- every object retains its own FP-04 ownership evidence;
- no automatic newest/oldest/closest-price selection;
- no blind cancel-all;
- no blind create-another;
- no assumption that extra provider protection is harmless;
- new exposure and protection mutation remain blocked until convergence/policy authority is established;
- cleanup/cancellation requires a later exact E4/E5 authorized action tied to current provider object identity and ownership evidence.

## Registry currentness / evidence identity

Define immutable canonical `ProtectionRegistryMultiplicityEvidence` (or equivalent) binding at minimum:

1. schema/profile version;
2. exact canonical Position reference/snapshot;
3. exact intended protection lineage reference/version;
4. exact provider observation generation/time;
5. deterministic complete observed ACTIVE_PROTECTION object-set identity/hash;
6. per-object FP-04 ownership evidence IDs/hashes;
7. exact runtime/process/config generation where runtime participates;
8. exact relevant E5 lifecycle projection/protection state reference;
9. multiplicity state;
10. registry reconciliation status/dispositions;
11. stable reason codes;
12. evaluation time/order constraints;
13. deterministic evidence ID/hash;
14. supersession/currentness rules.

The complete observed provider protection set must be part of the evidence identity. Adding/removing/changing any protection object or ownership evidence invalidates the old registry evidence.

A later timestamp alone does not make stale registry evidence current.

## Required fail-closed reason vocabulary

Define stable reasons covering at minimum:

- profile/schema mismatch;
- Position mismatch/stale Position evidence;
- intended protection lineage missing/mismatch/stale;
- provider observation incomplete/stale/unknown;
- protection object ownership evidence missing/stale/mismatched;
- zero active protection;
- multiple active protection;
- external/orphan/prior-generation object present;
- conflicting ownership evidence;
- exact intended object identity mismatch;
- lifecycle/protection-state contradiction;
- provider set changed since evaluation;
- registry evidence identity/hash invalid;
- fresh reconciliation / E5 reinterpretation / manual review / convergence required;
- exact single intended protection converged success reason.

Success must require the exact converged invariant; do not allow partial-green states.

## Cross-module ownership split

Document at minimum:

### E4

Owns provider observation of protection objects, exact object identifiers/snapshots, current observation generation, provider readback facts, and future provider-specific create/cancel/query mappings only under accepted provider capability authority.

### E5

Owns intended protection policy/PositionAction lineage, lifecycle interpretation, whether missing/conflicting protection requires create/replace/emergency exit/lock, and permission/veto for any cleanup/mutation.

### E6

Owns immutable persistence/registry projection of accepted evidence and mechanical reference/hash/currentness validation. E6 must not select which provider protection is semantically intended by arrival order or similarity.

### E7

Owns the shared profile, multiplicity/currentness vocabulary, cross-module consistency and release/integration interpretation.

### PM / Product Owner

PM sequences implementation/evidence; Product Owner authority remains separately required for provider/private/runtime/capital stages under current governance.

## FP-04 dependency

Every observed active protection object must carry current accepted FP-04 ownership evidence. Registry convergence may not bypass FP-04 classification.

`KNOWN_OWNED_CURRENT_GENERATION` is necessary but not sufficient by itself: exact provider-object lineage must also bind to the one intended protection lineage.

## FP-03 dependency

FP-03 protection-trigger validity remains create/replace pre-mutation geometry evidence. It does not prove a provider protection currently exists, is unique, or is owned. FP-11 must not infer registry convergence from FP-03 `ACTIONABLE` evidence.

## FP-02 dependency

Current accepted FP-02 design leaves provider-native protection endpoint/trigger/readback semantics unresolved. The shared FP-11 contract must therefore bind E4-supplied provider protection object references/snapshots abstractly and must not invent OKX fields/endpoints.

## FP-10 dependency

FP-10 close lifecycle convergence should later consume FP-11 registry state so terminal/flat convergence can prove intended protection cleanup or explicitly surface unresolved orphan protection after the Position becomes flat.

Do not implement FP-10 here.

## Deterministic implementation/test handoff

Define smallest future credential-free implementation/test boundaries for E4/E5/E6/E7, including at minimum:

- zero observed protection while local state claims protected -> fail closed + E5 reinterpretation;
- exactly one intended current-owned protection -> converged;
- exactly one external protection -> not converged / no silent adoption;
- intended current-owned + external extra protection -> multiplicity conflict;
- two current-owned objects for one intended lineage -> multiplicity conflict;
- prior-generation protection -> not current mutation authority;
- stale/incomplete provider observation set -> reject;
- changed provider protection set invalidates old registry evidence;
- changed FP-04 ownership evidence invalidates old registry evidence;
- Position/lifecycle change invalidates old registry evidence;
- blind cancel-all/create-another paths forbidden;
- new exposure blocked while registry unsafe;
- exact current Position + intended lineage + complete set required;
- no provider/network/credential access required for deterministic fixtures.

Do not implement executable changes in this task.

## Required artifacts

- `contracts/PROTECTION_REGISTRY_MULTIPLICITY_PROFILE_V0_1.md`;
- update `contracts/README.md`;
- `status/e7/FP11_PROTECTION_REGISTRY_MULTIPLICITY_CONTRACT_HANDOFF_20260829.md` documenting:
  - profile/version;
  - intended-lineage and observed-set model;
  - multiplicity/status/disposition/reason vocabularies;
  - evidence identity/currentness rules;
  - E4/E5/E6/E7 ownership split;
  - exact FP-04/FP-03/FP-02 dependencies;
  - FP-10 downstream dependency;
  - future deterministic implementation/test boundaries;
  - relationship to LF-2/LF-3/LF-4/LF-5/LF-6;
  - unresolved provider-specific facts, if any;
  - whether a new ADR is actually required;
  - recommended next Worker task(s), but do not issue them yourself.
- update `coordination/E7/STATUS.md`.

An ADR is optional only if a genuinely new architecture decision cannot be represented by accepted protection/ownership/lifecycle governance. Do not create one for documentation volume alone.

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

- `contracts/PROTECTION_REGISTRY_MULTIPLICITY_PROFILE_V0_1.md`;
- `contracts/README.md`;
- at most one E7 ADR if genuinely necessary;
- `status/e7/FP11_PROTECTION_REGISTRY_MULTIPLICITY_CONTRACT_HANDOFF_20260829.md`;
- `coordination/E7/STATUS.md`.

Do not modify executable source/tests, E1-E6 code/tests, E4 provider capability docs, AgentBridge/local action catalog, provider config/credentials/private allowlists, Product Owner authorization artifacts, risk limits/leverage/capital thresholds, or release criteria.

## Result classification

### DONE

Use DONE only if the shared FP-11 protection-registry/multiplicity profile and handoff are complete, internally consistent with accepted FP-04/protection/lifecycle governance, define exact fail-closed multiplicity/currentness behavior, preserve cross-role authority separation and grant no executable/provider/runtime/capital authority.

### PARTIAL

Use PARTIAL if a bounded shared-contract ambiguity prevents deterministic intended-lineage/object-set/multiplicity semantics. Record the exact ambiguity and do not invent provider semantics.

### BLOCKED

Use BLOCKED only if authoritative repository evidence is contradictory or insufficient to define the profile safely.

## Completion

Read latest `main`, verify wake task ID `E7-20260829-107`, execute only this docs-only task, persist evidence, update STATUS, commit/push the target branch, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start FP-11 executable implementation, FP-10, FP-05, FP-04 executable implementation, FP-16 executable implementation, AgentBridge changes, exact-revision preparation, qualification, provider verification, SHADOW/PAPER, 10U live-fire, Gate D, LIVE, mutation, order action or capital movement/exposure.
