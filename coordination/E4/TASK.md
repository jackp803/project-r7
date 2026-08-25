# E4 Current Task

- task_id: `E4-20260825-018`
- issued_at: `2026-08-25T13:13:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-gate-c-shadow-balance-handoff-20260825`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate C baseline PR #75, accepted E4 read-only Shadow boundary PR #78 merge `562c4c324129557e5d565b1a37deb49d2c007429`, Product Owner Gate C / SHADOW-only authorization

## Objective

Close one bounded Phase-1 handoff gap discovered during PM review before E5 may start Gate C risk-context derivation.

The accepted E4 Shadow reader correctly performs `GET /api/v5/account/balance?ccy=USDT` and validates `availBal`, but the current normalized result retains only `usdt_balance_known=True` and discards the exact runtime Decimal balance. The existing E5 `RiskContext.available_balance` requires a real known Decimal value for sizing/insufficient-balance checks. E5 must not be forced to re-trust an unrelated caller-supplied account balance.

Add a **runtime-only, non-durable exact USDT available-balance handoff** from the already-accepted read-only Shadow batch to later E5 consumption, while preserving the public/durable redaction boundary.

## Required behavior

1. Parse the accepted USDT `availBal` as finite non-negative `Decimal` and retain it in the in-memory Shadow read result when and only when balance truth is known.
2. Bind that exact balance to the same observation batch/account-config/clock/provider boundary as the existing `OKXShadowObservation`; do not create an independently caller-assertable balance flag/value pair.
3. Preserve one read-only `observe(...)` network batch; do not add provider endpoints, additional provider calls, WebSocket, submit, cancel, amend, leverage/mode mutation, transfer, deposit, withdrawal, or generic request authority.
4. The exact balance is **runtime-sensitive data, not durable/public evidence**:
   - it must not appear in `repr`, exception messages, logs, docs examples with real values, STATUS/handoff evidence, checkpoint payloads, callback payloads, or any serializer intended for durable/public evidence;
   - existing E6 sanitized Shadow checkpoint semantics must continue to persist only `balance_known`, never the exact balance;
   - no credential/provider identifier redaction rule may be weakened.
5. Healthy observation must expose the runtime exact balance to a later E5 pure derivation layer without E5 parsing provider payloads or using credentials/network.
6. Any missing/malformed/negative/non-finite balance remains fail closed and must not expose a usable runtime balance.
7. Preserve all accepted PR #78 invariants: exact GET allowlist/default deny, production/no-Demo header, operator-confirmed domain, <=5s clock check, exact `read_only` permission, dedicated sub-account/account/position-mode checks, unexpected exposure/order/fill fail closed, and structurally unreachable submit/mutation surface.
8. No shared contract/ADR change. If a safe runtime-only handoff cannot be represented without changing shared architecture, stop `BLOCKED` with exact evidence for E7.

Implementation shape is E4-owned. Prefer the smallest representation that keeps `observe(...)` as the single Shadow network operation and makes the distinction between sanitized durable observation fields and runtime-sensitive balance unambiguous.

## Tests

Update/add only E4-owned fake-transport tests proving at minimum:

- healthy batch exposes the exact Decimal USDT available balance in memory;
- value is bound to the same observation batch and is absent/unusable on balance failure;
- zero balance is valid known Decimal zero; negative/non-finite/malformed balance fails closed;
- `repr`/loggable/sanitized evidence does not contain the exact balance;
- any durable/public projection used by the E4 handoff excludes the exact balance;
- existing allowlist/no-submit/no-Demo/permission/clock/domain/redaction/fail-closed tests remain semantically unchanged;
- credentials do not change capability graph.

## Executable verification

Product Owner authorizes approved-local, non-GitHub, credential-free fake-based verification for this bounded task. If the approved local runner is available, run only:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
```

No real provider/private request or credential is authorized. If approved-local execution is unavailable, record `NOT_RUN` with the exact commands. `NOT_RUN != PASS`.

## Writable scope

Only:

- `src/brokers/okx_shadow.py` and narrowly required E4 exports;
- `tests/brokers/test_okx_shadow.py` and narrowly required E4 tests;
- `docs/execution/OKX_GATE_C_SHADOW_READER.md` if needed;
- E4 status/handoff artifacts;
- `coordination/E4/STATUS.md`.

Forbidden:

- E1/E2/E3/E5/E6/E7 production/tests;
- contracts/ADR changes;
- real credentials/secrets;
- provider/private real requests;
- additional provider endpoints;
- order submission or any provider/account mutation;
- PAPER/SHADOW runtime start;
- LIVE/capital exposure;
- GitHub Actions/CI/hosted/GitHub-triggered compute;
- unrelated cleanup.

## Acceptance

### DONE

- exact runtime Decimal available balance can flow from the accepted E4 read-only batch to later E5 derivation without caller assertion;
- exact balance remains non-durable/non-loggable/non-public;
- PR #78 safety invariants are preserved;
- tests define the behavior;
- local verification is PASS or explicitly `NOT_RUN` without misclassification;
- commit/push to target branch and terminal STATUS.

### BLOCKED

Stop if safe balance handoff requires a shared contract/architecture change. Do not broaden scope.

Execute only this TASK, update `coordination/E4/STATUS.md`, commit/push required work, and stop. Do not self-start E5 or credential-dependent verification.