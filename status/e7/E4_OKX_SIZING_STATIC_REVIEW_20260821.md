# E7 Static / Safety Review — E4 PR #11 Canonical Entry Translation and OKX Sizing

- Task: `E7-20260821-008`
- Review date: 2026-08-21
- Reviewer: E7 Integration / Architecture / System QA / Release Engineer
- PR: `#11 execution: add canonical entry translation and OKX sizing layer`
- E4 branch: `agent/e4-execution-v2`
- Reviewed implementation pin: `c71bf9c66a7f37cedb8bbbcf3000591970a081eb`
- PR current head observed: `aedb946c29e4e0695c3f020c90cdf0fcc8e9bd13`
- Parent schema: `contracts-v0.1`
- Entry profile: `entry-v0.1 / MARKET`
- Quantity profile: `base-asset-v0.1 / BASE_ASSET / BTC`
- Executable verification: `NOT_RUN`

## 1. Executive disposition

| Review area | Disposition |
|---|---|
| E5 ApprovedTradePlan -> E4 boundary | `PASS / STATIC ONLY` |
| E4 entry translator | `PASS / STATIC ONLY` |
| OKX local metadata / sizing safety | `PASS / STATIC ONLY` |
| Broker / PaperBroker regression | `PASS / STATIC ONLY` |
| Hard-coded 300-second metadata freshness policy | `NON_BLOCKING_HARDENING` |
| PR #11 source/static merge recommendation | `PASS — PM MAY MERGE` |
| Executable verification | `NOT_RUN` |
| Gate A / B / C / D | `BLOCKED / UNCHANGED` |

No blocking source/safety defect was found in the bounded reviewed scope.

Static acceptance does not constitute executable PASS, Demo authorization, PAPER/SHADOW/LIVE authorization, or real-money authorization.

## 2. Review pins and producer authority

The TASK noted that a prior E2/E5 review artifact was not present after E4 synchronization. That documentation absence was not treated as producer authority.

The actual merged producer code was verified directly on current `main`:

- E2 accepted producer revision: `f99a8d00cd1fe40e1d73964d8b1cf37bc1886bd4`
- current `main:src/strategy/trade_intent.py` blob SHA: `d2e877cbdcf23058e020db2a2e0158811bcca51b`
- accepted E2 pin had the same blob SHA.

- E5 accepted producer revision: `e5f7088301a92deadfd9f6c416ae03b466c38a47`
- current `main:src/risk/engine.py` blob SHA: `ce07c4ccf7aa7b4d57d47a5b9a00fd3b60bf0c78`
- accepted E5 pin had the same blob SHA.

Therefore the actual merged producer semantics used for this review have not drifted from the accepted E2/E5 implementation pins.

## 3. E5 -> E4 authority boundary

Disposition: `PASS / STATIC ONLY`.

`src/execution/gateway.py` requires the canonical profiled ApprovedTradePlan shape before translation, including:

```text
schema_version             = contracts-v0.1
symbol                     = BTC_USDT_PERP
entry_instruction.profile_version = entry-v0.1
entry_instruction.order_type      = MARKET
quantity_profile_version   = base-asset-v0.1
quantity_unit              = BASE_ASSET
quantity_asset             = BTC
```

The gateway rejects missing required ApprovedTradePlan fields, incompatible schema/symbol/direction, unsupported quantity profile/unit/asset, malformed/non-positive quantity or leverage, malformed instruction containers, invalid timestamps, and expired plans.

A raw TradeIntent lacks the required ApprovedTradePlan authority fields and cannot cross the gateway.

No E4 logic creates a RiskDecision, changes risk approval, invents quantity, or increases the approved canonical exposure.

## 4. Entry translation

Disposition: `PASS / STATIC ONLY`.

The accepted mapping is purely mechanical:

```text
LONG   -> BUY
SHORT  -> SELL
MARKET -> MARKET
ApprovedTradePlan.quantity -> OrderRequest.quantity unchanged
```

The translator requires exact:

```text
profile_version = entry-v0.1
order_type      = MARKET
```

The only allowed entry-instruction fields are:

```text
profile_version
order_type
reference_price
```

Executable `limit_price`, `stop_price`, `trigger_price`, and `time_in_force` are rejected. Unknown entry-instruction fields are rejected.

`reference_price`, when present, is validated as positive finite decimal context only. It is intentionally not promoted to `limit_price`, `stop_price`, trigger semantics, or TIF.

The produced shared `OrderRequest` retains:

```text
quantity_profile_version = base-asset-v0.1
quantity_unit            = BASE_ASSET
quantity_asset           = BTC
quantity                 = canonical approved BTC quantity
```

The provider-native OKX contract count is not written into shared `OrderRequest.quantity`.

## 5. OKX provider metadata boundary

Disposition: `PASS / STATIC ONLY`.

Provider mapping remains isolated in E4:

```text
BTC_USDT_PERP -> OKX BTC-USDT-SWAP
```

`OKXInstrumentMetadata` validates local snapshot facts including:

- provider identity;
- canonical symbol;
- `instrument_id`;
- `inst_type`;
- `ct_val`;
- `ct_mult`;
- `ct_val_ccy`;
- `ct_type`;
- `lot_sz`;
- `min_sz`;
- `tick_sz`;
- instrument `state`;
- UTC observation time;
- non-empty metadata reference;
- explicit freshness-policy version.

New exposure sizing fails closed for:

- missing metadata;
- provider/canonical/instrument mismatch;
- non-`SWAP` instrument type;
- non-`live` state;
- unknown freshness-policy version;
- future-dated metadata;
- stale metadata;
- malformed/non-positive numeric metadata;
- unsupported contract type;
- unsupported `ctValCcy`;
- invalid lot/minimum relationship.

Only the reviewed direct V1 class is accepted:

```text
provider = OKX
instType = SWAP
ctType   = linear
ctValCcy = BTC
state    = live
```

Price-dependent, inverse, non-base-denominated, and otherwise ambiguous conversions fail closed.

## 6. Official OKX provider recheck

Official OKX sources were rechecked during this task:

- `https://www.okx.com/docs-v5/en/`
- `GET /api/v5/public/instruments`
- current public `BTC-USDT-SWAP` instrument response
- official OKX derivatives tutorial/reference for `ctVal * ctMult` semantics

Current provider documentation confirms:

- `ctVal` = contract value;
- `ctMult` = contract multiplier;
- `ctValCcy` = contract-value currency;
- `ctType` includes `linear` / `inverse` for FUTURES/SWAP;
- derivative `lotSz` and `minSz` are contract counts;
- `tickSz` is instrument price tick size;
- instrument state includes `live`, `suspend`, `rebase`, and `post_only` behavior relevant to order eligibility;
- FUTURES/SWAP/OPTION order `sz` is number of contracts;
- `market` is a provider order type for the reviewed derivative path.

The official OKX tutorial/reference also states derivative contract nominal value can be calculated as:

```text
ctVal * ctMult
```

in units of `ctValCcy`.

Current public `BTC-USDT-SWAP` metadata observed through the official public endpoint is compatible with the E4 direct conversion class, including:

```text
instId   = BTC-USDT-SWAP
instType = SWAP
ctType   = linear
ctVal    = 0.01
ctMult   = 1
ctValCcy = BTC
lotSz    = 0.01 contracts
minSz    = 0.01 contracts
tickSz   = 0.1
state    = live
```

This live provider snapshot is review evidence only. It was not executed by project code and is not a replacement for future runtime metadata validation.

## 7. Quantization safety

Disposition: `PASS / STATIC ONLY`.

Implementation follows:

```text
base_per_contract = ctVal * ctMult
raw_contracts     = approved_base_quantity / base_per_contract
provider_sz       = floor(raw_contracts / lotSz) * lotSz
effective_base    = provider_sz * base_per_contract
```

The implementation uses decimal `ROUND_FLOOR` for positive contract quantities.

It then requires:

```text
provider_sz > 0
provider_sz >= minSz
provider_sz is an exact lotSz multiple
0 < effective_base <= canonical approved BTC quantity
```

If the approved amount is below the smallest representable size, E4 rejects. It does not round up to satisfy `minSz` and does not place a compensating residual order.

An explicit final guard rejects any result where:

```text
effective_base > OrderRequest.quantity
```

No static path was found that can quantize upward beyond the E5-approved canonical exposure bound.

## 8. Canonical/provider audit separation

Disposition: `PASS / STATIC ONLY`.

`OKXEntrySizingAudit` keeps distinct:

- canonical approved BTC quantity;
- canonical quantity profile/unit/asset;
- provider identity;
- provider instrument ID;
- provider requested contract quantity;
- effective canonical requested BTC quantity after round-down;
- base-per-contract conversion fact;
- metadata reference and observation time;
- freshness policy version.

Provider contract count is not substituted into shared canonical quantity fields.

Provider fill normalization and full provider order/fill audit remain future adapter/reconciliation work and are not falsely claimed by this task.

## 9. Broker / PaperBroker safety regression

Disposition: `PASS / STATIC ONLY`.

Previously accepted E4 safety behavior remains present:

- stable `client_order_id` for one logical order;
- stable `order_request_id` derived from that identity;
- quantity profile/unit/asset included in idempotency safety fingerprint;
- requested quantity and filled quantity remain distinct;
- partial fills are supported;
- fill quantities cannot exceed the approved `OrderRequest.quantity`;
- same client-order identity with changed safety payload raises idempotency conflict;
- ambiguous submit acknowledgement yields `RECONCILIATION_REQUIRED`;
- ambiguous state does not authorize blind duplicate submission;
- retry requires broker-issued reconciliation evidence;
- reconciliation compares supplied evidence against explicit broker order/position queries;
- retry re-queries order and position truth immediately before retry;
- fabricated reconciliation evidence is rejected.

The `Broker` interface exposes trading/reconciliation operations only. No withdrawal, funding-transfer, or sub-account-capital-movement operation is exposed.

## 10. Deterministic test-definition review

Disposition: `PASS / STATIC ONLY`; executable result remains `NOT_RUN`.

Static test definitions cover the required bounded scenarios, including:

- valid profiled MARKET translation;
- LONG/SHORT side mapping;
- advisory reference price remains non-executable;
- raw TradeIntent cannot cross the ApprovedTradePlan boundary;
- missing/unknown entry or quantity profiles reject;
- unsupported order type and executable price/TIF fields reject;
- malformed quantity and expired plan reject;
- stable idempotency;
- requested-vs-filled separation;
- partial fill and overfill rejection;
- ambiguous acknowledgement/reconciliation/retry safety;
- exact representable OKX size;
- deterministic round-down;
- below-minimum/nonrepresentable reject;
- invalid lot/minimum relation reject;
- stale/missing/malformed/non-tradable/mismatched metadata reject;
- unsupported direct conversion reject;
- provider sizing never exceeds canonical approved BTC;
- canonical BTC quantity and provider contract count remain distinct.

Required future local commands from the E4 handoff:

```text
python -m unittest discover -s tests/execution -p "test_*.py" -v
python -m unittest discover -s tests/brokers -p "test_*.py" -v
```

They were not run in this GitHub review environment.

## 11. Metadata freshness policy classification

Classification: `NON_BLOCKING_HARDENING`.

Current E4-local policy is:

```text
policy = okx-instrument-metadata-freshness-v0.1
max_age = 300 seconds
```

Reasons this is not a current blocker:

1. the policy is explicit and versioned;
2. it lives in E4/provider scope, not shared contracts;
3. missing/future/stale metadata fails closed;
4. this PR implements no provider networking or order submission, so the TTL cannot currently authorize a real provider order;
5. the supported conversion is additionally constrained by identity/type/state/unit validation and the final exposure upper-bound check.

Hardening required before a future Demo/private adapter is accepted:

- do not assume OKX guarantees instrument metadata is unchanged for 300 seconds;
- prefer submit-time refresh or an equally strong current-metadata proof for new exposure;
- account for official `upcChg` / `effTime` scheduled instrument updates where relevant, including updates that can affect `tickSz`, `minSz`, and FUTURES/SWAP `lotSz`;
- a scheduled effective change must invalidate or shorten a cached snapshot even if nominal cache age is below 300 seconds;
- preserve an explicit adapter freshness-policy version and metadata reference in audit evidence.

Owner: E4 in the future provider adapter task.

Finding ID: `E4-OKX-FRESHNESS-HARDEN-001`.

This finding is non-blocking for PR #11 local sizing-layer merge, but it becomes an acceptance criterion before Demo/private provider order construction can be considered safe.

## 12. Changed-file scope / security / repository policy

Disposition: `PASS / STATIC ONLY`.

PR #11 changes only:

- `coordination/E4/STATUS.md`
- `docs/execution/E4_TO_E7_HANDOFF.md`
- `docs/execution/OKX_SIZING_POLICY.md`
- `src/brokers/base.py`
- `src/brokers/okx_sizing.py`
- `src/brokers/paper.py`
- `src/execution/gateway.py`
- `src/execution/models.py`
- `tests/brokers/test_okx_sizing.py`
- `tests/brokers/test_paper_broker.py`
- `tests/execution/test_gateway.py`

No `contracts/**`, E1/E2/E3/E5/E6 production path, `.github/workflows/**`, provider credential file, or asset-movement implementation is present in the PR changed-file set.

No historical E4 evidence file is deleted by the PR. The only deletions reported by the PR are within replaced/updated text content rather than deletion of reviewed history artifacts.

No API key, secret, passphrase, private key, live token, or live `.env` content was found in the reviewed patch.

## 13. PR synchronization / merge readiness

At review time:

- PR #11 is open;
- GitHub reports `mergeable=true`;
- current E4 branch is ahead of latest main by its E4 history and behind latest main by 2 commits;
- those 2 newer main commits change only `coordination/E4/TASK.md` and `coordination/E7/TASK.md`;
- no producer/domain/contract file changed in that delta.

Therefore the branch-behind status is not a source/contract blocker for this static review.

Merge recommendation:

```text
PASS — PM MAY MERGE PR #11
```

This means merge the reviewed source/history into `main`; it does not mean executable verification passed.

## 14. Next-stage recommendation

After PR #11 is merged, PM may issue a separate bounded E4 task for the next provider stage.

Recommended construction scope may include, under a new explicit TASK:

- OKX Demo-first provider adapter structure;
- current official instrument metadata retrieval/caching with the freshness hardening above;
- provider request mapping for `instId`, `tdMode`, `ordType`, and `sz`;
- provider-safe client-order-ID mapping/validation;
- account-mode / isolated-operation prerequisite verification;
- authenticated Demo request construction and fail-closed response/reconciliation semantics if explicitly authorized by that future TASK;
- local-only executable verification in a Product-Owner-approved environment.

This recommendation does **not** authorize:

- real-money execution;
- production credentials in Git;
- withdrawal/funding-transfer/sub-account movement;
- PAPER/SHADOW/LIVE transition;
- release-gate advancement;
- Demo/private network execution in this current review task.

Real-money execution remains blocked pending later release gates and explicit Product Owner approval.

## 15. Release / executable disposition

```text
Executable verification: NOT_RUN
Gate A RESEARCH_READY: BLOCKED / UNCHANGED
Gate B PAPER_READY: BLOCKED / UNCHANGED
Gate C SHADOW_READY: BLOCKED / UNCHANGED
Gate D LIVE_READY: BLOCKED / UNCHANGED
```

No GitHub Actions, CI, hosted runner, GitHub-triggered runner, project test, provider API experiment, or broker simulation was used for executable verification.

## 16. Findings

### Blocking findings

`NONE` in the reviewed static/source scope.

### Non-blocking hardening

- `E4-OKX-FRESHNESS-HARDEN-001` — owner E4 in future provider adapter construction; 300-second metadata TTL must not be treated as provider stability guarantee and must account for current/scheduled metadata changes before Demo/private order acceptance.

## 17. Completion

Task `E7-20260821-008` is complete at static/source-review level.

E7 does not merge PR #11, does not modify E4 implementation, does not start provider networking, and does not advance any release gate. E7 stops and waits for PM.
