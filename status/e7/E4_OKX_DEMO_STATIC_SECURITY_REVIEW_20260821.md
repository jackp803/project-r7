# E7 Static Security / Integration Review — E4 OKX Demo Adapter

- Task: `E7-20260821-010`
- Review date: `2026-08-21`
- Reviewer: E7 Integration / Architecture / System QA / Release
- PR: `#12 execution: add Demo-first OKX provider adapter`
- PR branch: `agent/e4-okx-demo-adapter-20260821`
- Reviewed implementation/tests/docs/handoff revision: `b7031c52a38623c528ee9352276793d8110854e0`
- Current PR head observed during review: `94ca2f861d9e7a51277c5c63ff20f730c7f19f92`
- Parent E4 sizing merge: `9679a224da3764ecbab7161e6c6f256ca46aecf7`
- Parent schema: `contracts-v0.1`
- Entry profile: `entry-v0.1 / MARKET`
- Quantity profile: `base-asset-v0.1 / BASE_ASSET / BTC`
- Executable verification: `NOT_RUN`
- Actual OKX Demo/provider requests: `NOT_SENT`

## 1. Executive disposition

PR #12 is **not statically acceptable for merge in its current form**.

Separate dispositions:

| Review area | Disposition |
|---|---|
| Demo environment / authentication security | `PASS / STATIC ONLY` |
| Request materialization / account prerequisites | `FAIL / BLOCKING` |
| Freshness hardening | `PASS / ACCEPT / STATIC ONLY` |
| Ambiguity / reconciliation / retry safety | `FAIL / BLOCKING` |
| Provider response normalization | `FAIL / BLOCKING` |
| Broker / PaperBroker regression compatibility | `PASS / STATIC ONLY` |
| PR #12 merge recommendation | `BLOCKED / DO NOT MERGE` |
| Approved-local Demo connectivity/dry integration stage | `BLOCKED` |
| Demo order authorization | `NOT AUTHORIZED` |
| PAPER / SHADOW / LIVE | `BLOCKED / UNCHANGED` |

The static blockers are source-level safety defects. They were identified without executing project code and without sending a provider request.

## 2. Review scope / branch state

The E7 target branch `agent/e7-e4-okx-demo-review-20260821` was confirmed identical to latest `main` at task start.

PR #12 current head is one STATUS-only commit ahead of the implementation pin:

```text
b7031c52a38623c528ee9352276793d8110854e0
  -> 94ca2f861d9e7a51277c5c63ff20f730c7f19f92
```

The successor changes only `coordination/E4/STATUS.md`. Production/test/docs review therefore remains pinned to `b7031c52...`.

The PR branch was two commits behind the latest `main` observed during review, but those main-side changes modified only `coordination/E4/TASK.md` and `coordination/E7/TASK.md`. No producer, shared-contract, or E4 parent implementation drift was found from that delta.

Changed-file scope is bounded to E4 code/tests/docs/status:

- `coordination/E4/STATUS.md`
- `docs/execution/E4_TO_E7_HANDOFF.md`
- `docs/execution/OKX_DEMO_ADAPTER.md`
- `docs/execution/OKX_SIZING_POLICY.md`
- `src/brokers/okx_demo.py`
- `src/brokers/okx_sizing.py`
- `tests/brokers/test_okx_demo_adapter.py`
- `tests/brokers/test_okx_demo_status_mapping.py`
- `tests/brokers/test_okx_sizing.py`

No shared-contract edit, other-agent production rewrite, GitHub workflow/CI addition, real credential material, asset-movement method, or account/leverage/position-mode setter was found in scope.

## 3. Official OKX V5 provider fact recheck

Current official OKX API V5 documentation/changelog was rechecked for the provider assumptions used by the adapter.

Confirmed for this bounded review:

- current global REST guidance includes `https://openapi.okx.com`;
- Demo authenticated requests require `x-simulated-trading: 1`;
- private REST authentication uses `OK-ACCESS-KEY`, `OK-ACCESS-SIGN`, `OK-ACCESS-TIMESTAMP`, and `OK-ACCESS-PASSPHRASE`;
- REST signature material is `timestamp + method + requestPath + body`, HMAC-SHA256 with the secret and Base64 encoded;
- GET query parameters participate in `requestPath` signing;
- `clOrdId` is case-sensitive alphanumeric, maximum 32 characters, with uniqueness scoped to pending orders rather than guaranteed across full history;
- SWAP order `sz` is provider contract quantity;
- `tdMode=isolated`, `side`, `posSide`, and `ordType=market` are provider request concepts and remain adapter-local;
- current account config exposes `acctLv` and `posMode`;
- current private read surfaces include account config, positions, pending orders, order details, and fills;
- public instrument metadata exposes the contract/lot/state facts required by the accepted E4 sizing boundary;
- current `upcChg` shape exposes scheduled changes such as `tickSz`, `minSz`, and `maxMktSz` with `newValue` and `effTime`;
- known order states include `live`, `partially_filled`, `filled`, `canceled`, and `mmp_canceled`.

No current official global source was found that was strong enough to canonicalize test fixture code `51603` as a stable, deployment-independent order-absence contract for this project. It is therefore not accepted as repository authority for retry enablement.

Provider facts must be rechecked again when an approved-local provider stage is eventually authorized.

## 4. Demo environment / authentication security — PASS / STATIC ONLY

Accepted statically:

- credentials are constructor/runtime injected rather than read from a committed secret file;
- `OKXCredentials.__repr__` is redacted;
- prepared request representation exposes header names/body length rather than private header values;
- authenticated request construction always adds `x-simulated-trading: 1`;
- non-Demo environment is structurally rejected by `OKXDemoAdapterConfig`;
- alternate REST base configuration is rejected by the bounded config;
- private endpoint allowlist is limited to the task-authorized place-order/reconciliation read paths;
- no withdrawal, deposit, transfer, funding movement, sub-account capital movement, leverage setter, position-mode setter, or account-mode mutation API was added;
- no real credential/secret value was found in PR scope;
- no concrete provider request was sent during this review.

Non-blocking future connectivity hardening:

- before a concrete transport is accepted, bind that transport itself to the approved Demo/global host and TLS behavior; merely validating a config string does not constrain an arbitrary injected transport implementation;
- before connectivity, verify provider time synchronization / timestamp precision and allowable request-clock skew using current official guidance.

These are not the reason PR #12 is blocked today.

## 5. Request materialization / account prerequisites — FAIL / BLOCKING

### Finding `E4-OKX-MATERIALIZATION-INTEGRITY-001` — BLOCKING

**Owner:** E4

`materialize_demo_market_order()` accepts a caller-supplied `OKXEntrySizingAudit` and validates several identity fields, but it does not re-establish the provider exposure calculation from the supplied current metadata.

The materializer checks, among other things:

```text
sizing.trade_plan_id == request.trade_plan_id
sizing.canonical_approved_quantity == request.quantity
sizing.provider / instrument identity
metadata_ref / observed_at equality
provider side
provider_requested_contract_quantity > 0
0 < sizing.effective_canonical_requested_quantity <= request.quantity
```

It then serializes:

```text
body.sz = sizing.provider_requested_contract_quantity
```

However, `OKXEntrySizingAudit` is an ordinary caller-constructible dataclass. The materializer does not recompute or prove:

```text
base_per_contract = current ctVal * current ctMult
provider_sz is a current lotSz multiple
provider_sz >= current minSz
provider_sz is within current provider market-size constraints as applicable
effective_base = provider_sz * base_per_contract
effective_base <= E5-approved canonical BTC quantity
```

Therefore a forged/tampered sizing audit can pair an arbitrarily large provider contract `sz` with a fabricated small `effective_canonical_requested_quantity`, while keeping the currently checked IDs/reference fields consistent. The body can then contain provider exposure that is not structurally tied to the E5-approved BTC bound.

This violates the mandatory quantity safety invariant and blocks merge.

**Required E4 correction:** at materialization, recompute/verify provider sizing against the exact `OrderRequest` and current validated metadata, or replace the caller-constructible audit trust boundary with an adapter-issued/opaque integrity-bound artifact. The order body `sz` must be derivable from and provably bounded by the exact canonical request and current metadata.

**Required tests:** forged sizing audit with oversized `provider_sz`, falsified effective quantity, metadata mismatch/tamper, lot/min violation, and any changed materialization must fail closed.

### Finding `E4-OKX-ACCOUNT-MATRIX-001` — BLOCKING

**Owner:** E4

`OKXDemoAdapterConfig` independently accepts:

```text
expected_account_level in {1,2,3,4}
expected_position_mode in {net_mode,long_short_mode}
```

and prerequisite validation only proves that provider-read values equal those configured values.

Explicit configuration is not proof that a particular account-level / position-mode combination is legal or supported for this bounded isolated `BTC-USDT-SWAP` flow. Current official semantics make at least some combinations definitely incompatible, including Spot mode (`acctLv=1`) for this derivatives flow and Portfolio margin with `long_short_mode` where the mode is not supported. Where account/region/product combinations remain ambiguous, this project must fail closed rather than let caller configuration declare them valid.

**Required E4 correction:** encode a reviewed supported account-level/position-mode matrix for the bounded adapter, or narrow V1 to a single explicitly approved combination. Reject unsupported/uncertain combinations before request materialization.

**Required tests:** test legal supported combinations and explicit rejection of impossible/unsupported combinations, not only “actual value differs from configured value.”

### Dedicated R7 sub-account identity

The Product Owner baseline requires a dedicated R7 sub-account for future real execution. The current staged architecture places Demo before that real-execution boundary. Therefore absence of a hard-coded expected `uid/mainUid` binding is not independently treated as a PR #12 Demo-source merge blocker here.

Before any future real execution stage, account identity must be explicitly bound to the intended R7 sub-account and must reject the Product Owner's general-purpose/main account.

## 6. Freshness hardening — PASS / ACCEPT / STATIC ONLY

Finding `E4-OKX-FRESHNESS-HARDEN-001` is statically addressed in this revision.

Accepted E4-local policy:

```text
freshness policy version = okx-instrument-metadata-freshness-v0.2
general sizing/cache ceiling = 300 seconds
submit preparation max observation age = 5 seconds
scheduled sizing-change guard = 60 seconds
```

Accepted behavior:

- submit preparation revalidates metadata instead of treating the old 300-second cache ceiling as submit permission;
- observations older than five seconds are rejected at materialization;
- malformed/unknown scheduled-change parameters fail closed;
- already-effective scheduled changes remaining in the snapshot fail closed;
- scheduled `minSz` / `maxMktSz` changes inside the 60-second guard block materialization;
- `tickSz` remains audit metadata and does not manufacture a MARKET entry price.

The five-second and sixty-second thresholds are E4 safety margins, not OKX stability guarantees and must not move into shared contracts merely for convenience.

Executable/provider validation remains `NOT_RUN` / `NOT_SENT`.

## 7. Ambiguity / reconciliation / retry safety — FAIL / BLOCKING

### Finding `E4-OKX-RETRY-PROVENANCE-001` — BLOCKING

**Owner:** E4

`OKXReconciliationEvidence` and nested `OKXOrderLookup` are caller-constructible dataclasses. `retry_entry()` accepts a caller-supplied evidence object and only validates its visible field values.

Current checks include:

```text
retry_allowed == true
matching provider clOrdId
explicit_absence_code is not None
no fills
no non-zero position
no matching pending order
```

There is no adapter-issued one-time retry token, MAC/signature, internal evidence registry, immutable fresh-query handle, exact materialization fingerprint, or fresh provider-query recomputation inside `retry_entry()`.

A caller can therefore fabricate an evidence object satisfying those fields, causing the adapter to discard the prior ambiguous result and execute a second submit. This directly violates TASK requirement 8 and is a blocking duplicate-exposure safety defect.

The source comment that evidence is “produced by reconcile_ambiguous” is not an enforceable provenance property.

**Required E4 correction:** retry authorization must be structurally derived from fresh provider truth and bound to the exact ambiguous materialization. Acceptable patterns include a one-time adapter-issued token bound to a canonical materialization fingerprint and internally stored fresh-query result, or recomputation/query inside `retry_entry()`. Caller-constructible data alone must never authorize retry.

**Required tests:** forged evidence, mutated evidence, replayed/consumed evidence, evidence for another materialization, and materially changed body/size under the same logical client identity must all fail without a second submit.

### Finding `E4-OKX-ORDER-ABSENCE-001` — BLOCKING FOR RETRY CAPABILITY

**Owner:** E4

The conservative default `order_not_found_codes=frozenset()` is safe because no non-success order lookup proves absence. However, the adapter permits an arbitrary caller-provided code set to become authoritative absence semantics, and the fake test demonstrates retry with configured `51603`.

This review did not find a sufficiently stable current official OKX global source to adopt `51603` as a canonical project-wide absence code. An arbitrary configuration value must not create authority that the official provider contract has not established for this deployment.

**Required E4 correction:** keep retry structurally disabled until an E7-reviewed/provider-authoritative order-absence policy exists, or make the absence policy itself a controlled, validated adapter policy that an ordinary caller cannot invent. In all cases, actual Demo retry remains blocked until approved-local integration proves the relevant current absence semantics.

The correction to retry provenance remains required even if retry is initially disabled.

## 8. Reconciliation truth-set review

The intended reconciliation truth set is directionally correct:

```text
GET order by clOrdId + instId
GET positions for BTC-USDT-SWAP
GET fills for BTC-USDT-SWAP, correlated to clOrdId
GET pending orders, correlated to clOrdId
```

Positive provider truth blocks retry when an order, matching fill, non-zero exposure, or matching pending order exists.

Requested provider contracts, fill contracts, positions, and canonical normalized quantities remain represented as distinct facts rather than being collapsed into one field.

This design is not enough to overcome the provenance/order-absence blockers above.

## 9. Provider response normalization — FAIL / BLOCKING

### Accepted response behavior

- place-order acknowledgement is not treated as fill truth;
- success acknowledgement maps only to `PENDING` with zero canonical filled quantity;
- explicit row rejection maps to `REJECTED`;
- malformed/unknown/id-mismatched acknowledgement maps to `RECONCILIATION_REQUIRED`;
- provider order `sz` must equal the materialized provider quantity;
- accumulated fill contracts cannot exceed requested contracts;
- provider fill rows require provider order/trade identity and normalize contract fill quantities into canonical BTC;
- cumulative fill rows exceeding materialized provider contracts fail closed;
- unknown provider order state maps to `RECONCILIATION_REQUIRED`.

### Finding `E4-OKX-ORDER-STATE-CONSISTENCY-001` — BLOCKING

**Owner:** E4

Known provider states are mapped directly without enforcing state/fill-quantity consistency.

Examples currently accepted by the parser include conceptually impossible/contradictory combinations such as:

```text
state=filled with accFillSz < sz
state=partially_filled with accFillSz = 0
state=live with accFillSz > 0
```

Under current official state semantics these facts are contradictory. In particular, `filled` is a fully executed terminal state and `live` represents an active order without fills. Mapping a contradictory response optimistically to `FILLED`, `PARTIALLY_FILLED`, or `OPEN` violates the task's fail-closed normalization requirement.

**Required E4 correction:** enforce a state/fill consistency table before returning a normal canonical state. At minimum:

```text
live             -> accFillSz == 0
partially_filled -> 0 < accFillSz < sz
filled           -> accFillSz == sz
canceled / mmp_canceled -> 0 <= accFillSz <= sz; average fill price required when filled > 0
```

Any contradictory/malformed combination must produce explicit hard failure or `RECONCILIATION_REQUIRED`, never optimistic success.

**Required tests:** each contradictory state/fill combination must be covered deterministically.

## 10. Provider `clOrdId` / idempotency review

The deterministic mapping:

```text
clOrdId = "R7" + first 30 hex characters of SHA-256(internal E4 client_order_id)
```

is statically acceptable as a provider-local legal identifier:

- deterministic;
- alphanumeric;
- 32 characters;
- traceable alongside the original internal client-order ID.

Correctly, the implementation does not assume historical provider uniqueness because current provider semantics scope uniqueness to pending orders and a historical value may be reused.

However, `clOrdId` stability alone does not prove order-material integrity. The retry and sizing-artifact blockers above must bind the exact request/materialization to the retry identity before the path is safe.

## 11. Deterministic test-definition review

Good static coverage exists for:

- signing and Demo headers with fake credentials;
- production-mode/base configuration rejection;
- legal/stable `clOrdId`;
- isolated MARKET payload;
- provider `sz` vs canonical BTC separation on valid sizing output;
- net/long-short `posSide` mapping;
- configured-vs-observed account/position-mode mismatch;
- existing target exposure/pending orders blocking new exposure;
- acknowledgement as PENDING;
- timeout ambiguity and ordinary resubmit suppression;
- provider order size contradiction;
- provider fill-contract to canonical-BTC normalization;
- order/position/fill/pending reconciliation sequence;
- no default absence code -> no retry;
- no asset-movement/account-mutation methods;
- five-second submit freshness;
- scheduled-change guard / unknown scheduled-change rejection.

Blocking missing coverage aligns with the source defects:

- forged caller-constructed reconciliation evidence;
- mutated/replayed reconciliation evidence;
- evidence/materialization fingerprint mismatch;
- forged/tampered sizing audit with excessive `sz` and falsified effective BTC;
- materially changed order materialization under the same logical ID;
- invalid supported-account-level / position-mode matrix combinations;
- `filled` with partial quantity;
- `partially_filled` with zero quantity;
- `live` with non-zero fill quantity.

Additional redaction hardening should assert that API key and passphrase, not only secret key, stay out of diagnostic representations.

No tests were executed in GitHub.

## 12. Broker / PaperBroker regression compatibility — PASS / STATIC ONLY

PR #12 does not modify the previously accepted broker-neutral core files:

- `src/brokers/base.py`
- `src/brokers/paper.py`
- `src/execution/gateway.py`
- `src/execution/models.py`

No static evidence was found that this PR rewrites the previously accepted stable-idempotency, requested-vs-filled, partial-fill, overfill, ambiguity, or query/reconcile-before-retry PaperBroker semantics.

Executable regression evidence remains `NOT_RUN`.

## 13. Merge and next-stage recommendation

### PR #12

```text
DO NOT MERGE
```

PR merge is blocked until E4 corrects and hands off at least:

1. `E4-OKX-MATERIALIZATION-INTEGRITY-001`
2. `E4-OKX-ACCOUNT-MATRIX-001`
3. `E4-OKX-RETRY-PROVENANCE-001`
4. `E4-OKX-ORDER-ABSENCE-001`
5. `E4-OKX-ORDER-STATE-CONSISTENCY-001`

E7 must then re-review the revised E4 source/test definitions before merge.

### Approved-local Demo connectivity / dry integration

```text
NOT YET
```

The next stage must not begin while source safety remains blocked. After source correction + E7 static PASS, PM/Product Owner may separately decide whether to authorize an approved-local connectivity/dry integration stage.

Even then:

- actual Demo order submission requires separate explicit authorization;
- Demo retry remains disabled until authoritative absence semantics and retry provenance are accepted and locally verified;
- provider/account prerequisites must be verified from live Demo account facts;
- no successful Demo operation advances PAPER/SHADOW/LIVE automatically;
- real-money execution remains separately blocked.

## 14. Verification / release disposition

```text
Executable tests             NOT_RUN
Fake-transport tests          NOT_RUN
Provider connectivity         NOT_RUN / NOT_SENT
Demo order                    NOT_SENT / NOT AUTHORIZED
GitHub Actions / CI / runner  NOT_USED
Codex ticket                  NONE / NOT_APPLICABLE WITHOUT LOCAL REPRODUCTION
Gate A                        BLOCKED / UNCHANGED
Gate B                        BLOCKED / UNCHANGED
Gate C                        BLOCKED / UNCHANGED
Gate D                        BLOCKED / UNCHANGED
```

No E1-E6 production code, shared contract, provider credential, provider account configuration, or provider state was modified by E7.

E7 stops after persisting this review and STATUS and waits for PM.