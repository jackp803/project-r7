# E7 Current Task

- task_id: `E7-20260825-069`
- issued_at: `2026-08-25T14:31:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-c-credential-free-qualification-20260825`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, Gate C baseline PR #75, accepted Phase-1/2 PRs #76/#77/#78/#79/#80, accepted Phase-3 PR #81 merge `9b3370cbf29ce47abe048cc18860cc89b5fd532d`, Product Owner Gate C / SHADOW-only authorization

## Objective

Execute only Gate C Phase 4: one complete **credential-free, fake/sanitized, approved-local Gate C qualification** against the exact accepted source revision below.

This task is executable evidence collection only. Do not modify production code, test definitions, contracts, ADRs, migrations, risk policy, or provider semantics. Do not perform remediation in this task.

## Exact executable source revision

The only revision that may be executed for qualification is:

```text
9b3370cbf29ce47abe048cc18860cc89b5fd532d
```

This is the accepted `main` revision immediately after PR #81 and before this TASK issuance. The TASK issuance commit itself is coordination-only and is intentionally not part of the executable source revision.

Before execution, local evidence must prove:

- repository revision exactly equals the SHA above;
- working tree is clean;
- approved local Windows / non-GitHub environment;
- Python executable/version and `PYTHONPATH=src`;
- no GitHub Actions/CI/hosted/GitHub-triggered compute.

If exact revision/clean-tree/environment identity cannot be established, do not run and stop `BLOCKED` with exact evidence.

## Qualification matrix

Run the complete credential-free repository test matrix on the approved local environment. Use the exact source revision above and record each suite separately with command, start/end timestamp, test count, failures/errors/skips if reported, exit code, and PASS/FAIL.

Required suites:

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

A suite is PASS only if its command exits `0` and unittest reports no failures/errors. `NOT_RUN != PASS`.

The qualification is PASS only if **all required suites PASS in the same approved-local qualification job/run against the exact source revision**.

## Local-job execution boundary

Product Owner has already authorized approved-local, non-GitHub, credential-free verification for Gate C work.

If the repository's approved local execution bridge is available, request exactly one bounded local job for this task using the existing E7 local-job mailbox mechanism. Use an action name specific to this task such as:

```text
GATE_C_CREDENTIAL_FREE_QUALIFICATION
```

The local job must execute only the matrix above against the exact source revision. It must not use provider credentials or real provider/private network access.

If the approved local bridge/operator surface is genuinely unavailable, persist the exact blocker and stop `BLOCKED`; do not substitute GitHub compute or another environment.

## Credential-free / network safety rules

This phase uses only fake/sanitized test inputs.

Forbidden during this task:

- real API key/secret/passphrase/token/cookie/browser-auth material;
- real provider/private authenticated request;
- external exchange account read;
- order submission/place/cancel/amend/close;
- leverage/account/position-mode mutation;
- transfer/deposit/withdrawal/capital movement;
- PAPER or SHADOW runtime start;
- LIVE/Gate D/capital exposure;
- GitHub Actions/CI/hosted/GitHub-triggered execution.

Public internet/provider access is not required for this qualification and must not be added merely to make tests pass.

## Failure handling

If any required suite fails or errors:

1. preserve enough sanitized executable evidence to identify every failing/erroring test, exception/reason, command, exit code, source revision and environment;
2. mark the qualification `FAIL`;
3. do **not** selectively rerun, repair production/tests, weaken assertions, or start a remediation task yourself;
4. update E7 STATUS and evidence artifact and stop `PARTIAL` or `BLOCKED` as appropriate for PM review.

A failed first qualification attempt remains evidence. Do not hide it with a second attempt in the same task.

## Required evidence artifact

Create/update only E7-owned evidence, for example:

```text
status/e7/GATE_C_CREDENTIAL_FREE_QUALIFICATION_20260825.md
```

It must contain, in sanitized form:

- task ID;
- exact execution source revision;
- Product Owner authority reference;
- local request/action/job identifiers if used;
- OS/Python/environment evidence;
- clean-tree proof;
- exact matrix commands;
- per-suite counts/exits/results;
- total tests if determinable;
- proof credential/private-provider/network mutation was not used;
- proof GitHub compute was not used;
- overall qualification result.

Do not include secrets, raw provider payloads, raw UID/account identifiers, exact balances, provider order/fill IDs, cookies/tokens, or browser-auth material.

## Release interpretation

Even if this credential-free qualification PASSes:

```text
Gate C — SHADOW_READY = BLOCKED / CREDENTIAL-DEPENDENT EVIDENCE STILL REQUIRED
SHADOW runtime = NOT STARTED
Gate D / LIVE = BLOCKED / NOT AUTHORIZED
```

Do not mark Gate C PASS from this task alone. The accepted Gate C baseline separately requires operator-gated production read-only verification after safe regional-domain/read-only credential setup and PM review.

## Writable scope

Only E7-owned qualification/evidence/control paths needed for this task:

- `coordination/E7/LOCAL_JOB_REQUEST.json` using the existing local-job mailbox mechanism if required;
- `coordination/E7/STATUS.md`;
- `status/e7/**` for this qualification evidence;
- `status/INTEGRATION_STATUS.md` / `status/RELEASE_GATES.md` only to record non-promotional qualification state, never Gate C PASS.

Forbidden:

- all production source changes;
- all test-definition changes;
- E1-E6 STATUS/TASK or owned code/tests;
- contracts/ADRs/migrations;
- remediation;
- credentials/secrets;
- provider/private real execution;
- PAPER/SHADOW runtime start;
- Gate D/LIVE/capital exposure;
- GitHub compute.

## Acceptance

### DONE

- exact source revision and clean approved-local environment are proven;
- exactly one complete credential-free Gate C qualification matrix is executed;
- every required suite PASSes with exit `0` and no unittest failure/error;
- sanitized evidence is committed/pushed;
- Gate C remains blocked pending credential-dependent read-only evidence and PM review.

### PARTIAL / BLOCKED

- any required suite fails/errors, exact revision cannot be proven, approved-local execution is unavailable, or evidence is insufficient.
- preserve evidence, update STATUS, and stop without remediation or rerun.

## Completion

Read latest `main`, verify wake task ID `E7-20260825-069`, execute only this TASK, update `coordination/E7/STATUS.md`, commit/push required evidence to the target branch, and stop on `DONE`, `PARTIAL`, or `BLOCKED`. Do not self-start credential setup/provider verification, remediation, SHADOW runtime, Gate D, or LIVE work.