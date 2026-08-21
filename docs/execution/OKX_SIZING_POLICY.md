# E4 OKX Local Sizing / Metadata Policy

Status: bounded static/source implementation for `E4-20260821-006`.

This document defines only provider metadata validation and deterministic sizing for the configured mapping:

```text
BTC_USDT_PERP -> OKX BTC-USDT-SWAP
```

It does **not** authorize or implement OKX networking, Demo/private API calls, authentication, signatures, account queries, leverage changes, or order submission.

## Canonical boundary

The accepted shared profiles are:

```text
schema_version           = contracts-v0.1
entry profile            = entry-v0.1
entry order type         = MARKET
quantity profile         = base-asset-v0.1
quantity unit            = BASE_ASSET
quantity asset           = BTC
```

`ApprovedTradePlan.quantity` and shared `OrderRequest.quantity` remain canonical BTC exposure upper bounds. OKX provider contract quantity (`sz`) is a separate adapter fact and must never be copied into those shared fields.

## Official OKX V5 references rechecked

Rechecked on 2026-08-21 against the current official OKX V5 documentation:

- `https://www.okx.com/docs-v5/en/`
- Public Data / `GET /api/v5/public/instruments`
- Order Book Trading / Trade / `POST /api/v5/trade/order`

Provider facts relied on by this bounded implementation:

- OKX instrument metadata exposes `instType`, `ctVal`, `ctMult`, `ctValCcy`, `ctType`, `lotSz`, `minSz`, `tickSz`, and `state`.
- For derivatives, `lotSz` and `minSz` are expressed in number of contracts.
- For `FUTURES/SWAP/OPTION`, order `sz` is the number of contracts rather than canonical BTC quantity.
- `market` is an OKX order type applicable to `SWAP`.
- Normal new MARKET exposure requires a compatible tradable state; `post_only` is not compatible with MARKET, and suspended/rebase states are not accepted by this implementation.
- OKX `clOrdId` has provider-specific constraints. This task does not implement provider request construction or map the existing internal `client_order_id` into an OKX `clOrdId`; that remains a later provider-adapter concern.

The base-quantity conversion formula is governed by E7's accepted `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md` and ADR-0003. This implementation does not invent a different conversion from provider examples.

## E4 metadata freshness policy

Version:

```text
okx-instrument-metadata-freshness-v0.1
```

Maximum age for new-exposure sizing:

```text
300 seconds
```

The policy is intentionally fail-closed. New exposure is blocked when metadata is missing, older than 300 seconds, future-dated, malformed, provider/instrument mismatched, non-tradable, or uses an unsupported freshness-policy version.

Every sizing audit retains:

- provider and provider instrument identity;
- canonical symbol;
- metadata observation timestamp;
- metadata reference;
- freshness-policy version;
- canonical approved BTC quantity;
- provider requested contract quantity;
- effective canonical BTC quantity after provider round-down.

## Supported conversion class

V1 supports only the E7-approved direct class:

```text
provider       = OKX
canonical      = BTC_USDT_PERP
instrument     = BTC-USDT-SWAP
instType       = SWAP
ctType         = linear
ctValCcy       = BTC
state          = live
```

All of `ctVal`, `ctMult`, `lotSz`, `minSz`, and `tickSz` must be positive finite decimal values. `minSz` must be an exact `lotSz` multiple.

The deterministic conversion is:

```text
base_per_contract = ctVal * ctMult
raw_contracts     = approved_base_quantity / base_per_contract
provider_sz       = floor(raw_contracts / lotSz) * lotSz
effective_base    = provider_sz * base_per_contract
```

Acceptance requires:

```text
provider_sz > 0
provider_sz >= minSz
provider_sz is a valid lotSz multiple
0 < effective_base <= canonical approved BTC quantity
```

Quantization may only round down or reject. It never rounds up to satisfy `minSz`, and it never creates a compensating order for the residual quantity.

## Unsupported conversion

The bounded V1 sizing path rejects:

- non-`linear` contract type;
- `ctValCcy` other than canonical `BTC`;
- any price-dependent conversion;
- provider/instrument mappings other than the configured BTC mapping;
- unknown contract semantics.

A future conversion class requires separate E7 review/versioning.

## MARKET / price boundary

`entry-v0.1` is MARKET-only. `reference_price` is advisory/audit context only.

Therefore E4 does not produce from `reference_price`:

- `limit_price`;
- `stop_price`;
- `trigger_price`;
- `time_in_force`;
- tick-rounded executable price.

`tickSz` is retained and validated as instrument metadata only in this task.

## Security / operational boundary

No capability in this implementation performs:

- withdrawal;
- funding transfer;
- sub-account capital movement;
- private API authentication;
- account-mode mutation;
- leverage-setting calls;
- Demo or real order submission.

PAPER/SHADOW/LIVE remain unauthorized by this policy.
