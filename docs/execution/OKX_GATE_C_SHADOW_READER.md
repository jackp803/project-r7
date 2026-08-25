# OKX Gate C Production Read-Only Shadow Reader

## Scope

This document records the E4 Phase-1 Gate C component introduced by task `E4-20260825-017` and the bounded runtime-balance handoff added by `E4-20260825-018`.

The component is intentionally separate from the submit-capable `OKXDemoAdapter`.

```text
OKXShadowProviderReader
= production-provider/private REST read-only observation
= GET-only exact allowlist
= no Demo header
= no submit/cancel/amend/mutation surface
= no concrete network transport in repository
```

It does not start SHADOW runtime, does not submit simulated or real orders, does not mutate provider/account state, and does not authorize LIVE.

## Provider identity

```text
provider = OKX API V5
canonical symbol = BTC_USDT_PERP
provider instrument = BTC-USDT-SWAP
environment = production_read_only_shadow
```

The REST base URL must be explicitly supplied and separately operator-confirmed. The two configured values must normalize to the same HTTPS `*.okx.com` hostname. E4 does not infer the account registration region. Missing, non-OKX, non-HTTPS, path-bearing, or mismatched domain configuration fails before transport.

This construction does not prove that a configured regional hostname is correct for a future real account. That remains a later operator/credential-dependent prerequisite.

## Private allowlist

Authenticated access is default-deny. Only `GET` is accepted and only these exact path/query pairs are admitted:

```text
GET /api/v5/account/config
GET /api/v5/account/balance?ccy=USDT
GET /api/v5/account/positions?instId=BTC-USDT-SWAP
GET /api/v5/account/leverage-info?instId=BTC-USDT-SWAP&mgnMode=isolated
GET /api/v5/trade/orders-pending?instType=SWAP&instId=BTC-USDT-SWAP
GET /api/v5/trade/fills?instType=SWAP&instId=BTC-USDT-SWAP
```

The implementation canonicalizes query ordering before signing. Query keys/values must match the allowlist exactly. Extra, missing, or changed query material is denied.

Public clock verification uses only:

```text
GET /api/v5/public/time
```

Private WebSocket is not implemented.

## Signing

Private GET requests preserve the accepted OKX V5 signing rule:

```text
prehash = timestamp + "GET" + requestPath + ""
signature = Base64(HMAC-SHA256(secret, prehash))
```

`requestPath` includes the canonical query string. GET body text is always empty.

Private headers are limited to the required authentication/read headers:

```text
Accept
OK-ACCESS-KEY
OK-ACCESS-SIGN
OK-ACCESS-TIMESTAMP
OK-ACCESS-PASSPHRASE
```

Production Shadow requests never add:

```text
x-simulated-trading: 1
```

Prepared-request and credential `repr` values redact credential/signature values.

## Clock gate

Before the first private read, the reader obtains OKX provider time and compares it with the injected local UTC clock.

Gate C policy:

```text
absolute(local_time - provider_time) <= 5,000 ms
```

At or below the limit the batch may continue. Above the limit the observation is `DEGRADED / CLOCK_SKEW_EXCEEDED` and private request count remains zero.

## Permission and account boundary

The first private endpoint is always account config.

The response must establish:

```text
perm = read_only
acctLv = configured expected level (V0.1: 2)
posMode = configured expected mode (net_mode | long_short_mode)
uid != mainUid  # dedicated sub-account relationship
```

Any Trade/Withdraw/mixed/ambiguous permission is a hard fail-closed observation. No other private evidence is accepted after a permission mismatch.

Raw `uid`, `mainUid`, API label, and bound-IP values are used only transiently for validation and are never copied into the normalized observation.

## Sanitized normalized observation

`OKXShadowObservation` contains only bounded E4 facts suitable for later governed E5/E6 adaptation:

- provider/API/environment/domain identity;
- local/provider timestamps and clock skew;
- permission category;
- account config known status, account level, position mode, sub-account classification;
- USDT balance known status without exact balance;
- BTC-USDT-SWAP position known status and unexpected-exposure boolean;
- isolated leverage prerequisite known/OK status without leverage mutation;
- pending-order count without order IDs;
- recent-fill window count and sanitized timestamp/count checkpoint without fill/order IDs;
- new-unreconciled-fill count;
- private GET count;
- `HEALTHY | DEGRADED` and stable sanitized reason codes.

No exact balance, raw credential, raw UID/main UID, API label, bound IP, provider order ID, provider fill ID, provider response body, or signature is present in `OKXShadowObservation`.

## Runtime-sensitive USDT balance handoff

The same `observe(...)` batch also returns an `OKXShadowReadResult`. It binds two different data classes of authority without adding another provider read:

```text
OKXShadowReadResult.sanitized_observation
    -> OKXShadowObservation
    -> balance-known boolean only
    -> durable/public-safe projection

OKXShadowReadResult.runtime_available_balance
    -> Decimal | None
    -> exact USDT availBal from the same accepted balance response
    -> runtime-only E4 -> later E5 handoff
```

The exact value is retained only after all of these earlier batch facts have already been established by the same reader invocation:

```text
provider/domain identity
provider clock check <= 5 seconds
account config parsed
permission exactly read_only
dedicated sub-account/account/position-mode checks accepted
USDT balance response parsed as one finite non-negative Decimal
```

A zero Decimal balance is valid known truth. Missing USDT detail, malformed Decimal, negative Decimal, NaN, or infinity leaves `usdt_balance_known=false`, exposes no runtime balance, and terminates the batch fail closed.

The runtime value is deliberately not a field on `OKXShadowObservation`. `OKXShadowReadResult` is a slots-based non-dataclass wrapper with a redacted `repr`; its explicit `sanitized_observation` projection is the object intended for durable/public persistence. The exact runtime balance must not be copied into checkpoints, callback/public evidence payloads, logs, STATUS/handoff evidence, or general-purpose durable serializers.

Later E5 derivation may consume the exact Decimal together with `sanitized_observation`; E5 does not need provider credentials, provider response parsing, or an independently caller-asserted balance value.

## Fail-closed batch order

The production-read batch is intentionally sequential:

```text
public time
-> account config / permission
-> USDT balance known + runtime-only exact Decimal
-> BTC-USDT-SWAP positions
-> isolated leverage info
-> pending orders
-> recent fills / checkpoint
```

The batch returns `DEGRADED` immediately on any provider/transport/parse/safety failure. Later endpoints are not read after the first blocking condition.

Blocking conditions include:

- clock skew above policy;
- permission not exactly `read_only`;
- account-level/position-mode/sub-account mismatch;
- malformed/missing required response;
- unknown/malformed/negative/non-finite USDT balance;
- non-isolated or malformed position/leverage evidence;
- unexpected non-zero BTC-USDT-SWAP exposure;
- unexpected pending order;
- new/unreconciled recent fill;
- recent-fill checkpoint regression;
- transport/provider failure.

Raw transport exception messages are not intended to become normalized evidence; only a stable E4 reason code is returned.

## Recent-fill checkpoint

Gate C V0.1 deliberately does not persist provider order/fill IDs. The E4 checkpoint is therefore limited to:

```text
latest_fill_timestamp_ms
records_at_latest_timestamp
```

It never contains the runtime available balance.

If no prior checkpoint exists, any returned recent fill is treated as new/unreconciled provider activity and the batch fails closed.

If a prior checkpoint exists:

- a lower latest timestamp is a checkpoint regression;
- a lower count at the same latest timestamp is a checkpoint regression;
- records newer than the prior timestamp, or additional records at the same latest timestamp, are new/unreconciled activity;
- an already-reconciled identical timestamp/count window may remain healthy.

This checkpoint is intentionally sanitized and is not a substitute for future durable E6 conflict/reconciliation design.

## Capability graph

The Shadow-facing reader exposes only one operational callable:

```text
observe(...)
```

It does not expose:

```text
submit / submit_entry / place_order
cancel / amend / close_position
set_leverage / set_position_mode / set_account_mode
transfer / deposit / withdraw
retry_entry / prepare_entry
generic request / send
private WebSocket
```

Credentials are constructor data only and do not activate another method graph or hidden submit branch.

The injected transport remains private to the reader. The repository provides no concrete network transport in this task, so this implementation cannot itself perform a real provider request without a separately supplied local transport.

## Verification state

Task `E4-20260825-018` authorizes only approved-local, credential-free fake-based verification. If no approved local runner is available to the E4 conversation, verification remains:

```text
NOT_RUN
```

Required later command from repository root:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests/brokers -p "test_*.py" -v
python -m unittest discover -s tests/execution -p "test_*.py" -v
```

No GitHub Actions/CI/hosted runner, provider/private network request, real credential, order submit, mutation, SHADOW runtime start, or LIVE activity is permitted by this implementation task.
