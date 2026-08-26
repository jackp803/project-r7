# E4 Current Task

- task_id: `E4-20260826-022`
- issued_at: `2026-08-26T09:51:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-gate-c-zero-balance-test-compat-20260826`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, accepted E7 zero-funds semantics PR #87, accepted E4 zero-balance normalization PR #88 merge `469706da386ccb63330140a8a5d47f0216ca402b`, preserved failed E7-077 requalification PR #89, accepted E7 diagnostic PR #90 merge `d962ca05e12338b1020d3f47951f68087d49ff51`, Product Owner Gate C / SHADOW-only authorization

## Objective

Perform only the smallest E4-owned **broker test compatibility remediation** identified by E7-078.

The accepted production semantic is already authoritative and must not be changed:

```text
exact authenticated GET /api/v5/account/balance?ccy=USDT
+ successful otherwise-valid envelope
+ details exactly []
-> usdt_balance_known = true
-> runtime_available_balance = Decimal("0")
```

E7-078 recovered exactly one failing legacy assertion from E7-077:

```text
test = test_malformed_balance_wrong_margin_and_fill_checkpoint_regression_fail_closed
file = tests/brokers/test_okx_shadow.py
historical failing line = 463
legacy expected = ("BALANCE_USDT_UNKNOWN",)
actual under accepted semantics = ()
```

The failure is a stale regression expectation for the now-accepted empty-details zero-balance case.

## Required change

1. Update only the stale empty-`details` assertion in `tests/brokers/test_okx_shadow.py` so it validates the accepted known-zero behavior instead of expecting `BALANCE_USDT_UNKNOWN`.
2. Preserve meaningful coverage in the same test area:
   - assert the empty-details result is healthy/known as appropriate for the otherwise-valid fake batch;
   - assert `runtime_available_balance == Decimal("0")`;
   - preserve redaction expectations if present/appropriate;
   - preserve the existing wrong-margin fail-closed assertion;
   - preserve the existing fill-checkpoint regression fail-closed assertion.
3. Rename the test method only if needed to stop calling the accepted empty-details case "malformed"; keep the remaining negative scenarios explicit.
4. Do not delete or weaken unrelated broker safety assertions.
5. Do not modify production code. In particular, do not change `src/brokers/okx_shadow.py`.
6. Do not change endpoint/method allowlists, authentication, credentials, no-submit/no-mutation surfaces, E5 risk semantics, E6 storage, E7 contracts/composition, or release-gate semantics.

## Writable scope

Only:

- `tests/brokers/test_okx_shadow.py`;
- bounded E4 status/handoff evidence under `status/e4/**`;
- `coordination/E4/STATUS.md`.

Do not modify the newer dedicated `tests/brokers/test_okx_shadow_zero_balance.py` unless you find a direct contradiction that cannot be resolved in the legacy test alone; if so, stop `BLOCKED` rather than broaden scope.

## Verification

Credential-free local verification is allowed only on the Product-Owner-approved non-GitHub local environment.

If the approved local runner is available, run exactly:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

Use repository fake/sanitized fixtures only. No real provider/network/credential access.

If the approved local environment is unavailable, record `NOT_RUN` plus the exact command above. `NOT_RUN != PASS`.

Do not run a full Gate C qualification in this task. A broker-suite PASS cannot replace E7-077 FAIL and cannot be combined with the 13 historical PASS suites.

## Safety / release interpretation

Throughout this task:

```text
E7-077 credential-free requalification = FAIL / PRESERVED
Gate C = BLOCKED
production read-only re-verification = NOT STARTED
SHADOW runtime = NOT STARTED
Gate D / LIVE = BLOCKED / NOT AUTHORIZED
```

Forbidden:

- production source changes;
- provider/public/private real requests;
- real credentials/secrets;
- order submit/place/cancel/amend/close or provider mutation;
- leverage/account/position-mode mutation;
- transfer/deposit/withdrawal/capital movement;
- Demo verification;
- PAPER/SHADOW runtime start;
- Gate D/LIVE/capital exposure;
- GitHub Actions/CI/hosted/GitHub-triggered compute;
- full qualification/requalification;
- unrelated cleanup.

## Acceptance

### DONE

- only the stale E4 broker regression expectation is aligned with accepted zero-balance semantics;
- wrong-margin and fill-checkpoint negative safety checks remain intact;
- production code is unchanged;
- local broker verification is PASS or explicitly `NOT_RUN` without misclassification;
- evidence and E4 STATUS are committed/pushed to the target branch;
- Gate C remains BLOCKED pending PM review and a later new full E7 credential-free requalification.

### BLOCKED

Stop if resolving the conflict requires production behavior, shared contract, E5/E6/E7 semantics, or broader test changes beyond the identified stale assertion.

## Completion

Read latest `main`, verify wake task ID `E4-20260826-022`, execute only this TASK, update `coordination/E4/STATUS.md`, commit/push required work to the target branch, and stop on DONE, PARTIAL, or BLOCKED. Do not self-start another task.