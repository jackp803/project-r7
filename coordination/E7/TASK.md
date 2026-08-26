# E7 Current Task

- task_id: `E7-20260826-079`
- issued_at: `2026-08-26T09:50:00+08:00`
- state: `HOLD`
- authority: `agents/E7_INTEGRATION.md`, `agents/README.md`, `contracts-v0.1`, accepted E7 zero-funds decision PR #87, accepted E4 normalization PR #88 merge `469706da386ccb63330140a8a5d47f0216ca402b`, preserved failed E7-077 qualification PR #89, accepted diagnostic PR #90 merge `d962ca05e12338b1020d3f47951f68087d49ff51`, Product Owner Gate C / SHADOW-only authorization

## Objective

Hold after E7-078 recovered the exact broker failure from the original E7-077 approved-local job without executing project code.

Authoritative state:

```text
E7-077 credential-free requalification = FAIL / PRESERVED
exact failing test = tests/brokers/test_okx_shadow.py legacy empty-details assertion
accepted provider semantic = exact ccy=USDT + valid details=[] -> known runtime Decimal("0")
next owner = E4 / bounded test-only compatibility remediation
Gate C = BLOCKED
SHADOW runtime = NOT STARTED
Gate D / LIVE = BLOCKED / NOT AUTHORIZED
```

## Required actions while HOLD

- Preserve E7-077 FAIL and E7-078 diagnostic evidence.
- Do not modify E4-owned broker source/tests.
- Do not execute project code or request local/provider jobs under this HOLD.
- Do not start qualification/requalification, production read-only verification, Demo verification, PAPER/SHADOW runtime, Gate D, LIVE, or capital movement.
- Do not request/read/store real credentials or provider-sensitive payloads.
- Do not use GitHub Actions/CI/hosted/GitHub-triggered compute.
- Do not claim Gate C PASS.

## Dependency

Wait for PM review of the bounded E4 test-only compatibility remediation. If accepted, PM may issue a new E7 full fourteen-suite credential-free requalification against the resulting exact accepted revision. A broker-only PASS must never be combined with E7-077's 13 passing suites to manufacture a Gate C qualification PASS.

## Writable scope

Only `coordination/E7/STATUS.md` for HOLD acknowledgement if needed.

## Completion

Acknowledge HOLD if needed and stop. Do not self-start another task.