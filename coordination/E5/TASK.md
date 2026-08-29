# E5 Current Task

- task_id: `E5-20260829-033`
- issued_at: `2026-08-29T18:24:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e5-fp11-protection-policy-consumer-20260829`
- authority: `agents/E5_RISK_POSITION.md`, `agents/README.md`, accepted `protection-registry-multiplicity-v0.1`, accepted protection/lifecycle projection/execution-binding profiles, merged E4 FP-11 producer static candidate, `status/PM_E4_032_REVIEW_20260829.md`, active LF-0 exact-revision infrastructure blocker

## Objective

Implement the smallest deterministic **provider-neutral E5 FP-11 protection-registry policy/lifecycle reinterpretation consumer** for accepted `ProtectionRegistryMultiplicityEvidence`.

The consumer must answer only the E5-owned safety question: given one exact current Position/lifecycle authority and one exact current FP-11 registry evidence object, what protection/lifecycle policy interpretation is allowed under existing accepted E5 semantics?

This task must not query or mutate a provider, choose/cancel/create/replace provider protection objects, invent provider cleanup authority, persist/select registry heads, redefine the shared FP-11 profile, or treat registry convergence as provider mutation authority.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E5_RISK_POSITION.md`;
- `contracts/PROTECTION_REGISTRY_MULTIPLICITY_PROFILE_V0_1.md`;
- accepted `protection-v0.1` and Position lifecycle projection/execution-binding profiles;
- current E5 protection policy/lifecycle transition/currentness helpers;
- merged E4 FP-11 producer/currentness public boundary in `src/execution/protection_registry_evidence_boundary.py`;
- current E5 FP-04/FP-10 reinterpretation implementation only where terminal/flat protection convergence interacts with existing lifecycle semantics;
- `status/PM_E4_032_REVIEW_20260829.md`;
- active `status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`.

Do not read or execute another Worker's TASK mailbox.

## Implementation boundary

Add E5-owned provider-neutral deterministic functions/types that consume:

1. one exact current canonical Position and its exact authoritative observation reference/hash;
2. one exact current lifecycle projection and, where applicable, lifecycle execution binding;
3. one exact FP-11 `ProtectionRegistryMultiplicityEvidence` object;
4. currentness material sufficient to prove the FP-11 evidence still binds the exact current Position/lifecycle generation;
5. existing E5 protection policy/configuration inputs already accepted by repository contracts, only where required to choose an existing E5 action/transition;
6. optional prior E5 interpretation result only if existing E5 patterns require immutable/currentness identity.

Produce an E5-owned deterministic interpretation result using existing E5 action/lifecycle vocabulary and existing shared lifecycle events only. Do not create a new cross-module contract. If safe policy interpretation requires an undefined shared event/field/semantic, persist a precise E7 change request and stop at PARTIAL rather than inventing it.

## Required safety semantics

### Registry evidence validity/currentness

- reject unsupported profile/schema/identity/hash/reference material;
- require exact Position ID/ref/hash/observation binding;
- require exact lifecycle projection/binding/current generation where supplied by FP-11;
- materially newer Position/lifecycle/provider-set/FP-11 evidence invalidates an older E5 interpretation;
- timestamp-only reevaluation must not convert stale/non-converged evidence into healthy protection;
- `NOT_RUN`, merge acceptance, or static candidate status is never executable PASS.

### Converged exactly-one path

The only registry evidence that may support a healthy unique-protection interpretation is the exact shared success tuple:

```text
multiplicity_state = EXACTLY_ONE_INTENDED_ACTIVE_PROTECTION
registry_status = CONVERGED_EXACTLY_ONE_INTENDED
required_dispositions = [NO_ACTION_REGISTRY_CONVERGED]
reason_codes = [EXACT_SINGLE_INTENDED_PROTECTION_CONVERGED]
```

Even this tuple is observation/policy input only. It must not itself create provider mutation authority.

If the current E5 lifecycle already claims `OPEN_PROTECTED` or `PROFIT_PROTECTED` and all exact Position/lifecycle/currentness bindings remain valid, the consumer may preserve the existing healthy protected interpretation using existing E5 semantics. It must not fabricate a new provider verification event merely because a row exists.

If lifecycle state is incompatible with the exact current registry evidence, use existing E5 reconciliation/reinterpretation semantics; do not silently force either side to match.

### Missing protection

For a current open Position with:

```text
multiplicity_state = NO_ACTIVE_PROTECTION_OBSERVED
registry_status = MISSING_PROTECTION_REINTERPRETATION_REQUIRED
```

E5 must treat healthy protected state as no longer safely established.

Use only existing accepted E5 protection/lifecycle policy to determine whether the correct bounded output is a fresh protection action, emergency exit, reconciliation/lock, or another existing safe result. The implementation must not treat the FP-11 evidence itself as permission to create protection.

If current accepted E5 semantics are insufficient to make that choice deterministically, return a fail-closed reconciliation/policy-required result or raise a precise shared-policy dependency; do not invent a new autonomous recovery policy.

### Multiple/orphan/external/prior/conflict/unknown/stale paths

Any of these states remain non-healthy and fail closed:

- `MULTIPLE_ACTIVE_PROTECTIONS`
- `ORPHAN_OR_EXTERNAL_PROTECTION_PRESENT`
- `OWNERSHIP_CONFLICT_PRESENT`
- `PROTECTION_SET_STALE`
- `PROTECTION_SET_UNKNOWN`

Required behavior:

- no provider-object winner selection;
- no blind cancel-all;
- no blind create-another;
- no adoption of external/prior objects by similarity;
- no cleanup target authority;
- no new-exposure approval from registry evidence;
- preserve explicit reconciliation/manual-review/refresh requirements;
- use existing E5 lifecycle/risk veto/reconciliation semantics when a protected lifecycle claim is contradicted by non-converged registry truth.

### Terminal/flat interaction

If FP-11 includes `FP10_TERMINAL_FLAT_PROTECTION_CONVERGENCE_REQUIRED`, preserve that unresolved provider protection remains a terminal-close convergence dependency.

E5 must not emit a false-green terminal interpretation solely because canonical Position is flat. Compose with existing FP-10/external-close reinterpretation semantics where applicable; do not erase unresolved active protection and do not authorize E4 cleanup/cancel.

### Financial safety boundary

This consumer may produce only existing E5 policy/lifecycle outputs. It must not:

- raise leverage/size/loss limits;
- weaken kill switches;
- bypass current risk vetoes;
- generate raw provider commands;
- convert HOLD/reconciliation evidence into direct E4 mutation authority;
- authorize LIVE/SHADOW/PAPER or capital exposure.

## Deterministic identity/currentness

If the E5 interpretation result follows existing deterministic identity/hash conventions, bind at minimum:

- exact Position identity/hash/observation;
- exact lifecycle projection/revision/binding refs as applicable;
- exact FP-11 evidence ID and canonical hash;
- exact resulting existing E5 action/event/next-state/reasons;
- behavior-affecting policy/config generation when applicable.

Material input change must invalidate prior interpretation. A later evaluation timestamp alone must not refresh stale evidence or create a materially new decision.

## Required tests to define

Add provider-free deterministic E5-owned tests covering at minimum:

- exact current converged FP-11 + compatible current protected lifecycle -> healthy protected interpretation preserved without provider mutation authority;
- converged FP-11 with incompatible/stale lifecycle binding -> fail closed/reinterpretation, not forced healthy;
- complete/current missing protection while lifecycle claims protected -> healthy protected claim rejected and existing E5 safe reinterpretation path used;
- missing protection does not itself authorize a PROTECT provider mutation;
- multiple active protections -> fail closed, no winner/cancel target;
- one intended plus external/prior/orphan extra -> fail closed, no adoption;
- ownership conflict/unknown -> manual-review/reconciliation path;
- stale/incomplete/unknown provider set -> refresh/reconciliation path;
- changed Position/lifecycle/FP-11 evidence invalidates old interpretation;
- timestamp-only reevaluation does not refresh stale/non-converged truth;
- terminal/flat + unresolved active protection preserves FP-10 terminal-protection convergence dependency and does not false-green CLOSED solely from flat Position;
- no provider/network/credentials/mutation dependency;
- existing protection/lifecycle/risk safety tests remain included in the later approved-local verification matrix.

Do not execute tests through GitHub.

## Verification boundary

All executable verification is local-only. LF-0 approved-local exact-revision preparation remains blocked.

Unless independently approved local execution authority is explicitly available in current repository evidence:

```text
project executable verification = NOT_RUN / NOT_PASS
```

Record exact future Windows/local commands for bounded FP-11 E5 tests plus relevant existing position/risk/safety regressions. `NOT_RUN` is not PASS.

```text
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
protection query/create/cancel/amend/replace = 0
order actions = 0
SHADOW/PAPER runtime = NOT_STARTED / NOT_AUTHORIZED
10U live-fire = NOT_AUTHORIZED
capital exposure = NONE
LF-0 = BLOCKED / UNCHANGED
LF-2 = NOT PASS
Gate D / LIVE = BLOCKED / UNAUTHORIZED
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

## Required durable evidence

Create:

`status/e5/FP11_PROTECTION_REGISTRY_POLICY_CONSUMER_20260829.md`

Document task ID, exact source/test files changed, accepted profile inputs, exact E5 interpretation boundary, converged/missing/multiple/orphan/conflict/stale/unknown behavior, terminal/flat FP-10 interaction, deterministic identity/currentness behavior if implemented, tests defined, exact future local commands/result, known limitations/shared-contract dependencies, and confirmation of zero provider/credential/runtime/capital authority.

Update `coordination/E5/STATUS.md`, commit, and push the target branch.

## Writable scope

Only E5-owned paths:

- `src/position/`;
- `src/risk/` only if a minimal existing risk-veto integration is directly required;
- `tests/position/`;
- `tests/risk/` and `tests/safety/` only if directly required by the bounded E5 interpretation;
- `status/e5/FP11_PROTECTION_REGISTRY_POLICY_CONSUMER_20260829.md`;
- `coordination/E5/STATUS.md`.

Do not modify `contracts/**`, E4/E6/E7 implementation/docs, provider transport/auth/config/credentials, AgentBridge/local action catalog, provider allowlists, Product Owner authorization artifacts, release criteria, leverage/capital thresholds, or GitHub Actions/CI files.

## Result classification

### DONE

Use DONE only if implementation/test definitions are complete and required executable verification actually ran on an approved local exact revision with PASS evidence.

### PARTIAL

Use PARTIAL when implementation/test definitions are complete but executable verification remains `NOT_RUN`, or a precise shared-contract/policy dependency prevents safe completion without invented semantics.

### BLOCKED

Use BLOCKED only for contradictory authoritative requirements or a safety dependency that prevents bounded implementation within E5 scope.

## Completion

Read latest `main`, verify wake task ID `E5-20260829-033`, execute only this task, persist evidence, update STATUS, commit/push the target branch, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start E4 provider protection mutation/cleanup, E6 persistence, E7 integration/requalification, exact-revision preparation, provider verification, SHADOW/PAPER, bounded live-fire, Gate D, LIVE, order action, or capital movement/exposure.
