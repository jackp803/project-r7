# E4 OKX Demo Adapter — Static Source Boundary

Status: bounded source implementation for PR #12. Actual provider connectivity, Demo order execution, provider retry, production/live trading, PAPER/SHADOW/LIVE promotion, and release-gate advancement are not authorized.

## Environment and credentials

The adapter is Demo-only:

```text
environment = demo
REST base   = https://openapi.okx.com
x-simulated-trading = 1 on every authenticated request
```

Runtime credentials are injected through `OKXCredentials`; their representation is redacted. No credential, secret, live `.env`, withdrawal/deposit/funding/internal transfer/sub-account transfer/balance-adjustment surface exists in this source.

Private REST signing remains:

```text
prehash   = timestamp + METHOD + requestPath + body
signature = Base64(HMAC-SHA256(secret, prehash))
```

The transport remains injected. No concrete network transport is implemented.

## Bounded entry path

Only the accepted provider-neutral path is materialized:

```text
BTC_USDT_PERP -> BTC-USDT-SWAP
tdMode = isolated
BUY  -> buy
SELL -> sell
MARKET -> market
```

Provider contract `sz` remains distinct from canonical BTC quantity. `materialize_demo_market_order()` recomputes provider sizing from the exact current `OrderRequest` plus submit-validated metadata and treats caller sizing audit as evidence only.

Invariant:

```text
0 < effective canonical BTC <= E5-approved OrderRequest.quantity
```

## Submit-boundary integrity — E4-OKX-MATERIALIZATION-INTEGRITY-001

Task `E4-20260821-012` closes the remaining submit-boundary bypass with an adapter-owned issued-preparation registry.

`prepare_entry()` now performs the normal materialization validation, then stores an internal immutable `_IssuedOKXPreparation` containing the exact trusted preparation facts:

- `order_request_id`;
- `trade_plan_id`;
- internal `client_order_id`;
- provider `clOrdId`;
- provider instrument;
- provider side;
- provider position side;
- `ordType=market`;
- `tdMode=isolated`;
- provider contract quantity;
- effective canonical BTC quantity;
- E5-approved canonical BTC quantity;
- instrument metadata reference and observation timestamp;
- metadata freshness policy version;
- preparation timestamp;
- Demo environment;
- reviewed account level and position mode.

The registry retains the exact issued `OKXOrderMaterialization` object instance. A caller-constructed clone, even with identical visible values, is not an issued preparation and fails closed.

`submit_entry()` performs provenance/integrity validation **before** consulting the idempotency result cache and before any transport call:

1. the exact object instance must be present in this adapter's issued-preparation registry;
2. every public semantic materialization field must still exactly equal the internal immutable preparation facts;
3. Demo/account/position-mode context must still match the adapter;
4. `clOrdId` must still deterministically bind to the internal client identity;
5. canonical exposure bound must still hold;
6. the caller-visible `body` must exactly equal a body freshly derived from internal trusted facts.

The body that is actually signed is freshly re-derived from `_IssuedOKXPreparation`:

```text
instId  = trusted provider instrument
tdMode  = isolated
clOrdId = trusted provider client order id
side    = trusted provider side
posSide = trusted provider position side
ordType = market
sz      = trusted provider contract quantity
```

`materialization.body` is therefore comparison/audit data only; it is never execution authority. Post-prepare mutation of `sz`, `instId`, `side`, `posSide`, `ordType`, or `clOrdId` causes rejection before transport.

The adapter also records one preparation fingerprint per provider `clOrdId`. Re-preparing the same provider identity with materially different preparation facts fails closed.

## Preserved accepted boundaries

The correction does not redesign the four E7 findings already closed by targeted re-review:

- account matrix remains V1 `acctLv=2` Futures mode with `net_mode | long_short_mode` only;
- provider retry remains structurally disabled;
- no caller-configurable provider error code can establish order absence;
- known order states remain subject to `accFillSz/sz` consistency checks before canonical mapping.

Freshness policy remains E4-local `okx-instrument-metadata-freshness-v0.2`:

- 300 seconds is only a general cache/sizing ceiling;
- submit preparation requires metadata observation age `<= 5 seconds`;
- scheduled `upcChg` values are parsed and fail closed under the existing guard rules.

Broker/PaperBroker behavior is unchanged.

## Deterministic local-only tests

`tests/brokers/test_okx_submit_integrity.py` defines cases for:

- mutate `body["sz"]` after prepare -> reject before transport;
- mutate `instId` -> reject before transport;
- mutate `side` -> reject before transport;
- mutate `posSide` -> reject before transport;
- mutate `ordType` -> reject before transport;
- mutate `clOrdId` -> reject before transport;
- direct caller-constructed clone -> reject before transport;
- cross-adapter materialization -> reject before transport;
- materially changed content under the same logical client identity -> reject;
- repeated materially different preparation under one provider `clOrdId` -> reject;
- valid adapter-issued preparation -> exact Demo MARKET isolated body;
- repeated submit of the same issued preparation -> no second transport call;
- provider effective canonical quantity never exceeds the E5-approved BTC bound.

Executable verification is `NOT_RUN`. These tests are source definitions only until a Product Owner-approved local project environment runs them.

Required local commands:

```text
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

GitHub Actions, hosted CI, hosted runners, and provider execution are prohibited for verification.
