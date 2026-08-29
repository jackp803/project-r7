# E7 Current Task

- task_id: `E7-20260829-116`
- issued_at: `2026-08-29T21:00:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-p0-static-closure-20260829`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, accepted FP-02/03/04/05/10/11/16 profiles/designs, merged owner static candidates through E4-20260829-035, `status/PM_E4_035_REVIEW_20260829.md`, `contracts/BOUNDED_LIVE_FIRE_READINESS_PROFILE_V0_1.md`, active LF-0 exact-revision infrastructure blocker

## Objective

Perform the smallest final **credential-free P0 static integration closure/audit and qualification-manifest update** for the currently merged FP-02, FP-03, FP-04, FP-05, FP-10, FP-11, and FP-16 owner-level static implementations.

This is integration/test-definition work only. It must determine whether the merged credential-free implementation graph has any remaining deterministic project-code gap before approved-local exact-revision qualification can be attempted, while preserving all unresolved provider facts and authority boundaries.

Do not execute project code, create Local Job Requests, prepare exact revisions, call providers, inspect/request credentials, launch/restart processes, mutate provider/account state, submit/cancel/amend/close/protection orders, start SHADOW/PAPER/live runtime, expose/move capital, or modify AgentBridge/operator infrastructure.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E7_INTEGRATION.md`;
- `contracts/BOUNDED_LIVE_FIRE_READINESS_PROFILE_V0_1.md`;
- `contracts/RUNTIME_PREFLIGHT_PROFILE_V0_1.md`;
- `contracts/PROTECTION_TRIGGER_VALIDITY_PROFILE_V0_1.md`;
- `contracts/EXTERNAL_PROVIDER_OBJECT_OWNERSHIP_RECONCILIATION_PROFILE_V0_1.md`;
- `contracts/EXTERNAL_MANUAL_CLOSE_LIFECYCLE_CONVERGENCE_PROFILE_V0_1.md`;
- `contracts/PROTECTION_REGISTRY_MULTIPLICITY_PROFILE_V0_1.md`;
- `docs/execution/OKX_SWAP_ACTION_ROLE_CAPABILITY_MATRIX_V0_1.md`;
- merged E4 FP-02 capability resolver and its tests/handoff;
- merged E4 FP-03/04/05/10/11 implementation surfaces;
- merged E5 FP-03/04/10/11 policy/lifecycle consumers;
- merged E6 FP-04/10/11 persistence/currentness/restart surfaces;
- merged E7 FP-16 runtime-preflight evaluator;
- `status/e7/P0_INTEGRATED_DETERMINISTIC_SAFETY_MATRIX_20260829.md`;
- `status/e7/P0_CREDENTIAL_FREE_QUALIFICATION_MANIFEST_20260829.md`;
- `status/PM_E4_035_REVIEW_20260829.md`;
- active `status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`.

E7 may read repository implementation broadly for integration. Do not execute another Worker's TASK mailbox.

## Static integration closure boundary

Review the merged code graph and add/update only E7-owned deterministic integration/safety test definitions and durable matrix/manifest evidence needed to close the credential-free P0 static graph.

The result must distinguish at least:

- `IMPLEMENTED_UNQUALIFIED` project behavior;
- unresolved provider-native facts that remain intentionally fail closed;
- executable verification `NOT_RUN / NOT_PASS`;
- LF-0 exact-revision preparation blocker;
- future Product Owner authority for provider read-only, SHADOW/PAPER, bounded live fire, Gate D/LIVE.

Do not convert static integration completeness into executable PASS or release readiness.

## Required FP-02 integration scenarios

Integrate the newly merged E4 FP-02 boundary with existing P0 safety definitions. At minimum define cross-module tests proving:

1. exact E4 canonical ENTRY owner row may yield only provider-local `REPO_EVIDENCED` mapping evidence; it does not create order dispatch/runtime/Product Owner authority;
2. copied descriptor/hash with forged/mismatched ref/generation cannot become `REPO_EVIDENCED`;
3. role/mode cross-use cannot become positive capability;
4. FP-03 `ACTIONABLE` + FP-11 converged protection facts still leave PROTECTION_STOP provider-native capability unresolved/fail closed;
5. coherent FP-05 sizing still leaves POSITION_EXIT and EMERGENCY_EXIT provider-native endpoint/fieldset/`posSide`/reduce-only semantics unresolved/fail closed;
6. emergency semantics do not bypass capability proof;
7. READ_ONLY_RECONCILIATION remains GET-only/default-deny and cannot be used for mutation;
8. `REPO_EVIDENCED` capability evidence is not equivalent to provider verification, runtime-preflight authorization, or an allowlisted mutation action;
9. changed owner-row provenance/current material invalidates prior positive FP-02 evidence;
10. no provider/network/credential/mutation dependency is introduced by the integration fixture.

## Required FP-16 composition scenarios

Ensure the merged FP-16 evaluator composes with the rest of P0 without collapsing authority layers:

- FP-16 `ELIGIBLE` is admission evidence only and cannot upgrade unresolved FP-02 provider capability;
- a runtime-preflight capability/allowlist reference must not substitute for E4 provider-native capability proof;
- E4 `REPO_EVIDENCED` must not substitute for Product Owner/runtime authorization;
- external-consumer participation remains fail closed when current external authority exists but compatible evidence is missing;
- role-specific preflight remains non-transferable;
- bounded-live-fire mode policy remains undefined/fail closed under current V0.1;
- historical exact-clean evidence for another revision cannot satisfy the current candidate.

## Existing P0 chain preservation

Preserve and, if necessary, re-register deterministic integration coverage for:

- FP-03 breached/equality/stale trigger geometry fail closed;
- FP-04 external/manual/prior/unknown/conflicting ownership no silent adoption;
- FP-05 fresh actual reducible exposure / residual semantics / no requested-entry-quantity fallback;
- FP-10 flatness and lifecycle close convergence, including unresolved active protection blocking CLOSED;
- FP-11 exactly-one intended/current-owned/current-lineage requirement and no cleanup/create mutation authority;
- E6 restart/currentness no false-green from row existence or stale material.

Do not duplicate owner semantics or change shared contracts merely to make integration tests green.

## Credential-free static closure audit

Create a durable E7 conclusion answering exactly:

```text
Are any deterministic credential-free project implementation/test-definition gaps still visible in FP-02/03/04/05/10/11/16 after the currently merged owner candidates?
```

Allowed conclusions:

- `NO_STATIC_IMPLEMENTATION_GAP_IDENTIFIED / UNQUALIFIED` — only if repository inspection supports it; this still means NOT_RUN / NOT_PASS and does not clear LF-0 or unresolved provider facts; or
- `REMAINING_STATIC_GAP` — with an exact owner/path/behavior dependency and no scope expansion.

Do not label LF-2 PASS. Do not infer provider facts. If a genuine implementation defect is found, persist a precise owner change request and stop PARTIAL rather than patch another owner's production code.

## Qualification manifest update

Update the future approved-local credential-free qualification manifest so it includes the exact current merged modules, especially:

- `tests/brokers/test_okx_action_capability.py`;
- `tests/integration/test_runtime_preflight.py`;
- all existing FP-03/04/05/10/11 owner and cross-module suites already registered;
- E6 restart/currentness tests;
- E7 cross-module P0 safety/E2E tests.

The manifest must record:

- exact suite/module list and deterministic order;
- exact Windows PowerShell commands from repository root;
- required approved non-GitHub Windows environment and clean exact revision assertion;
- actual test counts must be measured later, never guessed;
- zero provider request / zero private credential / zero mutation / zero process-launch / zero capital assertions;
- qualification revision remains **TBD until this task is merged and a fresh approved-local exact-clean preparation succeeds**;
- historical `8fbf5fcae2eaf44accdf535121d8abf29ef5c93c` is historical only and cannot qualify the new candidate;
- E7-101 request/job IDs remain terminal/non-reusable;
- LF-0 remains the infrastructure blocker until fresh current-candidate exact-clean evidence exists.

Do not create or submit a Local Job Request in this task.

## Writable scope

Only E7-owned integration/evidence paths:

- `tests/integration/`;
- `tests/e2e/` only if directly needed for static P0 composition;
- cross-module `tests/safety/` only for E7-owned integration safety definitions;
- `status/e7/P0_INTEGRATED_DETERMINISTIC_SAFETY_MATRIX_20260829.md`;
- `status/e7/P0_CREDENTIAL_FREE_QUALIFICATION_MANIFEST_20260829.md`;
- create `status/e7/P0_STATIC_IMPLEMENTATION_CLOSURE_20260829.md`;
- `coordination/E7/STATUS.md`.

Do not modify E1-E6 production code, E4/E5/E6 tests owned by those agents, shared contracts/ADRs unless a true contradiction requires a separately documented E7 change request, provider adapters/auth/config/credentials, AgentBridge/local-action infrastructure, Product Owner authorization artifacts, risk/leverage/capital thresholds, LIVE/release policy, or GitHub Actions/CI.

## Verification boundary

All executable verification remains local-only. LF-0 remains blocked.

Unless separately authoritative approved-local evidence already exists for the exact resulting revision, record:

```text
project executable verification = NOT_RUN / NOT_PASS
P0 integrated credential-free execution = NOT_RUN / NOT_PASS
FP-02 executable verification = NOT_RUN / NOT PASS
FP-16 executable verification = NOT_RUN / NOT PASS
LF-0 = BLOCKED / UNCHANGED
LF-1 = NOT_RUN / NOT PASS
LF-2 = PARTIAL / NOT PASS
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
order/protection actions = 0
process launch/restart = 0
SHADOW/PAPER = NOT_AUTHORIZED
10U bounded live fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

`NOT_RUN` is not PASS. Static closure is not executable qualification.

## Result classification

### DONE

Use DONE only if required executable qualification actually ran on an approved local exact revision and passed. Under current LF-0, DONE is not expected.

### PARTIAL

Use PARTIAL when static integration closure/test definitions/manifest are complete but executable verification remains `NOT_RUN / NOT_PASS`, or a precise remaining static owner gap is identified.

### BLOCKED

Use BLOCKED only if contradictory authoritative requirements prevent even bounded static integration closure.

## Completion

Read latest `main`, verify wake task ID `E7-20260829-116`, execute only this task, persist evidence, update STATUS, commit/push the target branch, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start exact-revision preparation, Local Job Requests, qualification execution, provider verification, credentials, AgentBridge migration, SHADOW/PAPER, bounded live fire, Gate D, LIVE, provider/account mutation, process action, order action, or capital movement/exposure.
