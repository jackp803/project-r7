# E7 Current Task

- task_id: `E7-20260825-077`
- issued_at: `2026-08-25T23:00:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-c-zero-balance-requalification-20260825`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate C baseline and Phase-1/2/3 work, preserved historical E7-069 FAIL, accepted prior credential-free requalification PR #85, accepted E7 zero-funds decision PR #87, accepted E4 zero-balance normalization PR #88 merge `469706da386ccb63330140a8a5d47f0216ca402b`, Product Owner Gate C / SHADOW-only authorization including approved local-only credential-free verification

## Objective

Execute only a new complete **credential-free Gate C requalification** after the accepted E4 production Shadow zero-balance normalization.

The prior credential-free PASS is valid only for its earlier exact revision and must not be carried forward automatically after production source changed.

Current authoritative interpretation:

```text
E4 zero-balance normalization = MERGED / STATICALLY ACCEPTED
E4 local verification         = NOT_RUN / NOT PASS
prior Gate C credential-free PASS = HISTORICAL / EARLIER REVISION ONLY
new Gate C credential-free qualification = REQUIRED
production read-only provider evidence    = MUST NOT RUN IN THIS TASK
Gate C = BLOCKED
SHADOW runtime = NOT STARTED
Gate D / LIVE = BLOCKED / NOT AUTHORIZED
```

## Exact executable source revision

The only project-code revision permitted for this task is:

```text
469706da386ccb63330140a8a5d47f0216ca402b
```

This is accepted `main` immediately after PR #88 merged. Later mailbox-only coordination commits are intentionally outside the executable source revision.

Before execution, prove in sanitized local evidence:

- repository revision exactly equals the SHA above;
- working tree is clean;
- approved local Windows / non-GitHub environment;
- Python executable/version and `PYTHONPATH=src`;
- no GitHub Actions/CI/hosted/GitHub-triggered compute.

If exact revision, clean tree, or approved environment cannot be established, do not execute project code; stop `BLOCKED` with exact evidence.

## Required complete requalification matrix

Run all fourteen suites in one bounded approved-local job/run against the exact source revision:

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

Overall requalification PASS requires **all fourteen suites PASS in the same approved-local job/run** against the exact revision above.

## Required regression interpretation

The matrix must include the merged E4 broker regression definitions and therefore exercise, through the normal `tests/brokers` discovery:

- exact authenticated `ccy=USDT` + valid envelope + `details=[]` -> known runtime `Decimal("0")`;
- explicit zero and positive USDT detail parsing unchanged;
- wrong-currency, duplicate, malformed details/availBal and provider error remain fail closed;
- runtime balance remains absent from durable/public evidence;
- exact GET-only allowlist/default deny and no-submit/no-mutation Shadow surface remain unchanged.

Do not add, edit, weaken, or selectively exclude tests in this evidence task.

## Local-job boundary

Use only the existing Product-Owner-approved local non-GitHub AgentBridge/local-job mechanism. Request exactly one qualification job with a task-specific action such as:

```text
GATE_C_ZERO_BALANCE_CREDENTIAL_FREE_REQUALIFICATION
```

Use only repository fake/sanitized fixtures and local temp/storage resources required by tests.

No real credentials, provider/public/private network request, or external exchange account read is authorized or needed.

## Failure handling

If any required suite fails/errors:

1. preserve sanitized evidence sufficient to identify every failing/erroring test, classification, assertion/exception reason, relevant traceback location, command, exact source revision, environment and exit code;
2. mark the requalification `FAIL`;
3. do not selectively rerun to replace the first result;
4. do not repair source/tests, weaken assertions, or assign another owner inside this task;
5. update E7 STATUS/evidence and stop `PARTIAL` or `BLOCKED` for PM review.

A later diagnostic/remediation, if justified, must be a separate governed task.

## Required evidence

Persist only E7-owned sanitized evidence, for example:

```text
status/e7/GATE_C_ZERO_BALANCE_CREDENTIAL_FREE_REQUALIFICATION_20260825.md
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
- explicit note that prior qualification evidence remains historical and is not overwritten;
- proof no credentials/provider traffic/mutation/runtime/GitHub compute were used;
- overall requalification result.

Do not include secrets, raw provider responses, raw UID/account identifiers, exact balances, provider order/fill IDs, cookies/tokens/browser-auth material, or unnecessary user-specific filesystem paths.

## Credential-free / financial safety boundary

Forbidden:

- real API key/secret/passphrase/token/cookie/browser-auth material;
- any real OKX/provider request, including public/private reads;
- external exchange account reads;
- order submit/place/cancel/amend/close;
- leverage/account/position-mode mutation;
- transfer/deposit/withdrawal/capital movement;
- Demo verification;
- PAPER or SHADOW runtime start;
- Gate D/LIVE/capital exposure;
- GitHub Actions/CI/hosted/GitHub-triggered execution;
- production/test/contract/migration modification.

## Release interpretation

Even if every suite PASSes:

```text
credential-free Gate C blocker for revision 469706da... = CLOSED / PASS
production read-only Gate C evidence on revision 469706da... = NOT YET RE-VERIFIED
Gate C — SHADOW_READY = BLOCKED / production read-only re-verification + PM final review still required
SHADOW runtime = NOT STARTED
Gate D / LIVE = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
```

Do not start production read-only provider verification, SHADOW runtime, Gate D or LIVE in this task. PM will review and issue any later provider-read task separately.

## Writable scope

Only E7-owned qualification/control/evidence paths:

- `coordination/E7/LOCAL_JOB_REQUEST.json` if required by the existing local-job mechanism;
- `coordination/E7/STATUS.md`;
- `status/e7/**` for this requalification evidence;
- `status/INTEGRATION_STATUS.md` / `status/RELEASE_GATES.md` only for accurate non-promotional qualification state.

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
- Gate C remains blocked pending separately governed production read-only re-verification and PM final review.

### PARTIAL / BLOCKED

- any required suite fails/errors;
- exact revision/clean tree cannot be proven;
- approved-local execution unavailable;
- evidence insufficient to identify a failure;
- any safety/authority boundary cannot be satisfied.

## Completion

Read latest `main`, verify wake task ID `E7-20260825-077`, execute only this TASK, update `coordination/E7/STATUS.md`, commit/push required evidence to the target branch, and stop on `DONE`, `PARTIAL`, or `BLOCKED`. Do not self-start provider verification, SHADOW runtime, Gate D, LIVE, remediation, or another task.