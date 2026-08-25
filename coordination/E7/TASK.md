# E7 Current Task

- task_id: `E7-20260825-078`
- issued_at: `2026-08-25T23:28:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e7-gate-c-zero-balance-broker-diagnostic-20260825`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, accepted E7 zero-funds decision PR #87, accepted E4 zero-balance normalization PR #88 merge `469706da386ccb63330140a8a5d47f0216ca402b`, accepted failed E7-077 requalification evidence PR #89 merge `521716642edbe722e3dc9b15604d0765f0d61e79`, Product Owner Gate C / SHADOW-only authorization including approved local-only credential-free diagnostics

## Objective

Recover the exact broker-suite failure identity and reason from the failed E7-077 credential-free Gate C requalification. This task is **diagnostic only**.

Authoritative failed qualification:

```text
E7-077 source revision = 469706da386ccb63330140a8a5d47f0216ca402b
qualification result   = FAIL
local job              = JOB-0941F793B86D7D94
required suites        = 14
passed suites          = 13 / 14
failing suite          = tests/brokers
broker test count      = 135
broker exit            = 1
exact failure detail   = unavailable because durable callback was truncated
```

The E7-077 FAIL is immutable historical/current evidence for this revision until a later separately governed full requalification succeeds. Do not relabel or replace it in this task.

## Required diagnostic order

1. **Prefer evidence recovery without executing project code.** Use the existing approved local AgentBridge/local-job evidence surface to recover the complete sanitized stdout/stderr/failure summary for original job:

```text
JOB-0941F793B86D7D94
```

If the original job record can provide the failing/erroring test identity, failure/error classification, assertion/exception reason, relevant traceback location, broker command, source revision and exit code, persist that evidence and stop. Do not rerun tests merely for convenience.

2. **Only if the original job detail is genuinely unavailable**, one isolated diagnostic execution is authorized against exactly:

```text
469706da386ccb63330140a8a5d47f0216ca402b
```

Approved-local Windows / non-GitHub environment, clean working tree, `PYTHONPATH=src`, credential-free fake/sanitized fixtures only.

Run only:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

This isolated broker run is diagnostic evidence only. It is **not** a Gate C qualification/requalification and cannot convert E7-077 from FAIL to PASS even if it exits 0.

## Evidence required

Persist E7-owned sanitized diagnostic evidence, for example:

```text
status/e7/GATE_C_ZERO_BALANCE_BROKER_FAILURE_DIAGNOSTIC_20260825.md
```

Include:

- task ID;
- E7-077 original job/request identity;
- exact source revision;
- whether evidence came from original-job recovery or one isolated broker diagnostic run;
- if run: OS/Python/PYTHONPATH/clean-tree proof, exact command, start/end, test count, exit;
- every failing/erroring test identity;
- failure vs error classification;
- assertion/exception reason;
- relevant traceback file/line;
- enough sanitized context for PM to identify the correct owner and bounded remediation;
- explicit statement that E7-077 remains FAIL and no diagnostic result replaces it;
- confirmation of zero credentials/provider traffic/mutation/runtime/GitHub compute.

Do not persist secrets, raw provider responses, UIDs, exact balances, provider order/fill IDs, cookies/tokens/browser-auth material, or unnecessary local filesystem paths.

## Scope and safety boundary

Forbidden:

- production source changes;
- test-definition changes;
- weakening/deleting assertions;
- E1-E6 code/tests/TASK/STATUS changes;
- remediation or owner implementation changes;
- full qualification/requalification rerun;
- selective reruns beyond the single allowed `tests/brokers` diagnostic fallback;
- real credentials;
- any real OKX/provider public/private network request;
- external exchange account read;
- Demo verification;
- order submit/place/cancel/amend/close;
- leverage/account/position-mode mutation;
- transfer/deposit/withdrawal/capital movement;
- PAPER/SHADOW runtime start;
- Gate D/LIVE/capital exposure;
- GitHub Actions/CI/hosted/GitHub-triggered project compute.

## Result interpretation

### DONE

- exact broker failure identity/reason is recovered with sufficient sanitized evidence for PM ownership/remediation review;
- E7-077 remains FAIL;
- no remediation or requalification occurs.

### BLOCKED

- neither original-job evidence recovery nor the one allowed isolated broker diagnostic can provide sufficient failure identity/reason;
- exact revision/clean approved-local environment cannot be proven if diagnostic execution is needed;
- any safety/authority constraint cannot be satisfied.

## Writable scope

Only:

- `coordination/E7/LOCAL_JOB_REQUEST.json` if required by the existing local-job mechanism;
- `coordination/E7/STATUS.md`;
- `status/e7/**` for this diagnostic evidence.

## Completion

Read latest `main`, verify wake task ID `E7-20260825-078`, execute only this TASK, update `coordination/E7/STATUS.md`, commit/push required diagnostic evidence to the target branch, and stop on `DONE` or `BLOCKED`. Do not self-start remediation, requalification, provider verification, SHADOW runtime, Gate D, LIVE, or another task.