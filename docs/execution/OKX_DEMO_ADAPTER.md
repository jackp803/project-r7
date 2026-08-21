# E4 OKX Demo Adapter — Bounded Source Layer

Status: static/source construction for `E4-20260821-008`.

This layer is Demo-first and fail-closed. It provides deterministic OKX V5 request construction, authentication/signing, prerequisite read models, MARKET request materialization, response parsing, and ambiguity reconciliation through an injected transport. It does **not** authorize or perform real-money trading, and no provider request was executed as part of this task.

## Official OKX V5 references rechecked

Rechecked on 2026-08-21:

- `https://www.okx.com/docs-v5/en/`
- REST authentication section
- Demo Trading request requirements
- `GET /api/v5/public/instruments`
- `GET /api/v5/account/config`
- `GET /api/v5/account/positions`
- `POST /api/v5/trade/order`
- `GET /api/v5/trade/order`
- `GET /api/v5/trade/orders-pending`
- `GET /api/v5/trade/fills`

Provider facts relied on by this source layer:

- private REST authentication uses `OK-ACCESS-KEY`, `OK-ACCESS-SIGN`, `OK-ACCESS-TIMESTAMP`, and `OK-ACCESS-PASSPHRASE`;
- REST signature prehash is `timestamp + method + requestPath + body`, signed with HMAC-SHA256 using the API secret and Base64-encoded;
- GET query parameters are part of `requestPath` for signing;
- Demo authenticated requests require `x-simulated-trading: 1`;
- `clOrdId` is case-sensitive alphanumeric, maximum 32 characters, and uniqueness is required among pending orders rather than assumed across all history;
- `GET /api/v5/account/config` reports account level (`acctLv`) and position mode (`posMode`);
- SWAP `posSide` mapping depends on configured net vs long/short position mode;
- derivative `sz` is provider contract quantity, not canonical BTC;
- order states include `live`, `partially_filled`, `filled`, and `canceled`/`mmp_canceled`;
- instrument metadata may include upcoming changes in `upcChg` with `param`, `newValue`, and `effTime`.

## Environment guard

The bounded adapter is structurally Demo-only:

```text
environment = demo
REST base   = https://openapi.okx.com
header      = x-simulated-trading: 1
```

`OKXDemoAdapterConfig` rejects production/live mode and rejects an alternate REST base URL. There is no convenience fallback to production.

## Runtime-only credentials

`OKXCredentials` accepts API key, secret, and passphrase only through runtime injection. No credential loader persists them to Git. Its representation is redacted, and request representations expose header names rather than header values.

No real credentials, live `.env` values, tokens, or provider secrets are committed.

## Transport boundary

`OKXTransport` is a Protocol/injected seam. No concrete HTTP/network transport is implemented in this task.

This allows local approved tests to supply a fake transport without contacting OKX. GitHub stores source/test definitions only; GitHub infrastructure must never execute these provider flows.

## Private endpoint allowlist

The source layer materializes only the bounded execution/reconciliation paths:

```text
POST /api/v5/trade/order
GET  /api/v5/trade/order
GET  /api/v5/trade/orders-pending
GET  /api/v5/account/positions
GET  /api/v5/trade/fills
GET  /api/v5/account/config
```

Public metadata uses:

```text
GET /api/v5/public/instruments?instType=SWAP&instId=BTC-USDT-SWAP
```

There is no withdrawal, deposit, funding transfer, internal transfer, sub-account capital movement, Demo balance adjustment, position-mode setter, leverage setter, or account-mode mutation method.

## MARKET entry mapping

Only the already-approved canonical path is accepted:

```text
canonical symbol = BTC_USDT_PERP
provider instId  = BTC-USDT-SWAP
tdMode           = isolated
OrderRequest BUY -> side=buy
OrderRequest SELL -> side=sell
order type       = market
```

`posSide` is mechanical from explicit configured position mode:

```text
net_mode        -> net
long_short_mode + BUY  -> long
long_short_mode + SELL -> short
```

The adapter does not mutate the OKX position mode to make a request work.

Provider `sz` is taken **only** from the accepted `OKXEntrySizingAudit`. Canonical BTC `OrderRequest.quantity` is never copied directly to `sz`.

No `limit_price`, stop/trigger price, TIF, or executable price is manufactured for this MARKET profile.

## Provider client-order identity

Internal E4 `client_order_id` remains the canonical idempotency identity. The provider identifier is deterministic:

```text
clOrdId = "R7" + first 30 hex characters of SHA-256(internal client_order_id)
```

This is stable, alphanumeric, and <=32 characters. `OKXClientOrderIdentity` retains both internal and provider IDs for traceability.

Historical provider uniqueness is deliberately not assumed. Reconciliation therefore scopes order lookup using current `instId` plus provider `clOrdId` and still validates returned provider identities/state.

## Account / position prerequisites

Before materializing new Demo exposure the caller must supply provider-read facts that match explicit adapter configuration:

- expected `acctLv`;
- expected `posMode` (`net_mode` or `long_short_mode`);
- target instrument position truth;
- target pending-order truth.

The bounded new-entry flow fails closed if:

- account level is not the explicitly configured level;
- position mode differs from configuration;
- non-zero provider exposure already exists for the target instrument;
- observed position margin mode is not isolated;
- pending target orders exist.

This task validates configuration; it never calls account/position/leverage setters.

## Metadata freshness hardening

Finding `E4-OKX-FRESHNESS-HARDEN-001` is addressed by `okx-instrument-metadata-freshness-v0.2`.

The older 300-second limit remains only a general cache/sizing ceiling. It is not submit permission.

At order materialization:

```text
provider metadata observation age <= 5 seconds
```

`upcChg` is parsed. Unknown scheduled-change parameters fail closed. `minSz` or `maxMktSz` effective inside a 60-second submit guard blocks materialization. Already-effective scheduled changes remaining in the snapshot also block. A scheduled `tickSz` change is retained for audit but does not manufacture/block a MARKET price under the current profile.

The 5-second and 60-second boundaries are E4 safety policy, not claims about provider stability.

## Authentication and canonical request serialization

Private request construction is deterministic:

1. build exact request path, including sorted GET query parameters;
2. serialize POST JSON compactly and deterministically;
3. calculate prehash `timestamp + METHOD + requestPath + body`;
4. HMAC-SHA256 with runtime secret;
5. Base64-encode signature;
6. add the four OKX access headers plus `x-simulated-trading: 1`.

No secrets are placed in a persisted request/audit object.

## Acknowledgement vs execution truth

A successful `POST /trade/order` acknowledgement is mapped only to `OrderStatus.PENDING` with `filled_quantity=0`. It is not interpreted as a fill.

Explicit per-row provider rejection maps to `REJECTED`. Missing IDs, malformed acknowledgement, unknown acknowledgement shape, or inconsistent identity maps to `RECONCILIATION_REQUIRED`.

## Provider order / fill normalization

Order lookup maps known current provider states to existing E4 states:

```text
live             -> OPEN
partially_filled -> PARTIALLY_FILLED
filled           -> FILLED
canceled         -> CANCELED
mmp_canceled     -> CANCELED
unknown          -> RECONCILIATION_REQUIRED
```

Provider requested/fill contract counts are validated against the materialized provider size. Provider fills are normalized back to canonical BTC using the accepted sizing conversion while preserving provider `ordId`/`tradeId` identity. Cumulative provider fills greater than materialized `sz`, provider order-size contradiction, missing fill identity, or unknown order state fails closed.

## Ambiguous submit and retry

Timeout or connection break while submitting produces `RECONCILIATION_REQUIRED`. A repeated ordinary `submit_entry` for the same provider client ID returns the saved ambiguous result and does not issue another transport send.

The explicit reconciliation sequence is:

```text
GET order by clOrdId
GET target positions
GET fills
GET pending orders
reconcile provider truth
```

Retry is denied if any matching order, fill, non-zero exposure, or pending order exists.

### Explicit order-absence limitation

The current global official documentation recheck did not provide a sufficiently stable, task-authoritative error-code table from which this implementation can safely hard-code a particular `GET /trade/order` error as definitive order absence.

Therefore `order_not_found_codes` is explicit adapter configuration and defaults to the empty set. With the default configuration, a non-success order lookup **never** proves absence and cannot unlock retry. An exact code may be configured only when a deployment/local integration step has current official provider authority for that code.

This is intentionally stricter than guessing from historical examples or third-party libraries.

## Verification

Executable verification remains:

```text
NOT_RUN
```

No Product Owner-approved local runtime was used in this source-construction session.

Required local commands from repository root:

```text
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

No GitHub Actions, hosted runner, GitHub-triggered runner, or provider request was used.

## Release / live impact

This source does not advance PAPER, Demo readiness, SHADOW, or LIVE gates. It contains no real-money mode and no production fallback. Demo/private source construction is not permission to execute a Demo order until a separately approved local validation stage exists.
