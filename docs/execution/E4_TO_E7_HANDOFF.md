# E4 -> E7 Handoff — OKX Demo-First Adapter Source Layer

## Handoff

**From:** E4 / Trading Execution & Broker Integration Engineer  
**To:** E7 / Integration Engineer  
**Branch:** `agent/e4-okx-demo-adapter-20260821`  
**Task:** `E4-20260821-008`  
**Date:** 2026-08-21

### 1. Objective

Construct only the bounded Demo-first OKX V5 provider adapter source layer on top of the merged E4 ApprovedTradePlan translation, deterministic sizing, Broker/PaperBroker idempotency, partial-fill, and ambiguity/reconciliation behavior.

This handoff does not authorize provider execution from GitHub, real credentials, real-money mode, account mutation, PAPER/SHADOW/LIVE promotion, or asset movement.

### 2. Baseline / branch

The PM-created target branch was identical to current `main` at task start:

```text
agent/e4-okx-demo-adapter-20260821
baseline main = fbf22930a185c30ea0f8c600471ba1c83698a29f
```

No merge/rebase/force rewrite was required.

### 3. What changed

#### Demo-only transport and authentication boundary

Added `src/brokers/okx_demo.py` with:

- injected `OKXTransport` protocol; no concrete HTTP/network transport;
- runtime-only/redacted `OKXCredentials`;
- deterministic OKX V5 REST HMAC-SHA256/Base64 signing;
- deterministic compact POST body and signed GET request path/query construction;
- authenticated Demo header `x-simulated-trading: 1` on every private request;
- structural rejection of non-Demo environment or alternate production-style base URL;
- strict private endpoint allowlist limited to task-authorized execution/reconciliation reads.

#### Demo MARKET request materialization

The provider request accepts only the already-approved canonical MARKET path:

```text
BTC_USDT_PERP -> BTC-USDT-SWAP
tdMode         = isolated
BUY            -> buy
SELL           -> sell
MARKET         -> market
```

`posSide` is derived only from explicit configured OKX position mode:

```text
net_mode                  -> net
long_short_mode + BUY     -> long
long_short_mode + SELL    -> short
```

Provider `sz` comes only from `OKXEntrySizingAudit.provider_requested_contract_quantity`. Canonical BTC quantity is not copied into provider `sz`.

#### Provider `clOrdId`

Stable mapping:

```text
R7 + first 30 hexadecimal characters of SHA-256(E4 client_order_id)
```

It is deterministic, alphanumeric, <=32 characters, and retained alongside the original internal E4 client ID for traceability. Historical provider uniqueness is not assumed.

#### Account / position prerequisites

Mode facts are read/validated, not mutated:

- `GET /api/v5/account/config` -> expected explicit `acctLv` and `posMode`;
- `GET /api/v5/account/positions` -> target exposure truth;
- `GET /api/v5/trade/orders-pending` -> pending-order truth.

New bounded entry fails closed on configured account-level mismatch, position-mode mismatch, non-zero target exposure, incompatible margin-mode fact, or pending target orders.

No `set-position-mode`, `set-leverage`, or account-mode mutation capability exists.

#### Acknowledgement / provider truth

`POST /api/v5/trade/order` success acknowledgement maps only to E4 `PENDING` with canonical `filled_quantity=0`. Acknowledgement is not fill truth.

Explicit row rejection maps to `REJECTED`. Malformed/unknown/id-mismatched acknowledgement maps to `RECONCILIATION_REQUIRED`.

Order lookup maps current recognized provider states:

```text
live             -> OPEN
partially_filled -> PARTIALLY_FILLED
filled           -> FILLED
canceled         -> CANCELED
mmp_canceled     -> CANCELED
unknown          -> RECONCILIATION_REQUIRED
```

Provider contract `sz` / `accFillSz` are checked against the materialized order and normalized back to canonical BTC. Contradictory size/fill facts fail closed.

Fills retain provider `ordId`/`tradeId` identity and normalize `fillSz` contracts to shared canonical BTC quantity without conflation.

#### Ambiguity and reconciliation

Timeout/connection failure during submission maps to `RECONCILIATION_REQUIRED`. Repeating ordinary `submit_entry` returns the prior ambiguous result and does not send another request.

Explicit reconciliation reads:

```text
GET /api/v5/trade/order
GET /api/v5/account/positions
GET /api/v5/trade/fills
GET /api/v5/trade/orders-pending
```

Any matching order, fill, exposure, or pending order blocks retry.

Order absence must be explicitly proven by a provider code configured from current authoritative provider semantics. `order_not_found_codes` defaults to empty; therefore an unrecognized/non-success lookup cannot unlock retry.

### 4. Freshness hardening disposition

Finding `E4-OKX-FRESHNESS-HARDEN-001` is addressed in `src/brokers/okx_sizing.py` and `docs/execution/OKX_SIZING_POLICY.md`.

Policy version is now:

```text
okx-instrument-metadata-freshness-v0.2
```

The earlier 300-second value remains only a general cache/sizing ceiling. It is explicitly not submit permission.

At Demo submit materialization:

```text
provider metadata age <= 5 seconds
```

Current official `upcChg` is parsed into typed scheduled-change records. Unknown change parameters fail closed. Already-effective scheduled changes fail closed. `minSz` or `maxMktSz` changes effective within a 60-second guard window block materialization. `tickSz` remains audit metadata and does not generate an executable MARKET price.

These 5-second/60-second values are E4 safety policy, not provider stability guarantees.

### 5. Official OKX V5 references rechecked

Rechecked on 2026-08-21:

- `https://www.okx.com/docs-v5/en/`
- REST authentication
- Demo Trading
- `GET /api/v5/public/instruments`
- `GET /api/v5/account/config`
- `GET /api/v5/account/positions`
- `POST /api/v5/trade/order`
- `GET /api/v5/trade/order`
- `GET /api/v5/trade/orders-pending`
- `GET /api/v5/trade/fills`

Current semantics used:

- private signing prehash = `timestamp + method + requestPath + body`;
- HMAC-SHA256 with API secret, Base64 encoded;
- Demo private requests require `x-simulated-trading: 1`;
- `clOrdId` is case-sensitive alphanumeric <=32 chars and uniqueness is pending-order scoped;
- account config exposes `acctLv` / `posMode`;
- `posSide` semantics depend on configured position mode;
- provider SWAP sizing remains contract-based;
- instrument metadata exposes `upcChg(param,newValue,effTime)` for documented scheduled parameter updates.

#### Order-absence limitation

The current global official documentation recheck did not produce a sufficiently stable task-authoritative error-code table for hard-coding a specific `GET /trade/order` error as definitive absence. E4 therefore did not stabilize a historical/third-party error code. Deployment/local integration must explicitly configure an authoritative order-not-found code before retry can ever be permitted.

### 6. Files changed

- `src/brokers/okx_demo.py`
- `src/brokers/okx_sizing.py`
- `tests/brokers/test_okx_demo_adapter.py`
- `tests/brokers/test_okx_demo_status_mapping.py`
- `tests/brokers/test_okx_sizing.py`
- `docs/execution/OKX_DEMO_ADAPTER.md`
- `docs/execution/OKX_SIZING_POLICY.md`
- `docs/execution/E4_TO_E7_HANDOFF.md`
- `coordination/E4/STATUS.md` (completion commit follows)

Existing canonical gateway, Broker/PaperBroker, idempotency, partial-fill, overfill, and ambiguity semantics were not broadened or weakened.

### 7. Contracts consumed

- `contracts-v0.1`
- `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`
- ADR-0002
- ADR-0003
- merged E4 canonical `OrderRequest` / `OrderResult` / `Fill` semantics

### 8. Contracts produced or changed

`NONE`.

No `contracts/**` file was edited.

### 9. Test definitions added/updated

Local-only fake-transport definitions cover:

- deterministic signature/request construction using fake credentials;
- Demo header always present;
- production mode/base rejection;
- stable legal provider `clOrdId` mapping;
- isolated MARKET payload;
- provider `sz` sourced from sizing audit, not canonical BTC;
- net and long/short `posSide` mapping;
- account/position-mode mismatch fail closed;
- existing exposure/pending orders block new exposure;
- submit-time metadata <=5 seconds;
- scheduled sizing change guard;
- unknown scheduled change fail closed;
- acknowledgement is PENDING, not fill truth;
- timeout -> reconciliation required and repeated ordinary submit does not resend;
- order + position + fills + pending query-before-retry path;
- partial/filled/canceled provider-state mapping;
- unknown state -> reconciliation required;
- contradictory provider order size fails closed;
- provider fill contracts normalize to canonical BTC;
- no asset-movement/account-mutation surface;
- provider effective exposure never exceeds E5-approved BTC.

### 10. Local verification

Result: `NOT_RUN`

Reason: no Product Owner-approved local project execution environment was available. No project code, fake-transport test, broker simulation, or provider request was executed on GitHub.

Required local commands:

```text
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

No executable PASS is claimed.

### 11. Known limitations

- No concrete HTTP/network transport exists; only injected transport source is defined.
- No provider request was sent in this task.
- Exact authoritative OKX order-not-found error-code configuration remains a local/integration prerequisite; default is fail-closed/no retry.
- No automatic leverage/account/position-mode mutation exists.
- No restart-persistent provider execution journal is added by this bounded task.
- Only `BTC_USDT_PERP -> BTC-USDT-SWAP`, MARKET, isolated mapping is implemented.
- Real-money/production mode is structurally rejected.

### 12. Security / secrets

Confirmed:

- no real API key, secret, passphrase, token, password, private key, or live `.env` value was committed;
- credentials are runtime-only and representations are redacted;
- fake test credentials are explicitly synthetic;
- no withdrawal, deposit, funding transfer, internal/sub-account transfer, balance adjustment, or asset-movement capability exists.

### 13. GitHub compute policy

Confirmed:

- no GitHub Actions workflow created or used;
- no GitHub-hosted/GitHub-triggered runner used;
- no project test, provider simulation, provider request, or recovery test executed on GitHub;
- verification remains `NOT_RUN`.

### 14. Live / release impact

- OKX Demo source construction: implemented statically
- Demo execution: `NOT_RUN / NOT AUTHORIZED IN THIS SESSION`
- production/real-money mode: `REJECTED / NOT IMPLEMENTED`
- PAPER/SHADOW/LIVE: `NOT ADVANCED`
- Gate A/B/C/D: remain `BLOCKED`

### 15. Required next action

E7/PM should perform static review. Product Owner-approved local verification is required before any Demo provider request is considered. Separately verify/configure authoritative current order-not-found semantics before enabling any retry path.

### 16. Codex bug ticket

`NONE` — executable verification was not run, so no bounded runtime defect is claimed.
