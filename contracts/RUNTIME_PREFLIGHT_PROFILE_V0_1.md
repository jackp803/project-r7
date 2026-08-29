# Runtime Preflight Identity / Readiness Profile — V0.1

> Parent governance: `contracts-v0.1` + `bounded-live-fire-readiness-v0.1`  
> Profile identifier: `runtime-preflight-v0.1`  
> Status: `BASELINE`  
> Technical authority: E7 Integration / Architecture / System QA / Release Engineer  
> Decision task: `E7-20260829-105`

## 1. Purpose

`runtime-preflight-v0.1` defines the provider-neutral, fail-closed evidence required before one exact project-r7 process may be considered **eligible** to begin a declared runtime role.

The profile closes the FP-16 contract/design gap only:

```text
wrong revision / wrong process / wrong mode / wrong config / stale heartbeat
!= healthy runtime
```

It composes existing authority rather than replacing it:

- Git/operator evidence owns exact revision and approved-local process facts;
- E6 owns durable `OperationalMode` and restart/reconciliation storage facts;
- E4 owns execution/provider-health facts;
- E5 owns financial risk veto / kill-switch / risk-admission facts;
- E7 owns this preflight profile and cross-module compatibility;
- external operator / AgentBridge owns launcher, supervisor, process identity, heartbeat and local action allowlisting where it participates;
- PM reviews release evidence;
- Product Owner remains final authority for provider/runtime/capital stages.

An `ELIGIBLE` preflight result is **not** provider authority, order authority, SHADOW/PAPER authority, bounded-live-fire authority, Gate D, or LIVE authorization. It proves only that the exact declared preflight inputs are coherent for the exact declared runtime role and authorization generation.

## 2. Compatibility decision

Classification:

```text
ADDITIVE_SHARED_EVIDENCE_PROFILE
schema_version = contracts-v0.1 / unchanged
bounded-live-fire-readiness-v0.1 = referenced / unchanged
OperationalMode semantics = referenced / unchanged
```

No existing serialized domain object is amended. No new `OperationalMode` value is introduced. In particular, `BOUNDED_LIVE_FIRE_RUNTIME` is a preflight **role classification**, not a new durable OperationalMode and not a synonym for recurring `LIVE`.

No ADR is required for V0.1 because the profile does not change architecture direction, state-machine ownership or runtime authority. It makes already-required runtime admission facts explicit and versioned.

## 3. Canonical evidence object

Canonical shared object:

```text
RuntimePreflightEvidence
```

Required top-level fields:

- `schema_version` — exactly `contracts-v0.1`;
- `runtime_preflight_profile_version` — exactly `runtime-preflight-v0.1`;
- `runtime_preflight_id` — deterministic identity from section 15;
- `runtime_role` — one value from section 5;
- `launch_intent` — `START | RESTART | VERIFY_EXISTING`;
- `evaluated_at` — RFC 3339 UTC preflight decision time;
- `project_revision` — exact full project commit SHA being admitted;
- `revision_authority_ref` — sanitized exact-revision evidence reference;
- `revision_authority_hash` — canonical `sha256:<lowercase hex>` of the referenced sanitized revision evidence;
- `worktree_classification` — `EXACT_CLEAN | CLEAN_UNQUALIFIED | DIRTY | UNKNOWN`;
- `requested_operational_mode` — exact existing durable mode expected for the role;
- `operational_mode_transition_id` — exact current E6 transition identity;
- `operational_mode_revision` — exact current E6 non-negative mode revision;
- `operational_mode_payload_hash` — exact current E6 mode payload hash;
- `runtime_config_generation_id` — immutable generation identifier for all behavior-affecting runtime configuration;
- `runtime_config_hash` — hash of the canonical sanitized configuration envelope;
- `process_instance_id` — opaque identity of the exact running process instance;
- `process_start_generation_id` — immutable boot/start generation for that process;
- `process_started_at` — RFC 3339 UTC process-start observation;
- `single_instance_status` — `SINGLE | CONFLICT | UNKNOWN`;
- `heartbeat_evidence` — exact heartbeat object from section 7;
- `supervisor_evidence` — exact supervisor/watchdog object from section 8;
- `capability_evidence` — exact local action/capability object from section 9;
- `reconciliation_evidence` — exact readiness object from section 10;
- `dependency_evidence` — deterministic sequence of owner-authoritative references from section 11;
- `external_consumer_evidence` — external compatibility object from section 12 or `null` only when the declared role proves no external orchestrator materially participates;
- `authorization_evidence` — exact role/authority object from section 13;
- `preflight_status` — `ELIGIBLE | FAIL_CLOSED`;
- `reason_codes` — deterministic ordered sequence from section 14.

The evidence object contains sanitized identities/references/hashes only. It must not persist credentials, secret values, local filesystem paths, raw command lines, provider signatures, provider tokens, exact account balances or raw provider payloads.

## 4. Exact revision and worktree binding

A preflight claim is valid only for the exact `project_revision` recorded in the evidence.

When the declared role is revision-qualified, `worktree_classification` must be exactly:

```text
EXACT_CLEAN
```

and the exact revision authority must prove that same full SHA on the approved environment/generation.

Rules:

- another revision's clean worktree is not transferable;
- a docs-only assertion does not establish `EXACT_CLEAN`;
- `CLEAN_UNQUALIFIED` is not sufficient when exact revision qualification is required;
- `DIRTY` or `UNKNOWN` is always fail closed;
- historical exact-revision evidence may remain historical but cannot qualify a newer process/revision;
- a terminal refused preparation request is not evidence of a prepared worktree and cannot be retried under the same request identity.

Current LF-0 blocker remains authoritative for candidate `9462b2594675b2e28388f55a2af189100b7cbdfc`; this profile does not resolve it.

## 5. Runtime-role classification

`runtime_role` is exactly one of:

- `CREDENTIAL_FREE_LOCAL_VERIFICATION`
- `PROVIDER_READ_ONLY_OBSERVATION`
- `SHADOW_RUNTIME`
- `PAPER_RUNTIME`
- `BOUNDED_LIVE_FIRE_RUNTIME`

A PASS/`ELIGIBLE` for one role is never transferable to another role.

### 5.1 Role matrix

| Runtime role | Provider/network capability | Required role authority | OperationalMode relationship | Required reconciliation/dependency class | External consumer requirement |
|---|---|---|---|---|---|
| `CREDENTIAL_FREE_LOCAL_VERIFICATION` | No provider/network capability for the project verification itself | Exact active task/request/action authority; no provider or capital authority | Must bind the exact current durable mode/config; the verification role itself does not promote mode | Exact revision/worktree and any test-harness prerequisites only; no provider-health fact may be fabricated | Required when an external runner/supervisor materially executes or launches the job |
| `PROVIDER_READ_ONLY_OBSERVATION` | Read-only provider capability only; zero mutation | Separate current Product Owner/PM-governed read-only authorization plus secure local credential mechanism | Must bind current durable mode and may not infer SHADOW/LIVE merely from read-only access | Provider/account/clock/reconciliation evidence references as required by the authorized observation plan | Required when AgentBridge/operator launches/controls the observation |
| `SHADOW_RUNTIME` | Provider observation/read-only capability only under accepted SHADOW boundary | Explicit current SHADOW runtime authorization; historical consumed authorization is invalid | Exact persisted mode must be `SHADOW`; `LOCKED`, `PAUSED`, `PAPER`, `RESEARCH`, `LIVE` do not satisfy | Fresh reconciliation and required market/risk/execution/provider-health references; ADR-0010 external-consumer compatibility required | Required |
| `PAPER_RUNTIME` | Simulated execution only; no production private mutation is created by this role | Explicit current PAPER runtime authorization | Exact persisted mode must be `PAPER`; no default/promote from other modes | Current local market/risk/execution/recovery readiness references required by the PAPER plan | Required when an external supervisor controls the runtime |
| `BOUNDED_LIVE_FIRE_RUNTIME` | Only the finite mutation capabilities explicitly enumerated by a future LF-6 Product Owner artifact | Explicit future single-session Product Owner authorization bound to exact revision/config/capabilities | V0.1 creates no new OperationalMode and does not infer recurring `LIVE`; the future LF-6 artifact plus accepted E7 governance must define the exact existing mode representation. If that mapping is not explicitly accepted, preflight fails closed | LF-0..LF-5 accepted evidence plus fresh reconciliation, risk admission, provider health and all session-specific prerequisites | Required |

Credentials being present locally never upgrades the role. An installed provider client, an allowlisted action, a previous role PASS, or a persisted `SHADOW`/`PAPER`/`LIVE` string never creates missing authorization.

## 6. OperationalMode binding

`requested_operational_mode` must be an existing canonical E6 `OperationalMode` value. The preflight consumes, but never creates or reinterprets:

```text
OperationalModeRecord.transition_id
OperationalModeRecord.mode_revision
OperationalModeRecord.mode
OperationalModeRecord.payload_hash
```

The exact current durable record must match all preflight mode fields.

Fail closed when:

- current durable mode is missing/corrupt/unknown;
- requested mode differs from current durable mode;
- mode revision/transition identity/hash differs from current durable truth;
- a caller tries to substitute an environment variable, scheduler default, prior process memory or UI state for E6 durable truth;
- a role-specific mode rule in section 5 is unsatisfied.

A process restart never carries forward prior in-memory mode authority. The new process must re-read and bind current durable E6 mode truth.

## 7. Process identity and heartbeat evidence

`heartbeat_evidence` contains exactly:

- `heartbeat_source_id` — sanitized source identity;
- `heartbeat_policy_generation_id` — immutable policy/config generation that defines heartbeat freshness;
- `heartbeat_policy_hash` — hash of the sanitized policy envelope;
- `heartbeat_process_instance_id` — must equal top-level `process_instance_id`;
- `heartbeat_process_start_generation_id` — must equal top-level `process_start_generation_id`;
- `heartbeat_observed_at` — RFC 3339 UTC source observation time;
- `heartbeat_received_at` — RFC 3339 UTC local receipt time;
- `heartbeat_freshness_status` — `FRESH | STALE | UNKNOWN`.

V0.1 deliberately defines no numeric heartbeat TTL. The threshold belongs to an accepted behavior-affecting runtime/supervisor configuration generation and therefore must be covered by `heartbeat_policy_generation_id` + hash. If the applicable policy generation or freshness classification is unavailable, preflight fails closed.

Heartbeat rules:

```text
heartbeat_process_instance_id == process_instance_id
heartbeat_process_start_generation_id == process_start_generation_id
heartbeat_observed_at >= process_started_at
heartbeat_received_at >= heartbeat_observed_at, subject to the accepted clock/receipt policy
evaluated_at >= heartbeat_received_at
heartbeat_freshness_status == FRESH
single_instance_status == SINGLE
```

A heartbeat from a prior boot, replaced PID/instance, different process start generation, duplicate process set, missing source, stale classification or unknown policy is never authority for the current process.

## 8. Supervisor / watchdog evidence

`supervisor_evidence` contains:

- `supervisor_present` — boolean;
- `supervisor_id` — sanitized stable identity or `null` only when no supervisor participates;
- `supervisor_generation_id` — exact behavior/config generation or `null` only when no supervisor participates;
- `supervisor_config_hash` — sanitized hash or `null` only when no supervisor participates;
- `supervisor_compatibility_status` — `ACCEPTED | NOT_ACCEPTED | UNKNOWN | NOT_APPLICABLE`;
- `restart_permission_status` — `ALLOWED_BY_CURRENT_EVIDENCE | NOT_ALLOWED | UNKNOWN | NOT_APPLICABLE`.

Process liveness and restart permission are separate facts.

A watchdog may not restart a provider-capable runtime solely because a process is dead. For `launch_intent=RESTART`, restart eligibility must be recomputed from current:

- exact revision/worktree evidence;
- durable OperationalMode;
- runtime config generation;
- process/single-instance state;
- current reconciliation evidence;
- current role authorization;
- current capability allowlisting;
- current external-consumer compatibility;
- current E5 risk/kill-switch reference where the runtime role requires it.

The prior process's heartbeat, mode cache, role admission result or provider authorization is not inherited by the new process.

## 9. Local action / capability evidence

`capability_evidence` contains:

- `capability_snapshot_ref`;
- `capability_snapshot_hash`;
- `capability_generation_id`;
- `required_action_ids` — deterministic sorted array of exact canonical action IDs needed by the declared execution/runtime plan;
- `registered_action_ids` — deterministic sorted array visible in the accepted canonical project catalog/generation;
- `allowlisted_action_ids` — deterministic sorted array actually enabled by the external operator/runtime generation;
- `capability_status` — `READY | NOT_READY | UNKNOWN`.

Rules:

- canonical catalog presence alone is not local allowlisting;
- local allowlisting alone is not Product Owner/runtime authority;
- task-specific aliases must not substitute canonical action IDs;
- each `required_action_id` must be present in both the accepted registered and allowlisted sets for the exact capability generation;
- a refused action result is terminal evidence for that request identity and does not become `READY` by retry inference;
- no shell path, executable path, command line, secret, branch, remote or local filesystem path belongs in this shared evidence.

The current LF-0 `PREPARE_EXACT_REVISION` refusal is an example of catalog registration without current local project allowlisting.

## 10. Reconciliation readiness evidence

`reconciliation_evidence` contains:

- `reconciliation_ref`;
- `reconciliation_hash`;
- `reconciliation_generation_id`;
- `reconciliation_observed_at`;
- `reconciliation_status` — `READY | NOT_READY | UNKNOWN`;
- `fresh_reconciliation_required` — boolean.

E6 supplies durable recovery/readiness facts and E4/E5 remain authoritative for the underlying broker/risk interpretation. This profile does not map provider objects or lifecycle events itself.

For any role that can observe, plan against, or mutate provider/exposure state:

```text
reconciliation_status == READY
fresh_reconciliation_required == false
```

must be proven at the applicable runtime boundary. If restart invalidates freshness, preflight remains fail closed until the required fresh reconciliation generation is accepted.

## 11. Referenced market / risk / execution / provider-health evidence

`dependency_evidence` is sorted lexicographically by `(owner, evidence_class, evidence_ref)` and each entry contains:

- `owner` — `E1 | E4 | E5 | E6 | E7 | OPERATOR`;
- `evidence_class` — stable class name declared by the consuming runtime plan;
- `evidence_ref`;
- `evidence_hash`;
- `evidence_generation_id`;
- `observed_at`;
- `readiness_status` — `READY | NOT_READY | UNKNOWN`.

This profile only validates presence, identity, generation, temporal currency and required `READY` classification. It does **not** duplicate:

- E1 market health/freshness semantics;
- E4 execution/provider-health semantics;
- E5 risk/kill-switch/trade-approval semantics;
- E6 persistence/recovery semantics.

If a required owner-authoritative reference is missing, stale, conflicting or `UNKNOWN`, preflight fails closed. A later/newer authoritative dependency observation invalidates older preflight evidence when the role plan declares that dependency current-sensitive.

## 12. External consumer / AgentBridge compatibility evidence

When an external orchestrator, launcher, AgentBridge supervisor or operator-owned runtime materially participates, `external_consumer_evidence` is required and contains:

- `external_consumer_id`;
- `external_consumer_generation_id`;
- `external_consumer_config_hash`;
- `compatibility_profile_ref`;
- `compatibility_evidence_hash`;
- `compatibility_status` — `ACCEPTED | NOT_ACCEPTED | UNKNOWN`;
- `compatibility_observed_at`.

The evidence proves only compatibility of the exact external generation with the declared project runtime interface. It does not grant provider or financial authority.

For any future SHADOW runtime, ADR-0010 consumer migration/review is a required compatibility prerequisite. A historical external generation that uses the deprecated pre-provider risk timestamp call cannot be accepted for a new SHADOW preflight merely because project source is qualified.

E7-105 does not implement or modify AgentBridge.

## 13. Authorization evidence

`authorization_evidence` contains:

- `authorization_class` — `CREDENTIAL_FREE_TASK | PROVIDER_READ_ONLY | SHADOW_RUNTIME | PAPER_RUNTIME | BOUNDED_LIVE_FIRE_RUNTIME`;
- `authorization_ref` — exact current authority artifact/reference;
- `authorization_generation_id`;
- `authorized_project_revision` — exact revision or explicit exact compatible revision scope;
- `authorized_runtime_role` — exact role;
- `authorized_capability_set_hash`;
- `authorization_status` — `VALID | MISSING | MISMATCH | EXPIRED | CONSUMED | UNKNOWN`.

For `CREDENTIAL_FREE_LOCAL_VERIFICATION`, current task/request/action authority may satisfy the authorization class; no provider/capital authority is implied.

For provider read-only, SHADOW, PAPER and bounded-live-fire roles, the exact current governance/authorization artifact required by the applicable LF gate must exist. Where Product Owner authority is required by current governance, PM/E7 evidence cannot substitute for it.

Consumed single-session authority is non-reusable. Historical SHADOW authorizations remain consumed.

## 14. Fail-closed reason vocabulary

`reason_codes` is deterministic, unique and emitted in this fixed order when applicable:

1. `PREFLIGHT_EVIDENCE_IDENTITY_INVALID`
2. `PREFLIGHT_REVISION_MISMATCH`
3. `PREFLIGHT_WORKTREE_NOT_EXACT_CLEAN`
4. `PREFLIGHT_OPERATIONAL_MODE_UNKNOWN`
5. `PREFLIGHT_OPERATIONAL_MODE_MISMATCH`
6. `PREFLIGHT_OPERATIONAL_MODE_GENERATION_CONFLICT`
7. `PREFLIGHT_CONFIG_GENERATION_MISMATCH`
8. `PREFLIGHT_PROCESS_IDENTITY_INVALID`
9. `PREFLIGHT_SINGLE_INSTANCE_CONFLICT`
10. `PREFLIGHT_PROCESS_START_GENERATION_MISMATCH`
11. `PREFLIGHT_HEARTBEAT_POLICY_UNKNOWN`
12. `PREFLIGHT_HEARTBEAT_MISSING`
13. `PREFLIGHT_HEARTBEAT_WRONG_PROCESS`
14. `PREFLIGHT_HEARTBEAT_PRIOR_BOOT`
15. `PREFLIGHT_HEARTBEAT_STALE`
16. `PREFLIGHT_SUPERVISOR_GENERATION_UNRECOGNIZED`
17. `PREFLIGHT_RESTART_NOT_AUTHORIZED`
18. `PREFLIGHT_ACTION_CAPABILITY_MISSING`
19. `PREFLIGHT_ACTION_CAPABILITY_NOT_ALLOWLISTED`
20. `PREFLIGHT_RECONCILIATION_NOT_READY`
21. `PREFLIGHT_DEPENDENCY_EVIDENCE_NOT_READY`
22. `PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED`
23. `PREFLIGHT_RUNTIME_AUTHORITY_UNKNOWN`
24. `PREFLIGHT_RUNTIME_AUTHORITY_CONSUMED`
25. `PREFLIGHT_ROLE_AUTHORITY_EXCEEDED`
26. `PREFLIGHT_ROLE_MODE_POLICY_UNDEFINED`
27. `PREFLIGHT_EVIDENCE_TIME_INVALID`
28. `RUNTIME_PREFLIGHT_ELIGIBLE`

`RUNTIME_PREFLIGHT_ELIGIBLE` is present only when no fail-closed reason exists.

`preflight_status=ELIGIBLE` requires:

```text
reason_codes = [RUNTIME_PREFLIGHT_ELIGIBLE]
```

Any other reason yields `preflight_status=FAIL_CLOSED`.

These reasons are admission diagnostics only. They do not reinterpret E5 risk state, E6 OperationalMode, E4 provider truth, or Product Owner authority.

## 15. Evidence identity and canonical serialization

`runtime_preflight_id` is deterministic over the complete immutable evidence payload except the ID field itself.

Algorithm:

1. remove `runtime_preflight_id`;
2. serialize the remaining object as canonical UTF-8 JSON with lexicographically sorted keys and compact separators;
3. arrays defined as deterministic sets in this profile are already sorted as specified;
4. timestamps are canonical UTC `Z` strings;
5. hashes use `sha256:<lowercase hex>`;
6. compute SHA-256 over the canonical JSON;
7. prefix the lowercase hex digest with:

```text
runtimepreflight_
```

Same exact evidence produces the same ID. Any revision, mode revision, config generation, process/start generation, heartbeat, capability, reconciliation, dependency, consumer, authorization, time or result change produces a different ID.

Same ID with changed payload is corrupt/conflicting evidence and fails closed.

## 16. Temporal ordering rules

All timestamps are UTC evidence boundaries, not substitutes for owner semantics.

Required ordering includes:

```text
process_started_at <= evaluated_at
heartbeat_observed_at >= process_started_at
heartbeat_received_at <= evaluated_at
reconciliation_observed_at <= evaluated_at
external_consumer.compatibility_observed_at <= evaluated_at, when required
all current-sensitive dependency observed_at <= evaluated_at
```

A heartbeat/process-start generation from an earlier boot can never satisfy a later process even if its timestamp appears recent.

If an accepted clock policy permits bounded source/receipt skew, that policy must be bound by configuration/evidence generation; V0.1 invents no new numeric skew or heartbeat tolerance.

For runtime composition that performs provider observation followed by risk interpretation, ADR-0010 ordering remains authoritative. This profile does not collapse strategy time, provider observation time, heartbeat time or risk-decision time into one timestamp.

## 17. Watchdog / restart / kill-switch separation

The following are distinct state planes:

1. **process liveness / heartbeat** — external process-health fact;
2. **supervisor/watchdog restart permission** — operator control decision;
3. **durable OperationalMode** — E6-authoritative mode history;
4. **reconciliation lock/readiness** — current operational/provider truth readiness;
5. **financial kill switch / risk veto** — E5-authoritative financial safety state;
6. **runtime/provider/capital authorization** — governance/Product Owner authority.

No plane may be reconstructed from another.

Examples:

- dead process does not imply restart is safe;
- `SHADOW` mode does not imply SHADOW authorization exists;
- `LOCKED` does not mean the E5 financial kill switch is active;
- a financial kill switch does not rewrite OperationalMode history;
- a fresh heartbeat does not prove reconciliation or provider health;
- valid credentials do not imply provider or LIVE authority.

A restart decision must re-run preflight from current evidence rather than copying a prior `ELIGIBLE` result.

## 18. Future implementation boundary

The smallest safe future implementation is split deliberately.

### 18.1 Project-r7 E7/E6 responsibilities

A future bounded project implementation may:

- define/serialize/validate `RuntimePreflightEvidence`;
- read exact current E6 OperationalMode/recovery facts;
- mechanically validate hashes/references/generations;
- compose owner-provided readiness references;
- return `ELIGIBLE` or `FAIL_CLOSED` without provider access;
- persist sanitized preflight evidence if E6 is assigned that storage work.

It must not become a new risk engine or provider supervisor.

### 18.2 External operator / AgentBridge responsibilities

A future external implementation may:

- establish exact approved-local revision/worktree facts;
- provide process instance/start-generation facts;
- enforce single instance;
- produce heartbeat and supervisor generations;
- expose exact registered/allowlisted canonical local action facts;
- enforce restart admission using current project preflight evidence;
- supply external-consumer compatibility generation evidence.

It must not infer trading policy, E5 approval, OperationalMode, or Product Owner authorization.

### 18.3 PM responsibilities

PM reviews that evidence generations match the release/runtime task and that historical evidence is not rebound. PM may sequence work but cannot grant Product Owner-only authority.

### 18.4 Product Owner responsibilities

Product Owner authority is not required for deterministic contract/source/tests that remain provider-free. It is required where current governance requires provider/private runtime, SHADOW/PAPER runtime, bounded live-fire/capital exposure, Gate D or LIVE authorization.

## 19. Required deterministic credential-free tests for future implementation

Future project/external implementations must define and execute locally, without provider/network/credentials, at minimum:

1. exact revision + exact clean worktree -> accepted when every other field is current;
2. revision mismatch -> `PREFLIGHT_REVISION_MISMATCH`;
3. dirty/unproven worktree -> `PREFLIGHT_WORKTREE_NOT_EXACT_CLEAN`;
4. mode exact match and exact E6 revision/hash -> accepted;
5. mode mismatch -> `PREFLIGHT_OPERATIONAL_MODE_MISMATCH`;
6. mode revision/hash conflict -> `PREFLIGHT_OPERATIONAL_MODE_GENERATION_CONFLICT`;
7. config generation/hash mismatch -> `PREFLIGHT_CONFIG_GENERATION_MISMATCH`;
8. duplicate process -> `PREFLIGHT_SINGLE_INSTANCE_CONFLICT`;
9. heartbeat for different process -> `PREFLIGHT_HEARTBEAT_WRONG_PROCESS`;
10. prior-boot/start-generation heartbeat -> `PREFLIGHT_HEARTBEAT_PRIOR_BOOT`;
11. stale heartbeat under bound policy -> `PREFLIGHT_HEARTBEAT_STALE`;
12. missing heartbeat/policy -> fail closed;
13. supervisor/watchdog generation mismatch -> `PREFLIGHT_SUPERVISOR_GENERATION_UNRECOGNIZED`;
14. required canonical action absent from catalog snapshot -> `PREFLIGHT_ACTION_CAPABILITY_MISSING`;
15. required canonical action registered but not allowlisted -> `PREFLIGHT_ACTION_CAPABILITY_NOT_ALLOWLISTED`;
16. reconciliation not ready/fresh-required -> `PREFLIGHT_RECONCILIATION_NOT_READY`;
17. external-consumer compatibility mismatch -> `PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED`;
18. role authority missing/consumed/mismatched -> fail closed;
19. requested runtime role stronger than exact authority -> `PREFLIGHT_ROLE_AUTHORITY_EXCEEDED`;
20. restart never defaults/promotes to `SHADOW`, `PAPER` or `LIVE` from prior process state;
21. financial kill-switch/risk reference remains semantically independent from OperationalMode/restart state;
22. timestamp/order violation -> `PREFLIGHT_EVIDENCE_TIME_INVALID`;
23. changed canonical evidence under same ID -> `PREFLIGHT_EVIDENCE_IDENTITY_INVALID`;
24. each runtime role PASS is non-transferable to every other runtime role;
25. all deterministic tests assert zero provider requests, zero credential reads and zero mutation/order actions.

Any project executable implementation change requires fresh approved-local credential-free qualification for the exact integrated revision. Operator-only implementation changes require separate operator verification evidence but do not by themselves requalify project source.

## 20. Relationship to bounded-live-fire LF gates

### LF-0 — exact revision infrastructure

This profile consumes LF-0 evidence; it cannot create it. The active `9462b259...` exact-clean blocker remains `BLOCKED`.

### LF-3 — failure injection/recovery

FP-16 tests become mandatory LF-3 scenarios for wrong revision/mode/config/process/heartbeat, restart denial, capability absence and reconciliation-not-ready behavior.

### LF-5 — SHADOW/PAPER readiness

LF-5 must consume an accepted exact-role preflight implementation plus ADR-0010 external-consumer compatibility where applicable. Historical consumed SHADOW authorizations remain non-reusable.

### LF-6 — bounded live-fire

A future bounded-live-fire process must produce fresh `BOUNDED_LIVE_FIRE_RUNTIME` preflight evidence bound to the exact LF-6 Product Owner authorization/config/capability generation. A successful bounded session does not transfer that preflight authority to recurring LIVE.

## 21. Current state at E7-105

```text
FP-16 shared contract/design = DEFINED BY THIS TASK / EXECUTABLE IMPLEMENTATION NOT_STARTED
FP-16 prior audit classification = PARTIAL
LF-0 = BLOCKED / PREPARE_EXACT_REVISION LOCAL ALLOWLIST-INFRASTRUCTURE
FP-03 combined candidate = IMPLEMENTED / UNQUALIFIED
candidate revision = 9462b2594675b2e28388f55a2af189100b7cbdfc
exact clean candidate = NOT_ESTABLISHED
credential-free combined qualification = NOT_RUN / NOT_PASS
provider-facing verification on candidate = NOT_RUN / NOT_INFERRED
SHADOW/PAPER = NOT_AUTHORIZED
10U live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
```

No historical qualification, exact-revision, provider, heartbeat or SHADOW evidence is rebound by this profile.

## 22. Security and authority boundary

This profile stores sanitized classifications, references and hashes only. It never stores or requests real credentials.

`runtime-preflight-v0.1` grants no:

- Local Job execution;
- provider request;
- private API access;
- credential access;
- provider/account mutation;
- order submit/cancel/amend/close;
- SHADOW/PAPER runtime;
- 10 USDT live-fire session;
- capital exposure;
- Gate D;
- recurring LIVE authority.

Unknown or inconsistent preflight evidence means no provider-capable work and no new exposure.