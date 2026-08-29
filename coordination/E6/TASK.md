# E6 Current Task

- task_id: `E6-20260829-028`
- issued_at: `2026-08-29T18:42:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e6-fp11-persistence-currentness-20260829`
- authority: `agents/E6_PLATFORM.md`, `agents/README.md`, accepted `protection-registry-multiplicity-v0.1`, merged E4 FP-11 producer static candidate, merged E5 FP-11 policy consumer static candidate, `status/PM_E5_033_REVIEW_20260829.md`, active LF-0 exact-revision infrastructure blocker

## Objective

Implement the smallest deterministic **provider-neutral E6 FP-11 immutable persistence, current-head/currentness and restart/read-model consumer** for accepted `ProtectionRegistryMultiplicityEvidence` plus the merged E5 FP-11 interpretation result.

The platform must preserve exact evidence history and expose fail-closed current state across restart. It must never infer `protected`, `healthy`, `converged`, cleanup authority, provider mutation authority, or lifecycle truth merely because a database row exists.

No provider/network/credential/runtime/live authority is granted.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E6_PLATFORM.md`;
- `contracts/PROTECTION_REGISTRY_MULTIPLICITY_PROFILE_V0_1.md`;
- accepted position lifecycle projection/execution-binding profiles;
- merged E4 FP-11 producer/currentness public boundary;
- merged E5 `src/position/protection_registry_policy.py` public interpretation/result shape;
- current E6 FP-04/FP-10 append-only/currentness/restart patterns from E6-20260829-026;
- `status/PM_E5_033_REVIEW_20260829.md`;
- active `status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`.

Do not read or execute another Worker's TASK mailbox.

## Implementation boundary

Within E6-owned storage/platform paths, add deterministic persistence/read-model behavior for:

1. immutable FP-11 registry evidence history keyed by exact `protection_registry_evidence_id` and canonical payload/hash identity;
2. explicit supersession-chain storage for the same logical Position/intended-protection lineage;
3. deterministic current-head selection that rejects competing heads, missing predecessors, cycles, cross-lineage supersession, duplicate ID with changed payload, or reference/hash corruption;
4. immutable E5 FP-11 interpretation/audit records bound to exact Position/lifecycle/binding + exact FP-11 source evidence/material hash;
5. restart/reload currentness evaluation that rebinds the selected FP-11 head and E5 interpretation to exact current Position/lifecycle/provider-set/runtime material supplied by owner-authoritative inputs;
6. a platform/read-model health state that distinguishes at least current healthy unique protection, non-converged/reconciliation-required, incomplete/conflict, stale/superseded, and unknown/unavailable without inventing new shared lifecycle semantics.

Use existing E6 migration/repository/currentness conventions where possible. Do not create a parallel shared contract. If a shared semantic is missing, persist a precise E7 change request and stop at PARTIAL rather than inventing it.

## Fail-closed persistence/currentness requirements

- FP-11 evidence is append-only and immutable; update/delete of accepted immutable evidence must be rejected mechanically.
- same evidence ID + changed payload/hash is corruption/conflict, never overwrite.
- explicit supersession is the only basis for selecting a newer immutable evidence object in one logical lineage; insertion time, max row ID, latest `evaluated_at`, or newest database timestamp is not authority.
- competing unsuperseded heads -> conflict/reconciliation-required, not arbitrary winner selection.
- missing predecessor, broken supersession link, cycle, cross-Position/cross-lineage link -> incomplete/conflict, never current healthy.
- stale/mismatched Position/lifecycle/projection/binding/provider-set/runtime generation invalidates current FP-11 health.
- a persisted exact-one/converged FP-11 row is not healthy if current E5 interpretation is missing, stale, source-mismatched, non-current, or no longer bound to the same exact current authority.
- a persisted E5 `healthy_protection=True` record is never sufficient by itself; current FP-11 evidence and current Position/lifecycle bindings must still match.
- missing/multiple/orphan/external/conflict/stale/unknown FP-11 evidence remains visible and fail closed after restart; do not cosmetically map it to green/healthy.
- terminal/flat Position with unresolved active protection must preserve the FP-10 terminal protection convergence dependency; restart must not render false-green `CLOSED` solely from flat Position/local lifecycle rows.
- no storage/read-model state may authorize provider query/create/cancel/amend/replace/cleanup or new exposure.

## Required deterministic tests to define

Add E6-owned provider-free tests covering at minimum:

- immutable insert/read/reload of one valid FP-11 evidence row;
- update/delete rejection for immutable FP-11 evidence;
- duplicate ID + changed payload/hash rejection;
- explicit same-lineage supersession selects one current head;
- timestamp-only/newer-row insertion without valid supersession does not replace authority;
- competing heads -> conflict/non-green;
- missing predecessor/cycle/cross-lineage supersession -> fail closed;
- exact current converged FP-11 + current matching E5 interpretation + current Position/lifecycle/binding -> healthy unique-protection read model only;
- missing/stale/mismatched E5 interpretation prevents healthy read model;
- missing/multiple/orphan/external/conflict/stale/unknown FP-11 remains non-green after restart;
- changed Position/lifecycle/provider-set/runtime generation invalidates previously healthy persisted evidence;
- flat/CLOSED + unresolved active protection remains terminal convergence/reconciliation-required after restart;
- no provider/network/credentials/mutation dependency;
- migrations/restart behavior are included in later approved-local verification.

Do not execute tests through GitHub.

## Verification boundary

All executable verification is local-only. LF-0 approved-local exact-revision preparation remains blocked.

Unless an independently approved local exact-revision path is explicitly available:

```text
project executable verification = NOT_RUN / NOT_PASS
```

Record exact future Windows/local commands for bounded storage/migration/restart tests and relevant FP-11 E4/E5/E6 regressions. `NOT_RUN` is not PASS.

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

`status/e6/FP11_PERSISTENCE_CURRENTNESS_RESTART_20260829.md`

Document task ID, exact schema/migration/source/test files changed, immutable/supersession/current-head behavior, E5 interpretation binding, restart/read-model fail-closed behavior, tests defined, exact future local commands/result, limitations/downstream E7 integration needs, and confirmation of zero provider/credential/runtime/capital authority.

Update `coordination/E6/STATUS.md`, commit, and push the target branch.

## Writable scope

Only E6-owned paths:

- `src/storage/`;
- `src/platform/` only for bounded read-model/currentness integration;
- `tests/storage/`;
- `tests/platform/` only if directly required;
- E6-owned migrations/schema files under existing project conventions;
- `status/e6/FP11_PERSISTENCE_CURRENTNESS_RESTART_20260829.md`;
- `coordination/E6/STATUS.md`.

Do not modify `contracts/**`, E4/E5/E7 implementation/docs, provider transport/auth/config/credentials, AgentBridge/local action catalog, provider allowlists, Product Owner authorization artifacts, risk/lifecycle policy, release criteria, leverage/capital thresholds, or GitHub Actions/CI files.

## Result classification

### DONE
Use DONE only if implementation/test definitions are complete and required executable verification actually ran on an approved local exact revision with PASS evidence.

### PARTIAL
Use PARTIAL when bounded implementation/test definitions are complete but executable verification remains `NOT_RUN`, or a precise shared-contract dependency prevents safe completion.

### BLOCKED
Use BLOCKED only for contradictory authoritative requirements or a safety dependency that prevents bounded implementation within E6 scope.

## Completion

Read latest `main`, verify wake task ID `E6-20260829-028`, execute only this task, persist evidence, update STATUS, commit/push the target branch, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start provider verification, E7 integration/requalification, exact-revision preparation, SHADOW/PAPER, bounded live-fire, Gate D, LIVE, mutation, order action, or capital movement/exposure.
