# FP-16 Runtime Preflight Contract Handoff — 2026-08-29

## Scope

- task_id: `E7-20260829-105`
- profile: `runtime-preflight-v0.1`
- contract: `contracts/RUNTIME_PREFLIGHT_PROFILE_V0_1.md`
- task type: `CONTRACT / DOCS / STATUS ONLY`
- executable implementation: `NOT_STARTED`
- project executable verification: `NOT_RUN / NOT REQUIRED FOR CONTRACT-DOCS TASK`
- Local Job Request: `NONE`
- provider/private API: `NONE`
- credentials: `NONE`
- mutation/order actions: `0`
- SHADOW/PAPER: `NOT_STARTED / NOT_AUTHORIZED`
- bounded 10U live-fire: `NOT_AUTHORIZED`
- capital exposure: `NONE`
- Gate D / LIVE: `BLOCKED / UNAUTHORIZED`
- GitHub compute: `NOT_USED`

This handoff defines the shared FP-16 design only. `NOT_RUN` is not executable PASS.

## Profile decision

`runtime-preflight-v0.1` is an additive shared evidence profile under existing `contracts-v0.1` and `bounded-live-fire-readiness-v0.1` governance.

No existing object profile or OperationalMode semantic is amended. No new OperationalMode is introduced. No new ADR is required because the accepted architecture already separates:

```text
E6 durable mode/recovery truth
E4 provider/execution truth
E5 financial risk veto/kill-switch truth
E7 integration/release evidence
external operator process/supervisor/action-allowlist truth
Product Owner provider/runtime/capital authority
```

The missing FP-16 element was one deterministic admission evidence schema tying those existing authorities to the same exact process/revision/config/heartbeat generation.

## Canonical evidence schema

The profile defines immutable `RuntimePreflightEvidence` with exact bindings for:

1. full project revision and exact-revision authority reference/hash;
2. exact-clean worktree classification where revision-qualified execution is required;
3. requested durable `OperationalMode`, transition ID, mode revision and payload hash;
4. behavior-affecting runtime config generation and hash;
5. exact process instance identity;
6. exact process start/boot generation;
7. heartbeat source/policy/process/start-generation/timestamps/freshness;
8. supervisor/watchdog identity/config generation and restart-permission classification;
9. required/registered/allowlisted canonical local action capability sets;
10. reconciliation readiness generation;
11. owner-authoritative market/risk/execution/provider-health dependency references without semantic duplication;
12. external-consumer/AgentBridge compatibility generation where materially involved;
13. exact runtime-role authorization generation;
14. post-source evaluation timestamp/order;
15. deterministic `runtimepreflight_<sha256>` identity.

Top-level result:

```text
preflight_status = ELIGIBLE | FAIL_CLOSED
```

`ELIGIBLE` is admission evidence only. It never creates provider, runtime, mutation, capital, Gate D or LIVE authority.

## Runtime-role matrix

| Role | Transferable from another role? | Provider/mutation class | Minimum authority boundary | Key additional requirement |
|---|---|---|---|---|
| `CREDENTIAL_FREE_LOCAL_VERIFICATION` | NO | none | exact task/request/action authority | exact revision/worktree + external runner compatibility when used |
| `PROVIDER_READ_ONLY_OBSERVATION` | NO | read-only / zero mutation | separate current read-only authorization under LF-4 governance | secure local credentials + exact read-only capability generation |
| `SHADOW_RUNTIME` | NO | provider observation/read-only | explicit fresh SHADOW runtime authority | persisted mode `SHADOW`, fresh reconciliation, ADR-0010 external consumer accepted |
| `PAPER_RUNTIME` | NO | simulated execution only | explicit fresh PAPER runtime authority | persisted mode `PAPER` + local lifecycle/recovery dependencies |
| `BOUNDED_LIVE_FIRE_RUNTIME` | NO | only finite LF-6 enumerated mutation capabilities | future exact Product Owner single-session authorization | LF-0..LF-5 accepted, exact mode representation explicitly governed, all session bounds exact |

Credentials on disk, a prior role PASS, a registered action, or a persisted mode value cannot upgrade role authority.

## Fail-closed reason vocabulary

Stable reasons are defined in contract order:

```text
PREFLIGHT_EVIDENCE_IDENTITY_INVALID
PREFLIGHT_REVISION_MISMATCH
PREFLIGHT_WORKTREE_NOT_EXACT_CLEAN
PREFLIGHT_OPERATIONAL_MODE_UNKNOWN
PREFLIGHT_OPERATIONAL_MODE_MISMATCH
PREFLIGHT_OPERATIONAL_MODE_GENERATION_CONFLICT
PREFLIGHT_CONFIG_GENERATION_MISMATCH
PREFLIGHT_PROCESS_IDENTITY_INVALID
PREFLIGHT_SINGLE_INSTANCE_CONFLICT
PREFLIGHT_PROCESS_START_GENERATION_MISMATCH
PREFLIGHT_HEARTBEAT_POLICY_UNKNOWN
PREFLIGHT_HEARTBEAT_MISSING
PREFLIGHT_HEARTBEAT_WRONG_PROCESS
PREFLIGHT_HEARTBEAT_PRIOR_BOOT
PREFLIGHT_HEARTBEAT_STALE
PREFLIGHT_SUPERVISOR_GENERATION_UNRECOGNIZED
PREFLIGHT_RESTART_NOT_AUTHORIZED
PREFLIGHT_ACTION_CAPABILITY_MISSING
PREFLIGHT_ACTION_CAPABILITY_NOT_ALLOWLISTED
PREFLIGHT_RECONCILIATION_NOT_READY
PREFLIGHT_DEPENDENCY_EVIDENCE_NOT_READY
PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED
PREFLIGHT_RUNTIME_AUTHORITY_UNKNOWN
PREFLIGHT_RUNTIME_AUTHORITY_CONSUMED
PREFLIGHT_ROLE_AUTHORITY_EXCEEDED
PREFLIGHT_ROLE_MODE_POLICY_UNDEFINED
PREFLIGHT_EVIDENCE_TIME_INVALID
RUNTIME_PREFLIGHT_ELIGIBLE
```

`RUNTIME_PREFLIGHT_ELIGIBLE` is the only reason on an `ELIGIBLE` result. Every other listed condition is fail closed.

## Heartbeat and process-generation boundary

No numeric heartbeat TTL is invented by E7-105.

Heartbeat freshness belongs to an accepted behavior-affecting policy/config generation. Preflight binds:

```text
heartbeat_policy_generation_id
heartbeat_policy_hash
heartbeat_freshness_status = FRESH | STALE | UNKNOWN
```

A missing policy, missing heartbeat, stale heartbeat, prior-boot heartbeat, wrong process identity or wrong start generation is fail closed.

The process start generation prevents an apparently recent heartbeat from a prior process/boot from qualifying the new process.

## Watchdog / restart boundary

These are explicitly separate:

```text
process liveness / heartbeat
supervisor restart permission
E6 OperationalMode
reconciliation readiness/lock
E5 financial kill switch/risk veto
provider/runtime/capital authorization
```

A watchdog cannot restart provider-capable work merely because the process died. `RESTART` must recompute the entire preflight against current durable mode, current config, current exact revision, current reconciliation, current action allowlisting, current external-consumer compatibility and current authorization.

No prior process `ELIGIBLE` result is inherited.

## Canonical local-action boundary

The profile distinguishes:

```text
catalog registration != local allowlisting
local allowlisting != runtime/Product Owner authority
```

The active LF-0 blocker demonstrates this distinction: `PREPARE_EXACT_REVISION` exists in the canonical project catalog but the E7-101 approved-local request was refused because the process action was not locally allowlisted for the project.

A future preflight must bind exact `required_action_ids`, `registered_action_ids` and `allowlisted_action_ids` for one capability generation.

## Ownership split

### E7 / project-r7

Owns:

- `runtime-preflight-v0.1` schema/version;
- deterministic identity/reason/role compatibility rules;
- cross-module admission composition;
- integration/safety tests if project code materializes the validator/composer;
- release interpretation and exact-revision evidence non-transferability.

E7 does not become the process supervisor or risk engine.

### E6

Supplies/owns:

- durable OperationalMode current record/revision/hash;
- recovery/fresh-reconciliation readiness state;
- future persistence/display of sanitized preflight evidence only if separately assigned.

E6 does not infer risk, provider health or Product Owner authority.

### External operator / AgentBridge

Supplies/owns:

- approved-local exact worktree/revision facts;
- process instance/start generation;
- single-instance enforcement;
- heartbeat policy and heartbeat generation;
- supervisor/watchdog generation;
- registered/allowlisted local action facts;
- external-consumer compatibility generation;
- restart enforcement using current project admission evidence.

The external operator must not infer E5 trading policy, E6 mode, or Product Owner authority.

### E4 / E5

E4 continues to own provider/execution/reconciliation facts; E5 continues to own financial risk veto/kill-switch and trade/lifecycle policy. Preflight consumes only exact readiness references and does not duplicate those semantics.

### PM

PM reviews revision/config/evidence generations, sequences implementation/qualification, and rejects historical evidence rebinding. PM cannot grant Product Owner-only runtime/capital authority.

### Product Owner

No Product Owner authority is required for deterministic provider-free implementation/tests. Current governance requires explicit Product Owner authority for provider/private stages, SHADOW/PAPER/runtime stages where specified, bounded live-fire/capital, Gate D or LIVE.

## Future deterministic implementation boundary

The smallest safe future implementation can be split into two coordinated tasks.

### Project-r7 bounded implementation

Possible E7/E6-owned executable scope:

- shared data model/validator/composer for `RuntimePreflightEvidence`;
- exact E6 OperationalMode/recovery binding;
- deterministic hash/reference/generation validation;
- role matrix and reason-code fail-closed evaluation;
- no provider/network/credential operations.

Any project executable change requires fresh approved-local credential-free qualification on the exact integrated revision.

### External operator / AgentBridge implementation

External scope:

- process/start generation and single-instance facts;
- heartbeat/supervisor/config generations;
- canonical action registered+allowlisted snapshot;
- state-aware restart admission;
- AgentBridge ADR-0010 consumer compatibility evidence for future SHADOW.

Operator-only changes require their own operator verification evidence but do not automatically change/qualify project source.

## Required deterministic test matrix

Future tests must include at minimum:

| Scenario | Expected result |
|---|---|
| exact revision + exact-clean + all current facts | eligible for the declared role only |
| wrong revision | `PREFLIGHT_REVISION_MISMATCH` |
| dirty/unproven exact worktree | `PREFLIGHT_WORKTREE_NOT_EXACT_CLEAN` |
| mode mismatch | `PREFLIGHT_OPERATIONAL_MODE_MISMATCH` |
| mode revision/hash conflict | `PREFLIGHT_OPERATIONAL_MODE_GENERATION_CONFLICT` |
| runtime config generation mismatch | `PREFLIGHT_CONFIG_GENERATION_MISMATCH` |
| duplicate process | `PREFLIGHT_SINGLE_INSTANCE_CONFLICT` |
| heartbeat wrong process | `PREFLIGHT_HEARTBEAT_WRONG_PROCESS` |
| prior-boot heartbeat | `PREFLIGHT_HEARTBEAT_PRIOR_BOOT` |
| stale/missing heartbeat | fail closed with stable heartbeat reason |
| unrecognized supervisor generation | `PREFLIGHT_SUPERVISOR_GENERATION_UNRECOGNIZED` |
| required action absent from catalog | `PREFLIGHT_ACTION_CAPABILITY_MISSING` |
| canonical action registered but not locally allowlisted | `PREFLIGHT_ACTION_CAPABILITY_NOT_ALLOWLISTED` |
| reconciliation not ready / fresh reconciliation still required | `PREFLIGHT_RECONCILIATION_NOT_READY` |
| external consumer compatibility mismatch | `PREFLIGHT_EXTERNAL_CONSUMER_NOT_ACCEPTED` |
| authorization missing/consumed/mismatched | fail closed |
| requested role stronger than available authority | `PREFLIGHT_ROLE_AUTHORITY_EXCEEDED` |
| restart after prior SHADOW/PAPER/LIVE process | cannot default/promote to prior mode or authority |
| kill switch vs OperationalMode | remain separately represented and independently authoritative |
| invalid timestamp ordering | `PREFLIGHT_EVIDENCE_TIME_INVALID` |
| same evidence ID with changed payload | `PREFLIGHT_EVIDENCE_IDENTITY_INVALID` |
| role PASS reused for a different role | rejected |

Every deterministic test must require:

```text
provider requests = 0
credentials = NONE
mutation/order actions = 0
capital exposure = NONE
```

## Relationship to readiness gates

### LF-0

FP-16 does not solve exact-revision infrastructure. Current LF-0 remains:

```text
candidate = 9462b2594675b2e28388f55a2af189100b7cbdfc
exact clean candidate = NOT_ESTABLISHED
PREPARE_EXACT_REVISION = LOCAL ALLOWLIST/INFRASTRUCTURE BLOCKED
```

### LF-3

Future FP-16 implementation/tests are part of failure-injection/recovery evidence: wrong process/revision/mode/config, stale heartbeat, missing capabilities and restart denial all need approved-local deterministic PASS.

### LF-5

Future SHADOW/PAPER readiness requires role-specific preflight plus current OperationalMode/reconciliation evidence. SHADOW additionally requires accepted ADR-0010 external-consumer migration/review. Historical consumed SHADOW authorizations remain non-reusable.

### LF-6

Future bounded live-fire requires fresh `BOUNDED_LIVE_FIRE_RUNTIME` preflight tied to the exact LF-6 Product Owner authorization, exact revision/config/action capabilities and finite session limits. It does not imply recurring LIVE.

## Current unresolved dependencies

```text
LF-0 exact candidate infrastructure = BLOCKED
candidate revision = 9462b2594675b2e28388f55a2af189100b7cbdfc
FP-03 combined qualification = NOT_RUN / NOT_PASS
FP-16 executable project implementation = NOT_STARTED
FP-16 external operator/AgentBridge implementation = NOT_STARTED
ADR-0010 AgentBridge consumer migration/review = REQUIRED BEFORE FUTURE SHADOW
provider-facing verification on candidate = NOT_RUN / NOT_INFERRED
SHADOW/PAPER = NOT_AUTHORIZED
10U live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
```

## Recommended next Worker tasks

These are recommendations only; E7-105 does not issue or execute them.

1. **E7/E6 project preflight implementation task** — materialize the provider-free profile validator/composer and local deterministic tests, while keeping external process-supervision details abstracted behind sanitized evidence.
2. **External operator/AgentBridge FP-16 task** — implement process/start generation, heartbeat policy/evidence, single-instance and state-aware restart admission, plus exact action allowlist snapshot and external-consumer compatibility evidence.
3. **After LF-0 is restored and bounded P0 executable work is intentionally integrated:** one fresh complete credential-free qualification on the exact integrated candidate rather than reusing historical PASS.

FP-04/05/10/11 remain separate dependencies and are not started by this task.

## ADR decision

```text
new ADR = NO / NOT REQUIRED
```

Reason: V0.1 makes an existing accepted authority separation explicit; it does not introduce a new architecture direction, state machine or authority transfer.

## Completion boundary

E7-105 completes contract/design definition only. It does not modify executable source/tests, AgentBridge, local action catalog, provider configuration, credentials, Product Owner authorization artifacts, risk thresholds, leverage/capital limits or release criteria. It does not resolve LF-0 or make FP-16 executable-qualified.