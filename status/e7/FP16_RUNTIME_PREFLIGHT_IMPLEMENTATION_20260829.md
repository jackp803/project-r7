# FP-16 Runtime Preflight Implementation — E7-20260829-112

## Authority / classification

- task: `E7-20260829-112`
- branch: `agent/e7-fp16-runtime-preflight-implementation-20260829`
- branch base main: `70fb2fbaad43773d0c2278de84e8e47f8fc2fdea`
- accepted profile consumed: `contracts/RUNTIME_PREFLIGHT_PROFILE_V0_1.md` / `runtime-preflight-v0.1`
- parent readiness profile: `bounded-live-fire-readiness-v0.1`
- implementation classification: `IMPLEMENTED_UNQUALIFIED`
- executable verification: `NOT_RUN / NOT_PASS`
- LF-0: `BLOCKED / UNCHANGED`

This task materializes only the provider-neutral E7 admission-evidence interpreter defined by the accepted contract. It creates no provider, process, runtime, order, Product Owner, or capital authority.

## Exact E7-owned implementation/test changes

- `src/integration/runtime_preflight.py`
- `tests/integration/test_runtime_preflight.py`
- `tests/safety/test_p0_integrated_fail_closed.py` — migrated E7-111 FP-16 coverage from file absence to evaluator behavior
- `status/e7/FP16_RUNTIME_PREFLIGHT_IMPLEMENTATION_20260829.md`
- `status/e7/P0_INTEGRATED_DETERMINISTIC_SAFETY_MATRIX_20260829.md` — FP-16 classification update only
- `status/e7/P0_CREDENTIAL_FREE_QUALIFICATION_MANIFEST_20260829.md` — future focused command/module update only
- `coordination/E7/STATUS.md`

No E1-E6 production source, E6 OperationalMode semantics/storage, provider adapter/auth/config, AgentBridge/operator infrastructure, Product Owner authorization artifact, risk/leverage/capital threshold, LIVE/release policy, shared contract/ADR, or GitHub Actions/CI file is changed.

## Pure evaluator boundary

`src/integration/runtime_preflight.py` defines:

- `RuntimePreflightInput` — the canonical runtime-preflight facts being interpreted;
- `RuntimePreflightAuthority` — caller-supplied current sanitized authority/currentness facts only;
- `evaluate_runtime_preflight(input, authority)` — pure deterministic `ELIGIBLE | FAIL_CLOSED` interpreter;
- `validate_runtime_preflight_evidence(evidence)` — exact field/schema/profile/canonical-shape/reason/identity validator;
- `stable_runtime_preflight_id(evidence)` — `runtimepreflight_<sha256>` over the complete immutable evidence except the ID field;
- `runtime_preflight_evidence_is_current(...)` — exact recomputation/currentness comparison helper.

The implementation performs no I/O. It has no provider client, network transport, credential reader, process launcher, restart executor, order submit/cancel/amend/close path, or capital action.

`ELIGIBLE` means only that the exact supplied admission facts are internally coherent for the declared role and authority generation. The returned object intentionally contains no mutation/order/process-launch/restart/SHADOW/PAPER/LIVE/capital authorization field.

## Deterministic validation / reason behavior

The evaluator preserves the accepted fixed reason ordering from `runtime-preflight-v0.1` and emits `RUNTIME_PREFLIGHT_ELIGIBLE` only when no fail-closed reason applies.

### Revision / worktree

- full project revision is compared to supplied revision authority;
- revision authority ref/hash must match supplied current authority;
- revision-qualified evaluation requires `EXACT_CLEAN` both in the preflight facts and current authority;
- historical exact-clean evidence for another revision cannot transfer;
- `CLEAN_UNQUALIFIED`, `DIRTY`, `UNKNOWN`, revision mismatch or authority mismatch fail closed.

The module consumes LF-0 facts; it cannot create or prepare an exact revision. Active E7-101/LF-0 infrastructure blocking remains unchanged.

### OperationalMode / config

- accepted existing E6 modes only are recognized;
- requested mode is compared to supplied current E6 mode truth;
- transition ID, mode revision and payload hash are exact-generation bindings;
- runtime config generation/hash are exact current bindings;
- `SHADOW_RUNTIME` requires `SHADOW`;
- `PAPER_RUNTIME` requires `PAPER`;
- `BOUNDED_LIVE_FIRE_RUNTIME` remains fail closed with `PREFLIGHT_ROLE_MODE_POLICY_UNDEFINED` because V0.1 intentionally defines no existing-mode mapping for LF-6;
- the evaluator never creates or changes an OperationalMode.

### Process / heartbeat

- process instance/start-generation facts remain explicit;
- `single_instance_status` must be `SINGLE`;
- heartbeat policy generation/hash must match supplied current policy authority;
- heartbeat process instance and start generation must match the exact process facts;
- stale/unknown heartbeat, wrong process, prior boot, missing evidence or invalid timestamp ordering fail closed;
- no numeric TTL/skew is invented.

### Supervisor / restart

- absent supervisor is represented explicitly as `NOT_APPLICABLE` material;
- present supervisor generation/config must match supplied current authority and compatibility must be `ACCEPTED`;
- `RESTART` requires `ALLOWED_BY_CURRENT_EVIDENCE` on the current supervisor evidence;
- dead/lost process state is never itself restart authority;
- the module never launches or restarts a process.

### Capability / allowlist

- required/registered/allowlisted action arrays are deterministic sorted unique sets;
- capability snapshot ref/hash/generation must match supplied current authority;
- every required canonical action must be registered and separately allowlisted;
- `READY` is required;
- catalog registration alone cannot satisfy allowlisting;
- allowlisting alone cannot satisfy authorization;
- no executable path, shell command, filesystem path or secret is represented.

### Reconciliation / owner dependencies

- provider/exposure-capable roles require exact current reconciliation authority, `READY`, and `fresh_reconciliation_required=false`;
- required owner dependencies are matched by `(owner, evidence_class, evidence_ref)` plus exact hash/generation;
- dependency arrays are deterministic and each supplied required dependency must be `READY` and temporally valid;
- E1/E4/E5/E6 domain semantics are not duplicated; only supplied readiness classifications/references are interpreted.

### External consumer

- SHADOW and bounded-live-fire roles retain mandatory external-consumer compatibility;
- conditional external participation is also fail closed when supplied supervisor/external authority demonstrates participation;
- present consumer evidence must match exact supplied generation/config/profile/evidence hashes and be `ACCEPTED`;
- compatibility timestamps cannot postdate the preflight evaluation;
- AgentBridge/operator code is not read or modified by the evaluator.

### Authorization / role isolation

Exact role-to-authorization classes are preserved:

- `CREDENTIAL_FREE_LOCAL_VERIFICATION -> CREDENTIAL_FREE_TASK`
- `PROVIDER_READ_ONLY_OBSERVATION -> PROVIDER_READ_ONLY`
- `SHADOW_RUNTIME -> SHADOW_RUNTIME`
- `PAPER_RUNTIME -> PAPER_RUNTIME`
- `BOUNDED_LIVE_FIRE_RUNTIME -> BOUNDED_LIVE_FIRE_RUNTIME`

Only exact current `VALID` authorization facts may contribute to `ELIGIBLE`. Missing/mismatched/expired/unknown authority fails closed; consumed authority emits the distinct consumed reason. Role, revision and authorized capability-set hash must match the evaluated facts. Evidence for one runtime role is non-transferable to another.

Synthetic provider-role fixtures in tests are data only. They do not alter repository authorization state and do not constitute Product Owner authority.

## E7-111 safety migration

The accepted E7-111 safety baseline asserted that `src/integration/runtime_preflight.py` was absent while FP-16 was `CONTRACT_ONLY`.

E7-112 replaces that stale absence assertion with behavior coverage:

- coherent credential-free synthetic evidence can evaluate `ELIGIBLE` only as admission evidence;
- role substitution fails closed;
- no returned provider/order/process/runtime/capital authority is created;
- pure evaluator takes only supplied `value` + `authority` inputs.

FP-16 therefore becomes:

```text
IMPLEMENTED_UNQUALIFIED / NOT_RUN / NOT_PASS
```

not executable PASS.

## Deterministic test definitions

`tests/integration/test_runtime_preflight.py` defines credential-free cases for:

- coherent credential-free `ELIGIBLE` evidence with no authority side effects;
- deterministic same-input identity/currentness;
- role substitution/non-transferability;
- revision and `EXACT_CLEAN` binding;
- OperationalMode value/generation mismatch;
- runtime config generation mismatch;
- single-instance conflict/unknown;
- heartbeat stale/unknown/wrong-process/prior-boot/time/policy mismatch;
- supervisor incompatibility/unknown and restart permission;
- registered-vs-allowlisted action separation and capability readiness;
- reconciliation readiness/freshness;
- required dependency missing/not-ready/unknown;
- external-consumer missing/incompatible for SHADOW;
- authorization missing/mismatch/expired/consumed/unknown and exact role/revision/capability binding;
- bounded-live-fire mode-policy undefined;
- corrupt immutable evidence identity;
- synthetic provider-role fixture non-authority.

No test is executed in E7-112 because the task and local-only policy prohibit project execution here and LF-0 remains blocked.

## Exact future approved-local commands

After this candidate is merged, PM binds the exact merged revision, approved-local infrastructure establishes that exact revision as `EXACT_CLEAN`, and a fresh execution task authorizes qualification, run from the approved Windows repository root:

```powershell
$env:PYTHONPATH = 'src'
python -m unittest discover -s tests/integration -p 'test_runtime_preflight.py' -v
python -m unittest discover -s tests/safety -p 'test_p0_integrated_fail_closed.py' -v
```

Then run the focused P0 sequence and complete 14-suite credential-free matrix recorded in `status/e7/P0_CREDENTIAL_FREE_QUALIFICATION_MANIFEST_20260829.md` on that same exact clean revision.

Required future evidence must record actual test counts/results, exact revision, approved local OS/Python, clean/exact-clean fact, and zero provider/private/credential/mutation/process-launch/order/runtime/capital/GitHub-compute classifications.

## Current verification / release state

```text
project executable verification = NOT_RUN / NOT_PASS
FP-16 runtime-preflight tests = NOT_RUN / NOT_PASS
LF-0 = BLOCKED / UNCHANGED
LF-1 = NOT_RUN / NOT_PASS
LF-2 = PARTIAL / NOT PASS
provider requests = 0
private API = NONE
credentials = NONE
provider/account mutation = 0
process launch/restart = 0
order/protection actions = 0
SHADOW/PAPER = NOT_AUTHORIZED
10U bounded live-fire = NOT_AUTHORIZED
Gate D / LIVE = BLOCKED / UNAUTHORIZED
capital exposure = NONE
GitHub Actions/CI/hosted/GitHub-triggered compute = NOT_USED
```

`NOT_RUN` is not PASS. Merge/static review cannot change that classification.

## Limitations / next dependency

- exact merged E7-112 candidate revision is not yet the approved-local exact-clean qualification revision;
- active LF-0 exact-revision preparation infrastructure remains blocked;
- FP-02 provider-native close/protection facts remain unresolved/fail-closed;
- external AgentBridge/operator runtime-preflight production facts/launcher enforcement are outside this task;
- provider read-only requires future Product Owner authority;
- SHADOW/PAPER remain unauthorized;
- bounded 10U live-fire remains unauthorized;
- Gate D / recurring LIVE remain blocked/unauthorized.
