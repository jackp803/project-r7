# E7 Current Task

- task_id: `E7-20260825-072`
- issued_at: `2026-08-25T19:05:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-c-credential-free-requalification-20260825`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate C baseline PR #75, accepted Phase-1/2/3 work through PR #81, preserved failed qualification PR #82, recovered diagnostic PR #83, accepted E6 storage export remediation PR #84 merge `83be94fbc4ee666156c2aaf7a7141b3eda9a4b4c`, Product Owner Gate C / SHADOW-only authorization including approved local-only credential-free verification

## Objective

Execute only a new complete **credential-free Gate C requalification** after the accepted E6 storage export compatibility remediation.

The prior E7-069 qualification remains immutable historical evidence:

```text
E7-069 qualification source = 9b3370cbf29ce47abe048cc18860cc89b5fd532d
E7-069 result               = FAIL
historical failing suite    = tests/storage
historical failure          = storage.__all__ public-export compatibility
```

Do not erase, relabel, or combine the old result with this requalification. This task qualifies only the exact remediated source revision below.

## Exact executable source revision

The only revision permitted for project-code execution is:

```text
83be94fbc4ee666156c2aaf7a7141b3eda9a4b4c
```

This is accepted `main` immediately after PR #84 merged. Later mailbox-only coordination commits are intentionally outside the executable source revision.

Before execution, local evidence must prove:

- repository revision exactly equals the SHA above;
- working tree is clean;
- approved local Windows / non-GitHub environment;
- Python executable/version and `PYTHONPATH=src`;
- no GitHub Actions/CI/hosted/GitHub-triggered compute.

If exact revision, clean tree, or approved environment cannot be established, do not run; stop `BLOCKED` with exact evidence.

## Required requalification matrix

Run all required suites in one bounded approved-local job/run against the exact source revision:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/market_data -p "test_*.py" -v
python -m unittest discover -s tests/indicators -p "test_*.py" -v
python -m unittest discover -s tests/strategy -p "test_*.py" -v
python -m unittest discover -s tests/backtest -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/risk -p "test_*.py" -v
python -m unittest discover -s tests/position -p "test_*.py" -v
python -m unittest discover -s tests/storage -p "test_*.py" -v
python -m unittest discover -s tests/platform -p "test_*.py" -v
python -m unittest discover -s tests/registry -p "test_*.py" -v
python -m unittest discover -s tests/integration -p "test_*.py" -v
python -m unittest discover -s tests/e2e -p "test_*.py" -v
python -m unittest discover -s tests/safety -p "test_*.py" -v
```

A suite is PASS only if the command exits `0` with no unittest failures/errors. `NOT_RUN != PASS`.

The credential-free requalification is PASS only if **every required suite PASSes in the same approved-local requalification job/run** against the exact source revision.

## Local-job boundary

Use the existing approved E7 local-job mailbox mechanism if available. Request exactly one requalification job with a task-specific action such as:

```text
GATE_C_CREDENTIAL_FREE_REQUALIFICATION
```

The job may use only repository fake/sanitized fixtures and local storage/temp files required by the tests.

No real provider/private network access or real credential is required or permitted.

## Failure handling

If any suite fails/errors:

1. preserve sanitized evidence sufficient to identify every failing/erroring test, failure/error classification, assertion/exception reason, relevant traceback location, command, source revision, environment and exit code;
2. mark this requalification `FAIL`;
3. do not selectively rerun, repair source/tests, weaken assertions, or start remediation inside this task;
4. update E7 STATUS/evidence and stop `PARTIAL` or `BLOCKED` for PM review.

Do not hide a failed first requalification attempt with a second attempt in the same task.

## Required evidence

Persist bounded E7-owned evidence, for example:

```text
status/e7/GATE_C_CREDENTIAL_FREE_REQUALIFICATION_20260825.md
```

Include in sanitized form:

- task ID;
- exact executable source revision;
- local request/action/job IDs;
- OS/Python/PYTHONPATH/clean-tree evidence;
- all exact commands;
- per-suite test counts, start/end timestamps, exits and PASS/FAIL;
- failure identities/reasons if any;
- total test count if determinable;
- explicit comparison that E7-069 remains historical FAIL evidence and is not overwritten;
- proof no real credentials/provider/private requests/mutation/runtime/GitHub compute were used;
- overall requalification result.

Do not include secrets, raw provider payloads, raw UID/account identifiers, exact balances, provider order/fill IDs, cookies/tokens/browser-auth material, or unnecessary user-specific local paths.

## Credential-free / financial safety boundary

Forbidden:

- real API key/secret/passphrase/token/cookie/browser-auth material;
- real provider/private authenticated request;
- external exchange account read;
- order submission/place/cancel/amend/close;
- leverage/account/position-mode mutation;
- transfer/deposit/withdrawal/capital movement;
- PAPER or SHADOW runtime start;
- Gate D/LIVE/capital exposure;
- GitHub Actions/CI/hosted/GitHub-triggered execution;
- production/test/contract/migration remediation in this evidence task.

## Release interpretation

Even if every credential-free suite PASSes:

```text
credential-free Gate C blocker = CLOSED / PASS FOR EXACT REMEDIATED REVISION
Gate C — SHADOW_READY          = BLOCKED / CREDENTIAL-DEPENDENT READ-ONLY EVIDENCE STILL REQUIRED
SHADOW runtime                 = NOT STARTED
Gate D / LIVE                  = BLOCKED / NOT AUTHORIZED
LIVE                           = UNAUTHORIZED
```

Do not start credential setup, provider verification, SHADOW runtime, Gate D or LIVE in this task. PM will review the result and issue any later operator-gated work separately.

## Writable scope

Only E7-owned requalification/control/evidence paths:

- `coordination/E7/LOCAL_JOB_REQUEST.json` if required by the existing mailbox mechanism;
- `coordination/E7/STATUS.md`;
- `status/e7/**` for this requalification evidence;
- `status/INTEGRATION_STATUS.md` / `status/RELEASE_GATES.md` only for accurate non-promotional credential-free qualification state.

Forbidden:

- all production source changes;
- all test-definition changes;
- E1-E6 TASK/STATUS or owned code/tests;
- contracts/ADRs/migrations;
- remediation;
- provider/private real execution;
- credentials/secrets;
- PAPER/SHADOW runtime start;
- Gate D/LIVE/capital exposure;
- GitHub compute.

## Acceptance

### DONE

- exact remediated source revision and clean approved-local environment are proven;
- exactly one complete required requalification matrix is executed;
- every required suite PASSes with exit `0` and no unittest failure/error;
- sanitized evidence is committed/pushed;
- Gate C remains blocked pending credential-dependent read-only evidence and PM review.

### PARTIAL / BLOCKED

- any required suite fails/errors;
- exact revision/clean tree cannot be proven;
- approved-local execution is unavailable;
- evidence is insufficient to diagnose a failure;
- any safety/authority constraint cannot be satisfied.

## Completion

Read latest `main`, verify wake task ID `E7-20260825-072`, execute only this TASK, update `coordination/E7/STATUS.md`, commit/push required evidence to the target branch, and stop on `DONE`, `PARTIAL`, or `BLOCKED`. Do not self-start credential-dependent provider verification, SHADOW runtime, Gate D, LIVE, remediation, or another task.