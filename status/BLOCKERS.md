# Project Blockers

## SHADOW_TEMPORAL_REQUALIFICATION_PREPARE_ACTION_NOT_ALLOWLISTED — 2026-08-26 — ACTIVE

```text
state = ACTIVE / EXTERNAL OPERATOR DEPENDENCY / FAIL-CLOSED
blocked_task = E7-20260826-093 / BLOCKED
candidate_revision = 8fbf5fcae2eaf44accdf535121d8abf29ef5c93c
preparation_action = PREPARE_EXACT_REVISION
preparation_request = REQ-E7-PREPARE-093-01-8D31B5C4
preparation_job = JOB-5CF665C8F9DD49B8 / REFUSED / 0.000s
reason = LOCAL PREPARATION ACTION NOT ALLOWLISTED FOR PROJECT
qualification_action = GATE_C_CREDENTIAL_FREE_REQUALIFICATION
qualification_request = NOT CREATED
qualification_execution = NOT_RUN / NOT_PASS
candidate_qualification = NOT_QUALIFIED
provider_requests = 0
credentials = NONE
mutation_requests = 0
submit_requests = 0
SHADOW_runtime = NOT_STARTED
PAPER_runtime = NOT_STARTED
capital_exposure = NONE
GitHub_compute = NOT_USED
worker_dispatch = E7 HOLD
idle_watchdog_fingerprint = 4E851ED697246EF5
last_revalidated_at = 2026-08-26T23:59:00+08:00
```

PM reviewed E7-093 and accepted it only as terminal infrastructure-blocked evidence. `PREPARE_EXACT_REVISION` is named in the repository canonical action catalog, but the approved local AgentBridge refused the action before any project execution because it is not locally allowlisted for `project-r7`. No credential-free qualification suite ran; `NOT_RUN` is not PASS and the candidate remains unqualified.

Idle-watchdog revalidation for fingerprint `4E851ED697246EF5` found no newer authoritative operator registration/allowlisting evidence and no authoritative evidence that a clean approved-local active worktree at exact revision `8fbf5fcae2eaf44accdf535121d8abf29ef5c93c` has already been prepared. The blocker therefore remains fail-closed and no ACTIVE Worker task is justified.

Unblock condition: the local operator must register/allowlist the governed `PREPARE_EXACT_REVISION` capability for `project-r7`, or provide authoritative approved-local evidence that a clean active worktree at exact revision `8fbf5fcae2eaf44accdf535121d8abf29ef5c93c` has already been prepared. After that dependency is satisfied, PM may issue a fresh E7 credential-free requalification task with new request IDs. Do not substitute another revision, GitHub/cloud/container execution, or an invented action alias.

This blocker grants no provider, credential, SHADOW/PAPER, third-session, mutation, order, capital, Gate D or LIVE authority. Both prior SHADOW session authorizations remain consumed.

## ZERO_CAPITAL_SHADOW_THIRD_SESSION_REQUIRES_PRODUCT_OWNER_AUTHORITY — 2026-08-26 — ACTIVE

```text
state = ACTIVE / THIRD SESSION PRODUCT OWNER DECISION REQUIRED / TECHNICAL REQUALIFICATION BLOCKED
latest_execution_task = E7-20260826-090 / PARTIAL / FAIL_CLOSED
latest_local_job_id = JOB-79100A97B3B2AC08
terminal_stop_reason = UNSAFE_PROVIDER_OR_RECONCILIATION_STATE
first_session_authorization = CONSUMED / NO RETRY
replacement_authorization = PO-ZERO-CAPITAL-SHADOW-REAUTH-20260826-01 / CONSUMED / NO RETRY
HTTPS_GET_COUNT = 9
MUTATION_REQUEST_COUNT = 0
SUBMIT_REQUEST_COUNT = 0
available_balance_is_zero = YES
capital_exposure = NONE
operational_mode = LOCKED
complete_safe_shadow_cycles = 0
successful_SHADOW_runtime_evidence = NOT ESTABLISHED
technical_remediation = E7-20260826-092 / SOURCE ACCEPTED AS UNQUALIFIED CANDIDATE
candidate_main_revision = 8fbf5fcae2eaf44accdf535121d8abf29ef5c93c
credential_free_requalification = E7-20260826-093 / BLOCKED / NOT_RUN
worker_dispatch = E7 HOLD / NO PROVIDER OR CREDENTIAL AUTHORITY
PAPER = NOT AUTHORIZED
Gate_D = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
```

PM accepted E7-090 only as terminal fail-closed evidence. The replacement session preserved the hard safety invariants but established no complete safe SHADOW cycle.

Both Product Owner session allowances are consumed. The original E7-088 authorization and replacement authorization `PO-ZERO-CAPITAL-SHADOW-REAUTH-20260826-01` remain append-only historical evidence and must not be reset, deleted, renamed, overwritten, or reused.

E7-092 confirmed and remediated the E7 integration temporal-ordering defect without weakening E5 semantics: deterministic strategy evaluation remains caller-bound, E4 provider observation occurs afterward, and E7 obtains the risk-decision timestamp only after E4 observation. The source/test/ADR remediation was accepted through PR #99 only as an **unqualified executable candidate**. `NOT_RUN` was not treated as PASS.

E7-093 attempted only governed exact-revision local preparation for credential-free requalification. The preparation action was refused before project execution, so no qualification request was created and every qualification suite remains `NOT_RUN / NOT_PASS`. The candidate remains unqualified.

Unblock condition for **runtime execution** remains unchanged: any third or replacement zero-capital SHADOW session requires a new explicit Product Owner authorization defining its own bounded runtime/safety limits, and before such a session the AgentBridge consumer must be migrated/reviewed against ADR-0010 and the replacement project executable revision must be successfully requalified and accepted.

## ZERO_CAPITAL_SHADOW_SESSION_REAUTHORIZATION_REQUIRED — 2026-08-26 — RESOLVED

```text
state = RESOLVED / REPLACEMENT AUTHORITY WAS RECORDED AND CONSUMED
execution_task = E7-20260826-088 / PARTIAL / FAIL_CLOSED
session_authorization = CONSUMED / NO RETRY
replacement_authorization = PO-ZERO-CAPITAL-SHADOW-REAUTH-20260826-01 / CONSUMED BY E7-090
operator_root_cause = REPAIRED
successful_SHADOW_runtime_evidence = NOT ESTABLISHED
Gate_C = PASS / UNCHANGED FOR PRIOR QUALIFIED REVISION
PAPER = NOT AUTHORIZED
Gate_D = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
```

This blocker was resolved when the Product Owner explicitly authorized one replacement session. That replacement was subsequently consumed by E7-090 and terminated fail closed. It remains preserved as historical authority/evidence only.

## ZERO_CAPITAL_SHADOW_LOCAL_ACTION_NOT_REGISTERED — 2026-08-26 — RESOLVED

```text
state = RESOLVED / OPERATOR REGISTRATION ACCEPTED BY PM
current_release_gate = Gate C — SHADOW_READY = PASS
prior_qualified_gate_c_revision = ab725965e96cac7a9769fd1ab15a3e626f920b95
registered_matching_session_action = GATE_C_ZERO_CAPITAL_SHADOW_SESSION
execution_dependency = SATISFIED
```

The canonical SHADOW action remains registered, but capability registration is not authorization for another session.

## NEXT_PHASE_REQUIRES_PRODUCT_OWNER_AUTHORITY — 2026-08-26 — RESOLVED

```text
state = RESOLVED / SUPERSEDED BY PRIOR BOUNDED PRODUCT OWNER AUTHORIZATIONS
current_release_gate = Gate C — SHADOW_READY = PASS
prior_qualified_revision = ab725965e96cac7a9769fd1ab15a3e626f920b95
PAPER_runtime = NOT STARTED
Gate_D = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
capital_exposure = NONE
```

Earlier bounded SHADOW authority was granted and consumed. All broader runtime remains unauthorized: PAPER, recurring/continuous SHADOW, provider/account mutation, order submission, capital movement/exposure, Gate D and LIVE require separate explicit Product Owner authority.