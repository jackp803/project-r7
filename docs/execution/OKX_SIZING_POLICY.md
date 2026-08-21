# E4 OKX Local Sizing / Metadata Policy

Status: bounded static/source implementation extended by `E4-20260821-008`.

Configured mapping:

```text
BTC_USDT_PERP -> OKX BTC-USDT-SWAP
```

This document defines provider metadata validation, deterministic contract sizing, and the stricter metadata checks required immediately before Demo request materialization. It does not authorize real-money trading or GitHub execution.

## Canonical boundary

Accepted profiles remain:

```text
schema_version           = contracts-v0.1
entry profile            = entry-v0.1
entry order type         = MARKET
quantity profile         = base-asset-v0.1
quantity unit            = BASE_ASSET
quantity asset           = BTC
```

`ApprovedTradePlan.quantity` and shared `OrderRequest.quantity` remain canonical BTC upper bounds. OKX `sz` is provider contract quantity and is retained separately.

## Official OKX V5 references rechecked

Rechecked on 2026-08-21 against current official OKX V5 documentation:

- `https://www.okx.com/docs-v5/en/`
- Public Data / `GET /api/v5/public/instruments`
- Order Book Trading / `POST /api/v5/trade/order`

Facts used:

- instrument metadata exposes `instType`, `ctVal`, `ctMult`, `ctValCcy`, `ctType`, `lotSz`, `minSz`, `tickSz`, `state`, and `upcChg`;
- `upcChg` is an array of upcoming changes carrying `param`, `newValue`, and millisecond `effTime`;
- current documented `upcChg.param` values include `tickSz`, `minSz`, and `maxMktSz`;
- derivative `sz`, `lotSz`, and `minSz` are contract counts;
- MARKET is supported for SWAP;
- `state=live` is the accepted normal tradable state for this bounded path.

## Freshness policy v0.2

Version:

```text
okx-instrument-metadata-freshness-v0.2
```

Two different freshness boundaries are intentionally distinguished.

### General sizing/cache validation

```text
max age = 300 seconds
```

This is only a cache/sizing validation ceiling. It is **not** a provider stability guarantee and does not authorize order materialization.

### Submit preparation validation

At Demo order materialization time:

```text
metadata observation age <= 5 seconds
```

The submit path therefore requires a provider observation at or immediately before materialization.

Scheduled changes are inspected:

- unknown `upcChg.param` -> fail closed;
- an `effTime` already reached while still present in the snapshot -> fail closed;
- `minSz` or `maxMktSz` becoming effective inside the next 60 seconds -> fail closed;
- `tickSz` is retained/audited but does not manufacture a MARKET price, so it does not by itself block the MARKET path under the current profile.

The 60-second guard is an E4 safety margin, not a provider guarantee. If official semantics later broaden `upcChg` or another scheduled change affects sizing/exposure, the adapter must fail closed until reviewed.

## Supported conversion

Only the E7-approved direct class is supported:

```text
provider       = OKX
instrument     = BTC-USDT-SWAP
instType       = SWAP
ctType         = linear
ctValCcy       = BTC
state          = live
```

Formula:

```text
base_per_contract = ctVal * ctMult
raw_contracts     = approved_base_quantity / base_per_contract
provider_sz       = floor(raw_contracts / lotSz) * lotSz
effective_base    = provider_sz * base_per_contract
```

Required invariants:

```text
provider_sz > 0
provider_sz >= minSz
provider_sz is a lotSz multiple
0 < effective_base <= E5-approved canonical BTC
```

Round-down or reject only. Never round up and never submit a compensating order for residual quantity.

## MARKET / price boundary

`reference_price` remains advisory. No `limit_price`, `stop_price`, `trigger_price`, TIF, or tick-rounded executable price is generated from it.

## Security / operational boundary

The Demo adapter may consume this sizing result but cannot reinterpret the quantity. This module exposes no withdrawal, deposit, transfer, account-mode mutation, leverage mutation, production trading, or live enablement capability.
