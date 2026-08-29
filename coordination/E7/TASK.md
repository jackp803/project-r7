# E7 Current Task

- task_id: `E7-20260829-111`
- issued_at: `2026-08-29T19:40:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-p0-integrated-safety-matrix-20260829`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, accepted FP-03/FP-04/FP-05/FP-10/FP-11/FP-16 profiles/designs, merged owner static candidates through E6-20260829-029, `status/PM_E6_029_REVIEW_20260829.md`, `contracts/BOUNDED_LIVE_FIRE_READINESS_PROFILE_V0_1.md`, active LF-0 exact-revision infrastructure blocker

## Objective

Define the smallest **credential-free cross-module P0 integrated deterministic safety/E2E qualification matrix and test definitions** for the currently merged owner-level static candidates.

This is an integration/test-definition task only. Do not execute project code, create Local Job Requests, prepare exact revisions, call provider endpoints, read/request credentials, start SHADOW/PAPER/live runtime, submit/cancel/amend/close orders, mutate provider/account state, or expose/move capital.

The task must make the future approved-local qualification mechanically clear while preserving every current fail-closed boundary. Test definitions or merge status must never be represented as executable PASS.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E7_INTEGRATION.md`;
- `contracts/BOUNDED_LIVE_FIRE_READINESS_PROFILE_V0_1.md`;
- `contracts/PROTECTION_TRIGGER_VALIDITY_PROFILE_V0_1.md`;
- `contracts/EXTERNAL_PROVIDER_OBJECT_OWNERSHIP_RECONCILIATION_PROFILE_V0_1.md`;
- `contracts/EXTERNAL_MANUAL_CLOSE_LIFECYCLE_CONVERGENCE_PROFILE_V0_1.md`;
- `contracts/PROTECTION_REGISTRY_MULTIPLICITY_PROFILE_V0_1.md`;
- `contracts/RUNTIME_PREFLIGHT_PROFILE_V0_1.md`;
- E4 accepted FP-02 capability matrix/design and merged provider-neutral FP-03/FP-04/FP-05/FP-10/FP-11 implementation surfaces currently on `main`;
- E5 merged FP-03, FP-04/FP-10, and FP-11 policy/lifecycle consumer surfaces currently on `main`;
- E6 merged FP-04/FP-10 and remediated FP-11 persistence/currentness/restart surfaces currently on `main`;
- `status/PM_MATURE_OKX_BOT_FAILURE_PREVENTION_BASELINE_20260829.md`;
- `status/PM_10U_BOUNDED_LIVE_FIRE_READINESS_PLAN_20260829.md`;
- `status/PM_E6_029_REVIEW_20260829.md`;
- `status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`.

E7 may read the repository broadly for integration, but do not execute another Worker's TASK mailbox.

## Integration boundary

Add E7-owned deterministic integration/safety/E2E test definitions and a durable matrix that compose the accepted/merged owner surfaces without reimplementing their domain semantics.

At minimum, the matrix must distinguish:

1. **implemented static candidate behavior** that can be exercised later credential-free;
2. **contract/design-only behavior** that has no project implementation yet;
3. **provider-specific capability facts still unresolved/fail-closed**;
4. **approved-local executable verification still NOT_RUN / NOT_PASS**;
5. **future Product Owner authority dependencies** for provider read-only, SHADOW/PAPER, bounded live-fire, Gate D/LIVE.

Do not redefine shared contracts merely to make the matrix green. If integration exposes a genuine contract contradiction, document a precise E7-owned contract/change request and stop at PARTIAL rather than weakening a fail-closed invariant.

## Required integrated safety scenarios

Define provider/network/credential-free cross-module tests for at least the following.

### FP-03 trigger validity + protection policy

- LONG stop at/above LAST_PRICE and SHORT stop at/below LAST_PRICE remain non-actionable/fail closed;
- equality remains breached/non-actionable;
- unchanged breached evidence cannot be blindly retried into protection success;
- materially newer market/Position/lifecycle evidence invalidates prior trigger-validity decision;
- trigger geometry does not choose provider triggerPxType or create mutation authority.

### FP-04 ownership + external/manual truth

- current-generation-owned exact object may remain current only with exact immutable provider snapshot/reference/generation lineage;
- external/manual/prior-generation/unknown/conflicting ownership cannot be silently adopted;
- newer external/manual Position truth requires E5 reinterpretation;
- missing local rows or similarity cannot establish ownership;
- uncertain ownership grants no cleanup/cancel/mutation authority.

### FP-05 close/residual sizing

- close sizing is driven by fresh actual current Position/provider-reducible exposure, never original entry/requested quantity;
- positive representable residual is not flat;
- positive non-representable residual remains explicit fail-closed state;
- metadata/capability unknown or stale remains `CLOSE_CAPABILITY_UNPROVEN` / `METADATA_STALE_OR_UNKNOWN` as applicable;
- generic canonical `reduce_only=true` never proves unresolved provider-native close semantics;
- ACK/FILLED close order alone never proves flatness.

### FP-10 lifecycle close convergence

- terminal/FILLED order + positive Position cannot close lifecycle;
- external/manual partial reduction remains open/reinterpretation-required;
- flat provider Position with unresolved execution/fill ambiguity cannot force CLOSED;
- flat Position with unresolved active protection cannot force terminal convergence;
- `LIFECYCLE_CLOSE_ELIGIBLE` remains input evidence to E5 only, not a transition emitted by E4/E6;
- TradeResult completeness remains distinct and no Fill/OrderRequest lineage is fabricated.

### FP-11 protection registry / multiplicity

- only exact one intended/current-owned/current-known-owned/exact-lineage object with complete/current set may be healthy;
- zero active protection cannot itself authorize create/PROTECT;
- two or more active protection objects cannot select a winner;
- intended + external/prior/orphan remains non-converged;
- ownership conflict/unknown/stale/incomplete set remains non-green;
- flat/CLOSED + unresolved active protection remains FP-10 terminal-protection convergence/reconciliation-required;
- no cleanup target, cancel-all, create-another, or provider mutation authority is produced.

### E6 restart/currentness composition

- real E6 Paper lifecycle writer output composes with remediated FP-11 restart currentness using lifecycle projection payload hash in its own domain and Position hash in its own domain;
- current-head selection depends only on explicit valid supersession, never insertion/evaluation/persist time;
- competing heads, missing predecessor, cycle, cross-lineage supersession, stored payload/hash corruption, missing current E5 interpretation, stale FP-04 dependency, lifecycle/binding/provider-set/runtime mismatch all prevent healthy read model;
- restart cannot false-green protected or CLOSED state from row existence alone.

### Runtime-preflight / capability gaps

Do not invent missing implementation.

- Represent `runtime-preflight-v0.1` as a required future runtime authority boundary where the current repository lacks a qualified implementation;
- keep role-specific runtime preflight non-transferable across credential-free/provider-read-only/SHADOW/PAPER/bounded-live-fire roles;
- absence, stale generation, dead process, missing heartbeat/supervisor/action allowlist or incompatible external consumer must remain non-authorizing;
- keep FP-02 unresolved provider-native close/protection capability facts explicit and fail closed;
- test/matrix status must distinguish `STATIC_TEST_DEFINED`, `IMPLEMENTED_UNQUALIFIED`, `CONTRACT_ONLY`, `UNRESOLVED_PROVIDER_FACT`, and `NOT_RUN / NOT_PASS` rather than collapsing them into PASS.

## Deterministic qualification manifest

Create a durable E7 manifest for the future approved-local credential-free P0 qualification that lists:

- exact test modules/suites to run after this integration work is merged;
- dependency/order expectations;
- exact Windows PowerShell commands from repository root;
- required environment assertions (approved non-GitHub local host, exact revision, clean worktree, expected Python/runtime assumptions already accepted by project evidence);
- explicit zero-provider-request / zero-credential / zero-mutation assertions;
- expected evidence fields to record per suite;
- explicit rule that qualification revision is **TBD until the integration candidate is merged and exact-clean preparation succeeds**;
- explicit rule that historical exact-clean `8fbf5fcae2eaf44accdf535121d8abf29ef5c93c` does not qualify the new integrated candidate;
- explicit rule that E7-101 request/job IDs are terminal and must not be reused.

Do not create/submit any Local Job Request in this task.

## Required tests/files

Preferred E7-owned writable paths:

- `tests/integration/`;
- `tests/e2e/`;
- `tests/safety/` only for genuinely cross-module safety scenarios not owned by E4/E5;
- `status/e7/` for the integrated P0 matrix/qualification manifest/handoff;
- `coordination/E7/STATUS.md`.

You may add a minimal E7-owned integration fixture/helper under `tests/` if needed. Do not modify E1-E6 production source merely to make integration tests easier. If a domain defect is found, persist a bounded defect/change request for the owner.

Do not modify provider adapters/auth/config/credentials, AgentBridge/local-action infrastructure, Product Owner authorization artifacts, leverage/risk/capital thresholds, operational LIVE policy, or GitHub Actions/CI.

## Verification boundary

All executable verification is local-only. LF-0 remains blocked.

Unless separately authoritative approved-local execution evidence becomes available during this task—which must itself already exist in repository authority, not be invented—record:

```text
project executable verification = NOT_RUN / NOT_PASS
integrated P0 safety/E2E matrix execution = NOT_RUN / NOT_PASS
LF-0 = BLOCKED / UNCHANGED
LF-1 = NOT_RUN / NOT_PASS
LF-2 = PARTIAL / NOT PASS
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order/protection actions = 0
SHADOW/PAPER = NOT_AUTHORIZED
10U bounded live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

`NOT_RUN` is not PASS. Static composition must not alter release readiness.

## Required durable evidence

Create at minimum:

- `status/e7/P0_INTEGRATED_DETERMINISTIC_SAFETY_MATRIX_20260829.md`;
- `status/e7/P0_CREDENTIAL_FREE_QUALIFICATION_MANIFEST_20260829.md`.

Document task ID, exact files changed, owner surfaces composed, scenario matrix, implementation-vs-contract-only-vs-provider-fact gaps, exact future local commands, LF-0 blocker, limitations/next owner dependencies, and confirmation of zero provider/credential/runtime/capital authority.

Update `coordination/E7/STATUS.md`, commit, and push the target branch.

## Result classification

### DONE

Use DONE only if integration definitions are complete **and** required executable verification actually ran on an approved local exact revision with PASS evidence. Under the current LF-0 blocker, DONE is not expected.

### PARTIAL

Use PARTIAL when integration/test definitions and durable matrix/manifest are complete but executable verification remains `NOT_RUN / NOT_PASS`, or a precise owner/shared-contract dependency remains.

### BLOCKED

Use BLOCKED only for a contradictory authoritative requirement that prevents even bounded static integration definition.

## Completion

Read latest `main`, verify wake task ID `E7-20260829-111`, execute only this task, persist evidence, update STATUS, commit/push the target branch, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start exact-revision preparation, Local Job Requests, qualification execution, provider verification, SHADOW/PAPER, 10U bounded live-fire, Gate D, LIVE, mutation, order action, or capital movement/exposure.
