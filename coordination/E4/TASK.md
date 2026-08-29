# E4 Current Task

- task_id: `E4-20260829-030`
- issued_at: `2026-08-29T17:18:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-fp04-fp10-evidence-producer-20260829`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, accepted `external-provider-object-ownership-reconciliation-v0.1`, accepted `external-manual-close-lifecycle-convergence-v0.1`, accepted Position/lifecycle execution evidence profiles, accepted FP-11 profile, accepted E4 FP-05 design, merged E5/E6 FP-04/FP-10 static candidates, `status/PM_E6_026_REVIEW_20260829.md`, active LF-0 exact-revision infrastructure blocker

## Objective

Implement the smallest **provider-neutral E4 FP-04 ownership/reconciliation evidence producer plus FP-10 convergence evidence assembler** from already-supplied authoritative broker/Position/order/fill/protection observations and owner-authoritative references.

This task is deterministic and provider-free. It must not perform network I/O, invoke OKX/private/public endpoints, read credentials, submit/cancel/amend/close orders, mutate account/provider state, retry ambiguous mutations, start SHADOW/PAPER/live runtime, or infer provider capability that remains unproven.

The implementation may construct accepted shared evidence objects, but must not redefine their schemas/vocabularies or take over E5 lifecycle policy / E6 persistence semantics.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E4_EXECUTION.md`;
- `contracts/EXTERNAL_PROVIDER_OBJECT_OWNERSHIP_RECONCILIATION_PROFILE_V0_1.md`;
- `contracts/EXTERNAL_MANUAL_CLOSE_LIFECYCLE_CONVERGENCE_PROFILE_V0_1.md`;
- accepted Position / lifecycle projection / lifecycle execution-binding profiles;
- `contracts/PROTECTION_REGISTRY_MULTIPLICITY_PROFILE_V0_1.md`;
- accepted E4 `docs/execution/OKX_SWAP_CLOSE_RESIDUAL_SIZING_V0_1.md` only as provider-local FP-05 evidence vocabulary;
- current E4 provider Position/order/fill/reconciliation snapshot types and deterministic evidence identity conventions;
- merged E5 FP-04/FP-10 consumer public input expectations;
- merged E6 FP-04/FP-10 persistence/currentness public storage expectations;
- `status/PM_E6_026_REVIEW_20260829.md`;
- active `status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`.

Do not read or execute another Worker's TASK mailbox.

## Implementation boundary

Add provider-neutral deterministic E4 functions/types under E4-owned paths that operate only on supplied in-memory/fixture facts.

At minimum provide:

1. an FP-04 evidence producer for one exact provider object/exposure observation that binds exact provider identity, object/snapshot/generation, local lineage/registry evidence, runtime/project generations, ownership classification, reconciliation status, dispositions/reasons and supersession reference exactly as allowed by the accepted profile;
2. deterministic validation/currentness helpers sufficient to reject malformed, stale, contradictory or unsupported FP-04 producer inputs before evidence is emitted;
3. an FP-10 convergence evidence assembler that binds exact current provider Position/normalized Position facts, execution/fill evidence set, FP-04 evidence rows, optional FP-05 residual evidence, FP-11/terminal-protection evidence, lifecycle projection/execution binding, runtime/project generation and exact convergence state/reasons/dispositions supplied by the accepted owner-authoritative interpretation boundary;
4. deterministic evidence IDs/hashes exactly matching accepted canonical profile rules;
5. explicit supersession references when replacing prior immutable FP-04/FP-10 evidence;
6. zero provider/network/credential dependency.

Do not create a parallel shared contract. If accepted profiles lack a field required for safe deterministic production, record a precise E7 change request and stop at PARTIAL rather than inventing a field or semantic.

## FP-04 ownership / reconciliation rules

E4 may produce only classifications/reconciliation states that are justified by exact supplied lineage/registry/provider facts under the accepted FP-04 profile.

Required fail-closed behavior includes:

- provider object identity/snapshot/generation missing or mismatched -> no current-known-owned evidence;
- current project/runtime/process/config generation mismatch -> fail closed;
- contradictory or unknown local lineage -> no `CURRENT_KNOWN_OWNED`;
- stale/conflicting registry evidence -> no `CURRENT_KNOWN_OWNED`;
- external/manual/untracked object -> preserve external ownership classification and required reinterpretation/reconciliation dispositions; do not silently adopt it;
- prior-generation project object -> preserve prior-generation classification; prior ownership does not transfer current mutation authority;
- ambiguous/multiple object identity -> reconciliation/manual-review path, not guessed ownership;
- `NO_ACTION_CURRENT_KNOWN_OWNED` may be emitted only for the exact accepted current-owned success tuple;
- newer materially different provider/local evidence requires a new immutable evidence object; a later evaluation timestamp alone does not refresh stale evidence.

This task does not authorize provider cleanup/adoption/mutation.

## FP-10 assembly rules

The assembler must not decide E5 lifecycle policy. It may only combine exact owner-authoritative facts into the accepted FP-10 evidence shape.

Required structural invariants:

- terminal/FILLED order status alone never produces `LIFECYCLE_CLOSE_ELIGIBLE`;
- positive normalized actual exposure cannot produce any flat/close-eligible state;
- representable/unrepresentable positive residual remains non-flat;
- provider Position currentness and normalized Position reconciliation must be explicit;
- execution/fill evidence set must be complete/current/compatible when close eligibility is claimed;
- each referenced FP-04 row must bind exact immutable FP-04 evidence ID/hash/object/snapshot/currentness;
- external/manual lineage remains external/manual; assembler must not relabel it current-generation project execution;
- flat exposure does not erase protection; terminal protection clear requires exact accepted current terminal-protection observation/reference;
- FP-10 lifecycle projection and execution-binding refs/hashes must bind exact supplied E5 lifecycle authority;
- runtime/process/config generation is bound when applicable;
- any materially newer provider/Position/execution/FP-04/FP-05/FP-11/lifecycle/runtime generation invalidates prior assembled evidence;
- `LIFECYCLE_CLOSE_ELIGIBLE` may be emitted only when the exact accepted success invariant is already satisfied by supplied facts; it remains evidence for E5 interpretation, not a transition or mutation authority.

Do not manufacture missing Fill/Order/protection/lifecycle evidence.

## E5 / E6 boundary

The produced objects must be consumable by the merged E5 and E6 static candidates without special-case bypasses.

E4 must not:

- call E5 transition functions to decide lifecycle state;
- persist or select current heads using E6 storage logic;
- infer `CLOSED` from missing Position/order rows;
- turn ownership/convergence evidence into provider mutation authority;
- treat accepted static E5/E6 implementations as executable PASS.

## Required tests to define

Add provider-free deterministic E4-owned tests covering at minimum:

### FP-04

- exact current known-owned provider Position/object evidence -> exact accepted current-owned tuple;
- external/manual object -> external classification + reinterpretation/reconciliation disposition, never silent adoption;
- prior runtime/process/config generation -> fail closed / prior-generation path;
- contradictory local lineage -> conflict/reconciliation path;
- stale registry evidence -> no current-known-owned success;
- provider object/snapshot/generation mismatch -> fail closed;
- exact deterministic ID/hash stable across equivalent canonical input;
- materially changed provider/local evidence -> new immutable evidence ID and explicit supersession reference;
- later timestamp alone cannot convert stale/mismatched evidence into current.

### FP-10

- positive Position + terminal order -> not close eligible;
- partial/manual reduction -> external/manual reinterpretation path, no lineage adoption;
- positive representable residual -> non-flat;
- positive unrepresentable residual -> explicit non-flat/fail-closed;
- flat Position + execution/fill ambiguity -> reconciliation-required state;
- flat Position + non-converged terminal protection -> protection-convergence-required state;
- exact flat/current/compatible execution + current FP-04 + terminal protection clear + current lifecycle/binding -> deterministic close-eligible evidence object only;
- missing/mismatched FP-04 dependency -> no close eligibility;
- newer provider/FP-04/FP-05/FP-11/lifecycle/runtime facts invalidate old evidence/currentness;
- deterministic evidence identity independent of input mapping insertion order;
- no provider/network/credentials required.

Do not execute tests through GitHub.

## Verification boundary

All executable verification remains local-only. LF-0 approved-local exact-revision preparation remains blocked.

Unless an independently approved local execution path is explicitly available in current authoritative evidence:

```text
project executable verification = NOT_RUN / NOT_PASS
```

Record exact Windows/local commands for the bounded E4 tests plus relevant existing execution/broker suites. `NOT_RUN` is not PASS.

No provider/network/private API/credential use is required or authorized:

```text
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order submit/cancel/amend/close = 0
SHADOW/PAPER runtime = NOT_STARTED / NOT_AUTHORIZED
10U live-fire = NOT_AUTHORIZED
capital exposure = NONE
Gate D / LIVE = BLOCKED / UNAUTHORIZED
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

## Required durable evidence

Create:

`status/e4/FP04_FP10_EVIDENCE_PRODUCER_20260829.md`

Document:

- task ID;
- exact source/test files changed;
- accepted profiles consumed;
- FP-04 producer semantics and fail-closed classification/currentness behavior;
- FP-10 assembler semantics and exact close-eligibility structural conditions;
- deterministic ID/hash/supersession behavior;
- E5/E6 boundary;
- tests defined;
- local commands/result (`NOT_RUN` if unavailable);
- known limitations / exact E7 dependency if any;
- no provider/credential/runtime/capital authority.

Update `coordination/E4/STATUS.md`, commit, and push the target branch.

## Writable scope

Only E4-owned paths:

- `src/execution/`;
- `src/brokers/` only if an existing provider-neutral reconciliation/evidence module belongs there;
- `tests/execution/`;
- `tests/brokers/` only if directly required;
- `status/e4/FP04_FP10_EVIDENCE_PRODUCER_20260829.md`;
- `coordination/E4/STATUS.md`.

Do not modify:

- `contracts/**`;
- E5/E6/E7 implementation or docs;
- risk/lifecycle policy;
- E6 storage/migrations;
- AgentBridge/local action catalog;
- provider credentials/config/private allowlists;
- provider network clients or mutation dispatch paths unless merely imported as read-only type definitions without behavior change;
- Product Owner authorization artifacts;
- risk limits/leverage/capital thresholds;
- release criteria;
- GitHub Actions/CI files.

## Result classification

### DONE

Use DONE only if bounded implementation/test definitions are complete **and** all required executable verification was actually performed on an approved local environment with PASS evidence.

### PARTIAL

Use PARTIAL when source/test implementation is complete but executable verification remains `NOT_RUN`, or when a precise shared-contract dependency prevents safe completion without inventing semantics.

### BLOCKED

Use BLOCKED only if authoritative repository requirements are contradictory or implementation cannot safely proceed within E4 scope.

## Completion

Read latest `main`, verify wake task ID `E4-20260829-030`, execute only this task, persist evidence, update STATUS, commit/push the target branch, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start provider verification, FP-05 provider mutation translation, FP-11 provider cleanup, E7 integration/requalification, exact-revision preparation, SHADOW/PAPER, 10U live-fire, Gate D, LIVE, mutation, order action or capital movement/exposure.
