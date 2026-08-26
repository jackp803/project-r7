# E7 Current Task

- task_id: `E7-20260826-080`
- issued_at: `2026-08-26T09:57:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-c-post-test-compat-requalification-20260826`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate C baseline and Phase-1/2/3 work, accepted E7 zero-funds decision PR #87, accepted E4 zero-balance normalization PR #88, preserved failed E7-077 qualification PR #89, accepted E7 diagnostic PR #90, accepted E4 test-only compatibility remediation PR #91 merge `ab725965e96cac7a9769fd1ab15a3e626f920b95`, Product Owner Gate C / SHADOW-only authorization including approved local-only credential-free verification

## Objective

Execute only a new complete **credential-free Gate C requalification** after the accepted E4 test-only compatibility remediation.

Historical evidence must remain intact:

```text
E7-077 source revision = 469706da386ccb63330140a8a5d47f0216ca402b
E7-077 result = FAIL / 13 of 14 suites PASS / tests/brokers FAIL
E7-078 diagnostic = recovered stale legacy broker assertion conflict
PR #91 = test-definition-only compatibility remediation / production source unchanged
```

Do not combine historical PASS suites with any new result. This task must produce one new complete qualification run.

## Exact executable source revision

The only project-code/test-definition revision permitted for this task is:

```text
ab725965e96cac7a9769fd1ab15a3e626f920b95
```

This is accepted `main` immediately after PR #91 merged. Later mailbox-only coordination commits are intentionally outside the executable source revision.

Before any project-code execution, sanitized local evidence must prove:

- repository revision exactly equals `ab725965e96cac7a9769fd1ab15a3e626f920b95`;
- working tree is clean;
- approved local Windows / non-GitHub environment;
- Python executable/version and `PYTHONPATH=src`;
- no GitHub Actions/CI/hosted/GitHub-triggered compute.

If exact revision, clean tree, or approved environment cannot be established, do not execute project code; stop `BLOCKED` with exact evidence.

## Required complete requalification matrix

Run all fourteen suites in one bounded approved-local job/run:

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

A suite is PASS only if its command exits `0` with no unittest failures/errors. `NOT_RUN != PASS`.

Overall PASS requires **all fourteen suites PASS in the same approved-local job/run** against the exact revision above.

## Required broker regression interpretation

Normal `tests/brokers` discovery must exercise both accepted and fail-closed behavior without test edits in this task:

- exact authenticated `ccy=USDT` + successful otherwise-valid envelope + `details=[]` -> healthy known runtime `Decimal("0")`;
- runtime exact balance remains redacted from public/durable projection and repr;
- explicit zero and positive USDT detail parsing remains valid;
- wrong-currency, duplicate, malformed details/availBal and provider errors remain fail closed;
- wrong leverage margin mode remains fail closed;
- fill-checkpoint regression remains fail closed;
- exact GET-only allowlist/default deny and no-submit/no-mutation Shadow surface remain unchanged.

Do not add, edit, weaken, rename, skip, or selectively exclude tests in this qualification task.

## Local-job boundary

Use only the existing Product-Owner-approved local non-GitHub AgentBridge/local-job mechanism. Request exactly one qualification job with a task-specific action such as:

```text
GATE_C_POST_TEST_COMPAT_CREDENTIAL_FREE_REQUALIFICATION
```

Use only repository fake/sanitized fixtures and local resources required by tests.

No real credentials, provider/public/private network request, external exchange account read, or Demo access is authorized or needed.

## Failure handling

If any required suite fails/errors:

1. persist sanitized evidence identifying every failing/erroring test, failure/error classification, assertion/exception reason, relevant traceback location, exact command, exact source revision, environment and exit code;
2. mark the requalification `FAIL`;
3. do not selectively rerun to replace the result;
4. do not repair source/tests or weaken assertions in this task;
5. do not assign or execute remediation inside this task;
6. update E7 STATUS/evidence and stop `PARTIAL` or `BLOCKED` for PM review.

If the callback is truncated, prefer recovering the original local-job evidence in a later separately governed diagnostic rather than guessing.

## Required evidence

Persist only E7-owned sanitized qualification evidence, for example:

```text
status/e7/GATE_C_POST_TEST_COMPAT_CREDENTIAL_FREE_REQUALIFICATION_20260826.md
```

Include:

- task ID;
- exact executable source revision;
- local request/action/job IDs;
- OS/Python/PYTHONPATH/clean-tree evidence;
- exact commands;
- per-suite test counts/timestamps/exit/result;
- total tests if determinable;
- every failure/error identity and reason if present;
- explicit preservation of E7-077 historical FAIL and E7-078 diagnostic evidence;
- proof no credentials/provider traffic/mutation/runtime/GitHub compute were used;
- overall requalification result.

Do not include secrets, raw provider responses, raw UID/account identifiers, exact balances, provider order/fill IDs, cookies/tokens/browser-auth material, or unnecessary local filesystem paths.

## Credential-free / financial safety boundary

Forbidden:

- real API key/secret/passphrase/token/cookie/browser-auth material;
- any real OKX/provider public/private request;
- external exchange account reads;
- order submit/place/cancel/amend/close;
- leverage/account/position-mode mutation;
- transfer/deposit/withdrawal/capital movement;
- Demo verification;
- PAPER or SHADOW runtime start;
- Gate D/LIVE/capital exposure;
- GitHub Actions/CI/hosted/GitHub-triggered execution;
- production or test-definition modification.

## Release interpretation

Even if all fourteen suites PASS:

```text
credential-free Gate C blocker for revision ab725965... = CLOSED / PASS
production read-only Gate C evidence on revision ab725965... = NOT YET RE-VERIFIED
Gate C — SHADOW_READY = BLOCKED / production read-only re-verification + PM final review still required
SHADOW runtime = NOT STARTED
Gate D / LIVE = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
```

Do not start production read-only provider verification, SHADOW runtime, Gate D, LIVE, or another task. PM will review this evidence and issue any later provider-read task separately.

## Writable scope

Only E7-owned qualification/control/evidence paths:

- `coordination/E7/LOCAL_JOB_REQUEST.json` if required;
- `coordination/E7/STATUS.md`;
- `status/e7/**` for this qualification evidence;
- `status/INTEGRATION_STATUS.md` / `status/RELEASE_GATES.md` only if needed to preserve accurate non-promotional state.

Forbidden:

- production source changes;
- test-definition changes;
- E1-E6 TASK/STATUS or owned code/tests;
- contracts/ADRs/migrations;
- remediation;
- provider/private/public real execution;
- credentials/secrets;
- PAPER/SHADOW runtime start;
- Gate D/LIVE/capital exposure;
- GitHub compute.

## Acceptance

### DONE

- exact revision and clean approved-local environment proven;
- exactly one complete fourteen-suite credential-free matrix executed;
- all required suites PASS with exit `0` and no unittest failures/errors;
- sanitized evidence committed/pushed;
- historical E7-077 FAIL remains preserved;
- Gate C remains blocked pending separately governed production read-only re-verification and PM final review.

### PARTIAL / BLOCKED

- any required suite fails/errors;
- exact revision/clean tree cannot be proven;
- approved-local execution unavailable;
- failure evidence insufficient;
- any safety/authority boundary cannot be satisfied.

## Completion

Read latest `main`, verify wake task ID `E7-20260826-080`, execute only this TASK, update `coordination/E7/STATUS.md`, commit/push required evidence to the target branch, and stop on `DONE`, `PARTIAL`, or `BLOCKED`. Do not self-start provider verification, SHADOW runtime, Gate D, LIVE, remediation, or another task.