# E4 Status

- task_id: `E4-20260825-017`
- agent: `E4`
- state: `DONE`
- branch: `agent/e4-gate-c-shadow-reader-20260825`
- baseline_main_sha: `952b57e45f673a0af16c8f3b23640996c88e4d1c`
- head_sha: `a6cee881c427a4adbc3b13a6b3e223caaafbd0ca` (source/tests/docs HEAD immediately before this terminal STATUS-only commit)
- summary: `Implemented only the E4 Phase-1 Gate C production read-only OKX Shadow provider surface. OKXShadowProviderReader is structurally separate from OKXDemoAdapter, exposes only observe(...), signs only exact allowlisted private GETs, has no Demo header or submit/cancel/amend/mutation/generic-request/WebSocket surface, enforces operator-confirmed HTTPS OKX domain identity, <=5s provider clock skew, exact read_only permission before other private evidence, dedicated sub-account/account-mode expectations, sanitized normalized observations, unexpected exposure/order/fill fail-closed behavior, and a provider-ID-free recent-fill checkpoint. No concrete network transport, real credential, provider request, order submission, mutation, SHADOW runtime start, or LIVE activity occurred.`
- files_changed: `src/brokers/okx_shadow.py; tests/brokers/test_okx_shadow.py; docs/execution/OKX_GATE_C_SHADOW_READER.md; coordination/E4/STATUS.md`
- contracts_changed: `NO`
- local_verification: `NOT_RUN`
- not_run: `Product Owner authorizes credential-free fake-based approved-local verification for this task, but this E4 conversation has no available approved local runner action. Required later Windows PowerShell commands from repository root: $env:PYTHONPATH="src" ; python -m unittest discover -s tests/brokers -p "test_*.py" -v ; python -m unittest discover -s tests/execution -p "test_*.py" -v`
- blockers: `NONE for bounded construction/static completion. Operator regional-domain confirmation and real read-only credential setup remain later credential-dependent prerequisites and do not block this task.`
- gate_effect: `No Gate C/SHADOW_READY PASS is claimed. No SHADOW runtime was started. LIVE remains outside this task.`

## Wake / authority verification

Wake message task ID:

```text
E4-20260825-017
```

Latest `main:coordination/E4/TASK.md` matched exactly before any implementation work began.

Authoritative files read first:

- `README.md`
- `agents/README.md`
- `agents/E4_EXECUTION.md`
- `coordination/E4/TASK.md`

Only E4's TASK was read; no other Agent TASK was read or executed.

## Baseline / branch

At task start:

```text
main = 952b57e45f673a0af16c8f3b23640996c88e4d1c
target branch = did not yet exist
```

The target branch was created from that exact `main` revision. Latest `main` remained the same before terminal status. No merge, rebase, force update, history rewrite, GitHub Actions, CI, hosted runner, or GitHub-triggered compute was used.

## Read-only Shadow architecture

Added:

```text
src/brokers/okx_shadow.py
```

Provider identity is fixed:

```text
provider = OKX
api_version = V5
canonical_symbol = BTC_USDT_PERP
provider_instrument = BTC-USDT-SWAP
environment = production_read_only_shadow
```

The component does not import or instantiate `OKXDemoAdapter`. The Shadow-facing class is:

```text
OKXShadowProviderReader
```

Its public operational callable surface is only:

```text
observe(...)
```

It has no public submit/place/cancel/amend/close/leverage-mode/account-mode/transfer/deposit/withdraw/retry/materialization/generic-request/send/WebSocket method. Credential values are constructor data only and cannot activate an alternate public capability graph.

No concrete network transport is provided by this implementation; transport remains an injected seam for later separately authorized local use.

## Domain identity

`OKXShadowReaderConfig` requires both:

```text
rest_base_url
operator_confirmed_rest_base_url
```

Both must normalize to the same HTTPS OKX hostname. Non-HTTPS, non-OKX, userinfo/port/path/query/fragment-bearing, or mismatched values fail before transport.

E4 does not infer the user's account registration region. Correct regional hostname confirmation remains a later local-operator prerequisite.

## Exact private default-deny allowlist

Authenticated request construction accepts only method `GET` and only the exact path/query material below:

```text
GET /api/v5/account/config
GET /api/v5/account/balance?ccy=USDT
GET /api/v5/account/positions?instId=BTC-USDT-SWAP
GET /api/v5/account/leverage-info?instId=BTC-USDT-SWAP&mgnMode=isolated
GET /api/v5/trade/orders-pending?instType=SWAP&instId=BTC-USDT-SWAP
GET /api/v5/trade/fills?instType=SWAP&instId=BTC-USDT-SWAP
```

The implementation canonicalizes query ordering before signing. Extra/missing/changed query keys or any other private path are denied before transport. Any method other than GET is denied before transport.

Public clock check uses only:

```text
GET /api/v5/public/time
```

Private WebSocket is not implemented.

## Signing / Demo separation

Private read signing is independently implemented with the accepted OKX V5 rule:

```text
requestPath includes query
GET body = empty
prehash = timestamp + "GET" + requestPath
signature = Base64(HMAC-SHA256(secret, prehash))
```

Private request headers contain required auth/read headers only. Production Shadow requests never add:

```text
x-simulated-trading: 1
```

Credential and prepared-request repr values are redacted. Raw transport exception detail is deliberately discarded rather than chained into loggable Shadow evidence.

## Clock / permission gates

Before any private read:

```text
GET /api/v5/public/time
absolute(local - provider) <= 5,000 ms
```

Skew above 5 seconds returns `DEGRADED / CLOCK_SKEW_EXCEEDED` with `private_get_count=0`.

The first private request is always account config. It must establish exactly:

```text
perm = read_only
acctLv = configured expected level (V0.1 = 2)
posMode = configured expected net_mode | long_short_mode
uid != mainUid
```

Trade, Withdraw, mixed, missing, or ambiguous permission fails closed before balance/position/leverage/order/fill reads. Raw UID/main UID/API label/bound-IP values are never copied to normalized observation.

## Sanitized observation

`OKXShadowObservation` carries only bounded E4 facts:

- provider/API/environment/hostname/instrument;
- local/provider timestamps and clock-skew status;
- permission category;
- account-config known status, account level, position mode and sub-account classification;
- USDT balance known status without exact balance;
- position known status and unexpected-exposure boolean;
- isolated leverage prerequisite known/OK status;
- pending-order count without IDs;
- recent-fill window count, sanitized checkpoint and new-unreconciled count without provider IDs;
- private GET count;
- `HEALTHY | DEGRADED` plus sanitized reason codes.

It contains no raw API key/secret/passphrase/signature, UID/main UID, API label, bound IP, exact USDT balance, provider order ID, provider fill ID, or full provider response body.

## Fail-closed batch behavior

Read order is:

```text
public time
-> account config/permission
-> USDT balance
-> BTC-USDT-SWAP positions
-> isolated leverage info
-> pending orders
-> recent fills/checkpoint
```

The first blocking provider/transport/parse/safety condition stops the batch and returns `DEGRADED` sanitized evidence.

Explicit blockers include:

- clock skew above policy;
- permission not exactly read_only;
- account-level/position-mode/sub-account mismatch;
- malformed/missing/provider-error response;
- unknown/malformed USDT balance;
- non-isolated/malformed position or leverage fact;
- unexpected non-zero BTC-USDT-SWAP exposure;
- unexpected pending order;
- new/unreconciled recent fill;
- fill-checkpoint regression;
- transport/provider failure.

No exchange truth is fabricated.

## Recent-fill checkpoint

Provider order/fill IDs are intentionally excluded. V0.1 checkpoint material is only:

```text
latest_fill_timestamp_ms
records_at_latest_timestamp
```

No prior checkpoint + any returned fill is new/unreconciled activity and fails closed. A lower timestamp/count than the prior checkpoint fails closed as regression. An already-reconciled identical timestamp/count window can remain healthy.

## Test definitions

Added credential-free fake-transport definitions in:

```text
tests/brokers/test_okx_shadow.py
```

Definitions cover:

- exact query-inclusive HMAC/Base64 signing;
- empty GET body;
- <=5s clock acceptance and >5s pre-private abort;
- exact read_only permission and Trade/Withdraw/mixed/ambiguous abort;
- all six allowlisted private GETs;
- non-GET/nonallowlisted denial before transport;
- no submit/cancel/amend/mutation/generic-request/WebSocket public capability;
- credentials do not alter reachable public capability graph;
- production requests never carry Demo header;
- explicit/mismatched domain rejection;
- credential/signature/account/balance/provider-ID redaction;
- raw transport exception suppression;
- unexpected exposure/pending-order/new-fill fail closed;
- malformed balance, margin mismatch and checkpoint regression fail closed;
- already-reconciled fill checkpoint handling;
- dedicated sub-account and position-mode mismatch rejection.

Definitions only; not executed by this E4 conversation.

## Verification / execution state

```text
local_verification = NOT_RUN
GitHub Actions / CI = NOT_USED
GitHub-hosted / GitHub-triggered runner = NOT_USED
provider/private real network request = NOT_PERFORMED
real credentials = NOT_USED
order submission = NOT_PERFORMED
provider/account mutation = NOT_PERFORMED
PAPER/SHADOW runtime = NOT_STARTED
LIVE/capital exposure = NOT_AUTHORIZED_OR_USED
```

Required later approved-local commands:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
```

`NOT_RUN != PASS`.

## Completion boundary

The bounded E4 Phase-1 construction is complete. E4 stops here and does not self-start credential-dependent provider verification, SHADOW runtime, E5/E6/E7 integration work, another Gate C task, Gate D, LIVE, or capital exposure.
