# Gate C Zero-Balance Broker Failure Diagnostic — 2026-08-25

- task_id: `E7-20260825-078`
- source_task_id: `E7-20260825-077`
- source_request_id: `REQ-E7-GATEC-077-01-5D8C2A64`
- source_action_id: `GATE_C_ZERO_BALANCE_CREDENTIAL_FREE_REQUALIFICATION`
- source_job_id: `JOB-0941F793B86D7D94`
- source_revision: `469706da386ccb63330140a8a5d47f0216ca402b`
- source_job_state: `FAILED`
- source_job_exit_code: `1`
- recovery_request_id: `REQ-E7-GATEC-078-01-6A9D4C21`
- recovery_action_id: `GATE_C_ZERO_BALANCE_BROKER_FAILURE_EVIDENCE_RECOVERY`
- recovery_job_id: `JOB-61830F3DE483D4B9`
- recovery_job_state: `SUCCEEDED`
- recovery_job_exit_code: `0`
- diagnostic_method: `ORIGINAL_JOB_EVIDENCE_RECOVERY / NO PROJECT CODE EXECUTED`
- diagnostic_result: `DONE / EXACT FAILURE RECOVERED`

## Recovered broker failure

The original E7-077 broker suite ran:

```text
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

Original broker-suite result:

```text
tests = 135
exit  = 1
result = FAILED (failures=1)
```

Exactly one failure was recovered from the original approved-local job record:

```text
classification = FAIL / AssertionError
test = test_malformed_balance_wrong_margin_and_fill_checkpoint_regression_fail_closed
class = test_okx_shadow.OKXShadowReaderTests
traceback = tests/brokers/test_okx_shadow.py:463
assertion = expected reason_codes ("BALANCE_USDT_UNKNOWN",) but actual reason_codes were ()
```

Sanitized assertion difference:

```text
expected = ('BALANCE_USDT_UNKNOWN',)
actual   = ()
```

## Diagnostic interpretation

This failure is a compatibility conflict between the accepted E4 zero-balance normalization and an existing broker regression assertion on the same accepted source revision.

The accepted zero-balance behavior intentionally treats an otherwise-valid exact `ccy=USDT` balance response with `details=[]` as known zero. The recovered legacy assertion still expects that shape to produce `BALANCE_USDT_UNKNOWN`. The diagnostic therefore identifies the exact disagreement for PM ownership/remediation review; E7-078 does not decide or implement the remediation and does not modify production source or tests.

## E7-077 preservation

E7-077 remains authoritative as:

```text
source revision = 469706da386ccb63330140a8a5d47f0216ca402b
qualification result = FAIL
required suites = 14
passed suites = 13 / 14
failing suite = tests/brokers
```

This diagnostic does not replace, relabel, rerun, or convert E7-077. A later remediation or full requalification requires a separately governed task.

## Safety / execution confirmation

The E7-078 recovery job read existing durable local-job evidence only. It executed no project code and performed no broker test rerun. No real credentials were read or requested. No OKX/provider public/private traffic, external account read, Demo verification, mutation, order action, transfer/deposit/withdrawal, PAPER/SHADOW runtime, Gate D/LIVE action, or capital exposure occurred. GitHub Actions, CI, hosted runners, and GitHub-triggered project compute were not used.

No raw provider response, UID/account identifier, exact balance, provider order/fill ID, cookie/token/browser-auth material, secret, or unnecessary local filesystem path is persisted here.

## Release interpretation

```text
E7-077 credential-free requalification = FAIL / PRESERVED
Gate C — SHADOW_READY = BLOCKED
SHADOW runtime = NOT STARTED
Gate D — LIVE_READY = BLOCKED / NOT AUTHORIZED
LIVE = UNAUTHORIZED
```

E7-078 is diagnostic only and stops after exact failure recovery.