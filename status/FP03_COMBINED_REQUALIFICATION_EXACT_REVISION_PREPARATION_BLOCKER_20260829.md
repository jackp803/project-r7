# FP-03 Combined Requalification Exact-Revision Preparation Blocker

```text
state = ACTIVE / FAIL-CLOSED / EXTERNAL APPROVED-LOCAL INFRASTRUCTURE DEPENDENCY
blocked_task = E7-20260829-101 / BLOCKED
candidate_revision = 9462b2594675b2e28388f55a2af189100b7cbdfc
preparation_action = PREPARE_EXACT_REVISION
preparation_request = REQ-E7-PREPARE-101-01-72A4C9E1
preparation_job = JOB-41D0F958C484CCF7 / REFUSED
refusal_reason = LOCAL ACTION NOT ALLOWLISTED
exact_clean_candidate = NOT_ESTABLISHED
qualification_request = REQ-E7-GATEC-101-01-D5F381B7 / NOT_CREATED
qualification = NOT_RUN / NOT_PASS
required_suites = 14 / ALL NOT_RUN / NOT_PASS
fp03_position_test = NOT_RUN / NOT_PASS
fp03_execution_test = NOT_RUN / NOT_PASS
project_test_failure = NONE_OBSERVED / TESTS_DID_NOT_RUN
provider_requests = 0
credentials = NONE
mutation_requests = 0
submit_cancel_amend_close = 0
SHADOW = NOT_STARTED
PAPER = NOT_STARTED
capital_exposure = NONE
Gate_D = BLOCKED / NOT_AUTHORIZED
LIVE = UNAUTHORIZED
latest_idle_watchdog_fingerprint = 993BD98269D985DA
latest_watchdog_local_exact_revision = 8fbf5fcae2eaf44accdf535121d8abf29ef5c93c / EXACT_CLEAN / JOB-852ABEE9A8CC
latest_watchdog_revalidation = DOES_NOT_SATISFY CANDIDATE 9462b259... EXACT-CLEAN PRECONDITION
worker_dispatch = NONE / E1-E7 REMAIN HOLD
```

## Unblock condition

This blocker is resolved only when authoritative approved-local evidence establishes one of the following for exact revision `9462b2594675b2e28388f55a2af189100b7cbdfc`:

1. canonical `PREPARE_EXACT_REVISION` is restored/allowlisted for project-r7 and a **fresh** preparation request produces `EXACT_CLEAN`; or
2. an equivalent approved-local operator fact proves that the exact candidate worktree already exists and is `EXACT_CLEAN` under current governance.

The refused E7-101 preparation request ID is terminal and must not be retried or reused. After unblock, PM must issue a fresh E7 requalification task with fresh request IDs.

## Watchdog revalidation — 993BD98269D985DA

The idle watchdog reported all Workers on HOLD and only the historical approved-local fact:

```text
LOCAL_EXACT_REVISION:8fbf5fcae2eaf44accdf535121d8abf29ef5c93c:EXACT_CLEAN:PREPARE_EXACT_REVISION:JOB-852ABEE9A8CC
```

That evidence remains valid only for historical revision `8fbf5fca...`. It does not prove `EXACT_CLEAN` for the current FP-03 combined candidate `9462b259...` and therefore does not unblock E7 requalification. No new Worker TASK is justified from this watchdog signal. E7 remains on `E7-20260829-102 / HOLD`; E1-E6 remain on their existing HOLD tasks.

## Authority boundary

Resolving this blocker does **not** require Product Owner trading/runtime authority, provider credentials, provider access, capital, SHADOW/PAPER authority, Gate D, or LIVE authority. It is an external AgentBridge/operator infrastructure dependency only.

Until resolved, FP-03 remains an implemented but unqualified candidate. Historical qualification evidence must not be rebound to `9462b259...`, and no provider/runtime step may use FP-03 as executable-qualified evidence.
