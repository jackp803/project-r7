# E4 OKX Demo Adapter — Static Source Boundary

Status: corrected static/source implementation for `E4-20260821-010` on PR #12 branch.

This adapter remains **Demo-only source construction**. It does not authorize or provide concrete networking, real credentials, production/live trading, account mutation, asset movement, PAPER/SHADOW/LIVE promotion, or actual provider retry.

## Official OKX V5 references rechecked

Rechecked on 2026-08-21 against current official OKX documentation:

- `https://www.okx.com/docs-v5/en/`
- account mode / account config (`acctLv`, `posMode`)
- set position mode guidance
- place order `POST /api/v5/trade/order`
- get order `GET /api/v5/trade/order`
- pending orders `GET /api/v5/trade/orders-pending`
- positions `GET /api/v5/account/positions`
- fills `GET /api/v5/trade/fills`
- public instruments `GET /api/v5/public/instruments`

Provider facts used by this bounded implementation:

- Demo authenticated requests require `x-simulated-trading: 1`.
- Private REST signing uses `timestamp + METHOD + requestPath + body`, HMAC-SHA256, Base64.
- `clOrdId` is case-sensitive alphanumeric, maximum 32 characters, and uniqueness is scoped to currently pending orders.
- `acctLv=1` is Spot mode, `2` Futures mode, `3` Multi-currency margin, `4` Portfolio margin.
- For FUTURES/SWAP, Futures mode supports both `net_mode` and `long_short_mode`; Portfolio margin supports net mode only.
- Current place-order guidance states `tdMode=isolated` is not available in Multi-currency margin or Portfolio margin mode.
- SWAP order `sz`, `accFillSz`, and `fillSz` are contract quantities.
- Order state semantics: `live` = active with no fills; `partially_filled` = partially executed and active; `filled` = fully executed terminal; `canceled` and `mmp_canceled` = canceled terminal and may preserve prior fills.

No provider error code is treated as authoritative order-absence proof in this revision.

## Demo/auth boundary preserved

- `environment` must equal `demo`.
- REST base remains `https://openapi.okx.com` for the bounded config.
- every authenticated request includes `x-simulated-trading: 1`.
- credentials are runtime injected and redacted from object repr output.
- private endpoint allowlist remains limited to the task-authorized order/reconciliation/account-read surface.
- no withdrawal, deposit, funding/internal/sub-account transfer, balance adjustment, account-mode setter, position-mode setter, or leverage setter exists.
- `OKXTransport` remains injected; no concrete network transport is implemented.

## Finding corrections

### `E4-OKX-MATERIALIZATION-INTEGRITY-001`

`materialize_demo_market_order()` no longer trusts caller-provided provider sizing as authority.

At the exact submit-preparation boundary it:

1. validates current metadata with freshness policy `okx-instrument-metadata-freshness-v0.2`;
2. recomputes `OKXEntrySizingAudit` from the exact current `OrderRequest` and exact validated metadata;
3. compares the caller-supplied prior audit against the recomputed audit as evidence only;
4. rejects any mismatch;
5. writes provider `body.sz` only from the recomputed audit.

The audit now binds the conversion facts used for integrity comparison, including `ctVal`, `ctMult`, `ctValCcy`, `ctType`, lot size, minimum size, optional current `maxMktSz`, metadata reference/observation, provider contract quantity, and effective canonical BTC quantity.

Invariant remains:

```text
0 < effective_canonical_quantity <= E5-approved OrderRequest.quantity
```

Provider sizing may round down or reject; it cannot round above the E5 BTC bound.

### `E4-OKX-ACCOUNT-MATRIX-001`

V1 intentionally narrows account support to the smallest explicitly documented isolated SWAP subset:

```text
acctLv = 2  (Futures mode)
posMode = net_mode | long_short_mode
tdMode = isolated
```

Rejected before materialization:

```text
acctLv = 1  Spot mode
acctLv = 3  Multi-currency margin
acctLv = 4  Portfolio margin
unknown/unsupported position modes
```

The adapter validates provider-read account facts; it does not repair or mutate account/position mode.

Position-side mapping remains mechanical:

```text
net_mode -> posSide=net
long_short_mode + BUY  -> posSide=long
long_short_mode + SELL -> posSide=short
```

### `E4-OKX-RETRY-PROVENANCE-001`

Provider retry is structurally disabled in V1.

`OKXReconciliationEvidence` is audit/reporting data only. `retry_entry()` always raises `OKXReconciliationError` and cannot clear the stored ambiguous result or issue a second transport submit. Forged, mutated, replayed, or cross-materialization evidence therefore cannot create execution authority.

### `E4-OKX-ORDER-ABSENCE-001`

Caller-controlled `order_not_found_codes` was removed from adapter configuration.

A non-success `GET /api/v5/trade/order` result is represented as provider error / absence-not-proven audit state. A success response with empty data is also not treated as authoritative absence. No fixture/example code, including `51603`, enables retry.

Until E7 separately accepts current provider-authoritative absence semantics, provider retry remains disabled.

### `E4-OKX-ORDER-STATE-CONSISTENCY-001`

Known provider states are validated against provider `sz` / `accFillSz` before canonical mapping:

```text
live              -> accFillSz == 0
partially_filled  -> 0 < accFillSz < sz
filled            -> accFillSz == sz
canceled          -> 0 <= accFillSz <= sz
mmp_canceled      -> 0 <= accFillSz <= sz
```

Additional fail-closed rules:

- `accFillSz > sz` is a hard reconciliation failure;
- contradictory known state/fill combinations map to `RECONCILIATION_REQUIRED`;
- unknown states map to `RECONCILIATION_REQUIRED`;
- any positive accumulated fill requires a valid average fill price in the current response model;
- canceled terminal states preserve actual partial-fill quantity rather than forcing zero.

## Freshness hardening preserved

`E4-OKX-FRESHNESS-HARDEN-001` remains intact:

```text
policy version                  = okx-instrument-metadata-freshness-v0.2
general cache/sizing ceiling    = 300 seconds
submit preparation max age      = 5 seconds
scheduled sizing-change guard   = 60 seconds
```

`upcChg` scheduled changes remain fail closed for unknown parameters and sizing-relevant changes entering the guard window. These thresholds are E4 safety margins, not provider stability guarantees.

## Reconciliation truth set

After an ambiguous submit, the adapter may query for audit/reconciliation:

```text
GET /api/v5/trade/order
GET /api/v5/account/positions
GET /api/v5/trade/fills
GET /api/v5/trade/orders-pending
```

Positive provider truth remains distinct:

- order truth;
- pending-order truth;
- provider contract fill truth;
- provider contract position truth;
- canonical normalized BTC fill truth.

Reconciliation can report these facts but cannot authorize a retry in V1.

## Verification policy

Executable verification: `NOT_RUN`.

Required Product Owner-approved local commands from repository root:

```text
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

No GitHub Actions/CI/hosted runner/project compute and no actual OKX request/order were used for this correction task.
