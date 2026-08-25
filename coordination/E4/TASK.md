# E4 Current Task

- task_id: `E4-20260825-017`
- issued_at: `2026-08-25T12:10:00+08:00`
- state: `ACTIVE`
- target_branch: `agent/e4-gate-c-shadow-reader-20260825`
- authority: `agents/E4_EXECUTION.md`, `agents/README.md`, `contracts-v0.1`, accepted Gate C baseline PR #75 merge `c158c8ca4fd01fa9314dd2e7a1a9c0c0d2935624`, Product Owner Gate C / SHADOW-only authorization

## Objective

Close only the E4 Phase-1 Gate C gap from `status/e7/GATE_C_READINESS_BASELINE_20260825.md`: construct a dedicated OKX production **read-only Shadow provider surface** whose dependency graph cannot submit orders or mutate provider/account state even when valid credentials later exist.

The existing submit-capable `OKXDemoAdapter` remains separate and must not be reused as the Gate C Shadow runtime dependency.

## Required architecture

Implement an E4-owned read-only provider component (name may follow existing conventions) with these hard properties:

1. Provider = OKX API V5; provider instrument = `BTC-USDT-SWAP`.
2. Authenticated transport is default-deny and permits only HTTP `GET` to the exact Gate C allowlist.
3. The Shadow-facing object exposes no `submit`, `place`, `cancel`, `amend`, leverage/mode mutation, transfer, withdrawal/deposit, or generic arbitrary-request method.
4. Valid credentials must not change the reachable method/capability graph.
5. No `x-simulated-trading: 1` header is used for production read-only Shadow.
6. Query parameters are included in the signed request path; GET has no request body; current OKX V5 HMAC/Base64 signing semantics are preserved.
7. Before a private-read batch, provider time is checked. Gate C policy requires absolute local/provider clock skew `<= 5 seconds`; otherwise fail closed before private account reads.
8. `GET /api/v5/account/config` permission must be validated as exactly `read_only` before other private Gate C evidence is accepted. Trade or Withdraw permission is a hard abort.
9. Regional REST hostname is explicit configuration supplied/confirmed by the local operator later. Unknown/mismatched domain must fail closed; do not guess the operator's account region.
10. Produce normalized, timestamped, sanitized E4 observations sufficient for later E5/E6 consumption without exposing secrets or durable sensitive identifiers.

## Exact private GET allowlist

Only these authenticated paths are allowed for Gate C V0.1:

```text
GET /api/v5/account/config
GET /api/v5/account/balance?ccy=USDT
GET /api/v5/account/positions?instId=BTC-USDT-SWAP
GET /api/v5/account/leverage-info?instId=BTC-USDT-SWAP&mgnMode=isolated
GET /api/v5/trade/orders-pending?instType=SWAP&instId=BTC-USDT-SWAP
GET /api/v5/trade/fills?instType=SWAP&instId=BTC-USDT-SWAP
```

Public provider time may use:

```text
GET /api/v5/public/time
```

Everything else is denied before transport. Private WebSocket is disabled for Gate C V0.1.

## Observation / fail-closed requirements

The read-only batch/projection must make it possible to determine, in sanitized normalized form:

- provider/domain identity;
- observation timestamps and clock-skew status;
- permission category = `read_only` only;
- account/position-mode/config known-status without raw UID/main UID/API label/bound-IP persistence;
- USDT balance known-status without persisting exact balance in public evidence;
- BTC-USDT-SWAP position known/zero-or-unexpected-exposure status;
- isolated leverage/margin prerequisite known-status;
- pending-order count/status;
- recent-fill checkpoint/new-unreconciled-activity status without exposing durable provider IDs;
- provider/auth/parse failures as explicit unknown/degraded outcomes.

Unexpected non-zero position, pending order, new/unreconciled fill, permission mismatch, malformed/missing response, auth/signature/provider failure, domain uncertainty, or clock skew must fail closed. Do not fabricate exchange truth.

## Tests

Add/update E4-owned unit tests using injected fake transports/sanitized fixtures proving at minimum:

- exact signing/path behavior for allowed GETs;
- clock skew `<=5s` accepted and `>5s` rejected before private batch;
- permission exactly `read_only` required;
- Trade/Withdraw or ambiguous permission aborts;
- every allowlisted path works through fake transport;
- any non-GET or non-allowlisted private path is rejected before transport;
- no submit/cancel/amend/mutation method is reachable from the Shadow reader;
- credentials do not activate a hidden submit branch;
- production Shadow requests never add Demo header;
- redaction: exceptions/loggable evidence cannot contain key/secret/passphrase/signature/raw UID/API label/bound IP/exact balances/provider order/fill IDs;
- malformed/contradictory/unexpected exposure/order/fill responses fail closed.

Do not perform a real provider/private network request in this implementation task.

## Executable verification

Product Owner authorizes approved-local, non-GitHub, **credential-free fake-based** verification for this task. If available, run only relevant E4 broker/execution tests, for example:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
```

No external provider network request or real credential is authorized in this task. If approved-local execution is unavailable, record `NOT_RUN` with exact commands. `NOT_RUN != PASS`.

## Writable scope

Only E4-owned paths necessary for this task:

- `src/brokers/**`;
- `src/execution/**` only for read-only provider composition/helper boundaries genuinely owned by E4;
- `tests/brokers/**`;
- `tests/execution/**`;
- `docs/execution/**`;
- `coordination/E4/STATUS.md`.

Forbidden:

- E1/E2/E3/E5/E6/E7 production/tests;
- shared contract/ADR changes without escalation;
- provider/private real requests in this task;
- real credentials/secrets/local secret files;
- order submission, simulated or real;
- cancel/amend/close/leverage/mode/account mutation;
- transfer/deposit/withdrawal/capital movement;
- generic authenticated arbitrary-request surface exposed to Shadow;
- GitHub Actions/CI/hosted/GitHub-triggered compute;
- PAPER/SHADOW runtime start;
- LIVE/capital exposure;
- unrelated cleanup.

## Acceptance

### DONE

- dedicated production read-only Shadow provider surface exists and is structurally non-submit-capable;
- exact allowlist/default-deny/permission/clock/domain/redaction/fail-closed semantics have tests;
- existing Demo submit-capable adapter remains separate;
- no real provider/private execution or credential use occurred;
- local evidence is PASS or explicitly `NOT_RUN` without misclassification;
- commit/push to target branch and terminal E4 STATUS.

### BLOCKED

If this cannot be built safely without changing a shared contract/architecture baseline, stop with exact evidence for E7. If only operator domain/credential setup is missing, that does not block this credential-free construction task; record it as a later prerequisite.

## Completion

Execute only this TASK, update `coordination/E4/STATUS.md`, commit/push required work to the target branch, and stop. Do not self-start provider verification or the next Gate C task.