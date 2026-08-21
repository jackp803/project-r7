# E4 OKX Sizing / Metadata Policy

Status: E4-local static/source policy after `E4-20260821-010` corrections.

Configured mapping:

```text
BTC_USDT_PERP -> OKX BTC-USDT-SWAP
```

Canonical `OrderRequest.quantity` remains the E5-approved BTC upper bound. Provider `sz` remains an OKX contract-count fact and is never copied into shared canonical quantity fields.

## Deterministic conversion

Supported direct conversion remains only:

```text
provider = OKX
instType = SWAP
ctType   = linear
ctValCcy = BTC
state    = live
```

Formula:

```text
base_per_contract = ctVal * ctMult
raw_contracts     = approved_BTC / base_per_contract
provider_sz       = floor(raw_contracts / lotSz) * lotSz
effective_BTC     = provider_sz * base_per_contract
```

Required:

```text
provider_sz > 0
provider_sz >= minSz
provider_sz is a valid lotSz multiple
provider_sz <= maxMktSz when current metadata provides maxMktSz
0 < effective_BTC <= approved_BTC
```

Provider quantization may only round down or reject.

## Materialization integrity

`OKXEntrySizingAudit` is not execution authority.

At order materialization E4 recomputes sizing from:

1. the exact current canonical `OrderRequest`; and
2. the exact submit-validated `OKXInstrumentMetadata` snapshot.

The caller-supplied prior audit must exactly match the recomputed audit. The audit binds:

- trade plan / canonical symbol / approved BTC quantity;
- quantity profile/unit/asset;
- provider/instrument/order side;
- provider contract quantity and effective BTC quantity;
- `ctVal`, `ctMult`, `ctValCcy`, `ctType`;
- `lotSz`, `minSz`, optional `maxMktSz`;
- metadata reference and observation timestamp;
- freshness policy version.

Any mismatch fails closed. Provider `body.sz` is serialized only from the recomputed result.

## Metadata freshness

Policy version:

```text
okx-instrument-metadata-freshness-v0.2
```

Safety margins:

```text
general cache/sizing maximum age = 300 seconds
submit preparation maximum age   = 5 seconds
scheduled sizing-change guard    = 60 seconds
```

The 300-second ceiling is not a provider stability guarantee and cannot independently authorize submit preparation.

`upcChg` is parsed for current documented scheduled-change fields. Unknown parameters fail closed. Already-effective scheduled changes fail closed. Sizing-relevant `minSz`/`maxMktSz` changes inside the 60-second guard fail closed. `tickSz` remains audit metadata for the current MARKET-only profile and does not create an executable price.

## Current provider metadata facts

The current local model retains at minimum:

- provider / canonical / instrument identity;
- `instType`;
- `ctVal`;
- `ctMult`;
- `ctValCcy`;
- `ctType`;
- `lotSz`;
- `minSz`;
- `tickSz`;
- optional current `maxMktSz` when returned;
- state;
- observation time/reference;
- scheduled `upcChg` facts;
- E4 freshness-policy version.

Missing, malformed, future-dated, stale, non-live, provider/instrument-mismatched, unsupported conversion, or unsafe scheduled-change metadata blocks new exposure preparation.

## Verification

Executable verification remains `NOT_RUN` without a Product Owner-approved local environment.

Required local command covering sizing/provider tests:

```text
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

No provider request or GitHub-hosted test execution is authorized by this policy.
