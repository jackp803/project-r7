# E7 Current Task

- task_id: `E7-20260829-101`
- issued_at: `2026-08-29T14:15:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-fp03-combined-requalification-20260829`
- authority: `agents/E7_INTEGRATION.md`, `agents/PROJECT_MANAGER.md`, `agents/README.md`, accepted `protection-trigger-validity-v0.1`, merged E5 FP-03 candidate PR #105, merged E4 FP-03 candidate PR #106, `status/PM_E5_029_REVIEW_20260829.md`, `status/PM_E4_024_REVIEW_20260829.md`, `coordination/LOCAL_ACTION_CATALOG.md`

## Objective

Perform the **fresh approved-local credential-free requalification of the combined FP-03 E5+E4 candidate** at exact revision:

`9462b2594675b2e28388f55a2af189100b7cbdfc`

This is a credential-free local verification task only. It does not authorize provider/private API access, credentials, provider/account mutation, SHADOW/PAPER runtime, capital exposure, Gate D or LIVE.

The E5 and E4 domain tasks both ended `PARTIAL` because their local verification was `NOT_RUN`. Their merged source/test definitions are candidates only. `NOT_RUN != PASS`; do not combine historical suite evidence or merge status into a new PASS.

## Exact-revision preparation

The latest authoritative operator signal available to PM before this task still reported the approved-local exact worktree at older revision `8fbf5fcae2eaf44accdf535121d8abf29ef5c93c`.

Therefore before qualification, establish a clean exact approved-local worktree for `9462b2594675b2e28388f55a2af189100b7cbdfc` unless authoritative local evidence already proves that exact worktree exists.

Canonical preparation action:

```text
action_id = PREPARE_EXACT_REVISION
request_id = REQ-E7-PREPARE-101-01-72A4C9E1
approved_revision = 9462b2594675b2e28388f55a2af189100b7cbdfc
```

Rules:

- use the canonical action exactly; do not invent shell/path/branch arguments or aliases;
- the revision must be reachable from registered `origin/main`;
- require authoritative result proving `EXACT_CLEAN` for the exact candidate revision;
- if preparation is refused or exact clean state cannot be established, stop `BLOCKED`; do not retry under the same request ID and do not substitute another revision/environment.

## Credential-free qualification

After exact clean preparation succeeds, run exactly one fresh governed qualification request:

```text
action_id = GATE_C_CREDENTIAL_FREE_REQUALIFICATION
request_id = REQ-E7-GATEC-101-01-D5F381B7
approved_revision = 9462b2594675b2e28388f55a2af189100b7cbdfc
```

The approved-local execution must remain Windows/non-GitHub and credential-free.

## Required qualification coverage

The qualification must execute the complete current credential-free matrix on the exact candidate revision, not merely the two new files. Require all current suites to PASS:

```text
market_data
indicators
strategy
backtest
validation
execution
brokers
risk
position
storage
platform
integration
e2e
safety
```

The resulting matrix must materially include the new FP-03 definitions:

- `tests/position/test_protection_trigger_validity.py`;
- `tests/execution/test_protection_trigger_consumer.py`;
- existing protection/risk/execution/broker/safety regressions affected by the new imports and consumer boundary.

Do not assume a historical aggregate count. Record the actual suite/test counts from this run.

## Required FP-03 assertions to preserve

Qualification must fail if any tested path permits:

- LONG/SHORT breached or equality trigger evidence to become ACTIONABLE;
- stale/unknown market evidence to become ACTIONABLE;
- stale/mismatched Position/action authority to remain current;
- unchanged breached truth to become retryable merely because time advanced;
- E4 to accept missing/unsupported/FAIL_CLOSED/mismatched evidence;
- REPLACE/MODIFY_PROTECTION to become executable;
- shared `LAST_PRICE` evidence to infer provider `triggerPxType` or another native trigger basis;
- provider capability to be manufactured by arbitrary caller assertions;
- bypass of existing `protection-v0.1` quantity/expiry/reconciliation/idempotency/no-stop-widening controls.

## Verification / safety boundary

For this task:

```text
provider requests = 0 required
private API access = forbidden
credentials = NONE / do not read/request/use
provider/account mutation = forbidden
order submit/cancel/amend/close = forbidden
SHADOW runtime = NOT_STARTED
PAPER runtime = NOT_STARTED
capital exposure = NONE
GitHub Actions/CI/hosted/GitHub-triggered compute = forbidden
Gate D / LIVE = BLOCKED / NOT AUTHORIZED
```

Do not call OKX/public or private endpoints merely to qualify FP-03. This task is entirely deterministic/credential-free.

## Evidence rules

Create:

`status/e7/FP03_COMBINED_CREDENTIAL_FREE_REQUALIFICATION_20260829.md`

Record at minimum:

- task ID;
- exact candidate revision;
- preparation request/job/result and exact-clean evidence;
- qualification request/job/result;
- approved local OS/Python/PYTHONPATH and clean-worktree facts;
- each required suite result and actual test count;
- explicit evidence that both new FP-03 test files were included;
- provider requests = 0;
- credentials = NONE;
- mutation/submit/order actions = 0;
- SHADOW/PAPER runtime = NOT_STARTED;
- capital exposure = NONE;
- GitHub compute = NOT_USED;
- qualification conclusion.

Update `coordination/E7/STATUS.md` and commit/push the task branch.

## Result classification

### DONE

Use `DONE` only when:

- exact revision `9462b259...` is proven clean on the approved local environment;
- the fresh qualification job completes successfully;
- all required current credential-free suites PASS on that exact revision;
- new E5/E4 FP-03 tests are materially included;
- there are zero provider requests, zero credential use, zero mutation/order actions, no runtime and no capital exposure.

Report:

```text
FP-03 E5+E4 credential-free executable qualification = PASS / PM REVIEW REQUIRED
provider-facing verification on 9462b259... = NOT_RUN / NOT_INFERRED
FP-02 = UNCHANGED / SEPARATE
FP-15 = UNCHANGED / SEPARATE
SHADOW/PAPER = NOT_AUTHORIZED BY THIS TASK
Gate D / LIVE = BLOCKED / UNAUTHORIZED
```

### PARTIAL

Use `PARTIAL` when approved-local execution runs but exposes one or more bounded reproducible project test failures. Record exact failing suites/tests and sanitized reason; do not weaken tests, do not retry under the same request ID, and do not call FP-03 qualified.

### BLOCKED

Use `BLOCKED` when preparation/AgentBridge/local infrastructure prevents exact approved-local execution before project tests run. Preserve every suite as `NOT_RUN / NOT_PASS`; do not substitute GitHub/cloud/container compute or another revision.

## Completion

Read latest `main`, verify wake task ID `E7-20260829-101`, execute only this task, persist evidence, update STATUS, commit/push to the target branch, and stop on `DONE`, `PARTIAL`, or `BLOCKED`.

Do not self-start provider verification, AgentBridge source changes, FP-02, FP-15, SHADOW/PAPER, Gate D, LIVE, mutation, order action or capital movement/exposure.
