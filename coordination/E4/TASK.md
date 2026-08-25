# E4 Current Task

- task_id: `E4-20260825-020`
- issued_at: `2026-08-25T22:54:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-gate-c-zero-balance-normalization-20260825`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate C baseline, accepted E4 Shadow reader PR #78 and runtime-balance handoff PR #79, accepted E7 zero-funds provider-semantics decision PR #87 merge `6c4523778949998687c1f8ac6866b9bde223a2cf`, Product Owner Gate C / SHADOW-only authorization

## Objective

Implement only the minimal E4-owned OKX production Shadow balance normalization accepted by E7 for the zero-funds dedicated sub-account case.

The accepted provider-specific rule applies only to the existing exact authenticated read-only request:

```text
GET /api/v5/account/balance?ccy=USDT
```

For a successful, otherwise-valid response whose account-balance `details` sequence is exactly empty, normalize the runtime-only available USDT balance to:

```text
usdt_balance_known        = true
runtime_available_balance = Decimal("0")
```

This is not a general `missing => zero` fallback and is not permission to trade.

## Required behavior

1. Change only the provider-local balance parsing/normalization needed for the exact accepted case.
2. Preserve the existing successful one-USDT-detail behavior unchanged, including valid explicit zero and positive finite non-negative `availBal` values.
3. Preserve fail-closed behavior for every non-authorized shape, including:
   - provider error / non-success response;
   - missing or malformed `data` envelope;
   - wrong number/type of account objects;
   - missing or non-sequence `details`;
   - non-empty `details` with no USDT item / wrong-currency item;
   - duplicate USDT details;
   - malformed, missing, negative, NaN, Infinity, or otherwise invalid `availBal`;
   - any path where the accepted exact `ccy=USDT` request identity is not established by the existing reader;
   - any unrelated account/position/order/fill/provider contradiction.
4. Do not widen the private endpoint allowlist or authenticated HTTP method surface. GET-only/default-deny remains unchanged.
5. Preserve all accepted Shadow safety boundaries:
   - no `OKXDemoAdapter` dependency;
   - no submit/cancel/amend/mutation capability on the Shadow reader;
   - no exact balance in durable/public evidence or repr/log output;
   - credentials remain runtime-only/redacted;
   - provider permission must remain exactly `read_only`;
   - account/position/order/fill failures remain fail closed.
6. Do not change E5 risk semantics, E6 persistence, E7 composition/contracts, or release-gate semantics.

## Tests

Add/update only E4-owned broker tests necessary to prove the rule. At minimum define coverage for:

- exact USDT balance response + valid envelope + `details=[]` -> known runtime `Decimal("0")`;
- one USDT detail with `availBal="0"` -> existing known zero behavior unchanged;
- one valid positive USDT detail -> existing value preserved exactly;
- wrong-currency detail -> fail closed, not zero;
- duplicate USDT details -> fail closed;
- missing/non-sequence `details` -> fail closed;
- malformed/negative/non-finite `availBal` -> fail closed;
- provider error/malformed account envelope -> fail closed;
- result repr/public sanitized observation does not expose exact runtime balance;
- exact private GET allowlist and no-submit/no-mutation capability graph remain unchanged.

Do not weaken existing fail-closed tests merely to make the new case pass.

## Executable verification

Product Owner authorizes approved-local, non-GitHub, **credential-free** verification for this bounded E4 change only.

If the approved local runner is available, run:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

Use only fake/sanitized fixtures. Do not use real provider credentials or provider/private network access.

If the approved local environment is unavailable, record `NOT_RUN` with the exact command above. `NOT_RUN != PASS`.

## Release / verification interpretation

Even if E4-owned tests PASS:

```text
Gate C = BLOCKED
credential-free full Gate C evidence for the new source revision = NOT YET QUALIFIED
production read-only Gate C evidence after this code change       = NOT YET RE-VERIFIED
SHADOW runtime                                                    = NOT STARTED
Gate D / LIVE                                                     = BLOCKED / NOT AUTHORIZED
```

Do not start or request E7 qualification/requalification, production credential-dependent verification, Demo verification, PAPER/SHADOW runtime, Gate D, or LIVE in this task. PM will review the implementation first and issue any later exact-revision verification separately.

## Writable scope

Only E4-owned paths needed for this bounded change:

- `src/brokers/okx_shadow.py`;
- `tests/brokers/test_okx_shadow.py` or directly related E4-owned broker test files;
- bounded E4 docs/status/handoff;
- `coordination/E4/STATUS.md`.

Forbidden:

- E1-E3/E5-E7 production/tests/TASK/STATUS;
- shared contracts/ADRs;
- storage/migrations;
- risk-policy changes;
- provider/network harness expansion;
- real credentials/secrets/provider responses;
- provider/private real requests;
- order place/cancel/amend/close or any provider mutation;
- deposit/transfer/withdrawal/capital movement;
- PAPER/SHADOW runtime start;
- Gate D/LIVE/capital exposure;
- GitHub Actions/CI/hosted/GitHub-triggered compute;
- unrelated cleanup.

## Acceptance

### DONE

- the exact empty-`details` zero-funds normalization is implemented within E4 ownership;
- all other malformed/contradictory shapes remain fail closed;
- endpoint/method/no-submit/redaction boundaries are unchanged;
- E4-owned regression definitions cover the accepted and rejected shapes;
- local verification is PASS or explicitly `NOT_RUN` without misclassification;
- required code/tests/evidence are committed/pushed to the target branch and E4 STATUS is terminal.

### BLOCKED

Stop if implementing the accepted rule requires changing a shared contract, E5/E6/E7 behavior, provider allowlist, or any broader architecture. Persist exact evidence and do not broaden scope.

## Completion

Read latest `main`, verify wake task ID `E4-20260825-020`, execute only this TASK, update `coordination/E4/STATUS.md`, commit/push required work to the target branch, and stop on DONE, PARTIAL, or BLOCKED. Do not self-start another task.