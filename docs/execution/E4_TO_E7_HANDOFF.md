# E4 -> E7 Handoff — PR #12 Blocking Finding Corrections

## Handoff

**From:** E4 / Trading Execution & Broker Integration Engineer  
**To:** E7 / Integration Engineer  
**Task:** `E4-20260821-010`  
**Branch:** `agent/e4-okx-demo-adapter-20260821`  
**Reviewed baseline:** `b7031c52a38623c528ee9352276793d8110854e0`  
**Corrected source/test HEAD before docs/status:** `817e5c557922c26a6cc49fa00b920188b76a794d`  
**Date:** 2026-08-21

### 1. Objective

Correct only the five blocking findings from E7 review `status/e7/E4_OKX_DEMO_STATIC_SECURITY_REVIEW_20260821.md` while preserving the already accepted Demo/auth security, freshness-v0.2 hardening, canonical/provider quantity separation, and Broker/PaperBroker safety boundaries.

No provider request was sent and no executable project test was run.

### 2. Branch synchronization

Before correction the PR #12 branch and `main` had diverged.

E4 synchronized non-destructively using two-parent merge commit:

```text
0ff16394709710fd7ce26c9528f3c63ad8fb1518
```

Parents preserve:

- prior PR #12 branch HEAD `94ca2f861d9e7a51277c5c63ff20f730c7f19f92`; and
- then-current `main` `ab9a75b0d24eb82cff35d028e349878fddd4b86b`.

No force update, destructive rebase, or history rewrite was used.

### 3. Finding dispositions

#### `E4-OKX-MATERIALIZATION-INTEGRITY-001` — corrected

`materialize_demo_market_order()` now re-establishes provider sizing from:

```text
exact current OrderRequest
+
exact submit-validated OKXInstrumentMetadata
```

using `size_okx_market_entry()` at materialization time.

Caller-supplied `OKXEntrySizingAudit` is evidence only and must exactly equal the recomputed audit. Any mismatch fails closed. Provider request `sz` is serialized only from the recomputed audit.

The audit now binds additional provider conversion facts:

- `ctVal`;
- `ctMult`;
- `ctValCcy`;
- `ctType`;
- `lotSz`;
- `minSz`;
- optional `maxMktSz`;
- metadata reference/observation;
- provider contract quantity;
- effective canonical BTC quantity.

Current `maxMktSz`, when supplied by metadata, is validated and enforced by sizing.

Tests define rejection for forged oversized provider size, falsified effective quantity, altered request quantity, altered metadata/conversion facts, and metadata-reference mismatch. Existing lot/min tests remain present.

#### `E4-OKX-ACCOUNT-MATRIX-001` — corrected

Current official OKX V5 account/order guidance was rechecked.

V1 is deliberately narrowed to the smallest explicitly supported isolated SWAP subset:

```text
acctLv = 2  (Futures mode)
posMode = net_mode | long_short_mode
tdMode = isolated
```

Rejected:

```text
acctLv=1 Spot mode
acctLv=3 Multi-currency margin
acctLv=4 Portfolio margin
unsupported position modes
```

Official basis rechecked:

- account config defines acctLv 1/2/3/4 as Spot/Futures/Multi-currency/Portfolio;
- FUTURES/SWAP in Futures mode support both net and long/short position mode;
- current place-order guidance states `isolated` is not available in Multi-currency margin or Portfolio margin mode.

The adapter validates account facts; it does not mutate account/position mode or leverage.

#### `E4-OKX-RETRY-PROVENANCE-001` — corrected by fail-closed V1 policy

Provider retry is structurally disabled.

`OKXReconciliationEvidence` is audit/reporting data only. `retry_entry()` always raises `OKXReconciliationError`; it never clears the stored ambiguous result and never calls transport.

Forged, mutated, replayed, or cross-materialization evidence cannot authorize a second provider submit.

#### `E4-OKX-ORDER-ABSENCE-001` — corrected

Caller-controlled `order_not_found_codes` was removed from `OKXDemoAdapterConfig`.

`parse_order_lookup_response()` now treats any non-success provider code as:

```text
PROVIDER_ERROR_NOT_ABSENCE_PROOF
```

and a success/empty response as:

```text
SUCCESS_EMPTY_NOT_ABSENCE_PROOF
```

Neither state authorizes retry. No fixture/example provider code, including `51603`, is repository authority for order absence.

Provider retry remains disabled until E7 separately accepts an authoritative absence policy.

#### `E4-OKX-ORDER-STATE-CONSISTENCY-001` — corrected

Known provider state/fill facts are checked before optimistic canonical mapping:

```text
live              -> accFillSz == 0
partially_filled  -> 0 < accFillSz < sz
filled            -> accFillSz == sz
canceled          -> 0 <= accFillSz <= sz
mmp_canceled      -> 0 <= accFillSz <= sz
```

Behavior:

- `accFillSz > sz` -> hard reconciliation failure;
- contradictory known state/fill -> `RECONCILIATION_REQUIRED`;
- unknown state -> `RECONCILIATION_REQUIRED`;
- positive accumulated fill requires valid average fill price in the current response model;
- canceled states preserve actual partial-fill canonical quantity.

Contradiction tests cover filled-underfill, partial-zero, partial-full, live-nonzero, and overfill.

### 4. Previously accepted boundaries preserved

Unchanged:

- Demo-only environment;
- mandatory `x-simulated-trading: 1` for authenticated requests;
- runtime-only/redacted credentials;
- deterministic OKX REST signing;
- private endpoint allowlist;
- `BTC_USDT_PERP -> BTC-USDT-SWAP`;
- `tdMode=isolated` and MARKET-only entry;
- no executable limit/stop/trigger/TIF invention;
- canonical BTC quantity remains distinct from provider contract `sz`;
- stable legal provider `clOrdId` mapping;
- no production/live fallback;
- no concrete network transport;
- no account/position-mode/leverage mutation;
- no withdrawal/deposit/funding/internal/sub-account transfer/balance-adjustment surface;
- freshness policy `okx-instrument-metadata-freshness-v0.2` with 5-second submit observation and scheduled-change guard;
- PaperBroker / broker-neutral safety behavior untouched.

### 5. Official OKX references rechecked

Current official authority rechecked on 2026-08-21:

- `https://www.okx.com/docs-v5/en/`
- Account mode / account config
- Set position mode
- `GET /api/v5/public/instruments`
- `POST /api/v5/trade/order`
- `GET /api/v5/trade/order`
- `GET /api/v5/trade/orders-pending`
- `GET /api/v5/account/positions`
- `GET /api/v5/trade/fills`

No stable current provider authority was adopted for a specific order-not-found error code.

### 6. Files changed for this correction

- `src/brokers/okx_demo.py`
- `src/brokers/okx_sizing.py`
- `tests/brokers/test_okx_demo_adapter.py`
- `tests/brokers/test_okx_demo_status_mapping.py`
- `docs/execution/OKX_DEMO_ADAPTER.md`
- `docs/execution/OKX_SIZING_POLICY.md`
- `docs/execution/E4_TO_E7_HANDOFF.md`
- `coordination/E4/STATUS.md` (completion update follows)

No shared contract or other-agent production file was modified by E4 correction commits.

### 7. Local verification

Result: `NOT_RUN`

Reason: no Product Owner-approved local project execution environment was used in this chat. No test was executed on GitHub infrastructure.

Required approved-local commands:

```text
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

No PASS is claimed from unexecuted test definitions.

### 8. Security / secrets

Confirmed:

- no real API key, secret, passphrase, token, private key, or live `.env` value was added;
- fake test credentials are synthetic labels only;
- no actual provider request/order was sent;
- production/live mode remains rejected;
- no asset-movement capability exists.

### 9. GitHub compute policy

Confirmed:

- no GitHub Actions workflow was created or used;
- no GitHub-hosted/triggered runner was used;
- no unit/integration/provider test or project compute was executed on GitHub.

### 10. Release / live impact

This correction does not authorize Demo connectivity/order submission or any PAPER/SHADOW/LIVE gate. Gate A/B/C/D remain unchanged/blocked.

### 11. Required next action

E7/PM should re-review PR #12 statically against the five blocking findings and, separately, arrange Product Owner-approved local executable verification. E4 stops after STATUS update and does not merge PR #12 or start connectivity/order execution.
