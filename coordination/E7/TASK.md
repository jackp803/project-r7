# E7 Current Task

- task_id: `E7-20260829-105`
- issued_at: `2026-08-29T15:26:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-fp16-runtime-preflight-contract-20260829`
- authority: `agents/E7_INTEGRATION.md`, `agents/PROJECT_MANAGER.md`, `agents/README.md`, accepted `bounded-live-fire-readiness-v0.1`, `status/PM_E4_026_REVIEW_20260829.md`, mature-OKX failure-prevention baseline/audit, active LF-0 exact-revision infrastructure blocker

## Objective

Define the shared **FP-16 runtime preflight identity/readiness profile** required before any provider-capable observation or mutation runtime may start.

This is a contract/docs/status-only E7 task. It must not implement runtime code, modify AgentBridge, create Local Job Requests, call provider endpoints, read credentials, authorize SHADOW/PAPER/10U live-fire, or change Gate D/LIVE status.

The profile must close only the FP-16 contract/design gap. Executable implementation and local qualification remain future tasks.

## Required reading

Read latest `main` and at minimum:

- `README.md`;
- `agents/README.md`;
- `agents/E7_INTEGRATION.md`;
- `agents/PROJECT_MANAGER.md`;
- accepted `contracts/BOUNDED_LIVE_FIRE_READINESS_PROFILE_V0_1.md`;
- current OperationalMode/recovery authority and relevant persistence/runtime-status contracts;
- current exact-revision/local-action governance including `coordination/LOCAL_ACTION_CATALOG.md`;
- current Gate B/Gate C exact-revision qualification evidence only as provenance examples;
- ADR-0010 and current AgentBridge external-consumer dependency only as needed to define temporal/runtime composition prerequisites;
- `status/e7/MATURE_OKX_FAILURE_PREVENTION_GAP_AUDIT_20260829.md` FP-16 row;
- active `status/FP03_COMBINED_REQUALIFICATION_EXACT_REVISION_PREPARATION_BLOCKER_20260829.md`;
- `status/PM_E4_026_REVIEW_20260829.md`.

Do not read or execute another Worker's TASK mailbox.

## Required shared profile

Create:

`contracts/RUNTIME_PREFLIGHT_PROFILE_V0_1.md`

Profile identifier:

`runtime-preflight-v0.1`

The profile must be provider-neutral at the shared boundary and fail closed. Define the canonical runtime-preflight evidence required before a provider-capable process may be considered eligible to start observation/planning/mutation work.

At minimum bind:

1. exact project revision;
2. clean/exact worktree authority where revision-qualified execution is required;
3. exact declared `OperationalMode` and authoritative persisted-mode generation/reference;
4. exact runtime/config generation identifier(s) materially affecting behavior;
5. process identity / single-instance identity;
6. process start generation / boot identity so stale heartbeat from a prior process cannot qualify a new process;
7. current heartbeat/liveness evidence with source time and evaluation time;
8. scheduler/supervisor identity if a separate launcher/watchdog controls restart;
9. registered/allowed action capability set needed for the planned runtime role;
10. current reconciliation readiness state;
11. current market/risk/execution/provider-health prerequisites only as references to authoritative owning evidence, without duplicating their semantics;
12. external-consumer compatibility generation where an external orchestrator such as AgentBridge materially participates;
13. evidence timestamp/ordering constraints;
14. deterministic stable evidence identity/hash/reference rules;
15. exact fail-closed reason vocabulary.

## Required runtime-role classification

At minimum define distinct preflight roles for:

- `CREDENTIAL_FREE_LOCAL_VERIFICATION`
- `PROVIDER_READ_ONLY_OBSERVATION`
- `SHADOW_RUNTIME`
- `PAPER_RUNTIME`
- `BOUNDED_LIVE_FIRE_RUNTIME`

The profile must not make one role's PASS transferable to another role. Each role must declare the minimum capability/evidence class required and every stronger authority must still be explicitly authorized; credentials existing locally do not create provider or LIVE authority.

## Required fail-closed semantics

The profile must reject or block when any of these are unknown/mismatched/stale:

- revision mismatch;
- dirty or unproven exact worktree where required;
- persisted mode vs requested mode mismatch;
- config generation mismatch;
- duplicate process/single-instance conflict;
- heartbeat from wrong process or prior boot generation;
- stale/missing heartbeat;
- unrecognized supervisor/watchdog generation;
- required canonical local action not registered/allowlisted;
- reconciliation not current/ready;
- external consumer compatibility not accepted where required;
- unknown provider/runtime authority;
- requested runtime role exceeds available capability/authorization;
- evidence timestamps violate temporal ordering;
- evidence identity/hash/reference validation fails.

Do not invent numeric heartbeat TTL, retry count, restart interval, or process timeout in V0.1 unless an accepted current contract already defines one. If no accepted numeric threshold exists, define threshold ownership/config-binding and fail closed when the required configured value/evidence is absent.

## Watchdog/restart boundary

Define the distinction between:

- process liveness/heartbeat;
- supervisor/watchdog restart permission;
- persisted `OperationalMode`;
- reconciliation lock/readiness;
- financial kill switch/risk veto.

A watchdog may not restart a provider-capable runtime merely because a process is dead. Restart eligibility must consume the current durable mode/config/reconciliation/preflight facts and must never infer LIVE or mutation authority from the prior process state.

Historical or stale heartbeat/process identity must not survive restart as authority.

## AgentBridge/external-operator boundary

The shared profile may define required evidence fields/compatibility references, but do not modify AgentBridge or invent external implementation behavior.

Document which portions are:

- project-r7 E7/E6 implementation responsibility;
- external operator/AgentBridge implementation responsibility;
- PM evidence/release review responsibility;
- Product Owner authority responsibility only for provider/runtime/capital stages.

The existing LF-0 blocker (`PREPARE_EXACT_REVISION` local allowlist/infrastructure for the current FP-03 candidate) must remain active and must not be resolved by this docs task.

## Deterministic implementation/test handoff

Define the smallest future executable implementation boundaries and credential-free tests needed to prove FP-16, including at minimum:

- exact revision match/mismatch;
- dirty/unproven revision rejection;
- mode match/mismatch;
- config generation match/mismatch;
- process identity duplicate detection;
- prior-boot heartbeat rejection;
- stale/missing heartbeat rejection;
- supervisor/watchdog generation mismatch;
- missing/unallowlisted canonical action capability rejection;
- reconciliation-not-ready rejection;
- external-consumer compatibility mismatch rejection;
- requested runtime role exceeds available authority rejection;
- restart cannot default to SHADOW/PAPER/LIVE;
- financial kill switch remains semantically distinct from operational restart/preflight state;
- no provider/network/credential access required for deterministic tests.

Do not implement these executable changes in this task.

## Required artifacts

- `contracts/RUNTIME_PREFLIGHT_PROFILE_V0_1.md`;
- update `contracts/README.md`;
- `status/e7/FP16_RUNTIME_PREFLIGHT_CONTRACT_HANDOFF_20260829.md` documenting:
  - profile/version;
  - evidence schema/vocabulary;
  - runtime-role matrix;
  - fail-closed reasons;
  - ownership split among E7/E6/external operator/PM/PO;
  - future implementation/test boundaries;
  - relationship to LF-0/LF-3/LF-5/LF-6;
  - current unresolved external dependencies;
  - whether a new ADR is actually required;
  - recommended next Worker task(s), but do not issue them yourself.
- update `coordination/E7/STATUS.md`.

An ADR is optional only if a genuinely new architecture decision cannot be represented by the accepted readiness and operational-mode governance. Do not create one for documentation volume alone.

## Verification boundary

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
Gate D / LIVE = BLOCKED / UNAUTHORIZED
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

`NOT_RUN` is not executable PASS.

## Writable scope

Only:

- `contracts/RUNTIME_PREFLIGHT_PROFILE_V0_1.md`;
- `contracts/README.md`;
- at most one E7 ADR if genuinely necessary;
- `status/e7/FP16_RUNTIME_PREFLIGHT_CONTRACT_HANDOFF_20260829.md`;
- `coordination/E7/STATUS.md`.

Do not modify executable source/tests, E1-E6 code/tests, AgentBridge/local action catalog, provider config/credentials/private allowlists, Product Owner authorization artifacts, risk limits/leverage/capital thresholds, or release criteria.

## Result classification

### DONE

Use DONE only if the shared runtime-preflight profile and handoff are complete, internally consistent with accepted governance, preserve role/authority separation, and grant no executable/provider/runtime/capital authority.

### PARTIAL

Use PARTIAL if a bounded shared architecture ambiguity prevents a deterministic evidence field/ownership definition. Record the exact ambiguity and do not invent semantics.

### BLOCKED

Use BLOCKED only if current authoritative repository evidence is contradictory or insufficient to define the profile safely.

## Completion

Read latest `main`, verify wake task ID `E7-20260829-105`, execute only this docs-only task, persist evidence, update STATUS, commit/push the target branch, and stop on DONE, PARTIAL, or BLOCKED.

Do not self-start FP-16 executable implementation, AgentBridge changes, FP-04/05/10/11, exact-revision preparation, qualification, provider verification, SHADOW/PAPER, 10U live-fire, Gate D, LIVE, mutation, order action or capital movement/exposure.
