# Project Blockers

## SHADOW_TEMPORAL_REQUALIFICATION_PREPARE_ACTION_NOT_ALLOWLISTED — 2026-08-26 — RESOLVED

```text
state = RESOLVED / EXACT CLEAN LOCAL WORKTREE PREPARED / REQUALIFICATION COMPLETED
blocked_task = E7-20260826-093 / BLOCKED / HISTORICAL
candidate_revision = 8fbf5fcae2eaf44accdf535121d8abf29ef5c93c
historical_preparation_job = JOB-5CF665C8F9DD49B8 / REFUSED
resolution_action = PREPARE_EXACT_REVISION
resolution_job = JOB-852ABEE9A8CC
approved_local_worktree = 8fbf5fcae2eaf44accdf535121d8abf29ef5c93c / EXACT_CLEAN
credential_free_requalification = E7-20260827-095 / PASS
qualification_job = JOB-3296319DD36E588C / SUCCEEDED / exit 0
qualification_matrix = 14/14 suites PASS / 589 tests
candidate_qualification = CREDENTIAL_FREE_REQUALIFIED / PM ACCEPTED
provider_requests = 0
credentials = NONE
mutation_requests = 0
submit_requests = 0
SHADOW_runtime = NOT_STARTED
PAPER_runtime = NOT_STARTED
capital_exposure = NONE
GitHub_compute = NOT_USED
resolved_at = 2026-08-27T09:35:00+08:00
```

The earlier preparation refusal remains historical fail-closed evidence. The exact candidate was later prepared cleanly by approved-local AgentBridge job `JOB-852ABEE9A8CC`, and E7-095 then executed the canonical credential-free requalification on that exact revision. PM accepted the resulting 14/14-suite, 589-test local PASS through `status/PM_E7_095_REVIEW_20260827.md`.

No provider verification, credential operation, SHADOW/PAPER runtime, provider/account mutation, order action, capital exposure, Gate D, LIVE, or GitHub compute occurred as part of this resolution.

## ZERO_CAPITAL_SHADOW_THIRD_SESSION_REQUIRES_PRODUCT_OWNER_AUTHORITY — 2026-08-26 — ACTIVE

```text
state = ACTIVE / FAIL-CLOSED / PRODUCT OWNER + EXTERNAL CONSUMER DEPENDENCIES
latest_provider_session = E7-20260826-090 / PARTIAL / FAIL_CLOSED
first_session_authorization = CONSUMED / NO RETRY
replacement_authorization = PO-ZERO-CAPITAL-SHADOW-REAUTH-20260826-01 / CONSUMED / NO RETRY
successful_SHADOW_runtime_evidence = NOT ESTABLISHED
historical_provider-qualified_project_revision = ab725965e96cac7a9769fd1ab15a3e626f920b95
temporal_remediation_revision = 8fbf5fcae2eaf44accdf535121d8abf29ef5c93c
credential_free_requalification = E7-20260827-095 / PASS / PM ACCEPTED / 589 TESTS
provider_verification_on_temporal_remediation_revision = NOT_RUN / NOT_INFERRED
AgentBridge_ADR0010_consumer_migration = REQUIRED / NOT YET ACCEPTED
third_SHADOW_Product_Owner_authority = REQUIRED / NOT GRANTED
PAPER = NOT AUTHORIZED
Gate_D = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
capital_exposure = NONE
```

PM accepts the new project revision only for its completed credential-free qualification. Historical provider-read-only and bounded-SHADOW evidence generated against `ab725965e96cac7a9769fd1ab15a3e626f920b95` must not be rebound, copied, or inferred as provider evidence for `8fbf5fcae2eaf44accdf535121d8abf29ef5c93c`.

Before any future provider SHADOW session, all of the following must be satisfied independently:

1. AgentBridge must migrate/review the SHADOW consumer against ADR-0010 and bind the separated `strategy_evaluation_time` / post-provider `risk_time_provider` semantics to the accepted project revision;
2. any provider-facing verification required for the replacement revision must receive its own authority and evidence and may not be inferred from credential-free PASS;
3. a third/replacement SHADOW runtime requires a new explicit Product Owner authorization with its own bounded runtime/safety limits and a fresh PM task/request ID.

Until then, no Local Job Request for provider observation/session runtime may be issued. No recurring SHADOW, PAPER, provider/account mutation, order submission, capital movement/exposure, Gate D, or LIVE is authorized.

## ZERO_CAPITAL_SHADOW_SESSION_REAUTHORIZATION_REQUIRED — 2026-08-26 — RESOLVED

```text
state = RESOLVED / REPLACEMENT AUTHORITY WAS RECORDED AND CONSUMED
execution_task = E7-20260826-088 / PARTIAL / FAIL_CLOSED
session_authorization = CONSUMED / NO RETRY
replacement_authorization = PO-ZERO-CAPITAL-SHADOW-REAUTH-20260826-01 / CONSUMED BY E7-090
successful_SHADOW_runtime_evidence = NOT ESTABLISHED
PAPER = NOT AUTHORIZED
Gate_D = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
```

This blocker was resolved when the Product Owner explicitly authorized one replacement session. That replacement was subsequently consumed by E7-090 and terminated fail closed. It remains preserved as historical authority/evidence only.

## ZERO_CAPITAL_SHADOW_LOCAL_ACTION_NOT_REGISTERED — 2026-08-26 — RESOLVED

```text
state = RESOLVED / OPERATOR REGISTRATION ACCEPTED BY PM
registered_matching_session_action = GATE_C_ZERO_CAPITAL_SHADOW_SESSION
execution_dependency = SATISFIED FOR HISTORICAL REGISTERED GENERATION
```

The canonical SHADOW action remains a registered capability, but capability registration is not authorization for another session and its historical revision binding must not be reused for the remediated project revision without operator reconciliation.

## NEXT_PHASE_REQUIRES_PRODUCT_OWNER_AUTHORITY — 2026-08-26 — RESOLVED

```text
state = RESOLVED / SUPERSEDED BY PRIOR BOUNDED PRODUCT OWNER AUTHORIZATIONS
PAPER_runtime = NOT STARTED
Gate_D = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
capital_exposure = NONE
```

Earlier bounded SHADOW authority was granted and consumed. All broader runtime remains unauthorized: PAPER, recurring/continuous SHADOW, provider/account mutation, order submission, capital movement/exposure, Gate D and LIVE require separate explicit Product Owner authority.
