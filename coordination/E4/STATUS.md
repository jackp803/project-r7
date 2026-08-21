# E4 Status

- task_id: `E4-20260821-008`
- agent: `E4`
- state: `DONE`
- branch: `agent/e4-okx-demo-adapter-20260821`
- head_sha: `b7031c52a38623c528ee9352276793d8110854e0` (implementation + tests/docs + E4->E7 handoff HEAD immediately before this status-only completion commit)
- summary: `Completed the bounded Demo-first OKX V5 adapter source layer: injected transport, runtime-only signing credentials, mandatory Demo header, MARKET/isolated provider request materialization, deterministic legal clOrdId mapping, account/position prerequisite reads and validation, order/pending/position/fill reconciliation reads, fail-closed response normalization, ambiguity-before-retry behavior, and submit-time instrument-metadata freshness hardening. No provider request/test was executed, no real credential was used, production mode is rejected, and no asset-movement/account-mutation surface was added.`
- files_changed: `src/brokers/okx_demo.py; src/brokers/okx_sizing.py; tests/brokers/test_okx_demo_adapter.py; tests/brokers/test_okx_demo_status_mapping.py; tests/brokers/test_okx_sizing.py; docs/execution/OKX_DEMO_ADAPTER.md; docs/execution/OKX_SIZING_POLICY.md; docs/execution/E4_TO_E7_HANDOFF.md; coordination/E4/STATUS.md`
- contracts_changed: `NO`
- local_verification: `NOT_RUN`
- not_run: `No Product Owner-approved local project execution environment was used. Required commands: python -m unittest discover -s tests/execution -p "test_*.py" -v ; python -m unittest discover -s tests/brokers -p "test_*.py" -v`
- blockers: `NONE for bounded static/source completion. Fail-closed integration prerequisite remains: current official recheck did not yield a stable task-authoritative order-not-found error-code table, so order_not_found_codes defaults empty and retry cannot be authorized from a non-success order lookup until an exact current official code is explicitly configured/verified during approved local integration.`
- handoff_path: `docs/execution/E4_TO_E7_HANDOFF.md`
- next_owner: `E7/PM`

## Baseline / branch

- target branch existed from current main and was identical at task start;
- baseline main/branch commit: `fbf22930a185c30ea0f8c600471ba1c83698a29f`;
- no force update, destructive rebase, or old E4 branch rewrite was used.

## Demo-only environment / security guard

Implemented source rules:

```text
environment = demo
REST base   = https://openapi.okx.com
private header x-simulated-trading = 1
```

- non-Demo/production environment is rejected;
- alternate production-style base URL is rejected by this bounded adapter;
- credentials are runtime-injected only and credential/request reprs redact values;
- no real API key/secret/passphrase/token/live .env was committed;
- no withdrawal/deposit/funding/internal transfer/sub-account transfer/balance-adjustment capability exists;
- no account-mode, position-mode, or leverage mutation method exists.

## Authentication / deterministic request construction

Official OKX V5 REST rules rechecked on 2026-08-21 and implemented:

```text
prehash = timestamp + METHOD + requestPath + body
signature = Base64(HMAC-SHA256(secret, prehash))
```

Private request headers include:

- `OK-ACCESS-KEY`
- `OK-ACCESS-SIGN`
- `OK-ACCESS-TIMESTAMP`
- `OK-ACCESS-PASSPHRASE`
- `x-simulated-trading: 1`

GET query parameters are included deterministically in signed `requestPath`. POST JSON is compact/deterministic. No concrete network transport is provided; all provider I/O is through injected `OKXTransport`.

## MARKET / isolated request materialization

Only the accepted path is materialized:

```text
canonical BTC_USDT_PERP -> OKX BTC-USDT-SWAP
tdMode = isolated
BUY  -> buy
SELL -> sell
MARKET -> market
```

Position side mapping requires explicit account position-mode configuration:

```text
net_mode                  -> net
long_short_mode + BUY     -> long
long_short_mode + SELL    -> short
```

Provider `sz` is sourced only from accepted `OKXEntrySizingAudit.provider_requested_contract_quantity`. Canonical `OrderRequest.quantity` remains BTC and is never copied into provider contract `sz`. Effective canonical provider exposure must stay `> 0` and `<=` the E5-approved quantity.

No executable limit/stop/trigger price or TIF is invented.

## Provider client order identity

Current official `clOrdId` constraints are respected by deterministic mapping:

```text
R7 + sha256(E4 client_order_id).hexdigest()[:30]
```

The result is stable, alphanumeric, <=32 chars. Internal and provider IDs remain separate/auditable. Historical global uniqueness is not assumed; current provider docs describe pending-order uniqueness requirements.

## Prerequisite reads / validation

Mode/exposure prerequisites are modeled/read, not repaired:

- `GET /api/v5/account/config`
- `GET /api/v5/account/positions`
- `GET /api/v5/trade/orders-pending`

New bounded entry fails closed when configured `acctLv`/`posMode` mismatch, target exposure is non-zero, observed target margin mode is not isolated, or target pending orders exist.

No `set-position-mode`, `set-leverage`, or account-mode mutation is called/implemented.

## Freshness hardening — E4-OKX-FRESHNESS-HARDEN-001

Resolved statically by policy:

```text
okx-instrument-metadata-freshness-v0.2
```

- existing 300-second value retained only as a general cache/sizing ceiling;
- submit materialization separately requires provider metadata observation age `<= 5 seconds`;
- current official `upcChg` shape (`param`, `newValue`, `effTime`) is parsed;
- unknown scheduled-change parameter -> fail closed;
- scheduled change already effective in snapshot -> fail closed;
- `minSz` / `maxMktSz` change within 60-second guard -> fail closed;
- `tickSz` remains audit metadata and does not manufacture an executable MARKET price.

The 5-second and 60-second values are E4 safety policy, not provider stability guarantees.

## Acknowledgement / order / fill mapping

- successful place-order acknowledgement -> `PENDING`, canonical `filled_quantity=0`; acknowledgement is not fill truth;
- explicit row rejection -> `REJECTED`;
- malformed/unknown/id-mismatched acknowledgement -> `RECONCILIATION_REQUIRED`;
- provider state mapping: `live -> OPEN`, `partially_filled -> PARTIALLY_FILLED`, `filled -> FILLED`, `canceled/mmp_canceled -> CANCELED`;
- unknown provider order state -> `RECONCILIATION_REQUIRED`;
- provider `sz`/`accFillSz` contradictions or overfill -> fail closed;
- provider `fillSz` contracts normalize to canonical BTC shared `Fill.quantity` while provider IDs remain traceable.

## Ambiguous acknowledgement / reconciliation / retry

Timeout or connection break -> `RECONCILIATION_REQUIRED`.

Ordinary repeat submit for the same provider `clOrdId` returns the stored ambiguous result and does not send another request.

Minimum explicit reconciliation sequence:

```text
GET /api/v5/trade/order by clOrdId
GET /api/v5/account/positions
GET /api/v5/trade/fills
GET /api/v5/trade/orders-pending
```

Retry is denied if an order, matching fill, non-zero provider exposure, or matching pending order exists. A non-success order lookup is not assumed to prove absence unless its exact code is explicitly supplied via authoritative integration configuration.

## Current official OKX references rechecked

Rechecked 2026-08-21:

- `https://www.okx.com/docs-v5/en/`
- REST authentication / Demo Trading requirements
- `GET /api/v5/public/instruments`
- `GET /api/v5/account/config`
- `GET /api/v5/account/positions`
- `POST /api/v5/trade/order`
- `GET /api/v5/trade/order`
- `GET /api/v5/trade/orders-pending`
- `GET /api/v5/trade/fills`

## Deterministic local-only test definitions

Added/updated fake-transport definitions for:

- signature/canonical request construction with fake credentials;
- mandatory Demo header and production rejection;
- stable legal `clOrdId`;
- MARKET/isolated payload and `posSide` mappings;
- `sz` sourced from sizing audit only;
- account/position-mode mismatch;
- existing exposure/pending-order rejection;
- submit-time metadata <=5 seconds;
- scheduled change guard / unknown-change fail closed;
- successful acknowledgement not conflated with fill truth;
- timeout -> reconciliation required and no blind ordinary resubmit;
- order + position + fill + pending query-before-retry path;
- partial / filled / canceled / unknown-state mapping;
- contradictory provider response fail closed;
- provider fill normalization to BTC;
- no asset-movement/account-mutation method surface;
- provider effective exposure never exceeds E5-approved canonical BTC.

## Verification / execution policy

- executable verification: `NOT_RUN`
- GitHub Actions / CI / hosted runner: `NOT_USED`
- provider requests: `NOT_SENT`
- project/fake-transport tests: `NOT_RUN`
- no Gate A/B/C/D advancement claimed

Required approved-local commands:

```text
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

## Provider / release status

- OKX Demo adapter source: `IMPLEMENTED / STATIC ONLY`
- concrete network transport: `NOT_IMPLEMENTED`
- real credentials: `NOT USED / NOT COMMITTED`
- actual OKX Demo request/order: `NOT_RUN / NOT SENT`
- production/real-money mode: `REJECTED / NOT IMPLEMENTED`
- automatic account/leverage/mode mutation: `NOT IMPLEMENTED`
- asset movement: `NOT EXPOSED`
- PAPER/SHADOW/LIVE: `NOT ADVANCED`
- shared contracts: `UNCHANGED`

## Completion boundary

This bounded source task is complete. E4 stops here and does not send a Demo order, enable production/live execution, or begin another feature automatically.
