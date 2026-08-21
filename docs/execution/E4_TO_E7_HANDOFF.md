# E4 -> E7 Handoff — Final PR #12 Materialization Integrity Correction

**From:** E4 / Trading Execution & Broker Integration Engineer  
**To:** E7 / Integration Engineer  
**Task:** `E4-20260821-012`  
**Branch:** `agent/e4-okx-demo-adapter-20260821`  
**PR:** #12 `execution: add Demo-first OKX provider adapter`

## Objective

Close only the single remaining targeted E7 blocker:

```text
E4-OKX-MATERIALIZATION-INTEGRITY-001
```

The four prior findings remain closed and were not redesigned:

- `E4-OKX-ACCOUNT-MATRIX-001`
- `E4-OKX-RETRY-PROVENANCE-001`
- `E4-OKX-ORDER-ABSENCE-001`
- `E4-OKX-ORDER-STATE-CONSISTENCY-001`

No provider request, Demo order, production/live path, retry enablement, concrete transport, account mutation, asset movement, or release-gate advancement is included.

## Branch synchronization

Before the correction, the PR #12 branch had diverged from latest `main`.

E4 synchronized it non-destructively using two-parent merge commit:

```text
64508c6f15be959cf8eabefed580a48cd3c964c0
```

Parents preserve:

- prior PR #12 branch HEAD `c151fa7c37adafbf9f93157d80cf4b763dd775e2`;
- then-current `main` `7c6522e5c52722f734c11c1772c0b2e86b81b51c`.

No force update, destructive rebase, or branch-history rewrite was used.

## Correction design

The provider submit boundary now uses **adapter-owned issued-preparation provenance plus submit-time body re-derivation**.

### Preparation

`OKXDemoAdapter.prepare_entry()` still invokes the accepted materialization path, which:

- validates the Demo/account prerequisites;
- validates submit-fresh provider metadata;
- recomputes sizing from the exact `OrderRequest` plus metadata;
- treats caller `OKXEntrySizingAudit` as evidence only;
- enforces canonical BTC exposure `> 0` and `<=` E5-approved quantity.

After that succeeds, the adapter stores an internal frozen `_IssuedOKXPreparation` containing the exact preparation authority:

- `order_request_id`;
- `trade_plan_id`;
- internal `client_order_id`;
- provider `clOrdId`;
- provider instrument;
- provider side;
- provider position side;
- provider order type `market`;
- provider trade mode `isolated`;
- provider contract quantity;
- effective canonical BTC quantity;
- E5-approved canonical BTC quantity;
- metadata reference and observation timestamp;
- metadata freshness policy version;
- preparation time;
- Demo environment;
- account level and position mode.

The record retains the exact issued materialization object instance, not merely visible field values.

### Submit

`submit_entry()` now calls `_authorize_submit()` **before** reading the idempotency cache and before any transport operation.

A submit fails closed unless:

1. the exact object instance was issued by this adapter;
2. all materialization semantic fields exactly match the frozen issued facts;
3. Demo/account/position-mode context still matches;
4. `clOrdId` still derives from the internal client identity;
5. `0 < effective canonical BTC <= E5-approved canonical quantity`;
6. provider contract quantity is positive;
7. caller-visible `materialization.body` exactly equals the provider body freshly derived from trusted internal facts.

The actual request body passed into OKX signing is the freshly derived trusted body, never the caller mapping.

This closes both remaining bypass classes:

- direct caller construction of `OKXOrderMaterialization`;
- post-prepare mutation of `body` or public semantic facts.

A second preparation under the same provider `clOrdId` with materially different trusted preparation facts also fails closed.

## Request body authority

The signed body is re-derived as:

```text
instId  = trusted BTC-USDT-SWAP
tdMode  = isolated
clOrdId = trusted adapter-generated provider id
side    = trusted buy/sell
posSide = trusted net/long/short
ordType = market
sz      = trusted provider contract quantity
```

Provider `sz` remains separate from canonical BTC quantity.

## Source / test revisions

Primary source correction commit:

```text
36e91fb41976da3846b99d0c36164ac7780ebfa5
```

Targeted deterministic test-definition commit:

```text
41d66c0da10c4d79dfbc6e6ece622f0a6ac19cde
```

Files added/changed for this correction:

- `src/brokers/okx_demo.py`
- `tests/brokers/test_okx_submit_integrity.py`
- `docs/execution/OKX_DEMO_ADAPTER.md`
- `docs/execution/E4_TO_E7_HANDOFF.md`
- `coordination/E4/STATUS.md` (completion update follows)

No `contracts/**`, other-agent production code, Broker/PaperBroker source, endpoint scope, concrete transport, or provider retry semantics were changed.

## Test definitions

New local-only deterministic definitions prove:

- tampered `sz` rejected before transport;
- tampered `instId` rejected before transport;
- tampered `side` rejected before transport;
- tampered `posSide` rejected before transport;
- tampered `ordType` rejected before transport;
- tampered `clOrdId` rejected before transport;
- direct caller-constructed materialization clone rejected before transport;
- cross-adapter materialization rejected before transport;
- materially changed facts under the same logical identity rejected;
- materially different re-preparation under the same `clOrdId` rejected;
- valid adapter-issued preparation signs the exact expected Demo MARKET isolated body;
- repeated submit of the same issued object remains idempotent without a second transport call;
- provider effective canonical quantity remains within the E5-approved BTC upper bound.

## Preserved closed findings / boundaries

Unchanged:

- V1 account matrix: `acctLv=2` Futures mode with `net_mode | long_short_mode`;
- `tdMode=isolated`;
- MARKET-only entry;
- Demo-only environment and mandatory `x-simulated-trading: 1`;
- runtime-only/redacted credentials;
- private endpoint allowlist;
- freshness policy `okx-instrument-metadata-freshness-v0.2`;
- provider retry structurally disabled;
- no caller-configurable order-absence authority;
- provider state/fill consistency validation;
- no production/live fallback;
- no account/position/leverage mutation;
- no withdrawal/deposit/funding/internal/sub-account transfer/balance-adjustment surface;
- Broker/PaperBroker source behavior unchanged.

## Verification

Executable verification: `NOT_RUN`.

Reason: no Product Owner-approved local project execution environment was used. No GitHub Actions, CI, hosted runner, project compute, broker simulation, or OKX provider request was executed.

Required approved-local commands:

```text
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

No executable PASS is claimed.

## E7 requested action

Perform targeted static re-review of PR #12 at the new branch head, focusing only on closure of `E4-OKX-MATERIALIZATION-INTEGRITY-001` and regression preservation of the four already-closed findings.

Do not infer Demo connectivity/order authorization or PAPER/SHADOW/LIVE readiness from this handoff.
