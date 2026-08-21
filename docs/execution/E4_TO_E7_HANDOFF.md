# E4 -> E7 Handoff — Canonical Entry Translation / OKX Local Sizing

## Handoff

**From:** E4 / Trading Execution & Broker Integration Engineer  
**To:** E7 / Integration Engineer  
**Branch:** `agent/e4-execution-v2`  
**Task:** `E4-20260821-006`  
**Date:** 2026-08-21

### 1. Objective

Extend the accepted E4 Broker/PaperBroker skeleton with only:

1. canonical `entry-v0.1 / MARKET` ApprovedTradePlan -> OrderRequest translation; and
2. deterministic, local-only OKX instrument metadata validation and BTC-to-contract sizing for the configured `BTC_USDT_PERP -> BTC-USDT-SWAP` mapping.

No OKX private/Demo networking, authentication, account access, leverage-setting call, order submission, SHADOW, or LIVE behavior is included.

### 2. Synchronization / baseline

The existing E4 branch had diverged from `main`. It was synchronized non-destructively with a two-parent merge commit:

```text
2e0a60e3ba3e9fbe5f298fded2408988beb81fe0
```

Parents preserve both:

- prior accepted E4 skeleton/history; and
- then-current `main` `2bbe3726f7897f3ad2df0b67a58f9ba9829c17d4`.

No force update or history rewrite was used.

Accepted upstream pins from the TASK:

- E2: `f99a8d00cd1fe40e1d73964d8b1cf37bc1886bd4`
- E5: `e5f7088301a92deadfd9f6c416ae03b466c38a47`
- parent schema: `contracts-v0.1`
- entry profile: `entry-v0.1 / MARKET`
- quantity profile: `base-asset-v0.1 / BASE_ASSET / BTC`

### 3. What changed

#### Provider-neutral entry translation

`src/execution/gateway.py` now accepts only a current executable profiled ApprovedTradePlan for this path:

```text
symbol                   = BTC_USDT_PERP
entry profile             = entry-v0.1
entry order type          = MARKET
quantity profile          = base-asset-v0.1
quantity unit             = BASE_ASSET
quantity asset            = BTC
```

Mechanical translation only:

```text
LONG  -> BUY
SHORT -> SELL
MARKET -> MARKET
ApprovedTradePlan.quantity -> OrderRequest.quantity unchanged
```

`reference_price` is validated only as optional advisory context. It does not become an executable limit/stop/trigger price or TIF.

Missing/unknown profiles, unsupported order types, malformed quantity, expired plans, incompatible symbol/unit/asset, and forbidden executable entry price/TIF fields fail closed.

`OrderRequest` now carries the canonical quantity profile identifiers so E4 does not lose the base-asset unit at the provider boundary. These fields are included in the idempotency safety fingerprint.

#### Deterministic OKX local sizing

Added `src/brokers/okx_sizing.py` with:

- `OKXInstrumentMetadata` local snapshot model;
- explicit E4 metadata freshness policy;
- metadata identity/type/state/decimal validation;
- direct linear BTC-denominated conversion only;
- deterministic lot-size round-down;
- below-minimum/nonrepresentable rejection;
- `OKXEntrySizingAudit` that keeps canonical and provider-native facts separate.

Configured mapping:

```text
BTC_USDT_PERP -> OKX BTC-USDT-SWAP
```

Supported conversion class:

```text
provider = OKX
instType = SWAP
ctType   = linear
ctValCcy = BTC
state    = live
```

Sizing follows the E7-approved profile/ADR formula:

```text
base_per_contract = ctVal * ctMult
raw_contracts     = approved_base_quantity / base_per_contract
provider_sz       = floor(raw_contracts / lotSz) * lotSz
effective_base    = provider_sz * base_per_contract
```

Acceptance:

```text
provider_sz > 0
provider_sz >= minSz
provider_sz is a valid lotSz multiple
0 < effective_base <= approved canonical BTC quantity
```

Round-up is never used. Residual approved BTC is left unexecuted.

### 4. Metadata freshness policy

Policy version:

```text
okx-instrument-metadata-freshness-v0.1
```

Maximum age for new-exposure sizing:

```text
300 seconds
```

Missing, future-dated, stale, malformed, provider/instrument-mismatched, non-live, or unsupported metadata blocks sizing/new exposure.

The audit object retains:

- canonical approved BTC quantity/profile;
- provider requested contract quantity;
- effective canonical requested BTC after round-down;
- provider/instrument identity;
- base-per-contract;
- metadata reference/observation;
- freshness policy version.

### 5. Official OKX V5 references rechecked

Rechecked on 2026-08-21:

- `https://www.okx.com/docs-v5/en/`
- Public Data / `GET /api/v5/public/instruments`
- Order Book Trading / Trade / `POST /api/v5/trade/order`

Provider semantics relied upon:

- derivatives `lotSz` / `minSz` are contract counts;
- FUTURES/SWAP/OPTION order `sz` is number of contracts;
- `market` is supported for SWAP;
- instrument `state=live` is normal tradable state, while `post_only` is incompatible with MARKET;
- provider metadata includes the contract/lot/tick/state facts required by the E7 profile.

The conversion formula itself is governed by `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md` and ADR-0003; E4 does not invent a different provider conversion from examples.

Provider-specific `clOrdId` constraints were also observed in the official docs. This task does not implement request construction or map the internal E4 `client_order_id` into OKX `clOrdId`; that remains future provider-adapter scope.

### 6. Files changed in this task

- `src/execution/gateway.py`
- `src/execution/models.py`
- `src/brokers/okx_sizing.py`
- `tests/execution/test_gateway.py`
- `tests/brokers/test_paper_broker.py`
- `tests/brokers/test_okx_sizing.py`
- `docs/execution/OKX_SIZING_POLICY.md`
- `docs/execution/E4_TO_E7_HANDOFF.md`
- `coordination/E4/STATUS.md` (completion update follows this handoff)

Existing `src/brokers/base.py` and `src/brokers/paper.py` behavior was preserved.

### 7. Contracts consumed

- `contracts-v0.1`
- `contracts/EXECUTION_OBJECT_PROFILES_V0_1.md`
- ADR-0002
- ADR-0003
- E5 ApprovedTradePlan producer pin `e5f7088301a92deadfd9f6c416ae03b466c38a47`

### 8. Contracts produced or changed

`NONE`.

No `contracts/**` file was modified.

### 9. Deterministic local-only test definitions

Definitions cover:

- valid profiled MARKET translation;
- LONG/SHORT side mapping;
- advisory reference price does not become executable price;
- missing/unknown profiles fail closed;
- unsupported order type / forbidden executable price/TIF fail closed;
- malformed quantity / expired plan rejection;
- stable E4 idempotency;
- PaperBroker partial fill / overfill / ambiguity / reconciliation behavior;
- exact representable OKX quantity;
- round-down quantity;
- below-minimum/nonrepresentable reject;
- lot/min-size validation;
- missing/stale/malformed/non-tradable/mismatched metadata reject;
- unsupported conversion reject;
- provider sizing never exceeds approved BTC exposure;
- canonical BTC quantity remains distinct from provider contract quantity.

### 10. Local verification

Result: `NOT_RUN`

Reason: this chat has no Product Owner-approved local project execution environment. No project test was executed on GitHub infrastructure.

Required local commands from repository root:

```text
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

No PASS is claimed until approved local execution occurs.

### 11. Known limitations / documentation gap

- No OKX public/private network request exists in this implementation; metadata is supplied as a local snapshot object.
- No actual current `BTC-USDT-SWAP` metadata snapshot is hard-coded. The tests use synthetic deterministic metadata to verify conversion invariants.
- Only direct `linear` + `ctValCcy=BTC` conversion is supported. Price-dependent/inverse/ambiguous conversion fails closed.
- Provider request formatting (`instId`, `tdMode`, `sz`, `clOrdId`) is not implemented.
- Existing internal `client_order_id` is not claimed to already satisfy OKX `clOrdId` formatting/length constraints; provider ID mapping is future scoped work.
- The TASK names `status/e7/E2_E5_PROFILE_CHAIN_STATIC_REVIEW_20260821.md`, but that file was not present/searchable after synchronization. No substitute E7 review was invented. This implementation used the TASK's explicit accepted pins/disposition plus the present canonical profile and ADR-0002/0003.

### 12. Dependencies / blockers

No blocker to this bounded static/source completion.

Before any future OKX provider execution stage:

- E7 must review this translation/sizing implementation;
- local tests must be run in an approved environment;
- current provider metadata retrieval/caching must be implemented and validated;
- account mode / isolated-operation prerequisites must be verified;
- provider-native client-order-ID mapping must be defined;
- separate authorization is required for Demo/private APIs.

### 13. Required next action

E7/PM should perform static integration review and arrange Product Owner-approved local test execution. Do not promote PAPER_READY/Demo/SHADOW/LIVE from this handoff alone.

### 14. Security / secrets

Confirmed:

- no API key, secret, passphrase, credential, token, private key, or live `.env` value was added;
- no authenticated endpoint code exists;
- no withdrawal, funding transfer, or sub-account capital-movement capability exists;
- test data is synthetic.

### 15. GitHub compute policy

Confirmed:

- no GitHub Actions workflow was created or used;
- no hosted/GitHub-triggered runner was used;
- no unit/integration/broker/API test or project compute was executed on GitHub;
- executable verification remains `NOT_RUN`.

### 16. Live-trading impact

No real/Demo provider order can be submitted by this task. PAPER/SHADOW/LIVE remain disabled/unauthorized. The change only materializes a fail-closed translation and sizing boundary for later provider integration.

### 17. Codex bug ticket

`NONE` — no executable local verification was performed, so no bounded implementation defect is claimed.
