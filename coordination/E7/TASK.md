# E7 Current Task

- task_id: `E7-20260829-109`
- issued_at: `2026-08-29T16:15:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-fp10-external-manual-close-lifecycle-convergence-contract-20260829`
- authority: `agents/E7_INTEGRATION.md`, `agents/PROJECT_MANAGER.md`, `agents/README.md`, accepted `bounded-live-fire-readiness-v0.1`, accepted FP-04 ownership/reconciliation profile, accepted FP-11 protection-registry/multiplicity profile, accepted E4 FP-05 close/residual sizing design, `status/PM_E4_028_REVIEW_20260829.md`, mature-OKX failure-prevention baseline/audit, active LF-0 exact-revision infrastructure blocker

## Objective

Define the shared **FP-10 external/manual close lifecycle convergence profile** so project-r7 cannot declare a Position/lifecycle closed merely because a close order is ACKed/terminal, local quantity arithmetic reaches zero, or provider exposure changed outside the current automation generation.

This is a contract/docs/status-only E7 task. It must not implement E4/E5/E6 executable code, modify provider adapters, call provider endpoints, read credentials, create Local Job Requests, authorize SHADOW/PAPER/10U live-fire, mutate provider/account state, or change Gate D/LIVE status.

The profile closes only the FP-10 contract/design gap. Executable implementation and exact-revision local qualification remain future bounded tasks.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E7_INTEGRATION.md`;
- `agents/PROJECT_MANAGER.md`;
- accepted Position lifecycle / execution-evidence / close profiles;
- accepted `contracts/EXTERNAL_PROVIDER_OBJECT_OWNERSHIP_RECONCILIATION_PROFILE_V0_1.md`;
- accepted `contracts/PROTECTION_REGISTRY_MULTIPLICITY_PROFILE_V0_1.md`;
- accepted E4 `docs/execution/OKX_SWAP_CLOSE_RESIDUAL_SIZING_V0_1.md`;
- accepted E4 `docs/execution/OKX_SWAP_ACTION_ROLE_CAPABILITY_MATRIX_V0_1.md` only as provider-role design evidence;
- current E4 order/fill/Position reconciliation semantics;
- current E5 lifecycle transition/reconciliation semantics, especially `RECONCILED_FLAT`, `POSITION_CLOSED`, `CLOSED`, `RECONCILIATION_REQUIRED`, and protection-state handling;
- current E6 persistence/currentness semantics;
- `status/e7/MATURE_OKX_FAILURE_PREVENTION_GAP_AUDIT_20260829.md` FP-10 row;
- `status/PM_E4_028_REVIEW_20260829.md`;
- active `status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`.

Do not read or execute another Worker's TASK mailbox.

## Required shared profile

Create:

`contracts/EXTERNAL_MANUAL_CLOSE_LIFECYCLE_CONVERGENCE_PROFILE_V0_1.md`

Profile identifier:

`external-manual-close-lifecycle-convergence-v0.1`

The profile must be provider-neutral at the shared boundary and fail closed. It must define the evidence required to converge current provider exposure/fill/order/protection truth back into the E5-owned lifecycle when exposure is reduced or flattened by project-r7, manually, externally, by a prior process/generation, or under an ambiguous/reconciled outcome.

## Required evidence distinctions

At minimum distinguish and bind independently:

1. current authoritative provider Position/exposure snapshot;
2. exact normalized canonical Position truth and broker observation generation;
3. aggregate relevant Fill/execution evidence when needed to explain current exposure;
4. close/order terminal state as execution evidence only, never flatness authority by itself;
5. current FP-04 ownership/reconciliation evidence for relevant provider position/order/fill objects;
6. current FP-05 close/residual sizing state where a project close path participated;
7. current FP-11 protection registry/multiplicity evidence;
8. current E5 lifecycle projection and execution binding;
9. current runtime/process/config generation where runtime participates;
10. exact evaluation time/currentness/supersession identity.

Do not duplicate E4 provider truth, E5 lifecycle transition policy, or E6 persistence semantics; bind owner-authoritative references.

## Required convergence states

Define a stable shared vocabulary equivalent in intent to:

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

You may refine names to fit current contract style, but preserve the distinctions. `LIFECYCLE_CLOSE_ELIGIBLE` is evidence for E5 interpretation only; it must not itself emit or force a lifecycle transition.

## Exact flatness rule

The profile must explicitly require:

```text
fresh authoritative provider/normalized Position zero-exposure truth
+ current compatible FP-04 ownership/reconciliation evidence
+ no unresolved execution/fill ambiguity that can contradict Position truth
+ current FP-11 terminal protection convergence appropriate for flat exposure
+ current lifecycle/execution-binding references
+ no newer superseding provider/local/runtime truth
= lifecycle close eligibility evidence
```

A terminal order, FILLED status, requested close quantity, arithmetic remainder, missing local Position row, missing pending order, or stale local ledger state is insufficient by itself.

## Reduced-but-not-flat rule

Any positive current exposure, including an FP-05 `RESIDUAL_NONZERO_REPRESENTABLE` or `RESIDUAL_NONZERO_UNREPRESENTABLE` case, is not flat and cannot converge to lifecycle `CLOSED`.

A non-representable residual remains explicit. It may require E5 policy/lifecycle reinterpretation or manual review, but FP-10 must not write it off, round it to zero, or create retry/mutation authority.

## External/manual close boundary

When provider exposure is reduced/flattened by manual or external action:

- do not require the current automation to have created the closing provider order as a precondition for observing the truth;
- do require current FP-04 ownership/reconciliation classification of the relevant provider objects/exposure;
- do not silently adopt an external/manual order into current-generation execution lineage;
- route changed exposure through fresh E5 lifecycle reinterpretation;
- a provider flat Position may be authoritative exposure truth while execution lineage remains external/manual;
- lifecycle closure still requires all independent currentness/protection/reconciliation conditions defined by the profile.

## Protection convergence boundary

Flat provider exposure does not erase provider protection objects.

Consume FP-11 so that:

- active orphan/external/prior-generation/multiple/unknown protection after flatness remains explicit;
- unresolved protection cleanup blocks full terminal convergence where current lifecycle/release policy requires it;
- no blind cancel-all or silent ignore is authorized;
- FP-10 records the dependency/disposition but does not select or execute provider cleanup.

## Order/fill ambiguity boundary

Define fail-closed behavior when:

- order ACK/terminal state disagrees with current Position truth;
- fill aggregate and current Position truth are inconsistent or incomplete;
- a prior close outcome was ambiguous and no fresh reconciliation exists;
- external/manual fills are observed without current ownership/reconciliation evidence;
- provider Position becomes flat before all local execution objects have terminal/converged state.

Current authoritative Position truth may drive lifecycle reinterpretation, but unresolved contradictory execution evidence must remain explicitly represented; do not silently discard it.

## Evidence identity/currentness

Define immutable canonical `ExternalManualCloseLifecycleConvergenceEvidence` (or equivalent) binding at minimum:

1. schema/profile version;
2. exact Position/provider observation generation/ref/hash;
3. exact relevant execution/fill/order evidence refs/hashes;
4. exact current FP-04 evidence refs/hashes;
5. exact current FP-05 sizing/residual evidence ref/hash when applicable;
6. exact current FP-11 registry evidence ref/hash;
7. exact current E5 lifecycle projection/execution-binding refs/hashes;
8. runtime/process/config generation when applicable;
9. convergence state/status/dispositions;
10. deterministic reason codes;
11. evaluation time/order constraints;
12. deterministic evidence ID/hash;
13. supersession/currentness rules.

Any materially newer provider Position, fill/order, ownership, residual sizing, protection registry, lifecycle or runtime generation invalidates old convergence evidence. A later timestamp alone does not refresh stale evidence.

## Required fail-closed reasons

Define stable reasons covering at minimum:

- profile/schema mismatch;
- Position/provider exposure missing/stale/mismatch;
- positive exposure remains;
- residual nonzero representable/unrepresentable;
- terminal order without flat Position proof;
- execution/fill ambiguity or contradiction;
- FP-04 ownership/reconciliation missing/stale/conflicting/external review required;
- FP-11 protection convergence missing/stale/non-converged;
- lifecycle projection/execution-binding mismatch or stale;
- external/manual reinterpretation required;
- provider/local/runtime evidence superseded;
- evidence identity/hash/time invalid;
- lifecycle close eligibility success reason.

Success must require the exact current flat/converged invariant and must not be inferred from one subsystem alone.

## Cross-module ownership split

Document at minimum:

### E4

Owns provider Position/order/fill observations, exact provider object/snapshot identity, execution/reconciliation facts, and FP-05 provider-local sizing/residual evidence.

### E5

Owns lifecycle reinterpretation/transitions, including whether accepted convergence evidence produces `RECONCILED_FLAT`, `POSITION_CLOSED`, `CLOSED`, EMERGENCY handling, hold/lock, or another accepted lifecycle outcome. E7 FP-10 must not manufacture transitions.

### E6

Owns immutable persistence/projection and mechanical reference/hash/currentness validation; it must not infer flatness or lifecycle closure from persistence absence/order.

### E7

Owns the shared convergence profile, deterministic evidence/state/reason vocabulary, cross-module consistency, integration/release interpretation.

### PM / Product Owner

PM sequences bounded implementation/evidence review. Product Owner provider/private/runtime/capital authority remains separately required under existing governance.

## Deterministic future implementation/test handoff

Define the smallest credential-free future implementation/test boundaries for E4/E5/E6/E7, including at minimum:

- terminal close order but Position still positive -> not eligible;
- Position reduced but nonzero -> not eligible;
- FP-05 representable residual -> not eligible;
- FP-05 non-representable residual -> explicit fail-closed/not flat;
- authoritative flat Position + current execution evidence + converged FP-11 -> close eligible evidence;
- authoritative flat Position + orphan/multiple protection -> protection convergence required;
- external/manual flat Position -> E5 reinterpretation path, no silent order adoption;
- manual partial reduction -> lifecycle remains open/reinterpreted, not closed;
- ambiguous prior close result -> reconciliation required;
- provider Position/fill/order contradiction -> fail closed;
- newer provider Position invalidates old convergence evidence;
- newer FP-04/FP-05/FP-11/lifecycle evidence invalidates old convergence evidence;
- stale runtime generation invalidates when applicable;
- missing local Position row does not equal flat;
- no pending order does not equal flat;
- deterministic fixtures require zero provider/network/credentials.

Do not implement executable changes in this task.

## Required artifacts

- `contracts/EXTERNAL_MANUAL_CLOSE_LIFECYCLE_CONVERGENCE_PROFILE_V0_1.md`;
- update `contracts/README.md`;
- `status/e7/FP10_EXTERNAL_MANUAL_CLOSE_LIFECYCLE_CONVERGENCE_CONTRACT_HANDOFF_20260829.md` documenting profile/version, evidence/state/reason vocabularies, exact FP-04/FP-05/FP-11 dependencies, cross-module ownership split, currentness/supersession, future deterministic implementation/test boundaries, LF-gate relationship, unresolved provider-specific facts if any, and recommended next Worker tasks without issuing them;
- update `coordination/E7/STATUS.md`.

Create an ADR only if a genuinely new architecture decision cannot be represented by accepted lifecycle/reconciliation governance. Do not create one for documentation volume alone.

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

- `contracts/EXTERNAL_MANUAL_CLOSE_LIFECYCLE_CONVERGENCE_PROFILE_V0_1.md`;
- `contracts/README.md`;
- at most one E7 ADR if genuinely necessary;
- `status/e7/FP10_EXTERNAL_MANUAL_CLOSE_LIFECYCLE_CONVERGENCE_CONTRACT_HANDOFF_20260829.md`;
- `coordination/E7/STATUS.md`.

Do not modify executable source/tests, E1-E6 code/tests, E4 provider design docs, AgentBridge/local action catalog, provider config/credentials/private allowlists, Product Owner authorization artifacts, risk limits/leverage/capital thresholds, or release criteria.

## Result classification

### DONE

Use DONE only if the shared FP-10 convergence profile and handoff are complete, internally consistent with accepted FP-04/FP-05/FP-11/lifecycle governance, define exact fail-closed currentness/flatness/convergence behavior, preserve E5 lifecycle authority, and grant no executable/provider/runtime/capital authority.

### PARTIAL

Use PARTIAL if a bounded shared-contract ambiguity prevents deterministic convergence semantics. Record the exact ambiguity and do not invent provider or lifecycle policy.

### BLOCKED

Use BLOCKED only if authoritative repository evidence is contradictory or insufficient to define the profile safely.

## Completion

Read latest `main`, verify wake task ID `E7-20260829-109`, execute only this docs-only task, persist evidence, update STATUS, commit/push the target branch, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start FP-10 executable implementation, FP-04/FP-05/FP-11/FP-16 executable work, AgentBridge changes, exact-revision preparation, qualification, provider verification, SHADOW/PAPER, 10U live-fire, Gate D, LIVE, mutation, order action, or capital movement/exposure.
